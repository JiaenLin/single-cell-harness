"""`sch catalogue`: every plugin the family has, in one vocabulary, read without importing any.

WHY THIS EXISTS (GAP-005, ADR-0030). An agent asked a question has to choose a method before it
can run one, and until now it could not list them: scProfile has no list command, and the
harness's kernel sees only `plugin.yml` directories (`Stack.resolve_plugin`). The family's methods
were in a layout the harness could not read, described in a vocabulary it did not share.

WHERE EACH PLUGIN IS READ FROM
  harness     every `plugin.yml` under each `$SCH_PLUGINS` directory, then under the shipped
              `plugins/`: the kernel's own search roots, in its order, so a site plugin shadows a
              shipped one here exactly as it does at mount.
  scprofile   a checkout named by `--scprofile`: `kernels/<name>.py` (the one-file layout and the
              maker's), `kernels/<name>/kernel.yml` (the legacy six-file shape its host still
              loads), and three declarations of the tool's own, each read as text:
                DEVPOINTS.yaml          the maker's outstanding markers and the round's records
                scprofile/declare.py    `CAPABILITIES`, which says what each need resolves from
                .git/HEAD               the commit that was read

NOTHING IS IMPORTED, AND NOTHING IS DROPPED. Declarations are literals and YAML, parsed. A file
that cannot be read is an error naming it, reported beside the rows it did not stop; a source
that cannot be read at all is refused by name; and a source that was not asked for says so, so a
partial listing never reads as the whole family.
"""
from __future__ import annotations

import os
from pathlib import Path

from . import read as R
from . import row as W
from .row import NOT_DECLARED, UNKNOWN, FORMATS  # noqa: F401  (the vocabulary of a row)

HARNESS = "harness"
SCPROFILE = "scprofile"
#: scProfile's plugin directory: `KERNEL_DIRNAME` in its `scprofile/kernels.py`, and the layout its
#: plugin API documents (`kernels/myplugin.py`, `scprofile/plugin.py`).
SCPROFILE_PLUGINS = "kernels"
#: Where scProfile states its capability vocabulary as a literal.
SCPROFILE_VOCABULARY = ("scprofile/declare.py", "CAPABILITIES")
END_TO_END = ("DEVPOINTS.yaml rules.end_to_end: the plugin a round runs end to end on a real "
              "cohort")


class CatalogueError(Exception):
    """A source the caller named cannot be read at all. Refused by name; nothing is listed from it."""


def harness_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def build(scprofile=None, environ=None) -> dict:
    """The catalogue: {catalogue, sources, plugins, errors, vocabulary}. Reads, never runs."""
    env = os.environ if environ is None else environ
    cat = {"catalogue": 1, "sources": [], "plugins": [], "errors": [], "vocabulary": {}}
    _harness(cat, env)
    if scprofile:
        _scprofile(cat, Path(scprofile))
    else:
        cat["sources"].append({"name": SCPROFILE, "read": False,
                               "why": "no --scprofile CHECKOUT was given, so none of scProfile's "
                                      "plugins is in this listing"})
    _shadow(cat)
    cat["plugins"].sort(key=lambda r: (r["id"], r.get("_rank", 0)))
    for r in cat["plugins"]:
        r.pop("_rank", None)
    cat["errors"].sort(key=lambda e: (e["source"], e["path"]))
    return cat


def public(row, details=False) -> dict:
    """A row as it is printed: `details` (what `show` adds) only when asked for."""
    out = {k: v for k, v in row.items() if k != "_details"}
    if details:
        out["details"] = row.get("_details", {})
    return out


def find(cat, ident: str) -> list:
    """The rows `ident` names: its exact id, else every id ending in `:ident` or `/ident`.

    A shadowed row answers only to nothing: the row that wins at mount is the one returned."""
    rows = [r for r in cat["plugins"] if not r.get("shadowed_by")]
    exact = [r for r in rows if r["id"] == ident]
    if exact:
        return exact
    return [r for r in rows if r["id"].endswith(":" + ident) or r["id"].endswith("/" + ident)]


# ------------------------------------------------------------------------------- harness
def _harness(cat, env):
    root = harness_root()
    # THE KERNEL'S ORDER: `$SCH_PLUGINS` before the shipped directory, split as the kernel splits
    # it (`Stack._plugin_paths`), so the row that wins here is the plugin `sch mount` would load.
    dirs = [Path(p) for p in str(env.get("SCH_PLUGINS", "")).split(":") if p]
    dirs.append(root / "plugins")
    src = {"name": HARNESS, "read": True, "root": str(root), "commit": R.head_of(root),
           "searched": [str(d) for d in dirs], "plugins": 0, "errors": 0, "warnings": []}
    cat["sources"].append(src)
    ran = _ran_names(_devpoints(root, src, quiet=True))
    for rank, d in enumerate(dirs):
        if not d.is_dir():
            src["warnings"].append(f"{d}: not a directory, so no plugin was read from it")
            continue
        for pf in sorted(d.rglob("plugin.yml")):
            if "__pycache__" in pf.parts:
                continue
            _directory(cat, src, root, pf, ran, rank)


