"""Whether a plugin's DECLARED version still describes the code that version names.

WHAT THIS IS FOR, AND IT IS A NEAR MISS AND NOT A HYPOTHETICAL. In at least one repository this
suite serves, a plugin's declared version is a REUSE KEY: a later run hands it to the landscape,
an earlier unit carrying the same key is matched, and that unit's products are HARDLINKED IN
instead of being recomputed. So a commit that changes what a plugin draws and leaves the field
alone makes every reusing run serve the old products - and report success.

Measured: thirty-five legends were added to one plugin's draw sites in a single commit and the
declared version stayed where it was. The next run reusing from the previous one would have
adopted last week's undescribed panels, printed REUSED, and the fix would have read as a failure.

WHY THE CONVERTER OWES THIS AND THE PLUGIN DOES NOT. The repository's declaration already lists
this field among the keys a plugin MUST DECLARE, so the maker demands that it exists. No stage
fills it and none should: it is not extracted from the wrapped tool, and it is not a judgement
about the method - it is a fact about this plugin's own history. Nothing in the suite had ever
asked whether the declared value was still TRUE OF THE CODE, which is a different question from
whether it is present and the only one that protects a reuse.

IT IS NOT THE ONLY VERSION-SHAPED FIELD AND THE OTHERS ARE NOT BROKEN. A plugin format may also
declare the host contract it was written against - that moves when the HOST changes, and no edit
to a plugin can make it stale - and a version of the NUMBERS, which by its own definition rises
when the same inputs would give different output, so a change to a caption correctly does not
move it. Only a field whose meaning is "this is the code" is a claim about the code. The
repository says which field that is; this module never guesses.

REPORT, NEVER WRITE. `points.py` states the policy for registration and it holds here for the
same reason and one more. The same reason: text-editing somebody's Python literal is guesswork
the moment the file is formatted differently from the way the guesser expects. The extra one: a
number is a statement by the author about what changed, and a maker that picks one has asserted
on the author's behalf. This names the plugin, the declared value, the commit that last set it,
what has happened to the file since, and what a person should do.

AND IT SAYS WHEN IT CANNOT SAY, in the idiom the extractors already use. A repository that is not
under git, a checkout with no commits, a shallow clone whose history is truncated, a file git
does not track, a field whose value is not a literal in the file, a field that two dicts both
carry, a field that has never been set as a distinct act, and an artefact this cannot read as it
stood at the commit that set the field - each is a `cannot say` and never an alarm. This suite
has shipped a false alarm from exactly this kind of inference before and it cost more than the
check was worth; the answer "I could not look" is a first-class result here.
"""
from __future__ import annotations

import ast
import os
import subprocess
from pathlib import Path

from . import convert as CV
from . import points as pts

#: Where the point names the field, inside its own `convert:` block. THE HARNESS'S KEY, NOT A
#: REPOSITORY'S FIELD - the same arrangement as `outstanding_if` and `entry_keys`.
KEY = "version_field"
#: Optional prose the repository writes about what that field is FOR. Printed in the advice,
#: because "bump it" without "and here is what silently reuses it" is a chore and not a reason.
MEANS_KEY = "version_means"

#: The four answers. `CANNOT_SAY` is not a failure and `QUESTION` is not an assertion.
CANNOT_SAY, CURRENT, QUESTION, STALE = "cannot-say", "current", "question", "stale"


