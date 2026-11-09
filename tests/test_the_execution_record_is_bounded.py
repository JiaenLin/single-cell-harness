#!/usr/bin/env python3
"""A tool's declared execution record cannot excuse a result (autodev W029, GAP-C63).

`fixture.execution_record` (autodev W019) lets a tool name the fields its run records about its
own execution - wall time, cores, memory, the models fitted from them - which `agree` and the
baseline then report and never judge. Its globs were unbounded: `*` crossed `/`, `.` and `::`, so
`["*"]` excused every field of every product. On de's real fixture runs that was 192 fields, all
32 DE result columns among them, and `agree` stayed green (the W019 verifier's probe). Nothing
declared such a glob; the next blind conversion is checked by this rule, so it is bounded first:
  - a glob is `product::key`, with one `::`; the parts are matched apart;
  - in the product, `*` stays inside one path segment;
  - the key's first segment is literal - `measured.*` names a namespace, `*` names everything;
  - it excuses JSON leaves only: a glob that matches a CSV column is a declaration error, and
    the column is judged.
Every error fails `agree`, the baseline's check and its recording, naming the glob.

Run: PYTHONPATH=. python3 tests/test_the_execution_record_is_bounded.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sch.dev import baseline as B                                               # noqa: E402
from sch.dev import ladder as L                                                 # noqa: E402

try:
    import anndata  # noqa: F401
    HAVE_ANNDATA = True
except ImportError:
    HAVE_ANNDATA = False

# The declaration scProfile carries for de (W013's fix-up 5, as the W019 builder measured it):
# fourteen globs, every one JSON, every key beginning with a literal segment.
FOURTEEN = ["run/kernels/*/in.json::resources.*", "run/kernels/*/out.json::measured.cores_*",
            "run/kernels/*/out.json::measured.cpu_s", "run/kernels/*/out.json::measured.wall_s",
            "run/kernels/*/out.json::measured.peak_rss_gb", "run/report.json::cores",
            "run/report.json::cores_model.*", "run/report.json::cost_model.*",
            "run/report.json::memory_model.*", "run/report.json::kernels.*.spec.cores",
            "run/report.json::kernels.*.spec.memory_gb_per_100k",
            "run/report.json::kernels.*.spec.executor.cores",
            "run/report.json::kernels.*.spec.executor.memory_gb_per_100k",
            "run/report.json::schedule[*][*].cores"]


def write_run(d: Path, *, wall: float, lfc: float):
    """A de-shaped fixture run: the kernel's record of its execution, the host's report, and the
    result table DE writes. Two shapes differ in `wall` (a measurement) and, where a test says so,
    in `lfc` (a result)."""
    k = d / "run" / "kernels" / "de"
    k.mkdir(parents=True, exist_ok=True)
    (k / "in.json").write_text(json.dumps({"resources": {"cores": 4, "memory_gb": wall / 10}}))
    (k / "out.json").write_text(json.dumps({
        "config": {"alpha": 0.05},
        "measured": {"wall_s": wall, "cpu_s": wall * 2, "peak_rss_gb": wall / 50,
                     "cores_mean": 1.9, "cores_given": 4, "n_cells": 2000}}))
    (d / "run" / "report.json").write_text(json.dumps({
        "cores": 4, "cores_model": {"de": {"peak": wall / 20}},
        "cost_model": {"de": {"s_per_100k": wall * 50, "points": 1}},
        "memory_model": {"de": {"gb_per_100k": wall / 3}},
        "kernels": {"de": {"spec": {"cores": 4, "memory_gb_per_100k": 2.0}}},
        "schedule": [[{"cores": 4, "name": "de"}]],
        "describe": {"n_obs": 2000}}))
    (d / "run" / "de_by_population.csv").write_text(
        "population,log2FoldChange,padj\nT,%s,0.01\nB,%s,0.2\n" % (lfc, -lfc / 2))


class TheRecordIsBounded(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix="sch-c63-"))
        write_run(self.d / "run_a", wall=43.26, lfc=1.5)
        write_run(self.d / "run_b", wall=42.86, lfc=1.5)
        self.fa, self.fb = B.fingerprint(self.d / "run_a"), B.fingerprint(self.d / "run_b")
        self.shapes = [{"tier": "fixture_a", "ok": True, "skipped": False},
                       {"tier": "fixture_b", "ok": True, "skipped": False}]

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def agree(self, record):
        doc = {"_root": str(self.d), "fixture": {"command": ["true"], "execution_record": record}}
        return L.t_agree(doc, "", "de", self.d, list(self.shapes))

    def baseline(self, record, recording=False):
        doc = {"_root": str(self.d), "fixture": {"command": ["true"], "execution_record": record}}
        if not recording:
            B.record(self.d / "run_a", self.d / "tests" / "baselines" / "de.baseline.json")
        return L.t6_baseline(doc, self.d, list(self.shapes), "de", record=recording)

    def assertRefused(self, record, needle):
        """`agree`, the baseline's check and its recording each fail, naming `needle`."""
        r = self.agree(record)
        self.assertFalse(r["ok"], r["evidence"])
        self.assertIn(needle, "\n".join(r["evidence"]))
        r = self.baseline(record)
        self.assertFalse(r["ok"], r["evidence"])
        self.assertIn(needle, "\n".join(r["evidence"]))
        shutil.rmtree(self.d / "tests", ignore_errors=True)
        r = self.baseline(record, recording=True)
        self.assertFalse(r["ok"], r["evidence"])
        self.assertIn(needle, "\n".join(r["evidence"]))
        self.assertFalse((self.d / "tests" / "baselines" / "de.baseline.json").exists(),
                         "a baseline was recorded under a declaration that excuses results")

    def test_a_star_is_a_declaration_error_not_everything_excused(self):
        self.assertRefused(["*"], "'*'")

    def test_every_csv_column_is_a_declaration_error(self):
        self.assertRefused(["*.csv::*"], "'*.csv::*'")

    def test_a_result_column_named_exactly_is_a_declaration_error_and_is_judged(self):
        glob = "run/de_by_population.csv::log2FoldChange"
        self.assertRefused([glob], "log2FoldChange")
        with self.assertRaises(ValueError):            # bl.RecordError, a declaration error
            L.shape_comparison(self.fa, self.fb, (), [glob])

    def test_a_key_must_begin_with_a_literal_segment(self):
        for glob in ("run/report.json::*", "run/report.json::cores*", "run/report.json::*.cores",
                     "run/report.json*", "run/report.json::cores::x", "::cores"):
            with self.subTest(glob):
                r = self.agree([glob])
                self.assertFalse(r["ok"], (glob, r["evidence"]))
                self.assertIn("misdeclared", "\n".join(r["evidence"]), glob)

    def test_a_product_star_stays_inside_one_path_segment(self):
        """`*/out.json` names an out.json one directory down, not every out.json in the run."""
        c = L.shape_comparison(self.fa, self.fb, (), ["*/out.json::measured.*"])
        excused = {k for k, _x, _y in c["resources"]}
        self.assertNotIn("run/kernels/de/out.json::measured.wall_s", excused)
        self.assertTrue(any("out.json::measured.wall_s" in x for x in c["disagree"]),
                        c["disagree"])                 # run/kernels/de/out.json is judged
        r = self.agree(["run/kernels/*/out.json::measured.*", "run/kernels/*/in.json::resources.*",
                        "run/report.json::cores_model.*", "run/report.json::cost_model.*",
                        "run/report.json::memory_model.*"])
        self.assertTrue(r["ok"], r["evidence"])

    def test_a_result_that_moves_is_judged_under_any_bounded_record(self):
        write_run(self.d / "run_b", wall=42.86, lfc=-1.5)
        c = L.shape_comparison(self.fa, B.fingerprint(self.d / "run_b"), (), FOURTEEN)
        self.assertTrue(any("log2FoldChange" in x for x in c["disagree"]), c["disagree"])

    def test_the_fourteen_globs_excuse_what_they_excused(self):
        """de's declaration is JSON-only and its keys begin with a literal segment: what it
        excuses is unchanged, and every DE number is still compared."""
        c = L.shape_comparison(self.fa, self.fb, (), FOURTEEN)
        self.assertEqual(c["disagree"], [])
        excused = {k for k, _x, _y in c["resources"]}
        self.assertEqual(excused, {
            "run/kernels/de/in.json::resources.cores", "run/kernels/de/in.json::resources.memory_gb",
            "run/kernels/de/out.json::measured.cores_given",
            "run/kernels/de/out.json::measured.cores_mean",
            "run/kernels/de/out.json::measured.cpu_s",
            "run/kernels/de/out.json::measured.peak_rss_gb",
            "run/kernels/de/out.json::measured.wall_s", "run/report.json::cores",
            "run/report.json::cores_model.de.peak", "run/report.json::cost_model.de.points",
            "run/report.json::cost_model.de.s_per_100k", "run/report.json::kernels.de.spec.cores",
            "run/report.json::kernels.de.spec.memory_gb_per_100k",
            "run/report.json::memory_model.de.gb_per_100k",
            "run/report.json::schedule[*][*].cores"})
        for k in ("run/de_by_population.csv::log2FoldChange.sum", "run/de_by_population.csv::padj.max",
                  "run/kernels/de/out.json::measured.n_cells", "run/report.json::describe.n_obs"):
            self.assertIn(k, c["compared"])
        self.assertTrue(self.agree(FOURTEEN)["ok"])
        self.assertTrue(self.baseline(FOURTEEN)["ok"])


