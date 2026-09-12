#!/usr/bin/env python3
"""A stage that declares a command is answered by running it, when there is a run to run against.

`measure` and `promised` were test-phase stages judged by whether the field they fill was PRESENT
- a run-side question answered from the declaration - and the run-side stations of a repository's
own loop had no way into the conversion at all. The loop said BLOCKED at 6b while `status`
printed the test phase as 2 of 2 complete about the same run.

So `status --run RUNDIR` runs every command stage against that directory and reads the exit code
as the verdict. Zero is answered; anything else owes; a command that cannot run owes and says
why. The command's own last lines are kept as the reason, because the maker knows nothing about
what they mean and does not need to.

WHAT IS FIXED HERE IS THE MECHANISM, NOT ANY REPOSITORY'S STATIONS: the commands are `true`,
`false`, `echo` and a path that does not exist.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sch.dev import convert as CV                                          # noqa: E402
from sch.dev import points as P                                            # noqa: E402

DEVPOINTS = """\
tool: quarry
devpoints: 1
tests:
  command: ["true"]
fixture:
  command: [["true"]]
  products: []
baseline_dir: b
points:
  seam:
    what: one seam
    lives: seams
    must_declare: [api]
    example: alpha
    proves: it is read
    cannot_prove: that it is right
    convert:
      placeholder: TODO
      upstream: grain.tool
      stages:
        - name: shaping
          phase: build
          fills: [api]
          why: the api
        - name: holds
          phase: test
          fills: []
          command: ["true"]
          why: it holds
        - name: cracks
          phase: test
          fills: []
          command: ["false"]
          why: it cracks
        - name: names
          phase: test
          fills: []
          command: ["echo", "run={run}", "name={name}"]
          why: it names the run
        - name: absent
          phase: test
          fills: []
          command: ["/nonexistent/quarry-tool", "{run}"]
          why: it cannot run
{extra}"""


def _repo(extra=""):
    d = Path(tempfile.mkdtemp(prefix="sch-runstage-"))
    (d / "seams").mkdir()
    (d / "seams" / "alpha.py").write_text("SEAM = {}\n", encoding="utf-8")
    # `replace`, NOT `format`: the template carries `{run}` and `{name}` for the maker to fill.
    (d / "DEVPOINTS.yaml").write_text(DEVPOINTS.replace("{extra}", extra), encoding="utf-8")
    return d


class AnsweredByRunning(unittest.TestCase):
    def setUp(self):
        self.d = _repo()
        self.doc = P.load(self.d)
        self.run = Path(tempfile.mkdtemp(prefix="sch-run-"))

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)
        shutil.rmtree(self.run, ignore_errors=True)

    def _rows(self, run=""):
        return {r["stage"]: r for r in CV.status({"api": 1}, self.doc, "seam", "alpha", run=run)}

    def test_without_a_run_a_verifying_stage_is_unasked_and_not_done(self):
        rows = self._rows()
        for st in ("holds", "cracks", "names", "absent"):
            self.assertEqual(rows[st]["ran"], {}, st)
            self.assertTrue(rows[st]["unasked"], st)
            self.assertFalse(rows[st]["done"], st)
        self.assertFalse(rows["shaping"]["unasked"])
        text = CV.format_status(list(rows.values()), "alpha", "seam", doc=self.doc,
                                root=str(self.d))
        self.assertIn("RUN? holds", text)
        self.assertIn("not asked", text)
        self.assertIn("test: 0 of 4 complete", text)

    def test_with_a_run_nothing_is_unasked(self):
        rows = self._rows(run=self.run)
        self.assertFalse(any(r["unasked"] for r in rows.values()))

    def test_zero_answers(self):
        rows = self._rows(run=self.run)
        self.assertTrue(rows["holds"]["done"])
        self.assertEqual(rows["holds"]["ran"]["rc"], 0)
        self.assertFalse(rows["holds"]["ran"]["owes"])

    def test_non_zero_owes(self):
        rows = self._rows(run=self.run)
        self.assertFalse(rows["cracks"]["done"])
        self.assertTrue(rows["cracks"]["ran"]["owes"])
        self.assertEqual(rows["cracks"]["ran"]["rc"], 1)

    def test_the_run_and_the_name_reach_the_command(self):
        rows = self._rows(run=self.run)
        says = " ".join(rows["names"]["ran"]["says"])
        self.assertIn(f"run={self.run}", says)
        self.assertIn("name=alpha", says)
        self.assertEqual(rows["names"]["ran"]["argv"][0], "echo")

    def test_a_command_that_cannot_run_owes_and_says_why(self):
        rows = self._rows(run=self.run)
        self.assertTrue(rows["absent"]["ran"]["owes"])
        self.assertIsNone(rows["absent"]["ran"]["rc"])
        self.assertIn("could not run", " ".join(rows["absent"]["ran"]["says"]))
        self.assertFalse(rows["absent"]["done"])

    def test_a_build_stage_is_never_run(self):
        rows = self._rows(run=self.run)
        self.assertEqual(rows["shaping"]["ran"], {})

    def test_the_status_prints_the_verdict_and_the_tail(self):
        rows = CV.status({"api": 1}, self.doc, "seam", "alpha", run=str(self.run))
        text = CV.format_status(rows, "alpha", "seam", doc=self.doc, root=str(self.d),
                                run=str(self.run))
        self.assertIn("answered by running", text)
        self.assertIn("ran:  true", text)
        self.assertIn("OWES  (exit 1)", text)
        self.assertIn("answered  (exit 0)", text)
        self.assertIn("could not run", text)
        self.assertIn("test: 2 of 4 complete", text)


class AStageFillsOrRuns(unittest.TestCase):
    def test_a_stage_that_fills_nothing_and_runs_nothing_is_refused(self):
        d = _repo(extra="        - name: idle\n          phase: test\n          fills: []\n"
                        "          why: nothing\n")
        try:
            with self.assertRaises(CV.ConvertError) as cm:
                CV.plan(P.load(d), "seam")
            self.assertIn("idle", str(cm.exception))
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_a_stage_with_no_fills_key_at_all_is_still_refused(self):
        d = _repo(extra="        - name: bare\n          phase: test\n          command: [true]\n"
                        "          why: no fills key\n")
        try:
            with self.assertRaises(CV.ConvertError) as cm:
                CV.plan(P.load(d), "seam")
            self.assertIn("fills", str(cm.exception))
        finally:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
