"""The development suite: does it read a declaration, catch what it claims to catch, and refuse
what it claims to refuse?

The three tests that matter most here are the negative ones. A scaffolder that writes files is
easy to believe; a checker is only worth what it REFUSES, so `test_job_refuses_*` and
`test_registration_absent_is_reported` are the ones to read first. The fixture tests assert every
hazard is actually present, because a hazard named in a manifest and missing from the data is
worse than no hazard at all - it is a claim a reader will trust.
"""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from sch.dev import baseline as B
from sch.dev import fixture as F
from sch.dev import job as J
from sch.dev import points as P

ROOT = Path(__file__).resolve().parents[1]

DECL = """
tool: demo
devpoints: 1
points:
  widget:
    what: a thing
    lives: pkg
    register:
      - {file: pkg/reg.py, table: WIDGETS}
    must_declare: [state_version]
    proves: it runs
    cannot_prove: that it is right
"""


class Devpoints(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / "pkg").mkdir()
        (self.d / "pkg" / "reg.py").write_text("WIDGETS = {'alpha': 1, 'beta': 2}\nOTHER = [x for x in ()]\n")
        (self.d / "DEVPOINTS.yaml").write_text(DECL)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_loads_and_finds_upwards(self):
        (self.d / "pkg" / "deep").mkdir()
        doc = P.load(self.d / "pkg" / "deep")
        self.assertEqual(doc["tool"], "demo")

    def test_registration_present_and_absent(self):
        doc = P.load(self.d)
        self.assertTrue(P.registration(doc, "widget", "alpha")[0]["present"])
        self.assertFalse(P.registration(doc, "widget", "gamma")[0]["present"])
        self.assertEqual(sorted(P.existing(doc, "widget")), ["alpha", "beta"])

    def test_unreadable_registry_is_not_reported_as_empty(self):
        """A registry built by a comprehension cannot be read; saying so is the point. Reporting
        it as empty would turn "I cannot see" into "it is not there"."""
        self.assertIsNone(P._table_keys(self.d / "pkg" / "reg.py", "OTHER"))

    def test_a_point_missing_cannot_prove_is_rejected(self):
        (self.d / "DEVPOINTS.yaml").write_text(DECL.replace("    cannot_prove: that it is right\n", ""))
        with self.assertRaises(P.DevpointsError):
            P.load(self.d)

    def test_unknown_point_names_the_ones_that_exist(self):
        doc = P.load(self.d)
        with self.assertRaises(P.DevpointsError) as e:
            P.point(doc, "sprocket")
        self.assertIn("widget", str(e.exception))


class Fixture(unittest.TestCase):
    def test_deterministic(self):
        self.assertEqual(F.digest(F.build(n_cells=300, n_genes=120)),
                         F.digest(F.build(n_cells=300, n_genes=120)))

    def test_a_different_seed_is_a_different_cohort(self):
        self.assertNotEqual(F.digest(F.build(seed=1, n_cells=300, n_genes=120)),
                            F.digest(F.build(seed=2, n_cells=300, n_genes=120)))

    def test_every_declared_hazard_is_present(self):
        c = F.build()
        o, X, g = c["obs"], c["X"], c["genes"]
        found = {
            "tiny_sample": int((o["_role_sample"] == "S12").sum()) == 7,
            "arm_exclusive_type": "Type_zeta" not in set(o.loc[o["_role_condition"] == "ctrl", "_role_cell_type"]),
            "singleton_type": int((o["_role_cell_type"] == "Type_eta").sum()) == 1,
            "nan_in_numeric_obs": bool(o["pct_counts_mt_like"].isna().any()),
            "unused_category": "S99" in list(o["_role_sample"].cat.categories)
                               and int((o["_role_sample"] == "S99").sum()) == 0,
            "duplicate_barcodes": bool(o["barcode"].duplicated().any()),
            "empty_cell": float(X[0].sum()) == 0.0,
            "empty_gene": float(X[:, -1].sum()) == 0.0,
            "constant_gene": len(set(X[1:, -2].tolist())) == 1 and X[1, -2] != 0,
            "gene_named_like_obs": "condition" in g,
            "prefix_sample_names": {"S1", "S10"} <= set(map(str, o["_role_sample"].unique())),
            "awkward_label": any(" " in t and "/" in t for t in map(str, o["_role_cell_type"].unique())),
            "mixed_object_obs": bool(o["free_note"].isna().any()) and bool(o["free_note"].notna().any()),
            "design_row_without_cells": "S98" in set(c["design"]["_role_sample"])
                                        and int((o["_role_sample"] == "S98").sum()) == 0,
            "mito_genes": sum(x.startswith("MT-") for x in g) >= 3,
            "constant_covariate_in_arm": float(o.loc[o["_role_condition"] == "treated", "_role_covariate"].std()) == 0.0,
        }
        self.assertEqual(sorted(found), sorted(F.HAZARDS),
                         "the manifest and the test disagree about which hazards exist")
        self.assertEqual([k for k, v in found.items() if not v], [])

    def test_obs_names_are_unique_despite_the_duplicate_barcode(self):
        self.assertTrue(F.build()["obs"].index.is_unique)

    def test_the_two_shapes_rename_every_role_and_share_nothing_by_accident(self):
        for role, names in F.ROLES.items():
            self.assertNotEqual(names["a"], names["b"], f"role {role} is named the same in both shapes")


