"""CLI for feature-skew-attribution-lab with explicit 0/1/2 exit codes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from feature_skew_attribution_lab.attributor import SkewSummary, attribute_skew, load_parity_rows
from feature_skew_attribution_lab.config import load_policy


def render_table(s: SkewSummary, max_rows: int = 12) -> str:
    """Render scannable three-way skew attribution table."""
    hdr = f"{'RowID':<7} {'Feature':<18} {'ParMM':<5} {'TrErr':>7} {'SvErr':>7} {'BlamedSide'}"
    lines = [
        "Feature Skew Attribution: Breaking Training vs Serving Parity Symmetry",
        (
            f"Rows: {s.total_rows} | Parity Mismatches: {s.parity_mismatches_count} | "
            f"Train Faults: {s.training_fault_count} | Serve Faults: {s.serving_fault_count} | "
            f"Both Wrong: {s.both_fault_count}"
        ),
        hdr,
        "-" * len(hdr),
    ]
    ordered = sorted(s.verdicts, key=lambda v: (0 if v.blamed_side != "CLEAN_PARITY" else 1, v.row_id))
    for v in ordered[:max_rows]:
        lines.append(
            f"{v.row_id:<7} {v.feature_name:<18} {str(v.parity_mismatch):<5} "
            f"{v.train_err:>7.2f} {v.serve_err:>7.2f} {v.blamed_side}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Execute CLI and return 0 (pass), 1 (answered no), or 2 (error)."""
    p = argparse.ArgumentParser(prog="skew-attr")
    sub = p.add_subparsers(dest="cmd", required=True)
    ap = sub.add_parser("attribute")
    ap.add_argument("--fixture", default="fixtures/feature_parity_rows.jsonl")
    ap.add_argument("--policy", default=None)
    ap.add_argument("--out", default="reports/skew_audit.json")
    ap.add_argument("--max-rows", type=int, default=12)
    ap.add_argument("--json-only", action="store_true")
    try:
        args = p.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2
    try:
        pol = load_policy(args.policy)
        s = attribute_skew(load_parity_rows(args.fixture), pol)
        op = Path(args.out)
        op.parent.mkdir(parents=True, exist_ok=True)
        op.write_text(json.dumps(s.to_dict(), indent=2) + "\n", encoding="utf-8")
    except (FileNotFoundError, ValueError, KeyError, json.JSONDecodeError, TypeError) as exc:
        sys.stderr.write(f"Skew input error: {exc}\n")
        return 2
    if args.json_only:
        sys.stdout.write(json.dumps(s.to_dict(), indent=2) + "\n")
    else:
        sys.stdout.write(render_table(s, max_rows=args.max_rows) + "\n")
    return 0 if s.gate_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
