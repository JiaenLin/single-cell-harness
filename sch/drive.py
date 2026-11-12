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
refusal, quoted. A choice a tool declares as the user's (`decisions:` in its plugin.yml, each naming
the escape its tool's `describe` declares) is never answered here and never a plain param: the run
stops before that stage, naming it, and resumes from the answer, recorded with who gave it; an
escape that lifts one of the tool's refusals (`unanswered: tool-default`) does not stop the run -
unanswered, its flag is not passed, the tool's own default, and the stage's events say so.
A run is its request and EXACTLY THE FILES DECLARED FOR IT (`declared`, autodev W056 design read D6): by the
request's schema (the request, its samplesheet and the column naming each library's object, the design, an
adapter the harness does not ship), by the site's (its stack layer, the harness's own code) and by each adapter's
`files:` (each param of its tool that names a file, a folder or its checkout, and the columns or keys of a file it
names that its tool opens). Any other string is text, never opened or refused for its look. `run_inputs` walks that
set (every file under a folder named, links followed): the set is recomputed and compared at the plan, at
each stage's start and its seal, and on a resume for every sealed stage, and a generated job carries
it and checks it with the run's answers; a seal is trusted only on the run's own record, and a seal
that record names is never missing (the sealed stages are the first, in order). What may have run
upstream of an assay is what the first stage's tool accepts there (its adapter's `upstream_accepts:`);
rule 2 over it is read from the profile this harness ships, and every place a step is declared must agree.

Nothing about a cohort or a site is here. The request is data that lives with the cohort; this
module holds its schema (FIELDS) and `docs/request.example.yml` a synthetic example.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import time
import unicodedata
from pathlib import Path

from . import yamlish

SCHEMA = 1
#: What a request holds, and nothing else: a misspelt field is a missing one that looks present.
FIELDS = {
    "request": "the schema version, 1",
    "observations": "the samplesheet: one row per library, a parts manifest (relative to the request); or, "
                    "with `object:`, ONE .h5ad holding every library",
    "parts": "the samplesheet's column naming each library's object (with `object:`, the column of the "
             "samplesheet the parts step writes)",
    "keys": "the profile's roles -> the samplesheet's and design's column names; `sample` (the library) is "
            "required; `replicate`, the unit the design sheet is keyed on, is required with `object:` and "
            "is the library when not declared",
    "object": "observations is one object holding every library: {counts: the slot holding the integer "
              "counts (X, raw/X or layers/<name>), symbols: the column of that slot's genes naming each "
              "gene's symbol, carry: [further obs columns carried into every part], chunk_values: the "
              "most stored values the step holds at once}; keys.sample and keys.replicate are obs columns",
    "design": "the design sheet (relative to the request)",
    "context": "what the dataset is, declared once: profile axes (assay, species, tissue, ...)",
    "upstream": "the steps the family does not perform, each by name: alignment and ambient",
    "stages": "in order, each {plugin, params}: params are the tool's own flags, verbatim",
    "resources": "the cohort's sizes, for the driver and per stage: {drive|<stage>: {ncpus, mem, walltime}}; "
                 "the queue is the site's, chosen from these by the site file's pbs.queues",
}
REQUIRED = ("request", "observations", "parts", "keys", "context", "upstream", "stages")
#: THE FILES A DRIVEN RUN DEPENDS ON ARE EXACTLY THE FILES DECLARED FOR IT (autodev W056, design read D6; ARCHITECTURE
#: C2, dependencies are declared, never discovered): by the request's schema and the site's (DECLARED) and by each
#: stage adapter's `files:` (PLUGIN_FORMAT) - {param: {kind, check, list, names}}, and `observations: {names}` for the
#: samplesheet's columns its tool opens. A string nothing declares is TEXT, whatever it looks like: never resolved,
#: looked up, opened, pinned or refused for its look. `declared()` is the one place; `run_inputs` walks it.
KINDS = ("file", "dir", "path", "checkout")       # `path`: a file or a folder, as found; `checkout`: a tool's own code
CHECKS = ("pinned", "present", "named")           # its digest compared | there and readable | recorded as its text
ENTRY = ("kind", "check", "list", "names")
READER = ("format", "at", "relative_to", "each")  # which columns (by header) or key paths ([*]: every element) name
FORMATS = ("table", "json", "yaml")               # files, and from where a relative one is read
RELATIVE = ("file", "none")                       # beside the file naming it | its tool's working directory: refused
DECLARED = {
    "request": "the request's schema: the request, a file",
    "observations": "the request's schema: the samplesheet, a file (with object:, the one .h5ad); its parts column "
                    "names each library's object, beside the sheet, as the stack reads it (services/dataset.py)",
    "design": "the request's schema: the design sheet, a file",
    "<stage>.plugin": "the request's schema: a stage's adapter the harness does not ship, a folder (its code too)",
    "site.stack.yml": "the site's schema: the layer beneath every stage's stack, a file; no leaf of it is followed",
    "harness": "the site's schema: the harness's own code, a checkout (its sch/ and plugins/)",
}
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
JOB_SITE = ("harness", "python", "runs", "setup", "submit", "commit_file")
#: A GENERATED JOB NEVER RUNS GIT WHERE IT RUNS (autodev W056 fix 1, R0): what needs git - a checkout at the commit
#: the job expects, with no tracked change - is read by the job's SUBMIT recipe where it is submitted, by its own
#: shell lines and git (RECIPE_PROGRAMS: no python runs there), into the run folder as CHECKOUTS; the job refuses that
#: record missing, changed after submission (its sha256 passes with qsub -v), about another run or job, or naming
#: another commit. Where the job runs it compares what needs no git: the file every checkout carries holding its
#: commit, when the site declares one (job.yml `commit_file`, a site fact). A site declaring none: each such check is
#: said as not made, and why. The record is one line a field or a checkout, its fields separated by a TAB (the
#: recipe refuses a value holding a TAB or a newline before it writes one): `record sch-checkouts-1`, `rundir`, `job`,
#: `pins` (the job's pins digest), `commit_file` (`-`: none), `made_at`, then `checkout ROLE TOP COMMIT TRACKED
#: COMMIT_FILE` for the harness (ROLE `harness`) and each tool - COMMIT a commit, `-` (not a git checkout) or
#: `absent`; TRACKED the digest of its tracked changes as `_git_state` reads them, `clean` for none (`-` outside git);
#: COMMIT_FILE the file's content, `-` where the site declares none.
CHECKOUTS = "CHECKOUTS.tsv"
RECORD = "sch-checkouts-1"
#: What a site's job.yml must declare; the rest is optional.
JOB_REQUIRED = ("harness", "python", "runs")
#: An upstream step is its tool's name and its version, nothing else (autodev W042 fix 2, A): a command
#: line, a `ran` flag or a note is free text no rule can read, so it is not accepted.
STEP_FIELDS = ("tool", "version")
#: A release number, as an upstream step's `version` is written: digits and dots, a leading `v`, and a
#: pre- or post-release tag of the usual kinds. A name, a command or a sentence is not a version.
VERSION = re.compile(r"v?\d+(\.\d+)*([a-z]|[._-]?(a|b|c|rc|alpha|beta|dev|post|p)\d+|[._-]?(alpha|beta|dev|post|rc))?",
                     re.I)
#: A stage's name, a job's stage directory and its purpose: each is written into the generated job as it
#: is (a path, the run key, a shell line), so each is a plain word (autodev W042 fix 2, ATTACKS 6).
STAGE_WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*", re.ASCII)
#: The answers to the user's decision on a step the profile asks about (`ask_when_delivered`, D-031).
ASK_VALUES = ("accept", "decline")
#: THE RUN'S INPUTS (autodev W042 fix 2, B), named limits, each said in the run's record. A file larger
#: than HASH_LIMIT bytes is not hashed at every step: its size, modification time and the sha256 of its
#: first and last SAMPLE bytes are recorded instead. A named directory holding more than TREE_LIMIT
#: files is recorded as unpinned. A walk leaves out what EXCLUDED names.
HASH_LIMIT = 1 << 30
SAMPLE = 1 << 20
TREE_LIMIT = 5000
EXCLUDED = {".git": "a checkout's history, not what its tool reads (its work tree is hashed)",
            "__pycache__": "the interpreter's compiled cache, written when a tool runs",
            "*.pyc": "the same cache, as single files"}
#: An upstream step's tool is one plain name (autodev W049): printable ASCII once NFKC has folded it, so no
#: zero-width, control or look-alike character can make two names read as one; a command, a note or a
#: second tool joined by `;` or a newline is not a name.
TOOL_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9 ._+|/()-]{0,79}", re.ASCII)
#: What an adapter's `upstream_columns:` says of a step (PLUGIN_FORMAT): the column naming its tool and the
#: one naming its release, and the columns saying it was performed or declined (each a list: True).
COLUMN_FIELDS = {"tool": False, "version": False, "performed": True, "declined": True}
#: What a tool accepts upstream when its declaration names no list: any plain name (autodev W049).
ANY = "any"
POLICY = {"hash_limit_bytes": HASH_LIMIT, "sample_bytes": SAMPLE, "tree_limit_files": TREE_LIMIT,
          "excluded": EXCLUDED, "declared": "the request's schema, the site's and each stage adapter's files:",
          "open": "a file over the hash limit is compared by size, modification time and its first and last "
                  "bytes, so an edit of its middle that keeps its size and modification time is not seen; a "
                  "directory over the tree limit is not compared at all; a change made and undone while one "
                  "stage's tool runs, between that stage's start and its seal, is seen only if the tool records "
                  "what it read; the set is what is declared: a file a tool opens that no declaration names (an "
                  "environment variable, a default outside its checkout, a file derived from a named one, a child "
                  "process's reads) is not in it, and a value no declaration names is text, never opened; a "
                  "`present` input is there and readable, its content not compared; a `named` one is its text; a "
                  "git checkout (the harness, a tool's) is its commit and its tracked changes, not its untracked "
                  "files; records rewritten consistently everywhere are not told from true ones (no signature)"}
#: ONE OBJECT HOLDING EVERY LIBRARY (harness W045, GAP-C90): what `object:` declares, and what it must.
OBJECT_FIELDS = ("counts", "symbols", "carry", "chunk_values")
OBJECT_REQUIRED = ("counts", "symbols")
#: The harness's own step that writes an object's per-library parts: stage 00 of such a request.
STEP = "parts"
#: The samplesheet column the parts step names each library by besides keys.sample (its SHEET_LIBRARY).
SHEET_LIBRARY = "sample"


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


def _word(v) -> str:
    """A name as a profile's list is compared with it: NFKC, trimmed, case-folded, and spaces, `_` and
    `-` folded away, so `Cell Ranger` is `cellranger`. Nothing else is folded: any other character keeps
    the name off every list."""
    return re.sub(r"[\s_-]+", "", unicodedata.normalize("NFKC", str(v)).strip().casefold())


def _key(k) -> str:
    """A parameter's name as its tool's parser reads it: `no-exclude` and `No_Exclude` are `no_exclude`."""
    return str(k).strip().casefold().replace("-", "_")


def _has(params: dict, path: str) -> list:
    """The spellings under which `params` sets the parameter `path` (`cmd.flag` or `flag`)."""
    head, _, rest = str(path).partition(".")
    tops = [k for k in params if _key(k) == _key(head)]
    if not rest:
        return [k for k in tops if params[k] is not None and params[k] is not False]
    return [f"{t}.{k}" for t in tops for k, v in dict(params[t] or {}).items()
            if _key(k) == _key(rest) and v is not None and v is not False]


def _keys(v, path: str = ""):
    """(path, key) of every key of a params mapping, at every depth."""
    if isinstance(v, dict):
        for k, x in v.items():
            here = f"{path}.{k}" if path else str(k)
            yield here, k
            yield from _keys(x, here)


def _entry(p: Path) -> dict:
    """One file as the run's record holds it: its sha256, or, over HASH_LIMIT, a sample (said)."""
    st = p.stat()
    if st.st_size <= HASH_LIMIT:
        return {"path": str(p), "sha256": _sha(p)}
    with open(p, "rb") as fh:
        head = hashlib.sha256(fh.read(SAMPLE)).hexdigest()
        fh.seek(max(0, st.st_size - SAMPLE))
        tail = hashlib.sha256(fh.read(SAMPLE)).hexdigest()
    return {"path": str(p), "sampled": {"size": st.st_size, "mtime_ns": st.st_mtime_ns, "head": head,
                                        "tail": tail},
            "why": f"larger than HASH_LIMIT ({HASH_LIMIT} bytes): not hashed at every step"}


def _add(files: dict, role: str, p: Path):
    """A named path into the set: a file, every file under a directory (walked sorted, EXCLUDED left
    out), or the path as absent - so a file that appears later is a change too."""
    try:
        if p.is_file():
            files[role] = _entry(p)
            return
    except OSError as e:                         # said, and compared as such: the tool cannot read it either
        files[role] = {"path": str(p), "unreadable": f"{type(e).__name__}: {e}"}
        return
    if not p.is_dir():
        files[role] = {"path": str(p), "absent": True}
        return
    found = _walk(p, {os.path.realpath(p)})
    if found is None:
        files[role] = {"path": str(p), "unpinned": f"more than TREE_LIMIT ({TREE_LIMIT}) files: not "
                                                   f"hashed at every step"}
        return
    files[role] = {"path": str(p), "dir": len(found)}
    for f in found:
        if isinstance(f, tuple):                 # a loop, or a linked subtree given up: the link, its target
            link, real, kind = f
            files[f"{role}/{link.relative_to(p).as_posix()}"] = {"path": str(link), "loop": real} if kind == "loop" \
                else {"path": str(link), "target": real, "unpinned": f"a link to a directory of more than TREE_LIMIT "
                      f"({TREE_LIMIT}) files: this link alone is not hashed at every step"}
            continue
        rel = f.relative_to(p).as_posix()
        try:
            files[f"{role}/{rel}"] = _entry(f) if f.is_file() else {"path": str(f), "absent": True}
        except OSError as e:
            files[f"{role}/{rel}"] = {"path": str(f), "unreadable": f"{type(e).__name__}: {e}"}


def _walk(top: Path, seen: set):
    """The files under a directory, walked sorted (EXCLUDED left out), or None over TREE_LIMIT of its own.
    A LINKED DIRECTORY IS WALKED TOO (autodev W049, route 5): what a tool reads through a link is a file it
    reads. Each directory is walked once, by its real path; a link back to one already walked is a loop,
    kept as `(link, target, "loop")`, so retargeting it is a change. A linked directory is its own subtree
    with its own limit (W049 fix 1): over it, only that link is given up, kept as `(link, target,
    "unpinned")`, and the files of the directory that holds it are still compared."""
    found, own = [], 0
    for root, dirs, names in os.walk(top):
        keep = []
        for d in sorted(x for x in dirs if x not in EXCLUDED):
            full = Path(root) / d
            real = os.path.realpath(full)
            if real in seen:
                found.append((full, real, "loop"))
                continue
            seen.add(real)
            if full.is_symlink():
                sub = _walk(full, seen)
                found += sub if sub is not None else [(full, real, "unpinned")]
            else:
                keep.append(d)
        dirs[:] = keep
        here = [Path(root) / n for n in sorted(names) if not n.endswith(".pyc")]
        found, own = found + here, own + len(here)
        if own > TREE_LIMIT:
            return None
    return found


def _git_state(d: Path, pathspec=()) -> dict | None:
    """A git work tree as the set holds it (autodev W049, routes 10 and 14): its top, its commit and a
    digest of its tracked changes against that commit (limited to `pathspec`); None outside one. Read
    with no optional lock, so two jobs reading one checkout never collide on its index."""
    import subprocess

    def g(*a):                                   # what the work tree holds, not what git is told to see:
        # no replace objects, no fsmonitor, and a file's change of status time read as a change, whatever the
        # checkout's own config says (a same-size, same-mtime edit is otherwise clean; autodev W049 fix 1)
        r = subprocess.run(["git", "--no-optional-locks", "--no-replace-objects", "-c", "core.fsmonitor=false",
                            "-c", "core.trustctime=true", "-c", "core.checkStat=default", "-C", str(d), *a],
                           capture_output=True, timeout=120)
        return r.stdout if r.returncode == 0 else None
    try:
        top, head = g("rev-parse", "--show-toplevel"), g("rev-parse", "HEAD")
        if not top or not head:
            return None
        spec = ["--", *pathspec] if pathspec else []
        st = g("status", "--porcelain=v1", "--untracked-files=no", *spec)
        diff = g("diff", "--binary", "HEAD", *spec)
        flags = g("ls-files", "-v", *spec)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if st is None or diff is None or flags is None:
        return None
    # A FILE GIT IS TOLD NOT TO LOOK AT (autodev W049 fix 1, ATTACKS 22): assume-unchanged (a lower-case tag)
    # and skip-worktree (`S`) hide a changed file from status and diff, so they are its state too
    hidden = b"\n".join(x for x in flags.splitlines() if x[:1].islower() or x[:1] == b"S")
    return {"path": top.decode().strip(), "git": head.decode().strip(),
            "tracked_changes": hashlib.sha256(st + b"\0" + diff + (b"\0" + hidden if hidden else b"")).hexdigest()}


