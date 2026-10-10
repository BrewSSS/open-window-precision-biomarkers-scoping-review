#!/usr/bin/env python3
"""Read-only and mock checks for the formal extraction resume safeguards."""
from __future__ import annotations

import copy
import csv
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_resume_2026_10_10 as runner


class ResumeIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = runner.schema()
        cls.valid_ids = [entry["record_id"] for entry in runner.manifest()["entries"] if entry.get("valid")]

    def test_existing_valid_outputs_remain_valid_and_unselected(self):
        self.assertGreater(len(self.valid_ids), 0)
        for ref in self.valid_ids:
            self.assertTrue(runner.valid_output(runner.load_run(ref), self.spec, ref), ref)
        args = type("Args", (), {"ids_file": None, "resume": True, "limit": 0})()
        pending, missing = runner.selected_refs(args, self.spec)
        self.assertTrue(set(self.valid_ids).isdisjoint(pending + missing))

    def test_bad_identity_is_rejected_even_when_json_shape_is_valid(self):
        ref = self.valid_ids[0]
        original = runner.load_run(ref)
        altered = copy.deepcopy(original)
        altered["parsed"]["reference_id"] = "FS-999999"
        self.assertFalse(runner.valid_output(altered, self.spec, ref))
        altered = copy.deepcopy(original)
        altered["parsed"]["tables"]["sample_sets"][0]["report_id"] = "PILOT-FS-999999"
        self.assertFalse(runner.valid_output(altered, self.spec, ref))
        altered = copy.deepcopy(original)
        altered["record_id"] = "FS-999999"
        self.assertFalse(runner.valid_output(altered, self.spec, ref))
        altered = copy.deepcopy(original)
        del altered["parsed"]["tables"]["reports"][0]["report_id"]
        self.assertFalse(runner.valid_output(altered, self.spec, ref))

    def test_every_mock_attempt_is_logged_even_when_invalid(self):
        ref = self.valid_ids[0]
        parsed = runner.load_run(ref)["parsed"]
        wrong = copy.deepcopy(parsed)
        wrong["reference_id"] = "FS-999999"
        responses = [{"parsed": wrong, "usage": {"input_tokens": 10, "output_tokens": 5}},
                     {"parsed": parsed, "usage": {"input_tokens": 12, "output_tokens": 6}}]
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "ledger.csv"
            with patch.object(runner, "LEDGER", ledger), \
                 patch.object(runner.ER, "call_sol", side_effect=responses):
                first = runner.attempt(ref, "", self.spec, runner.SCHEMA, Path(tmp))
                second = runner.attempt(ref, "", self.spec, runner.SCHEMA, Path(tmp))
            with ledger.open(encoding="utf-8") as handle:
                records = list(csv.DictReader(handle))
        self.assertFalse(first["valid"])
        self.assertTrue(second["valid"])
        self.assertEqual([row["valid"] for row in records], ["False", "True"])
        self.assertEqual(runner.token_totals(records), (33, 0))

    def test_existing_valid_output_short_circuits_model_call(self):
        ref = self.valid_ids[0]
        existing = runner.load_run(ref)
        with patch.object(runner, "load_run", return_value=existing), \
             patch.object(runner.ER, "call_sol", side_effect=AssertionError("model call attempted")):
            returned = runner.run_one(ref, {}, {}, "", "", self.spec, Path("/tmp"), "", "")
        self.assertIs(returned, existing)

    def test_repair_retries_failed_tables_and_never_drops_existing_ids(self):
        ref = "FS-000001"
        parsed = {"report_id": "PILOT-" + ref,
                  "tables": {"study_families": [{"study_id": "S-1"}],
                             "cohorts": [{"cohort_id": "C-1"}],
                             "sample_sets": [{"sample_set_id": "SS-1"}],
                             "measurements": []}}
        old = [{"measurement_id": "M-FS-000001-001", "report_id": "PILOT-" + ref,
                "study_id": "S-1", "cohort_id": "C-1", "sample_set_ids": ["SS-1"]}]
        new = [{**old[0], "measurement_id": "M-FS-000001-002"}]
        self.assertFalse(runner.replacement_rows_ok(ref, "measurements", old, new, parsed))
        self.assertTrue(runner.replacement_rows_ok(ref, "measurements", old, old + new, parsed))
        self.assertEqual(runner.repair_flags(ref, {"tables": {"measurements": []},
                                                    "unresolved_questions": ["incomplete extraction"]}, ""),
                         ["measurements", "precision_validation"])

    def test_repair_prompt_shows_target_ids_and_rejection_preserves_extraction(self):
        ref = self.valid_ids[0]
        original = runner.load_run(ref)
        old = original["parsed"]["tables"]["measurements"]
        self.assertGreater(len(old), 1)
        prompt = runner.repair_prompt("SYSTEM", "measurements", original["parsed"], "SOURCE")
        self.assertIn(old[0]["measurement_id"], prompt)
        self.assertIn("Existing target table for ID and value reconciliation", prompt)
        self.assertNotIn('"_locators"', prompt)
        self.assertEqual(original["parsed"]["tables"]["measurements"], old)

        output = copy.deepcopy(original)
        before = copy.deepcopy(output["parsed"])
        reason = runner.apply_repair_response(
            ref, "measurements", output,
            {"valid": True, "parsed": {"measurements": old[1:]}}, self.spec)
        self.assertIn("missing_existing_ids", reason)
        self.assertEqual(output["parsed"], before)
        self.assertTrue(output["valid"])
        self.assertFalse(output["_per_table_mode"]["measurements"])
        self.assertEqual(output["_per_table_rejections"]["measurements"], reason)

        new_row = copy.deepcopy(old[0])
        highest = max(int(row["measurement_id"].rsplit("-", 1)[1]) for row in old)
        new_row["measurement_id"] = f"M-{ref}-{highest + 1:03d}"
        reason = runner.apply_repair_response(
            ref, "measurements", output,
            {"valid": True, "parsed": {"measurements": old + [new_row]}}, self.spec)
        self.assertIsNone(reason)
        self.assertEqual(len(output["parsed"]["tables"]["measurements"]), len(old) + 1)
        self.assertTrue(output["_per_table_mode"]["measurements"])
        self.assertNotIn("measurements", output["_per_table_rejections"])

    def test_unknown_token_counts_are_not_zero(self):
        self.assertEqual(runner.token_totals([{"input_tokens": "10", "output_tokens": "5"},
                                              {"input_tokens": "", "output_tokens": ""}]), (15, 1))

    def test_extended_timeout_only_for_prior_timeout(self):
        ref = "FS-000001"
        info = {"bibliographic": {"title": "NR", "year": "NR", "doi": "NR", "pmid": "NR"}}
        response = {"parsed": None, "valid": False, "error": "timeout", "usage": None}
        for prior_error, expected in (("timeout after 1200.0s", 1800), ("schema invalid", 1200)):
            with self.subTest(prior_error=prior_error), \
                 patch.object(runner, "load_run", return_value={"valid": False, "error": prior_error}), \
                 patch.object(runner, "attempt", return_value=response) as call, \
                 patch.object(runner, "atomic_json"), patch.object(runner, "update_manifest"):
                runner.run_one(ref, {"record_id": ref}, info, "", "", self.spec,
                               Path("/tmp"), "", "", 1800)
                self.assertEqual(call.call_args.kwargs["timeout"], expected)

    def test_historical_truncation_adds_table_repair_without_changing_other_flags(self):
        parsed = {"tables": {"measurements": [{}] * 6, "precision_validation": [{}] * 7},
                  "unresolved_questions": []}
        self.assertEqual(runner.repair_flags("FS-000001", parsed, ""), [])
        self.assertEqual(runner.repair_flags("FS-000001", parsed, "", historical_truncated=True),
                         ["measurements", "precision_validation"])

    def test_candidate_cap_marker_triggers_formal_table_repair(self):
        parsed = {"tables": {"measurements": [{"measurement_notes": "MORE_CANDIDATES_THAN_EXTRACTED; remainder summarized"}],
                             "precision_validation": [{}] * 7},
                  "unresolved_questions": []}
        self.assertEqual(runner.repair_flags("FS-000001", parsed, ""),
                         ["measurements", "precision_validation"])
        self.assertEqual(runner.repair_flags("FS-000001", parsed, "", include_candidate_cap=False), [])

    def test_main_default_covers_current_texts(self):
        lengths = [len(path.read_text(encoding="utf-8", errors="replace"))
                   for path in (runner.FT / "V_text").glob("FS-*.txt")]
        self.assertTrue(lengths)
        self.assertLess(max(lengths), 500000)
        args = type("Args", (), {"ids_file": None, "resume": True, "limit": 0})()
        pending, missing = runner.selected_refs(args, self.spec)
        self.assertFalse(missing)
        rows, info = runner.source_rows(pending, 500000)
        self.assertEqual(len(rows), len(pending))
        self.assertFalse(any(row["truncated"] for row in info.values()))

    def test_audit_metrics_use_actual_note_rule_and_both_time_schemas(self):
        path = runner.ROOT / "06_synthesis/prototype_2026-10-09/build_prototype.py"
        spec = importlib.util.spec_from_file_location("audit_test_prototype", path)
        prototype = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(prototype)
        common = {"precision_domain": "independent_validation_and_use", "evidence_state": "evidence_present",
                  "evidence_notes": "No independent validation was reported.", "validation_split": "none"}
        older = {"tables": {"precision_validation": [common],
                            "sample_sets": [{"time_bin": "30min_to_lt3h",
                                             "time_from_exercise_end_value": "2", "time_unit": "h"}],
                            "measurements": [{"analyte_id": {"original_label": "IL-6",
                                                                 "standard_name": "interleukin-6"}}]}}
        revised = {"tables": {"precision_validation": [common],
                              "sample_sets": [{"time_bin": "30min_to_lt3h", "time_value_min": 120}],
                              "measurements": [{"analyte_id": {"analyte_raw": "IL-6",
                                                                   "analyte_canonical": "IL-6"}}]}}
        old_metrics = runner.audit_quality([older], "v1", prototype)
        new_metrics = runner.audit_quality([revised], "v1_1", prototype)
        for metrics in (old_metrics, new_metrics):
            self.assertEqual(metrics["evidence_present_negative_notes"], 1)
            self.assertEqual(metrics["independent_validation_without_independent_split"], 1)
            self.assertEqual(metrics["numeric_post_time_rows"], 1)
            self.assertEqual(metrics["post_sample_sets"], 1)
            self.assertEqual(metrics["analyte_raw_distinct"], 1)
            self.assertEqual(metrics["analyte_canonical_distinct"], 1)
        self.assertIsNone(old_metrics["other_text_usage"])
        self.assertIn("cohorts.training_status_other_text", new_metrics["other_text_usage"])


if __name__ == "__main__":
    unittest.main()
