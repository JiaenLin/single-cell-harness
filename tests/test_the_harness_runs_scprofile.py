"""The harness runs its fourth tool: `prof@scprofile` through the real `sch` CLI (harness W036, GAP-001).

Until this wave the kernel ran scQC, scAnno and scIntegrate and no profiling: a cohort's stage 4 ran
as a hand-written job script. The adapter calls scProfile's REAL command line - `doctor`, then one
`run` over the cohort's integrated object - and adopts scProfile's own STATUS.json and seal as the
stage's record. Which plugins run is scProfile's: `--kernel` is the stage's flag and scProfile's own
plan skips what the design does not admit, which the mount names and never hides. Its result is a
LAYER: the tables and the object scProfile wrote, referenced where they lie, and exactly what its
record says it merged into the observations. Differential expression and abundance are per
population, so a mount of them leaves the view over the observations as it was - and unmounting any
mount gives back the view it was mounted on.

Most tests use a stand-in for scProfile's package (`fixtures/fake_scprofile/`) that honours the same
flags and status contract. The last class runs the REAL scProfile on the harness's own synthetic
fixture when `SCH_TEST_SCPROFILE` names its checkout and this interpreter carries its plugins'
packages (`SCPROFILE_<PLUGIN>_PYTHON` points scProfile at it). Every assertion reads the world - the
argv the tool received, the view's digest, the files on disk - never the kernel's report of itself.
"""
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

from helpers import FIXTURES, HAVE_H5PY, ROOT
from sch.cli import main
from sch.kernel import Stack

FAKE = FIXTURES / "fake_scprofile"
PLUGIN = ROOT / "plugins" / "single-cell" / "prof@scprofile"
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


def integrated(dest: Path, n=N, parts=1):
    """A cohort's integrated object - three libraries already in one file - as the one part of a
    manifest, read-only as a deliverable is (written with the scIntegrate stand-in's h5py writer).
    obs carries the sample, a label and a design factor; obsm an embedding. Returns (manifest,
    design, part)."""
    import numpy as np
    w = _load(FIXTURES / "fake_scintegrate" / "scintegrate" / "cli.py", "fake_scintegrate_writer")
    dest = Path(dest)
    libs = [f"L{1 + i * 3 // n}" for i in range(n)]
    index = [f"{lib}_BC{i:04d}" for i, lib in enumerate(libs)]
    rows = ["part\th5ad"]
    for k in range(parts):
        part = dest / "objects" / f"integrated{k or ''}.h5ad"
        w.write_object(part, index, {
            "sample": ("cat", libs),
            "cell_type": ("cat", ["T" if i % 2 else "B" for i in range(n)]),
            "age": ("cat", ["a2" if lib == "L2" else "a1" for lib in libs]),
        }, obsm={"X_int": np.random.default_rng(0).normal(size=(n, 4)).astype("float32")})
        rows.append(f"integrated{k or ''}\t{part}")
    manifest = dest / "integrated.tsv"
    manifest.write_text("\n".join(rows) + "\n")
    design = dest / "design.csv"
    design.write_text("sample,age\nL1,a1\nL2,a2\nL3,a1\n")
    for p in [manifest, design] + sorted((dest / "objects").glob("*.h5ad")):
        p.chmod(0o444)
    return manifest, design, dest / "objects" / "integrated.h5ad"


def block(**over):
    """run's flags, as a stage declares them: scProfile's names, `-` written `_`."""
    b = {"kernel": "de,abundance", "label_key": "cell_type", "sample_key": "sample",
         "batch_key": "sample", "embedding": "X_int", "control": ["age=a1"], "no_cache": True,
         "prefix": "/declared/prefix", "timeout": 600}
    for k, v in over.items():
        if v is None:
            b.pop(k, None)
        else:
            b[k] = v
    return b


