"""The rules of a development round, declared by the repository and checked rather than promised.

WHY A ROUND HAS RULES AT ALL. A maker's only real evidence is a plugin it has never seen. That
evidence is destroyed by ordinary helpfulness: fix the eight plugins that are broken and there is
nothing left to test the maker on; hand-edit the one plugin being converted and the maker is no
longer what produced it. So a round states, up front, which files are OUTPUT, which are HELD OUT,
and which are the mechanism that may be worked on - and then the statement is worth exactly as
much as the thing that checks it.

THIS FILE IS THAT THING. It holds no repository's vocabulary: the rules are read from the
repository's own declaration, the artefacts from its own extension point, and the history from its
own git. What it contributes is the four questions and the refusal to answer any of them from
silence.

WHAT EACH RULE REDUCES TO.

  held_out   - named artefacts, unchanged in the range. Asked of git, which is the only witness
               that does not depend on anybody remembering.

  in_place   - every path changed in the range is inside the declared mechanism, or is the
               artefact the round is converting. A change outside both is out of scope, and the
               point of saying so is that scope creep is invisible one commit at a time.

  maker_output - the hard one, and the one worth the most. A plugin is the maker's OUTPUT, so
               general mechanism inside it is either generated or hand-written, and only the
               second is a defect. THE SIGNAL IS DUPLICATION: method is written once because it
               is about one method; mechanism appears twice because it is about all of them.
               Measured on the family this was written for, a plugin carried THREE byte-similar
               copies of a ceiling reader and SIX copies of a draw wrapper, in three variants -
               and one of those variants recorded, in its own comment, a run lost because a
               function defined in two of the copies was missing from the third. A generated
               definition cannot have that defect; three hand-written ones cannot avoid it.

  end_to_end - what the round runs end to end is the complement of what it holds out, and neither
               list may quietly grow into the other.

NOTHING HERE WRITES. A rule check that could repair what it found would be the one tool in the
round permitted to break the rules it enforces.
"""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from . import convert as CV
from . import points as pts

HELD, BROKEN, CANNOT_SAY = "held", "BROKEN", "cannot say"

#: A block shorter than this is a coincidence: an `if`, a `try`, a two-line guard. Eight
#: significant lines repeated verbatim is not something two methods do by accident.
MIN_BLOCK = 8


def declared(doc):
    """The `rules:` block of a repository's declaration, or {}. Absence is an answer, not a pass."""
    r = doc.get("rules")
    return r if isinstance(r, dict) else {}


def since_of(doc):
    """The commit the round declares it started at, or "".

    WHY THE START IS DECLARED AND NOT PASSED IN. Two of these rules are answered from history, so
    whoever chooses the range chooses the answer - and the flattering range is always available.
    Pinning it in the declaration makes the range part of the claim: moving it is a diff, and a
    reader can see it move. `--since` still overrides, and the report says which it used.
    """
    return str((declared(doc).get("since") or {}).get("commit") or "")


def _git(cwd, *args):
    try:
        p = subprocess.run(("git",) + args, cwd=str(cwd), capture_output=True, text=True,
                           timeout=60)
    except (OSError, subprocess.SubprocessError) as e:                     # noqa: BLE001
        return False, "", str(e)
    return p.returncode == 0, p.stdout.strip(), p.stderr.strip()


def changed(root, since):
    """([paths], note) changed between `since` and the working tree, including uncommitted work.

    UNCOMMITTED WORK COUNTS. A rule that only read commits would call a tree clean while a
    held-out plugin sat modified on disk, which is the state a person is actually in when they
    are about to break the rule.
    """
    ok, top, note = _git(root, "rev-parse", "--show-toplevel")
    if not ok:
        return None, f"not a git repository: {note or 'git said nothing'}"
    ok, _out, note = _git(top, "rev-parse", "--verify", f"{since}^{{commit}}")
    if not ok:
        return None, f"{since!r} is not a commit in this repository"
    paths = set()
    for args in (("diff", "--name-only", f"{since}", "--"),
                 ("diff", "--name-only", "--"),
                 ("diff", "--name-only", "--cached", "--"),
                 ("ls-files", "--others", "--exclude-standard")):
        ok, out, _n = _git(top, *args)
        if ok:
            paths.update(ln for ln in out.splitlines() if ln.strip())
    return sorted(paths), f"{len(paths)} path(s) changed since {since}"


def _under(path, roots):
    p = Path(path)
    for r in roots:
        r = Path(str(r))
        if p == r or r in p.parents:
            return True
    return False


def _artefact_paths(doc, point_name, names):
    """{artefact: repository-relative path}. The artefact itself, never its companions."""
    out = {}
    root = Path(str(doc.get("_root") or "."))
    for n in names:
        f = CV.artefact(doc, point_name, n)
        if f is not None:
            try:
                out[n] = str(f.resolve().relative_to(root.resolve()))
            except ValueError:
                out[n] = str(f)
    return out


