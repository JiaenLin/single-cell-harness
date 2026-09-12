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
import re
import shlex
import shutil
import tempfile
import unittest
from pathlib import Path

from sch.dev import baseline as B
from sch.dev import fixture as F
from sch.dev import job as J
from sch.dev import ladder as L
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

    def test_a_registry_can_name_the_command_that_satisfies_it(self):
        """A gate without its command sends a newcomer to hand-edit a generated document.

        scProfile's Tier 0 table is rendered from the kernel declarations, so the way to get a
        name into it is `scprofile generated --write` and never an edit. The registry entry carries
        that, `sch dev map` announces it before anyone hits the gate, and the declaration tier
        repeats it in the failure.
        """
        (self.d / "REG.md").write_text("| `alpha` | x |\n")
        (self.d / "DEVPOINTS.yaml").write_text(DECL.replace(
            "      - {file: pkg/reg.py, table: WIDGETS}",
            "      - {file: REG.md, pattern: \"^\\\\| `{name}` \\\\|\", fix: make reg}"))
        doc = P.load(self.d)
        hit = P.registration(doc, "widget", "alpha")[0]
        miss = P.registration(doc, "widget", "gamma")[0]
        self.assertTrue(hit["present"])
        self.assertFalse(miss["present"])
        self.assertEqual(miss["fix"], "make reg")
        row = L.t0_declaration(doc, "widget", "gamma", [])
        self.assertIn("make reg", " ".join(row["evidence"]))

    def test_a_registry_without_a_fix_says_nothing_about_one(self):
        """The field is optional, and an absent one must not print an empty backtick pair."""
        doc = P.load(self.d)
        self.assertEqual(P.registration(doc, "widget", "gamma")[0]["fix"], "")
        row = L.t0_declaration(doc, "widget", "gamma", [])
        self.assertNotIn("Run ``", " ".join(row["evidence"]))

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


class ACrossedDesign(unittest.TestCase):
    """The second factor, and the reason it is off by default.

    WHAT IT IS FOR. With one factor the richest thing this cohort expresses is a main effect. Four
    defects in this family lived in the branch that reads an INTERACTION - a subtraction done the
    wrong way round that stayed self-consistent, marginals emitted before the strata they average,
    a marginal arm with no object behind it, and a composed section that called five small movers
    the leading ones - and not one of them is reachable on a one-factor cohort. A plugin could
    pass every tier here and meet all four on the first real study.
    """

    def test_the_default_cohort_is_byte_for_byte_what_it_was(self):
        """THE WHOLE CONSTRAINT. Every recorded baseline in five repositories rests on this
        string. A second factor that moved it would have bought one plugin's tier with everyone
        else's evidence."""
        self.assertEqual(F.digest(F.build()), "d423a5817fdcb29e")

    def test_a_crossed_cohort_is_a_different_cohort_and_says_so(self):
        self.assertNotEqual(F.digest(F.build(crossed=True)), F.digest(F.build()))

    def test_it_is_deterministic_too(self):
        self.assertEqual(F.digest(F.build(crossed=True)), F.digest(F.build(crossed=True)))

    def test_every_cell_of_the_two_by_two_holds_two_samples(self):
        """SIX SAMPLES CANNOT DO THIS. A 2x2 out of six is 2/1 somewhere, and a cell holding one
        sample has no spread - so the simple effect it is half of is undefined and the
        interaction degrades to a main effect without saying it has."""
        d = F.build(crossed=True)["design"]
        d = d[d["_role_sample"] != "S98"]
        cells = d.groupby(["_role_condition", "_role_stratum"], observed=True).size()
        self.assertEqual(len(cells), 4, "the design is not crossed")
        self.assertEqual(sorted(cells.tolist()), [2, 2, 2, 2])

    def test_batch_is_crossed_with_both_factors_and_confounded_with_neither(self):
        """A batch confounded with the design makes every conclusion here unattributable, which
        is a real lesson and a different fixture's."""
        d = F.build(crossed=True)["design"]
        d = d[d["_role_sample"] != "S98"]
        for cell, sub in d.groupby(["_role_condition", "_role_stratum"], observed=True):
            self.assertEqual(len(set(sub["_role_batch"])), 2, f"one chip fills the cell {cell}")

    def test_the_one_factor_cohort_carries_no_second_factor_at_all(self):
        """Not an empty column, not a constant one: absent. A column of one level is a factor a
        resolver will enumerate and find nothing to compare."""
        self.assertNotIn("_role_stratum", F.build()["obs"].columns)
        self.assertNotIn("_role_stratum", F.build()["design"].columns)

    def test_the_tiny_sample_survives_the_extra_samples(self):
        """It was addressed as "S12", which the crossed design appends a sample after."""
        for crossed in (False, True):
            c = F.build(crossed=crossed)
            last = str(c["design"]["_role_sample"].iloc[-2])
            self.assertEqual(int((c["obs"]["_role_sample"] == last).sum()), 7)

    def test_the_crossed_hazards_are_declared_and_true(self):
        c = F.build(crossed=True)
        d = c["design"][c["design"]["_role_sample"] != "S98"]
        tiny = str(d["_role_sample"].iloc[-1])
        cell = d[d["_role_sample"] == tiny][["_role_condition", "_role_stratum"]].iloc[0]
        self.assertEqual(len(F.CROSSED_HAZARDS), 2)
        self.assertTrue(bool(cell["_role_stratum"]), "the tiny sample sits in no stratum")
        for _subject, sub in d.groupby("_role_subject", observed=True):
            self.assertEqual(len(set(zip(sub["_role_condition"], sub["_role_stratum"]))), 1,
                             "a subject spans two cells, so it is not nested after all")


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


