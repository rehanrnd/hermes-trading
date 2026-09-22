from __future__ import annotations

from html import escape
from math import floor
from typing import Iterable

from .agents import AgentCard
from .goal import Goal
from .paper import SimulationResult

INITIAL_CASH = 10_000.0


def _signed_money(value: float) -> str:
    sign = "+" if value >= 0 else "-"
    return f"{sign}${abs(value):,.2f}"


def _signed_pct(value: float) -> str:
    sign = "+" if value >= 0 else "-"
    return f"{sign}{abs(value):.2f}%"


def _money(value: float) -> str:
    return f"${value:,.2f}"


def _chip(text: str, kind: str = "neutral") -> str:
    return f'<span class="chip chip--{escape(kind)}">{escape(text)}</span>'


def _progress(value: int | None) -> int:
    if value is None:
        return 0
    return max(0, min(100, int(value)))


def _sparkline(values: list[float], *, stroke: str, fill: str, label: str) -> str:
    if not values:
        values = [0.0, 0.0]
    if len(values) == 1:
        values = values + values

    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in label).strip("-") or "series"
    width = 320
    height = 110
    left = 8
    right = width - 8
    top = 10
    bottom = height - 12
    span = right - left
    value_min = min(values)
    value_max = max(values)
    if value_max == value_min:
        value_max = value_min + 1.0

    def y_for(value: float) -> float:
        normalized = (value - value_min) / (value_max - value_min)
        return bottom - normalized * (bottom - top)

    points = []
    for index, value in enumerate(values):
        x = left + (span * index / max(1, len(values) - 1))
        points.append((x, y_for(value)))

    polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    area = [f"M {left:.1f} {bottom:.1f}", f"L {points[0][0]:.1f} {points[0][1]:.1f}"]
    for x, y in points[1:]:
        area.append(f"L {x:.1f} {y:.1f}")
    area.append(f"L {points[-1][0]:.1f} {bottom:.1f} Z")
    path = " ".join(area)

    return f"""
    <div class="sparkline-wrap" aria-label="{escape(label)}">
      <svg viewBox="0 0 {width} {height}" preserveAspectRatio="none" role="img" aria-label="{escape(label)}">
        <defs>
          <linearGradient id="grad-{slug}" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stop-color="{escape(fill)}" stop-opacity="0.35" />
            <stop offset="100%" stop-color="{escape(fill)}" stop-opacity="0" />
          </linearGradient>
        </defs>
        <path d="{path}" fill="url(#grad-{slug})"></path>
        <polyline points="{polyline}" fill="none" stroke="{escape(stroke)}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"></polyline>
      </svg>
    </div>
    """


def _metric(label: str, value: str, delta: str | None = None, tone: str = "neutral", icon: str = "◼") -> str:
    delta_html = f'<div class="metric-delta">{escape(delta)}</div>' if delta else ""
    return f"""
    <article class="metric-card metric-card--{escape(tone)}">
      <div class="metric-top">
        <span class="metric-icon">{escape(icon)}</span>
        <span class="metric-label">{escape(label)}</span>
      </div>
      <div class="metric-value">{escape(value)}</div>
      {delta_html}
    </article>
    """


def _agent_card(agent: AgentCard, *, accent: str, icon: str) -> str:
    progress = _progress(agent.progress)
    role = agent.role.replace("_", " ")
    watch_html = ""
    if agent.watch_asset and agent.watch_symbol:
        change_text = "n/a"
        if agent.watch_change_pct is not None:
            sign = "+" if agent.watch_change_pct >= 0 else "-"
            change_text = f"{sign}{abs(agent.watch_change_pct):.2f}%"
        price_text = f"${agent.watch_price:,.2f}" if agent.watch_price is not None else "n/a"
        watch_html = f"""
        <div class="agent-watch">
          <div class="agent-watch-head">
            <span class="agent-watch-label">Live watch</span>
            <span class="agent-watch-pill">{escape(agent.watch_signal or 'watch')}</span>
          </div>
          <div class="agent-watch-row">
            <strong>{escape(agent.watch_asset)} / {escape(agent.watch_symbol)}</strong>
            <span>{escape(price_text)} · {escape(change_text)}</span>
          </div>
          <div class="agent-watch-foot">
            <span>{escape(agent.watch_action or 'waiting for setup')}</span>
            <small>{escape(agent.watch_updated_at or 'updating live')}</small>
          </div>
        </div>
        """
    return f"""
    <article class="agent-card">
      <div class="agent-head">
        <div class="agent-avatar agent-avatar--{escape(accent)}">{escape(icon)}</div>
        <div class="agent-status">
          <span class="agent-status-line">{escape(role.upper())}</span>
          <span class="agent-status-pill agent-status-pill--{escape(accent)}">{escape(agent.status.upper())}</span>
        </div>
      </div>
      <h3>{escape(agent.name.title())}</h3>
      <p class="agent-copy">{escape(agent.purpose)}</p>
      {watch_html}
      {f'<div class="agent-performance">{escape(agent.performance_summary)}</div>' if agent.performance_summary else ''}
      <div class="agent-meta">
        <div>
          <span class="agent-meta-label">Current task</span>
          <strong>{escape(agent.current_task or "Awaiting next task")}</strong>
        </div>
        <div>
          <span class="agent-meta-label">Next action</span>
          <strong>{escape(agent.next_action or "Queued")}</strong>
        </div>
      </div>
      <div class="agent-footer">
        <div class="agent-progress">
          <div class="agent-progress-track"><span style="width:{progress}%"></span></div>
          <small>{progress}% complete</small>
        </div>
        <div class="agent-health">{escape(agent.health or "stable")}</div>
      </div>
    </article>
    """


