"""Property, boundary, and CLI tests for feature-skew-attribution-lab."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from feature_skew_attribution_lab.attributor import ParityRow, attribute_skew, load_parity_rows
from feature_skew_attribution_lab.cli import main as cli_main, render_table
from feature_skew_attribution_lab.config import SkewPolicy, load_policy

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "fixtures" / "feature_parity_rows.jsonl"
POL = ROOT / "policy" / "skew_policy.json"


class TestSkewAttributorProperties(unittest.TestCase):
    def test_policies_validate_and_reject_invalid_values(self) -> None:
        SkewPolicy().validate()
        self.assertAlmostEqual(load_policy(POL).abs_tolerance, 0.01)
        self.assertEqual(load_policy(None).max_allowed_skewed_rows, 0)
        with self.assertRaises(FileNotFoundError):
            load_policy(Path("/tmp/missing_skpol_999.json"))
        with self.assertRaises(ValueError):
            SkewPolicy(abs_tolerance=-0.1).validate()
        with self.assertRaises(ValueError):
            SkewPolicy(max_allowed_skewed_rows=-1).validate()
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "p.json"
            p.write_text("[]", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_policy(p)

    def test_loader_boundary_checks_and_null_serving_val_war_story(self) -> None:
        with self.assertRaises(FileNotFoundError):
            load_parity_rows(Path("/tmp/missing_skfix_999.jsonl"))
        with tempfile.TemporaryDirectory() as tmp:
            e = Path(tmp) / "e.jsonl"
            e.write_text("\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_parity_rows(e)
            b = Path(tmp) / "b.jsonl"
            b.write_text("[]\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_parity_rows(b)
            n = Path(tmp) / "n.jsonl"
            row = {
                "row_id": "FN",
                "feature_name": "f",
                "training_val": 10.0,
                "serving_val": None,
                "reference_val": 10.0,
            }
            n.write_text(json.dumps(row) + "\n", encoding="utf-8")
            s = attribute_skew(load_parity_rows(n), SkewPolicy())
            self.assertEqual(s.serving_fault_count, 1)

    def test_committed_fixture_attributes_four_train_six_serve_and_two_both_wrong(self) -> None:
        s = attribute_skew(load_parity_rows(FIX), load_policy(POL))
        self.assertEqual(s.total_rows, 30)
        self.assertEqual(s.parity_mismatches_count, 10)
        self.assertEqual(s.training_fault_count, 4)
        self.assertEqual(s.serving_fault_count, 6)
        self.assertEqual(s.both_fault_count, 2)
        self.assertEqual(s.clean_parity_count, 18)
        self.assertAlmostEqual(s.resolution_floor_pct, 3.33)
        self.assertFalse(s.gate_passed)

    def test_empty_rows_rejected(self) -> None:
        with self.assertRaises(ValueError):
            attribute_skew([], SkewPolicy())

    def test_cli_exit_codes_and_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            oj = Path(tmp) / "o.json"
            rc = cli_main([
                "attribute", "--fixture", str(FIX), "--policy", str(POL), "--out", str(oj)
            ])
            self.assertEqual(rc, 1)
            pf = Path(tmp) / "p.json"
            pf.write_text(json.dumps({"max_allowed_skewed_rows": 50}), encoding="utf-8")
            rc2 = cli_main([
                "attribute", "--fixture", str(FIX), "--policy", str(pf),
                "--out", str(oj), "--json-only",
            ])
            self.assertEqual(rc2, 0)
        self.assertEqual(cli_main(["attribute", "--fixture", "/tmp/missing_sk_888.jsonl"]), 2)
        self.assertEqual(cli_main(["attribute", "--max-rows", "abc"]), 2)
        self.assertEqual(cli_main(["--help"]), 0)
        s = attribute_skew(load_parity_rows(FIX), load_policy(POL))
        self.assertIn("BOTH_SIDES_WRONG", render_table(s))
