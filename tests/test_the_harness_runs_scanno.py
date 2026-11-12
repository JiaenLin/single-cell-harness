"""The harness runs its second tool: `anno@scanno` through the real `sch` CLI (harness W026, GAP-001).

Until this wave the kernel could run scQC and no other tool of the family: a cohort's annotation ran
as a hand-written job script. The adapter calls scAnno's REAL command line - `cluster`, `annotate`
once per library, `rescue`, in that order - and adopts scAnno's own STATUS.<cmd>.json and seals as
the stage's record. Its labels are the harness's kind of contribution: a LAYER of columns over the
observations, never an edit of them, so unmounting it gives back the view it was mounted on.

Most tests use a stand-in for scAnno's CLI (`fixtures/fake_scanno.py`) that honours the same flags
and writes the same layout, as `fake_scqc.py` does for scQC. The last class runs the REAL scAnno
on a synthetic cohort when `SCH_TEST_SCANNO` names its CLI and anndata and scanpy import.

Every assertion reads the world - the argv the tool received, the view's columns and digest, the
files on disk - never the kernel's report of itself.
"""
import csv
import importlib.util
import io
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from helpers import FIXTURES, HAVE_H5PY, PROTO_HEAD, ROOT, read_only, release_tree, write_plugin
from sch.cli import main
from sch.kernel import Stack

FAKE = FIXTURES / "fake_scanno.py"
PLUGIN = ROOT / "plugins" / "single-cell" / "anno@scanno"
LADDER = ["1.0", "2.0", "3.0"]
KEYS = [f"leiden_{r.replace('.', 'p')}" for r in LADDER]


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


