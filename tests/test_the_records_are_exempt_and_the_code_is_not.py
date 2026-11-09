"""The harness's records may name a cohort; its code may not (W024, GAP-110).

WHAT WAS WRONG. Tier II of the program's rules lets the harness's own records name the cohorts
they are about - the goals, the ledgers, the ADRs, the blind tests, the post-mortems - and S1 had
no way to know which files those are. So `sch conform` on the harness failed with the cohorts'
lists, and the commit gate ran it WITHOUT them: a cohort string written into `sch/` or `tests/`
was never looked for at commit.

WHAT A REPOSITORY DECLARES NOW. `LEAK_SCOPE.txt` at its root, one entry per line,
`<path> :: <what may appear> :: <why>`. `*` declares a record: S1 does not read it, and says how
many files that covers. A comma list of terms excuses those terms at that path and nothing else.
The reason is required, and an entry that does not parse is a failure that is not applied. The
gate reads the cohorts' lists from an untracked local file beside it, when the clone has one.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from helpers import ROOT
from sch.conform import conform_repo

ENV = ("SCH_SITE_TERMS", "SCH_SITE", "SCH_SITE_SHAPES", "SCH_FORBIDDEN_TERMS")
RECORDS = ("GOALS.md", "autodev/", "docs/adr/", "docs/blind/", "docs/postmortem/")
LOCATING = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_PREFIX")


def row(checks, prefix):
    got = [c for c in checks if c["id"].startswith(prefix)]
    return got[0] if got else None


def entries(text):
    """(path, what, why) for each entry line of a LEAK_SCOPE.txt."""
    out = []
    for line in text.splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            parts = [x.strip() for x in s.split("::")]
            out.append(tuple(parts + [""] * (3 - len(parts)))[:3])
    return out


class TheHarnessDeclaresItsRecords(unittest.TestCase):
    def test_the_five_record_paths_are_declared_each_with_a_reason(self):
        f = ROOT / "LEAK_SCOPE.txt"
        self.assertTrue(f.is_file(), "the harness declares no leak scope")
        got = {p: (what, why) for p, what, why in entries(f.read_text())}
        for rec in RECORDS:
            self.assertIn(rec, got, f"{rec} is not declared a record")
            self.assertEqual(got[rec][0], "*", rec)
            self.assertTrue(len(got[rec][1]) > 20, f"{rec} carries no reason")

    def test_nothing_the_harness_runs_or_ships_is_declared_a_record(self):
        """The declaration excuses records, never code: no entry may cover the package, the
        tests, the skills, the setup or the plugins, and a job script only by its own name."""
        f = ROOT / "LEAK_SCOPE.txt"
        for p, what, _ in entries(f.read_text()):
            for code in ("sch/", "tests/", "skills/", "setup/", "plugins/", "spike/"):
                self.assertFalse(p.startswith(code) or code.startswith(p.rstrip("*")),
                                 f"{p} covers {code}")
            if p.startswith("jobs/"):
                self.assertFalse(any(ch in p for ch in "*?["), f"{p}: a job record is named, not globbed")
                self.assertTrue((ROOT / p).is_file(), f"{p} is declared and does not exist")


class TheScopeIsAppliedAsDeclared(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sch-scope-"))
        self.repo = self.tmp / "tool"
        self.repo.mkdir()
        self.terms = self.tmp / "terms.txt"
        self.terms.write_text("# invented\nzorblax\nword:quuxberry\n")
        self._saved = {k: os.environ.pop(k, None) for k in ENV}

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        for k, v in self._saved.items():
            if v is not None:
                os.environ[k] = v

    def _put(self, rel, text):
        p = self.repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def _conform(self):
        return conform_repo(self.repo, terms_file=str(self.terms))

    def test_a_term_in_a_record_is_not_a_finding_and_the_same_term_in_code_is(self):
        shutil.copy(ROOT / "LEAK_SCOPE.txt", self.repo / "LEAK_SCOPE.txt")
        for rec in ("GOALS.md", "autodev/STATE.md", "docs/adr/0001-x.md", "docs/blind/0001-x.md",
                    "docs/postmortem/0001-x.md"):
            self._put(rec, "measured on the zorblax cohort, quuxberry arm\n")
        self._put("sch/planted.py", "COHORT = 'zorblax'\n")
        self._put("tests/test_planted.py", "ARM = 'quuxberry'\n")
        checks = self._conform()
        s1 = row(checks, "S1 ")
        self.assertFalse(s1["ok"])
        found = {e.split(":")[0] for e in s1["evidence"] if " site term " in e}
        self.assertEqual(found, {"sch/planted.py", "tests/test_planted.py"}, s1["evidence"])
        f = row(checks, "S1f")
        self.assertTrue(f["ok"], f["evidence"])
        self.assertTrue(any("5 file(s)" in e for e in f["evidence"]), f["evidence"])

    def test_an_entry_without_a_reason_is_refused_and_not_applied(self):
        self._put("LEAK_SCOPE.txt", "GOALS.md :: * ::\nnotes/ :: *\n")
        self._put("GOALS.md", "zorblax\n")
        self._put("notes/a.md", "zorblax\n")
        checks = self._conform()
        f = row(checks, "S1f")
        self.assertIsNotNone(f, "a scope that does not load must be reported")
        self.assertFalse(f["ok"])
        self.assertEqual(f["level"], "error")
        self.assertEqual(len([e for e in f["evidence"] if "LEAK_SCOPE.txt:" in e]), 2, f["evidence"])
        found = {e.split(":")[0] for e in row(checks, "S1 ")["evidence"] if " site term " in e}
        self.assertEqual(found, {"GOALS.md", "notes/a.md"})

    def test_a_term_entry_excuses_only_its_term_and_only_at_its_path(self):
        self._put("LEAK_SCOPE.txt",
                  "# the tool's reference vocabulary\n"
                  "refs/ :: quuxberry :: the reference tree names every arm of the field\n")
        self._put("refs/tree.yml", "- quuxberry\n- zorblax\n")
        self._put("src/a.py", "ARM = 'quuxberry'\n")
        checks = self._conform()
        ev = row(checks, "S1 ")["evidence"]
        self.assertTrue(any(e.startswith("refs/tree.yml:2") and "zorblax" in e for e in ev), ev)
        self.assertFalse(any(e.startswith("refs/tree.yml:1") for e in ev), ev)
        self.assertTrue(any(e.startswith("src/a.py:1") for e in ev), ev)
        f = row(checks, "S1f")
        self.assertTrue(any("refs/tree.yml:1" in e for e in f["evidence"]),
                        "a scoped finding must stay visible: " + str(f["evidence"]))

    def test_a_number_with_a_comma_is_one_name(self):
        """Found validating the proposed entries on the eight repositories (W024): names were split
        on every comma, so a published database's comma-grouped size became two numbers and the
        entry excused nothing. Names are separated by a comma AND a space."""
        self.terms.write_text("# invented\nword:4,321\nword:quuxberry\n")
        self._put("LEAK_SCOPE.txt", "refs/ :: 4,321, quuxberry :: a published table's size and a word\n")
        self._put("refs/table.md", "| db | 4,321 | quuxberry |\n")
        checks = self._conform()
        self.assertTrue(row(checks, "S1 ")["ok"], row(checks, "S1 ")["evidence"])
        self.assertEqual(len([e for e in row(checks, "S1f")["evidence"] if "(excused)" in e]), 2)

    def test_the_scope_file_may_name_what_it_allows_and_nothing_else(self):
        self._put("LEAK_SCOPE.txt",
                  "# zorblax is excused below; quuxberry is not excused anywhere\n"
                  "refs/ :: zorblax :: the reference tree names it\n")
        self._put("refs/tree.yml", "- zorblax\n")
        ev = row(self._conform(), "S1 ")["evidence"]
        self.assertTrue(any(e.startswith("LEAK_SCOPE.txt:1") and "quuxberry" in e for e in ev), ev)
        self.assertFalse(any("zorblax" in e for e in ev), ev)

    def test_an_entry_that_covers_no_file_is_said(self):
        self._put("LEAK_SCOPE.txt", "gone/ :: * :: a directory that was deleted\n")
        self._put("src/a.py", "X = 1\n")
        g = row(self._conform(), "S1g")
        self.assertIsNotNone(g)
        self.assertFalse(g["ok"])
        self.assertEqual(g["level"], "warn")
        self.assertTrue(any("gone/" in e for e in g["evidence"]))


@unittest.skipUnless(shutil.which("git") and shutil.which("bash"), "needs git and bash")
class TheCommitGateReadsTheCohortsListsWhenTheCloneHasThem(unittest.TestCase):
    """The hook is run for real, with `python3` replaced by a stub that records how it was
    called: the suite and conform are the hook's business, and what is tested here is only which
    lists it hands to conform."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sch-gate-"))
        self.repo = self.tmp / "clone"
        (self.repo / "setup" / "githooks").mkdir(parents=True)
        shutil.copy(ROOT / "setup" / "githooks" / "pre-commit",
                    self.repo / "setup" / "githooks" / "pre-commit")
        self.env = {k: v for k, v in os.environ.items() if k not in LOCATING}
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True, env=self.env)
        stub = self.tmp / "bin"
        stub.mkdir()
        self.calls = self.tmp / "calls.txt"
        # one bracket per argument, so a path holding a space is seen as one argument or two
        (stub / "python3").write_text(f'#!/bin/bash\nprintf "[%s]" "$@" >> "{self.calls}"\n'
                                      f'echo >> "{self.calls}"\nexit 0\n')
        (stub / "python3").chmod(0o755)
        self.env["PATH"] = f"{stub}{os.pathsep}{self.env.get('PATH', '')}"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _gate(self):
        r = subprocess.run(["bash", "setup/githooks/pre-commit"], cwd=str(self.repo),
                           capture_output=True, text=True, env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return [c for c in self.calls.read_text().splitlines() if "[conform]" in c]

    def test_without_a_local_file_the_gate_runs_conform_as_before(self):
        self.assertEqual(self._gate(), ["[-m][sch][conform][.]"])

    def test_the_local_files_lists_are_handed_to_conform(self):
        a = self.tmp / "a cohort folder" / "terms.txt"             # cohort folders hold spaces
        b, s = self.tmp / "b" / "terms.txt", self.tmp / "site shapes.txt"
        (self.repo / "setup" / "githooks" / "conform.local").write_text(
            "# this clone's cohorts; never committed\n"
            f"terms={a}{os.pathsep}{b}\n"
            f"shapes={s}\n")
        self.assertEqual(self._gate(),
                         [f"[-m][sch][conform][.][--terms][{a}{os.pathsep}{b}][--shapes][{s}]"])

    def test_the_local_file_is_ignored_by_git_so_it_cannot_be_committed(self):
        shutil.copy(ROOT / ".gitignore", self.repo / ".gitignore")
        (self.repo / "setup" / "githooks" / "conform.local").write_text("terms=/x\n")
        r = subprocess.run(["git", "-C", str(self.repo), "status", "--porcelain", "--untracked-files=all"],
                           capture_output=True, text=True, env=self.env)
        self.assertNotIn("conform.local", r.stdout)


if __name__ == "__main__":
    unittest.main()
