"""CSV-backed storage. Plain text so trades stay human-readable and editable."""

from __future__ import annotations

import csv
import os
from pathlib import Path

from .models import FIELDNAMES, Trade

DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "trades.csv"


def db_path() -> Path:
    """Location of the trades CSV (override with TRADE_JOURNAL_DB)."""
    return Path(os.environ.get("TRADE_JOURNAL_DB", DEFAULT_DB))


def load(path: Path | None = None) -> list[Trade]:
    path = path or db_path()
    if not path.exists():
        return []
    with path.open(newline="") as fh:
        return [Trade.from_row(row) for row in csv.DictReader(fh)]


def append(trade: Trade, path: Path | None = None) -> None:
    path = path or db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not path.exists()
    with path.open("a", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        if new_file:
            writer.writeheader()
        writer.writerow(trade.to_row())