class Baseline(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / "report.json").write_text(json.dumps({"score": 1.0, "n": 5, "started": "x"}))
        (self.d / "t.csv").write_text("a,b\n1,2\n3,4\n")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_identical_run_has_no_differences(self):
        self.assertEqual(B.compare(B.fingerprint(self.d), B.fingerprint(self.d)), [])

    def test_a_volatile_field_is_not_a_difference(self):
        ref = B.fingerprint(self.d)
        (self.d / "report.json").write_text(json.dumps({"score": 1.0, "n": 5, "started": "later"}))
        self.assertEqual(B.compare(B.fingerprint(self.d), ref), [])

    def test_a_moved_number_is_a_difference(self):
        ref = B.fingerprint(self.d)
        (self.d / "report.json").write_text(json.dumps({"score": 1.5, "n": 5, "started": "x"}))
        self.assertEqual([d["what"] for d in B.compare(B.fingerprint(self.d), ref)], ["score"])

    def test_a_moved_csv_column_is_a_difference(self):
        ref = B.fingerprint(self.d)
        (self.d / "t.csv").write_text("a,b\n1,2\n3,9\n")
        self.assertIn("b.sum", [d["what"] for d in B.compare(B.fingerprint(self.d), ref)])

    def test_missing_baseline_raises_rather_than_passing(self):
        with self.assertRaises(FileNotFoundError):
            B.check(self.d, self.d / "nope.json")

    def test_true_and_one_are_not_the_same_value(self):
        ref = B.fingerprint(self.d)
        (self.d / "report.json").write_text(json.dumps({"score": True, "n": 5, "started": "x"}))
        self.assertEqual([d["what"] for d in B.compare(B.fingerprint(self.d), ref)], ["score"])


class Job(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / "ref").mkdir()
        (self.d / "tool" / ".git").mkdir(parents=True)
        (self.d / "tool" / ".git" / "HEAD").write_text("a" * 40 + "\n")
        (self.d / "ref" / "STATUS.json").write_text(json.dumps(
            {"tool": "t", "status": "ok", "argv": ["t", "run", "--key", "cell_type_forced", "--out", "/old"]}))
        (self.d / "ref" / "report.json").write_text('{"seed": 1}')
        self.kw = dict(ref_dir=str(self.d / "ref"), rundir=str(self.d / "new"),
                       tooldir=str(self.d / "tool"), queue="long", select="select=1:ncpus=1")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_the_command_comes_from_the_reference_argv(self):
        text = J.emit(prediction="identical", **self.kw)
        self.assertIn("cell_type_forced", text)
        self.assertIn(str(self.d / "new"), text)
        self.assertNotIn("--out /old", text)

    def test_refuses_without_a_prediction(self):
        with self.assertRaises(ValueError):
            J.emit(prediction="   ", **self.kw)

    def test_refuses_when_the_reference_records_no_argv(self):
        (self.d / "ref" / "STATUS.json").write_text(json.dumps({"tool": "t", "status": "ok"}))
        with self.assertRaises(ValueError) as e:
            J.emit(prediction="identical", **self.kw)
        self.assertIn("argv", str(e.exception))

    def test_refuses_when_the_reference_argv_names_no_output(self):
        (self.d / "ref" / "STATUS.json").write_text(json.dumps(
            {"tool": "t", "status": "ok", "argv": ["t", "run"]}))
        with self.assertRaises(ValueError):
            J.emit(prediction="identical", **self.kw)

    def test_refuses_without_a_queue(self):
        kw = dict(self.kw, queue="")
        with self.assertRaises(ValueError):
            J.emit(prediction="identical", **kw)

    def test_the_checkout_is_frozen_at_the_commit_read_from_git(self):
        self.assertIn("a" * 40, J.emit(prediction="identical", **self.kw))

    def test_products_are_taken_from_the_reference_directory(self):
        self.assertEqual(sorted(J.products_of(self.d / "ref")), ["STATUS.json", "report.json"])

    def test_a_host_pin_carries_the_queue_finding(self):
        text = J.emit(prediction="identical", **dict(self.kw, select="select=1:ncpus=1:host=n42"))
        self.assertIn("Insufficient amount", text)


