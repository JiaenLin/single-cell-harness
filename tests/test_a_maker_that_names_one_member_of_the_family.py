#!/usr/bin/env python3
"""A general maker may name a convention. It may not name one member of the family.

WHAT THIS INSTRUMENT IS FOR. The evidence that a maker generalises is a plugin it has never seen,
and that evidence is spent the moment it is used. Between conversions there is nothing to appeal to
but the maker's own source. `sch dev convert overfit` measures the two things that CAN be read off
a family with no run: how many artefacts each instrument could look at, and whether any constant in
the maker names a single member's upstream.

EVERY CASE BELOW IS A FALSE ALARM THIS SCAN ACTUALLY RAISED, or a real finding it actually missed.

  PROSE IS NOT CODE. The first version asked whether a literal occurred in exactly one artefact's
  file. The artefacts of the family it was written for are several thousand lines each and mostly
  English, so `cache`, `detail`, `digest` and `dump` each landed in exactly one of them by
  coincidence and were reported as fitted constants - thirty rows of noise around two real
  findings. Asking the DECLARATION which names are the upstream's took it to zero.

  A SUBSTRING IS NOT A NAME. `gate` was reported because `netVisual_aggregate` contains it,
  `Stack` because `StackedVlnPlot` does, `diff` because `netVisual_diffInteraction` does.

  A FLAG IS THE MAKER TALKING TO A TOOL. `--show-toplevel` and `--diff-filter=A` are how the
  freshness check asks git a question; split into pieces they named a plotting convention.

  A BLOCK SCALAR IN THE DECLARATION IS EVIDENCE, exactly as a docstring is one language over. The
  sentence that JUSTIFIES a stage names the plugins it was learnt from, and must not be read as
  the maker knowing them.

  BLIND IS NOT DONE. An instrument that found nothing to look at has not passed. A version of this
  that scored abstention as a pass would report the widest corpus for the check with none.

THE FIXTURE NAMES NO REPOSITORY THIS SUITE SERVES and shares no word with one, so a scan that had
quietly learnt a real family could not pass here.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sch.dev import overfit as OF                                          # noqa: E402


def rows_for(answers_by_element):
    """Turn {element: {answer: [artefact]}} into what `format_report` and `verdict` read."""
    out = []
    for st, answers in answers_by_element.items():
        n = sum(len(v) for v in answers.values())
        blind = len(answers.get("blind", ()))
        out.append({"stage": st, "phase": "build", "kind": "mechanical", "answers": answers,
                    "n": n, "blind": blind, "seen": n - blind,
                    "distinct": len([k for k in answers if k != "blind"])})
    return out


class AMakerThatNamesOneMemberOfTheFamily(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix="overfit-"))

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def maker(self, body, name="element.py"):
        p = self.d / name
        p.write_text(body, encoding="utf-8")
        return [p]

    # ---- the corpus half -------------------------------------------------------------

    def test_an_instrument_that_could_look_at_one_says_so(self):
        r = rows_for({"seal/imprint": {"blind": ["ka", "ki", "ko", "ku"], "held:2": ["ke"]}})[0]
        self.assertIn("CORPUS 1 of 5", OF.verdict(r))

    def test_abstention_is_not_a_pass(self):
        # Four blind and one answer must NOT read as "five read, one answer, ok".
        r = rows_for({"seal/imprint": {"blind": ["ka", "ki", "ko", "ku"], "held:2": ["ke"]}})[0]
        self.assertEqual(1, r["seen"])
        self.assertEqual(4, r["blind"])

    def test_one_answer_over_a_wide_corpus_is_reported_as_possibly_vacuous(self):
        r = rows_for({"seal/imprint": {"held:2": ["ka", "ki", "ko", "ku", "ke"]}})[0]
        self.assertIn("ONE ANSWER", OF.verdict(r))

    def test_a_finished_family_is_not_called_vacuous(self):
        # Every artefact `done` is a finished family, not a check that asks nothing - and calling
        # it vacuous would be a false alarm on every completed conversion there will ever be.
        r = rows_for({"seal": {"done": ["ka", "ki", "ko", "ku", "ke"]}})[0]
        v = OF.verdict(r)
        self.assertIn("ALL DONE", v)
        self.assertNotIn("ONE ANSWER", v)
        self.assertIn("Scaffold one from nothing", v)

    def test_a_wide_corpus_with_several_answers_is_quiet(self):
        r = rows_for({"seal": {"done": ["ka", "ki"], "owes": ["ko"], "partial": ["ku"]}})[0]
        self.assertEqual("", OF.verdict(r))

    def test_judgement_is_never_scored(self):
        r = rows_for({"ruling": {"done": ["ka", "ki", "ko"]}})[0]
        r["kind"] = "judgement"
        self.assertEqual("", OF.verdict(r))

    def test_a_run_side_stage_this_scan_could_not_ask_is_a_note_and_not_a_finding(self):
        # A stage that verifies a RUN and was given none has abstained on every artefact. Read
        # as "corpus 0, fitted by construction" it would fail the scan on a stage it never ran;
        # it is measured by `status --run RUNDIR`, and the report says so instead.
        r = rows_for({"weighed": {"blind": ["ka", "ki", "ko"]}})[0]
        r["phase"] = "test"
        self.assertTrue(OF.unasked(r))
        self.assertEqual("", OF.verdict(r))
        rep = OF.format_report([r], [], "seal", ["ka", "ki", "ko"])
        self.assertIn("not asked", rep)
        self.assertIn("0 element(s) with a corpus", rep)
        # and a BUILD stage blind everywhere is still the corpus finding it always was
        b = rows_for({"shaped": {"blind": ["ka", "ki", "ko"]}})[0]
        self.assertFalse(OF.unasked(b))
        self.assertIn("CORPUS 0 of 3", OF.verdict(b))

    # ---- the literal half ------------------------------------------------------------

    #: `turn` is a CONVENTION here - two members spell a symbol with it. `hewStone` is one
    #: member's own vocabulary. The scan must tell them apart, and that is the whole rule.
    VOCAB = [("ke", {"quarry", "hewStone_face", "hewStone_edge", "trimBlock"}),
             ("ka", {"lathe", "turnSpindle"}),
             ("ki", {"kiln", "turnBisque"})]

    def test_a_constant_naming_one_members_upstream_is_found(self):
        f = self.maker('PATTERN = "^(hewStone|turn)"\n')
        got = OF.fitted_literals(f, self.VOCAB)
        self.assertEqual(["hewStone"], [r["piece"] for r in got])
        self.assertEqual("ke", got[0]["artefact"])

    def test_a_name_two_members_share_is_a_convention_and_is_not_reported(self):
        f = self.maker('PATTERN = "^(turn)"\n')
        self.assertEqual([], OF.fitted_literals(f, self.VOCAB))

    def test_a_word_inside_a_symbol_is_not_a_name(self):
        # `Stone` sits inside `hewStone_face` at a case boundary and IS a component; `ewSt` does
        # not and is not. Without the boundary rule `gate` named a plugin through `aggregate`.
        self.assertEqual(["Stone"],
                         [r["piece"] for r in OF.fitted_literals(self.maker('X = "Stone"\n'),
                                                                 self.VOCAB)])
        self.assertEqual([], OF.fitted_literals(self.maker('X = "ewSt"\n'), self.VOCAB))

    def test_a_comment_is_evidence_and_not_knowledge(self):
        f = self.maker("# hewStone_face was the one that taught us this\nX = 1\n")
        self.assertEqual([], OF.fitted_literals(f, self.VOCAB),
                         "a sentence recording why a rule exists was read as the rule")

    def test_a_docstring_is_evidence_and_not_knowledge(self):
        # ONE WORD, AND THAT IS THE WHOLE POINT OF THE FIXTURE. Written as prose sentences these
        # docstrings are excluded by the no-space rule whatever the docstring rule does, so
        # deleting the docstring rule left the test green - the fixture could not express the
        # failure it is named for, which is this codebase's most frequent defect and was caught
        # here by mutating the module on a copy rather than by reading it.
        f = self.maker('"""hewStone_face"""\n\n\ndef g():\n    """trimBlock"""\n    return 1\n')
        self.assertEqual([], OF.fitted_literals(f, self.VOCAB),
                         "a docstring naming the plugin a rule was learnt from was read as the "
                         "maker knowing that plugin")

    def test_a_command_line_flag_is_the_maker_talking_to_a_tool(self):
        f = self.maker('ARGS = ["--hewStone-only"]\n')
        self.assertEqual([], OF.fitted_literals(f, self.VOCAB))

    def test_a_block_scalar_in_the_declaration_is_prose(self):
        p = self.d / "DEVPOINTS.yaml"
        p.write_text("points:\n  seam:\n    why: >\n"
                     "      hewStone_face and trimBlock were both silently wrong\n"
                     "    lives: seams\n", encoding="utf-8")
        self.assertEqual([], OF.fitted_literals([p], self.VOCAB))

    def test_a_declaration_key_naming_one_members_upstream_is_still_found(self):
        p = self.d / "DEVPOINTS.yaml"
        p.write_text("points:\n  seam:\n    pattern: hewStone\n", encoding="utf-8")
        self.assertEqual(["hewStone"], [r["piece"] for r in OF.fitted_literals([p], self.VOCAB)])

    def test_one_artefact_is_not_a_family_and_it_says_nothing(self):
        f = self.maker('PATTERN = "^(hewStone)"\n')
        self.assertEqual([], OF.fitted_literals(f, self.VOCAB[:1]),
                         "generality was reported as a fact about a single artefact")

    def test_the_vocabulary_is_the_declarations_and_not_a_guess(self):
        v = OF.upstream_vocabulary({"wraps": {"tool": "Quarry"},
                                    "native_plots": {"pl.hewStone_face": {}, "ab": {}}})
        self.assertIn("Quarry", v)
        self.assertIn("pl.hewStone_face", v)
        self.assertIn("hewStone_face", v, "the dotted tail was not offered as a name")
        self.assertNotIn("ab", v, "a two-character symbol is a coincidence generator")

    def test_it_reports_and_never_writes(self):
        import inspect
        src = inspect.getsource(OF)
        for forbidden in ("write_text(", "open(", "mkdir(", "unlink("):
            self.assertNotIn(forbidden, src, f"{forbidden} in a module that only reports")


if __name__ == "__main__":
    unittest.main()
