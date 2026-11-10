"""`sch conform terms build COHORT --out FILE`: a cohort's word list, GENERATED from its records.

WHY GENERATED (W024, GAP-008). Each cohort's `docs/forbidden_terms.txt` was written by hand once
and never grew: sample names, site strings, four counts. It held no factor level, so the first
cohort's age and diet levels sat in two tools' test fixtures and passed; no small count, no
"N of M", no margin, so W011's builder and verifier found 59 of the first cohort's measured
numbers in one tool by hand. A list that a person must remember to extend is a list that misses
whatever nobody remembered. This one is rebuilt from the cohort's own records.

WHAT IT READS, NEVER WRITES. The sheets (`stages/*/design*.csv`, `stages/*/samplesheet*`), the
records (`RUNLOG.md`, `DECISIONS.md`, `PROTOCOL.md` and `PROMOTED*.md` under `stages/*/` and
`results/*/`), the hand list (`docs/forbidden_terms.txt`, carried verbatim and first), a hand-kept
stems file, and lists handed back by earlier work. The output holds the cohort's strings by
design, so it is refused anywhere inside the cohort and inside any repository: it lives with the
cohort and is installed there by a person, after review.

EVERY TERM SITS UNDER THE LINE IT CAME FROM, `# [class] file:line  text`, so a reviewer can see why
each one is there - and a term nobody can source is said to be unsourced.

Nothing here names a cohort. The rules are shapes - a factor's levels, a comma-grouped count, a
count beside a measuring word - and the field's own vocabulary (the profile's axes) is never listed.
"""
from __future__ import annotations

import csv
import datetime as _dt
import re
import sys
from pathlib import Path

from .checks import Term, _TOKEN, _is_binary

SHEETS = ("stages/*/design*.csv", "stages/*/samplesheet*.tsv", "stages/*/samplesheet*.csv")
RECORDS = ("stages/*/RUNLOG.md", "stages/*/DECISIONS.md", "stages/*/PROTOCOL.md",
           "stages/*/PROMOTED*.md", "results/*/PROMOTED*.md",
           # The cohort's README and docs state measured numbers the stage records do not
           # (W024 fix-up: a share in the README, a ceiling in a portability note).
           "README.md", "docs/**/*.md")
#: Where a cohort's job scripts are, for the queues they name.
JOBS = ("stages/*/jobs/*.pbs", "stages/*/*.pbs", "jobs/*.pbs")
SITE_SHAPES = "docs/site_shapes.txt"
HAND = "docs/forbidden_terms.txt"
#: The first line of every generated list says so. A hand list that says it is refused: a generated
#: list read back as the hand list would be carried verbatim by every later build, and no term could
#: ever leave it. The generated list is installed BESIDE the hand list, never over it.
GENERATED = "GENERATED from this cohort's records"
STEMS = "docs/leak_stems.txt"
SAMPLE_COLUMNS = ("sample", "sample_id", "sample_name", "library", "library_id")
#: Where a handed-back term is looked for, to give it a source line: the cohort's text, minus its
#: data, file by file up to this size.
SEARCH_MAX_BYTES = 2 * 1024 * 1024

# ------------------------------------------------------------------------------- the rules
# A NUMBER IS NEVER TAKEN FROM INSIDE ANOTHER: not after a digit or a digit-and-separator, not
# before a separator-and-digit. `3.12.13` is a version, not 3.12 and 12.13; `2,047` holds no 47.
_NUM_L = r"(?<![0-9])(?<![0-9][.,])"
_NUM_R = r"(?![0-9])(?![.,][0-9])"
_COMMA = re.compile(_NUM_L + r"(\d{1,3}(?:,\d{3})+)" + _NUM_R)
_DECIMAL = re.compile(_NUM_L + r"(\d+\.\d+)" + _NUM_R)
_PERCENT = re.compile(_NUM_L + r"(\d+\.\d+)\s?%")
_N = r"\d{1,3}(?:,\d{3})+|\d+"
_FRACTION = re.compile(_NUM_L + rf"({_N})\s+of\s+({_N})" + _NUM_R)
# PLURAL ONLY: every count taken is ten or more, and the singular after a number is another word -
# a live record wrote a job id before the verb "read", and "a 50 gene signature" counts no gene.
# UMI is the exception: it is written as a unit after a count.
_NOUNS = (r"cells|nuclei|genes|barcodes|droplets|reads|umis?|features|clusters|samples|libraries|"
          r"animals|mice|markers|doublets|labels|organoids|donors")
