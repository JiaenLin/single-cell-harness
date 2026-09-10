"""A declared version is a claim about code, and until now nothing asked whether it was true.

WHAT THIS PREVENTS, AND IT NEARLY SHIPPED. In one of the repositories this suite serves, a
plugin's declared version is a REUSE KEY: a later run hands it to the landscape, an earlier unit
carrying the same key is matched, and its products are hardlinked in instead of recomputed. One
commit added thirty-five legends to a plugin's draw sites and left the version where it was. The
next run reusing from the last one would have adopted the undescribed panels, printed REUSED,
and reported a clean success - and the fix would have read as a failure.

The maker demanded the field EXIST - it is in the point's `must_declare` - and no stage filled it
or checked it, so the suite had never had an opinion about whether it was CORRECT RELATIVE TO THE
CODE. These tests hold the check that now asks, and they hold just as hard on every way it is
allowed to answer "I cannot say" - because a false alarm from this kind of inference has cost
this suite trust before, and a check that cannot tell must say so rather than guess.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sch.dev import freshness as FR
from sch.dev import points as P

ROOT = Path(__file__).resolve().parents[1]
HAVE_GIT = shutil.which("git") is not None

#: THE FIELD IS NOT CALLED `version` HERE ON PURPOSE. The harness must read the name out of the
#: repository's declaration, and a fixture that used the real repository's word would pass just
#: as well against a hard-coded literal in `sch/`.
DECL = """
tool: demo
devpoints: 1
tests:
  command: ["{python}", "-c", "print(1)"]
points:
  widget:
    what: a widget
    lives: widgets
    proves: it runs
    cannot_prove: that it is right
    convert:
      placeholder: "TODO"
      upstream: wraps.tool
      version_field: stamp
      version_means: the key an earlier unit is adopted by
      stages:
        - {name: contract, fills: [inject]}
