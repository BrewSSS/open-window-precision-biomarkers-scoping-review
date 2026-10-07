#!/usr/bin/env python3
"""Generic runner: send every record in a batch CSV to one LLM API, one record per request,
validate the JSON response against ai_triage/schema_v1.json, checkpoint every 50 records.

Uses only the `requests` library (no openai/anthropic SDKs). Two provider modes:

  openai_compat  -> POST {base_url}/chat/completions
                    body: {model, messages:[system,user], temperature, response_format:{"type":"json_object"}}

  anthropic      -> POST {base_url}/v1/messages
                    headers: x-api-key, anthropic-version: 2023-06-01
                    body: {model, system, messages:[user], temperature, max_tokens:1500}

Both: header User-Agent: scoping-review-search/1.0. No e-mail or personal data is ever sent.

API key is read ONLY from an environment variable (--api-key-env VAR_NAME). If that env var is
not already set, this script will try to source KEY=VALUE lines from --secrets-file (default
~/.config/scoping_review/secrets.env) into the process environment first (it does not print the
key, does not log it, and does not write it to any output file).

Checkpointing: every 50 processed records, writes {out_dir}/checkpoint_{batchname}.json. At the
end (or on a clean finish) writes {out_dir}/{batchname}.json with the full run metadata. Each
record's raw_response (provider's raw text, parsed-JSON side) is stored alongside the validated
result; the schema restricts quotes to <=25 words and forbids free re-typing of the whole
abstract, so these outputs should never contain full abstract text as long as the model
complies with the prompt -- this script does not re-embed the input abstract in its outputs
beyond what the model echoes.

--resume skips record_ids already present in an existing checkpoint or final file for the same
batchname in the same out-dir.

--dry-run builds the exact request payload for the FIRST record in --in and prints it (as JSON)
WITHOUT sending any network request, then exits 0. Use this to inspect payload shape for either
provider with a dummy API key env var.
"""
import argparse
import csv
import json
import logging
import os
import sys
import time
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

try:
    import jsonschema  # optional; used only if importable
except ImportError:
    jsonschema = None

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SECRETS_FILE = Path.home() / ".config/scoping_review/secrets.env"
USER_AGENT = "scoping-review-search/1.0"


# --------------------------------------------------------------------------------------
# Prompt file parsing
# --------------------------------------------------------------------------------------

def parse_prompt_file(path: Path):
    """Extract the system prompt and the user-message template from prompt_v1.md."""
    text = path.read_text(encoding="utf-8")

    sys_match = re.search(
        r"## SYSTEM PROMPT.*?\n\n(.*?)\n\n---\n", text, re.S
    )
    if not sys_match:
        raise SystemExit(f"Could not locate '## SYSTEM PROMPT' section in {path}")
    system_prompt = sys_match.group(1).strip()

    user_match = re.search(
        r"## USER MESSAGE TEMPLATE.*?```\n(.*?)\n```", text, re.S
    )
    if not user_match:
        raise SystemExit(f"Could not locate '## USER MESSAGE TEMPLATE' code block in {path}")
    user_template = user_match.group(1)

    return system_prompt, user_template


def render_user_message(template: str, row: dict) -> str:
    return (
        template.replace("{record_id}", row.get("record_id", ""))
        .replace("{title}", row.get("title", "") or "")
        .replace("{journal}", row.get("journal", "") or "")
        .replace("{year}", row.get("year", "") or "")
        .replace("{abstract}", row.get("abstract", "") or "")
    )


# --------------------------------------------------------------------------------------
# Minimal schema validator (jsonschema used if importable, else hand-rolled)
# --------------------------------------------------------------------------------------

