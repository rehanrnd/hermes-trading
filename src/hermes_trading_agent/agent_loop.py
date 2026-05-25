from __future__ import annotations

from dataclasses import dataclass

from .data import MarketData
from .goal import Goal
from .paper import SimulationResult, reflection_recommendation, run_paper_backtest, run_paper_backtest_from_market_data


@dataclass(frozen=True)
class LoopReport:
    result: SimulationResult
    recommendation: str


def run_reflection_loop(goal: Goal, prices: list[float], signals: list[float], **backtest_kwargs) -> LoopReport:
    result = run_paper_backtest(prices, signals, **backtest_kwargs)
    recommendation = reflection_recommendation(
        result,
        target_drawdown=goal.max_drawdown,
        target_sharpe=goal.min_sharpe,
    )
    return LoopReport(result=result, recommendation=recommendation)


def run_reflection_loop_from_market_data(goal: Goal, market_data: MarketData, **backtest_kwargs) -> LoopReport:
    result = run_paper_backtest_from_market_data(market_data, **backtest_kwargs)
    recommendation = reflection_recommendation(
        result,
        target_drawdown=goal.max_drawdown,
        target_sharpe=goal.min_sharpe,
    )
    return LoopReport(result=result, recommendation=recommendation)
