from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hermes_trading_agent.agents import load_agents
from hermes_trading_agent.dashboard import render_dashboard
from hermes_trading_agent.goal import load_goal
from hermes_trading_agent.paper import run_paper_backtest
from hermes_trading_agent.summary import build_backtest_summary


class DashboardRenderTests(unittest.TestCase):
    def test_render_dashboard_matches_ops_dashboard_shape(self) -> None:
        goal = load_goal()
        result = run_paper_backtest([100.0, 101.0, 100.5, 102.0], [1.0, 0.0, -1.0, 0.0])
        summary = build_backtest_summary(goal, result, source="synthetic sample")

        html = render_dashboard(goal, load_agents(), result, summary=summary)

        self.assertIn("Hermes AI Operations Dashboard", html)
        self.assertIn("Command Center", html)
        self.assertIn("Activity feed", html)
        self.assertIn("Portfolio performance", html)
        self.assertIn("AI TEAM", html)
        self.assertIn("2 AGENTS", html)
        self.assertIn("Trading", html)
        self.assertIn("Airdrop", html)
        self.assertIn("$", html)
        self.assertIn("%", html)
        self.assertIn("● LIVE", html)

    def test_render_dashboard_includes_xau_monitor_panel(self) -> None:
        goal = load_goal()
        result = run_paper_backtest([100.0, 101.0, 100.5, 102.0], [1.0, 0.0, -1.0, 0.0])
        monitor_state = {
            "asset": "XAU",
            "symbol": "GC=F",
            "price": 2398.12,
            "change_pct": 0.84,
            "signal_state": "bullish",
            "signal_action": "prepare long",
            "signal_confidence": 77.0,
            "signal_reason": "Trend and momentum are aligned upward.",
            "risk_state": "normal",
            "updated_at": "2026-05-25T12:00:00+00:00",
            "history": [2388.0, 2390.5, 2392.2, 2395.4, 2398.1],
        }

        html = render_dashboard(goal, load_agents(), result, monitor_state=monitor_state)

        self.assertIn("XAU monitor", html)
        self.assertIn("LIVE MARKET WATCH", html)
        self.assertIn("prepare long", html)
        self.assertIn("$2,398.12", html)


if __name__ == "__main__":
    unittest.main()