_PARTICIPLES = r"predicted|flagged|removed|kept|retained|dropped|withheld|called"
_VERBS = r"held|kept|removed|dropped|retained|withheld|flagged|predicted"
_COUNT_THEN_WORD = re.compile(_NUM_L + rf"(\d{{2,6}})\s+({_NOUNS}|{_PARTICIPLES})\b", re.I)
_WORD_THEN_COUNT = re.compile(rf"\b({_VERBS})\s+(\d{{2,6}})" + _NUM_R, re.I)
_MARGIN = re.compile(r"\b(gap|margin|delta|AUC|ARI|NMI)(\s*[=:]?\s*)(\d*\.\d{2,})" + _NUM_R, re.I)

CLASSES = ("carried", "stem", "sample", "level", "identifier", "count", "fraction", "measured",
           "percentage", "margin", "value", "carry")

# A SETTING OR A CONSTANT IS NOT A MEASUREMENT (measured on the eight repositories, W024). The
# first lists put `100.0` in every tool that computes a percentage, MAD's normal-consistency
# constant in every tool that uses MAD, a `top-N markers` and a quoted read-count threshold in
# tools that set the same defaults. So: a decimal needs four significant digits once its zeros at BOTH ends
# are gone (`100.0` has one); a percentage needs two (`0.1%` is a default); a number after `<`,
# `>`, `≤` or `≥` is a threshold; a `top-N` is a setting; and the constants of statistics below
# are the field's, whoever writes them down.
_CONSTANTS = {"1.4826", "0.6745", "1.349", "2.576", "2.5758", "3.1416", "3.14159", "2.7183",
              "2.71828", "1.4142", "0.6931"}
_THRESHOLD = re.compile(r"(?:[<>≤≥]|top[- ])\s*$", re.I)


def _setting(line: str, start: int) -> bool:
    return bool(_THRESHOLD.search(line[max(0, start - 6):start]))


# A DATE IS NOT A COUNT (W024 fix-up): `Removed 2026-08-06` gave `Removed 2026`.
_DATE = re.compile(r"(?<![0-9])(?:19|20)\d{2}-\d{2}(?:-\d{2})?(?![0-9])")


def _in_a_date(line: str, start: int, end: int) -> bool:
    return any(d.start() < end and start < d.end() for d in _DATE.finditer(line))


def _in_a_path(line: str, start: int, end: int) -> bool:
    """Is this match inside a run of non-space text holding a `/` - a path, a URL, a DOI
    (`10.1016/...` is a publisher's prefix, not a measurement), a fraction written `3/10`?"""
    a = start
    while a > 0 and not line[a - 1].isspace():
        a -= 1
    b = end
    while b < len(line) and not line[b].isspace():
        b += 1
    return "/" in line[a:b]


def _significant(number: str) -> int:
    """Significant digits of a decimal as written, its zeros at both ends dropped: `100.0` has
    one, `0.120` two, `0.8642` four."""
    return len(number.replace(".", "").replace(",", "").strip("0"))


def _value(number: str) -> float:
    return float(number.replace(",", ""))


def _excerpt(line: str, n: int = 110) -> str:
    s = " ".join(line.split())
    return s if len(s) <= n else s[:n - 3] + "..."


def _phrase(s: str) -> str:
    return " ".join(s.split())


# ------------------------------------------------------------------------------- the reading
def _rel(p: Path, root: Path) -> str:
    return p.relative_to(root).as_posix()


def _glob(root: Path, patterns) -> list:
    out = []
    for pat in patterns:
        out += [p for p in sorted(root.glob(pat)) if p.is_file() and p not in out]
    return out


def _sheet(p: Path):
    """(header, [(line number, row)]) of a design sheet or samplesheet; `#` lines are skipped."""
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    data = [(n, l) for n, l in enumerate(lines, 1) if l.strip() and not l.lstrip().startswith("#")]
    if not data:
        return [], []
    delim = "\t" if p.suffix == ".tsv" else ","
    rows = list(csv.reader([l for _, l in data], delimiter=delim))
    header = [h.strip() for h in rows[0]]
    return header, [(data[i][0], [c.strip() for c in r]) for i, r in enumerate(rows[1:], 1)]


def _numeric(v: str) -> bool:
    try:
        float(v)
        return True
    except ValueError:
        return False


