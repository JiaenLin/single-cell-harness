#!/usr/bin/env python3
"""A round states its rules; this is what makes the statement worth anything.

WHY A ROUND HAS RULES. A maker's only real evidence that it generalises is a plugin it has never
seen, and ordinary helpfulness destroys that evidence: repair the plugins that are broken and
there is nothing left to test the maker on; hand-edit the one being converted and the maker is no
longer what produced it. Both feel like progress while they are happening.

WHAT IS CHECKED HERE, AND WHY EACH ONE EXISTS.

  DUPLICATION IS THE SIGNAL FOR HAND-WRITTEN MECHANISM. Method is written once because it is about
  one method. Mechanism appears twice because it is about all of them. Measured on the family this
  was written for: one plugin carried three near-identical copies of a ceiling reader and six of a
  draw wrapper, and one of those copies recorded, in its own comment, a run lost because a
  function defined in two of them was missing from the third.

  ONE BLOCK REPORTED ONCE. Every start offset inside a 33-line duplicate is itself a duplicate, so
  the first version printed one finding eleven times, at 33, 32, 31 ... lines. A report a reader
  cannot count is a report that gets skimmed.

  A COMMENT IS NOT CODE. Two copies of a mechanism differ in their comments far more than in their
  code; a comparison that kept the comments would call them different and find nothing.

  THE RANGE IS DECLARED, NOT PASSED. Two of the rules are answered from history, so whoever picks
  the range picks the answer and the flattering range is always available.

  SILENCE IS NOT A PASS. No `rules:` block, or a range that is not a commit, must report "cannot
  say" - not "held". This suite's own family has met that defect in four other places.

THE FIXTURE NAMES NO REPOSITORY THIS SUITE SERVES.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

#: COMPUTE NODES ON THIS FAMILY'S CLUSTER HAVE NO GIT BINARY - `sch/dev/job.py` says so twice and
#: reads its own commit from a FILE for that reason. Two of these rules are answered from history
#: and there is no history to ask without it, so they skip; the other two need none and still run.
#:
#: THE FIRST VERSION HAD NO GUARD AND SIX TESTS ERRORED, on the machine the full ladder runs on.
#: An absent tool reported as a failing check is exactly the confusion every other reader in this
#: package is built to avoid, and it was introduced by the file that ratchets that distinction.
HAVE_GIT = shutil.which("git") is not None
NEEDS_GIT = "git is not installed here, and these two rules are git's answer or none"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sch.dev import points as P                                            # noqa: E402
from sch.dev import rules as RU                                            # noqa: E402

HEAD = """\
tool: quarry
devpoints: 1
tests:
  command: ["true"]
fixture:
  command: [["true"]]
  products: []
baseline_dir: b
"""

RULES = """\
rules:
  since:
    commit: HEAD
  maker_output:
    min_block: 8
    means: mechanism is generated or written once, never copied
  held_out:
    names: [beta]
    means: the held-out set is the test set
  in_place:
    paths: [engine]
    means: the engine is what this round improves
  end_to_end:
    names: [alpha]
    means: one seam runs end to end
"""

POINT = """\
points:
  seam:
    what: one seam
    lives: seams
    must_declare: [api]
    example: alpha
    proves: it is read
    cannot_prove: that it is right
