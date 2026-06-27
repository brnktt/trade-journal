"""Command-line interface: `journal add`, `journal stats`, `journal list`."""

from __future__ import annotations

import argparse
import datetime as dt

from . import storage
from .analytics import analyze, format_report
from .models import RESULTS, Trade


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
            direction=args.direction or "",
            setup=args.setup or "",
            risk_usd=args.risk or 0.0,
            planned_rr=args.rr if args.rr is not None else 1.3,
            result=args.result,
            target_hit=args.target_hit,
            dragged_stop=args.dragged_stop,
            out_of_plan=args.out_of_plan,
            reversal_zone=args.reversal_zone,
            notes=args.notes or "",
        )
    else:  # interactive
        print("Log a trade (Enter accepts the [default]).\n")
        date = _prompt("Date", today)
        instrument = _prompt("Instrument", "ES")
        timeframe = _prompt("Timeframe", "30s")
        direction = _prompt("Direction (long/short)", "long")
        setup = _prompt("Setup", "")
        risk = float(_prompt("Risk $", "500") or 0)
        rr = float(_prompt("Planned R:R", "1.3") or 0)
        result = _prompt(f"Result {RESULTS}", "be").lower()
        target_hit = _prompt_bool("Did price reach your target?")
        dragged_stop = _prompt_bool("Did you move/drag the stop?")
        out_of_plan = _prompt_bool("Was this trade out-of-plan?")
        reversal_zone = _prompt_bool("Entered a SIBI/reversal zone before target?")
        notes = _prompt("Notes", "")
        trade = Trade(
            date=date,
            instrument=instrument,
            timeframe=timeframe,
            direction=direction,
            setup=setup,
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


def cmd_list(args: argparse.Namespace) -> int:
    trades = storage.load()[-args.n:]
    if not trades:
        print("No trades logged yet.")
        return 0
    print(f"{'date':<11}{'setup':<14}{'dir':<6}{'res':<8}"
          f"{'realR':>7}{'leakR':>7}  flags")
    for t in trades:
        flags = ",".join(
            f for f, on in (
                ("drag", t.dragged_stop),
                ("oop", t.out_of_plan),
                ("zone", t.reversal_zone),
            ) if on
        )
        setup = (t.setup or "-")[:13]
        print(f"{t.date:<11}{setup:<14}{t.direction:<6}"
              f"{t.result:<8}{t.effective_realized_r():>+7.2f}"
              f"{t.leak_r():>7.2f}  {flags}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="journal", description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    a = sub.add_parser("add", help="log a trade (interactive, or via flags)")
    a.add_argument("--date")
    a.add_argument("--instrument")
    a.add_argument("--timeframe")
    a.add_argument("--direction")
    a.add_argument("--setup")
    a.add_argument("--risk", type=float)
    a.add_argument("--rr", type=float)
    a.add_argument("--result", choices=RESULTS)
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

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
