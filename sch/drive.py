"""One request, every stage: the stage driver (harness W041, ROUTE R03; GAP-001's driver part).

A cohort's stages are separate stacks, not mounts on one: every adapter reads ITS stack's
observations as a parts manifest, in place and pinned read-only, and refuses a view masked beneath
it. So the driver chains stacks. Stage 1's observations are the request's samplesheet; stage k's are
a manifest naming what stage k-1 HANDED ON, read from stage k-1's own record (its mount's out.json),
never from a promoted path. Each stage is the kernel's ordinary path - `Stack.init`, the plugin
declared in its `stack.yml`, `run_declared()` (what `sch run --stack DIR` does), `report()` - and then
sealed: its outputs read-only, so the next stage can pin them, and `SEALED.json` beside them.

It adds no analysis and hides none. Every flag is the request's, passed verbatim; every other flag is
the tool's own default. What a stage cannot run is said by that stage's declaration or its adapter's
refusal, quoted. A choice a tool declares as the user's (`decisions:` in its plugin.yml) is never
answered here: the run stops before that stage, naming it, and resumes from the answer, recorded
with who gave it.

Nothing about a cohort or a site is here. The request is data that lives with the cohort; this
module holds its schema (FIELDS) and `docs/request.example.yml` a synthetic example.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import time
from pathlib import Path

from . import yamlish

SCHEMA = 1
#: What a request holds, and nothing else: a misspelt field is a missing one that looks present.
FIELDS = {
    "request": "the schema version, 1",
    "observations": "the samplesheet: one row per library, a parts manifest (relative to the request)",
    "parts": "the samplesheet's column naming each library's object",
    "keys": "the profile's roles -> the samplesheet's and design's column names; `sample` is required",
    "design": "the design sheet (relative to the request)",
    "context": "what the dataset is, declared once: profile axes (assay, species, tissue, ...)",
    "upstream": "the steps the family does not perform, each by name: alignment and ambient",
    "stages": "in order, each {plugin, params}: params are the tool's own flags, verbatim",
    "resources": "the cohort's sizes, for the driver and per stage: {drive|<stage>: {ncpus, mem, walltime}}; "
                 "the queue is the site's, chosen from these by the site file's pbs.queues",
}
REQUIRED = ("request", "observations", "parts", "keys", "context", "upstream", "stages")
WAITING = 3          # the exit status of a run stopped at a user's decision
SHAPES = ("libraries", "joint")
#: What an unanswered decision does (autodev W042 fix 1, D): `stop` - the run stops before its stage
#: until it is answered (the tool has no default the driver may assume); `tool-default` - an escape the
#: tool declares (`describe` escapes[]) that lifts one of its refusals: unanswered, its flag is not
#: passed, which is the tool's own default, and the stage's events say so; answered, it is passed and
#: recorded with who gave it. Either way it is never a plain param.
UNANSWERED = ("stop", "tool-default")
#: What the plan says of the tool a stage wraps.
WRAPS = ("tool", "version")
#: The driver's own job, as `resources:` names it beside the stages' short names.
DRIVE = "drive"
#: A size, in the words a request and a tool's `resources:` use (the pbs executor writes `select`).
SIZE_WORDS = ("ncpus", "mem", "walltime", "select")
#: What a site's job.yml declares for a generated job: where the harness is, the kernel's
#: interpreter, where run directories go (relative to the job's own directory), and shell lines.
JOB_SITE = ("harness", "python", "runs", "setup", "submit")
#: What a site's job.yml must declare; the rest is optional.
JOB_REQUIRED = ("harness", "python", "runs")


class RequestError(ValueError):
    """Refused before any tool starts. The message names what was refused and the fix."""


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _sha(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _resolve(ref: str):
    """A plugin by path or by name, searched as a stack searches (SCH_PLUGINS, then shipped)."""
    from .registry.manifest import load_manifest
    p = Path(ref)
    if p.exists() and (p / "plugin.yml").exists():
        return load_manifest(p)
    roots = [Path(x) for x in os.environ.get("SCH_PLUGINS", "").split(":") if x]
    roots.append(Path(__file__).resolve().parent.parent / "plugins")
    for root in roots:
        for cand in (root / ref, *sorted(root.glob(f"*/{ref}"))):
            if (cand / "plugin.yml").exists():
                m = load_manifest(cand)
                if m.name == ref:
                    return m
    raise RequestError(f"plugin {ref!r} not found under {[str(r) for r in roots]}")


def _site_pbs():
    """The site's `pbs:` block when its stack layer runs stages on the scheduler, else None."""
    site = os.environ.get("SCH_SITE")
    f = Path(site) / "stack.yml" if site else None
    if f is None or not f.is_file():
        return None
    layer = yamlish.load(f) or {}
    return dict(layer["pbs"]) if str(layer.get("executor")) == "pbs" and isinstance(layer.get("pbs"), dict) else None


def _hands_on(m, params: dict) -> list:
    """The shapes a stage hands the next one: its declaration, each shape's condition a param."""
    out = []
    for shape, when in dict(m.data.get("hands_on") or {}).items():
        if when is None or when in params:
            out.append(shape)
    return out


