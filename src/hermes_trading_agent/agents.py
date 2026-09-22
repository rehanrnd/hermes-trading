from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AgentCard:
    name: str
    role: str
    status: str
    purpose: str
    last_update: str | None = None
    notes: str | None = None
    current_task: str | None = None
    next_action: str | None = None
    health: str | None = None
    progress: int | None = None
    watch_asset: str | None = None
    watch_symbol: str | None = None
    watch_price: float | None = None
    watch_change_pct: float | None = None
    watch_signal: str | None = None
    watch_action: str | None = None
    watch_updated_at: str | None = None
    performance_summary: str | None = None


def _default_agents() -> list[AgentCard]:
    return [
        AgentCard(
            name="trading",
            role="execution",
            status="monitoring",
            purpose="Monitor XAU around the clock, wait for a clean entry, and keep risk inside guardrails.",
            last_update="just now",
            notes="Paper-first, withdrawals disabled, and every change stays auditable.",
            current_task="Watch the XAU proxy feed and hold fire until the setup is clean.",
            next_action="Refresh the monitor state and confirm the next entry window.",
            health="stable",
            progress=74,
            watch_asset="XAU",
            watch_symbol="GC=F",
            watch_signal="watch",
            watch_action="wait for pullback",
            performance_summary="Closed trades: 0 | Realized PnL: $0.00 | Open position: none",
        ),
        AgentCard(
            name="airdrop",
            role="research_ops",
            status="researching",
            purpose="Track crypto airdrop opportunities, eligibility rules, and claim windows.",
            last_update="5m ago",
            notes="Focus on low-risk participation, wallet hygiene, and checklist logging.",
            current_task="Scan active campaigns and shortlist the ones worth tracking.",
            next_action="Collect network, wallet, and task prerequisites.",
            health="watching",
            progress=41,
        ),
    ]


def _coerce_progress(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return max(0, min(100, int(value)))
    except (TypeError, ValueError):
        return None


def load_agents(path: str | Path = "state/agents.json") -> list[AgentCard]:
    agents_path = Path(path)
    if not agents_path.exists():
        return _default_agents()

    data = json.loads(agents_path.read_text(encoding="utf-8"))
    raw_agents = data.get("agents", [])
    agents: list[AgentCard] = []
    for item in raw_agents:
        agents.append(
            AgentCard(
                name=item["name"],
                role=item["role"],
                status=item.get("status", "idle"),
                purpose=item.get("purpose", ""),
                last_update=item.get("last_update"),
                notes=item.get("notes"),
                current_task=item.get("current_task"),
                next_action=item.get("next_action"),
                health=item.get("health"),
                progress=_coerce_progress(item.get("progress")),
                watch_asset=item.get("watch_asset"),
                watch_symbol=item.get("watch_symbol"),
                watch_price=item.get("watch_price"),
                watch_change_pct=item.get("watch_change_pct"),
                watch_signal=item.get("watch_signal"),
                watch_action=item.get("watch_action"),
                watch_updated_at=item.get("watch_updated_at"),
                performance_summary=item.get("performance_summary"),
            )
        )
    return agents or _default_agents()
