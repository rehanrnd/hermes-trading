from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hermes_trading_agent.monitor import MarketSnapshot, SignalDecision  # noqa: E402


class PaperTraderTests(unittest.TestCase):
    @patch("scripts.run_paper_trader._sync_agent_registry")
    @patch("scripts.run_paper_trader._save_state")
    @patch("scripts.run_paper_trader._load_state", return_value={})
    @patch("scripts.run_paper_trader.load_trading_monitor_state", return_value=[{"history": [1.0, 2.0]}])
    @patch("scripts.run_paper_trader.fetch_gold_price_snapshot")
    @patch("scripts.run_paper_trader.evaluate_market")
    def test_run_once_handles_list_monitor_state_without_crashing(
        self,
        evaluate_market,
        fetch_gold_price_snapshot,
        _load_monitor_state,
        _load_state,
        _save_state,
        _sync_agent_registry,
    ) -> None:
        from scripts.run_paper_trader import run_once

        fetch_gold_price_snapshot.return_value = MarketSnapshot(
            asset="XAU",
            symbol="GC=F",
            source="yahoo_finance",
            timestamp="2026-05-25T12:00:00+00:00",
            price=2390.0,
            previous_close=2388.0,
            change_pct=0.08,
            history=[2388.0, 2390.0],
            source_label="Gold futures proxy",
        )
        evaluate_market.return_value = SignalDecision(
            state="flat",
            action="wait",
            confidence=42.0,
            reason="test",
            risk_state="normal",
        )

        state = run_once(symbol="GC=F", asset="XAU", timeout=1)

        self.assertEqual(state["status"], "running")
        self.assertIsNone(state["open_position"])
        self.assertEqual(state["signal_state"], "flat")


if __name__ == "__main__":
    unittest.main()
