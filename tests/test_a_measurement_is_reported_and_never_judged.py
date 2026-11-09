#!/usr/bin/env python3
"""What an execution measures of itself is reported and never judged; a byte count is not
content; and a declared refusal is a result with nothing to compare (autodev W019, GAP-C41).

FOUND BY THE BLIND CONVERSION OF de (scProfile docs/MIGRATIONS.md, autodev W013). With the
plugin's own interpreter, de ran on both fixture shapes and the shapes agreed on every number DE
writes - and `agree` failed, on wall time, CPU time, resident memory, the cores used and the cost
and memory models fitted from them: two shapes are two executions on a shared machine, and which
of those fields moved was different on every run. Its first baseline named eight file sizes as
unstable - a size moves with the digits of every timing written into the file - so a third
execution failed on a different eight. And on a machine without the plugin's environment, where
the fixture refuses exactly as the point declares it may, `agree` passed having compared nothing
and `baseline` either failed every product as absent or left the check incomplete for ever.

THE RULE, ONCE, in `sch/dev/baseline.py`: a number whose key names a resource of the execution
(`RESOURCE_WORDS`) is recorded and reported, never compared - by `agree` or by the baseline. Nothing
the fixture writes is such a name, which this file checks against the fixture itself.

Run: PYTHONPATH=. python3 tests/test_a_measurement_is_reported_and_never_judged.py
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
from sch.dev import fixture as FX                                               # noqa: E402
from sch.dev import ladder as L                                                 # noqa: E402
from sch.dev import points as P                                                 # noqa: E402

try:
    import anndata  # noqa: F401
    HAVE_ANNDATA = True
except ImportError:
    HAVE_ANNDATA = False

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

# The shape of one run of a plugin on the fixture: the RESULT it computed, and what the execution
# measured of itself - spelled as de's host spells them, and with a camelCase and a CSV column so
# the rule is not read off one spelling.
def _write_run(d: Path, *, wall, cpu, rss, peak, rate_s, rate_gb, log2fc=1.5, h5ad=b"OBJ" * 64):
    (d / "kernels" / "x").mkdir(parents=True, exist_ok=True)
    (d / "kernels" / "x" / "out.json").write_text(json.dumps({
        "config": {"alpha": 0.05, "min_cells": 10},
        "measured": {"wall_s": wall, "cpu_s": cpu, "peak_rss_gb": rss, "cores_mean": round(cpu / wall, 2),
                     "cores_given": 4, "n_cells": 2000},
        "result": {"log2fc": log2fc, "n_hits": 12}}))
    (d / "report.json").write_text(json.dumps({
        "cores_model": {"x": {"declared": 4, "given": 4, "mean": peak, "peak": peak, "points": 1}},
        "cost_model": {"x": {"points": 1, "s_per_100k": rate_s}},
        "memory_model": {"x": {"declared_per_100k": 7.3, "gb_per_100k": rate_gb, "points": 1}},
        "describe": {"n_obs": 2000, "n_vars": 520},
        "timing": {"wallTime": wall},
        "products": [{"path": "report.json", "bytes": int(wall * 100)}]}))
    (d / "timings.csv").write_text(f"step,wall_s,n_genes\nfit,{wall},520\n")
    (d / "obj.h5ad").write_bytes(h5ad)


class AgreeReportsWhatTheExecutionMeasured(unittest.TestCase):

    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix="sch-c41-"))
        self.a, self.b = self.d / "run_a", self.d / "run_b"
        _write_run(self.a, wall=43.26, cpu=80.86, rss=0.674, peak=1.87, rate_s=2163.0, rate_gb=33.7)
        _write_run(self.b, wall=42.86, cpu=80.30, rss=0.676, peak=1.91, rate_s=2143.0, rate_gb=33.8)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_two_shapes_that_differ_only_in_what_they_measured_agree(self):
        found = L.shape_disagreements(B.fingerprint(self.a), B.fingerprint(self.b))
        self.assertEqual(found, [], "a resource of the execution was judged as an output")

    def test_the_resources_are_reported_and_every_result_is_still_compared(self):
        cmp_ = L.shape_comparison(B.fingerprint(self.a), B.fingerprint(self.b))
        reported = {k for k, _x, _y in cmp_["resources"]}
        for k in ("kernels/x/out.json::measured.wall_s", "kernels/x/out.json::measured.cpu_s",
                  "kernels/x/out.json::measured.peak_rss_gb", "kernels/x/out.json::measured.cores_mean",
                  "report.json::cores_model.x.peak", "report.json::cost_model.x.s_per_100k",
                  "report.json::memory_model.x.gb_per_100k", "report.json::timing.wallTime",
                  "timings.csv::wall_s"):
            self.assertIn(k, reported)
        for k in ("kernels/x/out.json::result.log2fc", "kernels/x/out.json::result.n_hits",
                  "kernels/x/out.json::measured.n_cells", "kernels/x/out.json::config.alpha",
                  "report.json::describe.n_obs", "timings.csv::n_genes.sum"):
            self.assertIn(k, cmp_["compared"], k)
        self.assertFalse(reported & set(cmp_["compared"]))

    def test_a_result_that_moved_beside_them_still_fails(self):
        _write_run(self.b, wall=42.86, cpu=80.30, rss=0.676, peak=1.91, rate_s=2143.0,
                   rate_gb=33.8, log2fc=-1.5)
        found = L.shape_disagreements(B.fingerprint(self.a), B.fingerprint(self.b))
        self.assertEqual(len(found), 1, found)
        self.assertIn("result.log2fc", found[0])
        self.assertIn("SIGN FLIPPED", found[0])

    def test_the_tier_is_green_and_says_what_it_compared_and_what_it_only_reported(self):
        res = [{"tier": "fixture_a", "ok": True, "skipped": False},
               {"tier": "fixture_b", "ok": True, "skipped": False}]
        doc = {"_root": str(self.d), "fixture": {"command": ["true"]}}
        r = L.t_agree(doc, "", "x", self.d, res)
        self.assertTrue(r["ok"], r["evidence"])
        self.assertTrue(r["applicable"])
        text = "\n".join(r["evidence"])
        self.assertIn("value(s) compared", text)
        self.assertIn("reported, not judged", text)
        self.assertIn("measured.wall_s", text)          # it moved, so its two values are shown


class TheFixtureNamesNoResource(unittest.TestCase):
    """The rule reads keys, and a key of a fixture run can be a name the fixture wrote - a
    population, a sample, a gene. None of them may be read as a resource, or a number about the
    data would go unjudged."""

    def _names(self):
        names = set()
        for r in FX.ROLES.values():
            names |= {r["a"], r["b"]}
        for v in FX.VALUES.values():
            names |= {v["a"], v["b"]}
        names |= set(FX.TYPES)
        for g in FX.REAL_GENES + [g for block in FX.LR_BLOCKS.values() for g in block]:
            names |= {g, FX.respell(g, "b")}
        try:
            import numpy  # noqa: F401
            import pandas  # noqa: F401
        except ImportError:
            return names, False
        for crossed in (False, True):
            core = FX.build(crossed=crossed)
            for shape in ("a", "b"):
                obs = FX._rename(core["obs"], shape)
                names |= {str(c) for c in obs.columns}
                for c in obs.columns:
                    if str(obs[c].dtype) in ("category", "object"):
                        names |= {str(x) for x in obs[c].dropna().unique()}
                design = FX._rename(core["design"], shape)
                names |= {str(c) for c in design.columns}
                names |= {str(x) for c in design.columns for x in design[c].dropna().unique()
                          if isinstance(x, str)}
            names |= {FX.respell(g, s) for g in core["genes"] for s in ("a", "b")}
        return names, True

    def test_no_name_the_fixture_writes_is_a_resource(self):
        names, built = self._names()
        self.assertGreater(len(names), 100 if built else 40)
        hits = sorted(n for n in names if B.is_resource(n) or B.is_size(n))
        self.assertEqual(hits, [], f"fixture names read as resources: {hits}")

    def test_time_is_not_a_resource_word(self):
        # pseudotime and latent time are RESULTS of some plugins; only `wall` and `cpu` say a
        # clock was read
        for k in ("pseudotime", "latent_time", "velocity_pseudotime", "dpt_pseudotime", "time"):
            self.assertFalse(B.is_resource(k), k)
        for k in ("wall_s", "cpu_s", "peak_rss_gb", "cores_model", "memory_gb", "cost_model",
                  "runtime_s", "wallTime"):
            self.assertTrue(B.is_resource(k), k)


class TheBaselineJudgesContentOnly(unittest.TestCase):

    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix="sch-c41b-"))

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_a_baseline_check_where_only_resources_and_byte_counts_moved_is_clean(self):
        a, b = self.d / "a", self.d / "b"
        _write_run(a, wall=43.26, cpu=80.86, rss=0.674, peak=1.87, rate_s=2163.0, rate_gb=33.7)
        _write_run(b, wall=9.8, cpu=20.1, rss=0.701, peak=2.05, rate_s=490.0, rate_gb=35.1)
        self.assertEqual(B.compare(B.fingerprint(b), B.fingerprint(a)), [])
        rep = B.reported(B.fingerprint(a))
        self.assertIn("report.json::products[0].bytes", rep["byte_counts"])
        self.assertIn("kernels/x/out.json::measured.wall_s", rep["resources"])
        # and a result still moves it
        _write_run(b, wall=9.8, cpu=20.1, rss=0.701, peak=2.05, rate_s=490.0, rate_gb=35.1,
                   log2fc=2.0)
        self.assertEqual([x["what"] for x in B.compare(B.fingerprint(b), B.fingerprint(a))],
                         ["result.log2fc"])

    def test_an_opaque_files_size_is_not_compared_and_an_emptied_one_is_a_finding(self):
        run = self.d / "run"
        run.mkdir()
        (run / "obj.h5ad").write_bytes(b"x" * 4096)
        (run / "r.json").write_text('{"k": 1.0}')
        path = self.d / "b.json"
        B.record(run, path)
        ref = json.loads(path.read_text())
        ref["not_execution_stable"] = ["obj.h5ad::content"]      # it embeds a timing
        path.write_text(json.dumps(ref))
        (run / "obj.h5ad").write_bytes(b"y" * 4097)             # a digit longer
        self.assertEqual(B.check(run, path)[0], [])
        (run / "obj.h5ad").write_bytes(b"")
        self.assertEqual([x["what"] for x in B.check(run, path)[0]], ["emptied"])
        (run / "obj.h5ad").unlink()
        self.assertEqual([x["what"] for x in B.check(run, path)[0]], ["absent"])


class ADeclaredRefusalHasNothingToCompare(unittest.TestCase):

    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix="sch-c41r-"))
        (self.d / "pkg").mkdir()
        (self.d / "pkg" / "reg.py").write_text("WIDGETS = {'alpha': 1}\n")
        (self.d / "DEVPOINTS.yaml").write_text(DECL)
        self.fx = self.d / "fx"
        self.fx.mkdir()
        for shape in ("a", "b"):
            (self.fx / f"fixture_{shape}.h5ad").write_text("x")
            (self.fx / f"design_{shape}.csv").write_text("x\n1\n")
        self.doc = P.load(self.d)
        # A REFUSAL WHOSE STATUS IS NOT WHERE THE TIER USED TO LOOK: the tool writes its run one
        # level down, as scProfile's `run --out {out}/run` does, and its refusal is its words.
        self.doc["fixture"] = {
            "command": [["python3", "-c", "import sys; print('NOT READY HERE'); sys.exit(2)"],
                        ["python3", "-c", "raise SystemExit(0)"]],
            "accepts_refusal": True, "refusal_says": "NOT READY HERE", "products": []}

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _shapes(self):
        res = []
        for sh in ("a", "b"):
            L._fixture_tier(self.doc, "widget", "alpha", sh, self.fx, res, f"fixture_{sh}")
        self.assertTrue(all(r["ok"] and r.get("refused") for r in res), res)
        return res

    def test_agree_is_not_applicable_on_a_refusal(self):
        res = self._shapes()
        r = L.t_agree(self.doc, "widget", "alpha", self.fx, res)
        self.assertFalse(r["applicable"], r)
        self.assertTrue(r["skipped"])
        self.assertIn("declared refusal", r["evidence"][0])

    def test_the_baseline_is_not_applicable_on_a_refusal_with_or_without_a_record(self):
        res = self._shapes()
        r = L.t6_baseline(self.doc, self.fx, res, "alpha", point_name="widget")
        self.assertTrue(r["ok"], r)
        self.assertFalse(r["applicable"], r)
        # and with a baseline recorded where the plugin RAN: not every product absent, not FAILED
        bdir = self.d / "tests" / "baselines"
        bdir.mkdir(parents=True)
        run = self.d / "realrun"
        _write_run(run, wall=1.0, cpu=1.0, rss=0.1, peak=1.0, rate_s=1.0, rate_gb=1.0)
        B.record(run, bdir / "alpha.baseline.json")
        res = self._shapes()
        r = L.t6_baseline(self.doc, self.fx, res, "alpha", point_name="widget")
        self.assertTrue(r["ok"], r["evidence"])
        self.assertFalse(r["applicable"], r)

    def test_a_refusal_is_never_recorded_as_a_baseline(self):
        res = self._shapes()
        r = L.t6_baseline(self.doc, self.fx, res, "alpha", record=True, point_name="widget")
        self.assertFalse(r["ok"], r)
        self.assertTrue(r["skipped"] and r["applicable"], r)       # could not: exit 3, not 0
        self.assertIn("refusing to record", r["evidence"][0])
        self.assertFalse((self.d / "tests" / "baselines" / "alpha.baseline.json").exists())


@unittest.skipUnless(HAVE_ANNDATA, "the fixture needs anndata, which this interpreter has not got")
class ThroughTheRealCli(unittest.TestCase):
    """`sch dev check` on a repository whose fixture command writes, per shape, the same result and
    a different wall time and memory: the ladder's own fixture, both shapes, the real CLI."""

    def test_agree_is_green_when_only_the_execution_differs(self):
        d = Path(tempfile.mkdtemp(prefix="sch-c41cli-"))
        try:
            (d / "pkg").mkdir()
            (d / "pkg" / "reg.py").write_text("WIDGETS = {'alpha': 1}\n")
            body = ("import json, pathlib, sys, time\n"
                    "out = pathlib.Path(sys.argv[1]); t = time.time()\n"
                    "json.dump({'result': {'n_obs_read': 2000.0},\n"
                    "           'measured': {'wall_s': t % 97.0, 'peak_rss_gb': (t * 7) % 3.0}},\n"
                    "          open(out / 'out.json', 'w'))\n")
            decl = DECL + textwrap.dedent(f"""\
                fixture:
                  command: ["{{python}}", "-c", {json.dumps(body)}, "{{out}}"]
                  products: ["out.json"]
                """)
            (d / "DEVPOINTS.yaml").write_text(decl)
            env = dict(os.environ, PYTHONPATH=str(ROOT))
            p = subprocess.run([sys.executable, "-m", "sch", "dev", "check", "--root", str(d),
                                "--point", "widget", "--name", "alpha", "--only", "fixture_a",
                                "--only", "fixture_b", "--only", "agree",
                                "--fixture-dir", str(d / "fx")],
                               capture_output=True, text=True, env=env, cwd=str(ROOT), timeout=600)
            out = p.stdout + p.stderr
            self.assertEqual(p.returncode, 0, out)
            self.assertIn("reported, not judged", out)
            self.assertRegex(out, r"ok   agree")
        finally:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
