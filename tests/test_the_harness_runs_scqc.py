"""The harness runs its first tool: `qc@scqc` through the real `sch` CLI (harness W010, GAP-001).

Until this wave the kernel could run no tool of the family: it had no adapter, and a cohort's
stages ran as hand-written job scripts. The adapter calls scQC's REAL command line - here a
stand-in that honours the same flags and writes the same layout, as scQC's own suite stands in for
its R detector - and adopts scQC's own STATUS.json and seal as the stage's record. Its removal is
the harness's: one whole mask per criterion over the observations, so it unmounts.

Every assertion reads the world - the argv the tool received, the masks on disk, the view's digest
- never the kernel's report of itself.
"""
import csv
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from helpers import FIXTURES, HAVE_H5PY, PROTO_HEAD, library_cohort, write_plugin
from sch.cli import main
from sch.kernel import Stack

FAKE = FIXTURES / "fake_scqc.py"
CRITERIA = ["fail_not_cellbender_cell", "fail_umi_floor", "fail_gene_floor", "fail_mito_ceiling",
            "fail_doublet", "fail_mito_nf"]


def cli(*argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(list(argv))
    return rc, buf.getvalue()


@unittest.skipUnless(HAVE_H5PY, "h5py is not available in this interpreter")
class TheHarnessRunsScqc(unittest.TestCase):
    LIBRARIES, DROPLETS = 4, 120

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sch-scqc-"))
        self.sheet, self.registry, self.design = library_cohort(
            self.tmp, libraries=self.LIBRARIES, droplets=self.DROPLETS)
        self.stack = self.tmp / "stack"
        self.calls = self.tmp / "scqc_calls.jsonl"
        self._env = {k: os.environ.get(k) for k in ("FAKE_SCQC_LOG", "FAKE_SCQC_MODE",
                                                    "FAKE_SCQC_STATE_VERSION")}
        os.environ["FAKE_SCQC_LOG"] = str(self.calls)
        os.environ.pop("FAKE_SCQC_MODE", None)
        os.environ.pop("FAKE_SCQC_STATE_VERSION", None)

    def tearDown(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ----------------------------------------------------------------------- helpers
    def init(self, *context):
        rc, out = cli("init", str(self.stack), "--profile", "single-cell/1.0",
                      "--observations", str(self.sheet), "--parts", "ambient_h5",
                      "--key", "sample=sample", "--design", str(self.design), *context)
        self.assertEqual(rc, 0, out)

    def mount(self, *extra):
        rc, out = cli("--json", "mount", "--stack", str(self.stack), "qc@scqc",
                      "--param", f"scqc={FAKE}", "--param", f"registry={self.registry}",
                      "--param", "executor=local", "--param", "allow_local=true",
                      "--param", "dbr=0.06", "--param", "seed=0", *extra)
        return rc, json.loads(out)

    def view(self):
        rc, out = cli("--json", "materialise", "--stack", str(self.stack))
        self.assertEqual(rc, 0, out)
        return json.loads(out)

    def scqc_runs(self) -> list:
        if not self.calls.exists():
            return []
        calls = [json.loads(x) for x in self.calls.read_text().splitlines()]
        return [c["argv"] for c in calls if c["argv"][:1] == ["run"]]

    # ----------------------------------------------------------------------- the stage
    def test_it_mounts_through_the_real_cli_and_unmount_restores_every_observation(self):
        self.init("--context", "assay=snrna")
        before = self.view()
        total = self.LIBRARIES * self.DROPLETS
        self.assertEqual((before["kept"], before["total"]), (total, total))

        rc, r = self.mount()
        self.assertEqual(rc, 0, r)
        self.assertEqual(r["status"], "mounted", r)

        # scQC received exactly the declared call: its own flags, in its parser's order, the
        # samplesheet the stack declared as its observations, and a project inside the plugin's
        # own output - nothing defaulted on its behalf.
        runs = self.scqc_runs()
        self.assertEqual(len(runs), 1, runs)
        out_dir = self.stack.resolve() / "plugins" / "qc_scqc" / "out"
        self.assertEqual(runs[0], ["run", "--project", str(out_dir / "scqc"),
                                   "--samplesheet", str(self.sheet.resolve()),
                                   "--registry", str(self.registry),
                                   "--executor", "local", "--allow-local",
                                   "--dbr", "0.06", "--seed", "0"])

        # one WHOLE mask per criterion, each over every observation, merged by identity
        res = next(p for p in (out_dir / "scqc" / "results").iterdir() if p.name != "latest"
                   and p.is_dir())
        removed = set()
        for s in [f"L{i + 1}" for i in range(self.LIBRARIES)]:
            with open(res / "tables" / f"{s}.percell.csv", newline="") as fh:
                removed |= {f"{s}|{r['barcode']}" for r in csv.DictReader(fh) if r["keep"] == "False"}
        for c in CRITERIA:
            with open(out_dir / "masks" / f"{c}.csv", newline="") as fh:
                rows = list(csv.DictReader(fh))
            self.assertEqual(len(rows), total, c)
        mounted = self.view()
        self.assertEqual(mounted["kept"], total - len(removed))
        self.assertLess(mounted["kept"], total)

        # the stage record is scQC's own, adopted rather than rewritten
        out = json.loads((out_dir / "out.json").read_text())
        self.assertEqual(out["answer"]["stage_record"]["status"], "ok")
        self.assertEqual(out["answer"]["stage_record"]["seal"], "SEALED.txt")
        self.assertIn("scQC", out["wrapped_versions"])
        self.assertTrue(any(t.endswith("removal_ledger.csv") for t in out["tables"]))

        rc, out = cli("--json", "unmount", "--stack", str(self.stack), "qc_scqc", "--dry-run")
        self.assertEqual(rc, 2, out)            # the runtime is named qc@scqc, not its directory
        rc, out = cli("--json", "unmount", "--stack", str(self.stack), "qc@scqc", "--dry-run")
        self.assertEqual(rc, 0, out)
        self.assertEqual(json.loads(out)["would_restore"], len(removed))
        rc, out = cli("--json", "unmount", "--stack", str(self.stack), "qc@scqc")
        self.assertEqual(rc, 0, out)
        after = self.view()
        self.assertEqual((after["kept"], after["total"]), (total, total))
        self.assertEqual(after["digest"], before["digest"])

    def test_the_gate_and_the_companion_held_on_the_mount(self):
        self.init("--context", "assay=snrna")
        rc, r = self.mount()
        self.assertEqual(rc, 0, r)
        gates = {g["gate"]: g for g in r["gates"]}
        self.assertEqual(gates["differential_check"]["verdict"], "PASS", gates)
        events = [json.loads(x) for x in (self.stack / "events.jsonl").read_text().splitlines()]
        held = [e for e in events if e["kind"] == "invariant/held" and e.get("owner") == "qc@scqc"]
        self.assertTrue(held, "the plugin's companion did not run")

    # ----------------------------------------------------------------------- rule 2
    def test_an_assay_the_stack_did_not_declare_is_refused_before_scqc_runs(self):
        self.init()
        rc, r = self.mount()
        self.assertEqual(rc, 2, r)
        self.assertEqual(r["status"], "refused", r)
        self.assertIn("assay", r["reason"])
        self.assertIn("--context assay=", r["fix"])
        self.assertEqual(self.scqc_runs(), [], "scQC ran without a declared assay")

    def test_a_library_whose_assay_disagrees_or_is_empty_is_refused(self):
        lines = self.sheet.read_text().splitlines()
        for why, edit in (("differs", lambda f: f.__setitem__(4, "scrna")),
                          ("is empty", lambda f: f.__setitem__(4, ""))):
            with self.subTest(why):
                fields = lines[3].split("\t")              # L2
                edit(fields)
                self.sheet.write_text("\n".join(lines[:3] + ["\t".join(fields)] + lines[4:]) + "\n")
                shutil.rmtree(self.stack, ignore_errors=True)
                self.init("--context", "assay=snrna")
                rc, r = self.mount()
                self.assertEqual(rc, 2, r)
                self.assertIn("L2", r["reason"])
                self.assertEqual(self.scqc_runs(), [])

    # ----------------------------------------------------------------------- the stage record
    def test_scqcs_refusal_is_the_mounts_refusal_with_its_fix(self):
        self.init("--context", "assay=snrna")
        os.environ["FAKE_SCQC_MODE"] = "refuse"
        rc, r = self.mount()
        self.assertEqual((rc, r["status"]), (2, "refused"), r)
        self.assertIn("no valley", r["reason"])
        self.assertIn("decisions.yml", r["fix"])

    def test_a_failed_or_unsealed_run_is_a_death_not_a_result(self):
        self.init("--context", "assay=snrna")
        for mode in ("fail", "unsealed"):
            with self.subTest(mode):
                os.environ["FAKE_SCQC_MODE"] = mode
                rc, r = self.mount()
                self.assertEqual((rc, r["status"]), (2, "died"), r)
                self.assertEqual(self.view()["kept"], self.LIBRARIES * self.DROPLETS)

    def test_the_companion_fails_a_keep_column_the_masks_do_not_fold_to(self):
        """The regression the companion exists for: scQC's `keep` and its criteria disagree, so
        the masks the harness folds would deliver a different set than scQC delivered."""
        self.init("--context", "assay=snrna")
        os.environ["FAKE_SCQC_MODE"] = "disagree"
        rc, r = self.mount()
        self.assertEqual((rc, r["status"]), (2, "refused"), r)
        self.assertIn("keep", r["reason"])

    def test_a_universe_that_is_not_the_observations_is_refused_with_both_counts(self):
        self.init("--context", "assay=snrna")
        os.environ["FAKE_SCQC_MODE"] = "short"
        rc, r = self.mount()
        self.assertEqual((rc, r["status"]), (2, "refused"), r)
        self.assertIn("covers", r["reason"])

    def test_numbers_scqc_versioned_differently_are_refused_before_any_compute(self):
        self.init("--context", "assay=snrna")
        os.environ["FAKE_SCQC_STATE_VERSION"] = "2"
        rc, r = self.mount()
        self.assertEqual((rc, r["status"]), (2, "refused"), r)
        self.assertIn("state_version", r["reason"])
        self.assertEqual(self.scqc_runs(), [])

    def test_a_parameter_scqc_does_not_take_or_the_adapter_owns_is_refused(self):
        self.init("--context", "assay=snrna")
        for bad in ("min_umi=350", f"project={self.tmp}", f"samplesheet={self.sheet}"):
            with self.subTest(bad):
                rc, r = self.mount("--param", bad)
                self.assertEqual((rc, r["status"]), (2, "refused"), r)
                self.assertIn(bad.split("=")[0], r["reason"])
        self.assertEqual(self.scqc_runs(), [])

    def test_it_refuses_a_view_something_beneath_it_already_masked(self):
        """scQC reads the delivered libraries itself; mounted above another removal it would
        derive its thresholds on observations the stack had already set aside."""
        self.init("--context", "assay=snrna")
        write_plugin(self.tmp / "plugins", "drop_one",
                     {"profile": "single-cell/1.0", "provides": ["mask/drop_one"],
                      "gates": {"differential_check": "optional"}},
                     PROTO_HEAD + """
import csv
rows = list(csv.DictReader(open(run.data)))
idc = run.inp["identity"]["column"]
# one barcode of EVERY library, so the removal is even across the design and the gate passes it
run.mask("drop_one", {r[idc]: not r[idc].endswith("|BC00000-1") for r in rows}, reason="first",
         id_field=idc)
sys.exit(run.finish(headline="masked one per library"))
""")
        st = Stack.open(self.stack)
        r = st.mount(str(self.tmp / "plugins" / "drop_one"))
        st.close()
        self.assertEqual(r.status, "mounted", r.reason)
        rc, r = self.mount()
        self.assertEqual((rc, r["status"]), (2, "refused"), r)
        self.assertIn("masked", r["reason"])
        self.assertEqual(self.scqc_runs(), [])


if __name__ == "__main__":
    unittest.main()
