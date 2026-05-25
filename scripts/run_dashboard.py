from __future__ import annotations

import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hermes_trading_agent.agents import load_agents  # noqa: E402
from hermes_trading_agent.dashboard import render_dashboard  # noqa: E402
from hermes_trading_agent.goal import load_goal  # noqa: E402
from hermes_trading_agent.agent_loop import run_reflection_loop  # noqa: E402


def build_latest_report():
    goal = load_goal()
    prices = [100.0, 101.0, 102.0, 101.5, 103.0, 104.0, 103.0, 105.0]
    signals = [1, 1, 1, 0, -1, -1, 0, 1]
    report = run_reflection_loop(goal, prices, signals)
    return goal, report


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in {"/", "/index.html"}:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")
            return

        goal, report = build_latest_report()
        html = render_dashboard(goal, load_agents(), report.result).encode("utf-8")
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
