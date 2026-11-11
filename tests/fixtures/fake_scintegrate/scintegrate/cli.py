"""A stand-in for scIntegrate's CLI (`python -m scintegrate.cli`), for tests that drive
`int@scintegrate` through `sch` without scanpy, anndata or any integration method.

It honours the parts of scIntegrate's contract the adapter relies on, and nothing more, as
`fake_scanno.py` stands in for scAnno:

    describe        the declaration, as JSON: `state_version`, and the assays `axes` accepts
    doctor          one line; exit 0
    integrate       parsed with the flags scIntegrate's own parser declares for it (0.5.0,
                    b148030), so a flag scIntegrate does not have fails here as it would there,
                    and `--lisi-subsample` stops at the parser with exit 2

`integrate` keeps scIntegrate's status contract in `--out`: `STATUS.json` written first as
`partial` with `sys.argv`, `RUNNING.txt`, then the outcome with its products and `SEALED.txt` or
`FAILED.txt`. Its object, `objects/<--object-name>`, is an `.h5ad` written with h5py in anndata's
on-disk encodings, made as scIntegrate makes its own:
  - obs: the batch, label and l1 columns, the colour columns and every design column, COPIED from
    the input node by node (so they are the input's own), a design column the input lacks joined
    on by the batch value; every other obs column left out (scIntegrate's slim);
  - obsm: the input's PCA copied (scIntegrate keeps it as the uncorrected baseline); one
    embedding per method that has one (NaN rows for cells `--drop-labels` withholds); a 2-D view
    per method; and the chosen method's view again under the input's 2-D key, so that entry is a
    rewrite when the input carries one;
  - obsp: a graph method's two graphs, when one is among `--methods`.

What it computes is a fixed pattern of the input's numbers, never an integration: a test using it
checks the harness around scIntegrate, never scIntegrate. The obsm keys it writes are scIntegrate's
names; they live here, in a test fixture, and nowhere in the adapter.

Environment:
    FAKE_SCINTEGRATE_LOG              append {"argv", "argv0", "cwd", "pythonpath"} per call
    FAKE_SCINTEGRATE_MODE             ok (default) | refuse | fail | unsealed | short | other_argv |
                                      reversed (rows written last first) | relabel (l1 rewritten)
    FAKE_SCINTEGRATE_STATE_VERSION    what `describe` and STATUS report (default 1)
"""
import argparse
import csv
import json
import os
import socket
import sys
import time
from pathlib import Path

MODE = os.environ.get("FAKE_SCINTEGRATE_MODE", "ok")
STATE_VERSION = int(os.environ.get("FAKE_SCINTEGRATE_STATE_VERSION", "1"))
VERSION, COMMIT = "0.0.0-fake", "e" * 40
ASSAYS = ("scrna", "snrna")
GRAPH_METHODS = ("bbknn",)
PCA, VIEW = "X_pca", "X_umap"


def log_call():
    path = os.environ.get("FAKE_SCINTEGRATE_LOG")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"argv": sys.argv[1:], "argv0": sys.argv[0], "cwd": os.getcwd(),
                                 "pythonpath": os.environ.get("PYTHONPATH")}) + "\n")


