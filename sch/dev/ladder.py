"""Six tiers between an idea and a queue, in the order that makes the cheapest failure the first.

WHAT THIS IS FOR. The proof that a change is sound has, until now, cost a cluster run against the
real cohort: an hour, a queue slot, and a reproduction that either matches or does not. That is
the right final proof and it is the wrong first one, because most changes fail for reasons a
laptop could have found in four seconds - a registry entry missing, a declaration incomplete, a
column name assumed. When the only available proof is expensive, it gets deferred, and a change
reaches the queue carrying three defects instead of one.

    T0  declaration   the point exists, the thing is registered, it declares what it must
    T1  contract      `sch conform` on the repository - the rules the family already has
    T2  unit          the repository's own suite, as the repository defines it
    T3  fixture a     it runs end to end on synthetic data and leaves a valid status behind
    T4  fixture b     the same, with every role renamed - the overfit detector
    T5  leak          no cohort or site term in the source, the tests, or the output
    T6  baseline      the numbers that were not supposed to move did not move

EVERY TIER SAYS WHAT IT DOES NOT PROVE, and the run ends by printing the union of those, with the
command that would settle them. A green ladder is not a merge; it is permission to spend an hour
on the cluster with a reasonable expectation that the hour will not be wasted. Stating that
plainly at the end of a passing run is the difference between a gate and a rubber stamp - the
whole risk of a fast local check is that it starts to feel like the answer.

NO SHELL PIPELINES ANYWHERE IN HERE. Three times in this project's history a real failure was
hidden by a pipe: `| tee` and `| tail` return the exit code of the last command in the pipeline,
so a tool that refused and a tool that passed looked identical to the script watching it. Every
tier below runs its command as an argument list through `subprocess.run` and reads `returncode`
off the process that actually did the work. A toolkit that leaves that to each agent to remember
has not removed the failure - it has only moved it.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from . import baseline as bl
from . import fixture as fx
from . import points as pts

TIERS = ("declaration", "contract", "unit", "fixture_a", "fixture_b", "leak", "baseline")


def _t(results, tier, ok, evidence, cannot="", skipped=False, seconds=0.0):
    results.append({"tier": tier, "ok": bool(ok), "skipped": bool(skipped),
                    "evidence": evidence, "cannot_prove": cannot, "seconds": round(seconds, 2)})
    return results[-1]


def _run(cmd, cwd, env=None, timeout=1800) -> dict:
    """One command, no shell, exit code read from the process that did the work."""
    t0 = time.time()
    try:
        p = subprocess.run([str(c) for c in cmd], cwd=str(cwd), env=env, timeout=timeout,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        return {"code": p.returncode, "out": p.stdout or "", "seconds": time.time() - t0,
                "cmd": [str(c) for c in cmd]}
    except FileNotFoundError as e:
        return {"code": 127, "out": f"{e}", "seconds": time.time() - t0, "cmd": [str(c) for c in cmd]}
    except subprocess.TimeoutExpired:
        return {"code": 124, "out": f"timed out after {timeout}s", "seconds": time.time() - t0,
                "cmd": [str(c) for c in cmd]}


def _fill(template, **kw):
    return [str(x).format(**kw) for x in template]


def _commands(spec):
    """One command, or a sequence of them. A tool whose end-to-end exercise is three invocations
    - init, mount, materialise - should not have to hide them in a shell script to be checkable,
    and a shell script is exactly where the pipeline-exit-code trap lives."""
    cmd = spec.get("command")
    if not cmd:
        return []
    return [list(c) for c in cmd] if isinstance(cmd[0], (list, tuple)) else [list(cmd)]


def _roles(shape):
    """Every role, under the name it carries in this shape. A tool that is TOLD which column
    holds the samples is behaving correctly; the fixture must be able to tell it, or shape b
    fails for the wrong reason and the overfit detector cries wolf."""
    return {f"role_{r}": names[shape] for r, names in fx.ROLES.items()}


def _fixture_spec(doc, point_name):
    pt = (doc.get("points") or {}).get(point_name) or {}
    return pt.get("fixture") or doc.get("fixture") or {}


# ------------------------------------------------------------------------------- the tiers
def t0_declaration(doc, point_name, name, results):
    t0 = time.time()
    ev, ok = [], True
    try:
        pt = pts.point(doc, point_name)
    except pts.DevpointsError as e:
        return _t(results, "declaration", False, [str(e)], seconds=time.time() - t0)
    rows = pts.registration(doc, point_name, name)
    for r in rows:
        if not r["readable"]:
            ev.append(f"{r['file']}: {r['table']} is not a literal - registration cannot be read here")
            ok = False
        elif not r["present"]:
            ev.append(f"{r['file']}: {name!r} is not in {r['table']} (has {len(r['keys'])} entries)")
            ok = False
        else:
            ev.append(f"{r['file']}: {name!r} is in {r['table']}")
    if not rows:
        ev.append(f"point {point_name!r} declares no registry - nothing to check here")
    for k in pt.get("must_declare") or []:
        ev.append(f"must declare: {k}")
    return _t(results, "declaration", ok, ev,
              cannot="that the declaration is TRUE - only that it is present",
              seconds=time.time() - t0)


def t1_contract(doc, results, terms=None):
    from ..conform import conform_repo
    t0 = time.time()
    root = doc["_root"]
    terms = terms or (Path(root) / doc["terms"] if doc.get("terms") else None)
    checks = conform_repo(root, str(terms) if terms and Path(terms).is_file() else None)
    bad = [f"{c['id']}: {c['evidence']}" for c in checks if not c["ok"] and c["level"] == "error"]
    warn = sum(1 for c in checks if not c["ok"] and c["level"] == "warn")
    return _t(results, "contract", not bad,
              bad or [f"{len(checks)} checks, 0 failing, {warn} warning(s)"],
              cannot="that a RUN conforms - `sch conform --run` is a different question",
              seconds=time.time() - t0)


def t2_unit(doc, results, skip=False):
    cmd = (doc.get("tests") or {}).get("command")
    if skip or not cmd:
        return _t(results, "unit", True, ["no `tests.command` declared" if not cmd else "skipped by request"],
                  skipped=True)
    r = _run(_fill(cmd, python=sys.executable, root=doc["_root"]), doc["_root"])
    tail = [ln for ln in r["out"].splitlines() if ln.strip()][-12:]
    return _t(results, "unit", r["code"] == 0, [f"exit {r['code']}: {' '.join(r['cmd'])}"] + tail,
              cannot="anything about data the suite does not carry",
              seconds=r["seconds"])


def _fixture_tier(doc, point_name, name, shape, fixdir, results, tier):
    spec = _fixture_spec(doc, point_name)
    if not spec.get("command"):
        return _t(results, tier, True, ["no `fixture.command` declared - nothing to run"], skipped=True)
    obs = Path(fixdir) / f"fixture_{shape}.h5ad"
    dsn = Path(fixdir) / f"design_{shape}.csv"
    if not obs.is_file():
        return _t(results, tier, False, [f"{obs} was not generated - is anndata installed?"], skipped=True)
    out = Path(fixdir) / f"run_{shape}"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    env = dict(os.environ, PYTHONNOUSERSITE="1", SCH_DEV_FIXTURE=shape)
    ev, ok, secs = [], True, 0.0
    for raw in _commands(spec):
        cmd = _fill(raw, python=sys.executable, observations=obs, design=dsn, out=out,
                    name=name, shape=shape, root=doc["_root"], **_roles(shape))
        r = _run(cmd, doc["_root"], env=env, timeout=int(spec.get("timeout") or 1800))
        secs += r["seconds"]
        ev.append(f"exit {r['code']} in {r['seconds']:.1f}s: {' '.join(r['cmd'])}")
        if r["code"] != 0:
            ev += [ln for ln in r["out"].splitlines() if ln.strip()][-14:]
            ok = False
            break
    status = out / "STATUS.json"
    if status.is_file():
        try:
            st = json.loads(status.read_text(encoding="utf-8"))
            ev.append(f"STATUS.json: {st.get('status')} - {st.get('headline')}")
            if st.get("status") == "refused" and spec.get("accepts_refusal"):
                ok = True
                ev.append("refusal accepted: this point declares refusal a valid outcome on the fixture")
            elif st.get("status") not in ("ok",):
                ok = False
        except ValueError as e:
            ev.append(f"STATUS.json is not readable: {e}")
            ok = False
    elif spec.get("products"):
        ev.append("no STATUS.json - the status contract is not being written by this command")
    missing = [p for p in (spec.get("products") or []) if not (out / str(p).format(name=name)).exists()]
    if missing:
        ev.append("missing products: " + ", ".join(missing))
        ok = False
    return _t(results, tier, ok, ev,
              cannot=("that anything here is biologically meaningful - the cohort is synthetic"
                      if shape == "a" else
                      "that names beyond the seven declared roles are resolved rather than assumed"),
              seconds=secs)


def t5_leak(doc, fixdir, results, terms=None):
    """Cohort and site terms, in the SOURCE and in what the fixture run produced. The second half
    matters more than it looks: a tool can be clean in its source and still write a cohort's
    vocabulary into an output because it carries a default it was given once."""
    from ..conform.checks import _load_terms, _read, _text_files
    t0 = time.time()
    root = Path(doc["_root"])
    # THE WORD LIST LIVES OUTSIDE THE REPOSITORY, ALWAYS. A tool that ships the cohort's
    # vocabulary in order to check that it does not ship the cohort's vocabulary has shipped it.
    # Each child already established the convention - $SCQC_FORBIDDEN_TERMS and its siblings -
    # so this looks there before anywhere else, and says which source it used.
    env_var = doc.get("terms_env") or f"{str(doc.get('tool') or 'SCH').upper()}_FORBIDDEN_TERMS"
    candidates = [terms, os.environ.get(env_var), os.environ.get("SCH_FORBIDDEN_TERMS")]
    if doc.get("terms"):
        candidates.append(root / doc["terms"])
    tf = next((c for c in candidates if c and Path(c).is_file()), None)
    words = _load_terms(str(tf)) if tf else []
    if not words:
        return _t(results, "leak", True,
                  [f"no word list: pass --terms, or set ${env_var} to a file of terms this "
                   f"repository must not contain. The list belongs outside the repository."],
                  skipped=True)
    hits = []
    for p in list(_text_files(root)) + [q for q in Path(fixdir).rglob("*")
                                        if q.is_file() and q.suffix in (".json", ".csv", ".md", ".txt")]:
        low = _read(p).lower()
        for w in words:
            if w.lower() in low:
                hits.append(f"{p}: {w}")
    return _t(results, "leak", not hits,
              hits[:20] or [f"{len(words)} terms from {tf}, none present in source or output"],
              cannot="that a term nobody listed is absent - the list is the limit of this check",
              seconds=time.time() - t0)


def t6_baseline(doc, fixdir, results, name, record=False):
    spec = _fixture_spec(doc, "")
    bdir = Path(doc["_root"]) / (doc.get("baseline_dir") or "tests/baselines")
    path = bdir / f"{name}.baseline.json"
    run = Path(fixdir) / "run_a"
    if not run.is_dir():
        return _t(results, "baseline", True, ["no fixture run to fingerprint"], skipped=True)
    if record:
        fp = bl.record(run, path)
        return _t(results, "baseline", True,
                  [f"recorded {len(fp['products'])} products to {path}",
                   f"covers {len(fp['covers'])}, opaque {len(fp['does_not_cover'])}"],
                  cannot="anything - recording is not checking")
    if not path.is_file():
        return _t(results, "baseline", True,
                  [f"no baseline at {path}; record one with `sch dev check --record-baseline`"],
                  cannot="that the numbers are unchanged - there is nothing to compare with",
                  skipped=True)
    diffs, ref = bl.check(run, path)
    ev = [f"{d['product']}: {d['what']} {d['detail']}" for d in diffs[:15]]
    return _t(results, "baseline", not diffs,
              ev or [f"{len(ref.get('products', {}))} products agree within rtol {ref.get('rtol')}"],
              cannot="that a difference is wrong - a deliberate change bumps state_version and re-records")


# ------------------------------------------------------------------------------------ driver
def run(root=".", point_name=None, name=None, only=None, skip=(), keep_going=False,
        record_baseline=False, terms=None, fixdir=None, seed=20260906) -> dict:
    doc = pts.load(root)
    results: list = []
    want = (lambda t: (not only or t in only) and t not in skip)
    tmp = fixdir or tempfile.mkdtemp(prefix="sch-dev-fixture-")
    made_fixture = False

    def stop():
        return (not keep_going) and any((not r["ok"]) and not r["skipped"] for r in results)

    if point_name and name and want("declaration"):
        t0_declaration(doc, point_name, name, results)
    if not stop() and want("contract"):
        t1_contract(doc, results, terms)
    if not stop() and want("unit"):
        t2_unit(doc, results, skip="unit" in skip)
    if not stop() and (want("fixture_a") or want("fixture_b")):
        try:
            fx.write_both(tmp, seed=seed)
            made_fixture = True
        except ImportError as e:
            _t(results, "fixture_a", False, [f"cannot build the fixture: {e}"], skipped=True)
    if made_fixture and not stop() and want("fixture_a"):
        _fixture_tier(doc, point_name or "", name or "", "a", tmp, results, "fixture_a")
    if made_fixture and not stop() and want("fixture_b"):
        _fixture_tier(doc, point_name or "", name or "", "b", tmp, results, "fixture_b")
    if not stop() and want("leak"):
        t5_leak(doc, tmp, results, terms)
    if not stop() and want("baseline") and name:
        t6_baseline(doc, tmp, results, name, record=record_baseline)

    ran = [r["tier"] for r in results if not r["skipped"]]
    failed = [r["tier"] for r in results if not r["ok"] and not r["skipped"]]
    return {"tool": doc.get("tool"), "point": point_name, "name": name, "fixture_dir": tmp,
            "results": results, "ran": ran, "failed": failed,
            "not_run": [t for t in TIERS if t not in ran],
            "ok": not failed,
            "cannot_prove": _unproven(results)}


def _unproven(results) -> list:
    out = ["that the tool reproduces the real cohort - only a cluster run against the reference "
           "does that: `sch dev job` writes it, `sch conform --run NEW --against REF` reads it"]
    for r in results:
        if r["cannot_prove"] and r["cannot_prove"] not in out:
            out.append(f"[{r['tier']}] {r['cannot_prove']}")
        if r["skipped"]:
            out.append(f"[{r['tier']}] did not run: {r['evidence'][0] if r['evidence'] else 'skipped'}")
    return out


def format_run(rep: dict) -> str:
    lines = [f"{rep['tool']}" + (f" :: {rep['point']} {rep['name']}" if rep.get("name") else "")]
    for r in rep["results"]:
        mark = "skip" if r["skipped"] else ("ok  " if r["ok"] else "FAIL")
        lines.append(f"  {mark} {r['tier']:<12} {r['seconds']:>6.1f}s")
        for e in (r["evidence"] or [])[:14]:
            lines.append(f"           {e}")
    lines.append("")
    lines.append("what a green ladder does NOT establish:")
    for c in rep["cannot_prove"]:
        lines.append(f"  - {c}")
    lines.append("")
    lines.append(f"{len(rep['ran'])} tier(s) ran, {len(rep['failed'])} failing"
                 + (f": {', '.join(rep['failed'])}" if rep["failed"] else ""))
    return "\n".join(lines)
