#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/rehan/hermes-trading"
LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"

start_if_missing() {
  local pattern="$1"
  local cmd="$2"
  local log_file="$3"

  if ! pgrep -f "$pattern" >/dev/null 2>&1; then
    nohup bash -lc "cd '$ROOT' && $cmd" >>"$LOG_DIR/$log_file" 2>&1 &
    echo "started: $pattern"
  fi
}

start_if_missing "scripts/run_xau_monitor.py" "python3 scripts/run_xau_monitor.py" "xau_monitor.log"
start_if_missing "scripts/run_paper_trader.py" "python3 scripts/run_paper_trader.py" "paper_trader.log"
start_if_missing "scripts/run_dashboard.py" "python3 scripts/run_dashboard.py" "dashboard.log"

# Health check dashboard port
if lsof -nP -iTCP:8787 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "ok: dashboard listening on 8787"
else
  echo "warn: dashboard not listening on 8787"
fi
