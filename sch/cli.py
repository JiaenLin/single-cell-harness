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
            recs = ([F.write(a.dir, shape=a.shape, seed=a.seed)] if a.shape
                    else F.write_both(a.dir, seed=a.seed))
        except ImportError as e:
            print(f"the fixture needs anndata, numpy and pandas: {e}", file=sys.stderr)
            return CANNOT_RUN
        if a.json:
            print(json.dumps(recs, indent=1))
            return 0
        for r in recs:
            print(f"  shape {r['shape']}  {r['cells']} cells x {r['genes']} genes  digest {r['digest']}")
            print(f"    {r['observations']}")
            print(f"    {r['design']}")
            print("    roles: " + ", ".join(f"{k}={v}" for k, v in r["roles"].items()))
        print(f"\n  {len(F.HAZARDS)} structural hazards are built in; see FIXTURE_<shape>.json")
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

    if a.sub == "convert":
        from .dev import convert as CV
        doc = P.load(a.root)
        point = a.point or next(iter(P.points(doc)))
        try:
            _ph, up_path, _stages = CV.plan(doc, point)
        except CV.ConvertError as e:
            print(f"sch dev convert: {e}", file=sys.stderr)
            return CANNOT_RUN
        # THE SPECS ARE FOR THE ACTIONS THAT READ A DECLARATION, and `measure` is not one of
        # them: it runs the child's own command against a completed run and never opens a plugin.
        # Requiring them first made it refuse with "no widget named None" - an error about the
        # wrong thing entirely, on a repository where nothing was wrong.
        specs = []
        if a.action in ("status", "inventory", "account"):
            specs = _convert_specs(doc, point, a.root, a.name)
            if not specs:
                print(f"sch dev convert: no {point} named {a.name!r} under {a.root}",
                      file=sys.stderr)
                return CANNOT_RUN
        if a.action == "status":
            out = []
            for nm, spec in specs:
                out.append(CV.format_status(CV.status(spec, doc, point), nm, point))
            print("\n\n".join(out))
            return OK
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
            print(CV.worksheet(tool, best.names, spec.get("native_plots"), _ph))
        return FAILED if bad else OK

    if a.action == "measure":
        # THE STAGE DECLARES ITS OWN COMMAND, the way `tests` and `fixture` already do. The
        # harness does not know what a run directory of this tool looks like and must not learn.
        cmd = CV.stage_command(doc, point, "measure")
        if not cmd:
            print(f"sch dev convert: point {point!r} declares no command for the measure stage, "
                  f"so there is nothing to run. Add `command:` to that stage in DEVPOINTS.yaml.",
                  file=sys.stderr)
            return CANNOT_RUN
        if not a.run:
            print("sch dev convert measure: pass --run RUNDIR, a completed run of this plugin. "
                  "The measurement is fitted from what a real run cost; nothing here can invent "
                  "it.", file=sys.stderr)
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
    p.add_argument("--subject"); p.set_defaults(fn=cmd_ask)
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
    q.add_argument("--seed", type=int, default=20260906); q.set_defaults(fn=cmd_dev)
    q = rooted(ds.add_parser("check")); q.add_argument("--point"); q.add_argument("--name")
    q.add_argument("--only", action="append", choices=list(_TIERS)); q.add_argument("--skip", action="append", choices=list(_TIERS))
    q.add_argument("--keep-going", action="store_true"); q.add_argument("--record-baseline", action="store_true")
    q.add_argument("--terms"); q.add_argument("--fixture-dir"); q.add_argument("--seed", type=int, default=20260906)
    q.set_defaults(fn=cmd_dev)
    # CONVERT: a raw tool becoming a plugin, and picking that up where it was left. `status` is
    # the default because the first question on returning to a half-built plugin is always the
    # same one, and it is computed from the file rather than remembered.
    q = rooted(ds.add_parser("convert"))
    q.add_argument("action", nargs="?", default="status",
                   choices=["status", "inventory", "account", "measure"])
    q.add_argument("--point", default=None)
    q.add_argument("--name", default=None, help="the plugin being converted; omit for all of them")
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
