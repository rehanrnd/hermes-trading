from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv


@dataclass(frozen=True)
class MarketData:
    timestamps: list[str]
    prices: list[float]
    signals: list[float]


def _require_field(row: dict[str, str], field: str, *, line_number: int) -> str:
    value = row.get(field)
    if value is None or value == "":
        raise ValueError(f"missing required '{field}' value on line {line_number}")
    return value


def load_market_data_csv(
    path: str | Path,
    *,
    timestamp_column: str = "timestamp",
    price_column: str = "close",
    signal_column: str = "signal",
) -> MarketData:
    csv_path = Path(path)
    timestamps: list[str] = []
    prices: list[float] = []
    signals: list[float] = []

    with csv_path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames or []
        if price_column not in fieldnames:
            raise ValueError(f"CSV must contain '{price_column}' column")
        if timestamp_column not in fieldnames:
            raise ValueError(f"CSV must contain '{timestamp_column}' column")

        for line_number, row in enumerate(reader, start=2):
            if not row:
                continue
            timestamp = _require_field(row, timestamp_column, line_number=line_number)
            price_text = _require_field(row, price_column, line_number=line_number)
            signal_text = row.get(signal_column, "0") or "0"
            try:
                price = float(price_text)
            except ValueError as exc:
                raise ValueError(f"invalid price on line {line_number}: {price_text!r}") from exc
            try:
                signal = float(signal_text)
            except ValueError as exc:
                raise ValueError(f"invalid signal on line {line_number}: {signal_text!r}") from exc

            timestamps.append(timestamp)
            prices.append(price)
            signals.append(signal)

    if not prices:
        raise ValueError(f"CSV {csv_path} did not contain any data rows")

    return MarketData(timestamps=timestamps, prices=prices, signals=signals)