class BaselineRecordsOnlyWhatTwoRunsAgreedOn(unittest.TestCase):
    """The rule the harmony finding forced: a field that moves between executions is excluded and
    named, not silently baked into a baseline that will fail on the next machine."""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / "pkg").mkdir()
        (self.d / "pkg" / "reg.py").write_text("WIDGETS = {'alpha': 1}\n")
        (self.d / "DEVPOINTS.yaml").write_text(DECL)
        self.fx = self.d / "fx"
        self.fx.mkdir()
        for shape in ("a", "b"):
            (self.fx / f"fixture_{shape}.h5ad").write_text("x")
            (self.fx / f"design_{shape}.csv").write_text("x\n1\n")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _record(self, body):
        from sch.dev import ladder as L
        doc = P.load(self.d)
        doc["fixture"] = {"command": ["python3", "-c", body, "{out}"], "products": ["out.json"]}
        res = []
        L._fixture_tier(doc, "widget", "alpha", "a", self.fx, res, "fixture_a")
        self.assertTrue(res[0]["ok"], res[0]["evidence"])
        L.t6_baseline(doc, self.fx, res, "alpha", record=True, point_name="widget")
        path = self.d / "tests" / "baselines" / "alpha.baseline.json"
        return res[-1], json.loads(path.read_text())

    def test_the_runs_account_of_itself_is_not_fingerprinted(self):
        """A seal records the job id, the host and the times. Every field in it is supposed to
        differ between runs, so baselining one produces a check that can never pass - and no
        redaction fixes it, because stripping a job id and a hostname leaves nothing."""
        d = Path(tempfile.mkdtemp())
        try:
            # An invented scheduler id, not this site's. The leak guard caught the real one
            # when it was first written here, which is the guard doing its job on its own repo.
            for sub, jid in (("a", "11.sched-00"), ("b", "12.sched-00")):
                (d / sub).mkdir()
                (d / sub / "SEALED.txt").write_text(f"exit=0\njobid={jid}\nhost=node-{sub}\n")
                (d / sub / "SEALED.cluster.txt").write_text(f"exit=0\njobid={jid}\n")
                (d / sub / "report.json").write_text('{"score": 0.5}')
            fa = B.fingerprint(d / "a")
            self.assertEqual(sorted(fa["products"]), ["report.json"])
            self.assertEqual(B.compare(fa, B.fingerprint(d / "b")), [])
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_a_file_the_baseline_calls_unstable_is_not_hashed_again(self):
        """Its content is excluded from the comparison, so reading it buys nothing - and on a
        real run it is a 40 MB object plus three PDFs, read on every check."""
        d = Path(tempfile.mkdtemp())
        try:
            run = d / "run"; run.mkdir()
            (run / "big.bin").write_bytes(b"x" * 4096)
            (run / "r.json").write_text('{"k": 1.0}')
            path = d / "b.json"
            B.record(run, path)
            ref = json.loads(path.read_text())
            ref["not_execution_stable"] = ["big.bin::content"]
            path.write_text(json.dumps(ref))
            (run / "big.bin").write_bytes(b"y" * 4096)      # same size, different bytes
            diffs, _ = B.check(run, path)
            self.assertEqual(diffs, [])                      # excluded, and never read
            fp = B.fingerprint(run, skip_content={"big.bin"})
            self.assertIsNone(fp["products"]["big.bin"]["sha256"])
            self.assertEqual(fp["products"]["big.bin"]["bytes"], 4096)
            (run / "big.bin").write_bytes(b"y" * 8192)      # size still compared
            self.assertEqual([x["what"] for x in B.check(run, path)[0]], ["size"])
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_a_rendering_is_checked_for_presence_and_not_for_bytes(self):
        """A report is derived from the data, and its bytes move for reasons that are not the
        numbers - an embedded path, a timestamp, a table reporting the size of an object the
        baseline has already measured as unstable. Comparing them reported the same instability
        twice, the second time as if it were news."""
        d = Path(tempfile.mkdtemp())
        try:
            for sub, mb in (("a", "13.0"), ("b", "13.4")):
                (d / sub).mkdir()
                (d / sub / "report.md").write_text(
                    f"generated 2026-09-06T15:12:08Z\n\n| objects/*.h5ad | 1 | {mb} MB |\n")
                (d / sub / "fig.pdf").write_bytes(b"%PDF" + sub.encode() * 40)
                (d / sub / "r.json").write_text('{"score": 0.5}')
            fa, fb = B.fingerprint(d / "a"), B.fingerprint(d / "b")
            self.assertEqual(B.compare(fa, fb), [])
            self.assertEqual(fa["covers"], ["r.json"])
            self.assertEqual(fa["presence_only"], ["fig.pdf", "report.md"])
            # what it must still catch
            (d / "b" / "r.json").write_text('{"score": 0.9}')
            self.assertEqual([x["what"] for x in B.compare(B.fingerprint(d / "b"), fa)], ["score"])
            (d / "b" / "fig.pdf").unlink()
            self.assertIn("fig.pdf", [x["product"] for x in B.compare(B.fingerprint(d / "b"), fa)])
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_provenance_is_still_redacted_from_a_text_artefact_that_is_compared(self):
        """A config the run wrote is data, not a rendering, so it keeps a content hash - and the
        timestamp inside it still must not count."""
        d = Path(tempfile.mkdtemp())
        try:
            for sub, when in (("a", "2026-09-06T15:12:08Z"), ("b", "2026-09-06T19:44:01Z")):
                (d / sub).mkdir()
                (d / sub / "settings.yml").write_text(f"written: {when}\nseed: 0\n")
            self.assertEqual(B.compare(B.fingerprint(d / "a"), B.fingerprint(d / "b")), [])
            (d / "b" / "settings.yml").write_text("written: 2026-09-06T19:44:01Z\nseed: 1\n")
            self.assertEqual([x["what"] for x in B.compare(B.fingerprint(d / "b"),
                                                           B.fingerprint(d / "a"))], ["content"])
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_a_moving_field_is_excluded_and_named(self):
        # The counter lives OUTSIDE run_a, which the tier wipes before each execution, so the two
        # runs genuinely disagree.
        body = ("import json, pathlib, sys\n"
                "seen = pathlib.Path(MARK)\n"
                "n = len(list(seen.glob('seen.*')))\n"
                "(seen / ('seen.%d' % n)).write_text('')\n"
                "json.dump({'stable': 2.0, 'moves': float(n)}, open(pathlib.Path(sys.argv[1])/'out.json', 'w'))\n")
        body = body.replace("MARK", repr(str(self.fx)))
        tier, fp = self._record(body)
        self.assertTrue(tier["ok"], tier["evidence"])
        self.assertIn("out.json::moves", fp["not_execution_stable"])
        self.assertIn("stable", fp["products"]["out.json"]["numbers"])
        self.assertEqual(fp["measured_over"], 2)
        self.assertTrue(any("NOT execution-stable" in e for e in tier["evidence"]))

    def test_the_check_immediately_after_recording_is_clean(self):
        """The round trip the cluster caught: recording excluded three kinds of field and the
        very next check failed on all three, because exclusion deleted them and a deleted
        reference key reads as a NEW field."""
        from sch.dev import ladder as L
        body = ("import json, pathlib, sys\n"
                "seen = pathlib.Path(MARK)\n"
                "n = len(list(seen.glob('seen.*')))\n"
                "(seen / ('seen.%d' % n)).write_text('')\n"
                "out = pathlib.Path(sys.argv[1])\n"
                "json.dump({'stable': 2.0, 'moves': float(n)}, open(out/'out.json', 'w'))\n"
                "(out/'blob.bin').write_bytes(bytes([n]))\n"
                "open(out/'t.csv','w').write('a,b\\n1,%d\\n' % n)\n")
        body = body.replace("MARK", repr(str(self.fx)))
        tier, fp = self._record(body)
        self.assertTrue(tier["ok"], tier["evidence"])
        for expect in ("out.json::moves", "blob.bin::content", "t.csv::b.sum"):
            self.assertIn(expect, fp["not_execution_stable"])
        # now CHECK, on a third execution, and only the stable fields must be compared
        doc = P.load(self.d)
        doc["fixture"] = {"command": ["python3", "-c", body, "{out}"], "products": ["out.json"]}
        res = []
        L._fixture_tier(doc, "widget", "alpha", "a", self.fx, res, "fixture_a")
        L.t6_baseline(doc, self.fx, res, "alpha", record=False, point_name="widget")
        self.assertTrue(res[-1]["ok"], res[-1]["evidence"])

    def test_content_that_embeds_its_own_output_path_is_not_stable(self):
        """The second execution writes elsewhere, so a value that is really the destination
        cannot be mistaken for a value the tool computed."""
        body = ("import json, pathlib, sys\n"
                "out = pathlib.Path(sys.argv[1])\n"
                "json.dump({'where': str(out), 'n': 3.0}, open(out/'out.json', 'w'))\n")
        from sch.dev import ladder as L
        doc = P.load(self.d)
        doc["fixture"] = {"command": ["python3", "-c", body, "{out}"], "products": ["out.json"]}
        res = []
        L._fixture_tier(doc, "widget", "alpha", "a", self.fx, res, "fixture_a")
        L.t6_baseline(doc, self.fx, res, "alpha", record=True, point_name="widget")
        fp = json.loads((self.d / "tests" / "baselines" / "alpha.baseline.json").read_text())
        self.assertEqual(fp["not_execution_stable"], [])   # a string path is not a number leaf
        self.assertIn("n", fp["products"]["out.json"]["numbers"])

    def test_it_refuses_to_record_when_the_second_run_fails(self):
        from sch.dev import ladder as L
        body = ("import json, pathlib, sys\n"
                "seen = pathlib.Path(MARK)\n"
                "n = len(list(seen.glob('seen.*')))\n"
                "(seen / ('seen.%d' % n)).write_text('')\n"
                "sys.exit(1) if n else json.dump({'k': 1}, open(pathlib.Path(sys.argv[1])/'out.json', 'w'))\n")
        body = body.replace("MARK", repr(str(self.fx)))
        doc = P.load(self.d)
        doc["fixture"] = {"command": ["python3", "-c", body, "{out}"], "products": ["out.json"]}
        res = []
        L._fixture_tier(doc, "widget", "alpha", "a", self.fx, res, "fixture_a")
        self.assertTrue(res[0]["ok"], res[0]["evidence"])
        L.t6_baseline(doc, self.fx, res, "alpha", record=True, point_name="widget")
        self.assertFalse(res[-1]["ok"])
        self.assertTrue(any("one run" in e for e in res[-1]["evidence"]))
        self.assertFalse((self.d / "tests" / "baselines" / "alpha.baseline.json").exists())


