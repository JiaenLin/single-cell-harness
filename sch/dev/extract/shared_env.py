"""What a SHARED environment LENDS a plugin, and what the plugin loses the moment it is alone.

THE DEFECT, MEASURED. A plugin in this family had spent its whole life inside a seven-member
environment. Unplug the other eight and the resolver correctly gives it an environment of its own
- the group name hashes the union of its members' requirements, so a group of one is a different
directory - and two of its drawing paths died in it:

    native plot geneExpression FAILED: there is no package called 'Seurat'
    net embedding FAILED: Cannot find UMAP ... (umap-learn)

54 panels of 711, three draw sites across 18 units. Its SELFTEST STILL PASSED, because a selftest
proves the plugin's imports resolve and neither package is imported at module scope: they are
reached only when a particular panel is drawn. The plugin had even met the error before and
misread it as the wrong interpreter rather than a missing declaration - and inside a shared
environment those two look identical, because both of them look like "it works here".

THE QUESTION, AND WHY IT IS WORTH ASKING WITHOUT A RUN. Resolve a plugin ALONE and you have the
set its own declaration asks for. Resolve it WITH ITS FAMILY and you have the set its environment
is built from. The difference is what the group LENDS it: everything it can use today and will
lose the day it is the only member. No run, no environment built, no network - two calls into the
repository's own resolver and a subtraction.

A LENT PACKAGE IS NOT A DEFECT, AND SAYING SO IS THE WHOLE DESIGN. A seven-member environment
lends its members over a hundred names each and almost none of them is ever touched. A check that
printed "110 undeclared dependencies" would be a false-alarm generator, and this project has paid
for those. So the loan is REPORTED AS EXPOSURE - a number, with what it does and does not mean -
and the rows that are worth a person's attention are the ones NARROWED by looking for the lent
name in the plugin's own source:

    LOADED      the plugin's own code imports or attaches it. Strongest: this is a dependency the
                declaration does not carry.
    mentioned   the name appears in the source - a comment, a string, an argument. WEAK, and
                labelled weak. Both of the packages that died tonight are this: one is a string
                argument inside embedded R, the other a sentence in an R comment.
    (neither)   available and never named. Counted, never itemised.

TWO PLACES A NAME CAN BE WRITTEN, AND A NAME KNOWS WHICH. A plugin here is Python with scripts of
another language embedded in it, and the two ecosystems spell a package differently: the same
library is a lowercase channel entry to the builder and a CamelCase symbol to the script that
attaches it. So the repository declares, per field of its own requirement, how an entry is spelled
and WHICH OF THE TWO TEXTS that spelling is written in. Searching an embedded-language name in the
host text is what turned `r-matrix`, `r-shape`, `r-base` and `r-cluster` into rows on seven
plugins whose Python prose says "matrix", "shape", "base" and "cluster" in English - measured, and
the reason the scan is scoped rather than global.

THE ANSWER IS A LOWER BOUND AND THE REPORT SAYS SO IN EVERY BLOCK. The loan is the difference of
DIRECT declarations. A built environment also contains every transitive dependency of them, and a
package present only that way is invisible here: nothing in the declaration names it, so no
subtraction can find it. That is not a hole to paper over - it is the second half of tonight's
finding, and the report prints the size of it beside every loan.

A ONE-MEMBER GROUP LENDS NOTHING, AND THAT IS AN ANSWER. It is printed as one - "this environment
holds exactly what this plugin asks for" - and never as an empty section, for the same reason an
inventory that could not look is not an inventory of zero.

REPORT, NEVER WRITE. Ratcheted, like every other registration check in this suite.

NO REPOSITORY'S VOCABULARY IS IN THIS FILE. The package that resolves environments, the callable
that groups plugins, the attribute that names a group's members and the fields a group's contents
live in are all read from the repository's own DEVPOINTS.yaml, which is where `sch dev` reads
everything else about a repository. What is here is the SHAPE of the question.
"""
from __future__ import annotations

import ast
import json
import re
import subprocess
from pathlib import Path

from . import Inventory
from . import draw_sites as DS

