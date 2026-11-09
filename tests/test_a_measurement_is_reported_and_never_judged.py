#!/usr/bin/env python3
"""What a run records of its own execution is reported and never judged - where the TOOL declares
it; a byte count is not content; and a refusal is a result only when both shapes give it (autodev
W019, GAP-C41, and its verifier's D1 and D2).

FOUND BY THE BLIND CONVERSION OF de (scProfile docs/MIGRATIONS.md, autodev W013). With the
plugin's own interpreter, de ran on both fixture shapes and the shapes agreed on every number DE
writes - and `agree` failed, on wall time, CPU time, resident memory, the cores used and the cost
and memory models fitted from them: two shapes are two executions on a shared machine, and which
of those fields moved was different on every run. Its first baseline named eight file sizes as
unstable, and a third execution moved a different eight. And where the fixture refuses exactly as
the point declares it may, `agree` passed having compared nothing and `baseline` either failed
every product as absent or left the check incomplete for ever.

WHICH FIELDS ARE THE EXECUTION'S OWN RECORD IS THE TOOL'S DECLARATION, `fixture.execution_record`
(globs of `product::key`); nothing else is excused, whatever it is called. The first version read
the quantities off the keys' words, and its verifier showed results named `memory_score`,
`transport_cost`, `ot.cost`, populations `Memory_B` and `CD8_memory`, going unjudged.

AND ONE SHAPE REFUSING IS A DISAGREEMENT: the two shapes are one cohort, so a refusal that depends
on which names were asked is what `agree` exists to find. Only both refusing is "nothing to compare".

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

# What this tool would declare as its run's record of its own execution - spelled as de's host
# writes it, with a CSV column and a camelCase key, so the declaration is shown to reach both.
RECORD = ["kernels/*/out.json::measured.wall_s", "kernels/*/out.json::measured.cpu_s",
          "kernels/*/out.json::measured.peak_rss_gb", "kernels/*/out.json::measured.cores_*",
          "report.json::cores_model.*", "report.json::cost_model.*",
          "report.json::memory_model.*", "report.json::timing.*", "timings.csv::wall_s"]


# One run of a plugin on the fixture: the RESULT it computed, and its record of its own execution.
def _write_run(d: Path, *, wall, cpu, rss, peak, rate_s, rate_gb, log2fc=1.5, h5ad=b"OBJ" * 64):
    (d / "kernels" / "x").mkdir(parents=True, exist_ok=True)
    (d / "kernels" / "x" / "out.json").write_text(json.dumps({
        "config": {"alpha": 0.05, "min_cells": 10},
        "measured": {"wall_s": wall, "cpu_s": cpu, "peak_rss_gb": rss,
                     "cores_mean": round(cpu / wall, 2), "cores_given": 4, "n_cells": 2000},
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


class AgreeReportsTheDeclaredExecutionRecord(unittest.TestCase):

    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix="sch-c41-"))
        self.a, self.b = self.d / "run_a", self.d / "run_b"
        _write_run(self.a, wall=43.26, cpu=80.86, rss=0.674, peak=1.87, rate_s=2163.0, rate_gb=33.7)
        _write_run(self.b, wall=42.86, cpu=80.30, rss=0.676, peak=1.91, rate_s=2143.0, rate_gb=33.8)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def cmp(self, record=RECORD):
        fa, fb = B.fingerprint(self.a), B.fingerprint(self.b)
        # nothing declared is the call every version takes, so the base is held to it as it is
        return (L.shape_comparison(fa, fb, record=record) if record
                else L.shape_comparison(fa, fb))

    def test_two_shapes_that_differ_only_in_their_declared_record_agree(self):
        self.assertEqual(self.cmp()["disagree"], [])

    def test_undeclared_the_same_fields_are_judged(self):
        found = self.cmp(record=())["disagree"]
        self.assertTrue(any("measured.wall_s" in f for f in found), found)
        self.assertTrue(any("cost_model.x.s_per_100k" in f for f in found), found)

    def test_the_record_is_reported_and_everything_else_is_still_compared(self):
        c = self.cmp()
        reported = {k for k, _x, _y in c["resources"]}
        for k in ("kernels/x/out.json::measured.wall_s", "kernels/x/out.json::measured.cores_mean",
                  "report.json::cores_model.x.peak", "report.json::cost_model.x.s_per_100k",
                  "report.json::memory_model.x.gb_per_100k", "report.json::timing.wallTime",
                  "timings.csv::wall_s"):
            self.assertIn(k, reported)
        for k in ("kernels/x/out.json::result.log2fc", "kernels/x/out.json::measured.n_cells",
                  "kernels/x/out.json::config.alpha", "report.json::describe.n_obs",
                  "timings.csv::n_genes.sum"):
            self.assertIn(k, c["compared"], k)
        self.assertFalse(reported & set(c["compared"]))

    def test_a_result_that_moved_beside_the_record_still_fails(self):
        _write_run(self.b, wall=42.86, cpu=80.30, rss=0.676, peak=1.91, rate_s=2143.0,
                   rate_gb=33.8, log2fc=-1.5)
        found = self.cmp()["disagree"]
        self.assertEqual(len(found), 1, found)
        self.assertIn("result.log2fc", found[0])
        self.assertIn("SIGN FLIPPED", found[0])

    def test_the_tier_reads_the_declaration_and_says_what_it_did_and_did_not_judge(self):
        res = [{"tier": "fixture_a", "ok": True, "skipped": False},
               {"tier": "fixture_b", "ok": True, "skipped": False}]
        doc = {"_root": str(self.d), "fixture": {"command": ["true"], "execution_record": RECORD}}
        r = L.t_agree(doc, "", "x", self.d, res)
        self.assertTrue(r["ok"], r["evidence"])
        text = "\n".join(r["evidence"])
        self.assertIn("value(s) compared", text)
        self.assertIn("declared execution record", text)
        self.assertIn("measured.wall_s", text)          # it moved, so its two values are shown
        # without the declaration the tier fails, and says where a tool declares it
        doc["fixture"].pop("execution_record")
        r = L.t_agree(doc, "", "x", self.d, res[:2])
        self.assertFalse(r["ok"])
        self.assertIn("fixture.execution_record", "\n".join(r["evidence"]))


class ANameIsNotADeclaration(unittest.TestCase):
    """The verifier's probe (autodev W019, D2): outputs whose names happen to carry the words of a
    resource. Each differs between the shapes, so each must be judged - declared record or not."""

    def setUp(self):
        self.t = Path(tempfile.mkdtemp(prefix="sch-c41n-"))
        for sub, v in (("a", 10.0), ("b", 99.0)):
            d = self.t / sub
            d.mkdir()
            (d / "scores.csv").write_text("population,memory_score,transport_cost,n_cells\n"
                                          f"T,{v},{2 * v},100\n")
            (d / "out.json").write_text(json.dumps({
                "result": {"n_hits": 12},
                "per_label": {"Memory_B": {"n": v}, "CD8_memory": {"frac": v / 10}},
                "ot": {"cost": v * 3}, "coresets": {"n": v}, "measured": {"wall_s": v}}))

    def tearDown(self):
        shutil.rmtree(self.t, ignore_errors=True)

    def test_a_result_named_with_a_resource_word_is_judged(self):
        fa, fb = B.fingerprint(self.t / "a"), B.fingerprint(self.t / "b")
        for record in ((), ["out.json::measured.*"]):
            # undeclared first, by the call every version takes
            found = " ".join((L.shape_comparison(fa, fb, record=record) if record
                              else L.shape_comparison(fa, fb))["disagree"])
            for name in ("scores.csv::memory_score", "scores.csv::transport_cost",
                         "per_label.Memory_B.n", "per_label.CD8_memory.frac", "ot.cost",
                         "coresets.n"):
                self.assertIn(name, found, (record, found))
            self.assertEqual("measured.wall_s" in found, not record)
            whats = [x["what"] for x in (B.compare(fb, fa, record) if record
                                         else B.compare(fb, fa))]
            for name in ("memory_score.sum", "transport_cost.sum", "per_label.Memory_B.n",
                         "ot.cost", "coresets.n"):
                self.assertIn(name, whats, (record, whats))


class TheBaselineJudgesContentOnly(unittest.TestCase):

    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix="sch-c41b-"))

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_a_baseline_check_where_only_the_record_and_byte_counts_moved_is_clean(self):
        a, b = self.d / "a", self.d / "b"
        _write_run(a, wall=43.26, cpu=80.86, rss=0.674, peak=1.87, rate_s=2163.0, rate_gb=33.7)
        _write_run(b, wall=9.8, cpu=20.1, rss=0.701, peak=2.05, rate_s=490.0, rate_gb=35.1)
        self.assertEqual(B.compare(B.fingerprint(b), B.fingerprint(a), RECORD), [])
        self.assertIn("measured.wall_s", [x["what"] for x in B.compare(B.fingerprint(b),
                                                                       B.fingerprint(a))])
        rep = B.reported(B.fingerprint(a), RECORD)
        self.assertIn("report.json::products[0].bytes", rep["byte_counts"])
        self.assertIn("kernels/x/out.json::measured.wall_s", rep["resources"])
        _write_run(b, wall=9.8, cpu=20.1, rss=0.701, peak=2.05, rate_s=490.0, rate_gb=35.1,
                   log2fc=2.0)
        self.assertEqual([x["what"] for x in B.compare(B.fingerprint(b), B.fingerprint(a), RECORD)],
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

    @unittest.skipUnless(HAVE_ANNDATA, "writing an AnnData file needs anndata")
    def test_an_objects_shape_and_keys_show_when_its_content_is_unstable(self):
        """The verifier's note on the size: once content is named unstable, a size change no
        longer showed - an object that doubled passed. Its shape and keys are read instead."""
        import anndata as ad
        import numpy as np
        run = self.d / "run"
        run.mkdir()

        def write(n, layers=()):
            obj = ad.AnnData(np.full((n, 5), float(n), dtype="float32"))
            for name in layers:
                obj.layers[name] = obj.X.copy()
            obj.write_h5ad(run / "obj.h5ad")
        write(10)
        (run / "r.json").write_text('{"k": 1.0}')
        path = self.d / "b.json"
        B.record(run, path)
        ref = json.loads(path.read_text())
        self.assertEqual(ref["products"]["obj.h5ad"]["structure"]["n_obs"], 10)
        ref["not_execution_stable"] = ["obj.h5ad::content"]      # it embeds a timing
        path.write_text(json.dumps(ref))
        write(10)
        self.assertEqual(B.check(run, path)[0], [])
        write(20)
        self.assertEqual([x["what"] for x in B.check(run, path)[0]], ["structure"])
        write(10, layers=("counts",))
        diffs = B.check(run, path)[0]
        self.assertEqual([x["what"] for x in diffs], ["structure"])
        self.assertIn("layers", diffs[0]["detail"])


class ARefusalOnTheFixture(unittest.TestCase):

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

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _fixture(self, refusing):
        """The tool refuses on the shapes named, and on the others runs and writes its result one
        level down, as scProfile's `run --out {out}/run` does."""
        body = ("import os, sys, json, pathlib\n"
                "out = pathlib.Path(sys.argv[1])\n"
                f"if os.environ.get('SCH_DEV_FIXTURE') in {tuple(refusing)!r}:\n"
                "    print('NOT READY HERE: the design could not be keyed'); sys.exit(2)\n"
                "(out / 'run').mkdir(parents=True, exist_ok=True)\n"
                "json.dump({'result': {'log2fc': 1.5}}, open(out / 'run' / 'out.json', 'w'))\n")
        self.doc["fixture"] = {"command": [["python3", "-c", body, "{out}"]],
                               "accepts_refusal": True, "refusal_says": "NOT READY HERE",
                               "products": []}
        res = []
        for sh in ("a", "b"):
            L._fixture_tier(self.doc, "widget", "alpha", sh, self.fx, res, f"fixture_{sh}")
        self.assertTrue(all(r["ok"] for r in res), res)
        return res

    def test_both_shapes_refusing_leave_agree_nothing_to_compare(self):
        res = self._fixture(("a", "b"))
        self.assertTrue(all(r.get("refused") for r in res))
        r = L.t_agree(self.doc, "widget", "alpha", self.fx, res)
        self.assertFalse(r["applicable"], r)
        self.assertTrue(r["skipped"])
        self.assertIn("both shapes", r["evidence"][0])

    def test_one_shape_refusing_fails_agree_and_names_it(self):
        """The verifier's D1: shape b refused under its names while shape a ran and wrote its
        result; `agree` read "not applicable". It is the PBS 712313 failure class."""
        for refusing, ran in (("b", "a"), ("a", "b")):
            res = self._fixture((refusing,))
            r = L.t_agree(self.doc, "widget", "alpha", self.fx, res)
            self.assertFalse(r["ok"], r)
            self.assertFalse(r["skipped"])
            self.assertIn(f"fixture_{refusing} refused and fixture_{ran} ran", r["evidence"][0])

    def test_the_baseline_is_not_applicable_on_a_refusal_with_or_without_a_record(self):
        res = self._fixture(("a", "b"))
        r = L.t6_baseline(self.doc, self.fx, res, "alpha", point_name="widget")
        self.assertTrue(r["ok"], r)
        self.assertFalse(r["applicable"], r)
        bdir = self.d / "tests" / "baselines"
        bdir.mkdir(parents=True)
        run = self.d / "realrun"
        _write_run(run, wall=1.0, cpu=1.0, rss=0.1, peak=1.0, rate_s=1.0, rate_gb=1.0)
        B.record(run, bdir / "alpha.baseline.json")
        res = self._fixture(("a", "b"))
        r = L.t6_baseline(self.doc, self.fx, res, "alpha", point_name="widget")
        self.assertTrue(r["ok"], r["evidence"])
        self.assertFalse(r["applicable"], r)

    def test_a_refusal_is_never_recorded_as_a_baseline(self):
        res = self._fixture(("a", "b"))
        r = L.t6_baseline(self.doc, self.fx, res, "alpha", record=True, point_name="widget")
        self.assertFalse(r["ok"], r)
        self.assertTrue(r["skipped"] and r["applicable"], r)       # could not: exit 3, not 0
        self.assertIn("refusing to record", r["evidence"][0])
        self.assertFalse((self.d / "tests" / "baselines" / "alpha.baseline.json").exists())

    def test_a_shape_that_did_not_run_leaves_no_run_to_hold_or_record(self):
        """The verifier's residual: shape a skipped - its fixture not generated - while an earlier
        check's run_a is still in the directory; the baseline read that run."""
        (self.fx / "run_a").mkdir()
        (self.fx / "run_a" / "out.json").write_text('{"an_earlier_check": 1.0}')
        (self.fx / "fixture_a.h5ad").unlink()
        self.doc["fixture"] = {"command": ["python3", "-c", "pass"], "products": []}
        res = []
        L._fixture_tier(self.doc, "widget", "alpha", "a", self.fx, res, "fixture_a")
        self.assertTrue(res[0]["skipped"])
        for record in (False, True):
            r = L.t6_baseline(self.doc, self.fx, res, "alpha", record=record, point_name="widget")
            self.assertFalse(r["ok"], r)
            self.assertTrue(r["skipped"] and r["applicable"], r)
        self.assertFalse((self.d / "tests" / "baselines" / "alpha.baseline.json").exists())


