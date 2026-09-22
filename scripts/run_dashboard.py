from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hermes_trading_agent.agents import load_agents  # noqa: E402
from hermes_trading_agent.dashboard import render_dashboard  # noqa: E402
from hermes_trading_agent.goal import load_goal  # noqa: E402
from hermes_trading_agent.monitor import load_trading_monitor_state  # noqa: E402
from hermes_trading_agent.paper import (  # noqa: E402
    SimulationResult,
    Trade,
    compute_max_drawdown,
    compute_sharpe,
)
from hermes_trading_agent.summary import build_backtest_summary  # noqa: E402

STATE_PATH = ROOT / "state" / "paper_trader.json"
LEDGER_PATH = ROOT / "state" / "paper_trades.jsonl"
INITIAL_CASH = 10_000.0


def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _load_jsonl(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    rows: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _build_live_paper_result() -> tuple[dict[str, object], SimulationResult] | None:
    state = _load_json(STATE_PATH, {})
    if not isinstance(state, dict) or not state:
        return None

    closed_trades: list[Trade] = []
    equity_curve: list[float] = [INITIAL_CASH]
    current_equity = INITIAL_CASH
    close_rows: list[dict[str, object]] = []

    for row in _load_jsonl(LEDGER_PATH):
        if row.get("event") != "close":
            continue
        close_rows.append(row)
        try:
            trade = Trade(
                side=str(row["side"]),
                entry_price=float(row["entry_price"]),
                exit_price=float(row["exit_price"]),
                quantity=float(row["quantity"]),
            )
        except (KeyError, TypeError, ValueError):
            continue
        closed_trades.append(trade)
        try:
            current_equity += float(row.get("pnl", trade.pnl))
        except (TypeError, ValueError):
            current_equity += trade.pnl
        equity_curve.append(current_equity)

    try:
        final_equity = float(state.get("equity", current_equity))
    except (TypeError, ValueError):
        final_equity = current_equity
    if not equity_curve or equity_curve[-1] != final_equity:
        equity_curve.append(final_equity)

    returns: list[float] = []
    previous = INITIAL_CASH
    for equity in equity_curve:
        returns.append(0.0 if previous == 0 else (equity - previous) / previous)
        previous = equity

    total_return = 0.0 if INITIAL_CASH == 0 else (final_equity - INITIAL_CASH) / INITIAL_CASH
    result = SimulationResult(
        trades=closed_trades,
        equity_curve=equity_curve,
        returns=returns,
        final_equity=final_equity,
        max_drawdown=compute_max_drawdown(equity_curve),
        sharpe=compute_sharpe(returns),
        total_return=total_return,
    )

    close_count = len(close_rows)
    win_count = 0
    loss_count = 0
    pnl_sum = 0.0
    last_close_reason = "none"
    for row in close_rows:
        try:
            pnl = float(row.get("pnl", 0.0) or 0.0)
        except (TypeError, ValueError):
            pnl = 0.0
        pnl_sum += pnl
        if pnl > 0:
            win_count += 1
        elif pnl < 0:
            loss_count += 1
        last_close_reason = str(row.get("exit_reason") or row.get("decision_action") or row.get("reason") or last_close_reason)

    daily_marker = str(state.get("updated_at", ""))[:10]
    daily_close_count = 0
    daily_pnl = 0.0
    for row in close_rows:
        timestamp = str(row.get("timestamp", ""))
        if daily_marker and timestamp[:10] != daily_marker:
            continue
        daily_close_count += 1
        try:
            daily_pnl += float(row.get("pnl", 0.0) or 0.0)
        except (TypeError, ValueError):
            continue

    win_rate = 0.0 if close_count == 0 else (win_count / close_count) * 100.0
    avg_pnl = 0.0 if close_count == 0 else pnl_sum / close_count
    recommendation = "Collect more trades before changing risk settings."
    if result.max_drawdown > 0.02:
        recommendation = "Trim position size until drawdown settles below 2%."
    elif result.sharpe < 0.0:
        recommendation = "Tighten the entry filter so only higher-conviction signals are traded."
    elif result.total_return <= 0:
        recommendation = "Increase signal selectivity before raising position size."
    else:
        recommendation = "Keep the current setup and collect another sample of trades before changing one variable."

    summary = {
        "source": "live paper trader",
        "recommendation": recommendation,
        "daily_metric": f"{win_rate:.0f}% win rate",
        "daily_focus": f"{daily_close_count} closes today · {daily_pnl:+.2f} PnL · avg {avg_pnl:+.2f} per trade · last exit {last_close_reason}",
        "closed_trades": close_count,
        "win_rate": win_rate,
        "daily_close_count": daily_close_count,
        "daily_pnl": daily_pnl,
        "avg_pnl": avg_pnl,
        "last_close_reason": last_close_reason,
        "updated_at": state.get("updated_at"),
        "signal_state": state.get("signal_state"),
        "signal_action": state.get("signal_action"),
        "signal_confidence": state.get("signal_confidence"),
        "trade_count": state.get("trade_count"),
        "realized_pnl": state.get("realized_pnl"),
        "equity": final_equity,
    }
    return summary, result


def build_latest_report():
    goal = load_goal()
    live = _build_live_paper_result()
    if live is None:
        from hermes_trading_agent.agent_loop import run_reflection_loop  # noqa: WPS433,E402

        prices = [100.0, 101.0, 102.0, 101.5, 103.0, 104.0, 103.0, 105.0]
        signals = [1, 1, 1, 0, -1, -1, 0, 1]
        report = run_reflection_loop(goal, prices, signals)
        summary = build_backtest_summary(goal, report.result, source="synthetic sample")
        return goal, report, summary

    live_summary, result = live
    summary = build_backtest_summary(goal, result, source="live paper trader")
    summary.update(live_summary)
    return goal, type("Report", (), {"result": result})(), summary


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in {"/health", "/healthz"}:
            payload = b"ok"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        if self.path not in {"/", "/index.html"}:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")
            return

        goal, report, summary = build_latest_report()
        html = render_dashboard(goal, load_agents(), report.result, summary=summary, monitor_state=load_trading_monitor_state()).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        self.wfile.write(html)

    def log_message(self, format, *args):  # noqa: A003
        return


def main(host: str = "0.0.0.0", port: int | None = None) -> None:
    if port is None:
        port = int(os.getenv("PORT", "8787"))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Serving Hermes Trading Dashboard at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
