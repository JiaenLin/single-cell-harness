"""A stand-in for scIntegrate's CLI (`python -m scintegrate.cli`), for tests that drive
`int@scintegrate` through `sch` without scanpy, anndata or any integration method.

It honours the parts of scIntegrate's contract the adapter relies on, and nothing more, as
`fake_scanno.py` stands in for scAnno. It is held to scIntegrate 0.7.0 (2fc7a6c, state version 2):
where a harness test relies on a behaviour, the tool's is copied here, its words included, and
`TheRealScintegrate` runs this stand-in and the real tool on the same inputs and compares what
each writes, because a stand-in laxer than its tool passes where the tool refuses (ATTACKS 1).

    describe        the declaration, as JSON: `state_version`, and the assays `axes` accepts
    doctor          one line; exit 0
    integrate       parsed with the flags scIntegrate's own parser declares for it (0.7.0,
                    2fc7a6c), so a flag scIntegrate does not have fails here as it would there,
                    and `--lisi-subsample` stops at the parser with exit 2

`integrate` keeps scIntegrate's status contract in `--out`: `STATUS.json` written first as
`partial` with `sys.argv`, `RUNNING.txt`, then the outcome with its products and `SEALED.txt` or
`FAILED.txt`. BEFORE ANYTHING IS COMPUTED it refuses by name - exit 2, STATUS `refused`, the
tool's fix - what the tool refuses there: a key the object's obs lacks; a design table with no
rows, without its `--design-sample-col`, without a row for a batch, or without a `--bio-factor`; a
design column named like a column another option carries, differing from it; a design key whose
column the object holds with other values; a name the object's writer forbids (`/` in it,
`_index`, empty, `.`, a NUL, a column without a name, the index's own name on other values)
among the columns the object would carry or the input's var; an `--object-name` that is not a
file name ending `.h5ad`. Its object, `objects/<--object-name>`, is an `.h5ad` written with h5py
in anndata's on-disk encodings, made as scIntegrate makes its own:
  - obs, in the tool's order: the batch, label and l1 columns and the colour columns, COPIED from
    the input node by node (so they are the input's own); every design column, copied when the
    input has it, else joined on by the batch value (`withheld_from_integration` on the cells
    `--drop-labels` withholds); last, the design's key under the design's own name: nothing added
    when it IS the batch key, added from the batch column (the withheld cells included) when the
    input lacks it, the input's own kept when it equals the batch column; every other obs column
    left out (scIntegrate's slim);
  - obsm: X_pca, the input's as delivered when no withheld cell has a row in it or with
    `--keep-input-pca`, else a fixed pattern standing for the refit on the retained cells (centred
    over them), NaN on the withheld rows; one embedding per method that has one, made from that
    PCA (NaN rows for the withheld cells); a 2-D view per method; and the chosen method's view again
    under the input's 2-D key, so that entry is a rewrite when the input carries one;
  - obsp: a graph method's two graphs, when one is among `--methods`.
`report.json` carries `chosen`, `design_key` (the tool's record, word for word) and `pca` (which
PCA was used, in the tool's words for its source). The input must carry X_pca: the stand-in
computes no PCA.

What it computes is a fixed pattern of the input's numbers, never an integration: a test using it
checks the harness around scIntegrate, never scIntegrate. The obsm keys it writes are scIntegrate's
names; they live here, in a test fixture, and nowhere in the adapter.

Environment:
    FAKE_SCINTEGRATE_LOG              append {"argv", "argv0", "cwd", "pythonpath"} per call
    FAKE_SCINTEGRATE_MODE             ok (default) | refuse | fail | unsealed | short | other_argv |
                                      reversed (rows written last first) | relabel (l1 rewritten)
    FAKE_SCINTEGRATE_STATE_VERSION    what `describe`, STATUS and the object's provenance report, as a
                                      JSON value (default 2, 2fc7a6c's; `2.0` or `"2"` plant a non-integer)
    FAKE_SCINTEGRATE_STATUS_STATE_VERSION   what STATUS alone reports (default: the above)
    FAKE_SCINTEGRATE_PROV_STATE_VERSION     what the object's `uns/scintegrate/provenance` alone
                                      reports (default: the above; `absent` writes none)
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
STATE_VERSION = json.loads(os.environ.get("FAKE_SCINTEGRATE_STATE_VERSION", "2"))
STATUS_STATE_VERSION = json.loads(os.environ.get("FAKE_SCINTEGRATE_STATUS_STATE_VERSION", json.dumps(STATE_VERSION)))
PROV_STATE_VERSION = os.environ.get("FAKE_SCINTEGRATE_PROV_STATE_VERSION", json.dumps(STATE_VERSION))
VERSION, COMMIT = "0.0.0-fake", "e" * 40
ASSAYS = ("scrna", "snrna")
GRAPH_METHODS = ("bbknn",)
PCA, VIEW = "X_pca", "X_umap"
WITHHELD = "withheld_from_integration"
#: the tool's fix on every refusal it records (scintegrate/cli.py, the status wrapper)
REFUSAL_FIX = "change the input the refusal names, or the flag it asks for"


def log_call():
    path = os.environ.get("FAKE_SCINTEGRATE_LOG")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"argv": sys.argv[1:], "argv0": sys.argv[0], "cwd": os.getcwd(),
                                 "pythonpath": os.environ.get("PYTHONPATH")}) + "\n")


# ---------------------------------------------------------------------------- an .h5ad, with h5py
def write_object(path, index, obs, obsm=None, obsp=None, copy_from=None, provenance=None):
    """An .h5ad holding obs (`{name: (kind, values)}`, kind cat|str|int|float, or a node of
    `copy_from` to copy as it is), obsm (`{key: array}`) and obsp (`{key: (data, indices, indptr,
    shape)}`, compressed sparse rows); with `provenance` (`{key: value}`), the tool's own record in
    `uns/scintegrate/provenance`, each value a scalar dataset as anndata writes one."""
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
        u = f.create_group("uns")
        u.attrs["encoding-type"], u.attrs["encoding-version"] = "dict", "0.1.0"
        if provenance is not None:
            g = u.create_group("scintegrate").create_group("provenance")
            for grp in (u["scintegrate"], g):
                grp.attrs["encoding-type"], grp.attrs["encoding-version"] = "dict", "0.1.0"
            for key, v in provenance.items():
                if isinstance(v, str):
                    d = g.create_dataset(key, data=v, dtype=vlen)
                    d.attrs["encoding-type"], d.attrs["encoding-version"] = "string", "0.2.0"
                else:
                    d = g.create_dataset(key, data=np.array(v))
                    d.attrs["encoding-type"], d.attrs["encoding-version"] = "numeric-scalar", "0.2.0"


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
    """An obs column (or the index) as text, in the encodings anndata writes: a categorical, a
    string array, a nullable array (values and a mask: pandas' string columns under anndata 0.13),
    a number array."""
    import h5py
    if isinstance(node, h5py.Group):
        if "codes" in node:
            cats = _column_text(node["categories"])
            return [cats[k] if k >= 0 else None for k in node["codes"][()]]
        vals = _strings(node["values"][()])
        mask = node["mask"][()].tolist() if "mask" in node else [False] * len(vals)
        return [None if m else v for v, m in zip(vals, mask)]
    return _strings(node[()])


def _columns(g):
    """A dataframe group's column names, in its own order."""
    if g is None:
        return []
    order = g.attrs.get("column-order", [])
    return [c.decode() if isinstance(c, bytes) else str(c) for c in list(order)]


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
           "commit": COMMIT, "state_version": STATUS_STATE_VERSION, "status": "partial",
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


class Refuse(Exception):
    """A refusal the tool makes before anything is computed: exit 2, STATUS refused."""


def _refused(out, rec, why):
    print(f"scintegrate: REFUSE - {why}", file=sys.stderr)
    return _finish(out, rec, "refused", 2, f"refused: {str(why)[:300]}",
                   refusal={"reason": str(why), "fix": REFUSAL_FIX})


# ---------------------------------------------------------------------------- before anything is computed
def _what_is_wrong(name):
    """scIntegrate's reader's reason for a name the writer refused, word for word (cli.py)."""
    if not isinstance(name, str):
        return (f"it is {name!r}, not text: a design row with more fields than its header gives a "
                "column without a name")
    if name == "":
        return "it is empty: a design header ending in a comma gives such a column"
    if "/" in name:
        return "it holds '/', which the file format reads as a path separator"
    if name == "_index":
        return "the file format reserves it for a table's index"
    if name == ".":
        return "the file format reads '.' as the table itself"
    if "\x00" in name:
        return "it holds a NUL character"
    return "see the writer's words"


def _forbidden(name):
    """What the object's writer refuses as a column name (anndata 0.13 over h5py, as W046 measured
    it): a column without a name, an empty one, a '/' anywhere, exactly `_index`, `.`, a NUL."""
    return not isinstance(name, str) or name in ("", "_index", ".") or "/" in name or "\x00" in name


def _read_design(path, samples, sample_col):
    rows = list(csv.DictReader(open(path, newline="", encoding="utf-8-sig")))
    if not rows:
        raise Refuse(f"design table {path} has no rows")
    cols = list(rows[0].keys())
    key = sample_col or cols[0]
    if key not in cols:
        raise Refuse(f"--design-sample-col {key!r} not in {path}: columns are " + ", ".join(map(repr, cols)))
    table = {r[key]: r for r in rows}
    unmatched = [s for s in sorted(set(map(str, samples))) if s not in table]
    if unmatched:
        raise Refuse(f"{len(unmatched)} batch(es) in the object have no row in {path}: "
                     + ", ".join(map(repr, unmatched)))
    return table, key, [c for c in cols if c != key]


def _design_key(text, key, batch_key, n):
    """scIntegrate's three cases for the design's key column (inputs.design_key), word for word."""
    if key == batch_key:
        return {"column": key, "how": "the batch column itself", "added": False}
    if key in text:
        mine, batch = text[key], text[batch_key]
        off = [i for i in range(n) if str(mine[i]) != str(batch[i])]
        if off:
            i = off[0]
            raise Refuse(
                f"the design is keyed on {key!r}, whose rows are named by {batch_key!r} values, but the "
                f"object's own {key!r} column differs from {batch_key!r} on {len(off):,} of {n:,} "
                f"cells (the first: {mine[i]!r} where {batch_key!r} is {batch[i]!r}). The deliverable "
                f"cannot carry both under one name. Rename the design's key column or the object's, or "
                f"pass --batch-key {key} if that column is the batch.")
        return {"column": key, "how": f"the object's own column, equal to {batch_key!r} on every cell",
                "added": False}
    return {"column": key, "how": f"added from {batch_key!r}: each cell's {batch_key} value, the withheld "
                                  f"cells included", "added": True}


def _carried(a, g, n):
    """Every obs column the object will carry, in the tool's order, each with the option naming it
    (cli._carried_obs), and the values of the ones it adds; refused here when two would claim one
    name or the writer forbids one. Returns (keep, named, added, design_key, design, factors)."""
    cols = _columns(g)
    for role, k in (("--batch-key", a.batch_key), ("--label-key", a.label_key), ("--l1-key", a.l1_key)):
        if k is not None and k not in cols:
            raise Refuse(f"{role} {k!r} is not in obs. obs carries {len(cols)} column(s): "
                         + ", ".join(repr(c) for c in cols))
    text = {c: _column_text(g[c]) for c in cols}
    asked = [c.strip() for c in (a.colour_by or "").split(",") if c.strip()]
    for c in asked:
        if c not in cols:
            raise Refuse(f"--colour-by names {c!r}, which is not an obs column. "
                         f"Present: {', '.join(map(str, cols[:20]))}")
    colour = {c: "named in --colour-by" for c in asked} or {
        c: f"{w} (pass --colour-by to draw more label columns)"
        for c, w in ((a.l1_key, "--l1-key"), (a.label_key, "--label-key")) if c and c in cols}
    named = {}
    for c, why in ([(a.batch_key, "--batch-key"), (a.label_key, "--label-key")]
                   + ([(a.l1_key, "--l1-key")] if a.l1_key else [])
                   + [(c, f"a colour column ({w})") for c, w in colour.items()]):
        named.setdefault(c, []).append(why)
    keep, added, design, dk, factors = list(named), {}, {}, None, []
    batch = text[a.batch_key]
    if a.design:
        table, key, factors = _read_design(a.design, batch, a.design_sample_col)
        dk = _design_key(text, key, a.batch_key, n)
        bad = [f for f in (a.bio_factor or []) if f not in factors]
        if bad:
            raise Refuse(f"--bio-factor {bad} not in {a.design}: it offers {factors}")
        for f in factors:
            v = [table[b][f] for b in batch]
            design[f] = v
            why = "a column of --design"
            if f in named:
                off = [i for i in range(n) if str(text[f][i]) != str(v[i])]
                if off:
                    i = off[0]
                    raise Refuse(
                        f"{why}, {f!r}, has the name of the column {' and '.join(named[f])} carries, and "
                        f"differs from it on {len(off):,} of {n:,} cells (the first: {v[i]!r} where the "
                        f"object holds {text[f][i]!r}). The object cannot carry both under one name; "
                        f"rename the design's column.")
                named[f].append(why + ", equal to it on every cell")
                continue
            named.setdefault(f, []).append(why)
            keep.append(f)
            if f not in cols:
                added[f] = v
        why = "the design's key (--design-sample-col, or the design's first column)"
        if dk["column"] in named:
            named[dk["column"]].append(why)
        else:
            named[dk["column"]] = [why]
            keep.append(dk["column"])
            if dk["added"]:
                added[dk["column"]] = [str(b) for b in batch]
    return keep, named, added, dk, design, text


def _check_writable(a, f, keep, named, text, index):
    """Refuse, before anything is computed, a run whose object the writer would refuse to write."""
    name = a.object_name
    if Path(name).name != name or name in ("", ".", "..") or not name.endswith(".h5ad"):
        raise Refuse(f"--object-name {name!r} is not a file name ending in .h5ad: the object is "
                     f"written into objects/ under it, and the run lists its .h5ad files as its products")
    idx = f["obs"].attrs.get("_index", "_index")
    idx = idx.decode() if isinstance(idx, bytes) else str(idx)
    lines = []
    for c in keep:
        if _forbidden(c) or (c == idx != "_index" and c in text and text[c] != list(index)):
            lines.append(f"{c!r}, {' and '.join(named.get(c, ['a column']))}: {_what_is_wrong(c)} "
                         f"(the writer's rule, as this stand-in holds it)")
    for c in _columns(f.get("var")):
        if _forbidden(c):
            lines.append(f"{c!r}, a column of the input's var: {_what_is_wrong(c)} "
                         f"(the writer's rule, as this stand-in holds it)")
    if lines:
        raise Refuse("the object's writer refuses " + ("this name" if len(lines) == 1 else
                     f"these {len(lines)} names") + ", so nothing was computed: "
                     + "; ".join(lines) + ". Rename each in the design or the input.")


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
    methods = ["none"] + [m for m in (a.methods or "").split(",") if m.strip() and m != "none"]
    with h5py.File(a.h5ad, "r") as f:
        g = f["obs"]
        key = g.attrs.get("_index", "_index")
        index = [v if v is not None else "" for v in _column_text(g[key.decode() if isinstance(key, bytes) else key])]
        n = len(index)
        try:
            keep, named, added, dk, design, text = _carried(a, g, n)
            _check_writable(a, f, keep, named, text, index)
        except Refuse as e:
            return _refused(out, rec, e)
        labels = text[a.label_key]
        drop = np.isin(np.array(labels, dtype=object), [x for x in (a.drop_labels or "").split(",") if x])
        obs = {}
        for c in keep:
            if c in added:
                v = list(added[c])
                if c in design and drop.any():          # a design column the input lacks
                    v = [WITHHELD if d else x for x, d in zip(v, drop)]
                obs[c] = ("str", v)
            else:
                obs[c] = ("copy", g[c])
        p_in = np.asarray(f["obsm"][PCA][()], dtype="float32")
        n_w = int(drop.sum())
        in_fit = int((~np.isnan(p_in[drop].astype("float64")).any(axis=1)).sum()) if n_w else 0
        pca_rec = {"source": "input", "declared": None, "n_withheld_not_fitted": n_w, "n_withheld_in_fit": 0}
        if in_fit and not a.keep_input_pca:
            pca = (p_in - p_in[~drop].mean(axis=0)).astype("float32")     # stands for the refit
            pca[drop] = np.nan
            pca_rec["source"] = "refit"
        else:
            pca = p_in
            if in_fit:
                pca_rec.update(declared="--keep-input-pca", n_withheld_not_fitted=n_w - in_fit,
                               n_withheld_in_fit=in_fit)
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
        # the tool's provenance, as 2fc7a6c writes it: its state_version among the run's own words
        prov = {"tool": "scintegrate", "version": VERSION}
        if PROV_STATE_VERSION != "absent":
            prov["state_version"] = json.loads(PROV_STATE_VERSION)
        write_object(out / "objects" / a.object_name, index, obs, obsm, obsp, provenance=prov)
    (out / "tables").mkdir(parents=True, exist_ok=True)
    (out / "tables" / "scib_aggregate.csv").write_text(
        "method,total\n" + "".join(f"{m},{0.5 + i / 100:.6f}\n" for i, m in enumerate(methods)))
    (out / "report.json").write_text(json.dumps({"version": VERSION, "command": "integrate",
                                                 "chosen": {"default": chosen}, "species": a.species,
                                                 "assay": a.assay, "methods": methods,
                                                 "design_key": dk, "pca": pca_rec}, indent=1))
    if MODE == "unsealed":
        rec.update({"status": "ok", "products": _products(out)})
        (out / "STATUS.json").write_text(json.dumps(rec, indent=1) + "\n")
        return 0
    return _finish(out, rec, "ok", 0, "every method compared and the object written")


# ---------------------------------------------------------------------------- the parser (2fc7a6c's flags)
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
    g.add_argument("--keep-input-pca", action="store_true")
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
