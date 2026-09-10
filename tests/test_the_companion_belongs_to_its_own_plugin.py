#!/usr/bin/env python3
"""A generated companion file belongs to ONE artefact, and a shared one belongs to nobody.

THE DEFECT, MEASURED IN A REAL TREE. One of the repositories this suite serves keeps nine
one-file plugins side by side in a single directory. The maker generates a draw wrapper for any
plugin that draws through a second language, and a check asks whether the wrapper the plugin runs
actually refuses past the ceilings the plugin declares. The check found that wrapper by globbing
the plugin's PARENT DIRECTORY - so one generated file, written by whichever plugin was scaffolded
first, answered the requirement for all nine. Eight of them had never read it.

That is the borrowing defect this suite already keeps a file for at the environment point, in the
form it takes at the source-file point: green while the family is together, red the day the plugin
is deployed alone, and alone is exactly when nobody is looking at a build stage any more.

TWO SHAPES COUNT AND ONLY TWO. A file inside a directory named for the artefact, and a sibling
whose name begins with the artefact's own stem. Both say the artefact's name; a bare `draw.R`
beside nine plugins says nothing.

THE FIXTURE NAMES NO REPOSITORY THIS SUITE SERVES. Its point, its artefacts and its language are
invented, so a maker that had quietly learnt one repository's layout could not pass here.
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
"""

SEAM = 'PLUGIN = {"api": 1, "name": "%s"}\n'


class TheCompanionBelongsToItsOwnPlugin(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix="companion-"))
        (self.d / "DEVPOINTS.yaml").write_text(DEVPOINTS, encoding="utf-8")
        self.seams = self.d / "seams"
        self.seams.mkdir()
        for n in ("alpha", "beta"):
            (self.seams / f"{n}.py").write_text(SEAM % n, encoding="utf-8")
        self.doc = P.load(self.d)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def names(self, who):
        return [fn for _text, fn in CV._r_beside(self.doc, "seam", who)]

    def test_a_file_shared_by_the_whole_directory_is_nobodys(self):
        (self.seams / "draw.R").write_text("draw <- function() NULL\n", encoding="utf-8")
        self.assertEqual([], self.names("alpha"),
                         "a bare draw.R beside every seam was read as alpha's own")
        self.assertEqual([], self.names("beta"))

    def test_a_sibling_carrying_the_stem_is_that_artefacts_own(self):
        (self.seams / "alpha.draw.R").write_text("draw <- function() NULL\n", encoding="utf-8")
        self.assertEqual(["alpha.draw.R"], self.names("alpha"))
        self.assertEqual([], self.names("beta"), "beta was credited with alpha's companion")

    def test_a_directory_named_for_the_artefact_is_that_artefacts_own(self):
        sub = self.seams / "alpha"
        sub.mkdir()
        (sub / "draw.R").write_text("draw <- function() NULL\n", encoding="utf-8")
        self.assertEqual(["draw.R"], self.names("alpha"))
        self.assertEqual([], self.names("beta"))

    def test_the_artefact_itself_is_never_its_own_companion(self):
        # A point whose artefacts ARE .R files would otherwise read each one as its own companion
        # and report every plugin as carrying the generated mechanism it has never been given.
        (self.seams / "alpha.R").write_text("draw <- function() NULL\n", encoding="utf-8")
        self.assertEqual(["alpha.R"], self.names("alpha"),
                         "a sibling sharing the stem is still a companion of alpha")
        got = CV._companions(self.seams / "alpha.R", ".R")
        self.assertEqual([], [fn for _t, fn in got],
                         "alpha.R was returned as a companion of itself")

    def test_a_prefix_that_is_not_the_whole_stem_does_not_borrow(self):
        # `alphabet` starts with `alpha`. The artefact is `alpha.py`, so `alphabet.draw.R` is a
        # DIFFERENT seam's companion and must not answer for alpha.
        (self.seams / "alphabet.py").write_text(SEAM % "alphabet", encoding="utf-8")
        (self.seams / "alphabet.draw.R").write_text("draw <- function() NULL\n", encoding="utf-8")
        self.assertEqual(["alphabet.draw.R"], self.names("alphabet"))
        self.assertEqual([], self.names("alpha"),
                         "alpha was credited with alphabet's companion by a bare prefix match")


if __name__ == "__main__":
    unittest.main()
