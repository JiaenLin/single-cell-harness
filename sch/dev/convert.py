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

import re

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


def _clip(text, n):
    """Truncated so the reader can see it was truncated. A silent cut reads as the whole thing."""
    t = " ".join(str(text or "").split())
    return t if len(t) <= n else t[:n - 1] + "…"


def worksheet(tool, inv, declared, source="", placeholder="TODO", width=96):
    """A paste-ready accounting block with the evidence for each decision beside it.

    PRINTED TO PASTE, NOT WRITTEN INTO THE FILE. This tool already has that idiom - every run fits
    both memory terms "and prints them ready to paste" - and it is right here for a reason beyond
    consistency: inserting a nested dict into Python source means an AST round-trip that loses the
    comments a plugin is mostly made of, or a regex over somebody's declaration.

    A NAME IS THE ONE THING THE DECIDER ALREADY HAS. The first version listed thirty-five of them
    and left somebody to open thirty-five documentation pages and read five thousand lines of
    plugin. Both answers are already available: what the function draws is in the package, and
    whether this wrapper calls it is in the wrapper. Each entry now carries the upstream signature
    and summary line, and the call site with the string literals on it - which for cellchat is
    `npng("heatmap_count", netVisual_heatmap(cc, ...))`, the output's own name.

    NOTHING IS DECIDED HERE. Every undecided entry stays a placeholder however strong the evidence,
    so a half-filled worksheet pasted into a plugin does not validate. A wrong `use` reads as a
    decision and is worse than an absent one.

    What is already decided is carried through unchanged, so this is re-runnable after a version
    bump and the answer is then the diff.
    """
    detail = getattr(inv, "detail", None) or {}
    names = list(getattr(inv, "names", inv) or [])
    calls = callsites(source, names) if source else {}
    decided = dict(declared or {})
    known = [n for n in names if n in decided]
    new = [n for n in names if n not in decided]
    stale = [n for n in decided if n not in names]

    L = [f'    # {len(names)} function(s) exported by {tool}. '
         f'{len(known)} already decided, {len(new)} to rule on; '
         f'{sum(1 for n in new if n in calls)} of those are called by this plugin.',
         '    "native_plots": {']
    for n in known:
        L.append(f'        {n!r}: {decided[n]!r},')
    if new:
        L += ['        # ---- NOT YET RULED ON. Each is either USED - say where its output lands -',
              '        # or SKIPPED for one of exactly three reasons, with what that reason supplies:',
              '        #   {"use": "figures/x.png"}',
              '        #   {"skip": "not_applicable",       "evidence": "..."}',
              '        #   {"skip": "superseded_by_design", "panel": "...", "defect": "..."}',
              '        #   {"skip": "duplicate_of",         "same_as": "..."}',
              '        # "reimplemented", "not considered" and "dependency missing" are rejected by',
              '        # name; see scprofile/native.py.']
        for n in new:
            d = detail.get(n) or {}
            sig = d.get("signature") or ""
            summary = d.get("summary") or ""
            # THE SUMMARY GETS ITS OWN LINE. Both on one, truncated together, meant decoupler's
            # signatures - which carry full type annotations and a return type - pushed the
            # docstring line off the end, losing the single most useful thing on the row.
            L.append(f"        # {n}{_clip(sig, 104)}")
            if summary:
                L.append(f"        #   {_clip(summary, 104)}")
            if d.get("deprecated"):
                L.append("        #   DEPRECATED upstream. Using it ties this plugin to something "
                         "its author is removing.")
            c = calls.get(n)
            if c:
                where = "in a COMMENT at" if c["in_comment"] else "called at"
                L.append(f'        #   {where} line {c["line"]}: {c["text"]}')
                if c["literals"]:
                    L.append(f'        #   strings on that line: '
                             f'{", ".join(repr(x) for x in c["literals"])}')
                L.append(f'        {n!r}: {{"use": "{placeholder} — confirm where this lands"}},')
            else:
                L.append("        #   not called anywhere in this plugin.")
                L.append(f'        {n!r}: {{"use": "{placeholder} — use it, or which skip '
                         f'applies?"}},')
    L.append("    },")
    if stale:
        L.append(f"    # DECLARED AND NO LONGER EXPORTED by {tool}: {sorted(stale)}")
        L.append("    # Either the upstream dropped them or the inventory pattern stopped")
        L.append("    # matching. Both are worth knowing; neither is fixed by deleting the line.")
    return "\n".join(L)


