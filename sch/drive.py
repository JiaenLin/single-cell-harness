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
A run is its request and every file it reads (`run_inputs`: the samplesheet and every path in it,
the design, every path a param or an answer names, every file under a directory named (links
followed), every path a named document holds, the site layer, each tool's checkout and the harness's
own code, an adapter the harness does not ship): the set is recomputed and compared at the plan, at
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
#: A DOCUMENT A PARAM, AN ANSWER OR THE SITE NAMES IS READ FOR THE PATHS IN IT (autodev W049, route 13):
#: a table or a YAML/JSON file up to DOC_LIMIT bytes, one level deep (a document it names is pinned as
#: its text). A relative path in it is pinned beside it, as the stack reads a samplesheet's.
DOCS = {".tsv": "\t", ".txt": "\t", ".csv": ",", ".yml": None, ".yaml": None, ".json": None}
DOC_LIMIT = 4 << 20
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
          "excluded": EXCLUDED, "document_limit_bytes": DOC_LIMIT, "documents": sorted(DOCS),
          "open": "a file over the hash limit is compared by size, modification time and its first and last "
                  "bytes, so an edit of its middle that keeps its size and modification time is not seen; a "
                  "directory over the tree limit is not compared at all; a change made and undone while one "
                  "stage's tool runs, between that stage's start and its seal, is seen only if the tool records "
                  "what it read; a path inside a named document is pinned one level deep, a relative one beside "
                  "that document (a tool that resolves it from elsewhere reads a file the set does not hold); a "
                  "git checkout (the harness, a tool's) is its commit and its tracked changes, not its untracked "
                  "files; records rewritten consistently everywhere are not told from true ones (no signature)"}


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
    found, seen = [], {os.path.realpath(p)}
    # A LINKED DIRECTORY IS WALKED TOO (autodev W049, route 5): what a tool reads through a link is a file
    # it reads. Each directory is walked once, by its real path; a link back to one already walked is a
    # loop, kept in the set as the link and its target, so retargeting it is a change.
    for root, dirs, names in os.walk(p, followlinks=True):
        keep = []
        for d in sorted(x for x in dirs if x not in EXCLUDED):
            real = os.path.realpath(os.path.join(root, d))
            if real in seen:
                found.append((Path(root) / d, real))
            else:
                seen.add(real)
                keep.append(d)
        dirs[:] = keep
        found += [Path(root) / n for n in sorted(names) if not n.endswith(".pyc")]
        if len(found) > TREE_LIMIT:
            files[role] = {"path": str(p), "unpinned": f"more than TREE_LIMIT ({TREE_LIMIT}) files: not "
                                                       f"hashed at every step"}
            return
    files[role] = {"path": str(p), "dir": len(found)}
    for f in found:
        if isinstance(f, tuple):                 # a loop: the link, and where it leads
            files[f"{role}/{f[0].relative_to(p).as_posix()}"] = {"path": str(f[0]), "loop": f[1]}
            continue
        rel = f.relative_to(p).as_posix()
        try:
            files[f"{role}/{rel}"] = _entry(f) if f.is_file() else {"path": str(f), "absent": True}
        except OSError as e:
            files[f"{role}/{rel}"] = {"path": str(f), "unreadable": f"{type(e).__name__}: {e}"}


def _paths(v, base: Path | None, words: bool = False) -> list:
    """The paths a value names, the way its reader resolves them: absolute or `~/`; with `base` (a
    samplesheet's directory, as the stack reads a parts column), also a relative path that is there or
    that has a `/` in it. A comma-separated list of paths is each of them. `words` (a document's values,
    which are mostly words): a bare word is a path only when a FILE of that name is beside it."""
    if not isinstance(v, str) or not v.strip():
        return []
    pieces = [x.strip() for x in v.split(",")] if "," in v else [v.strip()]

    def one(x):
        if x.startswith(("/", "~/")):
            return Path(os.path.expanduser(x))
        if base is not None and x and ("/" in x or ((base / x).is_file() if words else (base / x).exists())):
            return base / x
        return None
    got = [one(x) for x in pieces]
    if len(pieces) > 1 and not all(got):
        return []                                # a list of words, not of paths
    return [g for g in got if g is not None]


