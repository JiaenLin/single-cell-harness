"""`sch` — the command line.

    sch init DIR --profile P --observations FILE [--design FILE] [--key k=v ...]
    sch stack [DIR] [--dump]            the mounted stack; --dump prints the composed declaration
    sch plan PLUGIN [--param k=v]       what would run and what is missing, before any compute
    sch mount PLUGIN [--param k=v] [--escape GATE --why ... --by ...] [--name N]
    sch unmount NAME [--dry-run]
    sch materialise [--full] [--out]
    sch ask PROBE [--param k=v]
    sch scratch SCRIPT.py [--label L]   arbitrary code against a read-only view; unquotable
    sch promote SCRATCH_ID --by PERSON --plugin DIR
    sch report [--include-scratch]
    sch fork NEWDIR [--without NAME ...]
    sch run                             mount everything stack.yml declares
    sch events [--kind K]
    sch plugin validate|test|new
    sch doctor --architecture | --runtime DIR
    sch conform REPO [--terms FILE] | --run RUNDIR [--against REFRUN]

    sch dev map [--json]                what can be added to this repository, and how
    sch dev new POINT NAME              a conformant skeleton, its SPEC and its test
    sch dev fixture DIR [--shape a|b]   the two-shape synthetic cohort to develop against
    sch dev check [--point P --name N]  the ladder: contract, unit, both shapes, leak, baseline
    sch dev baseline record|check RUNDIR --path FILE
    sch dev job --ref REFRUN --rundir DIR --tool DIR --queue Q --select S --predict TEXT
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from . import __version__, CONTRACT
from .dev.ladder import TIERS as _TIERS


def _kv(pairs) -> dict:
    out = {}
    for p in pairs or []:
        if "=" not in p:
            raise SystemExit(f"expected key=value, got {p!r}")
        k, v = p.split("=", 1)
        try:
            v = json.loads(v)
        except ValueError:
            pass
        out[k] = v
    return out


def _stack(a):
    from .kernel import Stack
    d = getattr(a, "stack", None) or "."
    return Stack.open(d)


def _emit(a, obj, text=None):
    if getattr(a, "json", False) or text is None:
        print(json.dumps(obj, indent=1, sort_keys=True, default=str))
    else:
        print(text)


# --------------------------------------------------------------------------- commands
def cmd_init(a):
    from .kernel import Stack
    st = Stack.init(a.dir, a.profile, a.observations, a.design, _kv(a.key),
                    plugin_paths=a.plugin_path or None)
    _emit(a, {"stack": str(st.dir), "profile": st.profile.id}, f"initialised {st.dir} ({st.profile.id})")
    st.close()
    return 0


def cmd_stack(a):
    st = _stack(a)
    if a.dump:
        _emit(a, st.decl)
        st.close()
        return 0
    view, _ = st.materialise()
    lines = [f"  observations   {st.dataset.observations.name}: {view.n_total} observations, {view.n} kept      immutable"]
    for r in st.registry.runtimes:
        tag = {"mounted": "mounted", "invalid": "INVALID", "rebuild": "REBUILD", "refused": "refused"}.get(r.state, r.state)
        kind = "checkpoint" if r.is_checkpoint else "stack"
        contribs = ", ".join(c.capability() for c in st.dataset.contributions_of(r.name)) or "-"
        lines.append(f"  ▸ {r.name:<22} {r.manifest.version:<8} sv{r.manifest.state_version!s:<3} {kind:<10} {tag:<8} {contribs}")
    _emit(a, st.declaration(), "\n".join(lines))
    st.close()
    return 0


def cmd_plan(a):
    st = _stack(a)
    p = st.plan(a.plugin, _kv(a.param), a.name)
    lines = [f"  {p['plugin']}  layer {p['layer']}  reversible {p['reversible']}  state_version {p['state_version']}",
             f"  admitted: {p['admitted']}" + (f"  — {p['reason']}" if p.get("reason") else "")]
    for n in p.get("needs", []):
        lines.append(f"    needs   {n}")
    for g in p.get("gates", []):
        lines.append(f"    gate    {g}")
    for m in p.get("missing", []):
        lines.append(f"    MISSING {m['need']}   fix: {m['fix']}")
    for c in p.get("cannot_show", []):
        lines.append(f"    cannot_show: {c}")
    _emit(a, p, "\n".join(lines))
    st.close()
    return 0 if p["admitted"] else 2


def cmd_mount(a):
    st = _stack(a)
    escapes = {}
    if a.escape:
        if not (a.why and a.by):
            raise SystemExit("--escape needs --why and --by: an escape is a recorded pair")
        for g in a.escape:
            escapes[g] = {"why": a.why, "by": a.by}
    r = st.mount(a.plugin, _kv(a.param), escapes, a.name)
    text = f"  {r.name}: {r.status}" + (f" — {r.reason}" if r.reason else "") + (f"\n  fix: {r.fix}" if r.fix else "")
    for g in r.gates:
        text += f"\n  gate {g['gate']}: {g['verdict']} ({g['reason']})" + ("  [escaped]" if g.get("escaped") else "")
    if r.headline:
        text += f"\n  {r.headline}"
    if r.undeclared:
        text += f"\n  undeclared outputs not merged: {r.undeclared}"
    _emit(a, r.to_dict(), text)
    st.close()
    return 0 if r.ok else 2


def cmd_unmount(a):
    st = _stack(a)
    r = st.unmount(a.name, dry_run=a.dry_run)
    lines = [f"  {r['name']}: {r['status']}" + (f" — {r.get('reason')}" if r.get("reason") else "")]
    if "would_restore" in r:
        lines.append(f"  would restore {r['would_restore']} observations")
        if r["would_invalidate"]:
            lines.append("  would invalidate, in order:")
            for x in r["would_invalidate"]:
                lines.append(f"    {x['name']:<24} {x['state']}")
        else:
            lines.append("  nothing above it depends on it")
    _emit(a, r, "\n".join(lines))
    st.close()
    return 0 if r["status"] != "refused" else 2


def cmd_materialise(a):
    st = _stack(a)
    view, d = st.materialise(filtered=not a.full)
    if a.out:
        import shutil
        shutil.copy(view.path, a.out)
    _emit(a, {"path": str(view.path), "kept": view.n, "total": view.n_total, "digest": view.digest(),
              "cache": {"hits": st.cache.hits, "misses": st.cache.misses}},
          f"  {view.path}\n  {view.n} of {view.n_total} kept, digest {view.digest()}")
    st.close()
    return 0


def cmd_ask(a):
    st = _stack(a)
    r = st.ask(a.probe, _kv(a.param), {"out_dir": a.subject} if a.subject else None)
    _emit(a, r)
    st.close()
    return 0 if not r["died"] else 2


def cmd_scratch(a):
    st = _stack(a)
    r = st.scratch(a.script, a.label, _kv(a.param))
    _emit(a, r, f"  scratch {r['id']}: {'died' if r['died'] else (r['out'] or {}).get('headline', 'ran')}\n"
                f"  {r['dir']}\n  nothing here is quotable (A2)")
    st.close()
    return 0 if not r["died"] else 2


def cmd_promote(a):
    st = _stack(a)
    r = st.promote(a.scratch_id, a.by, a.plugin)
    _emit(a, r, f"  {r['status']}: {r.get('reason', r.get('note', ''))}")
    st.close()
    return 0 if r["status"] == "promoted" else 2


def cmd_report(a):
    st = _stack(a)
    from .services.invariant import InvariantFailure
    try:
        r = st.report(include_scratch=a.include_scratch)
    except InvariantFailure as e:
        _emit(a, {"status": "refused", "reason": str(e)}, f"  report refused: {e}")
        st.close()
        return 2
    _emit(a, r, f"  {st.dir / 'report' / 'report.json'}: {len(r['numbers'])} number(s), every one an event")
    st.close()
    return 0


def cmd_fork(a):
    st = _stack(a)
    new = st.fork(a.newdir, a.without)
    _emit(a, {"stack": str(new.dir), "without": a.without},
          f"  forked to {new.dir} without {a.without or 'nothing'}; run `sch run` there")
    new.close()
    st.close()
    return 0


def cmd_run(a):
    st = _stack(a)
    results = st.run_declared()
    text = "\n".join(f"  {r.name}: {r.status}" + (f" — {r.reason}" if r.reason else "") for r in results) or "  nothing to mount"
    _emit(a, [r.to_dict() for r in results], text)
    st.close()
    return 0 if all(r.ok for r in results) else 2


def cmd_events(a):
    st = _stack(a)
    ev = st.prov.replay()
    if a.kind:
        ev = [e for e in ev if e["kind"] == a.kind or e["kind"].startswith(a.kind + "/")]
    _emit(a, ev, "\n".join(f"  {e['seq']:>4} {e['kind']:<22} " + json.dumps({k: v for k, v in e.items() if k not in ('seq', 'ts', 'kind')}, default=str)[:110] for e in ev))
    st.close()
    return 0


def cmd_plugin(a):
    if a.sub == "validate":
        from .plugin.validate import validate, format_problems
        rc = 0
        for d in a.dirs:
            probs = validate(d)
            print(f"{d}: " + format_problems(probs))
            if any(p["level"] == "error" for p in probs):
                rc = 2
        return rc
    if a.sub == "test":
        from .plugin.test import run_plugin_test
        rep = run_plugin_test(a.dir, keep=a.keep, params=_kv(a.param))
        text = "\n".join(f"  {'ok  ' if s.get('ok') else ('skip' if s.get('skipped') else 'FAIL')} {s['step']}" +
                         (f"  {s.get('detail')}" if isinstance(s.get('detail'), str) and not s.get('ok') else "")
                         for s in rep["steps"])
        _emit(a, rep, text + f"\n  {'passes' if rep.get('ok') else 'FAILS'}" + (f" (skipped: {rep['skipped']})" if rep.get("skipped") else ""))
        return 0 if rep.get("ok") else 2
    if a.sub == "new":
        from .plugin.scaffold import scaffold
        d = scaffold(a.name, a.dest, a.profile, a.wraps, a.language)
        print(f"  scaffolded {d}; every TODO must be answered before `sch plugin validate` passes")
        return 0
    return 1


def cmd_doctor(a):
    from .doctor import check_architecture, check_runtime, format_findings
    if a.runtime:
        f = check_runtime(a.runtime)
    else:
        f = check_architecture()
    _emit(a, f, format_findings(f))
    return 0 if all(x["ok"] for x in f) else 2


def cmd_conform(a):
    from .conform import conform_against, conform_repo, conform_run, format_checks
    if a.against:
        if not a.run or len(a.run) != 1:
            raise SystemExit("--against needs exactly one --run RUNDIR to compare")
        checks = conform_against(a.run[0], a.against)
        print(f"{a.run[0]}\n  against {a.against}:")
        print(format_checks(checks))
        if a.json:
            print(json.dumps(checks, indent=1, default=str))
        return 0 if all(c["ok"] or c["level"] == "warn" for c in checks) else 2
    if a.run:
        checks = []
        for r in a.run:
            cs = conform_run(r)
            print(f"{r}:")
            print(format_checks(cs))
            checks += cs
    else:
        checks = conform_repo(a.repo, a.terms, getattr(a, "shapes", None))
        print(f"{a.repo}:")
        print(format_checks(checks))
    if a.json:
        print(json.dumps(checks, indent=1, default=str))
    return 0 if all(c["ok"] or c["level"] == "warn" for c in checks) else 2


# WHAT AN AGENT BRANCHES ON. Three outcomes, and the third is the one that was missing:
#
#   0  what ran, passed
#   2  a check FAILED, or the caller's input was refused - something is wrong and it is named
#   3  nothing could be run: no declaration, a dependency absent, nothing to compare against.
#      NOTHING WAS PROVED EITHER WAY, which is a different fact from passing and used to be
#      reported as 0 by a check whose every tier had skipped.
OK, FAILED, CANNOT_RUN = 0, 2, 3


def _convert_specs(doc, point, root, only):
    """[(name, declaration)] for the artefacts at this point. Read, never imported.

    PARSED RATHER THAN IMPORTED, because a half-built plugin is exactly the kind that does not
    import - its `run()` raises and its dependencies are not installed yet, which is the state a
    conversion exists to get it out of. A converter that could only read plugins that already work
    would be useless on every plugin that needs it.
    """
    import ast
    from .dev import points as P
    pt = P.point(doc, point)
    d = Path(doc["_root"]) / str(pt.get("lives") or ".")
    out = []
    for f in sorted(d.glob("*.py")):
        if f.stem.startswith("_") or (only and f.stem != only):
            continue
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "PLUGIN":
                try:
                    out.append((f.stem, ast.literal_eval(node.value)))
                except ValueError:
                    pass
                break
    return out


def cmd_dev(a):
    from . import dev as D
    from .dev import ladder, points as P
    a.root = getattr(a, "root", None) or "."

    if a.sub == "map":
        if getattr(a, "init", False):
            try:
                f = P.init(a.root, force=a.force)
            except D.DevpointsError as e:
                print(e, file=sys.stderr)
                return FAILED
            print(f"  wrote {f}")
            print("  fill in the marked places, then `sch dev map` reads it back")
            return OK
        try:
            doc = P.load(a.root)
        except D.DevpointsError as e:
            print(e, file=sys.stderr)
            return CANNOT_RUN
        pts = doc.get("points") or {}
        if a.json:
            # EVERYTHING NEEDED TO FORM THE NEXT COMMAND, so an agent never has to read prose to
            # act. It used to return the points alone, which left the fixture command, the test
            # command and the meaning of `{role_sample}` to be looked up in docs/DEVELOPING.md -
            # three lookups between "what can I add here" and "what do I run".
            from .dev.ladder import TIERS, _jobs, _roles
            print(json.dumps({
                "tool": doc["tool"], "path": doc["_path"], "root": doc["_root"],
                "points": {k: dict(v, registered=P.existing(doc, k)) for k, v in pts.items()},
                "tests": doc.get("tests") or {},
                "fixture": doc.get("fixture") or {},
                "tiers": list(TIERS),
                "placeholders": {
                    "{python}": "the interpreter running the check",
                    "{root}": doc["_root"], "{out}": "the run directory for this shape",
                    "{observations}": "the fixture object for this shape",
                    "{design}": "the fixture design table for this shape",
                    "{name}": "the name passed to --name", "{shape}": "a or b",
                    "{jobs}": _jobs(),
                    **{"{" + k + "}": f"shape a: {va}, shape b: {vb}"
                       for (k, va), (_, vb) in zip(_roles("a").items(), _roles("b").items())},
                },
                "next": {
                    "start one": f"sch dev new POINT NAME --root {doc['_root']}",
                    "check one": f"sch dev check --root {doc['_root']} --point POINT --name NAME",
                    "reproduce": "sch dev job --ref REFRUN --rundir NEWRUN --tool TOOLDIR "
                                 "--queue Q --select S --predict TEXT --out FILE",
                },
            }, indent=1, default=str))
            return 0
        print(f"{doc['tool']}  ({doc['_path']})")
        for k, v in pts.items():
            reg = P.existing(doc, k)
            print(f"\n  {k}: {v['what']}")
            print(f"    lives      {v['lives']}")
            if v.get("example"):
                print(f"    example    {v['example']}")
            if reg:
                print(f"    registered {len(reg)}: {', '.join(map(str, reg[:10]))}")
            for r in v.get("register") or []:
                what = r.get("table") or f"a line matching {r['pattern']}"
                fix = f"   — `{r['fix']}` writes it" if r.get("fix") else ""
                print(f"    register   {what} in {r['file']}{fix}")
            keys = [k for k in (v.get("must_declare") or []) if P._KEYISH.match(str(k))]
            prose = [k for k in (v.get("must_declare") or []) if not P._KEYISH.match(str(k))]
            if keys:
                print(f"    declare    {', '.join(keys)}   (checked by parsing)")
            for q in prose:
                print(f"    also       {q}   (for a person to check)")
            if v.get("scaffold_command"):
                print(f"    scaffold   {v['scaffold_command']}")
            print(f"    proves     {v['proves']}")
            print(f"    CANNOT     {v['cannot_prove']}")
        print(f"\n  sch dev new POINT NAME     starts one")
        return 0

    if a.sub == "new":
        try:
            info = D.new(a.root, a.point, a.name, force=a.force)
        except D.DevpointsError as e:
            print(e, file=sys.stderr)
            return CANNOT_RUN                       # the point is not declared: setup, not defect
        except ValueError as e:
            print(e, file=sys.stderr)
            return FAILED
        if a.json:
            print(json.dumps(info, indent=1))
            return 0
        if info.get("scaffold_command"):
            print(f"  THIS TOOL SCAFFOLDS ITS OWN. Run:  {info['scaffold_command']}")
            print(f"  (nothing was written in its place; below is what this suite adds to it)")
        for f in info["written"]:
            print(f"  wrote   {f}")
        for f in info["skipped"]:
            print(f"  kept    {f}  (exists; --force to overwrite)")
        print(f"\n  it must declare: {', '.join(info['must_declare']) or 'nothing beyond the point'}")
        print(f"  a green ladder proves: {info['proves']}")
        print(f"  and does NOT prove:    {info['cannot_prove']}")
        print("\n  next:")
        for n in info["next"]:
            print(f"    - {n}")
        return 0

    if a.sub == "fixture":
        from .dev import fixture as F
        try:
            recs = ([F.write(a.dir, shape=a.shape, seed=a.seed, n_cells=a.cells,
                             splice=a.splice, crossed=a.crossed, force=a.force)] if a.shape
                    else F.write_both(a.dir, seed=a.seed, n_cells=a.cells,
                                      splice=a.splice, crossed=a.crossed, force=a.force))
        except ImportError as e:
            print(f"the fixture needs anndata, numpy and pandas: {e}", file=sys.stderr)
            return CANNOT_RUN
        if a.json:
            print(json.dumps(recs, indent=1))
            return 0
        for r in recs:
            print(f"  shape {r['shape']}  {r['cells']} cells x {r['genes']} genes  "
                  f"digest {r['digest']}"
                  + ("   REUSED - already on disk from these arguments; --force rebuilds"
                     if r.get("reused") else ""))
            print(f"    {r['observations']}")
            print(f"    {r['design']}")
            print("    roles: " + ", ".join(f"{k}={v}" for k, v in r["roles"].items()))
            print("    factors: " + " x ".join(r["factors"])
                  + ("  - crossed, so an interaction exists to get wrong"
                     if r["crossed"] else "  - one factor, so no interaction is expressible here"))
        print(f"\n  {len(recs[0]['hazards'])} structural hazards are built in; "
              f"see FIXTURE_<shape>.json")
        print("  SYNTHETIC. No number here is quotable and no result on it is evidence about biology.")
        return 0

    if a.sub == "check":
        try:
            rep = ladder.run(a.root, point_name=a.point, name=a.name,
                             only=set(a.only or []) or None, skip=set(a.skip or []),
                             keep_going=a.keep_going, record_baseline=a.record_baseline,
                             terms=a.terms, fixdir=a.fixture_dir, seed=a.seed)
        except D.DevpointsError as e:
            print(e, file=sys.stderr)
            return CANNOT_RUN
        print(ladder.format_run(rep))
        if a.json:
            print(json.dumps(rep, indent=1, default=str))
        if rep["failed"]:
            return FAILED
        if not rep["complete"]:
            missing = ", ".join(rep["not_run"])
            print(f"\nINCOMPLETE. {len(rep['ran'])} of {len(rep['asked'])} tiers ran; "
                  f"{missing} could not. Nothing that did run failed, but a check that skipped "
                  f"{'every' if not rep['ran'] else 'part of'} its ladder has not established "
                  f"what a full one would - so this exits 3, not 0.", file=sys.stderr)
            return CANNOT_RUN
        return OK

    if a.sub == "jobcheck":
        from .dev import jobcheck as JC
        paths = list(a.paths) or sorted((Path(a.root) / "jobs").glob("*.pbs"))
        if not paths:
            print(f"sch dev jobcheck: no job scripts given and none under {a.root}/jobs",
                  file=sys.stderr)
            return CANNOT_RUN
        print(f"job scripts read: {len(paths)}")
        bad = JC.report(paths)
        print(f"  {bad} of {len(paths)} with at least one problem")
        return FAILED if bad else OK

    if a.sub == "convert":
        from .dev import convert as CV
        try:
            doc = P.load(a.root)
        except D.DevpointsError as e:
            print(f"sch dev convert: {e}", file=sys.stderr)
            return CANNOT_RUN
        # `P.points` DOES NOT EXIST. `points.py` exports `point` (singular), so every
        # `sch dev convert` without --point died on AttributeError - the default path, which is
        # the one somebody types first. Found by a cold agent, not by me and not by the suite:
        # every test and every example I wrote passed --point, so the default was never executed.
        point = a.point or next(iter(doc.get("points") or {}), None)
        if not point:
            print(f"sch dev convert: {a.root} declares no extension points. "
                  f"`sch dev map --root {a.root} --init` writes a first DEVPOINTS.yaml.",
                  file=sys.stderr)
            return CANNOT_RUN
        try:
            _ph, up_path, _stages = CV.plan(doc, point)
        except CV.ConvertError as e:
            print(f"sch dev convert: {e}", file=sys.stderr)
            return CANNOT_RUN
        # THE SPECS ARE FOR THE ACTIONS THAT READ A DECLARATION, and `measure` is not one of
        # them: it runs the child's own command against a completed run and never opens a plugin.
        # Requiring them first made it refuse with "no widget named None" - an error about the
        # wrong thing entirely, on a repository where nothing was wrong.
        #
        # NAMED BY EXCLUSION, because the inclusive list was a second place to register an action
        # and `legends` was added to the parser and not to it. Nothing failed: `specs` stayed
        # empty, the loop ran zero times, and the command printed nothing and exited 0. A missing
        # registration must not be able to look like a plugin with no figures.
        # ONE PLUGIN AT A TIME, AND THE SUITE ENFORCES IT RATHER THAN TRUSTING IT.
        #
        # THE ACTIONS THAT FILL A DECLARATION ARE HELD-OUT ACTIONS. `account`, `inventory`,
        # `defaults`, `references`, `contract`, `legends` and `build` all put the wrapped tool's
        # own surface in front of whoever is converting. Run across a whole family at once they
        # show every answer before any of them has been decided - and any change made to THIS
        # TOOL afterwards is fitted to all of them at once, with nothing left over to test
        # whether it generalises. The next unseen tool is then the first real test, and there is
        # no evidence left to predict how it will go.
        #
        # Measured here: nine plugins were inventoried in one submission, which made every
        # extractor fix after it a fix against a corpus already read. The loop that does not do
        # that is: convert ONE, finish it, have a person check it, change the maker from what
        # that one taught, then the next - where the next is a genuine test.
        #
        # THE THRESHOLD IS MORE THAN ONE, not "no name given". A point holding a single artefact
        # has no held-out set to spend, so refusing there is friction that buys nothing - and
        # the first version of this rule refused it anyway and took seven of this suite's own
        # tests with it.
        #
        # `status` is exempt: it reads the declarations and shows nobody an upstream. `build` is
        # NOT - it walks the build phase and runs every mechanical stage in it, which would have
        # left the widest door open behind a closed one.
        #
        # `borrowed` is exempt on the same ground and for the same reason it is useless on one
        # plugin: what a shared environment lends is a fact about a FAMILY, and a report on one
        # member cannot say whether the loan is this plugin's alone or everybody's.
        #
        # `freshness` is exempt for the same reason `status` is: it reads the declarations and
        # this repository's own git history, and shows nobody an upstream surface. It is also
        # the one action that is USELESS on a single plugin - the question "has anybody here
        # kept this field up to date" is answered by the family or not at all.
        FILLS = ("inventory", "account", "defaults", "references", "contract", "legends",
                 "build")
        specs = []
        if a.action not in ("measure",):
            specs = _convert_specs(doc, point, a.root, a.name)
            if not specs:
                print(f"sch dev convert: no {point} named {a.name!r} under {a.root}",
                      file=sys.stderr)
                return CANNOT_RUN
            if a.action in FILLS and not a.name and len(specs) > 1:
                names = ", ".join(nm for nm, _ in specs)
                print(f"sch dev convert {a.action}: name ONE with --name. This point holds "
                      f"{len(specs)}: {names}\n"
                      f"\n"
                      f"  This action shows you the wrapped tool's own surface. Run over the "
                      f"whole family at once it puts every\n"
                      f"  answer in front of you before any has been decided, and every change "
                      f"made to this tool afterwards is\n"
                      f"  fitted to all of them - with nothing held back to show it generalises. "
                      f"The next unseen tool is then\n"
                      f"  the first real test, and there is no evidence left to predict it.\n"
                      f"\n"
                      f"  Convert one, finish it, have it checked, improve the maker from what "
                      f"it taught, then start the next.\n"
                      f"  The next one is the test.\n"
                      f"\n"
                      f"  `sch dev convert status --root {a.root}` reads every declaration and "
                      f"shows you no upstream, so it is\n"
                      f"  answers \"where is everything\".", file=sys.stderr)
                return CANNOT_RUN
        if a.action == "status":
            out = []
            for nm, spec in specs:
                # THE PLUGIN'S NAME REACHES `status`, and it has to. A stage that rules on where
                # the plugin DRAWS is measured from that plugin's source, and a status that did
                # not pass the name would report "could not look" for every one of them - which
                # is honest, and useless, on the one command a person types first.
                out.append(CV.format_status(CV.status(spec, doc, point, nm), nm, point,
                                            doc=doc, root=a.root, python=a.python or ""))
            print("\n\n".join(out))
            return OK
        if a.action == "freshness":
            # A DECLARED VERSION IS A CLAIM ABOUT CODE AND NOTHING CHECKED IT. Where the field is
            # a reuse key, a plugin that changes what it draws and leaves the field alone makes
            # every later run adopt the old products and report success. This reports; it writes
            # nothing and bumps nothing.
            from .dev import freshness as FR
            _field, _means = FR.declared_field(doc, point)
            rows = FR.check_all(doc, point, specs)
            print(FR.format_report(rows, point, _means, a.root))
            if any(r.verdict == FR.STALE for r in rows):
                return FAILED
            # EVERY ROW A "CANNOT SAY" IS NOT A PASS. The ladder already exits 3 rather than 0
            # when nothing it asked for could run, and a check that established nothing about
            # any plugin has to say so in the status as well as in the text - otherwise a job
            # that greps the exit code reads "no repository, no history" as "all fresh".
            if rows and all(r.verdict == FR.CANNOT_SAY for r in rows):
                return CANNOT_RUN
            return OK
        if a.action == "borrowed":
            # WHAT A SHARED ENVIRONMENT LENDS, AND WHAT GOES AWAY WHEN A PLUGIN IS ALONE. Measured
            # from declarations only: the repository's own resolver is asked twice, once over the
            # whole family and once per plugin, and the difference is the loan. Nothing is run and
            # no environment is built - which is the point, because the failure this prevents only
            # shows up in a run that has already been paid for.
            #
            # IT EXITS 0 ON A LOAN. A lent package is exposure and not a defect, and a check that
            # went red on one would be a false-alarm generator on a seven-member environment that
            # lends its members a hundred names each. The exit code speaks only for whether
            # anything could be established at all.
            from .dev.extract import shared_env as SE
            rows = SE.survey(doc, point, a.root, python=a.python or "python3",
                             only=(a.name or ""))
            print(SE.format_report(rows, point, a.root))
            if rows and all(not r.complete for r in rows):
                return CANNOT_RUN
            return OK
        if a.action == "legends":
            # TWO HALVES, AND A PLUGIN IS NOT FINISHED WHILE EITHER IS OWED. The declared half
            # rules on every figure the plugin DECLARES - who drew it. The measured half reads the
            # plugin's own source and asks where it PRODUCES a panel without describing one, which
            # nothing in a declaration can answer because a draw site is not declared anywhere.
            #
            # NEITHER HALF IS REQUIRED. A point may declare one, the other, or both; a stage that
            # declares neither is the error, and it is reported as one rather than printing an
            # empty worksheet that reads as no work left.
            bad = 0
            for nm, spec in specs:
                print(f"\n{nm}")
                said, last = 0, "this stage declares neither half"
                for fn in (lambda: CV.items_worksheet(spec, doc, point, "legends"),
                           lambda: CV.draw_worksheet(doc, point, "legends", nm)):
                    try:
                        print(fn())
                        print("")
                        said += 1
                    except CV.ConvertError as e:
                        last = e
                if not said:
                    bad += 1
                    print(f"{nm}: {last}", file=sys.stderr)
            return FAILED if bad else OK
        # GUARDED, because it was not. This block had no `if` on it and returned at the end, so
        # the `account` branch below was unreachable and `convert account` silently printed an
        # inventory. Dead code behind an unconditional return, which is the same shape as a test
        # defined below the runner that collects it - and neither says anything when it happens.
        if a.action == "inventory":
            bad = 0
            for nm, spec in specs:
                tool = a.tool or CV._dotted(spec, up_path)
                if not tool:
                    print(f"{nm}: declares no `{up_path}`, so there is no upstream to inventory. A "
                          f"plugin that wraps nothing owes no accounting.")
                    continue
                print(f"\n{nm}  wraps {tool}")
                looked = False
                for ext, inv in CV.inventory(tool, python=a.python, rscript=a.rscript):
                    if inv.complete:
                        looked = True
                        print(f"  {ext}: {len(inv)} function(s) - {inv.how}")
                        for fn in inv.names:
                            print(f"      {fn}")
                    else:
                        print(f"  {ext}: could not look - {inv.why_not}")
                if not looked:
                    bad += 1
                    print(f"  NO EXTRACTOR COULD LOOK AT {tool}. That is not an empty inventory and "
                          f"must not be recorded as one.")
            return FAILED if bad else OK

    if a.action == "account":
        # THE INVENTORY TURNED INTO A DECISION. Printed to paste, which is this tool's existing
        # idiom for a measurement a machine took and a maintainer owns.
        bad = 0
        for nm, spec in specs:
            tool = a.tool or CV._dotted(spec, up_path)
            if not tool:
                continue
            best = None
            for _ext, inv in CV.inventory(tool, python=a.python, rscript=a.rscript):
                if inv.complete and (best is None or len(inv) > len(best)):
                    best = inv
            if best is None:
                bad += 1
                print(f"\n{nm}: no extractor could look at {tool}, so there is nothing to rule "
                      f"on yet. Build this plugin's environment first.")
                continue
            print(f"\n# ---- {nm}: paste into kernels/{nm}.py, then rule on each entry")
            print(f"#      {best.how}")
            # THE PLUGIN'S OWN SOURCE IS HALF THE ANSWER, so it is read and passed in.
            src = ""
            for f in sorted((Path(a.root) / str(P.point(doc, point).get("lives") or ".")).glob("*.py")):
                if f.stem == nm:
                    src = f.read_text(encoding="utf-8")
                    break
            ctx = CV.ruling_context(spec, doc, point)
            if ctx:
                print(ctx)
            print(CV.worksheet(tool, best, spec.get("native_plots"), src, _ph))
        return FAILED if bad else OK

    if a.action == "build":
        # THE WHOLE BUILD, IN ORDER, STOPPING WHERE ONLY A PERSON CAN GO ON. `status` named the
        # next stage and not the command; naming the command still left an agent to run six of
        # them by hand and know which need the plugin's own interpreter. This walks the BUILD
        # phase - never the test phase, which needs data and is a different question - runs each
        # mechanical stage, and stops at the first thing requiring a decision.
        #
        # IT RUNS NOTHING THAT WRITES. Every stage here reads source and prints; the worksheets
        # are pasted by whoever read them. A driver that edited declarations would be deciding
        # the things this pipeline exists to put in front of somebody.
        rows = None
        for nm, spec in specs:
            rows = CV.status(spec, doc, point, nm)
            build = [r for r in rows if r.get("phase", "build") == "build"]
            done = sum(1 for r in build if r["done"])
            print(f"\n=== {nm}: build is {done} of {len(build)}")
            for r in build:
                if r["done"]:
                    print(f"  done {r['stage']}")
                    continue
                cmd = CV.advance_command(r, doc, point, a.root, nm, a.python or "", "")
                if not cmd or r["kind"] == "judgement":
                    print(f"\n  STOP at {r['stage']}: nothing runs this. It is what only you can "
                          f"answer: {', '.join(r['missing'])}")
                    if r["why"]:
                        print(f"       {r['why'].strip()}")
                    break
                if r.get("partial") or r.get("draws", {}).get("looked") is not None:
                    # A DEBT MEASURED FROM SOURCE STOPS THE BUILD TOO. `partial` is what the
                    # plugin admits about itself; the draw-site half is what its source says
                    # whether it admits it or not, and a driver that walked past it would run
                    # every later stage and report a build that has 35 undescribed panels in it.
                    said = r.get("partial") or CV.draw_summary(r.get("draws") or {})
                    if said:
                        print(f"\n  STOP at {r['stage']}: started, and the source says what is "
                              f"left.")
                        print(f"       {said[:200]}")
                        print(f"       to see the rest:  {cmd}")
                        break
                print(f"\n  --- {r['stage']}")
                argv = cmd.split()
                if argv[:1] == ["sch"]:
                    argv = [sys.executable, "-m", "sch"] + argv[1:]
                if "<the interpreter this plugin runs in>" in cmd:
                    print(f"  STOP at {r['stage']}: needs the interpreter this plugin runs in. "
                          f"Pass --python; `scprofile install {nm} --prefix DIR` builds it.")
                    break
                # NOT `cwd=a.root`. The sub-command already knows the repository from --root,
                # and running it from there put the harness off `sys.path`, so every stage died on
                # "No module named sch" - and the driver dutifully reported the stage as failing.
                env = dict(os.environ)
                here = str(Path(__file__).resolve().parents[1])
                env["PYTHONPATH"] = os.pathsep.join(
                    [here] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
                # FLUSHED FIRST. The parent's prints are buffered and the child's are not, so
                # the stage's output arrived ABOVE the header saying which stage it was - which
                # for a driver whose whole job is to say where you are is the one thing it must
                # not do.
                sys.stdout.flush()
                rc = subprocess.run(argv, env=env).returncode
                sys.stdout.flush()
                if rc != 0:
                    print(f"  {r['stage']} exited {rc}; stopping here.")
                    return rc
        return OK

    if a.action in ("defaults", "references", "contract"):
        # SCANS READ THE PLUGIN; the defaults stage also asks the upstream what its parameters are.
        lives = str(P.point(doc, point).get("lives") or ".")
        for nm, spec in specs:
            src = ""
            f = Path(a.root) / lives / f"{nm}.py"
            if f.is_file():
                src = f.read_text(encoding="utf-8")
            if not src:
                print(f"{nm}: not a single file under {lives}/, so it cannot be read here")
                continue
            tool = a.tool or CV._dotted(spec, up_path) or ""
            if a.action == "contract":
                got = CV.contract_in(src)
                _dec = [f.get("id") for f in ((spec.get("report") or {}).get("figures") or [])]
                print(f"\n# ---- {nm}: what the code emits, held against what it declares")
                for field, found, declared in (("produces", got["produces"],
                                                list(spec.get("produces") or [])),
                                               ("report.figures", got["report.figures"], _dec)):
                    fs, ds = set(found), set(declared)
                    # A NAME IS OFTEN DECLARED WITH A SUFFIX THE EMIT DOES NOT CARRY.
                    same = {f for f in fs if any(f in d or d in f for d in ds)}
                    print(f"    # {field}: {len(found)} emitted, {len(declared)} declared, "
                          f"{len(same)} matched")
                    extra = sorted(fs - same)
                    if extra:
                        print(f"    #   EMITTED AND NOT DECLARED: {extra}")
                    unseen = sorted(d for d in ds if not any(d in f or f in d for f in fs))
                    if unseen:
                        print(f"    #   declared and not seen by this scan: {unseen}")
                if got["dynamic"]:
                    print(f"    # THIS SCAN IS BLIND TO {len(got['dynamic'])} EMISSION(S) whose "
                          f"name is computed:")
                    for fn_, ln_, expr in got["dynamic"]:
                        print(f"    #   line {ln_}: {fn_}({expr})")
                    print("    #   So 'declared and not seen' above is NOT evidence the "
                          "declaration is wrong. Read those lines before changing anything.")
                print(f"    # reads from ctx: {', '.join(got['reads']) or 'nothing'}")
                continue
            if a.action == "references":
                found = CV.references_in(src, tool)
                print(f"\n# ---- {nm}: consulted, and not from the user's object")
                # SAY WHAT IS ALREADY THERE, EVEN WHEN NOTHING WAS FOUND. This printed the
                # same "nothing found, declare {}" line before and after somebody declared `{}`,
                # because the already-declared line was only reached when the extractor had
                # candidates - so a maintainer who had just done the work was told to do it again
                # and reasonably concluded their edit had not taken.
                have = spec.get("references")
                if not found:
                    if isinstance(have, dict) and not have:
                        print('    # nothing found, and `"references": {}` is declared - so this '
                              "says somebody looked. Nothing to do.")
                    elif have:
                        print(f"    # nothing found, and {len(have)} already declared: "
                              f"{sorted(have)}. This scan reads Python; a reference fetched from R "
                              f"or a subprocess is invisible to it, so those are not contradicted.")
                    else:
                        print(f"    # nothing found, and nothing declared. If that is right, "
                              f'declare it: "references": {{}} says you looked; absent says '
                              f"nobody did.")
                    continue
                for r in found:
                    print(f"    # {r['kind']:9s} line {r['line']}: {r['what']}")
                    print(f"    #   {r['why']}")
                print(f"    # already declared: {sorted(spec.get('references') or {})}")
                continue
            # defaults
            if not tool:
                print(f"{nm}: declares no `{up_path}`, so there is no upstream to read")
                continue
            calls = CV.upstream_calls(src, tool)
            if not calls:
                print(f"\n# ---- {nm}: no call into {tool} found, so nothing is being inherited "
                      f"from it. If this wrapper drives the tool some other way - a subprocess, "
                      f"an R string - this scan cannot see it and has not said there is nothing.")
                continue
            from .dev.extract import python_package as _PP
            params = _PP.parameters(sorted(calls), python=a.python or "python3")
            print(f"\n# ---- {nm}: paste into kernels/{nm}.py, then rule on each")
            print(CV.defaults_worksheet(tool, calls, params, spec.get("config"), _ph,
                                        pins=(spec.get("requires") or {}).get("packages")))
        return OK

    # ANY STAGE THAT DECLARES A COMMAND IS RUN BY ITS OWN NAME. This branch used to be
    # `if a.action == "measure"`, and the comment under it said the harness "does not know what a
    # run directory of this tool looks like and must not learn" - which was true of the COMMAND
    # and false of the NAME sitting in the `if`. The second command stage this repository declared
    # was unreachable: `promised` was in DEVPOINTS, printed by `status`, and no way to run it.
    #
    # A stage is a command stage because it DECLARES a command, which is a fact this module can
    # read. (`--action` still enumerates the stage names it will accept, which is the same leak one
    # level up and is not fixed here; it is written down in tests/test_convert.py.)
    # EVERY ACTION THAT REACHES HERE IS A COMMAND-STAGE ATTEMPT. Each build action above returns,
    # so what is left is a stage this repository declares a `command:` for - and the guard here
    # must NOT be "is it a declared stage", because a point that declares no such stage at all
    # would then fall past this branch and out of the dispatcher with "unknown dev subcommand".
    cmd = CV.stage_command(doc, point, a.action)
    if not cmd:
        # A STAGE THAT IS NOT A COMMAND STAGE SAYS SO. Reached when this repository declares
        # the stage but no `command:` for it - which is the ordinary case for every build
        # stage, and an error only for an action the caller asked to RUN.
        print(f"sch dev convert: point {point!r} declares no command for the {a.action} "
              f"stage, so there is nothing to run. Add `command:` to that stage in "
              f"DEVPOINTS.yaml.", file=sys.stderr)
        return CANNOT_RUN
    if not a.run:
        print(f"sch dev convert {a.action}: pass --run RUNDIR, a completed run of this "
              f"plugin. This stage is in the TEST phase - it reads back from something that "
              f"actually ran, and nothing here can invent it.", file=sys.stderr)
        return CANNOT_RUN
    argv = CV.fill(cmd, {"python": sys.executable, "run": str(a.run), "root": str(a.root)})
    print("  " + " ".join(argv))
    return subprocess.run(argv, cwd=a.root).returncode



    if a.sub == "baseline":
        from .dev import baseline as B
        if a.action == "record":
            fp = B.record(a.rundir, a.path)
            print(f"  recorded {len(fp['products'])} products to {a.path}")
            print(f"  covers {len(fp['covers'])} readable, {len(fp['does_not_cover'])} opaque (bytes only)")
            return 0
        try:
            diffs, ref = B.check(a.rundir, a.path)
        except FileNotFoundError as e:
            print(e, file=sys.stderr)
            return CANNOT_RUN                       # no baseline is not a failing baseline
        for d in diffs[:40]:
            print(f"  {d['product']}: {d['what']}  {d['detail']}")
        print(f"  {len(diffs)} difference(s) against {a.path} at rtol {ref.get('rtol')}")
        if diffs:
            print("  a deliberate change bumps state_version and re-records; anything else is a defect")
        return OK if not diffs else FAILED

    if a.sub == "job":
        from .dev import job as J
        try:
            info = J.write(a.out, ref_dir=a.ref, rundir=a.rundir, tooldir=a.tool,
                           prediction=a.predict, queue=a.queue, select=a.select,
                           walltime=a.walltime, name=a.name or "reproduce")
        except (ValueError, OSError) as e:
            print(e, file=sys.stderr)
            return FAILED
        if a.json:
            print(json.dumps(info, indent=1))
            return 0
        print(f"  wrote {info['path']}")
        print(f"  command taken from  {info['argv_source']}  ({info['reference']})")
        print(f"  reference commit    {info['ref_commit']}")
        print(f"  tool frozen at      {info['tool_commit']}")
        print(f"  products expected   {info['products']}")
        print(f"\n  {info['submit']}")
        return 0
    raise SystemExit(f"unknown dev subcommand {a.sub!r}")


# --------------------------------------------------------------------------- parser
def build_parser():
    ap = argparse.ArgumentParser(prog="sch", description=f"single-cell-harness {__version__}, contract {CONTRACT}")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def stackable(p):
        p.add_argument("--stack", default=".", help="stack directory (default .)")

    p = sub.add_parser("init"); p.add_argument("dir"); p.add_argument("--profile", required=True)
    p.add_argument("--observations", required=True); p.add_argument("--design")
    p.add_argument("--key", action="append", metavar="KEY=COLUMN"); p.add_argument("--plugin-path", action="append")
    p.set_defaults(fn=cmd_init)
    p = sub.add_parser("stack"); stackable(p); p.add_argument("--dump", action="store_true"); p.set_defaults(fn=cmd_stack)
    p = sub.add_parser("plan"); stackable(p); p.add_argument("plugin"); p.add_argument("--param", action="append")
    p.add_argument("--name"); p.set_defaults(fn=cmd_plan)
    p = sub.add_parser("mount"); stackable(p); p.add_argument("plugin"); p.add_argument("--param", action="append")
    p.add_argument("--name"); p.add_argument("--escape", action="append", metavar="GATE")
    p.add_argument("--why"); p.add_argument("--by"); p.set_defaults(fn=cmd_mount)
    p = sub.add_parser("unmount"); stackable(p); p.add_argument("name"); p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_unmount)
    p = sub.add_parser("materialise"); stackable(p); p.add_argument("--full", action="store_true"); p.add_argument("--out")
    p.set_defaults(fn=cmd_materialise)
    p = sub.add_parser("ask"); stackable(p); p.add_argument("probe"); p.add_argument("--param", action="append")
    p.add_argument("--subject")
    p.add_argument("--upto", default=None,
                   help="materialise the view BELOW this mounted plugin - the view a gate saw "
                        "when it mounted, so a refusal's number can be reproduced")
    p.set_defaults(fn=cmd_ask)
    p = sub.add_parser("scratch"); stackable(p); p.add_argument("script"); p.add_argument("--label")
    p.add_argument("--param", action="append"); p.set_defaults(fn=cmd_scratch)
    p = sub.add_parser("promote"); stackable(p); p.add_argument("scratch_id"); p.add_argument("--by")
    p.add_argument("--plugin"); p.set_defaults(fn=cmd_promote)
    p = sub.add_parser("report"); stackable(p); p.add_argument("--include-scratch", action="store_true"); p.set_defaults(fn=cmd_report)
    p = sub.add_parser("fork"); stackable(p); p.add_argument("newdir"); p.add_argument("--without", action="append")
    p.set_defaults(fn=cmd_fork)
    p = sub.add_parser("run"); stackable(p); p.set_defaults(fn=cmd_run)
    p = sub.add_parser("events"); stackable(p); p.add_argument("--kind"); p.set_defaults(fn=cmd_events)
    p = sub.add_parser("plugin"); ps = p.add_subparsers(dest="sub", required=True)
    q = ps.add_parser("validate"); q.add_argument("dirs", nargs="+")
    q = ps.add_parser("test"); q.add_argument("dir"); q.add_argument("--keep", action="store_true"); q.add_argument("--param", action="append")
    q = ps.add_parser("new"); q.add_argument("name"); q.add_argument("--dest", default="."); q.add_argument("--profile", required=True)
    q.add_argument("--wraps"); q.add_argument("--language", default="python")
    p.set_defaults(fn=cmd_plugin)
    p = sub.add_parser("doctor"); p.add_argument("--architecture", action="store_true"); p.add_argument("--runtime", metavar="STACK")
    p.set_defaults(fn=cmd_doctor)
    p = sub.add_parser("dev", help="the development suite: map, new, fixture, check, baseline, job")
    p.add_argument("--root", default=".", help="repository (default .; DEVPOINTS.yaml is found upwards)")
    ds = p.add_subparsers(dest="sub", required=True)

    def rooted(q):
        # Also on the subcommand, so `sch dev map --root X` works as readily as
        # `sch dev --root X map`. Argparse accepts a parent option only before the subcommand,
        # and an agent that has to remember which side it goes on will put it on the wrong one.
        q.add_argument("--root", default=None, help="repository (default .)")
        return q

    q = rooted(ds.add_parser("map"))
    q.add_argument("--init", action="store_true",
                   help="write a starter DEVPOINTS.yaml here, for a repository that declares nothing yet")
    q.add_argument("--force", action="store_true", help="with --init, overwrite an existing one")
    q.set_defaults(fn=cmd_dev)
    q = rooted(ds.add_parser("new")); q.add_argument("point"); q.add_argument("name")
    q.add_argument("--force", action="store_true"); q.set_defaults(fn=cmd_dev)
    q = rooted(ds.add_parser("fixture")); q.add_argument("dir"); q.add_argument("--shape", choices=["a", "b"])
    q.add_argument("--seed", type=int, default=20260906)
    q.add_argument("--cells", type=int, default=2000,
                   help="cells per shape. Two sizes are what separates a fixed memory cost from a "
                        "per-cell one; one size cannot")
    q.add_argument("--splice", action="store_true",
                   help="also write spliced and unspliced layers, for a plugin whose input is "
                        "those. Off by default: the digest is a contract every baseline rests on")
    q.add_argument("--force", action="store_true",
                   help="rebuild even when a fixture written from these exact arguments is "
                        "already there. The cohort is a pure function of them, so the default "
                        "is to reuse it - the same rule `scprofile install` applies to an "
                        "environment")
    q.add_argument("--crossed", action="store_true",
                   help="a second design factor crossed with the first: eight samples, two in "
                        "every cell of a 2x2. Off by default for the same reason. Without it no "
                        "interaction exists, so the branch that reads one is never entered")
    q.set_defaults(fn=cmd_dev)
    q = rooted(ds.add_parser("check")); q.add_argument("--point"); q.add_argument("--name")
    q.add_argument("--only", action="append", choices=list(_TIERS)); q.add_argument("--skip", action="append", choices=list(_TIERS))
    q.add_argument("--keep-going", action="store_true"); q.add_argument("--record-baseline", action="store_true")
    q.add_argument("--terms"); q.add_argument("--fixture-dir"); q.add_argument("--seed", type=int, default=20260906)
    q.set_defaults(fn=cmd_dev)
    # CONVERT: a raw tool becoming a plugin, and picking that up where it was left. `status` is
    # the default because the first question on returning to a half-built plugin is always the
    # same one, and it is computed from the file rather than remembered.
    jc = rooted(ds.add_parser("jobcheck",
                              help="the shell defects this family has paid for, on ANY job "
                                   "script - not only the ones kept in jobs/"))
    jc.add_argument("paths", nargs="*", type=Path,
                    help="job scripts to read (default: every jobs/*.pbs under --root)")
    jc.set_defaults(fn=cmd_dev)

    q = rooted(ds.add_parser("convert"))
    q.add_argument("action", nargs="?", default="status",
                   choices=["status", "freshness", "borrowed", "inventory", "account",
                            "measure", "promised", "defaults", "references", "contract", "legends",
                            "build"])
    q.add_argument("--point", default=None)
    q.add_argument("--name", default=None,
                   help="the plugin being converted. REQUIRED for the actions that fill a "
                        "declaration: they show you the upstream, and seeing the whole family's "
                        "at once leaves nothing held out to prove a change to this tool "
                        "generalises. `status` reads declarations only and takes all of them")
    q.add_argument("--tool", default=None, help="override the upstream named in the declaration")
    q.add_argument("--python", default=None, help="the interpreter the plugin's own env uses")
    q.add_argument("--rscript", default=None)
    q.add_argument("--run", default=None, help="a completed run, for `measure`")
    q.set_defaults(fn=cmd_dev)
    q = rooted(ds.add_parser("baseline")); q.add_argument("action", choices=["record", "check"])
    q.add_argument("rundir"); q.add_argument("--path", required=True); q.set_defaults(fn=cmd_dev)
    q = rooted(ds.add_parser("job")); q.add_argument("--ref", required=True); q.add_argument("--rundir", required=True)
    q.add_argument("--tool", required=True); q.add_argument("--queue", required=True)
    q.add_argument("--select", required=True); q.add_argument("--predict", required=True)
    q.add_argument("--out", required=True); q.add_argument("--walltime", default="04:00:00")
    q.add_argument("--name"); q.set_defaults(fn=cmd_dev)

    p = sub.add_parser("conform"); p.add_argument("repo", nargs="?"); p.add_argument("--terms")
    p.add_argument("--shapes", metavar="FILE",
                   help="site shapes (hostnames, job ids, filesystem roots) - the file belongs to "
                        "the site, not to the tool; $SCH_SITE_SHAPES is the fallback")
    p.add_argument("--run", action="append")
    p.add_argument("--against", metavar="REFRUN", help="a reference run: is a comparison with --run meaningful?")
    p.set_defaults(fn=cmd_conform)

    # `--json` IS GLOBAL, SO IT IS ACCEPTED IN BOTH PLACES. It was declared only on the top-level
    # parser, which made `sch dev map --json` - the form the skill, the README and DEVELOPING all
    # give an agent - exit 2 with "unrecognized arguments". An agent following the documentation
    # failed on its first machine-readable call, and the working form was undocumented.
    #
    # SUPPRESS is what makes this safe: without it the subcommand's default of False would
    # overwrite a True set before the subcommand, so `sch --json dev map` would silently stop
    # emitting JSON. With it the attribute is simply not set when the flag is absent.
    for name, child in sub.choices.items():
        if not any(a.dest == "json" for a in child._actions):
            child.add_argument("--json", action="store_true", default=argparse.SUPPRESS,
                               help="machine-readable output (accepted here or before the subcommand)")
        for gname, grand in getattr(child, "_subparsers", None) and _grandchildren(child) or []:
            if not any(a.dest == "json" for a in grand._actions):
                grand.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    return ap


def _grandchildren(parser):
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return list(action.choices.items())
    return []


def main(argv=None) -> int:
    ap = build_parser()
    a = ap.parse_args(argv)
    if not hasattr(a, "json"):
        a.json = False
    if a.cmd == "conform" and not a.repo and not a.run and not a.against:
        ap.error("conform needs a repository path or --run RUNDIR")
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
