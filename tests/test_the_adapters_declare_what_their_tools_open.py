"""THE ADAPTERS DECLARE WHAT THEIR TOOLS OPEN (harness autodev W056, wave B of the design read D6).

Wave A made the files a driven run depends on exactly the files DECLARED for it (each stage adapter's `files:`). A
declaration can be wrong: a tool opens a file its adapter does not declare, or an adapter declares what its tool never
opens. Here each stand-in (tests/fixtures) declares in its `describe` the files each command opens (`files`: its flags
by dest, and for scQC the samplesheet's columns), as its tool would, and REFUSES a call whose declared file is absent,
so no test can pass a stand-in a file the declaration would not have caught (ATTACKS 1).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
#: Each stand-in: how its `describe` is called, and its parser's source.
STAND_INS = {
    "scQC": ([str(FIXTURES / "fake_scqc.py")], None, FIXTURES / "fake_scqc.py"),
    "scAnno": ([str(FIXTURES / "fake_scanno.py")], None, FIXTURES / "fake_scanno.py"),
    "scIntegrate": (["-m", "scintegrate.cli"], FIXTURES / "fake_scintegrate",
                    FIXTURES / "fake_scintegrate" / "scintegrate" / "cli.py"),
    "scProfile": (["-m", "scprofile.cli"], FIXTURES / "fake_scprofile",
                  FIXTURES / "fake_scprofile" / "scprofile" / "cli.py"),
}


def stand_in(tool: str, *argv, cwd=None):
    head, path, _ = STAND_INS[tool]
    env = dict(os.environ, PYTHONPATH=str(path)) if path else dict(os.environ)
    for k in [k for k in env if k.startswith("FAKE_")]:
        env.pop(k)
    return subprocess.run([sys.executable, *head, *argv], capture_output=True, text=True, env=env, cwd=cwd)


def described(tool: str) -> dict:
    r = stand_in(tool, "describe")
    assert r.returncode == 0, (tool, r.stderr)
    return json.loads(r.stdout)["files"]


class EachStandInRefusesAnAbsentDeclaredFile(unittest.TestCase):
    """Change 1: a stand-in is no laxer than its declaration - every file its `describe` declares, absent, refuses."""

    def setUp(self):
        import tempfile
        self.tmp = Path(tempfile.mkdtemp(prefix="w056b_"))
        self.addCleanup(__import__("shutil").rmtree, self.tmp, True)

    def present(self, kind: str, name: str) -> str:
        p = self.tmp / name
        p.mkdir() if kind == "dir" else p.write_text("a declared input\n")
        return str(p)

    def calls(self, tool: str):
        """(the declared flag, a call naming every declared file present, the same call with that one absent)."""
        files = described(tool)["flags"]
        base = {"scQC": ["run", "--project", str(self.tmp / "p"), "--mode", "evidence"],
                "scAnno": None, "scIntegrate": ["integrate", "--out", str(self.tmp / "o"), "--label-key", "l",
                                                "--species", "s"],
                "scProfile": ["run", "--out", str(self.tmp / "o")]}[tool]
        for cmd, flags in files.items():
            argv = base or [cmd, "--out", str(self.tmp / "o")] + (
                ["--cluster-key", "k", "--species", "s", "--tissue", "t", "--assay", "scrna"]
                if cmd == "annotate" else [] if cmd != "rescue" else ["--label-key", "l"])
            given = {d: self.present(k, f"{cmd}.{d}") for d, k in flags.items()}
            if tool == "scQC":                   # the samplesheet: one library, its declared cells present
                cols = described(tool)["columns"]["run.samplesheet"]
                cells = {c: self.present(k, f"cell.{c}") for c, k in cols.items()}
                Path(given["samplesheet"]).write_text("sample\t" + "\t".join(cells) + "\nL1\t" +
                                                      "\t".join(cells.values()) + "\n")
            full = argv + [x for d, v in given.items() for x in (f"--{d.replace('_', '-')}", v)]
            for d in flags:
                gone = [x if x != given[d] else str(self.tmp / "absent" / Path(x).name) for x in full]
                yield f"{cmd} --{d.replace('_', '-')}", full, gone
            if tool == "scQC":
                for c in cols:
                    sheet = self.tmp / f"sheet.{c}.tsv"
                    sheet.write_text(Path(given["samplesheet"]).read_text().replace(
                        cells[c], str(self.tmp / "absent" / c)))
                    yield f"column {c}", full, [x if x != given["samplesheet"] else str(sheet) for x in full]

    def test_each_stand_in_refuses_a_call_whose_declared_file_is_absent_and_names_it(self):
        seen = {}
        for tool in STAND_INS:
            for what, full, gone in self.calls(tool):
                r = stand_in(tool, *full)
                self.assertNotIn(" is not a ", r.stderr, (tool, what, "every declared file present", r.stderr))
                self.assertNotIn("names no file", r.stderr, (tool, what, r.stderr))
                r = stand_in(tool, *gone)
                flag = what.split(" ", 1)[1]
                self.assertEqual(r.returncode, 2, (tool, what, r.stdout, r.stderr))
                self.assertIn(flag.removeprefix("column ") if what.startswith("column") else flag, r.stderr,
                              (tool, what))
                seen.setdefault(tool, []).append(what)
        self.assertEqual(sorted(seen), sorted(STAND_INS), seen)
        self.assertIn("annotate --tree", seen["scAnno"])
        self.assertIn("column matrix", seen["scQC"])
        self.assertIn("run --section", seen["scProfile"])

    def test_a_stand_ins_describe_declares_its_files_as_its_tool_would(self):
        for tool in STAND_INS:
            f = described(tool)
            self.assertTrue(f["flags"], tool)
            for cmd, flags in f["flags"].items():
                self.assertTrue(set(flags.values()) <= {"file", "dir", "path"}, (tool, cmd, flags))
        self.assertEqual(sorted(described("scQC")["columns"]), ["run.samplesheet"])


if __name__ == "__main__":
    unittest.main()
