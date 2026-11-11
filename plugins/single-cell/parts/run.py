#!/usr/bin/env python3
"""parts: one object holding every library becomes the per-library parts the stages read (harness
W045, ROUTE R43, GAP-C90).

A cohort can arrive as ONE object - every library in one file, as public atlases deliver it - with
its counts in a slot other than X, stable gene ids as var_names and the symbols in a column. The
family's first stage reads libraries: scQC ingests one object per library from its samplesheet, its
counts in X, and matches the mitochondrial prefix on var_names. This step writes exactly that, per
library, and the samplesheet naming them, and adds nothing:

  - every value is the object's: a part's X is the declared counts slot's stored values in their
    dtype, row for row; its var_names are the declared symbol column (the stable ids kept in
    `gene_ids`); its obs is the object's barcodes in the object's order, with the library, the
    replicate and the carried columns;
  - nothing is guessed: the slot, the symbol column, the library and the replicate columns are the
    request's, by name; a slot holding any stored value that is not a non-negative integer is
    refused, naming the first cell and gene, and no part is kept;
  - duplicate symbols follow one stated rule (DUPLICATES), which the record repeats, name by name;
  - it streams: one pass over the slot in chunks of at most `chunk_values` stored values, each
    library's rows appended to its own file. Its memory is a chunk's plus a few bytes per cell,
    whatever the size of the object; the record states its own peak resident memory.

Nothing about a cohort or a site is here.
"""
import csv
import importlib.util
import json
import os
import re
import resource
import shutil
import sys
import time
from pathlib import Path

#: THE RULE FOR A SYMBOL TWO GENES SHARE, stated once and repeated in every record.
DUPLICATES = ("the first gene carrying a symbol, in the object's gene order, keeps it; the k-th repeat "
              "is written SYMBOL-k (k = 1, 2, ...), the form anndata's var_names_make_unique writes; "
              "a written name that is already another gene's symbol is refused")
#: Where the stable gene ids go in every part: the column a 10x reader and scQC name `gene_ids`.
GENE_IDS = "gene_ids"
#: The samplesheet column qc@scqc and scQC name each library by (qc@scqc SCQC_LIBRARY).
SHEET_LIBRARY = "sample"
#: The most stored values one chunk holds, unless the request declares `object.chunk_values`.
CHUNK_VALUES = 1 << 23
#: A library's name is a part's file name: refused, never rewritten, when it is not one.
SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]*")
#: The anndata on-disk encodings this step writes (anndata's spec, as anndata 0.8 onwards reads it).
ENC = {"anndata": "0.1.0", "csr_matrix": "0.1.0", "dataframe": "0.2.0", "string-array": "0.2.0",
       "categorical": "0.2.0", "array": "0.2.0", "dict": "0.1.0", "string": "0.2.0"}
EMPTY_GROUPS = ("layers", "obsm", "obsp", "varm", "varp")
#: What the driver writes into this step's params from the request; each is required.
DECLARED = ("library", "replicate", "counts", "symbols", "column")
#: The step's tables, and the numbers its record states.
TABLES = ("libraries", "replicates", "duplicate_symbols")
NUMBERS = ("n_obs", "n_var", "n_stored", "n_libraries", "n_replicates", "libraries_holding_several_replicates",
           "replicates_in_several_libraries", "peak_rss_kb")


class Refused(Exception):
    def __init__(self, reason, fix):
        super().__init__(reason)
        self.reason, self.fix = reason, fix


def _decode(x):
    return x.decode() if isinstance(x, bytes) else str(x)


def _enc(node, kind):
    node.attrs["encoding-type"] = kind
    node.attrs["encoding-version"] = ENC[kind]


