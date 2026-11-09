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

# The fingerprint's own version. Bumped whenever what is recorded changes shape - format 2 split
# renderings out of opaque files. A baseline written by an older format cannot be compared field
# by field against a newer one, and saying "kind opaque -> rendering" fourteen times is not an
# answer a reader can act on.
FORMAT = 2
RTOL = 1e-9
ATOL = 1e-12
READABLE = (".json", ".csv", ".tsv")
# Values that differ between two correct runs by construction. Fingerprinting them would make
# every baseline fail for reasons that are never the tool's.
VOLATILE = {"started", "finished", "seconds", "elapsed", "timings", "commit", "tool_commit",
            "jobid", "job", "host", "argv", "python", "generated", "date", "out", "out_dir",
            "path", "paths", "run", "rundir", "pid", "hostname", "wrapped_versions", "version"}

#: A BYTE COUNT MEASURES A FILE, NOT WHAT IS IN IT. A status contract lists each product with its
#: size, and a size moves with the names the file holds - shape b's `library_id` is four bytes
#: longer than shape a's `sample` in every row that spells it - and with the digits of every timing
#: written into it: 43.26 seconds and 9.8 seconds are one byte apart. Measured twice: the first
#: cluster run of `agree` (PBS 719917) found only `products[*].bytes`, in scAnno and scIntegrate;
#: and de's first baseline (autodev W013) named eight `products[*].bytes` as moving between two
#: executions - a different eight on the next pair, so a baseline that names them is one that fails
#: on the third run for a reason that is never the tool's. Not a number about the data, so neither
#: `agree` nor the baseline compares one; the baseline still RECORDS it, for a reader.
SIZE_OF_A_FILE = re.compile(r"(?:^|[.\]])(?:bytes|n_bytes|size_bytes)$")

#: WHAT A RUN MEASURES OF ITSELF IS A MEASUREMENT, NOT AN OUTPUT (autodev W019, GAP-C41). How long
#: the execution took, how many cores it used, how much memory it held, and the cost and memory
#: models a tool fits from those: they are recorded so that a scheduler and a reader can use them,
#: and they move between two executions of the SAME input on the same machine, because the machine
#: is shared. Judged as outputs they made a check fail for a reason that is never the change: de's
#: two fixture shapes agreed on every number DE writes, and `agree` failed on wall time, CPU time,
#: resident memory and the two models fitted from them - a different subset on every run.
#:
#: A key NAMES a resource when one of its words - split at `_` and at a lower-to-upper case change -
#: is one of these. The words are the quantities, not any tool's spelling of them; `time` is
#: deliberately absent, because pseudotime and latent time are RESULTS of some tools, and only
#: `wall` and `cpu` say which clock was read. Only identifier-shaped keys are read: a population or
#: a gene that becomes a key carries spaces or punctuation often enough, and the fixture's own names
#: are held outside this rule by a test (tests/test_a_measurement_is_reported_and_never_judged.py).
#: A resource field is RECORDED and REPORTED, never judged - by `agree` or by the baseline.
RESOURCE_WORDS = frozenset({"cores", "cpu", "wall", "walltime", "rss", "memory", "cost", "runtime"})
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_CASE_CHANGE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def _words(key: str) -> set:
    return {w.lower() for w in _CASE_CHANGE.sub("_", key).split("_") if w}


def is_resource(path: str) -> bool:
    """Whether a numeric field - `measured.wall_s`, `cores_model.x.peak`, a CSV column - is the
    execution's measurement of itself rather than a number about the data. See RESOURCE_WORDS."""
    for seg in re.sub(r"\[[^\]]*\]", "", str(path)).split("."):
        if _IDENTIFIER.match(seg) and _words(seg) & RESOURCE_WORDS:
            return True
    return False


def is_size(path: str) -> bool:
    """Whether a numeric field is a file's byte count. See SIZE_OF_A_FILE."""
    return bool(SIZE_OF_A_FILE.search(str(path)))


def judged(path: str) -> bool:
    """Whether a numeric field is compared at all: not a resource and not a byte count."""
    return not is_resource(path) and not is_size(path)


def reported(fp: dict) -> dict:
    """{"resources": [...], "byte_counts": [...]} - the `product::field` names a fingerprint
    RECORDS and no comparison judges. Printed by a check, so that what is not compared is said."""
    out = {"resources": [], "byte_counts": []}
    for rel, item in sorted((fp.get("products") or {}).items()):
        for k in sorted(item.get("numbers") or {}):
            if is_resource(k):
                out["resources"].append(f"{rel}::{k}")
            elif is_size(k):
                out["byte_counts"].append(f"{rel}::{k}")
    return out


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
_TEXTISH = {".yml", ".yaml", ".cfg", ".ini", ".toml"}