# ---------------------------------------------------------------------------- the request
def load(path, files: bool = True) -> dict:
    """Read and check a request. Everything a refusal needs is decided here, before any tool.
    `files=False` (a job generated where it is authored, not where it runs): the samplesheet and the
    design are named, not opened - they may be the cluster's only - and the job's own `sch run` checks
    them where they are."""
    from .profile import load_profile
    src = Path(path).resolve()
    if not src.is_file():
        raise RequestError(f"no request at {src}")
    try:
        doc = yamlish.load(src)
    except Exception as e:                       # noqa: BLE001 - the reader's own words, quoted
        raise RequestError(f"{src.name} is not a request: {e}") from None
    if not isinstance(doc, dict):
        raise RequestError(f"{src.name} is not a mapping of {', '.join(FIELDS)}")
    unknown = sorted(set(doc) - set(FIELDS))
    if unknown:
        raise RequestError(f"the request declares {', '.join(map(repr, unknown))}, which is not a request "
                           f"field; its fields are {', '.join(FIELDS)}")
    absent = [k for k in REQUIRED if doc.get(k) in (None, "", [], {})]
    if absent:
        raise RequestError(f"the request declares no {', '.join(absent)}: "
                           + "; ".join(f"{k}: {FIELDS[k]}" for k in absent))
    if doc["request"] != SCHEMA:
        raise RequestError(f"request: {doc['request']!r}; this harness reads schema {SCHEMA}")
    base = src.parent

    def where(k):
        p = Path(str(doc[k]))
        p = p if p.is_absolute() else base / p
        if files and not p.is_file():
            raise RequestError(f"{k}: {p} is not a file")
        return str(p)
    keys = doc["keys"]
    if not isinstance(keys, dict) or not keys.get("sample"):
        raise RequestError("keys: declares no `sample`, the column naming each library")

    # ---- the context: one word per fact, each fact once (rule 2; W041 point 3)
    ctx = doc["context"]
    if not isinstance(ctx, dict):
        raise RequestError("context: is not a mapping of profile axes")
    # a word is its letters: " snrna " is snrna, and what reaches the stacks is the trimmed word
    # (autodev W042 fix 1, observation 3)
    ctx = {str(k): (str(v).strip() if v is not None else v) for k, v in ctx.items()}
    assay = str(ctx.get("assay") or "").strip()
    if not assay:
        raise RequestError("the request declares no assay; single cells and single nuclei are separate "
                           "rule sets in every tool, and none of them is a default (rule 2): "
                           "context: {assay: scrna | snrna}")
    if "organism" in ctx:
        raise RequestError("context: declares `organism`; the species is one fact, declared once as "
                           "`species`, and each adapter writes it in its tool's own word")

    # ---- the stages, each read from its own declaration
    stages = doc["stages"]
    if not isinstance(stages, list):
        raise RequestError("stages: is not a list of {plugin, params}")
    plan, seen = [], set()
    for i, s in enumerate(stages, 1):
        if not isinstance(s, dict) or not s.get("plugin"):
            raise RequestError(f"stages[{i}]: declares no plugin")
        extra = sorted(set(s) - {"plugin", "params"})
        if extra:
            raise RequestError(f"stages[{i}]: {', '.join(extra)} is not a stage field (plugin, params)")
        m = _resolve(str(s["plugin"]))
        params = dict(s.get("params") or {})
        short = m.name.split("@")[0]
        if short in seen:
            raise RequestError(f"stages[{i}]: a second {short!r} stage; each stage runs once")
        seen.add(short)
        # THE LIBRARY IS ONE FACT (autodev W042, GAP-C92): each tool takes the column naming each
        # library where its adapter declares (`library_key:`), and the driver writes the request's
        # keys.sample there, wherever that command is declared. A stage that names another column
        # is refused: two names for one column is how the fixture's second shape died at stage 4.
        lib = str(keys["sample"])
        paths = m.data.get("library_key") or []
        for path in [paths] if isinstance(paths, str) else list(paths):
            head, _, rest = str(path).partition(".")
            if rest and head not in params:
                continue                         # that command is not declared: nothing to tell it
            got = dict(params.get(head) or {}).get(rest) if rest else params.get(head)
            if got is not None and str(got) != lib:
                raise RequestError(f"stages[{i}] ({m.name}): {path} is {got!r}, but the request's library "
                                   f"column is keys.sample = {lib!r}; the library is one fact and the driver "
                                   f"writes it into every stage: drop {path} from the stage's params")
            params = _set(params, str(path), lib)
        # A FACT OF THE CONTEXT IS STATED ONCE (autodev W042 fix 1, observation 2): where a tool takes a
        # context axis as its own flag (`context_params:`), a stage that states it differently is two
        # facts for one, and refused; the same word, said twice, is the same fact.
        for axis, path in dict(m.data.get("context_params") or {}).items():
            head, _, rest = str(path).partition(".")
            got = dict(params.get(head) or {}).get(rest) if rest else params.get(head)
            want = ctx.get(axis)
            norm = lambda v: re.sub(r"[\s_-]+", "_", str(v).strip().casefold())  # noqa: E731
            if got is not None and want is not None and norm(got) != norm(want):
                raise RequestError(f"stages[{i}] ({m.name}): {path} is {got!r}, but the request's context "
                                   f"declares {axis} {want!r}; the {axis} is one fact, stated once in context: "
                                   f"write the context's word in {path}, or correct the context")
        decisions = []
        for d in m.data.get("decisions") or []:
            head, _, rest = str(d["param"]).partition(".")
            if (rest and rest in dict(params.get(head) or {})) or (not rest and head in params):
                raise RequestError(f"stages[{i}] ({m.name}): params set {d['param']}, which {m.name} declares "
                                   f"the user's decision {short}.{d['name']} ({d['what']}); the driver passes "
                                   f"it only as an answer recorded with who gave it: --answer "
                                   f"{short}.{d['name']}=VALUE --by WHO")
            if str(d.get("unanswered") or "stop") not in UNANSWERED:
                raise RequestError(f"{m.name}: decision {d['name']} declares unanswered: {d.get('unanswered')!r}; "
                                   f"it is one of {', '.join(UNANSWERED)}")
            decisions.append({"name": f"{short}.{d['name']}", "param": str(d["param"]), "what": d["what"],
                              "escape": d.get("escape"), "unanswered": str(d.get("unanswered") or "stop")})
        plan.append({"stage": f"{i:02d}_{short}", "plugin": m.name, "dir": str(m.dir),
                     "profile": m.profile, "version": m.version,
                     "wraps": {k: (m.data.get("wraps") or {}).get(k) for k in WRAPS},
                     "assays": list(m.data.get("assays") or []), "reads": m.data.get("reads"),
                     "hands_on": _hands_on(m, params), "params": params, "decisions": decisions,
                     "library_key": [paths] if isinstance(paths, str) else list(paths),
                     "resources": dict(m.data.get("resources") or {}),
                     "cannot_show": list(m.data.get("cannot_show") or [])})

    # ---- the sizes: the cohort's, per stage and for the driver; a tool's own default beneath them
    res = doc.get("resources") or {}
    if not isinstance(res, dict):
        raise RequestError("resources: is not a mapping of {drive | <stage>: {ncpus, mem, walltime}}")
    short = {p["stage"].split("_", 1)[1]: p for p in plan}
    for who, size in res.items():
        if who != DRIVE and who not in short:
            raise RequestError(f"resources: {who!r} is neither {DRIVE!r} nor a stage of this request "
                               f"({', '.join(short)})")
        if not isinstance(size, dict):
            raise RequestError(f"resources.{who}: is not a mapping of {', '.join(SIZE_WORDS)}")
        if "queue" in size:
            raise RequestError(f"resources.{who}: declares a queue; a queue is the site's, chosen from the "
                               f"size by the site file's pbs.queues - declare ncpus, mem and walltime")
        bad = sorted(set(size) - set(SIZE_WORDS))
        if bad:
            raise RequestError(f"resources.{who}: {', '.join(bad)} is not a size word ({', '.join(SIZE_WORDS)})")
        if who in short:
            short[who]["resources"] = {**short[who]["resources"], **{k: str(v) for k, v in size.items()}}

    # EVERY SIZE AGAINST THE SITE'S QUEUES BEFORE ANYTHING RUNS (autodev W042 fix 1, observation 1):
    # a size no queue holds is refused here, for every stage and the driver's own job, not when its
    # stage comes to be submitted after the ones before it ran. The site's queues are read where the
    # stages read them ($SCH_SITE/stack.yml); with no pbs site there is no queue to hold anything.
    site_pbs = _site_pbs()
    if site_pbs is not None:
        from .services.executor import ExecutorError, PbsExecutor
        for who, plugin, size in [(DRIVE, DRIVE, dict(res.get(DRIVE) or {}))] + [
                (p["stage"], p["plugin"], p["resources"]) for p in plan]:
            if not size:
                continue
            plugins = dict(site_pbs.get("plugins") or {})
            plugins[plugin] = {**dict(plugins.get(plugin) or {}), **{k: str(v) for k, v in size.items()}}
            try:
                PbsExecutor(config={**site_pbs, "plugins": plugins}).settings(plugin)
            except ExecutorError as e:
                raise RequestError(f"resources ({who}): {e}") from None

    # one spelling per assay: the word every stage's tool is declared to take
    words = [set(p["assays"]) for p in plan]
    common = sorted(set.intersection(*words)) if words else []
    if assay not in common:
        no = [p["plugin"] for p in plan if assay not in p["assays"]]
        raise RequestError(f"context: assay {assay!r} is not a word {', '.join(no)} declares; the family "
                           f"spells the two assays {', '.join(common) or '(none in common)'}, and each "
                           f"adapter writes them in its tool's own word")
    prof = load_profile(plan[0]["profile"])
    bad = sorted(set(ctx) - set(prof.axes))
    if bad:
        raise RequestError(f"context: {', '.join(bad)} is not an axis of {prof.id} ({', '.join(prof.axes)})")

    # ---- upstream: what produced the matrices, by name (step 1 alignment, step 2 ambient)
    up = doc["upstream"]
    rule = dict(prof.data.get("upstream") or {})
    steps = list(rule.get("steps") or [])
    if not isinstance(up, dict):
        raise RequestError("upstream: is not a mapping of steps")
    for step in steps:
        v = up.get(step)
        if not isinstance(v, dict) or not str(v.get("tool") or "").strip():
            raise RequestError(f"upstream: declares no {step}; name the tool that performed it, or "
                               f"`tool: none` - {step} is declared upstream, never inferred: "
                               f"upstream: {{{step}: {{tool: <name> | none}}}}")
    other = sorted(set(up) - set(steps))
    if other:
        raise RequestError(f"upstream: {', '.join(other)} is not an upstream step ({', '.join(steps)})")
    # RULE 2 BY WHAT MAY RUN, NOT BY WHAT MAY NOT (autodev W042 fix 1, A): a ban by name is spelt
    # around (the name with its version, its command line); the profile's `allowed` names
    # every tool a step may declare on an assay, and any other name is refused. The rule is the
    # profile's; this module holds no tool's name.
    if "never" in rule:
        raise RequestError(f"{prof.id}: upstream.never is not read; rule 2 is written as what may run "
                           f"(upstream.allowed.<assay>.<step>: [names])")
    for step, names in dict((rule.get("allowed") or {}).get(assay) or {}).items():
        said = str((up.get(step) or {}).get("tool") or "")
        if said.strip().casefold() not in [str(n).strip().casefold() for n in names or []]:
            raise RequestError(f"upstream: {step} by {said!r} on {assay}: not a tool {prof.id} allows there "
                               f"(upstream.allowed.{assay}.{step}: {', '.join(map(str, names or [])) or 'none'}); "
                               f"rule 2: a remover calibrated on nuclei is not lent to cells, and what may run "
                               f"upstream of {assay} is what the profile names - deliver the aligner's call "
                               f"(`tool: none`), or add a remover made for {assay} to the profile, reviewed")

    # ---- the chain: each stage reads a shape the stage before it hands on
    if plan[0]["reads"] != "libraries":
        raise RequestError(f"{plan[0]['plugin']} reads {plan[0]['reads']!r}; the request's observations are "
                           f"libraries, so the first stage must read libraries")
    for prev, nxt in zip(plan, plan[1:]):
        if nxt["reads"] not in prev["hands_on"]:
            cond = {s: w for s, w in dict(_resolve(prev["dir"]).data.get("hands_on") or {}).items()}
            how = (f"; {prev['plugin']} hands on {nxt['reads']} when its params declare "
                   f"{cond[nxt['reads']]!r}") if cond.get(nxt["reads"]) else ""
            raise RequestError(f"{nxt['plugin']} reads {nxt['reads']}; {prev['plugin']} hands on "
                               f"{', '.join(prev['hands_on']) or 'nothing'}{how}")
    return {"path": str(src), "sha256": _sha(src), "observations": where("observations"),
            "design": where("design") if doc.get("design") else None, "parts": str(doc["parts"]),
            "keys": {str(k): str(v) for k, v in keys.items()},
            "context": {str(k): str(v) for k, v in ctx.items()}, "upstream": up, "stages": plan,
            "drive_resources": {str(k): str(v) for k, v in dict(res.get(DRIVE) or {}).items()}}


