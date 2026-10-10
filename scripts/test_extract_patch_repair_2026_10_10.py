#!/usr/bin/env python3
"""Focused, model-free checks for incremental extraction patch safety."""
from __future__ import annotations

import copy
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import extract_patch_repair_2026_10_10 as P


class PatchSafety(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ref = "FS-000460"
        cls.baseline = P.X.load_run(cls.ref)
        cls.spec = P.load_schema()
        cls.source = P.source_text(cls.ref)
        cls.page = re.search(r"\[\[page\s+(\d+)\]\]", cls.source).group(1)
        first_page = P.page_text(cls.source, cls.page)
        cls.quote = next(q for line in first_page.splitlines()
                         if len(line.split()) >= 5 and "[" not in line
                         for q in [" ".join(line.split())[:50]]
                         if P.X.scrub_context_value(q) == q)
        assert P.evidence_valid(cls.source, cls.page, cls.quote)

    def patch(self, table, add_rows=None, updates=None):
        return {"record_id": self.ref, "table": table,
                "coverage": {"source_review": "partial", "completion": "partial", "pages_reviewed": [self.page],
                             "remaining_missing": ["mock test does not check every page"],
                             "coverage_basis": "source page checked"},
                "add_rows": add_rows or [], "updates": updates or []}

    def update(self, table, field, row_id, value):
        return {"row_id": row_id, "field": field, "value_text": value,
                "value_integer": None, "value_text_list": None, "set_null": False,
                "page": self.page, "quote": self.quote, "reason": "mock source check"}

    def test_sparse_update_preserves_other_rows(self):
        original = copy.deepcopy(self.baseline["parsed"])
        first = original["tables"]["measurements"][0]
        new = first["measurement_notes"] + " [mock verified]"
        patch = self.patch("measurements", updates=[self.update("measurements", "measurement_notes", first["measurement_id"], new)])
        candidate, errors = P.apply_patches(original, {"measurements": patch}, self.source, self.spec)
        self.assertEqual(errors, [])
        self.assertEqual(candidate["tables"]["measurements"][0]["measurement_notes"], new)
        self.assertEqual(original, self.baseline["parsed"])
        self.assertEqual(candidate["tables"]["precision_validation"], original["tables"]["precision_validation"])

    def test_duplicate_id_rejected(self):
        original = self.baseline["parsed"]
        row = copy.deepcopy(original["tables"]["measurements"][0])
        row["_locators"] = [{"field": "measurement_notes", "page": self.page, "quote": self.quote}]
        candidate, errors = P.apply_patches(original, {"measurements": self.patch("measurements", add_rows=[row])}, self.source, self.spec)
        self.assertIsNone(candidate)
        self.assertTrue(any("duplicate row ID" in e for e in errors))

    def test_new_row_with_exact_duplicate_scientific_values_rejected(self):
        original = self.baseline["parsed"]
        row = copy.deepcopy(original["tables"]["measurements"][0])
        m_max = max(int(r["measurement_id"].rsplit("-", 1)[1])
                    for r in original["tables"]["measurements"])
        row["measurement_id"] = f"M-{self.ref}-{m_max+1:03d}"
        row["_locators"] = [{"field": "measurement_notes", "page": self.page, "quote": self.quote}]
        candidate, errors = P.apply_patches(original,
                                            {"measurements": self.patch("measurements", add_rows=[row])},
                                            self.source, self.spec)
        self.assertIsNone(candidate)
        self.assertTrue(any("exact duplicate scientific values" in error for error in errors))

    def test_illegal_field_rejected(self):
        row = self.baseline["parsed"]["tables"]["measurements"][0]
        update = self.update("measurements", "report_id", row["measurement_id"], "wrong")
        candidate, errors = P.apply_patches(self.baseline["parsed"], {"measurements": self.patch("measurements", updates=[update])}, self.source, self.spec)
        self.assertIsNone(candidate)
        self.assertTrue(errors)

    def test_invalid_fk_rejected(self):
        original = self.baseline["parsed"]
        row = copy.deepcopy(original["tables"]["measurements"][0])
        nums = [int(m.group(1)) for x in original["tables"]["measurements"]
                if (m := re.search(r"-(\d{3})$", x["measurement_id"]))]
        row["measurement_id"] = f"M-{self.ref}-{max(nums)+1:03d}"
        row["cohort_id"] = "C-UNKNOWN-99"
        row["_locators"] = [{"field": "measurement_notes", "page": self.page, "quote": self.quote}]
        candidate, errors = P.apply_patches(original, {"measurements": self.patch("measurements", add_rows=[row])}, self.source, self.spec)
        self.assertIsNone(candidate)
        self.assertTrue(any("unknown cohort_id" in e for e in errors))

    def test_optional_literal_null_is_not_an_unknown_measurement(self):
        for value in ("null", "NA", "NR", "UNCLEAR", ""):
            candidate = copy.deepcopy(self.baseline["parsed"])
            candidate["tables"]["precision_validation"][0]["measurement_id"] = value
            with self.subTest(value=value):
                self.assertEqual(P.check_record_links(candidate, self.ref), [])
                self.assertEqual(candidate["tables"]["precision_validation"][0]["measurement_id"], value)
        for value in ("M-FS-999999-999", "NULL"):
            candidate = copy.deepcopy(self.baseline["parsed"])
            candidate["tables"]["precision_validation"][0]["measurement_id"] = value
            with self.subTest(value=value):
                self.assertTrue(any("unknown measurement_id" in e
                                    for e in P.check_record_links(candidate, self.ref)))

    def test_wrong_page_quote_rejected(self):
        original = self.baseline["parsed"]
        row = original["tables"]["measurements"][0]
        update = self.update("measurements", "measurement_notes", row["measurement_id"], "mock")
        update["page"] = "999999"
        candidate, errors = P.apply_patches(original, {"measurements": self.patch("measurements", updates=[update])}, self.source, self.spec)
        self.assertIsNone(candidate)
        self.assertTrue(any("quote/page not found" in e for e in errors))

    def test_precision_link_can_use_new_measurement_from_first_patch(self):
        original = self.baseline["parsed"]
        measurement = copy.deepcopy(original["tables"]["measurements"][0])
        m_max = max(int(r["measurement_id"].rsplit("-", 1)[1]) for r in original["tables"]["measurements"])
        measurement["measurement_id"] = f"M-{self.ref}-{m_max+1:03d}"
        measurement["measurement_notes"] += " [distinct mock measurement]"
        measurement["_locators"] = [{"field": "measurement_notes", "page": self.page, "quote": self.quote}]
        precision = copy.deepcopy(original["tables"]["precision_validation"][0])
        p_max = max(int(r["precision_record_id"].rsplit("-", 1)[1])
                    for r in original["tables"]["precision_validation"])
        precision["precision_record_id"] = f"PV-{self.ref}-{p_max+1:03d}"
        precision["measurement_id"] = measurement["measurement_id"]
        precision["_locators"] = [{"field": "evidence_notes", "page": self.page, "quote": self.quote}]
        patches = {"measurements": self.patch("measurements", add_rows=[measurement]),
                   "precision_validation": self.patch("precision_validation", add_rows=[precision])}
        candidate, errors = P.apply_patches(original, patches, self.source, self.spec)
        self.assertEqual(errors, [])
        self.assertEqual(candidate["tables"]["precision_validation"][-1]["measurement_id"],
                         measurement["measurement_id"])
        alone, errors = P.apply_patches(original, {"precision_validation": patches["precision_validation"]},
                                       self.source, self.spec)
        self.assertIsNone(alone)
        self.assertTrue(any("unknown measurement_id" in error for error in errors))

    def test_noop_update_is_ignored(self):
        original = self.baseline["parsed"]
        first = original["tables"]["measurements"][0]
        update = self.update("measurements", "measurement_notes", first["measurement_id"],
                             first["measurement_notes"])
        candidate, errors = P.apply_patches(original,
                                            {"measurements": self.patch("measurements", updates=[update])},
                                            self.source, self.spec)
        self.assertEqual(errors, [])
        self.assertEqual(candidate, original)

    def test_ellipsis_quote_rejected(self):
        self.assertFalse(P.evidence_valid(self.source, self.page, self.quote + " ..."))

    def test_strict_schema_has_no_unsupported_keywords(self):
        for table in P.TABLES:
            schema = P.strict_patch_schema(table, self.spec)
            text = json.dumps(schema)
            for keyword in ("$ref", "$defs", "maxLength", "uniqueItems"):
                self.assertNotIn(keyword, text)
            P.T.jsonschema.Draft202012Validator.check_schema(schema)

    def test_call_schema_binds_source_reference_id(self):
        with tempfile.TemporaryDirectory() as directory:
            path = P.call_schema_file(self.ref, "measurements", self.spec, Path(directory))
            schema = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(schema["properties"]["record_id"]["enum"], [self.ref])
            self.assertEqual(schema["properties"]["table"]["enum"], ["measurements"])
            good = self.patch("measurements")
            wrong_report_id = copy.deepcopy(good)
            wrong_report_id["record_id"] = f"PILOT-{self.ref}"
            self.assertEqual(P.T.validate_against_schema(good, schema), [])
            self.assertTrue(P.T.validate_against_schema(wrong_report_id, schema))
            self.assertNotEqual(P.digest(path), P.digest(P.schema_path("measurements")))

    def test_privacy_cleanup_preserves_scientific_row_ids(self):
        candidate = copy.deepcopy(self.baseline["parsed"])
        old_ids = {table: [row[P.PK[table]] for row in candidate["tables"][table]] for table in P.TABLES}
        counts = P.privacy_cleanup(candidate, self.ref, self.spec)
        self.assertGreaterEqual(counts["authors_withheld"], 0)
        self.assertTrue(all(row["authors"] == "WITHHELD" for row in candidate["tables"]["reports"]))
        self.assertTrue(all(row["digitization_software_version"] == "NR"
                            for row in candidate["tables"]["measurements"]))
        self.assertEqual(old_ids, {table: [row[P.PK[table]] for row in candidate["tables"][table]]
                                   for table in P.TABLES})

    def test_fully_checked_empty_patch_is_valid_without_claiming_new_rows(self):
        pages = sorted({m.group(1) for m in P.PAGE.finditer(self.source)})
        patches = {table: self.patch(table) for table in P.TABLES}
        for patch in patches.values():
            patch["coverage"]["source_review"] = "fully_checked"
            patch["coverage"]["pages_reviewed"] = pages
        candidate, errors = P.apply_patches(self.baseline["parsed"], patches, self.source, self.spec)
        self.assertEqual(errors, [])
        self.assertEqual(candidate, self.baseline["parsed"])
        # A source review can be complete while reportable gaps remain unresolved.
        self.assertEqual(patches["measurements"]["coverage"]["remaining_missing"],
                         ["mock test does not check every page"])

    def test_partial_completion_requires_explicit_remaining_gap(self):
        patch_doc = self.patch("measurements")
        patch_doc["coverage"]["remaining_missing"] = []
        candidate, errors = P.apply_patches(self.baseline["parsed"],
                                            {"measurements": patch_doc}, self.source, self.spec)
        self.assertIsNone(candidate)
        self.assertTrue(any("remaining_missing" in error for error in errors))

    def test_isolation_keeps_supported_operations_and_original_rows(self):
        original = copy.deepcopy(self.baseline["parsed"])
        rows = original["tables"]["measurements"]
        m_max = max(int(row["measurement_id"].rsplit("-", 1)[1]) for row in rows)
        added = []
        for number, suffix, quote in ((1, "supported", self.quote),
                                      (2, "unsupported", "quote absent from source 987654321")):
            row = copy.deepcopy(rows[0])
            row["measurement_id"] = f"M-{self.ref}-{m_max+number:03d}"
            row["measurement_notes"] += f" [{suffix} mock]"
            row["_locators"] = [{"field": "measurement_notes", "page": self.page, "quote": quote}]
            added.append(row)
        added[1]["_locators"].append({"field": "measurement_notes", "page": self.page,
                                     "quote": self.quote})
        updates = [self.update("measurements", "measurement_notes", rows[0]["measurement_id"],
                               rows[0]["measurement_notes"] + " [supported update mock]")]
        bad_update = self.update("measurements", "measurement_notes", rows[1]["measurement_id"],
                                 rows[1]["measurement_notes"] + " [unsupported mock]")
        bad_update["quote"] = "quote absent from source 987654321"
        updates.append(bad_update)
        raw = self.patch("measurements", add_rows=added, updates=updates)
        unchanged_raw = copy.deepcopy(raw)
        filtered, isolated, errors = P.isolate_evidence_operations(
            original, raw, "measurements", self.source, self.spec)
        self.assertEqual(errors, [])
        self.assertEqual(len(isolated), 2)
        self.assertEqual({x["reason"] for x in isolated},
                         {"unsupported_update_quote_page", "unsupported_new_row_locator"})
        self.assertEqual(next(x for x in isolated if x["reason"] == "unsupported_new_row_locator")["field"],
                         "measurement_notes")
        self.assertEqual(len(filtered["updates"]), 1)
        self.assertEqual(len(filtered["add_rows"]), 1)
        self.assertEqual(filtered["coverage"]["source_review"], "partial")
        self.assertEqual(filtered["coverage"]["completion"], "partial")
        self.assertEqual(len(filtered["coverage"]["remaining_missing"]), 3)
        candidate, errors = P.apply_patches(original, {"measurements": filtered}, self.source, self.spec)
        self.assertEqual(errors, [])
        self.assertEqual([r["measurement_id"] for r in candidate["tables"]["measurements"][:len(rows)]],
                         [r["measurement_id"] for r in rows])
        self.assertEqual(original, self.baseline["parsed"])
        self.assertEqual(raw, unchanged_raw)

    def test_all_unsupported_evidence_can_be_isolated_without_new_values(self):
        original = self.baseline["parsed"]
        row = original["tables"]["measurements"][0]
        update = self.update("measurements", "measurement_notes", row["measurement_id"], "mock")
        update["quote"] = "quote absent from source 987654321"
        filtered, isolated, errors = P.isolate_evidence_operations(
            original, self.patch("measurements", updates=[update]),
            "measurements", self.source, self.spec)
        self.assertEqual(errors, [])
        self.assertEqual(filtered["updates"], [])
        self.assertEqual(len(isolated), 1)
        candidate, errors = P.apply_patches(original, {"measurements": filtered}, self.source, self.spec)
        self.assertEqual(errors, [])
        self.assertEqual(candidate, original)

    def test_structural_errors_are_not_hidden_by_bad_evidence(self):
        original = self.baseline["parsed"]
        row = original["tables"]["measurements"][0]
        invalid_update = self.update("measurements", "report_id", row["measurement_id"], "bad")
        invalid_update["quote"] = "quote absent from source 987654321"
        bad_fk = copy.deepcopy(row)
        m_max = max(int(r["measurement_id"].rsplit("-", 1)[1])
                    for r in original["tables"]["measurements"])
        bad_fk["measurement_id"] = f"M-{self.ref}-{m_max+1:03d}"
        bad_fk["cohort_id"] = "C-UNKNOWN-99"
        bad_fk["_locators"] = [{"field": "measurement_notes", "page": self.page,
                                "quote": "quote absent from source 987654321"}]
        duplicate_id = copy.deepcopy(bad_fk)
        duplicate_id["measurement_id"] = row["measurement_id"]
        duplicate_id["cohort_id"] = row["cohort_id"]
        wrong_type = self.update("measurements", "measurement_notes", row["measurement_id"], "mock")
        wrong_type["value_text"] = None
        wrong_type["value_integer"] = 7
        wrong_type["quote"] = "quote absent from source 987654321"
        for raw in (self.patch("measurements", updates=[invalid_update]),
                    self.patch("measurements", add_rows=[bad_fk]),
                    self.patch("measurements", add_rows=[duplicate_id]),
                    self.patch("measurements", updates=[wrong_type])):
            filtered, isolated, errors = P.isolate_evidence_operations(
                original, raw, "measurements", self.source, self.spec)
            self.assertIsNone(filtered)
            self.assertEqual(isolated, [])
            self.assertTrue(errors)

    def test_precision_dependency_isolated_only_for_rejected_measurement(self):
        original = self.baseline["parsed"]
        measurement = copy.deepcopy(original["tables"]["measurements"][0])
        m_max = max(int(row["measurement_id"].rsplit("-", 1)[1])
                    for row in original["tables"]["measurements"])
        measurement["measurement_id"] = f"M-{self.ref}-{m_max+1:03d}"
        measurement["measurement_notes"] += " [distinct mock row]"
        measurement["_locators"] = [{"field": "measurement_notes", "page": self.page,
                                     "quote": "quote absent from source 987654321"}]
        filtered_m, isolated_m, errors = P.isolate_evidence_operations(
            original, self.patch("measurements", add_rows=[measurement]),
            "measurements", self.source, self.spec)
        self.assertEqual(errors, [])
        self.assertEqual(len(isolated_m), 1)
        precision = copy.deepcopy(original["tables"]["precision_validation"][0])
        p_max = max(int(row["precision_record_id"].rsplit("-", 1)[1])
                    for row in original["tables"]["precision_validation"])
        precision["precision_record_id"] = f"PV-{self.ref}-{p_max+1:03d}"
        precision["measurement_id"] = measurement["measurement_id"]
        precision["_locators"] = [{"field": "evidence_notes", "page": self.page, "quote": self.quote}]
        filtered_p, isolated_p, errors = P.isolate_evidence_operations(
            original, self.patch("precision_validation", add_rows=[precision]),
            "precision_validation", self.source, self.spec, [measurement])
        self.assertEqual(errors, [])
        self.assertEqual(filtered_p["add_rows"], [])
        self.assertEqual(isolated_p[0]["reason"], "depends_on_isolated_measurement")
        unrelated = copy.deepcopy(precision)
        unrelated["measurement_id"] = "M-UNKNOWN-999"
        rejected, isolated, errors = P.isolate_evidence_operations(
            original, self.patch("precision_validation", add_rows=[unrelated]),
            "precision_validation", self.source, self.spec, [measurement])
        self.assertIsNone(rejected)
        self.assertEqual(isolated, [])
        self.assertTrue(any("unknown measurement_id" in error for error in errors))

    def test_rejected_attempt_updates_manifest_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runs = root / "runs"
            runs.mkdir()
            raw = runs / f"{self.ref}.json"
            run = {"record_id": self.ref, "valid": True,
                   "parsed": {"reference_id": self.ref, "tables": {}}}
            raw.write_text(json.dumps(run), encoding="utf-8")
            before = raw.read_bytes()
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"entries": [{"record_id": self.ref}]}), encoding="utf-8")
            with patch.object(P.X, "RUNS", runs), patch.object(P.X, "MANIFEST", manifest), \
                 patch.object(P.X, "MANIFEST_LOCK_PATH", root / "manifest.lock"):
                P.record_attempt(self.ref, P.parsed_sha(run["parsed"]), "measurements",
                                 "patch_rejected", None, "mock invalid evidence")
            self.assertEqual(raw.read_bytes(), before)
            entries = json.loads(manifest.read_text())["entries"]
            self.assertEqual(entries[0]["patch_repair_attempts"][0]["state"], "patch_rejected")

    def test_cached_first_table_patch_is_reusable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = "base-sha"
            context = "context-sha"
            prompt_sha = "prompt-sha"
            schema_sha = "schema-sha"
            table = "measurements"
            patch_doc = self.patch(table)
            (root / f"{self.ref}_{table}_patch.json").write_text(json.dumps(patch_doc))
            (root / f"{self.ref}_{table}_call.json").write_text(json.dumps(
                {"valid": True, "base_parsed_sha256": base, "context_sha256": context,
                 "prompt_sha256": prompt_sha, "patch_schema_sha256": schema_sha}))
            with patch.object(P, "PATCH_DIR", root):
                loaded, _ = P.cached_patch(self.ref, table, base, context, prompt_sha, schema_sha)
                stale, _ = P.cached_patch(self.ref, table, base, "changed-context", prompt_sha, schema_sha)
                stale_prompt, _ = P.cached_patch(self.ref, table, base, context, "changed-prompt", schema_sha)
                stale_schema, _ = P.cached_patch(self.ref, table, base, context, prompt_sha, "changed-schema")
            self.assertEqual(loaded, patch_doc)
            self.assertIsNone(stale)
            self.assertIsNone(stale_prompt)
            self.assertIsNone(stale_schema)

    def test_mock_model_runs_full_prompt_apply_commit_chain(self):
        """Only the paid model boundary is mocked; all patch orchestration is real."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runs = root / "runs"
            runs.mkdir()
            patch_dir = root / "patches"
            patch_dir.mkdir()
            run = copy.deepcopy(self.baseline)
            P.X.withhold_output_details(run["parsed"])
            run_path = runs / f"{self.ref}.json"
            run_path.write_text(json.dumps(run), encoding="utf-8")
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"entries": [{"record_id": self.ref}]}), encoding="utf-8")
            pages = sorted({m.group(1) for m in P.PAGE.finditer(self.source)})
            model_calls = []
            added_measurement = copy.deepcopy(run["parsed"]["tables"]["measurements"][0])
            m_max = max(int(row["measurement_id"].rsplit("-", 1)[1])
                        for row in run["parsed"]["tables"]["measurements"])
            added_measurement["measurement_id"] = f"M-{self.ref}-{m_max+1:03d}"
            added_measurement["measurement_notes"] += " [distinct mock row]"
            added_measurement["_locators"] = [{"field": "measurement_notes", "page": self.page,
                                               "quote": self.quote}]

            def fake_call_sol(call_ref, prompt_text, model, effort, timeout, temp, schema):
                table = next(t for t in P.TABLES if call_ref.endswith(f"_{t}_patch"))
                model_calls.append(table)
                self.assertIn("FULL PAGE-MARKED SOURCE:", prompt_text)
                self.assertIn("bare digit strings", prompt_text)
                self.assertIn("at most 25 words", prompt_text)
                self.assertIn("pages_reviewed lists every [[page N]] page", prompt_text)
                self.assertIn("EXISTING ID AND ROW CONTEXT", prompt_text)
                self.assertIn(f"record_id exactly to the source reference_id '{self.ref}'", prompt_text)
                call_schema = json.loads(schema.read_text(encoding="utf-8"))
                self.assertEqual(call_schema["properties"]["record_id"]["enum"], [self.ref])
                self.assertEqual(call_schema["properties"]["table"]["enum"], [table])
                if table == "precision_validation":
                    self.assertIn(added_measurement["measurement_id"], prompt_text)
                return {"parsed": {"record_id": self.ref, "table": table,
                        "coverage": {"source_review": "fully_checked", "completion": "partial",
                                     "pages_reviewed": pages, "remaining_missing": ["mock unresolved gap"],
                                     "coverage_basis": "mock complete page review"},
                        "add_rows": [added_measurement] if table == "measurements" else [],
                        "updates": []},
                        "usage": {"input_tokens": 1, "output_tokens": 1,
                                  "cached_input_tokens": 0, "reasoning_output_tokens": 0},
                        "t_completed_s": 1}

            with patch.object(P.X, "RUNS", runs), patch.object(P.X, "MANIFEST", manifest), \
                 patch.object(P.X, "LEDGER", root / "ledger.csv"), \
                 patch.object(P.X, "LEDGER_LOCK_PATH", root / "ledger.lock"), \
                 patch.object(P.X, "MANIFEST_LOCK_PATH", root / "manifest.lock"), \
                 patch.object(P, "PATCH_DIR", patch_dir), patch.object(P.ER, "call_sol", fake_call_sol):
                P.QUOTA_STOP.clear()
                result = P.run_record(self.ref, self.spec, root)
                P.QUOTA_STOP.clear()

            self.assertEqual(model_calls, list(P.TABLES), result)
            self.assertTrue(result["valid"])
            self.assertEqual(result["repair_status"], "changes_applied")
            saved = json.loads(run_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["parsed"]["tables"]["measurements"][:-1],
                             run["parsed"]["tables"]["measurements"])
            self.assertEqual(saved["parsed"]["tables"]["measurements"][-1]["measurement_id"],
                             added_measurement["measurement_id"])
            self.assertEqual(len(saved["_patch_repair_attempts"]), 2)
            self.assertEqual(len(json.loads(manifest.read_text())["entries"][0]["patch_repair_attempts"]), 2)
            self.assertEqual(len((root / "ledger.csv").read_text().splitlines()), 3)
            self.assertTrue((patch_dir / f"{self.ref}_measurements_patch.json").exists())
            self.assertTrue((patch_dir / f"{self.ref}_precision_validation_patch.json").exists())

    def test_cached_evidence_rejected_measurement_is_filtered_without_recall(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runs = root / "runs"
            runs.mkdir()
            patches = root / "patches"
            patches.mkdir()
            run = copy.deepcopy(self.baseline)
            P.X.withhold_output_details(run["parsed"])
            run_path = runs / f"{self.ref}.json"
            run_path.write_text(json.dumps(run), encoding="utf-8")
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"entries": [{"record_id": self.ref}]}), encoding="utf-8")
            baseline_sha = P.parsed_sha(run["parsed"])
            call_schema = P.call_schema_file(self.ref, "measurements", self.spec, root)
            update = self.update("measurements", "measurement_notes",
                                 run["parsed"]["tables"]["measurements"][0]["measurement_id"], "mock")
            update["quote"] = "quote absent from source 987654321"
            raw_patch = self.patch("measurements", updates=[update])
            (patches / f"{self.ref}_measurements_patch.json").write_text(json.dumps(raw_patch))
            meta = {"valid": True, "base_parsed_sha256": baseline_sha,
                    "context_sha256": baseline_sha,
                    "prompt_sha256": __import__("hashlib").sha256(
                        P.prompt_for(self.ref, "measurements", run["parsed"], self.source).encode()).hexdigest(),
                    "patch_schema_sha256": P.digest(call_schema), "table": "measurements"}
            (patches / f"{self.ref}_measurements_call.json").write_text(json.dumps(meta))
            calls = []

            def fake_call_sol(call_ref, prompt_text, model, effort, timeout, temp, schema):
                calls.append(call_ref)
                self.assertTrue(call_ref.endswith("_precision_validation_patch"))
                return {"parsed": self.patch("precision_validation"),
                        "usage": {"input_tokens": 1, "output_tokens": 1}, "t_completed_s": 1}

            with patch.object(P.X, "RUNS", runs), patch.object(P.X, "MANIFEST", manifest), \
                 patch.object(P.X, "LEDGER", root / "ledger.csv"), \
                 patch.object(P.X, "LEDGER_LOCK_PATH", root / "ledger.lock"), \
                 patch.object(P.X, "MANIFEST_LOCK_PATH", root / "manifest.lock"), \
                 patch.object(P, "PATCH_DIR", patches), patch.object(P.ER, "call_sol", fake_call_sol):
                P.QUOTA_STOP.clear()
                result = P.run_record(self.ref, self.spec, root)
                P.QUOTA_STOP.clear()

            self.assertEqual(len(calls), 1)
            self.assertTrue(result["valid"], result)
            self.assertEqual(result["repair_status"], "partial_accepted")
            self.assertEqual(result["isolated_operations"][0]["reason"], "unsupported_update_quote_page")
            saved = json.loads(run_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["parsed"]["tables"]["measurements"],
                             run["parsed"]["tables"]["measurements"])
            self.assertTrue(saved["_patch_repair"]["partial_accepted"])
            self.assertTrue(json.loads(manifest.read_text())["entries"][0]["patch_repair"]["partial_accepted"])

    def test_quota_stop_prevents_new_dispatch(self):
        called = []
        def fake_worker(ref, spec, temp):
            called.append(ref)
            P.QUOTA_STOP.set()
            return {"record_id": ref, "valid": False, "repair_status": "quota"}
        with tempfile.TemporaryDirectory() as directory, patch.object(P, "run_record", fake_worker), \
             patch.object(P, "STATUS", Path(directory) / "status.md"):
            P.QUOTA_STOP.clear()
            P.run_selected([(f"FS-{n:06d}", list(P.TABLES)) for n in range(1, 6)], self.spec, 2)
            P.QUOTA_STOP.clear()
        self.assertLessEqual(len(called), 2)


if __name__ == "__main__":
    unittest.main()
