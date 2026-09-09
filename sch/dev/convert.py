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

import ast
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
        # A FIELD THAT IS PRESENT IS NOT ALWAYS A STAGE THAT IS FINISHED. velocity's `native_plots`
        # holds two of scvelo's twenty and its `wraps.plots_unreviewed` says the other eighteen are
        # unruled - and this reported the stage as done, because the field was there and carried no
        # placeholder. The plugin was telling the truth in one field and the status was reading the
        # other. A point declares which field, if any, means the work is still outstanding.
        partial = ""
        if not missing and st.get("outstanding_if"):
            said = _dotted(spec, st["outstanding_if"])
            if said:
                partial = str(said)
        out.append({"stage": st["name"],
                    "partial": partial,
                    "kind": st.get("kind", "mechanical"),
                    # BUILD OR TEST, and the split is the point. A BUILD stage reads source - the
                    # plugin's own code, or the wrapped tool's signatures and namespace - and
                    # touches no data at all, so it CANNOT be overfitted to a cohort. A TEST stage
                    # needs something to run on, and that is where a fixture or an existing
                    # dataset belongs.
                    #
                    # Keeping them apart is what stops the build reaching for a real cohort
                    # because that is where the data happens to be. A plugin whose build is
                    # complete is finished as a piece of code; whether it is CORRECT is the test
                    # stage's question and a different one.
                    "phase": st.get("phase", "build"),
                    "fills": list(st["fills"]),
                    "done": not missing and not partial,
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


def format_status(rows, name, point_name, doc=None, root=".", python="", run=""):
    """The line-per-stage a person reads to know where a conversion stands.

    REPORTED IN TWO HALVES, because they are two different claims. "The build is complete" says
    this plugin is finished as a piece of code and was written without any data in front of it -
    which is the only way to know it was not shaped around one cohort. "The tests pass" says it
    behaves, and needs something to run on.
    """
    L = []
    for phase, headline in (("build", "BUILD - reads source only, so it cannot be fitted to a "
                                      "cohort"),
                            ("test", "TEST - needs something to run on: the fixture, or a "
                                     "dataset you already have")):
        group = [r for r in rows if r.get("phase", "build") == phase]
        if not group:
            continue
        done = sum(1 for r in group if r["done"])
        L.append(f"{name}  ({point_name})  {phase}: {done} of {len(group)} complete    {headline}")
        for r in group:
            mark = ("done" if r["done"]
                    else "PART" if r.get("partial")
                    else "ASK " if r["kind"] == "judgement" else "todo")
            L.append(f"  {mark} {r['stage']:12s} {', '.join(r['fills'])}")
            if r.get("partial"):
                L.append(f"       started, and the plugin says so: {r['partial'][:150]}")
            elif not r["done"]:
                L.append(f"       unfilled: {', '.join(r['missing'])}")
                if r["why"]:
                    L.append(f"       {r['why']}")
        L.append("")
    todo = [r for r in rows if not r["done"]]
    if not todo:
        L.append("  nothing left to convert")
        return "\n".join(L)
    L.append("  what is left, in order:")
    for r in todo:
        # `doc` IS OPTIONAL AND MUST BE. A caller that only wants the summary should not have to
        # hand over the declaration; without it the stages are still named and only the commands
        # are missing, which is a smaller loss than a TypeError.
        cmd = advance_command(r, doc, point_name, root, name, python, run) if doc else ""
        if cmd:
            L.append(f"    {r['stage']:12s} {cmd}")
        else:
            L.append(f"    {r['stage']:12s} nothing runs this - it is what only you can answer: "
                     f"{', '.join(r['missing'])}")
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
        # AS MUCH OF THE DOTTED NAME AS THE INVENTORY GIVES. Matching the tail alone reported
        # scvelo's `pl.paga` as called at `scv.tl.paga(...)` - a different submodule - and
        # `pl.plot` at `ctx.plot()` and `pl.scatter` at `ax.scatter(...)`, neither of them scvelo
        # at all. Three of seven "called" were wrong, presented as evidence, and each would have
        # sent somebody to write a `use` entry for a function this plugin never calls.
        #
        # `(?<!\w)` and not `(?<![\w.])` on the front: excluding a preceding dot rejected
        # `sc.pl.umap(adata)`, which is how every scanpy plot is called, so it found nothing in
        # the eight Python plugins. A word character still excludes `foo_umap(`.
        want = ".".join(str(name).split(".")[-2:]) if "." in str(name) else tail
        rx = re.compile(r"(?<!\w)" + re.escape(want).replace(r"\.", r"\.") + r"\s*\(")
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


# -----------------------------------------------------------------------------------------------
# SCANS READ THE PLUGIN. EXTRACTORS READ THE UPSTREAM. Keeping the two apart is what stops this
# module learning one package's habits: everything below parses the wrapper, which this family
# wrote and can therefore rely on being Python.
# -----------------------------------------------------------------------------------------------


def _aliases(tree, tool):
    """{local name: dotted upstream path} for every way this file names the wrapped tool.

    THE IMPORTS ARE INSIDE THE FUNCTIONS, deliberately - `scprofile/plugin.py` requires it, because
    module scope runs in the HOST's interpreter, which has none of the plugin's pins. So this walks
    the whole tree rather than the module body, and a grep for `^import` finds almost nothing.
    """
    root = str(tool).split(".")[0]
    out = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for al in node.names:
                if al.name == root or al.name.startswith(root + "."):
                    out[al.asname or al.name.split(".")[0]] = al.name
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod == root or mod.startswith(root + "."):
                for al in node.names:
                    out[al.asname or al.name] = f"{mod}.{al.name}"
    return out


def _dotted_name(node):
    """`sc.tl.score_genes` out of an ast attribute chain, or ""."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return ""
    parts.append(node.id)
    return ".".join(reversed(parts))


def upstream_calls(source, tool):
    """{upstream dotted path: {line, passes:[kwarg names], text}} for calls into the wrapped tool.

    WHICH FUNCTIONS THIS WRAPPER ACTUALLY DRIVES, which is the set whose defaults matter. A tool
    exports hundreds; a plugin calls a handful, and it is that handful whose parameters are being
    inherited silently. `passes` is what the call names explicitly - everything else in the
    signature is a default nobody has looked at.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}
    al = _aliases(tree, tool)
    if not al:
        return {}
    out = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _dotted_name(node.func)
        if not name:
            continue
        head, _, rest = name.partition(".")
        if head not in al:
            continue
        full = al[head] + ("." + rest if rest else "")
        got = out.setdefault(full, {"line": node.lineno, "passes": set(), "calls": 0,
                                    "splat": False})
        got["calls"] += 1
        for kw in node.keywords:
            if kw.arg:
                got["passes"].add(kw.arg)
            else:
                # `f(**opts)` HIDES EVERY KEYWORD IT PASSES. Not the case in any shipped plugin,
                # but "passes: nothing by name" would otherwise be reported for a call that in
                # fact names all of them - the same blind spot the contract scan has for a
                # computed emit name, and knowable at the same moment.
                got["splat"] = True
    for v in out.values():
        v["passes"] = sorted(v["passes"])
    return out


def _satisfies(installed, pin):
    """Crudely: does this version sit inside this pin? Only used to decide whether to WARN."""
    m = re.findall(r"(>=|<=|==|<|>)\s*([0-9][0-9.]*)", str(pin))
    if not m:
        return True
    def parts(v):
        return tuple(int(x) for x in re.findall(r"\d+", v)[:3])
    got = parts(installed)
    for op, ver in m:
        want = parts(ver)
        n = min(len(got), len(want)) or 1
        a, b = got[:n], want[:n]
        if op == ">=" and not a >= b: return False
        if op == ">" and not a > b: return False
        if op == "<=" and not a <= b: return False
        if op == "<" and not a < b: return False
        if op == "==" and a != b: return False
    return True


def defaults_worksheet(tool, calls, params, declared, placeholder="TODO", pins=None):
    """What the wrapper is inheriting from the tool without saying so.

    `config` MEANS "THE TOOL'S OWN DEFAULTS, DECLARED RATHER THAN INHERITED", and the failure it
    exists to stop is silent: `predict_terminal_states()` was called bare, so the single number
    deciding which macrostates the fate probabilities are probabilities OF appeared nowhere a
    reader could see it. Nothing in the plugin was wrong; nothing said what it had chosen.

    Three groups, because they need three different decisions:
      PASSED      the call names it. Already a decision, and only worth declaring in `config` if a
                  user should be able to change it.
      INHERITED   the call does not name it and the tool has a default. THIS IS THE GROUP THE
                  STAGE IS FOR - each is a choice made by somebody else, invisible in the report.
      REQUIRED    no default upstream, so the call must supply it. Not a config question.

    Nothing is decided here either. An inherited default is not automatically a `config` key: most
    are noise and a handful decide the answer, and only a person who understands the method can
    say which. What the machine can do is stop them being invisible.
    """
    decided = set((declared or {}).keys())
    L = [f"    # {tool}: what this wrapper inherits without declaring it.",
         '    "config": {']
    for path in sorted(calls):
        info = params.get(path) or {}
        if not info.get("found"):
            # A MISSING ATTRIBUTE IS USUALLY THE WRONG INTERPRETER, AND THE TOOL KNOWS IT. Asked
            # with a python holding decoupler 2.2.0 about a plugin pinned to >=1.8,<1.9, this said
            # only "module has no attribute run_ulm" - true, useless, and it reads as a broken
            # plugin. The version is in hand and the pin is in the declaration; saying both turns
            # a puzzle into the answer.
            L.append(f"        # {path}: could not read its signature - {info.get('why_not', '')}")
            inst, want = info.get("installed", ""), (pins or {}).get(path.split(".")[0], "")
            if inst or want:
                L.append(f"        #      this interpreter has {inst or 'an unknown version'}"
                         + (f"; the plugin pins {want}" if want else ""))
                if inst and want and not _satisfies(inst, want):
                    L.append("        #      THOSE DISAGREE. Ask with the interpreter this plugin "
                             "runs in - `scprofile install <name> --prefix DIR` builds it - "
                             "because a signature from another version is one it will never see.")
            continue
        passed = set(calls[path].get("passes") or ())
        inherited = [q for q in info["params"]
                     if not q["required"] and q["name"] not in passed and q["name"] != "self"]
        required = [q["name"] for q in info["params"] if q["required"]]
        L.append(f"        # ---- {path}  (called at line {calls[path]['line']})")
        if info.get("summary"):
            L.append(f"        #      {_clip(info['summary'], 100)}")
        L.append(f"        #      passes: {sorted(passed) or 'nothing by name'}")
        if calls[path].get("splat"):
            L.append("        #      AND `**kwargs`, so this scan cannot see every keyword it "
                     "passes; the inherited list below may be too long.")
        if required:
            L.append(f"        #      required by the signature: {required}")
        if not inherited:
            L.append("        #      inherits nothing - every optional parameter is named.")
            continue
        L.append(f"        #      INHERITED SILENTLY ({len(inherited)}): each is a default chosen "
                 f"by {tool}, not by this plugin.")
        for q in inherited:
            # A CONFIG KEY OF THE SAME NAME IS NOT THE SAME PARAMETER, and saying "already in
            # config" for one implied it was handled. velocity declares `min_confidence` default
            # 0.5 - its OWN threshold for a figure gate - and calls `scv.tl.latent_time(A)` bare,
            # which inherits scvelo's `min_confidence` of 0.75. Two values, one name, both live in
            # the same plugin, and a reader of the config would reasonably think they were one.
            if q["name"] in decided:
                mine = (declared or {}).get(q["name"]) or {}
                mine_d = mine.get("default", "?") if isinstance(mine, dict) else "?"
                mark = (f'NAME COLLISION: this plugin declares `{q["name"]}` (default {mine_d!r}) '
                        f'and does NOT pass it here, so {tool} uses {q["default"]}')
            else:
                mark = f'{placeholder} — declare it, or leave it and say nothing?'
            L.append(f'        #        {q["name"]:24s} = {q["default"]:<22s} {mark}')
    L.append("    },")
    return "\n".join(L)


#: Names that mean "this fetches something the user did not supply". Deliberately broad: a false
#: positive costs a glance at a line number, and a missed reference is one the plan cannot warn
#: about and the report cannot name.
_FETCHY = re.compile(r"^(get|fetch|load|download|read)_|^(get|fetch|download)$", re.I)
_URL = re.compile(r"https?://[^\s\"\'<>)]+")


def _literal_items(node):
    """The strings a module-level assignment holds, seeing through a trailing `.split()`.

    THE FIRST VERSION MISSED THE ONLY REAL FINDING. cellcycle's gene sets are written
    `S_GENES = <triple-quoted block>.split()`, which is a Call and not a literal, so
    `ast.literal_eval` raised and the 97 symbols this plugin scores every cell against were
    invisible - while a docstring assigned to a variable came back as a 29-entry data set.
    """
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
            and node.func.attr == "split":
        node = node.func.value
    try:
        value = ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError):
        return []
    if isinstance(value, str):
        return [t for t in value.split() if t]
    if isinstance(value, (list, tuple, set, frozenset)):
        return [t for t in value if isinstance(t, str)]
    return []


