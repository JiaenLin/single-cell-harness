"""An `.h5ad`, read with h5py alone: obs, obsm and obsp, in the encodings anndata writes them in.

The kernel reads a part's identities this way (`H5adReader`), and so does anno@scanno for obs
(`h5obs.py`, whose obs decoding this repeats rather than imports: a plugin is a directory the
kernel runs, and one plugin reaching into another's would make each the other's dependency).
Nothing here needs anndata, so the harness's own interpreter can read the tool's object.

Every function takes an open `h5py.File`:

    index(f)              -> [str]              the obs names
    columns(f)            -> [str]              obs columns, in the dataframe's column-order
    column(f, name)       -> [str | None]       one obs column, every value as text, None if missing
    keys(f, "obsm"|"obsp") -> [str]             what the object carries there
    array(f, key)         -> numpy array        one obsm entry, dense, as stored
    graph(f, key)         -> Graph              one obsp entry, as compressed sparse rows or columns

obs values are TEXT, as anno@scanno reads them: whether a tool rewrote a column must not depend on
one copy being stored as a category and the other as an integer.

An encoding not listed here raises Unreadable, naming the entry and its encoding. An entry this
reader cannot read is never skipped: a skipped embedding is a result that silently leaves the layer.
"""
from __future__ import annotations

import json

OBS_ENCODINGS = ("array", "string-array", "categorical", "nullable-integer", "nullable-boolean",
                 "nullable-string-array")
SPARSE = ("csr_matrix", "csc_matrix")


class Unreadable(ValueError):
    pass


class Graph:
    """One obsp entry: `fmt` csr (rows compressed) or csc, its arrays as stored, and its shape."""

    def __init__(self, fmt, data, indices, indptr, shape):
        self.fmt, self.data, self.indices, self.indptr = fmt, data, indices, indptr
        self.shape = tuple(int(x) for x in shape)

    def triples(self, perm=None):
        """(row, col, value) of every stored entry, sorted, with rows and columns renumbered by
        `perm` (old position -> new) when one is given: a graph compared by identity, not position."""
        import numpy as np
        n_major = len(self.indptr) - 1
        major = np.repeat(np.arange(n_major), np.diff(self.indptr))
        rows, cols = (major, self.indices) if self.fmt == "csr" else (self.indices, major)
        if perm is not None:
            rows, cols = perm[rows], perm[cols]
        order = np.lexsort((cols, rows))
        return rows[order], cols[order], self.data[order]


def _attr(node, key, default=None):
    v = node.attrs.get(key, default)
    return v.decode() if isinstance(v, bytes) else v


def _text(x):
    """One scalar as text, or None when it is missing."""
    if isinstance(x, bytes):
        return x.decode()
    if isinstance(x, str):
        return x
    if x is None:
        return None
    try:
        if x != x:                               # NaN is the one value unequal to itself
            return None
    except (TypeError, ValueError):
        pass
    return str(x)


def _values(f, name, node):
    """Every value of one obs node, as text or None, by its encoding."""
    import h5py
    enc = _attr(node, "encoding-type")
    if isinstance(node, h5py.Dataset):
        if enc not in (None, "array", "string-array"):
            raise Unreadable(f"{f.filename}: obs column {name!r} is a dataset encoded {enc!r}; this "
                             f"reader knows {', '.join(OBS_ENCODINGS)}")
        return [_text(x) for x in node[()]]
    keys = set(node.keys())
    if enc == "categorical" or (enc is None and {"categories", "codes"} <= keys):
        cats = _values(f, f"{name}/categories", node["categories"])
        return [cats[c] if c >= 0 else None for c in node["codes"][()].tolist()]
    if enc in ("nullable-integer", "nullable-boolean", "nullable-string-array") or \
            (enc is None and {"values", "mask"} <= keys):
        vals = [_text(x) for x in node["values"][()]]
        if "mask" not in keys:
            return vals
        return [None if m else v for v, m in zip(vals, node["mask"][()].tolist())]
    raise Unreadable(f"{f.filename}: obs column {name!r} is encoded {enc or 'without a type'!r} "
                     f"(keys {sorted(keys)}); this reader knows {', '.join(OBS_ENCODINGS)}")


