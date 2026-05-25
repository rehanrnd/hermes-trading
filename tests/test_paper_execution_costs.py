from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hermes_trading_agent.paper import run_paper_backtest


class PaperExecutionCostModelTests(unittest.TestCase):
    def test_run_paper_backtest_applies_fee_bps_to_final_equity(self) -> None:
        result = run_paper_backtest(
            [100.0, 110.0],
            [1.0, 0.0],
            initial_cash=1_000.0,
            position_fraction=1.0,
            fee_bps=10.0,
        )

        self.assertAlmostEqual(result.final_equity, 1097.9, places=6)
        self.assertAlmostEqual(result.total_return, 0.0979, places=6)

    def test_run_paper_backtest_applies_slippage_bps_to_fill_prices(self) -> None:
        result = run_paper_backtest(
            [100.0, 110.0],
            [1.0, 0.0],
            initial_cash=1_000.0,
            position_fraction=1.0,
            slippage_bps=100.0,
        )

        self.assertAlmostEqual(result.final_equity, 1078.2178217821784, places=6)
        self.assertAlmostEqual(result.total_return, 0.07821782178217837, places=6)


if __name__ == "__main__":
    unittest.main()