#: A symbol, not a word. `origin (29 entries, e.g. on, the, single)` was a docstring split on
#: whitespace and reported as a data set; requiring most entries to look like identifiers rather
#: than prose is what tells 97 gene symbols from a paragraph.
_SYMBOL = re.compile(r"^[A-Z0-9][A-Z0-9._:-]{1,}$")


def references_in(source, tool="", min_items=20, symbol_share=0.7):
    """[{kind, what, line, why}] for everything this plugin consults that is not the user's object.

    THREE SHAPES, and the third is the one that hides. A URL is obvious. A call named
    `get_progeny` is nearly obvious. A gene list pasted into the file is not obvious at all -
    cellcycle carries 97 symbols from Tirosh et al. 2016, declares `references: None`, and the
    report therefore cannot say where its phase calls came from. Its own comment says HUMAN
    symbols, which is the case the format warns about: a prior published for one organism returns
    a small plausible table for the wrong one rather than failing.

    A LITERAL IS A `bundled` REFERENCE. It ships with the plugin and is pinned by the plugin's
    version, which is what that tier means; being spelled in Python rather than downloaded changes
    who stores it, not whether it decides the answer.

    URLS IN PROSE ARE NOT REFERENCES. Every plugin records its upstream's homepage and docs in its
    own declaration, and reporting those made each plugin look like it had two undeclared fetches.
    Only URLs in executable code count - a URL something actually goes to.
    """
    out = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return out
    docs = {id(n) for n in ast.walk(tree)
            if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            and getattr(n, "body", None) and isinstance(n.body[0], ast.Expr)
            and isinstance(n.body[0].value, ast.Constant)
            for n in [n.body[0].value]}
    declared = {id(n) for a in tree.body
                if isinstance(a, ast.Assign) and getattr(a.targets[0], "id", "") == "PLUGIN"
                for n in ast.walk(a)}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        if id(node) in docs or id(node) in declared:
            continue
        for u in _URL.findall(node.value):
            out.append({"kind": "fetch", "what": u, "line": getattr(node, "lineno", 0),
                        "why": "a URL in executable code. Declare it with a checksum, or say "
                               "which tier it is."})
    if tool:
        for path, info in sorted(upstream_calls(source, tool).items()):
            if _FETCHY.match(path.rsplit(".", 1)[-1]):
                out.append({"kind": "runtime?", "what": path, "line": info["line"],
                            "why": "named like something that fetches. If it reaches the network "
                                   "at run time the COMPUTE NODE needs a route, and a node "
                                   "without one fails after the queue slot is spent."})
    for node in tree.body:
        if not isinstance(node, ast.Assign) or not isinstance(node.targets[0], ast.Name):
            continue
        items = _literal_items(node.value)
        if len(items) < min_items:
            continue
        share = sum(1 for t in items if _SYMBOL.match(t)) / len(items)
        if share < symbol_share:
            continue
        out.append({"kind": "bundled",
                    "what": f"{node.targets[0].id} ({len(items)} entries, e.g. "
                            f"{', '.join(items[:3])})",
                    "line": node.lineno,
                    "why": "a data set written into the plugin. It ships with this file and is "
                           "pinned by its version - that is what `bundled` means - and the report "
                           "cannot name it while it is undeclared."})
    return out


