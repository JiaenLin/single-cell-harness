#!/usr/bin/env python3
"""A stage can demand mechanism, and find it, and still not know it is the maker's output.

THE THREE CLAIMS, AND WHY THE THIRD NEEDED ITS OWN CHECK.

  DEMANDED - the stage requires that a plugin's drawing code refuses past its declared ceilings.
  CHECKED  - it finds code that does, in the plugin or in a file beside it.
  GENERATED - the code is what the maker WRITES, not a hand-written file that satisfies the check.

The first two were in place and the third was being reported without being asked. It was not a
small gap: the generator named in the declaration CRASHED for every artefact in the repository it
was written for - it wrote a six-file layout that repository had replaced, and took the artefact's
path for a directory - so the file it was said to generate had never been generated once, while
being given as the reason the mechanism was no longer hand-written.

WHAT IS CHECKED HERE IS A COMPARISON, NOT A CLAIM: the generator is run into a scratch directory
and the result compared byte for byte with what sits beside the artefact.

  DRIFTED must be reported, or the mechanism is one hand edit away from being hand-written again
  and the next regeneration silently reverts whoever made it.

  MISSING must be reported, and it is not the same answer as drift.

  A GENERATOR THAT CANNOT RUN IS `cannot say`, never a pass. Every other reader in this suite
  carries that distinction and this is the newest place it was needed.

  A REPOSITORY THAT GENERATES NOTHING GETS NO ROWS AND NO VERDICT, so adding this asks nothing of
  a repository that had no such declaration.

THE FIXTURE'S GENERATOR IS A SHELL COMMAND WRITTEN HERE, so this file names no repository's tool.
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
      upstream: wraps.tool
      stages:
        - name: shaping
          phase: build
          fills: [api]
          places_every:
            - {field: plates, named_by: use}
          generated_by:
            command: %s
"""

GENERATOR = '["{python}", "-c", "import sys,pathlib;' \
            'pathlib.Path(sys.argv[1], sys.argv[2] + \\".hone.q\\").write_text(\\"HONE\\\\n\\")",' \
            ' "{out}", "{name}"]'


class DemandedCheckedAndGeneratedAreThreeClaims(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix="generated-"))
        (self.d / "seams").mkdir()
        (self.d / "seams" / "alpha.py").write_text('PLUGIN = {"api": 1}\n', encoding="utf-8")
        self.declare(GENERATOR)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def declare(self, gen):
        (self.d / "DEVPOINTS.yaml").write_text(DEVPOINTS % gen, encoding="utf-8")
        self.doc = P.load(self.d)
        _ph, _up, stages = CV.plan(self.doc, "seam")
        self.st = stages[0]

    def rows(self):
        return CV.generated_drift(self.st, self.doc, "seam", "alpha")

    def companion(self, text):
        (self.d / "seams" / "alpha.hone.q").write_text(text, encoding="utf-8")

    def test_a_companion_that_matches_is_generated(self):
        self.companion("HONE\n")
        r = self.rows()
        self.assertEqual(["generated"], [x["verdict"] for x in r])
        self.assertIn("byte for byte", CV.generated_report(r))

    def test_a_companion_edited_by_hand_is_reported_as_drifted(self):
        self.companion("HONE\n# and one small tweak\n")
        r = self.rows()
        self.assertEqual(["DRIFTED"], [x["verdict"] for x in r])
        self.assertIn("silently reverts", CV.generated_report(r))

    def test_a_companion_that_is_absent_is_reported_as_missing_not_drifted(self):
        r = self.rows()
        self.assertEqual(["MISSING"], [x["verdict"] for x in r],
                         "an absent companion and an edited one are different answers")

    def test_a_generator_that_cannot_run_is_cannot_say_and_never_a_pass(self):
        self.companion("HONE\n")
        self.declare('["{python}", "-c", "import sys; sys.exit(9)"]')
        r = self.rows()
        self.assertEqual(["cannot say"], [x["verdict"] for x in r])
        self.assertNotIn("byte for byte", CV.generated_report(r))

    def test_a_generator_that_writes_nothing_says_so_rather_than_passing(self):
        self.companion("HONE\n")
        self.declare('["{python}", "-c", "pass"]')
        r = self.rows()
        self.assertEqual(["none"], [x["verdict"] for x in r])
        self.assertIn("wrote nothing", CV.generated_report(r))

    def test_a_stage_declaring_no_generator_is_asked_nothing(self):
        self.companion("HONE\n")
        st = dict(self.st)
        st.pop("generated_by")
        self.assertEqual([], CV.generated_drift(st, self.doc, "seam", "alpha"))
        self.assertEqual("", CV.generated_report([]))

    def test_the_stage_is_not_done_while_a_companion_has_drifted(self):
        self.companion("HONE\n# and one small tweak\n")
        rows = CV.status({"api": 1}, self.doc, "seam", "alpha")
        self.assertFalse(rows[0]["done"],
                         "the stage reported finished with its generated mechanism edited in "
                         "place - which is the asymmetry this whole stage exists to close")
        self.companion("HONE\n")
        rows = CV.status({"api": 1}, self.doc, "seam", "alpha")
        self.assertTrue(rows[0]["done"])


if __name__ == "__main__":
    unittest.main()
