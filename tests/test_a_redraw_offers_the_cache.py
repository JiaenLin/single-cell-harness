"""A redraw carries the reference's argv, and says which flags it carries; a flag the tool
declares as contradicting a redraw is dropped from one, and said so (harness ADR-0026, step 1).

EVERY RERUN OF THE ARC RE-INFERRED CELLCHAT ON ALL EIGHTEEN UNITS. `sch dev job` copies the
reference run's argv verbatim, as it should; the reference was the audit reproduction, which
ruled the cache out with `--no-cache` on purpose, and every rerun job since jobs/rerun_0006
carried that flag at column ~900 of one line - eight minutes of every thirty, fourteen times,
read by nobody. The emitter stays tool-agnostic: the TOOL's DEVPOINTS names the flags a redraw
must not carry (`run.redraw_drops`), the emitter drops them on a redraw only, lists every flag
it carries in the header where a reader looks, and keeps one by name when asked.
"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from sch.dev import job as J
from sch.dev import points as P


class ARedrawOffersTheCache(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / "ref").mkdir()
        (self.d / "tool" / ".git").mkdir(parents=True)
        (self.d / "tool" / ".git" / "HEAD").write_text("a" * 40 + "\n")
        (self.d / "ref" / "STATUS.json").write_text(json.dumps(
            {"tool": "t", "status": "ok",
             "argv": ["t", "run", "--key", "cell_type_forced", "--out", "/old", "--timeout",
                      "21600", "--no-cache"]}))
        (self.d / "ref" / "report.json").write_text('{"seed": 1}')
        self.kw = dict(ref_dir=str(self.d / "ref"), rundir=str(self.d / "new"),
                       tooldir=str(self.d / "tool"), queue="long", select="select=1:ncpus=1")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_the_tool_declares_which_flags_a_redraw_drops(self):
        (self.d / "DEVPOINTS.yaml").write_text(
            "tool: t\ndevpoints: 1\nrun:\n  redraw_drops: [\"--no-cache\"]\n"
            "points:\n  widget:\n    what: w\n    lives: widgets\n    proves: p\n"
            "    cannot_prove: c\n")
        self.assertEqual(P.run_redraw_drops(P.load(self.d)), ["--no-cache"])
        (self.d / "DEVPOINTS.yaml").write_text(
            "tool: t\ndevpoints: 1\npoints:\n  widget:\n    what: w\n    lives: widgets\n"
            "    proves: p\n    cannot_prove: c\n")
        self.assertEqual(P.run_redraw_drops(P.load(self.d)), [])

    def test_a_reproduction_carries_every_flag_and_lists_them(self):
        text = J.emit(prediction="identical", **self.kw)
        self.assertIn("--no-cache", text.split("set -euo pipefail")[1])
        head = text.split("set -euo pipefail")[0]
        self.assertIn("FLAGS CARRIED FROM THE REFERENCE", head)
        self.assertIn("--key cell_type_forced", head)
        self.assertIn("--timeout 21600", head)
        self.assertIn("--no-cache", head)

    def test_a_redraw_drops_the_declared_flag_and_says_so(self):
        text = J.emit(prediction="identical", redraw=True, drop=["--no-cache"], **self.kw)
        body = text.split("set -euo pipefail")[1]
        self.assertNotIn("--no-cache", body)
        self.assertIn("--timeout 21600", body)
        head = text.split("set -euo pipefail")[0]
        self.assertIn("--no-cache", head)
        self.assertIn("dropped", head.lower())

    def test_the_interpreters_module_switch_is_not_a_flag_of_the_tool(self):
        (self.d / "ref" / "STATUS.json").write_text(json.dumps(
            {"tool": "t", "status": "ok",
             "argv": [str(self.d / "tool" / "pkg" / "cli.py"), "run", "--out", "/old", "--x", "1"]}))
        info = J.write(str(self.d / "job.pbs"), prediction="identical", python="/env/bin/python",
                       **self.kw)
        self.assertEqual([f for f in info["flags"] if f.startswith("-m")], [])
        self.assertIn("--x 1", info["flags"])

    def test_a_flag_kept_by_name_stays_on_a_redraw(self):
        text = J.emit(prediction="identical", redraw=True, drop=["--no-cache"],
                      keep=["--no-cache"], **self.kw)
        self.assertIn("--no-cache", text.split("set -euo pipefail")[1])

    def test_a_reproduction_that_is_not_a_redraw_drops_nothing(self):
        text = J.emit(prediction="identical", drop=["--no-cache"], **self.kw)
        self.assertIn("--no-cache", text.split("set -euo pipefail")[1])

    def test_the_written_record_names_the_flags_and_the_dropped(self):
        info = J.write(str(self.d / "job.pbs"), prediction="identical", redraw=True,
                       drop=["--no-cache"], **self.kw)
        self.assertIn("--no-cache", info["dropped"])
        self.assertIn("--key cell_type_forced", info["flags"])


if __name__ == "__main__":
    unittest.main()


class AJobIsNotEmittedOverABuildThatOwes(unittest.TestCase):
    """`sch dev job --plugin NAME` reads the maker's build status for that plugin first and
    refuses to emit while a build stage owes (harness ADR-0026, found by editing the plugin at
    random: a plan over budget, a refused axis, an unruled entry could all be emitted and
    submitted). `--anyway` emits regardless and the header says so."""

    DECL = """