def plan_lines(req: dict, answers: dict | None = None) -> list:
    answers = answers or {}
    a = req["context"]
    lines = [f"  request {req['path']} (sha256 {req['sha256'][:12]})",
             f"  context {', '.join(f'{k}={v}' for k, v in a.items())}",
             "  upstream " + "; ".join(f"{s}: {v.get('tool')}" for s, v in req["upstream"].items())]
    for p in req["stages"]:
        w = p["wraps"]
        lines.append(f"  {p['stage']:<8} {p['plugin']} {p['version']} ({w.get('tool')} {w.get('version')})  "
                     f"reads {p['reads']}, hands on {', '.join(p['hands_on']) or 'nothing'}")
        lines.append(f"           given: {', '.join(sorted(p['params'])) or 'nothing'}; every other flag: "
                     f"{w.get('tool')}'s own default")
        if p.get("library_key"):
            lines.append(f"           the library column: keys.sample={req['keys']['sample']} -> "
                         f"{', '.join(p['library_key'])}")
        if p.get("resources"):
            lines.append("           size: " + ", ".join(f"{k}={v}" for k, v in sorted(p["resources"].items()))
                         + " (on pbs, the site file's queues choose the queue)")
        for d in p["decisions"]:
            esc = f", {w.get('tool')}'s escape {d['escape']}" if d.get("escape") else ""
            got = (f"answered {json.dumps(answers[d['name']]['value'])} by {answers[d['name']]['by']}"
                   if d["name"] in answers else "UNANSWERED - the run stops before this stage"
                   if d["unanswered"] == "stop" else f"not passed ({w.get('tool')}'s default) unless answered")
            lines.append(f"           the user's: {d['name']} ({d['param']}{esc}) - {d['what']}; {got}")
    return lines