class _Base(unittest.TestCase):
    ENV = ("FAKE_SCPROFILE_LOG", "FAKE_SCPROFILE_MODE", "FAKE_SCPROFILE_STATE_VERSION")
    CONTEXT = ("--context", "assay=snrna", "--context", "organism=mouse")

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sch-scprof-"))
        self.stack = self.tmp / "stack"
        self.calls = self.tmp / "scprofile_calls.jsonl"
        self._env = {k: os.environ.get(k) for k in self.ENV}
        for k in self.ENV:
            os.environ.pop(k, None)
        os.environ["FAKE_SCPROFILE_LOG"] = str(self.calls)

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

    def init(self, manifest, *context, design=None):
        extra = ["--design", str(design)] if design else []
        rc, out = cli("init", str(self.stack), "--profile", "single-cell/1.0", "--observations",
                      str(manifest), "--parts", "h5ad", "--key", "sample=part", *extra, *context)
        self.assertEqual(rc, 0, out)

    def mount(self, run, checkout=None, **extra):
        argv = ["--json", "mount", "--stack", str(self.stack), "prof@scprofile",
                "--param", f"scprofile={checkout or FAKE}"]
        if run is not None:
            argv += ["--param", f"run={json.dumps(run)}"]
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
        return self.stack.resolve() / "plugins" / "prof_scprofile" / "out"

    def out_json(self):
        return json.loads((self.run_dir / "out.json").read_text())

    def contributions(self):
        st = Stack(self.stack)
        try:
            return sorted(c.capability() for c in st.dataset.contributions_of("prof@scprofile"))
        finally:
            st.close()


def flags_of(argv):
    """argv as argparse reads it: {flag: [values]}, a repeated flag's values in order."""
    out, k = {}, None
    for x in argv:
        if x.startswith("--"):
            k = x
            out.setdefault(k, [])
        elif k is not None:
            out[k].append(x)
    return out


