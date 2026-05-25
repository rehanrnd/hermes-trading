from __future__ import annotations

from csv import DictWriter
from io import StringIO
from pathlib import Path

from .paper import SimulationResult

FIELDNAMES = [
    "asset",
    "source",
    "trade_index",
    "side",
    "entry_price",
    "exit_price",
    "quantity",
    "pnl",
    "return_pct",
]


def _trade_rows(result: SimulationResult, *, asset: str, source: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for index, trade in enumerate(result.trades, start=1):
        rows.append(
            {
                "asset": asset,
                "source": source,
                "trade_index": str(index),
                "side": trade.side,
                "entry_price": str(trade.entry_price),
                "exit_price": str(trade.exit_price),
                "quantity": str(trade.quantity),
                "pnl": str(trade.pnl),
                "return_pct": str(trade.return_pct),
            }
        )
    return rows


def render_trade_journal_csv(result: SimulationResult, *, asset: str, source: str) -> str:
    buffer = StringIO()
    writer = DictWriter(buffer, fieldnames=FIELDNAMES, lineterminator="\n")
    writer.writeheader()
    writer.writerows(_trade_rows(result, asset=asset, source=source))
    return buffer.getvalue()


def write_trade_journal_csv(path: str | Path, result: SimulationResult, *, asset: str, source: str) -> Path:
    journal_path = Path(path)
    journal_path.write_text(render_trade_journal_csv(result, asset=asset, source=source), encoding="utf-8")
    return journal_path