def _with_companions(doc, point_name, names):
    """The artefacts' paths AND the files generated beside them, all repository-relative.

    A GENERATED COMPANION IS IN SCOPE WHEREVER ITS ARTEFACT IS. The first version of the
    in-place rule listed the artefact alone, so the moment the maker generated a file beside the
    plugin it was converting - which is the whole point of generating it - the rule reported the
    round had left its own scope.
    """
    out, root = [], Path(str(doc.get("_root") or "."))
    for n in names:
        f = CV.artefact(doc, point_name, n)
        if f is None:
            continue
        for c in [f] + list(CV.companion_paths(f)):
            try:
                out.append(str(c.resolve().relative_to(root.resolve())))
            except ValueError:
                out.append(str(c))
    return out


import re as _re

#: `"key": value,` / `'key': value,` - one entry of a mapping literal, in either quote - and a
#: line that is nothing but brackets and commas, which is the skeleton a list of such entries
#: leaves once its entries are dropped: fifty-seven `{` / `},` pairs read as a 9-line block
#: repeated fifty-three times.
_DECL = _re.compile(r"""^(?:(['"])[\w.\-]+\1\s*:\s*\S.*|[\[\]{}(),;]+)$""")


def _significant(text):
    """[(line number, normalised line)] - what two blocks have to share to be the same block.

    Whitespace and full-line comments are dropped, in both languages a plugin here is made of.
    Two copies of a mechanism differ in their comments far more than in their code, and a
    comparison that kept the comments would report them as different and find nothing.
    """
    out = []
    for i, ln in enumerate(text.splitlines(), 1):
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        # A QUOTED KEY AND ITS VALUE IS A DECLARATION, NOT A STATEMENT. Two entries of a figure
        # plan share nine of their lines - who draws, the function, the axis, the position, the
        # ceiling, the device, the size - and differ in the expression and the legend; that is
        # the plan's shape. Mechanism is statements: calls, assignments, control flow, and none
        # of those is written as `"key": value,` or as a line of brackets.
        if _DECL.match(s):
            continue
        out.append((i, " ".join(s.split())))
    return out


def _windows(sig, n):
    for i in range(len(sig) - n + 1):
        body = "\n".join(s for _ln, s in sig[i:i + n])
        yield i, hashlib.sha256(body.encode()).hexdigest()[:16]


def repeated_blocks(texts, n=MIN_BLOCK):
    """[{digest, lines, places}] for every maximal run of >= n significant lines appearing twice.

    `texts` is [(label, source)]. Places are (label, first line, last line). A block repeated
    inside ONE artefact and a block shared BETWEEN two are both reported, because both say the
    same thing: this is not about one method.
    """
    sigs = {label: _significant(t) for label, t in texts}
    seen = {}
    for label, sig in sigs.items():
        for i, d in _windows(sig, n):
            seen.setdefault(d, []).append((label, i))
    out = []
    for d, at in seen.items():
        if len(at) < 2:
            continue
        # GROW EACH OCCURRENCE WHILE THEY ALL STILL AGREE, so a 40-line duplicate is one row and
        # not thirty-three overlapping ones.
        k = n
        while True:
            nxt = set()
            for label, i in at:
                sig = sigs[label]
                if i + k >= len(sig):
                    nxt = None
                    break
                nxt.add(sig[i + k][1])
            if nxt is None or len(nxt) != 1:
                break
            k += 1
        places = [(label, sigs[label][i][0], sigs[label][i + k - 1][0]) for label, i in at]
        out.append({"digest": d, "lines": k, "places": sorted(places), "start": min(i for _l, i in at)})
    # DROP A BLOCK THAT IS ONLY THE INSIDE OF A LONGER ONE. Every start offset inside a 33-line
    # duplicate is itself a duplicate, so the raw answer for three copies of one wrapper was the
    # same block printed eleven times at 33, 32, 31 ... lines. Containment is by LINE RANGE and
    # not by start: the shorter runs share the longer one's end and only differ where they begin.
    out.sort(key=lambda r: (-r["lines"], r["places"][0]))
    kept, covered = [], []
    for r in out:
        inside = any(
            all(any(lab == klab and a >= ka and b <= kb for klab, ka, kb in k)
                for lab, a, b in r["places"])
            for k in covered)
        if inside:
            continue
        covered.append(r["places"])
        kept.append(r)
    return kept