def _git_state(d: Path, pathspec=()) -> dict | None:
    """A git work tree as the set holds it (autodev W049, routes 10 and 14): its top, its commit and a
    digest of its tracked changes against that commit (limited to `pathspec`); None outside one. Read
    with no optional lock, so two jobs reading one checkout never collide on its index."""
    import subprocess

    def g(*a):
        r = subprocess.run(["git", "--no-optional-locks", "-C", str(d), *a], capture_output=True, timeout=120)
        return r.stdout if r.returncode == 0 else None
    try:
        top, head = g("rev-parse", "--show-toplevel"), g("rev-parse", "HEAD")
        if not top or not head:
            return None
        spec = ["--", *pathspec] if pathspec else []
        st = g("status", "--porcelain=v1", "--untracked-files=no", *spec)
        diff = g("diff", "--binary", "HEAD", *spec)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if st is None or diff is None:
        return None
    return {"path": top.decode().strip(), "git": head.decode().strip(),
            "tracked_changes": hashlib.sha256(st + b"\0" + diff).hexdigest()}


def _document(f: Path):
    """[(where, value)] of a table or a YAML/JSON document, or None when it is not one the driver reads."""
    sep = DOCS.get(f.suffix.lower(), False)
    if sep is False or f.stat().st_size > DOC_LIMIT:
        return None
    try:
        if sep:
            with open(f, newline="", encoding="utf-8") as fh:
                rows = list(csv.reader(fh, delimiter=sep))
            return [(f"[{i}.{j}]", v) for i, r in enumerate(rows) for j, v in enumerate(r)]
        doc = json.loads(f.read_text(encoding="utf-8")) if f.suffix.lower() == ".json" else yamlish.load(f)
    except Exception:                            # noqa: BLE001 - not a document: pinned as its text
        return None
    return list(_leaves(doc))


