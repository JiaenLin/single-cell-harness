"""The harness runs its third tool: `int@scintegrate` through the real `sch` CLI (harness W034, GAP-001).

Until this wave the kernel ran scQC and scAnno and no integration: a cohort's stage 3 ran as a
hand-written job script. The adapter calls scIntegrate's REAL command line - `describe`, `doctor`,
one `integrate` over the cohort's joint object - and adopts scIntegrate's own STATUS.json and seal
as the stage's record. Its result is the harness's kind of contribution: a LAYER of embeddings,
graphs and columns over the observations, never an edit of them, so unmounting it gives back the
view it was mounted on. A layer of embeddings alone used to leave the view's digest as it was; the
kernel now covers embeddings and graphs by their content (the last classes but one).

Most tests use a stand-in for scIntegrate's package (`fixtures/fake_scintegrate/`) that honours
the same flags and writes the same layout, as `fake_scanno.py` does for scAnno. The last class runs
the REAL scIntegrate on a synthetic object when `SCH_TEST_SCINTEGRATE` names its checkout and the
analysis stack imports.

Every assertion reads the world - the argv the tool received, the view's digest, the files on disk
- never the kernel's report of itself.
"""
import csv
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from helpers import FIXTURES, HAVE_H5PY, PROTO_HEAD, ROOT, write_plugin
from sch.cli import main
from sch.kernel import Stack

