from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hermes_trading_agent.monitor import (  # noqa: E402
    DEFAULT_ASSET,
    DEFAULT_STATE_PATH,
    DEFAULT_SYMBOL,
    TradingMonitorState,
    format_trading_monitor_state,
    load_trading_monitor_state,
    run_monitor_cycle,
    save_trading_monitor_state,
)


def _extract_history(state: object | None) -> list[float]:
    if not state:
        return []
    if isinstance(state, dict):
        history = state.get("history", [])
    elif isinstance(state, list):
        history = state
    else:
        return []
    if not isinstance(history, list):
        return []
    cleaned: list[float] = []
    for item in history:
        try:
            cleaned.append(float(item))
        except (TypeError, ValueError):
            continue
    return cleaned


def _state_summary(state: TradingMonitorState) -> str:
    return format_trading_monitor_state(state)


def run_once(*, symbol: str, asset: str, state_path: Path, timeout: int, interval: int) -> TradingMonitorState:
    previous_state = load_trading_monitor_state(state_path)
    history = _extract_history(previous_state)
    last_error = None
    if isinstance(previous_state, dict):
        last_error = previous_state.get("last_error")
    try:
        state = run_monitor_cycle(
            symbol=symbol,
            asset=asset,
            history=history,
            next_check_seconds=interval,
            timeout=timeout,
            last_error=last_error if isinstance(last_error, str) else None,
        )
    except Exception as exc:
        if previous_state and isinstance(previous_state, dict):
            fallback = TradingMonitorState(
                asset=str(previous_state.get("asset", asset)),
                symbol=str(previous_state.get("symbol", symbol)),
                source=str(previous_state.get("source", "yahoo_finance")),
                source_label=str(previous_state.get("source_label", "Gold futures proxy")),
                updated_at=str(previous_state.get("updated_at", "")),
                price=float(previous_state.get("price", 0.0) or 0.0),
                previous_close=previous_state.get("previous_close"),
                change_pct=previous_state.get("change_pct"),
                signal_state=str(previous_state.get("signal_state", "error")),
                signal_action=str(previous_state.get("signal_action", "wait")),
                signal_confidence=float(previous_state.get("signal_confidence", 0.0) or 0.0),
                signal_reason=str(previous_state.get("signal_reason", "Price fetch failed; holding position.")),
                risk_state=str(previous_state.get("risk_state", "watch")),
                status="monitoring_with_warning",
                history=history[-120:],
                sample_count=len(history),
                next_check_seconds=interval,
                last_error=str(exc),
            )
            return fallback
        raise
    return state


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the 24/7 XAU monitor loop.")
    parser.add_argument("--symbol", default=os.getenv("XAU_MONITOR_SYMBOL", DEFAULT_SYMBOL))
    parser.add_argument("--asset", default=os.getenv("XAU_MONITOR_ASSET", DEFAULT_ASSET))
    parser.add_argument("--state-path", default=os.getenv("XAU_MONITOR_STATE", str(DEFAULT_STATE_PATH)))
    parser.add_argument("--interval", type=int, default=int(os.getenv("XAU_MONITOR_INTERVAL", "60")))
    parser.add_argument("--timeout", type=int, default=int(os.getenv("XAU_MONITOR_TIMEOUT", "15")))
    parser.add_argument("--once", action="store_true", help="Run a single cycle and exit.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    state_path = Path(args.state_path)

    if args.once:
        state = run_once(symbol=args.symbol, asset=args.asset, state_path=state_path, timeout=args.timeout, interval=args.interval)
        save_trading_monitor_state(state, state_path)
        print(_state_summary(state))
        return 0

    print(f"Starting XAU monitor at {state_path} ({args.symbol}, every {args.interval}s)")
    while True:
        try:
            state = run_once(symbol=args.symbol, asset=args.asset, state_path=state_path, timeout=args.timeout, interval=args.interval)
            save_trading_monitor_state(state, state_path)
            print(_state_summary(state))
        except KeyboardInterrupt:
            print("Stopping XAU monitor.")
            return 0
        except Exception as exc:
            print(f"monitor error: {exc}", file=sys.stderr)
        time.sleep(max(5, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