@unittest.skipUnless(HAVE_ANNDATA, "the fixture needs anndata, which this interpreter has not got")
class ThroughTheRealCli(unittest.TestCase):
    """`sch dev check` on a repository whose DEVPOINTS.yaml declares `["*"]`."""

    DECL = textwrap.dedent("""\
        tool: widgettool
        devpoints: 1
        points:
          widget:
            what: a widget
            lives: pkg
            must_declare: []
            register:
              - {file: pkg/reg.py, table: WIDGETS}
            tests: []
            proves: it runs
            cannot_prove: that it is right
        """)
    BODY = ("import json, pathlib, sys, time\n"
            "out = pathlib.Path(sys.argv[1]); t = time.time()\n"
            "json.dump({'result': {'lfc': t % 7.0}, 'measured': {'wall_s': t % 97.0}},\n"
            "          open(out / 'out.json', 'w'))\n")

    def check(self, record):
        d = Path(tempfile.mkdtemp(prefix="sch-c63cli-"))
        fx = Path(tempfile.mkdtemp(prefix="sch-c63fx-"))
        try:
            (d / "pkg").mkdir()
            (d / "pkg" / "reg.py").write_text("WIDGETS = {'alpha': 1}\n")
            (d / "DEVPOINTS.yaml").write_text(self.DECL + textwrap.dedent(f"""\
                fixture:
                  command: ["{{python}}", "-c", {json.dumps(self.BODY)}, "{{out}}"]
                  products: []
                  execution_record: {json.dumps(record)}
                """))
            env = dict(os.environ, PYTHONPATH=str(ROOT))
            p = subprocess.run([sys.executable, "-m", "sch", "dev", "check", "--root", str(d),
                                "--point", "widget", "--name", "alpha", "--only", "fixture_a",
                                "--only", "fixture_b", "--only", "agree", "--fixture-dir", str(fx)],
                               capture_output=True, text=True, env=env, cwd=str(ROOT), timeout=900)
            return p.returncode, p.stdout + p.stderr
        finally:
            shutil.rmtree(d, ignore_errors=True)
            shutil.rmtree(fx, ignore_errors=True)

    def test_a_star_fails_the_check_where_it_used_to_pass_it(self):
        rc, out = self.check(["*"])
        self.assertEqual(rc, 2, out)
        self.assertIn("execution_record is misdeclared", out)

    def test_a_bounded_record_still_excuses_the_measurement_and_judges_the_result(self):
        rc, out = self.check(["out.json::measured.*"])
        self.assertEqual(rc, 2, out)                       # `result.lfc` moved, and is judged
        self.assertIn("result.lfc", out)
        self.assertNotIn("misdeclared", out)


if __name__ == "__main__":
    unittest.main()