def _axes(profile: str) -> set:
    from ..profile import load_profile
    try:
        return {a.lower() for a in load_profile(profile).axes}
    except Exception:                                                     # noqa: BLE001
        return set()


class _List:
    """The terms in the order they are written, one entry per term (case-insensitive)."""

    def __init__(self):
        self.order, self.by_key, self.dropped = [], {}, []
        self.not_terms = {}              # handed-back line -> why a person says it is no term

    def add(self, cls, line, source, excerpt="", note=""):
        key = Term(line).low
        if key in self.by_key:
            return False
        e = {"cls": cls, "line": line, "source": source, "excerpt": excerpt, "notes": []}
        if note:
            e["notes"].append(note)
        self.order.append(e)
        self.by_key[key] = e
        return True

    def note(self, line, text):
        e = self.by_key.get(Term(line).low)
        if e is not None:
            e["notes"].append(text)
        return e is not None

    def drop(self, why):
        self.dropped.append(why)


def _from_sheets(cohort: Path, axes: set, out: _List):
    for p in _glob(cohort, SHEETS):
        rel = _rel(p, cohort)
        header, rows = _sheet(p)
        if not header or not rows:
            continue
        lower = [h.lower() for h in header]
        si = next((lower.index(c) for c in SAMPLE_COLUMNS if c in lower), 0)
        for n, row in rows:
            if si < len(row) and row[si]:
                out.add("sample", f"word:{row[si]}", f"{rel}:{n}", f"column {header[si]}")
        for j, col in enumerate(header):
            if j == si:
                continue
            cells = [(n, r[j]) for n, r in rows if j < len(r) and r[j]]
            distinct = list(dict.fromkeys(v for _, v in cells))
            if col.lower() in axes or not distinct:
                continue                 # the field's vocabulary: S13's business, not S1's
            if any("/" in v for v in distinct) or all(_numeric(v) for v in distinct):
                continue                 # paths and numbers are not levels
            if len(distinct) < 2:
                continue                 # one value across the cohort is not a factor
            cls = "identifier" if len(distinct) == len(cells) and len(cells) > 2 else "level"
            for v in distinct:
                n = next(n for n, x in cells if x == v)
                if len(v) < 2:
                    out.drop(f"level {v!r} ({rel} column {col}): one character cannot be told "
                             f"from ordinary text")
                    continue
                # TWO CHARACTERS KEEP THEIR CASE; THREE OR MORE MATCH IN ANY CASE (W024 fix-up). A
                # two-character token in another case is overwhelmingly an identifier - `wt` the
                # variable, gzip's "wt" mode - so a two-letter level is exact. From three characters a recased
                # copy is the leak's own shape: the verifier found a three-letter diet level in
                # lowercase in two tools' fixtures, which an exact match let through.
                mode = "exact" if len(v) <= 2 else "word"
                out.add(cls, f"{mode}:{v}", f"{rel}:{n}", f"column {col}")


def _from_records(cohort: Path, out: _List):
    stats = {"round": 0}
    for p in _glob(cohort, RECORDS):
        rel = _rel(p, cohort)
        for n, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            src, ex = f"{rel}:{n}", _excerpt(line)

            def take(cls, term, m):
                if _in_a_date(line, m.start(), m.end()):
                    stats["date"] = stats.get("date", 0) + 1
                elif _setting(line, m.start()):
                    stats["setting"] = stats.get("setting", 0) + 1
                elif not _in_a_path(line, m.start(), m.end()):
                    out.add(cls, f"word:{term}", src, ex)

            for m in _COMMA.finditer(line):
                num = m.group(1)
                if _value(num) % 100 == 0:
                    stats["round"] += 1
                    continue
                take("count", num, m)
                if _value(num) >= 10000:
                    take("count", num.replace(",", ""), m)
            for m in _FRACTION.finditer(line):
                if _value(m.group(2)) >= 10:
                    take("fraction", f"{m.group(1)} of {m.group(2)}", m)
            for rx in (_COUNT_THEN_WORD, _WORD_THEN_COUNT):
                for m in rx.finditer(line):
                    take("measured", _phrase(m.group(0)), m)
            for m in _PERCENT.finditer(line):
                num = m.group(1)
                frac = num.split(".")[1]
                if (len(frac) == 1 and frac in "05") or _significant(num) < 2:
                    stats["setting"] = stats.get("setting", 0) + 1
                    continue             # x.0%, x.5% and one-digit percentages read as settings
                take("percentage", f"{num}%", m)
            for m in _MARGIN.finditer(line):
                take("margin", _phrase(m.group(0)), m)
            for m in _DECIMAL.finditer(line):
                num = m.group(1)
                if _significant(num) >= 4 and num not in _CONSTANTS:
                    take("value", num, m)
    if stats["round"]:
        out.drop(f"{stats['round']} round comma-grouped number(s) (a multiple of 100 reads as a "
                 f"setting, and listing it would flag every tool with the same default)")
    if stats.get("date"):
        out.drop(f"{stats['date']} number(s) inside a date (a year is not a count)")
    if stats.get("setting"):
        out.drop(f"{stats['setting']} number(s) written as a setting - after <, >, ≤ or ≥, a "
                 f"top-N, or a percentage of one significant digit or ending .0 or .5")