class HarnessDeclaresItsOwnPoints(unittest.TestCase):
    def test_the_harness_devpoints_is_valid(self):
        doc = P.load(ROOT)
        self.assertEqual(doc["tool"], "sch")
        self.assertIn("plugin", doc["points"])


if __name__ == "__main__":
    unittest.main()


class TheStarterDeclarationIsUsable(unittest.TestCase):
    """`sch dev map` without a declaration tells you to run `sch dev map --init`. That flag did
    not exist - the error named a command the tool did not have, which is the same defect this
    suite exists to find, one level up. And the first starter it wrote did not parse."""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_the_starter_loads_and_maps(self):
        from sch.dev import points as PP
        PP.init(self.d, tool="demo")
        doc = PP.load(self.d)
        self.assertEqual(doc["tool"], "demo")
        self.assertTrue(doc["points"])
        for pt in doc["points"].values():
            for field in ("what", "lives", "proves", "cannot_prove"):
                self.assertTrue(pt.get(field), f"the starter omits {field}")

    def test_it_does_not_overwrite_without_force(self):
        from sch.dev import points as PP
        PP.init(self.d, tool="demo")
        (self.d / "DEVPOINTS.yaml").write_text("tool: mine\ndevpoints: 1\n")
        with self.assertRaises(PP.DevpointsError):
            PP.init(self.d, tool="demo")
        self.assertIn("mine", (self.d / "DEVPOINTS.yaml").read_text())

    def test_the_error_without_a_declaration_names_a_command_that_exists(self):
        from sch.cli import build_parser
        from sch.dev import points as PP
        with self.assertRaises(PP.DevpointsError) as e:
            PP.load(self.d)
        msg = str(e.exception)
        named = re.findall(r"`sch ([^`]+)`", msg)
        self.assertTrue(named, "the error names no command at all")
        for cmd in named:
            build_parser().parse_args(shlex.split(cmd))       # raises SystemExit if it does not exist