#: A git work tree with no tracked change, as `_git_state` digests it: what a job that states a tool's commit
#: expects where it runs (autodev W049 fix 1).
CLEAN = hashlib.sha256(b"\0").hexdigest()


def _checkout_dirs(req: dict) -> dict:
    """{`<stage>.<param>@checkout`: (the path a param declared `kind: checkout` names, the directory read as its
    checkout)} - the declaration, by the role names `tool_param` had (autodev W056, design read D6)."""
    return {role: (got, got if got.is_dir() else got.parent) for _p, _x, role, _v, got in _checkouts(req)}


def _checkout_state(got: Path, d: Path) -> dict:
    """A tool's checkout as the set holds it: recorded absent, never dropped (autodev W049 fix 1); its git state; or,
    outside git, its files' digest."""
    if not got.exists():
        return {"path": str(got), "absent": True}
    return _git_state(d) or _nogit_state(got, d)


def _nogit_state(got: Path, d: Path) -> dict:
    """A tool's checkout outside git, read with no git (where it is generated, or where a job runs, autodev W056 fix
    1): its files' digest, or, when the param names the directory itself, that directory walked as the param's."""
    return ({"path": str(d), "git": None, "tracked_changes": _tree_digest(d)} if got.is_file() else
            {"path": str(d), "git": None, "tracked_changes": "the directory itself, walked as the param"})


# ---------------------------------------------------------------------------- what a run depends on, declared
def _entry_ok(e, where: str, sheet: bool = False):
    """One `files:` entry, or a reader's `each`, checked by name (autodev W056, design read D6)."""
    if not isinstance(e, dict):
        raise RequestError(f"{where} is not a mapping of " + ("names (its reader)" if sheet else ", ".join(ENTRY)))
    bad = sorted(set(map(str, e)) - ({"names"} if sheet else set(ENTRY)))
    if bad:
        raise RequestError(f"{where}: {', '.join(bad)} is not a word of " + (
            "the samplesheet's entry (names: its reader)" if sheet else f"a files: entry ({', '.join(ENTRY)})"))
    if not sheet:
        kind, check = str(e.get("kind")), str(e.get("check") or "pinned")
        if kind not in KINDS:
            raise RequestError(f"{where}: kind {e.get('kind')!r} is not one of {', '.join(KINDS)}")
        if check not in CHECKS:
            raise RequestError(f"{where}: check {e.get('check')!r} is not one of {', '.join(CHECKS)}")
        if e.get("list") is not None and not (isinstance(e["list"], str) and len(e["list"]) == 1):
            raise RequestError(f"{where}: list {e['list']!r} is not the one character joining several paths")
        if e.get("names") is not None and kind != "file":
            raise RequestError(f"{where}: names: reads the paths a file names, and a {kind} is not one")
        if kind == "checkout" and (e.get("list") is not None or check != "pinned"):
            raise RequestError(f"{where}: a checkout is its commit and its tracked changes: no check, list or names")
    if e.get("names") is not None:
        _reader_ok(e["names"], f"{where}.names")


def _reader_ok(r, where: str):
    """A reader, checked by name (autodev W056, D6): {format, at, relative_to, each}, each word declared."""
    if not isinstance(r, dict):
        raise RequestError(f"{where} is not a reader ({', '.join(READER)})")
    bad = sorted(set(map(str, r)) - set(READER))
    absent = [k for k in READER if r.get(k) in (None, "", [], {})]
    if bad or absent:
        raise RequestError(f"{where}: " + (f"{', '.join(bad)} is not a word of a reader" if bad else
                                           f"declares no {', '.join(absent)}") + f" ({', '.join(READER)})")
    if str(r["format"]) not in FORMATS:
        raise RequestError(f"{where}: format {r['format']!r} is not one of {', '.join(FORMATS)}")
    if not isinstance(r["at"], list) or not all(isinstance(x, str) and x for x in r["at"]):
        raise RequestError(f"{where}: at: is not a list of columns (by their header) or key paths")
    if str(r["relative_to"]) not in RELATIVE:
        raise RequestError(f"{where}: relative_to {r['relative_to']!r} is not one of {', '.join(RELATIVE)}")
    _entry_ok(r["each"], f"{where}.each")


def _decl(m) -> dict:
    """A stage adapter's `files:` (autodev W056, D6), refused by name when it is missing (`{}` is a statement, a missing
    key is not), holds a word no declaration has, or declares a param the adapter sets itself (its `owned:`)."""
    f = m.data.get("files")
    if f is None:
        raise RequestError(f"{m.name} declares no files: - each param of its tool that names a file, a folder or its "
                           f"checkout, {{kind, check, list, names}}, and observations: {{names: <reader>}} for the "
                           f"samplesheet's columns its tool opens (PLUGIN_FORMAT); `files: {{}}` when none. What a run "
                           f"depends on is what is declared, never guessed from how a value looks")
    if not isinstance(f, dict):
        raise RequestError(f"{m.name}: files: is not a mapping of params")
    owned = {_key(x) for x in m.data.get("owned") or []}
    for param, e in f.items():
        if _key(param) in owned:
            raise RequestError(f"{m.name}: files.{param}: {param} is a flag {m.name} sets itself (its owned:): what "
                               f"it names is the stack's, not the request's")
        _entry_ok(e, f"{m.name}: files.{param}", str(param) == "observations")
    return {str(k): v for k, v in f.items()}


def _param(params: dict, path: str) -> tuple:
    """(True, its value) where a stage's params set the param `path` (`flag` or `cmd.flag`), else (False, None)."""
    head, _, rest = str(path).partition(".")
    if head not in params:
        return False, None
    if not rest:
        return True, params[head]
    block = params[head]
    return (True, block[rest]) if isinstance(block, dict) and rest in block else (False, None)


def _values(v, e: dict, what: str, base: Path | None = None) -> list:
    """The paths ONE DECLARED value names (autodev W056, D6): it is text - one path, or each piece where its entry
    declares `list` - absolute or `~/` (the running user's home); a relative one is read beside the file naming it
    where its reader says `relative_to: file` (`base`), and refused by name otherwise: its tool reads it from its own
    working directory, where nothing the set holds is. None, false or empty names nothing."""
    if v is None or v is False or v == "":
        return []
    if not isinstance(v, str):
        raise RequestError(f"{what} is {v!r}, which is not text: it is declared a {e.get('kind') or 'file'} (its "
                           f"adapter's files:), so its value is one path" + (
                               f", or several joined by {e['list']!r}" if e.get("list") else ""))
    out = []
    for x in (v.split(e["list"]) if e.get("list") else [v]):
        if not x:
            continue
        if x.startswith("/"):
            out.append(Path(x))
        elif x.startswith("~/"):
            out.append(Path(os.path.expanduser(x)))
        elif base is not None and not _climbs(x):
            out.append(base / x)
        else:
            raise RequestError((f"{what}: {x!r} is a relative path" if what.startswith("--answer") else
                                f"{what} is {x!r}, a relative path") + (" out of its tool's working directory" if
                               _climbs(x) else "") + "; its tool reads it from its own working directory (the stage's "
                               "run directory), not from the request's, and what it names there would not be pinned: "
                               "write it absolute, or ~/")
    return out


def _cells(f: Path, r: dict) -> list:
    """[(at, where, value)] of a file's declared columns or keys, as its tool reads them (autodev W056, D6): a table by
    its header, exactly (the delimiter its suffix says, else its header's: a TAB or a comma; a byte-order mark, CRLF
    and a quoted cell holding a newline read as the csv module reads them), each row `<column>[<row>]`, a column it
    lacks an empty cell a row; a JSON or YAML document by its key paths (`[*]` for every element)."""
    if r["format"] == "table":
        text = f.read_text(encoding="utf-8-sig")
        sep = {".csv": ",", ".tsv": "\t", ".txt": "\t"}.get(f.suffix.lower())
        if sep is None:
            top = text.split("\n", 1)[0]
            sep = "\t" if top.count("\t") >= top.count(",") else ","
        rows = list(csv.reader(io.StringIO(text, newline=""), delimiter=sep))
        head = rows[0] if rows else []
        return [(a, f"{a}[{i}]", (row[head.index(a)] if head.index(a) < len(row) else "") if a in head else "")
                for a in r["at"] for i, row in enumerate(rows[1:], 1)]
    doc = json.loads(f.read_text(encoding="utf-8")) if r["format"] == "json" else yamlish.load(f)
    pats = [(a, re.compile(re.escape(a).replace(r"\[\*\]", r"\[\d+\]"))) for a in r["at"]]
    return [(a, w, v) for w, v in _leaves(doc) for a, pat in pats if pat.fullmatch(w)]


def _item(out: list, role: str, p: Path, e: dict, by: str) -> dict:
    """One declared input into `out`; a FILE whose entry names a reader is read for the inputs it names - only where it
    is a file, each by the reader's `each` (depth is what `names` nests, not a number)."""
    it = {"role": role, "path": str(p), "kind": str(e.get("kind") or "file"), "check": str(e.get("check") or "pinned"),
          "by": by}
    out.append(it)
    r = e.get("names")
    if r and it["check"] != "named" and p.is_file():
        it["read"] = _named_by(out, role, p, r, by)
    return it


def _named_by(out: list, role: str, f: Path, r: dict, by: str) -> list:
    """[(column or key, rows naming a file, rows, who declared it)] of a reader over the file `f`, each input it names
    into `out` as `<role>><column>[<row>]` or `<role>><key path>`: a misspelt column reads 0 of n."""
    try:
        got = _cells(f, r)
    except Exception as x:                       # noqa: BLE001 - not what it is declared to be: said, by name
        raise RequestError(f"{role} {f}: {by} reads it as a {r['format']} naming files ({', '.join(r['at'])}), and it "
                           f"does not read as one ({type(x).__name__}: {x})") from None
    base = f.parent if r["relative_to"] == "file" else None
    counts = {a: [0, 0] for a in r["at"]}
    for a, where, v in got:
        paths = _values(v, r["each"], f"{role} {f}: {where} ({by})", base)
        counts[a][0] += bool(paths)
        counts[a][1] += 1
        for j, p in enumerate(paths):
            _item(out, f"{role}>{where}" + (f"#{j}" if len(paths) > 1 else ""), p, r["each"], by)
    return [(a, k, n, by) for a, (k, n) in counts.items()]


def _sheet_cells(out: list, req: dict, sheet: Path, readers: list) -> list:
    """The request's samplesheet as the stack reads it (services/dataset.py read_manifest): each cell of a column a
    reader declares - the request's parts column, beside the sheet; the first stage's tool's columns, as its adapter
    declares them - as `observations.<column>[<library>]`. A column declared twice is one role, read the stricter way."""
    from .services.dataset import read_manifest
    try:
        _head, rows = read_manifest(sheet)
    except Exception:                            # noqa: BLE001 - the stack's own init says what is wrong
        return []
    cols: dict = {}
    for r, by in readers:
        for a in r["at"]:
            cols.setdefault(str(a), []).append((r, by))
    reads = []
    for col, decls in cols.items():
        base = sheet.parent if all(r["relative_to"] == "file" for r, _b in decls) else None
        each = {**decls[0][0]["each"], "check": min((str(r["each"].get("check") or "pinned") for r, _b in decls),
                                                    key=CHECKS.index),
                "names": next((r["each"]["names"] for r, _b in decls if r["each"].get("names")), None)}
        by, k = " and ".join(b for _r, b in decls), 0
        for i, row in enumerate(rows, 1):
            lib = str(row.get(req["keys"]["sample"]) or i).strip()
            paths = _values(row.get(col), each, f"observations {sheet}: {col}[{lib}] ({by})", base)
            k += bool(paths)
            for j, f in enumerate(paths):
                _item(out, f"observations.{col}[{lib}]" + (f"#{j}" if len(paths) > 1 else ""), f, each, by)
        reads.append((col, k, len(rows), by))
    return reads


def _checkouts(req: dict) -> list:
    """[(stage, param, `<stage>.<param>@checkout`, its value as the request writes it, its path)]: each param a stage's
    adapter declares `kind: checkout` - its tool's own code (autodev W056, D6; it was `tool_param`)."""
    out = []
    for p in req["stages"]:
        for param, e in (p.get("files") or {}).items():
            found, v = _param(p["params"], param) if (e or {}).get("kind") == "checkout" else (False, None)
            got = _values(v, e, f"{p['stage']} ({p['plugin']}): {param}") if found else []
            if got:
                out.append((p, param, f"{p['stage']}.{param}@checkout", str(v), got[0]))
    return out


def declared(req: dict, answers: dict | None = None) -> list:
    """THE ONE PLACE (autodev W056, design read D6): every input a driven run depends on, as declared, [{role, path,
    kind, check, by, read}] - by the request's schema and the site's (DECLARED) and by each stage adapter's `files:`,
    and nothing else: a string no declaration names is text. A file a declared reader names is read from the file
    naming it, so the roles inside it are a function of that file's pinned bytes and of the declaration. An answer is
    its decision's param's value, so that param's entry types it. Refused by name: a declared value that is not text,
    or relative where its reader resolves nothing beside a file."""
    out: list = []
    root = Path(__file__).resolve().parent.parent
    out.append({"role": "harness", "path": str(root), "kind": "checkout", "check": "pinned", "by": DECLARED["harness"]})
    _item(out, "request", Path(req["path"]), {"kind": "file"}, DECLARED["request"])
    sheet = Path(req["observations"])
    obs = _item(out, "observations", sheet, {"kind": "file"}, DECLARED["observations"])
    if req.get("design"):
        _item(out, "design", Path(req["design"]), {"kind": "file"}, DECLARED["design"])
    first = req["stages"][0] if req["stages"] else {}
    readers = [] if req.get("object") else [({"format": "table", "at": [str(req["parts"])], "relative_to": "file",
                                               "each": {"kind": "file"}}, "the request's schema (parts)")]
    mine = ((first.get("files") or {}).get("observations") or {}).get("names")
    if mine and readers and first.get("reads") == "libraries":
        readers.append((mine, f"{first['plugin']} files.observations"))
    if readers and sheet.is_file():
        obs["read"] = _sheet_cells(out, req, sheet, readers)
    shipped = (root / "plugins").resolve()
    for p in req["stages"]:
        d = Path(p["dir"]).resolve()
        if not str(d).startswith(str(shipped) + os.sep):
            _item(out, f"{p['stage']}.plugin", d, {"kind": "dir"}, DECLARED["<stage>.plugin"])
        decl = p.get("files") or {}
        for param, e in decl.items():
            found, v = _param(p["params"], param) if param != "observations" else (False, None)
            if not found:
                continue
            by = f"{p['plugin']} files.{param}"
            paths = _values(v, e, f"{p['stage']} ({p['plugin']}): {param}")
            if e.get("kind") == "checkout":
                for f in paths[:1]:              # the param's own file or folder, and the checkout holding it
                    _item(out, f"{p['stage']}.{param}", f, {"kind": "path"}, by)
                    out.append({"role": f"{p['stage']}.{param}@checkout", "path": str(f), "kind": "checkout",
                                "check": "pinned", "by": by})
                continue
            for j, f in enumerate(paths):
                _item(out, f"{p['stage']}.{param}" + (f"#{j}" if len(paths) > 1 else ""), f, e, by)
        for dd in p["decisions"]:
            if dd["name"] in (answers or {}) and dd["param"] in decl:
                a = answers[dd["name"]]
                e = decl[dd["param"]]
                paths = _values(a.get("value") if isinstance(a, dict) else a, e, f"--answer {dd['name']}")
                for j, f in enumerate(paths):
                    _item(out, f"answer[{dd['name']}]" + (f"#{j}" if len(paths) > 1 else ""), f, e,
                          f"{p['plugin']} files.{dd['param']} (the decision {dd['name']})")
    site = os.environ.get("SCH_SITE")
    if site:
        _item(out, "site.stack.yml", Path(site) / "stack.yml", {"kind": "file"}, DECLARED["site.stack.yml"])
    return out


def _present(p: Path) -> dict:
    """A `present` input (autodev W056, D6): there and readable - its content is not compared - or absent, or not."""
    try:
        if p.is_dir() or p.is_file():
            if os.access(p, os.R_OK | (os.X_OK if p.is_dir() else 0)):
                return {"path": str(p), "present": "folder" if p.is_dir() else "file"}
            return {"path": str(p), "unreadable": "PermissionError: not readable here"}
    except OSError as e:
        return {"path": str(p), "unreadable": f"{type(e).__name__}: {e}"}
    return {"path": str(p), "absent": True}


