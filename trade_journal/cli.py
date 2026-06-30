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
            tags=tuple(args.tag or ()),
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
        registry = storage.load_tags()
        hint = f" {registry}" if registry else " (none yet — journal tags add)"
        tags = _known_only(_prompt(f"Tags{hint}", "").split(), registry)
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
            tags=tags,
            notes=notes,
        )

    storage.append(trade)
    leak = trade.leak_r()
    msg = f"Logged {trade.result.upper()} {trade.setup or trade.instrument}"
    if leak > 1e-9:
        msg += f"  ⚠ leaked {leak:.2f}R vs plan"
    print(msg)
    return 0


# Built-in behaviour tags (fixed; they drive leak attribution in stats).
_BUILTIN_TAGS = {
    "drag": lambda t: t.dragged_stop,
    "oop": lambda t: t.out_of_plan,
    "zone": lambda t: t.reversal_zone,
}


def _trade_tags(t: Trade) -> list[str]:
    """All tags on a trade: active built-ins + custom, in display order."""
    return [name for name, on in _BUILTIN_TAGS.items() if on(t)] + list(t.tags)


def _filterable_tags() -> list[str]:
    """Tags you can filter by = built-ins + the custom registry."""
    return list(_BUILTIN_TAGS) + storage.load_tags()


def _load_filtered(args: argparse.Namespace) -> list[Trade]:
    trades = storage.load()
    if getattr(args, "since", None):
        trades = [t for t in trades if t.date >= args.since]
    for tag in getattr(args, "tag", None) or []:  # AND across tags
        trades = [t for t in trades if tag in _trade_tags(t)]
    return trades


def cmd_stats(args: argparse.Namespace) -> int:
    print(format_report(analyze(_load_filtered(args))))
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
    trades = _load_filtered(args)[-args.n:]
    if not trades:
        print("No trades logged yet.")
        return 0
    headers = ["id", "date", "session", "setup", "dir", "grade", "pa",
               "result", "dur", "realR", "leakR", "tags"]
    rows = []
    for t in trades:
        tags = ",".join(_trade_tags(t))
        rows.append([
            t.id, t.date, t.session, t.setup or "-", t.direction,
            t.grade or "-", t.price_action, t.result, t.duration_min or "-",
            f"{t.effective_realized_r():+.2f}", f"{t.leak_r():.2f}",
            tags or "-",
        ])
    print(_render_table(headers, rows, aligns="rllllrlllrrl"))
    return 0


def cmd_delete(args: argparse.Namespace) -> int:
    if storage.delete(args.id):
        print(f"Deleted trade {args.id}")
        return 0
    print(f"No trade with id {args.id}")
    return 1


# --- custom tag registry (CRUD) ------------------------------------------
def _known_only(names: list[str], registry: list[str]) -> tuple[str, ...]:
    """Keep names that are registered tags; warn (don't fail) on the rest."""
    keep = []
    for n in names:
        n = n.strip().lower()
        if n in registry:
            keep.append(n)
        elif n:
            print(f"  ⚠ unknown tag {n!r} (create with: journal tags add {n}) — skipped")
    return tuple(keep)


def _check_new_name(name: str) -> str | None:
    """Normalize a proposed tag name, or return an error string."""
    name = name.strip().lower()
    if not name or " " in name:
        return "tag name must be one word, no spaces"
    if name in _BUILTIN_TAGS:
        return f"{name!r} is a built-in tag and can't be redefined"
    return None


def cmd_tags(args: argparse.Namespace) -> int:
    registry = storage.load_tags()

    if args.tagcmd == "list":
        print("Built-in:", ", ".join(_BUILTIN_TAGS))
        print("Custom  :", ", ".join(registry) if registry else "(none)")
        return 0

    if args.tagcmd == "add":
        name = args.name.strip().lower()
        if err := _check_new_name(name):
            print(err)
            return 1
        if name in registry:
            print(f"Tag {name!r} already exists")
            return 1
        storage.save_tags(registry + [name])
        print(f"Added tag {name!r}")
        return 0

    if args.tagcmd == "rename":
        old, new = args.old.strip().lower(), args.new.strip().lower()
        if old not in registry:
            print(f"No custom tag {old!r}")
            return 1
        if err := _check_new_name(new):
            print(err)
            return 1
        if new in registry:
            print(f"Tag {new!r} already exists")
            return 1
        storage.rename_tag(old, new)
        print(f"Renamed {old!r} → {new!r} (updated on all trades)")
        return 0

    # delete
    name = args.name.strip().lower()
    if name not in registry:
        print(f"No custom tag {name!r}")
        return 1
    storage.delete_tag(name)
    print(f"Deleted tag {name!r} (removed from all trades)")
    return 0


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
    a.add_argument("--tag", action="append", choices=storage.load_tags(),
                   help="attach a custom tag (repeatable; must exist)")
    a.add_argument("--notes")
    a.set_defaults(func=cmd_add)

    s = sub.add_parser("stats", help="print the performance & leak report")
    s.add_argument("--since", help="only trades on/after this date (YYYY-MM-DD)")
    s.add_argument("--tag", action="append", choices=_filterable_tags(),
                   help="only trades with this tag (repeatable, AND)")
    s.set_defaults(func=cmd_stats)

    l = sub.add_parser("list", help="show recent trades")
    l.add_argument("-n", type=int, default=20, help="how many to show")
    l.add_argument("--tag", action="append", choices=_filterable_tags(),
                   help="only trades with this tag (repeatable, AND)")
    l.set_defaults(func=cmd_list)

    d = sub.add_parser("delete", help="delete a trade by id")
    d.add_argument("id", type=int)
    d.set_defaults(func=cmd_delete)

    tg = sub.add_parser("tags", help="manage custom tags (add/list/rename/delete)")
    tgs = tg.add_subparsers(dest="tagcmd", required=True)
    tgs.add_parser("list", help="show built-in and custom tags")
    tgs.add_parser("add", help="create a custom tag").add_argument("name")
    tgr = tgs.add_parser("rename", help="rename a custom tag everywhere")
    tgr.add_argument("old")
    tgr.add_argument("new")
    tgs.add_parser("delete", help="delete a custom tag everywhere").add_argument("name")
    tg.set_defaults(func=cmd_tags)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
