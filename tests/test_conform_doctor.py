import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import ROOT
from sch.conform import conform_against, conform_repo, conform_run
from sch.doctor import check_architecture


def by_id(checks, prefix):
    return [c for c in checks if c["id"].startswith(prefix)]


class TestConform(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sch-conf-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _repo(self, leaky=True):
        r = self.tmp / "tool"
        (r / "tool").mkdir(parents=True)
        (r / "tests").mkdir()
        (r / "jobs").mkdir()
        (r / "VERSION").write_text("0.2.0\n")
        (r / "tool" / "__init__.py").write_text('__version__ = "0.1.0"\n')
        code = ('import argparse\nap = argparse.ArgumentParser()\nap.add_argument("--out", default="out")\n'
                'for cand in ("cluster_FLAG", "FLAG"):\n    pass\n')
        if leaky:
            code += '# measured on ' + '/ho' + 'me/someone/projects/COHORT and lo' + 'gin-10-03, job 12' + '3456.hn-' + '10-03\n'
        (r / "tool" / "cli.py").write_text(code)
        (r / "jobs" / "run.pbs").write_text("#!/bin/bash\n#PBS -q workq\ncd $HOME\nnohup python x.py &\n")
        return r

    def test_static_checks_name_the_leaks_and_the_fixes(self):
        checks = conform_repo(self._repo())
        s1 = by_id(checks, "S1 ")[0]
        self.assertFalse(s1["ok"])
        self.assertTrue(any("home path" in e for e in s1["evidence"]))
        self.assertTrue(any("login-node" in e for e in s1["evidence"]))
        self.assertTrue(any("job id" in e for e in s1["evidence"]))
        self.assertFalse(by_id(checks, "S2 ")[0]["ok"])
        self.assertFalse(by_id(checks, "S3 ")[0]["ok"])
        self.assertFalse(by_id(checks, "S4 ")[0]["ok"])
        s5 = by_id(checks, "S5 ")[0]
        self.assertFalse(s5["ok"])
        self.assertTrue(any("seal" in e for e in s5["evidence"]))
        self.assertFalse(by_id(checks, "S6 ")[0]["ok"])
        self.assertFalse(by_id(checks, "S11 ")[0]["ok"])
        for c in checks:
            if not c["ok"]:
                self.assertTrue(c["fix"], c["id"])

    def test_site_terms_come_from_outside_the_repo(self):
        r = self._repo(leaky=False)
        (r / "tool" / "notes.md").write_text("validated on the NAMEDCOHORT cohort\n")
        clean = conform_repo(r)
        self.assertTrue(by_id(clean, "S1 ")[0]["ok"])
        terms = self.tmp / "terms.txt"
        terms.write_text("# site\nnamedcohort\n")
        found = conform_repo(r, terms_file=str(terms))
        self.assertFalse(by_id(found, "S1 ")[0]["ok"])

    def test_run_dir_checks(self):
        good = self.tmp / "20260101T000000Z__tool-abc1234__01_stage"
        (good / "logs").mkdir(parents=True)
        (good / "logs" / "driver.log").write_text("x")
        (good / "SEALED.txt").write_text("exit=0\njobid=1\nproducts=ok\n")
        (good / "TOOL_HEAD.txt").write_text("abc1234def\n")
        (good / "STATUS.json").write_text(json.dumps({"status": "ok"}))
        checks = conform_run(good)
        self.assertTrue(all(c["ok"] for c in checks), [c for c in checks if not c["ok"]])
        percmd = self.tmp / "20260101T000000Z__tool-abc1234__02_stage"
        (percmd / "logs").mkdir(parents=True)
        (percmd / "logs" / "x.log").write_text("x")
        (percmd / "SEALED.annotate.txt").write_text("exit=0\njobid=1\nproducts=a\n")
        (percmd / "TOOL_HEAD.txt").write_text("abc1234\n")
        (percmd / "STATUS.annotate.json").write_text(json.dumps({"status": "ok"}))
        checks = conform_run(percmd)
        self.assertTrue(all(c["ok"] for c in checks), [c for c in checks if not c["ok"]])
        bad = self.tmp / "out"
        bad.mkdir()
        checks = conform_run(bad)
        self.assertFalse(by_id(checks, "R1")[0]["ok"])
        self.assertFalse(by_id(checks, "R2 ")[0]["ok"])
        self.assertFalse(by_id(checks, "R4")[0]["ok"])

    def test_this_repository_conforms_to_its_own_scan(self):
        checks = conform_repo(ROOT)
        s1 = by_id(checks, "S1 ")[0]
        self.assertTrue(s1["ok"], s1["evidence"])


class TestDoctor(unittest.TestCase):
    def test_architecture_holds(self):
        f = check_architecture()
        bad = [x for x in f if not x["ok"]]
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()


class TestConformAgainst(unittest.TestCase):
    """Post-mortem 0001: a difference between two runs given different inputs is evidence about
    nothing, and it reads exactly like a change that moved the numbers."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sch-against-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, name, *, label="cell_type", commit="a" * 40, state_version=1, seed=0,
             inp="/data/object.h5ad", reused=None, argv=None):
        d = self.tmp / name
        d.mkdir(parents=True)
        (d / "STATUS.json").write_text(json.dumps({
            "status": "ok", "commit": commit, "state_version": state_version,
            "argv": argv or ["run", "--label-key", label]}))
        (d / "report.json").write_text(json.dumps({
            "input": inp, "label_key": label, "seed": seed, "version": "1.2.3",
            "keys": {"label": label, "sample": "sample"}, "reused": reused,
            "seconds": {"a": 12.5}}))
        return d

    def test_two_runs_of_the_same_thing_on_different_code_are_comparable(self):
        a = self._run("new", commit="b" * 40)
        b = self._run("ref", commit="c" * 40)
        checks = conform_against(a, b)
        self.assertTrue(all(c["ok"] for c in checks), [c for c in checks if not c["ok"]])

    def test_a_different_label_column_is_named_before_any_output_is_compared(self):
        # the exact defect of post-mortem 0001
        a = self._run("new", label="cell_type", commit="b" * 40)
        b = self._run("ref", label="cell_type_forced", commit="c" * 40)
        checks = conform_against(a, b)
        a2 = by_id(checks, "A2 ")[0]
        self.assertFalse(a2["ok"])
        self.assertTrue(any("label_key" in e for e in a2["evidence"]), a2["evidence"])
        self.assertTrue(any("keys.label" in e for e in a2["evidence"]), a2["evidence"])
        self.assertIn("reference run's own record", a2["fix"])

    def test_a_different_input_is_a_comparison_of_the_inputs(self):
        a = self._run("new", inp="/data/one.h5ad", commit="b" * 40)
        b = self._run("ref", inp="/data/two.h5ad", commit="c" * 40)
        self.assertFalse(by_id(conform_against(a, b), "A3")[0]["ok"])

    def test_a_bumped_state_version_makes_a_reproduction_the_wrong_test(self):
        a = self._run("new", state_version=2, commit="b" * 40)
        b = self._run("ref", state_version=1, commit="c" * 40)
        c = by_id(conform_against(a, b), "A4")[0]
        self.assertFalse(c["ok"])
        self.assertIn("wrong test", c["fix"])

    def test_an_adopted_result_compares_nothing(self):
        a = self._run("new", commit="b" * 40, reused=["cellchat[unit1]"])
        b = self._run("ref", commit="c" * 40)
        self.assertFalse(by_id(conform_against(a, b), "A6")[0]["ok"])

    def test_comparing_a_run_against_itself_warns(self):
        a = self._run("new", commit="b" * 40)
        b = self._run("ref", commit="b" * 40)
        c = by_id(conform_against(a, b), "A5")[0]
        self.assertFalse(c["ok"])
        self.assertEqual(c["level"], "warn")

    def test_a_run_that_recorded_nothing_is_a_finding_about_the_tool(self):
        a = self._run("new", commit="b" * 40)
        b = self.tmp / "silent"
        (b / "logs").mkdir(parents=True)
        c = by_id(conform_against(a, b), "A1")[0]
        self.assertFalse(c["ok"])
        self.assertIn("S7", c["fix"])

    def test_a_check_that_fires_on_correct_behaviour_gets_switched_off(self):
        """Both misfires found by running it against the real pair, within a minute of writing it.

        A reference run made before the tool declared `state_version` records none, and a
        resource limit is not a parameter: reading either as a disagreement fails a comparison
        that is sound. Each is reported, as a warning, and neither fails the check.
        """
        a = self._run("new", commit="b" * 40, state_version=1)
        b = self._run("ref", commit="c" * 40, state_version=None)
        (b / "report.json").write_text(json.dumps({
            "input": "/data/object.h5ad", "label_key": "cell_type", "seed": 0,
            "keys": {"label": "cell_type", "sample": "sample"}, "timeout": 7200}))
        (a / "report.json").write_text(json.dumps({
            "input": "/data/object.h5ad", "label_key": "cell_type", "seed": 0,
            "keys": {"label": "cell_type", "sample": "sample"}, "timeout": 21600}))
        checks = conform_against(a, b)
        self.assertEqual([c["id"] for c in checks if not c["ok"] and c["level"] == "error"], [])
        sv = by_id(checks, "A4")[0]
        self.assertEqual(sv["level"], "warn")
        self.assertIn("predates the declaration", sv["fix"])
        res = by_id(checks, "A2c")[0]
        self.assertEqual(res["level"], "warn")
        self.assertTrue(any("timeout" in e for e in res["evidence"]))
        self.assertTrue(by_id(checks, "A2 ")[0]["ok"], by_id(checks, "A2 ")[0]["evidence"])


class PrefilterLosesNothing(unittest.TestCase):
    """`sch conform` skips work it can prove is unnecessary. This asserts the proof.

    Every rule that walks lines now asks a cheap question of the whole file first and walks only
    when the answer is yes, which took the scan from 2.5s to 0.5s across the family. A fast path
    is worth exactly as much as the evidence that it loses nothing, so the prefilters can all be
    switched off with SCH_CONFORM_NO_PREFILTER and this compares the two on a real tree.
    """

    def _run(self, root, env_extra):
        code = ("import json,sys;from sch.conform import conform_repo;"
                "print(json.dumps(conform_repo(sys.argv[1]), default=str, sort_keys=True))")
        r = subprocess.run([sys.executable, "-c", code, str(root)], capture_output=True, text=True,
                           cwd=str(ROOT), env={**os.environ, "PYTHONPATH": str(ROOT), **env_extra})
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        return r.stdout

    def test_the_fast_path_and_the_slow_path_agree(self):
        self.assertEqual(json.loads(self._run(ROOT, {})),
                         json.loads(self._run(ROOT, {"SCH_CONFORM_NO_PREFILTER": "1"})))

    def test_every_generic_shape_carries_a_literal_it_cannot_match_without(self):
        """The gate is exact only while the literal really is required. A shape added without one,
        or with the wrong one, silently stops being checked."""
        from sch.conform.checks import GENERIC_PATTERNS
        for pat, why, lits in GENERIC_PATTERNS:
            self.assertTrue(lits, f"{why} has no required literal")
            bare = pat.replace("\\", "")
            for lit in lits:
                self.assertIn(lit.strip("/."), bare, f"{why}: {lit!r} is not in its own pattern")

    def test_a_planted_leak_of_every_shape_is_still_found(self):
        """The end-to-end guarantee: one file carrying an example of every shape, and the
        prefiltered scan must report all seven.

        The examples are ASSEMBLED AT RUN TIME rather than written out. Spelling them here would
        put seven site identifiers into this repository, and S1 would report this very file -
        which it did, on the first attempt.
        """
        from sch.conform.checks import GENERIC_PATTERNS
        sl = chr(47)
        planted = [f"{sl}home{sl}someone{sl}x", f"{sl}data{sl}grp{sl}home{sl}",
                   "login" + "-01-02", "hn" + "-01-02", "123456." + "hn" + "-01-02",
                   "a" + chr(64) + "b.edu", f"scratch{sl}20260101__x"]
        self.assertEqual(len(planted), len(GENERIC_PATTERNS))
        d = Path(tempfile.mkdtemp())
        try:
            (d / "pkg").mkdir()
            (d / "pkg" / "m.py").write_text("\n".join(f"x = {q!r}" for q in planted) + "\n")
            s1 = [c for c in conform_repo(d) if c["id"].startswith("S1 ")][0]
            self.assertFalse(s1["ok"])
            for _, why, _ in GENERIC_PATTERNS:
                self.assertTrue(any(why in e for e in s1["evidence"]), f"{why} was not reported")
        finally:
            shutil.rmtree(d, ignore_errors=True)
