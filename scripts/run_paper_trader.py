from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hermes_trading_agent.agents import load_agents  # noqa: E402
from hermes_trading_agent.monitor import (  # noqa: E402
    DEFAULT_ASSET,
    DEFAULT_SYMBOL,
    evaluate_market,
    fetch_gold_price_snapshot,
    format_trading_monitor_state,
    load_trading_monitor_state,
)

STATE_PATH = ROOT / "state" / "paper_trader.json"
LEDGER_PATH = ROOT / "state" / "paper_trades.jsonl"
AGENTS_PATH = ROOT / "state" / "agents.json"
INITIAL_CASH = 10_000.0
POSITION_FRACTION = 0.10
FEE_BPS = 1.0
SLIPPAGE_BPS = 2.0


@dataclass(frozen=True)
class PaperPosition:
    side: str
    entry_price: float
    quantity: float
    opened_at: str
    signal_state: str
    signal_action: str
    signal_confidence: float
    reason: str
    stop_loss: float
    take_profit: float
    strategy: str


@dataclass(frozen=True)
class TradePlan:
    side: str
    entry_price: float
    stop_loss: float
    take_profit: float
    reward_risk: float
    strategy: str
    reason: str


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _coerce_history(state: object | None) -> list[float]:
    if not state:
        return []
    if isinstance(state, dict):
        history = state.get("history", [])
    elif isinstance(state, (list, tuple)):
        history = state
    else:
        return []
    if not isinstance(history, list):
        history = list(history)
    cleaned: list[float] = []
    for item in history:
        try:
            cleaned.append(float(item))
        except (TypeError, ValueError):
            continue
    return cleaned


def _entry_fill(price: float, side: int, slippage_rate: float) -> float:
    if side > 0:
        return price * (1.0 + slippage_rate)
    return price * (1.0 - slippage_rate)


def _exit_fill(price: float, side: int, slippage_rate: float) -> float:
    if side > 0:
        return price * (1.0 - slippage_rate)
    return price * (1.0 + slippage_rate)


def _signal_side(decision_state: str, confidence: float, risk_state: str) -> int:
    if risk_state == "high" or confidence < 58.0:
        return 0
    if decision_state == "bullish":
        return 1
    if decision_state == "bearish":
        return -1
    return 0


def _recent_range_metrics(history: list[float]) -> tuple[float, float]:
    cleaned = _coerce_history(history)
    if len(cleaned) < 4:
        return 0.0, 0.0
    window = cleaned[-8:]
    returns: list[float] = []
    for first, second in zip(window, window[1:]):
        if first != 0:
            returns.append((second - first) / first)
    volatility = pstdev(returns) if len(returns) >= 2 else 0.0
    range_pct = 0.0 if min(window) == 0 else (max(window) - min(window)) / min(window)
    return volatility, range_pct


def _build_trade_plan(price: float, decision_state: str, decision_confidence: float, risk_state: str, history: list[float]) -> TradePlan | None:
    side = _signal_side(decision_state, decision_confidence, risk_state)
    if side == 0:
        return None

    volatility, range_pct = _recent_range_metrics(history)
    stop_pct = max(0.0025, volatility * 1.8, range_pct * 0.22)
    reward_risk = 1.8
    stop_distance = price * stop_pct
    target_distance = stop_distance * reward_risk

    if side > 0:
        stop_loss = price - stop_distance
        take_profit = price + target_distance
        strategy = "trend-following pullback long"
        reason = "Bullish momentum plus trend alignment. Enter only with a fixed stop below structure and a 1:1.8 target."
    else:
        stop_loss = price + stop_distance
        take_profit = price - target_distance
        strategy = "trend-following pullback short"
        reason = "Bearish momentum plus trend alignment. Enter only with a fixed stop above structure and a 1:1.8 target."

    return TradePlan(
        side="long" if side > 0 else "short",
        entry_price=price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        reward_risk=reward_risk,
        strategy=strategy,
        reason=reason,
    )


