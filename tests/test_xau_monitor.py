from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hermes_trading_agent.monitor import (  # noqa: E402
    MarketSnapshot,
    build_trading_monitor_state,
    evaluate_market,
    format_trading_monitor_state,
)


class XauMonitorTests(unittest.TestCase):
    def test_evaluate_market_detects_clean_uptrend(self) -> None:
        decision = evaluate_market([100.0, 100.5, 101.0, 101.8, 102.4, 103.0, 103.9, 104.5])

        self.assertEqual(decision.state, "bullish")
        self.assertEqual(decision.action, "prepare long")
        self.assertGreater(decision.confidence, 50.0)

    def test_monitor_state_format_mentions_xau_and_signal(self) -> None:
        snapshot = MarketSnapshot(
            asset="XAU",
            symbol="GC=F",
            source="yahoo_finance",
            timestamp="2026-05-25T12:00:00+00:00",
            price=2388.45,
            previous_close=2371.25,
            change_pct=0.72,
            history=[2371.25, 2378.10, 2388.45],
            source_label="Gold futures proxy",
        )
        decision = evaluate_market(snapshot.history + [2391.20, 2394.10, 2399.50, 2404.30])
        state = build_trading_monitor_state(snapshot, decision)

        rendered = format_trading_monitor_state(state)
        self.assertIn("XAU monitor", rendered)
        self.assertIn("GC=F", rendered)
        self.assertIn("signal", rendered)
        self.assertIn("price", rendered)

    @patch("scripts.run_xau_monitor.run_monitor_cycle")
    @patch("scripts.run_xau_monitor.load_trading_monitor_state", return_value=[{"history": [1.0, 2.0]}])
    def test_run_once_handles_list_state_without_crashing(self, _load_state, run_monitor_cycle) -> None:
        from scripts.run_xau_monitor import run_once
        from hermes_trading_agent.monitor import TradingMonitorState

        run_monitor_cycle.return_value = TradingMonitorState(
            asset="XAU",
            symbol="GC=F",
            source="yahoo_finance",
            source_label="Gold futures proxy",
            updated_at="2026-05-25T12:00:00+00:00",
            price=2390.0,
            previous_close=2388.0,
            change_pct=0.08,
            signal_state="flat",
            signal_action="wait",
            signal_confidence=42.0,
            signal_reason="test",
            risk_state="normal",
            status="monitoring",
            history=[2388.0, 2390.0],
            sample_count=2,
            next_check_seconds=60,
            last_error=None,
        )

        state = run_once(symbol="GC=F", asset="XAU", state_path=Path("state/xau_monitor.json"), timeout=1, interval=60)

        self.assertEqual(state.status, "monitoring")
        self.assertEqual(state.price, 2390.0)


if __name__ == "__main__":
    unittest.main()