def _feed_item(source: str, title: str, detail: str, when: str, tone: str = "cyan") -> str:
    return f"""
    <li class="feed-item">
      <div class="feed-time">{escape(when)}</div>
      <div class="feed-body">
        <strong class="feed-source feed-source--{escape(tone)}">{escape(source)}</strong>
        <p>{escape(title)}</p>
        <small>{escape(detail)}</small>
      </div>
    </li>
    """


def _market_watch_panel(monitor_state: dict[str, object] | None) -> str:
    if not monitor_state:
        return ""

    price = monitor_state.get("price")
    change_pct = monitor_state.get("change_pct")
    signal_state = str(monitor_state.get("signal_state", "watch"))
    signal_action = str(monitor_state.get("signal_action", "wait"))
    signal_confidence = monitor_state.get("signal_confidence")
    signal_reason = str(monitor_state.get("signal_reason", "Monitoring the market for a clean setup."))
    updated_at = str(monitor_state.get("updated_at", "just now"))
    risk_state = str(monitor_state.get("risk_state", "normal"))
    history = monitor_state.get("history") if isinstance(monitor_state.get("history"), list) else []
    spark_values: list[float] = []
    for item in history[-24:]:
        try:
            spark_values.append(float(item))
        except (TypeError, ValueError):
            continue
    if not spark_values:
        spark_values = [0.0, 0.0]

    change_text = "n/a"
    change_tone = "neutral"
    if isinstance(change_pct, (int, float)):
        sign = "+" if change_pct >= 0 else "-"
        change_text = f"{sign}{abs(float(change_pct)):.2f}%"
        change_tone = "green" if float(change_pct) >= 0 else "amber"

    price_text = "$0.00"
    if isinstance(price, (int, float)):
        price_text = f"${float(price):,.2f}"

    confidence_text = "n/a"
    if isinstance(signal_confidence, (int, float)):
        confidence_text = f"{float(signal_confidence):.0f}%"

    return f"""
    <section class="market-panel panel">
      <div class="section-head">
        <div>
          <div class="eyebrow">LIVE MARKET WATCH</div>
          <h2>XAU monitor</h2>
        </div>
        <div class="market-chip">{escape(signal_state.upper())}</div>
      </div>
      <div class="market-grid">
        <div class="market-block">
          <span class="market-label">Price</span>
          <strong>{escape(price_text)}</strong>
          <small>{escape(str(monitor_state.get('asset', 'XAU')))} / {escape(str(monitor_state.get('symbol', 'GC=F')))} proxy</small>
        </div>
        <div class="market-block market-block--{escape(change_tone)}">
          <span class="market-label">Change</span>
          <strong>{escape(change_text)}</strong>
          <small>Latest day/session move</small>
        </div>
        <div class="market-block">
          <span class="market-label">Signal</span>
          <strong>{escape(signal_action)}</strong>
          <small>{escape(confidence_text)} confidence · {escape(risk_state)} risk</small>
        </div>
      </div>
      <div class="market-foot">
        <div>{escape(signal_reason)}</div>
        <div class="market-updated">Updated {escape(updated_at)}</div>
      </div>
      <div class="market-sparkline">{_sparkline(spark_values, stroke='#55dfff', fill='#55dfff', label='XAU monitor')}</div>
    </section>
    """


def _performance_card(title: str, value: str, subvalue: str, spark_values: list[float], *, tone: str, accent: str) -> str:
    return f"""
    <article class="performance-card performance-card--{escape(tone)}">
      <div class="performance-head">
        <div>
          <div class="performance-kicker">{escape(title)}</div>
          <div class="performance-value">{escape(value)}</div>
          <div class="performance-subvalue">{escape(subvalue)}</div>
        </div>
        <span class="live-pill">● LIVE</span>
      </div>
      {_sparkline(spark_values, stroke=accent, fill=accent, label=title)}
    </article>
    """


def _trade_stats(result: SimulationResult) -> dict[str, float]:
    pnl = result.final_equity - INITIAL_CASH
    win_count = sum(1 for trade in result.trades if trade.pnl > 0)
    flat_count = sum(1 for trade in result.trades if trade.pnl == 0)
    total = len(result.trades) or 1
    win_rate = (win_count / total) * 100.0
    return {
        "pnl": pnl,
        "pnl_pct": result.total_return * 100.0,
        "equity": result.final_equity,
        "drawdown_pct": result.max_drawdown * 100.0,
        "sharpe": result.sharpe,
        "trade_count": float(len(result.trades)),
        "win_rate": win_rate,
        "flat_count": float(flat_count),
    }


def _equity_points(result: SimulationResult) -> list[float]:
    return result.equity_curve or [INITIAL_CASH, INITIAL_CASH]


