"""Turning somebody else's tool into a plugin, and picking that job up where it was left.

A HALF-BUILT PLUGIN AND A RAW TOOL ARE THE SAME INPUT AT DIFFERENT POINTS ON ONE LINE. Converting
a repository is resuming from zero. That is not a convenience: it is the reason resume works at
all, because it makes resume the ONLY mode and there is no second code path that only runs the
first time and is therefore never exercised.

THE STATE IS THE PLUGIN FILE. Nothing is remembered between invocations - no lock file, no journal,
no `.convert-state.json` to go stale against the thing it describes. What remains to be done is
computed from the declaration every time, by asking which fields still carry the scaffold's
placeholder. A conversion interrupted by a lost connection, a different machine, or four months is
resumed by reading the file.

WHAT THIS MODULE DOES NOT KNOW. It names no tool, no field and no plugin format. Which stage fills
which field is declared by the repository being converted into, in its own `DEVPOINTS.yaml`, for
the same reason `sch dev` reads everything else from there: this suite serves five repositories and
a stage list written here would be one repository's shape imposed on the other four.

WHY THE STAGES SPLIT WHERE THEY DO. Every stage is either something a machine can extract from the
tool's own source, or something only a person or an agent can answer - and never both. The
mechanical ones are commands that run in seconds and can be re-run. The judgement ones are asked
ONCE, with the evidence already gathered, which is the whole efficiency argument: the expensive
participant should be answering "should this wrapper be using scvelo's 34th plotting function",
not finding out that scvelo has 34.
"""
from __future__ import annotations

from . import points as pts

#: Where a point declares its conversion, inside its entry in DEVPOINTS.yaml.
KEY = "convert"
#: What a stage entry must carry.
STAGE_REQUIRED = ("name", "fills")


class ConvertError(Exception):
    """The declaration cannot be read, or does not say enough to convert anything."""


def _dotted(spec, path):
    """`wraps.tool` out of a nested declaration, or None. Never raises on a missing branch."""
    cur = spec
    for part in str(path).split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def plan(doc, point_name):
    """(placeholder, upstream_path, [stage]) as the target repository declares them."""
    pt = pts.point(doc, point_name)
    conv = pt.get(KEY)
    if not isinstance(conv, dict):
        raise ConvertError(
            f"point {point_name!r} declares no `{KEY}:` block, so there is nothing to convert "
            f"INTO. A conversion needs to know which stage fills which field of this format, and "
            f"only this repository knows that.")
    stages = conv.get("stages") or []
    if not stages:
        raise ConvertError(f"point {point_name!r} declares `{KEY}:` with no stages")
    for i, st in enumerate(stages):
        missing = [k for k in STAGE_REQUIRED if not st.get(k)]
        if missing:
            raise ConvertError(f"point {point_name!r}: stage {i} declares no {missing}")
    return conv.get("placeholder", "TODO"), conv.get("upstream", ""), list(stages)


def unfilled(spec, fields, placeholder):
    """Which of these declared fields are absent or still carry the placeholder.

    ABSENT AND PLACEHOLDER ARE THE SAME ANSWER HERE and different everywhere else. To a reader of
    the finished plugin they differ - a missing `report` block is a WARN and a `report` full of
    TODO is an ERROR. To a conversion they are one thing: not done yet.
    """
    out = []
    for f in fields:
        v = _dotted(spec, f)
        if v is None:
            out.append(f)
        elif placeholder and placeholder in _flatten(v):
            out.append(f)
    return out


def _flatten(value):
    """Every string anywhere inside a value, joined. For asking "is the marker still in there"."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(_flatten(k) + " " + _flatten(v) for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return " ".join(_flatten(v) for v in value)
    return ""


def status(spec, doc, point_name):
    """[{stage, kind, done, missing, why}] in declared order. The whole resume mechanism."""
    placeholder, _up, stages = plan(doc, point_name)
    out = []
    for st in stages:
        missing = unfilled(spec, list(st["fills"]), placeholder)
        out.append({"stage": st["name"],
                    "kind": st.get("kind", "mechanical"),
                    "fills": list(st["fills"]),
                    "done": not missing,
                    "missing": missing,
                    "why": st.get("why", "")})
    return out


def next_stage(spec, doc, point_name):
    """The first stage not done, or None. Order is the declaration's, and it is the dependency.

    A LIST IS A DEPENDENCY GRAPH WHEN THE ORDER IS MEANT. `account` cannot run before `inventory`,
    and `judgement` is asked last because every earlier stage is evidence for it. Declaring that as
    an ordered list rather than as edges is enough here and says so: if a conversion ever needs two
    stages that genuinely do not depend on each other to run at once, this is where that shows up.
    """
    for row in status(spec, doc, point_name):
        if not row["done"]:
            return row
    return None


def inventory(tool, python=None, rscript=None):
    """Ask every extractor that can look. [(extractor name, Inventory)].

    ALL OF THEM, NOT THE RIGHT ONE. The declaration does not say whether a wrapped tool is a Python
    package or an R one - `wraps.tool` is a name - and inferring it from `requires.r` would be a
    guess that is wrong for the first plugin that wraps a Python package and also needs R. Each
    extractor fails fast when it cannot look, and says which of those two happened, so trying them
    all costs a second and produces a better answer than a guess: the ones that could not look say
    so by name.
    """
    from . import extract
    got = []
    for name, mod in sorted(extract.discover().items()):
        kind = mod.EXTRACT.get("reads")
        try:
            if kind == "python-package":
                inv = mod.inventory(tool, python=python or "python3")
            elif kind == "r-package":
                inv = mod.inventory(tool, rscript=rscript)
            else:
                continue
        except Exception as e:                                            # noqa: BLE001
            from .extract import Inventory
            inv = Inventory(tool, [], "", complete=False,
                            why_not=f"{type(e).__name__}: {e}")
        got.append((name, inv))
    return got


def format_status(rows, name, point_name):
    """The line-per-stage a person reads to know where a conversion stands."""
    done = sum(1 for r in rows if r["done"])
    L = [f"{name}  ({point_name})  {done} of {len(rows)} stage(s) complete"]
    for r in rows:
        mark = "done" if r["done"] else ("ASK " if r["kind"] == "judgement" else "todo")
        L.append(f"  {mark} {r['stage']:12s} {', '.join(r['fills'])}")
        if not r["done"]:
            L.append(f"       unfilled: {', '.join(r['missing'])}")
            if r["why"]:
                L.append(f"       {r['why']}")
    nxt = next((r for r in rows if not r["done"]), None)
    L.append(f"\n  next: {nxt['stage']}" if nxt else "\n  nothing left to convert")
    return "\n".join(L)
