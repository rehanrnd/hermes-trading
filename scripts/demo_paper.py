from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hermes_trading_agent.agent_loop import run_reflection_loop
from hermes_trading_agent.data import load_market_data_csv
from hermes_trading_agent.goal import load_goal


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Run a Hermes Trading paper demo")
    parser.add_argument(
        "--data-csv",
        type=Path,
        help="Optional CSV file with timestamp, close, and signal columns",
    )
    parser.add_argument(
        "--fee-bps",
        type=float,
        default=0.0,
        help="Optional round-trip fee model in basis points per side",
    )
    parser.add_argument(
        "--slippage-bps",
        type=float,
        default=0.0,
        help="Optional slippage model in basis points per fill",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    goal = load_goal()

    if args.data_csv is None:
        prices = [100.0, 101.0, 102.0, 101.5, 103.0, 104.0, 103.0, 105.0]
        signals = [1, 1, 1, 0, -1, -1, 0, 1]
        source = "synthetic sample"
    else:
        market_data = load_market_data_csv(args.data_csv)
        prices = market_data.prices
        signals = market_data.signals
        source = str(args.data_csv)

    backtest_kwargs = {
        "fee_bps": args.fee_bps,
        "slippage_bps": args.slippage_bps,
    }
    report = run_reflection_loop(goal, prices, signals, **backtest_kwargs)

    print("Goal:", goal.asset, goal.max_drawdown, goal.min_sharpe)
    print("Source:", source)
    if args.fee_bps or args.slippage_bps:
        print("Cost model:", f"fee_bps={args.fee_bps}", f"slippage_bps={args.slippage_bps}")
    print("Trades:", len(report.result.trades))
    print("Final equity:", round(report.result.final_equity, 2))
    print("Total return:", round(report.result.total_return * 100, 2), "%")
    print("Max drawdown:", round(report.result.max_drawdown * 100, 2), "%")
    print("Sharpe:", round(report.result.sharpe, 3))
    print("Recommendation:", report.recommendation)


if __name__ == "__main__":
    main()