EXTRACT = {
    "reads": "plugin-environment",
    "summary": "what a shared environment lends a plugin that its own declaration never asked for",
}

#: Where a point declares how ITS repository turns requirements into environments. THE HARNESS'S
#: KEY, holding the repository's names - the same arrangement as `version_field` next door.
KEY = "environment"
#: The keys inside it. Every value is a name belonging to the repository, never to this suite.
CATALOGUE, PLUGIN_NAMED = "catalogue", "plugin_named"
GROUPS, ENV_NAMED, SHARED_BY = "groups", "environment_named", "shared_by"
HOLDS = "holds"
#: And the keys of one `holds` entry: the attribute the contents live on, the prose that labels
#: it in a report, and how one entry there is spelled where a plugin would write it.
FIELD, WHAT, SPELLED, AS, WRITTEN_IN = "field", "what", "spelled", "as", "written_in"

#: THE TWO TEXTS A PLUGIN IS MADE OF, and this suite's own words for them - not a repository's.
#: `HOST` is the plugin file itself; `EMBEDDED` is a script of another language sitting inside it,
#: found the way `draw_sites` finds one. A spelling declares which text it belongs to, because a
#: name searched in the wrong one is either invisible or an English word.
HOST, EMBEDDED = "host", "embedded"

#: How an embedded script of another language ATTACHES a package. A PATTERN, with the same status
#: as `draw_sites.R_DEVICES`: a script attaching a package some other way is invisible to it, and
#: the row then reads `mentioned` rather than LOADED, which understates and never overstates.
EMBEDDED_LOADERS = ("library", "require", "requireNamespace", "loadNamespace", "attachNamespace")

#: How the three verdicts on one name are spelled in a record. LENT is a name the plugin's
#: environment holds and the plugin never asked for. STRAY is a name the plugin's source reaches
#: for that NO environment of its own holds under any spelling - and that some OTHER environment
#: of this repository declares, which is what makes it a name and not a guess.
LENT, STRAY = "lent", "stray"


# -----------------------------------------------------------------------------------------------
# REACHING THE REPOSITORY'S OWN RESOLVER
#
# IN ITS OWN INTERPRETER, NEVER THIS ONE, for the reason `python_package` states: importing a
# foreign repository into the process doing the measuring either fails or succeeds against
# whatever happens to be on this path. It also keeps a repository's import side effects out of the
# maker, which matters more here than there - this one is asked about nine plugins in a row.
# -----------------------------------------------------------------------------------------------

_PROBE = r'''
import importlib, json, sys
root = sys.argv[1]
plan = json.loads(sys.argv[2])
sys.path.insert(0, root)
out = {"complete": False, "why_not": "", "environments": [], "alone": {}, "loose": []}

def reach(path):
    mod, _, attr = path.rpartition(".")
    obj = importlib.import_module(mod)
    for part in attr.split("."):
        obj = getattr(obj, part)
    return obj

def bail(msg):
    out["why_not"] = msg
    print(json.dumps(out))
    raise SystemExit(0)

try:
    catalogue = reach(plan["catalogue"])
except Exception as e:
    bail("the catalogue this repository declares, %s, could not be reached from %s "
         "(%s: %s)" % (plan["catalogue"], root, type(e).__name__, e))
try:
    grouper = reach(plan["groups"])
except Exception as e:
    bail("the resolver this repository declares, %s, could not be reached from %s "
         "(%s: %s)" % (plan["groups"], root, type(e).__name__, e))
try:
    found = catalogue()
except Exception as e:
    bail("%s raised %s: %s" % (plan["catalogue"], type(e).__name__, e))

items = list(found.values()) if hasattr(found, "values") else list(found)
by = {}
for it in items:
    nm = getattr(it, plan["plugin_named"], None)
    if nm:
        by[str(nm)] = it
if not by:
    bail("%s returned %d item(s), none of which carries a `%s`, so this could not tell which "
         "plugin is which" % (plan["catalogue"], len(items), plan["plugin_named"]))

def contents(g):
    got = {}
    for field in plan["fields"]:
        v = getattr(g, field, None)
        got[field] = [str(x) for x in (v or [])]
    return got

try:
    groups = list(grouper(items))
except Exception as e:
    bail("%s raised %s: %s" % (plan["groups"], type(e).__name__, e))

placed = set()
for g in groups:
    mem = [str(x) for x in (getattr(g, plan["shared_by"], None) or [])]
    placed.update(mem)
    out["environments"].append({"id": str(getattr(g, plan["environment_named"], "") or ""),
                                "sharing": mem, "contents": contents(g)})
out["loose"] = sorted(n for n in by if n not in placed)

for nm in sorted(by):
    try:
        one = list(grouper([by[nm]]))
    except Exception as e:
        out["alone"][nm] = {"why_not": "%s: %s" % (type(e).__name__, e)}
        continue
    out["alone"][nm] = {"contents": contents(one[0]) if one else {}, "any": bool(one)}
out["complete"] = True
print(json.dumps(out))
'''