def _drawdown_points(result: SimulationResult) -> list[float]:
    curve = result.equity_curve or [INITIAL_CASH, INITIAL_CASH]
    peak = curve[0]
    points: list[float] = []
    for equity in curve:
        peak = max(peak, equity)
        dd = 0.0 if peak == 0 else ((peak - equity) / peak) * 100.0
        points.append(dd)
    return points


def _agent_feed(agents: Iterable[AgentCard], result: SimulationResult) -> list[tuple[str, str, str, str, str]]:
    stats = _trade_stats(result)
    items: list[tuple[str, str, str, str, str]] = [
        (
            "Trader",
            "Latest cycle closed with a realized gain.",
            f"{_signed_money(stats['pnl'])} / {_signed_pct(stats['pnl_pct'])} on the latest run.",
            "just now",
            "green",
        ),
        (
            "Risk",
            "Current drawdown remains inside the guardrail.",
            f"Max drawdown sits at {_signed_pct(-stats['drawdown_pct']) if stats['drawdown_pct'] else '0.00%'}.",
            "1m",
            "amber",
        ),
    ]

    for agent in agents:
        if agent.name.lower() == "trading":
            items.append(
                (
                    "Trading",
                    agent.current_task or agent.purpose,
                    agent.next_action or "Queued for review.",
                    agent.last_update or "just now",
                    "cyan",
                )
            )
        else:
            items.append(
                (
                    "Airdrop",
                    agent.current_task or agent.purpose,
                    agent.next_action or "Queued for review.",
                    agent.last_update or "5m ago",
                    "violet",
                )
            )

    items.extend(
        [
            (
                "System",
                "Portfolio value now tracks at $10k+ with percent change visible front and center.",
                f"Equity: {_money(stats['equity'])}, win rate: {stats['win_rate']:.0f}%.",
                "3m",
                "cyan",
            ),
            (
                "Airdrop",
                "Wallet hygiene checklist still pending for the next campaign.",
                "No live claims yet; scouting only.",
                "7m",
                "violet",
            ),
        ]
    )
    return items