class Freshness:
    """What one plugin's declared version is worth as a description of its code.

    NEVER A BARE BOOLEAN, for the reason `Inventory` is never a bare list: "the code has not
    changed" and "I could not find out whether the code changed" are different findings and only
    the first is about the plugin.
    """

    def __init__(self, plugin, field=""):
        self.plugin = plugin
        self.field = field
        self.declared = None
        self.file = ""
        #: False when this could not be worked out at all. NOT the same as "nothing has changed".
        self.complete = False
        self.why_not = ""
        #: {sha, short, date, subject} for the commit that last set the field.
        self.set_by = {}
        #: [{short, subject}] - the commits that have touched the artefact since. Named, not
        #: counted: a count sends a reader to `git log` and a list is the reason.
        self.commits_since = []
        #: True/False/None. None means the narrowing below could not be computed, and `code_why`
        #: says why. TWO THINGS LEAVE IT NONE and only one of them is `_significant`'s: a text
        #: that will not parse as Python, and a text that could not be read at all. The second
        #: used to be silent - see `_named_at`.
        self.code_changed = None
        self.code_why = ""
        #: The artefact has uncommitted changes, which no commit count can see.
        self.dirty = False
        self.verdict = CANNOT_SAY

    def __bool__(self):
        return self.complete

    def cannot(self, why):
        self.complete, self.why_not, self.verdict = False, why, CANNOT_SAY
        return self

    def as_dict(self):
        return {"plugin": self.plugin, "field": self.field, "declared": self.declared,
                "file": self.file, "complete": self.complete, "why_not": self.why_not,
                "set_by": self.set_by, "commits_since": self.commits_since,
                "code_changed": self.code_changed, "code_why": self.code_why,
                "dirty": self.dirty, "verdict": self.verdict}


def declared_field(doc, point_name):
    """(field path, what the repository says it means). ("", "") when the point names none."""
    try:
        conv = pts.point(doc, point_name).get(CV.KEY) or {}
    except Exception:                                                     # noqa: BLE001
        return "", ""
    if not isinstance(conv, dict):
        return "", ""
    return str(conv.get(KEY) or ""), " ".join(str(conv.get(MEANS_KEY) or "").split())


# ------------------------------------------------------------------ finding the field's LINE
def key_lines(source, dotted, value):
    """Every line of `source` where a dict literal declares `dotted` with this exact value.

    THE VALUE IS HALF THE ADDRESS AND THE FIRST DRAFT USED ONLY THE KEY. One of the nine plugins
    this was measured against declares the same key twice - once for itself and once, nested,
    for the upstream package it wraps - so a key-only search returned two lines and would have
    read the UPSTREAM's history as the plugin's. `convert._dotted` has already resolved which
    value the declaration means; matching on both makes the address unambiguous or reports that
    it is not.

    Returns [] when the source will not parse, when the value is not a literal in the file, or
    when nothing matches - three findings the caller distinguishes and none of them "unchanged".
    """
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return []
    parts = [p for p in str(dotted).split(".") if p]
    if not parts:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for k, v in zip(node.keys, node.values):
            if not (isinstance(k, ast.Constant) and k.value == parts[0]):
                continue
            target = v
            for seg in parts[1:]:
                if not isinstance(target, ast.Dict):
                    target = None
                    break
                target = next((vv for kk, vv in zip(target.keys, target.values)
                               if isinstance(kk, ast.Constant) and kk.value == seg), None)
                if target is None:
                    break
            if target is None:
                continue
            if isinstance(target, ast.Constant) and target.value == value:
                out.append(getattr(target, "lineno", None) or k.lineno)
    return sorted(set(out))