# ---------------------------------------------------------------------------- an .h5ad, with h5py
def write_object(path, index, obs, obsm=None, obsp=None, copy_from=None):
    """An .h5ad holding obs (`{name: (kind, values)}`, kind cat|str|int|float, or a node of
    `copy_from` to copy as it is), obsm (`{key: array}`) and obsp (`{key: (data, indices, indptr,
    shape)}`, compressed sparse rows)."""
    import h5py
    import numpy as np
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    vlen = h5py.string_dtype()
    with h5py.File(path, "w") as f:
        f.attrs["encoding-type"], f.attrs["encoding-version"] = "anndata", "0.1.0"
        g = f.create_group("obs")
        g.attrs["encoding-type"], g.attrs["encoding-version"] = "dataframe", "0.2.0"
        g.attrs["_index"] = "_index"
        g.attrs["column-order"] = list(obs)
        d = g.create_dataset("_index", data=np.array(index, dtype=object), dtype=vlen)
        d.attrs["encoding-type"], d.attrs["encoding-version"] = "string-array", "0.2.0"
        for name, spec in obs.items():
            if spec[0] == "copy":
                spec[1].file.copy(spec[1], g, name=name)
                continue
            kind, vals = spec
            if kind == "cat":
                cats = sorted({v for v in vals if v is not None})
                c = g.create_group(name)
                c.attrs["encoding-type"], c.attrs["encoding-version"] = "categorical", "0.2.0"
                c.attrs["ordered"] = False
                cs = c.create_dataset("categories", data=np.array(cats, dtype=object), dtype=vlen)
                cs.attrs["encoding-type"], cs.attrs["encoding-version"] = "string-array", "0.2.0"
                c.create_dataset("codes", data=np.array(
                    [cats.index(v) if v is not None else -1 for v in vals], dtype="int8"))
            elif kind == "str":
                s = g.create_dataset(name, data=np.array(vals, dtype=object), dtype=vlen)
                s.attrs["encoding-type"], s.attrs["encoding-version"] = "string-array", "0.2.0"
            else:
                s = g.create_dataset(name, data=np.array(vals, dtype={"int": "int64", "float": "float64"}[kind]))
                s.attrs["encoding-type"], s.attrs["encoding-version"] = "array", "0.2.0"
        m = f.create_group("obsm")
        for key, arr in (obsm or {}).items():
            s = m.create_dataset(key, data=arr)
            s.attrs["encoding-type"], s.attrs["encoding-version"] = "array", "0.2.0"
        p = f.create_group("obsp")
        for key, (data, indices, indptr, shape) in (obsp or {}).items():
            c = p.create_group(key)
            c.attrs["encoding-type"], c.attrs["encoding-version"] = "csr_matrix", "0.1.0"
            c.attrs["shape"] = list(shape)
            c.create_dataset("data", data=data)
            c.create_dataset("indices", data=indices)
            c.create_dataset("indptr", data=indptr)
        f.create_group("uns")


def ring(n, step=1, scale=1.0):
    """A graph over n observations, each joined to the next `step` along: as compressed rows."""
    import numpy as np
    indices = np.array([(i + step) % n for i in range(n)], dtype="int32")
    return (np.full(n, scale, dtype="float32"), indices, np.arange(n + 1, dtype="int32"), (n, n))


def permuted(graph, perm):
    """The same graph with rows and columns renumbered by `perm` (old position -> new)."""
    import numpy as np
    data, indices, indptr, shape = graph
    rows = perm[np.repeat(np.arange(len(indptr) - 1), np.diff(indptr))]
    cols = perm[indices]
    order = np.lexsort((cols, rows))
    counts = np.bincount(rows, minlength=shape[0])
    return (data[order], cols[order].astype(indices.dtype),
            np.concatenate([[0], np.cumsum(counts)]).astype(indptr.dtype), shape)


def _strings(raw):
    return [x.decode() if isinstance(x, bytes) else str(x) for x in raw]


def _column_text(node):
    import h5py
    if isinstance(node, h5py.Group):
        cats = _strings(node["categories"][()])
        return [cats[k] if k >= 0 else None for k in node["codes"][()]]
    return _strings(node[()])


# ---------------------------------------------------------------------------- the status contract
def _products(out):
    res = []
    for sub in ("", "tables", "objects", "figures", "reports"):
        d = out / sub if sub else out
        if d.is_dir():
            for p in sorted(d.iterdir()):
                if p.is_file() and p.suffix in (".json", ".csv", ".html", ".h5ad", ".md", ".png", ".pdf"):
                    res.append({"path": str(p.relative_to(out)), "bytes": p.stat().st_size})
    return res