"""

#: A nested dict carrying the SAME KEY for the wrapped tool. One of the nine real plugins does
#: exactly this, and a key-only search read the upstream's line as the plugin's.
WIDGET = '''"""A widget, with a module docstring nobody runs."""
PLUGIN = {
    "stamp": "0.1.0",
    "upstream": {"stamp": "9.9.9", "home": "https://example.invalid"},
    "inject": {"required": []},
    "draws": "a panel",
}
'''


def _run(cwd, *args, check=True):
    p = subprocess.run(("git", *args), cwd=str(cwd), capture_output=True, text=True)
    if check and p.returncode != 0:
        raise AssertionError(f"git {' '.join(args)}: {p.stderr}")
    return p.stdout


def _commit(d, msg):
    _run(d, "add", "-A")
    _run(d, "-c", "user.email=t@example.invalid", "-c", "user.name=T",
         "commit", "-q", "--no-gpg-sign", "-m", msg)


@unittest.skipUnless(HAVE_GIT, "git is not installed, and this check is git's answer or none")
class AVersionThatNoLongerDescribesTheCodeIsReported(unittest.TestCase):

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.d, ignore_errors=True)
        (self.d / "DEVPOINTS.yaml").write_text(DECL)
        (self.d / "widgets").mkdir()
        self.w = self.d / "widgets" / "w.py"
        self.w.write_text(WIDGET)
        _run(self.d, "init", "-q", "-b", "main")
        _commit(self.d, "the widget arrives")
        # A SECOND COMMIT TOUCHING THE FIELD, so the field has been set as a distinct act and the
        # "never bumped" answer below is not the one under test here.
        self.w.write_text(WIDGET.replace('"stamp": "0.1.0"', '"stamp": "0.2.0"'))
        _commit(self.d, "the stamp moves on its own")
        self.doc = P.load(self.d)
        self.spec = {"stamp": "0.2.0", "upstream": {"stamp": "9.9.9"}, "inject": {"required": []}}

    def _check(self):
        return FR.check(self.spec, self.doc, "widget", "w")

    def test_a_plugin_whose_code_moved_while_its_stamp_stood_still_is_reported_stale(self):
        """THE WHOLE DEFECT. Change what the plugin draws, leave the reuse key alone, and every
        later run adopts the old products and reports success."""
        self.w.write_text(self.w.read_text().replace('"a panel"', '"a panel, with a legend"'))
        _commit(self.d, "thirty-five legends")
        f = self._check()
        self.assertTrue(f.complete, f.why_not)
        self.assertEqual(f.verdict, FR.STALE)
        self.assertIs(f.code_changed, True)
        self.assertEqual([c["subject"] for c in f.commits_since], ["thirty-five legends"])
        self.assertEqual(f.set_by["subject"], "the stamp moves on its own")

    def test_the_fields_line_is_read_from_the_commit_and_not_from_the_working_tree(self):
        """THE MODULE'S MOST-ARGUED LINE, AND IT WAS BOUGHT BY NOTHING UNTIL THIS TEST.

        `git log -L n,n:file` counts n IN THE REVISION IT STARTS FROM. A working tree that has
        drifted from HEAD - three comment lines nobody has committed, above the field - puts the
        field on a different line in each, and reading the number out of the working tree points
        the trace at whatever HEAD happens to have on that line. Here that is the very commit
        that made this plugin stale: the check would then report the change as the act that SET
        the version, find nothing after it, call the row a question and exit 0. The whole verdict
        inverts, and the report reads confident either way.

        The other cannot-say about the working tree does not reach this: it changes the declared
        VALUE and never the file, so both files still put the field on the same line.
        """
        self.w.write_text(self.w.read_text().replace('"a panel"', '"a panel, with a legend"'))
        _commit(self.d, "thirty-five legends")
        self.w.write_text("# three lines of comment\n# that nobody has\n# committed yet\n"
                          + self.w.read_text())
        self.assertEqual(FR.key_lines(_run(self.d, "show", "HEAD:widgets/w.py"),
                                      "stamp", "0.2.0"), [3])
        self.assertEqual(FR.key_lines(self.w.read_text(), "stamp", "0.2.0"), [6],
                         "the two must disagree, or this test is worth nothing")
        f = self._check()
        self.assertTrue(f.complete, f.why_not)
        self.assertEqual(f.set_by["subject"], "the stamp moves on its own",
                         "the commit that set the field, not the one that made it stale")
        self.assertEqual([c["subject"] for c in f.commits_since], ["thirty-five legends"])
        self.assertIs(f.code_changed, True)
        self.assertEqual(f.verdict, FR.STALE)

    def test_a_plugin_renamed_after_the_change_still_names_the_change(self):
        """`-L` FOLLOWS RENAMES AND THE TWO COMMANDS AFTER IT DID NOT, so the three were talking
        about three different files. The commit that made this stale had touched the file under
        its old name, so it fell out of the list, the earlier text could not be read at all, and
        the row came out as a question with git's own `fatal:` in the prose - "nothing to decide",
        exit 0, and the commit a reader was told to go and read was not there to read."""
        self.w.write_text(self.w.read_text().replace('"a panel"', '"a panel, with a legend"'))
        _commit(self.d, "THE REAL CHANGE the stamp should have named")
        _run(self.d, "mv", "widgets/w.py", "widgets/renamed.py")
        _commit(self.d, "renamed afterwards")
        f = FR.check(self.spec, P.load(self.d), "widget", "renamed")
        self.assertTrue(f.complete, f.why_not)
        self.assertEqual(f.set_by["subject"], "the stamp moves on its own")
        self.assertIn("THE REAL CHANGE the stamp should have named",
                      [c["subject"] for c in f.commits_since])
        self.assertIs(f.code_changed, True)
        self.assertEqual(f.code_why, "")
        self.assertEqual(f.verdict, FR.STALE)

    def test_a_stamp_raised_in_the_same_commit_as_the_change_is_current(self):
        src = self.w.read_text().replace('"a panel"', '"a panel, with a legend"')
        self.w.write_text(src.replace('"stamp": "0.2.0"', '"stamp": "0.3.0"'))
        _commit(self.d, "legends, and the stamp that says so")
        self.spec["stamp"] = "0.3.0"
        f = self._check()
        self.assertEqual(f.verdict, FR.CURRENT)
        self.assertEqual(f.commits_since, [])

    def test_a_comment_only_commit_is_asked_about_and_not_asserted_to_be_stale(self):
        """NOT EVERY EDIT DESERVES A BUMP. A comment does not change what a run produces, and a
        check that called every commit significant would demand a bump for a typo fix - which is
        how a check stops being read. Measured on the nine real plugins: 6 of 243 commits to
        those files changed nothing but comments, docstrings and layout."""
        self.w.write_text("# a note for a reader\n" + self.w.read_text()
                          .replace('"""A widget, with a module docstring nobody runs."""',
                                   '"""A widget. Rewritten prose."""'))
        _commit(self.d, "prose")
        f = self._check()
        self.assertTrue(f.complete, f.why_not)
        self.assertEqual(f.verdict, FR.QUESTION)
        self.assertIs(f.code_changed, False)
        self.assertNotEqual(f.commits_since, [], "the commit is still named, not silently dropped")

    def test_a_string_the_plugin_actually_carries_is_not_treated_as_prose(self):
        """The plugin this was built against embeds a whole R script in ordinary string
        constants, and its legends live there. A fingerprint that normalised strings the way it
        normalises docstrings would have called that commit cosmetic - which is the exact commit
        this check exists to catch."""
        self.w.write_text(self.w.read_text().replace('"a panel"', '"a panel\\nlegend: n = 12"'))
        _commit(self.d, "a legend inside a literal")
        self.assertIs(self._check().code_changed, True)

    def test_an_uncommitted_edit_is_named_because_no_commit_count_can_see_it(self):
        self.w.write_text(self.w.read_text().replace('"a panel"', '"a panel, edited just now"'))
        f = self._check()
        self.assertTrue(f.dirty)
        self.assertEqual(f.commits_since, [])
        self.assertEqual(f.verdict, FR.STALE)

    def test_the_upstreams_own_stamp_is_not_read_as_the_plugins_history(self):
        """A key-only search found two lines in a real plugin - its own and the wrapped tool's -
        and would have traced the wrong one. The declared VALUE is the other half of the
        address."""
        at_head = _run(self.d, "show", "HEAD:widgets/w.py")
        self.assertEqual(FR.key_lines(at_head, "stamp", "0.2.0"),
                         [3], "the plugin's own line, not the upstream's")
        self.assertEqual(FR.key_lines(at_head, "upstream.stamp", "9.9.9"), [4])

    def test_the_check_writes_nothing_and_bumps_nothing(self):
        """REGISTRATION IS CHECKED, NOT WRITTEN, and a version is the same policy plus one more
        reason: the number is the author's statement about what changed."""
        self.w.write_text(self.w.read_text().replace('"a panel"', '"a panel, with a legend"'))
        _commit(self.d, "thirty-five legends")
        before = self.w.read_bytes()
        head = _run(self.d, "rev-parse", "HEAD")
        f = self._check()
        FR.format_report([f], "widget", "means", str(self.d))
        self.assertEqual(self.w.read_bytes(), before)
        self.assertEqual(_run(self.d, "rev-parse", "HEAD"), head)
        self.assertEqual(_run(self.d, "status", "--porcelain"), "")


