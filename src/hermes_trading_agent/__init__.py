"""Hermes trading agent scaffold."""

from .agent_loop import run_reflection_loop, run_reflection_loop_from_market_data
from .data import MarketData, load_market_data_csv
from .goal import Goal, load_goal
from .paper import SimulationResult, Trade, reflection_recommendation, run_paper_backtest, run_paper_backtest_from_market_data

__all__ = [
    "Goal",
    "MarketData",
    "SimulationResult",
    "Trade",
    "load_goal",
    "load_market_data_csv",
    "reflection_recommendation",
    "run_paper_backtest",
    "run_paper_backtest_from_market_data",
    "run_reflection_loop",
    "run_reflection_loop_from_market_data",
]
