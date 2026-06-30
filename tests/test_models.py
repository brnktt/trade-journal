"""Trade model: validation, R-accounting, tag/price-action handling, round-trip."""

import unittest

from trade_journal.models import FIELDNAMES, Trade


class ValidationTest(unittest.TestCase):
    def test_bad_result_rejected(self):
        with self.assertRaises(ValueError):
            Trade("2026-06-30", result="moon")

    def test_grade_range_enforced(self):
        Trade("2026-06-30", grade=1)   # ok
        Trade("2026-06-30", grade=5)   # ok
        Trade("2026-06-30", grade=0)   # 0 = ungraded, allowed
        with self.assertRaises(ValueError):
            Trade("2026-06-30", grade=6)

    def test_price_action_validated(self):
        with self.assertRaises(ValueError):
            Trade("2026-06-30", price_action="ranging")

    def test_price_action_prefix_autocomplete(self):
        self.assertEqual(Trade("2026-06-30", price_action="d").price_action,
                         "directional")
        self.assertEqual(Trade("2026-06-30", price_action="c").price_action,
                         "choppy")
        self.assertEqual(Trade("2026-06-30", price_action="DIRECT").price_action,
                         "directional")


class RAccountingTest(unittest.TestCase):
    def test_win_banks_planned_rr(self):
        t = Trade("2026-06-30", result="win", planned_rr=1.3, target_hit=True)
        self.assertEqual(t.effective_realized_r(), 1.3)
        self.assertEqual(t.leak_r(), 0.0)

    def test_dragged_winner_leaks(self):
        t = Trade("2026-06-30", result="be", planned_rr=1.3,
                  target_hit=True, dragged_stop=True)
        self.assertEqual(t.plan_r(), 1.3)
        self.assertEqual(t.effective_realized_r(), 0.0)
        self.assertAlmostEqual(t.leak_r(), 1.3)

    def test_loss_no_leak(self):
        t = Trade("2026-06-30", result="loss", target_hit=False)
        self.assertEqual(t.effective_realized_r(), -1.0)
        self.assertEqual(t.leak_r(), 0.0)

    def test_missed_forgone(self):
        t = Trade("2026-06-30", result="missed", planned_rr=1.3, target_hit=True)
        self.assertFalse(t.is_executed)
        self.assertEqual(t.forgone_r(), 1.3)
        self.assertEqual(t.leak_r(), 0.0)

    def test_realized_r_override(self):
        t = Trade("2026-06-30", result="partial", realized_r=0.6)
        self.assertEqual(t.effective_realized_r(), 0.6)


class IsWinTest(unittest.TestCase):
    def test_win_always(self):
        self.assertTrue(Trade("2026-06-30", result="win").is_win)

    def test_partial_only_if_banked(self):
        self.assertTrue(Trade("2026-06-30", result="partial", realized_r=0.6).is_win)
        self.assertFalse(Trade("2026-06-30", result="partial", realized_r=0).is_win)
        self.assertFalse(Trade("2026-06-30", result="partial").is_win)  # default 0

    def test_loss_be_missed_not_win(self):
        for res in ("loss", "be", "missed"):
            self.assertFalse(Trade("2026-06-30", result=res).is_win)


class SerializationTest(unittest.TestCase):
    def test_round_trip_full(self):
        t = Trade(
            date="2026-06-30", id=7, instrument="NQ", timeframe="1m",
            session="ny pm", direction="short", setup="3m SIBI", grade=4,
            price_action="directional", risk_usd=500, planned_rr=1.3,
            result="partial", duration_min=12, target_hit=True,
            dragged_stop=True, out_of_plan=False, reversal_zone=True,
            entry=21000.5, sl=20990, tp=21030, realized_r=0.6,
            tags=("fomo", "news"), notes="ok",
        )
        back = Trade.from_row(t.to_row())
        self.assertEqual(back, t)

    def test_id_is_first_column(self):
        self.assertEqual(FIELDNAMES[0], "id")
        self.assertIn("tags", FIELDNAMES)

    def test_tags_space_joined(self):
        row = Trade("2026-06-30", tags=("a", "b")).to_row()
        self.assertEqual(row["tags"], "a b")
        self.assertEqual(Trade.from_row({"date": "x", "tags": "a b"}).tags,
                         ("a", "b"))

    def test_missing_columns_use_defaults(self):
        # an old CSV row with only the original columns still loads
        t = Trade.from_row({"date": "2026-06-30", "result": "be"})
        self.assertEqual(t.id, 0)
        self.assertEqual(t.session, "ny am")
        self.assertEqual(t.price_action, "choppy")
        self.assertEqual(t.tags, ())


if __name__ == "__main__":
    unittest.main()
