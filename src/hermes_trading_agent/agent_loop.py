from __future__ import annotations

from dataclasses import dataclass

from .goal import Goal
from .paper import SimulationResult, reflection_recommendation, run_paper_backtest


@dataclass(frozen=True)
class LoopReport:
    result: SimulationResult
    recommendation: str


def run_reflection_loop(goal: Goal, prices: list[float], signals: list[float]) -> LoopReport:
    result = run_paper_backtest(prices, signals)
    recommendation = reflection_recommendation(
        result,
        target_drawdown=goal.max_drawdown,
        target_sharpe=goal.min_sharpe,
    )
    return LoopReport(result=result, recommendation=recommendation)
