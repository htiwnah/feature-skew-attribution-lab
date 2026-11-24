"""Explicit policy loader for numeric tolerance and skew fault budgets."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SkewPolicy:
    """Immutable skew tolerance and fault budget policy."""

    policy_version: str = "1.0"
    abs_tolerance: float = 0.01
    max_allowed_skewed_rows: int = 0
    fixture_path: str = "fixtures/feature_parity_rows.jsonl"

    def validate(self) -> None:
        """Enforce non-negative tolerance and fault budget."""
        if self.abs_tolerance < 0.0:
            raise ValueError("abs_tolerance must be >= 0.0")
        if self.max_allowed_skewed_rows < 0:
            raise ValueError("max_allowed_skewed_rows must be >= 0")


def load_policy(path: str | Path | None = None) -> SkewPolicy:
    """Load SkewPolicy from JSON or return validated defaults."""
    if path is None:
        cfg = SkewPolicy()
        cfg.validate()
        return cfg
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Policy not found: {p}")
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Policy must be a JSON object")
    cfg = SkewPolicy(**raw)
    cfg.validate()
    return cfg