# ------------------------------------------------------------------ what counts as a change
def _significant(source):
    """A fingerprint of the source with comments, docstrings and formatting removed. None if not.

    NOT EVERY EDIT DESERVES A BUMP, AND THE NARROWING IS DECLARED RATHER THAN ASSUMED. What is
    removed here is exactly what a run cannot carry: comments, module/class/function docstrings,
    blank lines and layout. Everything else survives, INCLUDING every string literal that is not
    a docstring - which matters more than it sounds, because the plugin this was measured on
    embeds a whole R script in ordinary string constants and its thirty-five legends live there.
    A fingerprint that normalised strings would have called that commit cosmetic.

    IT IS AN AST DUMP AND NOT A TEXT DIFF because a text diff calls a reflow of one argument list
    a change to the code, and this check's whole value is that it does not cry wolf.

    THE ARGUABLE HALF IS THE DOCSTRING, and it is written down rather than hidden: a repository
    that puts a plugin's module docstring on the page it publishes would want it counted. When
    that day comes it becomes a key in the declaration; until then the choice is stated here and
    the report says what it ignored, so a reader can disagree with a specific sentence.

    None when the artefact is not Python or will not parse - the caller then asks its question
    rather than asserting an answer. THAT IS ONE OF THE TWO WAYS `code_changed` ENDS UP NONE and
    this docstring used to read as though it were the only one: the other is that one of the two
    texts never arrived, which is the caller's finding and now a `cannot say` rather than a
    question nobody can answer.
    """
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return None
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if (body and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)):
            node.body = body[1:] or [ast.Pass()]
    return ast.dump(tree)


