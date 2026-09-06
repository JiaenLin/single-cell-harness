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
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, CONTRACT


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
        checks = conform_repo(a.repo, a.terms)
        print(f"{a.repo}:")
        print(format_checks(checks))
    if a.json:
        print(json.dumps(checks, indent=1, default=str))
    return 0 if all(c["ok"] or c["level"] == "warn" for c in checks) else 2


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
    p = sub.add_parser("conform"); p.add_argument("repo", nargs="?"); p.add_argument("--terms"); p.add_argument("--run", action="append")
    p.add_argument("--against", metavar="REFRUN", help="a reference run: is a comparison with --run meaningful?")
    p.set_defaults(fn=cmd_conform)
    return ap


def main(argv=None) -> int:
    ap = build_parser()
    a = ap.parse_args(argv)
    if a.cmd == "conform" and not a.repo and not a.run and not a.against:
        ap.error("conform needs a repository path or --run RUNDIR")
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