def contract_in(source):
    """{produces:[...], reads:[...]} inferred from what the plugin emits and asks `ctx` for."""
    produces, reads = [], set()
    #: Emissions whose name is COMPUTED, so this scan cannot say what they are called. velocity
    #: emits inside `for col in ...: ctx.emit_obs(col, ...)` and as an f-string, which is why a
    #: scan of it finds 3 tables where the declaration has 9. THAT DIFFERENCE IS NOT EVIDENCE THE
    #: DECLARATION IS WRONG, and presenting the found set as if it were a replacement would have
    #: deleted six correct entries.
    dynamic = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {"produces": [], "report.figures": [], "reads": [], "dynamic": []}
    # FIGURES ARE NOT `produces` AND MUST NOT BE OFFERED AS IF THEY WERE. They are declared in
    # `report.figures`, each with the question it settles; listing them here sent a reader to add
    # five entries to the wrong field. Grouped by where each one is declared.
    EMIT = {"emit_obs": ("produces", "obs[{}]"), "emit_obsm": ("produces", "obsm[{}]"),
            "emit_layer": ("produces", "layers[{}]"), "emit_table": ("produces", "tables/{}"),
            "emit_figure": ("report.figures", "{}")}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            fn = node.func.attr
            if fn in EMIT and node.args:
                where, shape = EMIT[fn]
                arg = node.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    produces.append((where, shape.format(arg.value)))
                else:
                    dynamic.append((fn, node.lineno, ast.unparse(arg)[:60]
                                    if hasattr(ast, "unparse") else "<computed>"))
        if isinstance(node, ast.Attribute) and _dotted_name(node).startswith("ctx."):
            reads.add(_dotted_name(node).split(".", 2)[1])
        if isinstance(node, ast.Subscript) and _dotted_name(node.value) == "ctx.keys" \
                and isinstance(node.slice, ast.Constant):
            reads.add(f"keys[{node.slice.value}]")
    out = {"produces": [], "report.figures": [], "reads": sorted(reads), "dynamic": dynamic}
    for where, what in sorted(set(produces)):
        out[where].append(what)
    return out


