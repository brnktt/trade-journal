"""Turn a list of trades into the numbers that matter.

The headline is the leak report: realized vs plan-traded performance, and the
attribution of the gap to specific behaviours (dragged stops, out-of-plan
trades) plus the opportunity cost of missed setups.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import Trade


@dataclass
class Report:
    n_executed: int
    n_missed: int
    wins: int
    realized_win_rate: float       # wins / executed
    setup_hit_rate: float          # target_hit / executed (edge before execution)
    realized_r: float
    plan_r: float
    leak_r: float
    expectancy_r: float            # realized R per executed trade
    plan_expectancy_r: float       # plan R per executed trade
    leak_dragged_r: float
    leak_out_of_plan_r: float
    leak_other_r: float
    missed_would_win: int
    forgone_r: float
    avg_risk_usd: float

    # convenience $ views (using average risk; trades may differ)
    @property
    def realized_usd(self) -> float:
        return self.realized_r * self.avg_risk_usd

    @property
    def plan_usd(self) -> float:
        return self.plan_r * self.avg_risk_usd

    @property
    def leak_usd(self) -> float:
        return self.leak_r * self.avg_risk_usd


def _safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0


def analyze(trades: list[Trade]) -> Report:
    executed = [t for t in trades if t.is_executed]
    missed = [t for t in trades if not t.is_executed]

    n_exec = len(executed)
    wins = sum(1 for t in executed if t.result == "win")
    realized_r = sum(t.effective_realized_r() for t in executed)
    plan_r = sum(t.plan_r() for t in executed)
    leak_r = sum(t.leak_r() for t in executed)

    # Attribute the leak. A trade may carry more than one flag; we credit the
    # whole leak to the first matching cause in priority order so the parts sum
    # to the total.
    leak_dragged = sum(t.leak_r() for t in executed if t.dragged_stop)
    leak_oop = sum(
        t.leak_r() for t in executed if t.out_of_plan and not t.dragged_stop
    )
    leak_other = leak_r - leak_dragged - leak_oop

    avg_risk = _safe_div(
        sum(t.risk_usd for t in executed), n_exec
    )

    return Report(
        n_executed=n_exec,
        n_missed=len(missed),
        wins=wins,
        realized_win_rate=_safe_div(wins, n_exec),
        setup_hit_rate=_safe_div(
            sum(1 for t in executed if t.target_hit), n_exec
        ),
        realized_r=realized_r,
        plan_r=plan_r,
        leak_r=leak_r,
        expectancy_r=_safe_div(realized_r, n_exec),
        plan_expectancy_r=_safe_div(plan_r, n_exec),
        leak_dragged_r=leak_dragged,
        leak_out_of_plan_r=leak_oop,
        leak_other_r=leak_other,
        missed_would_win=sum(1 for t in missed if t.target_hit),
        forgone_r=sum(t.forgone_r() for t in missed),
        avg_risk_usd=avg_risk,
    )


def format_report(report: Report) -> str:
    r = report
    if r.n_executed == 0 and r.n_missed == 0:
        return "No trades logged yet. Add one with: journal add"

    lines = [
        "",
        "════════════════════ TRADE JOURNAL ════════════════════",
        f" Executed trades : {r.n_executed}",
        f" Wins            : {r.wins}  "
        f"(realized win rate {r.realized_win_rate:.0%})",
        f" Setup hit rate  : {r.setup_hit_rate:.0%}  "
        f"(how often price reached target — your edge before execution)",
        "",
        " ── Performance ───────────────────────────────────────",
        f" Realized     : {r.realized_r:+.2f}R   "
        f"({r.realized_usd:+,.0f} @ avg ${r.avg_risk_usd:,.0f}/trade)",
        f" Plan-traded  : {r.plan_r:+.2f}R   ({r.plan_usd:+,.0f})",
        f" Expectancy   : {r.expectancy_r:+.2f}R/trade   "
        f"(plan: {r.plan_expectancy_r:+.2f}R/trade)",
    ]

    if r.leak_r > 1e-9:
        lines += [
            "",
            " ── LEAK (R left on the table vs. your plan) ──────────",
            f"  TOTAL          : -{r.leak_r:.2f}R   (-{r.leak_usd:,.0f})",
            f"   dragged stops : -{r.leak_dragged_r:.2f}R",
            f"   out-of-plan   : -{r.leak_out_of_plan_r:.2f}R",
            f"   other         : -{r.leak_other_r:.2f}R",
        ]
    else:
        lines += ["", " No execution leak — you traded your plan. ✓"]

    if r.n_missed:
        lines += [
            "",
            " ── Missed setups (opportunity cost) ─────────────────",
            f"  Missed         : {r.n_missed}  "
            f"(of which {r.missed_would_win} would have hit target)",
            f"  Forgone        : +{r.forgone_r:.2f}R not taken",
        ]

    lines.append(
        "════════════════════════════════════════════════════════"
    )
    return "\n".join(lines)
