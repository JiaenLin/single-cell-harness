"""A reproduction job written from the reference run's own record, not from memory.

FIVE FAILURES THIS REMOVES, EACH ONE PAID FOR IN A WASTED CLUSTER HOUR DURING SEPTEMBER 2026:

  the flags       PBS 706246 reproduced scProfile with `--label-key cell_type` copied out of a
                  stage script, while the run being reproduced had used `cell_type_forced`. The
                  job sealed FAILED and the difference was mine. A reproduction takes its
                  parameters from the RECORD OF THE RUN IT REPRODUCES - here, literally its argv.
  the products    PBS 706223 checked `rescue/STATUS.rescue.json` while the tool writes `rescued/`.
                  Expected products are derived from the reference run's own directory, not typed.
  the checkout    twice in one afternoon a `git pull` landed in a tool checkout while a run was
                  using it. The rule existed; nothing enforced it. The emitted job records the
                  commit at submission and REFUSES AT START if the checkout has moved.
  the exit code   `| tee` and `| tail` return the last command's status, so a refusal read as a
                  pass three separate times. Nothing below is piped, and `set -o pipefail` is set
                  where a pipe is unavoidable.
  the queue       `-l select=...:host=<node>` in the wrong queue fails with "Insufficient amount
                  of resource: host", which reads like the node does not exist; it means the
                  queue's pool does not contain it. The queue is required, never defaulted, and
                  the header carries the finding.

AND ONE THING IT REQUIRES: the prediction is written into the job header BEFORE submission, in
the author's words, saying what each output should do and what it would mean if it did not. A
prediction made after the numbers are in is not a prediction. The emitter refuses without one.
"""
from __future__ import annotations

import json
import os
import shlex
import time
from pathlib import Path

OUT_FLAGS = ("--out", "--out-dir", "--outdir", "-o", "--output", "--prefix")


def commit_of(repo) -> str | None:
    """By file. Compute nodes have no git binary, and the emitted job reads it the same way.

    A TREE EXPORTED WITHOUT .git CARRIES HEAD.txt (harness ADR-0017's rule for the tool's own
    seal, ADR-0019 for this): the cellchat-only tree on the cluster is such an export.
    """
    git = Path(repo) / ".git"
    head_txt = Path(repo) / "HEAD.txt"
    if not git.exists() and head_txt.is_file():
        try:
            return head_txt.read_text().strip().split()[0]
        except (OSError, IndexError):
            return None
    try:
        if git.is_file():
            git = Path(git.read_text().split(":", 1)[1].strip())
        head = (git / "HEAD").read_text().strip()
        if not head.startswith("ref:"):
            return head
        ref = head.split(None, 1)[1]
        f = git / ref
        if f.exists():
            return f.read_text().strip()
        packed = git / "packed-refs"
        if packed.exists():
            for ln in packed.read_text().splitlines():
                if ln.endswith(" " + ref):
                    return ln.split()[0]
    except (OSError, IndexError):
        return None
    return None


def products_of(ref_dir, figures=True) -> list:
    """What the reference run actually left behind, relative to itself - so the job checks for
    the files the tool writes rather than the files somebody expected it to write.

    `figures=False` leaves the pictures out (harness ADR-0019): a rerun after figure changes
    is allowed to change them, and the plan's promise and the eye judge those."""
    ref = Path(ref_dir)
    keep = {".json", ".csv", ".tsv", ".h5ad", ".html", ".md", ".png", ".pdf", ".npy"}
    if not figures:
        keep -= {".png", ".pdf"}

    def _wanted(rel):
        rel = Path(rel)
        return (rel.suffix in keep and rel.parts[0] not in ("logs", "cache", "tmp")
                and not rel.name.startswith(("RUNNING", "SEALED", "FAILED")))

    # THE RUN'S OWN RECORD FIRST (harness ADR-0019, blind 0006). A directory holds more than the
    # run: the reference's job had run four of the tool's reading commands there, each leaving a
    # STATUS.<cmd>.json, and the rerun sealed FAILED with every product of the run itself present.
    # When the record says what the run delivered, that is the expectation; the scan is for a
    # reference without one.
    # Read from STATUS.json itself - the run command's own record under the conformance
    # contract - and not from the merged record, whose `products` is whichever reader wrote last.
    try:
        import json as _json
        _rec = _json.loads((ref / "STATUS.json").read_text(encoding="utf-8"))
        recorded = [str(x.get("path")) for x in (_rec.get("products") or [])
                    if isinstance(x, dict) and x.get("path") and int(x.get("bytes") or 0) > 0]
    except Exception:                                                     # noqa: BLE001
        recorded = []
    if recorded:
        return sorted({r for r in recorded if _wanted(r)})
    out = []
    for p in sorted(ref.rglob("*")):
        if p.is_file() and p.stat().st_size > 0:
            rel = p.relative_to(ref)
            if _wanted(rel):
                out.append(str(rel))
    return out