def run_inputs(req: dict, answers: dict | None = None) -> dict:
    """THE COMPLETE SET OF FILES A RUN READS (autodev W042 fix 2, B; W049), {role: entry}: the request,
    its samplesheet, its design, every path-valued cell of the samplesheet (any column), every path-valued
    stage param and ANSWER (`answer[<decision>]`: set into a stage's params at run time, read by its tool
    as a param is), the site layer every stage's stack is composed over and every path it names, every
    file under any directory one of them names (links followed), every path a document among them names
    (one level), each stage's tool checkout and the harness's own code (their commit and tracked
    changes), and every file of an adapter the harness does not ship. ONE function, so the plan, each
    stage's start and seal, a resume and the generated job compare the same set the same way. The roles
    are the request's own words, the same on every machine; a path is where the file was found."""
    from .services.dataset import read_manifest
    files: dict = {}
    root = Path(__file__).resolve().parent.parent
    files["harness"] = _git_state(root, ("sch", "plugins")) or {   # route 10: its code, as it runs
        "path": str(root), "git": None, "tracked_changes": _tree_digest(root / "sch") + _tree_digest(root / "plugins")}
    _add(files, "request", Path(req["path"]))
    sheet = Path(req["observations"])
    _add(files, "observations", sheet)
    if req.get("design"):
        _add(files, "design", Path(req["design"]))
    shipped = (Path(__file__).resolve().parent.parent / "plugins").resolve()
    for p in req["stages"]:                      # an adapter the harness does not ship (named by a path, or
        d = Path(p["dir"]).resolve()             # found on SCH_PLUGINS) is read like any input: its code too
        if not str(d).startswith(str(shipped) + os.sep):
            _add(files, f"{p['stage']}.plugin", d)
    try:
        _head, rows = read_manifest(sheet) if sheet.is_file() else ([], [])
    except Exception:                            # noqa: BLE001 - the stack's own init says what is wrong
        rows = []
    for i, r in enumerate(rows, 1):
        lib = str(r.get(req["keys"]["sample"]) or i).strip()
        for col, v in r.items():
            got = _paths(v, sheet.parent)
            for j, f in enumerate(got):
                _add(files, f"observations.{col}[{lib}]" + (f"#{j}" if len(got) > 1 else ""), f)
    named = []                                   # the roles a param, an answer or the site names
    for p in req["stages"]:
        for path, v in _leaves(p["params"]):
            got = _paths(v, None)
            for j, f in enumerate(got):
                named.append(f"{p['stage']}.{path}" + (f"#{j}" if len(got) > 1 else ""))
                _add(files, named[-1], f)
        tool = p.get("tool_param")               # route 14: the checkout around the file naming its tool
        got = _paths(dict(_leaves(p["params"])).get(tool), None) if tool else []
        if got and got[0].exists():
            d = got[0] if got[0].is_dir() else got[0].parent
            files[f"{p['stage']}.{tool}@checkout"] = _git_state(d) or (
                {"path": str(d), "git": None, "tracked_changes": _tree_digest(d)} if got[0].is_file() else
                {"path": str(d), "git": None, "tracked_changes": "the directory itself, walked as the param"})
    for name in sorted(answers or {}):           # route 6: an answer is read by its tool as a param is
        a = answers[name]
        for path, v in _leaves(a.get("value") if isinstance(a, dict) else a):
            got = _paths(v, None)
            for j, f in enumerate(got):
                named.append(f"answer[{name}]" + (f".{path}" if path else "") + (f"#{j}" if len(got) > 1 else ""))
                _add(files, named[-1], f)
    site = os.environ.get("SCH_SITE")            # route 11: the layer beneath every stage's stack.yml
    if site:
        f = Path(site) / "stack.yml"
        _add(files, "site.stack.yml", f)
        layer = yamlish.load(f) if f.is_file() else None
        for path, v in _leaves(layer if isinstance(layer, dict) else {}):
            for j, g in enumerate(got := _paths(v, None)):
                named.append(f"site.{path}" + (f"#{j}" if len(got) > 1 else ""))
                _add(files, named[-1], g)
    for role in named:                           # route 13: a document's paths, one level, beside it
        e = files.get(role) or {}
        if not e.get("sha256"):
            continue
        f = Path(e["path"])
        for where, v in _document(f) or []:
            got = _paths(v, f.parent, words=True)
            for j, g in enumerate(got):
                _add(files, f"{role}>{where}" + (f"#{j}" if len(got) > 1 else ""), g)
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
        return "unpinned"
    if e.get("unreadable"):
        return "unreadable"
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
    first = plan[0]
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
    if where is not None:
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
        # A FLAG THE ADAPTER OWNS IS REFUSED WHEN THE PLAN IS MADE (autodev W042 fix 2, the observation):
        # `owned:` is the manifest's copy of its run.py's OWNED, tied by a test; refused here, not after
        # the stages before it ran.
        for path in m.data.get("owned") or []:
            got = _has(params, str(path))
            if got:
                raise RequestError(f"stages[{i}] ({m.name}): params set {got[0]}, which {m.name} sets itself from "
                                   f"the stack (its `owned:`); drop it from the stage's params")
        # A RELATIVE PATH IS READ WHERE ITS TOOL RUNS (autodev W042 fix 2, B): a tool is given its params
        # verbatim and reads a relative path from its own working directory, the stage's run directory;
        # one that names a file beside the request would be pinned here and not be what the tool reads.
        # That directory is the run's own and new, so a relative path names what the run made - unless it
        # climbs out of it (`..`) or names another account's home (`~name/`): outside the run, and never
        # pinned, so refused too.
        for path, v in _leaves(params):
            for x in ([y.strip() for y in v.split(",")] if isinstance(v, str) else []):
                out_of = _climbs(x)
                if _relative_path(x, [base]):
                    raise RequestError(f"stages[{i}] ({m.name}): {path} is {x!r}, a relative path"
                                       + (" out of its tool's working directory" if out_of else f" to {base / x}")
                                       + f"; {m.name}'s tool reads its params from its own working directory (the "
                                       f"stage's run directory), not from the request's, and what it names there "
                                       f"would not be pinned: write it absolute, or ~/")
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
                     "profile": m.profile, "version": m.version,
                     "wraps": {k: (m.data.get("wraps") or {}).get(k) for k in WRAPS},
                     "assays": list(m.data.get("assays") or []), "reads": m.data.get("reads"),
                     "hands_on": _hands_on(m, params), "params": params, "decisions": decisions,
                     "library_key": [paths] if isinstance(paths, str) else list(paths),
                     "resources": dict(m.data.get("resources") or {}),
                     "upstream_columns": m.data.get("upstream_columns"),
                     "upstream_accepts": m.data.get("upstream_accepts"), "tool_param": m.data.get("tool_param"),
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
            "decisions": run_decisions,
            "drive_resources": {str(k): str(v) for k, v in dict(res.get(DRIVE) or {}).items()}}


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


#: An answer and who gave it are one line each: they are recorded, and written into a generated job's
#: header and shell lines as they are (autodev W049, ATTACKS 6).
LINE = re.compile(r"[^\x00-\x1f\x7f\x85\u2028\u2029]+")


def _climbs(x: str) -> bool:
    """A relative path out of its tool's working directory (`..`), or into another account's home."""
    return bool(re.search(r"(^|/)\.\.(/|$)", x) or re.match(r"~[^/\s]+/", x))


