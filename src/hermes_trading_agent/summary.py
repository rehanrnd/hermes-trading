from __future__ import annotations

import json
from pathlib import Path

from .goal import Goal
from .paper import SimulationResult, reflection_recommendation


def build_backtest_summary(goal: Goal, result: SimulationResult, *, source: str) -> dict[str, object]:
    return {
        "asset": goal.asset,
        "source": source,
        "trade_count": len(result.trades),
        "final_equity": result.final_equity,
        "total_return": result.total_return,
        "max_drawdown": result.max_drawdown,
        "sharpe": result.sharpe,
        "recommendation": reflection_recommendation(
            result,
            target_drawdown=goal.max_drawdown,
            target_sharpe=goal.min_sharpe,
        ),
    }


def render_backtest_summary_json(goal: Goal, result: SimulationResult, *, source: str) -> str:
    return json.dumps(build_backtest_summary(goal, result, source=source), indent=2, sort_keys=True)


def write_backtest_summary_json(path: str | Path, goal: Goal, result: SimulationResult, *, source: str) -> Path:
    summary_path = Path(path)
    summary_path.write_text(render_backtest_summary_json(goal, result, source=source), encoding="utf-8")
    return summary_path