def declared(doc, point_name):
    """The block in which a point says how its repository resolves environments, or {}.

    Never raises on a tree that does not have one: a repository that declares no resolver is a
    `complete=False` below, with the key to add named in the sentence.
    """
    from .. import convert as CV
    from .. import points as pts
    try:
        conv = pts.point(doc, point_name).get(CV.KEY) or {}
    except Exception:                                                     # noqa: BLE001
        return {}
    block = conv.get(KEY) if isinstance(conv, dict) else None
    return block if isinstance(block, dict) else {}


def _plan(block):
    """(what the probe needs, what is missing). Every value is the repository's own name."""
    holds = [h for h in (block.get(HOLDS) or []) if isinstance(h, dict) and h.get(FIELD)]
    plan = {CATALOGUE: str(block.get(CATALOGUE) or ""),
            PLUGIN_NAMED: str(block.get(PLUGIN_NAMED) or ""),
            GROUPS: str(block.get(GROUPS) or ""),
            ENV_NAMED: str(block.get(ENV_NAMED) or ""),
            SHARED_BY: str(block.get(SHARED_BY) or ""),
            "fields": [str(h[FIELD]) for h in holds]}
    missing = [k for k in (CATALOGUE, PLUGIN_NAMED, GROUPS, ENV_NAMED, SHARED_BY) if not plan[k]]
    if not holds:
        missing.append(HOLDS)
    return plan, missing, holds


class Landscape:
    """Every environment this repository would build, and what each plugin asks for alone.

    NEVER A BARE DICT, for the reason `Inventory` is never a bare list: "this repository resolves
    to three environments" and "I could not reach its resolver" are different findings and only
    the first is about the repository.
    """

    def __init__(self, environments=(), alone=None, loose=(), complete=True, why_not="", how=""):
        self.environments = list(environments)
        self.alone = dict(alone or {})
        #: Plugins the resolver placed in no environment at all - by its own account, they need
        #: none. A positive answer, and the report prints it as one.
        self.loose = list(loose)
        self.complete = bool(complete)
        self.why_not = why_not
        self.how = how

    def __bool__(self):
        return self.complete

    def of(self, plugin):
        """The environment this plugin lands in, or None."""
        for e in self.environments:
            if plugin in e["sharing"]:
                return e
        return None

    def plugins(self):
        got = sorted({m for e in self.environments for m in e["sharing"]} | set(self.loose))
        return got


