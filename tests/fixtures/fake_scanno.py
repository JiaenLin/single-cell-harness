#!/usr/bin/env python3
"""A stand-in for scAnno's CLI (`bin/scanno`), for tests that drive `anno@scanno` through `sch`
without scanpy, anndata or a marker corpus.

It honours the parts of scAnno's contract the adapter relies on, and nothing more, as
`fake_scqc.py` stands in for scQC:

    describe                 the declaration, as JSON (`state_version` is what the adapter checks, and
                             `files`, what each command opens, as scAnno's parser types it)
    cluster | annotate | rescue | embed
                             each parsed with the flags scAnno's own parser declares for it (at
                             d0ee926), so a flag scAnno does not have fails here as it would there

Each command keeps scAnno's status contract beside its primary output: `STATUS.<cmd>.json`
written first as `partial` with the call's `argv`, `RUNNING.<cmd>.txt`, then the outcome and
`SEALED.<cmd>.txt` or `FAILED.<cmd>.txt`. Objects are `.h5ad` files written with h5py, holding an
obs dataframe in anndata's on-disk encodings (string-array, categorical, numeric, bool) and
nothing else. Output names follow scAnno's rules: `cluster --out-dir` writes
`<stem>_clustered.h5ad`, `rescue --out-dir` writes `<stem>.rescued.h5ad`.

What it computes is a fixed pattern of each observation's position, never a clustering or a label:
a test using it checks the harness around scAnno, never scAnno.

Environment:
    FAKE_SCANNO_LOG             append {"argv", "cwd"} as one JSON line per call
    FAKE_SCANNO_MODE            ok (default) | <kind>:<command> with kind refuse, fail or unsealed |
                                nostatus:<command>:<n> (the n-th call of it exits 2 at the parse,
                                before any record, as an argument error does) |
                                short (annotate loses each object's first observation)
    FAKE_SCANNO_STATE_VERSION   what `describe` and every STATUS report (default 1)
"""
import argparse
import json
import os
import sys
from pathlib import Path

MODE = os.environ.get("FAKE_SCANNO_MODE", "ok")
#: The escapes scAnno's `describe` declares, copied from the tool (scanno/cli.py:3227-3231 at 779fd08):
#: the adapter's `decisions:` must ask each one (harness W042 fix 1, D); FAKE_SCANNO_MODE=escape_drift
#: declares one more, as a newer scAnno would.
ESCAPES = [{"flag": "--no-exclude", "lifts": "the upstream exclusion", "recorded": "STATUS.annotate.json escapes[]"},
           {"flag": "--background-from-clusters", "lifts": "the calibrated store", "recorded": "STATUS.annotate.json escapes[]"},
           {"flag": "--gap-min", "lifts": "the descent threshold", "recorded": "STATUS.annotate.json escapes[]"},
           {"flag": "--tissue-fallback", "lifts": "the declared tissue: every tissue of the species is read", "recorded": "STATUS.<cmd>.json escapes[] and corpus"},
           {"flag": "--marker-species", "lifts": "the declared species, for markers only", "recorded": "STATUS.<cmd>.json escapes[] and corpus"}]
STATE_VERSION = int(os.environ.get("FAKE_SCANNO_STATE_VERSION", "1"))
VERSION, COMMIT = "0.0.0-fake", "f" * 40


def log_call():
    path = os.environ.get("FAKE_SCANNO_LOG")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"argv": sys.argv[1:], "cwd": os.getcwd()}) + "\n")


def tag(r) -> str:
    """scAnno's resolution tag: 1.0 -> 1p0, 1.25 -> 1p25."""
    s = f"{float(r):g}"
    return (s if "." in s else s + ".0").replace(".", "p")


