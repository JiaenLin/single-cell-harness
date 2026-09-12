"""Is this maker general, or was it fitted to the one artefact it was built on?

WHY THIS IS A COMMAND AND NOT A JUDGEMENT. The maker's whole claim is that a plugin is its output,
and the only honest evidence for that is a plugin it has never seen. That evidence is expensive and
it is spent once: convert one, finish it, improve the maker from what it taught, and the NEXT one
is the test. Between those points there is nothing to appeal to but the maker's own source, and a
sentence in a commit message saying it looks general.

So this measures the two things that CAN be read off a family with no run and no conversion, and
refuses to pretend they are the third:

  CORPUS - how many artefacts a stage's instrument could actually look at. A check whose corpus is
  ONE was fitted by construction, however carefully it was written, and no change to it is
  falsifiable. Measured here: the check that a drawing wrapper honours its declared ceilings can
  only look at a plugin that embeds a second language, and in the family it was written for
  exactly one of nine does. "Clean across the held-out eight" was written in a commit message
  about that check before anybody asked what it had read.

  DISCRIMINATION - how many DISTINCT answers a stage has ever given. A stage that says the same
  thing about every artefact has never distinguished anything; it may be a constant wearing a
  check's clothes. This is the vacuity test, and it is the one that catches a stage which passes
  everywhere because it asks nothing.

  FITTED LITERALS - identifier-shaped constants in the maker's own source that occur in exactly
  ONE artefact of the family. A general tool may name a convention; it may not name a member.
  Measured here: the R namespace extractor's default pattern is CellChat's own export naming,
  which its docstring says out loud, and which no other plugin in the family could match.

WHAT IT CANNOT SAY. That a stage with nine artefacts and four distinct answers is RIGHT - only
that it is not vacuous and not fitted to one. Held-out conversion remains the gold standard and
this is not a substitute for it; it is what is available while the gold standard is still unspent.

IT READS AND NEVER WRITES, and it shows nobody an upstream surface - so it is in the same class as
`status`, `freshness` and `borrowed`, and like `borrowed` it is useless on a single artefact:
whether a maker generalises is a fact about a family or about nothing.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

from . import convert as CV

#: A literal that could be a name rather than a sentence. Messages have spaces; identifiers,
#: field names, regexes and function names do not. Three characters is the floor at which a
#: coincidence stops being likely.
_IDENTIFIERISH = re.compile(r"^[^\s]{3,}$")

#: Words that belong to Python, to this suite's own vocabulary, or to any repository at all. A
#: literal in here is not evidence of anything: it would match one artefact by accident as easily
#: as by fitting.
_NEUTRAL = frozenset("""
utf-8 ascii replace strict ignore latin-1 r w rb wb a+ __main__ __init__ __name__ __file__
name id path file line text type kind value key field stage point plugin tool root out src
true false none null yes no ok done todo error warn info debug
.py .yml .yaml .json .csv .tsv .png .pdf .md .txt .R .r
""".split())

#: THE MAKER'S OWN MACHINERY, WHICH IS EVERY REPOSITORY'S. `sch dev convert freshness` asks git
#: what a field looked like at a commit, so `show` and `diff` are literals in this suite for a
#: reason that has nothing to do with any wrapped tool - and both are also ordinary components of
#: plotting-function names, so they were reported as one plugin's vocabulary. A word here is not
#: evidence either way; it is a word the maker needs whatever it is converting.
_MACHINERY = frozenset("""
show diff log status pull fetch clone commit merge rebase checkout branch rev-parse ls-files
""".split())


def _literals(py: Path):
    """Every identifier-shaped string constant in a source file, with the line it is on.

    PARSED, NOT GREPPED, so comments and docstrings are excluded by construction. This suite
    writes its evidence in comments - the very sentences that RECORD a fitted heuristic name the
    artefact it was fitted to - and a grep would report every one of them as the defect it
    describes.
    """
    try:
        tree = ast.parse(py.read_text(encoding="utf-8", errors="replace"))
    except (OSError, SyntaxError):
        return
    docs = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", None) or []
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                docs.add(id(body[0].value))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        if id(node) in docs:
            continue
        v = node.value
        # A FLAG IS THE MAKER TALKING TO A TOOL, NOT NAMING ONE. `--show-toplevel` and
        # `--diff-filter=A` are how this suite asks git a question; split into pieces they
        # reported `show` and `diff` as a wrapped tool's vocabulary.
        if v.startswith("-") or not _IDENTIFIERISH.match(v) or v.lower() in _NEUTRAL:
            continue
        yield v, node.lineno


def code_only(text):
    """`text` with its full-line comments removed, in every language it is made of.

    A NAME MUST BE MATCHED IN CODE OR IT IS MATCHED IN PROSE. The artefacts of this family are
    files where two thirds of the lines are English: the first version of this scan reported
    `cache`, `detail`, `misses`, `dump` and `doctor` as constants naming one plugin, because each
    happened to appear in exactly one plugin's COMMENTS. That is the same false alarm the
    environment survey already paid for once, where `r-matrix` matched the English word `matrix`
    in seven plugins' comments, and the fix is the same one: scope the search to the text the
    spelling belongs to.

    FULL-LINE ONLY, and both halves of that are deliberate. Prose in these files is written in
    blocks, so removing lines whose first non-space character is `#` removes nearly all of it -
    while `col = "#4C72B0"` keeps its colour and `import x  # noqa` keeps its code. And it is
    language-neutral: `#` opens a comment in the host Python and in the R embedded inside it, so
    one rule reads a file made of both without knowing which lines are which.
    """
    return "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("#"))


def _pieces(literal):
    """The names inside a literal. A regex alternation is several names in one constant.

    `"^(netVisual|netAnalysis|plot|Plot|show|draw|gg|Stacked|vis|Vis)"` is not one name that
    happens to appear in one plugin; it is ten, and the fitted ones are hidden among generic ones
    that appear everywhere. Split first or the whole constant scores as generic.
    """
    out = {p for p in re.split(r"[^A-Za-z0-9_.]+", literal) if len(p) >= 3}
    return out or {literal}


def upstream_vocabulary(spec):
    """The wrapped tool's OWN names, as this artefact declares them.

    THE MAKER MAY NAME A CONVENTION AND MAY NOT NAME A MEMBER, and this is the set that decides
    which is which. It is the tool's name plus every upstream symbol the plugin accounts for -
    a small curated set that the plugin itself wrote down, not a guess about what is domain
    vocabulary and what is English.

    THE FIRST VERSION ASKED WHETHER A LITERAL OCCURRED IN EXACTLY ONE ARTEFACT'S SOURCE and it
    was useless: the artefacts here are files of several thousand lines, so `cache`, `detail`,
    `digest` and `dump` each landed in exactly one of them by coincidence and were reported as
    fitted constants. A corpus that large answers "is this word rare" and never "is this word
    the upstream's". Ask the declaration instead, and the noise goes to nothing.
    """
    out = set()
    wraps = spec.get("wraps")
    if isinstance(wraps, dict) and wraps.get("tool"):
        out.add(str(wraps["tool"]))
    for k in (spec.get("native_plots") or {}):
        out.add(str(k))
        out.add(str(k).rsplit(".", 1)[-1])
    return {v for v in out if len(v) >= 4}


def _yaml_tokens(text):
    """Identifier-shaped tokens of a declaration file, by line. It is not Python; do not parse it.

    The repository's own declaration is part of the maker: it is what tells a general suite which
    field of this format each stage fills. It may name the FORMAT and it may not name a member's
    upstream, so it is scanned by the same rule as the code.
    """
    depth = None
    for i, ln in enumerate(text.splitlines(), 1):
        # A BLOCK SCALAR IS PROSE, AND PROSE IS EVIDENCE RATHER THAN KNOWLEDGE THE MAKER ACTS ON -
        # exactly as a docstring is, one language over. The `why:` under this format's `defaults`
        # stage records that "decoupler's `min_n` and cellrank's terminal-state method were both
        # being passed silently", which is the sentence that JUSTIFIES the stage; read as keys it
        # reported two members' tools as constants fitting the maker to them.
        if depth is not None:
            if not ln.strip():
                continue
            if len(ln) - len(ln.lstrip()) > depth:
                continue
            depth = None
        ln = ln.split("#", 1)[0]
        if re.search(r":\s*[>|][-+0-9]*\s*$", ln):
            depth = len(ln) - len(ln.lstrip())
            continue
        for tok in re.findall(r"[A-Za-z_][A-Za-z0-9_.]{2,}", ln):
            yield tok, i


def fitted_literals(maker_files, vocab, min_len=4):
    """[{literal, piece, where, line, artefact}] for maker constants naming ONE tool's symbols.

    `vocab` is [(artefact, {upstream symbol})]. A piece that is part of one artefact's upstream
    vocabulary and no other's is knowledge the maker holds about a single member of the family.
    """
    if len(vocab) < 2:
        return []

    def names(piece, sym):
        """Does `piece` name a COMPONENT of `sym`, rather than land inside one?

        A SUBSTRING IS NOT A NAME AND THIS IS WHERE IT SHOWED. Matched as a plain substring,
        `gate` named cellchat because `netVisual_aggregate` contains it, `Stack` because
        `StackedVlnPlot` does, and `diff` because `netVisual_diffInteraction` does - three
        ordinary English words in this suite's own code reported as one plugin's upstream
        vocabulary. A symbol's components are separated by `_`, by `.`, or by a change of case,
        and a match has to start and end on one of those.
        """
        i = sym.find(piece)
        while i != -1:
            j = i + len(piece)
            head = i == 0 or sym[i - 1] in "_." or (sym[i - 1].islower() and piece[0].isupper())
            tail = j == len(sym) or sym[j] in "_." or sym[j].isupper()
            if head and tail:
                return True
            i = sym.find(piece, i + 1)
        return False

    def whose(piece):
        return [n for n, syms in vocab if any(names(piece, s) for s in syms)]

    rows, seen = [], set()
    for py in maker_files:
        items = (_literals(py) if py.suffix == ".py"
                 else _yaml_tokens(py.read_text(encoding="utf-8", errors="replace")))
        for lit, line in items:
            for piece in _pieces(lit):
                if len(piece) < min_len or piece.lower() in _MACHINERY:
                    continue
                hits = whose(piece)
                if len(hits) != 1:
                    continue
                k = (str(py), line, piece)
                if k in seen:
                    continue
                seen.add(k)
                rows.append({"literal": lit, "piece": piece, "where": str(py),
                             "line": line, "artefact": hits[0]})
    rows.sort(key=lambda r: (r["artefact"], r["where"], r["line"]))
    return rows


def _answer(row):
    """One stage's verdict on one artefact, reduced to something comparable.

    UNASKED IS BLIND. A stage that verifies a run and was given none has abstained, not
    answered: counting it as `owes` on every artefact would report one answer over the whole
    family and call the stage a constant, when the stage was never run at all.
    """
    if row.get("unasked"):
        return "blind"
    if row.get("done"):
        return "done"
    if row.get("missing"):
        return "missing:" + ",".join(sorted(row["missing"]))
    if row.get("partial"):
        return "partial"
    return "owes"


def checks_of(row):
    """[(element, answer)] for one stage on one artefact - the stage, and each instrument in it.

    A STAGE IS NOT THE UNIT. `placement` asks three separate questions with three separate
    instruments: where a family goes, how many of it there are, and whether the DRAWING CODE
    reads the ceiling at all. The first two read a declaration, so their corpus is every artefact;
    the third has to find code in whatever language the plugin draws in, and in the family this
    was written for exactly one plugin of nine embeds one. Rolled into a single stage row the
    corpus reads 9 and the answer is wrong.

    BLIND IS NOT DONE AND IT IS NOT A DEBT. An instrument that found nothing to look at has not
    passed; it has abstained. Keeping that as its own word is this module's whole subject.
    """
    out = [(row["stage"], _answer(row))]
    d = row.get("draws") or {}
    if d:
        out.append((row["stage"] + "/draw-sites",
                    "blind" if not d.get("looked") else
                    ("silent:%d" % len(d.get("silent") or ()) if d.get("silent") else "described")))
    pl = row.get("places") or {}
    if pl.get("enforces"):
        g = pl.get("guards") or []
        out.append((row["stage"] + "/ceiling-guard",
                    "blind" if not g else
                    ("unguarded:%d" % len(pl.get("unguarded") or ()) if pl.get("unguarded")
                     else "guarded:%d" % len(g))))
    return out


def stage_corpus(doc, point_name, specs):
    """[{stage, phase, kind, n, seen, blind, distinct, answers}] over every artefact at a point."""
    out = {}
    order = []
    for name, spec in specs:
        for row in CV.status(spec, doc, point_name, name):
            for st, ans in checks_of(row):
                if st not in out:
                    out[st] = {"stage": st, "phase": row.get("phase", "build"),
                               "kind": row.get("kind", "mechanical"), "answers": {}}
                    order.append(st)
                out[st]["answers"].setdefault(ans, []).append(name)
    rows = []
    for st in order:
        r = out[st]
        blind = len(r["answers"].get("blind", ()))
        n = sum(len(v) for v in r["answers"].values())
        rows.append({**r, "n": n, "blind": blind, "seen": n - blind,
                     "distinct": len([k for k in r["answers"] if k != "blind"])})
    return rows


def unasked(row):
    """A run-side stage this scan could not ask: every artefact blind, and a test-phase stage."""
    return (row.get("phase") == "test" and row["n"] > 0 and row["blind"] == row["n"])


def verdict(row):
    """The sentence a reader acts on, or "" when there is nothing to say about this element."""
    if row["kind"] == "judgement":
        return ""
    if unasked(row):
        # NOT A CORPUS STATEMENT. A run-side stage this scan handed no run has abstained on
        # every artefact; calling that "corpus 0, fitted by construction" would fail the scan
        # on a stage it never ran. `status --run RUNDIR` is where such a stage is measured.
        return ""
    if row["seen"] <= 1:
        return (f"CORPUS {row['seen']} of {row['n']}: its instrument could look at "
                f"{row['seen']} - fitted by construction, and no change to it is falsifiable "
                f"on this family")
    if row["distinct"] <= 1:
        only = next(iter(row["answers"]), "")
        if only == "done":
            # A FINISHED FAMILY CANNOT SHOW THAT A STAGE DISCRIMINATES, and calling that vacuity
            # would be a false alarm on every stage of every completed conversion. It is a real
            # gap in the evidence and it has a known filler: scaffold the artefact from nothing
            # and read what the stage says then. Measured - a plugin generated by the scaffold
            # and asked at once reported 0 of 7, so all four of these stages DO distinguish an
            # unfinished artefact from a finished one. That run is the corpus; this family is not.
            return ("ALL DONE, so this family cannot show whether it discriminates - every "
                    "artefact is finished here. Scaffold one from nothing and ask again")
        return (f"ONE ANSWER ({only}) for all {row['seen']} it read - it has never distinguished "
                f"two artefacts, so it may be a constant rather than a check")
    return ""


def unmeasured(maker_files, rows):
    """[(module, why)] for maker elements this scan does not put a corpus number on.

    A SCAN THAT DOES NOT SAY WHAT IT SKIPPED IS A SCAN THAT READS AS COMPLETE. The corpus half
    below asks one question - what could this instrument look at, across the artefacts at a point -
    and that question only has a meaning for an element that is asked PER ARTEFACT. A shell
    checker reads job scripts; a ladder reads repositories; a fixture generator reads nothing at
    all. Their corpus is real and it is not this family, so they get no row - and the way that
    fact is kept honest is by naming them rather than by their absence.

    The literal half above DOES cover them: it reads every file of the maker.
    """
    measured = {r["stage"].split("/")[0] for r in rows}
    out = []
    for f in maker_files:
        if f.suffix != ".py" or f.name.startswith("_"):
            continue
        stem = f.stem
        if stem in measured or stem in ("convert", "overfit", "points"):
            continue
        out.append((stem, "not asked per artefact at this point"))
    return sorted(set(out))


def format_report(rows, lits, point_name, names, vocab=(), skipped=()):
    L = [f"{len(names)} {point_name}(s) read: " + ", ".join(names),
         "  reads declarations and source; writes nothing, and shows no upstream surface", ""]
    L.append("  CORPUS AND DISCRIMINATION - what each stage could look at, and whether it has")
    L.append("  ever said two different things about two artefacts.")
    L.append("")
    w = max([len("element")] + [len(r["stage"]) for r in rows])
    L.append(f"    {'element':<{w}} {'phase':<6} {'read':>5} {'blind':>6} {'answers':>8}   verdict")
    bad = 0
    for r in rows:
        v = verdict(r)
        bad += bool(v)
        L.append(f"    {r['stage']:<{w}} {r['phase']:<6} {r['seen']:>5} {r['blind']:>6} "
                 f"{r['distinct']:>8}   "
                 + (v.split(" - ")[0] if v else
                    "not asked: a run-side stage; `status --run RUNDIR` measures it"
                    if unasked(r) else "ok"))
        if v:
            for tail in v.split(" - ")[1:]:
                L.append(f"    {'':<{w}} {'':<6} {'':>5} {'':>6} {'':>8}   ...{tail}")
            for a, who in sorted(r["answers"].items()):
                L.append(f"      {a:<14} {', '.join(who)}")
    L.append("")
    if not lits:
        L.append("  FITTED LITERALS - none: no constant in the maker names the upstream")
        L.append("  vocabulary of exactly one artefact of this family.")
    else:
        L.append("  FITTED LITERALS - constants in the maker that name the UPSTREAM vocabulary")
        L.append("  of exactly one artefact: its tool's name, or a symbol it accounts for. A")
        L.append("  general maker may name a convention; it may not name a member's tool.")
        L.append("")
        for r in lits:
            L.append(f"    {r['artefact']:<12} {r['piece']:<22} "
                     f"{Path(r['where']).as_posix()}:{r['line']}")
            if r["piece"] != r["literal"]:
                L.append(f"                 in  {CV._clip(r['literal'], 68)}")
    if vocab:
        # HOW MUCH OF THE FAMILY'S UPSTREAM VOCABULARY EACH MEMBER OWNS. A member holding most of
        # it makes every hit above weak evidence on its own: a generic plot-name heuristic will
        # name that member because there is barely anybody else to name. Printed so the reader
        # weighs the rows rather than counting them.
        tot = sum(len(v) for _n, v in vocab) or 1
        L.append("")
        L.append("  UPSTREAM VOCABULARY THIS SCAN HAD TO WORK WITH - the tool names and accounted")
        L.append("  symbols each artefact declares. A corpus one member dominates cannot")
        L.append("  distinguish that member's vocabulary from the family's.")
        L.append("")
        for n, v in sorted(vocab, key=lambda x: -len(x[1])):
            L.append(f"    {n:<12} {len(v):>4} symbol(s)   {100 * len(v) // tot:>3}% of the corpus")
    if skipped:
        L.append("")
        L.append("  NOT GIVEN A CORPUS NUMBER HERE - these are maker elements that are not asked")
        L.append("  per artefact, so the question above has no meaning for them. The literal scan")
        L.append("  DOES read them. Their own corpus is job scripts, repositories or a fixture.")
        L.append("")
        L.append("    " + ", ".join(m for m, _w in skipped))
    L.append("")
    L.append(f"  {bad} element(s) with a corpus of one or a single answer; "
             f"{len(lits)} fitted literal(s)")
    L.append("")
    L.append("  WHAT THIS CANNOT SAY: that a stage with a wide corpus is RIGHT. Held-out")
    L.append("  conversion is the only evidence of that, and this does not spend it.")
    return "\n".join(L)
