from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hermes_trading_agent.data import MarketData, load_market_data_csv


class MarketDataIngestionTests(unittest.TestCase):
    def test_load_market_data_csv_reads_prices_and_signals(self) -> None:
        tmp_path = Path(self._get_tmp_dir())
        csv_path = tmp_path / "market_data.csv"
        csv_path.write_text(
            "timestamp,close,signal\n"
            "2026-01-01T00:00:00Z,100.5,1\n"
            "2026-01-01T00:05:00Z,101.0,0\n"
            "2026-01-01T00:10:00Z,100.8,-1\n",
            encoding="utf-8",
        )

        data = load_market_data_csv(csv_path)

        self.assertEqual(
            data,
            MarketData(
                timestamps=["2026-01-01T00:00:00Z", "2026-01-01T00:05:00Z", "2026-01-01T00:10:00Z"],
                prices=[100.5, 101.0, 100.8],
                signals=[1.0, 0.0, -1.0],
            ),
        )

    def test_load_market_data_csv_requires_close_column(self) -> None:
        tmp_path = Path(self._get_tmp_dir())
        csv_path = tmp_path / "bad_market_data.csv"
        csv_path.write_text(
            "timestamp,signal\n"
            "2026-01-01T00:00:00Z,1\n",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "close"):
            load_market_data_csv(csv_path)

    def _get_tmp_dir(self) -> str:
        import tempfile

        return tempfile.mkdtemp()


if __name__ == "__main__":
    unittest.main()
