"""Tests built around the real trades that motivated this tool.

The 2026-06-24 session: 4 trades, two winners turned into break-even by
dragging the stop. A +1.6R day became a -1R day. The leak report must show it.
"""

from trade_journal.analytics import analyze
from trade_journal.models import Trade


def june24_session() -> list[Trade]:
    return [
        # 1) 30s long, out-of-plan error, stopped out.
        Trade(date="2026-06-24", timeframe="30s", direction="long",
              setup="-", risk_usd=500, planned_rr=1.3, result="loss",
              target_hit=False, out_of_plan=True),
        # 2) 1m short, legit BE — re-swept, never reached target.
        Trade(date="2026-06-24", timeframe="1m", direction="short",
              setup="3m SIBI re-sweep", risk_usd=500, planned_rr=1.3,
              result="be", target_hit=False),
        # 3) 30s short, hit target but dragged stop -> BE.
        Trade(date="2026-06-24", timeframe="30s", direction="short",
              setup="3m SIBI", risk_usd=500, planned_rr=1.3, result="be",
              target_hit=True, dragged_stop=True),
        # 4) 1m short, hit target but dragged stop -> BE.
        Trade(date="2026-06-24", timeframe="1m", direction="short",
              setup="3m SIBI", risk_usd=500, planned_rr=1.3, result="be",
              target_hit=True, dragged_stop=True),
    ]


def test_realized_vs_plan_swing():
    r = analyze(june24_session())
    # Realized: -1 (loss) + 0 + 0 + 0 = -1R
    assert round(r.realized_r, 2) == -1.0
    # Plan-traded: -1 + 0 + 1.3 + 1.3 = +1.6R
    assert round(r.plan_r, 2) == 1.6
    # Leak = plan - realized = 2.6R
    assert round(r.leak_r, 2) == 2.6


def test_leak_attributed_to_dragged_stops():
    r = analyze(june24_session())
    # Both leaking trades were dragged stops -> 2.6R credited there.
    assert round(r.leak_dragged_r, 2) == 2.6
    assert round(r.leak_out_of_plan_r, 2) == 0.0


def test_setup_hit_rate_vs_realized_win_rate():
    r = analyze(june24_session())
    # Setups reached target on 2 of 4 trades...
    assert round(r.setup_hit_rate, 2) == 0.50
    # ...but zero were banked as wins. The whole story in two numbers.
    assert r.wins == 0
    assert r.realized_win_rate == 0.0


def test_usd_view():
    r = analyze(june24_session())
    assert round(r.realized_usd) == -500
    assert round(r.leak_usd) == 1300  # the $1,300 swing


def test_missed_setup_opportunity_cost():
    trades = [
        Trade(date="2026-06-26", setup="5m SIBI", risk_usd=500,
              planned_rr=1.3, result="missed", target_hit=True),
    ]
    r = analyze(trades)
    assert r.n_executed == 0
    assert r.n_missed == 1
    assert r.missed_would_win == 1
    assert round(r.forgone_r, 2) == 1.3


def test_clean_day_no_leak():
    trades = [
        Trade(date="2026-07-01", setup="5m SIBI", risk_usd=500,
              planned_rr=1.3, result="win", target_hit=True),
        Trade(date="2026-07-01", setup="5m SIBI", risk_usd=500,
              planned_rr=1.3, result="loss", target_hit=False),
    ]
    r = analyze(trades)
    assert round(r.leak_r, 2) == 0.0
    assert round(r.realized_r, 2) == round(r.plan_r, 2) == 0.30
