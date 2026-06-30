"""CSV-backed storage. Plain text so trades stay human-readable and editable."""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path

from .models import FIELDNAMES, Trade

DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "trades.csv"


def db_path() -> Path:
    """Location of the trades CSV (override with TRADE_JOURNAL_DB)."""
    return Path(os.environ.get("TRADE_JOURNAL_DB", DEFAULT_DB))


def tags_path() -> Path:
    """Tag registry, paired to the active DB (trades.csv → trades.tags.json)."""
    db = db_path()
    return db.with_name(db.stem + ".tags.json")


def load(path: Path | None = None) -> list[Trade]:
    path = path or db_path()
    if not path.exists():
        return []
    with path.open(newline="") as fh:
        return [Trade.from_row(row) for row in csv.DictReader(fh)]


def append(trade: Trade, path: Path | None = None) -> None:
    path = path or db_path()
    # ponytail: scan existing for the next id — fine at journal scale (1000s of
    # rows). If this ever holds millions, store a counter instead.
    existing = load(path)
    trade.id = max((t.id for t in existing), default=0) + 1
    path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not path.exists()
    with path.open("a", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        if new_file:
            writer.writeheader()
        writer.writerow(trade.to_row())


def _write_all(trades: list[Trade], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        writer.writeheader()
        for t in trades:
            writer.writerow(t.to_row())


def delete(trade_id: int, path: Path | None = None) -> bool:
    """Remove the trade with this id, rewriting the file. False if not found."""
    path = path or db_path()
    trades = load(path)
    kept = [t for t in trades if t.id != trade_id]
    if len(kept) == len(trades):
        return False
    _write_all(kept, path)
    return True


# --- tag registry --------------------------------------------------------
def load_tags() -> list[str]:
    path = tags_path()
    return sorted(json.loads(path.read_text())) if path.exists() else []


def save_tags(tags) -> None:
    path = tags_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sorted(set(tags))))


def rename_tag(old: str, new: str) -> None:
    """Rename in the registry and on every trade carrying it."""
    save_tags([new if t == old else t for t in load_tags()])
    trades = load()
    for t in trades:
        if old in t.tags:
            t.tags = tuple(new if x == old else x for x in t.tags)
    _write_all(trades, db_path())


def delete_tag(name: str) -> None:
    """Remove from the registry and strip from every trade."""
    save_tags([t for t in load_tags() if t != name])
    trades = load()
    for t in trades:
        if name in t.tags:
            t.tags = tuple(x for x in t.tags if x != name)
    _write_all(trades, db_path())
