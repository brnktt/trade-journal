"""Core data model for a single trade and its R-multiple accounting.

The key idea: every executed trade has a *realized* outcome (what you banked)
and a *plan* outcome (what your written plan would have produced). When price
reaches your planned target but you didn't bank the win — because you dragged
the stop, exited early, etc. — the difference is the **leak**.
"""

from __future__ import annotations

from dataclasses import dataclass

# Executed results map to a default R-multiple (a `win` uses planned_rr).
RESULTS = ("win", "loss", "be", "partial", "missed")
_DEFAULT_R = {"loss": -1.0, "be": 0.0, "partial": 0.0, "missed": 0.0}
PRICE_ACTION = ("choppy", "directional")


def _to_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "t", "yes", "y")


def _to_float(value):
    if value is None or value == "":
        return None
    return float(value)


def _to_int(value) -> int:
    if value is None or value == "":
        return 0
    return int(float(value))


def _fmt(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


@dataclass
class Trade:
    date: str
    id: int = 0                  # storage-assigned, incremental; 0 = unsaved
    instrument: str = ""
    timeframe: str = ""
    session: str = "ny am"       # e.g. ny am / ny pm / london
    direction: str = ""          # long / short
    setup: str = ""              # e.g. "5m SIBI"
    grade: int = 0               # setup quality 1 (lowest) – 5; 0 = ungraded
    price_action: str = "choppy"  # one of PRICE_ACTION
    risk_usd: float = 0.0
    planned_rr: float = 1.3
    result: str = "be"           # one of RESULTS
    duration_min: int = 0        # time in trade, minutes (0 = unrecorded)
    target_hit: bool = False     # did price reach the planned target?
    dragged_stop: bool = False   # moved the stop after entry
    out_of_plan: bool = False    # trade not part of the written plan
    reversal_zone: bool = False  # entered a SIBI / reversal zone before target
    entry: float | None = None
    sl: float | None = None
    tp: float | None = None
    realized_r: float | None = None  # optional override; else derived
    tags: tuple[str, ...] = ()   # user-defined tags (registry-enforced in CLI)
    notes: str = ""

    # --- validation -------------------------------------------------------
    def __post_init__(self) -> None:
        self.result = self.result.strip().lower()
        if self.result not in RESULTS:
            raise ValueError(
                f"result must be one of {RESULTS}, got {self.result!r}"
            )
        if self.grade and not 1 <= self.grade <= 5:
            raise ValueError(f"grade must be 1-5, got {self.grade}")
        self.price_action = self.price_action.strip().lower()
        prefix = [p for p in PRICE_ACTION if p.startswith(self.price_action)]
        if self.price_action and len(prefix) == 1:  # "d" → "directional"
            self.price_action = prefix[0]
        if self.price_action not in PRICE_ACTION:
            raise ValueError(
                f"price_action must be one of {PRICE_ACTION}, "
                f"got {self.price_action!r}"
            )

    @property
    def is_executed(self) -> bool:
        return self.result != "missed"

    @property
    def is_win(self) -> bool:
        if self.result == "win":
            return True
        # a partial counts as a win only if it actually banked R
        return self.result == "partial" and self.effective_realized_r() > 0

    # --- R-multiple accounting -------------------------------------------
    def effective_realized_r(self) -> float:
        """R actually banked on this trade."""
        if self.realized_r is not None:
            return self.realized_r
        if self.result == "win":
            return self.planned_rr
        return _DEFAULT_R[self.result]

    def plan_r(self) -> float:
        """R the written plan would have produced.

        If the trade reached its target, the plan says you bank planned_rr —
        regardless of what you actually did. Otherwise the plan outcome and
        the realized outcome are the same (the trade genuinely didn't work).
        """
        if not self.is_executed:
            return 0.0
        if self.target_hit:
            return self.planned_rr
        return self.effective_realized_r()

    def leak_r(self) -> float:
        """R left on the table vs. trading the plan (>= 0 for executed)."""
        if not self.is_executed:
            return 0.0
        return self.plan_r() - self.effective_realized_r()

    def forgone_r(self) -> float:
        """For missed setups: R given up by not taking a trade that hit target."""
        if self.result == "missed" and self.target_hit:
            return self.planned_rr
        return 0.0

    # --- (de)serialization ------------------------------------------------
    def to_row(self) -> dict[str, str]:
        return {
            "id": _fmt(self.id),
            "date": self.date,
            "instrument": self.instrument,
            "timeframe": self.timeframe,
            "session": self.session,
            "direction": self.direction,
            "setup": self.setup,
            "grade": _fmt(self.grade),
            "price_action": self.price_action,
            "risk_usd": _fmt(self.risk_usd),
            "planned_rr": _fmt(self.planned_rr),
            "result": self.result,
            "duration_min": _fmt(self.duration_min),
            "target_hit": str(self.target_hit).lower(),
            "dragged_stop": str(self.dragged_stop).lower(),
            "out_of_plan": str(self.out_of_plan).lower(),
            "reversal_zone": str(self.reversal_zone).lower(),
            "entry": _fmt(self.entry),
            "sl": _fmt(self.sl),
            "tp": _fmt(self.tp),
            "realized_r": _fmt(self.realized_r),
            "tags": " ".join(self.tags),
            "notes": self.notes,
        }

    @classmethod
    def from_row(cls, row: dict) -> "Trade":
        return cls(
            id=_to_int(row.get("id")),
            date=row.get("date", ""),
            instrument=row.get("instrument", ""),
            timeframe=row.get("timeframe", ""),
            session=row.get("session") or "ny am",
            direction=row.get("direction", ""),
            setup=row.get("setup", ""),
            grade=_to_int(row.get("grade")),
            price_action=row.get("price_action") or "choppy",
            risk_usd=_to_float(row.get("risk_usd")) or 0.0,
            planned_rr=_to_float(row.get("planned_rr")) or 0.0,
            result=row.get("result", "be"),
            duration_min=_to_int(row.get("duration_min")),
            target_hit=_to_bool(row.get("target_hit")),
            dragged_stop=_to_bool(row.get("dragged_stop")),
            out_of_plan=_to_bool(row.get("out_of_plan")),
            reversal_zone=_to_bool(row.get("reversal_zone")),
            entry=_to_float(row.get("entry")),
            sl=_to_float(row.get("sl")),
            tp=_to_float(row.get("tp")),
            realized_r=_to_float(row.get("realized_r")),
            tags=tuple(row.get("tags", "").split()),
            notes=row.get("notes", ""),
        )


FIELDNAMES = list(Trade("").to_row().keys())
