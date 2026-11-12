"""One object holding every library becomes the parts the stages read (harness W045, ROUTE R43, GAP-C90).

Public atlases deliver a cohort as ONE object: every library in one file, the counts in `raw/X` beside
a normalized `X`, stable gene ids as var_names and the symbols in a column, and libraries that each
pool several donors - of both arms. The family's first stage reads libraries. What must hold, each
asserted against the files and the tools' argv, never the driver's account:
  - a request declares the object's counts slot, symbol column, library column (keys.sample) and
    replicate column (keys.replicate) by name, and what the object does not hold is refused by name
    before any tool starts;
  - through `sch run --request`, stage 00 writes one read-only part per library whose counts equal
    the object's, cell for cell and gene for gene, and the samplesheet that qc@scqc then mounts;
    the chunk size changes no byte of a part;
  - a counts slot that is not integers is refused at the step, and no part is kept;
  - duplicate symbols follow the stated rule, and a collision is refused;
  - the replicate, not the library, is the unit of the design downstream: qc's differential gate
    reads both arms inside one pooled library, scProfile's --sample-key is the replicate, and a tool
    that keys the design on the library is refused before any tool runs.
The synthetic object is written here with h5py alone, independently of the step's own writer.
"""
import csv
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from helpers import FIXTURES, HAVE_H5PY, release_tree
from sch import yamlish
from sch.cli import main

ROOT = Path(__file__).resolve().parent.parent
STEP = ROOT / "plugins" / "single-cell" / "parts" / "run.py"
LOGS = ("FAKE_SCQC_LOG", "FAKE_SCANNO_LOG", "FAKE_SCINTEGRATE_LOG", "FAKE_SCPROFILE_LOG")
ANSWERS = ["--answer", "qc.mode=apply", "--answer", "qc.decisions=null", "--by", "tester"]
N_LIB, N_DONOR = 6, 9


