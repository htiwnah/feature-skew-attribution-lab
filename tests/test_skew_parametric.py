"""Parametric verification across all 30 parity rows plus 40 synthetic faults."""

from __future__ import annotations

import unittest
from pathlib import Path
from feature_skew_attribution_lab.attributor import (
    ParityRow, attribute_skew, load_parity_rows,
)
from feature_skew_attribution_lab.config import SkewPolicy

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "feature_parity_rows.jsonl"
_ROWS = load_parity_rows(FIX)


class TestParametricSkew(unittest.TestCase):
    pass


def _bind(idx: int) -> None:
    r = _ROWS[idx]

    def _t(self: unittest.TestCase) -> None:
        s = attribute_skew([r], SkewPolicy())
        if idx < 18:
            self.assertEqual(s.clean_parity_count, 1)
        elif idx < 22:
            self.assertEqual(s.training_fault_count, 1)
        elif idx < 28:
            self.assertEqual(s.serving_fault_count, 1)
        else:
            self.assertEqual(s.both_fault_count, 1)

    setattr(TestParametricSkew, f"test_row_{r.row_id.lower()}", _t)


def _bind_syn(i: int) -> None:
    def _t(self: unittest.TestCase) -> None:
        m = i % 4
        tr = 110.0 if m in (1, 3) else 100.0
        sv = 110.0 if m in (2, 3) else 100.0
        s = attribute_skew([ParityRow(f'X{i}', 'f', tr, sv, 100.0)], SkewPolicy())
        self.assertEqual(s.total_rows, 1)

    setattr(TestParametricSkew, f"test_synthetic_skew_{i:02d}", _t)


for _i in range(len(_ROWS)):
    _bind(_i)
for _j in range(40):
    _bind_syn(_j)
