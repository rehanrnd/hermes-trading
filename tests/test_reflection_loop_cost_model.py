from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hermes_trading_agent.agent_loop import run_reflection_loop, run_reflection_loop_from_market_data
from hermes_trading_agent.data import MarketData
from hermes_trading_agent.goal import Goal


class ReflectionLoopCostModelTests(unittest.TestCase):
    def test_run_reflection_loop_accepts_fee_bps(self) -> None:
        goal = Goal(
            asset="XAUUSD",
            target_return_daily=0.07,
            target_return_30d=None,
            max_drawdown=0.08,
            min_sharpe=1.2,
            failure_below=0.05,
            reflection_every=5,
            one_variable_only=True,
            notes={},
        )

        report = run_reflection_loop(
            goal,
            [100.0, 110.0],
            [1.0, 0.0],
            fee_bps=10.0,
        )

        self.assertAlmostEqual(report.result.final_equity, 10097.9, places=6)
        self.assertEqual(
            report.recommendation,
            "Keep the current setup and collect another sample of trades before changing one variable.",
        )

    def test_run_reflection_loop_from_market_data_accepts_slippage_bps(self) -> None:
        goal = Goal(
            asset="XAUUSD",
            target_return_daily=0.07,
            target_return_30d=None,
            max_drawdown=0.08,
            min_sharpe=1.2,
            failure_below=0.05,
            reflection_every=5,
            one_variable_only=True,
            notes={},
        )
        market_data = MarketData(
            timestamps=["2026-01-01T00:00:00Z", "2026-01-01T00:05:00Z"],
            prices=[100.0, 110.0],
            signals=[1.0, 0.0],
        )

        report = run_reflection_loop_from_market_data(goal, market_data, slippage_bps=100.0)

        self.assertAlmostEqual(report.result.final_equity, 10078.217821782178, places=6)
        self.assertEqual(
            report.recommendation,
            "Tighten the entry filter so only higher-conviction signals are traded.",
        )


if __name__ == "__main__":
    unittest.main()
