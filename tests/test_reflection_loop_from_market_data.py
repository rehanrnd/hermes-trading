from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hermes_trading_agent.agent_loop import run_reflection_loop, run_reflection_loop_from_market_data
from hermes_trading_agent.data import MarketData
from hermes_trading_agent.goal import load_goal


class ReflectionLoopFromMarketDataTests(unittest.TestCase):
    def test_run_reflection_loop_from_market_data_matches_direct_lists(self) -> None:
        goal = load_goal()
        market_data = MarketData(
            timestamps=["2026-01-01T00:00:00Z", "2026-01-01T00:05:00Z", "2026-01-01T00:10:00Z"],
            prices=[100.0, 101.0, 102.0],
            signals=[1.0, 0.0, -1.0],
        )

        direct = run_reflection_loop(goal, market_data.prices, market_data.signals)
        from_data = run_reflection_loop_from_market_data(goal, market_data)

        self.assertEqual(from_data, direct)


if __name__ == "__main__":
    unittest.main()