class TheFixtureIsNotRebuiltWhenItIsAlreadyThere(unittest.TestCase):
    """Exists-and-matches, the same rule the environment installer applies.

    The cohort is a pure function of (seed, cells, genes, splice, crossed) - that is what
    "deterministic: same seed, same bytes" means - so writing it again produces the files that
    are already on disk. A memory measurement needs two sizes WITH splice layers, and that was
    rebuilt on every submission of a job whose expensive part it is not.

    `--force` rebuilds, because the escape hatch has to exist and has to be asked for.
    """

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.d, True)
        try:
            import anndata  # noqa: F401
        except ImportError:
            self.skipTest("the fixture needs anndata")

    def test_a_second_write_is_reused_and_says_so(self):
        first = F.write(self.d, shape="a", n_cells=200, n_genes=60)
        self.assertFalse(first.get("reused"))
        again = F.write(self.d, shape="a", n_cells=200, n_genes=60)
        self.assertTrue(again.get("reused"))
        self.assertEqual(first["digest"], again["digest"])

    def test_force_rebuilds(self):
        F.write(self.d, shape="a", n_cells=200, n_genes=60)
        self.assertFalse(F.write(self.d, shape="a", n_cells=200, n_genes=60,
                                 force=True).get("reused"))

    def test_a_different_argument_is_a_different_cohort_and_is_not_reused(self):
        F.write(self.d, shape="a", n_cells=200, n_genes=60)
        for kw in ({"n_cells": 300}, {"n_genes": 80}, {"seed": 7},
                   {"splice": True}, {"crossed": True}):
            got = F.write(self.d, shape="a", **{"n_cells": 200, "n_genes": 60, **kw})
            self.assertFalse(got.get("reused"), f"{kw} was served a cohort built without it")

    def test_splice_is_on_the_record_or_the_check_cannot_see_it(self):
        """THE ONE THAT WOULD HAVE BITTEN. Without `splice` recorded, a run asking for the layers
        matches a record written without them and is handed an object missing the only thing it
        needs - and velocity's whole input is those two layers."""
        plain = F.write(self.d, shape="a", n_cells=200, n_genes=60)
        self.assertIn("splice", plain)
        self.assertFalse(plain["splice"])
        spliced = F.write(self.d, shape="a", n_cells=200, n_genes=60, splice=True)
        self.assertFalse(spliced.get("reused"))
        import anndata as ad
        self.assertIn("spliced", ad.read_h5ad(spliced["observations"]).layers)

    def test_both_shapes_carry_a_log_normalised_layer(self):
        """The first plugin the host ever ran on this fixture was skipped before it ran: it
        requires `lognorm` and the object had counts alone. Both shapes carry the layer under
        the name the host's resolver looks for first, and the record says so."""
        import json
        import anndata as ad
        for shape in ("a", "b"):
            F.write(self.d, shape=shape, n_cells=200, n_genes=60)
            rec = json.loads((self.d / f"FIXTURE_{shape}.json").read_text())
            self.assertIn("lognorm", rec.get("layers", []), rec.get("layers"))
            A = ad.read_h5ad(rec["observations"])
            self.assertIn("lognorm", A.layers)
            self.assertTrue(float(A.layers["lognorm"].max()) > 0)

    def test_a_record_that_outlived_its_files_is_not_a_match(self):
        rec = F.write(self.d, shape="a", n_cells=200, n_genes=60)
        Path(rec["observations"]).unlink()
        self.assertFalse(F.write(self.d, shape="a", n_cells=200,
                                 n_genes=60).get("reused"))

    def test_both_shapes_skip_without_building_the_core(self):
        F.write_both(self.d, n_cells=200, n_genes=60)
        again = F.write_both(self.d, n_cells=200, n_genes=60)
        self.assertTrue(all(r.get("reused") for r in again))
        self.assertEqual(len({r["digest"] for r in again}), 1,
                         "the two shapes stopped sharing a digest")


