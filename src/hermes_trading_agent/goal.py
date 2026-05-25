from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Goal:
    asset: str
    target_return_daily: float | None
    target_return_30d: float | None
    max_drawdown: float
    min_sharpe: float
    failure_below: float
    reflection_every: int
    one_variable_only: bool
    notes: dict[str, Any]


def _parse_scalar(raw: str) -> Any:
    value = raw.strip()
    if value in {"null", "Null", "NULL", "~"}:
        return None
    if value in {"true", "True", "TRUE"}:
        return True
    if value in {"false", "False", "FALSE"}:
        return False
    if value.startswith(('"', "'")) and value.endswith(('"', "'")) and len(value) >= 2:
        return value[1:-1]
    try:
        if "." in value or "e" in value.lower():
            return float(value)
        return int(value)
    except ValueError:
        return value


def load_goal(path: str | Path = "state/goal.yaml") -> Goal:
    goal_path = Path(path)
    lines = goal_path.read_text(encoding="utf-8").splitlines()
    data: dict[str, Any] = {}
    notes: dict[str, Any] = {}
    in_notes = False

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not line.startswith(" ") and ":" in line:
            key, raw = line.split(":", 1)
            key = key.strip()
            raw = raw.strip()
            if key == "notes":
                in_notes = True
                continue
            data[key] = _parse_scalar(raw)
            continue
        if in_notes and line.startswith("  ") and ":" in line:
            key, raw = line.strip().split(":", 1)
            notes[key.strip()] = _parse_scalar(raw)

    return Goal(
        asset=data["asset"],
        target_return_daily=data.get("target_return_daily"),
        target_return_30d=data.get("target_return_30d"),
        max_drawdown=data["max_drawdown"],
        min_sharpe=data["min_sharpe"],
        failure_below=data["failure_below"],
        reflection_every=data["reflection_every"],
        one_variable_only=data["one_variable_only"],
        notes=notes,
    )
