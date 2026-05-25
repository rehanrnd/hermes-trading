from __future__ import annotations

from .goal import load_goal


def scaffold_summary() -> str:
    goal = load_goal()
    return (
        f"Asset={goal.asset} | "
        f"daily_target={goal.target_return_daily} | "
        f"max_drawdown={goal.max_drawdown} | "
        f"min_sharpe={goal.min_sharpe} | "
        f"reflection_every={goal.reflection_every} | "
        f"one_variable_only={goal.one_variable_only}"
    )
