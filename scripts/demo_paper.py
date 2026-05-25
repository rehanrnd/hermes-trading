from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hermes_trading_agent.agent_loop import run_reflection_loop
from hermes_trading_agent.goal import load_goal


def main() -> None:
    goal = load_goal()
    prices = [100.0, 101.0, 102.0, 101.5, 103.0, 104.0, 103.0, 105.0]
    signals = [1, 1, 1, 0, -1, -1, 0, 1]
    report = run_reflection_loop(goal, prices, signals)

    print("Goal:", goal.asset, goal.max_drawdown, goal.min_sharpe)
    print("Trades:", len(report.result.trades))
    print("Final equity:", round(report.result.final_equity, 2))
    print("Total return:", round(report.result.total_return * 100, 2), "%")
    print("Max drawdown:", round(report.result.max_drawdown * 100, 2), "%")
    print("Sharpe:", round(report.result.sharpe, 3))
    print("Recommendation:", report.recommendation)


if __name__ == "__main__":
    main()