# ---------------------------------------------------------------------------- the run
#: The run's record of every file its request names, hashed when it starts (autodev W042 fix 1, B).
INPUTS = "INPUTS.json"


def _leaves(v, path=""):
    if isinstance(v, dict):
        for k, x in v.items():
            yield from _leaves(x, f"{path}.{k}" if path else str(k))
    elif isinstance(v, list):
        for i, x in enumerate(v):
            yield from _leaves(x, f"{path}[{i}]")
    else:
        yield path, v


def named_files(req: dict) -> dict:
    """EVERY FILE A REQUEST NAMES IS PART OF THE REQUEST (autodev W042 fix 1, B): {role: path} for
    the request, its samplesheet, its design, each library the samplesheet names (as the stack reads
    it: relative to the samplesheet) and each stage param that names a file. A resume on files that
    changed is another run's input under this run's record, so the run hashes them all."""
    from .services.dataset import read_manifest
    files = {"request": req["path"], "observations": req["observations"]}
    if req.get("design"):
        files["design"] = req["design"]
    sheet = Path(req["observations"])
    try:
        _head, rows = read_manifest(sheet)
    except Exception:                            # noqa: BLE001 - the stack's own init says what is wrong
        rows = []
    for i, r in enumerate(rows, 1):
        v = str(r.get(req["parts"]) or "").strip()
        f = Path(v) if Path(v).is_absolute() else sheet.parent / v
        if v and f.is_file():
            files[f"observations.{req['parts']}[{r.get(req['keys']['sample']) or i}]"] = str(f)
    for p in req["stages"]:
        for path, v in _leaves(p["params"]):
            if isinstance(v, str) and v.startswith(("/", "~/")) and Path(os.path.expanduser(v)).is_file():
                files[f"{p['stage']}.{path}"] = str(Path(os.path.expanduser(v)).resolve())
    return files


def _pinned(out: Path, req: dict, dfile: Path) -> dict:
    """The named files' hashes, recorded when the run starts and compared on every resume; and
    decisions.json's, so a recorded decision is changed by nobody but `sch run`."""
    now = {k: {"path": v, "sha256": _sha(v)} for k, v in named_files(req).items()}
    rec_f = out / INPUTS
    if not rec_f.exists():
        if (out / "request.json").exists():
            raise RequestError(f"{out} records no {INPUTS}: its stages ran on files nobody hashed, so a resume "
                               f"cannot say they are the same - start a new --out")
        rec = {"started_at": _now(), "files": now, "decisions_sha256": None}
        rec_f.write_text(json.dumps(rec, indent=1) + "\n")
        return rec
    rec = json.loads(rec_f.read_text())
    then = rec.get("files") or {}
    changed = [k for k in sorted(set(then) | set(now))
               if (then.get(k) or {}).get("sha256") != (now.get(k) or {}).get("sha256")]
    if changed:
        said = "; ".join(f"{k} {(then.get(k) or now.get(k))['path']} (sha256 "
                         f"{((then.get(k) or {}).get('sha256') or 'not named')[:12]} when the run started, "
                         f"{((now.get(k) or {}).get('sha256') or 'not named now')[:12]} now)" for k in changed)
        raise RequestError(f"{out} was started on other files: {said}. A run is one request and every file it "
                           f"names; a stage sealed on the old ones would be read beside one run on the new. "
                           f"Restore each file as it was, or start a new --out")
    if dfile.exists() and _sha(dfile) != rec.get("decisions_sha256"):
        raise RequestError(f"{dfile} was changed outside `sch run` (sha256 {_sha(dfile)[:12]}, recorded "
                           f"{str(rec.get('decisions_sha256'))[:12]}); a recorded decision is not rewritten: "
                           f"restore it, or start a new --out")
    return rec


def _record(out: Path, **rec):
    (out / "DRIVE.json").write_text(json.dumps({"at": _now(), **rec}, indent=1, default=str) + "\n")


def _set(params: dict, path: str, value) -> dict:
    head, _, rest = path.partition(".")
    out = json.loads(json.dumps(params))
    if rest:
        out.setdefault(head, {})[rest] = value
    else:
        out[head] = value
    return out


def _home(v):
    """A param's leading `~/` is the running user's home, as a shell would read it: a request names
    a tool's checkout without naming an account, and is read where it runs."""
    if isinstance(v, str) and v.startswith("~/"):
        return os.path.expanduser(v)
    if isinstance(v, list):
        return [_home(x) for x in v]
    if isinstance(v, dict):
        return {k: _home(x) for k, x in v.items()}
    return v