def rebuild_argv(record: dict, new_out: str, python: str | None = None,
                 tooldir: str | None = None) -> list:
    """The reference run's own argv, with the destination moved and nothing else touched.

    THE INTERPRETER, WHEN THE RECORD NAMES A SCRIPT (harness ADR-0019): a run records
    `sys.argv`, whose first element is the script - `<tool>/scprofile/cli.py` - and not the
    interpreter that ran it. Given `python`, a script under `tooldir` runs as its module
    (`python -m scprofile.cli ...`), the way the run itself was started."""
    argv = list(record.get("argv") or [])
    if not argv:
        raise ValueError(
            f"{record['dir']} records no argv, so the command that produced it cannot be "
            f"recovered. Reconstructing it by hand is the single most expensive mistake this "
            f"emitter exists to prevent; it will not guess. Reproduce a run that recorded its "
            f"argv, or add one to the record by hand and say in the header that you did.")
    # THE OUTPUT FLAG IS THE ONE WHOSE VALUE IS THE REFERENCE ITSELF (harness ADR-0019, blind
    # 0006). A list of names - `--out`, `--prefix` - is a guess about tools: for one tool
    # `--prefix` is where its plugin ENVIRONMENTS live, and rewriting it sent a rerun to an
    # empty directory where every instance failed at once. What the record knows for certain is
    # where the reference wrote: its own directory, whose key is its last path segment. So a
    # flag is rewritten when its value names that directory or that key, whatever the flag is
    # called; the name list is only the fallback for an argv that names its output some other way.
    ref_dir = str(record.get("dir") or "")
    ref_key = Path(ref_dir).name if ref_dir else ""

    def _is_ref(v):
        v = str(v).rstrip("/")
        return bool(v) and (v == ref_dir.rstrip("/") or (ref_key and Path(v).name == ref_key))

    def _rewrite(by_value):
        out, i, replaced = [], 0, False
        while i < len(argv):
            a = str(argv[i])
            if a.startswith("-") and i + 1 < len(argv) and (
                    _is_ref(argv[i + 1]) if by_value else a in OUT_FLAGS):
                out += [a, new_out]
                i += 2
                replaced = True
                continue
            if "=" in a and a.startswith("-") and (
                    _is_ref(a.split("=", 1)[1]) if by_value
                    else any(a.startswith(f + "=") for f in OUT_FLAGS)):
                out.append(a.split("=", 1)[0] + "=" + new_out)
                i += 1
                replaced = True
                continue
            out.append(a)
            i += 1
        return out, replaced

    out, replaced = _rewrite(by_value=True)
    if not replaced:
        out, replaced = _rewrite(by_value=False)
    if not replaced:
        raise ValueError(
            f"the reference argv names no output flag ({', '.join(OUT_FLAGS)}), so the "
            f"reproduction would write where the reference wrote. Refusing: {' '.join(argv[:12])}")
    if python and out and str(out[0]).endswith(".py"):
        script = Path(out[0])
        mod = None
        if tooldir:
            try:
                rel = script.resolve().relative_to(Path(tooldir).resolve())
                mod = ".".join(rel.with_suffix("").parts)
            except ValueError:
                mod = None
            if mod is None and Path(tooldir).name in script.parts:
                rel = Path(*script.parts[script.parts.index(Path(tooldir).name) + 1:])
                mod = ".".join(rel.with_suffix("").parts) or None
        out = ([python, "-m", mod] if mod else [python, str(script)]) + out[1:]
    return out