def _comment_block(lines, i) -> str:
    """The `#` lines directly above line i (0-based), joined: a stem's reason."""
    got = []
    j = i - 1
    while j >= 0 and lines[j].strip().startswith("#"):
        got.insert(0, lines[j].strip().lstrip("#").strip())
        j -= 1
    return " ".join(x for x in got if x)


_PATTERN = re.compile(r"[?\\\[|^$]")


class _CohortText:
    """The cohort's text, records first, for giving a handed-back term its source line."""

    def __init__(self, cohort: Path):
        first = _glob(cohort, RECORDS) + _glob(cohort, SHEETS)
        rest = []
        for p in sorted(cohort.rglob("*")):
            rel = p.relative_to(cohort).parts
            if not p.is_file() or p.is_symlink() or rel[0] in ("data", ".git") or p in first:
                continue
            try:
                if p.stat().st_size > SEARCH_MAX_BYTES or _is_binary(p):
                    continue
            except OSError:
                continue
            rest.append(p)
        self.files = []
        for p in first + rest:
            text = p.read_text(encoding="utf-8", errors="replace")
            low = text.lower()
            self.files.append((_rel(p, cohort), text, low, set(_TOKEN.findall(low))))

    def find(self, line: str):
        t = Term(line)
        if t.rx is None:
            return None
        for rel, text, low, toks in self.files:
            if not t.admits(low, toks):
                continue
            for n, l in enumerate(text.splitlines(), 1):
                if t.rx.search(l):
                    return f"{rel}:{n}", _excerpt(l)
        return None


def _carry(files, cohort: Path, out: _List):
    text = None
    for f in files:
        f = Path(f)
        lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        for i, raw in enumerate(lines):
            s = raw.strip()
            if not s or s.startswith("#"):
                continue
            where = f"{f.name}:{i + 1}"
            if s in out.not_terms:
                out.drop(f"{s} ({where}): {out.not_terms[s]}")
                continue
            if _PATTERN.search(s):
                out.drop(f"{s} ({where}): a pattern, not a string to look for; the strings it "
                         f"stands for are listed in their own right where a record holds them")
                continue
            line = s if s.startswith(("word:", "exact:")) else f"word:{s}"
            if out.note(line, f"also handed back: {where}"):
                continue
            text = text or _CohortText(cohort)
            found = text.find(line)
            if found:
                out.add("carry", line, where, f"in the cohort: {found[0]}  {found[1]}")
            else:
                out.add("carry", line, where, "not in the cohort's text files; carried as handed back")


def _stems(files, out: _List):
    """A stems file holds terms, and `not: <a handed-back line> :: <why>` - a person's decision
    that a line someone handed back describes a leak rather than spelling one."""
    for f in files:
        f = Path(f)
        lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        for i, raw in enumerate(lines):
            s = raw.strip()
            if not s or s.startswith("#"):
                continue
            if s.startswith("not:"):
                what, _, why = s[len("not:"):].partition("::")
                if not what.strip() or not why.strip():
                    raise ValueError(f"{f}:{i + 1}: `not: <line> :: <why>` needs both")
                out.not_terms[what.strip()] = f"{why.strip()} ({f.name}:{i + 1})"
                continue
            out.add("stem", s, f"{f.name}:{i + 1}", _comment_block(lines, i))


def _refuse_where(out: Path, cohort: Path):
    o = out.resolve()
    c = cohort.resolve()
    if o == c or c in o.parents:
        raise ValueError(f"refusing to write inside the cohort ({o}): the list is installed "
                         f"there by a person, after review, never by the generator")
    for d in [o.parent, *o.parent.parents]:
        if (d / ".git").exists():
            raise ValueError(f"refusing to write inside a repository ({d}): a word list in a "
                             f"repository is the leak it exists to prevent")