class Scaffold(unittest.TestCase):
    """`sch dev new` is the one command that WRITES into a repository, so what it declines to do
    matters as much as what it does."""

    def setUp(self):
        from sch.dev import scaffold as S
        self.S = S
        self.d = Path(tempfile.mkdtemp())
        (self.d / "pkg").mkdir()
        (self.d / "tests").mkdir()
        (self.d / "pkg" / "reg.py").write_text("WIDGETS = {'alpha': 1}\n")
        (self.d / "DEVPOINTS.yaml").write_text(DECL.replace("lives: pkg", "lives: pkg"))

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_writes_the_mechanism_its_spec_and_its_test(self):
        info = self.S.new(self.d, "widget", "gamma")
        self.assertTrue((self.d / "pkg" / "gamma.py").is_file())
        self.assertTrue((self.d / "pkg" / "SPEC.gamma.md").is_file())
        self.assertTrue((self.d / "tests" / "test_widget_gamma.py").is_file())
        self.assertEqual(len(info["written"]), 3)

    def test_the_spec_asks_for_what_the_code_cannot_say(self):
        self.S.new(self.d, "widget", "gamma")
        spec = (self.d / "pkg" / "SPEC.gamma.md").read_text()
        for heading in ("What it SEES", "What it CANNOT SHOW", "What would make it wrong",
                        "state_version"):
            self.assertIn(heading, spec)

    def test_the_scaffolded_test_fails_until_it_is_written(self):
        self.S.new(self.d, "widget", "gamma")
        t = (self.d / "tests" / "test_widget_gamma.py").read_text()
        self.assertIn("raise AssertionError", t)
        self.assertNotIn("import sch", t)      # children vendor; they do not import the harness

    def test_it_prints_the_registration_rather_than_performing_it(self):
        info = self.S.new(self.d, "widget", "gamma")
        self.assertTrue(any("WIDGETS" in e for e in info["register"]))
        self.assertNotIn("gamma", (self.d / "pkg" / "reg.py").read_text())

    def test_refuses_a_name_already_registered(self):
        with self.assertRaises(ValueError):
            self.S.new(self.d, "widget", "alpha")

    def test_refuses_a_point_that_is_not_declared(self):
        from sch.dev import points as PP
        with self.assertRaises(PP.DevpointsError):
            self.S.new(self.d, "sprocket", "gamma")

    def test_does_not_overwrite_without_force(self):
        self.S.new(self.d, "widget", "gamma")
        (self.d / "pkg" / "gamma.py").write_text("mine\n")
        info = self.S.new(self.d, "widget", "gamma", force=False)
        self.assertEqual((self.d / "pkg" / "gamma.py").read_text(), "mine\n")
        self.assertIn("pkg/gamma.py", info["skipped"])


