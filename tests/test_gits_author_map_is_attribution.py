"""git's author map is attribution, as the citation file is (autodev W029, GAP-C71).

S1 reads every file git lists by its content (W024), and an e-mail address is one of its universal
shapes - except where it is attribution, not leakage: the citation file and a package's metadata
name a person to credit (`CITATION.cff`, `pyproject.toml`). `.mailmap`, git's own map of authors'
names and addresses, is the same kind of file, and S1 read it as a site string: the harness's
`.mailmap`, which corrects one commit's author without rewriting public history (D-001), failed S1
once S1 read every file, and was withdrawn. git reads `.mailmap` at the top of the working tree
and nowhere else, so that one file is its attribution, and a `.mailmap` anywhere else is read like
any other file.

The address is built when the test runs, so this file holds none.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import helpers  # noqa: F401  (puts the repository on sys.path)
from sch.conform import conform_repo

ADDRESS = "a.person" + "@" + "example.org"
LINE = f"A Person <{ADDRESS}> <an.old.address{'@'}example.org>\n"
ENV = ("SCH_SITE_TERMS", "SCH_SITE", "SCH_SITE_SHAPES", "SCH_FORBIDDEN_TERMS")
LOCATING = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_PREFIX")


def s1(checks):
    return [c for c in checks if c["id"].startswith("S1 ")][0]


class GitsAuthorMapIsAttribution(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sch-mailmap-"))
        self.repo = self.tmp / "tool"
        self.repo.mkdir()
        (self.repo / "README.md").write_text("# a tool\n")
        self._saved = {k: os.environ.pop(k, None) for k in ENV}

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        for k, v in self._saved.items():
            if v is not None:
                os.environ[k] = v

    def put(self, rel, text=LINE):
        p = self.repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def findings(self):
        got = s1(conform_repo(self.repo))
        return got["ok"], [e for e in got["evidence"] if "an e-mail address" in e]

    def test_an_address_in_the_root_mailmap_is_attribution(self):
        self.put(".mailmap")
        ok, found = self.findings()
        self.assertTrue(ok, found)
        self.assertEqual(found, [])

    @unittest.skipUnless(shutil.which("git"), "no git binary here - a compute node has none")
    def test_and_so_it_is_where_git_lists_the_tree(self):
        env = {k: v for k, v in os.environ.items() if k not in LOCATING}
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True, env=env)
        self.put(".mailmap")
        subprocess.run(["git", "-C", str(self.repo), "add", "."], check=True, env=env)
        ok, found = self.findings()
        self.assertTrue(ok, found)

    def test_the_same_line_in_another_root_file_is_still_a_finding(self):
        for rel in ("AUTHORS", "NOTES.md"):
            self.put(rel)
        self.put(".mailmap")
        ok, found = self.findings()
        self.assertFalse(ok)
        self.assertEqual(sorted(e.split(":")[0] for e in found), ["AUTHORS", "NOTES.md"], found)

    def test_a_mailmap_below_the_root_is_not_gits_and_is_read(self):
        self.put("docs/.mailmap")
        ok, found = self.findings()
        self.assertFalse(ok)
        self.assertEqual([e.split(":")[0] for e in found], ["docs/.mailmap"], found)

    def test_the_citation_file_is_attribution_as_before(self):
        self.put("CITATION.cff", f"cff-version: 1.2.0\nauthors:\n  - email: {ADDRESS}\n")
        ok, found = self.findings()
        self.assertTrue(ok, found)


if __name__ == "__main__":
    unittest.main()