def _resolve_refs(node, schema):
    """Very small local $ref / allOf resolver for this schema's shape (#/$defs/...)."""
    if isinstance(node, dict):
        if "$ref" in node:
            ref = node["$ref"]
            assert ref.startswith("#/$defs/"), f"unsupported $ref: {ref}"
            target = schema["$defs"][ref.split("/")[-1]]
            return _resolve_refs(target, schema)
        if "allOf" in node:
            merged = {}
            for sub in node["allOf"]:
                resolved = _resolve_refs(sub, schema)
                for k, v in resolved.items():
                    if k == "properties" and k in merged:
                        merged[k] = {**merged[k], **v}
                    else:
                        merged[k] = v
            # properties/required declared alongside allOf (sibling keys) still apply
            for k, v in node.items():
                if k == "allOf":
                    continue
                if k == "properties" and k in merged:
                    merged[k] = {**merged[k], **v}
                else:
                    merged[k] = v
            return merged
        return {k: _resolve_refs(v, schema) for k, v in node.items()}
    if isinstance(node, list):
        return [_resolve_refs(v, schema) for v in node]
    return node


def minimal_validate(instance, schema):
    """Hand-rolled required-keys + enum-values validator. Returns list of error strings."""
    errors = []
    root = _resolve_refs(schema, schema)

    def validate_node(inst, node, path):
        if not isinstance(node, dict):
            return
        node_type = node.get("type")
        if node_type == "object" or ("properties" in node):
            if not isinstance(inst, dict):
                errors.append(f"{path}: expected object, got {type(inst).__name__}")
                return
            for req in node.get("required", []):
                if req not in inst:
                    errors.append(f"{path}: missing required key '{req}'")
            for key, subnode in node.get("properties", {}).items():
                if key in inst:
                    validate_node(inst[key], subnode, f"{path}.{key}")
        elif node_type == "array":
            if not isinstance(inst, list):
                errors.append(f"{path}: expected array, got {type(inst).__name__}")
                return
            item_schema = node.get("items")
            if item_schema:
                for i, item in enumerate(inst):
                    validate_node(item, item_schema, f"{path}[{i}]")
        elif "enum" in node:
            if inst not in node["enum"]:
                errors.append(f"{path}: value {inst!r} not in enum {node['enum']}")
        elif node_type == "string":
            if not isinstance(inst, str):
                errors.append(f"{path}: expected string, got {type(inst).__name__}")
            max_len = node.get("maxLength")
            if max_len and isinstance(inst, str) and len(inst) > max_len:
                errors.append(f"{path}: string longer than maxLength={max_len}")

    validate_node(instance, root, "$")
    return errors


def validate_against_schema(instance, schema):
    if jsonschema is not None:
        validator = jsonschema.Draft202012Validator(schema)
        errs = sorted(validator.iter_errors(instance), key=str)
        return [str(e) for e in errs]
    return minimal_validate(instance, schema)


# --------------------------------------------------------------------------------------
# Secrets / API key handling
# --------------------------------------------------------------------------------------

def load_secrets_file_into_env(secrets_file: Path):
    if not secrets_file.exists():
        return
    for line in secrets_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def get_api_key(env_var: str, secrets_file: Path) -> str:
    if env_var in os.environ and os.environ[env_var]:
        return os.environ[env_var]
    load_secrets_file_into_env(secrets_file)
    if env_var in os.environ and os.environ[env_var]:
        return os.environ[env_var]
    raise SystemExit(
        f"API key env var '{env_var}' is not set and was not found in {secrets_file}. "
        "Refusing to proceed (never pass keys on the command line)."
    )


# --------------------------------------------------------------------------------------
# Payload construction
# --------------------------------------------------------------------------------------

def build_payload(provider, model, system_prompt, user_message, temperature):
    if provider == "openai_compat":
        url_suffix = "/chat/completions"
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        headers = {"Content-Type": "application/json", "User-Agent": USER_AGENT}
        return url_suffix, headers, body
    elif provider == "anthropic":
        url_suffix = "/v1/messages"
        body = {
            "model": model,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_message}],
            "temperature": temperature,
            "max_tokens": 1500,
        }
        headers = {
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
            "User-Agent": USER_AGENT,
        }
        return url_suffix, headers, body
    else:
        raise ValueError(f"unknown provider: {provider}")


def extract_text_from_response(provider, resp_json):
    if provider == "openai_compat":
        return resp_json["choices"][0]["message"]["content"]
    elif provider == "anthropic":
        parts = resp_json.get("content", [])
        return "".join(p.get("text", "") for p in parts if p.get("type") == "text")
    raise ValueError(provider)