@unittest.skipUnless(HAVE_H5PY, "h5py is not available in this interpreter")
class TheHarnessRunsScprofile(_Base):
    def setUp(self):
        super().setUp()
        self.manifest, self.design, self.part = integrated(self.tmp)

    def test_it_mounts_through_the_real_cli_as_a_layer_of_tables_and_unmount_restores_the_view(self):
        self.init(self.manifest, *self.CONTEXT, design=self.design)
        before = self.view()
        rc, r = self.mount(block())
        self.assertEqual((rc, r["status"]), (0, "mounted"), r)
        # the calls, in order, as a stage-4 job makes them: doctor told the run's prefix, then run
        self.assertEqual([c["argv"][0] for c in self.calls_of()], ["doctor", "run"])
        self.assertEqual(self.calls_of("doctor")[0]["argv"], ["doctor", "--prefix", "/declared/prefix"])
        call = self.calls_of("run")[0]
        res = self.run_dir / "scprofile"
        self.assertEqual(call["pythonpath"], str(FAKE))
        self.assertEqual(Path(call["argv0"]).resolve(), (FAKE / "scprofile" / "cli.py").resolve())
        self.assertEqual(Path(call["cwd"]).resolve(), res)
        f = flags_of(call["argv"][1:])
        self.assertEqual(f["--h5ad"], [str(self.part)])                 # in place, never a copy
        self.assertEqual([Path(x).resolve() for x in f["--out"]], [res])
        self.assertEqual(f["--design"], [str(self.design.resolve())])    # the stack's design sheet
        self.assertEqual(f["--assay"], ["nucleus"])                       # snrna, in scProfile's words
        self.assertEqual(f["--organism"], ["mouse"])
        self.assertEqual((f["--kernel"], f["--control"], f["--no-cache"], f["--timeout"]),
                         (["de,abundance"], ["age=a1"], [], ["600"]))
        # scProfile's parser order, every flag once
        order = [x for x in call["argv"][1:] if x.startswith("--")]
        self.assertEqual(order, ["--control", "--no-cache", "--h5ad", "--out", "--kernel", "--prefix",
                                 "--label-key", "--sample-key", "--batch-key", "--embedding",
                                 "--organism", "--assay", "--design", "--timeout"])
        # the layer: the tables and the object, referenced where scProfile wrote them; nothing merged
        out = self.out_json()
        self.assertEqual(sorted(out["tables"]), ["scprofile/kernels/abundance/tables/abundance_by_population.csv",
                                                 "scprofile/kernels/de/tables/de_by_population.csv",
                                                 "scprofile/tables/abundance_by_population.csv",
                                                 "scprofile/tables/de_by_population.csv"])
        self.assertEqual(out["objects"], {"cohort_profiled": "scprofile/objects/cohort_profiled.h5ad"})
        self.assertEqual(out["answer"]["ran"], ["de", "abundance"])
        self.assertEqual(out["answer"]["layer"]["columns"]["added"] + out["answer"]["layer"]["embeddings"]["added"], [])
        self.assertEqual((out["numbers"]["n_tables"], out["numbers"]["n_observations"]), (4, N))
        self.assertEqual(out["answer"]["stage_record"]["run"]["seal"], "SEALED.txt")
        self.assertEqual(self.contributions(), ["object/cohort_profiled"])
        # per population, not per observation: the view does not move, and nothing is removed
        mounted = self.view()
        self.assertEqual((mounted["kept"], mounted["total"], mounted["digest"]),
                         (before["kept"], before["total"], before["digest"]))
        rc, out_u = cli("--json", "unmount", "--stack", str(self.stack), "prof@scprofile")
        self.assertEqual(rc, 0, out_u)
        self.assertEqual(self.view()["digest"], before["digest"])
        self.assertEqual(self.contributions(), [])

    def test_what_scprofile_merged_is_carried_as_columns_and_embeddings_and_unmount_takes_them_back(self):
        os.environ["FAKE_SCPROFILE_MODE"] = "merge"
        self.init(self.manifest, *self.CONTEXT, design=self.design)
        before = self.view()
        rc, r = self.mount(block())
        self.assertEqual((rc, r["status"]), (0, "mounted"), r)
        layer = self.out_json()["answer"]["layer"]
        self.assertEqual((layer["columns"]["added"], layer["embeddings"]["added"]), (["phase"], ["X_fake"]))
        self.assertEqual(self.contributions(), ["column/phase", "embedding/X_fake", "object/cohort_profiled"])
        ids = (self.run_dir / "embeddings" / "barcodes.txt").read_text().split()
        self.assertEqual(len(ids), N)
        self.assertTrue(all(i.startswith("integrated|L") for i in ids), ids[:3])
        mounted = self.view()
        self.assertNotEqual(mounted["digest"], before["digest"])        # a per-observation layer is seen
        self.assertEqual(mounted["kept"], mounted["total"])
        cli("--json", "unmount", "--stack", str(self.stack), "prof@scprofile")
        self.assertEqual(self.view()["digest"], before["digest"])

    def test_no_assay_or_a_word_scprofile_does_not_reason_about_is_refused_before_scprofile_runs(self):
        for context, needle in [((), "declares no assay"), (("--context", "assay=nucleus"), "scrna, snrna"),
                                (("--context", "assay=sn"), "unrecognised")]:
            with self.subTest(context=context):
                shutil.rmtree(self.stack, ignore_errors=True)
                self.init(self.manifest, *context, design=self.design)
                rc, r = self.mount(block())
                self.assertEqual(r["status"], "refused", r)
                self.assertIn(needle, r["reason"])
                self.assertIn("--context assay=", r["fix"])
                self.assertEqual(self.calls_of(), [])

    def test_scrna_is_written_cell_and_an_undeclared_organism_is_left_to_scprofile_and_said(self):
        self.init(self.manifest, "--context", "assay=scrna", design=self.design)
        rc, r = self.mount(block())
        self.assertEqual(r["status"], "mounted", r)
        f = flags_of(self.calls_of("run")[0]["argv"][1:])
        self.assertEqual(f["--assay"], ["cell"])
        self.assertNotIn("--organism", f)
        self.assertTrue(any("declares no organism" in c for c in self.out_json()["caveats"]))

    def test_a_flag_run_does_not_take_or_the_adapter_owns_is_refused_before_scprofile_runs(self):
        self.init(self.manifest, *self.CONTEXT, design=self.design)
        cases = [(block(h5ad="/elsewhere.h5ad"), "h5ad"), (block(out="/elsewhere"), "out"),
                 (block(design="/other.csv"), "design"), (block(assay="nucleus"), "assay"),
                 (block(organism="human"), "organism"), (block(bogus=1), "bogus is not a flag"),
                 ("de", "not an object"), (None, "no run declared")]
        for run_, needle in cases:
            with self.subTest(needle=needle):
                rc, r = self.mount(run_)
                self.assertEqual(r["status"], "refused", r)
                self.assertIn(needle, r["reason"])
        rc, r = self.mount(block(), stray=1)
        self.assertIn("stray", r["reason"])
        rc, r = self.mount(block(), checkout=str(self.tmp))
        self.assertIn("holds no scprofile/cli.py", r["reason"])
        self.assertEqual(self.calls_of(), [])

    def test_a_value_scprofile_would_read_as_an_option_is_refused_before_any_call(self):
        self.init(self.manifest, *self.CONTEXT, design=self.design)
        cases = [(block(no_cache="--assay=cell"), "takes no argument"), (block(kernel=True), "takes a value"),
                 (block(label_key="--assay=cell"), "begins with '-'"),
                 (block(control=["age=a1", "--design=x"]), "begins with '-'"),
                 (block(params={"seed": 1}), "not a value a command line carries"),
                 (block(object_name="../x.h5ad"), "not a file name")]
        for run_, needle in cases:
            with self.subTest(needle=needle):
                rc, r = self.mount(run_)
                self.assertEqual(r["status"], "refused", r)
                self.assertIn(needle, r["reason"])
        self.assertEqual(self.calls_of(), [])

    def test_a_masked_view_two_parts_or_a_missing_design_are_refused(self):
        # a stack of two parts
        manifest2, _d, _p = integrated(self.tmp / "two", parts=2)
        self.init(manifest2, *self.CONTEXT, design=self.design)
        rc, r = self.mount(block())
        self.assertIn("declares 2 parts", r["reason"])
        # a design that is not there any more
        shutil.rmtree(self.stack)
        moved = self.tmp / "gone.csv"
        shutil.copyfile(self.design, moved)
        self.init(self.manifest, *self.CONTEXT, design=moved)
        moved.chmod(0o644)
        moved.unlink()
        rc, r = self.mount(block())
        self.assertIn("is not a file", r["reason"])
        self.assertEqual(self.calls_of(), [])

    def test_scprofiles_refusal_is_the_mounts_refusal_with_its_fix_and_a_bad_run_is_a_death(self):
        self.init(self.manifest, *self.CONTEXT, design=self.design)
        before = self.view()
        os.environ["FAKE_SCPROFILE_MODE"] = "refuse"
        rc, r = self.mount(block())
        self.assertEqual(r["status"], "refused", r)
        self.assertIn("scProfile run refused: the design table has no column", r["reason"])
        self.assertIn("declare --control", r["fix"])
        for mode in ("fail", "unsealed", "other_argv"):
            with self.subTest(mode=mode):
                os.environ["FAKE_SCPROFILE_MODE"] = mode
                rc, r = self.mount(block())
                self.assertNotEqual(r["status"], "mounted", r)
                self.assertEqual(self.view()["digest"], before["digest"])
        os.environ["FAKE_SCPROFILE_MODE"] = "ok"
        os.environ["FAKE_SCPROFILE_STATE_VERSION"] = "2"
        rc, r = self.mount(block())
        self.assertEqual(r["status"], "refused", r)
        self.assertIn("state_version 2", r["reason"])

    def test_a_plugin_scprofiles_plan_skipped_is_named_never_hidden_and_doctor_is_a_record(self):
        os.environ["FAKE_SCPROFILE_MODE"] = "skip"
        self.init(self.manifest, *self.CONTEXT, design=self.design)
        rc, r = self.mount(block())
        self.assertEqual(r["status"], "mounted", r)
        out = self.out_json()
        self.assertEqual((out["answer"]["ran"], out["numbers"]["n_plugins_skipped"]), (["de"], 1))
        self.assertTrue(any("did not run abundance: the design admits no contrast" in c for c in out["caveats"]),
                        out["caveats"])
        os.environ["FAKE_SCPROFILE_MODE"] = "doctor_fail"
        cli("--json", "unmount", "--stack", str(self.stack), "prof@scprofile")
        rc, r = self.mount(block())
        self.assertEqual(r["status"], "mounted", r)
        self.assertEqual(self.out_json()["answer"]["stage_record"]["doctor"]["exit"], 1)