#: The convert actions that advance a stage of the same name. `judgement` has none and never will.
ADVANCES = ("contract", "defaults", "references", "inventory", "measure")


def advance_command(row, doc, point_name, root, name, python="", run=""):
    """The literal command that moves this stage on, or "" when only a person can.

    `next: inventory` TOLD AN AGENT WHERE IT WAS AND NOT WHAT TO DO. Knowing that
    `sch dev convert account --python <the plugin's own interpreter>` is the thing requires already
    knowing the tool, which is exactly what somebody arriving at a half-built plugin does not have.
    A status that names the stage and withholds the command is a status you need a guide beside.
    """
    stage = row["stage"]
    declared = stage_command(doc, point_name, stage)
    if declared:
        return " ".join(fill(declared, {"python": python or "python3", "run": run or "<RUNDIR>",
                                        "root": root, "name": name}))
    if stage in ADVANCES:
        # `inventory` IS SEEN WITH ONE ACTION AND DECIDED WITH ANOTHER. `inventory` lists what the
        # tool exports; `account` turns that into the worksheet with the evidence attached, which
        # is the one somebody actually works from.
        action = "account" if stage == "inventory" else stage
        cmd = f"sch dev convert {action} --root {root} --point {point_name} --name {name}"
        if stage in ("inventory", "defaults"):
            cmd += f" --python {python or '<the interpreter this plugin runs in>'}"
        return cmd
    return ""


def plan_of_work(rows, doc, point_name, root, name, python="", run=""):
    """[(stage, command|'', what a person must decide)] for every stage not yet done, in order."""
    out = []
    for r in rows:
        if r["done"]:
            continue
        out.append((r, advance_command(r, doc, point_name, root, name, python, run),
                    r["kind"] == "judgement"))
    return out
