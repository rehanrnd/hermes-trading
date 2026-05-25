from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hermes_trading_agent.paper import SimulationResult, Trade
from hermes_trading_agent.journal import render_trade_journal_csv, write_trade_journal_csv


class TradeJournalExportTests(unittest.TestCase):
    def test_render_trade_journal_csv_includes_header_and_trade_rows(self) -> None:
        result = SimulationResult(
            trades=[
                Trade(side="long", entry_price=100.0, exit_price=110.0, quantity=2.0),
                Trade(side="short", entry_price=120.0, exit_price=115.0, quantity=1.5),
            ],
            equity_curve=[1000.0, 1020.0],
            returns=[0.0, 0.02],
            final_equity=1020.0,
            max_drawdown=0.0,
            sharpe=1.0,
            total_return=0.02,
        )

        csv_text = render_trade_journal_csv(result, asset="XAUUSD", source="synthetic sample")
        lines = csv_text.strip().splitlines()

        self.assertEqual(
            lines[0],
            "asset,source,trade_index,side,entry_price,exit_price,quantity,pnl,return_pct",
        )
        self.assertEqual(lines[1], "XAUUSD,synthetic sample,1,long,100.0,110.0,2.0,20.0,0.1")
        self.assertEqual(lines[2], "XAUUSD,synthetic sample,2,short,120.0,115.0,1.5,7.5,0.041666666666666664")

    def test_write_trade_journal_csv_writes_file(self) -> None:
        result = SimulationResult(
            trades=[Trade(side="long", entry_price=50.0, exit_price=55.0, quantity=1.0)],
            equity_curve=[1000.0, 1005.0],
            returns=[0.0, 0.005],
            final_equity=1005.0,
            max_drawdown=0.0,
            sharpe=1.0,
            total_return=0.005,
        )

        tmp_dir = Path(self._get_tmp_dir())
        csv_path = tmp_dir / "journal.csv"
        write_trade_journal_csv(csv_path, result, asset="XAUUSD", source="demo")

        self.assertTrue(csv_path.exists())
        self.assertIn("XAUUSD,demo,1,long,50.0,55.0,1.0,5.0,0.1", csv_path.read_text(encoding="utf-8"))

    def _get_tmp_dir(self) -> str:
        import tempfile

        return tempfile.mkdtemp()


if __name__ == "__main__":
    unittest.main()
