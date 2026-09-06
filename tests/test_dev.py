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


class HarnessDeclaresItsOwnPoints(unittest.TestCase):
    def test_the_harness_devpoints_is_valid(self):
        doc = P.load(ROOT)
        self.assertEqual(doc["tool"], "sch")
        self.assertIn("plugin", doc["points"])


if __name__ == "__main__":
    unittest.main()