class TheReuseDecisionItselfNeedsNoCohort(unittest.TestCase):
    """`matching` reads a record and two paths, so it is testable where anndata is not installed.

    WORTH SEPARATING. The class above skips on this workstation, which means the reuse rule -
    the part that decides whether hours of work happen - would have shipped exercised only on
    the cluster. The decision is pure: a JSON record, the arguments, and whether the files it
    names are still there.
    """

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.d, True)
        self.h5 = self.d / "fixture_a.h5ad"
        self.csv = self.d / "design_a.csv"
        self.h5.write_bytes(b"not really an h5ad")
        self.csv.write_text("a,b\n")

    def _record(self, **over):
        rec = {"shape": "a", "seed": 20260906, "cells": 2000, "genes": 520,
               "splice": False, "crossed": False,
               "observations": str(self.h5), "design": str(self.csv), "digest": "x"}
        rec.update(over)
        (self.d / "FIXTURE_a.json").write_text(json.dumps(rec))
        return rec

    def _match(self, **over):
        args = {"seed": 20260906, "n_cells": 2000, "n_genes": 520,
                "splice": False, "crossed": False}
        args.update(over)
        return F.matching(self.d, "a", **args)

    def test_the_same_arguments_match(self):
        self._record()
        self.assertIsNotNone(self._match())

    def test_every_argument_is_part_of_the_key(self):
        self._record()
        for kw in ({"seed": 1}, {"n_cells": 1}, {"n_genes": 1},
                   {"splice": True}, {"crossed": True}):
            self.assertIsNone(self._match(**kw), f"{kw} was treated as the same cohort")

    def test_an_old_record_with_no_splice_key_does_not_match_a_plain_request(self):
        """A RECORD WRITTEN BEFORE THE KEY EXISTED must not be reused, in either direction. It
        says nothing about its layers, so believing it says `no layers` hands a plugin whose
        entire input is those layers an object without them."""
        rec = self._record()
        del rec["splice"]
        (self.d / "FIXTURE_a.json").write_text(json.dumps(rec))
        self.assertIsNone(self._match())
        self.assertIsNone(self._match(splice=True))

    def test_a_record_naming_files_that_are_gone_is_not_a_match(self):
        self._record()
        self.h5.unlink()
        self.assertIsNone(self._match())
        self.h5.write_bytes(b"back")
        self.csv.unlink()
        self.assertIsNone(self._match())

    def test_unreadable_or_absent_records_are_not_matches_and_do_not_raise(self):
        self.assertIsNone(self._match())
        (self.d / "FIXTURE_a.json").write_text("{not json")
        self.assertIsNone(self._match())