def leiden(i: int, r: float) -> str:
    """The stand-in's 'cluster' of the observation at position i, at resolution r."""
    return str((i // max(1, int(round(6 / float(r))))) % 4)


# ---------------------------------------------------------------------------- an obs dataframe
def _strings(raw):
    return [x.decode() if isinstance(x, bytes) else str(x) for x in raw]


def read_obs(path):
    """(index, {column: (kind, values)}) for the encodings this stand-in and its tests write."""
    import h5py
    with h5py.File(path, "r") as f:
        obs = f["obs"]
        idx = obs.attrs.get("_index", "_index")
        idx = idx.decode() if isinstance(idx, bytes) else str(idx)
        index = _strings(obs[idx][()])
        order = [c.decode() if isinstance(c, bytes) else str(c)
                 for c in obs.attrs.get("column-order", [])]
        cols = {}
        for c in order:
            node = obs[c]
            if isinstance(node, h5py.Group):
                cats = _strings(node["categories"][()])
                cols[c] = ("cat", [cats[k] if k >= 0 else None for k in node["codes"][()]])
            elif node.dtype.kind in ("S", "O", "U"):
                cols[c] = ("str", _strings(node[()]))
            elif node.dtype.kind == "b":
                cols[c] = ("bool", [bool(x) for x in node[()]])
            elif node.dtype.kind in ("i", "u"):
                cols[c] = ("int", [int(x) for x in node[()]])
            else:
                cols[c] = ("float", [float(x) for x in node[()]])
        return index, cols


def write_obs(path, index, cols, assay=None):
    import h5py
    import numpy as np
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    vlen = h5py.string_dtype()
    with h5py.File(path, "w") as f:
        f.attrs["encoding-type"], f.attrs["encoding-version"] = "anndata", "0.1.0"
        obs = f.create_group("obs")
        obs.attrs["encoding-type"], obs.attrs["encoding-version"] = "dataframe", "0.2.0"
        obs.attrs["_index"] = "_index"
        obs.attrs["column-order"] = list(cols)
        d = obs.create_dataset("_index", data=np.array(index, dtype=object), dtype=vlen)
        d.attrs["encoding-type"], d.attrs["encoding-version"] = "string-array", "0.2.0"
        for name, (kind, vals) in cols.items():
            if kind == "cat":
                cats = sorted({v for v in vals if v is not None})
                g = obs.create_group(name)
                g.attrs["encoding-type"], g.attrs["encoding-version"] = "categorical", "0.2.0"
                g.attrs["ordered"] = False
                c = g.create_dataset("categories", data=np.array(cats, dtype=object), dtype=vlen)
                c.attrs["encoding-type"], c.attrs["encoding-version"] = "string-array", "0.2.0"
                g.create_dataset("codes", data=np.array(
                    [cats.index(v) if v is not None else -1 for v in vals], dtype="int8"))
            elif kind == "str":
                ds = obs.create_dataset(name, data=np.array(vals, dtype=object), dtype=vlen)
                ds.attrs["encoding-type"], ds.attrs["encoding-version"] = "string-array", "0.2.0"
            else:
                dtype = {"bool": "bool", "int": "int64", "float": "float64"}[kind]
                ds = obs.create_dataset(name, data=np.array(vals, dtype=dtype))
                ds.attrs["encoding-type"], ds.attrs["encoding-version"] = "array", "0.2.0"
        uns = f.create_group("uns")
        if assay is not None:
            ctx = uns.create_group("scanno_context")
            ctx.create_dataset("assay", data=assay, dtype=vlen)


# ---------------------------------------------------------------------------- the status contract
class Status:
    def __init__(self, d, cmd):
        self.d, self.cmd = Path(d), cmd
        self.d.mkdir(parents=True, exist_ok=True)
        self.rec = {"contract": "1.0", "tool": "scanno", "command": cmd, "version": VERSION,
                    "commit": COMMIT, "state_version": STATE_VERSION, "status": "partial",
                    "headline": "started", "argv": list(sys.argv), "escapes": [], "refusal": None}
        self._write()
        (self.d / f"RUNNING.{cmd}.txt").write_text("started\n")

    def _write(self):
        (self.d / f"STATUS.{self.cmd}.json").write_text(json.dumps(self.rec, indent=1) + "\n")

    def finish(self, status, headline, code, refusal=None, n_obs=0, seal=True):
        self.rec.update(status=status, headline=headline, exit=code, refusal=refusal,
                        timings={"wall_s": 0.01, "n_obs": n_obs,
                                 "steps": [{"step": "whole", "wall_s": 0.01}]})
        self._write()
        if not seal:
            return code
        ok = status == "ok" and code == 0
        name, other = ((f"SEALED.{self.cmd}.txt", f"FAILED.{self.cmd}.txt") if ok
                       else (f"FAILED.{self.cmd}.txt", f"SEALED.{self.cmd}.txt"))
        (self.d / name).write_text(f"exit={code}\nstatus={status}\ncommand={self.cmd}\n")
        if (self.d / other).exists():
            (self.d / other).unlink()
        (self.d / f"RUNNING.{self.cmd}.txt").unlink()
        return code


def outcome(st, cmd, n_obs, headline):
    """The mode's outcome for this command, or None to carry on."""
    kind, _, which = MODE.partition(":")
    if which != cmd:
        return None
    if kind == "refuse":
        print(f"scanno: REFUSE - {cmd}: the stand-in was told to refuse", file=sys.stderr)
        return st.finish("refused", f"{cmd}: the stand-in was told to refuse", 2, n_obs=n_obs,
                         refusal={"reason": f"{cmd}: the stand-in was told to refuse",
                                  "fix": "declare what the refusal names", "code": "told"})
    if kind == "fail":
        print(f"scanno: ERROR - {cmd} died", file=sys.stderr)
        return st.finish("failed", f"RuntimeError: {cmd} died", 1, n_obs=n_obs)
    if kind == "unsealed":
        return st.finish("ok", headline, 0, n_obs=n_obs, seal=False)
    return None


#: THE FILES scAnno OPENS, as its `describe` would declare them (`files`; scAnno's `describe` declares none, its
#: parser types each of these `type=Path`: scanno/cli.py:2468, :2511, :2528, :2550, :2570, :2588, :2597, :2664,
#: :2904 at 9fb561c): each flag of a command naming a file it READS, by its dest. What it writes (`--out`,
#: `--out-dir`, `--status-dir`, ...) is not an input. Every command refuses an absent one, as scAnno does; the
#: adapter's `files:` and `owned:` are tied to this by tests/test_the_adapters_declare_what_their_tools_open.py.
FILES = {"flags": {"cluster": {"h5ad": "file"}, "rescue": {"h5ad": "file"}, "embed": {"h5ad": "file"},
                   "annotate": {"h5ad": "file", "tree": "file", "scope": "file", "l1_tree": "file", "db": "file",
                                "store": "file"}}}
IS = {"file": os.path.isfile, "dir": os.path.isdir, "path": os.path.exists}


def absent(a):
    """The first file this call's declared flags name that is not here, said as scAnno's parser would, or None."""
    for dest, kind in FILES["flags"].get(a.cmd, {}).items():
        v = getattr(a, dest, None)
        for x in (v if isinstance(v, list) else [v] if v else []):
            if not IS[kind](str(x)):
                return f"--{dest.replace('_', '-')} {str(x)!r} is not a {kind}"
    return None


# ---------------------------------------------------------------------------- the commands
def describe(_a):
    print(json.dumps({"contract": "1.0", "name": "scanno", "version": VERSION, "commit": COMMIT,
                      "state_version": STATE_VERSION, "class": "method", "layer": "stack",
                      "reversible": True, "sees": [], "escapes": ESCAPES + (
                          [{"flag": "--drift", "lifts": "a stand-in's new escape", "recorded": "nowhere"}]
                          if MODE == "escape_drift" else []),
                      "cannot_show": ["a stand-in shows nothing"], "files": FILES}))
    return 0


def cluster(a):
    st = Status(a.status_dir or a.out_dir or Path(a.out).parent, "cluster")
    res = [float(x) for x in (a.resolutions or "0.5,1.0").split(",")]
    n = 0
    for src in a.h5ad:
        index, cols = read_obs(src)
        n += len(index)
        for r in res:
            cols[f"leiden_{tag(r)}"] = ("cat", [leiden(i, r) for i in range(len(index))])
        write_obs(Path(a.out_dir) / f"{Path(src).stem}_clustered.h5ad", index, cols)
    done = outcome(st, "cluster", n, "clustered")
    return done if done is not None else st.finish("ok", "clustered", 0, n_obs=n)


def annotate(a):
    st = Status(a.status_dir or Path(a.out_h5ad).parent, "annotate")
    index, cols = read_obs(a.h5ad)
    missing = [k for k in a.cluster_key if k not in cols]
    if missing:
        print(f"scanno: ERROR - KeyError: {missing[0]!r}", file=sys.stderr)
        return st.finish("failed", f"KeyError: {missing[0]!r}", 1, n_obs=len(index))
    p, s = a.label_prefix, a.label_suffix
    first = cols[a.cluster_key[0]][1]
    if MODE == "short":
        index = index[1:]
        cols = {k: (kind, v[1:]) for k, (kind, v) in cols.items()}
        first = first[1:]
    cols[f"{p}_cell_type{s}"] = ("cat", [f"type_{c}" for c in first])
    cols[f"{p}_path{s}"] = ("cat", [f"root/type_{c}" for c in first])
    cols[f"{p}_gap{s}"] = ("float", [float("nan") if c == "0" else 0.5 for c in first])
    cols[f"{p}_forced{s}"] = ("bool", [c == "3" for c in first])
    if a.resolve:
        cols[f"{p}_resolved_path{s}"] = ("cat", [f"root/type_{c}" for c in first])
        for k in a.cluster_key:
            t = k.rsplit("_", 1)[-1]
            cols[f"{p}_resolved_path{s}_r{t}"] = ("cat", [f"root/type_{c}" for c in cols[k][1]])
    write_obs(a.out_h5ad, index, cols, assay=a.assay)
    done = outcome(st, "annotate", len(index), "annotated")
    return done if done is not None else st.finish("ok", "annotated", 0, n_obs=len(index))


def rescue(a):
    st = Status(a.status_dir or a.out_dir or Path(a.out).parent, "rescue")
    out_key = a.out_key or f"{a.label_key}_rescued"
    n, units = 0, []
    for src in a.h5ad:
        index, cols = read_obs(src)
        n += len(index)
        unit = (cols[a.unit_key][1][0] if a.unit_key and a.unit_key in cols
                else Path(src).stem.split(".")[0])
        units.append(unit)
        rungs = [c for c in cols if c.startswith(a.sweep_prefix)
                 and f"{a.cluster_prefix}{c[len(a.sweep_prefix):]}" in cols]
        if len(rungs) < 2:
            print(f"scanno: REFUSE - {src} carries fewer than two rungs", file=sys.stderr)
            return st.finish("refused", "fewer than two rungs", 2, n_obs=n,
                             refusal={"reason": "fewer than two rungs",
                                      "fix": "annotate at several resolutions"})
        cols[out_key] = ("cat", list(cols[a.label_key][1]))
        cols[f"{out_key}_origin"] = ("cat", ["kept"] * len(index))
        if a.out_dir:
            write_obs(Path(a.out_dir) / f"{Path(src).stem}.rescued.h5ad", index, cols)
    for p, text in ((a.out, json.dumps({"units": units, "n_found": 0, "moved": []}, indent=1)),
                    (a.out_table, "unit,label,n_before,n_after\n"),
                    (a.out_report, "<html><body>a stand-in's rescue</body></html>\n")):
        if p:
            Path(p).parent.mkdir(parents=True, exist_ok=True)
            Path(p).write_text(text)
    done = outcome(st, "rescue", n, "targeted rescue done")
    return done if done is not None else st.finish("ok", "targeted rescue done", 0, n_obs=n)


def embed(a):
    """scAnno's `embed`: every object's obs in one joint object, in order, its obs_names as they are
    (index_unique=None), `--label-obs OLD=NEW` renaming, and obsm X_pca / X_umap - a fixed pattern of
    each observation's position, never an embedding. A named column no object carries is refused."""
    import h5py
    import numpy as np
    st = Status(a.status_dir or Path(a.out).parent, "embed")
    rename = {}
    for spec in a.label_obs or []:
        old, _, new = str(spec).partition("=")
        rename[old] = new or old
    index, cols, order = [], {}, None
    for src in a.h5ad:
        idx, c = read_obs(src)
        if a.sample_key not in c:
            # scanno/embed.py: an object without the column is named by its file's stem
            c[a.sample_key] = ("cat", [Path(src).stem.replace("_annotated", "")] * len(idx))
        order = [k for k in (order if order is not None else list(c)) if k in c]
        index += idx
        for k in order:
            cols.setdefault(k, (c[k][0], []))[1].extend(c[k][1])
    gone = sorted(set(rename) - set(order or []))
    if gone:
        print(f"scanno: REFUSE - embed: --label-obs names {gone[0]!r}, which no object carries", file=sys.stderr)
        return st.finish("refused", f"embed: no column {gone[0]!r}", 2, n_obs=len(index),
                         refusal={"reason": f"embed: no column {gone[0]!r}", "fix": "name a column annotate wrote"})
    out = {rename.get(k, k): cols[k] for k in order or []}
    write_obs(a.out, index, out)
    pca = np.array([[((i * (k + 3)) % 17) / 17.0 for k in range(6)] for i in range(len(index))], dtype="float32")
    with h5py.File(a.out, "a") as f:
        m = f.create_group("obsm")
        m.create_dataset("X_pca", data=pca)
        m.create_dataset("X_umap", data=np.ascontiguousarray(pca[:, :2]))
    done = outcome(st, "embed", len(index), "embedded")
    return done if done is not None else st.finish("ok", "embedded", 0, n_obs=len(index))


def parse_error() -> bool:
    """`nostatus:<command>:<n>`: is this the call that dies at the parse, before any record?"""
    kind, _, rest = MODE.partition(":")
    cmd, _, nth = rest.partition(":")
    if kind != "nostatus" or sys.argv[1:2] != [cmd]:
        return False
    log = os.environ.get("FAKE_SCANNO_LOG")
    seen = [json.loads(x)["argv"][:1] for x in Path(log).read_text().splitlines()] if log else []
    return seen.count([cmd]) == int(nth or 1)


def main(argv=None):
    log_call()
    if parse_error():
        print("scanno: error: the stand-in was told to fail its parse", file=sys.stderr)
        return 2
    p = argparse.ArgumentParser(prog="scanno")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("describe").set_defaults(fn=describe)

    s = sub.add_parser("cluster")
    s.add_argument("--h5ad", required=True, nargs="+")
    s.add_argument("--out")
    s.add_argument("--split-by")
    s.add_argument("--out-dir")
    s.add_argument("--resolutions")
    s.add_argument("--n-top-genes", type=int)
    s.add_argument("--n-pcs", type=int)
    s.add_argument("--n-neighbors", type=int)
    s.add_argument("--seed", type=int, default=0)
    s.set_defaults(fn=cluster)

    s = sub.add_parser("annotate")
    s.add_argument("--h5ad", required=True)
    s.add_argument("--cluster-key", required=True, action="append")
    s.add_argument("--tree", required=True)
    s.add_argument("--resolve", action="store_true")
    s.add_argument("--scope")
    s.add_argument("--l1-tree")
    s.add_argument("--species", required=True)
    s.add_argument("--tissue", required=True)
    s.add_argument("--assay", required=True, choices=("scrna", "snrna", "sc", "sn"))
    s.add_argument("--db")
    s.add_argument("--store")
    s.add_argument("--background-from-clusters", action="store_true")
    s.add_argument("--exclude-flag")
    s.add_argument("--no-exclude", action="store_true")
    s.add_argument("--gap-min", type=float)
    s.add_argument("--tissue-fallback", choices=["species"])      # scanno/cli.py:2589 at 779fd08
    s.add_argument("--marker-species")
    s.add_argument("--min-tier", type=int, default=4)
    s.add_argument("--out-gene-key", default="gene_symbol")
    s.add_argument("--gene-key")
    s.add_argument("--use-raw", action="store_true")
    s.add_argument("--out")
    s.add_argument("--out-h5ad")
    s.add_argument("--report")
    s.add_argument("--sample-key")
    s.add_argument("--condition-key")
    s.add_argument("--label-suffix", default="")
    s.add_argument("--label-prefix", default="scanno")
    s.set_defaults(fn=annotate)

    s = sub.add_parser("rescue")
    s.add_argument("--h5ad", required=True, nargs="+")
    s.add_argument("--label-key", required=True)
    s.add_argument("--sweep-prefix", default="scanno_resolved_path_r")
    s.add_argument("--cluster-prefix", default="leiden_")
    s.add_argument("--unit-key")
    s.add_argument("--from-resolution", type=float)
    s.add_argument("--to-resolution", type=float)
    s.add_argument("--out-key")
    s.add_argument("--out-dir")
    s.add_argument("--out")
    s.add_argument("--out-table")
    s.add_argument("--out-report")
    s.set_defaults(fn=rescue)

    s = sub.add_parser("embed")
    s.add_argument("--h5ad", required=True, nargs="+")
    s.add_argument("--out", required=True)
    s.add_argument("--sample-key", default="sample")
    s.add_argument("--label-obs", nargs="*", default=None)
    s.add_argument("--gene-key")
    s.add_argument("--n-hvg", type=int, default=2000)
    s.add_argument("--n-pcs", type=int, default=50)
    s.add_argument("--n-neighbors", type=int, default=15)
    s.add_argument("--min-dist", type=float, default=0.2)
    s.add_argument("--seed", type=int, default=0)
    s.set_defaults(fn=embed)

    for sp in sub.choices.values():
        sp.add_argument("--status-dir")
        sp.add_argument("--by")
    a = p.parse_args(argv)
    why = absent(a)
    if why:
        print(f"scanno {a.cmd}: error: {why}", file=sys.stderr)
        return 2
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