@unittest.skipUnless(HAVE_H5PY, "h5py is not available in this interpreter")
class TheCompanion(unittest.TestCase):
    """The companion on its own, from the facts the kernel hands it."""

    def check(self, n_ids, n_rows, masked=()):
        import numpy as np
        d = Path(tempfile.mkdtemp(prefix="sch-scprof-inv-"))
        try:
            (d / "embeddings").mkdir()
            np.save(d / "embeddings" / "X.npy", np.zeros((n_rows, 2)))
            (d / "embeddings" / "barcodes.txt").write_text("".join(f"p|c{i}\n" for i in range(n_ids)))
            facts = {"plugin": "prof@scprofile", "out_dir": str(d), "out": {}, "masked": list(masked),
                     "observations": 5, "identity": "barcode",
                     "contributions": [{"slot": "embedding", "name": "X", "coverage": 0,
                                        "path": str(d / "embeddings" / "X.npy")}]}
            (d / "facts.json").write_text(json.dumps(facts))
            env = dict(os.environ, SCH_PROTOCOL=str(ROOT / "sch" / "plugin" / "protocol.py"))
            p = subprocess.run([sys.executable, str(PLUGIN / "invariant.py"), str(d / "facts.json"),
                                str(d / "result.json")], capture_output=True, text=True, env=env)
            return p.returncode, json.loads((d / "result.json").read_text())
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_a_layer_over_every_observation_holds_and_one_short_or_a_mask_fails(self):
        rc, res = self.check(5, 5)
        self.assertEqual((rc, res["failed"]), (0, []), res)
        rc, res = self.check(4, 4)
        self.assertEqual(rc, 1, res)
        self.assertIn("cover other than the stack's 5", res["failed"][0]["message"])
        rc, res = self.check(5, 4)
        self.assertEqual(rc, 1, res)
        rc, res = self.check(5, 5, masked=["p|c1"])
        self.assertEqual(rc, 1, res)
        self.assertIn("set aside 1 observation", res["failed"][0]["message"])