# ---------------------------------------------------------------------------- reading the object
def slot_of(f, counts):
    """(the counts slot's group, the var frame describing its genes) for `X`, `raw/X` or `layers/<n>`."""
    import h5py
    if counts not in f:
        raise Refused(f"the object holds no counts slot {counts!r} (it holds "
                      f"{', '.join(sorted(k for k in f.keys()))})", "object.counts: X | raw/X | layers/<name>")
    var = "raw/var" if counts.startswith("raw/") else "var"
    node = f[counts]
    kind = _decode(node.attrs.get("encoding-type", node.attrs.get("h5sparse_format", "")))
    if not isinstance(node, h5py.Group) or kind not in ("csr_matrix", "csr"):
        raise Refused(f"the counts slot {counts!r} is {kind or 'a dense array'}; this step reads a "
                      f"row-compressed (csr) slot one library at a time without loading it, and has "
                      f"no streaming reader for this encoding", "deliver the counts as a csr slot")
    return node, f[var], var


def column(frame, name, where):
    """A frame's column as (codes, levels) for strings and categoricals, or (values, None)."""
    import h5py
    import numpy as np
    if name not in frame:
        cols = [k for k in frame.keys() if not k.startswith("_")]
        raise Refused(f"{where} has no column {name!r} (its columns: {', '.join(cols)})",
                      f"name a column of {where}")
    node = frame[name]
    if isinstance(node, h5py.Group):
        if "codes" in node and "categories" in node:
            return node["codes"][()].astype(np.int64), [_decode(c) for c in node["categories"][()]]
        if "values" in node and "mask" in node and node["values"].dtype.kind in "OSU":
            vals, mask = node["values"][()], node["mask"][()]
            levels = sorted({_decode(v) for v, m in zip(vals, mask) if not m})
            pos = {v: i for i, v in enumerate(levels)}
            return np.array([-1 if m else pos[_decode(v)] for v, m in zip(vals, mask)]), levels
        raise Refused(f"{where}.{name} is a {_decode(node.attrs.get('encoding-type', 'group'))}, which "
                      f"this step does not carry", f"carry a categorical, string or numeric column")
    raw = node[()]
    if raw.dtype.kind in "OSU":
        vals = [_decode(v) for v in raw]
        levels = sorted(set(vals))
        pos = {v: i for i, v in enumerate(levels)}
        return np.array([pos[v] for v in vals], dtype=np.int64), levels
    return raw, None


def index_of(frame):
    name = _decode(frame.attrs.get("_index", "_index"))
    return frame[name]


def unique_symbols(symbols):
    """(written names, [(position, symbol, written)] for every repeat) by DUPLICATES."""
    taken, seen, out, dups = set(symbols), {}, [], []
    empty = [i for i, s in enumerate(symbols) if not str(s).strip() or str(s) == "nan"]
    if empty:
        raise Refused(f"{len(empty)} gene(s) carry no symbol (the first at gene position {empty[0]})",
                      "name a symbol column that names every gene")
    for i, s in enumerate(symbols):
        k = seen.get(s, 0)
        seen[s] = k + 1
        if k == 0:
            out.append(s)
            continue
        name = f"{s}-{k}"
        if name in taken:
            raise Refused(f"the symbol {s!r} repeats, and its repeat's name {name!r} is already another "
                          f"gene's symbol; by the stated rule ({DUPLICATES}) two genes would share it",
                          "name a symbol column whose repeats do not collide")
        taken.add(name)
        out.append(name)
        dups.append((i, s, name))
    return out, dups


def chunks(indptr, most):
    """[(first row, end row)] covering every row, each holding at most `most` stored values
    (a row holding more is a chunk on its own)."""
    import numpy as np
    out, a, n = [], 0, len(indptr) - 1
    while a < n:
        b = int(np.searchsorted(indptr, indptr[a] + most, side="right")) - 1
        b = min(max(b, a + 1), n)
        out.append((a, b))
        a = b
    return out


def gather(starts, lengths):
    """The stored-value positions of rows given by their starts and lengths, rows in that order."""
    import numpy as np
    total = int(lengths.sum())
    if total == 0:
        return np.zeros(0, dtype=np.int64)
    first = np.concatenate(([0], np.cumsum(lengths)[:-1]))
    return np.repeat(starts - first, lengths) + np.arange(total, dtype=np.int64)