def _layer_slots(profile_id):
    """The slots this plugin's profile binds to an object's layers, or None for an unknown profile."""
    from ..profile import load_profile, ProfileError
    try:
        prof = load_profile(str(profile_id))
    except (ProfileError, OSError, ValueError):
        return None
    return {name for name, s in prof.slots.items() if isinstance(s, dict) and s.get("binds") == "layers"}


def _lock_lines(f: Path) -> list:
    """Every dependency line of a `lock.yml` (an environment spec), pip lines included."""
    data = R.yaml_mapping(f)
    out = []
    for dep in data.get("dependencies") or []:
        if isinstance(dep, dict):
            for v in dep.values():
                out.extend(str(x) for x in (v if isinstance(v, list) else [v]))
        else:
            out.append(str(dep))
    return out


def _directory(cat, src, root, pf, ran, rank):
    d = pf.parent
    rel = _rel(d, root)
    try:
        data = R.yaml_mapping(pf)
        if not str(data.get("name") or "").strip():
            raise R.Unreadable(pf, "declares no `name`, so nothing can mount it by name")
        lock = _lock_lines(d / "lock.yml") if (d / "lock.yml").is_file() else None
        pys = sorted(p for p in d.rglob("*.py") if "__pycache__" not in p.parts)
        row = W.directory_row(
            data, source=HARNESS, rel=rel, fmt="directory",
            evidence=["the harness's plugin.yml directory (PLUGIN_FORMAT.md), which the kernel "
                      "mounts; a legacy layout under ADR-0030"],
            companions=[], layer_slots=_layer_slots(data.get("profile")),
            assay_lines=R.assay_reads(pys, root), ran=ran.get(str(data.get("name")), (UNKNOWN, None)),
            lock=lock)
    except R.Unreadable as e:
        return _error(cat, src, _rel(e.path, root), e.why)
    except W.Malformed as e:
        return _error(cat, src, _rel(pf, root), str(e))
    row["_rank"] = rank
    row["_details"] = W.directory_details(data)
    cat["plugins"].append(row)
    src["plugins"] += 1


# ----------------------------------------------------------------------------- scprofile
def _scprofile(cat, root: Path):
    if not root.is_dir():
        raise CatalogueError(f"--scprofile {root}: no such directory")
    if not (root / SCPROFILE_PLUGINS).is_dir():
        raise CatalogueError(f"--scprofile {root}: there is no {SCPROFILE_PLUGINS}/ directory in it, "
                             f"so it is not a scProfile checkout (its plugins live in "
                             f"{SCPROFILE_PLUGINS}/<name>.py)")
    root = root.resolve()
    kdir = root / SCPROFILE_PLUGINS
    src = {"name": SCPROFILE, "read": True, "root": str(root), "commit": R.head_of(root),
           "searched": [str(kdir)], "plugins": 0, "errors": 0, "warnings": []}
    cat["sources"].append(src)
    doc = _devpoints(root, src)
    markers = _maker_markers(doc, src)
    ran = _ran_names(doc)
    vocab = _vocabulary(root, src)
    if vocab is not None:
        cat["vocabulary"][SCPROFILE] = vocab
    files = sorted(p for p in kdir.glob("*.py") if not p.name.startswith("_"))
    stems = {p.stem for p in files}
    for f in files:
        # A `<stem>.<x>.py` BESIDE `<stem>.py` IS ITS COMPANION by the maker's naming rule
        # (`sch/dev/convert.py`, `companion_paths`), not a plugin of its own.
        if "." in f.stem and f.stem.split(".", 1)[0] in stems:
            continue
        _onefile(cat, src, root, f, markers, vocab, ran)
    for d in sorted(p for p in kdir.iterdir() if p.is_dir() and (p / "kernel.yml").is_file()):
        _kernel_yml(cat, src, root, d, vocab, ran)


def _devpoints(root: Path, src, quiet=False):
    f = root / "DEVPOINTS.yaml"
    if not f.is_file():
        if not quiet:
            src["warnings"].append(f"no DEVPOINTS.yaml in {root}: the maker's markers and the "
                                   f"round's records cannot be read, so no plugin here reads "
                                   f"`maker` and every cohort run reads `unknown`")
        return None
    try:
        return R.yaml_mapping(f)
    except R.Unreadable as e:
        src["warnings"].append(f"{e}: the maker's markers and the round's records cannot be read")
        return None


def _maker_markers(doc, src):
    """The fields the maker's declaration marks outstanding (`outstanding_if`), or None.

    Read from the point that lives in the plugin directory and declares `convert` stages: the
    maker's own word on when a build stage is unfinished. None when there is no such point."""
    if doc is None:
        return None
    for name, pt in (doc.get("points") or {}).items():
        if not isinstance(pt, dict) or str(pt.get("lives") or "").strip("/") != SCPROFILE_PLUGINS:
            continue
        conv = pt.get("convert")
        if isinstance(conv, dict) and isinstance(conv.get("stages"), list):
            return sorted({str(st["outstanding_if"]) for st in conv["stages"]
                           if isinstance(st, dict) and st.get("outstanding_if")})
    src["warnings"].append(f"DEVPOINTS.yaml declares no point living in {SCPROFILE_PLUGINS}/ with "
                           f"`convert` stages, so the maker's markers are unknown and no plugin "
                           f"here reads `maker`")
    return None