def run_inputs(req: dict, answers: dict | None = None, git: bool = True) -> dict:
    """THE SET OF FILES A RUN DEPENDS ON, {role: entry} (autodev W042 fix 2, B; W049; W056 design read D6): the walk over
    `declared()` and nothing else. A `pinned` input is its digest (a folder: every file under it, links followed, said
    over the tree limit), a `present` one whether it is there and reads, a checkout its commit and tracked changes
    (`git=False`, a generated job where it runs: no git is run there, and each checkout is the submit recipe's record,
    `expected`); a `named` one is its text, no role. ONE function, so the plan, each stage's start and seal, a resume and
    the generated job compare the same set the same way. The roles are the request's own words, the same on every
    machine; a path is where the file was found."""
    files: dict = {}
    root = Path(__file__).resolve().parent.parent
    for d in declared(req, answers):
        role, p = d["role"], Path(d["path"])
        if d["check"] == "named":
            continue
        if role == "harness":                    # route 10: its code, as it runs
            files[role] = (_git_state(root, ("sch", "plugins")) if git else None) or {
                "path": str(root), "git": None,
                "tracked_changes": _tree_digest(root / "sch") + _tree_digest(root / "plugins")}
        elif d["kind"] == "checkout":            # route 14: the checkout around the param naming its tool
            top = p if p.is_dir() else p.parent
            files[role] = _checkout_state(p, top) if git else (
                {"path": str(p), "absent": True} if not p.exists() else
                {"path": str(top), "git": None, "tracked_changes": "not read here: a generated job runs no git where it runs"})
        elif d["check"] == "present":
            files[role] = _present(p)
        else:
            _add(files, role, p)
    return files


def _tree_digest(d: Path) -> str:
    """A directory's files (sorted, EXCLUDED left out) as one digest: what stands for a checkout's state
    where git cannot say it. Over TREE_LIMIT files it is said, not hashed."""
    h, n = hashlib.sha256(), 0
    for r, dirs, names in os.walk(d):
        dirs[:] = sorted(x for x in dirs if x not in EXCLUDED)
        for x in sorted(names):
            if x.endswith(".pyc"):
                continue
            n += 1
            if n > TREE_LIMIT:
                return f"unpinned: more than TREE_LIMIT ({TREE_LIMIT}) files"
            f = Path(r) / x
            h.update(f.relative_to(d).as_posix().encode() + b"\0")
            h.update((_digest(_entry(f)) if f.is_file() else "absent").encode() + b"\n")
    return h.hexdigest()


def _digest(e: dict | None, mtime: bool = True) -> str | None:
    """One entry as compared: its hash, or what stands for one (said by its kind)."""
    if e is None:
        return None
    if e.get("sha256"):
        return e["sha256"]
    if e.get("sampled"):
        s = e["sampled"]
        return f"sampled:{s['size']}:{s['mtime_ns'] if mtime else '-'}:{s['head']}:{s['tail']}"
    if e.get("absent"):
        return "absent"
    if e.get("unpinned"):
        return "unpinned" + (f":{e['target']}" if e.get("target") else "")
    if e.get("unreadable"):
        return "unreadable"
    if e.get("present"):                         # there and readable: its content is not compared (W056, D6)
        return "present"
    if e.get("loop"):
        return f"loop:{e['loop']}"
    if "tracked_changes" in e:                   # a checkout: its commit and its tracked changes
        return f"git:{e.get('git')}:{e['tracked_changes']}"
    return f"dir:{e.get('dir')}"


def flat(files: dict, mtime: bool = True) -> dict:
    return {k: _digest(v, mtime) for k, v in files.items()}


def differ(then: dict, now: dict, here_only: bool = False) -> list:
    """[(role, then, now)] where two sets disagree, each a flat digest. `here_only` (a job checked where
    it runs): a role absent where the job was generated - or read from one that was: a file under a
    directory, a cell of a samplesheet (`observations.<column>[<library>]`) - is checked here for the
    first time, not a difference."""
    out = []
    for k in sorted(set(then) | set(now)):
        a, b = then.get(k), now.get(k)
        if a == b:
            continue
        if here_only and (a == "absent" or (a is None and any(
                then.get(k[:i]) == "absent" for i in range(len(k)) if k[i] in "/.>"))):
            continue
        out.append((k, a, b))
    return out


def said(diffs: list, paths: dict) -> str:
    def w(d):
        return "not named" if d is None else d if not re.fullmatch(r"[0-9a-f]{64}", d) else d[:12]
    return "; ".join(f"{k} {(paths.get(k) or {}).get('path', '')} ({w(a)} recorded, {w(b)} now)"
                     for k, a, b in diffs[:12]) + (f"; and {len(diffs) - 12} more" if len(diffs) > 12 else "")


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


def _shipped_profile(plan: list):
    """THE RULE IS THE HARNESS'S (autodev W042 fix 2, A): the profile every stage declares, read only
    from the file this harness ships for its id - never a path, never one a request or its plugin brings."""
    from .profile import HERE, known_profiles, load_profile
    ids = sorted({str(p["profile"]) for p in plan})
    for pid in ids:
        if pid.split("/")[0] not in known_profiles() or Path(pid).is_absolute() or pid.endswith((".yml", ".yaml")):
            raise RequestError(f"a stage's plugin declares the profile {pid!r}; rule 2 and the request's axes are read "
                               f"only from a profile this harness ships ({', '.join(known_profiles())}), by its id, "
                               f"never from a file a request or its plugin names")
    if len(ids) != 1:
        raise RequestError(f"the stages declare the profiles {', '.join(ids)}; one request is read under one profile")
    prof = load_profile(str(HERE / (ids[0].split("/")[0] + ".yml")))
    if not prof.accepts(ids[0]):
        raise RequestError(f"profile {ids[0]!r} is not served by {prof.id}")
    return prof


def _vword(v) -> str:
    return str(v).strip().casefold().lstrip("v")


def _family(prof_id: str, plan: list) -> list:
    """Every adapter of this profile the harness ships, and the request's own: (name, manifest data)."""
    out, seen = [], set()
    for f in sorted((Path(__file__).resolve().parent.parent / "plugins").glob("*/*/plugin.yml")):
        m = yamlish.load(f) or {}
        if str(m.get("profile", "")).split("/")[0] == prof_id.split("/")[0]:
            out.append((str(m.get("name")), m))
            seen.add(str(m.get("name")))
    out += [(p["plugin"], {"upstream_columns": p.get("upstream_columns"), "runs_upstream": p.get("runs_upstream")})
            for p in plan if p["plugin"] not in seen]
    return out


def _upstream(doc: dict, prof, assay: str, plan: list, keys: dict, where) -> tuple:
    """RULE 2 OVER WHAT THE STAGE-1 TOOL ACCEPTS (autodev W049; W042 fix 2, A): (upstream, the run's own
    decisions). What may have run upstream of an assay is what the first stage's tool accepts there (its
    adapter's `upstream_accepts:`, held by a drift test against the tool's own code), never a hand list.
    Over it, rule 2, the shipped profile's: on an assay where the family never performs a step
    (`never_performed`) a family tool's param that would perform it is refused, and libraries delivered
    with it performed (`ask_when_delivered`) - under any name, or a name carrying the tool the family
    runs only elsewhere - stop before stage 1 at the user's decision (D-031), never a silent pass. What
    the samplesheet says (every family adapter's `upstream_columns:`) must agree, whatever stage starts."""
    up = doc["upstream"]
    rule = dict(prof.data.get("upstream") or {})
    steps = [str(x) for x in rule.get("steps") or []]
    if not isinstance(up, dict):
        raise RequestError("upstream: is not a mapping of steps")
    stale = sorted({"never", "allowed", "ask"} & set(rule))
    if stale:
        raise RequestError(f"{prof.id}: upstream.{stale[0]} is not read; what may run upstream is what the first "
                           f"stage's tool accepts (its adapter's upstream_accepts:), and rule 2 is written as "
                           f"never_performed and ask_when_delivered")
    for step in steps:
        v = up.get(step)
        if not isinstance(v, dict) or v.get("tool") is None or not str(v.get("tool")).strip():
            raise RequestError(f"upstream: declares no {step}; name the tool that performed it, or "
                               f"`tool: none` - {step} is declared upstream, never inferred: "
                               f"upstream: {{{step}: {{tool: <name> | none, version: <its release>}}}}")
    other = sorted(set(map(str, up)) - set(steps))
    if other:
        raise RequestError(f"upstream: {', '.join(other)} is not an upstream step ({', '.join(steps)})")
    # the first stage that reads the libraries: with one object (W045) that is the stage after the harness's
    # own parts step, whose tool is the one that accepts or refuses what ran upstream (autodev W056, the merge)
    first = plan[1] if doc.get("object") and len(plan) > 1 and plan[0]["plugin"] == STEP else plan[0]
    accepts = (first.get("upstream_accepts") or {}).get(assay) if isinstance(first.get("upstream_accepts"), dict) \
        else None
    if first["reads"] != "libraries":            # the chain refuses it next, by name; nothing here is read
        accepts = {step: ANY for step in steps}
    if not isinstance(accepts, dict):
        raise RequestError(f"{first['plugin']} declares nothing of what its tool accepts upstream of {assay} "
                           f"(upstream_accepts.{assay}); nothing is allowed by silence")
    never = [str(x) for x in (rule.get("never_performed") or {}).get(assay) or []]
    ask = [str(x) for x in (rule.get("ask_when_delivered") or {}).get(assay) or []]
    family = _family(prof.id, plan)
    runs = {}                                    # step -> the tools the family runs it with (their own words)
    for _n, m in family:
        for step, entries in dict(m.get("runs_upstream") or {}).items():
            runs.setdefault(str(step), []).extend(str(e.get("tool")) for e in entries or [] if isinstance(e, dict))
    decisions, asked = [], {}
    for step in steps:
        v = up[step]
        extra = sorted(set(map(str, v)) - set(STEP_FIELDS))
        if extra:
            raise RequestError(f"upstream.{step}: {', '.join(extra)} is not a step field ({', '.join(STEP_FIELDS)}); "
                               f"what ran upstream is its tool's name and its release, and free text (a command "
                               f"line, a flag, a note) is not read, so it is not accepted")
        tool, ver = v["tool"], v.get("version")
        if not isinstance(tool, str) or not TOOL_NAME.fullmatch(unicodedata.normalize("NFKC", tool).strip()):
            raise RequestError(f"upstream.{step}.tool is {tool!r}; it is one tool's name, or none: printable "
                               f"letters, digits, spaces and . _ + | / ( ) -, nothing hidden and no second line")
        if ver is not None and (isinstance(ver, (bool, list, dict)) or not VERSION.fullmatch(str(ver).strip())):
            raise RequestError(f"upstream.{step}.version is {ver!r}, not a release number (digits and dots, as "
                               f"0.3.0 or v7.1.0); the tool is named in `tool`, once")
        none = _word(tool) == "none"
        if none and ver is not None:
            raise RequestError(f"upstream.{step}: tool none, version {ver!r}; a step nothing performed has no version")
        acc = accepts.get(step)
        if acc is None:
            raise RequestError(f"{first['plugin']} declares nothing of what its tool accepts as {step} upstream of "
                               f"{assay} (upstream_accepts.{assay}.{step}); nothing is allowed by silence")
        if not none and acc != ANY and _word(tool) not in map(_word, acc or []):
            raise RequestError(f"upstream: {step} by {tool!r} on {assay}: not a tool {first['plugin']}'s tool accepts "
                               f"there (upstream_accepts.{assay}.{step}: {', '.join(map(str, acc or [])) or 'nothing'})")
        # D-031: delivered performed where the family never performs it, or a name carrying a tool the
        # family runs for such a step - the user's decision, by name, whatever the spelling
        why = None
        if not none and step in ask:
            why = f"{step} already performed by {tool}{' ' + str(ver) if ver is not None else ''}"
        for o in never:
            hit = [t for t in runs.get(o) or [] if o != step and _word(t) and _word(t) in _word(tool)]
            if hit and o in ask:
                asked.setdefault(o, []).append(f"its {step} named {tool!r}, which carries {hit[0]}, a {o} tool "
                                               f"the family runs only where {prof.id} allows it")
        if why:
            asked.setdefault(step, []).insert(0, why)
    for step, whys in asked.items():
        decisions.append({"name": f"upstream.{step}", "param": None, "values": list(ASK_VALUES),
                          "unanswered": "stop", "step": step, "tool": up[step]["tool"],
                          "version": up[step].get("version"),
                          "what": f"this cohort's {assay} libraries arrive with " + "; and ".join(whys) + f": on "
                                  f"{assay} the family never performs {step} ({prof.id} never_performed; rule 2: a "
                                  f"remover calibrated on nuclei is not lent to cells) and asks whether to accept "
                                  f"libraries delivered so (ask_when_delivered, D-031): accept them for this run, "
                                  f"or decline"})
    for p in plan:                               # the family never performs a step where it may not
        for step, entries in (p.get("runs_upstream") or {}).items():
            for e in entries or []:
                got = _has(p["params"], str(e.get("param")))
                where_ok = assay in [str(x) for x in e.get("assays") or []] and str(step) not in never
                if got and not where_ok:
                    raise RequestError(f"{p['stage']} ({p['plugin']}): params set {got[0]}, with which its tool "
                                       f"performs {step} itself ({e.get('tool')}, run on "
                                       f"{', '.join(map(str, e.get('assays') or [])) or 'no assay'} by its own "
                                       f"policy); on {assay} the family never runs it (rule 2) - no decision lifts "
                                       f"this: drop it")
    if first["reads"] != "libraries":            # the chain refuses it next, by name
        return up, decisions
    cols, reads = {}, dict(first.get("upstream_columns") or {}) if isinstance(first.get("upstream_columns"), dict) \
        else None
    if reads is None:
        raise RequestError(f"{first['plugin']} reads the request's samplesheet and declares nothing of where it says "
                           f"what ran upstream (upstream_columns:, {{}} if nowhere); provenance is read from every "
                           f"place it can be declared")
    for _n, m in family:                         # every column a family tool reads as upstream provenance
        for step, c in dict(m.get("upstream_columns") or {}).items():
            got = cols.setdefault(str(step), {k: [] if many else None for k, many in COLUMN_FIELDS.items()})
            for k, many in COLUMN_FIELDS.items():
                v = (c or {}).get(k)
                if not many and v and got[k] and v != got[k]:   # two columns for one fact: never a pick
                    raise RequestError(f"{_n} reads {step}'s {k} from the samplesheet's {v!r} and another family "
                                       f"adapter from {got[k]!r}; one fact is one column - correct the adapter")
                got[k] = got[k] + [x for x in v or [] if x not in got[k]] if many else got[k] or v
    if where is not None and not doc.get("object"):  # one object: no samplesheet exists until stage 00 writes
        _sheet_agrees(Path(where("observations")), cols, up, keys, first, set(map(str, reads)))
    return up, decisions


def _sheet_agrees(sheet: Path, cols: dict, up: dict, keys: dict, first: dict, reads: set):
    """Every row of the request's samplesheet against the request's upstream block. The request is the
    run's record of what ran upstream, so it states every claim the samplesheet makes. For a step the
    first stage's tool reads from the sheet (`reads`), a column it lacks is that tool's reading (no
    `ambient_h5`: not performed); for one it does not, only the columns the sheet holds speak (autodev
    W049: the sheet is read whatever stage starts), and where the sheet is silent the request's word stands."""
    from .services.dataset import read_manifest
    try:
        head, rows = read_manifest(sheet)
    except Exception:                            # noqa: BLE001 - the stack's own init refuses it by name
        return
    head = set(map(str, head or (rows[0] if rows else {})))
    for step, c in cols.items():
        if step not in up:
            continue
        c = dict(c or {})
        mine = step in reads
        if not mine:
            c = {"tool": c.get("tool") if c.get("tool") in head else None,
                 "version": c.get("version") if c.get("version") in head else None,
                 "performed": [k for k in c.get("performed") or [] if k in head],
                 "declined": [k for k in c.get("declined") or [] if k in head]}
        tool, ver = up[str(step)]["tool"], up[str(step)].get("version")
        none = _word(tool) == "none"
        for i, r in enumerate(rows, 1):
            def cell(k):
                return str(r.get(k) or "").strip() if k else ""
            lib = cell(keys["sample"]) or str(i)
            st, sv = cell(c.get("tool")), cell(c.get("version"))
            done = [k for k in c.get("performed") or [] if cell(k)]
            skip = [k for k in c.get("declined") or [] if cell(k)]
            why = (f"{c['tool']}={st!r}" if st and _word(st) != _word(tool) else
                   f"{done[0]}={cell(done[0])!r}, which its tool reads as {step} performed" if none and done else
                   f"{skip[0]}={cell(skip[0])!r}, {step} declined" if not none and skip else
                   f"none of {', '.join(c['performed'])}, so no {step} performed" if not none and c.get("performed")
                   and not done and mine else
                   f"{c['version']}={sv!r}" if sv and (ver is None or _vword(sv) != _vword(ver)) else None)
            if why:
                raise RequestError(f"upstream.{step}: the request says {tool!r}"
                                   + (f" version {ver!r}" if ver is not None else " with no version")
                                   + f", and the samplesheet's row {lib} says {why}; what ran upstream is read from "
                                     f"every place it is declared - the request and the samplesheet's columns a "
                                     f"family tool reads as {step} (their upstream_columns:) - and the places must "
                                     f"agree: correct the one that is wrong")


