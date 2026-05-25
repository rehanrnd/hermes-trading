"""Hermes trading agent scaffold."""

from .agent_loop import run_reflection_loop
from .goal import Goal, load_goal
from .paper import SimulationResult, Trade, reflection_recommendation, run_paper_backtest

__all__ = [
    "Goal",
    "SimulationResult",
    "Trade",
    "load_goal",
    "reflection_recommendation",
    "run_paper_backtest",
    "run_reflection_loop",
]