@unittest.skipUnless(HAVE_GIT, "git is not installed, and this check is git's answer or none")
class WhatItCannotSayItSaysRatherThanGuessing(unittest.TestCase):
    """EVERY WAY TO KNOW NOTHING, AND NONE OF THEM MAY LOOK LIKE A PASS.

    This suite has shipped a false alarm from exactly this kind of inference before and it cost
    trust. The mirror-image failure costs more: a check that answers "current" when it could not
    look tells a run it is safe to adopt last week's products.
    """

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.d, ignore_errors=True)
        (self.d / "DEVPOINTS.yaml").write_text(DECL)
        (self.d / "widgets").mkdir()
        self.w = self.d / "widgets" / "w.py"
        self.w.write_text(WIDGET)
        self.spec = {"stamp": "0.1.0", "upstream": {"stamp": "9.9.9"}}

    def _check(self, doc=None):
        return FR.check(self.spec, doc or P.load(self.d), "widget", "w")

    def test_a_tree_that_is_not_a_git_repository_cannot_say_rather_than_reporting_it_fresh(self):
        if subprocess.run(("git", "rev-parse", "--show-toplevel"), cwd=str(self.d),
                          capture_output=True).returncode == 0:
            self.skipTest("the temporary directory is itself inside a repository")
        f = self._check()
        self.assertEqual(f.verdict, FR.CANNOT_SAY)
        self.assertIn("not inside a git repository", f.why_not)

    def test_a_repository_with_no_commits_yet_cannot_say(self):
        _run(self.d, "init", "-q", "-b", "main")
        f = self._check()
        self.assertEqual(f.verdict, FR.CANNOT_SAY)
        self.assertIn("no commits yet", f.why_not)

    def test_a_file_git_does_not_track_cannot_say(self):
        _run(self.d, "init", "-q", "-b", "main")
        (self.d / "README").write_text("x\n")
        (self.d / ".gitignore").write_text("widgets/\n")
        _commit(self.d, "everything but the widget")
        f = self._check()
        self.assertEqual(f.verdict, FR.CANNOT_SAY)
        self.assertIn("does not track", f.why_not)

    def test_a_shallow_clone_cannot_say_because_its_oldest_commit_is_a_graft(self):
        """The wrong end of a truncated history reads as a bump that never happened."""
        _run(self.d, "init", "-q", "-b", "main")
        _commit(self.d, "the widget arrives")
        self.w.write_text(WIDGET.replace('"0.1.0"', '"0.2.0"'))
        _commit(self.d, "a real bump")
        clone = Path(tempfile.mkdtemp()) / "shallow"
        self.addCleanup(shutil.rmtree, clone.parent, ignore_errors=True)
        _run(self.d, "clone", "-q", "--depth", "1", f"file://{self.d}", str(clone))
        self.spec["stamp"] = "0.2.0"
        f = FR.check(self.spec, P.load(clone), "widget", "w")
        self.assertEqual(f.verdict, FR.CANNOT_SAY)
        self.assertIn("SHALLOW", f.why_not)

    def test_a_stamp_never_set_since_the_file_was_created_cannot_say(self):
        """A file's birth writes the field and the code in the same commit BY CONSTRUCTION, so
        counting from it would report every plugin still being written as stale, forever, from
        its second commit onward. Two of the nine real plugins are in this state."""
        _run(self.d, "init", "-q", "-b", "main")
        _commit(self.d, "the widget arrives")
        self.w.write_text(self.w.read_text().replace('"a panel"', '"a panel, with a legend"'))
        _commit(self.d, "a change nobody stamped")
        f = self._check()
        self.assertEqual(f.verdict, FR.CANNOT_SAY)
        self.assertIn("never been set as a distinct act", f.why_not)

    def test_a_value_written_at_two_places_cannot_say_rather_than_picking_one(self):
        _run(self.d, "init", "-q", "-b", "main")
        self.w.write_text(WIDGET.replace('"9.9.9"', '"0.1.0"'))
        _commit(self.d, "the widget arrives")
        self.w.write_text(self.w.read_text() + "\nOTHER = 1\n")
        _commit(self.d, "something else")
        f = self._check()
        self.assertEqual(f.verdict, FR.CANNOT_SAY)
        self.assertIn("2 places", f.why_not)

    def test_a_file_that_cannot_be_read_at_the_commit_that_set_it_cannot_say(self):
        """THE EIGHTH ANSWER, AND WHAT USED TO COME OUT HERE WAS "nothing to decide".

        If the earlier text never arrives there is no comparison to make, and the row this
        produced was a QUESTION - printed as "to decide", exit 0 - carrying git's own `fatal:`
        in the middle of a user-facing sentence. A rename the follow could not chase is how it
        happens; that follow is stubbed out here because a hole that only opens when git's
        rename detection fails cannot be reached on demand."""
        _run(self.d, "init", "-q", "-b", "main")
        _commit(self.d, "the widget arrives")
        self.w.write_text(WIDGET.replace('"stamp": "0.1.0"', '"stamp": "0.2.0"'))
        _commit(self.d, "the stamp moves on its own")
        self.w.write_text(self.w.read_text().replace('"a panel"', '"a panel, with a legend"'))
        _commit(self.d, "a change nobody stamped")
        _run(self.d, "mv", "widgets/w.py", "widgets/renamed.py")
        _commit(self.d, "renamed afterwards")
        self.spec["stamp"] = "0.2.0"
        with mock.patch.object(FR, "_named_at", return_value=""):
            f = FR.check(self.spec, P.load(self.d), "widget", "renamed")
        self.assertEqual(f.verdict, FR.CANNOT_SAY)
        self.assertIn("cannot be read as it stood at", f.why_not)
        self.assertNotIn("fatal", f.why_not, "git says `fatal:` to a shell, not to a reader")

    def test_a_plugin_born_identical_to_its_neighbour_is_not_followed_into_the_neighbour(self):
        """WHY ONE OF THE THREE STILL DOES NOT FOLLOW, MEASURED WHILE FIXING THE OTHER TWO.

        `--follow` finds a path's source by rename AND COPY detection, so a plugin whose first
        commit is byte-identical to the one it was scaffolded from - which is how every one of
        them starts - walks off into its neighbour's history. The birth query would then answer
        with the NEIGHBOUR's birth, `born == set_by` would never hold, and a plugin still being
        written would be reported stale forever from its second commit. The trace and the list
        of commits since follow; the birth query may not, and this is the reason."""
        _run(self.d, "init", "-q", "-b", "main")
        _commit(self.d, "the widget arrives")
        self.w.write_text(WIDGET.replace('"stamp": "0.1.0"', '"stamp": "0.2.0"'))
        _commit(self.d, "the stamp moves on its own")
        twin = self.d / "widgets" / "v.py"
        twin.write_text(WIDGET)                    # byte for byte, w.py as it was first committed
        _commit(self.d, "a second widget, scaffolded from the first")
        twin.write_text(twin.read_text().replace('"a panel"', '"a panel, with a legend"'))
        _commit(self.d, "a change nobody stamped")
        followed = _run(self.d, "log", "--follow", "--diff-filter=A", "--format=%s",
                        "--", "widgets/v.py").splitlines()
        self.assertEqual(followed[:1], ["the widget arrives"],
                         "git itself follows the twin - if it stops, this test is worth nothing")
        f = FR.check(self.spec, P.load(self.d), "widget", "v")
        self.assertEqual(f.verdict, FR.CANNOT_SAY)
        self.assertIn("never been set as a distinct act", f.why_not)

    def test_a_stamp_changed_only_in_the_working_tree_cannot_say(self):
        """`git log -L` counts lines in the revision it starts from. A value that is not in the
        committed file has no committed line, and answering from the working tree's line number
        would produce a confident wrong commit."""
        _run(self.d, "init", "-q", "-b", "main")
        _commit(self.d, "the widget arrives")
        self.spec["stamp"] = "9.0.0"
        f = self._check()
        self.assertEqual(f.verdict, FR.CANNOT_SAY)
        self.assertIn("not a literal", f.why_not)