def view_rows(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def libraries(dest: Path, n_libraries=3, n_obs=12, stem=None):
    """A manifest of `n_libraries` libraries, each part one library's object after QC, read-only as
    delivered data are. Every part carries the same barcodes (they recur across libraries), and
    four obs columns: `sample`, a count, a float with a missing value, and two clusterings - one
    the stand-in's `cluster` will recompute IDENTICALLY (`leiden_1p0`), one it will rewrite
    (`leiden_2p0`). Returns (manifest, references)."""
    fake = _load(FAKE, "fake_scanno_for_fixture")
    dest = Path(dest)
    rows = ["sample\th5ad"]
    for i in range(n_libraries):
        s = f"L{i + 1}"
        part = (dest / "objects" / s / f"{stem}.h5ad") if stem else (dest / "objects" / f"{s}.qc.h5ad")
        index = [f"BC{j:05d}-1" for j in range(n_obs)]
        fake.write_obs(part, index, {
            "sample": ("cat", [s] * n_obs),
            "n_counts": ("int", [100 + j for j in range(n_obs)]),
            "frac": ("float", [float("nan") if j == 2 else j / 10 for j in range(n_obs)]),
            "leiden_1p0": ("int", [int(fake.leiden(j, 1.0)) for j in range(n_obs)]),
            "leiden_2p0": ("int", [0] * n_obs),
        })
        rows.append(f"{s}\t{part}")
    manifest = dest / "observations.tsv"
    manifest.write_text("\n".join(rows) + "\n")
    read_only([manifest] + sorted((dest / "objects").rglob("*.h5ad")))
    refs = {}
    for name in ("tree.json", "scope.json", "corpus.db", "store.npz"):
        (dest / "refs").mkdir(parents=True, exist_ok=True)
        (dest / "refs" / name).write_text("{}\n")
        refs[name.split(".")[0]] = str(dest / "refs" / name)
    return manifest, refs


def blocks(refs, **over):
    """The three commands' flags, as a stage declares them: scAnno's names, `-` written `_`."""
    b = {"cluster": {"resolutions": ",".join(LADDER), "seed": 0},
         "annotate": {"cluster_key": KEYS, "resolve": True, "tree": refs["tree"],
                      "scope": refs["scope"], "db": refs["corpus"], "store": refs["store"],
                      "species": "species_x", "tissue": "tissue_x"},
         "rescue": {"label_key": "scanno_resolved_path", "unit_key": "sample",
                    "sweep_prefix": "scanno_resolved_path_r", "cluster_prefix": "leiden_",
                    "from_resolution": 1.0, "to_resolution": 3.0, "out_key": "label_rescued"}}
    for k, v in over.items():
        if v is None:
            b.pop(k, None)
        else:
            b[k] = v
    return b


class _Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sch-scanno-"))
        self.stack = self.tmp / "stack"
        self.calls = self.tmp / "scanno_calls.jsonl"
        self._env = {k: os.environ.get(k) for k in ("FAKE_SCANNO_LOG", "FAKE_SCANNO_MODE",
                                                    "FAKE_SCANNO_STATE_VERSION")}
        os.environ["FAKE_SCANNO_LOG"] = str(self.calls)
        os.environ.pop("FAKE_SCANNO_MODE", None)
        os.environ.pop("FAKE_SCANNO_STATE_VERSION", None)

    def tearDown(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        release_tree(self.tmp)                   # never follows a link (W056 fix 1)

    def init(self, manifest, *context):
        rc, out = cli("init", str(self.stack), "--profile", "single-cell/1.0",
                      "--observations", str(manifest), "--parts", "h5ad", "--key", "sample=sample",
                      *context)
        self.assertEqual(rc, 0, out)

    def mount(self, params: dict, scanno=None, *extra):
        argv = ["--json", "mount", "--stack", str(self.stack), "anno@scanno",
                "--param", f"scanno={scanno or FAKE}"]
        for k, v in params.items():
            argv += ["--param", f"{k}={json.dumps(v)}"]
        rc, out = cli(*argv, *extra)
        return rc, json.loads(out)

    def view(self):
        rc, out = cli("--json", "materialise", "--stack", str(self.stack))
        self.assertEqual(rc, 0, out)
        return json.loads(out)

    def calls_of(self, cmd=None) -> list:
        if not self.calls.exists():
            return []
        calls = [json.loads(x)["argv"] for x in self.calls.read_text().splitlines()]
        return [c for c in calls if cmd is None or c[:1] == [cmd]]

    @property
    def project(self) -> Path:
        return self.stack.resolve() / "plugins" / "anno_scanno" / "out" / "scanno"


@unittest.skipUnless(HAVE_H5PY, "h5py is not available in this interpreter")
class TheHarnessRunsScanno(_Base):
    N_LIB, N_OBS = 3, 12

    def setUp(self):
        super().setUp()
        self.manifest, self.refs = libraries(self.tmp, self.N_LIB, self.N_OBS)
        self.parts = [str(self.tmp / "objects" / f"L{i + 1}.qc.h5ad") for i in range(self.N_LIB)]

    # ----------------------------------------------------------------------- the stage
    def test_it_mounts_through_the_real_cli_as_a_layer_and_unmount_restores_the_view(self):
        self.init(self.manifest, "--context", "assay=snrna")
        before = self.view()
        total = self.N_LIB * self.N_OBS
        self.assertEqual((before["kept"], before["total"]), (total, total))

        rc, r = self.mount(blocks(self.refs))
        self.assertEqual((rc, r["status"]), (0, "mounted"), r)

        # scAnno received exactly the declared calls, in its own order: one cluster over every
        # library, one annotate per library, one rescue over the annotated objects. Its flags are
        # the declaration's, in scAnno's parser order; the paths inside the run are the adapter's.
        P = self.project
        self.assertEqual([c[0] for c in self.calls_of()],
                         ["describe", "cluster", "annotate", "annotate", "annotate", "rescue"])
        self.assertEqual(self.calls_of("cluster")[0],
                         ["cluster", "--h5ad", *self.parts, "--out-dir", str(P / "clustered"),
                          "--resolutions", "1.0,2.0,3.0", "--seed", "0"])
        for s, call in zip(("L1", "L2", "L3"), self.calls_of("annotate")):
            ck = [x for k in KEYS for x in ("--cluster-key", k)]
            self.assertEqual(call, ["annotate", "--h5ad", str(P / "clustered" / f"{s}.qc_clustered.h5ad"),
                                    *ck, "--tree", self.refs["tree"], "--resolve",
                                    "--scope", self.refs["scope"], "--species", "species_x",
                                    "--tissue", "tissue_x", "--assay", "snrna",
                                    "--db", self.refs["corpus"], "--store", self.refs["store"],
                                    "--out-h5ad", str(P / "annotated" / f"{s}.ladder.h5ad")])
        self.assertEqual(self.calls_of("rescue")[0],
                         ["rescue", "--h5ad", *[str(P / "annotated" / f"L{i + 1}.ladder.h5ad")
                                                for i in range(self.N_LIB)],
                          "--label-key", "scanno_resolved_path",
                          "--sweep-prefix", "scanno_resolved_path_r", "--cluster-prefix", "leiden_",
                          "--unit-key", "sample", "--from-resolution", "1.0",
                          "--to-resolution", "3.0", "--out-key", "label_rescued",
                          "--out-dir", str(P / "rescued"), "--out", str(P / "rescue" / "rescue.json"),
                          "--out-table", str(P / "rescue" / "impact.csv"),
                          "--out-report", str(P / "rescue" / "rescue.html")])

        # the layer: what scAnno ADDED or REWROTE, over every observation; nothing removed
        mounted = self.view()
        self.assertEqual((mounted["kept"], mounted["total"]), (total, total))
        self.assertNotEqual(mounted["digest"], before["digest"])
        rows = view_rows(mounted["path"])
        layer = sorted(c[len("column__"):] for c in rows[0] if c.startswith("column__"))
        out = json.loads((P.parent / "out.json").read_text())
        self.assertEqual(sorted(out["answer"]["layer"]["rewritten"]), ["leiden_2p0"])
        self.assertIn("leiden_3p0", out["answer"]["layer"]["added"])
        self.assertIn("label_rescued", out["answer"]["layer"]["added"])
        self.assertEqual(layer, sorted(out["answer"]["layer"]["added"]
                                       + out["answer"]["layer"]["rewritten"]))
        for gone in ("leiden_1p0", "sample", "n_counts", "frac"):
            self.assertNotIn(gone, layer, "a column the observations carry unchanged is not scAnno's")
        by_id = {r["barcode"]: r for r in rows}
        self.assertEqual(by_id["L2|BC00007-1"]["column__label_rescued"],
                         "root/type_" + _load(FAKE, "f").leiden(7, 1.0))
        self.assertEqual(by_id["L1|BC00000-1"]["column__scanno_gap"], "", "a NaN is missing")
        self.assertTrue(all(r[f"column__{c}"] != "" for r in rows for c in layer
                            if c != "scanno_gap"))

        # the stage record is scAnno's own, adopted: every call's STATUS, and each annotate's kept
        rec = out["answer"]["stage_record"]
        self.assertEqual(sorted(rec), ["annotate_L1", "annotate_L2", "annotate_L3", "cluster", "rescue"])
        self.assertTrue(all(v["status"] == "ok" and v["seal"] == f"SEALED.{k.split('_')[0]}.txt"
                            for k, v in rec.items()), rec)
        for s in ("L1", "L2", "L3"):
            kept = json.loads((P / "status" / f"annotate_{s}.STATUS.json").read_text())
            self.assertIn(f"{s}.ladder.h5ad", kept["argv"][-1])
        self.assertIn("scAnno", out["wrapped_versions"])
        self.assertTrue(any(t.endswith("rescue/impact.csv") for t in out["tables"]))

        # taken back: no observation to restore, nothing above it, the view as it was
        rc, dry = cli("--json", "unmount", "--stack", str(self.stack), "anno@scanno", "--dry-run")
        self.assertEqual(rc, 0, dry)
        self.assertEqual((json.loads(dry)["would_restore"], json.loads(dry)["would_invalidate"]), (0, []))
        rc, done = cli("--json", "unmount", "--stack", str(self.stack), "anno@scanno")
        self.assertEqual(rc, 0, done)
        after = self.view()
        self.assertEqual((after["kept"], after["total"], after["digest"]),
                         (total, total, before["digest"]))
        self.assertEqual([c for c in view_rows(after["path"])[0] if c.startswith("column__")], [])

    def test_the_companion_held_and_no_gate_is_asked_of_a_layer_that_removes_nothing(self):
        self.init(self.manifest, "--context", "assay=snrna")
        rc, r = self.mount(blocks(self.refs))
        self.assertEqual((rc, r["status"]), (0, "mounted"), r)
        self.assertEqual(r["gates"], [])
        events = [json.loads(x) for x in (self.stack / "events.jsonl").read_text().splitlines()]
        held = [e for e in events if e["kind"] == "invariant/held" and e.get("owner") == "anno@scanno"]
        self.assertEqual(len(held), 2, events[-5:])

    def test_the_declared_commands_run_and_no_other(self):
        """Without `rescue` the layer is the annotated objects'; without `cluster` annotate reads
        each library itself."""
        self.init(self.manifest, "--context", "assay=snrna")
        rc, r = self.mount(blocks(self.refs, rescue=None))
        self.assertEqual((rc, r["status"]), (0, "mounted"), r)
        self.assertEqual([c[0] for c in self.calls_of()], ["describe", "cluster"] + ["annotate"] * 3)
        out = json.loads((self.project.parent / "out.json").read_text())
        self.assertNotIn("label_rescued", out["answer"]["layer"]["added"])
        self.assertIn("scanno_resolved_path", out["answer"]["layer"]["added"])

        rc, _ = cli("--json", "unmount", "--stack", str(self.stack), "anno@scanno")
        self.calls.unlink()
        ann = dict(blocks(self.refs)["annotate"], cluster_key=["leiden_1p0", "leiden_2p0"])
        rc, r = self.mount(blocks(self.refs, cluster=None, rescue=None, annotate=ann))
        self.assertEqual((rc, r["status"]), (0, "mounted"), r)
        self.assertEqual([c[0] for c in self.calls_of()], ["describe"] + ["annotate"] * 3)
        self.assertEqual([c[2] for c in self.calls_of("annotate")], self.parts)
        out = json.loads((self.project.parent / "out.json").read_text())
        self.assertEqual(out["answer"]["layer"]["rewritten"], [], "nothing was re-clustered")

    # ----------------------------------------------------------------------- rule 2
    def test_an_assay_the_stack_did_not_declare_is_refused_before_scanno_runs(self):
        self.init(self.manifest)
        rc, r = self.mount(blocks(self.refs))
        self.assertEqual((rc, r["status"]), (2, "refused"), r)
        self.assertIn("assay", r["reason"])
        self.assertIn("--context assay=", r["fix"])
        self.assertEqual(self.calls_of(), [], "scAnno was called with no declared assay")

    def test_the_declared_assay_reaches_annotate_verbatim_and_no_parameter_sets_it(self):
        self.init(self.manifest, "--context", "assay=scrna")
        b = blocks(self.refs)
        rc, r = self.mount(dict(b, annotate=dict(b["annotate"], assay="snrna")))
        self.assertEqual((rc, r["status"]), (2, "refused"), r)
        self.assertIn("assay", r["reason"])
        self.assertEqual(self.calls_of(), [])
        rc, r = self.mount(b)
        self.assertEqual((rc, r["status"]), (0, "mounted"), r)
        for call in self.calls_of("annotate"):
            self.assertEqual(call[call.index("--assay") + 1], "scrna")
        self.assertTrue(all("--assay" not in c for c in self.calls_of("cluster") + self.calls_of("rescue")))

    # ----------------------------------------------------------------------- what was declared
    def test_a_flag_scanno_does_not_take_or_the_adapter_owns_is_refused_before_scanno_runs(self):
        self.init(self.manifest, "--context", "assay=snrna")
        b = blocks(self.refs)
        bad = {
            "a flag annotate does not have": dict(b, annotate=dict(b["annotate"], min_cells=3)),
            "cluster's output": dict(b, cluster=dict(b["cluster"], out_dir=str(self.tmp))),
            "cluster's split": dict(b, cluster=dict(b["cluster"], split_by="sample")),
            "annotate's output": dict(b, annotate=dict(b["annotate"], out_h5ad=str(self.tmp / "x.h5ad"))),
            "annotate's table": dict(b, annotate=dict(b["annotate"], out=str(self.tmp / "x.tsv"))),
            "rescue's record": dict(b, rescue=dict(b["rescue"], out=str(self.tmp / "x.json"))),
            "a status directory": dict(b, rescue=dict(b["rescue"], status_dir=str(self.tmp))),
            "an unknown parameter": dict(b, background={"cluster_key": "leiden_1p0"}),
            "a block that is not an object": dict(b, cluster="1.0,2.0"),
            "no annotate": blocks(self.refs, annotate=None),
        }
        for why, params in bad.items():
            with self.subTest(why):
                rc, r = self.mount(params)
                self.assertEqual((rc, r["status"]), (2, "refused"), r)
        rc, r = self.mount(b, scanno=str(self.tmp / "no_such_cli.py"))
        self.assertEqual((rc, r["status"]), (2, "refused"), r)
        self.assertIn("scanno", r["reason"])
        self.assertEqual(self.calls_of(), [])

    def test_a_value_scanno_would_read_as_an_option_is_refused_before_any_call(self):
        """Verifier W026 D1. A zero-argument flag given a value had that value written after it,
        and scanno's parser read it as an option: through the real scAnno, `resolve` carried a
        `--report=` that wrote beside the libraries (E2), and `background_from_clusters` carried an
        `--assay=` that overrode the stack's (rule 2). What a parameter cannot set by its own name
        it cannot set through another's: each is refused by name, before any scAnno process, and
        nothing is written beside the observations."""
        self.init(self.manifest, "--context", "assay=scrna")
        objects = self.tmp / "objects"
        delivered = sorted(p.name for p in objects.iterdir())
        b = blocks(self.refs)
        ann = b["annotate"]
        cases = {
            "(a) a report through resolve": ("resolve", dict(b, annotate=dict(
                ann, resolve=f"--report={objects}/x.html"))),
            "(b) a table through resolve": ("resolve", dict(b, annotate=dict(
                ann, resolve=f"--out={objects}/x.tsv"))),
            "(c) an assay through background_from_clusters": ("background_from_clusters", dict(
                b, annotate=dict(ann, background_from_clusters="--assay=snrna"))),
            "a zero-argument flag given a word": ("use_raw", dict(b, annotate=dict(ann, use_raw="yes"))),
            "a value that is an option": ("tree", dict(b, annotate=dict(ann, tree=f"--report={objects}/y.html"))),
            "one of a repeated flag's values": ("cluster_key", dict(b, annotate=dict(
                ann, cluster_key=KEYS + [f"--out={objects}/z.tsv"]))),
            "a negative number": ("gap_min", dict(b, annotate=dict(ann, gap_min=-0.5))),
            "a flag that takes a value, written bare": ("tree", dict(b, annotate=dict(ann, tree=True))),
            "cluster's values too": ("resolutions", dict(b, cluster=dict(b["cluster"], resolutions="-1.0,2.0"))),
            "rescue's values too": ("out_key", dict(b, rescue=dict(b["rescue"], out_key=f"--out={objects}/w"))),
        }
        for why, (flag, params) in cases.items():
            with self.subTest(why):
                rc, r = self.mount(params)
                self.assertEqual((rc, r["status"]), (2, "refused"), r)
                self.assertIn(flag, r["reason"])
        rc, r = self.mount(b, f"--{self.tmp}")
        self.assertEqual((rc, r["status"]), (2, "refused"), r)
        self.assertIn("scanno", r["reason"])
        shutil.rmtree(self.stack)
        self.init(self.manifest, "--context", "assay=--report=x.html")
        rc, r = self.mount(b)
        self.assertEqual((rc, r["status"]), (2, "refused"), r)
        self.assertIn("assay", r["reason"])
        self.assertEqual(self.calls_of(), [], "a scAnno process was started")
        self.assertEqual(sorted(p.name for p in objects.iterdir()), delivered,
                         "something was written beside the observations")

    def test_two_libraries_whose_objects_share_a_file_stem_are_refused(self):
        """`cluster --out-dir` names each output `<stem>_clustered.h5ad`, so two parts with one stem
        would be written to one file and one library's labels would be another's."""
        manifest, refs = libraries(self.tmp / "same", self.N_LIB, self.N_OBS, stem="deliverable")
        self.init(manifest, "--context", "assay=snrna")
        rc, r = self.mount(blocks(refs))
        self.assertEqual((rc, r["status"]), (2, "refused"), r)
        self.assertIn("deliverable", r["reason"])
        self.assertEqual(self.calls_of(), [])

    def test_it_refuses_a_view_something_beneath_it_already_masked(self):
        self.init(self.manifest, "--context", "assay=snrna")
        write_plugin(self.tmp / "plugins", "drop_one",
                     {"profile": "single-cell/1.0", "provides": ["mask/drop_one"],
                      "gates": {"differential_check": "optional"}},
                     PROTO_HEAD + """
import csv
rows = list(csv.DictReader(open(run.data)))
idc = run.inp["identity"]["column"]
run.mask("drop_one", {r[idc]: not r[idc].endswith("|BC00000-1") for r in rows}, reason="first",
         id_field=idc)
sys.exit(run.finish(headline="masked one per library"))
""")
        st = Stack.open(self.stack)
        r = st.mount(str(self.tmp / "plugins" / "drop_one"))
        st.close()
        self.assertEqual(r.status, "mounted", r.reason)
        rc, r = self.mount(blocks(self.refs))
        self.assertEqual((rc, r["status"]), (2, "refused"), r)
        self.assertIn("masked", r["reason"])
        self.assertEqual(self.calls_of(), [])

    def test_numbers_scanno_versioned_differently_are_refused_before_any_compute(self):
        self.init(self.manifest, "--context", "assay=snrna")
        os.environ["FAKE_SCANNO_STATE_VERSION"] = "2"
        rc, r = self.mount(blocks(self.refs))
        self.assertEqual((rc, r["status"]), (2, "refused"), r)
        self.assertIn("state_version", r["reason"])
        self.assertEqual([c[0] for c in self.calls_of()], ["describe"])

    # ----------------------------------------------------------------------- the stage record
    def test_scannos_refusal_is_the_mounts_refusal_with_its_fix(self):
        self.init(self.manifest, "--context", "assay=snrna")
        for cmd in ("cluster", "annotate", "rescue"):
            with self.subTest(cmd):
                os.environ["FAKE_SCANNO_MODE"] = f"refuse:{cmd}"
                rc, r = self.mount(blocks(self.refs))
                self.assertEqual((rc, r["status"]), (2, "refused"), r)
                self.assertIn(f"{cmd}: the stand-in was told to refuse", r["reason"])
                self.assertIn("declare what the refusal names", r["fix"])

    def test_a_failed_or_unsealed_command_is_a_death_and_the_view_is_unchanged(self):
        self.init(self.manifest, "--context", "assay=snrna")
        before = self.view()
        for mode in ("fail:cluster", "fail:annotate", "fail:rescue", "unsealed:cluster",
                     "unsealed:annotate", "unsealed:rescue"):
            with self.subTest(mode):
                os.environ["FAKE_SCANNO_MODE"] = mode
                rc, r = self.mount(blocks(self.refs))
                self.assertEqual((rc, r["status"]), (2, "died"), r)
                self.assertEqual(self.view()["digest"], before["digest"])

    def test_a_record_that_is_not_this_calls_own_is_not_adopted(self):
        """The ten annotate calls share one directory, so the STATUS.annotate.json there after a
        call that died before scAnno's status contract began is the PREVIOUS call's, sealed ok."""
        self.init(self.manifest, "--context", "assay=snrna")
        os.environ["FAKE_SCANNO_MODE"] = "nostatus:annotate:2"   # the second call, parse error
        rc, r = self.mount(blocks(self.refs))
        self.assertEqual((rc, r["status"]), (2, "died"), r)
        self.assertEqual(len(self.calls_of("annotate")), 2, "the chain went on past a call with no record")
        said = (self.stack / "plugins" / "anno_scanno" / "stderr.log").read_text()
        self.assertIn("no STATUS.annotate.json of its own", said)

    def test_the_companion_refuses_a_layer_that_lost_an_observation(self):
        self.init(self.manifest, "--context", "assay=snrna")
        os.environ["FAKE_SCANNO_MODE"] = "short"
        rc, r = self.mount(blocks(self.refs))
        self.assertEqual((rc, r["status"]), (2, "refused"), r)
        self.assertIn("cover", r["reason"])


@unittest.skipUnless(HAVE_H5PY, "h5py is not available in this interpreter")
class TheObsReader(unittest.TestCase):
    """The adapter reads obs with h5py alone, in every encoding anndata writes a dataframe in."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sch-h5obs-"))
        self.h5obs = _load(PLUGIN / "h5obs.py", "h5obs_under_test")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, build):
        import h5py
        path = self.tmp / "o.h5ad"
        with h5py.File(path, "w") as f:
            obs = f.create_group("obs")
            obs.attrs["encoding-type"] = "dataframe"
            obs.attrs["_index"] = "_index"
            build(obs)
        return path

    def test_every_encoding_is_read_as_text_and_missing_is_none(self):
        import h5py
        import numpy as np
        s = h5py.string_dtype()

        def build(obs):
            g = obs.create_group("_index")            # anndata 0.11+: a nullable string index
            g.attrs["encoding-type"] = "nullable-string-array"
            g.create_dataset("values", data=np.array(["a", "b", "c"], dtype=object), dtype=s)
            g.create_dataset("mask", data=np.array([False, False, False]))
            obs.attrs["column-order"] = ["cat", "num_cat", "i", "f32", "f64", "b", "s",
                                         "ni", "nb", "ns"]
            g = obs.create_group("cat")
            g.attrs["encoding-type"] = "categorical"
            g.create_dataset("categories", data=np.array(["x", "y"], dtype=object), dtype=s)
            g.create_dataset("codes", data=np.array([1, -1, 0], dtype="int8"))
            g = obs.create_group("num_cat")
            g.attrs["encoding-type"] = "categorical"
            g.create_dataset("categories", data=np.array([2, 7], dtype="int64"))
            g.create_dataset("codes", data=np.array([0, 1, 1], dtype="int8"))
            obs.create_dataset("i", data=np.array([1, -2, 3], dtype="int16")).attrs["encoding-type"] = "array"
            obs.create_dataset("f32", data=np.array([0.3, np.nan, 2.0], dtype="float32"))
            obs.create_dataset("f64", data=np.array([0.1, 1e-12, np.inf], dtype="float64"))
            obs.create_dataset("b", data=np.array([True, False, True]))
            d = obs.create_dataset("s", data=np.array(["p", "", "r"], dtype=object), dtype=s)
            d.attrs["encoding-type"] = "string-array"
            for name, kind, vals in (("ni", "nullable-integer", np.array([4, 5, 6])),
                                     ("nb", "nullable-boolean", np.array([True, False, False])),
                                     ("ns", "nullable-string-array",
                                      np.array(["u", "v", "w"], dtype=object))):
                g = obs.create_group(name)
                g.attrs["encoding-type"] = kind
                g.create_dataset("values", data=vals, **({"dtype": s} if vals.dtype == object else {}))
                g.create_dataset("mask", data=np.array([False, True, False]))
            return obs

        p = self.write(build)
        r = self.h5obs
        self.assertEqual(r.index(p), ["a", "b", "c"])
        self.assertEqual(r.columns(p), ["cat", "num_cat", "i", "f32", "f64", "b", "s", "ni", "nb", "ns"])
        expect = {"cat": ["y", None, "x"], "num_cat": ["2", "7", "7"], "i": ["1", "-2", "3"],
                  "f32": ["0.3", None, "2.0"], "f64": ["0.1", "1e-12", "inf"],
                  "b": ["True", "False", "True"], "s": ["p", "", "r"],
                  "ni": ["4", None, "6"], "nb": ["True", None, "False"], "ns": ["u", None, "w"]}
        for c, want in expect.items():
            with self.subTest(c):
                self.assertEqual(r.column(p, c), want)

    def test_an_encoding_it_cannot_read_is_named_never_skipped(self):
        def build(obs):
            obs.create_dataset("_index", data=[b"a"])
            obs.attrs["column-order"] = ["odd"]
            g = obs.create_group("odd")
            g.attrs["encoding-type"] = "awkward-array"
        p = self.write(build)
        with self.assertRaises(self.h5obs.UnreadableColumn) as e:
            self.h5obs.column(p, "odd")
        self.assertIn("odd", str(e.exception))
        self.assertIn("awkward-array", str(e.exception))


# ---------------------------------------------------------------------------- the real scAnno
def _real_scanno():
    """The scAnno CLI to run, when the environment can run it: `SCH_TEST_SCANNO` names it, and
    this interpreter has the analysis stack scAnno's commands import."""
    cli_path = os.environ.get("SCH_TEST_SCANNO")
    if not cli_path or not Path(cli_path).is_file():
        return None
    for mod in ("anndata", "scanpy", "leidenalg", "igraph"):
        if importlib.util.find_spec(mod) is None:
            return None
    return cli_path


def synthetic_cohort(dest: Path, n_libraries=3, per_type=30):
    """Libraries of four invented populations, each with fifteen invented marker symbols over a
    Poisson background; a corpus naming them under an invented species and tissue; a tree over
    them. Nothing here is any study's. Returns (manifest, tree, corpus)."""
    import anndata as ad
    import numpy as np
    import pandas as pd
    import scipy.sparse as sp

    panels = {f"{a} {b}": [f"{a[:1]}{b[:1]}M{i:02d}".upper() for i in range(15)]
              for a in ("Alpha", "Beta") for b in ("one", "two")}
    genes = [g for gs in panels.values() for g in gs] + [f"FILL{i:03d}" for i in range(140)]
    tree = {"children": {"root": ["Alpha", "Beta"], "Alpha": ["Alpha one", "Alpha two"],
                         "Beta": ["Beta one", "Beta two"]},
            "patterns": {"Alpha": ["alpha"], "Beta": ["beta"], "Alpha one": ["alpha one"],
                         "Alpha two": ["alpha two"], "Beta one": ["beta one"],
                         "Beta two": ["beta two"]},
            "members": {}}
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "tree.json").write_text(json.dumps(tree))
    con = sqlite3.connect(dest / "corpus.db")
    con.execute("CREATE TABLE assertion (species TEXT, tissue_class TEXT, cell_name TEXT, "
                "symbol_norm TEXT, evidence_tier INT, n_pmids INT)")
    con.executemany("INSERT INTO assertion VALUES (?,?,?,?,?,?)",
                    [("species_x", "tissue_x", f"{leaf} cell", g, 1, 12)
                     for leaf, gs in panels.items() for g in gs])
    con.commit()
    con.close()
    rows = ["sample\th5ad"]
    for i in range(n_libraries):
        s = f"L{i + 1}"
        rng = np.random.default_rng(i)
        y = np.repeat(np.arange(len(panels)), per_type)
        X = rng.poisson(0.6, size=(len(y), len(genes))).astype("float32")
        for li, leaf in enumerate(panels):
            idx = [genes.index(g) for g in panels[leaf]]
            X[np.ix_(np.flatnonzero(y == li), idx)] += rng.poisson(9.0, size=(per_type, len(idx)))
        A = ad.AnnData(X=sp.csr_matrix(X))
        A.obs_names = [f"BC{j:05d}-1" for j in range(A.n_obs)]
        A.var_names = [f"GX{j:06d}" for j in range(A.n_vars)]
        A.var["gene_symbol"] = genes
        A.obs["sample"] = pd.Categorical([s] * A.n_obs)
        A.obs["n_counts"] = np.asarray(X.sum(axis=1)).astype("int64")
        part = dest / "objects" / f"{s}.qc.h5ad"
        part.parent.mkdir(parents=True, exist_ok=True)
        A.write_h5ad(part)
        rows.append(f"{s}\t{part}")
    manifest = dest / "observations.tsv"
    manifest.write_text("\n".join(rows) + "\n")
    read_only([manifest] + sorted((dest / "objects").glob("*.h5ad")))
    return manifest, dest / "tree.json", dest / "corpus.db"


@unittest.skipUnless(_real_scanno(), "SCH_TEST_SCANNO does not name a scAnno CLI this interpreter "
                                     "can run (it needs anndata, scanpy, leidenalg and igraph)")
class TheRealScanno(_Base):
    """kernel -> adapter -> scAnno's REAL CLI -> the layer -> unmount -> the pre-mount digest."""

    def test_a_synthetic_cohort_through_the_real_scanno_and_back(self):
        os.environ.setdefault("NUMBA_CACHE_DIR", str(self.tmp / "cache" / "numba"))
        os.environ.setdefault("MPLCONFIGDIR", str(self.tmp / "cache" / "mpl"))
        manifest, tree, corpus = synthetic_cohort(self.tmp / "cohort")
        self.init(manifest, "--context", "assay=scrna")
        before = self.view()
        params = {
            "cluster": {"resolutions": "0.5,1.0,2.0", "seed": 0},
            "annotate": {"cluster_key": ["leiden_0p5", "leiden_1p0", "leiden_2p0"], "resolve": True,
                         "tree": str(tree), "db": str(corpus), "species": "species_x",
                         "tissue": "tissue_x", "background_from_clusters": True},
            "rescue": {"label_key": "scanno_resolved_path", "unit_key": "sample",
                       "sweep_prefix": "scanno_resolved_path_r", "cluster_prefix": "leiden_",
                       "out_key": "label_rescued"}}
        rc, r = self.mount(params, scanno=_real_scanno())
        self.assertEqual((rc, r["status"]), (0, "mounted"), r)
        mounted = self.view()
        self.assertEqual((mounted["kept"], mounted["total"]), (before["total"], before["total"]))
        out = json.loads((self.project.parent / "out.json").read_text())
        layer = out["answer"]["layer"]
        self.assertIn("label_rescued", layer["added"])
        self.assertIn("scanno_resolved_path", layer["added"])
        self.assertEqual(layer["rewritten"], [])
        rows = view_rows(mounted["path"])
        self.assertTrue(all(r["column__label_rescued"] for r in rows), "a label is missing")
        self.assertTrue(all(v["status"] == "ok" for v in out["answer"]["stage_record"].values()))
        for sub in ("clustered", "annotated", "rescued"):
            self.assertEqual(len(list((self.project / sub).glob("*.h5ad"))), 3, sub)
        rc, done = cli("--json", "unmount", "--stack", str(self.stack), "anno@scanno")
        self.assertEqual(rc, 0, done)
        after = self.view()
        self.assertEqual((after["kept"], after["digest"]), (before["kept"], before["digest"]))


if __name__ == "__main__":
    unittest.main()
