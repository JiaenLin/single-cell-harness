"""A TEST'S CLEAN-UP NEVER CHANGES A FILE OUTSIDE ITS OWN TREE (harness W056 fix 1).

On 2026-11-12 one run of one test set mode 0644 on about 395 real programs of the machine it ran on: the test had
filled a folder of its temp tree with symlinks to every program on the PATH, and the suite's clean-up chmodded every
path it walked - `Path.chmod` follows a link. Every clean-up and every read-only walk of the suite now goes through
`helpers.release_tree` and `helpers.read_only`, which never follow a link. These tests hold them to it on files of
their own (a throwaway program, never a system tool), and keep the walk-then-chmod pattern out of every other test
file, so a new clean-up cannot bring it back."""
import os
import re
import stat
import tempfile
import unittest
from pathlib import Path

from helpers import read_only, release_tree

HERE = Path(__file__).resolve().parent


def mode(p) -> str:
    return oct(stat.S_IMODE(os.stat(p).st_mode))


class AClean_upNeverFollowsALink(unittest.TestCase):
    def setUp(self):
        self.outside = Path(tempfile.mkdtemp(prefix="sch-outside-"))
        self.prog = self.outside / "prog"                # a throwaway program of this test's own
        self.prog.write_text("#!/bin/sh\necho hi\n")
        os.chmod(self.prog, 0o755)
        self.folder = self.outside / "folder"
        self.folder.mkdir()
        os.chmod(self.folder, 0o700)
        self.data = self.outside / "data.txt"
        self.data.write_text("x\n")
        os.chmod(self.data, 0o600)

    def tearDown(self):
        release_tree(self.outside)

    def tree(self) -> Path:
        """A temp tree as a test leaves it: links OUT of it (to a program, a folder, a file), read-only parts."""
        t = Path(tempfile.mkdtemp(prefix="sch-tree-"))
        (t / "bin").mkdir()
        (t / "bin" / "prog").symlink_to(self.prog)       # what the stopped nogit() made, for one program
        (t / "linked_dir").symlink_to(self.folder, target_is_directory=True)
        (t / "own.txt").write_text("own\n")
        (t / "own.txt").chmod(0o444)
        (t / "ro").mkdir()
        (t / "ro" / "deep.txt").write_text("deep\n")
        (t / "ro" / "deep_link").symlink_to(self.data)
        os.chmod(t / "ro", 0o555)
        return t

    def test_the_clean_up_removes_the_tree_and_changes_no_mode_outside_it(self):
        t = self.tree()
        release_tree(t)
        self.assertFalse(t.exists(), "the tree is removed, its read-only parts too")
        self.assertEqual(mode(self.prog), oct(0o755), "a program linked into the tree keeps its mode")
        self.assertEqual(mode(self.folder), oct(0o700), "a folder linked into the tree keeps its mode")
        self.assertEqual(mode(self.data), oct(0o600), "a file linked from a read-only folder keeps its mode")
        self.assertEqual(self.prog.read_text(), "#!/bin/sh\necho hi\n", "and its content: nothing outside is removed")
        self.assertTrue(self.folder.is_dir())

    def test_a_read_only_walk_changes_no_mode_outside_its_tree(self):
        t = self.tree()
        os.chmod(t / "ro", 0o755)
        read_only(p for p in sorted(t.rglob("*")) if p.is_file())
        self.assertEqual(mode(t / "ro" / "deep.txt"), oct(0o444), "the tree's own file is made read-only")
        self.assertEqual(mode(self.prog), oct(0o755))
        self.assertEqual(mode(self.data), oct(0o600))
        release_tree(t)

    def test_no_other_test_file_chmods_while_it_walks_a_tree(self):
        walk = re.compile(r"\.rglob\(|\.glob\(|os\.walk\(|\.iterdir\(|os\.scandir\(|os\.listdir\(")
        bad = []
        for f in sorted(HERE.glob("*.py")):
            if f.name in ("helpers.py", Path(__file__).name):
                continue
            lines = f.read_text(encoding="utf-8").splitlines()
            for i, ln in enumerate(lines):
                if re.search(r"\bfor\b", ln) and walk.search(ln) and any("chmod(" in x for x in lines[i:i + 4]):
                    bad.append(f"{f.name}:{i + 1}")
        self.assertEqual(bad, [], "a walk that chmods goes through helpers.release_tree or helpers.read_only, "
                                  "which never follow a link")


if __name__ == "__main__":
    unittest.main()