def _ran_names(doc):
    """{name: (status, record)} for the plugins the tool's own records say ran on a cohort."""
    rules = (doc or {}).get("rules")
    e2e = rules.get("end_to_end") if isinstance(rules, dict) else None
    names = e2e.get("names") if isinstance(e2e, dict) else None
    return {str(n): ("recorded", END_TO_END) for n in (names or []) if isinstance(names, list)}


def _vocabulary(root: Path, src):
    rel, name = SCPROFILE_VOCABULARY
    f = root / rel
    why = None
    if not f.is_file():
        why = f"no {rel}"
    else:
        try:
            v, _ = R.module_literal(f, name, what="capability vocabulary")
        except R.Unreadable as e:
            why = str(e)
        else:
            if isinstance(v, dict) and all(isinstance(x, dict) for x in v.values()):
                return {str(k): {"resolve": str(x.get("resolve") or ""), "why": str(x.get("why") or "")}
                        for k, x in v.items()}
            why = f"{rel}: `{name}` is not a mapping of capability -> {{resolve, why}}"
    src["warnings"].append(f"{why}: the tool's capability vocabulary could not be read, so which "
                           f"needs come from the design or from another plugin reads `unknown`")
    return None


def _companions(path: Path, root):
    from ..dev.convert import companion_paths
    return [_rel(c, root) for c in companion_paths(path)]


def _onefile(cat, src, root, f, markers, vocab, ran):
    try:
        spec, _line = R.plugin_literal(f)
        comps = _companions(f, root)
        fmt, ev = W.maker_format(spec, f.stem, comps, markers)
        row = W.onefile_row(spec, source=SCPROFILE, name=f.stem, rel=_rel(f, root), fmt=fmt,
                            evidence=ev, companions=comps, vocab=vocab,
                            assay_lines=R.assay_reads([f], root),
                            ran=ran.get(f.stem, (UNKNOWN, None)))
    except R.Unreadable as e:
        return _error(cat, src, _rel(e.path, root), e.why)
    except W.Malformed as e:
        return _error(cat, src, _rel(f, root), str(e))
    row["_rank"] = 1
    row["_details"] = W.onefile_details(spec)
    cat["plugins"].append(row)
    src["plugins"] += 1


def _kernel_yml(cat, src, root, d, vocab, ran):
    f = d / "kernel.yml"
    try:
        data = R.yaml_mapping(f)
        # THE OLD SHAPE SPELLS `needs` FLAT (`needs_obs`, `needs_layers`, `needs_design`); the
        # one-file shape nests it, and `FileKernel` flattens it back. Nested here, one mapping.
        spec = dict(data)
        needs = {role: data[f"needs_{role}"] for role in ("obs", "obsm", "layers", "kernels")
                 if data.get(f"needs_{role}")}
        if data.get("needs_design"):
            needs["design"] = True
        if needs and "needs" not in spec:
            spec["needs"] = needs
        files = sorted(p for p in d.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
        row = W.onefile_row(spec, source=SCPROFILE, name=d.name, rel=_rel(d, root), fmt="kernel-yml",
                            evidence=["scProfile's six-file directory (kernels/<name>/kernel.yml), "
                                      "which its host still loads; a legacy layout under ADR-0030"],
                            companions=[_rel(p, root) for p in files if p.name != "kernel.yml"],
                            vocab=vocab, assay_lines=R.assay_reads([p for p in files if p.suffix == ".py"], root),
                            ran=ran.get(d.name, (UNKNOWN, None)))
    except R.Unreadable as e:
        return _error(cat, src, _rel(e.path, root), e.why)
    except W.Malformed as e:
        return _error(cat, src, _rel(f, root), str(e))
    # scProfile's `discover()` lets a kernel.yml directory override a one-file plugin of the same
    # name, so the directory ranks first here.
    row["_rank"] = 0
    row["_details"] = W.onefile_details(spec)
    cat["plugins"].append(row)
    src["plugins"] += 1


# --------------------------------------------------------------------------------- common
def _error(cat, src, rel, why):
    cat["errors"].append({"source": src["name"], "path": rel, "error": f"{rel}: {why}"})
    src["errors"] += 1


def _shadow(cat):
    """Two rows with one id: the one the host would load wins, the other says what shadows it."""
    first = {}
    for r in sorted(cat["plugins"], key=lambda r: r.get("_rank", 0)):
        if r["id"] in first:
            r["shadowed_by"] = first[r["id"]]["path"]
        else:
            first[r["id"]] = r


def _rel(p, root) -> str:
    try:
        return str(Path(p).resolve().relative_to(Path(root).resolve()))
    except ValueError:
        return str(Path(p).resolve())