def build(cohort, out, stems=(), carry=(), profile="single-cell", shapes_out=None) -> dict:
    """Write the cohort's generated list to `out` (and its site shapes to `shapes_out`, when
    named); return what was written, by class."""
    cohort, out = Path(cohort), Path(out)
    if not cohort.is_dir():
        raise FileNotFoundError(f"no cohort directory at {cohort}")
    _refuse_where(out, cohort)
    if shapes_out:
        _refuse_where(Path(shapes_out), cohort)
    stems = [Path(s) for s in stems] or ([cohort / STEMS] if (cohort / STEMS).is_file() else [])
    for f in [*stems, *map(Path, carry)]:
        if not f.is_file():
            raise FileNotFoundError(f"named and not found: {f}")
    lst = _List()
    hand = cohort / HAND
    if hand.is_file() and GENERATED in hand.read_text(encoding="utf-8", errors="replace")[:400]:
        raise ValueError(f"{hand} is a generated list, not the hand list: install the generated list "
                         f"beside the hand list (for example docs/forbidden_terms.generated.txt) and "
                         f"keep {HAND} as a person wrote it")
    if hand.is_file():
        for n, raw in enumerate(hand.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            s = raw.strip()
            if s and not s.startswith("#"):
                lst.add("carried", s, f"{HAND}:{n}")
    _stems(stems, lst)
    _from_sheets(cohort, _axes(profile), lst)
    _from_records(cohort, lst)
    _carry(carry, cohort, lst)

    by = {c: sum(1 for e in lst.order if e["cls"] == c) for c in CLASSES}
    from .. import __version__
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    head = [
        f"# {cohort.name}: words and numbers no tool may contain, {GENERATED}.",
        f"# generated {stamp} by `sch conform terms build` (single-cell-harness {__version__})",
        f"# read: {len(_glob(cohort, SHEETS))} sheet(s), {len(_glob(cohort, RECORDS))} record "
        f"file(s), {HAND if hand.is_file() else 'no hand list'}, {len(stems)} stems file(s) "
        f"({', '.join(s.name for s in stems) or 'none'}), {len(list(carry))} handed-back list(s) "
        f"({', '.join(Path(c).name for c in carry) or 'none'})",
        f"# terms: {len(lst.order)} - " + ", ".join(f"{c} {v}" for c, v in by.items() if v),
        "#",
        "# HOW A LINE IS MATCHED (`sch conform` S1, harness W024):",
        "#   T          T anywhere, in any case. The hand list's lines are carried verbatim in this form.",
        "#   word:T     T as a whole word, in any case; a number never inside a longer number.",
        "#   exact:T    the same, in T's own case only.",
        "#   ...T*      after either prefix: a word that begins with T.",
        "# A child's own guard reads every line as a substring, so a prefixed line is invisible to it:",
        "# installing this list cannot turn a child's suite red on 'bold' or 'Kobe'.",
        "#",
        "# Every term sits under the line it came from: `# [class] file:line  text`.",
        "# This file holds the cohort's strings by design. It lives with the cohort, never in a",
        "# repository, installed BESIDE the hand list (docs/forbidden_terms.generated.txt), never over it.",
        "# Do not edit it: change a record, the stems or a handed-back list, and build again.",
    ]
    body, section = [], None
    for e in lst.order:
        if e["cls"] != section:
            section = e["cls"]
            body += ["", f"# == {section} =="]
        tail = "  ".join(x for x in [e["excerpt"], *(f"| {n}" for n in e["notes"])] if x)
        body += [f"# [{e['cls']}] {e['source']}" + (f"  {tail}" if tail else ""), e["line"]]
    if lst.dropped:
        body += ["", "# == not listed, and why =="] + [f"# not listed: {d}" for d in lst.dropped]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(head + body) + "\n", encoding="utf-8")
    shapes = _shapes(cohort, Path(shapes_out), stamp, __version__) if shapes_out else None
    return {"out": str(out), "total": len(lst.order), "by_class": {c: v for c, v in by.items() if v},
            "not_listed": len(lst.dropped), "shapes_out": str(shapes_out) if shapes_out else None,
            "shapes": shapes}