def extract_model_name(provider, resp_json, fallback):
    return resp_json.get("model", fallback)


def extract_json_object(text):
    """Best-effort extraction of a JSON object from model text (strip markdown fences)."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\n", "", text)
        text = re.sub(r"\n```$", "", text)
    return json.loads(text)


# --------------------------------------------------------------------------------------
# Checkpoint I/O
# --------------------------------------------------------------------------------------

def load_existing_results(out_dir: Path, batchname: str):
    final_path = out_dir / f"{batchname}.json"
    checkpoint_path = out_dir / f"checkpoint_{batchname}.json"
    for path in (final_path, checkpoint_path):
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return {r["record_id"]: r for r in data.get("results", [])}, data
            except (json.JSONDecodeError, KeyError):
                continue
    return {}, None


def write_run_file(path: Path, run_meta: dict, results: list):
    payload = dict(run_meta)
    payload["n_records"] = len(results)
    payload["results"] = results
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--provider", required=True, choices=["openai_compat", "anthropic"])
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--api-key-env", required=True, help="Name of the environment variable holding the API key")
    ap.add_argument("--secrets-file", default=str(DEFAULT_SECRETS_FILE),
                     help=f"KEY=VALUE lines sourced into env if --api-key-env is unset (default {DEFAULT_SECRETS_FILE})")
    ap.add_argument("--in", dest="in_csv", required=True, help="Input batch CSV (record_id,title,journal,year,pmid,doi,abstract)")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--prompt", default=str(ROOT / "04_screening/formal_2026-10-05_v0.9/ai_triage/prompt_v1.md"))
    ap.add_argument("--schema", default=str(ROOT / "04_screening/formal_2026-10-05_v0.9/ai_triage/schema_v1.json"))
    ap.add_argument("--rate", type=float, default=1.0, help="requests per second")
    ap.add_argument("--max-retries", type=int, default=5)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--dry-run", action="store_true",
                     help="Build and print the request payload for the first record only; send nothing.")
    args = ap.parse_args()

    in_csv = Path(args.in_csv)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    batchname = in_csv.stem

    prompt_path = Path(args.prompt)
    schema_path = Path(args.schema)
    system_prompt, user_template = parse_prompt_file(prompt_path)
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    prompt_sha256 = hashlib.sha256(prompt_path.read_bytes()).hexdigest()
    schema_sha256 = hashlib.sha256(schema_path.read_bytes()).hexdigest()

    with in_csv.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if args.dry_run:
        if not rows:
            raise SystemExit(f"No rows in {in_csv}")
        first = rows[0]
        user_message = render_user_message(user_template, first)
        _, headers, body = build_payload(args.provider, args.model, system_prompt, user_message, args.temperature)
        safe_headers = dict(headers)
        print(f"# DRY RUN -- provider={args.provider} base_url={args.base_url}")
        print(f"# endpoint: {args.base_url}{'/chat/completions' if args.provider=='openai_compat' else '/v1/messages'}")
        print(f"# headers (auth header name shown, value withheld):")
        print(json.dumps(safe_headers, indent=2))
        auth_header = "Authorization: Bearer <REDACTED>" if args.provider == "openai_compat" else "x-api-key: <REDACTED>"
        print(f"# + {auth_header}")
        print("# body:")
        print(json.dumps(body, indent=2, ensure_ascii=False))
        return 0

    if requests is None:
        raise SystemExit("The 'requests' library is required to send live requests (not needed for --dry-run).")

    api_key = get_api_key(args.api_key_env, Path(args.secrets_file))

    log_path = out_dir / "run.log"
    logger = logging.getLogger(batchname)
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler(log_path)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(fh)

    existing_results, existing_meta = ({}, None)
    if args.resume:
        existing_results, existing_meta = load_existing_results(out_dir, batchname)
        logger.info("Resuming: %d records already complete", len(existing_results))

    results = list(existing_results.values())
    done_ids = set(existing_results.keys())
    started_utc = (existing_meta or {}).get("started_utc") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    run_meta = {
        "batch": batchname,
        "provider": args.provider,
        "model": args.model,
        "prompt_sha256": prompt_sha256,
        "schema_sha256": schema_sha256,
        "started_utc": started_utc,
        "finished_utc": None,
    }

    min_interval = 1.0 / args.rate if args.rate > 0 else 0.0
    exit_code = 0
    processed_since_checkpoint = 0

    try:
        for row in rows:
            record_id = row["record_id"]
            if record_id in done_ids:
                continue

            user_message = render_user_message(user_template, row)
            url_suffix, headers, body = build_payload(
                args.provider, args.model, system_prompt, user_message, args.temperature
            )
            headers["Authorization" if args.provider == "openai_compat" else "x-api-key"] = (
                f"Bearer {api_key}" if args.provider == "openai_compat" else api_key
            )

            attempt = 0
            parsed = None
            raw_text = None
            validation_errors = None
            model_returned = args.model
            repaired_once = False

            while attempt <= args.max_retries:
                attempt += 1
                try:
                    t0 = time.time()
                    resp = requests.post(args.base_url.rstrip("/") + url_suffix, headers=headers, json=body, timeout=60)
                    elapsed = time.time() - t0
                    if resp.status_code != 200:
                        logger.warning("record %s attempt %d: HTTP %d: %s", record_id, attempt, resp.status_code, resp.text[:500])
                        time.sleep(min(2 ** attempt, 30))
                        continue
                    resp_json = resp.json()
                    model_returned = extract_model_name(args.provider, resp_json, args.model)
                    raw_text = extract_text_from_response(args.provider, resp_json)
                    parsed = extract_json_object(raw_text)
                    validation_errors = validate_against_schema(parsed, schema)
                    if not validation_errors:
                        break
                    logger.warning("record %s attempt %d: schema validation failed: %s", record_id, attempt, validation_errors)
                    if not repaired_once:
                        repaired_once = True
                        user_message = (
                            render_user_message(user_template, row)
                            + "\n\nYour previous reply did not validate against the required JSON schema "
                              f"(errors: {validation_errors}). Reply again with ONLY a corrected JSON object."
                        )
                        _, headers, body = build_payload(
                            args.provider, args.model, system_prompt, user_message, args.temperature
                        )
                        headers["Authorization" if args.provider == "openai_compat" else "x-api-key"] = (
                            f"Bearer {api_key}" if args.provider == "openai_compat" else api_key
                        )
                        continue
                    else:
                        break  # give up after one repair attempt; record what we have
                except (requests.RequestException, json.JSONDecodeError, KeyError, IndexError) as exc:
                    logger.warning("record %s attempt %d: error %s", record_id, attempt, exc)
                    time.sleep(min(2 ** attempt, 30))
                    continue
                finally:
                    if min_interval:
                        time.sleep(min_interval)

            result_entry = {
                "record_id": record_id,
                "model_returned": model_returned,
                "parsed": parsed,
                "raw_response": raw_text,
                "validation_errors": validation_errors,
                "attempts": attempt,
            }
            results.append(result_entry)
            done_ids.add(record_id)
            processed_since_checkpoint += 1

            if validation_errors:
                logger.error("record %s: unresolved schema validation errors after retries: %s", record_id, validation_errors)

            if processed_since_checkpoint >= 50:
                write_run_file(out_dir / f"checkpoint_{batchname}.json", run_meta, results)
                logger.info("Checkpoint written at %d records", len(results))
                processed_since_checkpoint = 0

    except Exception as exc:  # unrecoverable error: keep checkpoint, exit non-zero
        write_run_file(out_dir / f"checkpoint_{batchname}.json", run_meta, results)
        logger.exception("Unrecoverable error: %s", exc)
        print(f"FATAL: {exc}. Checkpoint preserved at {out_dir / ('checkpoint_' + batchname + '.json')}", file=sys.stderr)
        return 1

    run_meta["finished_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    write_run_file(out_dir / f"{batchname}.json", run_meta, results)
    logger.info("Run complete: %d records -> %s", len(results), out_dir / f"{batchname}.json")
    print(f"Done: {len(results)} records -> {out_dir / (batchname + '.json')}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
