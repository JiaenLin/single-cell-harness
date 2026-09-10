"""Seven tiers between an idea and a queue, in the order that makes the cheapest failure first.

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

import concurrent.futures as cf
import json
import os
import shutil
import subprocess
import sys
import tempfile
import re
import time
from pathlib import Path

from . import baseline as bl
from . import fixture as fx
from . import points as pts

TIERS = ("declaration", "rules", "contract", "unit", "fixture_a", "fixture_b", "leak",
         "baseline")


def _t(results, tier, ok, evidence, cannot="", skipped=False, seconds=0.0, applicable=True):
    """`applicable=False` marks a tier there is NOTHING HERE FOR - no test command declared, no
    products to fingerprint. That is different from a tier that could have run and could not, for
    want of a library or a word list, and only the second should make a check report itself
    incomplete. Conflating them would make every repository that legitimately has no baseline
    exit 3 for ever, and an exit code that is always the same is not read."""
    results.append({"tier": tier, "ok": bool(ok), "skipped": bool(skipped),
                    "applicable": bool(applicable),
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
    """Substitute the declared placeholders and NOTHING else.

    `str.format` was the obvious implementation and it is wrong here: a fixture command may
    legitimately contain braces that are not placeholders - a JSON argument, a shell expansion,
    a `python -c` body - and format raises KeyError on them, naming a "missing key" the author
    never wrote. Explicit replacement has no escaping rules to learn and leaves everything it
    does not recognise exactly as written.
    """
    out = []
    for x in template:
        t = str(x)
        for k, v in kw.items():
            t = t.replace("{" + k + "}", str(v))
        out.append(t)
    return out


#: A line that says what went wrong rather than where. Python names its exceptions
#: `SomethingError:` / `AssertionError:` at column 0 of the last frame, and unittest banners its
#: failures `ERROR:` / `FAIL:`; a runner of runners prints `FAIL <name>`.
_NAMES_A_FAULT = re.compile(r"^(?:[A-Za-z_.]*(?:Error|Exception|Exit)\b.*:|ERROR:|FAIL:?\s)")


def _excerpt(out: str, head: int = 6, tail: int = 14) -> list:
    """The beginning AND the end of a runner's output.

    This took only the last twelve lines, and a test runner prints its verdict FIRST: "4 FAILING
    of 66 suite(s):" followed by the names. A newcomer was shown one failure, fixed it, re-ran,
    was shown the next, and never once saw the count - four round trips through a tier that takes
    a quarter of a minute. The comment twenty lines above this one is about a pipe hiding exactly
    this kind of information.
    """
    lines = [ln for ln in out.splitlines() if ln.strip()]
    if len(lines) <= head + tail:
        return lines
    # AND THE LINES THAT NAME THE ERROR, WHICH ARE IN THE MIDDLE. A unittest failure block is
    # dots, then a banner, then a traceback, then `SomeError: what happened` - and head-plus-tail
    # keeps the dots and the innermost frames and drops the one line that says what went wrong.
    # Measured: six errors in one tier, diagnosed across three cluster submissions, and the
    # exception type was never once printed. An excerpt that omits the finding is the pipe this
    # function's own docstring is about, one level in.
    keep = [i for i, ln in enumerate(lines[head:-tail], head)
            if _NAMES_A_FAULT.match(ln.strip())]
    if not keep:
        return lines[:head] + [f"        … {len(lines) - head - tail} line(s) not shown …"] \
            + lines[-tail:]
    out_lines, prev = lines[:head], head - 1
    for i in keep[:12]:
        if i > prev + 1:
            out_lines.append(f"        … {i - prev - 1} line(s) not shown …")
        out_lines.append(lines[i])
        prev = i
    if len(lines) - tail > prev + 1:
        out_lines.append(f"        … {len(lines) - tail - prev - 1} line(s) not shown …")
    return out_lines + lines[-tail:]


def _jobs() -> int:
    """How many suites or shapes this machine should run at once.

    From the scheduler's allocation where there is one - a PBS job that asked for 8 cores gets 8,
    not the 128 the node happens to have - and from the CPU count otherwise. Capped, because past
    a handful of concurrent subprocesses the limit is the filesystem rather than the cores, and a
    developer's laptop should not be brought to its knees by a check.
    """
    n = os.environ.get("NCPUS") or os.environ.get("SCH_DEV_JOBS") or os.cpu_count() or 1
    try:
        return max(1, min(8, int(n)))
    except (TypeError, ValueError):
        return 1


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
            where = f"{r['table']} in {r['file']}" if r["keys"] or "{name}" not in str(r["table"]) \
                else f"{r['file']} (no line matching {r['table']})"
            ev.append(f"{name!r} is not registered: {where}"
                      + (f" — it has {len(r['keys'])} entries" if r["keys"] else "")
                      + (f". Run `{r['fix']}`" if r.get("fix") else ""))
            ok = False
        else:
            how = f"in {r['table']}" if r["keys"] else "as a line in"
            ev.append(f"{name!r} is registered {how} {r['file']}" if r["keys"]
                      else f"{name!r} is registered: a matching line is in {r['file']}")
    if not rows:
        ev.append(f"point {point_name!r} declares no registry - nothing to check here")
    # A bare identifier in `must_declare` is a key and is CHECKED against the artefact; a
    # sentence is a requirement for a person and is printed. Printing both and checking neither
    # is how a scaffold missing three required keys passed this tier while the tier was
    # displaying their names.
    keys = [k for k in (pt.get("must_declare") or []) if pts._KEYISH.match(str(k))]
    prose = [k for k in (pt.get("must_declare") or []) if not pts._KEYISH.match(str(k))]
    if keys:
        where, present = pts.declared_keys(doc, point_name, name)
        if present is None:
            ev.append(f"cannot read {where}, so {len(keys)} required key(s) are unchecked")
            ok = False
        else:
            missing = [k for k in keys if k not in present]
            if missing:
                ev.append(f"{where} does not declare "
                          + (missing[0] if len(missing) == 1 else ", nor ".join(missing)))
                ok = False
            else:
                ev.append(f"{where} declares all {len(keys)} required key(s)")
    for k in prose:
        ev.append(f"must declare (for a person to check): {k}")
    return _t(results, "declaration", ok, ev,
              cannot="that a declared key is TRUE - only that it is there. A sentence in "
                     "`must_declare` is printed and not checked; a bare key name is checked.",
              seconds=time.time() - t0)


def t_rules(doc, point_name, results):
    """The rules of the ROUND, if this repository declares any.

    A COMMAND YOU HAVE TO REMEMBER TO TYPE IS NOT ENFORCEMENT. The rules of a development round -
    which artefacts are held out, where a change may land, that general mechanism inside an
    artefact is generated and never copied - are worth what checks them on the way past, not what
    checks them when somebody asks. So they are a tier.

    A REPOSITORY THAT DECLARES NONE IS NOT FAILED BY THIS, and is not passed by it either: the
    tier reports that it could not run, which is the same answer the ladder already gives for a
    fixture nobody declared. Four of the five repositories this suite serves are in that state,
    and inventing rules for them here would be this tool deciding how somebody else's round works.

    THE RANGE COMES FROM THE DECLARATION. Passing one here would let the tier choose the answer.
    """
    from . import rules as RU
    from .convert import _convert_specs_for_ladder as _specs
    t0 = time.time()
    if not RU.declared(doc):
        return _t(results, "rules", True, [], skipped=True,
                  cannot=f"anything: {doc['_root']} declares no `rules:` block, so this round has "
                         f"stated no rules")
    try:
        specs = _specs(doc, point_name)
    except Exception as e:                                                # noqa: BLE001
        return _t(results, "rules", False, [f"could not read the artefacts at {point_name!r}: {e}"],
                  seconds=time.time() - t0)
    rows = RU.check(doc, point_name, specs, root=doc["_root"], since=RU.since_of(doc))
    bad = [f"{r['rule']}: {r['says']}" + ("".join("\n      " + d for d in r["detail"][:6]))
           for r in rows if r["verdict"] == RU.BROKEN]
    mute = [f"{r['rule']}: {r['says']}" for r in rows if r["verdict"] == RU.CANNOT_SAY]
    ev = bad + mute or [f"{len(rows)} rule(s) of this round hold"]
    return _t(results, "rules", not bad, ev,
              cannot="that the rules DECLARED are the right ones - only that what is declared "
                     "still holds. A round that declares an easy rule passes easily.",
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
              cannot="that a RUN conforms - `sch conform --run RUNDIR` is a different question",
              seconds=time.time() - t0)


def t2_unit(doc, results, skip=False):
    cmd = (doc.get("tests") or {}).get("command")
    if skip or not cmd:
        return _t(results, "unit", True,
                  ["no `tests.command` declared" if not cmd else "skipped by request"],
                  skipped=True, applicable=bool(cmd))
    r = _run(_fill(cmd, python=sys.executable, root=doc["_root"], jobs=_jobs()), doc["_root"])
    return _t(results, "unit", r["code"] == 0,
              [f"exit {r['code']}: {' '.join(r['cmd'])}"] + _excerpt(r["out"]),
              cannot="anything about data the suite does not carry",
              seconds=r["seconds"])


def _fixture_tier(doc, point_name, name, shape, fixdir, results, tier, out_name=None):
    spec = _fixture_spec(doc, point_name)
    if not spec.get("command"):
        return _t(results, tier, True, ["no `fixture.command` declared - nothing to run"],
                  skipped=True, applicable=False)
    obs = Path(fixdir) / f"fixture_{shape}.h5ad"
    dsn = Path(fixdir) / f"design_{shape}.csv"
    if not obs.is_file():
        return _t(results, tier, False, [f"{obs} was not generated - is anndata installed?"], skipped=True)
    out = Path(fixdir) / (out_name or f"run_{shape}")
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    env = dict(os.environ, PYTHONNOUSERSITE="1", SCH_DEV_FIXTURE=shape)
    ev, ok, secs = [], True, 0.0
    # A CORRECT REFUSAL IS NOT A FAILURE. The fixture carries a covariate deliberately confounded
    # with the condition, and a tool that plans an analysis on it anyway is the one with the
    # defect. scProfile refuses, exits non-zero, and the first version of this tier read that as
    # the tool breaking - which would have taught an agent to remove the hazard. A point may
    # therefore declare `accepts_refusal`, and must then also declare `refusal_says`: a phrase
    # the refusal itself contains, so that a crash - which says nothing in particular - still
    # fails. Accepting every non-zero exit would turn this tier off.
    says = str(spec.get("refusal_says") or "")
    for raw in _commands(spec):
        cmd = _fill(raw, python=sys.executable, observations=obs, design=dsn, out=out,
                    name=name, shape=shape, root=doc["_root"], jobs=_jobs(), **_roles(shape))
        r = _run(cmd, doc["_root"], env=env, timeout=int(spec.get("timeout") or 1800))
        secs += r["seconds"]
        ev.append(f"exit {r['code']} in {r['seconds']:.1f}s: {' '.join(r['cmd'])}")
        if r["code"] != 0:
            if spec.get("accepts_refusal") and says and says in r["out"]:
                ev.append(f"refused, as this point declares it should: {says!r} is in the output")
                continue
            if spec.get("accepts_refusal") and not says:
                ev.append("accepts_refusal is declared without refusal_says, so a crash would "
                          "pass as a refusal; refusing to accept it")
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
    """Cohort and site terms in the REPOSITORY. Not in what a run produced, and that boundary
    took two passes on the cluster to get right.

    The first version also scanned the fixture run's output, on the reasoning that a tool can be
    clean in its source and still write a cohort's vocabulary into a result. True, but the site
    list that catches a cohort also contains the site: the cluster's user, its group, its
    scheduler head node. A run record is SUPPOSED to say where it ran - that is provenance, and
    every STATUS.json and every seal carries it correctly. Scanning them reported three of five
    repositories as leaking because their runs recorded the machine they ran on.

    PATHS AND JOB IDS ARE PROVENANCE; A DEFAULT IS VOCABULARY. In a repository they are the same
    thing and both are defects, which is why the whole tree is scanned here. In a run's output
    they are opposites, and no word list distinguishes them. So this tier asks its question of
    the repository, where the answer is unambiguous, and says below what it therefore does not
    look at.

    THE GUARD FILE IS NOT EXEMPT HERE, AND THAT IS DELIBERATE. `sch conform`'s S1 exempts a file
    named test_portability or test_leak from its own scan, because such a file must SPELL the
    shapes it searches for - a home-path regex, a hostname pattern - and would otherwise report
    itself. That exemption is right for shapes and wrong for terms: terms are supplied from
    outside precisely so that no file in the repository has to contain one, which three of the
    four children demonstrate by containing none. This tier searches only supplied terms, never
    shapes, so it needs no exemption and grants none - and on 2026-09-06 it found a cohort's name
    in the comment of the one file whose job is to prove the cohort's name is absent, sitting in
    the blind spot the wholesale exemption creates."""
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
    # THE FIXTURE DIRECTORY'S OWN PATH IS NOT A LEAK. It is where the caller asked for the run
    # to be written, and on this cluster that is inside the project that owns the cohort - so
    # every manifest and every STATUS.json records it, and the first version of this tier
    # reported all five repositories as leaking because of where the run directory sat. What is
    # being asked here is whether the TOOL wrote a cohort's vocabulary into its output, so the
    # caller's path is redacted before the search and the redaction is reported.
    hits = []
    for p in _text_files(root):
        low = _read(p).lower()
        for w in words:
            if w.lower() in low:
                hits.append(f"{p.relative_to(root)}: {w}")
    return _t(results, "leak", not hits,
              hits[:20] or [f"{len(words)} terms from {tf}, none present anywhere in the tree"],
              cannot="that a term nobody listed is absent - the list is the limit of this check; "
                     "and nothing about a RUN's output, which records where it ran on purpose",
              seconds=time.time() - t0)


def t6_baseline(doc, fixdir, results, name, record=False, point_name=None):
    """A baseline records only what two executions agreed on.

    Recording a fingerprint of one run and calling it "unchanged" assumes every number in it is
    execution-stable, and this family has measured that it is not: harmony's embedding moved
    0.214 between two machines of the same model on 2026-09-06, and its benchmark total moves
    ~0.013 between executions on one. A baseline that includes such a field fails on the next
    machine, for a reason that is never the change - and a check that cries wolf is switched off
    within a week, which costs more than never having had it.

    So recording RUNS THE FIXTURE TWICE and keeps only the fields that agreed. The rest are
    excluded and NAMED in the file as `not_execution_stable`, which turns an assumption nobody
    stated into a measurement anybody can read. It is the same rule the reproduction discipline
    reached from the other direction: a prediction is per output, and an output that is not
    execution-stable is named with its spread rather than predicted identical.
    """
    spec = _fixture_spec(doc, point_name or "")
    bdir = Path(doc["_root"]) / (doc.get("baseline_dir") or "tests/baselines")
    path = bdir / f"{name}.baseline.json"
    run = Path(fixdir) / "run_a"
    if not run.is_dir():
        return _t(results, "baseline", True,
                  ["no fixture run to fingerprint - this point's fixture writes no products"],
                  skipped=True, applicable=False)
    if record:
        # THE FIRST EXECUTION IS STILL ON DISK. Its fingerprint used to be taken at the end of
        # every fixture_a and stashed in case a recording followed - reading and hashing every
        # product, including a 40 MB object, on every check, and throwing it away. The re-run
        # below writes to run_a2, so run_a is untouched and can be read here instead: the same
        # comparison, paid for only by the runs that actually record it.
        first = bl.fingerprint(run)["products"]
        second = []
        # THE SECOND EXECUTION WRITES SOMEWHERE ELSE, on purpose. Two runs into one directory
        # cannot tell a stable value from one that merely embeds its own output path - and a
        # baseline full of paths fails the first time anybody runs the check from a different
        # directory, which is every time. Running elsewhere makes path-dependence show up as
        # what it is: not execution-stable.
        _fixture_tier(doc, point_name or "", name, "a", fixdir, second, "_rerun", out_name="run_a2")
        again = Path(fixdir) / "run_a2"
        if not second or not second[0]["ok"]:
            return _t(results, "baseline", False,
                      ["the second execution did not succeed, so nothing can be shown to be "
                       "stable; refusing to record a baseline from one run"]
                      + (second[0]["evidence"][:6] if second else []))
        fp = bl.fingerprint(again)
        drift = bl.compare(fp, {"rtol": bl.RTOL, "atol": bl.ATOL, "products": first})
        # NAMED, NOT DELETED. `compare` skips these; removing them from the record would make the
        # next check report each one as a NEW field, and would miss opaque files entirely, whose
        # identity is a sha256 rather than a number.
        fp["not_execution_stable"] = sorted({f"{d['product']}::{d['what']}" for d in drift})
        unstable = fp["not_execution_stable"]
        fp["measured_over"] = 2
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(fp, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        ev = [f"recorded {len(fp['products'])} products to {path}, over two executions",
              f"covers {len(fp['covers'])}, opaque {len(fp['does_not_cover'])}"]
        ev += ([f"NOT execution-stable, excluded and named in the file: {len(unstable)}"]
               + [f"  {u}" for u in unstable[:8]] if unstable else
               ["every recorded field agreed between the two executions"])
        return _t(results, "baseline", True, ev,
                  cannot="anything about a THIRD execution, or about another machine - two runs "
                         "on one node is the weakest evidence of stability that is still evidence")
    if not path.is_file():
        return _t(results, "baseline", True,
                  [f"no baseline at {path}; record one with `sch dev check --record-baseline`"],
                  cannot="that the numbers are unchanged - there is nothing to compare with",
                  skipped=True)
    try:
        diffs, ref = bl.check(run, path)
    except bl.StaleBaseline as e:
        return _t(results, "baseline", False, [str(e)],
                  cannot="anything about the numbers until the baseline is re-recorded")
    ev = [f"{d['product']}: {d['what']} {d['detail']}" for d in diffs[:15]]
    note = bl.elsewhere(ref)
    if diffs and note:
        ev.append("NOTE: " + note)
    if ref.get("not_execution_stable"):
        ev.append(f"{len(ref['not_execution_stable'])} field(s) were excluded when this baseline "
                  f"was recorded, for moving between two executions; they are named in the file")
    return _t(results, "baseline", not diffs,
              ev or [f"{len(ref.get('products', {}))} products agree within rtol {ref.get('rtol')}"],
              cannot="that a difference is wrong - a deliberate change bumps state_version and re-records")


# ------------------------------------------------------------------------------------ driver
def run(root=".", point_name=None, name=None, only=None, skip=(), keep_going=False,
        record_baseline=False, terms=None, fixdir=None, seed=20260906,
        parallel=True) -> dict:
    doc = pts.load(root)
    results: list = []
    want = (lambda t: (not only or t in only) and t not in skip)
    tmp = fixdir or tempfile.mkdtemp(prefix="sch-dev-fixture-")
    made_fixture = False

    def stop():
        return (not keep_going) and any((not r["ok"]) and not r["skipped"] for r in results)

    if point_name and name and want("declaration"):
        t0_declaration(doc, point_name, name, results)
    if not stop() and want("rules"):
        t_rules(doc, point_name, results)
    if not stop() and want("contract"):
        t1_contract(doc, results, terms)
    if not stop() and want("unit"):
        t2_unit(doc, results, skip="unit" in skip)
    if not stop() and (want("fixture_a") or want("fixture_b")):
        try:
            fx.write_both(tmp, seed=seed)
            made_fixture = True
        except ImportError as e:
            # BOTH SHAPES, NOT JUST THE FIRST. Only a fixture_a row was appended, so fixture_b -
            # the tier this suite calls the one you will be tempted to skip - was absent from the
            # report entirely, and absent from the union of what a green ladder did not prove. A
            # tier that vanishes when it cannot run is worse than one that fails.
            for sh in ("a", "b"):
                if want(f"fixture_{sh}"):
                    _t(results, f"fixture_{sh}", False,
                       [f"cannot build the fixture: {e}"], skipped=True)
    if made_fixture and not stop():
        shapes = [sh for sh in ("a", "b") if want(f"fixture_{sh}")]
        # THE TWO SHAPES ARE INDEPENDENT, so they run at the same time. They read the same
        # read-only fixture and write to different directories, and on this family they are the
        # longest tier - 24.5s twice for scIntegrate, 18.2s twice for scAnno, half of it spent
        # waiting for the other one to finish.
        #
        # Running both even when the first fails is deliberate. The wall clock is the same, and
        # "a passes, b fails" is a different finding from "both fail" - the first says a column
        # name is assumed, the second says the mechanism is broken. Stopping early would have
        # hidden which.
        if parallel and len(shapes) == 2:
            with cf.ThreadPoolExecutor(max_workers=2) as pool:
                got = list(pool.map(
                    lambda sh: _fixture_tier(doc, point_name or "", name or "", sh, tmp, [],
                                             f"fixture_{sh}"), shapes))
            results.extend(got)                      # in declared order, not completion order
        else:
            for sh in shapes:
                if stop():
                    break
                _fixture_tier(doc, point_name or "", name or "", sh, tmp, results, f"fixture_{sh}")
    if not stop() and want("leak"):
        t5_leak(doc, tmp, results, terms)
    if not stop() and want("baseline") and name:
        t6_baseline(doc, tmp, results, name, record=record_baseline, point_name=point_name)

    ran = [r["tier"] for r in results if not r["skipped"]]
    failed = [r["tier"] for r in results if not r["ok"] and not r["skipped"]]
    # WHAT WAS ASKED FOR, AND WHAT ACTUALLY HAPPENED. A run of three tiers out of seven used to
    # be indistinguishable from a run of seven, because the exit code was computed from failures
    # alone. The skill says a green that established nothing must never be read as permission -
    # and the one thing an agent branches on could not tell the two apart.
    asked = [t for t in TIERS if (not only or t in only) and t not in skip]
    if not (point_name and name):
        asked = [t for t in asked if t not in ("declaration", "baseline")]
    inapplicable = {r["tier"] for r in results if not r.get("applicable", True)}
    unrun = [t for t in asked if t not in ran and t not in inapplicable]
    return {"tool": doc.get("tool"), "point": point_name, "name": name, "fixture_dir": tmp,
            "results": results, "ran": ran, "failed": failed,
            "asked": asked, "not_run": unrun,
            "ok": not failed,
            # `ran` must be non-empty too: asking only for a tier that needs a --name, without
            # one, leaves nothing asked AND nothing done, and "no tiers were requested" is not a
            # pass either.
            "complete": bool(ran) and not failed and not unrun,
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
    na = [r["tier"] for r in rep["results"] if not r.get("applicable", True)]
    lines.append(f"{len(rep['ran'])} of {len(rep.get('asked') or rep['ran'])} tier(s) ran"
                 + (f" ({len(na)} not applicable here: {', '.join(na)})" if na else "")
                 + f", {len(rep['failed'])} failing"
                 + (f": {', '.join(rep['failed'])}" if rep["failed"] else ""))
    if rep.get("not_run"):
        lines.append(f"  COULD NOT run: {', '.join(rep['not_run'])} - so this is not a full check")
    return "\n".join(lines)
