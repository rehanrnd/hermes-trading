# Hermes Trading Agent Scaffold

## Purpose
A local, reproducible scaffold for a trading agent workflow.

## Current strategy
- Asset: `XAUUSD`
- Daily compounding target: `7%`
- Max drawdown: `8%`
- Minimum Sharpe: `1.2`
- Reflection cadence: every `5` closed trades
- Guardrail: `one_variable_only: true`

## Safe defaults
- Paper trading / simulation first
- No live execution until the execution layer is explicitly added and reviewed
- Keep changes to one variable at a time during reflection cycles

## Structure
- `state/goal.yaml` — confirmed strategy goal
- `state/agents.json` — simple managed-agent registry for the local dashboard
- `src/hermes_trading_agent/goal.py` — load and validate goal state with stdlib only
- `src/hermes_trading_agent/paper.py` — paper-trading simulator and metrics
- `src/hermes_trading_agent/agent_loop.py` — one-pass evaluation and reflection wrapper
- `src/hermes_trading_agent/agents.py` — agent registry loader
- `src/hermes_trading_agent/dashboard.py` — HTML dashboard renderer
- `scripts/show_goal.py` — quick local inspection command
- `scripts/demo_paper.py` — demo simulation and reflection output
- `scripts/run_dashboard.py` — local dashboard server on `127.0.0.1:8787`

## Next steps
1. Connect data ingestion.
2. Add paper-trading execution.
3. Add evaluation and reflection loop.
4. Add a dashboard only after the core workflow is stable.