class ARepositoryThatHasNotDeclaredTheFieldGetsNoOpinion(unittest.TestCase):
    """FIVE REPOSITORIES, ONE OF WHICH HAS DECLARED THIS. The other four must get a "cannot say"
    and never an answer invented out of a field name the harness picked for them."""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.d, ignore_errors=True)
        (self.d / "widgets").mkdir()
        (self.d / "widgets" / "w.py").write_text(WIDGET)

    def test_a_point_that_names_no_field_cannot_say_and_says_which_key_to_add(self):
        (self.d / "DEVPOINTS.yaml").write_text(
            DECL.replace("      version_field: stamp\n", "")
                .replace("      version_means: the key an earlier unit is adopted by\n", ""))
        doc = P.load(self.d)
        self.assertEqual(FR.declared_field(doc, "widget"), ("", ""))
        f = FR.check({"stamp": "0.1.0"}, doc, "widget", "w")
        self.assertEqual(f.verdict, FR.CANNOT_SAY)
        self.assertIn("version_field", f.why_not)

    def test_a_declaration_missing_the_field_entirely_is_the_other_tiers_finding(self):
        (self.d / "DEVPOINTS.yaml").write_text(DECL)
        f = FR.check({"inject": {}}, P.load(self.d), "widget", "w")
        self.assertEqual(f.verdict, FR.CANNOT_SAY)
        self.assertIn("no `stamp`", f.why_not)

    def test_the_harness_names_no_repositorys_field(self):
        """`sch/dev/convert.py`'s docstring says this family names no tool, no field and no
        plugin format. The three version-shaped fields of the one repository that declares this
        must appear nowhere in the module as literals - nor may the module know a plugin format
        by the name of its dict."""
        src = (ROOT / "sch" / "dev" / "freshness.py").read_text(encoding="utf-8")
        for word in ("version", "api", "state_version", "PLUGIN", "kernel", "kernels",
                     "scprofile", "cellchat", "report.figures"):
            self.assertNotIn(f'"{word}"', src, f"{word!r} is one repository's vocabulary")
            self.assertNotIn(f"'{word}'", src, f"{word!r} is one repository's vocabulary")

    def test_nothing_in_the_module_can_write(self):
        """A RATCHET AND NOT A HOPE. `points.py` says registration is checked and not written;
        the whole value of this check is that it reports a stale version and leaves the number
        to the author, so the module may not acquire a writing path later."""
        src = (ROOT / "sch" / "dev" / "freshness.py").read_text(encoding="utf-8")
        for forbidden in ("write_text(", ".write(", "os.remove", "shutil.", "unlink("):
            self.assertNotIn(forbidden, src, f"{forbidden!r} writes, and this only reports")