def callsites(source, names, window=3):
    """{name: {line, text, context, literals, in_comment}} for every inventory name the code calls.

    THE ACCOUNTING IS MOSTLY ALREADY WRITTEN, IN THE PLUGIN. Thirty-two of cellchat's thirty-five
    entries say where a function's output lands, and the plugin is what put it there - so asking a
    maintainer to supply that is asking them to re-derive what the file in front of them states.

    EVIDENCE, NOT A GUESS AT THE ANSWER. The first version tried to name the output by looking for
    the nearest path literal, and found one for 1 of 32 - because the outputs are not path
    literals. cellchat's line reads `npng("heatmap_count", netVisual_heatmap(cc, ...))`: the name
    is the first argument of the plugin's own saving wrapper, and the declared use is
    `figures/native_heatmap_{count,weight}.png`, assembled by a convention this module must not
    learn. Encoding `npng` here would be one plugin's habit compiled into a suite that serves five
    repositories.

    So this reports the call, the lines around it, and the string literals on it. Everything a
    reader needs to write the entry is then in front of them, and nothing has been decided for
    them - a wrong `use` reads as a decision, which is worse than an absent one.

    A MATCH IN A COMMENT IS STILL WORTH REPORTING and is marked as one. `rankNet`'s only mention is
    the comment "return.data, nothing drawn", which is precisely the evidence the entry needs; a
    scan that hid it would have thrown away the answer. Non-comment matches are preferred.
    """
    lines = source.splitlines()
    out = {}
    for name in names:
        tail = str(name).split(".")[-1]
        if not tail:
            continue
        # `(?<!\w)` AND NOT `(?<![\w.])`. Excluding a preceding dot rejected `sc.pl.umap(adata)`,
        # which is how every scanpy plot is called - so this found nothing in the eight Python
        # plugins, the ones that need it. A word character still excludes `foo_umap(`.
        rx = re.compile(r"(?<!\w)" + re.escape(tail) + r"\s*\(")
        best = None
        for i, line in enumerate(lines):
            if not rx.search(line):
                continue
            comment = line.lstrip().startswith("#")
            if best is None or (best["in_comment"] and not comment):
                best = {"line": i + 1, "text": line.strip()[:120],
                        "context": [l.rstrip()[:120] for l in lines[i + 1:i + 1 + window]],
                        "literals": [x for x in re.findall(r"[\"\']([^\"\'\n]{2,80})[\"\']", line)
                                     if not x.isspace()][:4],
                        "in_comment": comment}
            if best and not best["in_comment"]:
                break
        if best:
            out[name] = best
    return out


def stage_command(doc, point_name, stage_name):
    """The argv a stage declares, or []. Stages that are a command say so; the rest are not."""
    _ph, _up, stages = plan(doc, point_name)
    for st in stages:
        if st["name"] == stage_name:
            return list(st.get("command") or [])
    return []


def fill(argv, values):
    """`{python}` and `{run}` substituted by name. EXPLICIT, never `str.format`.

    A declaration is somebody else's text and may contain a brace for its own reasons; `format`
    would raise on it, or worse, substitute something. The same rule the ladder already follows.
    """
    out = []
    for tok in argv:
        s = str(tok)
        for k, v in values.items():
            s = s.replace("{" + k + "}", str(v))
        out.append(s)
    return out
