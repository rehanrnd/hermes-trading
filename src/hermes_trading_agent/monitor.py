from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean, pstdev
import json
import os
import tempfile
from typing import Any
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen

DEFAULT_ASSET = "XAU"
DEFAULT_SYMBOL = "GC=F"
DEFAULT_SOURCE = "yahoo_finance"
DEFAULT_STATE_PATH = Path("state/xau_monitor.json")


@dataclass(frozen=True)
class MarketSnapshot:
    asset: str
    symbol: str
    source: str
    timestamp: str
    price: float
    previous_close: float | None
    change_pct: float | None
    history: list[float]
    source_label: str


@dataclass(frozen=True)
class SignalDecision:
    state: str
    action: str
    confidence: float
    reason: str
    risk_state: str


@dataclass(frozen=True)
class TradingMonitorState:
    asset: str
    symbol: str
    source: str
    source_label: str
    updated_at: str
    price: float
    previous_close: float | None
    change_pct: float | None
    signal_state: str
    signal_action: str
    signal_confidence: float
    signal_reason: str
    risk_state: str
    status: str
    history: list[float]
    sample_count: int
    next_check_seconds: int
    last_error: str | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load_json_file(path: str | Path) -> dict[str, Any] | None:
    json_path = Path(path)
    if not json_path.exists():
        return None
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if isinstance(data, dict):
        return data
    return None


def load_trading_monitor_state(path: str | Path = DEFAULT_STATE_PATH) -> dict[str, Any] | None:
    return _load_json_file(path)


def save_trading_monitor_state(state: TradingMonitorState, path: str | Path = DEFAULT_STATE_PATH) -> None:
    json_path = Path(path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "asset": state.asset,
        "symbol": state.symbol,
        "source": state.source,
        "source_label": state.source_label,
        "updated_at": state.updated_at,
        "price": state.price,
        "previous_close": state.previous_close,
        "change_pct": state.change_pct,
        "signal_state": state.signal_state,
        "signal_action": state.signal_action,
        "signal_confidence": state.signal_confidence,
        "signal_reason": state.signal_reason,
        "risk_state": state.risk_state,
        "status": state.status,
        "history": state.history,
        "sample_count": state.sample_count,
        "next_check_seconds": state.next_check_seconds,
        "last_error": state.last_error,
    }
    payload_text = json.dumps(payload, indent=2, sort_keys=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=json_path.parent, delete=False) as tmp:
        tmp.write(payload_text)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    tmp_path.replace(json_path)


def _coerce_history(values: list[float] | tuple[float, ...] | None) -> list[float]:
    if not values:
        return []
    history: list[float] = []
    for value in values:
        try:
            history.append(float(value))
        except (TypeError, ValueError):
            continue
    return history


def _trim_history(history: list[float], limit: int) -> list[float]:
    if limit <= 0:
        return history
    return history[-limit:]


def _gold_symbol_label(symbol: str) -> str:
    if symbol.upper() == "GC=F":
        return "Gold futures proxy"
    return symbol


def fetch_gold_price_snapshot(
    *,
    symbol: str = DEFAULT_SYMBOL,
    asset: str = DEFAULT_ASSET,
    timeout: int = 15,
) -> MarketSnapshot:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1d&interval=5m&includePrePost=false"
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        raise RuntimeError(f"failed to fetch price data for {symbol}: {exc}") from exc

    chart = payload.get("chart", {})
    result = (chart.get("result") or [{}])[0]
    meta = result.get("meta", {})
    indicators = result.get("indicators", {})
    quote = (indicators.get("quote") or [{}])[0]
    close_series = [float(value) for value in quote.get("close", []) if value is not None]

    price = meta.get("regularMarketPrice")
    if price is None and close_series:
        price = close_series[-1]
    if price is None:
        raise RuntimeError(f"no market price found for {symbol}")

    previous_close = meta.get("previousClose")
    if previous_close is None and len(close_series) >= 2:
        previous_close = close_series[-2]

    change_pct = None
    if previous_close:
        change_pct = ((float(price) - float(previous_close)) / float(previous_close)) * 100.0

    history = close_series[-120:] if close_series else [float(price)]
    return MarketSnapshot(
        asset=asset,
        symbol=symbol,
        source=DEFAULT_SOURCE,
        timestamp=utc_now(),
        price=float(price),
        previous_close=float(previous_close) if previous_close is not None else None,
        change_pct=change_pct,
        history=history,
        source_label=_gold_symbol_label(symbol),
    )


