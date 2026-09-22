from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hermes_trading_agent.bitget import build_bitget_setup_report, load_bitget_config


class BitgetReadinessTests(unittest.TestCase):
    def test_build_bitget_setup_report_marks_paper_futures_ready_when_env_is_present(self) -> None:
        config_path = Path(self._testMethodName + "_config.json")
        env_path = Path(self._testMethodName + "_env")
        try:
            config_path.write_text(
                """
                {
                  "exchange": "bitget",
                  "mode": "paper",
                  "demo": true,
                  "product": "futures",
                  "api_key_env": "BITGET_API_KEY",
                  "api_secret_env": "BITGET_API_SECRET",
                  "passphrase_env": "BITGET_API_PASSPHRASE",
                  "base_url": null,
                  "withdrawals_enabled": false,
                  "notes": {"purpose": "test"}
                }
                """,
                encoding="utf-8",
            )
            env_path.write_text(
                "\n".join(
                    [
                        "BITGET_API_KEY=test-key",
                        "BITGET_API_SECRET=test-secret",
                        "BITGET_API_PASSPHRASE=test-passphrase",
                    ]
                ),
                encoding="utf-8",
            )

            config = load_bitget_config(config_path)
            report = build_bitget_setup_report(config, env_file=env_path)

            self.assertTrue(report.ready_for_demo)
            self.assertEqual(report.checks, ())
            self.assertEqual(report.env_status, {
                "BITGET_API_KEY": True,
                "BITGET_API_SECRET": True,
                "BITGET_API_PASSPHRASE": True,
            })
        finally:
            if config_path.exists():
                config_path.unlink()
            if env_path.exists():
                env_path.unlink()


if __name__ == "__main__":
    unittest.main()