def _path_list(v) -> list:
    """A declaration's one param path or list of them (library_key, replicate_key: W045), as a list."""
    return [str(v)] if isinstance(v, str) else [str(x) for x in (v or [])]


def _write_key(params: dict, paths: list, value: str, who: str, what: str, key: str) -> dict:
    """Write one column the request names into each tool flag an adapter declares takes it."""
    for path in paths:
        head, _, rest = path.partition(".")
        if rest and head not in params:
            continue                             # that command is not declared: nothing to tell it
        got = dict(params.get(head) or {}).get(rest) if rest else params.get(head)
        if got is not None and str(got) != value:
            raise RequestError(f"{who}: {path} is {got!r}, but the request's {what} column is {key} = "
                               f"{value!r}; the {what} is one fact and the driver writes it into every "
                               f"stage: drop {path} from the stage's params")
        params = _set(params, path, value)
    return params


def _object(doc: dict, keys: dict, observations: str, files: bool):
    """The request's `object:` declarations, checked by name against the object's own metadata
    (its slot's encoding and shape, its obs and var columns; no stored value is read here: the
    parts step refuses a slot that is not integers as it reads it). None for a samplesheet."""
    obj = doc.get("object")
    if obj is None:
        if str(observations).endswith(".h5ad"):
            raise RequestError(f"observations: {Path(observations).name} is one object; the stages read "
                               f"libraries: declare object: {{counts: <the integer slot>, symbols: <the gene "
                               f"symbol column>}} and keys.replicate, and the parts step writes them")
        return None
    if not isinstance(obj, dict):
        raise RequestError("object: is not a mapping of " + ", ".join(OBJECT_FIELDS))
    bad = sorted(set(obj) - set(OBJECT_FIELDS))
    if bad:
        raise RequestError(f"object: {', '.join(bad)} is not an object field ({', '.join(OBJECT_FIELDS)})")
    absent = [k for k in OBJECT_REQUIRED if not str(obj.get(k) or "").strip()]
    if absent:
        raise RequestError(f"object: declares no {', '.join(absent)}; nothing about the object is guessed: "
                           + FIELDS["object"])
    if not keys.get("replicate"):
        raise RequestError("keys: declares no `replicate`; in one object the library (keys.sample) and the "
                           "unit the design sheet is keyed on are declared apart: keys: {sample: <the library "
                           "column>, replicate: <the donor or sample column>}")
    carry = obj.get("carry") or []
    if not isinstance(carry, list):
        raise RequestError("object.carry: is not a list of obs columns")
    n = obj.get("chunk_values")
    if n is not None and (not str(n).isdigit() or int(n) < 1):
        raise RequestError(f"object.chunk_values: {n!r} is not a positive number of stored values")
    if not str(observations).endswith(".h5ad"):
        raise RequestError(f"observations: {Path(observations).name} is not an .h5ad; `object:` declares one")
    col = str(doc.get("parts") or "")
    if col in {SHEET_LIBRARY, str(keys["sample"]), *map(str, dict(doc.get("context") or {}))}:
        raise RequestError(f"parts: {col!r} is a column the parts step's samplesheet already writes (the "
                           f"library as {SHEET_LIBRARY!r} and keys.sample, and every context axis); name "
                           f"the column the first stage's tool reads a library's object from")
    out = {"path": str(observations), "counts": str(obj["counts"]), "symbols": str(obj["symbols"]),
           "carry": [str(c) for c in carry], "chunk_values": int(n) if n is not None else None}
    if not files:
        return out
    try:
        import h5py
    except ImportError:
        raise RequestError("object: reading the object's names needs h5py in this interpreter") from None
    with h5py.File(observations, "r") as f:
        slot = out["counts"]
        if slot not in f:
            raise RequestError(f"object.counts: the object holds no slot {slot!r} (its slots: "
                               f"{', '.join(sorted(f.keys()))})")
        node = f[slot]
        kind = node.attrs.get("encoding-type", node.attrs.get("h5sparse_format", b""))
        kind = kind.decode() if isinstance(kind, bytes) else str(kind)
        if kind not in ("csr_matrix", "csr"):
            raise RequestError(f"object.counts: {slot!r} is {kind or 'a dense array'}; the parts step streams "
                               f"a row-compressed (csr) slot, and no other")
        frames = {"obs": f["obs"], "var": f["raw/var" if slot.startswith("raw/") else "var"]}
        for frame, cols, what in (("obs", [keys["sample"], keys["replicate"], *out["carry"]], "keys/carry"),
                                  ("var", [out["symbols"]], "object.symbols")):
            have = [k for k in frames[frame].keys() if not k.startswith("_")]
            miss = [c for c in cols if str(c) not in have]
            if miss:
                name = "raw/var" if frame == "var" and slot.startswith("raw/") else frame
                raise RequestError(f"{what}: the object's {name} has no column {', '.join(map(repr, miss))} "
                                   f"(its columns: {', '.join(have)})")
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
    obj = _object(doc, keys, where("observations"), files)

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
    numbered = list(enumerate(stages, 1))
    if obj:
        # THE OBJECT'S PARTS ARE STAGE 00 (W045): the harness's own step, its params the request's
        # `object:` declarations; the library and the replicate reach it as every stage's do.
        step = {k: obj[k] for k in OBJECT_FIELDS if obj.get(k)}
        numbered.insert(0, (0, {"plugin": STEP, "params": {**step, "column": str(doc["parts"])}}))
    rep = str(keys.get("replicate") or keys["sample"])
    pooled = bool(keys.get("replicate")) and str(keys["replicate"]) != str(keys["sample"])
    for i, s in numbered:
        if not isinstance(s, dict) or not s.get("plugin"):
            raise RequestError(f"stages[{i}]: declares no plugin")
        extra = sorted(set(s) - {"plugin", "params"})
        if extra:
            raise RequestError(f"stages[{i}]: {', '.join(extra)} is not a stage field (plugin, params)")
        m = _resolve(str(s["plugin"]))
        params = dict(s.get("params") or {})
        short = m.name.split("@")[0]
        if not re.fullmatch(STAGE_WORD, short):      # a directory, and a word of the generated job's shell
            raise RequestError(f"stages[{i}]: {m.name!r} names its stage {short!r}; a stage's name is a "
                               f"directory and is written into the generated job: letters, digits, `_`, `-`, `.`")
        if short in seen:
            raise RequestError(f"stages[{i}]: a second {short!r} stage; each stage runs once")
        seen.add(short)
        # THE LIBRARY IS ONE FACT (autodev W042, GAP-C92): each tool takes the column naming each
        # library where its adapter declares (`library_key:`), and the driver writes the request's
        # keys.sample there, wherever that command is declared. A stage that names another column
        # is refused: two names for one column is how the fixture's second shape died at stage 4.
        # THE REPLICATE IS THE SECOND KEY (W045): a pooled library holds several replicates, so a tool
        # flag that names the unit the design sheet is keyed on (`replicate_key:`) takes keys.replicate,
        # and keys.sample where none is declared (each library one replicate, as the request says).
        paths = _path_list(m.data.get("library_key"))
        params = _write_key(params, paths, str(keys["sample"]), f"stages[{i}] ({m.name})", "library",
                            "keys.sample")
        rpaths = _path_list(m.data.get("replicate_key"))
        params = _write_key(params, rpaths, rep, f"stages[{i}] ({m.name})", "replicate",
                            "keys.replicate" if keys.get("replicate") else "keys.sample")
        if pooled:
            for path in _path_list(m.data.get("library_design")):
                head, _, rest = path.partition(".")
                if (dict(params.get(head) or {}).get(rest) if rest else params.get(head)) is not None:
                    tool = (m.data.get("wraps") or {}).get("tool") or m.name
                    raise RequestError(
                        f"stages[{i}] ({m.name}): {path} is a design sheet {tool} keys on the library "
                        f"({', '.join(paths)}); this request's design is keyed on keys.replicate = "
                        f"{rep!r}, and a pooled library holds several replicates, so {tool} cannot "
                        f"join it (a follow-up for {tool}): drop {path} from the stage's params")
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
        # A FLAG THE ADAPTER OWNS IS REFUSED WHEN THE PLAN IS MADE (autodev W042 fix 2, the observation):
        # `owned:` is the manifest's copy of its run.py's OWNED, tied by a test; refused here, not after
        # the stages before it ran.
        for path in m.data.get("owned") or []:
            got = _has(params, str(path))
            if got:
                raise RequestError(f"stages[{i}] ({m.name}): params set {got[0]}, which {m.name} sets itself from "
                                   f"the stack (its `owned:`); drop it from the stage's params")
        # WHAT ITS TOOL OPENS IS DECLARED (autodev W056, design read D6): the adapter's files:, checked by name, and each
        # declared value text, absolute or ~/ - A RELATIVE PATH IS READ WHERE ITS TOOL RUNS (W042 fix 2, B), the stage's
        # run directory, where it names nothing the set holds. Any other value is text: never looked up, never refused.
        files_decl = _decl(m)
        for param, e in files_decl.items():
            found, v = _param(params, param) if param != "observations" else (False, None)
            if found:
                _values(v, e, f"stages[{i}] ({m.name}): {param}")
        decisions = []
        for d in m.data.get("decisions") or []:
            # AN ESCAPE IS NEVER A PLAIN PARAM, WHEREVER IT IS PUT (autodev W042 fix 2, D): its name is
            # compared with `-`/`_` and case folded, at its own place and at any other depth of the stage's
            # params - an adapter declares each escape's flag under one command only
            leaf = _key(str(d["param"]).split(".")[-1]).replace("_", "")
            put = _has(params, str(d["param"])) + [x for x, k in _keys(params) if _key(k).replace("_", "") == leaf]
            if put:
                raise RequestError(f"stages[{i}] ({m.name}): params set {put[0]}, "
                                   f"which {m.name} declares "
                                   f"the user's decision {short}.{d['name']} ({d['what']}); the driver passes "
                                   f"it only as an answer recorded with who gave it: --answer "
                                   f"{short}.{d['name']}=VALUE --by WHO")
            if str(d.get("unanswered") or "stop") not in UNANSWERED:
                raise RequestError(f"{m.name}: decision {d['name']} declares unanswered: {d.get('unanswered')!r}; "
                                   f"it is one of {', '.join(UNANSWERED)}")
            decisions.append({"name": f"{short}.{d['name']}", "param": str(d["param"]), "what": d["what"],
                              "escape": d.get("escape"), "unanswered": str(d.get("unanswered") or "stop")})
        plan.append({"stage": f"{i:02d}_{short}", "plugin": m.name, "dir": str(m.dir),
                     "replicate_key": rpaths,
                     "profile": m.profile, "version": m.version,
                     "wraps": {k: (m.data.get("wraps") or {}).get(k) for k in WRAPS},
                     "assays": list(m.data.get("assays") or []), "reads": m.data.get("reads"),
                     "hands_on": _hands_on(m, params), "params": params, "decisions": decisions,
                     "library_key": paths,
                     "resources": dict(m.data.get("resources") or {}),
                     "upstream_columns": m.data.get("upstream_columns"),
                     "upstream_accepts": m.data.get("upstream_accepts"), "files": files_decl,
                     "runs_upstream": dict(m.data.get("runs_upstream") or {}),
                     "cannot_show": list(m.data.get("cannot_show") or [])})

    # A TOOL'S FLAGS ARE THE REQUEST'S (autodev W049, route 11): the site layer every stage's stack is
    # composed over declares where stages run, not a tool's flags - one it laid beneath a stage's params
    # would reach the tool unchecked (an escape, an owned flag, a path) and unpinned
    site = os.environ.get("SCH_SITE")
    layer = yamlish.load(Path(site) / "stack.yml") if site and (Path(site) / "stack.yml").is_file() else None
    for p in plan:
        got = dict(((layer or {}).get("plugins") or {}).get(p["plugin"]) or {}) if isinstance(layer, dict) else {}
        if got:
            raise RequestError(f"{site}/stack.yml declares plugins.{p['plugin']} ({', '.join(sorted(map(str, got)))}); "
                               f"a site layer declares where the stages run (executor, pbs), and a tool's flags are "
                               f"the request's (stages[].params), verbatim - move them there")

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
        hidden = [k for k, v in size.items() if not LINE.fullmatch(str(v))]
        if hidden:                               # a size is written into the job's header as it is (W049)
            raise RequestError(f"resources.{who}.{hidden[0]} is {size[hidden[0]]!r}; a size is one line of "
                               f"printable text - it is written into the generated job as it is")
        from .services.executor import ExecutorError, check_size
        try:
            check_size(size)
        except ExecutorError as e:
            raise RequestError(f"resources.{who}: {e}") from None
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
    prof = _shipped_profile(plan)
    bad = sorted(set(ctx) - set(prof.axes))
    if bad:
        raise RequestError(f"context: {', '.join(bad)} is not an axis of {prof.id} ({', '.join(prof.axes)})")

    up, run_decisions = _upstream(doc, prof, assay, plan, keys, where if files else None)

    # ---- the chain: each stage reads a shape the stage before it hands on
    first = "joint" if obj else "libraries"
    if plan[0]["reads"] != first:
        raise RequestError(f"{plan[0]['plugin']} reads {plan[0]['reads']!r}; the request's observations are "
                           f"{first}, so the first stage must read {first}")
    for prev, nxt in zip(plan, plan[1:]):
        if nxt["reads"] not in prev["hands_on"]:
            cond = {s: w for s, w in dict(_resolve(prev["dir"]).data.get("hands_on") or {}).items()}
            how = (f"; {prev['plugin']} hands on {nxt['reads']} when its params declare "
                   f"{cond[nxt['reads']]!r}") if cond.get(nxt["reads"]) else ""
            raise RequestError(f"{nxt['plugin']} reads {nxt['reads']}; {prev['plugin']} hands on "
                               f"{', '.join(prev['hands_on']) or 'nothing'}{how}")
    req = {"path": str(src), "sha256": _sha(src), "observations": where("observations"),
            "design": where("design") if doc.get("design") else None, "parts": str(doc["parts"]),
            "keys": {str(k): str(v) for k, v in keys.items()}, "object": obj,
            "context": {str(k): str(v) for k, v in ctx.items()}, "upstream": up, "stages": plan,
            "decisions": run_decisions,
            "drive_resources": {str(k): str(v) for k, v in dict(res.get(DRIVE) or {}).items()}}
    if files:                                    # a cell of a column a tool opens from its own directory, written
        declared(req)                            # relative, is refused here, by name (autodev W056, D6)
    return req


def plan_lines(req: dict, answers: dict | None = None) -> list:
    answers = answers or {}
    a = req["context"]
    lines = [f"  request {req['path']} (sha256 {req['sha256'][:12]})",
             f"  context {', '.join(f'{k}={v}' for k, v in a.items())}",
             "  upstream " + "; ".join(f"{s}: {v.get('tool')}" + (f" {v['version']}" if v.get("version") is not None
                                                                  else "") for s, v in req["upstream"].items())]
    for d in req.get("decisions") or []:
        got = (f"answered {json.dumps(answers[d['name']]['value'])} by {answers[d['name']]['by']}"
               if d["name"] in answers else f"UNANSWERED - nothing runs ({' | '.join(d['values'])})")
        lines.append(f"  the user's: {d['name']} - {d['what']}; {got}")
    for p in req["stages"]:
        w = p["wraps"]
        lines.append(f"  {p['stage']:<8} {p['plugin']} {p['version']} ({w.get('tool')} {w.get('version')})  "
                     f"reads {p['reads']}, hands on {', '.join(p['hands_on']) or 'nothing'}")
        lines.append(f"           given: {', '.join(sorted(p['params'])) or 'nothing'}; every other flag: "
                     f"{w.get('tool')}'s own default")
        if p["plugin"] == STEP and req.get("object"):
            o = req["object"]
            lines.append(f"           the object: counts {o['counts']}, symbols {o['symbols']}, carry "
                         f"{', '.join(o['carry']) or 'nothing'}; one part per keys.sample, the samplesheet's "
                         f"part column {req['parts']}")
        if p.get("library_key"):
            lines.append(f"           the library column: keys.sample={req['keys']['sample']} -> "
                         f"{', '.join(p['library_key'])}")
        if p.get("replicate_key"):
            k = req["keys"]
            lines.append("           the replicate column: " + (f"keys.replicate={k['replicate']}" if k.get(
                "replicate") else f"keys.sample={k['sample']} (no keys.replicate: each library one replicate)")
                + f" -> {', '.join(p['replicate_key'])}")
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


