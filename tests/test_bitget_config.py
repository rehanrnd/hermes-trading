from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hermes_trading_agent.bitget import bitget_env_status, load_bitget_config


class BitgetConfigTests(unittest.TestCase):
    def test_load_bitget_config(self) -> None:
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

            config = load_bitget_config(config_path)
            status = bitget_env_status(config, env_file=env_path)

            self.assertEqual(config.exchange, "bitget")
            self.assertEqual(config.mode, "paper")
            self.assertTrue(config.demo)
            self.assertEqual(config.product, "futures")
            self.assertFalse(config.withdrawals_enabled)
            self.assertEqual(
                status,
                {
                    "BITGET_API_KEY": False,
                    "BITGET_API_SECRET": False,
                    "BITGET_API_PASSPHRASE": False,
                },
            )
        finally:
            if config_path.exists():
                config_path.unlink()
            if env_path.exists():
                env_path.unlink()


if __name__ == "__main__":
    unittest.main()