# ------------------------------------------------------------------ git, asked without trusting
def _git(cwd, *args):
    """(ok, stdout, note). Never raises, never pages, never prompts, never writes."""
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0", GIT_PAGER="cat")
    try:
        p = subprocess.run(("git", *args), cwd=str(cwd), env=env,
                           capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as e:                    # noqa: BLE001
        return False, "", f"{type(e).__name__}: {e}"
    return p.returncode == 0, p.stdout.strip(), p.stderr.strip()


_SEP = "\x1f"
_FMT = f"%H{_SEP}%h{_SEP}%ad{_SEP}%s"


def _plainly(note):
    """git's stderr as one line a person can read, without the words git says to a shell.

    A REPORT IS PROSE AND `fatal:` IS NOT. This module quotes git when it has to - a note is
    often the only thing that distinguishes two identical-looking failures - but a line that
    opens with git's own alarm word reads as a crash in the check rather than an answer from it,
    and one of these once reached a user-facing paragraph complaining that a path "exists on
    disk" when the path plainly did.
    """
    line = " ".join(str(note or "").split())
    for word in ("fatal: ", "error: ", "warning: "):
        line = line.replace(word, "")
    return line


def _named_at(top, rel, sha):
    """What this artefact was CALLED at `sha`, following renames back from the name it has now.

    THE COMMANDS BELOW MUST ALL BE ABOUT THE SAME FILE AND IT TOOK A RENAME TO NOTICE THEY WERE
    NOT. `git log -L n,n:path` follows renames; `git log -- path` and `git show sha:path` do not.
    So a plugin renamed after the change that made it stale produced three answers about three
    different files: the trace named the right commit, the list of what happened since dropped
    the real change because it had touched the file under its old name, and reading the old
    revision failed with git's own words in the middle of a sentence a person was meant to read.
    It rendered as "nothing to decide", which is an exit status a job reads as fine.

    `--name-only` prints, for each commit, the path the file had AS OF that commit, which is
    exactly what `git show sha:path` needs. It returns "" and never `rel` when the follow chain
    does not reach `sha`, because "it was always called this" and "I lost it" would otherwise be
    the same answer, and only one of them may go on to be compared against anything.
    """
    ok, out, _n = _git(top, "-c", "core.quotepath=false", "log", "--follow",
                       "--format=%x00%H", "--name-only", "--", rel)
    if not ok:
        return ""
    at = ""
    for line in out.splitlines():
        if line.startswith("\x00"):
            at = line[1:].strip()
        elif line.strip() and at == sha:
            return line.strip()
    return ""


def _rows(out):
    rows = []
    for line in out.splitlines():
        bits = line.split(_SEP)
        if len(bits) == 4:
            rows.append({"sha": bits[0], "short": bits[1], "date": bits[2], "subject": bits[3]})
    return rows


# ------------------------------------------------------------------ the check
def check(spec, doc, point_name, name):
    """Has this plugin's code changed since its declared version last changed? A `Freshness`."""
    field, _means = declared_field(doc, point_name)
    f = Freshness(name, field)
    if not field:
        return f.cannot(
            f"point {point_name!r} declares no `{KEY}:` inside its `{CV.KEY}:` block, so nothing "
            f"here knows which of this format's fields is a claim about the code. Name it there "
            f"- the harness must not guess a field name, and a guess that was wrong would read "
            f"as a clean answer.")
    f.declared = CV._dotted(spec, field)
    if f.declared is None:
        return f.cannot(f"this declaration has no `{field}` at all, so there is no value whose "
                        f"history could be read. That is the declaration tier's finding, not "
                        f"this one's.")

    path = CV.artefact(doc, point_name, name)
    if path is None:
        return f.cannot(f"no artefact for {name!r} under the directory this point declares, so "
                        f"no file's history could be read.")
    root = Path(str(doc.get("_root") or "."))
    f.file = str(path)

    ok, top, note = _git(root, "rev-parse", "--show-toplevel")
    if not ok:
        return f.cannot(f"{root} is not inside a git repository, so when this version was set "
                        f"is not recorded anywhere this can read: "
                        f"{_plainly(note) or 'no toplevel'}")
    top = Path(top)
    ok, _head, note = _git(top, "rev-parse", "--verify", "HEAD")
    if not ok:
        return f.cannot(f"{top} is a git repository with no commits yet, so nothing has a "
                        f"history to compare against.")
    ok, shallow, _n = _git(top, "rev-parse", "--is-shallow-repository")
    if ok and shallow.strip() == "true":
        return f.cannot(f"{top} is a SHALLOW clone. The oldest commit it holds is a graft, so "
                        f"'the last commit that changed this line' could be the truncation "
                        f"rather than an edit - and the wrong end of a shallow history reads as "
                        f"a bump that never happened. Fetch the full history to ask this.")
    try:
        rel = str(path.resolve().relative_to(top.resolve()))
    except ValueError:
        return f.cannot(f"{path} is not inside {top}, so git holds no history for it.")
    ok, _o, _n = _git(top, "ls-files", "--error-unmatch", "--", rel)
    if not ok:
        return f.cannot(f"git does not track {rel}. A version nobody has ever committed cannot "
                        f"be compared against a state of the code nobody has ever committed.")

    # THE LINE IS FOUND IN HEAD'S BLOB AND NOT IN THE WORKING TREE. `git log -L n,n:file` counts
    # lines in the revision it starts from, so a working tree that has drifted from HEAD by a few
    # lines would point the trace at the wrong line and produce a confident wrong commit.
    ok, at_head, note = _git(top, "show", f"HEAD:{rel}")
    if not ok:
        return f.cannot(f"could not read {rel} at HEAD: {_plainly(note) or 'no output'}")
    lines = key_lines(at_head, field, f.declared)
    if not lines:
        return f.cannot(
            f"`{field}` = {f.declared!r} is not a literal at that path in the committed {rel}. "
            f"Either the value is computed rather than written, or it has been changed in the "
            f"working tree and not committed - in both cases git cannot say when it was set. "
            f"Commit the change, or declare a field whose value is written in the file.")
    if len(lines) > 1:
        return f.cannot(
            f"`{field}` = {f.declared!r} is written at {len(lines)} places in {rel} "
            f"(lines {', '.join(str(n) for n in lines)}), so no single line's history is this "
            f"field's history. Nothing here will pick one.")
    line = lines[0]

    ok, out, note = _git(top, "log", "-n", "2", f"-L{line},{line}:{rel}", "--no-patch",
                         f"--format={_FMT}", "--date=short")
    hist = _rows(out) if ok else []
    if not hist:
        return f.cannot(f"git recorded no change to {rel}:{line} - the line this field is "
                        f"written on - so there is no commit to measure from: "
                        f"{_plainly(note) or 'an empty history for that line'}")
    f.set_by = hist[0]

    # AND THIS ONE DOES NOT FOLLOW, WHICH IS NOT AN OVERSIGHT AND WAS MEASURED. `--follow` finds
    # the source of a path by rename AND COPY detection, so on a file whose first version is
    # byte-identical to a file that still exists beside it - two plugins scaffolded from the same
    # template, which is how every one of them starts - it walks off into the twin's history and
    # answers with the twin's birth. That silently loses the answer below, and the answer below is
    # the one that keeps a plugin still being written from being called stale forever. A rename
    # can at worst make this name the rename commit as the birth, which is one more `cannot say`;
    # a wrong twin would be one fewer.
    ok, added, _n = _git(top, "log", "--diff-filter=A", "--format=%H", "--", rel)
    born = added.splitlines()[0] if (ok and added) else ""
    if born and born == f.set_by["sha"]:
        return f.cannot(
            f"`{field}` has never been set as a distinct act: the only commit that has ever "
            f"touched its line is {f.set_by['short']}, the commit that ADDED {rel}. A file's "
            f"birth necessarily writes the field and the code together, so counting from it "
            f"would report every plugin still being written as stale, forever, from its second "
            f"commit onwards. Bump it once and this check has something to measure from.")

    # `--follow`, BECAUSE THE TRACE ABOVE FOLLOWS AND THIS ONCE DID NOT. A plugin renamed after
    # the commit that made it stale had that commit silently dropped from this list - the report
    # then said "read the commits above" about a change that was not above it, counted the row as
    # nothing to decide, and exited 0.
    ok, out, _n = _git(top, "log", "--follow", f"{f.set_by['sha']}..HEAD",
                       f"--format=%h{_SEP}%s", "--", rel)
    f.commits_since = [{"short": b[0], "subject": b[1]}
                       for b in (l.split(_SEP, 1) for l in out.splitlines()) if len(b) == 2]
    ok, dirt, _n = _git(top, "status", "--porcelain", "--", rel)
    f.dirty = bool(ok and dirt.strip())

    # WHAT CHANGED, NARROWED. The endpoints are deliberately the commit that set the field and
    # the WORKING TREE, not HEAD: the question a run is about to answer is whether the code
    # ABOUT TO RUN matches the version about to be written into the reuse key.
    then_rel = _named_at(top, rel, f.set_by["sha"])
    ok, then_src, note = _git(top, "show", f"{f.set_by['sha']}:{then_rel or rel}")
    if not ok:
        # THE EIGHTH CANNOT SAY. Not being able to read the file as it stood is not a small
        # question about a comment - it is one of the two texts being compared never arriving -
        # and what used to come out here was a QUESTION, printed as "to decide" and exiting 0,
        # with git's own alarm word in the sentence. A rename nothing could follow reaches it.
        was = (f" - this history calls it {then_rel} at that commit" if then_rel and
               then_rel != rel else "")
        return f.cannot(
            f"{rel} cannot be read as it stood at {f.set_by['short']}, the commit that set "
            f"`{field}`{was}, so there is no earlier text to compare the working tree against. "
            f"A file renamed in a way this could not follow reaches here. git's own answer: "
            f"{_plainly(note) or 'no output'}")
    now_src = ""
    try:
        now_src = path.read_text(encoding="utf-8")
    except OSError as e:                                                  # noqa: BLE001
        f.code_why = (f"the working tree's {rel} could not be read at all "
                      f"({type(e).__name__}: {e}), so there is nothing to compare")
    if not f.code_why:
        a, b = _significant(then_src), _significant(now_src)
        if a is None or b is None:
            f.code_why = (f"{rel} is not something this can parse as Python, so a comment-only "
                          f"edit cannot be told from a real one here")
        else:
            f.code_changed = (a != b)

    f.complete = True
    if not f.commits_since and not f.dirty:
        f.verdict = CURRENT
    elif f.code_changed is True:
        f.verdict = STALE
    else:
        f.verdict = QUESTION
    return f


def check_all(doc, point_name, specs):
    """[Freshness] for [(name, spec)], in the order given."""
    return [check(spec, doc, point_name, name) for name, spec in specs]


# ------------------------------------------------------------------ what a person reads
def advice(f, means):
    """The lines saying what to do, or [] when there is nothing to do."""
    if f.verdict == STALE:
        L = [f"       WHAT TO DO: raise `{f.field}` in {f.file}, in the same commit as the "
             f"change that made it stale."]
        if means:
            L.append(f"       Why it matters here, as this repository declares it: {means}")
        L.append("       Nothing here will do it. This suite checks registration and does not "
                 "write it, for the same reason: the")
        L.append("       number is the author's statement about what changed, and a maker that "
                 "picks one has made that statement for them.")
        return L
    if f.verdict == QUESTION:
        L = []
        if f.code_changed is False:
            L.append(f"       WHAT TO DO: probably nothing. Nothing outside comments, "
                     f"docstrings and layout differs between {f.set_by['short']} and the working")
            L.append(f"       tree, so no run would produce anything different. Read the "
                     f"commits above and raise `{f.field}` if one of them changed")
            L.append(f"       what this plugin PRODUCES in a way an AST cannot see - a data "
                     f"file beside it, a pinned dependency, an environment.")
        else:
            L.append(f"       WHAT TO DO: decide, because this could not. {f.code_why}.")
            L.append(f"       Read the commits above. If any of them changed what this plugin "
                     f"produces, raise `{f.field}` in {f.file}.")
        return L
    return []


def format_report(rows, point_name, means="", root="."):
    """One block per plugin. The idiom is `format_status`'s: a mark, then what stands behind it."""
    order = {STALE: 0, QUESTION: 1, CANNOT_SAY: 2, CURRENT: 3}
    mark = {STALE: "STALE", QUESTION: "ASK ", CANNOT_SAY: "?   ", CURRENT: "ok  "}
    rows = sorted(rows, key=lambda f: (order[f.verdict], f.plugin))
    n = {v: sum(1 for f in rows if f.verdict == v) for v in order}
    L = [f"is each declared version still true of the code?  ({point_name} in {root})",
         f"  {n[STALE]} stale, {n[QUESTION]} to decide, {n[CANNOT_SAY]} cannot say, "
         f"{n[CURRENT]} current, of {len(rows)}",
         ""]
    for f in rows:
        head = f"  {mark[f.verdict]} {f.plugin:12s}"
        if f.verdict == CANNOT_SAY:
            L.append(f"{head} CANNOT SAY, and that is an answer and not a pass:")
            L.append(f"       {f.why_not}")
            L.append("")
            continue
        L.append(f"{head} `{f.field}` = {f.declared!r}, set by {f.set_by['short']} on "
                 f"{f.set_by['date']}")
        L.append(f"       {f.set_by['subject'][:96]}")
        if f.verdict == CURRENT:
            L.append(f"       and no commit has touched {Path(f.file).name} since. The declared "
                     f"value still describes this code.")
            L.append("")
            continue
        if f.commits_since:
            L.append(f"       {len(f.commits_since)} commit(s) have touched "
                     f"{Path(f.file).name} since, and the version has not moved:")
            for c in f.commits_since[:6]:
                L.append(f"         {c['short']}  {c['subject'][:88]}")
            if len(f.commits_since) > 6:
                L.append(f"         ... and {len(f.commits_since) - 6} more")
        if f.dirty:
            L.append("       and the file has UNCOMMITTED changes, which no commit count sees.")
        if f.code_changed is True:
            L.append("       Ignoring comments, docstrings and layout, the code IS different "
                     "from the code that version named.")
        elif f.code_changed is False:
            L.append("       Ignoring comments, docstrings and layout, the code is IDENTICAL to "
                     "the code that version named.")
        L += advice(f, means)
        L.append("")
    return "\n".join(L)
