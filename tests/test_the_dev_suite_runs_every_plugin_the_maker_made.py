#!/usr/bin/env python3
"""The dev suite on the cluster checks every plugin the maker made, and records baselines where the
plugins run, inside its own run (autodev W019, GAP-C44).

`jobs/dev_suite.pbs` checked scProfile by ONE name written into the job - `--name abundance`, a
held-out plugin - so a plugin migrated through the maker was never on the cluster's ladder, and its
baseline was never recorded where its environment exists (scProfile docs/MIGRATIONS.md, de's
record). And where it did record, it recorded into the tool's own checkout under ~/tools, an install
that is never edited (LAYOUT); job 29 of autodev W012 showed the way that does not: a recording
root inside the run.

The list is the repository's to state: `rules.held_out` already says which artefacts are held out,
and every other artefact at the point is maker output (`sch.dev.rules.maker_output`). This file
holds the job to that, and runs the job itself - on this machine, over stub tools - where an
interpreter with anndata is at hand.

Run: PYTHONPATH=. python3 tests/test_the_dev_suite_runs_every_plugin_the_maker_made.py
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sch.dev import jobcheck as JC                                              # noqa: E402
from sch.dev import points as P                                                 # noqa: E402
from sch.dev import rules as RU                                                 # noqa: E402

JOB = ROOT / "jobs" / "dev_suite.pbs"

try:
    import anndata  # noqa: F401
    HAVE_ANNDATA = True
except ImportError:
    HAVE_ANNDATA = False

KERNEL_DECL = textwrap.dedent("""\
    tool: kerneltool
    devpoints: 1
    {extra}
    points:
      kernel:
        what: a kernel
        lives: kernels
        must_declare: []
        tests: []
        proves: it runs
        cannot_prove: that it is right
    """)


def _kernels(root: Path, names, rules=""):
    (root / "kernels").mkdir(parents=True, exist_ok=True)
    for n in names:
        (root / "kernels" / f"{n}.py").write_text(f'PLUGIN = {{"name": "{n}"}}\n\n\ndef run(ctx):\n    pass\n')
    (root / "kernels" / "_private.py").write_text("X = 1\n")
    (root / "DEVPOINTS.yaml").write_text(KERNEL_DECL.format(extra=rules))


class TheMakersOutputIsTheComplementOfTheHeldOut(unittest.TestCase):

    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix="sch-c44-"))

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_every_artefact_not_held_out_and_no_held_out_one(self):
        _kernels(self.d, ["gamma", "alpha", "beta", "delta"],
                 "rules:\n  held_out:\n    names: [gamma, delta]\n")
        self.assertEqual(RU.maker_output(P.load(self.d), "kernel"), ["alpha", "beta"])

    def test_with_no_rules_every_artefact_is_maker_output(self):
        _kernels(self.d, ["beta", "alpha"])
        self.assertEqual(RU.maker_output(P.load(self.d), "kernel"), ["alpha", "beta"])


def _listing_step(text):
    """The job's own listing program: the heredoc it hands to the interpreter."""
    m = re.search(r"<<'NAMES'[^\n]*\n(.*?)\nNAMES\n", text, flags=re.S)
    return m.group(1) if m else None


class TheJobAsksTheRepositoryWhichPluginsToCheck(unittest.TestCase):

    def setUp(self):
        self.text = JOB.read_text(encoding="utf-8")
        # the code, without the comments: the header records the name the job used to carry
        self.code = "\n".join(ln for ln in self.text.splitlines() if not ln.lstrip().startswith("#"))

    def test_the_job_names_no_plugin_of_the_repository_whose_rules_say_which(self):
        self.assertNotIn("abundance", self.code)
        self.assertFalse(re.search(r"scprofile\)\s+args\+=\(--point kernel --name ", self.code))
        self.assertIn("rules.maker_output(", self.code)

    def test_its_listing_step_run_as_the_job_runs_it_prints_the_makers_output(self):
        prog = _listing_step(self.text)
        self.assertIsNotNone(prog, "the job has no listing step for scProfile's plugins")
        d = Path(tempfile.mkdtemp(prefix="sch-c44l-"))
        try:
            _kernels(d, ["gamma", "alpha", "beta"], "rules:\n  held_out:\n    names: [gamma]\n")
            env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONNOUSERSITE="1")
            p = subprocess.run([sys.executable, "-", str(d), "kernel"], input=prog,
                               capture_output=True, text=True, env=env, timeout=120)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual(p.stdout.split(), ["alpha", "beta"])
            # nothing left to check is a refusal, not an empty pass
            _kernels(d, ["gamma"], "rules:\n  held_out:\n    names: [gamma, alpha, beta]\n")
            for f in ("alpha", "beta"):
                (d / "kernels" / f"{f}.py").unlink()
            p = subprocess.run([sys.executable, "-", str(d), "kernel"], input=prog,
                               capture_output=True, text=True, env=env, timeout=120)
            self.assertNotEqual(p.returncode, 0)
            self.assertIn("nothing to check", p.stderr)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_a_baseline_is_never_recorded_into_a_tool_checkout(self):
        # every command carrying --record-baseline roots at the recording root inside the run
        joined = re.sub(r"\\\n\s*", " ", self.text)
        for line in joined.splitlines():
            if "--record-baseline" in line and not line.lstrip().startswith("#") \
                    and "extra=(" not in line:
                self.fail(f"a recording command outside the recording step: {line.strip()}")
        self.assertIn('rroot="$RUNDIR/record/$tool"', self.text)
        self.assertRegex(joined, r'dev check --root "\$rroot"')

    def test_the_job_is_clean_by_the_familys_job_checks_and_parses(self):
        self.assertEqual(JC.problems(JOB), [])


