import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from helpers import ROOT, PLUGINS
from sch.cli import main
from sch.plugin.test import table_fixture


class TestCli(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sch-cli-"))
        self.rows, self.design = table_fixture(self.tmp)
        self.stack = self.tmp / "stack"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_cli(self, *argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(list(argv))
        return rc, buf.getvalue()

    def test_the_readme_transcript_shape(self):
        rc, _ = self.run_cli("init", str(self.stack), "--profile", "table/1.0", "--observations", str(self.rows),
                             "--design", str(self.design), "--key", "value=score", "--key", "group=arm", "--key", "unit=unit")
        self.assertEqual(rc, 0)
        rc, out = self.run_cli("plan", "--stack", str(self.stack), "filter_threshold", "--param", "min=5")
        self.assertEqual(rc, 0, out)
        rc, out = self.run_cli("mount", "--stack", str(self.stack), "filter_threshold", "--param", "min=5")
        self.assertEqual(rc, 0, out)
        self.assertIn("mounted", out)
        rc, out = self.run_cli("mount", "--stack", str(self.stack), "score")
        self.assertEqual(rc, 0, out)
        rc, out = self.run_cli("stack", "--stack", str(self.stack))
        self.assertIn("filter_threshold", out)
        self.assertIn("mask/threshold", out)
        rc, out = self.run_cli("unmount", "--stack", str(self.stack), "filter_threshold", "--dry-run")
        self.assertIn("would restore", out)
        self.assertIn("score", out)
        rc, out = self.run_cli("--json", "report", "--stack", str(self.stack))
        self.assertEqual(rc, 0, out)
        self.assertIn("filter_threshold/n_removed", json.loads(out)["numbers"])
        rc, out = self.run_cli("fork", "--stack", str(self.stack), str(self.tmp / "no-qc"), "--without", "filter_threshold")
        self.assertEqual(rc, 0, out)
        rc, out = self.run_cli("run", "--stack", str(self.tmp / "no-qc"))
        self.assertEqual(rc, 0, out)
        rc, out = self.run_cli("plugin", "validate", str(PLUGINS / "table" / "filter_threshold"))
        self.assertEqual(rc, 0, out)
        rc, out = self.run_cli("plugin", "test", str(PLUGINS / "table" / "filter_threshold"), "--param", "min=5")
        self.assertEqual(rc, 0, out)
        rc, out = self.run_cli("doctor", "--architecture")
        self.assertEqual(rc, 0, out)
        rc, out = self.run_cli("doctor", "--runtime", str(self.stack))
        self.assertEqual(rc, 0, out)

    def test_scaffold_does_not_validate_until_answered(self):
        rc, out = self.run_cli("plugin", "new", "velocity", "--dest", str(self.tmp), "--profile", "table/1.0", "--wraps", "scvelo")
        self.assertEqual(rc, 0)
        rc, out = self.run_cli("plugin", "validate", str(self.tmp / "velocity"))
        self.assertEqual(rc, 2)
        self.assertIn("TODO", out)


if __name__ == "__main__":
    unittest.main()
