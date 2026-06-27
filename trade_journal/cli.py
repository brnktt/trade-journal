"""Command-line interface: `journal add`, `journal stats`, `journal list`."""

from __future__ import annotations

import argparse
import datetime as dt

from . import storage
from .analytics import analyze, format_report
from .models import PRICE_ACTION, RESULTS, Trade


def _prompt(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{label}{suffix}: ").strip()
    return value or default


def _prompt_bool(label: str, default: bool = False) -> bool:
    d = "y" if default else "n"
    value = input(f"{label} (y/n) [{d}]: ").strip().lower()
    if not value:
        return default
    return value in ("y", "yes", "1", "true", "t")


def cmd_add(args: argparse.Namespace) -> int:
    today = dt.date.today().isoformat()

    if args.result:  # non-interactive path (flags provided)
        trade = Trade(
            date=args.date or today,
            instrument=args.instrument or "",
            timeframe=args.timeframe or "",
            session=args.session or "ny am",
            direction=args.direction or "",
            setup=args.setup or "",
            grade=args.grade or 0,
            price_action=args.price_action or "choppy",
            risk_usd=args.risk or 0.0,
            planned_rr=args.rr if args.rr is not None else 1.3,
            result=args.result,
            duration_min=args.duration or 0,
            realized_r=args.realized_r,
            target_hit=args.target_hit,
            dragged_stop=args.dragged_stop,
            out_of_plan=args.out_of_plan,
            reversal_zone=args.reversal_zone,
            notes=args.notes or "",
        )
    else:  # interactive
        print("Log a trade (Enter accepts the [default]).\n")
        date = _prompt("Date", today)
        instrument = _prompt("Instrument", "NQ")
        timeframe = _prompt("Timeframe", "30s")
        session = _prompt("Session", "ny am")
        direction = _prompt("Direction (long/short)", "long")
        setup = _prompt("Setup", "")
        grade = int(_prompt("Setup grade 1-5", "") or 0)
        price_action = _prompt(f"Price action {PRICE_ACTION}", "choppy").lower()
        risk = float(_prompt("Risk $", "500") or 0)
        rr = float(_prompt("Planned R:R", "1.3") or 0)
        result = _prompt(f"Result {RESULTS}", "be").lower()
        realized_r = (
            float(_prompt("What RR was realized?", "0") or 0)
            if result == "partial" else None
        )
        duration_min = int(_prompt("Duration (min)", "") or 0)
        target_hit = _prompt_bool("Did price reach your target?")
        dragged_stop = _prompt_bool("Did you move/drag the stop?")
        out_of_plan = _prompt_bool("Was this trade out-of-plan?")
        reversal_zone = _prompt_bool("Entered a Reversal zone before target?")
        notes = _prompt("Notes", "")
        trade = Trade(
            date=date,
            instrument=instrument,
            timeframe=timeframe,
            direction=direction,
            session=session,
            setup=setup,
            grade=grade,
            price_action=price_action,
            duration_min=duration_min,
            realized_r=realized_r,
            risk_usd=risk,
            planned_rr=rr,
            result=result,
            target_hit=target_hit,
            dragged_stop=dragged_stop,
            out_of_plan=out_of_plan,
            reversal_zone=reversal_zone,
            notes=notes,
        )

    storage.append(trade)
    leak = trade.leak_r()
    msg = f"Logged {trade.result.upper()} {trade.setup or trade.instrument}"
    if leak > 1e-9:
        msg += f"  ⚠ leaked {leak:.2f}R vs plan"
    print(msg)
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    trades = storage.load()
    if args.since:
        trades = [t for t in trades if t.date >= args.since]
    print(format_report(analyze(trades)))
    return 0


def _render_table(headers: list[str], rows: list[list], aligns: str) -> str:
    """Box-drawing table sized to its widest cell — nothing is truncated."""
    cols = list(zip(*([headers] + rows)))
    widths = [max(len(str(c)) for c in col) for col in cols]

    def fmt(cells) -> str:
        return " │ ".join(
            (str(c).rjust(w) if a == "r" else str(c).ljust(w))
            for c, w, a in zip(cells, widths, aligns)
        )

    sep = "─┼─".join("─" * w for w in widths)
    return "\n".join([fmt(headers), sep, *(fmt(r) for r in rows)])


def cmd_list(args: argparse.Namespace) -> int:
    trades = storage.load()[-args.n:]
    if not trades:
        print("No trades logged yet.")
        return 0
    headers = ["id", "date", "session", "setup", "dir", "grade", "pa",
               "result", "dur", "realR", "leakR", "flags"]
    rows = []
    for t in trades:
        flags = ",".join(
            f for f, on in (
                ("drag", t.dragged_stop),
                ("oop", t.out_of_plan),
                ("zone", t.reversal_zone),
            ) if on
        )
        rows.append([
            t.id, t.date, t.session, t.setup or "-", t.direction,
            t.grade or "-", t.price_action, t.result, t.duration_min or "-",
            f"{t.effective_realized_r():+.2f}", f"{t.leak_r():.2f}",
            flags or "-",
        ])
    print(_render_table(headers, rows, aligns="rllllrlllrrl"))
    return 0


def cmd_delete(args: argparse.Namespace) -> int:
    if storage.delete(args.id):
        print(f"Deleted trade {args.id}")
        return 0
    print(f"No trade with id {args.id}")
    return 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="journal", description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    a = sub.add_parser("add", help="log a trade (interactive, or via flags)")
    a.add_argument("--date")
    a.add_argument("--instrument")
    a.add_argument("--timeframe")
    a.add_argument("--session")
    a.add_argument("--direction")
    a.add_argument("--setup")
    a.add_argument("--grade", type=int, choices=range(1, 6), help="setup quality 1-5")
    a.add_argument("--price-action", help=f"{'/'.join(PRICE_ACTION)} (prefix ok, e.g. d)")
    a.add_argument("--duration", type=int, help="time in trade, minutes")
    a.add_argument("--risk", type=float)
    a.add_argument("--rr", type=float)
    a.add_argument("--result", choices=RESULTS)
    a.add_argument("--realized-r", type=float, help="R actually banked (for partial)")
    a.add_argument("--target-hit", action="store_true")
    a.add_argument("--dragged-stop", action="store_true")
    a.add_argument("--out-of-plan", action="store_true")
    a.add_argument("--reversal-zone", action="store_true")
    a.add_argument("--notes")
    a.set_defaults(func=cmd_add)

    s = sub.add_parser("stats", help="print the performance & leak report")
    s.add_argument("--since", help="only trades on/after this date (YYYY-MM-DD)")
    s.set_defaults(func=cmd_stats)

    l = sub.add_parser("list", help="show recent trades")
    l.add_argument("-n", type=int, default=20, help="how many to show")
    l.set_defaults(func=cmd_list)

    d = sub.add_parser("delete", help="delete a trade by id")
    d.add_argument("id", type=int)
    d.set_defaults(func=cmd_delete)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
