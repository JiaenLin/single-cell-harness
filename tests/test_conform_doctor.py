import json
import shutil
import tempfile
import unittest
from pathlib import Path

from helpers import ROOT
from sch.conform import conform_repo, conform_run
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
