"""A word list that is named is read, or the scan refuses to run (W024, GAP-101).

WHAT WAS WRONG. `term_files` raised only when two or more lists were named. One list, misspelt,
was dropped without a word: `sch conform --terms <a typo>` scanned no site term at all and S1
passed, with only S1c's warning to say so - while the docstring promised that a named missing
list raises. The same class one level up: the dev ladder's contract tier passed `A:B` to S1 only
when `Path("A:B").is_file()`, which it never is, so naming both cohorts' lists there read neither.

A list that is named and yields no term - every line a comment - is the same mistake in another
form: the guard looks for nothing and says it looked.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import ROOT
from sch.conform import conform_repo
from sch.dev import ladder as L
from sch.dev import points as P

ENV = ("SCH_SITE_TERMS", "SCH_SITE", "SCH_SITE_SHAPES", "SCH_FORBIDDEN_TERMS", "DEMO_FORBIDDEN_TERMS")
DECL = """
tool: demo
devpoints: 1
points:
  widget:
    what: a thing
    lives: pkg
    register:
      - {file: pkg/reg.py, table: WIDGETS}
    must_declare: [state_version]
    proves: it runs
    cannot_prove: that it is right
"""


class ANamedWordListIsReadOrRefused(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sch-named-list-"))
        self.repo = self.tmp / "tool"
        (self.repo / "pkg").mkdir(parents=True)
        (self.repo / "pkg" / "reg.py").write_text("WIDGETS = {}\nNAME = 'quuxberry'\n")
        self.one = self.tmp / "one.txt"
        self.one.write_text("# first project\nzorblax\n")
        self.two = self.tmp / "two.txt"
        self.two.write_text("# second project\nquuxberry\n")
        self.empty = self.tmp / "empty.txt"
        self.empty.write_text("# a list whose every line is a comment\n\n   # indented, still a comment\n")
        self.typo = self.tmp / "tpyo.txt"
        self._saved = {k: os.environ.pop(k, None) for k in ENV}

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        for k, v in self._saved.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v

    def test_one_named_list_that_does_not_exist_is_refused(self):
        with self.assertRaises(FileNotFoundError) as e:
            conform_repo(self.repo, terms_file=str(self.typo))
        self.assertIn(str(self.typo), str(e.exception))

    def test_a_list_named_by_the_environment_and_missing_is_refused_too(self):
        os.environ["SCH_SITE_TERMS"] = str(self.typo)
        with self.assertRaises(FileNotFoundError):
            conform_repo(self.repo)

    def test_a_named_list_that_yields_no_term_is_refused(self):
        with self.assertRaises(ValueError) as e:
            conform_repo(self.repo, terms_file=str(self.empty))
        self.assertIn(str(self.empty), str(e.exception))
        with self.assertRaises(ValueError):                       # one of several, the same
            conform_repo(self.repo, terms_file=f"{self.one}{os.pathsep}{self.empty}")

    def test_the_command_line_refuses_a_missing_list_and_names_it(self):
        env = {k: v for k, v in os.environ.items() if k not in ENV}
        env["PYTHONPATH"] = str(ROOT)
        r = subprocess.run([sys.executable, "-m", "sch", "conform", str(self.repo),
                            "--terms", str(self.typo)],
                           capture_output=True, text=True, cwd=str(ROOT), env=env)
        self.assertEqual(r.returncode, 2, r.stdout[-500:] + r.stderr[-500:])
        self.assertIn(str(self.typo), r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_the_ladders_contract_tier_reads_both_lists_of_a_pair(self):
        (self.repo / "DEVPOINTS.yaml").write_text(DECL)
        res = []
        L.t1_contract(P.load(self.repo), res, terms=f"{self.one}{os.pathsep}{self.two}")
        self.assertFalse(res[0]["ok"])
        self.assertTrue(any(e.startswith("S1 ") and "quuxberry" in e for e in res[0]["evidence"]),
                        res[0]["evidence"])

    def test_the_ladders_contract_tier_says_a_missing_list_instead_of_passing(self):
        (self.repo / "DEVPOINTS.yaml").write_text(DECL)
        res = []
        L.t1_contract(P.load(self.repo), res, terms=str(self.typo))
        self.assertFalse(res[0]["ok"], res[0]["evidence"])
        self.assertTrue(any(str(self.typo) in e for e in res[0]["evidence"]), res[0]["evidence"])

    def test_the_ladders_leak_tier_says_a_missing_list_instead_of_skipping(self):
        (self.repo / "DEVPOINTS.yaml").write_text(DECL)
        os.environ["DEMO_FORBIDDEN_TERMS"] = str(self.typo)
        res = []
        L.t5_leak(P.load(self.repo), self.repo, res)
        self.assertFalse(res[0]["ok"], res[0]["evidence"])
        self.assertFalse(res[0]["skipped"], "a named list that is missing is not 'no list'")
        self.assertTrue(any(str(self.typo) in e for e in res[0]["evidence"]), res[0]["evidence"])


if __name__ == "__main__":
    unittest.main()