def check(doc, point_name, specs, root=".", since=""):
    """[{rule, verdict, says, detail}] - one row per declared rule, in declaration order."""
    rules = declared(doc)
    rows = []
    if not rules:
        return [{"rule": "(none declared)", "verdict": CANNOT_SAY,
                 "says": "this repository's DEVPOINTS.yaml declares no `rules:` block, so a "
                         "round has stated no rules and nothing can be enforced",
                 "detail": []}]
    names = [n for n, _s in specs]
    paths = _artefact_paths(doc, point_name, names)
    diff, note = (changed(root, since) if since else (None, "no range given: pass --since REF"))

    for rid, block in rules.items():
        if rid == "since":
            continue
        block = block if isinstance(block, dict) else {}
        want = [str(x) for x in (block.get("names") or [])]
        under = [str(x) for x in (block.get("paths") or [])]
        says, detail, verdict = "", [], HELD

        if rid == "held_out":
            unknown = [n for n in want if n not in names]
            if diff is None:
                verdict, says = CANNOT_SAY, note
            else:
                touched = sorted(n for n in want if paths.get(n) in diff)
                verdict = BROKEN if touched else HELD
                says = (f"{len(touched)} of {len(want)} held-out {point_name}(s) changed"
                        if touched else
                        f"{len(want)} held-out {point_name}(s), none changed; {note}")
                detail = [f"{n}  {paths.get(n, '?')}" for n in touched]
            if unknown:
                detail.append(f"declared held out and not present at this point: "
                              f"{', '.join(unknown)}")

        elif rid == "in_place":
            # THE ARTEFACT BEING CONVERTED IS IN SCOPE BY DEFINITION - it is the round's
            # output. The held-out ones are not, and `held_out` above is what rules on them.
            _held = set(str(x) for x in ((rules.get("held_out") or {}).get("names") or []))
            allowed = list(under) + _with_companions(doc, point_name,
                                                     [n for n in names if n not in _held])
            if diff is None:
                verdict, says = CANNOT_SAY, note
            else:
                stray = sorted(p for p in diff if not _under(p, allowed))
                verdict = BROKEN if stray else HELD
                says = (f"{len(stray)} changed path(s) outside the declared mechanism"
                        if stray else f"every changed path is declared mechanism; {note}")
                detail = stray[:40]

        elif rid == "maker_output":
            # THE ONLY RULE THAT NEEDS NO HISTORY, and the only one that catches the violation
            # after the commit that made it has scrolled away.
            texts = []
            for n in names:
                f = CV.artefact(doc, point_name, n)
                if f is not None:
                    texts.append((n, f.read_text(encoding="utf-8", errors="replace")))
            if not texts:
                verdict, says = CANNOT_SAY, f"no {point_name} could be read"
            else:
                dup = repeated_blocks(texts, int(block.get("min_block") or MIN_BLOCK))
                verdict = BROKEN if dup else HELD
                says = (f"{len(dup)} block(s) of >= {block.get('min_block') or MIN_BLOCK} "
                        f"significant lines appear more than once - mechanism is written once "
                        f"or generated, never copied"
                        if dup else
                        f"{len(texts)} {point_name}(s) read; no block of "
                        f"{block.get('min_block') or MIN_BLOCK}+ significant lines is repeated")
                for r in dup[:12]:
                    detail.append(f"{r['lines']:>4} lines x{len(r['places'])}  " +
                                  "  ".join(f"{a}:{b}-{c}" for a, b, c in r["places"]))
                if len(dup) > 12:
                    detail.append(f"and {len(dup) - 12} more")

        elif rid == "end_to_end":
            held = [str(x) for x in ((rules.get("held_out") or {}).get("names") or [])]
            rest = sorted(set(names) - set(held))
            verdict = HELD if sorted(want) == rest else BROKEN
            says = (f"end to end is {', '.join(want) or 'nothing'}; the complement of the "
                    f"held-out set is {', '.join(rest) or 'nothing'}")
            if verdict == BROKEN:
                detail = [f"declared: {', '.join(want) or '-'}",
                          f"complement: {', '.join(rest) or '-'}"]
        else:
            verdict, says = CANNOT_SAY, "no check is defined for this rule id"

        rows.append({"rule": rid, "verdict": verdict, "says": says, "detail": detail,
                     "means": str(block.get("means") or "").strip()})
    return rows


def format_report(rows, point_name, since=""):
    L = [f"the rules of this round, checked against {point_name}s"
         + (f" and history since {since}" if since else ""), ""]
    for r in rows:
        L.append(f"  {r['verdict']:<10} {r['rule']:<14} {r['says']}")
        for d in r["detail"]:
            L.append(f"                            {d}")
        if r["verdict"] == BROKEN and r.get("means"):
            for ln in str(r["means"]).splitlines():
                if ln.strip():
                    L.append(f"                            | {ln.strip()}")
        L.append("")
    bad = sum(1 for r in rows if r["verdict"] == BROKEN)
    mute = sum(1 for r in rows if r["verdict"] == CANNOT_SAY)
    L.append(f"  {len(rows) - bad - mute} held, {bad} broken, {mute} could not be established")
    return "\n".join(L)
