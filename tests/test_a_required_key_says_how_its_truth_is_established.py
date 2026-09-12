#!/usr/bin/env python3
"""A required key no stage fills is one of four things, and the fourth is red.

`must_declare` says a key has to EXIST. Nothing said what makes it TRUE, and the coverage line
reported every key no stage filled as one kind of thing - which, on the repository this was
written for, put the conversion's input, three keys the validator refuses and two keys nothing
anywhere checks on the same line, none of it red. The two were the numbers a node is packed on.

So a point may say, per unowned key, how its truth is established - `input`, `validator`,
`measured` - and a key with no stage and no entry is CHECKED BY NOBODY. That state is printed
loudly on every status, because the alternative is what it was: a paragraph in a known-issues
file that a status never mentions.

THE DECLARATION IS VALIDATED AT LOAD. A `truth:` entry naming a key the point does not require,
or a value outside the three, is refused rather than read as nothing.
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
    must_declare: [api, grain, weight, colour, seed]
    truth:
      grain: input
      weight: validator
      colour: measured
{extra}    example: alpha
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
"""


def _repo(extra=""):
    d = Path(tempfile.mkdtemp(prefix="sch-truth-"))
    (d / "seams").mkdir()
    (d / "seams" / "alpha.py").write_text("SEAM = {}\n", encoding="utf-8")
    (d / "DEVPOINTS.yaml").write_text(DEVPOINTS.format(extra=extra), encoding="utf-8")
    return d


class FourStates(unittest.TestCase):
    def setUp(self):
        self.d = _repo()
        self.cov = CV.coverage(P.load(self.d), "seam")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_a_key_a_stage_fills_is_the_stages(self):
        self.assertEqual(self.cov["api"]["by"], "stage")
        self.assertEqual(self.cov["api"]["stages"], ["shaping"])

    def test_the_three_declared_states_are_read(self):
        self.assertEqual(self.cov["grain"]["by"], "input")
        self.assertEqual(self.cov["weight"]["by"], "validator")
        self.assertEqual(self.cov["colour"]["by"], "measured")

    def test_no_stage_and_no_entry_is_nobody(self):
        self.assertEqual(self.cov["seed"]["by"], "nobody")

    def test_nobody_is_printed_loudly_and_the_others_are_named(self):
        rep = CV.coverage_report(self.cov, "seam")
        self.assertIn("CHECKED BY NOBODY", rep)
        self.assertIn("seed", rep.split("CHECKED BY NOBODY")[1].splitlines()[0])
        self.assertIn("input to the conversion", rep)
        self.assertIn("grain", rep)
        self.assertIn("validator", rep)
        self.assertIn("measured from a run", rep)
        self.assertIn("1 of 5", rep)

    def test_every_key_owned_by_a_stage_is_one_quiet_line(self):
        cov = {k: {"by": "stage", "stages": ["s"], "says": ""} for k in ("a", "b")}
        rep = CV.coverage_report(cov, "seam")
        self.assertNotIn("NOBODY", rep)
        self.assertIn("every one of the 2", rep)

    def test_the_status_prints_the_split_when_anything_is_not_a_stages(self):
        doc = P.load(self.d)
        spec = {"api": "1", "grain": {"tool": "t"}, "weight": 2, "colour": "c", "seed": 1}
        text = CV.format_status(CV.status(spec, doc, "seam", "alpha"), "alpha", "seam", doc=doc,
                                root=str(self.d))
        self.assertIn("CHECKED BY NOBODY", text)
        self.assertIn("seed", text)


class TwoAnswersToOneQuestion(unittest.TestCase):
    def test_a_truth_entry_for_a_key_a_stage_fills_is_reported(self):
        d = _repo(extra="      api: validator\n")
        try:
            cov = CV.coverage(P.load(d), "seam")
            self.assertEqual(cov["api"]["by"], "stage")
            self.assertIn("two answers", cov["api"]["says"])
            self.assertIn("two answers", CV.coverage_report(cov, "seam"))
        finally:
            shutil.rmtree(d, ignore_errors=True)


class RefusedAtLoad(unittest.TestCase):
    def test_a_key_the_point_does_not_require_is_refused(self):
        d = _repo(extra="      flavour: input\n")
        try:
            with self.assertRaises(P.DevpointsError) as cm:
                P.load(d)
            self.assertIn("flavour", str(cm.exception))
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_a_value_outside_the_three_is_refused(self):
        d = _repo(extra="      seed: hopefully\n")
        try:
            with self.assertRaises(P.DevpointsError) as cm:
                P.load(d)
            self.assertIn("hopefully", str(cm.exception))
            for v in P.TRUTH:
                self.assertIn(v, str(cm.exception))
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_a_truth_that_is_not_a_mapping_is_refused(self):
        d = Path(tempfile.mkdtemp(prefix="sch-truth-"))
        try:
            (d / "seams").mkdir()
            (d / "seams" / "alpha.py").write_text("SEAM = {}\n", encoding="utf-8")
            text = DEVPOINTS.format(extra="").replace(
                "    truth:\n      grain: input\n      weight: validator\n      colour: measured\n",
                "    truth: [grain, weight]\n")
            (d / "DEVPOINTS.yaml").write_text(text, encoding="utf-8")
            with self.assertRaises(P.DevpointsError) as cm:
                P.load(d)
            self.assertIn("mapping", str(cm.exception))
        finally:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
