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
import re
from pathlib import Path

from .. import yamlish

FILENAME = "DEVPOINTS.yaml"
# Top-level keys the loader understands beyond `points`; anything else is the author's note.
TOP = ("tool", "devpoints", "tests", "fixture", "terms", "terms_env", "baseline_dir", "points")
SCHEMA = 1

# Every point must answer these. `proves`/`cannot_prove` are not documentation: the ladder prints
# them, so a point that cannot say what its fixture run fails to establish does not get one.
REQUIRED = ("what", "lives", "proves", "cannot_prove")
OPTIONAL = ("register", "must_declare", "example", "template", "scaffold_command",
            "tests", "fixture", "notes", "convert", "truth")

#: HOW A REQUIRED KEY'S TRUTH IS ESTABLISHED, for a key no conversion stage fills. `must_declare`
#: says a key has to EXIST; it never said what makes it TRUE, and "unowned" collapsed four honest
#: answers into one. Measured on the repository this was written for: six of seventeen required
#: keys were filled by no stage, and the line reporting them could not tell the conversion's
#: INPUT from a key the validator refuses from a key nothing anywhere checks - and two keys the
#: scheduler packs a node on sat in the last group with the scaffold's own template asking for
#: the check.
#:
#:   input      the conversion's input - the upstream it is driven by - which cannot be its output
#:   validator  refused by the repository's own validator when wrong
#:   measured   read back from a run by a named command
#:
#: A key filled by a stage needs no entry. A key with no stage and no entry is CHECKED BY NOBODY,
#: and `sch dev convert status` prints it that way on every status until somebody decides.
TRUTH = ("input", "validator", "measured")


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
        # A `truth:` ENTRY IS A CLAIM ABOUT A REQUIRED KEY, so it must name one and say one of
        # the three things that can be said. A misspelt value or a key the point does not require
        # would otherwise be a declaration nothing reads, which is the shape of defect this
        # loader exists to refuse.
        truth = pt.get("truth")
        if truth is not None:
            if not isinstance(truth, dict):
                raise DevpointsError(f"{f}: point {name!r}: `truth` must be a mapping of "
                                     f"required key -> one of {', '.join(TRUTH)}")
            keys = {str(k) for k in (pt.get("must_declare") or [])}
            for k, v in truth.items():
                if str(k) not in keys:
                    raise DevpointsError(f"{f}: point {name!r}: `truth` names {k!r}, which is "
                                         f"not in `must_declare`")
                if str(v) not in TRUTH:
                    raise DevpointsError(f"{f}: point {name!r}: `truth: {k}: {v!r}` - expected "
                                         f"one of {', '.join(TRUTH)}")
        for reg in pt.get("register") or []:
            if not isinstance(reg, dict) or not reg.get("file") or not (reg.get("table") or reg.get("pattern")):
                raise DevpointsError(
                    f"{f}: point {name!r}: each `register` entry needs `file` and either `table` "
                    f"(a Python literal, read by parsing) or `pattern` (a regular expression with "
                    f"{{name}} in it, for a registry that is not Python - a row in a table, a line "
                    f"in a manifest)")
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
  command: ["{{python}}", "tests/run_all.py"]   # whatever THIS repo already uses

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
    """One row per declared registry: {table, file, present, keys, readable, fix}.

    `fix` IS THE DIFFERENCE BETWEEN A GATE AND A CHORE. A registry entry says a name must appear
    somewhere; whether getting it there is an edit or a command is the whole cost to whoever hits
    it. scProfile's Tier 0 table is now rendered from the declarations, so the answer is
    `scprofile generated --write` - and a tier that reports the gate without the command sends a
    newcomer to hand-edit a generated document.
    """
    root = Path(doc["_root"])
    rows = []
    for reg in point(doc, point_name).get("register") or []:
        f = root / reg["file"]
        if reg.get("pattern"):
            # A REGISTRY THAT IS NOT PYTHON. scProfile's real admission gate is a row in
            # ROADMAP.md's Tier 0 table, enforced by its own suite and documented nowhere - a
            # newcomer found it only by running the tests and watching them go red. A pattern
            # entry lets the declaration name that gate so the tool announces it instead.
            try:
                text = f.read_text(encoding="utf-8")
            except OSError:
                rows.append({"file": reg["file"], "table": reg["pattern"], "readable": False,
                             "keys": [], "present": False, "fix": reg.get("fix", "")})
                continue
            rx = re.compile(reg["pattern"].replace("{name}", re.escape(name)), re.M)
            rows.append({"file": reg["file"], "table": reg["pattern"], "readable": True,
                         "keys": [], "present": bool(rx.search(text)),
                         "fix": reg.get("fix", "")})
            continue
        keys = _table_keys(f, reg["table"])
        rows.append({"file": reg["file"], "table": reg["table"],
                     "readable": keys is not None,
                     "keys": keys or [],
                     "present": bool(keys) and name in keys,
                     "fix": reg.get("fix", "")})
    return rows


# A `must_declare` entry that is a bare identifier is a KEY and is checked. One with a space in
# it is a sentence and is printed. The field carried both from the start - scProfile lists `sees`
# and `caveats`, scQC lists "a GATES entry with as_written" - and the tier printed all of them
# and enforced none, so a scaffold missing three required keys passed the declaration tier while
# the tier was displaying their names. A requirement that is only ever displayed is decoration.
_KEYISH = re.compile(r"^[a-z_][a-z0-9_]*$")


def _string_keys(path: Path) -> set | None:
    """Every string key of every dict literal in a module, and every module-level name assigned.

    None when the file cannot be read or parsed - which is a different answer from "the keys are
    absent", and is reported as such.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError):
        return None
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            found |= {k.value for k in node.keys
                      if isinstance(k, ast.Constant) and isinstance(k.value, str)}
        elif isinstance(node, ast.keyword) and node.arg:
            found.add(node.arg)
    for node in tree.body:
        for t in (node.targets if isinstance(node, ast.Assign) else
                  [node.target] if isinstance(node, ast.AnnAssign) else []):
            if isinstance(t, ast.Name):
                found.add(t.id)
                found.add(t.id.lower())
    return found


def declared_keys(doc: dict, point_name: str, name: str) -> tuple:
    """(where, keys) for the artefact this point says a new one lives in. keys is None when the
    artefact cannot be found or read."""
    pt = point(doc, point_name)
    base = Path(doc["_root"])
    lives = base / pt["lives"]
    target = lives / f"{name}.py" if lives.is_dir() else lives
    if not target.is_file():
        return str(target), None
    return str(target.relative_to(base)), _string_keys(target)


def existing(doc: dict, point_name: str) -> list:
    """Every name already registered at this point, across its registries - the union."""
    seen: list = []
    for row in registration(doc, point_name, "\0"):
        for k in row["keys"]:
            if k not in seen:
                seen.append(k)
    return seen
