"""What a repository says can be added to it, and whether a thing that was added is registered.

THE SUITE KNOWS NOTHING ABOUT KERNELS OR METHODS. The five repositories in this family extend
in five different ways - scProfile loads `kernels/<name>.py` carrying a PLUGIN dict, or an
out-of-process directory carrying `kernel.yml`; scIntegrate adds a key to METHODS and another to
SEES; scQC adds a module to _STEP_MODULES and a criterion to GATES; scAnno has no registry at
all and wires functions in its CLI; the harness has `sch plugin new`. A toolkit that hard-codes
any one of those is a toolkit for one repository.

So each repository DECLARES its extension points in `DEVPOINTS.yaml` and this module reads the
declaration. Adding a sixth repository, or a sixth kind of extension to an existing one, is a
file - not a change here. It is the same split the harness already makes between the plugin
format and the single-cell profile, for the same reason.

    tool: scintegrate
    devpoints: 1
    fixture:
      command: "{python} -m scintegrate.cli run --input {input} --out {out} --method {name}"
      products: ["report.json"]
    points:
      method:
        what: an integration method the benchmark can rank
        lives: scintegrate/methods.py
        register:
          - {file: scintegrate/methods.py, table: METHODS}
          - {file: scintegrate/methods.py, table: SEES}
        must_declare: [state_version, sees]
        example: harmony
        proves: "it runs, it declares what it sees, its output is masked and not zero-filled"
        cannot_prove: "that the embedding is any good - that is a cohort question"

REGISTRATION IS CHECKED, NOT WRITTEN. An earlier draft of this module edited the registry dict
for you. Text-editing a Python literal is guesswork the moment the file is formatted differently
from the way the guesser expects, and a scaffolder that silently half-registers something is
worse than one that does not try. `sch dev new` prints the edit; this module parses the file with
`ast` afterwards and says whether it landed. The tool that checks is not the tool that wrote,
which is the only arrangement in which the check means anything.
"""
from __future__ import annotations

import ast
from pathlib import Path

from .. import yamlish

FILENAME = "DEVPOINTS.yaml"
SCHEMA = 1

# Every point must answer these. `proves`/`cannot_prove` are not documentation: the ladder prints
# them, so a point that cannot say what its fixture run fails to establish does not get one.
REQUIRED = ("what", "lives", "proves", "cannot_prove")
OPTIONAL = ("register", "must_declare", "example", "template", "tests", "fixture", "notes")


class DevpointsError(ValueError):
    pass


def find(start=".") -> Path | None:
    """The nearest DEVPOINTS.yaml at or above `start`. None if the tree declares none."""
    p = Path(start).resolve()
    for d in (p, *p.parents):
        f = d / FILENAME
        if f.is_file():
            return f
    return None


def load(start=".") -> dict:
    f = find(start)
    if f is None:
        raise DevpointsError(
            f"no {FILENAME} at or above {Path(start).resolve()}. This repository has not declared "
            f"what can be added to it; `sch dev map --init` writes a first one.")
    doc = yamlish.load(f)
    if not isinstance(doc, dict):
        raise DevpointsError(f"{f}: expected a mapping at the top level")
    doc["_path"] = str(f)
    doc["_root"] = str(f.parent)
    _validate(doc, f)
    return doc


def _validate(doc, f):
    if int(doc.get("devpoints") or 0) != SCHEMA:
        raise DevpointsError(f"{f}: devpoints: {SCHEMA} required, found {doc.get('devpoints')!r}")
    if not doc.get("tool"):
        raise DevpointsError(f"{f}: `tool` is required - the name the run record will carry")
    points = doc.get("points") or {}
    if not isinstance(points, dict) or not points:
        raise DevpointsError(f"{f}: `points` must name at least one extension point")
    root = Path(doc["_root"])
    for name, pt in points.items():
        if not isinstance(pt, dict):
            raise DevpointsError(f"{f}: point {name!r} must be a mapping")
        for k in REQUIRED:
            if not pt.get(k):
                raise DevpointsError(f"{f}: point {name!r} is missing `{k}`")
        for k in pt:
            if k not in REQUIRED + OPTIONAL:
                raise DevpointsError(f"{f}: point {name!r} has unknown key {k!r}")
        for reg in pt.get("register") or []:
            if not isinstance(reg, dict) or not reg.get("file") or not reg.get("table"):
                raise DevpointsError(f"{f}: point {name!r}: each `register` entry needs file and table")
            if not (root / reg["file"]).is_file():
                raise DevpointsError(f"{f}: point {name!r}: register file {reg['file']} does not exist")


def point(doc: dict, name: str) -> dict:
    pts = doc.get("points") or {}
    if name not in pts:
        raise DevpointsError(
            f"{doc['tool']} declares no extension point {name!r}. It declares: "
            f"{', '.join(sorted(pts))}. Add it to {FILENAME} before adding code for it - the "
            f"declaration is what makes the new thing checkable.")
    return pts[name]


# ------------------------------------------------------------------ is it actually registered?
def _table_keys(path: Path, table: str) -> list | None:
    """Keys of a module-level dict/set/tuple/list literal, by parsing. None if absent.

    Only literal keys are returned. A registry built at import time by a loop or a comprehension
    cannot be read this way and is reported as unreadable rather than as empty, because "no keys
    found" and "keys I cannot see" are different facts and only one of them is a defect.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError):
        return None
    for node in tree.body:
        targets = (node.targets if isinstance(node, ast.Assign)
                   else [node.target] if isinstance(node, ast.AnnAssign) else [])
        if not any(isinstance(t, ast.Name) and t.id == table for t in targets):
            continue
        v = node.value
        if isinstance(v, ast.Dict):
            return [k.value for k in v.keys if isinstance(k, ast.Constant)]
        if isinstance(v, (ast.Set, ast.List, ast.Tuple)):
            return [e.value for e in v.elts if isinstance(e, ast.Constant)]
        return None
    return None


def registration(doc: dict, point_name: str, name: str) -> list:
    """One row per declared registry: {table, file, present, keys, readable}."""
    root = Path(doc["_root"])
    rows = []
    for reg in point(doc, point_name).get("register") or []:
        f = root / reg["file"]
        keys = _table_keys(f, reg["table"])
        rows.append({"file": reg["file"], "table": reg["table"],
                     "readable": keys is not None,
                     "keys": keys or [],
                     "present": bool(keys) and name in keys})
    return rows


def existing(doc: dict, point_name: str) -> list:
    """Every name already registered at this point, across its registries - the union."""
    seen: list = []
    for row in registration(doc, point_name, "\0"):
        for k in row["keys"]:
            if k not in seen:
                seen.append(k)
    return seen