@unittest.skipUnless(HAVE_ANNDATA and shutil.which("bash") and shutil.which("md5sum"),
                     "running the job needs bash, md5sum and an interpreter with anndata")
class TheJobRunsHere(unittest.TestCase):
    """The job itself, on this machine, over stub tools: what it checks, what it records and
    where, and that it leaves the tools as it found them."""

    @classmethod
    def setUpClass(cls):
        cls.d = Path(tempfile.mkdtemp(prefix="sch-c44job-"))
        d = cls.d
        # THE HARNESS, by a link to this checkout's package, under a declaration of its own: the
        # job checks $REPO too, and its own suite here would run this file again.
        repo = d / "harness"
        repo.mkdir()
        (repo / "sch").symlink_to(ROOT / "sch")
        (repo / "DEVPOINTS.yaml").write_text("tool: sch\ndevpoints: 1\npoints: {}\n")
        tools = d / "tools"
        body = ("import json, pathlib, sys, time\n"
                "out = pathlib.Path(sys.argv[1])\n"
                "json.dump({'result': {'n': 3.0, 'who': len(sys.argv[2])},\n"
                "           'measured': {'wall_s': time.time() % 97.0}}, open(out / 'out.json', 'w'))\n")
        # scIntegrate's stub WRITES NUMBERS, as harmony's fixture does: the job used to record its
        # baseline with the tool's own checkout as the root, into the tool.
        writes = textwrap.dedent(f"""\
            fixture:
              command: ["{{python}}", "-c", {json.dumps(body)}, "{{out}}", "{{name}}"]
              products: ["out.json"]
              execution_record: ["out.json::measured.*"]
            """)
        for tool, point in (("scQC", "criterion"), ("scAnno", "mechanism"),
                            ("scIntegrate", "method")):
            (tools / tool / "pkg").mkdir(parents=True)
            (tools / tool / "DEVPOINTS.yaml").write_text(textwrap.dedent(f"""\
                tool: {tool.lower()}
                devpoints: 1
                points:
                  {point}:
                    what: a stub
                    lives: pkg
                    must_declare: []
                    tests: []
                    proves: nothing
                    cannot_prove: anything
                """) + (writes if tool == "scIntegrate" else ""))
        prof = tools / "scProfile"
        _kernels(prof, ["alpha", "beta", "gamma"], textwrap.dedent(f"""\
            fixture:
              command: ["{{python}}", "-c", {json.dumps(body)}, "{{out}}", "{{name}}"]
              products: ["out.json"]
              execution_record: ["out.json::measured.*"]
            rules:
              held_out:
                names: [gamma]
            """))
        (prof / "tests" / "baselines").mkdir(parents=True)
        (prof / "tests" / "baselines" / "committed.json").write_text('{"k": 1}\n')
        cls.before = sorted((str(p.relative_to(tools)), p.stat().st_mtime_ns)
                            for p in tools.rglob("*") if p.is_file())
        cls.rundir = d / "run"
        cls.rundir.mkdir()
        env = dict(os.environ, RUNDIR=str(cls.rundir), REPO=str(repo), TOOLS=str(tools),
                   PY=sys.executable, PBS_O_WORKDIR=str(d), RECORD="1", NCPUS="2")
        env.pop("SCH_DEV_PREFIX", None)
        cls.p = subprocess.run(["bash", str(JOB)], env=env, capture_output=True, text=True,
                               timeout=1800)
        cls.tools = tools
        cls.log = (cls.rundir / "logs" / "driver.log").read_text(errors="replace") \
            if (cls.rundir / "logs" / "driver.log").is_file() else cls.p.stdout + cls.p.stderr

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.d, ignore_errors=True)

    def test_every_plugin_the_maker_made_is_checked_and_no_held_out_one(self):
        self.assertEqual((self.rundir / "logs" / "scprofile.names.txt").read_text().split(),
                         ["alpha", "beta"], self.log[-3000:])
        checks = self.rundir / "checks"
        self.assertTrue((checks / "scprofile.alpha.txt").is_file(), self.log[-3000:])
        self.assertTrue((checks / "scprofile.beta.txt").is_file())
        self.assertFalse((checks / "scprofile.gamma.txt").exists())
        # the repository's own tiers once, with the first name
        self.assertRegex((checks / "scprofile.alpha.txt").read_text(), r"\n  \S+\s+contract ")
        self.assertNotRegex((checks / "scprofile.beta.txt").read_text(), r"\n  \S+\s+contract ")
        self.assertIn("ok   agree", (checks / "scprofile.beta.txt").read_text())

    def test_baselines_are_recorded_in_the_run_and_rechecked(self):
        rec = self.rundir / "record" / "scprofile" / "tests" / "baselines"
        for n in ("alpha", "beta"):
            self.assertTrue((rec / f"{n}.baseline.json").is_file(), self.log[-3000:])
            self.assertIn("ok   baseline", (self.rundir / "checks" / f"recheck.scprofile.{n}.txt").read_text())
        self.assertFalse((rec / "gamma.baseline.json").exists())
        self.assertTrue((self.rundir / "record" / "scintegrate" / "tests" / "baselines"
                         / "harmony.baseline.json").is_file())
        # scAnno's stub declares no fixture: nothing to record, whatever an earlier check left in
        # the fixture directory the checks share
        self.assertFalse((self.rundir / "record" / "scanno" / "tests" / "baselines"
                          / "rescue.baseline.json").exists())

    def test_the_tools_are_left_as_they_were_and_no_link_outlives_the_job(self):
        after = sorted((str(p.relative_to(self.tools)), p.stat().st_mtime_ns)
                       for p in self.tools.rglob("*") if p.is_file())
        self.assertEqual(after, self.before)
        self.assertEqual([p for p in (self.rundir / "record").rglob("*") if p.is_symlink()], [])
        self.assertNotIn("baselines-touched", self.log)

    def test_the_seal_says_which_plugins_were_checked(self):
        seals = [p for p in (self.rundir / "SEALED.txt", self.rundir / "FAILED.txt") if p.is_file()]
        self.assertEqual(len(seals), 1, self.log[-3000:])
        self.assertIn("scprofile_checked=alpha beta", seals[0].read_text())