HEADER = r"""#!/bin/bash
#PBS -N {name}
#PBS -q {queue}
#PBS -l {select}
#PBS -l walltime={walltime}
#PBS -j oe
#
# ============================================================================================
# {title}
# ============================================================================================
#
# WRITTEN BY `sch dev job` ON {when} - do not hand-edit the derived sections below without
# saying so here, because their whole value is that they were not typed from memory.
#
# THE REFERENCE RUN
#   {ref}
#   commit       {ref_commit}
#   status       {ref_status}
#   state_version {ref_sv}
#   record read from: {ref_sources}
#
# THE COMMAND, TAKEN FROM THE REFERENCE RUN'S OWN RECORDED argv, with only the destination
# changed. It is not retyped from a stage script and not reconstructed from documentation - on
# 2026-09-06 both of those produced a job that sealed FAILED for a difference that was the job's
# and not the tool's.
#
# THE PREDICTION, WRITTEN BEFORE SUBMISSION:
{prediction}
#
# THE CHECKOUT IS FROZEN. The tool is expected at {tool_commit}. If it has moved when this job
# starts, the job refuses rather than measuring a mixture of two versions. Twice on 2026-09-06 a
# pull landed in a live checkout; the rule existed and nothing enforced it, which is a prediction
# rather than a guardrail.
#
# rule-one: no-removal - this job reads inputs and writes only inside its own run directory.
# Authored off-cluster and pushed (rule H1). No `git` command runs below.
#
{queue_note}
set -euo pipefail

RUNDIR="{rundir}"
TOOLDIR="{tooldir}"
EXPECT_COMMIT="{tool_commit}"
mkdir -p "$RUNDIR/logs"

# ---------------------------------------------------------------- seal, whatever happens next
finish() {{ s=$?
  set +e
  missing=""
  for p in {products}; do
    [ -s "$RUNDIR/$p" ] || missing="$missing $p"
  done
  # A SEAL THAT SAYS FAILED MUST EXIT NON-ZERO. Otherwise the scheduler records success while
  # the directory records failure, and whichever one a reader happens to look at is the answer.
  if [ "$s" -eq 0 ] && [ -z "$missing" ]; then
    seal="$RUNDIR/SEALED.txt"
  else
    seal="$RUNDIR/FAILED.txt"
    [ "$s" -eq 0 ] && s=1
  fi
  {{ echo "exit=$s"
     echo "jobid=${{PBS_JOBID:-none}}"
     echo "host=$(hostname -s)"
     echo "finished=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
     echo "reference={ref}"
     echo "tool_commit_expected=$EXPECT_COMMIT"
     echo "tool_commit_actual=${{ACTUAL_COMMIT:-unread}}"
     [ -n "$missing" ] && echo "missing=$missing"
     echo "products_expected={n_products}"
  }} > "$seal"
  rm -f "$RUNDIR/RUNNING.txt"
  exit $s
}}
trap 'exit 143' TERM INT HUP   # a killed job seals FAILED, not SEALED (harness ADR-0022)
trap finish EXIT

{{ echo "started=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "jobid=${{PBS_JOBID:-none}}"
  echo "host=$(hostname -s)"
}} > "$RUNDIR/RUNNING.txt"

# ---------------------------------------------------------- the checkout has not moved under us
# Read by FILE: compute nodes on this cluster have no git binary. A function with `local`
# declarations rather than a multi-line command substitution - the substitution form tripped
# `set -u` on its own internals, so the guard exited the script before it could compare anything
# and the job sealed on the products alone. A guard that fails open is worse than no guard,
# because the header claims it ran.
read_commit() {{
  local gd="$1/.git" head_ ref_
  # A TREE EXPORTED WITHOUT .git CARRIES HEAD.txt - read that first (harness ADR-0019).
  if [ ! -e "$gd" ] && [ -f "$1/HEAD.txt" ]; then cut -d' ' -f1 "$1/HEAD.txt"; return 0; fi
  if [ -f "$gd" ]; then gd="$(sed 's/^gitdir: //' "$gd")"; fi
  head_="$(cat "$gd/HEAD" 2>/dev/null || true)"
  case "$head_" in
    "")    return 1 ;;
    ref:*) ref_="${{head_#ref: }}"
           if [ -f "$gd/$ref_" ]; then cat "$gd/$ref_"
           else grep " $ref_\$" "$gd/packed-refs" 2>/dev/null | cut -d' ' -f1; fi ;;
    *)     printf '%s' "$head_" ;;
  esac
}}
ACTUAL_COMMIT="$(read_commit "$TOOLDIR" || true)"
[ -n "$ACTUAL_COMMIT" ] || {{ echo "REFUSED: cannot read a commit from $TOOLDIR/.git" >&2; exit 3; }}
echo "tool commit: $ACTUAL_COMMIT (expected $EXPECT_COMMIT)"
if [ "$ACTUAL_COMMIT" != "$EXPECT_COMMIT" ]; then
  echo "REFUSED: $TOOLDIR moved between submission and start." >&2
  echo "         expected $EXPECT_COMMIT, found $ACTUAL_COMMIT" >&2
  echo "         A run spanning two versions measures neither. Re-emit the job." >&2
  exit 3
fi

export PYTHONNOUSERSITE=1
# THE CODE THAT RUNS IS THE TREE THAT WAS VERIFIED (harness ADR-0019, blind 0006). The commit
# guard above reads the TREE; the interpreter resolves a module from wherever the package is
# installed - on one cluster, the full checkout beside a one-plugin export, so a nine-plugin
# resolver demanded an environment that did not exist (PBS 711058). The tree goes first on
# PYTHONPATH, and a module command is asked where its package imports from before it runs.
export PYTHONPATH="$TOOLDIR${{PYTHONPATH:+:$PYTHONPATH}}"
{import_guard}export XDG_CACHE_HOME="$RUNDIR/cache" MPLCONFIGDIR="$RUNDIR/cache/mpl"
export OMP_NUM_THREADS="${{NCPUS:-1}}" MKL_NUM_THREADS="${{NCPUS:-1}}" OPENBLAS_NUM_THREADS="${{NCPUS:-1}}"
mkdir -p "$RUNDIR/cache"
{env_lines}
echo "node: $(hostname -s)  cores: ${{NCPUS:-unset}}  started: $(date -u)"

# ------------------------------------------------------------------------------- the tool runs
# NOT PIPED, AND NOT TEED. `| tee` and `| tail` return the last command's status, which hid a
# refusal three times in this project; process substitution avoids that but can lose the tail of
# a log at exit. `#PBS -j oe` already captures both streams, so neither is needed here.
# `set -e` is lifted for exactly one line, so the code can be read and reported before the trap
# uses it - under `set -e` the script would leave before `rc` was ever assigned.
set +e
{command}
rc=$?
set -e
echo "tool exit: $rc"
[ "$rc" -eq 0 ] || exit "$rc"
# ------------------------------------------------------ what the repository says follows a run
# Declared in DEVPOINTS.yaml under `run.after` (harness ADR-0019); each line is one command. Its
# exit code is a VERDICT - `status` owing, `capacity --memory` refusing a declaration - which the
# maker reads from this log; it is not a failure of the run, whose seal reads the products.
{after_lines}
# ------------------------------------------------------------- the maker's status, for the record
{maker_lines}
[ "$rc" -eq 0 ] || exit "$rc"

echo "finished: $(date -u)"
"""


