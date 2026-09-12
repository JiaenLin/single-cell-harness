#!/usr/bin/env python3
"""The status banners a held-out artefact and the round's maker output, before any debt.

The rule that forbids repairing a held-out plugin lived in a declaration nobody reads while
working, and the routing loop that follows from it - host fix, maker fix, worksheet answer,
held-out record - lived in one session's memory. A status that lists "35 silent draw sites, fix
them" about a held-out plugin is an instruction to break the round. So the first lines of a
status say which side of the rules the named plugin is on, read from the same `rules:` block
`sch dev rules` checks.

A repository declaring no rules gets no banner: inventing one would be this tool deciding how
somebody else's round works.
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
{rules}points:
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
"""

RULES = """\
rules:
  since:
    commit: HEAD
    means: now
  maker_output:
    min_block: 8
    means: generated
  held_out:
    names: [ki, ko]
    means: the test set
  in_place:
    paths: [seams]
    means: mechanism
  end_to_end:
    names: [alpha]
    means: the one being converted
"""


def _repo(rules=""):
    d = Path(tempfile.mkdtemp(prefix="sch-side-"))
    (d / "seams").mkdir()
    for n in ("alpha", "ki", "ko", "ku"):
        (d / "seams" / f"{n}.py").write_text("SEAM = {}\n", encoding="utf-8")
    (d / "DEVPOINTS.yaml").write_text(DEVPOINTS.replace("{rules}", rules), encoding="utf-8")
    return d


def _status(d, name):
    doc = P.load(d)
    return CV.format_status(CV.status({"api": 1}, doc, "seam", name), name, "seam", doc=doc,
                            root=str(d))


class WithRules(unittest.TestCase):
    def setUp(self):
        self.d = _repo(RULES)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_a_held_out_artefact_is_bannered_first(self):
        text = _status(self.d, "ki")
        self.assertTrue(text.lstrip().startswith("HELD OUT: ki"), text[:200])
        self.assertIn("never a fix", text)
        self.assertIn("sch dev rules", text)

    def test_the_maker_output_is_bannered_first(self):
        text = _status(self.d, "alpha")
        self.assertTrue(text.lstrip().startswith("MAKER OUTPUT: alpha"), text[:200])
        self.assertIn("never by hand-editing", text)

    def test_an_artefact_on_neither_list_gets_no_banner(self):
        text = _status(self.d, "ku")
        self.assertNotIn("HELD OUT", text)
        self.assertNotIn("MAKER OUTPUT", text)

    def test_the_banner_names_come_from_the_rules_block_and_nowhere_else(self):
        self.assertEqual(CV._side_of_the_rules(P.load(self.d), "ko")[0].split(":")[0].strip(),
                         "HELD OUT")
        self.assertEqual(CV._side_of_the_rules(P.load(self.d), ""), [])


class WithoutRules(unittest.TestCase):
    def test_no_rules_no_banner(self):
        d = _repo("")
        try:
            text = _status(d, "ki")
            self.assertNotIn("HELD OUT", text)
            self.assertNotIn("MAKER OUTPUT", text)
            self.assertEqual(CV._side_of_the_rules(P.load(d), "ki"), [])
        finally:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
