"""Deterministic three-way feature skew attribution experiments."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from feature_skew_attribution_lab.attributor import attribute_skew, load_parity_rows  # noqa: E402
from feature_skew_attribution_lab.config import load_policy  # noqa: E402


def run_all_experiments(repo_root: Path | None = None) -> dict[str, object]:
    """Execute deterministic three-way skew attribution experiments."""
    root = repo_root or ROOT_DIR
    out_dir = root / "docs" / "experiments"
    out_dir.mkdir(parents=True, exist_ok=True)
    pol = load_policy(root / "policy" / "skew_policy.json")
    rows = load_parity_rows(root / "fixtures" / "feature_parity_rows.jsonl")
    full = attribute_skew(rows, pol)
    exp1 = {
        "total_rows": full.total_rows,
        "parity_mismatches_count": full.parity_mismatches_count,
        "training_fault_count": full.training_fault_count,
        "serving_fault_count": full.serving_fault_count,
        "both_fault_count": full.both_fault_count,
        "clean_parity_count": full.clean_parity_count,
        "resolution_floor_pct": full.resolution_floor_pct,
    }
    (out_dir / "exp1_three_way_skew.json").write_text(
        json.dumps(exp1, indent=2) + "\n", encoding="utf-8"
    )
    return {"exp1": exp1}


def main() -> None:
    e1 = run_all_experiments()["exp1"]
    print(
        f"Exp1 | rows={e1['total_rows']} | train={e1['training_fault_count']} | "
        f"serve={e1['serving_fault_count']} | both={e1['both_fault_count']}"
    )


if __name__ == "__main__":
    main()