def _trade_trigger_reason(position: PaperPosition, price: float) -> str | None:
    if position.side == "long":
        if price <= position.stop_loss:
            return "stop_loss"
        if price >= position.take_profit:
            return "take_profit"
    else:
        if price >= position.stop_loss:
            return "stop_loss"
        if price <= position.take_profit:
            return "take_profit"
    return None


def _position_to_dict(position: PaperPosition) -> dict[str, Any]:
    return {
        "side": position.side,
        "entry_price": position.entry_price,
        "quantity": position.quantity,
        "opened_at": position.opened_at,
        "signal_state": position.signal_state,
        "signal_action": position.signal_action,
        "signal_confidence": position.signal_confidence,
        "reason": position.reason,
        "stop_loss": position.stop_loss,
        "take_profit": position.take_profit,
        "strategy": position.strategy,
    }


def _position_from_dict(payload: dict[str, Any] | None) -> PaperPosition | None:
    if not payload or not isinstance(payload, dict):
        return None
    try:
        return PaperPosition(
            side=str(payload["side"]),
            entry_price=float(payload["entry_price"]),
            quantity=float(payload["quantity"]),
            opened_at=str(payload["opened_at"]),
            signal_state=str(payload.get("signal_state", "")),
            signal_action=str(payload.get("signal_action", "")),
            signal_confidence=float(payload.get("signal_confidence", 0.0) or 0.0),
            reason=str(payload.get("reason", "")),
            stop_loss=float(payload.get("stop_loss", payload["entry_price"])),
            take_profit=float(payload.get("take_profit", payload["entry_price"])),
            strategy=str(payload.get("strategy", "trend-following pullback")),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _load_state() -> dict[str, Any]:
    state = _load_json(STATE_PATH, {})
    if not isinstance(state, dict):
        return {}
    return state


def _save_state(state: dict[str, Any]) -> None:
    _write_json(STATE_PATH, state)


def _sync_agent_registry(state: dict[str, Any], summary: str, monitor_state: dict[str, Any]) -> None:
    data = _load_json(AGENTS_PATH, {"agents": []})
    if not isinstance(data, dict):
        data = {"agents": []}
    agents = data.get("agents", [])
    if not isinstance(agents, list):
        agents = []

    trading = None
    for item in agents:
        if isinstance(item, dict) and item.get("name") == "trading":
            trading = item
            break
    if trading is None:
        trading = {}
        agents.insert(0, trading)

    open_position = _position_from_dict(state.get("open_position"))
    current_task = "Watch the XAU proxy feed and keep the paper trader aligned with the live signal."
    if open_position:
        current_task = f"Managing open {open_position.side} paper position at {open_position.entry_price:,.2f}."

    signal_state = monitor_state.get("signal_state", monitor_state.get("watch_signal"))
    signal_action = monitor_state.get("signal_action", monitor_state.get("watch_action"))

    trading.update(
        {
            "name": "trading",
            "role": "execution",
            "status": "trading" if open_position else "monitoring",
            "purpose": "Monitor XAU around the clock, wait for a clean entry, and keep risk inside guardrails.",
            "last_update": monitor_state.get("updated_at", "just now"),
            "notes": "Paper-first, withdrawals disabled, and every change stays auditable.",
            "current_task": current_task,
            "next_action": "Hold the current position" if open_position else "Watch for the next clean entry.",
            "health": "active" if state.get("status") == "running" else "watching",
            "progress": min(99, 70 + int(state.get("closed_trade_count", 0) or 0)),
            "watch_asset": monitor_state.get("asset", DEFAULT_ASSET),
            "watch_symbol": monitor_state.get("symbol", DEFAULT_SYMBOL),
            "watch_price": monitor_state.get("price"),
            "watch_change_pct": monitor_state.get("change_pct"),
            "watch_signal": signal_state,
            "watch_action": signal_action,
            "watch_updated_at": monitor_state.get("updated_at"),
            "performance_summary": summary,
        }
    )
    data["agents"] = agents
    _write_json(AGENTS_PATH, data)


def _build_summary(state: dict[str, Any]) -> str:
    open_position = _position_from_dict(state.get("open_position"))
    signal_state = str(state.get("signal_state", "unknown"))
    signal_action = str(state.get("signal_action", "watch"))
    if open_position:
        return (
            f"Closed trades: {state.get('closed_trade_count', 0)} | "
            f"Realized PnL: ${state.get('realized_pnl', 0.0):,.2f} | "
            f"Open position: {open_position.side} @ {open_position.entry_price:,.2f} | "
            f"SL {open_position.stop_loss:,.2f} | TP {open_position.take_profit:,.2f} | "
            f"Signal: {signal_state} / {signal_action}"
        )
    return (
        f"Closed trades: {state.get('closed_trade_count', 0)} | "
        f"Realized PnL: ${state.get('realized_pnl', 0.0):,.2f} | Open position: none | "
        f"Signal: {signal_state} / {signal_action}"
    )


def run_once(*, symbol: str, asset: str, timeout: int) -> dict[str, Any]:
    previous_state = _load_state()
    monitor_state = load_trading_monitor_state()
    history = _coerce_history(monitor_state)
    if not history and isinstance(previous_state.get("history"), list):
        history = _coerce_history(previous_state)

    snapshot = fetch_gold_price_snapshot(symbol=symbol, asset=asset, timeout=timeout)
    combined_history = history + snapshot.history
    decision = evaluate_market(combined_history)

    cash = float(previous_state.get("cash", INITIAL_CASH) or INITIAL_CASH)
    realized_pnl = float(previous_state.get("realized_pnl", 0.0) or 0.0)
    closed_trade_count = int(previous_state.get("closed_trade_count", 0) or 0)
    trade_count = int(previous_state.get("trade_count", 0) or 0)
    open_position = _position_from_dict(previous_state.get("open_position"))
    fee_rate = FEE_BPS / 10_000.0
    slippage_rate = SLIPPAGE_BPS / 10_000.0
    last_event = "hold"
    exit_reason = None

    desired_side = _signal_side(decision.state, decision.confidence, decision.risk_state)
    current_side = 0 if open_position is None else (1 if open_position.side == "long" else -1)
    price = snapshot.price

    if open_position is not None:
        trigger_reason = _trade_trigger_reason(open_position, price)
        if trigger_reason is not None:
            exit_reason = trigger_reason
        elif desired_side == 0 or desired_side != current_side:
            exit_reason = "signal_flip"

    if open_position is not None and exit_reason is not None:
        if exit_reason == "take_profit":
            exit_price = open_position.take_profit
        elif exit_reason == "stop_loss":
            exit_price = open_position.stop_loss
        else:
            exit_price = _exit_fill(price, current_side, slippage_rate)

        pnl = current_side * (exit_price - open_position.entry_price) * open_position.quantity
        realized_pnl += pnl
        cash += pnl
        cash -= abs(exit_price * open_position.quantity) * fee_rate
        closed_trade_count += 1
        trade_count += 1
        _append_jsonl(
            LEDGER_PATH,
            {
                "timestamp": snapshot.timestamp,
                "event": "close",
                "asset": asset,
                "symbol": symbol,
                "side": open_position.side,
                "entry_price": open_position.entry_price,
                "exit_price": exit_price,
                "stop_loss": open_position.stop_loss,
                "take_profit": open_position.take_profit,
                "exit_reason": exit_reason,
                "strategy": open_position.strategy,
                "quantity": open_position.quantity,
                "pnl": pnl,
                "decision_state": decision.state,
                "decision_action": decision.action,
                "decision_confidence": round(decision.confidence, 2),
                "reason": decision.reason,
            },
        )
        open_position = None
        last_event = f"closed {current_side:+d} position via {exit_reason} for {pnl:+.2f}"
        current_side = 0

    if open_position is None and desired_side != 0:
        plan = _build_trade_plan(price, decision.state, decision.confidence, decision.risk_state, combined_history)
        if plan is not None:
            entry_price = _entry_fill(plan.entry_price, desired_side, slippage_rate)
            equity_for_size = max(cash, INITIAL_CASH * 0.1)
            notional = equity_for_size * POSITION_FRACTION
            quantity = 0.0 if entry_price == 0 else notional / entry_price
            if quantity > 0:
                cash -= notional * fee_rate
                open_position = PaperPosition(
                    side=plan.side,
                    entry_price=entry_price,
                    quantity=quantity,
                    opened_at=snapshot.timestamp,
                    signal_state=decision.state,
                    signal_action=decision.action,
                    signal_confidence=round(decision.confidence, 2),
                    reason=plan.reason,
                    stop_loss=plan.stop_loss,
                    take_profit=plan.take_profit,
                    strategy=plan.strategy,
                )
                trade_count += 1
                _append_jsonl(
                    LEDGER_PATH,
                    {
                        "timestamp": snapshot.timestamp,
                        "event": "open",
                        "asset": asset,
                        "symbol": symbol,
                        "side": open_position.side,
                        "entry_price": entry_price,
                        "stop_loss": open_position.stop_loss,
                        "take_profit": open_position.take_profit,
                        "reward_risk": plan.reward_risk,
                        "strategy": open_position.strategy,
                        "quantity": quantity,
                        "decision_state": decision.state,
                        "decision_action": decision.action,
                        "decision_confidence": round(decision.confidence, 2),
                        "reason": plan.reason,
                    },
                )
                last_event = (
                    f"opened {open_position.side} @ {entry_price:,.2f} | "
                    f"SL {open_position.stop_loss:,.2f} | TP {open_position.take_profit:,.2f}"
                )

    unrealized_pnl = 0.0
    if open_position is not None:
        direction = 1.0 if open_position.side == "long" else -1.0
        unrealized_pnl = direction * (price - open_position.entry_price) * open_position.quantity

    equity = cash + unrealized_pnl
    summary = _build_summary(
        {
            "closed_trade_count": closed_trade_count,
            "realized_pnl": realized_pnl,
            "open_position": _position_to_dict(open_position) if open_position else None,
            "signal_state": decision.state,
            "signal_action": decision.action,
        }
    )
    state = {
        "asset": asset,
        "symbol": symbol,
        "source": snapshot.source,
        "status": "running",
        "updated_at": snapshot.timestamp,
        "price": snapshot.price,
        "previous_close": snapshot.previous_close,
        "change_pct": snapshot.change_pct,
        "signal_state": decision.state,
        "signal_action": decision.action,
        "signal_confidence": round(decision.confidence, 2),
        "signal_reason": decision.reason,
        "risk_state": decision.risk_state,
        "cash": round(cash, 2),
        "equity": round(equity, 2),
        "realized_pnl": round(realized_pnl, 2),
        "unrealized_pnl": round(unrealized_pnl, 2),
        "closed_trade_count": closed_trade_count,
        "trade_count": trade_count,
        "open_position": _position_to_dict(open_position) if open_position else None,
        "history": combined_history[-120:],
        "next_check_seconds": 60,
        "last_event": last_event,
        "last_error": None,
    }
    _save_state(state)
    _sync_agent_registry(state, summary, state)
    print(f"paper trader | {last_event} | {summary} | equity=${equity:,.2f}")
    return state


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the long-lived XAU paper trader loop.")
    parser.add_argument("--symbol", default=DEFAULT_SYMBOL)
    parser.add_argument("--asset", default=DEFAULT_ASSET)
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--interval", type=int, default=60)
    parser.add_argument("--once", action="store_true", help="Run a single cycle and exit.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.once:
        run_once(symbol=args.symbol, asset=args.asset, timeout=args.timeout)
        return 0

    print(f"Starting paper trader for {args.asset}/{args.symbol} every {args.interval}s")
    while True:
        try:
            run_once(symbol=args.symbol, asset=args.asset, timeout=args.timeout)
        except KeyboardInterrupt:
            print("Stopping paper trader.")
            return 0
        except Exception as exc:  # pragma: no cover - runtime guard
            payload = _load_state()
            payload.update(
                {
                    "asset": args.asset,
                    "symbol": args.symbol,
                    "status": "error",
                    "last_error": str(exc),
                    "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
            )
            _save_state(payload)
            print(f"paper trader error: {exc}", file=sys.stderr)
        time.sleep(max(5, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