def resolve(root, tool, block, python="python3", timeout=180):
    """Ask the repository's own resolver twice: for the whole family, and for each plugin alone.

    COULD NOT ASK IS AN ANSWER. A repository whose resolver will not import, a declaration that
    names no resolver, a catalogue that raises - each returns `complete=False` and the sentence
    that says which. An empty landscape would read as "this repository shares nothing", which is
    the finding a reader would act on and the one thing this cannot establish.
    """
    plan, missing, _holds = _plan(block)
    if not block:
        return Landscape(complete=False,
                         why_not=f"this point declares no `{KEY}:` block, so nothing says how "
                                 f"this repository turns a plugin's requirement into an "
                                 f"environment. Until it does, whether a plugin is borrowing "
                                 f"from its neighbours cannot be asked, let alone answered.")
    if missing:
        return Landscape(complete=False,
                         why_not=f"the `{KEY}:` block names no {', '.join(missing)}, and the "
                                 f"resolver cannot be reached without it")
    if not tool:
        return Landscape(complete=False,
                         why_not="this repository's DEVPOINTS.yaml names no `tool:`, so there is "
                                 "no package to reach its resolver through")
    plan = dict(plan)
    for k in (CATALOGUE, GROUPS):
        plan[k] = f"{tool}.{plan[k]}"
    try:
        p = subprocess.run([python, "-c", _PROBE, str(root), json.dumps(plan)],
                           capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        return Landscape(complete=False,
                         why_not=f"could not run {python}: {type(e).__name__}: {e}")
    text = (p.stdout or "").strip().splitlines()
    if not text:
        return Landscape(complete=False,
                         why_not=f"{python} produced no answer: {(p.stderr or '')[-240:]}")
    try:
        d = json.loads(text[-1])
    except ValueError:
        return Landscape(complete=False,
                         why_not=f"unreadable answer from {python}: {text[-1][:200]}")
    how = (f"resolved twice by this repository's own {plan[GROUPS]}: once over every plugin "
           f"{plan[CATALOGUE]} lists, and once per plugin on its own")
    return Landscape(d["environments"], d["alone"], d["loose"], d["complete"], d["why_not"], how)


# -----------------------------------------------------------------------------------------------
# SPELLING: TURNING A DECLARED ENTRY INTO THE NAME A PLUGIN WOULD WRITE
# -----------------------------------------------------------------------------------------------

def spellings(entry, hold):
    """{(name, which text it is written in)} for one declared entry, per the repository's rules.

    A DECLARED ENTRY IS NOT A NAME. It carries a version, a channel prefix, an owner and a commit,
    and none of that is what a plugin writes when it reaches for the thing. The repository knows
    the difference - it is the grammar of its own requirement - so it declares the patterns and
    this applies them. An entry no pattern matches yields nothing and is counted in the loan all
    the same: it is available, it is simply not searchable.
    """
    out = set()
    for rule in (hold.get(SPELLED) or []):
        if not isinstance(rule, dict):
            continue
        pattern, where = str(rule.get(AS) or ""), str(rule.get(WRITTEN_IN) or HOST)
        if not pattern:
            continue
        try:
            m = re.match(pattern, str(entry))
        except re.error:
            continue
        if m:
            got = (m.group(1) if m.groups() else m.group(0)).strip()
            if got:
                out.add((got, where))
    return out


def provided(contents, holds):
    """{(name, text): (field, entry)} - every name an environment's contents make available."""
    got = {}
    for hold in holds:
        field = str(hold[FIELD])
        for entry in (contents.get(field) or []):
            for sp in spellings(entry, hold):
                got.setdefault(sp, (field, entry))
    return got


# -----------------------------------------------------------------------------------------------
# NARROWING: IS THE LENT NAME ANYWHERE IN THIS PLUGIN'S OWN SOURCE?
# -----------------------------------------------------------------------------------------------

class Source:
    """One plugin's two texts, and what each of them loads.

    THE EMBEDDED SCRIPTS ARE FOUND BY `draw_sites`, which already reads them out of a plugin and
    keeps the arithmetic that turns a line of the script into a line of the file. Reusing it means
    a plugin needs no declaration of where its other language lives, and it inherits that rule's
    stated limit: a literal holding no function definition is not recognised as a script.
    """

    def __init__(self, plugin, path, text):
        self.plugin = plugin
        self.path = path
        self.text = text
        self.lines = text.splitlines()
        self.blocks = DS.embedded_r(text)
        self.host_loads = _imported(text)
        self.embedded_loads = _attached([b for b, _base in self.blocks])
        self.readable = True

    def find(self, name, where):
        """(line, the line as written, was it LOADED, how many lines name it) or None.

        CASE-SENSITIVE IN THE HOST TEXT AND NOT IN THE EMBEDDED ONE, deliberately. A host package
        is written the way the requirement spells it. An embedded-language package is written the
        way its own ecosystem spells it, which is routinely a differently-cased version of the
        channel entry that installs it - so an exact match there would silently miss the case this
        exists to find, and a loose match here would turn every requirement into an English word.

        THE LINE SHOWN IS THE FIRST ONE THAT IS NOT A COMMENT, where there is one. Measured on the
        plugin this was built against: the first mention of the package whose absence killed five
        of its panels is a comment recounting the error, forty lines above the call that reaches
        for it. Both are evidence and only one of them is the code, and a row that showed the
        comment sent a reader to a paragraph about the problem instead of to the line with the
        problem in it. The count says how many lines name it at all, so a single incidental
        mention cannot be mistaken for a dependency.
        """
        if where == EMBEDDED:
            rx = re.compile(_TOKEN % re.escape(name), re.I)
            hit = any(x.lower() == name.lower() for x in self.embedded_loads)
            found = [(base + k, line) for body, base in self.blocks
                     for k, line in enumerate(body.splitlines(), 1) if rx.search(line)]
        else:
            rx = re.compile(_TOKEN % re.escape(name))
            hit = name in self.host_loads
            found = [(i, line) for i, line in enumerate(self.lines, 1) if rx.search(line)]
        if not found:
            return None
        code = [f for f in found if not f[1].lstrip().startswith("#")]
        at, line = (code or found)[0]
        return at, line.strip()[:110], hit, len(found)


#: A WHOLE NAME AND NOT A PIECE OF ONE. The hyphen is in both lookarounds because these names
#: carry hyphens: without it a two-word package matches inside a longer hyphenated word, and the
#: row sends a reader to a line that does not mention the package at all.
_TOKEN = r"(?<![\w.\-])%s(?![\w\-])"


def _imported(text):
    """The top-level names this plugin's own Python imports, function-local imports included.

    PARSED, NOT GREPPED. The distinction this column carries - a dependency the code IMPORTS
    versus a name that appears in a comment - is worth nothing if a comment saying `import numpy`
    counts as an import.
    """
    got = set()
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return got
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for al in node.names:
                got.add(al.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            got.add(node.module.split(".")[0])
    return got


def _attached(bodies):
    """The names an embedded script attaches, by the loaders above or by a namespace qualifier."""
    load = "|".join(re.escape(x) for x in EMBEDDED_LOADERS)
    rx = re.compile(r"(?:" + load + r")\s*\(\s*[\"']?([\w.]+)"
                    r"|(?<![\w.])([\w.]+):::?(?![:=])")
    got = set()
    for body in bodies:
        for m in rx.finditer(body):
            got.add(m.group(1) or m.group(2))
    return got


def read_source(doc, point_name, plugin):
    """The plugin's own text, or None with the reason. Reached the way every other stage is."""
    from .. import convert as CV
    path = CV.artefact(doc, point_name, plugin)
    if path is None:
        return None, (f"no artefact for {plugin!r} under the directory this point declares, so "
                      f"the loan below could not be narrowed by looking at its source")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        return None, f"{path}: {type(e).__name__}: {e}"
    root = Path(str(doc.get("_root") or "."))
    try:
        rel = path.relative_to(root)
    except ValueError:
        rel = path
    return Source(plugin, str(rel), text), ""


# -----------------------------------------------------------------------------------------------
# THE ANSWER FOR ONE PLUGIN
# -----------------------------------------------------------------------------------------------

class Loan:
    """What one plugin's environment lends it, and what it reaches for that nothing lends.

    `complete=False` IS A FIRST-CLASS ANSWER HERE and there are four ways to reach it: a
    repository whose resolver cannot be reached, a point that declares no resolver, a plugin the
    catalogue does not list, and a plugin whose source could not be read - the last of which
    leaves the loan itself intact and only the narrowing unavailable, and says so.
    """

    def __init__(self, plugin):
        self.plugin = plugin
        self.environment = ""
        self.members = []
        #: [{name, field, what, entry, written_in, verdict, at, line, loaded, by}]
        self.rows = []
        #: How many names the environment makes available that this plugin never asked for.
        self.lent = 0
        #: THE LOAN BROKEN DOWN BY FIELD, and it is not decoration. {field: (lent, held, what)}.
        #: A field that holds entries and lends NONE of them is the strongest thing this check
        #: can say and the easiest to miss in a total: this plugin's environment is IDENTICAL to
        #: its own declaration over that field, so no difference of declarations can ever predict
        #: it losing one of those - and if one does go missing, no declaration in this repository
        #: ever asked for it. That is exactly the half of tonight's finding that a subtraction
        #: cannot reach, and it is printed rather than left to be inferred from a zero.
        self.by_field = {}
        #: How many entries the environment declares in total. The loan is a difference of
        #: DIRECT declarations; each of these also installs its own dependencies, and this
        #: number is the size of what no subtraction here can see.
        self.entries = 0
        self.embedded = 0
        self.source = ""
        self.narrowed = False
        self.why_not_narrowed = ""
        self.complete = False
        self.why_not = ""
        self.how = ""

    def __bool__(self):
        return self.complete

    @property
    def alone(self):
        """True when this plugin is the only member of its environment."""
        return self.complete and len(self.members) == 1

    @property
    def needs_none(self):
        """True when the resolver placed this plugin in no environment at all."""
        return self.complete and not self.members

    def named(self, verdict=LENT):
        return [r for r in self.rows if r["verdict"] == verdict]

    def as_dict(self):
        return {"plugin": self.plugin, "environment": self.environment, "sharing": self.members,
                "rows": self.rows, "lent": self.lent, "entries": self.entries,
                "embedded": self.embedded, "source": self.source, "narrowed": self.narrowed,
                "why_not_narrowed": self.why_not_narrowed, "complete": self.complete,
                "why_not": self.why_not, "how": self.how}


def loan(landscape, holds, plugin, source=None, why_no_source=""):
    """What `plugin`'s environment lends it, narrowed by its own source where one was readable."""
    out = Loan(plugin)
    if not landscape.complete:
        out.why_not = landscape.why_not
        return out
    out.how = landscape.how
    if plugin in landscape.loose:
        out.complete = True
        out.narrowed = source is not None
        out.source = getattr(source, "path", "")
        return out
    env = landscape.of(plugin)
    if env is None:
        out.why_not = (f"the resolver this repository declares placed {plugin!r} in no "
                       f"environment and did not list it as needing none, so what its "
                       f"environment holds is not established here")
        return out
    out.complete = True
    out.environment = env["id"]
    out.members = list(env["sharing"])
    out.entries = sum(len(v) for v in env["contents"].values())
    mine = provided((landscape.alone.get(plugin) or {}).get("contents") or {}, holds)
    theirs = provided(env["contents"], holds)
    lent = {sp: v for sp, v in theirs.items() if sp not in mine}
    out.lent = len(lent)
    label = {str(h[FIELD]): str(h.get(WHAT) or h[FIELD]) for h in holds}
    for hold in holds:
        field = str(hold[FIELD])
        # NAMES ON BOTH SIDES OF THE COMPARISON. Counting lent NAMES against declared ENTRIES
        # printed "100 of 51", because one entry can be spelled more than one way and each
        # spelling is a name a plugin might write. A ratio whose halves are different units is
        # not a ratio, and this one was above 1.
        out.by_field[field] = (sum(1 for _sp, (f, _e) in lent.items() if f == field),
                               sum(1 for _sp, (f, _e) in theirs.items() if f == field),
                               label.get(field, field))

    if source is None:
        out.why_not_narrowed = why_no_source
        return out
    out.narrowed = True
    out.source = source.path
    out.embedded = len(source.blocks)

    for (name, where), (field, entry) in sorted(lent.items()):
        hit = source.find(name, where)
        if hit:
            out.rows.append(_row(name, where, field, label, entry, LENT, hit, env["sharing"]))

    # AND THE OTHER DIRECTION, WHICH IS WHERE TONIGHT'S SURVIVOR IS. A name this plugin's source
    # reaches for that NO spelling in its own environment provides, and that another environment
    # of this repository does declare. It is not a loan - nothing here is lending it - and if it
    # is present at all it is present as somebody's transitive dependency, which is a worse
    # footing than a loan: a loan at least has a declaration behind it that a person can read.
    #
    # THE CANDIDATE NAME COMES FROM A DECLARATION AND NEVER FROM THE SOURCE. That is the whole
    # guard against the false alarm: this reads the plugin's text only to answer yes or no about
    # a name the repository already wrote down, and never to invent one. A scan that harvested
    # package-shaped tokens out of embedded script text was measured at 116 candidates on one
    # plugin, of which the great majority were English words beginning a comment.
    have = {n for n, _w in theirs}
    others = {}
    for other in landscape.environments:
        if other is env:
            continue
        for sp, (field, entry) in provided(other["contents"], holds).items():
            if sp[0] in have:
                continue
            others.setdefault(sp, (field, entry, []))[2].extend(other["sharing"])
    for (name, where), (field, entry, by) in sorted(others.items()):
        hit = source.find(name, where)
        if hit:
            out.rows.append(_row(name, where, field, label, entry, STRAY, hit, sorted(set(by))))
    return out


def _row(name, where, field, label, entry, verdict, hit, by):
    line, text, loaded, times = hit
    return {"name": name, "field": field, "what": label.get(field, field), "entry": entry,
            "written_in": where, "verdict": verdict, "at": line, "line": text,
            "loaded": bool(loaded), "times": times, "by": list(by)}


def survey(doc, point_name, root=".", python="python3", only=""):
    """[Loan] for every plugin the repository's own catalogue lists, in name order."""
    block = declared(doc, point_name)
    land = resolve(root, doc.get("tool") or "", block, python=python)
    _plan_, _missing, holds = _plan(block)
    names = land.plugins() if land.complete else []
    if only:
        names = [n for n in names if n == only]
    if not names and land.complete:
        return []
    out = []
    for name in names or ([only] if only else []):
        src, why = read_source(doc, point_name, name)
        out.append(loan(land, holds, name, src, why))
    if not out:
        one = Loan(only or "")
        one.why_not = land.why_not
        out.append(one)
    return out


def inventory(loans):
    """The whole survey as one `Inventory`, so this answers the directory's contract too."""
    rows = [f"{L.plugin}:{r['name']}" for L in loans for r in L.rows]
    bad = [L for L in loans if not L.complete]
    if loans and len(bad) == len(loans):
        return Inventory("", [], "", complete=False, why_not=bad[0].why_not)
    return Inventory("", rows, loans[0].how if loans else "",
                     detail={f"{L.plugin}:{r['name']}": r for L in loans for r in L.rows})


# -----------------------------------------------------------------------------------------------
# WHAT A PERSON READS
# -----------------------------------------------------------------------------------------------

def format_report(loans, point_name, root="."):
    """One block per plugin. Every block says what its number does NOT mean."""
    L = [f"what does a shared environment lend each plugin?  ({point_name} in {root})",
         "  RESOLVED TWICE FROM DECLARATIONS ALONE - once with the family, once alone. Nothing "
         "was run and no environment was built.",
         "  A LENT NAME IS NOT A DEFECT. Most of a loan is never touched. The rows below are the "
         "part a person should read: a lent",
         "  name that this plugin's own source also writes down.",
         ""]
    sharing = [x for x in loans if x.complete and len(x.members) > 1]
    L.append(f"  {len(loans)} plugin(s); {len(sharing)} in a shared environment; "
             f"{sum(len(x.named(LENT)) for x in loans)} lent name(s) named in a plugin's own "
             f"source, "
             f"{sum(1 for x in loans for r in x.named(LENT) if r['loaded'])} of them LOADED by it")
    L.append("")
    for x in sorted(loans, key=lambda y: y.plugin):
        L += _block(x)
    return "\n".join(L)


def _block(x):
    head = f"  {x.plugin:12s}"
    if not x.complete:
        return [f"{head} CANNOT SAY, and that is an answer and not a pass:", f"       {x.why_not}",
                ""]
    if x.needs_none:
        return [f"{head} needs no environment at all, by this repository's own resolver - so "
                f"there is nothing to lend it", ""]
    if x.alone:
        return [f"{head} ALONE by declaration: it is the only member of {x.environment}.",
                f"       Its environment holds exactly what its own declaration asks for. "
                f"NOTHING IS LENT, so nothing can be lost",
                f"       by unplugging its neighbours. That is the clean answer to this "
                f"question, not a silence.",
                _bound(x), ""]
    out = [f"{head} {len(x.members)} members share {x.environment}: {', '.join(x.members)}",
           f"       LENDS {x.lent} name(s) this plugin's own declaration never asks for - it can "
           f"use every one of them today and would lose every one of them the day it is alone."]
    out += _per_field(x)
    if not x.narrowed:
        out += [f"       and the loan could NOT be narrowed: {x.why_not_narrowed}",
                "       so which of them this plugin actually reaches for is unknown, not zero.",
                _bound(x), ""]
        return out
    named = x.named(LENT)
    out.append(f"       {len(named)} of the {x.lent} "
               f"{'is' if len(named) == 1 else 'are'} named in {x.source}:")
    if not named:
        out.append("         none. Every lent name is unmentioned in this plugin's source - "
                   "exposure, and no evidence of use.")
    for r in named:
        out.append("         " + _line(r))
    out.append(f"       The other {x.lent - len(named)} are AVAILABLE AND NEVER NAMED here. That "
               f"is exposure, not debt, and is not itemised.")
    stray = x.named(STRAY)
    if stray:
        out.append("       AND NAMED HERE WITH NOTHING IN THIS ENVIRONMENT ASKING FOR IT - "
                   "declared only by a plugin that resolves elsewhere,")
        out.append("       so if it is present at all it is present as somebody's transitive "
                   "dependency and no declaration protects it:")
        for r in stray:
            out.append("         " + _line(r) + f"   declared by {', '.join(r['by'])}")
    out.append(_bound(x))
    out.append("")
    return out


def _per_field(x):
    """The loan by field, and the sentence a field that lends NOTHING has earned.

    A TOTAL HIDES THE ONE ANSWER THAT IS CERTAIN. "12 lent" says nothing about which KIND of
    package is at risk, and a reader who has just watched a package of one kind go missing will
    read the total as covering it. Where a field lends zero, the two resolutions agree over that
    whole field - so the subtraction has ruled the field out, and anything that still goes missing
    there was never in anybody's declaration to begin with.
    """
    if not x.by_field:
        return []
    said = ", ".join(f"{n} of {held} {what}" for _f, (n, held, what) in sorted(x.by_field.items())
                     if held)
    # `held` IS A COUNT OF NAMES AND NOT OF DECLARED ENTRIES - see `loan`. One entry can be
    # spelled two ways and each spelling is a name a plugin might write.
    out = [f"       by field: {said}"] if said else []
    for _f, (n, held, what) in sorted(x.by_field.items()):
        if held and not n:
            out.append(f"       0 of the {held} {what} are lent: this plugin declares the same "
                       f"{what} alone as it does here, so no")
            out.append(f"       difference of declarations can predict it losing one. If one goes "
                       f"missing anyway, nothing in this")
            out.append(f"       repository ever asked for it and the loan below cannot see it.")
    return out


def _line(r):
    mark = "LOADED   " if r["loaded"] else "mentioned"
    times = f"x{r['times']}" if r["times"] > 1 else "  "
    return (f"{mark} {times:>4s}  {r['name']:22s} {r['what']:18s} :{r['at']:<6d} "
            f"{r['line'][:66]}")


def _bound(x):
    return (f"       LOWER BOUND: this environment declares {x.entries} entries and each installs "
            f"its own dependencies; a package present only that way is invisible to a difference "
            f"of declarations.")