#: An answer and who gave it are one line each: they are recorded, and written into a generated job's
#: header and shell lines as they are (autodev W049, ATTACKS 6).
LINE = re.compile(r"[^\x00-\x1f\x7f\x85\u2028\u2029]+")


#: Letters that print as nothing: a name holds at least one letter or digit that prints (autodev W049 fix 1).
BLANK_LETTERS = frozenset("ᅟᅠㅤﾠ")


def _a_name(v) -> bool:
    """Who made a decision, as it is recorded: a name, so at least one letter or digit that prints - not a
    blank, and not only zero-width, format or filler characters (autodev W049 fix 1)."""
    import unicodedata
    return isinstance(v, str) and any(unicodedata.category(ch)[0] in "LN" and ch not in BLANK_LETTERS for ch in v)


def _climbs(x: str) -> bool:
    """A relative path out of its tool's working directory (`..`), or into another account's home."""
    return bool(re.search(r"(^|/)\.\.(/|$)", x) or re.match(r"~[^/\s]+/", x))


def answers_of(req: dict, given: list | None, by: str | None, recorded: dict | None = None) -> tuple:
    """(answers, the names answered now): the recorded answers and each `--answer NAME=VALUE` given now,
    read alike by the run, the plan and a generated job (autodev W049): a declared name, an allowed value,
    a recorded one never rewritten, who gave it a name on one line, and the answer to a param its adapter
    declares a file only absolute or `~/` - its tool reads a relative path from its own working directory,
    where the set would not pin what was meant; any other answer is text (autodev W056, D6)."""
    names = {d["name"]: d for p in req["stages"] for d in p["decisions"]}
    names.update({d["name"]: d for d in req.get("decisions") or []})
    answers, new, now = dict(recorded or {}), [], {}
    if given and not _a_name(by):
        raise RequestError("--answer needs --by: a decision is recorded with who made it, by name (a blank is no name, "
                           "nor are characters that print as nothing)")
    for what, v in [("--by", by)] + [("--answer", a) for a in given or []]:
        if v is not None and not LINE.fullmatch(str(v)):
            raise RequestError(f"{what} {str(v)!r}: an answer and who gave it are one line of printable text; they "
                               f"are recorded and written into a generated job as they are")
    typed = {d["name"]: (p.get("files") or {})[d["param"]] for p in req["stages"] for d in p["decisions"]
             if d["param"] in (p.get("files") or {})}   # an answer to a param declared a file is one (W056, D6)
    for a in given or []:
        name, sep, raw = str(a).partition("=")
        if not sep or name not in names:
            raise RequestError(f"--answer {a!r}: no stage declares a user's decision {name!r}; "
                               f"declared: {', '.join(names) or 'none'}")
        try:
            value = json.loads(raw)
        except ValueError:
            value = raw
            try:                                 # autodev W056 fix 1, S2 (ATTACKS 8): the record and what was passed
                read = yamlish._scalar(raw, 0)   # are one thing - a text the stage's params format reads as a
            except Exception:                    # boolean would be recorded as the text and reach the tool as the flag
                read = raw
            if isinstance(read, bool):
                raise RequestError(f"--answer {a!r}: {raw.strip()!r} is not JSON, so it would be recorded as the text "
                                   f"{json.dumps(raw)}, while the format of the stage's params reads it as the boolean "
                                   f"{json.dumps(read)}: write {name}={json.dumps(read)} for the boolean, or "
                                   f"{name}={json.dumps(raw)} (quoted, JSON) for the text")
        allowed_values = names[name].get("values")
        if allowed_values and value not in allowed_values:
            raise RequestError(f"--answer {a!r}: {name} is answered {' or '.join(allowed_values)}")
        if name in typed:
            _values(value, typed[name], f"--answer {a!r}: {name}")
        if name in now and now[name] != value:   # autodev W049 fix 1: one command, one answer a decision
            raise RequestError(f"--answer {name} is given twice in one command ({json.dumps(now[name])} and "
                               f"{json.dumps(value)}): a decision has one answer")
        now[name] = value
        if name in answers and answers[name]["value"] != value:
            raise RequestError(f"{name} is already answered {json.dumps(answers[name]['value'])} by "
                               f"{answers[name]['by']}; a recorded decision is not rewritten: start a new --out")
        if name in answers and name not in new and answers[name]["by"] != str(by).strip():
            raise RequestError(f"{name} is recorded {json.dumps(answers[name]['value'])} by {answers[name]['by']}, "
                               f"and given again by {str(by).strip()}: who made a recorded decision is not "
                               f"rewritten - leave it out of this command (it is recorded), or start a new --out")
        if name not in answers:
            answers[name] = {"value": value, "by": str(by).strip(), "at": _now(), "verbatim": a}
            new.append(name)
    return answers, new


def _answer_of(role: str):
    """The decision an `answer[<name>]...` role was named by, else None."""
    return role[len("answer["):role.index("]")] if role.startswith("answer[") and "]" in role else None


def _late(req: dict, out: Path, led, new: list):
    """AN ANSWER REACHES ONLY A STAGE THAT HAS NOT RUN (autodev W049 fix 1; ATTACKS 13, 21, 32). What the run's
    record says a stage was given is what that stage's seal says: an answer given now for a stage already
    sealed - its tool ran without it - is refused by name before anything runs (a run's own decision is
    read by every stage). A changed or re-attributed answer is refused by `answers_of`."""
    sealed = [p["stage"] for p in req["stages"] if (out / p["stage"] / "SEALED.json").exists()
              or ((led or {}).get("seals") or {}).get(p["stage"])]
    owners: dict = {}
    for p in req["stages"]:
        for d in p["decisions"]:
            owners.setdefault(d["name"], []).append(p["stage"])
    for name in new:
        hit = sealed if name in {d["name"] for d in req.get("decisions") or []} else \
            [s for s in owners.get(name) or [] if s in sealed]
        if hit:
            raise RequestError(f"--answer {name}: {hit[0]} is sealed, and its tool ran without this answer (its "
                               f"seal records {name} as not given); an answer to a stage that has run would be "
                               f"recorded as taken and never reach its tool - start a new --out")


def _given(p: dict, answers: dict) -> dict:
    """A stage's params as its tool is handed them: the request's, each answered decision set into its param."""
    params = dict(p["params"])
    for d in p["decisions"]:
        if d["name"] in answers:
            params = _set(params, d["param"], answers[d["name"]]["value"])
    return params


def _disagree(p: dict, req: dict, seal: dict, answers: dict) -> list:
    """[(what, the run's record, the seal's)] where what the run's record says stage `p` was given - each of
    its decisions answered, with who answered it, and the params its tool was handed - is not what its own
    seal says (autodev W049 fix 1): compared on every resume and at the run's seal."""
    out = []
    for d in [*p["decisions"], *(req.get("decisions") or [])]:
        mine, its = answers.get(d["name"]), (seal.get("decisions") or {}).get(d["name"])
        if mine != its:
            out.append((d["name"], mine, its))
    if seal.get("params") != _given(p, answers):
        out.append(("params", _given(p, answers), seal.get("params")))
    return out


def _disagreed(stage: str, bad: list) -> str:
    def w(k, v):
        if v is None:
            return "not given"
        if k != "params" and isinstance(v, dict) and "value" in v:
            return f"{json.dumps(v['value'])} by {v.get('by')}"
        return json.dumps(v, sort_keys=True)[:160]
    return "; ".join(f"{k}: {w(k, a)} in the run's record, {w(k, b)} in {stage}'s seal" for k, a, b in bad)


#: What in a run directory says a run was there: a directory holding any of them and no record of its
#: inputs is refused, never started afresh (autodev W042 fix 2, B).
TRACES = ("request.json", "DRIVE.json", "decisions.json", "SEALED.json")


def _refuse_trace(out: Path, req: dict):
    if not out.exists() or (out / INPUTS).exists():
        return
    stages = [p["stage"] for p in req["stages"]]
    seen = [x for x in TRACES if (out / x).exists()] + sorted(
        d.name for d in out.iterdir() if d.is_dir() and d.name.split(".failed-")[0] in stages)
    if seen:
        raise RequestError(f"{out} holds a run ({', '.join(seen)}) and no {INPUTS}, the record of the files it "
                           f"read: without it nothing says its stages ran on these files, and a missing record "
                           f"is not a fresh start - start a new --out")


def _ledger(out: Path, dfile: Path):
    """The run's record, checked before anything it names is read: None for a new run directory."""
    rec_f = out / INPUTS
    if not rec_f.exists():
        return None
    if not (out / "request.json").exists():
        raise RequestError(f"{out} records {INPUTS} and no request.json: the run's record is incomplete, "
                           f"and a missing record is not a fresh start - start a new --out")
    try:
        rec = json.loads(rec_f.read_text())
    except ValueError as e:
        raise RequestError(f"{rec_f} is not the run's record ({e}): start a new --out") from None
    if rec.get("out") != str(out):
        raise RequestError(f"{rec_f} records the run directory {rec.get('out')!r}, not {out}: a record copied "
                           f"from another run is not this run's - start a new --out")
    if (dfile.exists() and _sha(dfile) != rec.get("decisions_sha256")) or (
            not dfile.exists() and rec.get("decisions_sha256")):    # removed is changed too (W049)
        raise RequestError(f"{dfile} was changed outside `sch run` (sha256 "
                           f"{_sha(dfile)[:12] if dfile.exists() else 'none: it is gone'}, recorded "
                           f"{str(rec.get('decisions_sha256'))[:12]}); a recorded decision is not rewritten: "
                           f"restore it, or start a new --out")
    return rec


def _pinned(out: Path, req: dict, rec, answers: dict, new: list) -> tuple:
    """(the run's record, the set now). The set is recorded when the run starts; on a resume it must
    equal the record - but for the files an answer given now names, which enter it now (autodev W049) -
    and every sealed stage must be one this run sealed, on the same set (`_trust`)."""
    now = run_inputs(req, answers)
    if rec is None:
        rec = {"started_at": _now(), "out": str(out), "policy": POLICY, "files": now,
               "decisions_sha256": None, "seals": {}}
        (out / INPUTS).write_text(json.dumps(rec, indent=1) + "\n")
        return rec, now
    d = differ(flat(rec.get("files") or {}), flat(now))
    fresh = [k for k, a, _b in d if a is None and _answer_of(k) in new]
    d = [x for x in d if x[0] not in fresh]
    if d:
        raise RequestError(f"{out} was started on other files: {said(d, {**(rec.get('files') or {}), **now})}. "
                           f"A run is one request and every file it reads; a stage sealed on the old ones would "
                           f"be read beside one run on the new. Restore each file as it was, or start a new --out")
    # A MISSING SEAL IS NOT A FRESH START EITHER (autodev W042 fix 2, B): a stage the run's ledger names
    # as sealed still holds its seal, and the sealed stages are the first ones, in order - a stage run
    # again beneath a later one that stays sealed would hand on other files than that one read
    gap = None
    for p in req["stages"]:
        s = p["stage"]
        if (out / s / "SEALED.json").exists():
            if gap:
                raise RequestError(f"{s} is sealed and {gap}, before it, is not: {s} was made from what {gap} "
                                   f"handed on then, and {gap} run again would hand on other files - a run is "
                                   f"sealed in order: start a new --out")
            seal = _trust(out, s, rec, now)
            bad = _disagree(p, req, seal, {k: v for k, v in answers.items() if k not in new})
            if bad:                              # autodev W049 fix 1: the record is what each seal says
                raise RequestError(f"the run's record and {s}'s seal disagree: {_disagreed(s, bad)}. What a run "
                                   f"says a stage was given is what that stage's seal says: restore the record, "
                                   f"or start a new --out")
        elif (rec.get("seals") or {}).get(s):
            raise RequestError(f"the run's {INPUTS} names {s}'s seal ({str(rec['seals'][s])[:12]}) and "
                               f"{out / s / 'SEALED.json'} is not there: a missing seal is not a fresh start - "
                               f"start a new --out")
        else:
            gap = gap or s
    rec.setdefault("files", {}).update({k: now[k] for k in fresh})
    return rec, now