@unittest.skipUnless(HAVE_ANNDATA, "the fixture needs anndata, which this interpreter has not got")
class ThroughTheRealCli(unittest.TestCase):
    """`sch dev check` with the ladder's own fixture, both shapes, the real CLI: the record declared
    and not, and one shape refusing (the verifier's asym_cli). One fixture serves all three."""

    @classmethod
    def setUpClass(cls):
        cls.fx = Path(tempfile.mkdtemp(prefix="sch-c41fx-"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.fx, ignore_errors=True)

    def _check(self, fixture_yaml):
        d = Path(tempfile.mkdtemp(prefix="sch-c41cli-"))
        try:
            (d / "pkg").mkdir()
            (d / "pkg" / "reg.py").write_text("WIDGETS = {'alpha': 1}\n")
            (d / "DEVPOINTS.yaml").write_text(DECL + fixture_yaml)
            env = dict(os.environ, PYTHONPATH=str(ROOT))
            p = subprocess.run([sys.executable, "-m", "sch", "dev", "check", "--root", str(d),
                                "--point", "widget", "--name", "alpha", "--only", "fixture_a",
                                "--only", "fixture_b", "--only", "agree",
                                "--fixture-dir", str(self.fx)],
                               capture_output=True, text=True, env=env, cwd=str(ROOT), timeout=900)
            return p.returncode, p.stdout + p.stderr
        finally:
            shutil.rmtree(d, ignore_errors=True)

    BODY = ("import json, os, pathlib, sys, time\n"
            "out = pathlib.Path(sys.argv[1]); t = time.time()\n"
            "if os.environ.get('SCH_DEV_FIXTURE') in REFUSING:\n"
            "    print('NOT READY HERE'); sys.exit(2)\n"
            "json.dump({'result': {'n_obs_read': 2000.0},\n"
            "           'measured': {'wall_s': t % 97.0, 'peak_rss_gb': (t * 7) % 3.0}},\n"
            "          open(out / 'out.json', 'w'))\n")

    def _yaml(self, refusing=(), record=True):
        body = self.BODY.replace("REFUSING", repr(tuple(refusing)))
        return textwrap.dedent(f"""\
            fixture:
              command: ["{{python}}", "-c", {json.dumps(body)}, "{{out}}"]
              products: []
              accepts_refusal: true
              refusal_says: "NOT READY HERE"
            """) + ('  execution_record: ["out.json::measured.*"]\n' if record else "")

    def test_the_declared_record_is_reported_and_agree_is_green(self):
        rc, out = self._check(self._yaml())
        self.assertEqual(rc, 0, out)
        self.assertIn("reported, not judged", out)

    def test_undeclared_the_same_run_fails_agree_and_says_where_to_declare(self):
        rc, out = self._check(self._yaml(record=False))
        self.assertEqual(rc, 2, out)
        self.assertIn("fixture.execution_record", out)

    def test_one_shape_refusing_fails_agree(self):
        rc, out = self._check(self._yaml(refusing=("b",)))
        self.assertEqual(rc, 2, out)
        self.assertIn("fixture_b refused and fixture_a ran", out)


if __name__ == "__main__":
    unittest.main()
