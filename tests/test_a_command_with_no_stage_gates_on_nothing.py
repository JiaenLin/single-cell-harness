#!/usr/bin/env python3
"""A question the suite can answer and no stage asks is help you have to know exists.

TWO OF THIS SUITE'S OWN CHECKS WERE IN THAT STATE, and both had already been paid for.

  THE ENVIRONMENT. `sch dev convert borrowed` resolves a plugin alone, resolves it with its
  family, and subtracts - so a plugin that USES a package its own declaration never asks for is
  answerable with no run at all. It was a command. A plugin in one of the repositories this suite
  serves spent its whole life in a seven-member environment depending on two packages it declared
  neither of; its selftest passed, because neither is imported at module scope; `build: 7 of 7
  complete` was printed over it; and two drawing paths died forty minutes into a cohort run.

  THE REUSE KEY. `sch dev convert freshness` asks git whether the field a repository calls its
  reuse key moved when the artefact did. It was a command. A commit rewrote a plugin's drawing
  protocol and left the key standing still, and an audit found it AFTERWARDS - which as a stage is
  found before, which is the whole difference.

WHAT IS ASSERTED HERE.

  A LENT PACKAGE IS EXPOSURE; A LOADED ONE IS A DEBT. A shared environment lends its members a
  hundred names each and almost none is touched. A stage that owed on a loan would be red on
  every member of every shared environment at once, which is a false-alarm generator and gets a
  gate switched off.

  STALE IS THE ONLY DEBT. `CANNOT SAY` - uncommitted, computed, no history - is a fact about the
  checkout and not about the plugin, and must not be reported as owing.

  A POINT THAT DOES NOT ASK IS NOT ANSWERED. Neither key costs anything in a repository whose
  declaration does not carry it: no subprocess, no resolve, no git.

  THE SURVEY IS RESOLVED ONCE. It reads the whole family, and `status` is asked of every artefact
  at a point.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sch.dev import convert as CV                                          # noqa: E402


class _Loan:
    def __init__(self, plugin, rows, complete=True, alone=False, why_not=""):
        self.plugin, self.rows, self.complete = plugin, rows, complete
        self.alone, self.why_not = alone, why_not
        self.environment = "env-abc"


class _Fresh:
    def __init__(self, verdict, complete=True, why_not=""):
        self.verdict, self.complete, self.why_not = verdict, complete, why_not
        self.field, self.declared = "version", "0.2.0"
        self.set_by, self.commits_since = {"short": "abc1234"}, [{"short": "def5678"}]


def row(entry, loaded):
    return {"entry": entry, "loaded": loaded, "written_in": "host", "at": 12, "times": 1}


class ACommandWithNoStageGatesOnNothing(unittest.TestCase):

    def setUp(self):
        self._loans = dict(CV._LOANS)
        CV._LOANS.clear()

    def tearDown(self):
        CV._LOANS.clear()
        CV._LOANS.update(self._loans)

    def loan(self, rows, **kw):
        CV._LOANS[(".", "seam", "python3")] = [_Loan("alpha", rows, **kw)]
        st = {CV.LOAN_KEY: True}
        return CV.loan_debt(st, {"_root": "."}, "seam", "alpha")

    # ---- the environment --------------------------------------------------------------

    def test_a_package_the_plugin_loads_and_never_declares_is_a_debt(self):
        d = self.loan([row("scipy", True)])
        self.assertTrue(d["owes"])
        self.assertIn("scipy", d["says"])
        self.assertIn("LOADS", d["says"])

    def test_a_lent_package_nothing_loads_is_exposure_and_not_a_debt(self):
        d = self.loan([row("pandas", False), row("numpy", False)])
        self.assertFalse(d["owes"],
                         "a stage owing on a LOAN is red on every member of every shared "
                         "environment at once")
        self.assertTrue(d["complete"])

    def test_alone_is_a_positive_answer_and_not_a_silence(self):
        d = self.loan([], alone=True)
        self.assertFalse(d["owes"])
        self.assertIn("nothing is lent", d["says"])

    def test_a_survey_that_could_not_run_does_not_owe_and_says_why(self):
        d = self.loan([], complete=False, why_not="the resolver could not be reached")
        self.assertFalse(d["owes"], "an unanswerable question was reported as a debt")
        self.assertFalse(d["complete"])
        self.assertIn("resolver", d["says"])

    def test_a_plugin_the_catalogue_does_not_list_says_so(self):
        CV._LOANS[(".", "seam", "python3")] = []
        d = CV.loan_debt({CV.LOAN_KEY: True}, {"_root": "."}, "seam", "alpha")
        self.assertFalse(d["owes"])
        self.assertIn("catalogue", d["says"])

    def test_a_point_that_does_not_ask_pays_nothing(self):
        # No key, no survey: the dict is empty and no resolve is attempted at all.
        CV._LOANS[(".", "seam", "python3")] = RuntimeError("this must never be read")
        self.assertEqual({}, CV.loan_debt({}, {"_root": "."}, "seam", "alpha"))
        self.assertEqual({}, CV.loan_debt({CV.LOAN_KEY: True}, {"_root": "."}, "seam", ""))

    def test_the_family_is_resolved_once_and_not_once_per_artefact(self):
        calls = []

        class _SE:
            @staticmethod
            def survey(doc, point, root, python="python3"):
                calls.append(1)
                return [_Loan("alpha", []), _Loan("beta", [])]

        # PATCHED ON THE PACKAGE, NOT IN sys.modules. `from .extract import shared_env` reads the
        # ATTRIBUTE of the already-imported package, so swapping the sys.modules entry changed
        # nothing and the first version of this test measured zero calls and said so.
        import sch.dev.extract as pkg
        real = pkg.shared_env
        pkg.shared_env = _SE
        try:
            for who in ("alpha", "beta", "alpha"):
                CV.loan_debt({CV.LOAN_KEY: True}, {"_root": "."}, "seam", who)
        finally:
            pkg.shared_env = real
        self.assertEqual(1, len(calls),
                         f"the whole family was resolved {len(calls)} times for 3 questions")

    # ---- the reuse key ----------------------------------------------------------------

    def version(self, f):
        from sch.dev import freshness as FR
        real = FR.check
        FR.check = lambda *_a, **_kw: f
        try:
            return CV.version_debt({CV.VERSION_KEY: True}, {}, {"_root": "."}, "seam", "alpha")
        finally:
            FR.check = real

    def test_a_reuse_key_that_stood_still_is_a_debt(self):
        from sch.dev import freshness as FR
        d = self.version(_Fresh(FR.STALE))
        self.assertTrue(d["owes"])
        self.assertIn("commit(s) have touched", d["says"])

    def test_a_key_that_kept_up_is_not(self):
        from sch.dev import freshness as FR
        self.assertFalse(self.version(_Fresh(FR.CURRENT))["owes"])

    def test_cannot_say_is_reported_and_does_not_owe(self):
        from sch.dev import freshness as FR
        d = self.version(_Fresh(FR.CANNOT_SAY, complete=False, why_not="it is not committed"))
        self.assertFalse(d["owes"],
                         "a fact about the checkout was reported as a debt of the plugin")
        self.assertIn("not a pass", d["says"])
        self.assertIn("not committed", d["says"])

    def test_a_point_that_does_not_ask_is_not_answered(self):
        self.assertEqual({}, CV.version_debt({}, {}, {"_root": "."}, "seam", "alpha"))


if __name__ == "__main__":
    unittest.main()
