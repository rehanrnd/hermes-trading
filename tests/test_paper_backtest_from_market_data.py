from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hermes_trading_agent.data import MarketData
from hermes_trading_agent.paper import run_paper_backtest, run_paper_backtest_from_market_data


class PaperBacktestFromMarketDataTests(unittest.TestCase):
    def test_run_paper_backtest_from_market_data_matches_direct_lists(self) -> None:
        market_data = MarketData(
            timestamps=["2026-01-01T00:00:00Z", "2026-01-01T00:05:00Z", "2026-01-01T00:10:00Z"],
            prices=[100.0, 101.0, 102.0],
            signals=[1.0, 0.0, -1.0],
        )

        direct = run_paper_backtest(market_data.prices, market_data.signals)
        from_data = run_paper_backtest_from_market_data(market_data)

        self.assertEqual(from_data, direct)


if __name__ == "__main__":
    unittest.main()
