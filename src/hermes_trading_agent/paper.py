from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from statistics import fmean, pstdev
from typing import Iterable

from .data import MarketData


@dataclass(frozen=True)
class Trade:
    side: str  # "long" or "short"
    entry_price: float
    exit_price: float
    quantity: float

    @property
    def pnl(self) -> float:
        direction = 1.0 if self.side == "long" else -1.0
        return direction * (self.exit_price - self.entry_price) * self.quantity

    @property
    def return_pct(self) -> float:
        notional = abs(self.entry_price * self.quantity)
        return 0.0 if notional == 0 else self.pnl / notional


@dataclass(frozen=True)
class SimulationResult:
    trades: list[Trade]
    equity_curve: list[float]
    returns: list[float]
    final_equity: float
    max_drawdown: float
    sharpe: float
    total_return: float


def _sign(value: float) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def compute_max_drawdown(equity_curve: Iterable[float]) -> float:
    peak = None
    max_dd = 0.0
    for equity in equity_curve:
        if peak is None or equity > peak:
            peak = equity
        if peak:
            dd = (peak - equity) / peak
            if dd > max_dd:
                max_dd = dd
    return max_dd


def compute_sharpe(returns: Iterable[float]) -> float:
    data = list(returns)
    if len(data) < 2:
        return 0.0
    stdev = pstdev(data)
    if stdev == 0:
        return 0.0
    return fmean(data) / stdev * sqrt(len(data))


def run_paper_backtest(
    prices: list[float],
    signals: list[float],
    *,
    initial_cash: float = 10_000.0,
    position_fraction: float = 0.10,
    fee_bps: float = 0.0,
    slippage_bps: float = 0.0,
) -> SimulationResult:
    if len(prices) != len(signals):
        raise ValueError("prices and signals must have the same length")
    if not prices:
        raise ValueError("prices cannot be empty")
    if fee_bps < 0:
        raise ValueError("fee_bps cannot be negative")
    if slippage_bps < 0:
        raise ValueError("slippage_bps cannot be negative")

    fee_rate = fee_bps / 10_000.0
    slippage_rate = slippage_bps / 10_000.0

    def entry_fill(price: float, side: int) -> float:
        if side > 0:
            return price * (1.0 + slippage_rate)
        return price * (1.0 - slippage_rate)

    def exit_fill(price: float, side: int) -> float:
        if side > 0:
            return price * (1.0 - slippage_rate)
        return price * (1.0 + slippage_rate)

    cash = initial_cash
    position_qty = 0.0
    position_side = 0
    entry_price = 0.0
    equity_curve: list[float] = []
    returns: list[float] = []
    trades: list[Trade] = []
    previous_equity = initial_cash

    for price, signal in zip(prices, signals):
        desired_side = _sign(signal)

        if position_side != 0 and desired_side != position_side:
            exit_price = exit_fill(price, position_side)
            trade = Trade(
                side="long" if position_side > 0 else "short",
                entry_price=entry_price,
                exit_price=exit_price,
                quantity=position_qty,
            )
            cash += trade.pnl
            cash -= abs(exit_price * position_qty) * fee_rate
            trades.append(trade)
            position_qty = 0.0
            position_side = 0
            entry_price = 0.0

        if position_side == 0 and desired_side != 0:
            fill_price = entry_fill(price, desired_side)
            notional = cash * position_fraction
            position_qty = 0.0 if fill_price == 0 else notional / fill_price
            position_side = desired_side
            entry_price = fill_price
            cash -= notional * fee_rate

        mark_to_market = 0.0
        if position_side != 0:
            direction = 1.0 if position_side > 0 else -1.0
            mark_to_market = direction * (price - entry_price) * position_qty

        equity = cash + mark_to_market
        equity_curve.append(equity)
        returns.append(0.0 if previous_equity == 0 else (equity - previous_equity) / previous_equity)
        previous_equity = equity

    if position_side != 0:
        exit_price = exit_fill(prices[-1], position_side)
        trade = Trade(
            side="long" if position_side > 0 else "short",
            entry_price=entry_price,
            exit_price=exit_price,
            quantity=position_qty,
        )
        cash += trade.pnl
        cash -= abs(exit_price * position_qty) * fee_rate
        trades.append(trade)
        equity_curve[-1] = cash
        returns[-1] = 0.0 if len(equity_curve) < 2 else (equity_curve[-1] - equity_curve[-2]) / equity_curve[-2]

    final_equity = equity_curve[-1]
    total_return = 0.0 if initial_cash == 0 else (final_equity - initial_cash) / initial_cash
    return SimulationResult(
        trades=trades,
        equity_curve=equity_curve,
        returns=returns,
        final_equity=final_equity,
        max_drawdown=compute_max_drawdown(equity_curve),
        sharpe=compute_sharpe(returns),
        total_return=total_return,
    )


def run_paper_backtest_from_market_data(
    market_data: MarketData,
    **kwargs,
) -> SimulationResult:
    return run_paper_backtest(market_data.prices, market_data.signals, **kwargs)


def reflection_recommendation(result: SimulationResult, *, target_drawdown: float, target_sharpe: float) -> str:
    if result.max_drawdown > target_drawdown:
        return "Reduce position_fraction by 20% to lower drawdown."
    if result.sharpe < target_sharpe:
        return "Tighten the entry filter so only higher-conviction signals are traded."
    if result.total_return <= 0:
        return "Increase signal selectivity before raising position size."
    return "Keep the current setup and collect another sample of trades before changing one variable."