def _manifest(stage_dir: Path, shape: str, scope: str, handed: dict) -> tuple:
    """The next stage's observations: what the stage before it handed on, named where it lies."""
    f = stage_dir / "observations.tsv"
    if shape == "libraries":
        rows, col = [[scope, "h5ad"]] + [[k, v] for k, v in handed["libraries"].items()], scope
    else:
        rows, col = [["part", "h5ad"], [Path(handed["joint"]).name.split(".")[0], handed["joint"]]], "part"
    with open(f, "w", newline="", encoding="utf-8") as fh:
        csv.writer(fh, delimiter="\t", lineterminator="\n").writerows(rows)
    f.chmod(0o444)
    return f, col


def _seal(stage_dir: Path, run_dir: Path, rec: dict):
    """A stage's outputs read-only - a deliverable, so the next stage can pin it - and its seal."""
    for p in sorted((run_dir / "out").rglob("*")):
        if p.is_file() and not p.is_symlink():
            p.chmod(p.stat().st_mode & 0o555)
    (stage_dir / "SEALED.json").write_text(json.dumps({"sealed_at": _now(), **rec}, indent=1) + "\n")


def run(req: dict, out, answers_given: list | None = None, by: str | None = None) -> tuple:
    """(exit status, record). 0 sealed; 2 refused or a stage failed; 3 stopped at a user's decision."""
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    resume = f"sch run --request {req['path']} --out {out}"
    prior = out / "request.json"
    if prior.exists() and json.loads(prior.read_text())["sha256"] != req["sha256"]:
        raise RequestError(f"{out} was run from another request (sha256 "
                           f"{json.loads(prior.read_text())['sha256'][:12]}); a run is one request: "
                           f"start a new --out")
    dfile = out / "decisions.json"
    pins = _pinned(out, req, dfile)
    prior.write_text(json.dumps(req, indent=1, default=str) + "\n")
    names = {d["name"]: (p, d) for p in req["stages"] for d in p["decisions"]}
    answers = json.loads(dfile.read_text()) if dfile.exists() else {}
    for a in answers_given or []:
        name, sep, raw = str(a).partition("=")
        if not sep or name not in names:
            raise RequestError(f"--answer {a!r}: no stage declares a user's decision {name!r}; "
                               f"declared: {', '.join(names) or 'none'}")
        if not by:
            raise RequestError("--answer needs --by: a decision is recorded with who made it")
        try:
            value = json.loads(raw)
        except ValueError:
            value = raw
        if name in answers and answers[name]["value"] != value:
            raise RequestError(f"{name} is already answered {json.dumps(answers[name]['value'])} by "
                               f"{answers[name]['by']}; a recorded decision is not rewritten: start a new --out")
        answers.setdefault(name, {"value": value, "by": by, "at": _now(), "verbatim": a})
    dfile.write_text(json.dumps(answers, indent=1) + "\n")
    pins["decisions_sha256"] = _sha(dfile)
    (out / INPUTS).write_text(json.dumps(pins, indent=1) + "\n")
    inputs = {k: v["sha256"] for k, v in pins["files"].items()}

    handed, done = None, []
    for p in req["stages"]:
        sd = out / p["stage"]
        if (sd / "SEALED.json").exists():         # a sealed stage is never run again
            seal = json.loads((sd / "SEALED.json").read_text())
            handed, done = seal["hands_on"], done + [p["stage"]]
            continue
        if sd.exists():                          # a failed or interrupted attempt stays as its record
            n = 1
            while (out / f"{p['stage']}.failed-{n}").exists():
                n += 1
            sd.rename(out / f"{p['stage']}.failed-{n}")
        waiting = [d for d in p["decisions"] if d["name"] not in answers and d["unanswered"] == "stop"]
        if waiting:
            rec = {"status": "waiting", "stage": p["stage"], "sealed": done,
                   "waiting_for": waiting, "resume": resume + " " + " ".join(
                       f"--answer {d['name']}=VALUE" for d in waiting) + " --by WHO"}
            _record(out, **rec)
            return WAITING, rec
        params = dict(p["params"])
        for d in p["decisions"]:
            if d["name"] in answers:
                params = _set(params, d["param"], answers[d["name"]]["value"])

        def failed(why, fix, stack=None):
            rec = {"status": "failed", "stage": p["stage"], "plugin": p["plugin"], "sealed": done,
                   "reason": why, "fix": fix, "stack": str(sd), "resume": resume}
            open_ = [d for d in p["decisions"] if d["name"] not in answers and d["unanswered"] != "stop"]
            if open_:                            # the escapes this stage's tool declares, by name
                rec["escapes"] = [{"name": d["name"], "escape": d["escape"], "what": d["what"],
                                   "answer": f"--answer {d['name']}=VALUE --by WHO"} for d in open_]
            if stack is not None:
                stack.prov.append("drive/failed", stage=p["stage"], reason=why, fix=fix)
                stack.close()
            _record(out, **rec)
            return 2, rec
        if handed is not None and not (handed.get("joint") if p["reads"] == "joint" else handed.get("libraries")):
            return failed(f"{p['plugin']} reads {p['reads']}, and {done[-1]} handed on none (its out.json "
                          f"hands_on names no {p['reads']})", f"read {done[-1]}'s record: a stage that hands on "
                          f"no {p['reads']} cannot be read as one; run a new --out once it does")
        try:
            return_ = _stage(p, sd, req, handed, params, answers, done, failed)
        except Exception as e:                   # noqa: BLE001 - never leave the run marked running
            return failed(f"the driver stopped in {p['stage']}: {type(e).__name__}: {e}",
                          "read the stage's events; resume once the cause is corrected")
        if return_[0] is not None:
            return return_
        handed = return_[1]
        done.append(p["stage"])
    rec = {"status": "sealed", "sealed": done, "request": req["path"], "request_sha256": req["sha256"],
           "inputs": inputs, "decisions": answers, "upstream": req["upstream"],
           "reports": {s: str(out / s / "report" / "report.json") for s in done}}
    (out / "SEALED.json").write_text(json.dumps({"sealed_at": _now(), **rec}, indent=1, default=str) + "\n")
    _record(out, **rec)
    return 0, rec


