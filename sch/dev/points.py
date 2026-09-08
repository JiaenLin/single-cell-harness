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
# Top-level keys the loader understands beyond `points`; anything else is the author's note.
TOP = ("tool", "devpoints", "tests", "fixture", "terms", "terms_env", "baseline_dir", "points")
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


STARTER = """# What can be added to this repository, and how a reader can tell whether it was added
# correctly. `sch dev map` reads this; without it, nothing in `sch dev` can check anything here.
#
# Fill in the marked places and delete this line. Every field below is required except where it
# says otherwise; `sch dev map` will tell you what is missing.
tool: {tool}
devpoints: 1

# How this repository runs its own tests. `{{python}}` is the interpreter running the check, and
# `{{jobs}}` is how many things this machine should do at once - use it if your runner takes a
# concurrency flag.
tests:
  command: ["{{python}}", "-m", "pytest", "-q", "tests"]

# The end-to-end exercise, run twice: once on a synthetic cohort, once on the SAME cohort with
# every column renamed. Anything that resolves a role passes both; anything that knows a column
# name passes one. Placeholders: {{observations}} {{design}} {{out}} {{name}} {{shape}} {{root}}
# {{jobs}} and one per role - {{role_sample}} {{role_condition}} {{role_batch}} {{role_cell_type}}
# {{role_subject}} {{role_covariate}} {{role_counts}}. `sch dev map --json` lists them with values.
fixture:
  command: ["{{python}}", "-m", "{tool}", "run", "--input", "{{observations}}", "--out", "{{out}}"]
  products: []          # relative to {{out}}; each is checked for existence and non-zero size

baseline_dir: tests/baselines

points:
  # One block per kind of thing that can be added. Rename this one.
  thing:
    what: <one line a reader who is not you would recognise>
    lives: <the file or directory a new one goes into>
    # optional; each table is read by PARSING the file, never by editing it
    register: []
    must_declare: []
    example: <the existing one to start from>
    proves: <what a green `sch dev check` establishes for this kind>
    cannot_prove: <what it does NOT establish - the field everyone skips, and the one that decides how much cluster time a change here will cost>
"""


def init(root, tool: str | None = None, force: bool = False) -> Path:
    """Write a starter declaration. The error you get without one names this command, so it has
    to exist - it named a flag that did not, which is the same defect this suite exists to find,
    one level up."""
    root = Path(root).resolve()
    f = root / FILENAME
    if f.exists() and not force:
        raise DevpointsError(f"{f} already exists; --force overwrites it")
    f.write_text(STARTER.format(tool=tool or root.name.lower().replace("-", "_")), encoding="utf-8")
    return f


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
