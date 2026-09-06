"""The dataset service: observations, contributions, and materialisation.

D2  Nothing writes to observations. The file is opened read-only and its digest is checked by
    the A1 companion after every plugin run.
D4  A removal is a mask, never a delete. A mask is a whole keep-vector over every identity.
§6  Observation-level results merge by identity, never by position. A contribution covering a
    different identity set is refused with both counts; one covering fewer is filled with the
    profile's missing value, and the coverage is declared.
D6  Materialisation is a fold over the ordered contributions; the key is computed by the
    registry and the cache is exact-tuple.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from ..core import Service


class DatasetError(ValueError):
    pass


def file_digest(path, chunk=1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            b = fh.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


# ---------------------------------------------------------------------------- readers
class Reader:
    """How a profile reads identity and inventory from the observation file. Never writes."""

    def identities(self, path) -> list[str]:
        raise NotImplementedError

    def inventory(self, path) -> dict:
        """What the observations themselves provide: {slot: [names]}."""
        raise NotImplementedError


class CsvReader(Reader):
    def __init__(self, id_column: str):
        self.id_column = id_column

    def _rows(self, path):
        with open(path, newline="", encoding="utf-8") as fh:
            r = csv.DictReader(fh)
            return r.fieldnames or [], list(r)

    def identities(self, path):
        header, rows = self._rows(path)
        col = self.id_column if self.id_column in header else (header[0] if header else None)
        if col is None:
            raise DatasetError(f"{path}: empty CSV")
        ids = [row[col] for row in rows]
        if len(set(ids)) != len(ids):
            raise DatasetError(f"{path}: identities are not unique in column {col!r}")
        return ids

    def inventory(self, path):
        header, _ = self._rows(path)
        col = self.id_column if self.id_column in header else header[0]
        return {"column": [h for h in header if h != col]}


class H5adReader(Reader):
    """Identity and inventory from an .h5ad, through h5py, without loading the matrix."""

    def _open(self, path):
        try:
            import h5py  # noqa: F401
        except ImportError as e:
            raise DatasetError("reading an .h5ad needs h5py in the host environment; "
                               "install h5py, or materialise with a plugin that has it") from e
        import h5py
        return h5py.File(path, "r")

    @staticmethod
    def read_strings(node):
        """A string array however this anndata encoding wrote it: a dataset, a nullable-string
        group with `values`, or a categorical group with `categories` and `codes`."""
        import h5py
        if isinstance(node, h5py.Group):
            if "categories" in node and "codes" in node:
                cats = [c.decode() if isinstance(c, bytes) else str(c) for c in node["categories"][()]]
                return [cats[c] if c >= 0 else None for c in node["codes"][()]]
            if "values" in node:
                raw = node["values"][()]
            else:
                raise DatasetError(f"unreadable string encoding: group with keys {list(node.keys())}")
        else:
            raw = node[()]
        return [x.decode() if isinstance(x, bytes) else str(x) for x in raw]

    def identities(self, path):
        with self._open(path) as f:
            obs = f["obs"]
            idx = obs.attrs.get("_index", "_index")
            if isinstance(idx, bytes):
                idx = idx.decode()
            ids = self.read_strings(obs[str(idx)])
        if len(set(ids)) != len(ids):
            raise DatasetError(f"{path}: obs identities are not unique; make them unique within "
                               f"the identity scope before mounting")
        return ids

    def inventory(self, path):
        with self._open(path) as f:
            obs_keys = [k for k in f["obs"].keys() if not k.startswith("_")]
            layers = list(f["layers"].keys()) if "layers" in f else []
            obsm = list(f["obsm"].keys()) if "obsm" in f else []
            obsp = list(f["obsp"].keys()) if "obsp" in f else []
        return {"column": obs_keys, "matrix": layers, "embedding": obsm, "graph": obsp}


# ---------------------------------------------------------------------------- contributions
@dataclass
class Contribution:
    plugin: str
    slot: str
    name: str
    path: Path
    coverage: int = 0
    meta: dict = field(default_factory=dict)

    def capability(self) -> str:
        return f"{self.slot}/{self.name}"


def read_keyed_csv(path, id_field: str) -> dict:
    """`id,value` (or `id,keep,reason`) → {id: row}. Refuses duplicate identities."""
    out = {}
    with open(path, newline="", encoding="utf-8") as fh:
        r = csv.DictReader(fh)
        if not r.fieldnames or id_field not in r.fieldnames:
            raise DatasetError(f"{path}: no identity column {id_field!r} (header {r.fieldnames})")
        for row in r:
            k = row[id_field]
            if k in out:
                raise DatasetError(f"{path}: identity {k!r} appears twice")
            out[k] = row
    return out


# ---------------------------------------------------------------------------- the view
class View:
    """A materialisation. Read-only by construction and disposable: deleting it loses nothing."""

    def __init__(self, ids: list, keep: dict, columns: dict, masks: dict, path: Path | None):
        self._ids = tuple(ids)
        self._keep = dict(keep)
        self._columns = {k: dict(v) for k, v in columns.items()}
        self._masks = {k: dict(v) for k, v in masks.items()}
        self.path = path

    @property
    def ids(self) -> tuple:
        return self._ids

    @property
    def kept(self) -> list:
        return [i for i in self._ids if self._keep.get(i, True)]

    @property
    def n(self) -> int:
        return len(self.kept)

    @property
    def n_total(self) -> int:
        return len(self._ids)

    def keep(self, i) -> bool:
        return bool(self._keep.get(i, True))

    def column(self, name) -> dict:
        return dict(self._columns.get(name, {}))

    def columns(self) -> list:
        return sorted(self._columns)

    def masks(self) -> dict:
        return {k: dict(v) for k, v in self._masks.items()}

    def digest(self) -> str:
        """Over the kept ids, every mask and every column, so a mount that changes nothing a
        consumer sees produces the same digest and a mount that does changes it."""
        h = hashlib.sha256()
        for i in self.kept:
            h.update(i.encode())
            h.update(b"\0")
        for k in sorted(self._masks):
            h.update(k.encode())
            for i in self._ids:
                h.update(b"1" if self._masks[k].get(i, True) else b"0")
        for k in sorted(self._columns):
            h.update(k.encode())
            col = self._columns[k]
            for i in self._ids:
                v = col.get(i)
                h.update(("" if v is None else str(v)).encode())
                h.update(b"\0")
        return h.hexdigest()[:16]


# ---------------------------------------------------------------------------- the service
class Dataset(Service):
    def __init__(self, observations, profile, stack_dir, design=None):
        self.observations = Path(observations).resolve()
        self.profile = profile
        self.stack_dir = Path(stack_dir)
        self.design = Path(design).resolve() if design else None
        self.reader = self._reader()
        self._ids = None
        self._digest = None
        self._inventory = None
        self.contributions: list[Contribution] = []

    # ----------------------------------------------------------- observations
    def _reader(self) -> Reader:
        m = self.profile.materialiser
        idc = self.profile.identity.get("column", "id")
        if m == "csv":
            return CsvReader(idc)
        if m == "h5ad":
            return H5adReader()
        raise DatasetError(f"profile {self.profile.id} names materialiser {m!r}, which this kernel "
                           f"does not ship; known: csv, h5ad")

    @property
    def ids(self) -> list:
        if self._ids is None:
            if not self.observations.exists():
                raise DatasetError(f"observations not found: {self.observations}")
            self._ids = self.reader.identities(self.observations)
        return self._ids

    def digest(self) -> str:
        """Content digest of the observation file, cached beside the stack. D2's witness."""
        if self._digest is None:
            cache = self.stack_dir / "observations.sha256"
            st = self.observations.stat()
            if cache.exists():
                try:
                    rec = json.loads(cache.read_text())
                    if rec.get("size") == st.st_size and rec.get("mtime") == st.st_mtime:
                        self._digest = rec["sha256"]
                except (ValueError, KeyError):
                    pass
            if self._digest is None:
                self._digest = file_digest(self.observations)
                cache.write_text(json.dumps({"sha256": self._digest, "size": st.st_size,
                                             "mtime": st.st_mtime, "path": str(self.observations)}))
        return self._digest

    def digest_now(self) -> str:
        """Recomputed, uncached. What the A1 companion compares against `digest()`."""
        return file_digest(self.observations)

    def inventory(self) -> dict:
        if self._inventory is None:
            self._inventory = self.reader.inventory(self.observations)
        return self._inventory

    def observation_capabilities(self) -> list:
        caps = ["observations/raw"]
        for slot, names in self.inventory().items():
            caps.extend(f"{slot}/{n}" for n in names)
        return caps

    # ----------------------------------------------------------- contributions
    def add(self, c: Contribution):
        self.contributions.append(c)

    def remove(self, plugin: str) -> list:
        gone = [c for c in self.contributions if c.plugin == plugin]
        self.contributions = [c for c in self.contributions if c.plugin != plugin]
        return gone

    def contributions_of(self, plugin: str) -> list:
        return [c for c in self.contributions if c.plugin == plugin]

    def provided_capabilities(self) -> list:
        return [c.capability() for c in self.contributions]

    def check_identity(self, path, id_field, whole: bool, view_n: int | None = None) -> dict:
        """Merge-by-identity precondition. Returns the keyed rows or raises with both counts.

        A mask is a WHOLE value: it covers every observation, or every row of the view the
        plugin was handed (rows already masked beneath it carry no opinion, which folds as
        keep). Anything else is refused with both counts, never truncated or padded.
        """
        rows = read_keyed_csv(path, id_field)
        ids = set(self.ids)
        foreign = [k for k in rows if k not in ids]
        if foreign:
            raise DatasetError(f"{path}: {len(foreign)} identities are not observations "
                               f"(first: {foreign[:3]}); results merge by identity, never position")
        if whole and len(rows) != len(ids) and (view_n is None or len(rows) != view_n):
            raise DatasetError(f"{path}: a mask must cover every observation: covers "
                               f"{len(rows)} of {len(ids)}" + (f" (the view it saw had {view_n})" if view_n else ""))
        return rows

    # ----------------------------------------------------------- materialisation
    def fold(self, contributions: Iterable[Contribution]) -> tuple:
        """The pure fold: (keep, columns, masks) from an ordered list of contributions."""
        idc = self.profile.identity.get("column", "id")
        keep = {i: True for i in self.ids}
        columns, masks = {}, {}
        for c in contributions:
            if c.slot == "mask":
                rows = read_keyed_csv(c.path, idc)
                m = {i: rows[i]["keep"] in ("1", "true", "True") for i in self.ids if i in rows}
                masks[c.name] = m
                for i, k in m.items():
                    if not k:
                        keep[i] = False
            elif c.slot == "column":
                rows = read_keyed_csv(c.path, idc)
                columns[c.name] = {i: (rows[i]["value"] if rows[i]["value"] != "" else None)
                                   for i in rows}
        return keep, columns, masks

    def materialise(self, contributions, out_dir, filtered=True) -> View:
        keep, columns, masks = self.fold(contributions)
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        m = self.profile.materialiser
        if m == "csv":
            path = self._write_csv(out_dir, keep, columns, masks, filtered)
        else:
            path = self._write_h5ad(out_dir, keep, columns, masks, contributions, filtered)
        view = View(self.ids, keep, columns, masks, path)
        self._write_readme(out_dir, view, path)
        return view

    def _write_csv(self, out_dir, keep, columns, masks, filtered):
        idc = self.profile.identity.get("column", "id")
        path = out_dir / ("view.csv" if filtered else "view_full.csv")
        with open(self.observations, newline="", encoding="utf-8") as fh:
            r = csv.DictReader(fh)
            header = list(r.fieldnames or [])
            rows = list(r)
        idcol = idc if idc in header else header[0]
        extra = sorted(columns)
        mask_cols = sorted(masks)
        out_header = header + [f"column__{c}" for c in extra] + ["keep"] + [f"mask__{m}" for m in mask_cols]
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(out_header)
            for row in rows:
                i = row[idcol]
                k = keep.get(i, True)
                if filtered and not k:
                    continue
                vals = [row[h] for h in header]
                vals += ["" if columns[c].get(i) is None else columns[c].get(i) for c in extra]
                vals += ["1" if k else "0"]
                vals += ["1" if masks[m].get(i, True) else "0" for m in mask_cols]
                w.writerow(vals)
        os.chmod(path, 0o444)
        return path

    def _write_h5ad(self, out_dir, keep, columns, masks, contributions, filtered):
        try:
            import anndata as ad
            import numpy as np
        except ImportError as e:
            raise DatasetError("materialising an .h5ad view needs anndata and numpy in the host "
                               "environment") from e
        a = ad.read_h5ad(self.observations)
        ids = list(a.obs_names)
        for name, col in columns.items():
            a.obs[f"column__{name}"] = [col.get(i) for i in ids]
        a.obs["keep"] = [bool(keep.get(i, True)) for i in ids]
        for name, m in masks.items():
            a.obs[f"mask__{name}"] = [bool(m.get(i, True)) for i in ids]
        for c in contributions:
            if c.slot == "embedding" and c.path.suffix == ".npy":
                arr = np.load(c.path)
                bc_file = c.path.parent / "barcodes.txt"
                bcs = bc_file.read_text().split() if bc_file.exists() else []
                full = np.full((len(ids), arr.shape[1]), np.nan, dtype=arr.dtype)
                pos = {b: n for n, b in enumerate(ids)}
                for row, b in enumerate(bcs):
                    if b in pos:
                        full[pos[b]] = arr[row]
                a.obsm[f"X_{c.name}"] = full
        if filtered:
            a = a[a.obs["keep"].values].copy()
        path = out_dir / ("view.h5ad" if filtered else "view_full.h5ad")
        a.write_h5ad(path)
        os.chmod(path, 0o444)
        return path

    def _write_readme(self, out_dir, view, path):
        """Written by inspecting the directory, so it describes what is there (§11)."""
        lines = [f"# materialised view", "",
                 f"- observations: `{self.observations}` (sha256 {self.digest()[:12]})",
                 f"- profile: {self.profile.id}",
                 f"- kept: {view.n} of {view.n_total}",
                 f"- masks: {', '.join(sorted(view.masks())) or 'none'}",
                 f"- columns: {', '.join(view.columns()) or 'none'}",
                 f"- file: `{path.name}` (read-only)", "",
                 "This directory is derived and disposable. Deleting it loses nothing."]
        (out_dir / "README.md").write_text("\n".join(lines) + "\n")