def uns_scalar(f, *path):
    """One scalar under `uns` (`uns_scalar(f, "scintegrate", "provenance", "state_version")`), with its
    type as written: an integer dataset is an int, a float one a float (2.0 stays 2.0), a boolean a
    bool, text a str. A dict anndata had to write as JSON text is read through. None when absent."""
    import h5py
    node = f.get("uns")
    for i, key in enumerate(path):
        if isinstance(node, h5py.Dataset):                       # a dict kept as JSON text
            try:
                d = json.loads(_text(node[()]) or "")
            except ValueError:
                return None
            for k in path[i:]:
                if not isinstance(d, dict) or k not in d:
                    return None
                d = d[k]
            return d
        node = node.get(key) if node is not None else None
    if not isinstance(node, h5py.Dataset) or node.shape != ():
        return None
    v, kind = node[()], node.dtype.kind
    return bool(v) if kind == "b" else int(v) if kind in "iu" else float(v) if kind == "f" else _text(v)


def index(f) -> list:
    obs = f["obs"]
    key = str(_attr(obs, "_index", "_index"))
    return [v if v is not None else "" for v in _values(f, "the index", obs[key])]


def columns(f) -> list:
    obs = f["obs"]
    named = [c.decode() if isinstance(c, bytes) else str(c) for c in list(obs.attrs.get("column-order", []))]
    key = str(_attr(obs, "_index", "_index"))
    # a column stored but not in column-order is still a column the object carries
    rest = sorted(k for k in obs.keys() if k not in named and k != key and not k.startswith("__"))
    return named + rest


def column(f, name) -> list:
    obs = f["obs"]
    if name not in obs:
        raise Unreadable(f"{f.filename}: no obs column {name!r}")
    return _values(f, name, obs[name])


def keys(f, where) -> list:
    return sorted(f[where].keys()) if where in f else []


def array(f, key):
    """One obsm entry as a dense array of its stored dtype. A sparse entry is made dense, since an
    embedding is observations x k with k small; a dataframe entry is refused by name."""
    import h5py
    import numpy as np
    node = f["obsm"][key]
    enc = _attr(node, "encoding-type")
    if isinstance(node, h5py.Dataset):
        if enc not in (None, "array"):
            raise Unreadable(f"{f.filename}: obsm {key!r} is a dataset encoded {enc!r}; this reader "
                             f"knows a dense array, {' and '.join(SPARSE)}")
        return node[()]
    if enc in SPARSE:
        g = graph_of(f, node, f"obsm {key!r}")
        out = np.zeros(g.shape, dtype=g.data.dtype)
        r, c, v = g.triples()
        out[r, c] = v
        return out
    raise Unreadable(f"{f.filename}: obsm {key!r} is encoded {enc or 'without a type'!r}; this reader "
                     f"knows a dense array, {' and '.join(SPARSE)}")


def graph_of(f, node, what):
    import h5py
    enc = _attr(node, "encoding-type")
    if isinstance(node, h5py.Group) and enc in SPARSE:
        shape = node.attrs.get("shape")
        if shape is None or not {"data", "indices", "indptr"} <= set(node.keys()):
            raise Unreadable(f"{f.filename}: {what} is {enc} without data, indices, indptr and shape")
        return Graph(enc[:3], node["data"][()], node["indices"][()], node["indptr"][()], shape)
    raise Unreadable(f"{f.filename}: {what} is encoded {enc or 'without a type'!r}; this reader knows "
                     f"{' and '.join(SPARSE)}")


def graph(f, key) -> Graph:
    return graph_of(f, f["obsp"][key], f"obsp {key!r}")