def _relative_path(x: str, bases) -> bool:
    """A value its tool would read as a relative path, from its own working directory, and which names
    something the driver would not pin there (autodev W049): one climbing out, one naming a FILE beside
    the request (or where `sch` was run), or one with a `/` naming a directory there. A bare word naming a
    directory is a word - a method, a kernel or a key named like a folder of results is common - and a
    tool meant to read that folder refuses it where it runs."""
    if not x or x.startswith(("/", "~/")):
        return False
    return _climbs(x) or any((b / x).is_file() or ("/" in x and (b / x).is_dir()) for b in bases)


def answers_of(req: dict, given: list | None, by: str | None, recorded: dict | None = None) -> tuple:
    """(answers, the names answered now): the recorded answers and each `--answer NAME=VALUE` given now,
    read alike by the run, the plan and a generated job (autodev W049): a declared name, an allowed value,
    a recorded one never rewritten, who gave it a name on one line, and a value naming a file only
    absolute or `~/` - its tool reads a relative path from its own working directory, where the set
    would not pin what was meant."""
    names = {d["name"]: d for p in req["stages"] for d in p["decisions"]}
    names.update({d["name"]: d for d in req.get("decisions") or []})
    answers, new = dict(recorded or {}), []
    if given and (by is None or not str(by).strip()):
        raise RequestError("--answer needs --by: a decision is recorded with who made it, by name (a blank is no name)")
    for what, v in [("--by", by)] + [("--answer", a) for a in given or []]:
        if v is not None and not LINE.fullmatch(str(v)):
            raise RequestError(f"{what} {str(v)!r}: an answer and who gave it are one line of printable text; they "
                               f"are recorded and written into a generated job as they are")
    bases = [Path(req["path"]).parent, Path.cwd()]
    for a in given or []:
        name, sep, raw = str(a).partition("=")
        if not sep or name not in names:
            raise RequestError(f"--answer {a!r}: no stage declares a user's decision {name!r}; "
                               f"declared: {', '.join(names) or 'none'}")
        try:
            value = json.loads(raw)
        except ValueError:
            value = raw
        allowed_values = names[name].get("values")
        if allowed_values and value not in allowed_values:
            raise RequestError(f"--answer {a!r}: {name} is answered {' or '.join(allowed_values)}")
        for _path, v in _leaves(value):
            for x in ([y.strip() for y in v.split(",")] if isinstance(v, str) else []):
                if _relative_path(x, bases):
                    raise RequestError(f"--answer {a!r}: {x!r} is a relative path; {name}'s tool reads it from its "
                                       f"own working directory (the stage's run directory), not from here, and "
                                       f"what it names there would not be pinned: write it absolute, or ~/")
        if name in answers and answers[name]["value"] != value:
            raise RequestError(f"{name} is already answered {json.dumps(answers[name]['value'])} by "
                               f"{answers[name]['by']}; a recorded decision is not rewritten: start a new --out")
        if name not in answers:
            answers[name] = {"value": value, "by": str(by).strip(), "at": _now(), "verbatim": a}
            new.append(name)
    return answers, new


