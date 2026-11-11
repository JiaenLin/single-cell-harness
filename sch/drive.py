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
}
REQUIRED = ("request", "observations", "parts", "keys", "context", "upstream", "stages")
WAITING = 3          # the exit status of a run stopped at a user's decision
SHAPES = ("libraries", "joint")
#: What the plan says of the tool a stage wraps.
WRAPS = ("tool", "version")


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


def _hands_on(m, params: dict) -> list:
    """The shapes a stage hands the next one: its declaration, each shape's condition a param."""
    out = []
    for shape, when in dict(m.data.get("hands_on") or {}).items():
        if when is None or when in params:
            out.append(shape)
    return out


# ---------------------------------------------------------------------------- the request
def load(path) -> dict:
    """Read and check a request. Everything a refusal needs is decided here, before any tool."""
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
        if not p.is_file():
            raise RequestError(f"{k}: {p} is not a file")
        return str(p)
    keys = doc["keys"]
    if not isinstance(keys, dict) or not keys.get("sample"):
        raise RequestError("keys: declares no `sample`, the column naming each library")

    # ---- the context: one word per fact, each fact once (rule 2; W041 point 3)
    ctx = doc["context"]
    if not isinstance(ctx, dict):
        raise RequestError("context: is not a mapping of profile axes")
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
        decisions = []
        for d in m.data.get("decisions") or []:
            head, _, rest = str(d["param"]).partition(".")
            if (rest and rest in dict(params.get(head) or {})) or (not rest and head in params):
                raise RequestError(f"stages[{i}] ({m.name}): params set {d['param']}, which {m.name} declares "
                                   f"the user's decision {short}.{d['name']} ({d['what']}); the driver passes "
                                   f"it only as an answer recorded with who gave it: --answer "
                                   f"{short}.{d['name']}=VALUE --by WHO")
            decisions.append({"name": f"{short}.{d['name']}", "param": str(d["param"]), "what": d["what"]})
        plan.append({"stage": f"{i:02d}_{short}", "plugin": m.name, "dir": str(m.dir),
                     "profile": m.profile, "version": m.version,
                     "wraps": {k: (m.data.get("wraps") or {}).get(k) for k in WRAPS},
                     "assays": list(m.data.get("assays") or []), "reads": m.data.get("reads"),
                     "hands_on": _hands_on(m, params), "params": params, "decisions": decisions,
                     "cannot_show": list(m.data.get("cannot_show") or [])})

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
    for step, banned in dict((rule.get("never") or {}).get(assay) or {}).items():
        tool = str((up.get(step) or {}).get("tool") or "").strip().lower()
        if tool in [str(b).lower() for b in banned]:
            raise RequestError(f"upstream: {step} by {tool!r} on {assay}: never ({prof.id}: rule 2, a remover "
                               f"calibrated on nuclei is not lent to cells); deliver the aligner's call, or "
                               f"an ambient correction made for this assay")

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
            "context": {str(k): str(v) for k, v in ctx.items()}, "upstream": up, "stages": plan}


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
        for d in p["decisions"]:
            got = (f"answered {json.dumps(answers[d['name']]['value'])} by {answers[d['name']]['by']}"
                   if d["name"] in answers else "UNANSWERED - the run stops before this stage")
            lines.append(f"           the user's: {d['name']} ({d['param']}) - {d['what']}; {got}")
    return lines


# ---------------------------------------------------------------------------- the run
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
    from .kernel import Stack
    from .services.invariant import InvariantFailure
    from .stack import StackError
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    resume = f"sch run --request {req['path']} --out {out}"
    prior = out / "request.json"
    if prior.exists() and json.loads(prior.read_text())["sha256"] != req["sha256"]:
        raise RequestError(f"{out} was run from another request (sha256 "
                           f"{json.loads(prior.read_text())['sha256'][:12]}); a run is one request: "
                           f"start a new --out")
    prior.write_text(json.dumps(req, indent=1, default=str) + "\n")
    names = {d["name"]: (p, d) for p in req["stages"] for d in p["decisions"]}
    dfile = out / "decisions.json"
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
        waiting = [d for d in p["decisions"] if d["name"] not in answers]
        if waiting:
            rec = {"status": "waiting", "stage": p["stage"], "sealed": done,
                   "waiting_for": waiting, "resume": resume + " " + " ".join(
                       f"--answer {d['name']}=VALUE" for d in waiting) + " --by WHO"}
            _record(out, **rec)
            return WAITING, rec
        params = dict(p["params"])
        for d in p["decisions"]:
            params = _set(params, d["param"], answers[d["name"]]["value"])
        sd.mkdir(parents=True)
        if handed is None:
            obs, keys, parts = req["observations"], req["keys"], req["parts"]
        else:
            f, col = _manifest(sd, p["reads"], req["keys"]["sample"], handed)
            obs, keys, parts = str(f), {**req["keys"], "sample": col}, "h5ad"

        def failed(why, fix, stack=None):
            rec = {"status": "failed", "stage": p["stage"], "plugin": p["plugin"], "sealed": done,
                   "reason": why, "fix": fix, "stack": str(sd), "resume": resume}
            if stack is not None:
                stack.prov.append("drive/failed", stage=p["stage"], reason=why, fix=fix)
                stack.close()
            _record(out, **rec)
            return 2, rec
        try:
            st = Stack.init(sd, p["profile"], obs, req["design"], keys, context=req["context"], parts=parts)
        except StackError as e:
            return failed(f"sch init refused: {e}", "correct what the refusal names, then resume")
        st.close()
        decl = yamlish.load(sd / "stack.yml")
        decl["plugins"] = {p["plugin"]: {"plugin": p["dir"], "params": params}}
        yamlish.dump(decl, sd / "stack.yml")
        st = Stack.open(sd)
        st.prov.append("drive/stage", request=req["path"], request_sha256=req["sha256"], stage=p["stage"],
                       plugin=p["plugin"], reads_from=done[-1] if done else "the request's observations")
        st.prov.append("upstream/declared", **{k: v for k, v in req["upstream"].items()})
        for d in p["decisions"]:
            st.prov.append("decision/answered", name=d["name"], param=d["param"], what=d["what"],
                           **answers[d["name"]])
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
                       "request_sha256": req["sha256"]})
        done.append(p["stage"])
    rec = {"status": "sealed", "sealed": done, "request": req["path"], "request_sha256": req["sha256"],
           "decisions": answers, "upstream": req["upstream"],
           "reports": {s: str(out / s / "report" / "report.json") for s in done}}
    (out / "SEALED.json").write_text(json.dumps({"sealed_at": _now(), **rec}, indent=1, default=str) + "\n")
    _record(out, **rec)
    return 0, rec