FAKE = FIXTURES / "fake_scintegrate"
PLUGIN = ROOT / "plugins" / "single-cell" / "int@scintegrate"
N = 24


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def cli(*argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(list(argv))
    return rc, buf.getvalue()


def fake():
    return _load(FAKE / "scintegrate" / "cli.py", "fake_scintegrate_cli")


def h5py_file(path):
    import h5py
    return h5py.File(path, "r")


def joint(dest: Path, n=N, parts=1, library=None):
    """A cohort's joint object - three libraries' observations already in one file - as the one part
    of a manifest, read-only as a deliverable is. obs carries the batch, two label levels, one design
    factor (`age`) and a QC count, and, with `library` (a function of the batch value), a `library`
    column; obsm a PCA and a 2-D view; obsp one graph the stand-in will rewrite, one it will write
    again identically, and one it will drop. The design names `age`, which obs carries, and `diet`,
    which it does not. Returns (manifest, design, part)."""
    import numpy as np
    f = fake()
    dest = Path(dest)
    libs = [f"L{1 + i * 3 // n}" for i in range(n)]
    index = [f"{lib}_BC{i:04d}" for i, lib in enumerate(libs)]
    rng = np.random.default_rng(0)
    rows = ["part\th5ad"]
    for k in range(parts):
        part = dest / "objects" / f"joint{k or ''}.h5ad"
        f.write_object(part, index, {
            "sample": ("cat", libs),
            "cell_type": ("cat", ["EXCLUDED" if i % 7 == 3 else ("T" if i % 2 else "B") for i in range(n)]),
            "cell_compartment": ("str", ["lymphoid"] * n),
            "age": ("cat", ["a2" if lib == "L2" else "a1" for lib in libs]),
            "n_counts": ("int", [100 + i for i in range(n)]),
            **({"library": ("cat", [library(lib) for lib in libs])} if library else {}),
        }, obsm={"X_pca": rng.normal(size=(n, 6)).astype("float32"),
                 "X_umap": rng.normal(size=(n, 2)).astype("float32")},
            obsp={"bbknn_connectivities": f.ring(n, 2, 0.5),      # what the stand-in writes: unchanged
                  "bbknn_distances": f.ring(n, 1, 9.0),           # another graph: rewritten
                  "connectivities": f.ring(n, 1, 1.0)})           # not in its object: dropped
        rows.append(f"joint{k or ''}\t{part}")
    manifest = dest / "joint.tsv"
    manifest.write_text("\n".join(rows) + "\n")
    design = dest / "design.csv"
    design.write_text("sample,age,diet\nL1,a1,d1\nL2,a2,d2\nL3,a1,d2\n")
    for p in [manifest, design] + sorted((dest / "objects").glob("*.h5ad")):
        p.chmod(0o444)
    return manifest, design, dest / "objects" / "joint.h5ad"


def block(design_file, **over):
    """integrate's flags, as a stage declares them: scIntegrate's names, `-` written `_`."""
    b = {"batch_key": "sample", "label_key": "cell_type", "l1_key": "cell_compartment",
         "colour_by": "cell_type,cell_compartment", "drop_labels": "EXCLUDED", "design": str(design_file),
         "bio_factor": ["age", "diet"], "methods": "none,harmony,bbknn", "k": 5, "n_pcs": "6",
         "seed": 0, "n_cores": 1, "scib_resolutions": 3}
    for k, v in over.items():
        if v is None:
            b.pop(k, None)
        else:
            b[k] = v
    return b


class _Base(unittest.TestCase):
    ENV = ("FAKE_SCINTEGRATE_LOG", "FAKE_SCINTEGRATE_MODE", "FAKE_SCINTEGRATE_STATE_VERSION")

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sch-scint-"))
        self.stack = self.tmp / "stack"
        self.calls = self.tmp / "scintegrate_calls.jsonl"
        self._env = {k: os.environ.get(k) for k in self.ENV}
        for k in self.ENV:
            os.environ.pop(k, None)
        os.environ["FAKE_SCINTEGRATE_LOG"] = str(self.calls)

    def tearDown(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        for p in self.tmp.rglob("*"):
            try:
                p.chmod(0o755 if p.is_dir() else 0o644)
            except OSError:
                pass
        shutil.rmtree(self.tmp, ignore_errors=True)

    def init(self, manifest, *context):
        rc, out = cli("init", str(self.stack), "--profile", "single-cell/1.0", "--observations",
                      str(manifest), "--parts", "h5ad", "--key", "sample=part", *context)
        self.assertEqual(rc, 0, out)

    def mount(self, integrate, checkout=None, **extra):
        argv = ["--json", "mount", "--stack", str(self.stack), "int@scintegrate",
                "--param", f"scintegrate={checkout or FAKE}"]
        if integrate is not None:
            argv += ["--param", f"integrate={json.dumps(integrate)}"]
        for k, v in extra.items():
            argv += ["--param", f"{k}={json.dumps(v)}"]
        rc, out = cli(*argv)
        return rc, json.loads(out)

    def view(self):
        rc, out = cli("--json", "materialise", "--stack", str(self.stack))
        self.assertEqual(rc, 0, out)
        return json.loads(out)

    def calls_of(self, cmd=None) -> list:
        if not self.calls.exists():
            return []
        calls = [json.loads(x) for x in self.calls.read_text().splitlines()]
        return [c for c in calls if cmd is None or c["argv"][:1] == [cmd]]

    @property
    def run_dir(self) -> Path:
        return self.stack.resolve() / "plugins" / "int_scintegrate" / "out"

    def out_json(self):
        return json.loads((self.run_dir / "out.json").read_text())


@unittest.skipUnless(HAVE_H5PY, "h5py is not available in this interpreter")
class TheHarnessRunsScintegrate(_Base):
    def setUp(self):
        super().setUp()
        self.manifest, self.design, self.part = joint(self.tmp)

    # ----------------------------------------------------------------------- the stage
    def test_it_mounts_through_the_real_cli_as_a_layer_and_unmount_restores_the_view(self):
        self.init(self.manifest, "--context", "assay=snrna", "--context", "species=species_x")
        before = self.view()
        self.assertEqual((before["kept"], before["total"]), (N, N))

        rc, r = self.mount(block(self.design))
        self.assertEqual((rc, r["status"]), (0, "mounted"), r)

        # scIntegrate received exactly a stage-3 job's calls: describe, doctor, one integrate over
        # the part IN PLACE, every flag the declaration's in scIntegrate's parser order, the run's
        # directory the adapter's, the axes the stack's - and it ran from the declared checkout.
        P = self.run_dir / "scintegrate"
        self.assertEqual([c["argv"][0] for c in self.calls_of()], ["describe", "doctor", "integrate"])
        self.assertEqual(self.calls_of("integrate")[0]["argv"],
                         ["integrate", "--h5ad", str(self.part), "--out", str(P),
                          "--batch-key", "sample", "--label-key", "cell_type", "--species", "species_x",
                          "--assay", "snrna", "--l1-key", "cell_compartment", "--drop-labels", "EXCLUDED",
                          "--colour-by", "cell_type,cell_compartment", "--design", str(self.design),
                          "--bio-factor", "age", "--bio-factor", "diet", "--k", "5", "--n-pcs", "6",
                          "--seed", "0", "--methods", "none,harmony,bbknn", "--n-cores", "1",
                          "--scib-resolutions", "3"])
        for c in self.calls_of():
            self.assertEqual(c["pythonpath"], str(FAKE), "PYTHONPATH is the checkout and only it")
            self.assertEqual(Path(c["argv0"]).resolve(), (FAKE / "scintegrate" / "cli.py").resolve())
            self.assertEqual(Path(c["cwd"]).resolve(), P.resolve())

        # the layer: what scIntegrate ADDED or REWROTE; what it copied is the observation's own.
        # X_pca is a rewrite since 0.6.0: the withheld cells have rows in the part's PCA, so they were
        # in its fit, and scIntegrate refits it on the retained cells, NaN on the withheld rows.
        out = self.out_json()
        layer = out["answer"]["layer"]
        self.assertEqual(layer["embeddings"]["added"],
                         ["X_harmony", "X_none", "X_umap_bbknn", "X_umap_harmony", "X_umap_none"])
        self.assertEqual(layer["embeddings"]["rewritten"], ["X_pca", "X_umap"])
        self.assertEqual(layer["embeddings"]["unchanged"], [])
        self.assertEqual(layer["graphs"]["added"], [])
        self.assertEqual(layer["graphs"]["rewritten"], ["bbknn_distances"])
        self.assertEqual(layer["graphs"]["unchanged"], ["bbknn_connectivities"])
        self.assertEqual(layer["graphs"]["dropped"], ["connectivities"])
        self.assertEqual(layer["columns"]["added"], ["diet"])
        self.assertEqual(layer["columns"]["unchanged"], ["sample", "cell_type", "cell_compartment", "age"])
        self.assertEqual(layer["columns"]["dropped"], ["n_counts"])
        self.assertEqual(sorted(out["embeddings"]), sorted(layer["embeddings"]["added"] + ["X_pca", "X_umap"]))
        self.assertEqual(sorted(out["graphs"]), ["bbknn_distances"])
        self.assertTrue(any("connectivities" in c and "n_counts" in c for c in out["caveats"]), out["caveats"])

        # each embedding is the object's own array, bound to the stack's identities by barcodes.txt
        import h5py
        import numpy as np
        ids = (self.run_dir / "embeddings" / "barcodes.txt").read_text().split()
        self.assertEqual(ids, [f"joint|{n}" for n in fake()._strings(h5py.File(self.part, "r")["obs"]["_index"][()])])
        with h5py.File(P / "objects" / "cohort_integrated.h5ad", "r") as f:
            want = f["obsm"]["X_harmony"][()]
        got = np.load(self.run_dir / "embeddings" / "X_harmony.npy")
        self.assertTrue(np.array_equal(got, want, equal_nan=True))
        withheld = [i for i in range(N) if i % 7 == 3]
        self.assertEqual(np.flatnonzero(np.isnan(got).any(axis=1)).tolist(), withheld,
                         "the withheld cells are NaN rows, not missing rows")
        pca = np.load(self.run_dir / "embeddings" / "X_pca.npy")
        self.assertEqual(np.flatnonzero(np.isnan(pca).any(axis=1)).tolist(), withheld,
                         "the refit PCA is NaN on exactly the withheld rows")
        z = np.load(self.run_dir / "graphs" / "bbknn_distances.npz")
        self.assertEqual((str(z["format"]), tuple(z["shape"])), ("csr", (N, N)))

        # the view: every observation kept, the layer visible in its digest, the column in it
        mounted = self.view()
        self.assertEqual((mounted["kept"], mounted["total"]), (N, N))
        self.assertNotEqual(mounted["digest"], before["digest"])
        with open(mounted["path"], newline="") as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual([c for c in rows[0] if c.startswith("column__")], ["column__diet"])
        self.assertEqual(rows[0]["column__diet"], "d1")
        by_id = {x["barcode"]: x for x in rows}
        self.assertEqual(by_id["joint|L1_BC0003"]["column__diet"], "withheld_from_integration",
                         "a design column the part lacks reads so on the cells scIntegrate withheld")

        # the stage record is scIntegrate's own, adopted, at the numbers this adapter means
        rec = out["answer"]["stage_record"]
        self.assertEqual(sorted(rec), ["describe", "doctor", "integrate"])
        self.assertEqual((rec["integrate"]["status"], rec["integrate"]["seal"], rec["integrate"]["exit"]),
                         ("ok", "SEALED.txt", 0))
        self.assertEqual((rec["describe"]["state_version"], rec["integrate"]["state_version"]), (2, 2))
        # the design is keyed on the batch key itself: its key column is the batch column, nothing added
        report = json.loads((P / "report.json").read_text())
        self.assertEqual(report["design_key"], {"column": "sample", "how": "the batch column itself",
                                                "added": False})
        self.assertEqual((report["pca"]["source"], report["pca"]["n_withheld_not_fitted"]), ("refit", 3))
        self.assertEqual(out["answer"]["chosen"], "harmony")
        self.assertEqual((out["answer"]["assay"], out["answer"]["species"]), ("snrna", "species_x"))
        self.assertIn("scIntegrate", out["wrapped_versions"])
        self.assertEqual(out["objects"], {"cohort_integrated": "scintegrate/objects/cohort_integrated.h5ad"})
        self.assertIn("scintegrate/tables/scib_aggregate.csv", out["tables"])
        st = json.loads((P / "STATUS.json").read_text())
        self.assertFalse([x for x in st["products"] if x["path"].startswith("logs/")],
                         "the adapter's logs are not among scIntegrate's products")

        # taken back: nothing to restore, nothing above it, the view exactly as it was
        rc, dry = cli("--json", "unmount", "--stack", str(self.stack), "int@scintegrate", "--dry-run")
        self.assertEqual(rc, 0, dry)
        self.assertEqual((json.loads(dry)["would_restore"], json.loads(dry)["would_invalidate"]), (0, []))
        rc, done = cli("--json", "unmount", "--stack", str(self.stack), "int@scintegrate")
        self.assertEqual(rc, 0, done)
        after = self.view()
        self.assertEqual((after["kept"], after["total"], after["digest"]), (N, N, before["digest"]))

    def test_the_companion_held_and_no_gate_is_asked_of_a_layer_that_removes_nothing(self):
        self.init(self.manifest, "--context", "assay=scrna", "--context", "species=species_x")
        rc, r = self.mount(block(self.design))
        self.assertEqual((rc, r["status"]), (0, "mounted"), r)
        self.assertEqual(r["gates"], [])
        events = [json.loads(x) for x in (self.stack / "events.jsonl").read_text().splitlines()]
        held = [e for e in events if e["kind"] == "invariant/held" and e.get("owner") == "int@scintegrate"]
        self.assertEqual(len(held), 2, events[-5:])

    # ----------------------------------------------------------------------- rule 2, and the species
    def test_an_assay_or_a_species_the_stack_did_not_declare_is_refused_before_scintegrate_runs(self):
        for context, axis in (([], "assay"), (["--context", "species=species_x"], "assay"),
                              (["--context", "assay=snrna"], "species")):
            with self.subTest(context=context):
                shutil.rmtree(self.stack, ignore_errors=True)
                self.init(self.manifest, *context)
                rc, r = self.mount(block(self.design))
                self.assertEqual((rc, r["status"]), (2, "refused"), r)
                self.assertIn(axis, r["reason"])
                self.assertIn(f"--context {axis}=", r["fix"])
                self.assertEqual(self.calls_of(), [], "a scIntegrate process ran with an undeclared axis")
                self.assertFalse((self.run_dir / "scintegrate").exists())

    def test_the_declared_axes_reach_integrate_verbatim_and_no_parameter_sets_them(self):
        self.init(self.manifest, "--context", "assay=scrna", "--context", "species=species_y")
        for axis in ("assay", "species"):
            with self.subTest(axis):
                rc, r = self.mount(block(self.design, **{axis: "snrna"}))
                self.assertEqual((rc, r["status"]), (2, "refused"), r)
                self.assertIn(axis, r["reason"])
        self.assertEqual(self.calls_of(), [])
        rc, r = self.mount(block(self.design))
        self.assertEqual((rc, r["status"]), (0, "mounted"), r)
        call = self.calls_of("integrate")[0]["argv"]
        self.assertEqual((call[call.index("--assay") + 1], call[call.index("--species") + 1]),
                         ("scrna", "species_y"))

    def test_an_assay_scintegrate_does_not_accept_is_refused_after_describe_and_before_integrate(self):
        """scIntegrate's parser would stop at `--assay sn` with exit 2 and no STATUS.json - a death
        that names nothing. Its own declaration says what it accepts, so the adapter asks it."""
        self.init(self.manifest, "--context", "assay=sn", "--context", "species=species_x")
        rc, r = self.mount(block(self.design))
        self.assertEqual((rc, r["status"]), (2, "refused"), r)
        self.assertIn("'sn'", r["reason"])
        self.assertIn("scrna|snrna", r["fix"])
        self.assertEqual([c["argv"][0] for c in self.calls_of()], ["describe"])

    # ----------------------------------------------------------------------- what was declared
    def test_a_flag_integrate_does_not_take_or_the_adapter_owns_is_refused_before_scintegrate_runs(self):
        self.init(self.manifest, "--context", "assay=snrna", "--context", "species=species_x")
        b = block(self.design)
        bad = {
            "a flag integrate does not have": (block(self.design, min_cells=3), "min_cells"),
            "the flag 0.5.0 removed": (block(self.design, lisi_subsample=50), "lisi_subsample"),
            "the object's input": (block(self.design, h5ad=str(self.tmp / "x.h5ad")), "h5ad"),
            "the run's directory": (block(self.design, out=str(self.tmp)), "out"),
            "a block that is not an object": ("none,harmony", "integrate"),
            "no integrate": (None, "integrate"),
        }
        for why, (params, word) in bad.items():
            with self.subTest(why):
                rc, r = self.mount(params)
                self.assertEqual((rc, r["status"]), (2, "refused"), r)
                self.assertIn(word, r["reason"])
        rc, r = self.mount(b, assess={"k": 3})
        self.assertEqual((rc, r["status"], "assess" in r["reason"]), (2, "refused", True), r)
        rc, r = self.mount(b, checkout=str(self.tmp / "no_such_checkout"))
        self.assertEqual((rc, r["status"]), (2, "refused"), r)
        self.assertIn("scintegrate/cli.py", r["reason"])
        self.assertEqual(self.calls_of(), [])

    def test_a_value_scintegrate_would_read_as_an_option_is_refused_before_any_call(self):
        """What a parameter cannot set by its own name it cannot set through another's (verifier
        W026 D1, through scAnno): a bare flag given a word, a value flag written bare, any value
        beginning with '-', and an object name that is a path. Each is refused by name before any
        scIntegrate process, and nothing is written beside the observations."""
        self.init(self.manifest, "--context", "assay=snrna", "--context", "species=species_x")
        delivered = sorted(p.name for p in (self.tmp / "objects").iterdir())
        cases = {
            "a bare flag given a value": ("no_fast_leiden", block(self.design, no_fast_leiden="--assay=scrna")),
            "a bare flag given a word": ("coarse_from_path", block(self.design, coarse_from_path="yes")),
            "0.7.0's bare flag given a word": ("keep_input_pca", block(self.design, keep_input_pca="yes")),
            "a value flag written bare": ("design", block(self.design, design=True)),
            "a value that is an option": ("label_key", block(self.design, label_key="--out=elsewhere")),
            "one of a repeated flag's values": ("bio_factor", block(self.design, bio_factor=["age", "--species=x"])),
            "a negative number": ("min_dist", block(self.design, min_dist=-1.0)),
            "a nested value": ("methods", block(self.design, methods={"none": True})),
            "an object name that is a path": ("object_name", block(self.design, object_name="../x.h5ad")),
            "an object name that is not an h5ad": ("object_name", block(self.design, object_name="x.zarr")),
        }
        for why, (flag, params) in cases.items():
            with self.subTest(why):
                rc, r = self.mount(params)
                self.assertEqual((rc, r["status"]), (2, "refused"), r)
                self.assertIn(flag, r["reason"])
        rc, r = self.mount(block(self.design), checkout=f"--{self.tmp}")
        self.assertEqual((rc, r["status"]), (2, "refused"), r)
        shutil.rmtree(self.stack)
        self.init(self.manifest, "--context", "assay=snrna", "--context", "species=--out=x")
        rc, r = self.mount(block(self.design))
        self.assertEqual((rc, r["status"]), (2, "refused"), r)
        self.assertIn("species", r["reason"])
        self.assertEqual(self.calls_of(), [], "a scIntegrate process was started")
        self.assertEqual(sorted(p.name for p in (self.tmp / "objects").iterdir()), delivered,
                         "something was written beside the observations")

    def test_a_view_something_beneath_it_masked_is_refused(self):
        self.init(self.manifest, "--context", "assay=snrna", "--context", "species=species_x")
        write_plugin(self.tmp / "plugins", "drop_one",
                     {"profile": "single-cell/1.0", "provides": ["mask/drop_one"],
                      "gates": {"differential_check": "optional"}},
                     PROTO_HEAD + """
import csv
rows = list(csv.DictReader(open(run.data)))
idc = run.inp["identity"]["column"]
run.mask("drop_one", {r[idc]: not r[idc].endswith("BC0000") for r in rows}, reason="first", id_field=idc)
sys.exit(run.finish(headline="masked one"))
""")
        st = Stack.open(self.stack)
        r = st.mount(str(self.tmp / "plugins" / "drop_one"))
        st.close()
        self.assertEqual(r.status, "mounted", r.reason)
        rc, r = self.mount(block(self.design))
        self.assertEqual((rc, r["status"]), (2, "refused"), r)
        self.assertIn("masked", r["reason"])
        self.assertEqual(self.calls_of(), [])

    def test_a_stack_of_two_parts_is_refused_because_scintegrate_integrates_one_object(self):
        manifest, design, _part = joint(self.tmp / "two", parts=2)
        self.init(manifest, "--context", "assay=snrna", "--context", "species=species_x")
        rc, r = self.mount(block(design))
        self.assertEqual((rc, r["status"]), (2, "refused"), r)
        self.assertIn("2 parts", r["reason"])
        self.assertEqual(self.calls_of(), [])

    def test_numbers_scintegrate_versioned_differently_are_refused_before_any_compute(self):
        """The adapter means state version 2 (scIntegrate 0.7.0). An older scIntegrate (1: 0.5.0, whose
        PCA kept the withheld cells in its fit) and a newer one are each refused after `describe`."""
        for version in ("1", "3"):
            with self.subTest(version=version):
                shutil.rmtree(self.stack, ignore_errors=True)
                self.init(self.manifest, "--context", "assay=snrna", "--context", "species=species_x")
                self.calls.unlink(missing_ok=True)
                os.environ["FAKE_SCINTEGRATE_STATE_VERSION"] = version
                rc, r = self.mount(block(self.design))
                self.assertEqual((rc, r["status"]), (2, "refused"), r)
                self.assertIn(f"scIntegrate declares state_version {version}; this adapter's layer means "
                              f"state_version 2", r["reason"])
                self.assertEqual([c["argv"][0] for c in self.calls_of()], ["describe"])

    # ----------------------------------------------------------------------- the stage record
    def test_scintegrates_refusal_is_the_mounts_refusal_with_its_fix(self):
        self.init(self.manifest, "--context", "assay=snrna", "--context", "species=species_x")
        os.environ["FAKE_SCINTEGRATE_MODE"] = "refuse"
        rc, r = self.mount(block(self.design))
        self.assertEqual((rc, r["status"]), (2, "refused"), r)
        self.assertIn("scIntegrate integrate refused", r["reason"])
        self.assertIn("contradicted", r["reason"])
        self.assertEqual(r["fix"], "declare the species the cells came from")

    def test_a_failed_unsealed_short_or_foreign_run_is_a_death_and_the_view_is_unchanged(self):
        self.init(self.manifest, "--context", "assay=snrna", "--context", "species=species_x")
        before = self.view()
        for mode, words in (("fail", "did not finish ok"), ("unsealed", "seal none"),
                            ("other_argv", "no STATUS.json of its own"),
                            ("short", "only in the part")):
            with self.subTest(mode):
                os.environ["FAKE_SCINTEGRATE_MODE"] = mode
                rc, r = self.mount(block(self.design))
                self.assertEqual((rc, r["status"]), (2, "died"), r)
                self.assertIn(words, (self.stack / "plugins" / "int_scintegrate" / "stderr.log").read_text())
                self.assertEqual(self.view()["digest"], before["digest"])
                st = Stack.open(self.stack)
                self.assertEqual(st.registry.runtimes, [])
                st.close()

    def test_an_object_in_another_order_is_compared_by_identity_never_by_position(self):
        """A copied entry is the observation's own in whatever order scIntegrate writes its rows:
        reversed, the PCA, the kept columns and the graph it writes again identically are still
        unchanged, and every file of the layer names its rows by identity. (`keep_input_pca`: the part's
        PCA is kept as delivered, so it is a copied entry to compare.)"""
        self.init(self.manifest, "--context", "assay=snrna", "--context", "species=species_x")
        os.environ["FAKE_SCINTEGRATE_MODE"] = "reversed"
        rc, r = self.mount(block(self.design, keep_input_pca=True))
        self.assertEqual((rc, r["status"]), (0, "mounted"), r)
        layer = self.out_json()["answer"]["layer"]
        self.assertEqual(layer["embeddings"]["unchanged"], ["X_pca"])
        self.assertEqual(layer["graphs"]["unchanged"], ["bbknn_connectivities"])
        self.assertEqual(layer["columns"]["unchanged"], ["sample", "cell_type", "cell_compartment", "age"])
        ids = (self.run_dir / "embeddings" / "barcodes.txt").read_text().split()
        self.assertEqual(ids[0], f"joint|L3_BC{N - 1:04d}")
        with open(self.view()["path"], newline="") as fh:
            rows = {x["barcode"]: x for x in csv.DictReader(fh)}
        self.assertEqual(rows[f"joint|L1_BC0000"]["column__diet"], "d1")
        self.assertEqual(rows[f"joint|L3_BC{N - 1:04d}"]["column__diet"], "d2")

    def test_a_column_scintegrate_rewrote_is_in_the_layer(self):
        self.init(self.manifest, "--context", "assay=snrna", "--context", "species=species_x")
        os.environ["FAKE_SCINTEGRATE_MODE"] = "relabel"
        rc, r = self.mount(block(self.design))
        self.assertEqual((rc, r["status"]), (0, "mounted"), r)
        layer = self.out_json()["answer"]["layer"]
        self.assertEqual(layer["columns"]["rewritten"], ["cell_compartment"])
        self.assertIn("cell_compartment", self.out_json()["columns"])

    # ----------------------------------------------------------------------- 0.7.0: the design's key, names
    def _fresh(self, library=None):
        """A new stack over a new joint object (its read-only files removed first)."""
        shutil.rmtree(self.stack, ignore_errors=True)
        shutil.rmtree(self.tmp / "objects", ignore_errors=True)
        for p in (self.tmp / "joint.tsv", self.tmp / "design.csv"):
            p.unlink(missing_ok=True)
        self.manifest, self.design, self.part = joint(self.tmp, library=library)
        self.init(self.manifest, "--context", "assay=snrna", "--context", "species=species_x")
        self.calls.unlink(missing_ok=True)

    def _design(self, name, text):
        p = self.tmp / name
        p.write_text(text)
        return p

    def test_the_designs_key_column_travels_under_the_designs_own_name(self):
        """scIntegrate 0.7.0 carries the design's key column under the design's name, LAST: added from
        the batch column (every cell, the withheld included) when the part lacks it, the part's own kept
        when it equals the batch column, and the run REFUSED, by name, before anything is computed,
        when the part's column of that name differs. The stand-in used to drop the key."""
        keyed = self._design("design_library.csv", "library,age,diet\nL1,a1,d1\nL2,a2,d2\nL3,a1,d2\n")
        named = self._design("design_named.csv", "age,library,diet\na1,L1,d1\na2,L2,d2\na1,L3,d2\n")
        for why, library, params, how in (
                ("absent: added", None, block(keyed),
                 "added from 'sample': each cell's sample value, the withheld cells included"),
                ("named by --design-sample-col", None,
                 block(named, design_sample_col="library", bio_factor=["diet"]),
                 "added from 'sample': each cell's sample value, the withheld cells included"),
                ("present and equal: kept", lambda lib: lib, block(keyed),
                 "the object's own column, equal to 'sample' on every cell")):
            with self.subTest(why):
                self._fresh(library)
                rc, r = self.mount(params)
                self.assertEqual((rc, r["status"]), (0, "mounted"), r)
                columns = self.out_json()["answer"]["layer"]["columns"]
                with h5py_file(self.run_dir / "scintegrate" / "objects" / "cohort_integrated.h5ad") as f:
                    order = [str(c) for c in f["obs"].attrs["column-order"]]
                self.assertEqual(order[-1], "library", "the key is the object's last column")
                report = json.loads((self.run_dir / "scintegrate" / "report.json").read_text())
                self.assertEqual(report.get("design_key"), {"column": "library", "how": how,
                                                            "added": library is None})
                if library is None:
                    self.assertEqual(columns["added"][-1], "library")
                    with open(self.view()["path"], newline="") as fh:
                        rows = list(csv.DictReader(fh))
                    self.assertEqual([x["column__library"] for x in rows],
                                     [x["barcode"].split("|")[1].split("_")[0] for x in rows],
                                     "the key column holds each cell's batch value, withheld cells included")
                else:
                    self.assertIn("library", columns["unchanged"])
                    self.assertNotIn("library", columns["added"] + columns["dropped"])
        with self.subTest("present and different: refused by name"):
            self._fresh(lambda lib: {"L1": "L2", "L2": "L1"}.get(lib, lib))
            rc, r = self.mount(block(keyed))
            self.assertEqual((rc, r["status"]), (2, "refused"), r)
            self.assertIn("scIntegrate integrate refused: the design is keyed on 'library'", r["reason"])
            self.assertIn("column differs from 'sample' on 16 of 24 cells", r["reason"])
            self.assertEqual(r["fix"], "change the input the refusal names, or the flag it asks for")
            self.assertFalse(list((self.run_dir / "scintegrate").glob("objects/*")), "nothing was written")

    def test_a_name_the_objects_writer_forbids_is_refused_before_anything_runs(self):
        """A name the object's writer refuses (a '/', `_index`, the empty name a trailing comma gives)
        is refused by scIntegrate 0.7.0 before anything is computed, naming the option that carries it;
        the stand-in used to write it, and the mount died on the layer's file name or the writer's crash."""
        for why, text, name in (
                ("a factor holding '/'", "sample,donor/x\nL1,a\nL2,b\nL3,a\n", "'donor/x', a column of --design"),
                ("a factor named _index", "sample,_index\nL1,a\nL2,b\nL3,a\n", "'_index', a column of --design"),
                ("a header ending in a comma", "sample,age,\nL1,a1,\nL2,a2,\nL3,a1,\n", "'', a column of --design"),
                ("a key holding '/'", "lib/run,age\nL1,a1\nL2,a2\nL3,a1\n", "'lib/run', the design's key")):
            with self.subTest(why):
                self._fresh()
                rc, r = self.mount(block(self._design("design_bad.csv", text), bio_factor=None))
                self.assertEqual((rc, r["status"]), (2, "refused"), r)
                self.assertIn("the object's writer refuses this name, so nothing was computed: " + name,
                              r["reason"])
                self.assertEqual([c["argv"][0] for c in self.calls_of()], ["describe", "doctor", "integrate"])
                self.assertFalse(list((self.run_dir / "scintegrate").glob("objects/*")), "nothing was written")

    def test_the_withheld_cells_pca_is_refit_unless_keep_input_pca_keeps_it(self):
        """With withheld cells that have rows in the part's PCA, scIntegrate 0.6.0 and later refits it on
        the retained cells: X_pca is rewritten. `keep_input_pca` (0.7.0's flag, bare, after `--methods`)
        keeps the part's as delivered, and so does a run that withholds nothing: X_pca unchanged."""
        for why, params, source, flag in (
                ("keep_input_pca", block(self.design, keep_input_pca=True), "input", True),
                ("nothing withheld", block(self.design, drop_labels=None), "input", False)):
            with self.subTest(why):
                self._fresh()
                rc, r = self.mount(params)
                self.assertEqual((rc, r["status"]), (0, "mounted"), r)
                layer = self.out_json()["answer"]["layer"]
                self.assertEqual(layer["embeddings"]["unchanged"], ["X_pca"])
                argv = self.calls_of("integrate")[0]["argv"]
                self.assertEqual("--keep-input-pca" in argv, flag)
                if flag:
                    i = argv.index("--keep-input-pca")
                    self.assertEqual(argv[i - 2:i + 2], ["--methods", "none,harmony,bbknn", "--keep-input-pca",
                                                         "--n-cores"], "in scIntegrate's parser order")
                report = json.loads((self.run_dir / "scintegrate" / "report.json").read_text())
                self.assertEqual(report["pca"]["source"], source)
                self.assertEqual(report["pca"]["declared"], "--keep-input-pca" if flag else None)


# ---------------------------------------------------------------------------- the companion
@unittest.skipUnless(HAVE_H5PY, "h5py is not available in this interpreter")
class TheCompanion(unittest.TestCase):
    """Asked of a run directly: an embedding or a graph whose rows are not the stack's observations,
    once each, fails the check that the layer covers them."""

    def facts(self, d, n_ids, n_rows, slot="embedding"):
        import numpy as np
        d.mkdir(parents=True, exist_ok=True)
        sub = d / ("embeddings" if slot == "embedding" else "graphs")
        sub.mkdir()
        (sub / "barcodes.txt").write_text("".join(f"p|o{i}\n" for i in range(n_ids)))
        if slot == "embedding":
            path = sub / "e.npy"
            np.save(path, np.zeros((n_rows, 3), dtype="float32"))
        else:
            path = sub / "g.npz"
            np.savez(path, data=np.ones(n_rows, "float32"), indices=np.arange(n_rows, dtype="int32"),
                     indptr=np.arange(n_rows + 1, dtype="int32"), format=np.array("csr"),
                     shape=np.array([n_rows, n_rows]))
        facts = {"plugin": "int@scintegrate", "out_dir": str(d), "out": {}, "masked": [],
                 "observations": 5, "identity": "barcode",
                 "contributions": [{"slot": slot, "name": path.stem, "path": str(path), "coverage": 0}]}
        (d / "facts.json").write_text(json.dumps(facts))
        env = dict(os.environ, SCH_PROTOCOL=str(ROOT / "sch" / "plugin" / "protocol.py"))
        rc = subprocess.run([sys.executable, str(PLUGIN / "invariant.py"), str(d / "facts.json"),
                             str(d / "result.json")], env=env, capture_output=True, text=True)
        return rc.returncode, json.loads((d / "result.json").read_text())

    def test_a_layer_over_every_observation_holds_and_one_short_fails(self):
        tmp = Path(tempfile.mkdtemp(prefix="sch-scint-companion-"))
        try:
            for slot in ("embedding", "graph"):
                with self.subTest(slot):
                    rc, res = self.facts(tmp / slot / "whole", 5, 5, slot)
                    self.assertEqual((rc, res["failed"]), (0, []), res)
                    rc, res = self.facts(tmp / slot / "short", 4, 4, slot)
                    self.assertEqual(rc, 1, res)
                    self.assertIn("cover other than the stack's 5", res["failed"][0]["message"])
                    rc, res = self.facts(tmp / slot / "unbound", 5, 4, slot)
                    self.assertEqual(rc, 1, res)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------- the reader
@unittest.skipUnless(HAVE_H5PY, "h5py is not available in this interpreter")
class TheReader(unittest.TestCase):
    def setUp(self):
        self.r = _load(PLUGIN / "h5read.py", "int_scintegrate_h5read")
        self.tmp = Path(tempfile.mkdtemp(prefix="sch-h5read-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_an_embedding_and_a_graph_are_read_as_stored_and_an_unknown_encoding_is_named(self):
        import h5py
        import numpy as np
        p = self.tmp / "x.h5ad"
        f = fake()
        f.write_object(p, ["a", "b", "c"], {"g": ("str", ["x", "y", "z"])},
                       obsm={"dense": np.arange(6, dtype="float32").reshape(3, 2)},
                       obsp={"g1": f.ring(3, 1, 2.0)})
        with h5py.File(p, "a") as h:
            csc = h["obsp"].create_group("g2")
            csc.attrs["encoding-type"], csc.attrs["shape"] = "csc_matrix", [3, 3]
            csc.create_dataset("data", data=np.array([5.0]))
            csc.create_dataset("indices", data=np.array([2]))
            csc.create_dataset("indptr", data=np.array([0, 0, 1, 1]))
            sp = h["obsm"].create_group("sparse")
            sp.attrs["encoding-type"], sp.attrs["shape"] = "csr_matrix", [3, 2]
            sp.create_dataset("data", data=np.array([7.0]))
            sp.create_dataset("indices", data=np.array([1]))
            sp.create_dataset("indptr", data=np.array([0, 0, 0, 1]))
            df = h["obsm"].create_group("frame")
            df.attrs["encoding-type"] = "dataframe"
        with h5py.File(p, "r") as h:
            self.assertEqual(self.r.index(h), ["a", "b", "c"])
            self.assertEqual(self.r.keys(h, "obsm"), ["dense", "frame", "sparse"])
            self.assertTrue(np.array_equal(self.r.array(h, "dense"), np.arange(6).reshape(3, 2)))
            self.assertEqual(self.r.array(h, "sparse").tolist(), [[0, 0], [0, 0], [0, 7.0]])
            g1 = self.r.graph(h, "g1")
            self.assertEqual((g1.fmt, g1.shape), ("csr", (3, 3)))
            rows, cols, vals = self.r.graph(h, "g2").triples()
            self.assertEqual((rows.tolist(), cols.tolist(), vals.tolist()), ([2], [1], [5.0]))
            perm = np.array([2, 0, 1])                  # old position -> new
            rows, cols, _ = g1.triples(perm)
            self.assertEqual(sorted(zip(rows.tolist(), cols.tolist())), [(0, 1), (1, 2), (2, 0)])
            with self.assertRaises(self.r.Unreadable) as e:
                self.r.array(h, "frame")
            self.assertIn("frame", str(e.exception))
            self.assertIn("dataframe", str(e.exception))


# ---------------------------------------------------------------------------- the kernel
@unittest.skipUnless(HAVE_H5PY, "h5py is not available in this interpreter")
class TheViewsDigestCoversEmbeddingsAndGraphs(_Base):
    """A layer of embeddings or graphs alone used to leave the view's digest as it was: neither its
    mount nor its unmount could be seen, and E4 compared two equal digests (harness W034). The digest
    now covers each by its content. A view without them hashes as before (every other test)."""

    PLUGIN_PY = PROTO_HEAD + """
from pathlib import Path
kind, fill = run.params["kind"], float(run.params["fill"])
d = run.out_dir / ("embeddings" if kind == "embedding" else "graphs")
d.mkdir(parents=True, exist_ok=True)
ids = [l.split(",")[0] for l in open(run.data).read().splitlines()[1:]]
(d / "barcodes.txt").write_text("".join(i + "\\n" for i in ids))
if kind == "embedding":
    (d / "e.csv").write_text("barcode,d0\\n" + "".join(f"{i},{fill}\\n" for i in ids))
    run._out["embeddings"]["e"] = "embeddings/e.csv"
else:
    (d / "g.csv").write_text("row,col,value\\n" + "".join(f"{i},{i},{fill}\\n" for i in ids))
    run._out["graphs"]["g"] = "graphs/g.csv"
sys.exit(run.finish(headline="one " + kind))
"""

    def test_an_embedding_or_a_graph_moves_the_digest_and_its_unmount_restores_it(self):
        manifest, _design, _part = joint(self.tmp)
        write_plugin(self.tmp / "plugins", "carry", {"profile": "single-cell/1.0",
                                                    "provides": ["embedding/*", "graph/*"]}, self.PLUGIN_PY)
        self.init(manifest)
        before = self.view()
        seen = set()
        for kind in ("embedding", "graph"):
            for fill in ("1.0", "2.0"):
                with self.subTest(kind=kind, fill=fill):
                    st = Stack.open(self.stack)
                    r = st.mount(str(self.tmp / "plugins" / "carry"), {"kind": kind, "fill": fill})
                    st.close()
                    self.assertEqual(r.status, "mounted", r.reason)
                    try:
                        mounted = self.view()
                        self.assertNotEqual(mounted["digest"], before["digest"], "the layer is invisible")
                        self.assertNotIn(mounted["digest"], seen, "two contents, one digest")
                        seen.add(mounted["digest"])
                        readme = (Path(mounted["path"]).parent / "README.md").read_text()
                        self.assertIn(f"{kind}/{'e' if kind == 'embedding' else 'g'}", readme)
                    finally:
                        rc, done = cli("--json", "unmount", "--stack", str(self.stack), "carry")
                    self.assertEqual(rc, 0, done)
                    self.assertEqual(self.view()["digest"], before["digest"])


# ---------------------------------------------------------------------------- the real scIntegrate
def _real_scintegrate():
    """The scIntegrate checkout to run, when this interpreter can run it: `SCH_TEST_SCINTEGRATE`
    names it, and the analysis stack its `integrate` imports is here."""
    checkout = os.environ.get("SCH_TEST_SCINTEGRATE")
    if not checkout or not (Path(checkout) / "scintegrate" / "cli.py").is_file():
        return None
    for mod in ("anndata", "scanpy", "harmonypy", "bbknn", "scib", "threadpoolctl"):
        if importlib.util.find_spec(mod) is None:
            return None
    return checkout


def synthetic_joint(dest: Path, library=None):
    """Four invented populations over three libraries with a library shift, Ensembl-shaped invented
    identifiers of one species, counts and log-normalised values, a PCA, and a design; with `library`
    (a function of the batch value), a `library` column too. Nothing here is any study's. Returns
    (manifest, design)."""
    import anndata as ad
    import numpy as np
    import pandas as pd
    import scanpy as sc
    import scipy.sparse as sp
    rng = np.random.default_rng(0)
    libs = [f"L{i}" for i in (1, 2, 3)]
    types = ["Alpha", "Beta", "Gamma", "Delta"]
    lib = np.repeat(libs, 60)
    # object, not the types' fixed-width text: "EXCLUDED" written into a 5-character array is "EXCLU",
    # and `--drop-labels EXCLUDED` withheld no cell here until 2026-11-12 (W052)
    lab = np.tile(np.repeat(types, 15), 3).astype(object)
    lab[::29] = "EXCLUDED"
    n, g = len(lib), 120
    mu = np.full((n, g), 0.3)
    for k, t in enumerate(types):
        mu[lab == t, k * 20:(k + 1) * 20] += 2.0
    for k, b in enumerate(libs):
        mu[lib == b, 90 + k * 8:98 + k * 8] += 1.2
    X = rng.poisson(np.expm1(mu)).astype("float32")
    a = ad.AnnData(X=sp.csr_matrix(X))
    a.layers["counts"] = a.X.copy()
    sc.pp.normalize_total(a, target_sum=1e4)
    sc.pp.log1p(a)
    a.layers["lognorm"] = a.X.copy()
    a.obs_names = [f"{b}_C{i:04d}" for i, b in enumerate(lib)]
    a.var_names = [f"GENE{i:04d}" for i in range(g)]
    a.var["gene_ids"] = [f"ENSG{100000 + i:011d}" for i in range(g)]
    a.obs["sample"] = pd.Categorical(lib)
    a.obs["label"] = pd.Categorical(lab)
    a.obs["coarse"] = pd.Categorical(np.where(np.isin(lab, ["Alpha", "Beta"]), "AB", "GD"))
    if library:
        a.obs["library"] = pd.Categorical([library(b) for b in lib])
    sc.pp.pca(a, n_comps=12, svd_solver="arpack", random_state=0)
    part = dest / "objects" / "joint.h5ad"
    part.parent.mkdir(parents=True, exist_ok=True)
    a.write_h5ad(part)
    manifest = dest / "joint.tsv"
    manifest.write_text(f"part\th5ad\njoint\t{part}\n")
    design = dest / "design.csv"
    design.write_text("sample,arm\nL1,x\nL2,y\nL3,x\n")
    for p in (manifest, design, part):
        p.chmod(0o444)
    return manifest, design


@unittest.skipUnless(_real_scintegrate(), "SCH_TEST_SCINTEGRATE does not name a scIntegrate checkout this "
                                          "interpreter can run (it needs anndata, scanpy, harmonypy, "
                                          "bbknn, scib and threadpoolctl)")
class TheRealScintegrate(_Base):
    """kernel -> adapter -> scIntegrate's REAL CLI -> the layer -> unmount -> the pre-mount digest."""

    def test_a_synthetic_joint_object_through_the_real_scintegrate_and_back(self):
        for k, sub in (("NUMBA_CACHE_DIR", "numba"), ("MPLCONFIGDIR", "mpl")):
            os.environ.setdefault(k, str(self.tmp / "cache" / sub))
        manifest, design = synthetic_joint(self.tmp / "cohort")
        self.init(manifest, "--context", "assay=scrna", "--context", "species=homo_sapiens")
        before = self.view()
        integrate = {"batch_key": "sample", "label_key": "label", "l1_key": "coarse",
                     "drop_labels": "EXCLUDED", "design": str(design), "bio_factor": ["arm"],
                     "methods": "none,harmony,bbknn", "k": "10", "n_pcs": "12", "seed": "0",
                     "n_cores": "1", "scib_resolutions": "3"}
        rc, r = self.mount(integrate, checkout=_real_scintegrate())
        self.assertEqual((rc, r["status"]), (0, "mounted"), r)
        out = self.out_json()
        layer = out["answer"]["layer"]
        self.assertIn("X_harmony", layer["embeddings"]["added"])
        # 0.7.0: the EXCLUDED cells have rows in the part's PCA, so scIntegrate refits it on the rest
        self.assertIn("X_pca", layer["embeddings"]["rewritten"])
        self.assertEqual(layer["embeddings"]["unchanged"], [])
        import numpy as np
        pca = np.load(self.run_dir / "embeddings" / "X_pca.npy")
        self.assertEqual(np.flatnonzero(np.isnan(pca).any(axis=1)).tolist(), list(range(0, 180, 29)))
        self.assertEqual(layer["graphs"]["added"], ["bbknn_connectivities", "bbknn_distances"])
        self.assertIn("arm", layer["columns"]["added"])
        self.assertEqual(layer["columns"]["rewritten"], [])
        rec = out["answer"]["stage_record"]
        self.assertEqual(rec["integrate"]["status"], "ok")
        self.assertEqual((rec["describe"]["state_version"], rec["integrate"]["state_version"]), (2, 2))
        report = json.loads((self.run_dir / "scintegrate" / "report.json").read_text())
        self.assertEqual(report["design_key"], {"column": "sample", "how": "the batch column itself",
                                                "added": False}, "keyed on the batch: nothing added")
        mounted = self.view()
        self.assertEqual((mounted["kept"], mounted["total"]), (before["total"], before["total"]))
        self.assertNotEqual(mounted["digest"], before["digest"])
        rc, done = cli("--json", "unmount", "--stack", str(self.stack), "int@scintegrate")
        self.assertEqual(rc, 0, done)
        self.assertEqual(self.view()["digest"], before["digest"])

    def test_the_stand_in_writes_what_the_real_scintegrate_writes_on_the_same_inputs(self):
        """ATTACKS 1: a stand-in laxer than its tool passes where the tool refuses. The stand-in and the
        real scIntegrate each run `integrate`, alone, on the same small inputs, and what each WRITES is
        compared: the exit and the status, a refusal's own words up to the writer's, the object's obs
        columns in order and the key column's values, `design_key`, the `pca` record, whether X_pca is
        the part's and its NaN rows, and the obsm and obsp keys. The numbers are not compared: the
        stand-in computes a pattern, never an integration."""
        import h5py
        import numpy as np
        for k, sub in (("NUMBA_CACHE_DIR", "numba"), ("MPLCONFIGDIR", "mpl")):
            os.environ.setdefault(k, str(self.tmp / "cache" / sub))
        parts = {}
        for name, library in (("plain", None), ("equal", lambda b: b),
                              ("other", lambda b: {"L1": "L2", "L2": "L1"}.get(b, b))):
            synthetic_joint(self.tmp / name, library=library)
            parts[name] = self.tmp / name / "objects" / "joint.h5ad"
        designs = {}
        for name, text in (("batch", "sample,arm\nL1,x\nL2,y\nL3,x\n"), ("library", "library,arm\nL1,x\nL2,y\nL3,x\n"),
                           ("slash", "sample,donor/x\nL1,a\nL2,b\nL3,a\n"),
                           ("index", "sample,_index\nL1,a\nL2,b\nL3,a\n")):
            designs[name] = self.tmp / f"design_{name}.csv"
            designs[name].write_text(text)
        cases = (("keyed on the batch key", "plain", "batch", []),
                 ("the key absent: added", "plain", "library", []),
                 ("the key present and equal: kept", "equal", "library", []),
                 ("the key present and different: refused", "other", "library", []),
                 ("a factor holding '/': refused", "plain", "slash", []),
                 ("a factor named _index: refused", "plain", "index", []),
                 ("keep the part's PCA", "plain", "batch", ["--keep-input-pca"]),
                 ("nothing withheld", "plain", "batch", None))

        def written(out, part):
            if not (out / "STATUS.json").is_file():
                return {"status": None}                  # stopped at the parser, before any record
            st = json.loads((out / "STATUS.json").read_text())
            seen = {"status": st["status"],
                    "objects": sorted(p.name for p in out.glob("objects/*.h5ad"))}
            if st["status"] == "refused":
                seen["reason"] = str(st["refusal"]["reason"]).split(" (")[0]
                seen["fix"] = st["refusal"]["fix"]
                return seen
            if st["status"] != "ok" or not seen["objects"] or not (out / "report.json").is_file():
                seen["headline"] = st.get("headline")       # failed, or ok without its products
                return seen
            rep = json.loads((out / "report.json").read_text())
            seen["design_key"] = rep.get("design_key")
            seen["pca"] = {k: (rep.get("pca") or {}).get(k) for k in
                           ("source", "declared", "n_withheld_not_fitted", "n_withheld_in_fit")}
            with h5py.File(out / "objects" / seen["objects"][0], "r") as fo, h5py.File(part, "r") as fp:
                seen["obs"] = [str(c) for c in fo["obs"].attrs["column-order"]]
                if "library" in seen["obs"]:
                    seen["library"] = fake()._column_text(fo["obs"]["library"])
                mine, theirs = fo["obsm"]["X_pca"][()], fp["obsm"]["X_pca"][()]
                seen["X_pca is the part's"] = bool(np.array_equal(mine, theirs, equal_nan=True))
                seen["X_pca NaN rows"] = np.flatnonzero(np.isnan(mine).any(axis=1)).tolist()
                seen["obsm"], seen["obsp"] = sorted(fo["obsm"]), sorted(fo["obsp"])
            return seen

        for i, (why, part, design, extra) in enumerate(cases):
            with self.subTest(why):
                argv = ["integrate", "--h5ad", str(parts[part]), "--batch-key", "sample", "--label-key", "label",
                        "--species", "homo_sapiens", "--assay", "scrna", "--l1-key", "coarse",
                        "--design", str(designs[design]), "--k", "10", "--n-pcs", "12", "--seed", "0",
                        "--methods", "none,harmony,bbknn", "--n-cores", "1", "--scib-resolutions", "3"]
                argv += ["--drop-labels", "EXCLUDED"] + extra if extra is not None else []
                seen = {}
                for who, checkout in (("stand-in", FAKE), ("scIntegrate", _real_scintegrate())):
                    out = self.tmp / "runs" / f"{i}-{who}"
                    p = subprocess.run([sys.executable, "-m", "scintegrate.cli", *argv, "--out", str(out)],
                                       env=dict(os.environ, PYTHONPATH=str(checkout)), cwd=str(self.tmp),
                                       capture_output=True, text=True)
                    seen[who] = (p.returncode, written(out, parts[part]))
                self.assertEqual(seen["stand-in"], seen["scIntegrate"])
                self.assertEqual(seen["scIntegrate"][0], 2 if "refused" in why else 0, seen)


if __name__ == "__main__":
    unittest.main()