def _answer_of(role: str):
    """The decision an `answer[<name>]...` role was named by, else None."""
    return role[len("answer["):role.index("]")] if role.startswith("answer[") and "]" in role else None


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
            _trust(out, s, rec, now)
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
    last = json.loads((out / done[-1] / "SEALED.json").read_text()) if done else {}
    rec = {"status": "sealed", "sealed": done, "request": req["path"], "request_sha256": req["sha256"],
           "inputs": last.get("inputs") or inputs, "decisions": answers, "upstream": req["upstream"],
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
              "joint": str(rd / "out" / got["joint"]) if got.get("joint") else None}
    lost = [x for x in [*handed["libraries"].values(), handed["joint"]] if x and not Path(x).is_file()]
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
                   "answers_known": sorted(answers),
                   "handed_sha256": {x: _digest(_entry(Path(x))) for x in
                                     [*handed["libraries"].values(), handed["joint"],
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


def expected(req: dict, file, answers: dict | None = None) -> tuple:
    """(holds, lines, differences): the run's set now - with the job's answers (autodev W049) - against
    the set a job was generated for (autodev W042 fix 2, C), content only (a copy keeps no modification
    time); a file absent where the job was generated is checked here for the first time, and said."""
    try:
        then = json.loads(Path(file).read_text())["files"]
    except (OSError, ValueError, KeyError) as e:
        return False, [f"  differs: the job's record {file} cannot be read ({e})"], [("record", None, None)]
    now = {k: v for k, v in run_inputs(req, answers).items() if k not in JOB_UNPINNED}
    then = {k: v for k, v in then.items() if k not in JOB_UNPINNED}
    a, b = flat(then, mtime=False), flat(now, mtime=False)
    d = differ(a, b, here_only=True)
    bad = {k for k, _x, _y in d}
    here = [k for k in sorted(b) if a.get(k) in (None, "absent") and k not in bad]
    lines = [f"  pinned: {sum(1 for v in a.values() if v != 'absent')} of the run's files as the job was generated; "
             f"{len(here)} checked here only"]
    lines += [f"  only here: {k} {now[k]['path']}" for k in here[:40]]
    lines += [f"  differs: {k} {(now.get(k) or then.get(k) or {}).get('path', '')} ({x or 'not named'} when the job "
              f"was generated, {y or 'not named'} now)" for k, x, y in d]
    return not d, lines, d


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
    hn_sh = ('"$HOME"/' + q(hn[2:])) if hn.startswith("~/") else q(hn)
    py = str(job["python"])
    py_sh = ('"$HOME"/' + q(py[2:])) if py.startswith("~/") else q(py)
    at = str(where or jobs)
    at = at if re.fullmatch(r"[~A-Za-z0-9_./-]+", at) else q(at)   # `~` left for the shell to read
    key = f"$(date -u +%Y%m%dT%H%M%SZ)__sch-${{HC:0:7}}__{stage}" + (f"__{purpose}" if purpose else "")
    name = re.sub(r"[^A-Za-z0-9_]", "_", f"sch_{stage}")[:15]
    reports = " ".join(f'"$RUNDIR"/{p["stage"]}/report/report.json' for p in req["stages"])
    # THE JOB PINS THE RUN'S WHOLE SET (autodev W042 fix 2, C): B's set as it is where the job is
    # generated; what is absent here is named, and checked only where the job runs.
    pins = {k: v for k, v in run_inputs(req, given).items() if k not in JOB_UNPINNED}
    absent = [k for k, v in pins.items() if v.get("absent")]
    # by role, without where the file lies here: the roles are the same on every machine, and a path of
    # this workstation's has no place in a job that runs on another
    pins_doc = json.dumps({"generated_at": _now(), "policy": POLICY,
                           "files": {k: {x: y for x, y in v.items() if x != "path"} for k, v in pins.items()}},
                          sort_keys=True)
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
        f"#   inputs    {len(pins) - len(absent)} files the run reads, pinned as generated, its answers' among them (the "
        f"job refuses another set: `sch plan --request REQUEST --answer ... --expect PINS.json`); {len(absent)} checked "
        f"only where it runs" + (":" if absent else ""),
        *[re.sub(r"[\x00-\x1f\x7f]", "?", f"#     on the cluster only: {k} {os.path.relpath(pins[k]['path'], jobs) if not str(pins[k]['path']).startswith(str(Path.home())) else '~/' + os.path.relpath(pins[k]['path'], Path.home())}"
                 ) for k in absent],
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
        "cat > \"$RUNDIR/PINS.json\" <<'SCH_PINS_END'", pins_doc, "SCH_PINS_END",
        "set +e",
        "PYTHONPATH=\"$HARNESS\" \"$PY\" -m sch plan --request \"$REQUEST\"" + tail + " --expect \"$RUNDIR/PINS.json\" "
        "> \"$RUNDIR/PINS.txt\" 2>&1",
        "prc=$?",
        "set -e",
        "grep -E '^  (pinned|only here)' \"$RUNDIR/PINS.txt\" || true",
        "if [ \"$prc\" -ne 0 ]; then",
        "  why=$(grep -E '^  (differs|request refused)' \"$RUNDIR/PINS.txt\" | head -n 12 | tr '\\n' ';' || true)",
        "  [ -n \"$why\" ] || why=$(tail -n 3 \"$RUNDIR/PINS.txt\" | tr '\\n' ' ' || true)",
        "  echo \"VERDICT (pins): MISSED - the files this job was generated for differ: $why\" | tee -a \"$VERDICTS\"",
        "  exit 2",
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
    p = Path(job_path)
    if p.exists():                               # autodev W042 fix 2, C
        raise RequestError(f"--job {p}: a job is there already; a job carries its prediction, and generating "
                           f"over it would replace that prediction unseen - remove it yourself, or name another file")
    text = job_text(req, job_path, **kw)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:      # LF only: a CR breaks bash on the cluster
        fh.write(text)
    return {"job": str(p.resolve()), "md5": hashlib.md5(text.encode()).hexdigest(), "lines": text.count("\n")}