tool: t
devpoints: 1
run:
  forecast: ["{python}", "forecast.py", "{run}", "{name}"]
points:
  kernel:
    what: a kernel
    lives: kernels
    proves: it runs
    cannot_prove: that it is right
    convert:
      placeholder: "TODO"
      upstream: wraps.tool
      stages:
        - {name: contract, fills: [inject]}
        - {name: judgement, kind: judgement, fills: [summary]}
"""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / "DEVPOINTS.yaml").write_text(self.DECL)
        (self.d / "forecast.py").write_text(
            "import sys\nprint('  CACHE FORECAST for ' + sys.argv[2] + ': MISS - the span changed')\n")
        (self.d / "kernels").mkdir()
        (self.d / "ref").mkdir()
        (self.d / "tool" / ".git").mkdir(parents=True)
        (self.d / "tool" / ".git" / "HEAD").write_text("a" * 40 + "\n")
        (self.d / "ref" / "STATUS.json").write_text(json.dumps(
            {"tool": "t", "status": "ok", "argv": ["t", "run", "--out", "/old"]}))
        (self.d / "ref" / "report.json").write_text('{"seed": 1}')

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def sch(self, *args):
        import subprocess
        import sys
        return subprocess.run(
            [sys.executable, "-m", "sch", "dev", "job", "--root", str(self.d), "--ref",
             str(self.d / "ref"), "--rundir", str(self.d / "new"), "--tool", str(self.d / "tool"),
             "--queue", "q", "--select", "select=1:ncpus=1", "--predict", "identical",
             "--out", str(self.d / "job.pbs"), "--point", "kernel", "--plugin", "demo", *args],
            capture_output=True, text=True, cwd=str(Path(__file__).resolve().parents[1]))

    def test_a_build_that_owes_refuses_the_job_and_names_the_stage(self):
        (self.d / "kernels" / "demo.py").write_text(
            'PLUGIN = {"name": "demo", "summary": "s", "inject": "TODO"}\n')
        p = self.sch()
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("contract", p.stderr + p.stdout)
        self.assertFalse((self.d / "job.pbs").exists())

    def test_a_build_that_is_done_emits_and_the_header_carries_the_forecast(self):
        (self.d / "kernels" / "demo.py").write_text(
            'PLUGIN = {"name": "demo", "summary": "s", "inject": {"required": []}}\n')
        p = self.sch()
        self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
        self.assertTrue((self.d / "job.pbs").exists())
        head = (self.d / "job.pbs").read_text().split("set -euo pipefail")[0]
        self.assertIn("CACHE FORECAST for demo: MISS", head)

    def test_anyway_emits_over_an_owing_build_and_the_header_says_so(self):
        (self.d / "kernels" / "demo.py").write_text(
            'PLUGIN = {"name": "demo", "summary": "s", "inject": "TODO"}\n')
        p = self.sch("--anyway")
        self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
        self.assertIn("contract", (self.d / "job.pbs").read_text().split("set -euo pipefail")[0])


class TheSignaturesAreRecordedOnce(unittest.TestCase):
    """`sch dev convert inventory --record FILE` writes the upstream's functions and signatures
    where the tool is installed, as maker output the plugin's validator reads (harness
    ADR-0026): an argument the function has not got was learned from a thirty-minute run."""

    def test_the_record_carries_every_function_and_its_signature(self):
        import subprocess
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
        from test_convert import _fake_package, DECL
        d = Path(tempfile.mkdtemp())
        (d / "DEVPOINTS.yaml").write_text(DECL)
        (d / "widgets").mkdir()
        (d / "widgets" / "w.py").write_text('PLUGIN = {"name": "w", "wraps": {"tool": "fakepkg"}}\n')
        try:
            with _fake_package(pl=True) as py:
                p = subprocess.run([sys.executable, "-m", "sch", "dev", "convert", "inventory",
                                    "--root", str(d), "--point", "widget", "--name", "w",
                                    "--python", py, "--record", str(d / "w.signatures.json")],
                                   capture_output=True, text=True,
                                   cwd=str(Path(__file__).resolve().parents[1]))
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            rec = json.loads((d / "w.signatures.json").read_text())
            self.assertEqual(rec["tool"], "fakepkg")
            self.assertIn("pl.umap", rec["functions"])
            self.assertIn("recorded", rec)
        finally:
            shutil.rmtree(d, ignore_errors=True)