# THE BASELINE COMPARES DATA. A RENDERING IS CHECKED FOR PRESENCE.
#
# A report, a README and a figure are DERIVED from the run's data, and their bytes move for
# reasons that are not the numbers: an embedded path, a font, a summary of a product's size. One
# of scIntegrate's runs writes a README whose table reports "13.0 MB" for an object the baseline
# has already measured as not execution-stable - so the document inherited an instability that
# was already recorded against the object it describes, and reported it a second time as if it
# were news.
#
# Comparing them adds no independent signal: a change that moves a number moves report.json and
# the CSVs, which are parsed and compared field by field. So a rendering is recorded as present
# and nothing more - a rendering that VANISHES is still a finding, and that is the part worth
# keeping. Real data artefacts (.h5ad, .npy, anything unrecognised) keep size and content.
_RENDERING = {".md", ".html", ".htm", ".rst", ".txt", ".log",
              ".pdf", ".png", ".svg", ".jpg", ".jpeg"}


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


class StaleBaseline(ValueError):
    """The baseline was written by a different fingerprint format. Not a difference in the
    numbers, and reporting it as one wastes the reader's afternoon."""


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


def fingerprint(run_dir, skip_content=()) -> dict:
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
        elif p.suffix.lower() in _RENDERING:
            items[rel] = {"kind": "rendering", "bytes": p.stat().st_size}
        else:
            # A FILE THE BASELINE ALREADY CALLS UNSTABLE IS NOT WORTH HASHING. Its content is
            # excluded from the comparison, so reading it buys nothing. Size is still recorded,
            # for a reader and for one finding: a product that vanished, or is there and empty,
            # is a finding whatever its bytes do. A size is not compared (autodev W019).
            items[rel] = {"kind": "opaque", "bytes": p.stat().st_size,
                          "sha256": None if rel in skip_content else _opaque_digest(p)}
    return {"baseline": FORMAT, "rtol": RTOL, "atol": ATOL, "products": items,
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
            "covers": sorted(k for k, v in items.items() if v["kind"] in ("json", "csv")),
            "presence_only": sorted(k for k, v in items.items() if v["kind"] == "rendering"),
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
        if a["kind"] == "rendering":
            continue                     # present in both; its bytes are not a measurement
        if a["kind"] == "opaque":
            # THE CONTENT IS THE FINGERPRINT; THE SIZE IS NOT (autodev W019, GAP-C41). A size
            # moves with every timestamp and timing written into the file, so it failed on the
            # next execution for a reason that was never the content - and where the content
            # agrees, the size adds nothing. The size is still recorded. What a size used to catch
            # that the content cannot, once the content is named unstable, is a product that is
            # there and EMPTY: that is still a finding, and so is one that vanished (`absent`).
            if (b.get("bytes") or 0) > 0 and a.get("bytes") == 0:
                out.append({"product": rel, "what": "emptied",
                            "detail": f"{b.get('bytes')}b -> 0b"})
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
                if not judged(col):
                    continue                 # a resource or a byte count: recorded, not judged
                for stat in ("n", "nan", "sum", "min", "max"):
                    if not _close(an[col].get(stat), bn[col].get(stat), rtol, atol) \
                            and keep(rel, f"{col}.{stat}"):
                        out.append({"product": rel, "what": f"{col}.{stat}",
                                    "detail": f"{bn[col].get(stat)} -> {an[col].get(stat)}"})
            continue
        an = {k: v for k, v in (a.get("numbers") or {}).items() if judged(k)}
        bn = {k: v for k, v in (b.get("numbers") or {}).items() if judged(k)}
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
    if int(ref.get("baseline") or 1) != FORMAT:
        raise StaleBaseline(
            f"{p} was recorded by fingerprint format {ref.get('baseline')}, and this is format "
            f"{FORMAT}. What is recorded has changed shape, so the two cannot be compared field "
            f"by field. Re-record it - `sch dev check --record-baseline` - and say in the commit "
            f"that the format moved, not the numbers.")
    skip = {k.split("::", 1)[0] for k in (ref.get("not_execution_stable") or [])
            if k.endswith("::content")}
    return compare(fingerprint(run_dir, skip_content=skip), ref), ref