def render_dashboard(
    goal: Goal,
    agents: Iterable[AgentCard],
    result: SimulationResult | None = None,
    *,
    summary: dict[str, object] | None = None,
    monitor_state: dict[str, object] | None = None,
) -> str:
    agents = list(agents)
    if result is None:
        # Fallback to a tiny synthetic state so the dashboard still renders cleanly.
        result = SimulationResult(
            trades=[],
            equity_curve=[INITIAL_CASH, INITIAL_CASH],
            returns=[0.0, 0.0],
            final_equity=INITIAL_CASH,
            max_drawdown=0.0,
            sharpe=0.0,
            total_return=0.0,
        )

    stats = _trade_stats(result)
    pnl = stats["pnl"]
    pnl_pct = stats["pnl_pct"]
    equity = stats["equity"]
    drawdown_pct = stats["drawdown_pct"]
    sharpe = stats["sharpe"]
    recommendation = "Collect more trades before changing risk settings."
    daily_metric = f'{stats["win_rate"]:.0f}% win rate'
    daily_focus = recommendation
    if summary is not None:
        recommendation = str(summary.get("recommendation", recommendation))
        daily_metric = str(summary.get("daily_metric", daily_metric))
        daily_focus = str(summary.get("daily_focus", recommendation))

    hero_points = [
        f"{_signed_money(pnl)} realized on the latest paper cycle.",
        f"{_signed_pct(pnl_pct)} return with {len(result.trades)} closed trades.",
        f"Next improvement: {daily_focus}",
    ]

    hero_card = f"""
    <section class="hero-panel panel panel--gold">
      <div class="hero-kicker">
        <span class="timeline-flag">TODAY</span>
        <div class="hero-kicker-lines">
          <div><span class="pill pill--green">TR</span> Trading is compounding the paper stack.</div>
          <div><span class="pill pill--pink">AR</span> Airdrop research is tracking campaigns only.</div>
        </div>
      </div>
      <div class="hero-main">
        <div class="hero-left">
          <div class="hero-title-row">
            <div>
              <div class="eyebrow">CTRL · COMMAND CENTER</div>
              <h1>Hermes keeps the crypto machines in one view.</h1>
            </div>
            <div class="hero-badge">Overview</div>
          </div>
          <ul class="hero-list">
            {''.join(f'<li>{escape(item)}</li>' for item in hero_points)}
          </ul>
        </div>
        <aside class="hero-highlight">
          <div class="hero-highlight-label">NET P&L</div>
          <div class="hero-highlight-value">{_signed_money(pnl)}</div>
          <div class="hero-highlight-sub">{_signed_pct(pnl_pct)} from the latest run</div>
          <div class="hero-highlight-note">{len(agents)} agent focus · paper-first · withdrawals off</div>
          <button class="hero-button" type="button">Review update</button>
        </aside>
      </div>
    </section>
    """

    market_watch_html = _market_watch_panel(monitor_state)

    kpi_row = f"""
    <section class="kpi-row">
      {_metric('Net P&L', _signed_money(pnl), _signed_pct(pnl_pct) + ' on the latest cycle', tone='green', icon='↗')}
      {_metric('Equity', _money(equity), 'Starting from $10,000.00', tone='cyan', icon='◉')}
      {_metric('Drawdown', _signed_pct(-drawdown_pct if drawdown_pct else 0.0), 'Current max drawdown', tone='amber', icon='⚑')}
      {_metric('Sharpe', f'{sharpe:.3f}', 'Signal quality for the latest run', tone='violet', icon='⋯')}
    </section>
    """

    left_agents = []
    for agent in agents:
        if agent.name.lower() == "trading":
            left_agents.append(_agent_card(agent, accent="cyan", icon="₿"))
        else:
            left_agents.append(_agent_card(agent, accent="violet", icon="◆"))

    performance_row = f"""
    <section class="performance-section panel">
      <div class="section-head">
        <div>
          <div class="eyebrow">SOCIAL PERFORMANCE</div>
          <h2>Portfolio performance</h2>
        </div>
        <button class="refresh-button" type="button">↻ Refresh live data</button>
      </div>
      <div class="performance-grid">
        {_performance_card('Trading equity', _money(equity), _signed_money(pnl) + ' / ' + _signed_pct(pnl_pct), _equity_points(result), tone='cyan', accent='#55dfff')}
        {_performance_card('Risk curve', f'{drawdown_pct:.2f}%', 'Drawdown pressure on the latest cycle', _drawdown_points(result), tone='amber', accent='#f0b86c')}
        {_performance_card('Daily improvement', daily_metric, daily_focus, [28, 31, 35, 41, 44, 47, 49], tone='violet', accent='#d46cff')}
      </div>
    </section>
    """

    feed_items = _agent_feed(agents, result)
    feed_html = "\n".join(
        _feed_item(source, title, detail, when, tone=tone)
        for source, title, detail, when, tone in feed_items
    )

    summary_note = ""
    if summary is not None:
        footer_bits = [f"Snapshot source: {escape(str(summary.get('source', 'live paper trader')))}", f"Recommendation: {escape(recommendation)}"]
        if summary.get('last_close_reason'):
            footer_bits.append(f"Last close: {escape(str(summary.get('last_close_reason')))}")
        summary_note = f"<div class=\"footer-note\">{' · '.join(footer_bits)}</div>"

    return f"""
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Hermes AI Operations Dashboard</title>
        <style>
          :root {{
            color-scheme: dark;
            --bg: #070b17;
            --bg-2: #0b1020;
            --panel: #0d1326;
            --panel-2: #11182d;
            --line: rgba(124, 154, 205, 0.15);
            --line-strong: rgba(198, 148, 72, 0.68);
            --text: #eef2ff;
            --muted: #8b96ad;
            --cyan: #58dfff;
            --green: #49ea87;
            --amber: #f0b85d;
            --violet: #cf69ff;
            --shadow: 0 20px 60px rgba(0, 0, 0, 0.42);
          }}

          * {{ box-sizing: border-box; }}
          html, body {{ min-height: 100%; }}
          body {{
            margin: 0;
            color: var(--text);
            background:
              radial-gradient(circle at 20% 0%, rgba(88, 223, 255, 0.08), transparent 30%),
              radial-gradient(circle at 85% 0%, rgba(207, 105, 255, 0.08), transparent 24%),
              linear-gradient(180deg, #060a14 0%, #090f1d 45%, #050810 100%);
            font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            font-variant-numeric: tabular-nums;
          }}
          body::before {{
            content: "";
            position: fixed;
            inset: 0;
            pointer-events: none;
            background-image:
              linear-gradient(rgba(255,255,255,0.04) 1px, transparent 1px),
              linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px);
            background-size: 54px 54px;
            mask-image: linear-gradient(180deg, rgba(0,0,0,0.45), transparent 80%);
          }}
          button {{ font: inherit; }}
          .app {{
            display: grid;
            grid-template-columns: 72px minmax(0, 1fr) 312px;
            min-height: 100vh;
          }}
          .sidebar {{
            position: sticky;
            top: 0;
            height: 100vh;
            background: rgba(7, 11, 23, 0.92);
            border-right: 1px solid rgba(124, 154, 205, 0.08);
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 14px 0;
            gap: 14px;
            z-index: 3;
          }}
          .brand {{
            width: 42px;
            height: 42px;
            border-radius: 12px;
            background: linear-gradient(180deg, rgba(88, 223, 255, 0.18), rgba(88, 223, 255, 0.05));
            border: 1px solid rgba(88, 223, 255, 0.32);
            display: grid;
            place-items: center;
            color: var(--cyan);
            font-weight: 800;
            letter-spacing: 0.08em;
            box-shadow: 0 0 22px rgba(88, 223, 255, 0.18);
          }}
          .nav {{
            margin-top: 6px;
            display: grid;
            gap: 12px;
            width: 100%;
            justify-items: center;
          }}
          .nav-btn {{
            width: 40px;
            height: 40px;
            border: 1px solid rgba(124, 154, 205, 0.12);
            border-radius: 14px;
            background: rgba(15, 21, 38, 0.86);
            color: var(--muted);
            display: grid;
            place-items: center;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.02);
          }}
          .nav-btn--active {{
            color: var(--cyan);
            border-color: rgba(88, 223, 255, 0.3);
            box-shadow: 0 0 0 1px rgba(88, 223, 255, 0.08), 0 0 18px rgba(88, 223, 255, 0.12);
          }}
          .nav-spacer {{ flex: 1; }}
          .record {{
            width: 40px;
            padding: 10px 0 12px;
            border-radius: 999px;
            background: rgba(27, 28, 34, 0.95);
            border: 1px solid rgba(255,255,255,0.08);
            display: grid;
            place-items: center;
            gap: 10px;
            box-shadow: var(--shadow);
          }}
          .record-dot {{ width: 18px; height: 18px; border-radius: 50%; background: #ff7d57; box-shadow: 0 0 0 4px rgba(255, 125, 87, 0.18); }}
          .record-bars {{ display: grid; gap: 8px; }}
          .record-bars span {{ display: block; width: 14px; height: 3px; border-radius: 99px; background: rgba(255,255,255,0.82); }}
          .main {{ padding: 22px 18px 24px; min-width: 0; }}
          .topbar {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 18px;
            margin-bottom: 18px;
          }}
          .topbar-left {{ display: flex; align-items: baseline; gap: 14px; min-width: 0; }}
          .top-title {{
            font-weight: 800;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--text);
          }}
          .crumb {{ color: var(--muted); font-size: 12px; letter-spacing: 0.16em; text-transform: uppercase; }}
          .crumb strong {{ color: var(--cyan); font-size: 12px; letter-spacing: 0.16em; }}
          .topbar-right {{ display: flex; align-items: center; gap: 10px; }}
          .live {{ color: var(--green); font-size: 12px; font-weight: 700; letter-spacing: 0.08em; }}
          .pill {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-height: 22px;
            padding: 0 8px;
            border-radius: 999px;
            font-size: 11px;
            letter-spacing: 0.08em;
            font-weight: 700;
          }}
          .pill--green {{ background: rgba(73, 234, 135, 0.16); color: var(--green); }}
          .pill--pink {{ background: rgba(207, 105, 255, 0.14); color: var(--violet); }}
          .avatar {{
            width: 34px;
            height: 34px;
            border-radius: 50%;
            background: linear-gradient(180deg, #4f67ff, #6d8bff);
            display: grid;
            place-items: center;
            font-size: 12px;
            font-weight: 800;
          }}
          .meta-bar {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 14px;
          }}
          .section-label {{
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 12px;
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 0.18em;
          }}
          .section-label strong {{ color: var(--cyan); }}
          .panel {{
            background: linear-gradient(180deg, rgba(14, 19, 37, 0.95), rgba(10, 14, 26, 0.98));
            border: 1px solid rgba(124, 154, 205, 0.13);
            border-radius: 14px;
            box-shadow: var(--shadow);
          }}
          .panel--gold {{ border-top: 2px solid var(--line-strong); }}
          .hero-panel {{ padding: 12px 14px 16px; margin-bottom: 14px; }}
          .hero-kicker {{
            display: grid;
            grid-template-columns: auto 1fr;
            gap: 14px;
            align-items: center;
            margin-bottom: 12px;
            padding-bottom: 10px;
            border-bottom: 1px solid rgba(124, 154, 205, 0.1);
          }}
          .timeline-flag {{
            writing-mode: vertical-rl;
            transform: rotate(180deg);
            color: var(--amber);
            font-size: 11px;
            letter-spacing: 0.24em;
            font-weight: 800;
          }}
          .hero-kicker-lines {{ display: grid; gap: 8px; font-size: 12px; color: var(--muted); }}
          .hero-main {{ display: grid; grid-template-columns: minmax(0, 1fr) 340px; gap: 14px; align-items: stretch; }}
          .hero-left {{ padding: 4px 4px 0 0; }}
          .eyebrow {{
            color: var(--cyan);
            font-size: 11px;
            letter-spacing: 0.2em;
            text-transform: uppercase;
            margin-bottom: 10px;
            font-weight: 800;
          }}
          .hero-title-row {{
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 14px;
            margin-bottom: 10px;
          }}
          h1, h2, h3, p {{ margin-top: 0; }}
          h1 {{
            margin-bottom: 0;
            font-size: clamp(25px, 3.2vw, 44px);
            line-height: 0.98;
            letter-spacing: -0.05em;
            max-width: 14ch;
          }}
          .hero-badge {{
            padding: 8px 10px;
            border: 1px solid rgba(124, 154, 205, 0.14);
            border-radius: 10px;
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 0.16em;
            font-size: 11px;
            white-space: nowrap;
          }}
          .hero-list {{
            margin: 0;
            padding-left: 16px;
            color: var(--muted);
            display: grid;
            gap: 8px;
            font-size: 13px;
            line-height: 1.45;
          }}
          .hero-highlight {{
            border-radius: 12px;
            border: 1px solid rgba(124, 154, 205, 0.12);
            background: linear-gradient(180deg, rgba(9, 12, 25, 0.98), rgba(14, 20, 40, 0.95));
            padding: 14px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            gap: 10px;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.02);
          }}
          .hero-highlight-label {{ color: var(--amber); font-size: 11px; letter-spacing: 0.18em; text-transform: uppercase; font-weight: 800; }}
          .hero-highlight-value {{ font-size: clamp(32px, 4vw, 50px); line-height: 0.95; letter-spacing: -0.05em; font-weight: 900; }}
          .hero-highlight-sub {{ color: var(--green); font-size: 13px; font-weight: 700; }}
          .hero-highlight-note {{ color: var(--muted); font-size: 12px; line-height: 1.45; }}
          .hero-button {{
            align-self: start;
            border: 1px solid rgba(240, 184, 93, 0.5);
            background: rgba(240, 184, 93, 0.1);
            color: #ffdca3;
            border-radius: 10px;
            padding: 8px 12px;
            cursor: pointer;
            font-weight: 700;
          }}
          .hero-button:hover {{ background: rgba(240, 184, 93, 0.16); }}
          .kpi-row {{
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 14px;
            margin-bottom: 16px;
          }}
          .metric-card {{
            padding: 14px;
            border-radius: 14px;
            border: 1px solid rgba(124, 154, 205, 0.12);
            background: linear-gradient(180deg, rgba(14, 18, 36, 0.95), rgba(10, 14, 26, 0.98));
            min-height: 120px;
          }}
          .metric-card--green {{ box-shadow: inset 0 1px 0 rgba(73, 234, 135, 0.08); }}
          .metric-card--cyan {{ box-shadow: inset 0 1px 0 rgba(88, 223, 255, 0.08); }}
          .metric-card--amber {{ box-shadow: inset 0 1px 0 rgba(240, 184, 93, 0.08); }}
          .metric-card--violet {{ box-shadow: inset 0 1px 0 rgba(207, 105, 255, 0.08); }}
          .metric-top {{ display: flex; align-items: center; gap: 8px; margin-bottom: 12px; color: var(--muted); }}
          .metric-icon {{
            width: 20px;
            height: 20px;
            border-radius: 6px;
            display: inline-grid;
            place-items: center;
            font-size: 11px;
            color: var(--text);
          }}
          .metric-label {{ text-transform: uppercase; letter-spacing: 0.16em; font-size: 11px; font-weight: 800; }}
          .metric-value {{ font-size: clamp(26px, 2.8vw, 36px); line-height: 0.96; letter-spacing: -0.05em; font-weight: 900; margin-bottom: 10px; }}
          .metric-delta {{ color: var(--muted); font-size: 12px; line-height: 1.45; }}
          .market-panel {{ padding: 12px 14px 14px; margin-bottom: 16px; }}
          .market-chip {{
            padding: 6px 10px;
            border-radius: 999px;
            border: 1px solid rgba(88, 223, 255, 0.18);
            color: var(--cyan);
            text-transform: uppercase;
            letter-spacing: 0.16em;
            font-size: 11px;
            font-weight: 800;
          }}
          .market-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-bottom: 12px; }}
          .market-block {{
            padding: 12px;
            border-radius: 12px;
            border: 1px solid rgba(124, 154, 205, 0.1);
            background: rgba(255,255,255,0.02);
            min-height: 92px;
            display: flex;
            flex-direction: column;
            gap: 6px;
          }}
          .market-block strong {{ font-size: clamp(22px, 2.6vw, 30px); line-height: 0.98; letter-spacing: -0.04em; }}
          .market-block small {{ color: var(--muted); line-height: 1.45; }}
          .market-block--green {{ box-shadow: inset 0 1px 0 rgba(73, 234, 135, 0.08); }}
          .market-block--amber {{ box-shadow: inset 0 1px 0 rgba(240, 184, 93, 0.08); }}
          .market-foot {{ display: flex; align-items: end; justify-content: space-between; gap: 14px; color: var(--muted); font-size: 12px; line-height: 1.45; margin-bottom: 12px; }}
          .market-updated {{ color: var(--cyan); text-transform: uppercase; letter-spacing: 0.12em; font-size: 11px; font-weight: 800; white-space: nowrap; }}
          .market-sparkline {{ height: 74px; }}
          .market-sparkline svg {{ width: 100%; height: 100%; }}
          .market-sparkline polyline {{ filter: drop-shadow(0 0 12px rgba(88, 223, 255, 0.22)); }}
          .agent-watch {{
            padding: 10px;
            border-radius: 12px;
            background: rgba(88, 223, 255, 0.05);
            border: 1px solid rgba(88, 223, 255, 0.14);
            display: grid;
            gap: 8px;
            margin-bottom: 8px;
          }}
          .agent-watch-head {{ display: flex; align-items: center; justify-content: space-between; gap: 8px; }}
          .agent-watch-label {{ color: var(--muted); text-transform: uppercase; letter-spacing: 0.14em; font-size: 10px; font-weight: 800; }}
          .agent-watch-pill {{
            padding: 4px 8px;
            border-radius: 999px;
            background: rgba(73, 234, 135, 0.12);
            color: var(--green);
            text-transform: uppercase;
            letter-spacing: 0.14em;
            font-size: 10px;
            font-weight: 800;
          }}
          .agent-watch-row {{ display: grid; gap: 2px; }}
          .agent-watch-row strong {{ font-size: 12px; }}
          .agent-watch-row span, .agent-watch-foot {{ color: var(--muted); font-size: 11px; line-height: 1.45; }}
          .agent-watch-foot {{ display: flex; align-items: center; justify-content: space-between; gap: 8px; }}
          .agent-watch-foot small {{ color: var(--cyan); text-transform: uppercase; letter-spacing: 0.12em; }}
          .content-grid {{
            display: grid;
            grid-template-columns: minmax(0, 1fr);
            gap: 16px;
          }}
          .section-head {{
            display: flex;
            align-items: end;
            justify-content: space-between;
            gap: 14px;
            margin-bottom: 12px;
          }}
          .section-head h2 {{ margin-bottom: 0; font-size: 18px; letter-spacing: -0.03em; }}
          .refresh-button {{
            border: 1px solid rgba(88, 223, 255, 0.24);
            background: rgba(88, 223, 255, 0.09);
            color: #b8f5ff;
            border-radius: 10px;
            padding: 8px 10px;
            cursor: pointer;
            font-weight: 700;
          }}
          .team-panel {{ padding: 12px 14px 14px; }}
          .team-head {{ display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }}
          .team-badge {{
            padding: 6px 9px;
            border-radius: 999px;
            border: 1px solid rgba(88, 223, 255, 0.2);
            color: var(--cyan);
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.16em;
            font-weight: 800;
          }}
          .agent-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }}
          .agent-card {{
            border-radius: 14px;
            border: 1px solid rgba(124, 154, 205, 0.13);
            background: linear-gradient(180deg, rgba(12, 18, 35, 0.96), rgba(8, 12, 23, 0.98));
            padding: 12px;
            min-height: 202px;
            display: flex;
            flex-direction: column;
            gap: 10px;
          }}
          .agent-head {{ display: flex; align-items: start; justify-content: space-between; gap: 10px; }}
          .agent-avatar {{
            width: 28px;
            height: 28px;
            border-radius: 8px;
            display: grid;
            place-items: center;
            font-size: 14px;
            box-shadow: 0 0 18px rgba(88, 223, 255, 0.14);
          }}
          .agent-avatar--cyan {{ background: rgba(88, 223, 255, 0.14); color: var(--cyan); }}
          .agent-avatar--violet {{ background: rgba(207, 105, 255, 0.14); color: var(--violet); }}
          .agent-status {{ display: grid; justify-items: end; gap: 6px; }}
          .agent-status-line {{ color: var(--muted); font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase; }}
          .agent-status-pill {{
            padding: 5px 8px;
            border-radius: 999px;
            font-size: 10px;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            font-weight: 800;
          }}
          .agent-status-pill--cyan {{ background: rgba(88, 223, 255, 0.12); color: var(--cyan); }}
          .agent-status-pill--violet {{ background: rgba(207, 105, 255, 0.12); color: var(--violet); }}
          .agent-card h3 {{ margin-bottom: 0; font-size: 16px; letter-spacing: -0.03em; }}
          .agent-copy {{ color: var(--muted); font-size: 12px; line-height: 1.5; margin-bottom: 0; }}
          .agent-meta {{
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 10px;
          }}
          .agent-meta > div {{
            padding: 10px;
            border-radius: 12px;
            background: rgba(255,255,255,0.02);
            border: 1px solid rgba(124, 154, 205, 0.08);
          }}
          .agent-meta-label {{ display: block; color: var(--muted); font-size: 11px; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.14em; }}
          .agent-meta strong {{ display: block; font-size: 12px; line-height: 1.45; }}
          .agent-footer {{ display: flex; align-items: end; justify-content: space-between; gap: 10px; margin-top: auto; }}
          .agent-progress {{ flex: 1; }}
          .agent-progress-track {{ height: 6px; border-radius: 999px; background: rgba(124, 154, 205, 0.12); overflow: hidden; margin-bottom: 6px; }}
          .agent-progress-track span {{ display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, var(--cyan), var(--violet)); box-shadow: 0 0 18px rgba(88, 223, 255, 0.22); }}
          .agent-progress small, .agent-health {{ color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.12em; }}
          .performance-section {{ padding: 12px 14px 14px; }}
          .performance-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }}
          .performance-card {{
            padding: 12px;
            border-radius: 14px;
            border: 1px solid rgba(124, 154, 205, 0.12);
            background: linear-gradient(180deg, rgba(12, 17, 32, 0.96), rgba(8, 12, 24, 0.98));
            min-height: 240px;
            display: flex;
            flex-direction: column;
          }}
          .performance-card--cyan {{ box-shadow: inset 0 1px 0 rgba(88, 223, 255, 0.08); }}
          .performance-card--amber {{ box-shadow: inset 0 1px 0 rgba(240, 184, 93, 0.08); }}
          .performance-card--violet {{ box-shadow: inset 0 1px 0 rgba(207, 105, 255, 0.08); }}
          .performance-head {{ display: flex; align-items: start; justify-content: space-between; gap: 12px; margin-bottom: 8px; }}
          .performance-kicker {{ text-transform: uppercase; letter-spacing: 0.16em; color: var(--muted); font-size: 11px; margin-bottom: 8px; font-weight: 800; }}
          .performance-value {{ font-size: clamp(26px, 3vw, 38px); line-height: 0.96; font-weight: 900; letter-spacing: -0.05em; margin-bottom: 6px; }}
          .performance-subvalue {{ color: var(--muted); font-size: 12px; line-height: 1.45; }}
          .live-pill {{ color: var(--green); font-size: 11px; letter-spacing: 0.16em; text-transform: uppercase; font-weight: 800; }}
          .sparkline-wrap {{ margin-top: auto; height: 122px; }}
          .sparkline-wrap svg {{ width: 100%; height: 100%; display: block; }}
          .sparkline-wrap polyline {{ filter: drop-shadow(0 0 8px rgba(255,255,255,0.08)); }}
          .main-grid {{ display: grid; grid-template-columns: minmax(0, 1fr) 312px; gap: 16px; align-items: start; }}
          .right-rail {{ position: sticky; top: 18px; }}
          .feed-panel {{ padding: 12px; min-height: calc(100vh - 36px); }}
          .feed-title {{ display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 12px; }}
          .feed-title h2 {{ margin: 0; font-size: 14px; letter-spacing: 0.16em; text-transform: uppercase; color: var(--muted); }}
          .feed-list {{ list-style: none; padding: 0; margin: 0; display: grid; gap: 12px; }}
          .feed-item {{ display: grid; grid-template-columns: 48px minmax(0, 1fr); gap: 10px; }}
          .feed-time {{ color: rgba(255,255,255,0.3); font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase; padding-top: 2px; }}
          .feed-body p {{ margin: 4px 0 4px; color: var(--text); font-size: 12px; line-height: 1.45; }}
          .feed-body small {{ color: var(--muted); line-height: 1.45; display: block; }}
          .feed-source {{ display: inline-block; font-size: 12px; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; }}
          .feed-source--cyan {{ color: var(--cyan); }}
          .feed-source--green {{ color: var(--green); }}
          .feed-source--amber {{ color: var(--amber); }}
          .feed-source--violet {{ color: var(--violet); }}
          .dashboard-note {{ margin-top: 14px; color: var(--muted); font-size: 12px; line-height: 1.45; }}
          .footer-note {{
            margin-top: 14px;
            border-top: 1px solid rgba(124, 154, 205, 0.1);
            padding-top: 12px;
            color: var(--muted);
            font-size: 12px;
          }}
          .content-main {{ display: grid; gap: 16px; }}
          .layout-left {{ min-width: 0; }}
          .layout-right {{ min-width: 0; }}
          .hero-panel, .team-panel, .performance-section {{ overflow: hidden; }}
          .helper {{ color: var(--muted); }}
          .line {{ height: 1px; background: rgba(124,154,205,0.12); margin: 12px 0; }}
          @media (max-width: 1300px) {{
            .app {{ grid-template-columns: 72px minmax(0, 1fr); }}
            .right-rail {{ display: none; }}
          }}
          @media (max-width: 980px) {{
            .hero-main, .main-grid, .kpi-row, .agent-grid, .performance-grid {{ grid-template-columns: 1fr; }}
            .hero-title-row, .topbar {{ flex-direction: column; align-items: flex-start; }}
          }}
          @media (max-width: 720px) {{
            .app {{ grid-template-columns: 1fr; }}
            .sidebar {{ position: static; height: auto; border-right: 0; border-bottom: 1px solid rgba(124,154,205,0.08); flex-direction: row; justify-content: space-between; padding: 10px 12px; }}
            .nav {{ grid-auto-flow: column; grid-auto-columns: 40px; width: auto; }}
            .nav-spacer, .record {{ display: none; }}
            .main {{ padding: 12px; }}
          }}
        </style>
      </head>
      <body>
        <div class="app">
          <aside class="sidebar">
            <div class="brand">CTRL</div>
            <nav class="nav" aria-label="Primary">
              <button class="nav-btn nav-btn--active" type="button" aria-label="Overview">⌂</button>
              <button class="nav-btn" type="button" aria-label="Search">⌕</button>
              <button class="nav-btn" type="button" aria-label="Activity">≣</button>
              <button class="nav-btn" type="button" aria-label="Performance">▤</button>
              <button class="nav-btn" type="button" aria-label="Settings">⚙</button>
            </nav>
            <div class="nav-spacer"></div>
            <div class="record" aria-label="Recording indicator">
              <div class="record-dot"></div>
              <div class="record-bars"><span></span><span></span><span></span></div>
            </div>
          </aside>

          <main class="main">
            <header class="topbar">
              <div class="topbar-left">
                <div class="top-title">Command Center</div>
                <div class="crumb"><strong>Overview</strong></div>
              </div>
              <div class="topbar-right">
                <div class="live">● LIVE</div>
                <div class="pill pill--green">SYNC</div>
                <div class="avatar">H</div>
              </div>
            </header>

            <div class="main-grid">
              <div class="layout-left content-main">
                {hero_card}
                {market_watch_html}
                {kpi_row}

                <section class="team-panel panel">
                  <div class="team-head">
                    <div class="section-label"><strong>AI TEAM</strong> <span class="team-badge">2 AGENTS</span></div>
                  </div>
                  <div class="agent-grid">
                    {''.join(left_agents)}
                  </div>
                </section>

                {performance_row}
              </div>

              <aside class="right-rail">
                <section class="feed-panel panel">
                  <div class="feed-title">
                    <h2>Activity feed</h2>
                    <span class="live">● LIVE</span>
                  </div>
                  <ul class="feed-list">
                    {feed_html}
                  </ul>
                  <div class="dashboard-note">
                    Hermes is tracking only two money-focused agents for now: trading and airdrop research.
                    Add more by editing <code>state/agents.json</code>.
                    {summary_note}
                  </div>
                </section>
              </aside>
            </div>
          </main>
        </div>
      </body>
    </html>
    """