def not_counts(values):
    """A mask of the stored values that are not non-negative integers."""
    import numpy as np
    if values.dtype.kind in "iu":
        return values < 0
    if values.dtype.kind != "f":
        return np.ones(values.shape, dtype=bool)
    with np.errstate(invalid="ignore"):
        return ~np.isfinite(values) | (values < 0) | (values != np.floor(values))


# ---------------------------------------------------------------------------- writing a part
def _strings(group, name, values):
    import h5py
    ds = group.create_dataset(name, data=[_decode(v) for v in values], dtype=h5py.string_dtype("utf-8"))
    _enc(ds, "string-array")


def _frame(group, index, columns):
    """An anndata dataframe: `index` its index, `columns` {name: (codes, levels) | (values, None)}."""
    import numpy as np
    _enc(group, "dataframe")
    group.attrs["_index"] = "_index"
    group.attrs["column-order"] = list(columns)
    if index is not None:
        _strings(group, "_index", index)
    for name, (vals, levels) in columns.items():
        if levels is None:
            if vals.dtype.kind in "OSU":
                _strings(group, name, vals)
            else:
                _enc(group.create_dataset(name, data=vals), "array")
            continue
        used = np.unique(vals[vals >= 0])
        codes = np.where(vals >= 0, np.searchsorted(used, vals), -1)
        g = group.create_group(name)
        _enc(g, "categorical")
        g.attrs["ordered"] = False
        g.create_dataset("codes", data=codes.astype(np.int8 if len(used) < 127 else np.int32))
        _strings(g, "categories", [levels[u] for u in used])


def open_part(path, n_var, data_dtype, ind_dtype):
    import h5py
    with h5py.File(path, "w") as f:
        _enc(f, "anndata")
        x = f.create_group("X")
        _enc(x, "csr_matrix")
        x.attrs["shape"] = [0, n_var]
        for name, dt in (("data", data_dtype), ("indices", ind_dtype)):
            x.create_dataset(name, shape=(0,), maxshape=(None,), dtype=dt, chunks=(1 << 16,),
                             compression="gzip")
        f.create_group("obs").create_dataset("_index", shape=(0,), maxshape=(None,), chunks=(1 << 12,),
                                             dtype=h5py.string_dtype("utf-8"))


def append_part(path, data, indices, barcodes):
    import h5py
    with h5py.File(path, "a") as f:
        for name, vals in (("data", data), ("indices", indices), ("_index", barcodes)):
            ds = f["obs/_index"] if name == "_index" else f["X"][name]
            n = ds.shape[0]
            ds.resize((n + len(vals),))
            ds[n:] = vals


def close_part(path, lengths, n_var, columns, symbols, ids, uns):
    import h5py
    import numpy as np
    with h5py.File(path, "a") as f:
        x = f["X"]
        x.create_dataset("indptr", data=np.concatenate(([0], np.cumsum(lengths))).astype(np.int64))
        x.attrs["shape"] = [int(len(lengths)), int(n_var)]
        obs = f["obs"]
        _enc(obs["_index"], "string-array")
        _frame(obs, None, columns)
        _frame(f.create_group("var"), symbols, {GENE_IDS: (np.array(ids, dtype=object), None)})
        for g in EMPTY_GROUPS:
            _enc(f.create_group(g), "dict")
        u = f.create_group("uns")
        _enc(u, "dict")
        s = u.create_dataset("sch_parts", data=json.dumps(uns, sort_keys=True),
                             dtype=h5py.string_dtype("utf-8"))
        _enc(s, "string")


