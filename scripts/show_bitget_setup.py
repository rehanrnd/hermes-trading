from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hermes_trading_agent.bitget import build_bitget_setup_report, format_bitget_setup_report, load_bitget_config  # noqa: E402


def main() -> None:
    config = load_bitget_config()
    report = build_bitget_setup_report(config)
    print(format_bitget_setup_report(report))


if __name__ == "__main__":
    main()