class ACheckReadsOnlyTheRunItsOwnShapeWrote(unittest.TestCase):
    """Found by running the job: checks share a fixture directory, and a point that declares no
    fixture command left `run_a` as the previous check wrote it - so the baseline tier recorded a
    baseline of ANOTHER tool's products."""

    def test_a_point_with_no_fixture_records_nothing_from_a_run_it_did_not_write(self):
        from sch.dev import ladder as L
        d = Path(tempfile.mkdtemp(prefix="sch-c44s-"))
        try:
            (d / "pkg").mkdir()
            (d / "DEVPOINTS.yaml").write_text(textwrap.dedent("""\
                tool: stubtool
                devpoints: 1
                points:
                  widget:
                    what: a widget
                    lives: pkg
                    must_declare: []
                    tests: []
                    proves: nothing
                    cannot_prove: anything
                """))
            fx = d / "fx"
            (fx / "run_a").mkdir(parents=True)
            (fx / "run_a" / "out.json").write_text('{"another_tools_number": 1.0}')
            doc = P.load(d)
            res = []
            L._fixture_tier(doc, "widget", "alpha", "a", fx, res, "fixture_a")
            self.assertFalse(res[0]["applicable"])
            L.t6_baseline(doc, fx, res, "alpha", record=True, point_name="widget")
            self.assertFalse(res[-1]["applicable"], res[-1])
            self.assertFalse((d / "tests" / "baselines" / "alpha.baseline.json").exists())
        finally:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