def _stage(p, sd, req, handed, params, answers, done, failed) -> tuple:
    """One stage, as `sch init` + the declared mount + `sch report` + the seal: (None, handed on) when
    it sealed, else the failed record."""
    from .kernel import Stack
    from .services.invariant import InvariantFailure
    from .stack import StackError
    out = sd.parent
    inputs = {k: v["sha256"] for k, v in json.loads((out / INPUTS).read_text())["files"].items()}
    resume = f"sch run --request {req['path']} --out {out}"
    sd.mkdir(parents=True)
    if handed is None:
        obs, keys, parts = req["observations"], req["keys"], req["parts"]
    else:
        f, col = _manifest(sd, p["reads"], req["keys"]["sample"], handed)
        obs, keys, parts = str(f), {**req["keys"], "sample": col}, "h5ad"
    try:
        st = Stack.init(sd, p["profile"], obs, req["design"], keys, context=req["context"], parts=parts)
    except StackError as e:
        return failed(f"sch init refused: {e}", "correct what the refusal names, then resume")
    st.close()
    decl = yamlish.load(sd / "stack.yml")
    decl["plugins"] = {p["plugin"]: {"plugin": p["dir"], "params": _home(params)}}
    if p.get("resources"):
        # the stage's own run takes the stage's size; its probes, gates and companion keep the
        # site's default block (the pbs executor lays pbs.plugins.<name> over it, per run)
        decl["pbs"] = {"plugins": {p["plugin"]: dict(p["resources"])}}
    yamlish.dump(decl, sd / "stack.yml")
    st = Stack.open(sd)
    st.prov.append("drive/stage", request=req["path"], request_sha256=req["sha256"], stage=p["stage"],
                   plugin=p["plugin"], reads_from=done[-1] if done else "the request's observations")
    st.prov.append("upstream/declared", **{k: v for k, v in req["upstream"].items()})
    for d in p["decisions"]:
        if d["name"] in answers:
            st.prov.append("decision/answered", name=d["name"], param=d["param"], what=d["what"],
                           escape=d.get("escape"), **answers[d["name"]])
        else:                                # an escape nobody took: the tool's own default, said
            st.prov.append("decision/unanswered", name=d["name"], param=d["param"], what=d["what"],
                           escape=d.get("escape"), value=None, by=None,
                           said=f"not passed: {p['wraps'].get('tool')}'s default, the escape not taken")
    _record(out, status="running", stage=p["stage"], sealed=done, resume=resume)
    r = st.run_declared()[0]                 # what `sch run --stack DIR` does: the declared mount
    if not r.ok:
        return failed(f"{p['plugin']} {r.status}: {r.reason}", r.fix or "read the stage's stack", st)
    try:
        rep = st.report()
    except InvariantFailure as e:
        return failed(f"report refused: {e}", "read the stage's events", st)
    rd = st.run_dir(p["plugin"])
    got = (json.loads((rd / "out" / "out.json").read_text()).get("answer") or {}).get("hands_on") or {}
    handed = {"libraries": {k: str(rd / "out" / v) for k, v in (got.get("libraries") or {}).items()},
              "joint": str(rd / "out" / got["joint"]) if got.get("joint") else None}
    lost = [x for x in [*handed["libraries"].values(), handed["joint"]] if x and not Path(x).is_file()]
    if lost:
        return failed(f"{p['plugin']} names {lost[0]} as handed on and it is not there",
                      "read the stage's out.json", st)
    st.prov.append("drive/sealed", stage=p["stage"], hands_on=handed)
    st.close()
    _seal(sd, rd, {"stage": p["stage"], "plugin": p["plugin"], "hands_on": handed,
                   "report": str(sd / "report" / "report.json"), "numbers": len(rep.get("numbers") or []),
                   "request_sha256": req["sha256"], "inputs": inputs,
                   "decisions": {d["name"]: answers.get(d["name"]) for d in p["decisions"]}})
    return None, handed


# ---------------------------------------------------------------------------- the job (run 2)
def _site() -> tuple:
    """($SCH_SITE, its stack layer, its job.yml): the site's facts for a generated job."""
    site = os.environ.get("SCH_SITE")
    if not site or not (Path(site) / "stack.yml").is_file() or not (Path(site) / "job.yml").is_file():
        raise RequestError("--job: the job's queue, its size and where the harness is are the site's: "
                           "$SCH_SITE must name a directory holding stack.yml (executor: pbs, pbs: its "
                           "queues and defaults) and job.yml (" + ", ".join(JOB_SITE) + ")")
    layer, job = yamlish.load(Path(site) / "stack.yml"), yamlish.load(Path(site) / "job.yml")
    bad = sorted(set(job or {}) - set(JOB_SITE))
    if bad:
        raise RequestError(f"{site}/job.yml: {', '.join(bad)} is not a job field ({', '.join(JOB_SITE)})")
    absent = [k for k in JOB_REQUIRED if not (job or {}).get(k)]
    if absent:
        raise RequestError(f"{site}/job.yml declares no {', '.join(absent)}")
    if str(layer.get("executor")) != "pbs" or not isinstance(layer.get("pbs"), dict):
        raise RequestError(f"{site}/stack.yml: a job runs its stages on the scheduler; it declares "
                           f"`executor: pbs` and a `pbs:` block")
    return Path(site).resolve(), layer, job


def _commit(root: Path) -> str | None:
    import subprocess
    try:
        r = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True,
                           timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None


