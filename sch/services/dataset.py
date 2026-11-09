"""The dataset service: observations, contributions, and materialisation.

D2  Nothing writes to observations. The file is opened read-only and its digest is checked by
    the A1 companion after every plugin run.
A1  The observations are PINNED at init: their digest and, per file, (dev, inode, size,
    mtime_ns, ctime_ns). The fingerprint is re-checked before anything is read and after every
    plugin run, whatever its outcome, and a change is an error naming the file. Nothing
    re-baselines a stack silently (harness W010b): a library replaced by a plugin that then died
    used to be read as the new baseline by the next command.
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
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from ..core import Service


class DatasetError(ValueError):
    pass


#: What a file's identity is pinned by. `dev` is RECORDED and not compared on its own: an NFS
#: mount's device number is assigned per host, so a stack reopened on another node would differ in
#: it with nothing changed, and a rename cannot cross filesystems, so a replacement shows in
#: `inode` and `ctime_ns` wherever it came from.
FINGERPRINT = ("dev", "inode", "size", "mtime_ns", "ctime_ns")
COMPARED = ("inode", "size", "mtime_ns", "ctime_ns")
PIN = "observations.pin.json"


def fingerprint(path) -> dict:
    s = os.stat(path)
    return {"dev": s.st_dev, "inode": s.st_ino, "size": s.st_size, "mtime_ns": s.st_mtime_ns,
            "ctime_ns": s.st_ctime_ns}


def _owner(uid: int) -> str:
    try:
        import pwd
        return pwd.getpwuid(uid).pw_name
    except (ImportError, KeyError):
        return f"uid {uid}"


def remedy(paths: list) -> str:
    """How to make files read-only, as a shell can run it: `chmod a-w` for this user's own files,
    shell-quoted. A file someone else owns cannot be chmod'ed by this user (EPERM), so for it the
    remedy is its owner, or a read-only copy."""
    me = os.geteuid()
    mine, theirs = [], []
    for f in paths:
        try:
            uid = os.stat(f).st_uid
        except OSError:
            uid = me
        (mine if uid == me else theirs).append((str(f), uid))
    out = ["chmod a-w " + " ".join(shlex.quote(f) for f, _ in mine)] if mine else []
    for f, uid in theirs:
        who = _owner(uid)
        out.append(f"{shlex.quote(f)} is owned by {who}, and chmod by anyone else fails (EPERM): "
                   f"ask {who} to chmod a-w it, or point the manifest at a read-only copy "
                   f"(cp it, then chmod a-w the copy)")
    return "; ".join(out)


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
                cats = H5adReader.read_strings(node["categories"])     # categories may be a group too
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


# ---------------------------------------------------------------------------- a parts manifest
def read_manifest(path) -> tuple:
    """(header, rows) of a manifest: one row per part, tab- or comma-separated by its header.

    `#` lines and blank lines are skipped, as the tools' own samplesheets allow. The delimiter is
    read off the header and an ambiguous one is refused: a wrong delimiter does not fail to parse,
    it yields a table of the right length and the wrong shape.
    """
    lines = [ln for ln in Path(path).read_text(encoding="utf-8").splitlines()
             if ln.strip() and not ln.lstrip().startswith("#")]
    if not lines:
        raise DatasetError(f"{path}: the manifest has no header")
    tabs, commas = lines[0].count("\t"), lines[0].count(",")
    if not tabs and not commas:
        raise DatasetError(f"{path}: the manifest's header has one column; nothing names a part")
    if tabs == commas:
        raise DatasetError(f"{path}: the header has {tabs} tab(s) and {commas} comma(s), so it parses "
                           f"two ways; use one delimiter")
    r = csv.DictReader(lines, delimiter="\t" if tabs > commas else ",")
    return list(r.fieldnames or []), list(r)


# ---------------------------------------------------------------------------- the service
class Dataset(Service):
    """The observations, and the contributions folded over them.

    Observations are ONE file, or a PARTS MANIFEST (harness W010): a table with one row per part,
    `scope` naming the column that scopes each part's identities (the stack's `{sample}` key) and
    `parts` the column naming the file that holds them. An identity is then
    `<scope><joiner><identity within the part>`, the joiner being the profile's. The digest covers
    the manifest and every part, so a write to any of them is a write A1 sees; the view is
    identity-level (`view.csv`), and the parts are read in place, never copied.
    """

    def __init__(self, observations, profile, stack_dir, design=None, parts=None, scope=None):
        self.observations = Path(observations).resolve()
        self.profile = profile
        self.stack_dir = Path(stack_dir)
        self.design = Path(design).resolve() if design else None
        self.parts = str(parts) if parts else None
        self.scope = str(scope) if scope else None
        self.joiner = str(profile.identity.get("joiner") or "")
        if self.parts:
            if not profile.identity.get("scope"):
                raise DatasetError(f"profile {profile.id} gives identities no scope, so observations "
                                   f"cannot arrive in parts; declare one observation file")
            if not self.scope:
                key = str(profile.identity.get("scope")).strip("{}")
                raise DatasetError(f"observations in parts need the column that scopes them: "
                                   f"--key {key}=<the manifest's column naming each part>")
            if not self.joiner:
                raise DatasetError(f"profile {profile.id} declares no identity.joiner to write a "
                                   f"scoped identity with")
        self.reader = H5adReader() if self.parts else self._reader()
        self._ids = None
        self._scope_of = None
        self._parts = None
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

    def part_files(self) -> list:
        """[(scope value, path)] in manifest order, after every check a manifest must pass. A
        manifest that cannot define one observation set is refused here, naming the row."""
        if self._parts is None:
            m = self.observations
            if not m.is_file():
                raise DatasetError(f"observations not found: {m}")
            header, rows = read_manifest(m)
            absent = [c for c in (self.scope, self.parts) if c not in header]
            if absent:
                raise DatasetError(f"{m}: no column {', '.join(map(repr, absent))}; the stack scopes "
                                   f"parts by {self.scope!r} and names them by {self.parts!r} "
                                   f"(columns: {', '.join(header)})")
            out, seen = [], set()
            for n, row in enumerate(rows, 1):
                s, p = (row.get(self.scope) or "").strip(), (row.get(self.parts) or "").strip()
                if not s or not p:
                    raise DatasetError(f"{m}: row {n} leaves {self.scope!r} or {self.parts!r} empty")
                if self.joiner in s:
                    raise DatasetError(f"{m}: {self.scope} {s!r} contains the joiner {self.joiner!r}, "
                                       f"so its identities could not be split back; rename it")
                if s in seen:
                    raise DatasetError(f"{m}: {self.scope} {s!r} names two parts; a scope is one part")
                seen.add(s)
                path = Path(p) if Path(p).is_absolute() else m.parent / p
                if path.is_dir() or (path.exists() and path.suffix != ".h5ad"):
                    raise DatasetError(f"{m}: the part of {s!r} is {path.name!r}; this kernel reads a "
                                       f"part's identities from an .h5ad, and no reader is written "
                                       f"for that form")
                if not path.is_file():
                    raise DatasetError(f"{m}: the part of {s!r} does not exist: {path}")
                out.append((s, path))
            if not out:
                raise DatasetError(f"{m}: the manifest names no part")
            self._parts = out
        return self._parts

    @property
    def ids(self) -> list:
        if self._ids is None:
            if self.parts:
                ids, scope_of = [], {}
                for s, path in self.part_files():
                    for i in self.reader.identities(path):
                        ident = f"{s}{self.joiner}{i}"
                        ids.append(ident)
                        scope_of[ident] = s
                self._ids, self._scope_of = ids, scope_of
            else:
                if not self.observations.exists():
                    raise DatasetError(f"observations not found: {self.observations}")
                self._ids = self.reader.identities(self.observations)
        return self._ids

    def _files(self) -> list:
        """Every file whose bytes ARE the observations: the manifest, then each part."""
        if self.parts:
            return [self.observations] + [p for _, p in self.part_files()]
        return [self.observations]

    def _compute_digest(self) -> str:
        if not self.parts:
            return file_digest(self.observations)
        h = hashlib.sha256()
        for f in self._files():
            h.update(file_digest(f).encode())
            h.update(b"\0")
        return h.hexdigest()

    def pin(self) -> dict:
        """Pin the observations as they are now: their digest, and each file's fingerprint. Done
        once, at init; never again for the same stack."""
        rec = {"sha256": self._compute_digest(),
               "files": {str(f): fingerprint(f) for f in self._files()}}
        (self.stack_dir / PIN).write_text(json.dumps(rec, indent=1, sort_keys=True))
        self._digest = rec["sha256"]
        return rec

    def _load_pin(self):
        f = self.stack_dir / PIN
        if not f.exists():
            return None
        try:
            return json.loads(f.read_text())
        except ValueError as e:
            raise DatasetError(f"{f} is unreadable ({e}); a stack's pin is never rebuilt "
                               f"silently: initialise a new stack") from None

    def changed(self, pin=None) -> list:
        """Every pinned file whose fingerprint moved, named with what moved. Read off the pin's
        own list, so a manifest rewritten to name other parts shows as the manifest changing."""
        pin = pin if pin is not None else self._load_pin()
        if pin is None:
            return []
        out = []
        for f, was in sorted((pin.get("files") or {}).items()):
            try:
                now = fingerprint(f)
            except OSError:
                out.append(f"{f}: gone")
                continue
            moved = [k for k in COMPARED if now.get(k) != was.get(k)]
            if moved:
                out.append(f"{f}: {', '.join(moved)} changed")
        return out

    def digest(self) -> str:
        """The digest pinned at init, once every pinned file is checked unchanged. D2's witness.

        A stack initialised before observations were pinned is pinned on its first read, once;
        after that, as for every other stack, a change is an error and never a new baseline."""
        if self._digest is None:
            pin = self._load_pin()
            if pin is None:
                pin = self.pin()
            bad = self.changed(pin)
            if bad:
                raise DatasetError(
                    "A1: the observations changed after this stack was initialised - "
                    + "; ".join(bad) + ". Nothing re-baselines them: restore the file, or "
                    "initialise a new stack over the files as they now are")
            self._digest = pin["sha256"]
        return self._digest

    def digest_now(self) -> str:
        """Recomputed, uncached. What the A1 companion compares against `digest()`."""
        return self._compute_digest()

    def inventory(self) -> dict:
        if self._inventory is None:
            if self.parts:
                common = None
                for _, path in self.part_files():
                    inv = self.reader.inventory(path)
                    common = inv if common is None else \
                        {k: [x for x in v if x in (inv.get(k) or [])] for k, v in common.items()}
                inv = dict(common or {})
                inv["column"] = [self.scope] + [c for c in inv.get("column", []) if c != self.scope]
                self._inventory = inv
            else:
                self._inventory = self.reader.inventory(self.observations)
        return self._inventory

    def describe_observations(self):
        """What a plugin is told about the observations themselves (in.json `observations`): null
        on one observation file, where a plugin is handed only the read-only view (E2), and the
        manifest on a parts stack, whose libraries a plugin must read in place."""
        if not self.parts:
            return None
        return {"path": str(self.observations), "parts": self.parts, "scope": self.scope,
                "joiner": self.joiner}

    def writable(self) -> list:
        """The observation files a plugin is handed and this user could write: on a parts stack
        the manifest and every part. E2 holds by what a plugin is handed, so none may be writable
        (verifier W010 F3); on one file a plugin is handed only the read-only view, and this is
        empty."""
        if not self.parts:
            return []
        return [str(f) for f in self._files() if os.access(f, os.W_OK)]

    def refuse_writable(self):
        """Raise, naming the files and the fix, while any observation file a plugin is handed is
        writable by the running user."""
        w = self.writable()
        if w:
            raise DatasetError(
                f"{len(w)} observation file(s) are writable by this user: "
                f"{', '.join(Path(x).name for x in w[:5])}{' ...' if len(w) > 5 else ''}. A plugin "
                f"reads them in place, so their permissions are what keeps it from writing them "
                f"(E2). Delivered data are immutable: {remedy(w)}")

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
        if self.parts:
            path = self._write_parts_view(out_dir, keep, columns, masks, filtered)
        elif m == "csv":
            path = self._write_csv(out_dir, keep, columns, masks, filtered)
        else:
            path = self._write_h5ad(out_dir, keep, columns, masks, contributions, filtered)
        view = View(self.ids, keep, columns, masks, path)
        self._write_readme(out_dir, view, path)
        return view

    def _write_parts_view(self, out_dir, keep, columns, masks, filtered):
        """The view of a parts stack: one row per identity - its scope, the contributed columns,
        keep, every mask - and no matrix. The matrices stay in their parts and are read there
        (`in.json` `observations`); copying ten libraries into a view would make the cheapest
        operation of the kernel the most expensive one."""
        idc = self.profile.identity.get("column", "id")
        path = out_dir / ("view.csv" if filtered else "view_full.csv")
        ids = self.ids
        extra, mask_cols = sorted(columns), sorted(masks)
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow([idc, self.scope] + [f"column__{c}" for c in extra] + ["keep"]
                       + [f"mask__{m}" for m in mask_cols])
            for i in ids:
                k = keep.get(i, True)
                if filtered and not k:
                    continue
                w.writerow([i, self._scope_of[i]]
                           + ["" if columns[c].get(i) is None else columns[c].get(i) for c in extra]
                           + ["1" if k else "0"]
                           + ["1" if masks[m].get(i, True) else "0" for m in mask_cols])
        os.chmod(path, 0o444)
        return path

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
        parts = (f", a manifest of {len(self.part_files())} parts by {self.scope!r}, read in place"
                 if self.parts else "")
        lines = [f"# materialised view", "",
                 f"- observations: `{self.observations}` (sha256 {self.digest()[:12]}){parts}",
                 f"- profile: {self.profile.id}",
                 f"- kept: {view.n} of {view.n_total}",
                 f"- masks: {', '.join(sorted(view.masks())) or 'none'}",
                 f"- columns: {', '.join(view.columns()) or 'none'}",
                 f"- file: `{path.name}` (read-only)", "",
                 "This directory is derived and disposable. Deleting it loses nothing."]
        (out_dir / "README.md").write_text("\n".join(lines) + "\n")
