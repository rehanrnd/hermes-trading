from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hermes_trading_agent.goal import load_goal
from hermes_trading_agent.paper import run_paper_backtest
from hermes_trading_agent.summary import render_backtest_summary_json, write_backtest_summary_json


class BacktestSummaryExportTests(unittest.TestCase):
    def test_render_backtest_summary_json_includes_goal_and_metrics(self) -> None:
        goal = load_goal()
        result = run_paper_backtest([100.0, 101.0, 100.5], [1.0, 0.0, -1.0])

        text = render_backtest_summary_json(
            goal=goal,
            result=result,
            source="synthetic sample",
        )
        payload = json.loads(text)

        self.assertEqual(payload["asset"], "XAUUSD")
        self.assertEqual(payload["source"], "synthetic sample")
        self.assertEqual(payload["trade_count"], 2)
        self.assertIn("final_equity", payload)
        self.assertIn("recommendation", payload)

    def test_write_backtest_summary_json_writes_file(self) -> None:
        goal = load_goal()
        result = run_paper_backtest([100.0, 101.0, 102.0], [1.0, 1.0, 0.0])

        tmp_path = Path(self._get_tmp_dir())
        output = tmp_path / "summary.json"
        write_backtest_summary_json(output, goal=goal, result=result, source="demo")

        self.assertTrue(output.exists())
        payload = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(payload["source"], "demo")
        self.assertEqual(payload["asset"], "XAUUSD")

    def _get_tmp_dir(self) -> str:
        import tempfile

        return tempfile.mkdtemp()


if __name__ == "__main__":
    unittest.main()
