"""The suite leaves the real repository exactly as it found it (harness ADR-0029).

WHAT HAPPENED. On 2026-11-09 a commit in a linked worktree of this repository ran the commit gate,
and the gate ran this suite. git hands a hook run in a linked worktree an ABSOLUTE `GIT_DIR` and
`GIT_INDEX_FILE` (measured, git 2.55.0; the main checkout gets only the relative
`GIT_INDEX_FILE=.git/index`). Every test here that runs `git -C <a temporary directory> ...`
therefore acted on the real repository instead of its own:
- `git init` set `core.bare = true` in the shared config, so the main checkout stopped being a
  work tree;
- a test's `git config user.email t@t` became the author of the next commit on main;
- the tests' fixture commits advanced the worktree's branch;
- `git worktree add -b side` created a branch in the shared repository.

Every one of those tests named a temporary directory. The environment overrode it.

THE TWO DEFENCES. The gate unsets the repository-locating variables before it runs anything
(`setup/githooks/pre-commit`), and this module removes them from the suite's own environment when
it is imported. Discovery imports every module before any test runs, so no test inherits them.
The test below then checks the outcome directly: what the suite could have damaged is read at
discovery and again after every other module has run. This module's name sorts last, and
discovery runs modules in sorted order.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: What git exports to a hook that says WHICH repository to act on.
LOCATING = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
            "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_PREFIX",
            "GIT_NAMESPACE")
INHERITED = {k: os.environ.pop(k) for k in LOCATING if k in os.environ}

#: What the 2026-11-09 run changed, plus the one key a worktree reads its tree from. They are
#: local keys: the identity in the user's global config is not this repository's to guard.
KEYS = ("core.bare", "core.hooksPath", "core.worktree", "user.name", "user.email")


def _git(*args):
    p = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True,
                       timeout=60, env={k: v for k, v in os.environ.items() if k not in LOCATING})
    return p.returncode, p.stdout.strip()


def snapshot():
    """{key: value} for the real repository, or None where there is no git to ask (a compute
    node has none) or this tree is not a checkout."""
    if not shutil.which("git") or _git("rev-parse", "--git-dir")[0] != 0:
        return None
    snap = {k: _git("config", "--local", "--get", k)[1] for k in KEYS}
    snap["HEAD of this checkout"] = _git("rev-parse", "HEAD")[1]
    return snap


BEFORE = snapshot()


class TheSuiteLeavesTheRealRepositoryAsItFoundIt(unittest.TestCase):

    @unittest.skipIf(BEFORE is None, "no git binary, or not a checkout - nothing to guard")
    def test_nothing_any_test_ran_reached_the_real_repository(self):
        after = snapshot()
        moved = {k: (BEFORE[k], after.get(k)) for k in BEFORE if BEFORE[k] != after.get(k)}
        self.assertEqual({}, moved,
                         "the suite changed the real repository (before, after). A test's git "
                         "command reached it instead of the temporary directory it named - "
                         "look for an inherited GIT_DIR (ADR-0029)")

    def test_the_gate_unsets_what_locates_a_repository_before_it_runs_anything(self):
        """Executed, not read: the hook's own `unset` statement is run under a planted
        environment, and it must also come before the suite is started."""
        hook = (ROOT / "setup" / "githooks" / "pre-commit").read_text(encoding="utf-8")
        joined = hook.replace("\\\n", " ")
        unset = next((ln for ln in joined.splitlines() if ln.strip().startswith("unset ")), "")
        self.assertTrue(unset, "the commit gate unsets nothing")
        self.assertLess(joined.index(unset), joined.index("unittest discover"),
                        "the gate starts the suite before it unsets the locating variables")
        planted = {**os.environ, **{k: "/somewhere/else" for k in LOCATING}}
        out = subprocess.run(["bash", "-c", unset + "\nenv"], capture_output=True, text=True,
                             env=planted, timeout=30).stdout
        left = sorted(set(re.findall(r"^(GIT_[A-Z_]+)=", out, re.M)) & set(LOCATING))
        self.assertEqual([], left, f"the gate passes {left} on to the suite")


if __name__ == "__main__":
    unittest.main()