class BaselineRoundTrip(unittest.TestCase):
    def test_record_then_check_agrees_then_disagrees(self):
        d = Path(tempfile.mkdtemp())
        try:
            run = d / "run"
            run.mkdir()
            (run / "report.json").write_text(json.dumps({"score": 0.5}))
            path = d / "b.json"
            B.record(run, path)
            self.assertEqual(B.check(run, path)[0], [])
            (run / "report.json").write_text(json.dumps({"score": 0.6}))
            diffs, _ = B.check(run, path)
            self.assertEqual([x["what"] for x in diffs], ["score"])
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_a_difference_within_tolerance_is_not_a_difference(self):
        d = Path(tempfile.mkdtemp())
        try:
            run = d / "run"
            run.mkdir()
            (run / "report.json").write_text(json.dumps({"score": 1.0}))
            path = d / "b.json"
            B.record(run, path)
            (run / "report.json").write_text(json.dumps({"score": 1.0 + 1e-13}))
            self.assertEqual(B.check(run, path)[0], [])
        finally:
            shutil.rmtree(d, ignore_errors=True)


class LeakTierFindsItsWordList(unittest.TestCase):
    def test_the_environment_variable_is_consulted_before_the_repository(self):
        import os
        from sch.dev import ladder as L
        d = Path(tempfile.mkdtemp())
        try:
            (d / "pkg").mkdir()
            (d / "pkg" / "reg.py").write_text("WIDGETS = {}\nNAME = 'Belvedere'\n")
            (d / "DEVPOINTS.yaml").write_text(DECL)
            words = d / "words.txt"
            words.write_text("# a comment\nBelvedere\n")
            os.environ["DEMO_FORBIDDEN_TERMS"] = str(words)
            try:
                res = []
                L.t5_leak(P.load(d), d, res)
            finally:
                del os.environ["DEMO_FORBIDDEN_TERMS"]
            self.assertFalse(res[0]["ok"], res[0]["evidence"])
            self.assertTrue(any("Belvedere" in e for e in res[0]["evidence"]))
        finally:
            shutil.rmtree(d, ignore_errors=True)


class RefusalIsNotFailure(unittest.TestCase):
    """A tool that correctly declines on the fixture must not be reported as broken - and a tool
    that crashed must not be reported as having declined."""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / "pkg").mkdir()
        (self.d / "pkg" / "reg.py").write_text("WIDGETS = {'alpha': 1}\n")
        (self.d / "fx").mkdir()
        for shape in ("a", "b"):
            (self.d / "fx" / f"fixture_{shape}.h5ad").write_text("not really an object")
            (self.d / "fx" / f"design_{shape}.csv").write_text("x\n1\n")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _tier(self, spec):
        from sch.dev import ladder as L
        decl = DECL + "".join(f"\n    {k}: {v}" for k, v in [])
        (self.d / "DEVPOINTS.yaml").write_text(DECL)
        doc = P.load(self.d)
        doc["fixture"] = spec
        res = []
        L._fixture_tier(doc, "widget", "alpha", "a", self.d / "fx", res, "fixture_a")
        return res[0]

    def test_a_declared_refusal_passes(self):
        r = self._tier({"command": ["python3", "-c", "import sys; print('DESIGN IS CONFOUNDED'); sys.exit(2)"],
                        "accepts_refusal": True, "refusal_says": "DESIGN IS CONFOUNDED"})
        self.assertTrue(r["ok"], r["evidence"])
        self.assertTrue(any("refused, as this point declares" in e for e in r["evidence"]))

    def test_a_crash_does_not_pass_as_a_refusal(self):
        r = self._tier({"command": ["python3", "-c", "raise SystemExit(2)"],
                        "accepts_refusal": True, "refusal_says": "DESIGN IS CONFOUNDED"})
        self.assertFalse(r["ok"])

    def test_accepts_refusal_without_a_phrase_is_refused(self):
        """Otherwise the tier is switched off by a single key, and every crash becomes a pass."""
        r = self._tier({"command": ["python3", "-c", "raise SystemExit(2)"], "accepts_refusal": True})
        self.assertFalse(r["ok"])
        self.assertTrue(any("without refusal_says" in e for e in r["evidence"]))


class HarnessDeclaresItsOwnPoints(unittest.TestCase):
    def test_the_harness_devpoints_is_valid(self):
        doc = P.load(ROOT)
        self.assertEqual(doc["tool"], "sch")
        self.assertIn("plugin", doc["points"])


if __name__ == "__main__":
    unittest.main()