def evaluate_market(history: list[float]) -> SignalDecision:
    cleaned = _coerce_history(history)
    if len(cleaned) < 4:
        return SignalDecision(
            state="warming_up",
            action="watch",
            confidence=20.0,
            reason="Need more samples before taking a directional stance.",
            risk_state="neutral",
        )

    last = cleaned[-1]
    prev = cleaned[-2]
    short_base = cleaned[-4]
    long_base = cleaned[-8] if len(cleaned) >= 8 else cleaned[0]
    short_return = 0.0 if prev == 0 else (last - prev) / prev
    short_trend = 0.0 if short_base == 0 else (last - short_base) / short_base
    long_trend = 0.0 if long_base == 0 else (last - long_base) / long_base

    window = cleaned[-8:]
    returns = []
    for first, second in zip(window, window[1:]):
        if first != 0:
            returns.append((second - first) / first)
    volatility = pstdev(returns) if len(returns) >= 2 else 0.0
    average_return = fmean(returns) if returns else 0.0
    range_pct = 0.0 if min(window) == 0 else (max(window) - min(window)) / min(window)

    if volatility > 0.0105 and abs(short_trend) < 0.002:
        return SignalDecision(
            state="choppy",
            action="stand aside",
            confidence=52.0,
            reason="Volatility is elevated without a clean direction, so the agent should wait.",
            risk_state="high",
        )

    bullish_score = (short_return * 10_000) + (short_trend * 8_000) + (long_trend * 6_000) + (average_return * 7_000)
    bearish_score = (-short_return * 10_000) + (-short_trend * 8_000) + (-long_trend * 6_000) + (-average_return * 7_000)
    momentum_strength = max(abs(short_trend), abs(long_trend), abs(average_return)) * 10_000

    if bullish_score > 18 and short_return > 0 and long_trend > -0.001:
        confidence = min(96.0, 58.0 + bullish_score + momentum_strength * 0.4)
        return SignalDecision(
            state="bullish",
            action="prepare long",
            confidence=confidence,
            reason="Momentum and trend are aligned upward, so the next clean pullback is worth watching.",
            risk_state="normal" if volatility < 0.0075 and range_pct < 0.012 else "watch",
        )

    if bearish_score > 18 and short_return < 0 and long_trend < 0.001:
        confidence = min(96.0, 58.0 + bearish_score + momentum_strength * 0.4)
        return SignalDecision(
            state="bearish",
            action="prepare short",
            confidence=confidence,
            reason="Momentum and trend are aligned downward, so the next clean rally is worth watching.",
            risk_state="normal" if volatility < 0.0075 and range_pct < 0.012 else "watch",
        )

    confidence = max(24.0, min(68.0, 42.0 + abs(short_trend) * 3_000 + abs(long_trend) * 2_000))
    if short_return > 0:
        return SignalDecision(
            state="watch_long",
            action="wait for pullback",
            confidence=confidence,
            reason="Price is leaning upward, but the setup still needs a cleaner entry trigger.",
            risk_state="watch" if volatility < 0.009 else "high",
        )
    if short_return < 0:
        return SignalDecision(
            state="watch_short",
            action="wait for bounce",
            confidence=confidence,
            reason="Price is leaning downward, but the setup still needs a cleaner entry trigger.",
            risk_state="watch" if volatility < 0.009 else "high",
        )

    return SignalDecision(
        state="flat",
        action="wait",
        confidence=confidence,
        reason="The market is balanced, so the agent should keep monitoring and avoid forcing an entry.",
        risk_state="normal" if volatility < 0.009 else "watch",
    )


def build_trading_monitor_state(
    snapshot: MarketSnapshot,
    decision: SignalDecision,
    *,
    next_check_seconds: int = 60,
    status: str = "monitoring",
    last_error: str | None = None,
) -> TradingMonitorState:
    return TradingMonitorState(
        asset=snapshot.asset,
        symbol=snapshot.symbol,
        source=snapshot.source,
        source_label=snapshot.source_label,
        updated_at=snapshot.timestamp,
        price=snapshot.price,
        previous_close=snapshot.previous_close,
        change_pct=snapshot.change_pct,
        signal_state=decision.state,
        signal_action=decision.action,
        signal_confidence=round(decision.confidence, 2),
        signal_reason=decision.reason,
        risk_state=decision.risk_state,
        status=status,
        history=_trim_history(snapshot.history, 120),
        sample_count=len(snapshot.history),
        next_check_seconds=next_check_seconds,
        last_error=last_error,
    )


def run_monitor_cycle(
    *,
    symbol: str = DEFAULT_SYMBOL,
    asset: str = DEFAULT_ASSET,
    history: list[float] | None = None,
    next_check_seconds: int = 60,
    timeout: int = 15,
    last_error: str | None = None,
) -> TradingMonitorState:
    previous_history = _coerce_history(history)
    snapshot = fetch_gold_price_snapshot(symbol=symbol, asset=asset, timeout=timeout)
    combined_history = _trim_history(previous_history + snapshot.history, 120)
    enriched_snapshot = MarketSnapshot(
        asset=snapshot.asset,
        symbol=snapshot.symbol,
        source=snapshot.source,
        timestamp=snapshot.timestamp,
        price=snapshot.price,
        previous_close=snapshot.previous_close,
        change_pct=snapshot.change_pct,
        history=combined_history,
        source_label=snapshot.source_label,
    )
    decision = evaluate_market(combined_history)
    return build_trading_monitor_state(
        enriched_snapshot,
        decision,
        next_check_seconds=next_check_seconds,
        last_error=last_error,
    )


def format_trading_monitor_state(state: TradingMonitorState) -> str:
    change = "n/a"
    if state.change_pct is not None:
        sign = "+" if state.change_pct >= 0 else "-"
        change = f"{sign}{abs(state.change_pct):.2f}%"

    lines = [
        f"XAU monitor [{state.symbol}]",
        f"- updated_at: {state.updated_at}",
        f"- price: {state.price:,.2f}",
        f"- change: {change}",
        f"- signal: {state.signal_state} / {state.signal_action}",
        f"- confidence: {state.signal_confidence:.2f}",
        f"- risk_state: {state.risk_state}",
        f"- status: {state.status}",
        f"- sample_count: {state.sample_count}",
        f"- next_check_seconds: {state.next_check_seconds}",
    ]
    if state.last_error:
        lines.append(f"- last_error: {state.last_error}")
    lines.append(f"- reason: {state.signal_reason}")
    return "\n".join(lines)
