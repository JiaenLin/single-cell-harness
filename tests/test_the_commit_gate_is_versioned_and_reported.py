"""The commit gate is the repository's; whether a clone has it is the doctor's to say (GAP-111).

WHAT WAS WRONG. The suite asserted that the clone running it had installed the gate
(`core.hooksPath`), so every fresh clone failed its own suite by construction: a clone made to
read, verify or audit commits nothing, and the W024 verifier's fresh clone of the harness ran 658
tests with exactly that one failure. Fixing it by deleting the assertion would hide what it was
for - ADR-0022 closed with two commits landed red, and the gate exists so that cannot recur.

WHAT EACH PART CAN ESTABLISH. A TEST can establish what the REPOSITORY holds: that the versioned
hook exists, can run, and runs the suite and conform before every commit and refuses a red one.
Whether THIS clone runs it is a fact about the clone, not the repository: `sch doctor` reports it,
with the command that installs it, and conform's G1 warns. A fresh clone passes the suite.
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

HOOK = ROOT / "setup" / "githooks" / "pre-commit"
LOCATING = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_PREFIX",
            "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_NAMESPACE")


def _env(**extra):
    env = {k: v for k, v in os.environ.items()
           if k not in LOCATING and not k.startswith(("SCH_SITE", "SCH_FORBIDDEN"))}
    env.update(extra)
    return env


class TheVersionedHookIsTheGate(unittest.TestCase):
    def test_the_hook_runs_the_suite_and_conform_and_refuses_a_red_commit(self):
        self.assertTrue(HOOK.is_file(), "the repository versions no commit gate")
        self.assertTrue(os.access(HOOK, os.X_OK), "the hook is not executable: git would skip it")
        text = HOOK.read_text()
        for want in ("set -euo pipefail",                   # a failing step is not passed over
                     "unittest discover -s tests",         # the suite runs
                     "-m sch conform .",                   # and conform on the repository
                     "exit 1",                             # and a red one is refused
                     "unset GIT_DIR",                      # never acting on another repository
                     "setup/githooks/conform.local"):      # with the cohorts' lists when present
            self.assertIn(want, text)
        self.assertEqual(subprocess.run(["bash", "-n", str(HOOK)]).returncode, 0)


@unittest.skipUnless(shutil.which("git"), "no git binary here - a compute node has none")
class TheDoctorSaysWhetherThisCloneHasIt(unittest.TestCase):
    def test_the_doctor_reports_not_installed_with_the_command_then_installed(self):
        from sch.doctor import commit_gate
        with tempfile.TemporaryDirectory() as td:
            r = Path(td)
            subprocess.run(["git", "init", "-q", str(r)], check=True, env=_env())
            (r / "setup" / "githooks").mkdir(parents=True)
            shutil.copy2(HOOK, r / "setup" / "githooks" / "pre-commit")
            f = commit_gate(r)
            self.assertTrue(f["ok"], "a report about the clone, never a failure of the architecture")
            self.assertIn("NOT installed", f["message"])
            self.assertIn("git config core.hooksPath setup/githooks", f["message"])
            subprocess.run(["git", "-C", str(r), "config", "core.hooksPath", "setup/githooks"],
                           check=True, env=_env())
            f = commit_gate(r)
            self.assertIn("installed", f["message"])
            self.assertNotIn("NOT installed", f["message"])

    def test_the_architecture_check_carries_the_report_and_still_holds(self):
        from sch.doctor import check_architecture, format_findings
        found = check_architecture()
        gate = [f for f in found if f["rule"] == "GATE"]
        self.assertEqual(len(gate), 1)
        self.assertIn("note", format_findings(gate))


@unittest.skipUnless(shutil.which("git"), "no git binary here - a compute node has none")
@unittest.skipIf(os.environ.get("SCH_IN_A_FRESH_CLONE"), "this is the fresh clone's own run")
class AFreshCloneWithNoHooksPathPassesTheSuite(unittest.TestCase):
    """The modules that read the clone's git configuration - conform's G1 tests, the doctor's
    report and this module - run in a fresh clone of the working tree that has never set
    core.hooksPath. The full suite on a fresh clone is the wave's gate, measured; running it
    inside the suite as well would double the suite's time for one question."""

    def test_the_modules_that_read_the_clones_gate_pass_in_a_fresh_clone(self):
        listed = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z", "--cached", "--others",
                                 "--exclude-standard"], capture_output=True, env=_env())
        if listed.returncode != 0:
            self.skipTest("this tree is not a git checkout")
        d = Path(tempfile.mkdtemp(prefix="sch-fresh-clone-"))
        self.addCleanup(shutil.rmtree, d, True)
        for name in filter(None, listed.stdout.decode().split("\0")):
            src = ROOT / name
            if src.is_file() and not src.is_symlink():
                (d / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, d / name)
        subprocess.run(["git", "init", "-q", str(d)], check=True, env=_env())
        self.assertEqual(subprocess.run(["git", "-C", str(d), "config", "--get", "core.hooksPath"],
                                        capture_output=True, env=_env()).returncode, 1,
                         "a fresh clone has no hooksPath")
        for module in ("test_conform_doctor.py", "test_the_commit_gate_is_versioned_and_reported.py"):
            r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", module],
                               cwd=str(d), capture_output=True, text=True,
                               env=_env(PYTHONPATH=str(d), SCH_IN_A_FRESH_CLONE="1"))
            self.assertEqual(r.returncode, 0, f"{module} in a fresh clone:\n{r.stderr[-1500:]}")


if __name__ == "__main__":
    unittest.main()