def _trust(out: Path, stage: str, rec: dict, now: dict) -> dict:
    """A SEALED STAGE IS TRUSTED ONLY ON ITS RECORD (autodev W042 fix 2, B): the run's ledger names its
    seal with that seal's sha256; the seal was made in this run directory, on the set as it is now and as
    the run recorded it; and what it handed on hashes as it did when it was sealed."""
    f = out / stage / "SEALED.json"
    want = (rec.get("seals") or {}).get(stage)
    if want != _sha(f):
        raise RequestError(f"{stage}'s seal is not one this run recorded (the run's {INPUTS} names "
                           f"{str(want)[:12] if want else 'no seal for it'}, the seal is {_sha(f)[:12]}): a "
                           f"seal edited, or copied from another run, is not trusted - start a new --out")
    seal = json.loads(f.read_text())
    if seal.get("out") != str(out):
        raise RequestError(f"{stage} was sealed in {seal.get('out')!r}, not {out}: start a new --out")
    known = set(seal.get("answers_known") or [])  # an answer given after this seal: a file it never read
    d = [x for x in differ(seal.get("inputs") or {}, flat(now))
         if not (x[1] is None and _answer_of(x[0]) is not None and _answer_of(x[0]) not in known)]
    if d:
        raise RequestError(f"{stage} was sealed on other files: {said(d, now)}. Restore each file as it was, "
                           f"or start a new --out")
    for path, dig in (seal.get("handed_sha256") or {}).items():
        p = Path(path)
        if not p.resolve().is_relative_to(out.resolve()) if hasattr(p, "is_relative_to") else \
                not str(p.resolve()).startswith(str(out.resolve()) + os.sep):
            raise RequestError(f"{stage} hands on {path}, outside this run directory: start a new --out")
        got = _digest(_entry(p)) if p.is_file() else "absent"
        if got != dig:
            raise RequestError(f"{stage} handed on {path} ({str(dig)[:12]} when sealed, {str(got)[:12]} now): "
                               f"what a sealed stage handed on is the next stage's input - restore it, or start "
                               f"a new --out")
    return seal


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
    _refuse_trace(out, req)
    out.mkdir(parents=True, exist_ok=True)
    resume = f"sch run --request {req['path']} --out {out}"
    prior = out / "request.json"
    if prior.exists() and json.loads(prior.read_text())["sha256"] != req["sha256"]:
        raise RequestError(f"{out} was run from another request (sha256 "
                           f"{json.loads(prior.read_text())['sha256'][:12]}); a run is one request: "
                           f"start a new --out")
    dfile = out / "decisions.json"
    led = _ledger(out, dfile)                    # decisions.json's hash checked before its answers are read
    answers, new = answers_of(req, answers_given, by, json.loads(dfile.read_text()) if dfile.exists() else {})
    _late(req, out, led, new)                    # before anything is written (autodev W049 fix 1)
    pins, _now_set = _pinned(out, req, led, answers, new)
    prior.write_text(json.dumps(req, indent=1, default=str) + "\n")
    dfile.write_text(json.dumps(answers, indent=1) + "\n")
    pins["decisions_sha256"] = _sha(dfile)
    (out / INPUTS).write_text(json.dumps(pins, indent=1) + "\n")
    inputs = flat(pins["files"])

    # THE RUN'S OWN DECISIONS (D-031): single cells delivered already denoised, by any remover (W049), are
    # neither passed silently nor refused without recourse - nothing runs until the user
    # accepts them, by name, recorded with who; declined, the run is refused.
    for d in req.get("decisions") or []:
        if d["name"] not in answers:
            rec = {"status": "waiting", "stage": req["stages"][0]["stage"], "sealed": [],
                   "waiting_for": [d], "resume": resume + f" --answer {d['name']}=VALUE --by WHO"}
            _record(out, **rec)
            return WAITING, rec
        if answers[d["name"]]["value"] != "accept":
            raise RequestError(f"{d['name']} was answered {answers[d['name']]['value']!r} by "
                               f"{answers[d['name']]['by']}: {d['what']} - declined, nothing runs")

    # one object: stage 00 reads it as the `joint` shape, a one-row manifest naming it (W045)
    handed = {"libraries": {}, "joint": req["object"]["path"]} if req.get("object") else None
    done = []
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
        params = _given(p, answers)

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
    # THE RUN'S RECORD IS ITS STAGES' SEALS (autodev W049 fix 1): each stage's decisions, who answered them
    # and the params its tool was handed, as the run records them, are what its own seal says - or no seal
    seals = {p["stage"]: json.loads((out / p["stage"] / "SEALED.json").read_text()) for p in req["stages"]}
    for p in req["stages"]:
        bad = _disagree(p, req, seals[p["stage"]], answers)
        if bad:
            rec = {"status": "failed", "stage": p["stage"], "plugin": p["plugin"], "sealed": done,
                   "reason": f"the run is not sealed: its record and {p['stage']}'s seal disagree: "
                             f"{_disagreed(p['stage'], bad)}",
                   "fix": "what a run says a stage was given is what that stage's seal says: start a new --out",
                   "resume": resume}
            _record(out, **rec)
            return 2, rec
    last = seals[done[-1]] if done else {}
    rec = {"status": "sealed", "sealed": done, "request": req["path"], "request_sha256": req["sha256"],
           "inputs": last.get("inputs") or inputs, "decisions": answers, "upstream": req["upstream"],
           "agreed": f"the run's decisions, who answered them and the params each tool was handed are each "
                     f"stage's own seal ({len(done)} stages, {len(answers)} answers)",
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
    resume = f"sch run --request {req['path']} --out {out}"

    def changed(when):
        """THE SET AT THIS STAGE'S START AND AT ITS SEAL (autodev W042 fix 2, B): recomputed, never
        copied, and compared with the run's record; a difference fails the stage, naming each file."""
        rec = json.loads((out / INPUTS).read_text())
        now = run_inputs(req, answers)
        d = differ(flat(rec.get("files") or {}), flat(now))
        if d:
            return now, (f"the files the run reads changed {when}: {said(d, {**rec['files'], **now})}",
                         "restore each file as it was and resume, or start a new --out on the files as they are")
        return now, None
    _now_set, bad = changed(f"before {p['stage']} started")
    if bad:
        return failed(*bad)
    sd.mkdir(parents=True)
    if handed is None:
        obs, keys, parts = req["observations"], req["keys"], req["parts"]
    elif handed.get("samplesheet") and p["reads"] == "libraries":
        # the libraries with their samplesheet, as a cohort delivering libraries would deliver it (W045)
        obs, keys, parts = handed["samplesheet"], req["keys"], req["parts"]
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
    for d in [*(req.get("decisions") or []), *p["decisions"]]:
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
              "joint": str(rd / "out" / got["joint"]) if got.get("joint") else None,
              "samplesheet": str(rd / "out" / got["samplesheet"]) if got.get("samplesheet") else None}
    lost = [x for x in [*handed["libraries"].values(), handed["joint"], handed["samplesheet"]]
            if x and not Path(x).is_file()]
    if lost:
        return failed(f"{p['plugin']} names {lost[0]} as handed on and it is not there",
                      "read the stage's out.json", st)
    now, bad = changed(f"while {p['stage']} ran (its start and its seal disagree)")
    if bad:
        return failed(bad[0], bad[1], st)
    st.prov.append("drive/sealed", stage=p["stage"], hands_on=handed)
    st.close()
    _seal(sd, rd, {"stage": p["stage"], "plugin": p["plugin"], "hands_on": handed,
                   "report": str(sd / "report" / "report.json"), "numbers": len(rep.get("numbers") or []),
                   "request_sha256": req["sha256"], "out": str(out), "inputs": flat(now),
                   "answers_known": sorted(answers), "params": params,
                   "handed_sha256": {x: _digest(_entry(Path(x))) for x in
                                     [*handed["libraries"].values(), handed["joint"], handed["samplesheet"],
                                      str(sd / "report" / "report.json")] if x and Path(x).is_file()},
                   "decisions": {d["name"]: answers.get(d["name"]) for d in
                                 [*p["decisions"], *(req.get("decisions") or [])]}})
    led = json.loads((out / INPUTS).read_text())   # the run's ledger names every seal it made
    led.setdefault("seals", {})[p["stage"]] = _sha(sd / "SEALED.json")
    (out / INPUTS).write_text(json.dumps(led, indent=1) + "\n")
    return None, handed


#: What a job pins otherwise: the harness it runs, by its commit and a clean checkout (EXPECT_HARNESS and
#: the recipe's HARNESS-CLEAN), not by the work tree it was generated from.
JOB_UNPINNED = ("harness",)