# ---------------------------------------------------------------------------- the step
def split(obj, out, params, context):
    """Write the parts and the samplesheet into `out`; return the record. Raises Refused."""
    import h5py
    import numpy as np
    t0 = time.time()
    lib_col, rep_col = str(params["library"]), str(params["replicate"])
    counts, sym_col = str(params["counts"]), str(params["symbols"])
    carry = [str(c) for c in (params.get("carry") or [])]
    sheet_col = str(params["column"])
    most = int(params.get("chunk_values") or CHUNK_VALUES)
    parts = out / "parts"
    with h5py.File(obj, "r") as f:
        slot, var, var_name = slot_of(f, counts)
        obs = f["obs"]
        names = index_of(obs)
        n_obs, n_var = int(names.shape[0]), int(index_of(var).shape[0])
        shape = [int(v) for v in slot.attrs.get("shape", slot.attrs.get("h5sparse_shape", (-1, -1)))]
        if shape != [n_obs, n_var]:
            raise Refused(f"the counts slot {counts!r} is {shape[0]} x {shape[1]}, and the object holds "
                          f"{n_obs} observations and {var_name} {n_var} genes",
                          "deliver an object whose counts slot is its observations by its genes")
        cols = {}
        for c in [lib_col, rep_col] + [c for c in carry if c not in (lib_col, rep_col)]:
            cols[c] = column(obs, c, "the object's obs")
        lib_codes, libs = cols[lib_col]
        rep_codes, reps = cols[rep_col]
        for c, (vals, levels) in ((lib_col, cols[lib_col]), (rep_col, cols[rep_col])):
            if levels is None:
                raise Refused(f"obs.{c} is numeric; a library or a replicate is a name",
                              f"name a categorical or string column for {c}")
            if (vals < 0).any():
                raise Refused(f"obs.{c} names nothing for {int((vals < 0).sum())} observation(s)",
                              f"every observation's {c} is declared, or it is not delivered")
        present = sorted(set(int(v) for v in np.unique(lib_codes)))
        bad = [libs[i] for i in present if not SAFE_NAME.fullmatch(libs[i])]
        lowered = [libs[i].lower() for i in present]
        if bad or len(set(lowered)) != len(lowered):
            raise Refused(f"library name(s) {', '.join(map(repr, bad[:5])) or '(two differing by case)'} "
                          f"cannot name a file; a part is never renamed", "deliver file-safe library names")
        sym_codes, sym_levels = column(var, sym_col, f"the counts slot's genes ({var_name})")
        symbols = ([sym_levels[c] if c >= 0 else "" for c in sym_codes] if sym_levels is not None
                   else [str(v) for v in sym_codes])
        written, dups = unique_symbols(symbols)
        ids = [_decode(v) for v in index_of(var)[()]]
        indptr = slot["indptr"][()].astype(np.int64)
        data_ds, ind_ds = slot["data"], slot["indices"]
        parts.mkdir(parents=True, exist_ok=False)
        files = {i: parts / f"{libs[i]}.h5ad" for i in present}
        for p in files.values():
            open_part(p, n_var, data_ds.dtype, ind_ds.dtype)
        lengths = {i: [] for i in present}
        rows = {i: [] for i in present}
        sums = {i: 0 for i in present}
        plan = chunks(indptr, most)
        for a, b in plan:
            s, e = int(indptr[a]), int(indptr[b])
            data, ind = data_ds[s:e], ind_ds[s:e]
            wrong = not_counts(data)
            if wrong.any():
                k = int(np.argmax(wrong))
                r = int(np.searchsorted(indptr, s + k, side="right")) - 1
                raise Refused(f"the counts slot {counts!r} holds {data[k].item()!r} for observation "
                              f"{_decode(names[r])!r}, gene {ids[int(ind[k])]!r}: a stored value that is "
                              f"not a non-negative integer ({int(wrong.sum())} in rows {a}-{b - 1} alone); "
                              f"counts are integers, and a normalized slot is not counts",
                              "object.counts: the slot holding the integer counts (often raw/X)")
            codes = lib_codes[a:b]
            order = np.argsort(codes, kind="stable")
            lens = np.diff(indptr[a:b + 1])[order]
            pos = gather(indptr[a:b][order] - s, lens)
            d_s, i_s = data[pos], ind[pos]
            bcs = names[a:b][order]
            sc = codes[order]
            cum = np.concatenate(([0], np.cumsum(lens)))
            for lib in np.unique(sc):
                lo, hi = int(np.searchsorted(sc, lib, "left")), int(np.searchsorted(sc, lib, "right"))
                v0, v1 = int(cum[lo]), int(cum[hi])
                append_part(files[int(lib)], d_s[v0:v1], i_s[v0:v1], bcs[lo:hi])
                lengths[int(lib)].append(lens[lo:hi])
                rows[int(lib)].append(a + order[lo:hi])
                sums[int(lib)] += float(d_s[v0:v1].sum(dtype=np.float64))
        record_parts, lib_rows, rep_libs = {}, [], {}
        uns_base = {"step": "parts", "object": str(obj), "counts": counts, "symbols": f"{var_name}.{sym_col}",
                    "duplicates": DUPLICATES}
        for i in present:
            ln = np.concatenate(lengths[i]) if lengths[i] else np.zeros(0, dtype=np.int64)
            rw = np.concatenate(rows[i]) if rows[i] else np.zeros(0, dtype=np.int64)
            part_cols = {c: (vals[rw], levels) for c, (vals, levels) in cols.items()}
            close_part(files[i], ln, n_var, part_cols, written, ids, {**uns_base, "library": libs[i]})
            files[i].chmod(0o444)
            mine = sorted({reps[c] for c in np.unique(rep_codes[rw])})
            for r in mine:
                rep_libs.setdefault(r, set()).add(libs[i])
            levels_in = {c: len(np.unique(vals[rw])) for c, (vals, lv) in cols.items()
                         if lv is not None and c not in (lib_col, rep_col)}
            lib_rows.append([libs[i], len(rw), int(ln.sum()), sums[i], len(mine), "|".join(mine)]
                            + [levels_in[c] for c in sorted(levels_in)])
            record_parts[libs[i]] = {"path": f"parts/{files[i].name}", "cells": int(len(rw)),
                                     "stored": int(ln.sum())}
        carried_levels = sorted(c for c, (v, lv) in cols.items() if lv is not None and c not in (lib_col, rep_col))
    # the samplesheet the next stage mounts: one row per library, every context axis as a column
    head = [SHEET_LIBRARY] + ([lib_col] if lib_col != SHEET_LIBRARY else []) + [sheet_col] + list(context)
    with open(parts / "samplesheet.tsv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(head)
        for i in present:
            w.writerow([libs[i]] + ([libs[i]] if lib_col != SHEET_LIBRARY else []) + [str(files[i].resolve())]
                       + [context[k] for k in context])
    (parts / "samplesheet.tsv").chmod(0o444)
    tables = out / "tables"
    tables.mkdir(exist_ok=True)
    _tsv(tables / "libraries.tsv", [lib_col, "cells", "stored", "counts_sum", f"n_{rep_col}", rep_col]
         + [f"n_{c}" for c in carried_levels], lib_rows)
    rep_cells = np.bincount(rep_codes, minlength=len(reps))
    _tsv(tables / "replicates.tsv", [rep_col, "cells", f"n_{lib_col}", lib_col],
         [[r, int(rep_cells[k]), len(rep_libs.get(r, ())), "|".join(sorted(rep_libs.get(r, ())))]
          for k, r in enumerate(reps) if rep_cells[k]])
    _tsv(tables / "duplicate_symbols.tsv", ["position", GENE_IDS, "symbol", "written"],
         [[p, ids[p], s, n] for p, s, n in dups])
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return {"object": str(obj), "counts": counts, "dtype": str(data_ds.dtype), "symbols": f"{var_name}.{sym_col}",
            "library": lib_col, "replicate": rep_col, "carry": carry, "column": sheet_col,
            "n_obs": n_obs, "n_var": n_var, "n_stored": int(indptr[-1]), "n_libraries": len(present),
            "n_replicates": int((rep_cells > 0).sum()),
            "libraries_holding_several_replicates": sum(1 for r in lib_rows if r[4] > 1),
            "replicates_in_several_libraries": sum(1 for v in rep_libs.values() if len(v) > 1),
            "duplicates_rule": DUPLICATES, "duplicates": [{"position": p, GENE_IDS: ids[p], "symbol": s,
                                                           "written": n} for p, s, n in dups],
            "chunk_values": most, "chunks": len(plan), "wall_s": round(time.time() - t0, 3),
            # ru_maxrss is bytes on macOS and kilobytes on Linux
            "peak_rss_kb": int(peak / 1024) if sys.platform == "darwin" else int(peak),
            "peak_rss_by": "getrusage(RUSAGE_SELF).ru_maxrss of this step's own process",
            "parts": record_parts, "samplesheet": "parts/samplesheet.tsv"}


def _tsv(path, head, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(head)
        w.writerows(rows)


def _protocol():
    """The stdlib-only protocol helper: where the kernel says it is, or a copy beside this file."""
    for c in (os.environ.get("SCH_PROTOCOL"), Path(__file__).with_name("protocol.py")):
        if c and Path(c).exists():
            spec = importlib.util.spec_from_file_location("sch_protocol", str(c))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    sys.exit("protocol.py not found; set SCH_PROTOCOL or copy sch/plugin/protocol.py beside run.py")


def main():
    run = _protocol().Run.from_argv()
    out = Path(run.inp["out_dir"])
    params = dict(run.params)
    need = [k for k in DECLARED if not params.get(k)]
    if need:
        return run.refuse(f"no {', '.join(need)} declared; the step reads the request's declarations "
                          f"by name and guesses none", "declare object: {counts, symbols} and keys.replicate")
    obs = run.inp.get("observations") or {}
    if not obs.get("parts"):
        return run.refuse("the stack's observations are not a manifest naming the object",
                          "the driver mounts this step over a one-row manifest of the request's object")
    with open(obs["path"], newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    if len(rows) != 1:
        return run.refuse(f"the manifest names {len(rows)} objects; the step reads one", "name one object")
    p = Path(rows[0][obs["parts"]])
    obj = p if p.is_absolute() else Path(obs["path"]).parent / p
    try:
        import h5py  # noqa: F401
        import numpy  # noqa: F401
    except ImportError as e:
        return run.refuse(f"the step streams the object through h5py and numpy, and this interpreter "
                          f"has no {e.name}", "run the kernel where h5py and numpy are installed")
    try:
        rec = split(obj.resolve(), out, params, dict(run.inp.get("profile_context") or {}))
    except Refused as e:
        shutil.rmtree(out / "parts", ignore_errors=True)       # no part of a refused object is kept
        return run.refuse(e.reason, fix=e.fix)
    (out / "PARTS.json").write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8")
    for t in TABLES:
        run.table_at(f"tables/{t}.tsv")
    for lib, part in rec["parts"].items():
        run.object_at(lib, part["path"])
    for k in NUMBERS:
        run.number(k, rec[k])
    run.number("n_duplicate_symbols", len(rec["duplicates"]))
    run.answer(hands_on={"libraries": {lib: part["path"] for lib, part in rec["parts"].items()},
                         "samplesheet": rec["samplesheet"]},
               record="PARTS.json", duplicates_rule=DUPLICATES)
    return run.finish(headline=f"{rec['n_libraries']} parts of {rec['n_obs']:,} observations x {rec['n_var']:,} "
                               f"genes from {rec['counts']} ({rec['n_stored']:,} stored values, {rec['chunks']} "
                               f"chunks, peak {rec['peak_rss_kb'] // 1024:,} MB)")


if __name__ == "__main__":
    sys.exit(main())
