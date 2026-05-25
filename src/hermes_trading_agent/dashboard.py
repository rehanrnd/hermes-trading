from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Iterable

from .agents import AgentCard, load_agents
from .goal import Goal, load_goal
from .paper import SimulationResult
from .scaffold import scaffold_summary


def _render_agent_card(agent: AgentCard) -> str:
    last_update = f"<p><strong>Last update:</strong> {escape(agent.last_update)}</p>" if agent.last_update else ""
    notes = f"<p><strong>Notes:</strong> {escape(agent.notes)}</p>" if agent.notes else ""
    return f"""
    <section class=\"card\">
      <h3>{escape(agent.name)}</h3>
      <p><strong>Role:</strong> {escape(agent.role)}</p>
      <p><strong>Status:</strong> {escape(agent.status)}</p>
      <p>{escape(agent.purpose)}</p>
      {last_update}
      {notes}
    </section>
    """


def _render_metric(label: str, value: str) -> str:
    return f"<div class=\"metric\"><span>{escape(label)}</span><strong>{escape(value)}</strong></div>"


def render_dashboard(
    goal: Goal,
    agents: Iterable[AgentCard],
    result: SimulationResult | None = None,
) -> str:
    agent_html = "\n".join(_render_agent_card(agent) for agent in agents)
    result_html = ""
    if result is not None:
        result_html = f"""
        <section class=\"card\">
          <h2>Latest paper run</h2>
          <div class=\"metrics\">
            {_render_metric('Trades', str(len(result.trades)))}
            {_render_metric('Final equity', f'{result.final_equity:.2f}')}
            {_render_metric('Total return', f'{result.total_return * 100:.2f}%')}
            {_render_metric('Max drawdown', f'{result.max_drawdown * 100:.2f}%')}
            {_render_metric('Sharpe', f'{result.sharpe:.3f}')}
          </div>
        </section>
        """

    return f"""
    <!doctype html>
    <html lang=\"en\">
      <head>
        <meta charset=\"utf-8\" />
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
        <title>Hermes Trading Dashboard</title>
        <style>
          :root {{ color-scheme: dark; }}
          body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0b1020; color: #e8ecf6; margin: 0; }}
          .wrap {{ max-width: 1200px; margin: 0 auto; padding: 24px; }}
          h1, h2, h3 {{ margin-top: 0; }}
          .hero {{ background: linear-gradient(135deg, #1f2a44, #111827); border: 1px solid #2c3551; border-radius: 18px; padding: 20px; margin-bottom: 18px; }}
          .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 14px; }}
          .card {{ background: #111827; border: 1px solid #24304c; border-radius: 16px; padding: 16px; }}
          .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; }}
          .metric {{ background: #0f172a; border: 1px solid #26324f; border-radius: 12px; padding: 12px; }}
          .metric span {{ display: block; font-size: 12px; opacity: 0.75; margin-bottom: 6px; }}
          .metric strong {{ font-size: 18px; }}
          code {{ background: #0f172a; padding: 2px 6px; border-radius: 6px; }}
          .muted {{ opacity: 0.78; }}
        </style>
      </head>
      <body>
        <div class=\"wrap\">
          <div class=\"hero\">
            <h1>Hermes Trading Dashboard</h1>
            <p class=\"muted\">{escape(scaffold_summary())}</p>
            <p><strong>Goal file:</strong> <code>state/goal.yaml</code></p>
            <p><strong>Agent registry:</strong> <code>state/agents.json</code></p>
          </div>

          {result_html}

          <section class=\"card\">
            <h2>Managed agents</h2>
            <div class=\"grid\">
              {agent_html}
            </div>
          </section>
        </div>
      </body>
    </html>
    """