def cli(*argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(list(argv))
    return rc, buf.getvalue()


def step_module():
    spec = importlib.util.spec_from_file_location("sch_parts_step", str(STEP))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _strings(g, name, vals):
    import h5py
    d = g.create_dataset(name, data=[str(v) for v in vals], dtype=h5py.string_dtype("utf-8"))
    d.attrs.update({"encoding-type": "string-array", "encoding-version": "0.2.0"})


def _nullable(g, name, vals):
    """Strings as anndata 0.11 onwards writes pandas 3's default string dtype: a `nullable-string-array` group."""
    import h5py
    import numpy as np
    s = g.create_group(name)
    s.attrs.update({"encoding-type": "nullable-string-array", "encoding-version": "0.1.0"})
    s.create_dataset("values", data=[str(v) for v in vals], dtype=h5py.string_dtype("utf-8"))
    s.create_dataset("mask", data=np.array([v is None for v in vals], dtype=bool))


def _frame(g, index, cats, nullable=False):
    """`nullable`: the index and every column as anndata 0.13 with pandas 3 writes them by default (W056 fix 1,
    ATTACKS 49): nullable-string-array groups, not string-array datasets and categoricals."""
    import numpy as np
    g.attrs.update({"encoding-type": "dataframe", "encoding-version": "0.2.0", "_index": "_index",
                    "column-order": list(cats)})
    if nullable:
        _nullable(g, "_index", index)
        for name, vals in cats.items():
            _nullable(g, name, vals)
        return
    _strings(g, "_index", index)
    for name, vals in cats.items():
        levels = sorted(set(vals))
        c = g.create_group(name)
        c.attrs.update({"encoding-type": "categorical", "encoding-version": "0.2.0", "ordered": False})
        c.create_dataset("codes", data=np.array([levels.index(v) for v in vals], dtype=np.int8))
        _strings(c, "categories", levels)


def _csr(g, m, kind="csr_matrix"):
    g.attrs.update({"encoding-type": kind, "encoding-version": "0.1.0", "shape": list(m.shape)})
    for k in ("data", "indices", "indptr"):
        g.create_dataset(k, data=getattr(m, k))


def atlas(dest: Path, cells: int = 240, genes: int = 40, seed: int = 7, nullable: bool = False, libs=None) -> dict:
    """A published object of the scale cohort's SHAPE (no value of it): every library pools three
    donors of both arms, each donor in several libraries; cells interleaved across libraries; ids as
    var_names, the symbols (two of them shared by two genes) in raw/var; integer counts in raw/X and
    a normalized X; one CSC layer. Read-only, as delivered."""
    import h5py
    import numpy as np
    import scipy.sparse as sp
    rng = np.random.default_rng(seed)
    libs = list(libs or [f"lib{i + 1}" for i in range(N_LIB)])
    pool = {lib: [f"d{(i + k) % N_DONOR + 1}" for k in range(3)] for i, lib in enumerate(libs)}
    arm = {f"d{j + 1}": ("arm_a" if j % 2 == 0 else "arm_b") for j in range(N_DONOR)}
    lib_of = [libs[int(x)] for x in rng.integers(0, N_LIB, cells)]
    donor_of = [pool[lb][int(rng.integers(0, 3))] for lb in lib_of]
    ids = [f"GID{j:05d}" for j in range(genes)]
    symbols = ["MT-ND1", "MT-CO1", "MT-CYB"] + [f"SYM{j}" for j in range(3, genes)]
    symbols[11], symbols[30] = symbols[10], symbols[20]          # two symbols, each shared by two genes
    dense = rng.poisson(1.2, (cells, genes)) * (rng.random((cells, genes)) < 0.35)
    counts = sp.csr_matrix(dense.astype(np.float32))
    norm = counts.multiply(1e4 / np.maximum(counts.sum(1), 1)).tocsr()
    norm.data = np.log1p(norm.data).astype(np.float32)
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / "atlas.h5ad"
    barcodes = [f"BC{n:05d}-1-{lb}" for n, lb in enumerate(lib_of)]
    with h5py.File(path, "w") as f:
        f.attrs.update({"encoding-type": "anndata", "encoding-version": "0.1.0"})
        _csr(f.create_group("X"), norm)
        _frame(f.create_group("obs"), barcodes, {"library": lib_of, "donor": donor_of,
                                                 "arm": [arm[d] for d in donor_of],
                                                 "cell_type": [f"t{n % 3}" for n in range(cells)]}, nullable)
        _frame(f.create_group("var"), ids, {"symbol": symbols}, nullable)
        raw = f.create_group("raw")
        raw.attrs.update({"encoding-type": "raw", "encoding-version": "0.1.0"})
        _csr(raw.create_group("X"), counts)
        _frame(raw.create_group("var"), ids, {"symbol": symbols}, nullable)
        layers = f.create_group("layers")
        layers.attrs.update({"encoding-type": "dict", "encoding-version": "0.1.0"})
        _csr(layers.create_group("by_gene"), counts.tocsc(), "csc_matrix")
    path.chmod(0o444)
    (dest / "design.csv").write_text("donor,arm\n" + "".join(f"{d},{a}\n" for d, a in arm.items()))
    (dest / "registry.tsv").write_text("species\tbuild\tpath\nspecies_x\tref_1\treferences/species_x/ref_1\n")
    return {"dir": dest, "path": path, "counts": counts, "norm": norm, "barcodes": barcodes, "ids": ids,
            "symbols": symbols, "lib_of": lib_of, "donor_of": donor_of, "arm": arm, "pool": pool}


def qc_stage(a: dict) -> dict:
    return {"plugin": "qc@scqc", "params": {"scqc": str(FIXTURES / "fake_scqc.py"),
                                            "registry": str(a["dir"] / "registry.tsv"), "executor": "local",
                                            "allow_local": True, "dbr": 0.06, "seed": 0}}


def request(a: dict, name="request.yml", **over) -> Path:
    doc = {"request": 1, "observations": "atlas.h5ad", "parts": "matrix",
           "object": {"counts": "raw/X", "symbols": "symbol", "carry": ["arm", "cell_type"]},
           "keys": {"sample": "library", "replicate": "donor"}, "design": "design.csv",
           "context": {"assay": "scrna", "species": "species_x", "tissue": "tissue_x"},
           "upstream": {"alignment": {"tool": "aligner_x", "version": "1"}, "ambient": {"tool": "none"}},
           "stages": [qc_stage(a)]}
    for k, v in over.items():
        if v is None:
            doc.pop(k, None)
        else:
            doc[k] = v
    p = a["dir"] / name
    yamlish.dump(doc, p)
    return p


def read_part(path: Path) -> dict:
    import h5py
    import scipy.sparse as sp
    with h5py.File(path, "r") as f:
        x = f["X"]
        m = sp.csr_matrix((x["data"][()], x["indices"][()], x["indptr"][()]), shape=tuple(x.attrs["shape"]))
        dec = (lambda v: [b.decode() if isinstance(b, bytes) else str(b) for b in v])

        def cat(g, name):
            cats = dec(g[name]["categories"][()])
            return [cats[c] for c in g[name]["codes"][()]]
        return {"X": m, "dtype": x["data"].dtype, "obs": dec(f["obs/_index"][()]),
                "var": dec(f["var/_index"][()]), "gene_ids": dec(f["var/gene_ids"][()]),
                "donor": cat(f["obs"], "donor"), "arm": cat(f["obs"], "arm"),
                "library": cat(f["obs"], "library")}


@unittest.skipUnless(HAVE_H5PY, "h5py is not available in this interpreter")
class _Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sch-parts-"))
        self._env = {k: os.environ.get(k) for k in LOGS + ("FAKE_SCQC_MODE",)}
        os.environ.pop("FAKE_SCQC_MODE", None)
        for k in LOGS:
            os.environ[k] = str(self.tmp / f"{k.lower()}.jsonl")
        self.a = atlas(self.tmp / "c")

    def tearDown(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        release_tree(self.tmp)                   # never follows a link (W056 fix 1)

    def calls(self) -> list:
        out = []
        for k in LOGS:
            f = Path(os.environ[k])
            if f.exists():
                out += [(k, json.loads(x)["argv"]) for x in f.read_text().splitlines()]
        return out

    def drive(self, req, out, *extra):
        rc, text = cli("--json", "run", "--request", str(req), "--out", str(out), *extra)
        return rc, json.loads(text)


class OneObjectBecomesParts(_Base):
    def test_through_the_driver_the_parts_equal_the_object_and_qc_mounts_their_samplesheet(self):
        a, out = self.a, self.tmp / "run"
        rc, rec = self.drive(request(a), out, *ANSWERS)
        self.assertEqual((rc, rec["status"]), (0, "sealed"), rec)
        self.assertEqual(rec["sealed"], ["00_parts", "01_qc"])
        seal = json.loads((out / "00_parts" / "SEALED.json").read_text())
        libs = seal["hands_on"]["libraries"]
        self.assertEqual(sorted(libs), sorted(set(a["lib_of"])))
        # every part: the object's rows for its library, cell for cell and gene for gene, exactly
        seen = []
        for lib, path in libs.items():
            p = read_part(Path(path))
            self.assertEqual(Path(path).stat().st_mode & 0o777, 0o444, path)
            rows = [n for n, lb in enumerate(a["lib_of"]) if lb == lib]
            self.assertEqual(p["obs"], [a["barcodes"][n] for n in rows])        # the object's order
            self.assertEqual(p["gene_ids"], a["ids"])                              # gene for gene
            self.assertEqual(str(p["dtype"]), "float32")                           # the slot's dtype
            self.assertEqual((p["X"] != a["counts"][rows]).nnz, 0, lib)            # cell for cell
            self.assertEqual(p["library"], [lib] * len(rows))
            self.assertEqual(p["donor"], [a["donor_of"][n] for n in rows])
            self.assertEqual(p["arm"], [a["arm"][a["donor_of"][n]] for n in rows])
            self.assertEqual(len(set(p["arm"])), 2, f"{lib} pools both arms")
            self.assertEqual(p["var"][:3], ["MT-ND1", "MT-CO1", "MT-CYB"])
            self.assertEqual((p["var"][10], p["var"][11], p["var"][20], p["var"][30]),
                             ("SYM10", "SYM10-1", "SYM20", "SYM20-1"))
            seen += p["obs"]
        self.assertEqual(sorted(seen), sorted(a["barcodes"]))
        # the record repeats the rule and each name it wrote; the step's cost is a stage's
        run_out = Path(libs[sorted(libs)[0]]).parent.parent
        parts = json.loads((run_out / "PARTS.json").read_text())
        self.assertIn("SYMBOL-k", parts["duplicates_rule"])
        self.assertEqual([d["written"] for d in parts["duplicates"]], ["SYM10-1", "SYM20-1"])
        self.assertEqual((parts["n_obs"], parts["n_libraries"], parts["n_replicates"]), (240, N_LIB, len(set(a["donor_of"]))))
        self.assertEqual(parts["libraries_holding_several_replicates"], N_LIB)
        self.assertGreater(parts["peak_rss_kb"], 0)
        report = json.loads((out / "00_parts" / "report" / "report.json").read_text())
        self.assertEqual(report["cost"]["cells"]["value"], 240)
        self.assertGreater(report["cost"]["wall_s"]["value"], 0)
        # the samplesheet qc@scqc mounted: scQC's columns, every context axis, the parts in place
        sheet = Path(seal["hands_on"]["samplesheet"])
        with open(sheet, newline="") as fh:
            rows = list(csv.DictReader(fh, delimiter="\t"))
        self.assertEqual(list(rows[0]), ["sample", "library", "matrix", "assay", "species", "tissue"])
        self.assertEqual({r["sample"]: r["matrix"] for r in rows}, libs)
        qc_decl = yamlish.load(out / "01_qc" / "stack.yml")
        self.assertEqual(qc_decl["observations"], str(sheet))
        scqc_run = [x for k, x in self.calls() if k == "FAKE_SCQC_LOG" and x[0] == "run"][0]
        self.assertEqual(scqc_run[scqc_run.index("--samplesheet") + 1], str(sheet))
        # qc's required differential gate joined each cell's arm through its donor: two arms measured
        probe = [json.loads(p.read_text()) for p in (out / "01_qc").rglob("out.json")
                 if "unit" in json.dumps((json.loads(p.read_text()).get("answer") or {}))]
        self.assertTrue(probe, "the differential probe ran")
        ans = probe[0]["answer"]
        self.assertEqual((ans["unit"], ans["arms_known"], ans["unknown_arm"]), ("donor", True, 0))
        self.assertEqual(sorted(next(iter(ans["masks"].values()))["total"]), ["arm_a", "arm_b"])

    def test_the_chunk_size_changes_no_byte_of_a_part(self):
        import h5py
        mod, got = step_module(), {}
        params = {"library": "library", "replicate": "donor", "counts": "raw/X", "symbols": "symbol",
                  "carry": ["arm"], "column": "matrix"}
        for most in (7, 1 << 23):
            out = self.tmp / f"split-{most}"
            out.mkdir()
            rec = mod.split(self.a["path"], out, {**params, "chunk_values": most}, {"assay": "scrna"})
            got[most] = {lib: {k: h5py.File(out / p["path"], "r")["X"][k][()] for k in ("data", "indices", "indptr")}
                         for lib, p in rec["parts"].items()}
            got[most]["chunks"] = rec["chunks"]
        self.assertGreater(got[7]["chunks"], 50)
        self.assertEqual(got[1 << 23]["chunks"], 1)
        for lib in sorted(set(self.a["lib_of"])):
            for k in ("data", "indices", "indptr"):
                self.assertEqual(got[7][lib][k].tolist(), got[1 << 23][lib][k].tolist(), (lib, k))

    def test_duplicate_symbols_follow_the_stated_rule_and_a_collision_is_refused(self):
        mod = step_module()
        written, dups = mod.unique_symbols(["A", "B", "A", "A", "C"])
        self.assertEqual(written, ["A", "B", "A-1", "A-2", "C"])
        self.assertEqual(dups, [(2, "A", "A-1"), (3, "A", "A-2")])
        with self.assertRaises(mod.Refused) as e:
            mod.unique_symbols(["A", "A", "A-1"])
        self.assertIn("'A-1' is already another gene's symbol", e.exception.reason)
        with self.assertRaises(mod.Refused):
            mod.unique_symbols(["A", "", "B"])

    @unittest.skipUnless(importlib.util.find_spec("anndata"), "anndata is not in this interpreter")
    def test_a_part_reads_as_anndata_with_the_counts_in_x_and_symbols_as_var_names(self):
        import anndata as ad
        mod, out = step_module(), self.tmp / "split"
        out.mkdir()
        rec = mod.split(self.a["path"], out, {"library": "library", "replicate": "donor", "counts": "raw/X",
                                              "symbols": "symbol", "carry": ["arm"], "column": "matrix"},
                        {"assay": "scrna"})
        lib, p = sorted(rec["parts"].items())[0]
        part = ad.read_h5ad(out / p["path"])
        rows = [n for n, lb in enumerate(self.a["lib_of"]) if lb == lib]
        self.assertEqual(part.shape, (len(rows), 40))
        self.assertEqual((part.X != self.a["counts"][rows]).nnz, 0)
        self.assertEqual(list(part.var["gene_ids"]), self.a["ids"])
        self.assertTrue(part.var_names.is_unique)
        self.assertEqual(set(part.obs["arm"]), {"arm_a", "arm_b"})


PARAMS = {"library": "library", "replicate": "donor", "counts": "raw/X", "symbols": "symbol", "carry": ["arm"],
          "column": "matrix"}


def same_as_the_object(case, a, rec, out):
    """Every part is the object's rows for its library, cell for cell, in the object's order."""
    case.assertEqual(sorted(rec["parts"]), sorted(set(a["lib_of"])))
    for lib, p in rec["parts"].items():
        got = read_part(out / p["path"])
        rows = [n for n, lb in enumerate(a["lib_of"]) if lb == lib]
        case.assertEqual(got["obs"], [a["barcodes"][n] for n in rows], lib)
        case.assertEqual(got["gene_ids"], a["ids"], lib)
        case.assertEqual((got["X"] != a["counts"][rows]).nnz, 0, lib)
        case.assertEqual(got["donor"], [a["donor_of"][n] for n in rows], lib)


class TheFieldsCurrentEncodings(_Base):
    """W056 fix 1 (the verifier's R3, ATTACKS 49): an object written by the field's current library with its
    defaults (anndata 0.13 with pandas 3) stores its indexes and string columns as nullable-string-array
    groups; the step died on it with an AttributeError (the driver: "parts died: no out.json")."""

    def test_an_object_whose_indexes_and_strings_are_nullable_string_arrays_splits_through_the_driver(self):
        a, out = atlas(self.tmp / "n", nullable=True), self.tmp / "run"
        rc, rec = self.drive(request(a), out, *ANSWERS)
        self.assertEqual((rc, rec["status"]), (0, "sealed"), rec)
        mod, split = step_module(), self.tmp / "split"
        split.mkdir()
        same_as_the_object(self, a, mod.split(a["path"], split, PARAMS, {"assay": "scrna"}), split)

    def test_a_name_the_mask_marks_missing_is_refused_before_any_part(self):
        import h5py
        a = atlas(self.tmp / "m", nullable=True)
        a["path"].chmod(0o644)
        with h5py.File(a["path"], "r+") as f:
            m = f["obs/_index/mask"]
            m[3] = True
        mod, out = step_module(), self.tmp / "split"
        out.mkdir()
        with self.assertRaises(mod.Refused) as e:
            mod.split(a["path"], out, PARAMS, {"assay": "scrna"})
        self.assertIn("the object's obs's index names nothing at 1 position(s), the first at 3", e.exception.reason)
        self.assertFalse((out / "parts").exists())

    @unittest.skipUnless(importlib.util.find_spec("anndata"), "anndata is not in this interpreter")
    def test_every_input_shape_written_by_anndata_itself_with_its_defaults(self):
        """The object as the library writes it (`write_h5ad`, every default), beside the hand-written one: the
        counts in raw/X (a normalized X), in X, in a layer; the library a string column and a categorical."""
        import anndata as ad
        import h5py
        import pandas as pd
        a, mod = self.a, step_module()
        enc = {}
        for n, (lib_cat, counts) in enumerate([(False, "raw/X"), (True, "raw/X"), (False, "layers/counts"),
                                               (True, "X")]):
            with self.subTest(library_categorical=lib_cat, counts=counts):
                lib = pd.Categorical(a["lib_of"]) if lib_cat else list(a["lib_of"])
                obs = pd.DataFrame({"library": lib, "donor": list(a["donor_of"]),
                                    "arm": pd.Categorical([a["arm"][d] for d in a["donor_of"]])},
                                   index=list(a["barcodes"]))
                var = pd.DataFrame({"symbol": list(a["symbols"])}, index=list(a["ids"]))
                b = ad.AnnData(X=a["counts"].copy(), obs=obs, var=var)
                b.layers["counts"] = a["counts"].copy()
                b.raw = b
                if counts != "X":
                    b.X = a["norm"].copy()
                path = self.tmp / f"by_anndata_{n}.h5ad"
                b.write_h5ad(path)
                with h5py.File(path, "r") as f:
                    enc[n] = {k: f[k].attrs.get("encoding-type") for k in ("obs/_index", "obs/library", "var/_index",
                                                                            "raw/var/symbol")}
                out = self.tmp / f"split_{n}"
                out.mkdir()
                rec = mod.split(path, out, {**PARAMS, "counts": counts}, {"assay": "scrna"})
                same_as_the_object(self, a, rec, out)
        # what the library wrote, said: under pandas 3 the indexes are nullable-string-array groups
        print(f"\n    anndata {ad.__version__ if hasattr(ad, '__version__') else '?'}, pandas {pd.__version__}: {enc[0]}",
              file=sys.stderr)

    def test_a_library_no_file_can_be_named_after_or_two_one_by_case_are_refused_by_name_before_any_write(self):
        mod = step_module()
        long = "L" * 251
        for n, (libs, words) in enumerate([
                ([long, "lib2", "lib3", "lib4", "lib5", "lib6"], f"{long!r} (251 characters) cannot name a file"),
                (["Ab", "ab", "lib3", "lib4", "lib5", "lib6"], "library names 'Ab' and 'ab' differ only by case")]):
            with self.subTest(words=words[:40]):
                a, out = atlas(self.tmp / f"x{n}", libs=libs), self.tmp / f"split{n}"
                out.mkdir()
                with self.assertRaises(mod.Refused) as e:
                    mod.split(a["path"], out, PARAMS, {"assay": "scrna"})
                self.assertIn(words, e.exception.reason)
                self.assertEqual(list(out.iterdir()), [], "nothing written")
        a, out = atlas(self.tmp / "ok", libs=["L" * 250] + [f"lib{i}" for i in range(2, N_LIB + 1)]), self.tmp / "ok_split"
        out.mkdir()
        self.assertIn("L" * 250, mod.split(a["path"], out, PARAMS, {"assay": "scrna"})["parts"])


class WhatTheObjectDoesNotHoldIsRefused(_Base):
    def test_each_missing_or_wrong_declaration_is_refused_by_name_before_any_tool(self):
        a = self.a
        obj = {"counts": "raw/X", "symbols": "symbol", "carry": ["arm"]}
        cases = [({"keys": {"sample": "library"}}, "declares no `replicate`"),
                 ({"object": {**obj, "counts": "layers/none"}}, "holds no slot 'layers/none'"),
                 ({"object": {**obj, "counts": "layers/by_gene"}}, "'layers/by_gene' is csc_matrix"),
                 ({"object": {**obj, "symbols": "gene_symbol"}}, "raw/var has no column 'gene_symbol'"),
                 ({"object": {**obj, "carry": ["batch"]}}, "obs has no column 'batch'"),
                 ({"keys": {"sample": "library", "replicate": "subject"}}, "obs has no column 'subject'"),
                 ({"object": {"counts": "raw/X"}}, "declares no symbols"),
                 ({"object": {**obj, "count": "raw/X"}}, "count is not an object field"),
                 ({"object": None}, "atlas.h5ad is one object"),
                 ({"parts": "sample"}, "parts: 'sample' is a column the parts step's samplesheet")]
        for n, (over, words) in enumerate(cases):
            with self.subTest(words=words):
                rc, rec = self.drive(request(a, name=f"r{n}.yml", **over), self.tmp / f"run{n}", *ANSWERS)
                self.assertEqual((rc, rec["status"]), (2, "refused"), rec)
                self.assertIn(words, rec["reason"])
        self.assertEqual(self.calls(), [], "no tool started")

    def test_a_counts_slot_that_is_not_integers_is_refused_at_the_step_and_no_part_is_kept(self):
        a, out = self.a, self.tmp / "run"
        rc, rec = self.drive(request(a, object={"counts": "X", "symbols": "symbol"}), out, *ANSWERS)
        self.assertEqual((rc, rec["status"], rec["stage"]), (2, "failed", "00_parts"), rec)
        self.assertIn("not a non-negative integer", rec["reason"])
        self.assertIn("for observation 'BC", rec["reason"])
        self.assertEqual(list((out / "00_parts").rglob("*.h5ad")), [], "no part is kept")
        self.assertEqual(self.calls(), [], "no tool started")


class TheReplicateIsTheDesignsUnit(_Base):
    def stages(self, design=True):
        integ = {"batch_key": "sample", "label_key": "cell_type", "methods": "none"}
        if design:
            integ["design"] = str(self.a["dir"] / "design.csv")
        return [qc_stage(self.a),
                {"plugin": "anno@scanno", "params": {"scanno": str(FIXTURES / "fake_scanno.py"),
                                                     "embed": {"label_obs": ["scanno_cell_type=cell_type"]}}},
                {"plugin": "int@scintegrate", "params": {"scintegrate": str(FIXTURES / "fake_scintegrate"),
                                                         "integrate": integ}},
                {"plugin": "prof@scprofile", "params": {"scprofile": str(FIXTURES / "fake_scprofile"),
                                                        "run": {"kernel": "de", "label_key": "cell_type"}}}]

    def test_pooled_libraries_from_a_samplesheet_gate_qc_through_each_cells_replicate(self):
        """No object, no step: libraries delivered one file each, every one pooling donors of both
        arms, the design keyed on the donor. Before W045 qc's required gate joined the arm by the
        library and died on such a design (the probe's KeyError, the gate's REFUSE)."""
        import h5py
        a, d = self.a, self.a["dir"] / "libs"
        d.mkdir()
        rows = ["sample\tassay\tmatrix"]
        for lib in sorted(set(a["lib_of"])):
            idx = [n for n, lb in enumerate(a["lib_of"]) if lb == lib]
            p = d / f"{lib}.h5ad"
            with h5py.File(p, "w") as f:
                _frame(f.create_group("obs"), [a["barcodes"][n] for n in idx],
                       {"donor": [a["donor_of"][n] for n in idx]})
            p.chmod(0o444)
            rows.append(f"{lib}\tscrna\t{p}")
        (a["dir"] / "sheet.tsv").write_text("\n".join(rows) + "\n")
        (a["dir"] / "sheet.tsv").chmod(0o444)
        req = request(a, name="sheet.yml", observations="sheet.tsv", object=None,
                      keys={"sample": "sample", "replicate": "donor"})
        out = self.tmp / "run"
        rc, rec = self.drive(req, out, *ANSWERS)
        self.assertEqual((rc, rec["status"], rec["sealed"]), (0, "sealed", ["01_qc"]), rec)
        with open(next((out / "01_qc").rglob("view.csv")), newline="") as fh:
            self.assertEqual(next(csv.reader(fh))[:3], ["barcode", "sample", "donor"])
        probe = [json.loads(p.read_text())["answer"] for p in (out / "01_qc").rglob("out.json")
                 if '"unit"' in p.read_text()]
        self.assertEqual((probe[0]["unit"], probe[0]["arms_known"], probe[0]["unknown_arm"]), ("donor", True, 0))
        self.assertEqual(sorted(next(iter(probe[0]["masks"].values()))["total"]), ["arm_a", "arm_b"])

    def test_scprofile_takes_the_replicate_and_a_design_keyed_on_the_library_is_refused(self):
        a = self.a
        rc, rec = self.drive(request(a, name="pooled.yml", stages=self.stages()), self.tmp / "run", *ANSWERS)
        self.assertEqual((rc, rec["status"]), (2, "refused"), rec)
        self.assertIn("integrate.design is a design sheet scIntegrate keys on the library", rec["reason"])
        self.assertEqual(self.calls(), [], "no tool started")
        rc, text = cli("plan", "--request", str(request(a, name="ok.yml", stages=self.stages(design=False))))
        self.assertEqual(rc, 0, text)
        self.assertIn("the replicate column: keys.replicate=donor -> run.sample_key", text)
        self.assertIn("the library column: keys.sample=library -> embed.sample_key", text)
        self.assertIn("00_parts", text)
        self.assertIn("the object: counts raw/X, symbols symbol, carry arm, cell_type", text)


if __name__ == "__main__":
    unittest.main()


class TheObjectFollowsTheFixedDriver(_Base):
    """W056: W045's step on the driver as its three fix rounds left it."""

    def test_the_samplesheet_stage_00_hands_on_is_pinned_by_its_seal_and_an_edit_is_refused_at_the_resume(self):
        # W049 fix 1: what a sealed stage handed on hashes as it did when it was sealed. The parts' samplesheet
        # is the next stage's input, so it is among what stage 00's seal hashes (ATTACKS 8 and 21: the same
        # check, another file a stage hands on)
        a = atlas(self.tmp / "a")
        req, out = request(a), self.tmp / "run"
        rc, rec = self.drive(req, out)
        self.assertEqual((rc, rec["status"], rec["stage"]), (3, "waiting", "01_qc"), rec)
        seal = json.loads((out / "00_parts" / "SEALED.json").read_text())
        sheet = Path(seal["hands_on"]["samplesheet"])
        self.assertIn(str(sheet), seal["handed_sha256"])
        kept = sheet.read_bytes()
        sheet.chmod(0o644)
        sheet.write_bytes(kept + b"\n")
        rc, rec = self.drive(req, out, *ANSWERS)
        self.assertEqual(rc, 2, rec)
        self.assertIn(str(sheet), rec["reason"])
        self.assertFalse([k for k, _a in self.calls() if k == "FAKE_SCQC_LOG"], "stage 1 never read the edited sheet")
        sheet.write_bytes(kept)
        sheet.chmod(0o444)                       # restored as it was handed on: read-only (E2)
        rc, rec = self.drive(req, out, *ANSWERS)
        self.assertEqual((rc, rec["status"]), (0, "sealed"), rec)
