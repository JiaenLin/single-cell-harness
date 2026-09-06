"""What "unchanged" means, cheaply, before anything is submitted to a queue.

An agent that refactors has one honest question - did the numbers move? - and until now the only
way to answer it was a cluster run against the real cohort, which costs an hour and a queue slot.
So the question got skipped, and the answer arrived at merge time or not at all.

A baseline is the numeric fingerprint of a run over the synthetic fixture. Recording one takes
seconds; checking one takes seconds. It cannot tell you the tool is right - the fixture is
synthetic and nothing it produces is quotable - but it can tell you, in the time it takes to save
a file, that a change which was supposed to move nothing has moved something. That is the failure
worth catching early, because it is the one that is cheap to explain while the change is still in
your head and expensive to explain a week later.

WHAT A DIFFERENCE MEANS HERE. A moved number is not automatically a defect: a deliberate change
to what a tool computes SHOULD move it, and the family already has the vocabulary for that -
`state_version`, bumped, says "the same inputs now give a different answer, on purpose". So a
difference is a stop, not a verdict: either the number should not have moved, or `state_version`
must say it did. `sch dev check` enforces exactly that pairing and nothing more.

Floats are compared with a relative tolerance because bit-equality across machines is not a
property this family has - the harmony finding of 2026-09-06 measured 0.214 between two nodes of
the same model. A baseline recorded on one machine and checked on another is therefore compared,
not diffed, and the tolerance is recorded in the file so a reader knows what was allowed.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import re
import socket
import sys
from pathlib import Path

RTOL = 1e-9
ATOL = 1e-12
READABLE = (".json", ".csv", ".tsv")
# Values that differ between two correct runs by construction. Fingerprinting them would make
# every baseline fail for reasons that are never the tool's.
VOLATILE = {"started", "finished", "seconds", "elapsed", "timings", "commit", "tool_commit",
            "jobid", "job", "host", "argv", "python", "generated", "date", "out", "out_dir",
            "path", "paths", "run", "rundir", "pid", "hostname", "wrapped_versions", "version"}


def elsewhere(ref: dict) -> str | None:
    """A sentence to print beside a difference when the baseline came from another machine, and
    nothing when it did not. Not a verdict - the difference may still be the change - but a
    reader who is not told will spend the afternoon on the wrong question."""
    was = (ref.get("recorded_on") or {}).get("host_id")
    now = hashlib.sha256(socket.gethostname().encode()).hexdigest()[:12]
    if not was or was == now:
        return None
    return ("this baseline was recorded on a DIFFERENT machine from the one you are on; a numeric "
            "difference here may be the machine, which two runs on one node cannot rule out")


# A generated document embeds the moment it was generated and the directory it was written to.
# Both are provenance and neither is a result, but both change the bytes - so a content hash of
# a report fails on the next run for a reason that is never the numbers. This is the third time
# the same distinction has had to be drawn today: paths and times are provenance; values are
# content. Redact the first before hashing the second.
#
# The redaction is deliberately narrow - ISO timestamps, clock times, absolute paths - because
# everything it removes is something no reader would call a result, and everything it leaves is
# something they might.
_PROVENANCE = [
    (re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2})?(\.\d+)?Z?"), "<when>"),
    (re.compile(r"\d{4}-\d{2}-\d{2}"), "<date>"),
    (re.compile(r"\b\d{2}:\d{2}:\d{2}\b"), "<time>"),
    (re.compile(r"(?<![\w.])/(?:[\w.+@~-]+/)+[\w.+@~-]*"), "<path>"),
    (re.compile(r"\b\d+(\.\d+)?\s?(seconds|secs|s)\b"), "<elapsed>"),
]
# Suffixes read as text for that redaction. Anything else is hashed as bytes: a .npy or an .h5ad
# has no prose to redact, and mangling it would make the digest meaningless.
_TEXTISH = {".md", ".html", ".htm", ".txt", ".log", ".yml", ".yaml", ".rst"}


def _opaque_digest(p: Path) -> str:
    if p.suffix.lower() in _TEXTISH:
        try:
            t = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return hashlib.sha256(b"").hexdigest()[:16]
        for rx, sub in _PROVENANCE:
            t = rx.sub(sub, t)
        return hashlib.sha256(t.encode("utf-8")).hexdigest()[:16]
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def _numbers(obj, prefix="", into=None):
    """Numeric leaves, by path. Booleans are not numbers here: True becoming 1.0 is a change of
    kind, and it should read as one."""
    into = {} if into is None else into
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k).lower() in VOLATILE:
                continue
            _numbers(v, f"{prefix}.{k}" if prefix else str(k), into)
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            _numbers(v, f"{prefix}[{i}]", into)
    elif isinstance(obj, bool):
        into[prefix] = f"bool:{obj}"
    elif isinstance(obj, (int, float)):
        into[prefix] = float(obj)
    return into


def _csv_fingerprint(path: Path) -> dict:
    with path.open(newline="", encoding="utf-8", errors="replace") as fh:
        rows = list(csv.reader(fh))
    if not rows:
        return {"kind": "csv", "rows": 0, "header": [], "numbers": {}}
    header, body = rows[0], rows[1:]
    nums: dict = {}
    for j, name in enumerate(header):
        if name.lower() in VOLATILE:
            continue
        col = []
        for r in body:
            if j >= len(r):
                continue
            try:
                col.append(float(r[j]))
            except (TypeError, ValueError):
                col = None
                break
        if col:
            finite = [x for x in col if math.isfinite(x)]
            nums[name] = {"n": len(col), "nan": len(col) - len(finite),
                          "sum": sum(finite), "min": min(finite) if finite else None,
                          "max": max(finite) if finite else None}
    return {"kind": "csv", "rows": len(body), "header": header, "numbers": nums}


# THE RUN'S ACCOUNT OF ITSELF IS NOT A RESULT. The status contract's own files exist to say what
# happened, when, where and under which commit - they are provenance end to end, and every field
# in them is supposed to differ between runs. Fingerprinting them means a baseline that can never
# pass, and no amount of redaction fixes that: a job id and a hostname are not timestamps, and
# stripping them would leave a file with nothing in it. They are named here because the status
# contract names them, so this is a rule about a known shape rather than a guess about a filename.
SELF_ACCOUNT = ("RUNNING.txt", "SEALED.txt", "FAILED.txt")


def _is_self_account(rel: str) -> bool:
    name = Path(rel).name
    return name in SELF_ACCOUNT or (
        (name.startswith("SEALED.") or name.startswith("FAILED.")) and name.endswith(".txt"))


def fingerprint(run_dir) -> dict:
    """Every readable product, summarised. Unreadable products are LISTED with their size, not
    skipped: a baseline that quietly ignores the h5ad is a baseline that says nothing about the
    object, and a reader should be able to see that from the file."""
    run = Path(run_dir)
    items: dict = {}
    for p in sorted(run.rglob("*")):
        if not p.is_file() or any(x.startswith(".") for x in p.relative_to(run).parts):
            continue
        rel = str(p.relative_to(run))
        if _is_self_account(rel):
            continue
        if p.suffix == ".json":
            try:
                items[rel] = {"kind": "json", "numbers": _numbers(json.loads(p.read_text(encoding="utf-8")))}
            except (OSError, ValueError) as e:
                items[rel] = {"kind": "json", "unreadable": str(e)}
        elif p.suffix in (".csv", ".tsv"):
            try:
                items[rel] = _csv_fingerprint(p)
            except (OSError, ValueError) as e:
                items[rel] = {"kind": "csv", "unreadable": str(e)}
        else:
            items[rel] = {"kind": "opaque", "bytes": p.stat().st_size,
                          "sha256": _opaque_digest(p)}
    return {"baseline": 1, "rtol": RTOL, "atol": ATOL, "products": items,
            # WHERE IT WAS RECORDED, because two runs on one machine cannot rule out the machine.
            # This family measured 0.214 between two nodes of the same model on 2026-09-06; a
            # baseline that does not say where it came from turns that into a mystery failure
            # somewhere else, and a mystery failure is how a check gets switched off.
            #
            # THE HOST IS HASHED, NOT NAMED. A baseline is committed INTO a tool repository, and
            # a repository in this family carries no site identifier - the guards that enforce
            # that would reject a node name, correctly. All the check needs is "the same machine
            # or a different one", which an opaque id answers without telling a reader whose
            # cluster this was. The platform string stays readable: it is a property of the
            # software, not of the site.
            "recorded_on": {"host_id": hashlib.sha256(socket.gethostname().encode()).hexdigest()[:12],
                            "python": sys.version.split()[0],
                            "platform": platform.platform(), "machine": platform.machine()},
            "covers": sorted(k for k, v in items.items() if v["kind"] != "opaque"),
            "does_not_cover": sorted(k for k, v in items.items() if v["kind"] == "opaque")}


def record(run_dir, path) -> dict:
    fp = fingerprint(run_dir)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(fp, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return fp


def _close(a, b, rtol, atol) -> bool:
    if isinstance(a, str) or isinstance(b, str):
        return a == b
    if a is None or b is None:
        return a is b
    if math.isnan(a) and math.isnan(b):
        return True
    return abs(a - b) <= atol + rtol * abs(b)


def compare(new: dict, ref: dict) -> list:
    """Differences, most structural first. Empty means the fingerprints agree.

    FIELDS THE BASELINE MEASURED AS NOT EXECUTION-STABLE ARE SKIPPED HERE, not deleted at
    recording time. Deleting was the first implementation and it was wrong twice: an opaque
    file's identity is a `sha256`, not a number, so nothing was removed for those at all; and
    removing a key from the reference makes the very next comparison report it as NEW. The first
    check after recording therefore failed on precisely the fields the recording had just
    excluded. Keeping the values and filtering the comparison handles numbers, column statistics
    and bytes uniformly, and leaves a reader able to see what the unstable value actually was.
    """
    rtol, atol = float(ref.get("rtol", RTOL)), float(ref.get("atol", ATOL))
    unstable = set(ref.get("not_execution_stable") or [])
    out, np_, rp = [], new.get("products", {}), ref.get("products", {})

    def keep(product, what):
        return f"{product}::{what}" not in unstable
    for rel in sorted(set(rp) - set(np_)):
        out.append({"product": rel, "what": "absent", "detail": "the baseline has it; this run does not"})
    for rel in sorted(set(np_) - set(rp)):
        out.append({"product": rel, "what": "new", "detail": "this run has it; the baseline does not"})
    for rel in sorted(set(np_) & set(rp)):
        a, b = np_[rel], rp[rel]
        if a.get("kind") != b.get("kind"):
            out.append({"product": rel, "what": "kind", "detail": f"{b.get('kind')} -> {a.get('kind')}"})
            continue
        if a["kind"] == "opaque":
            # SIZE AND CONTENT ARE SEPARATE FACTS. Reported together, an exclusion for one
            # silently excludes the other, and a figure that vanished would hide behind a
            # timestamp that moved.
            if a.get("bytes") != b.get("bytes") and keep(rel, "size"):
                out.append({"product": rel, "what": "size",
                            "detail": f"{b.get('bytes')}b -> {a.get('bytes')}b"})
            if a.get("sha256") != b.get("sha256") and keep(rel, "content"):
                out.append({"product": rel, "what": "content",
                            "detail": f"{b.get('sha256')} -> {a.get('sha256')} "
                                      f"(timestamps and paths already redacted)"})
            continue
        if a["kind"] == "csv":
            if a.get("header") != b.get("header") and keep(rel, "header"):
                out.append({"product": rel, "what": "header", "detail": f"{b.get('header')} -> {a.get('header')}"})
            if a.get("rows") != b.get("rows") and keep(rel, "rows"):
                out.append({"product": rel, "what": "rows", "detail": f"{b.get('rows')} -> {a.get('rows')}"})
            an, bn = a.get("numbers", {}), b.get("numbers", {})
            for col in sorted(set(an) & set(bn)):
                for stat in ("n", "nan", "sum", "min", "max"):
                    if not _close(an[col].get(stat), bn[col].get(stat), rtol, atol) \
                            and keep(rel, f"{col}.{stat}"):
                        out.append({"product": rel, "what": f"{col}.{stat}",
                                    "detail": f"{bn[col].get(stat)} -> {an[col].get(stat)}"})
            continue
        an, bn = a.get("numbers", {}), b.get("numbers", {})
        for k in sorted(set(bn) - set(an)):
            if keep(rel, k):
                out.append({"product": rel, "what": f"{k} absent", "detail": f"was {bn[k]}"})
        for k in sorted(set(an) - set(bn)):
            if keep(rel, k):
                out.append({"product": rel, "what": f"{k} new", "detail": f"now {an[k]}"})
        for k in sorted(set(an) & set(bn)):
            if not _close(an[k], bn[k], rtol, atol) and keep(rel, k):
                out.append({"product": rel, "what": k, "detail": f"{bn[k]} -> {an[k]}"})
    return out


def check(run_dir, path) -> tuple:
    """(differences, reference). Raises if there is no baseline to check against - "no baseline"
    is not "no difference", and returning the second for the first is how a check stops meaning
    anything."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(
            f"no baseline at {p}. Record one from a run you believe - `sch dev baseline record "
            f"RUNDIR` - and commit it. A missing baseline is not a passing baseline.")
    ref = json.loads(p.read_text(encoding="utf-8"))
    return compare(fingerprint(run_dir), ref), ref