def _real_scprofile():
    """The checkout `SCH_TEST_SCPROFILE` names, when this interpreter can run its de and abundance."""
    c = os.environ.get("SCH_TEST_SCPROFILE")
    if not c or not (Path(c) / "scprofile" / "cli.py").is_file():
        return None
    for mod in ("anndata", "pydeseq2", "pertpy", "h5py"):
        if importlib.util.find_spec(mod) is None:
            return None
    return Path(c)


@unittest.skipUnless(_real_scprofile(), "SCH_TEST_SCPROFILE unset, or this interpreter lacks scProfile's "
                                        "plugins' packages")
class TheRealScprofile(_Base):
    """The harness's own synthetic fixture through the REAL scProfile, mounted and alone, compared."""

    def test_the_synthetic_fixture_through_the_real_scprofile_equals_scprofile_alone(self):
        checkout = _real_scprofile()
        fx = self.tmp / "fx"
        rc, out = cli("dev", "fixture", str(fx), "--shape", "a", "--cells", "1500", "--root", str(ROOT))
        self.assertEqual(rc, 0, out)
        meta = json.loads((fx / "FIXTURE_a.json").read_text())
        roles = meta["roles"]
        manifest = self.tmp / "integrated.tsv"
        manifest.write_text(f"part\th5ad\nfixture\t{meta['observations']}\n")
        for p in (manifest, Path(meta["observations"]), Path(meta["design"])):
            p.chmod(0o444)
        env = {f"SCPROFILE_{k}_PYTHON": sys.executable for k in ("DE", "ABUNDANCE")}
        os.environ.update(env)
        try:
            run_ = {"kernel": "de,abundance", "label_key": roles["cell_type"], "sample_key": roles["sample"],
                    "batch_key": roles["batch"], "counts_layer": roles["counts"], "lognorm_layer": "lognorm",
                    "embedding": "X_pca", "factor": [roles["condition"]],
                    "control": [f"{roles['condition']}={meta['declared']['control']}"], "no_cache": True,
                    "timeout": 1200}
            self.init(manifest, "--context", "assay=scrna", "--context", "organism=human",
                      design=Path(meta["design"]))
            before = self.view()
            rc, r = self.mount(run_, checkout=str(checkout))
            self.assertEqual(r["status"], "mounted", r)
            mine = self.run_dir / "scprofile"
            argv = json.loads((mine / "STATUS.json").read_text())["argv"]
            alone = self.tmp / "alone"
            (alone / "logs").mkdir(parents=True)
            subprocess.run([sys.executable, "-m", "scprofile.cli", *argv[1:argv.index("--out") + 1],
                            str(alone), *argv[argv.index("--out") + 2:]], cwd=str(alone),
                           env=dict(os.environ, PYTHONPATH=str(checkout)), check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for t in ("kernels/de/tables/de_by_population.csv",
                      "kernels/abundance/tables/abundance_by_population.csv",
                      "kernels/abundance/tables/abundance_counts.csv"):
                with self.subTest(table=t):
                    self.assertEqual((mine / t).read_bytes(), (alone / t).read_bytes())
            self.assertEqual(self.view()["digest"], before["digest"])
        finally:
            for k in env:
                os.environ.pop(k, None)


if __name__ == "__main__":
    unittest.main()
