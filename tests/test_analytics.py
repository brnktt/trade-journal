"""Tests built around the real trades that motivated this tool.

The 2026-06-24 session: 4 trades, two winners turned into break-even by
dragging the stop. A +1.6R day became a -1R day. The leak report must show it.
"""

import unittest

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


class AnalyticsTest(unittest.TestCase):
    def test_realized_vs_plan_swing(self):
        r = analyze(june24_session())
        # Realized: -1 (loss) + 0 + 0 + 0 = -1R
        self.assertEqual(round(r.realized_r, 2), -1.0)
        # Plan-traded: -1 + 0 + 1.3 + 1.3 = +1.6R
        self.assertEqual(round(r.plan_r, 2), 1.6)
        # Leak = plan - realized = 2.6R
        self.assertEqual(round(r.leak_r, 2), 2.6)

    def test_leak_attributed_to_dragged_stops(self):
        r = analyze(june24_session())
        # Both leaking trades were dragged stops -> 2.6R credited there.
        self.assertEqual(round(r.leak_dragged_r, 2), 2.6)
        self.assertEqual(round(r.leak_out_of_plan_r, 2), 0.0)

    def test_setup_hit_rate_vs_realized_win_rate(self):
        r = analyze(june24_session())
        # Setups reached target on 2 of 4 trades...
        self.assertEqual(round(r.setup_hit_rate, 2), 0.50)
        # ...but zero were banked as wins. The whole story in two numbers.
        self.assertEqual(r.wins, 0)
        self.assertEqual(r.realized_win_rate, 0.0)

    def test_usd_view(self):
        r = analyze(june24_session())
        self.assertEqual(round(r.realized_usd), -500)
        self.assertEqual(round(r.leak_usd), 1300)  # the $1,300 swing

    def test_missed_setup_opportunity_cost(self):
        trades = [
            Trade(date="2026-06-26", setup="5m SIBI", risk_usd=500,
                  planned_rr=1.3, result="missed", target_hit=True),
        ]
        r = analyze(trades)
        self.assertEqual(r.n_executed, 0)
        self.assertEqual(r.n_missed, 1)
        self.assertEqual(r.missed_would_win, 1)
        self.assertEqual(round(r.forgone_r, 2), 1.3)

    def test_clean_day_no_leak(self):
        trades = [
            Trade(date="2026-07-01", setup="5m SIBI", risk_usd=500,
                  planned_rr=1.3, result="win", target_hit=True),
            Trade(date="2026-07-01", setup="5m SIBI", risk_usd=500,
                  planned_rr=1.3, result="loss", target_hit=False),
        ]
        r = analyze(trades)
        self.assertEqual(round(r.leak_r, 2), 0.0)
        self.assertEqual(round(r.realized_r, 2), 0.30)
        self.assertEqual(round(r.plan_r, 2), 0.30)

    def test_empty(self):
        r = analyze([])
        self.assertEqual(r.n_executed, 0)
        self.assertEqual(r.realized_win_rate, 0.0)  # no div-by-zero
        self.assertEqual(r.leak_r, 0.0)

    def test_partial_with_realized_r_counts_as_win(self):
        # partial that banked 0.6R is a win; a 0R partial is not.
        trades = [
            Trade(date="2026-07-02", result="partial", realized_r=0.6,
                  risk_usd=500, target_hit=True, planned_rr=1.3),
            Trade(date="2026-07-02", result="partial", realized_r=0,
                  risk_usd=500),
        ]
        r = analyze(trades)
        self.assertEqual(r.wins, 1)
        self.assertEqual(r.realized_win_rate, 0.5)
        # leak: only the target-hit partial leaks (1.3 - 0.6)
        self.assertEqual(round(r.leak_r, 2), 0.70)


if __name__ == "__main__":
    unittest.main()