def job_text(req: dict, job_path, answers: list | None = None, by: str | None = None,
             predict=None, check=None, purpose: str | None = None, where: str | None = None) -> str:
    """THE JOB THAT RUNS ONE REQUEST ON THE CLUSTER, generated, never hand-written (ROUTE R03 run 2).

    Its body is one `sch run --request ... --out $RUNDIR` with the recorded answers; every stage is
    then the kernel's pbs executor's child job, sized by the request and queued by the site file.
    Its own `#PBS` block is the site's default, sized by the request's `resources.drive` and queued
    the same way. Every path in it is relative to the job's own directory (the cohort's folder is
    the same tree on the workstation and the cluster), or the site's. It seals its run directory,
    writes one VERDICT line for the chained run and one per check, and its last act is the GATE
    line. Nothing about a cohort or a site is in this function: the request, the site file, the
    prediction and the checks bring all of it."""
    import shlex
    from .services.executor import PBS_REQUIRED, PbsExecutor
    q = shlex.quote
    job_path = Path(job_path).resolve()
    jobs = job_path.parent
    if jobs.name != "jobs":
        raise RequestError(f"--job {job_path}: a job lives in its stage's jobs/ directory (the run key "
                           f"takes the stage's name from it)")
    stage = jobs.parent.name
    site, layer, job = _site()
    cfg = PbsExecutor(config={**dict(layer["pbs"]), "plugins": {DRIVE: req.get("drive_resources") or {}}}
                      ).settings(DRIVE)
    miss = [k for k in PBS_REQUIRED if not cfg.get(k)]
    if miss:
        raise RequestError(f"--job: the site's pbs block and resources.drive give no {', '.join(miss)}")

    def rel(p) -> str:
        return '"$PBS_O_WORKDIR"/' + q(os.path.relpath(Path(p).resolve(), jobs))
    root = Path(__file__).resolve().parent.parent
    commit = _commit(root)
    pre = [f"#   {ln}" if ln.strip() else "#" for ln in
           (Path(predict).read_text(encoding="utf-8").splitlines() if predict else
            ["NO PREDICTION WAS GIVEN (--predict): this job's GATE can only read MISSED."])]
    argv = ["sch", "run", "--request", "$REQUEST", "--out", "$RUNDIR"]
    tail = "".join(f" --answer {q(a)}" for a in (answers or [])) + (f" --by {q(by)}" if by else "")
    hn = str(job["harness"])
    hn_sh = ('"$HOME"/' + q(hn[2:])) if hn.startswith("~/") else q(hn)
    py = str(job["python"])
    py_sh = ('"$HOME"/' + q(py[2:])) if py.startswith("~/") else q(py)
    at = str(where or jobs)
    at = at if re.fullmatch(r"[~A-Za-z0-9_./-]+", at) else q(at)   # `~` left for the shell to read
    key = f"$(date -u +%Y%m%dT%H%M%SZ)__sch-${{HC:0:7}}__{stage}" + (f"__{purpose}" if purpose else "")
    name = re.sub(r"[^A-Za-z0-9_]", "_", f"sch_{stage}")[:15]
    reports = " ".join(f'"$RUNDIR"/{p["stage"]}/report/report.json' for p in req["stages"])
    out = [
        "#!/bin/bash", f"#PBS -N {name}", f"#PBS -q {cfg['queue']}", f"#PBS -l select={cfg['select']}",
        f"#PBS -l walltime={cfg['walltime']}", "#PBS -j oe",
        *([f"#PBS -P {cfg['account']}"] if cfg.get("account") else []), "#",
        "# GENERATED by `sch run --request ... --job` (the single-cell harness, ROUTE R03 run 2), never",
        "# hand-written: to change it, change the request, the site file or the prediction and generate it again.",
        f"#   request   {os.path.relpath(req['path'], jobs)}  sha256 {req['sha256']} (the job refuses another)",
        *([f"#   check     {os.path.relpath(Path(check).resolve(), jobs)}  sha256 {_sha(check)} (the job refuses "
           f"another)"] if check else []),
        f"#   site      {os.path.relpath(site, jobs)}  (stack.yml sha256 {_sha(site / 'stack.yml')[:16]}, "
        f"job.yml sha256 {_sha(site / 'job.yml')[:16]})",
        f"#   harness   {commit or 'not a git checkout: unpinned'}" + (f" (the job refuses another)" if commit else ""),
        f"#   stages    " + ", ".join(f"{p['stage']} {p['plugin']}" + (f" [{', '.join(f'{k}={v}' for k, v in sorted(p['resources'].items()))}]" if p.get("resources") else "") for p in req["stages"]),
        f"#   this job  {cfg.get('queue_chosen') or 'the site block queue'}",
        f"#   answers   {tail.strip() or 'none'}",
        "#", "# THE PREDICTION, WRITTEN BEFORE ANY RUN:", *pre, "#",
        "# The submit recipe (the login node; the CLEAN line must print before the qsub):",
        "# SUBMIT-BEGIN",
        f"#   cd {at}",
        *[f"#   {ln}" for ln in (job.get("submit") or [])],
        f"#   HN={hn_sh}; HC=$(cat $HN/HEAD.txt)",
        "#   [ -z \"$(git -C $HN status --porcelain)\" ] && [ \"$(git -C $HN rev-parse HEAD)\" = \"$HC\" ] && echo HARNESS-CLEAN",
        f"#   mkdir -p {q(str(job['runs']))}/{stage}; RUNS=$(cd {q(str(job['runs']))}/{stage} && pwd -P)",
        f"#   RUNDIR=$RUNS/{key}; mkdir \"$RUNDIR\" \"$RUNDIR/logs\"",
        f"#   qsub -o \"$RUNDIR/logs/\" -v RUNDIR=$RUNDIR,HARNESSHEAD=$HC {q(job_path.name)}",
        "# SUBMIT-END",
        "set -euo pipefail",
        "cd \"$PBS_O_WORKDIR\"",
        "RUNDIR=\"${RUNDIR:?RUNDIR must be passed with qsub -v}\"",
        f"HARNESS={hn_sh}",
        f"PY={py_sh}",
        f"REQUEST={rel(req['path'])}",
        f"export SCH_SITE={rel(site)}",
        f"EXPECT_HARNESS={q(commit or '')}",
        f"CHECK={rel(check) if check else q('')}",
        "VERDICTS=\"$RUNDIR/VERDICTS.txt\"",
        "finish() { s=$?",
        "  set +e",
        "  rm -rf \"$RUNDIR/cache\" 2>/dev/null",
        "  miss=''",
        f"  for w in \"$RUNDIR/DRIVE.json\" \"$RUNDIR/SEALED.json\" {reports}; do",
        "    [ -s \"$w\" ] || miss=\"$miss ${w#$RUNDIR/}\"",
        "  done",
        "  if [ -n \"$miss\" ] && [ \"$s\" -eq 0 ]; then s=97; fi",
        "  seal=SEALED.txt; [ \"$s\" -eq 0 ] || seal=FAILED.txt",
        "  n=$(grep -c '^VERDICT.*MISSED' \"$VERDICTS\" 2>/dev/null || true); n=${n:-0}",
        "  v=$(grep -c '^VERDICT' \"$VERDICTS\" 2>/dev/null || true); v=${v:-0}",
        "  if [ \"$s\" -eq 0 ] && [ \"$n\" -eq 0 ] && [ \"$v\" -gt 0 ]; then gate=\"GATE: AS PREDICTED\"",
        "  else gate=\"GATE: MISSED ($(( n > 0 ? n : 1 )))\"; fi",
        "  { echo \"exit=$s\"; echo \"jobid=${PBS_JOBID:-none}\"; echo \"harnesshead=${HARNESSHEAD:-unknown}\"",
        f"    echo \"request_sha256={req['sha256']}\"; echo \"stage={stage}\"; hostname; date -u +%Y-%m-%dT%H:%M:%SZ",
        "    if [ -n \"$miss\" ]; then echo \"missing=$miss\"; fi",
        "    cat \"$VERDICTS\" 2>/dev/null; echo \"$gate\"; } > \"$RUNDIR/$seal\"",
        "  find \"$RUNDIR\" -type f -not -path \"$RUNDIR/logs/*\" -exec chmod a-w {} +",
        "  echo \"$gate\"",
        "  exit \"$s\"",
        "}",
        "trap finish EXIT",
        "trap 'exit 143' TERM; trap 'exit 130' INT; trap 'exit 129' HUP   # killed is not clean",
        ": > \"$VERDICTS\"",
        "export OMP_NUM_THREADS=${NCPUS:-1} OPENBLAS_NUM_THREADS=${NCPUS:-1} MKL_NUM_THREADS=${NCPUS:-1}",
        "export NUMBA_NUM_THREADS=${NCPUS:-1} PYTHONNOUSERSITE=1 XDG_CACHE_HOME=\"$RUNDIR/cache\" MPLCONFIGDIR=\"$RUNDIR/cache/mpl\"",
        *[str(ln) for ln in (job.get("setup") or [])],
        "cp \"$HARNESS/HEAD.txt\" \"$RUNDIR/TOOL_HEAD.txt\"",
        "if [ -n \"$EXPECT_HARNESS\" ] && [ \"$(cat \"$HARNESS/HEAD.txt\")\" != \"$EXPECT_HARNESS\" ]; then",
        "  echo \"VERDICT (harness): MISSED - $HARNESS is at $(cat \"$HARNESS/HEAD.txt\"), this job was generated at $EXPECT_HARNESS\" | tee -a \"$VERDICTS\"",
        "  exit 2",
        "fi",
        # THE JOB RUNS THE FILES IT WAS GENERATED FOR (autodev W042 fix 1, C): the request, the check
        # script and the site's two files are compared with their hashes here, before anything runs; an
        # edited one would run under a prediction written for another
        "pin() { \"$PY\" -c 'import hashlib, sys; h = hashlib.sha256(); f = open(sys.argv[1], \"rb\"); "
        "[h.update(b) for b in iter(lambda: f.read(1 << 20), b\"\")]; print(h.hexdigest())' \"$1\"; }",
        "check_pin() { got=$(pin \"$2\" 2>/dev/null || echo unreadable)",
        "  if [ \"$got\" != \"$3\" ]; then",
        "    echo \"VERDICT (pins): MISSED - the $1 $2 has sha256 $got; this job and its prediction were generated for "
        "$3: generate the job again from the file as it is\" | tee -a \"$VERDICTS\"",
        "    exit 2",
        "  fi; }",
        f"check_pin request \"$REQUEST\" {req['sha256']}",
        *([f"check_pin check \"$CHECK\" {_sha(check)}"] if check else []),
        f"check_pin 'site stack.yml' \"$SCH_SITE/stack.yml\" {_sha(site / 'stack.yml')}",
        f"check_pin 'site job.yml' \"$SCH_SITE/job.yml\" {_sha(site / 'job.yml')}",
        "echo \"=== the chained run: $(date -u +%Y-%m-%dT%H:%M:%SZ) ===\"",
        "set +e",
        "PYTHONPATH=\"$HARNESS\" \"$PY\" -m " + " ".join(argv).replace("$REQUEST", "\"$REQUEST\"").replace("$RUNDIR", "\"$RUNDIR\"") + tail + " > \"$RUNDIR/DRIVE.log\" 2>&1",
        "rc=$?",
        "set -e",
        "tail -n 60 \"$RUNDIR/DRIVE.log\"",
        "status=$(grep -o '\"status\": \"[a-z]*\"' \"$RUNDIR/DRIVE.json\" 2>/dev/null | head -1 | cut -d'\"' -f4 || true)",
        f"if [ \"$rc\" -eq 0 ] && [ \"$status\" = sealed ]; then echo \"VERDICT (drive): SEALED - {len(req['stages'])} stages from one request\" | tee -a \"$VERDICTS\"",
        "else echo \"VERDICT (drive): MISSED - exit $rc, DRIVE.json status ${status:-none} (see DRIVE.log)\" | tee -a \"$VERDICTS\"; fi",
        "if [ -n \"$CHECK\" ]; then",
        "  echo \"=== the checks: $CHECK ===\"",
        "  set +e",
        "  RUNDIR=\"$RUNDIR\" PY=\"$PY\" HARNESS=\"$HARNESS\" bash \"$CHECK\" \"$RUNDIR\" > \"$RUNDIR/CHECKS.txt\" 2>&1",
        "  crc=$?",
        "  set -e",
        "  cat \"$RUNDIR/CHECKS.txt\"",
        "  grep '^VERDICT' \"$RUNDIR/CHECKS.txt\" >> \"$VERDICTS\" || true",
        "  [ \"$crc\" -eq 0 ] || echo \"VERDICT (checks): MISSED - the checks exited $crc\" | tee -a \"$VERDICTS\"",
        "fi",
        "if grep -q '^VERDICT.*MISSED' \"$VERDICTS\"; then exit 1; fi",
        "exit 0",
    ]
    return "\n".join(out) + "\n"


def write_job(req: dict, job_path, **kw) -> dict:
    text = job_text(req, job_path, **kw)
    p = Path(job_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:      # LF only: a CR breaks bash on the cluster
        fh.write(text)
    return {"job": str(p.resolve()), "md5": hashlib.md5(text.encode()).hexdigest(), "lines": text.count("\n")}