def emit(ref_dir, rundir, tooldir, *, prediction: str, queue: str, select: str,
         walltime: str = "04:00:00", name: str = "reproduce", title: str | None = None,
         env: dict | None = None, products: list | None = None, python: str | None = None,
         tool_commit: str | None = None, redraw: bool = False, after=(),
         maker_status=None) -> str:
    """The script text. Raises rather than guessing anything it cannot read.

    THE RERUN OF THE LOOP (harness ADR-0019): `python` prefixes a script argv; `tool_commit`
    is used where the tree is not readable here and the job verifies it at start; `redraw`
    leaves figures out of the expected products; `after` is what the repository declares
    follows a run (`run.after`); `maker_status=(plugin, point)` writes the maker's status of
    the new run into its logs."""
    from ..conform import run_record
    if not prediction or not prediction.strip():
        raise ValueError(
            "a reproduction without a prediction is a measurement looking for a story. Say, "
            "before the job runs, what each output should do and what a difference would mean.")
    if not queue:
        raise ValueError("name the queue. A host pin in the wrong queue fails as "
                         "'Insufficient amount of resource: host', which reads like a missing node.")
    rec = run_record(ref_dir)
    prods = products if products is not None else products_of(ref_dir, figures=not redraw)
    if not prods:
        raise ValueError(f"{ref_dir} has no products to expect; a job that checks for nothing "
                         f"seals SEALED whatever happens.")
    argv = rebuild_argv(rec, rundir, python=python, tooldir=tooldir)
    given = bool(tool_commit)
    tool_commit = tool_commit or commit_of(tooldir)
    if not tool_commit:
        raise ValueError(f"cannot read a commit from {tooldir}/.git or HEAD.txt - the checkout "
                         f"cannot be frozen, and an unfrozen checkout is how two versions end up "
                         f"in one measurement. Give it with --tool-commit where the tree is not "
                         f"readable here; the job reads the tree's own at start.")
    commit_note = (f"# THE COMMIT WAS GIVEN, NOT READ: the tree at {tooldir} is not readable where "
                   f"this was written. The job reads the tree's own HEAD.txt or .git at start "
                   f"and refuses a mismatch.\n#\n" if given else "")
    redraw_note = ("# A REDRAW: figures are not expected products. The plan's promise "
                   "(`capacity --promised`) and the eye judge them.\n#\n" if redraw else "")
    fill_ = {"python": python or "python3", "run": str(rundir), "root": str(tooldir)}

    def _fill(a):
        for k, v in fill_.items():
            a = str(a).replace("{" + k + "}", v)
        return a
    # THE IMPORT GUARD, when the command is a module: the package it names must import from
    # the verified tree, compared by real path, or the job refuses before the tool runs.
    import_guard = ""
    if len(argv) > 2 and argv[1] == "-m":
        _pkg = str(argv[2]).split(".")[0]
        _py = shlex.quote(str(argv[0]))
        import_guard = (
            f'IMPORTED="$({_py} -c \'import importlib, os, sys; m = importlib.import_module('
            f'sys.argv[1]); print(os.path.realpath(os.path.dirname(os.path.dirname('
            f'os.path.abspath(m.__file__)))))\' {shlex.quote(_pkg)})"\n'
            f'TOOLREAL="$(cd "$TOOLDIR" && pwd -P)"\n'
            f'case "$IMPORTED" in\n'
            f'  "$TOOLREAL"|"$TOOLREAL"/*) echo "tool code: {_pkg} imports from $IMPORTED" ;;\n'
            f'  *) echo "REFUSED: {_pkg} imports from $IMPORTED, not from the verified tree '
            f'$TOOLDIR. The tree was checked and something else would have run." >&2; exit 3 ;;\n'
            f'esac\n')
    after_lines = "\n".join(
        " ".join(shlex.quote(_fill(x)) for x in cmd)
        + f' && echo "after: exit 0 - {_name}" || echo "after: exit $? - {_name}"'
        for cmd in (after or ()) for _name in [shlex.quote(" ".join(str(x) for x in cmd[1:]))])
    maker_lines = ""
    if maker_status:
        _pl, _pt = maker_status
        maker_lines = ('HARNESS="${HARNESS:-$HOME/tools/single-cell-harness}"\n'
                       f'PYTHONPATH="$HARNESS" {shlex.quote(python or "python3")} -m sch dev '
                       f'convert status --root {shlex.quote(str(tooldir))} --point '
                       f'{shlex.quote(str(_pt))} --name {shlex.quote(str(_pl))} --run "$RUNDIR" '
                       f'> "$RUNDIR/logs/maker_status.txt" 2>&1 || true\n'
                       f'tail -30 "$RUNDIR/logs/maker_status.txt"')
    host_note = ""
    if "host=" in select:
        host = select.split("host=", 1)[1].split(":")[0]
        host_note = (f"# QUEUE/HOST: this job pins {host}. That pin only works in a queue whose node\n"
                     f"# pool contains it; elsewhere PBS says \"Can Never Run: Insufficient amount of\n"
                     f"# resource: host ({host})\" while the node sits idle. Pin in the queue the run\n"
                     f"# being reproduced actually used.\n#\n")
    return HEADER.format(
        name=name, queue=queue, select=select, walltime=walltime,
        title=title or f"REPRODUCE {Path(ref_dir).name} AT {tool_commit[:7]}",
        when=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        # THE REFERENCE BY ITS KEY, NOT BY WHERE IT WAS READ: a replay's scratch path means
        # nothing where the job runs and is the leak shape the site contract refuses.
        ref=Path(ref_dir).name, ref_commit=rec.get("commit") or "unrecorded",
        ref_status=rec.get("status") or "unrecorded",
        ref_sv=rec.get("state_version") if rec.get("state_version") is not None else "unrecorded",
        ref_sources=", ".join(rec.get("sources") or ["none"]),
        prediction="\n".join(f"#   {ln}" for ln in prediction.strip().splitlines()),
        tool_commit=tool_commit, rundir=rundir, tooldir=tooldir,
        products=" ".join(shlex.quote(p) for p in prods), n_products=len(prods),
        queue_note=host_note + commit_note + redraw_note,
        env_lines="\n".join(f'export {k}={shlex.quote(str(v))}' for k, v in (env or {}).items()),
        command=" ".join(shlex.quote(a) for a in argv),
        after_lines=after_lines, maker_lines=maker_lines, import_guard=import_guard)


def write(path, **kw) -> dict:
    text = emit(**kw)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    os.chmod(p, 0o755)
    from ..conform import run_record
    rec = run_record(kw["ref_dir"])
    return {"path": str(p), "reference": kw["ref_dir"], "argv_source": "reference run record",
            # THE SUMMARY SAYS WHAT THE JOB SAYS: the commit it was given where the tree is not
            # readable here, and the products it expects - without the figures on a redraw.
            "ref_commit": rec.get("commit"),
            "tool_commit": kw.get("tool_commit") or commit_of(kw["tooldir"]),
            "products": len(kw.get("products")
                            or products_of(kw["ref_dir"], figures=not kw.get("redraw"))),
            "submit": f"qsub -q {kw['queue']} -o {kw['rundir']}/logs/pbs.log {p}"}
