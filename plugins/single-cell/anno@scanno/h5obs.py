"""obs, read from an `.h5ad` with h5py alone: the encodings anndata writes a dataframe in.

The kernel already reads a part's identities this way (`H5adReader`). Neither needs anndata, so the
harness's own interpreter can read any tool's objects.

    index(path)           -> [str]            the obs names
    columns(path)         -> [str]            the obs columns, in the dataframe's column-order
    column(path, name)    -> [str | None]     one column, every value as text, None where missing

TEXT, because the harness's columns are text (`<identity>,<value>`), and because whether a tool
rewrote a column must not depend on one copy being stored as a category and the other as an
integer. A value is written as numpy writes its own scalar (`str`): the shortest text that reads
back as the same value of that dtype. MISSING is None: a NaN, a categorical code -1, a masked entry
of a nullable array.

An encoding not listed in ENCODINGS raises UnreadableColumn, naming the column and the encoding. A
column this reader cannot read is never skipped: a skipped column is a label that silently leaves
the layer.
"""
from __future__ import annotations

ENCODINGS = ("array", "string-array", "categorical", "nullable-integer", "nullable-boolean",
             "nullable-string-array")


class UnreadableColumn(ValueError):
    pass


def _open(path):
    import h5py
    return h5py.File(path, "r")


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


def _values(path, name, node):
    """Every value of one obs node, as text or None, by its encoding."""
    import h5py
    enc = _attr(node, "encoding-type")
    if isinstance(node, h5py.Dataset):
        if enc not in (None, "array", "string-array"):
            raise UnreadableColumn(f"{path}: obs column {name!r} is a dataset encoded {enc!r}; this "
                                   f"reader knows {', '.join(ENCODINGS)}")
        return [_text(x) for x in node[()]]
    keys = set(node.keys())
    if enc == "categorical" or (enc is None and {"categories", "codes"} <= keys):
        cats = _values(path, f"{name}/categories", node["categories"])
        return [cats[c] if c >= 0 else None for c in node["codes"][()].tolist()]
    if enc in ("nullable-integer", "nullable-boolean", "nullable-string-array") or \
            (enc is None and {"values", "mask"} <= keys):
        vals = [_text(x) for x in node["values"][()]]
        if "mask" not in keys:
            return vals
        return [None if m else v for v, m in zip(vals, node["mask"][()].tolist())]
    raise UnreadableColumn(f"{path}: obs column {name!r} is encoded {enc or 'without a type'!r} "
                           f"(keys {sorted(keys)}); this reader knows {', '.join(ENCODINGS)}")


def index(path) -> list:
    with _open(path) as f:
        obs = f["obs"]
        key = str(_attr(obs, "_index", "_index"))
        return [v if v is not None else "" for v in _values(path, "the index", obs[key])]


def columns(path) -> list:
    with _open(path) as f:
        obs = f["obs"]
        order = obs.attrs.get("column-order", [])
        named = [c.decode() if isinstance(c, bytes) else str(c) for c in list(order)]
        key = str(_attr(obs, "_index", "_index"))
        # a column stored but not in column-order is still a column the object carries
        rest = sorted(k for k in obs.keys() if k not in named and k != key and not k.startswith("__"))
        return named + rest


def column(path, name) -> list:
    with _open(path) as f:
        obs = f["obs"]
        if name not in obs:
            raise UnreadableColumn(f"{path}: no obs column {name!r}")
        return _values(path, name, obs[name])