@unittest.skipUnless(HAVE_GIT, "git is not installed, and this check is git's answer or none")
class TheCommandAPersonActuallyRuns(unittest.TestCase):
    """A CHECK NOBODY CAN RUN IS A CHECK NOBODY RUNS, and the exit status is what a job reads."""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.d, ignore_errors=True)
        (self.d / "DEVPOINTS.yaml").write_text(DECL)
        (self.d / "widgets").mkdir()
        for nm in ("w", "x"):
            (self.d / "widgets" / f"{nm}.py").write_text(WIDGET)
        _run(self.d, "init", "-q", "-b", "main")
        _commit(self.d, "two widgets arrive")
        for nm in ("w", "x"):
            p = self.d / "widgets" / f"{nm}.py"
            p.write_text(p.read_text().replace('"stamp": "0.1.0"', '"stamp": "0.2.0"'))
        _commit(self.d, "both stamps move on their own")

    def _cli(self):
        return subprocess.run([sys.executable, "-m", "sch", "dev", "convert", "freshness",
                               "--root", str(self.d), "--point", "widget"],
                              cwd=str(ROOT), capture_output=True, text=True)

    def test_a_stale_version_exits_nonzero_so_a_job_can_refuse_to_reuse(self):
        p = self.d / "widgets" / "w.py"
        p.write_text(p.read_text().replace('"a panel"', '"a panel, with a legend"'))
        _commit(self.d, "thirty-five legends")
        out = self._cli()
        self.assertEqual(out.returncode, 2, out.stdout + out.stderr)
        self.assertIn("STALE w", out.stdout)
        self.assertIn("thirty-five legends", out.stdout)
        self.assertIn("WHAT TO DO", out.stdout)
        self.assertIn("the key an earlier unit is adopted by", out.stdout)

    def test_it_reads_the_whole_family_without_being_named_one(self):
        """The actions that show somebody an UPSTREAM are held out one plugin at a time. This one
        shows no upstream, and the question "has anybody here kept this field up to date" is
        answered by the family or not at all - so being refused without --name would make it
        unrunnable in the only form that answers anything."""
        out = self._cli()
        self.assertNotIn("name ONE with --name", out.stdout + out.stderr)
        for nm in ("w", "x"):
            self.assertIn(nm, out.stdout)

    def test_a_report_that_established_nothing_about_anything_does_not_exit_zero(self):
        """The ladder already exits 3 rather than 0 when nothing it asked for could run. A job
        that greps the exit status must not read "no history here" as "every version fresh"."""
        d2 = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d2, ignore_errors=True)
        (d2 / "DEVPOINTS.yaml").write_text(
            DECL.replace("      version_field: stamp\n", ""))
        (d2 / "widgets").mkdir()
        (d2 / "widgets" / "w.py").write_text(WIDGET)
        out = subprocess.run([sys.executable, "-m", "sch", "dev", "convert", "freshness",
                              "--root", str(d2), "--point", "widget"],
                             cwd=str(ROOT), capture_output=True, text=True)
        self.assertEqual(out.returncode, 3, out.stdout + out.stderr)
        self.assertIn("CANNOT SAY", out.stdout)

    def test_a_renamed_plugin_that_is_stale_exits_nonzero_like_any_other(self):
        """THE EXIT STATUS IS THE ONLY THING A JOB READS. This row was rendered "0 stale, 1 to
        decide" - exit 0 - with the advice telling a person to read commits that had been
        dropped from the list, and git's `fatal:` printed at them as though the check had
        crashed. The rename is the only difference from the stale case above."""
        p = self.d / "widgets" / "w.py"
        p.write_text(p.read_text().replace('"a panel"', '"a panel, with a legend"'))
        _commit(self.d, "thirty-five legends")
        _run(self.d, "mv", "widgets/w.py", "widgets/renamed.py")
        _commit(self.d, "renamed afterwards")
        out = self._cli()
        self.assertEqual(out.returncode, 2, out.stdout + out.stderr)
        self.assertIn("STALE renamed", out.stdout)
        self.assertIn("thirty-five legends", out.stdout)
        self.assertIn("1 stale, 0 to decide", out.stdout)
        self.assertNotIn("fatal", out.stdout, "git says `fatal:` to a shell, not to a reader")

    def test_a_cannot_say_row_is_never_printed_as_a_pass_beside_one_that_is(self):
        """THE MIRROR OF THE FALSE ALARM, AND THE MORE EXPENSIVE ONE. A row nobody could read
        must not sit in the same column as a row that was read and found current - that is the
        report telling a run it is safe to adopt last week's products."""
        (self.d / "widgets" / "y.py").write_text(WIDGET)          # stamp never bumped since birth
        _commit(self.d, "a third widget, stamped only at birth")
        y = self.d / "widgets" / "y.py"
        y.write_text(y.read_text().replace('"a panel"', '"a panel, with a legend"'))
        _commit(self.d, "a change nobody stamped")
        out = self._cli()
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("?    y", out.stdout)
        self.assertIn("CANNOT SAY, and that is an answer and not a pass", out.stdout)
        self.assertIn("never been set as a distinct act", out.stdout)
        self.assertEqual(out.stdout.count("  ok   "), 2, "w and x, and never y")
        self.assertIn("1 cannot say", out.stdout)


if __name__ == "__main__":
    unittest.main()