# QUEUES AND BARE JOB IDS ARE THE SITE'S SHAPES, NOT A COHORT'S WORDS (W024 fix-up). A queue's
# name is often an ordinary word; `-q <queue>` names a site. And a job id written bare, `PBS` and
# six digits, passed every list, because a list names ids one at a time and the next run has a
# new one.
_QUEUE_DIRECTIVE = re.compile(r"^#PBS\s+-q\s+([A-Za-z][\w.-]*)", re.M)
_QUEUE_COMMAND = re.compile(r"\bqsub\b[^\n`]*?\s-q\s+([A-Za-z][\w.-]*)")
_QUEUE_PROSE = re.compile(r"\bqueue\s+`([A-Za-z][\w.-]*)`")
_JOB_ID = re.compile(r"\bPBS\s+(\d{5,8})\b")


def _shapes(cohort: Path, out: Path, stamp: str, version: str) -> int:
    """Write the site's shapes for this cohort: its own `docs/site_shapes.txt` carried verbatim,
    then a queue shape over every queue its jobs and records name, and a bare job id of the
    lengths its records write. Returns how many shapes were written."""
    lines, n = [], 0
    own = cohort / SITE_SHAPES
    if own.is_file():
        lines += ["", f"# == carried: {SITE_SHAPES}, verbatim =="]
        for i, raw in enumerate(own.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            s = raw.strip()
            if s and not s.startswith("#"):
                lines += [f"# [carried] {SITE_SHAPES}:{i}", s]
                n += 1
    queues, ids = {}, {}
    for p in _glob(cohort, JOBS):
        for m in _QUEUE_DIRECTIVE.finditer(p.read_text(encoding="utf-8", errors="replace")):
            queues.setdefault(m.group(1), _rel(p, cohort))
    for p in _glob(cohort, RECORDS):
        for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for rx in (_QUEUE_COMMAND, _QUEUE_PROSE):
                for m in rx.finditer(line):
                    queues.setdefault(m.group(1), f"{_rel(p, cohort)}:{i}")
            for m in _JOB_ID.finditer(line):
                ids.setdefault(len(m.group(1)), f"{_rel(p, cohort)}:{i}")
    if queues:
        names = sorted(queues)
        lines += ["", "# == generated: the queues this cohort's jobs and records name =="]
        lines += [f"# [queue] {q}: {queues[q]}" for q in names]
        lines.append(rf"(?<![\w-])-q\s+(?:{'|'.join(re.escape(q) for q in names)})\b :: "
                     f"a queue of this site (-q <queue>) :: -q")
        n += 1
    for k in sorted(ids):
        lines += ["", "# == generated: a job id written bare, as this cohort's records write it ==",
                  f"# [job id] {ids[k]}", rf"\bPBS \d{{{k}}}\b :: a scheduler job id written bare "
                  f"(PBS <{k} digits>) :: PBS"]
        n += 1
    head = [f"# {cohort.name}: the site's shapes for `sch conform REPO --shapes FILE`, {GENERATED}.",
            f"# generated {stamp} by `sch conform terms build` (single-cell-harness {version})",
            "# One per line: <regex> :: <what it is> :: <literal>. Installed beside the site's own",
            f"# {SITE_SHAPES} by a person, after review; never in a repository."]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(head + lines) + "\n", encoding="utf-8")
    return n


def run_cli(a) -> int:
    """`sch conform terms build COHORT --out FILE --stems FILE --carry FILE --shapes-out FILE`
    (all but --out optional; stems and carry repeatable), as the conform parser read it.
    Anything else that reached here is refused by name."""
    if a.repo != "terms" or a.verb != "build" or not a.cohort:
        print("refused: the generator is `sch conform terms build COHORT --out FILE`, and "
              "--out, --stems and --carry belong to it alone (a repository named terms is "
              "checked as ./terms)", file=sys.stderr)
        return 2
    if not a.out:
        print("refused: `sch conform terms build` needs --out FILE - the list is written outside "
              "the cohort and outside any repository, and installed by a person", file=sys.stderr)
        return 2
    try:
        s = build(a.cohort, a.out, a.stems or [], a.carry or [],
                  shapes_out=getattr(a, "shapes_out", None))
    except (ValueError, FileNotFoundError) as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    print(f"wrote {s['out']}: {s['total']} term(s) - "
          + ", ".join(f"{c} {v}" for c, v in s["by_class"].items())
          + (f"; {s['not_listed']} line(s) say what was not listed and why" if s["not_listed"] else ""))
    if s["shapes_out"]:
        print(f"wrote {s['shapes_out']}: {s['shapes']} shape(s)")
    return 0
