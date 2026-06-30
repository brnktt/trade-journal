"""Storage: id assignment, trade delete, and the custom tag registry."""

import os
import tempfile
import unittest
from pathlib import Path

from trade_journal import storage
from trade_journal.models import Trade


class StorageTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._prev = os.environ.get("TRADE_JOURNAL_DB")
        os.environ["TRADE_JOURNAL_DB"] = str(Path(self.tmp.name) / "trades.csv")

    def tearDown(self):
        if self._prev is None:
            os.environ.pop("TRADE_JOURNAL_DB", None)
        else:
            os.environ["TRADE_JOURNAL_DB"] = self._prev
        self.tmp.cleanup()

    def _add(self, setup):
        t = Trade("2026-06-30", setup=setup, result="be")
        storage.append(t)
        return t

    # --- ids & delete ----------------------------------------------------
    def test_ids_increment(self):
        self._add("a"); self._add("b"); self._add("c")
        self.assertEqual([t.id for t in storage.load()], [1, 2, 3])

    def test_delete_and_no_reuse(self):
        self._add("a"); self._add("b"); self._add("c")
        self.assertTrue(storage.delete(2))
        self.assertEqual([t.id for t in storage.load()], [1, 3])
        self._add("d")  # next id is 4, not the freed 2
        self.assertEqual([t.id for t in storage.load()], [1, 3, 4])

    def test_delete_missing(self):
        self._add("a")
        self.assertFalse(storage.delete(99))
        self.assertEqual(len(storage.load()), 1)

    # --- tag registry ----------------------------------------------------
    def test_tags_sorted_unique(self):
        storage.save_tags(["news", "fomo", "fomo"])
        self.assertEqual(storage.load_tags(), ["fomo", "news"])

    def test_load_tags_empty_when_absent(self):
        self.assertEqual(storage.load_tags(), [])

    def test_tags_paired_to_db(self):
        self.assertTrue(str(storage.tags_path()).endswith("trades.tags.json"))

    def test_rename_propagates(self):
        storage.save_tags(["fomo"])
        t = Trade("2026-06-30", setup="x", result="be", tags=("fomo",))
        storage.append(t)
        storage.rename_tag("fomo", "tilt")
        self.assertEqual(storage.load_tags(), ["tilt"])
        self.assertEqual(storage.load()[0].tags, ("tilt",))

    def test_delete_propagates(self):
        storage.save_tags(["fomo", "news"])
        storage.append(Trade("2026-06-30", setup="x", result="be",
                             tags=("fomo", "news")))
        storage.delete_tag("news")
        self.assertEqual(storage.load_tags(), ["fomo"])
        self.assertEqual(storage.load()[0].tags, ("fomo",))


if __name__ == "__main__":
    unittest.main()