def _begin(out, cmd):
    out.mkdir(parents=True, exist_ok=True)
    argv = list(sys.argv)
    if MODE == "other_argv":
        argv = argv[:1] + ["integrate", "--h5ad", "someone_else.h5ad"]
    rec = {"contract": "1.0", "tool": "scintegrate", "command": cmd, "version": VERSION,
           "commit": COMMIT, "state_version": STATE_VERSION, "status": "partial",
           "headline": "started", "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "argv": argv, "products": [], "refusal": None}
    (out / "STATUS.json").write_text(json.dumps(rec, indent=1) + "\n")
    (out / "RUNNING.txt").write_text("started\n")
    return rec


def _finish(out, rec, status, rc, headline, refusal=None, seal=True):
    rec.update({"status": status, "headline": headline, "exit": rc, "refusal": refusal,
                "products": _products(out),
                "finished": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    (out / "STATUS.json").write_text(json.dumps(rec, indent=1) + "\n")
    if seal:
        name = "SEALED.txt" if status == "ok" and rc == 0 else "FAILED.txt"
        (out / name).write_text(f"exit={rc}\nstatus={status}\nhost={socket.gethostname()}\n")
        (out / "RUNNING.txt").unlink()
    return rc


# ---------------------------------------------------------------------------- integrate
def integrate(a):
    import h5py
    import numpy as np
    out = Path(a.out)
    rec = _begin(out, "integrate")
    if MODE == "refuse":
        return _finish(out, rec, "refused", 2, "refused: the declared species is contradicted",
                       refusal={"reason": f"--species {a.species} is contradicted by the object's gene "
                                          f"identifiers", "fix": "declare the species the cells came from"})
    if MODE == "fail":
        return _finish(out, rec, "failed", 1, "RuntimeError: a method failed")
    design = {}
    if a.design:
        with open(a.design, newline="", encoding="utf-8-sig") as fh:
            rows = list(csv.DictReader(fh))
        key = a.design_sample_col or (list(rows[0]) if rows else [""])[0]
        design = {r[key]: r for r in rows}
        dcols = [c for c in (list(rows[0]) if rows else []) if c != key]
    else:
        dcols = []
    methods = ["none"] + [m for m in (a.methods or "").split(",") if m.strip() and m != "none"]
    with h5py.File(a.h5ad, "r") as f:
        g = f["obs"]
        key = g.attrs.get("_index", "_index")
        index = _strings(g[key.decode() if isinstance(key, bytes) else key][()])
        batch = _column_text(g[a.batch_key])
        labels = _column_text(g[a.label_key])
        keep = list(dict.fromkeys([a.batch_key, a.label_key] + ([a.l1_key] if a.l1_key else [])
                                  + [c for c in (a.colour_by or "").split(",") if c.strip()]))
        obs = {c: ("copy", g[c]) for c in keep}
        for c in dcols:
            obs[c] = ("copy", g[c]) if c in g else ("str", [design[b][c] for b in batch])
        pca = np.asarray(f["obsm"][PCA][()], dtype="float32")
        n = len(index)
        drop = np.isin(np.array(labels, dtype=object), [x for x in (a.drop_labels or "").split(",") if x])
        emb = {}
        for m in methods:
            if m in GRAPH_METHODS:
                continue
            e = pca + (0.0 if m == "none" else 0.5 + methods.index(m))
            e[drop] = np.nan
            emb[f"X_{m}"] = e.astype("float32")
        obsm = {PCA: pca, **emb}
        for m in methods:
            base = emb.get(f"X_{m}", pca * 2)
            obsm[f"X_umap_{m}"] = np.ascontiguousarray(base[:, :2]).astype("float32")
        chosen = [m for m in methods if f"X_{m}" in emb][-1]
        obsm[VIEW] = obsm[f"X_umap_{chosen}"].copy()
        obsp = {}
        for m in methods:
            if m in GRAPH_METHODS:
                obsp[f"{m}_connectivities"] = ring(n, 2, 0.5)
                obsp[f"{m}_distances"] = ring(n, 3, 1.5)
        if MODE == "relabel":            # scIntegrate never does this; the stand-in rewrites l1
            obs[a.l1_key] = ("str", [str(v).upper() for v in _column_text(obs[a.l1_key][1])])
        if MODE == "reversed":           # the same rows, written last first
            perm = np.arange(n)[::-1].copy()            # old position -> new
            index = index[::-1]
            obs = {c: ("str", (_column_text(v[1]) if v[0] == "copy" else list(v[1]))[::-1])
                   for c, v in obs.items()}
            obsm = {k: np.ascontiguousarray(v[::-1]) for k, v in obsm.items()}
            obsp = {k: permuted(v, perm) for k, v in obsp.items()}
        if MODE == "short":
            index = index[1:]
            obs = {c: ("str", _column_text(v[1])[1:] if v[0] == "copy" else v[1][1:]) for c, v in obs.items()}
            obsm = {k: v[1:] for k, v in obsm.items()}
            obsp = {}
        name = a.object_name
        write_object(out / "objects" / name, index, obs, obsm, obsp)
    (out / "tables").mkdir(parents=True, exist_ok=True)
    (out / "tables" / "scib_aggregate.csv").write_text(
        "method,total\n" + "".join(f"{m},{0.5 + i / 100:.6f}\n" for i, m in enumerate(methods)))
    (out / "report.json").write_text(json.dumps({"version": VERSION, "command": "integrate",
                                                 "chosen": {"default": chosen}, "species": a.species,
                                                 "assay": a.assay, "methods": methods}, indent=1))
    if MODE == "unsealed":
        rec.update({"status": "ok", "products": _products(out)})
        (out / "STATUS.json").write_text(json.dumps(rec, indent=1) + "\n")
        return 0
    return _finish(out, rec, "ok", 0, "every method compared and the object written")


# ---------------------------------------------------------------------------- the parser (b148030's flags)
class _Removed(argparse.Action):
    def __call__(self, parser, _ns, _values, option_string=None):
        parser.error(f"{option_string} was removed in 0.5.0")


def parser():
    ap = argparse.ArgumentParser(prog="scintegrate")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("describe")
    sub.add_parser("doctor")
    g = sub.add_parser("integrate")
    g.add_argument("--h5ad", required=True)
    g.add_argument("--out", required=True)
    g.add_argument("--batch-key", default="sample")
    g.add_argument("--label-key", required=True)
    g.add_argument("--species", required=True)
    g.add_argument("--assay", default=None, choices=list(ASSAYS))
    for flag in ("--l1-key", "--drop-labels", "--score-against", "--colour-by", "--design",
                 "--design-sample-col"):
        g.add_argument(flag, default=None)
    g.add_argument("--scanvi-max-epochs", type=int, default=None)
    g.add_argument("--coarse-from-path", action="store_true")
    g.add_argument("--label-sentinel", action="append", default=None)
    g.add_argument("--bio-factor", action="append", default=None)
    g.add_argument("--k", type=int, default=30)
    g.add_argument("--n-pcs", type=int, default=50)
    g.add_argument("--seed", type=int, default=0)
    g.add_argument("--min-per-k", type=int, default=3)
    g.add_argument("--min-dist", type=float, default=0.2)
    g.add_argument("--indicates-below", type=float, default=0.80)
    g.add_argument("--methods", default="none,harmony,scvi,scanvi")
    g.add_argument("--n-latent", type=int, default=30)
    g.add_argument("--max-epochs", type=int, default=None)
    g.add_argument("--w-bio", type=float, default=0.6)
    g.add_argument("--n-cores", type=int, default=1)
    g.add_argument("--lisi-subsample", action=_Removed, nargs="?")
    g.add_argument("--scib-resolutions", type=int, default=None)
    g.add_argument("--no-fast-leiden", action="store_true")
    g.add_argument("--object-name", default="cohort_integrated.h5ad")
    return ap


def main():
    log_call()
    a = parser().parse_args()
    if a.cmd == "describe":
        print(json.dumps({"name": "scintegrate", "version": VERSION, "commit": COMMIT,
                          "state_version": STATE_VERSION,
                          "axes": {"assay": {"required": False, "accepted": list(ASSAYS)},
                                   "species": {"required": True}}}))
        return 0
    if a.cmd == "doctor":
        print("scintegrate doctor (stand-in): nothing measured")
        return 0
    return integrate(a)


if __name__ == "__main__":
    sys.exit(main())