"""

MECHANISM = "\n".join(f"    step_{i} <- refine(stock, {i})" for i in range(12))


class TheRulesOfARoundAreCheckedNotPromised(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix="rules-"))
        (self.d / "seams").mkdir()
        (self.d / "engine").mkdir()
        (self.d / "engine" / "turn.py").write_text("x = 1\n", encoding="utf-8")
        self.write("alpha", "hone(stock)")
        self.write("beta", "polish(stock)")
        # WRITTEN BEFORE THE REPOSITORY IS MADE, so the declaration is a tracked file like every
        # other. Written afterwards it was itself an untracked change, and the in-place rule
        # correctly reported the fixture's own scaffolding as scope the round did not agree.
        (self.d / "DEVPOINTS.yaml").write_text(HEAD + RULES + POINT, encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def write(self, name, body):
        (self.d / "seams" / f"{name}.py").write_text(
            f'PLUGIN = {{"api": 1, "name": "{name}"}}\nSCRIPT = """\n{body}\n"""\n',
            encoding="utf-8")

    def load(self, rules=RULES):
        if rules != RULES:
            (self.d / "DEVPOINTS.yaml").write_text(HEAD + rules + POINT, encoding="utf-8")
        doc = P.load(self.d)
        specs = [(f.stem, {"api": 1, "name": f.stem})
                 for f in sorted((self.d / "seams").glob("*.py"))]
        return doc, specs

    def check(self, since="", rules=RULES):
        doc, specs = self.load(rules)
        return {r["rule"]: r for r in RU.check(doc, "seam", specs, root=self.d, since=since)}

    # ---- maker_output: duplication is the signal --------------------------------------

    def test_a_block_copied_inside_one_artefact_is_reported(self):
        self.write("alpha", MECHANISM + "\n    hone(stock)\n" + MECHANISM)
        r = self.check()["maker_output"]
        self.assertEqual(RU.BROKEN, r["verdict"])
        self.assertEqual(1, len(r["detail"]), f"one block, reported {len(r['detail'])} times")
        self.assertIn("x2", r["detail"][0])

    def test_a_block_shared_between_two_artefacts_is_reported(self):
        self.write("alpha", MECHANISM)
        self.write("beta", MECHANISM)
        r = self.check()["maker_output"]
        self.assertEqual(RU.BROKEN, r["verdict"])
        self.assertIn("alpha", r["detail"][0])
        self.assertIn("beta", r["detail"][0])

    def test_one_duplicate_is_one_row_and_not_one_per_offset(self):
        # A 20-line duplicate contains thirteen 8-line duplicates. Reporting each is a report
        # nobody reads, and it was the first version's actual output.
        long = "\n".join(f"    s{i} <- refine(stock, {i})" for i in range(20))
        self.write("alpha", long + "\n    hone(stock)\n" + long)
        r = self.check()["maker_output"]
        self.assertEqual(1, len(r["detail"]), r["detail"])
        self.assertIn("20 lines", r["detail"][0])

    def test_a_declaration_whose_entries_share_their_keys_is_not_a_copied_mechanism(self):
        # Two entries of a figure plan (harness ADR-0016) carry the same nine keys with the
        # same values - who draws, the function, the axis, the position, the ceiling, the
        # device, the size - and differ in the expression and the legend. That is the plan's
        # shape, not mechanism that escaped the maker; a rule that reported it would report
        # every migrated plugin as broken for declaring its figures completely.
        entry = "\n".join(f'        "k{i}": "v{i}",' for i in range(9))
        self.write("alpha", "PLUGIN = {\n    'figures': [\n    {\n" + entry
                   + "\n        'expr': 'a',\n    },\n    {\n" + entry
                   + "\n        'expr': 'b',\n    },\n    ],\n}\n")
        r = self.check()["maker_output"]
        self.assertEqual(RU.HELD, r["verdict"], r["detail"])

    def test_comments_are_not_what_makes_two_copies_different(self):
        a = "\n".join(f"    # note {i}\n    s{i} <- refine(stock, {i})" for i in range(12))
        b = "\n".join(f"    # a completely different note {i}\n    s{i} <- refine(stock, {i})"
                      for i in range(12))
        self.write("alpha", a)
        self.write("beta", b)
        self.assertEqual(RU.BROKEN, self.check()["maker_output"]["verdict"],
                         "two copies of one mechanism were called different by their comments")

    def test_a_short_repeat_is_a_coincidence_and_not_reported(self):
        short = "\n".join(f"    s{i} <- refine(stock, {i})" for i in range(4))
        self.write("alpha", short + "\n    hone(stock)\n" + short)
        self.assertEqual(RU.HELD, self.check()["maker_output"]["verdict"])

    def test_nothing_repeated_is_held_and_says_what_it_read(self):
        r = self.check()["maker_output"]
        self.assertEqual(RU.HELD, r["verdict"])
        self.assertIn("2 seam(s) read", r["says"])

    # ---- the history rules -------------------------------------------------------------

    def git(self, *args):
        subprocess.run(("git",) + args, cwd=str(self.d), capture_output=True, check=False)

    def repo(self):
        self.git("init", "-q")
        self.git("config", "user.email", "t@t")
        self.git("config", "user.name", "t")
        self.git("add", "-A")
        self.git("commit", "-qm", "base")
        out = subprocess.run(("git", "rev-parse", "HEAD"), cwd=str(self.d),
                             capture_output=True, text=True)
        return out.stdout.strip()

    @unittest.skipUnless(HAVE_GIT, NEEDS_GIT)
    def test_a_held_out_artefact_that_changed_is_reported(self):
        base = self.repo()
        self.write("beta", "polish(stock)  # improved")
        r = self.check(since=base)["held_out"]
        self.assertEqual(RU.BROKEN, r["verdict"])
        self.assertTrue(any("beta" in d for d in r["detail"]))

    @unittest.skipUnless(HAVE_GIT, NEEDS_GIT)
    def test_the_artefact_being_converted_is_in_scope(self):
        base = self.repo()
        self.write("alpha", "hone(stock)  # improved")
        self.assertEqual(RU.HELD, self.check(since=base)["in_place"]["verdict"],
                         "the round's own output was reported as outside its scope")

    @unittest.skipUnless(HAVE_GIT, NEEDS_GIT)
    def test_a_generated_companion_is_in_scope_wherever_its_artefact_is(self):
        base = self.repo()
        (self.d / "seams" / "alpha.draw.R").write_text("draw <- function() NULL\n",
                                                       encoding="utf-8")
        self.assertEqual(RU.HELD, self.check(since=base)["in_place"]["verdict"],
                         "a file the maker generates beside the artefact was reported as scope "
                         "the round did not agree")

    @unittest.skipUnless(HAVE_GIT, NEEDS_GIT)
    def test_a_change_outside_the_declared_mechanism_is_reported(self):
        base = self.repo()
        (self.d / "elsewhere.py").write_text("x = 2\n", encoding="utf-8")
        r = self.check(since=base)["in_place"]
        self.assertEqual(RU.BROKEN, r["verdict"])
        self.assertIn("elsewhere.py", r["detail"])

    def test_no_range_is_cannot_say_and_never_held(self):
        for rule in ("held_out", "in_place"):
            self.assertEqual(RU.CANNOT_SAY, self.check(since="")[rule]["verdict"],
                             f"{rule} passed on silence")

    @unittest.skipUnless(HAVE_GIT, NEEDS_GIT)
    def test_a_range_that_is_not_a_commit_is_cannot_say(self):
        self.repo()
        self.assertEqual(RU.CANNOT_SAY, self.check(since="not-a-commit")["held_out"]["verdict"])

    @unittest.skipUnless(HAVE_GIT, NEEDS_GIT)
    def test_the_declaration_pins_the_range(self):
        base = self.repo()
        (self.d / "DEVPOINTS.yaml").write_text(
            HEAD + RULES.replace("commit: HEAD", f"commit: {base}") + POINT, encoding="utf-8")
        self.assertEqual(base, RU.since_of(P.load(self.d)))

    # ---- the end-to-end complement, and silence ----------------------------------------

    def test_end_to_end_is_the_complement_of_the_held_out_set(self):
        self.assertEqual(RU.HELD, self.check()["end_to_end"]["verdict"])
        grown = RULES.replace("names: [beta]", "names: [beta, alpha]")
        self.assertEqual(RU.BROKEN, self.check(rules=grown)["end_to_end"]["verdict"],
                         "the two lists grew into each other and nothing said so")

    def test_a_repository_declaring_no_rules_says_so(self):
        rows = self.check(rules="")
        self.assertEqual(1, len(rows))
        r = next(iter(rows.values()))
        self.assertEqual(RU.CANNOT_SAY, r["verdict"])
        self.assertIn("declares no `rules:` block", r["says"])

    def test_it_reports_and_never_writes(self):
        import inspect
        src = inspect.getsource(RU)
        for forbidden in ("write_text(", "mkdir(", "unlink(", "rmtree("):
            self.assertNotIn(forbidden, src, f"{forbidden} in a module that only reports")


if __name__ == "__main__":
    unittest.main()
