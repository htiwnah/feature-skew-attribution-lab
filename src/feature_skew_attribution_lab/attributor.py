"""Deterministic three-way skew attributor breaking training-vs-serving parity symmetry."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from feature_skew_attribution_lab.config import SkewPolicy


@dataclass(frozen=True)
class ParityRow:
    """Entity feature compared across training, serving, and reference oracle."""

    row_id: str
    feature_name: str
    training_val: float
    serving_val: float
    reference_val: float


@dataclass(frozen=True)
class SkewVerdict:
    """Per-row fault attribution."""

    row_id: str
    feature_name: str
    parity_mismatch: bool
    train_err: float
    serve_err: float
    blamed_side: str


@dataclass(frozen=True)
class SkewSummary:
    """Aggregated skew attribution summary."""

    total_rows: int
    parity_mismatches_count: int
    training_fault_count: int
    serving_fault_count: int
    both_fault_count: int
    clean_parity_count: int
    resolution_floor_pct: float
    gate_passed: bool
    verdicts: list[SkewVerdict] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """Serialize summary to plain JSON dictionary."""
        return {
            "total_rows": self.total_rows,
            "parity_mismatches_count": self.parity_mismatches_count,
            "training_fault_count": self.training_fault_count,
            "serving_fault_count": self.serving_fault_count,
            "both_fault_count": self.both_fault_count,
            "clean_parity_count": self.clean_parity_count,
            "resolution_floor_pct": self.resolution_floor_pct,
            "gate_passed": self.gate_passed,
            "verdicts": [
                {
                    "row_id": v.row_id,
                    "feature_name": v.feature_name,
                    "parity_mismatch": v.parity_mismatch,
                    "train_err": v.train_err,
                    "serve_err": v.serve_err,
                    "blamed_side": v.blamed_side,
                }
                for v in self.verdicts
            ],
        }


def load_parity_rows(path: str | Path) -> list[ParityRow]:
    """Load JSONL parity rows with null-value coercion and validation."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Parity fixture not found: {p}")
    out: list[ParityRow] = []
    for ln_no, raw_ln in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        s = raw_ln.strip()
        if not s:
            continue
        r = json.loads(s)
        if not isinstance(r, dict):
            raise ValueError(f"Line {ln_no} must be a JSON object")
        tv = 0.0 if r.get("training_val") is None else float(r["training_val"])
        sv = 0.0 if r.get("serving_val") is None else float(r["serving_val"])
        rv = 0.0 if r.get("reference_val") is None else float(r["reference_val"])
        out.append(ParityRow(str(r["row_id"]), str(r["feature_name"]), tv, sv, rv))
    if not out:
        raise ValueError(f"No parity rows in {p}")
    return out


def attribute_skew(rows: list[ParityRow], policy: SkewPolicy) -> SkewSummary:
    """Compare training and serving values to reference oracle to blame guilty side."""
    if not rows:
        raise ValueError("Cannot attribute skew on empty list")
    policy.validate()
    tol = policy.abs_tolerance
    pmm = tf = sf = bf = cl = 0
    verdicts: list[SkewVerdict] = []
    for r in rows:
        mm = abs(r.training_val - r.serving_val) > tol
        te = round(abs(r.training_val - r.reference_val), 4)
        se = round(abs(r.serving_val - r.reference_val), 4)
        pmm += int(mm)
        tb, sb = te > tol, se > tol
        if tb and sb:
            bf += 1
            side = "BOTH_SIDES_WRONG"
        elif tb:
            tf += 1
            side = "TRAINING_FAULT"
        elif sb:
            sf += 1
            side = "SERVING_FAULT"
        else:
            cl += 1
            side = "CLEAN_PARITY"
        verdicts.append(SkewVerdict(r.row_id, r.feature_name, mm, te, se, side))
    n = len(verdicts)
    return SkewSummary(
        total_rows=n,
        parity_mismatches_count=pmm,
        training_fault_count=tf,
        serving_fault_count=sf,
        both_fault_count=bf,
        clean_parity_count=cl,
        resolution_floor_pct=round((1.0 / n) * 100.0, 2),
        gate_passed=(tf + sf + bf) <= policy.max_allowed_skewed_rows,
        verdicts=verdicts,
    )
