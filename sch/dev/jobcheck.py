"""The shell defects this family has actually paid for, checkable on ANY job script.

WHY THIS IS A MODULE AND NOT FIVE MORE TEST METHODS. These checks existed, as assertions inside
tests/test_convert.py, and every one of them globbed `<harness>/jobs/*.pbs`. So they guarded the
jobs kept in this repository and NOTHING ELSE - and the job you are about to submit is very often
not one of those. It is written for a cohort, it lives beside the run, and it gets none of this.

Measured, on the night this was written: a job authored in a scratch directory reproduced
`echo "  install exit: ${PIPESTATUS[0]}"` - the status displayed and not kept - and carried on
past a refused install to produce eighteen dead units, a FAILED seal and nine failed predictions
that all restated the same thing. That is the THIRD time this family has lost an exit code the
same way: `| tee` without pipefail is in docs/CHILD_CONFORMANCE.md, `$?` captured into an echo is
in tests/test_convert.py, and the checks for both were sitting in this repository unable to see
the file. A check that cannot be pointed at the thing you are about to run is a check you will
reproduce the defect in front of.

ONE DEFINITION. The ratchets in tests/test_convert.py call `problems()` too, so the command and
the suite cannot drift apart - which is the defect a mixin was extracted for elsewhere in this
codebase on the same day, for the same reason.

WHAT IT DOES NOT DO. It reads text. It does not run the job, does not know the scheduler, and
cannot tell whether the science is right - `bash -n` is the only execution-shaped thing here and
even that only parses. Every rule below exists because it once cost a submission; none of them is
a style opinion, and the list is meant to grow the same way.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

#: Each rule is (id, one-line why, predicate). A predicate takes the text and returns a list of
#: `line: offending text` strings. The id is stable so a job can silence one by name in a comment.
_RULES = []


def rule(rid, why):
    def take(fn):
        _RULES.append((rid, why, fn))
        return fn
    return take


def _lines(text):
    """(number, stripped) per logical line - CONTINUATIONS JOINED - skipping comments.

    A BACKSLASH CONTINUATION IS ONE COMMAND AND MUST BE READ AS ONE. The first version of this
    read raw lines and immediately produced two false positives against this repository's own
    `inventory_all.pbs`, one of them on a line whose `|| true` guard sat on the NEXT line - i.e.
    it reported the guarded form of the exact defect the guard was added for. A checker that
    cries wolf at correctly written code is read once and then ignored, which is worse than not
    having it, so the joining is not a nicety.
    """
    buf, start = "", None
    for i, raw in enumerate(text.splitlines(), 1):
        s = raw.strip()
        if not buf and (not s or s.startswith("#")):
            continue
        if start is None:
            start = i
        if s.endswith("\\"):
            buf += s[:-1] + " "
            continue
        out = (buf + s).strip()
        buf, at = "", start
        start = None
        if out:
            yield at, out


@rule("exit-displayed", "an exit code read into an echo is reset and kept nowhere")
def _exit_displayed(text, _p):
    return [f"{i}: {s}" for i, s in _lines(text) if re.search(r'^echo\s+.*\$\?', s)]


@rule("status-not-kept", "a command's status captured into a message and never tested")
def _status_not_kept(text, _p):
    # `echo "... ${PIPESTATUS[0]}"` is the same defect wearing the pipeline's clothes: the value
    # is printed, the next command overwrites it, and nothing ever branched on it.
    return [f"{i}: {s}" for i, s in _lines(text)
            if re.search(r'^echo\s+.*\$\{PIPESTATUS\[', s)]


@rule("tee-without-pipefail", "`cmd | tee log` exits with tee's status, so a failure reads as ok")
def _tee_without_pipefail(text, _p):
    if not re.search(r"^\s*[^#\n]*\|\s*tee\b", text, re.M):
        return []
    return [] if "pipefail" in text else ["the file pipes into tee and never sets pipefail"]


@rule("unguarded-grep-substitution",
      "a substitution whose pipeline fails ends a `set -e` shell, and grep fails when it "
      "finds nothing - which is the case the line exists to detect")
def _unguarded_grep(text, _p):
    if "set -e" not in text and "set -euo" not in text:
        return []
    out = []
    for i, s in _lines(text):
        # ONLY `grep`. awk and sed exit 0 when they match nothing; grep exits 1, which is what
        # makes it the one that ends a strict shell on the very case the line was written to
        # detect. Flagging the other two produced a false positive on an awk that cannot fail.
        #
        # AND THE SUBSTITUTION IS SCANNED BY BALANCING PARENS, not by a regex that stops at the
        # first `)`. The regex version reported this repository's own
        #     line=$(grep -m1 'function(s) exported by' ... || true)
        # because the `)` inside the quoted PATTERN ended its scan before it could see the guard
        # eleven characters later. It flagged the fixed form of the very defect it was written
        # for - which is the same shape as the defects this whole module collects.
        for m in re.finditer(r'=\s*\$\(', s):
            j, depth = m.end(), 1
            while j < len(s) and depth:
                depth += (s[j] == "(") - (s[j] == ")")
                j += 1
            inner = s[m.end():j - 1]
            if re.search(r"\bgrep\b", inner) and "||" not in inner:
                out.append(f"{i}: {s}")
                break
    return out


@rule("apostrophe-in-parameter-error",
      "an apostrophe inside ${VAR:?...} ends the word and the shell reads the rest as syntax")
def _apostrophe_in_param(text, _p):
    return [f"{i}: {s}" for i, s in _lines(text)
            for m in [re.search(r"\$\{[A-Za-z_][A-Za-z0-9_]*:\?[^}]*'", s)] if m]


@rule("no-seal", "a job that writes no seal cannot be told apart from one that never ran")
def _no_seal(text, _p):
    missing = [n for n in ("SEALED.txt", "FAILED.txt") if n not in text]
    return [f"writes no {n}" for n in missing]


@rule("does-not-parse", "bash cannot read it, so the scheduler will not either")
def _parses(_text, path):
    if not shutil.which("bash") or path is None:
        return []
    r = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True)
    return [] if r.returncode == 0 else [(r.stderr or "bash -n failed").strip()[:300]]


def problems(path):
    """[(rule id, why, [offences])] for one job script. Empty list means it passed every rule."""
    p = Path(path)
    text = p.read_text(encoding="utf-8", errors="replace")
    out = []
    for rid, why, fn in _RULES:
        # A JOB MAY SILENCE ONE RULE BY NAME, and must say so in the file where a reader will see
        # it. Anonymous suppression is how a check stops meaning anything.
        if re.search(rf"jobcheck:\s*allow\s+{re.escape(rid)}\b", text):
            continue
        hits = fn(text, p)
        if hits:
            out.append((rid, why, hits))
    return out


def report(paths, log=print):
    """Print `problems()` for each path. Returns the number of scripts with at least one."""
    bad = 0
    for path in paths:
        found = problems(path)
        if not found:
            log(f"  ok    {Path(path).name}")
            continue
        bad += 1
        log(f"  FAIL  {Path(path).name}")
        for rid, why, hits in found:
            log(f"          {rid}: {why}")
            for h in hits[:6]:
                log(f"            {h}")
            if len(hits) > 6:
                log(f"            ... and {len(hits) - 6} more")
    return bad