def _pins_sha(doc: dict) -> str:
    """A job's pins document as one digest, whatever its spacing: what a checkouts record is about."""
    return hashlib.sha256(json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _said_state(e) -> str:
    return "not named" if not e else "absent" if e.get("absent") else "not a git checkout" if not e.get("git") \
        else f"at {e['git']}, " + ("clean" if e.get("tracked_changes") == CLEAN else "with tracked changes")


def _commit_file(top, name) -> str | None:
    f = Path(top) / str(name)
    try:
        return f.read_text(encoding="utf-8").strip() if name and f.is_file() else None
    except (OSError, UnicodeDecodeError):
        return None


def _record_text(text: str) -> dict:
    """The checkouts record a submit recipe's shell lines wrote (CHECKOUTS: one line a field or a checkout, TAB-
    separated), as the job compares it: {field: value, "harness": entry, "checkouts": {role: entry}}."""
    rec: dict = {"checkouts": {}}
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    for n, ln in enumerate(lines, 1):
        f = ln.split("\t")
        if f[0] == "checkout" and len(f) == 6:
            role, top, at, tracked, cf = f[1:]
            if not top or not (tracked in ("clean", "-") or re.fullmatch(r"[0-9a-f]{64}", tracked)):
                raise ValueError(f"line {n}: {role}'s tracked changes are neither `clean` nor a digest")
            e = {"path": top, "absent": True} if at == "absent" else {
                "path": top, "git": None if at == "-" else at, "tracked_changes": CLEAN if tracked == "clean" else
                None if tracked == "-" else tracked, "commit_file": None if cf == "-" else cf}
            if role == "harness":
                rec["harness"] = e
            else:
                rec["checkouts"][role] = e
        elif len(f) == 2 and f[0] in ("record", "rundir", "job", "pins", "commit_file", "made_at") and f[0] not in rec:
            rec[f[0]] = f[1]
        else:
            raise ValueError(f"line {n} is not a line of a checkouts record")
    if rec.get("record") != RECORD:
        raise ValueError(f"its first line does not say `record\t{RECORD}`")
    rec["pins_sha256"] = rec.get("pins")
    return rec


def _record_of(path, doc: dict) -> tuple:
    """(the checkouts record a job's submit recipe made, None) or (None, why it is not read): it must be this
    run's (it names the run folder it lies in) and this job's (the pins it was compared with)."""
    p = Path(path)
    try:
        rec = _record_text(p.read_text(encoding="utf-8"))
        about = Path(str(rec["rundir"])).resolve()
    except (OSError, ValueError, KeyError, TypeError) as e:
        return None, (f"the record of the checkouts this job's submit recipe makes where git is, {p}, cannot be read "
                      f"({type(e).__name__}): a generated job runs no git where it runs; submit it by its own recipe")
    if about != p.resolve().parent:
        return None, (f"the checkouts record {p} was made for the run {rec['rundir']}, not this one ({p.resolve().parent}): "
                      f"a record is about one run")
    if rec.get("pins_sha256") != _pins_sha(doc):
        return None, (f"the checkouts record {p} was made for another job (pins {str(rec.get('pins_sha256'))[:12]}, "
                      f"this job's {_pins_sha(doc)[:12]}): generate and submit the job again")
    return rec, None


def _from_record(now: dict, rec: dict, doc: dict, dirs: dict) -> tuple:
    """(the set with each checkout as the record read it at submission, lines, differences): where the job runs only
    what needs no git is compared - the site's commit file, when it declares one; otherwise each check is said as
    not made, and why (autodev W056 fix 1, R0). A checkout that was not a git checkout at submission is read here
    from its files (`_nogit_state`, `dirs`: `_checkout_dirs`), as where the job was generated: the recipe's shell
    lines read no files' digest."""
    cf, lines, bad = doc.get("commit_file"), [], []
    h = rec.get("harness") or {}
    if doc.get("harness") and (h.get("git") != doc["harness"] or h.get("tracked_changes") != CLEAN):
        bad.append(f"harness {h.get('path', '')} (this job expects {doc['harness']}, clean; at submission {_said_state(h)})")
    elif doc.get("harness"):
        lines.append(f"  harness: at {h['git']}, clean at submission (git, the submit recipe's record); " + (
            f"here {cf} names it" if cf else "not compared here: the site declares no commit file, and this job runs "
            "no git where it runs"))
    for k in sorted(k for k in now if k.endswith("@checkout")):
        e = now[k]
        if e.get("absent"):
            continue                             # absent where the job runs: compared as absent
        r = (rec.get("checkouts") or {}).get(k)
        if not isinstance(r, dict) or not r.get("path"):
            bad.append(f"{k} {e['path']} (the submit recipe's record names no such checkout)")
            continue
        if r.get("absent"):
            bad.append(f"{k} {e['path']} (absent where the job was submitted, present here: the submit recipe's record "
                       f"read nothing of it)")
            continue
        top, d = Path(r["path"]).resolve(), Path(e["path"]).resolve()
        if d != top and top not in d.parents:
            bad.append(f"{k} (the record read the checkout {top} at submission; this job reads {d})")
            continue
        if not r.get("git"):
            now[k] = _nogit_state(*dirs[k]) if k in dirs else now[k]
            lines.append(f"  here: {k} {top}: not a git checkout at submission; its files are compared here")
            continue
        now[k] = {"path": r["path"], "git": r.get("git"), "tracked_changes": r.get("tracked_changes")}
        if not cf:
            lines.append(f"  not compared here: {k} {top} (the site declares no commit file, and this job runs no git "
                         f"where it runs: its commit and clean work tree are the submit recipe's record)")
        else:
            got = _commit_file(top, cf)
            if got != r["git"]:
                bad.append(f"{k} {top} (git read {r['git']} at submission; here its {cf} names {got or 'nothing'}: "
                           f"the checkout moved after the job was submitted)")
            else:
                lines.append(f"  here: {k} {top}: its {cf} names {got}, the commit git read at submission")
    return now, lines, bad


def _said_declared(req: dict, answers, now: dict) -> list:
    """PINS.txt's lines of what the declaration says beyond digests (autodev W056, D6): each `present` input that is
    there, each `named` one as its text, and per reader how many rows name a file in each column it declares (a
    misspelt column reads 0 of n)."""
    out = []
    for d in declared(req, answers):
        e = now.get(d["role"]) or {}
        if d["check"] == "present" and e.get("present"):
            out.append(f"  present: {d['role']} {e['path']} ({d['by']}: there and readable; its content is not compared)")
        elif d["check"] == "named":
            out.append(f"  named: {d['role']} {d['path']} ({d['by']}: recorded as its text, never looked at)")
        out += [f"  read: {d['role']} {col}: {k} of {n} rows name a file ({by})" for col, k, n, by in d.get("read") or []]
    return out


def expected(req: dict, file, answers: dict | None = None, checkouts=None, present: bool = False) -> tuple:
    """(holds, lines, differences): the run's set now - with the job's answers (autodev W049) - against
    the set a job was generated for (autodev W042 fix 2, C), content only (a copy keeps no modification
    time); a file absent where the job was generated is checked here for the first time, and said.
    `checkouts` (a generated job, where it runs: autodev W056 fix 1): no git is run; each checkout is the
    record its submit recipe made where git is, and the site's commit file is compared here. `present` (a
    generated job's CHECK_ONLY preflight, autodev W056 fix 1, A1): every input of the set must be present and
    readable where the job runs, a file absent where it was generated too."""
    try:
        doc = json.loads(Path(file).read_text())
        then = doc["files"]
    except (OSError, ValueError, KeyError) as e:
        return False, [f"  differs: the job's record {file} cannot be read ({e})"], [("record", None, None)]
    pre, extra = [], []
    if checkouts is None:
        now = {k: v for k, v in run_inputs(req, answers).items() if k not in JOB_UNPINNED}
    else:
        rec, why = _record_of(checkouts, doc)
        if why:
            return False, [f"  differs: {why}"], [("checkouts", None, None)]
        now, pre, extra = _from_record({k: v for k, v in run_inputs(req, answers, git=False).items()
                                        if k not in JOB_UNPINNED}, rec, doc, _checkout_dirs(req))
    then = {k: v for k, v in then.items() if k not in JOB_UNPINNED}
    stated = {k: v for k, v in then.items() if isinstance(v, dict) and v.get("stated")}
    # a stated tool's commit, clean, stands for the files of the param naming it (autodev W049 fix 1)
    now = {k: v for k, v in now.items() if not any(_under(k, r) for r in stated)}
    a, b = flat(then, mtime=False), flat(now, mtime=False)
    d = differ(a, b, here_only=True)
    bad = {k for k, _x, _y in d}
    here = [k for k in sorted(b) if a.get(k) in (None, "absent") and k not in bad]
    gone = [k for k in sorted(now) if present and k not in bad and (now[k].get("absent") or now[k].get("unreadable"))]
    lines = [f"  pinned: {sum(1 for v in a.values() if v != 'absent')} of the run's files as the job was generated; "
             f"{len(here)} checked here only"]
    lines += _said_declared(req, answers, now)
    lines += [f"  only here: {k} {now[k]['path']}" for k in here[:40]]
    # a tool the job states (--tool, autodev W049 fix 1): its checkout here against the commit stated, clean
    where = "here" if checkouts is None else "at submission"
    lines += [f"  tool: {v['stated']} at {v['git']}, clean, as this job states ({k} {now[k]['path']})"
              + ("" if checkouts is None else ": read where the job was submitted") for k, v in sorted(stated.items()) if k not in bad]
    lines += pre + [f"  differs: {x}" for x in extra]
    lines += [f"  differs: {k} {(now.get(k) or {}).get('path', '')} ({stated[k]['stated']}: this job expects "
              f"{stated[k]['git']}, clean; {where} {_said_state(now.get(k))})" if k in stated else
              f"  differs: {k} {(now.get(k) or then.get(k) or {}).get('path', '')} ({x or 'not named'} when the job "
              f"was generated, {y or 'not named'} now)" for k, x, y in d]
    lines += [f"  differs: {k} {now[k]['path']} (" + ("absent" if now[k].get("absent") else f"unreadable: "
              f"{now[k]['unreadable']}") + " where the job runs: its preflight finds every input present and readable "
              "before the first tool call)" for k in gone]
    return not d and not extra and not gone, lines, d + [(x.split(" ", 1)[0], None, None) for x in extra] + [
        (k, None, None) for k in gone]


# ---------------------------------------------------------------------------- what a submit recipe runs
#: WHAT A SUBMIT RECIPE RUNS (autodev W056 fix 1, amendment; the PI's standing rule for the site the jobs are for):
#: where a job is SUBMITTED nothing runs but git, the shell's own small tools and the scheduler's submit command - no
#: python, no tool, no compute; every python process belongs inside a submitted job. THE ONE LIST: `recipe_refused`
#: reads a recipe's text against it, `job_text` refuses to write a recipe (its own lines and the site's `submit:`
#: lines) that runs another command, and one test walks the recipe of every job shape the generator writes. Not on
#: it: a builtin that runs a string or a file as commands (eval, exec, source, `.`, trap, builtin, `command` but
#: `command -v`). The sha256 tool is whichever is there; the submit command is the scheduler's the site names
#: (`executor: pbs`: `qsub`, PBS_COMMANDS; a site's `pbs.commands` are the executor's, inside a job). A function the
#: recipe defines is its body's commands.
RECIPE_PROGRAMS = ("cd", "mkdir", "pwd", "date", "cat", "printf", "echo", "test", "[", "head", "cut", "tr", "git",
                   "sha256sum", "shasum")
RECIPE_BUILTINS = (":", "true", "false", "local", "return", "umask", "set", "unset", "shift", "exit", "read",
                   "command -v")
#: The recipe's own shell (W056 fix 1, amendment): it reads each checkout with git where the job is submitted and
#: writes CHECKOUTS, or refuses by name before anything is made. `ck_one ROLE PATH WANT WHY`: WANT is the commit the
#: job expects, `-` (not a git checkout when the job was generated) or `any` (absent then: checked where it runs); a
#: tracked change is refused always - read as `_git_state` reads it (its options; status, the diff against HEAD, and a
#: file git is told not to look at); WHY is the refusal's words. No line begins with `(` (gate.py's `recipe_of` reads
#: such a line as a remark) and none but the last names the submit command.
RECIPE_SHELL = (
    r"""CK=; CK_BAD=; CK_REC=; CK_CLEAN=""" + CLEAN + r"""; CK_T=$(printf '\t'); CK_N=$(printf '\nx'); CK_N=${CK_N%x}""",
    r"""ck_git() { git --no-optional-locks --no-replace-objects -c core.fsmonitor=false -c core.trustctime=true """
    r"""-c core.checkStat=default -C "$@"; }""",
    r"""ck_sha() { if command -v sha256sum >/dev/null 2>&1; then sha256sum; else shasum -a 256; fi | cut -d ' ' -f 1; }""",
    r"""ck_row() { local v w=$1; [ "$1" != checkout ] || w="$1 $2"; for v in "$@"; do if [ "${v#*"$CK_T"}" != "$v" ] """
    r"""|| [ "${v#*"$CK_N"}" != "$v" ]; then CK_BAD="$CK_BAD; the record's $w line: a value holds a TAB or a newline, """
    r"""which a record of one line a checkout cannot hold"; return 0; fi; done""",
    r"""  CK_REC="$CK_REC$1"; shift; for v in "$@"; do CK_REC="$CK_REC$CK_T$v"; done; CK_REC="$CK_REC$CK_N"; }""",
    r"""ck_one() { local w=$1 p=$2 d top at x hid l t k s=- f=- said; [ "$1" != harness ] || w='the harness'""",
    r"""  if [ ! -e "$p" ]; then top=$p; at=absent; k=absent; said=absent""",
    r"""  else d=$p; [ -d "$d" ] || { d=${p%/*}; d=${d:-/}; }""",
    r"""    if top=$(ck_git "$d" rev-parse --show-toplevel 2>/dev/null) && at=$(ck_git "$d" rev-parse HEAD 2>/dev/null); then""",
    r"""      x=$(ck_git "$d" ls-files -v 2>/dev/null | cut -c 1 | tr -cd abcdefghijklmnopqrstuvwxyzS) || x=; hid=""",
    r"""      [ -z "$x" ] || hid=$(ck_git "$d" ls-files -v 2>/dev/null | while IFS= read -r l; do t=${l:0:1}; if [ "$t" = S ] """
    r"""|| [ -z "${t#[abcdefghijklmnopqrstuvwxyz]}" ]; then printf '%s\n' "$l"; fi; done) || hid=""",
    r"""      s=$( { ck_git "$d" status --porcelain=v1 --untracked-files=no 2>/dev/null || printf '\1'; printf '\0'; """
    r"""ck_git "$d" diff --binary HEAD 2>/dev/null || printf '\1'; [ -z "$hid" ] || printf '\0%s' "$hid"; } | ck_sha )""",
    r"""      k=$at:$s; said="at $at, clean"; [ "$s" = "$CK_CLEAN" ] || said="at $at, with tracked changes"; """
    r"""[ "$s" != "$CK_CLEAN" ] || s=clean""",
    r"""      if [ -n "$CK_CF" ]; then x=$(cat "$top/$CK_CF" 2>/dev/null) || x=; if [ "$x" = "$at" ]; then f=$x; else """
    r"""CK_BAD="$CK_BAD; $w $top: its $CK_CF names ${x:-nothing}, git reads $at (the site declares $CK_CF as every """
    r"""checkout's commit, which the job compares where it runs)"; fi; fi""",
    r"""    else top=$d; at=-; k=-; said='not a git checkout'; fi""",
    r"""  fi""",
    r"""  [ "$3" = any ] || [ "$3" = "$k" ] || CK_BAD="$CK_BAD; $w $top$4; here $said""" + '"',
    r"""  ck_row checkout "$1" "$top" "$at" "$s" "$f"; }""",
    r"""ck_files() ( umask 222 && printf '%s' "$CK_REC" > "$RUNDIR/""" + CHECKOUTS + r"""" && printf '%s\n' """
    r""""${HC:-not a git checkout}" > "$RUNDIR/TOOL_HEAD.txt" )""",
    r"""ck_made() { if [ -n "$CK_BAD" ]; then echo "REFUSED, nothing submitted: ${CK_BAD#; }" >&2; return 1; fi""",
    r"""  if ! mkdir "$RUNDIR" 2>/dev/null || ! mkdir "$RUNDIR/logs"; then echo "REFUSED, nothing submitted: the run """
    r"""folder $RUNDIR cannot be made: a run folder is new" >&2; return 1; fi""",
    r"""  ck_files || return 1; CK=$(ck_sha < "$RUNDIR/""" + CHECKOUTS + r"""") || CK=; [ -n "$CK" ]; }""",
)
_SH_OPEN = {"if", "then", "else", "elif", "while", "until", "do", "!", "{"}
_SH_CLOSE = {"fi", "done", "}"}
_SH_OPS = ("&&", "||", ";;", "|&", "<<<", "<<", ">>", "<&", ">&", "<>", ">|", "&>", ";", "&", "|", "(", ")", "<", ">")
_SH_REDIRECT = {"<", ">", ">>", "<&", ">&", "<>", ">|", "&>", "<<<"}
_SH_ASSIGN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")


def _sh_quoted(s: str, i: int, cmds: list, defs: set) -> tuple:
    """(the index past a double-quoted text, its value), from just inside its opening quote."""
    out = []
    while i < len(s):
        ch = s[i]
        if ch == '"':
            return i + 1, "".join(out)
        if ch == "\\":
            out.append(s[i + 1:i + 2])
            i += 2
        elif ch == "`":
            cmds.append("`")                     # a backquoted command is not read: said as itself
            i += 1
        elif s.startswith("$(", i):
            i = _sh_sub(s, i + 2, cmds, defs)
            out.append("$(...)")
        elif s.startswith("${", i):
            i = _sh_brace(s, i + 2, cmds, defs)
            out.append("${...}")
        else:
            out.append(ch)
            i += 1
    cmds.append('"')                             # never closed
    return i, "".join(out)


def _sh_brace(s: str, i: int, cmds: list, defs: set) -> int:
    """The index past a `${...}`, its own substitutions walked."""
    while i < len(s):
        ch = s[i]
        if ch == "}":
            return i + 1
        if ch == '"':
            i, _v = _sh_quoted(s, i + 1, cmds, defs)
        elif ch == "'":
            j = s.find("'", i + 1)
            i = len(s) if j < 0 else j + 1
        elif ch == "\\":
            i += 2
        elif s.startswith("$(", i):
            i = _sh_sub(s, i + 2, cmds, defs)
        elif s.startswith("${", i):
            i = _sh_brace(s, i + 2, cmds, defs)
        elif ch == "`":
            cmds.append("`")
            i += 1
        else:
            i += 1
    cmds.append("${")
    return i


def _sh_sub(s: str, i: int, cmds: list, defs: set) -> int:
    """A `$(...)` (or `<(...)`) walked: its commands into `cmds`; the index past its `)`."""
    toks, i = _sh_tokens(s, i, cmds, defs, sub=True)
    _sh_walk(toks, cmds, defs)
    return i


def _sh_tokens(s: str, i: int, cmds: list, defs: set, sub: bool = False) -> tuple:
    """([("w", a word's value) or ("op", an operator)], the index past it): a newline is a `;`."""
    toks, word, depth = [], None, 0

    def end():
        nonlocal word
        if word is not None:
            toks.append(("w", word))
            word = None
    while i < len(s):
        ch = s[i]
        if sub and ch == ")" and depth == 0:
            end()
            return toks, i + 1
        if ch in " \t":
            end()
            i += 1
        elif ch == "\n":
            end()
            toks.append(("op", ";"))
            i += 1
        elif ch == "#" and word is None:
            j = s.find("\n", i)
            i = len(s) if j < 0 else j
        elif ch == "\\":
            word = (word or "") + ("" if s[i + 1:i + 2] == "\n" else s[i + 1:i + 2])
            i += 2
        elif ch == "'":
            j = s.find("'", i + 1)
            if j < 0:
                cmds.append("'")
                return toks, len(s)
            word = (word or "") + s[i + 1:j]
            i = j + 1
        elif ch == '"':
            i, v = _sh_quoted(s, i + 1, cmds, defs)
            word = (word or "") + v
        elif ch == "`":
            cmds.append("`")
            i += 1
        elif s.startswith("$(", i) or (ch in "<>" and s[i + 1:i + 2] == "("):
            i = _sh_sub(s, i + 2, cmds, defs)
            word = (word or "") + "$(...)"
        elif s.startswith("${", i):
            i = _sh_brace(s, i + 2, cmds, defs)
            word = (word or "") + "${...}"
        elif ch in ";&|()<>":
            if ch in "<>" and word is not None and word.isdigit():
                word = None                      # a descriptor's number: part of its redirection
            end()
            op = next(o for o in _SH_OPS if s.startswith(o, i))
            depth += {"(": 1, ")": -1}.get(op, 0)
            toks.append(("op", op))
            i += len(op)
        else:
            word = (word or "") + ch
            i += 1
    end()
    if sub:
        cmds.append("$(")                        # never closed
    return toks, i


def _sh_walk(toks: list, cmds: list, defs: set):
    """Each command word of a token list into `cmds`; each function it defines into `defs`."""
    expect, i, n = True, 0, len(toks)
    while i < n:
        kind, v = toks[i]
        if kind == "op":
            if v in _SH_REDIRECT:
                i += 2                           # the redirection and its target
                continue
            if v == "<<":
                cmds.append("<<")                # a here-document is not read: said as itself
                i += 2
                continue
            expect = v != ")"
            i += 1
            continue
        if not expect:
            i += 1
        elif v in _SH_OPEN:
            i += 1
        elif v in _SH_CLOSE:
            expect, i = False, i + 1
        elif _SH_ASSIGN.match(v):
            i += 1
        elif v == "for":                         # for NAME [in WORDS]; do
            while i < n and not (toks[i] == ("w", "do") and toks[i - 1] == ("op", ";")):
                i += 1
            i += 1
        elif toks[i + 1:i + 3] == [("op", "("), ("op", ")")]:
            defs.add(v)                          # a function: its body is walked as it comes
            i += 3
        else:
            if v == "command" and toks[i + 1:i + 2] == [("w", "-v")]:
                v, i = "command -v", i + 1
            cmds.append(v)
            expect, i = False, i + 1


def recipe_commands(text: str) -> tuple:
    """(every command a shell text runs, as its word, the functions it defines): the first word of each simple
    command - after `;`, `&&`, `||`, `|`, `&`, a newline, `(`, `{`, `!`, `if then else elif while until do` - and
    in every `$(...)`, `${...}` and process substitution, recursively; assignments and redirections before it
    skipped. What it does not read as shell (a backquote, a here-document, a quote never closed, `case`, `[[`) is
    said as itself, so it is never on the list."""
    cmds: list = []
    defs: set = set()
    toks, _i = _sh_tokens(text, 0, cmds, defs)
    _sh_walk(toks, cmds, defs)
    return cmds, defs


def recipe_refused(text: str, submit: str = "qsub") -> list:
    """The commands a recipe's text runs that a submit recipe may not: any but RECIPE_PROGRAMS, RECIPE_BUILTINS, the
    site's submit command and a function the text defines."""
    cmds, defs = recipe_commands(text)
    ok = {*RECIPE_PROGRAMS, *RECIPE_BUILTINS, str(submit), *defs}
    return [c for c in cmds if c not in ok]


def _sh(v, what: str, path: bool = False) -> str:
    """A value as one shell word of a recipe line (a comment line of the job), quoted; a path's `~/` left for that
    machine's shell. A value holding a newline or another control character is refused by name: it would end the
    comment line and run as a line of the job's body, and the record holds no TAB or newline."""
    import shlex
    s = str(v)
    if re.search(r"[\x00-\x1f\x7f]", s):
        raise RequestError(f"--job: {what} {s!r} holds a newline, a TAB or another control character, which a job's "
                           f"submit recipe (its comment lines) and its checkouts record cannot hold")
    return ('"$HOME"/' + shlex.quote(s[2:])) if path and s.startswith("~/") else shlex.quote(s)


def _checkout_words(req: dict) -> dict:
    """{checkout role: the path its declared checkout param names, as the request writes it}: what a job's submit recipe
    reads where the job is submitted, on that machine (`~/` is its home) - never a path of the machine generating it."""
    return {role: v for _p, _x, role, v, _got in _checkouts(req)}


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
    cf = (job or {}).get("commit_file")
    if cf is not None and not re.fullmatch(STAGE_WORD, str(cf)):   # spliced into the job's shell lines and paths
        raise RequestError(f"{site}/job.yml: commit_file {cf!r} is the name of the file in every checkout's top "
                           f"directory holding its commit (letters, digits, `_`, `-`, `.`), not a path")
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


HEX40 = re.compile(r"[0-9a-f]{40}")


def _under(k: str, checkout_role: str) -> bool:
    """Whether role `k` is the param a `<stage>.<param>@checkout` role is found from, or a file under it."""
    p = checkout_role[:-len("@checkout")]
    return k == p or k.startswith((p + "/", p + "#", p + ">"))


def _stated(req: dict, tools: list | None, pins: dict) -> dict:
    """{checkout role: (tool, commit)}: each `--tool <Tool>=<40 hex>` a job is generated with (autodev W049
    fix 1), by the name its adapter wraps (`wraps.tool`, the name `setup/autodev/gate.py --tool` moves a
    cluster checkout by). A name no stage runs from a checkout, a commit that is not 40 hex digits, or one
    tool given twice is refused by name, before the job is written."""
    roles: dict = {}
    for p, _x, role, _v, _got in _checkouts(req):
        if role in pins:
            roles.setdefault(str(p["wraps"].get("tool")), []).append(role)
    got: dict = {}
    for t in tools or []:
        name, sep, commit = str(t).partition("=")
        if not sep or name not in roles:
            raise RequestError(f"--tool {t!r}: no stage of this request runs a tool named {name!r} from a "
                               f"checkout; its tools: {', '.join(sorted(roles)) or 'none'} (--tool TOOL=COMMIT)")
        if not HEX40.fullmatch(commit):
            raise RequestError(f"--tool {t!r}: a tool's commit is its 40 hexadecimal digits, in lower case, as "
                               f"`git rev-parse HEAD` prints it - not a branch, a tag or a short one")
        if name in got:
            raise RequestError(f"--tool {name} is given twice: a job runs one commit of each tool")
        got[name] = commit
    return {r: (n, c) for n, c in got.items() for r in roles[n]}


def job_text(req: dict, job_path, answers: list | None = None, by: str | None = None,
             predict=None, check=None, purpose: str | None = None, where: str | None = None,
             tools: list | None = None) -> str:
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
    from .services.executor import PBS_COMMANDS, PBS_REQUIRED, PbsExecutor
    q = shlex.quote
    job_path = Path(job_path).resolve()
    jobs = job_path.parent
    if jobs.name != "jobs":
        raise RequestError(f"--job {job_path}: a job lives in its stage's jobs/ directory (the run key "
                           f"takes the stage's name from it)")
    stage = jobs.parent.name
    for what, v in (("the job's stage directory", stage), ("--purpose", purpose)):
        if v is not None and not re.fullmatch(STAGE_WORD, v):   # spliced into the run key and shell lines
            raise RequestError(f"--job: {what} is {v!r}; it is written into the job's run key and its shell "
                               f"lines as it is: letters, digits, `_`, `-`, `.`")
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
    given, _new = answers_of(req, answers, by)   # refused here, not on the cluster (autodev W049)
    tail = "".join(f" --answer {q(a)}" for a in (answers or [])) + (f" --by {q(by)}" if by else "")
    hn = str(job["harness"])
    hn_sh = _sh(hn, "the site's harness", path=True)
    py_sh = _sh(job["python"], "the site's python", path=True)
    at = str(where or jobs)
    at = at if re.fullmatch(r"[~A-Za-z0-9_./-]+", at) else _sh(at, "--where")   # `~` left for the shell to read
    key = f"$(date -u +%Y%m%dT%H%M%SZ)__sch-${{HC:0:7}}__{stage}" + (f"__{purpose}" if purpose else "")
    name = re.sub(r"[^A-Za-z0-9_]", "_", f"sch_{stage}")[:15]
    reports = " ".join(f'"$RUNDIR"/{p["stage"]}/report/report.json' for p in req["stages"])
    # THE JOB PINS THE RUN'S WHOLE SET (autodev W042 fix 2, C): B's set as it is where the job is
    # generated; what is absent here is named, and checked only where the job runs.
    pins = {k: v for k, v in run_inputs(req, given).items() if k not in JOB_UNPINNED}
    # A JOB STATES THE COMMIT OF EACH TOOL IT EXPECTS (autodev W049 fix 1, ATTACKS 33): a checkout named by
    # --tool is pinned as that commit and a clean work tree, and checked against them where the job runs -
    # never against this machine's checkout, which may be absent or at another commit
    for role, (tool, at_commit) in _stated(req, tools, pins).items():
        pins[role] = {"path": pins[role].get("path"), "git": at_commit, "tracked_changes": CLEAN, "stated": tool}
        for k in [k for k in pins if _under(k, role)]:   # the stated commit stands for the param's files
            del pins[k]
    absent = [k for k, v in pins.items() if v.get("absent")]
    said_tools = [re.sub(r"[\x00-\x1f\x7f]", "?", f"#   tool      {p['wraps'].get('tool')} ({p['stage']}): " + (
        f"expects {e['git']}, clean (--tool; read where the job is submitted, by its recipe: another commit or a "
        f"tracked change is refused there)"
        if e.get("stated") else "absent here and not stated (--tool): checked only where the job runs"
        if e.get("absent") else f"as it is here, {e.get('git') or 'not a git checkout'} (no --tool: the job refuses "
        f"any other)")) for p, _x, role, _v, _g in _checkouts(req) if (e := pins.get(role))]
    # by role, without where the file lies here: the roles are the same on every machine, and a path of
    # this workstation's has no place in a job that runs on another
    cf = job.get("commit_file")
    pins_doc = json.dumps({"generated_at": _now(), "policy": POLICY, "harness": commit, "commit_file": cf,
                           "files": {k: {x: y for x, y in v.items() if x != "path"} for k, v in pins.items()}},
                          sort_keys=True)
    # THE SUBMIT RECIPE RUNS ONLY RECIPE_PROGRAMS (autodev W056 fix 1, amendment): its own shell reads each checkout the
    # job pins with git where the job is submitted - by the path the request writes, never this machine's - and makes
    # the record or refuses by name; a recipe that would run anything else is refused here, before the job is written
    sub = PBS_COMMANDS[0]                        # the scheduler the site names (executor: pbs) submits with it
    sub_sh, runs = _sh(sub, "the site's submit command", path=True), _sh(job["runs"], "the site's runs")
    jq, site_lines = _sh(job_path.name, "the job's file name"), [str(ln) for ln in (job.get("submit") or [])]
    for ln in site_lines:
        _sh(ln, "the site's submit: line")       # a newline would end the comment and run in the job's body
        if set(recipe_commands(ln)[0]) & {"'", '"', "$(", "${", "`"}:
            raise RequestError(f"--job: the site's submit: line {ln!r} is not a whole line of shell (a quote or a "
                               f"substitution never closed): every recipe line after it would read as another")
    words, calls = _checkout_words(req), []
    for role in sorted(_checkout_dirs(req)):
        e = pins.get(role) or {}
        # WANT: a stated tool at its commit, clean; any other as it was when the job was generated (its commit and
        # the digest of its tracked changes, `_git_state`'s); `-` not a git checkout then; `any` absent then
        want, why = (f"{e['git']}:{CLEAN}", f" ({e['stated']}): this job expects {e['git']}, clean") if e.get("stated") \
            else ("any", ": absent where the job was generated") if e.get("absent") else (
                f"{e['git']}:{e['tracked_changes']}", f": not as it was when the job was generated ({_said_state(e)})"
            ) if e.get("git") else ("-", ": not as it was when the job was generated (not a git checkout)")
        calls.append(f"ck_one {_sh(role, 'a checkout role')} {_sh(words[role], role, path=True)} {want} {_sh(why, role)}")
    recipe = [
        f"cd {at}", *site_lines,
        f"HN={hn_sh}; HC=$(git -C \"$HN\" rev-parse HEAD)",
        "[ -z \"$(git -C \"$HN\" status --porcelain)\" ] && echo HARNESS-CLEAN",
        f"mkdir -p {runs}/{stage}; RUNS=$(cd {runs}/{stage} && pwd -P)",
        f"RUNDIR=$RUNS/{key}",
        *RECIPE_SHELL,
        f"CK_CF={cf or ''}; CK_REQ={_sh(os.path.relpath(req['path'], jobs), 'the request')}; CK_JOB={jq}; "
        "CK_X=$(ck_sha 2>/dev/null < \"$CK_REQ\") || CK_X=; CK_X=${CK_X:-unreadable}",
        f"[ \"$CK_X\" = {req['sha256']} ] || CK_BAD=\"$CK_BAD; the request $CK_REQ has sha256 ${{CK_X:0:12}}, and $CK_JOB "
        f"was generated for {req['sha256'][:12]}: generate the job again from the request as it is\"",
        "[ \"${RUNDIR#*,}\" = \"$RUNDIR\" ] || CK_BAD=\"$CK_BAD; the run folder $RUNDIR holds a comma, which the "
        "scheduler's -v list cannot pass\"",
        f"ck_row record {RECORD}; ck_row rundir \"$RUNDIR\"; ck_row job \"$CK_JOB\"; ck_row pins "
        f"{_pins_sha(json.loads(pins_doc))}; ck_row commit_file \"${{CK_CF:--}}\"; ck_row made_at "
        "\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"",
        f"ck_one harness \"$HN\" {f'{commit}:{CLEAN}' if commit else 'any'} " + _sh(f": this job expects {commit}, clean" if commit else
                                                         ": not a git checkout when the job was generated", "the harness"),
        *calls,
        "ck_made && echo CHECKOUTS-CLEAN",
        f"[ -n \"$CK\" ] && {sub_sh} -o \"$RUNDIR/logs/\" -v \"RUNDIR=$RUNDIR,HARNESSHEAD=$HC,CHECKOUTS_SHA256=$CK\" {jq}"]
    bad = recipe_refused("\n".join(recipe), sub)
    if bad:
        raise RequestError(f"--job: the submit recipe would run {', '.join(dict.fromkeys(bad))}; where a job is "
                           f"submitted only {' '.join(RECIPE_PROGRAMS)}, the shell's builtins that run no other program "
                           f"and {sub} run (the site's submit: lines are the recipe's too): every python process "
                           f"belongs inside a submitted job")
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
        "#   checkouts this job runs no git where it runs: its submit recipe reads every checkout with git where the job "
        "is submitted (its own shell lines; no python runs there) into $RUNDIR/" + CHECKOUTS + ", which the job refuses "
        "missing, changed after "
        "submission, about another run or job, or naming another commit; where it runs it compares " + (
            f"each checkout's {cf} (the site's commit file)" if cf else "nothing more: the site declares no commit file, "
            "so a checkout moved between submission and the job's start is not seen there (said in PINS.txt)"),
        "#   preflight CHECK_ONLY=1 (qsub -v; gate.py preflight) runs everything before the first tool call - the "
        "checkouts and pins, every input present and readable where the job runs" + (
            ", the checks graded on their own reference runs" if check else "") + " - and stops: PREFLIGHT: OK or "
        "PREFLIGHT: MISSED (n), one line per miss before it; no stage runs, nothing is sealed",
        f"#   inputs    {len(pins) - len(absent)} files the run reads, pinned as generated, its answers' among them (the "
        f"job refuses another set: `sch plan --request REQUEST --answer ... --expect PINS.json`); {len(absent)} checked "
        f"only where it runs" + (":" if absent else ""),
        *[re.sub(r"[\x00-\x1f\x7f]", "?", f"#     on the cluster only: {k} {os.path.relpath(pins[k]['path'], jobs) if not str(pins[k]['path']).startswith(str(Path.home())) else '~/' + os.path.relpath(pins[k]['path'], Path.home())}"
                 ) for k in absent],
        *said_tools,
        f"#   stages    " + ", ".join(f"{p['stage']} {p['plugin']}" + (f" [{', '.join(f'{k}={v}' for k, v in sorted(p['resources'].items()))}]" if p.get("resources") else "") for p in req["stages"]),
        f"#   this job  {cfg.get('queue_chosen') or 'the site block queue'}",
        f"#   answers   {tail.strip() or 'none'}",
        "#", "# THE PREDICTION, WRITTEN BEFORE ANY RUN:", *pre, "#",
        "# The submit recipe (the login node; the CLEAN lines must print before the qsub). It runs git, the shell's own",
        "# small tools and the submit command, nothing else (no python): it reads each checkout with git and writes",
        f"# $RUNDIR/{CHECKOUTS}, one TAB-separated line a checkout, or refuses by name before anything is made.",
        "# SUBMIT-BEGIN",
        *[f"#   {ln}" for ln in recipe],
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
        # CHECK_ONLY (autodev W056 fix 1, A1): a verdict is recorded; a preflight prints its misses once, at its end
        "say() { if [ \"${CHECK_ONLY:-}\" = 1 ]; then cat >> \"$VERDICTS\"; else tee -a \"$VERDICTS\"; fi; }",
        "finish() { s=$?",
        "  set +e",
        "  rm -rf \"$RUNDIR/cache\" 2>/dev/null",
        "  if [ \"${CHECK_ONLY:-}\" = 1 ]; then   # THE PREFLIGHT: no stage ran; nothing is sealed; no GATE line",
        "    n=$(grep -c '^VERDICT.*MISSED' \"$VERDICTS\" 2>/dev/null || true); n=${n:-0}",
        "    if [ \"$s\" -ne 0 ] && [ \"$n\" -eq 0 ]; then echo \"VERDICT (preflight): MISSED - the job stopped with exit $s "
        "before its preflight ended (see its log)\" >> \"$VERDICTS\"; n=1; fi",
        "    if [ \"$n\" -eq 0 ]; then pf=\"PREFLIGHT: OK\"; else pf=\"PREFLIGHT: MISSED ($n)\"; s=1; fi",
        "    grep '^VERDICT.*MISSED' \"$VERDICTS\" 2>/dev/null",
        "    { echo \"exit=$s\"; echo \"jobid=${PBS_JOBID:-none}\"; echo \"harnesshead=${HARNESSHEAD:-unknown}\"; hostname",
        "      date -u +%Y-%m-%dT%H:%M:%SZ; cat \"$VERDICTS\" 2>/dev/null; echo \"$pf\"; } > \"$RUNDIR/PREFLIGHT.txt\"",
        "    find \"$RUNDIR\" -type f -not -path \"$RUNDIR/logs/*\" -exec chmod a-w {} +",
        "    echo \"$pf\"",
        "    exit \"$s\"",
        "  fi",
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
        "pin() { \"$PY\" -c 'import hashlib, sys; h = hashlib.sha256(); f = open(sys.argv[1], \"rb\"); "
        "[h.update(b) for b in iter(lambda: f.read(1 << 20), b\"\")]; print(h.hexdigest())' \"$1\"; }",
        # THE CHECKOUTS, READ WHERE THE JOB WAS SUBMITTED (autodev W056 fix 1, R0): this job runs no git; its recipe
        # read every checkout with git into the record, whose sha256 it passed with qsub -v
        f"ck=$(pin \"$RUNDIR/{CHECKOUTS}\" 2>/dev/null || echo absent)",
        "if [ -z \"${CHECKOUTS_SHA256:-}\" ] || [ \"$ck\" != \"$CHECKOUTS_SHA256\" ]; then",
        f"  echo \"VERDICT (pins): MISSED - the record of the checkouts its submit recipe reads where git is, $RUNDIR/{CHECKOUTS}, "
        "is ${ck}; the recipe passed ${CHECKOUTS_SHA256:-none} (qsub -v): this job runs no git where it runs, so it is "
        "submitted by its own recipe (SUBMIT-BEGIN), and a record changed after submission is not read\" | tee -a \"$VERDICTS\"",
        "  exit 2",
        "fi",
        *([f"if [ -n \"$EXPECT_HARNESS\" ] && [ \"$(cat \"$HARNESS\"/{cf} 2>/dev/null)\" != \"$EXPECT_HARNESS\" ]; then",
           f"  echo \"VERDICT (harness): MISSED - $HARNESS/{cf} names $(cat \"$HARNESS\"/{cf} 2>/dev/null || echo nothing), this "
           "job was generated at $EXPECT_HARNESS\" | tee -a \"$VERDICTS\"",
           "  exit 2",
           "fi"] if cf else []),
        # THE JOB RUNS THE FILES IT WAS GENERATED FOR (autodev W042 fix 1, C): the request, the check
        # script and the site's two files are compared with their hashes here, before anything runs; an
        # edited one would run under a prediction written for another
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
        "cat > \"$RUNDIR/PINS.json\" <<'SCH_PINS_END'", pins_doc, "SCH_PINS_END",
        "PRESENT=''; [ \"${CHECK_ONLY:-}\" != 1 ] || PRESENT=--present   # a preflight: every input present and readable",
        "set +e",
        "PYTHONPATH=\"$HARNESS\" \"$PY\" -m sch plan --request \"$REQUEST\"" + tail + " --expect \"$RUNDIR/PINS.json\" "
        "--checkouts \"$RUNDIR/" + CHECKOUTS + "\" $PRESENT > \"$RUNDIR/PINS.txt\" 2>&1",
        "prc=$?",
        "set -e",
        "grep -E '^  (pinned|only here|tool|harness|here|not compared here|present|named|read):' \"$RUNDIR/PINS.txt\" || true",
        "if [ \"$prc\" -ne 0 ]; then",
        "  why=$(grep -E '^  (differs|request refused)' \"$RUNDIR/PINS.txt\" | head -n 12 | tr '\\n' ';' || true)",
        "  [ -n \"$why\" ] || why=$(tail -n 3 \"$RUNDIR/PINS.txt\" | tr '\\n' ' ' || true)",
        "  if [ \"${CHECK_ONLY:-}\" = 1 ] && grep -qE '^  (differs|request refused)' \"$RUNDIR/PINS.txt\"; then   # one line a miss",
        "    grep -E '^  (differs|request refused)' \"$RUNDIR/PINS.txt\" | while IFS= read -r ln; do echo \"VERDICT (pins): MISSED - ${ln#  }\" | say; done",
        "  else echo \"VERDICT (pins): MISSED - the files this job was generated for differ: $why\" | tee -a \"$VERDICTS\"; fi",
        "  exit 2",
        "fi",
        # THE PREFLIGHT (autodev W056 fix 1, A1; BRIEFS 0b): everything before the first tool call, then stop
        "if [ \"${CHECK_ONLY:-}\" = 1 ]; then",
        "  echo \"VERDICT (pins): AS PREDICTED - the checkouts and every input as this job was generated, present and readable here\" | say",
        *(["  set +e",
           "  CHECK_ONLY=1 RUNDIR=\"$RUNDIR\" REQUEST=\"$REQUEST\" PY=\"$PY\" HARNESS=\"$HARNESS\" bash \"$CHECK\" \"$RUNDIR\" > \"$RUNDIR/PREFLIGHT_CHECKS.txt\" 2>&1",
           "  crc=$?",
           "  set -e",
           "  grep '^VERDICT' \"$RUNDIR/PREFLIGHT_CHECKS.txt\" >> \"$VERDICTS\" || true",
           "  grep -q '^VERDICT' \"$RUNDIR/PREFLIGHT_CHECKS.txt\" || echo \"VERDICT (checks): MISSED - $CHECK graded no line on its "
           "reference runs with CHECK_ONLY=1 (see PREFLIGHT_CHECKS.txt)\" | say",
           "  [ \"$crc\" -eq 0 ] || echo \"VERDICT (checks): MISSED - the checks exited $crc with CHECK_ONLY=1 (see "
           "PREFLIGHT_CHECKS.txt)\" | say"] if check else []),
        "  exit 0",
        "fi",
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
        "  RUNDIR=\"$RUNDIR\" REQUEST=\"$REQUEST\" PY=\"$PY\" HARNESS=\"$HARNESS\" bash \"$CHECK\" \"$RUNDIR\" > \"$RUNDIR/CHECKS.txt\" 2>&1",
        "  crc=$?",
        "  set -e",
        "  cat \"$RUNDIR/CHECKS.txt\"",
        "  grep '^VERDICT' \"$RUNDIR/CHECKS.txt\" >> \"$VERDICTS\" || true",
        "  [ \"$crc\" -eq 0 ] || echo \"VERDICT (checks): MISSED - the checks exited $crc\" | tee -a \"$VERDICTS\"",
        "fi",
        "if grep -q '^VERDICT.*MISSED' \"$VERDICTS\"; then exit 1; fi",
        "exit 0",
    ]
    return "\n".join(ln.replace('| tee -a "$VERDICTS"', "| say") for ln in out) + "\n"


def write_job(req: dict, job_path, **kw) -> dict:
    p = Path(job_path)
    if p.exists():                               # autodev W042 fix 2, C
        raise RequestError(f"--job {p}: a job is there already; a job carries its prediction, and generating "
                           f"over it would replace that prediction unseen - remove it yourself, or name another file")
    text = job_text(req, job_path, **kw)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:      # LF only: a CR breaks bash on the cluster
        fh.write(text)
    return {"job": str(p.resolve()), "md5": hashlib.md5(text.encode()).hexdigest(), "lines": text.count("\n")}
