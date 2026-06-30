"""CLI end-to-end: drive main(argv), capture output, assert behaviour."""

import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path

from trade_journal.cli import main


def run(*argv):
    """Run the CLI, returning (exit_code, stdout). stderr is swallowed."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        code = main(list(argv))
    return code, out.getvalue()


class CliTest(unittest.TestCase):
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

    # --- add / list / delete --------------------------------------------
    def test_add_then_list(self):
        self.assertEqual(run("add", "--setup", "5m FVG", "--result", "win",
                             "--target-hit")[0], 0)
        code, out = run("list")
        self.assertEqual(code, 0)
        self.assertIn("5m FVG", out)
        self.assertIn("tags", out)  # header present

    def test_delete_via_cli(self):
        run("add", "--setup", "a", "--result", "be")
        self.assertEqual(run("delete", "1")[0], 0)
        self.assertEqual(run("delete", "1")[1].strip(), "No trade with id 1")
        self.assertEqual(run("delete", "1")[0], 1)

    def test_stats_runs(self):
        run("add", "--setup", "a", "--result", "win", "--target-hit")
        code, out = run("stats")
        self.assertEqual(code, 0)
        self.assertIn("TRADE JOURNAL", out)

    # --- tag CRUD --------------------------------------------------------
    def test_tag_crud_flow(self):
        self.assertEqual(run("tags", "add", "fomo")[0], 0)
        self.assertEqual(run("tags", "add", "fomo")[0], 1)        # dup
        self.assertEqual(run("tags", "add", "drag")[0], 1)        # reserved
        self.assertEqual(run("tags", "add", "two words")[0], 1)   # spaces
        _, out = run("tags", "list")
        self.assertIn("fomo", out)

        run("tags", "add", "news")
        self.assertEqual(run("tags", "rename", "fomo", "tilt")[0], 0)
        self.assertEqual(run("tags", "rename", "missing", "x")[0], 1)
        self.assertEqual(run("tags", "delete", "news")[0], 0)
        self.assertEqual(run("tags", "delete", "news")[0], 1)     # already gone

    def test_attach_requires_existing_tag(self):
        # unknown tag at add -> argparse rejects with exit
        with self.assertRaises(SystemExit):
            run("add", "--setup", "x", "--result", "be", "--tag", "ghost")

    def test_attach_and_filter(self):
        run("tags", "add", "fomo")
        run("add", "--setup", "revenge", "--result", "loss", "--tag", "fomo",
            "--dragged-stop")
        run("add", "--setup", "clean", "--result", "win", "--target-hit")
        # custom-tag filter
        _, out = run("list", "--tag", "fomo")
        self.assertIn("revenge", out)
        self.assertNotIn("clean", out)
        # built-in tag filter
        _, out = run("list", "--tag", "drag")
        self.assertIn("revenge", out)

    def test_rename_shows_on_list(self):
        run("tags", "add", "fomo")
        run("add", "--setup", "x", "--result", "be", "--tag", "fomo")
        run("tags", "rename", "fomo", "tilt")
        _, out = run("list")
        self.assertIn("tilt", out)
        self.assertNotIn("fomo", out)


if __name__ == "__main__":
    unittest.main()
