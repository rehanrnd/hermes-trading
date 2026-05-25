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


def _default_agents() -> list[AgentCard]:
    return [
        AgentCard(
            name="research",
            role="data_intake",
            status="idle",
            purpose="Collect market ideas, hypotheses, and source snapshots.",
        ),
        AgentCard(
            name="execution",
            role="paper_trading",
            status="idle",
            purpose="Run the paper-trading loop and produce trade journals.",
        ),
        AgentCard(
            name="reflection",
            role="evaluation",
            status="idle",
            purpose="Review the latest closed trades and suggest one change.",
        ),
    ]


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
            )
        )
    return agents or _default_agents()
