"""Where a plugin produces a panel, and whether that site offers a legend.

THE OTHER TWO EXTRACTORS READ THE UPSTREAM. This one reads the PLUGIN, and it is here rather than
beside the scans in `convert.py` for one reason: it answers the same shape of question those two
do - "I looked, here is what I found, and here is how I decided" - and it has the same failure
mode, which is the one this directory exists to refuse. A plugin whose source could not be read
and a plugin that draws nothing are different findings, and only the second is about the plugin.

WHAT IT IS FOR, MEASURED. On a sealed run: 711 panels, 69 with a written legend, 642 without. The
figure accounting could say which upstream function drew a panel and could not say whether anybody
had described one, because the description is written at the DRAW SITE and nothing in this suite
had ever looked at a draw site. Every check in the previous round counted the gap on the far side
- in the run's output - which is a count nobody can act on: it names a directory of PNGs, not the
lines of code that must change.

    47 R draw sites in one plugin. 12 pass a legend. 35 do not, and those 35 are ~642 panels.

WHY THE WRAPPERS ARE DISCOVERED AND NOT DECLARED. Requiring every plugin to name its own draw
wrappers would mean editing every plugin in order to find out that they need editing, and the
eight that are not being converted are the evidence that this generalises. So a draw wrapper is
recognised BY WHAT IT DOES, in each of the two languages a plugin here is written in:

  EMBEDDED R.  A function DEFINED in the plugin's own embedded R that opens a graphics device,
               evaluates an expression, and closes the device. That is a draw wrapper whatever it
               is called - `npng`, `ndev`, or the host's `scp_draw` once plugins take the writer
               `scprofile/captions.py` now ships. It needs no declaration and works for any
               plugin that embeds R.

  PYTHON.      The host's own emit path, which is not in the plugin at all. Its NAME is not a
               literal here: the repository declares what its host package is called - that is
               `tool:` at the top of DEVPOINTS.yaml, the same key `sch dev map` already reads -
               and the emit path is then MEASURED out of that package by the rule below. A
               repository that cannot be measured this way declares its draw paths instead, and
               the answer says which of the two routes produced it.

THE LEGEND PARAMETER IS DISCOVERED FROM THE WRAPPER'S OWN SIGNATURE. Not assumed to be called
`legend`, because it is called `caption` on the Python side of this very repository and neither
name belongs in this suite. The rule is one sentence and it is mechanical:

    A DRAW WRAPPER'S LEGEND SLOT IS THE PARAMETER WHOSE DEFAULT IS THE EMPTY STRING.

which is to say: the parameter the wrapper has no answer for unless its caller supplies one. Every
other parameter of a draw wrapper either has a working default (a width, a device, a provenance
that is right most of the time) or has none at all (the panel, the expression). A slot that
defaults to nothing is a slot whose whole purpose is to be filled in from outside, and a call that
leaves it empty is a panel going out undescribed.

WHAT THE RULE DOES NOT COVER, SAID RATHER THAN PAPERED OVER. A wrapper whose legend is REQUIRED -
no default at all - has no empty default to find, and this extractor will not claim one. It
reports that wrapper as offering no discoverable legend slot and its sites as UNKNOWN, never as
silent: a required legend means every call already carries one, and reporting those as debt would
manufacture 47 gaps out of a wrapper that has no gap at all. Unknown is a third answer here for
the same reason `complete=False` is one in the extractors beside this file.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

from . import Inventory

EXTRACT = {
    "reads": "plugin-source",
    "summary": "draw sites in a plugin, and whether each one offers a legend",
}

#: Graphics devices an R draw wrapper opens. A PATTERN, like `r_namespace.DEFAULT_PATTERN`, and
#: reported as one: a plugin drawing through a device this list does not name is invisible to it.
#: Short on purpose - these are the devices R itself ships plus the two replacement backends any
#: of these plugins could plausibly reach for.
R_DEVICES = ("png", "jpeg", "tiff", "bmp", "svg", "pdf", "cairo_pdf", "cairo_ps", "postscript",
             "agg_png", "agg_jpeg", "agg_tiff", "CairoPNG", "CairoPDF", "CairoSVG")

#: What closes one. A function that opens a device and never closes it is not a draw site; it is
#: a script's preamble, and treating it as one would report the whole file as a panel.
R_CLOSERS = ("dev.off", "dev_off")

#: How an R wrapper evaluates the expression it was handed. `print` for a plotting function that
#: RETURNS an object, `force`/`eval` for one that draws as a side effect - and this family has
#: already paid for the difference: one script was written with only the printing wrapper, called
#: the forcing one, and died at "could not find function" after one framing of two.
R_EVAL = ("print", "force", "eval", "plot", "draw", "grid.draw", "replayPlot")

#: How a PYTHON draw path writes the panel. Same status as `R_DEVICES`: a pattern, not a
#: definition, and named here because "writes a figure to disk" has no single spelling.
PY_SAVES = ("savefig", "imsave", "write_image", "save_figure", "saveas")


# -----------------------------------------------------------------------------------------------
# READING R THAT IS INSIDE PYTHON
# -----------------------------------------------------------------------------------------------

def _mask(text):
    """`text` with every R string and comment blanked, newlines kept, LENGTH PRESERVED.

    EVERY OFFSET INTO THE MASK IS AN OFFSET INTO THE SOURCE, which is the whole point: the scan
    is done on the mask so that a `(` inside a quoted caption cannot unbalance an argument list,
    and the text is then read back out of the ORIGINAL at the same indices. A mask that changed
    length would report a call site's line number from a position in a different file.

    Newlines survive inside strings and comments for the same reason. A multi-line caption that
    collapsed to one line here would move every draw site below it up the file.
    """
    out, i, n, quote = [], 0, len(text), None
    while i < n:
        c = text[i]
        if quote:
            if c == "\\" and i + 1 < n:
                out.append("  ")
                i += 2
                continue
            out.append("\n" if c == "\n" else " ")
            if c == quote:
                quote = None
            i += 1
            continue
        if c in "'\"`":
            quote = c
            out.append(" ")
            i += 1
            continue
        if c == "#":
            while i < n and text[i] != "\n":
                out.append(" ")
                i += 1
            continue
        out.append(c)
        i += 1
    return "".join(out)


def _code_only(text):
    """`text` with its R comments removed and its strings kept. For SHOWING an expression.

    A drawn expression is often a brace block whose first line is a paragraph of comment. Printed
    on one line - which is how a worksheet row prints it - the comment swallows the code that
    follows it and the row shows an explanation where it promised a plotting call. The comment is
    still where it was: the row names the file and the line.
    """
    out, i, n, quote = [], 0, len(text), None
    while i < n:
        c = text[i]
        if quote:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if c == quote:
                quote = None
            i += 1
            continue
        if c in "'\"`":
            quote = c
            out.append(c)
            i += 1
            continue
        if c == "#":
            while i < n and text[i] != "\n":
                i += 1
            continue
        out.append(c)
        i += 1
    return "".join(out)


def _closing(masked, open_at, pair="()"):
    """Index of the bracket that closes the one at `open_at`, or -1."""
    o, c = pair
    depth, i, n = 0, open_at, len(masked)
    while i < n:
        if masked[i] == o:
            depth += 1
        elif masked[i] == c:
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _split_args(text):
    """Top-level comma-separated pieces of an argument list, as written."""
    m = _mask(text)
    parts, depth, start = [], 0, 0
    for i, c in enumerate(m):
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == "," and depth == 0:
            parts.append(text[start:i])
            start = i + 1
    parts.append(text[start:])
    return [p for p in parts if p.strip()]


def _params(sig_text):
    """[(name, default-as-written or None)] for an R parameter list."""
    out = []
    for piece in _split_args(sig_text):
        name, eq, default = piece.partition("=")
        name = name.strip()
        if not name:
            continue
        out.append((name, default.strip() if eq else None))
    return out


def embedded_r(source):
    """[(R text, line of its first content line)] for every embedded R script in a Python file.

    FOUND BY WHAT IS IN IT, not by the name of the variable holding it. `_R_RUN`, `_R_COMPARE`
    and `_R_COHORT` are one plugin's habit; a scan keyed on that prefix finds nothing in the next
    plugin that embeds R and reports it as having no draw sites.

    THE LINE NUMBERS ARE THE PYTHON FILE'S. A draw site reported at "line 61 of the R" is a line
    number nobody can open. The mapping is arithmetic and is checked before it is used: a literal
    holding more newlines than the lines it spans has escapes in it, the arithmetic would be
    wrong, and such a literal is skipped rather than reported at a plausible wrong line.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            continue
        text = node.value
        if node.end_lineno is None or node.lineno is None:
            continue
        newlines = text.count("\n")
        if newlines > (node.end_lineno - node.lineno):
            continue
        if not re.search(r"(?m)^[ \t]*[.\w]+\s*<-\s*function\s*\(", text):
            continue
        # The literal's last content line sits on the line the literal ends on, so content line k
        # is `end_lineno - newlines - 1 + k`. Stored as the base; `+ k` is applied at each site.
        out.append((text, node.end_lineno - newlines - 1))
    return out


class Wrapper:
    """One discovered draw wrapper: what it is called, what it takes, where its legend goes."""

    def __init__(self, name, params, legend, line, lang, how, body=""):
        self.name = name
        #: [(name, default-as-written or None)] in declaration order.
        self.params = list(params)
        #: The parameter a legend is passed as, or None when the wrapper offers no findable slot.
        self.legend = legend
        self.line = line
        self.lang = lang
        self.how = how
        self.body = body

    @property
    def slot(self):
        """Position of the legend parameter in the signature, or -1."""
        names = [p for p, _d in self.params]
        return names.index(self.legend) if self.legend in names else -1

    def as_dict(self):
        return {"name": self.name, "params": [p for p, _d in self.params],
                "legend": self.legend, "line": self.line, "lang": self.lang, "how": self.how}


def _legend_param(params, used=()):
    """`(the parameter whose default is the empty string, why there is no single one)`.

    `used` narrows it to parameters the body actually mentions, so a dead parameter left behind by
    an edit is not reported as the slot a legend goes in.

    TWO EMPTY DEFAULTS IS NOT ONE OF THEM CHOSEN BY DECLARATION ORDER. `plate(slug, expr,
    provenance = "", subtitle = "", w = 900)` has two slots the wrapper cannot fill itself and
    nothing in the signature says which of them a legend goes in. Returning the first reported a
    DESCRIBED panel as silent - the call passed `subtitle` - and then printed `add: provenance =
    "..."`, sending the reader to fill in the wrong argument. The disagreement between two
    DEFINITIONS of one name is already reported next door; this is the same disagreement inside
    one signature, and it gets the same third answer: no slot, and the reason.
    """
    empty = ('""', "''", '" "', "character(0)")
    cands = [n for n, d in params if d is not None and d.strip() in empty]
    if used:
        inner = [n for n in cands if n in used]
        if inner:
            cands = inner
    if not cands:
        return None, ""
    if len(cands) > 1:
        listed = ", ".join(cands[:-1]) + " and " + cands[-1]
        return None, (f"its signature is AMBIGUOUS - {listed} each default to the empty string "
                      f"and nothing in it says which one carries the legend, so this extractor "
                      f"names none of them rather than sending you to fill in the wrong "
                      f"argument")
    return cands[0], ""


def r_wrappers(rtext):
    """[Wrapper] for every draw wrapper DEFINED in one embedded R script.

    A DRAW WRAPPER IS RECOGNISED BY WHAT IT DOES: it opens a graphics device, it evaluates
    something, and it closes the device. All three, in one function body. Two of the three is a
    device helper or a plotting helper and neither of those produces a panel on its own.
    """
    masked = _mask(rtext)
    dev = r"(?<![\w.])(?:[\w.]+:::?)?(?:" + "|".join(re.escape(d) for d in R_DEVICES) + r")\s*\("
    close = r"(?<![\w.])(?:" + "|".join(re.escape(c) for c in R_CLOSERS) + r")\s*\("
    ev = r"(?<![\w.])(?:[\w.]+:::?)?(?:" + "|".join(re.escape(e) for e in R_EVAL) + r")\s*\("
    out = []
    for mo in re.finditer(r"(?m)^[ \t]*([.\w]+)\s*<-\s*function\s*\(", masked):
        name = mo.group(1)
        op = masked.index("(", mo.end() - 1)
        cl = _closing(masked, op)
        if cl < 0:
            continue
        brace = masked.find("{", cl)
        if brace < 0:
            continue
        end = _closing(masked, brace, "{}")
        if end < 0:
            continue
        body_m, body = masked[brace:end + 1], rtext[brace:end + 1]
        if not (re.search(dev, body_m) and re.search(close, body_m)):
            continue
        params = _params(rtext[op + 1:cl])
        # WHAT THE BODY ACTUALLY USES. A parameter never mentioned in the body cannot be the
        # legend, however it is spelled.
        used = {n for n, _d in params if re.search(r"(?<![\w.])" + re.escape(n) + r"(?![\w.])",
                                                   body_m)}
        # AND WHAT IT PASSES TO THE DEVICE. Width, height and resolution are not descriptions of
        # a panel; excluding them keeps the empty-default rule from meeting a device argument
        # that happens to default to "".
        devcall = re.search(dev, body_m)
        devargs = set()
        if devcall:
            dcl = _closing(body_m, devcall.end() - 1)
            if dcl > 0:
                for piece in _split_args(body[devcall.end():dcl]):
                    devargs.update(re.findall(r"[.\w]+", piece))
        cands = [(n, d) for n, d in params if n not in devargs]
        legend, why = _legend_param(cands, used)
        evaluated = ""
        evm = re.search(ev, body_m)
        if evm:
            ecl = _closing(body_m, evm.end() - 1)
            if ecl > 0:
                evaluated = body[evm.end():ecl].strip()
        how = ("defined in this plugin's embedded R, opens a graphics device, evaluates "
               + (f"`{evaluated}`" if evaluated else "an expression") + " and closes the device")
        if why:
            how += ", but " + why
        out.append(Wrapper(name, params, legend, rtext[:mo.start()].count("\n") + 1, "R", how,
                           body))
    return out


# -----------------------------------------------------------------------------------------------
# THE HOST'S OWN EMIT PATH, WHICH IS NOT IN ANY PLUGIN
# -----------------------------------------------------------------------------------------------

#: The host package is the SAME for every plugin of a point, and a family status asks nine times.
#: Only the successful measurement is cached: a failure is usually something the reader is about
#: to fix - a package not yet on disk, a checkout half done - and a cached "could not look" would
#: outlive the fix for the rest of the process.
_EMITS: dict = {}


def _defs(node, owner=None):
    """`(owning class name or None, def node)` for every function in a module.

    THE OWNER IS PART OF THE MEASUREMENT. A def inside a class is reached through an instance and
    a def at module level is reached through an import, and `_reaches` needs to know which - the
    two are written differently at a call site and only one of them can be resolved from the
    plugin's own source.
    """
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.ClassDef):
            yield from _defs(child, child.name)
        elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield owner, child
            yield from _defs(child, owner)
        else:
            yield from _defs(child, owner)


def _call_shape(node, drop_self=False):
    """What a call to this def has to look like: `{required, positional, most, keywords}`.

    `keywords` is None when the def takes `**kwargs` and `most` is None when it takes `*args` -
    an unbounded signature accepts anything and this says so rather than guessing a bound.
    """
    a = node.args
    pos = [x.arg for x in list(getattr(a, "posonlyargs", [])) + list(a.args)]
    if drop_self and pos:
        pos = pos[1:]
    ndef = len(a.defaults)
    required = pos[:len(pos) - ndef] if ndef else list(pos)
    required += [x.arg for x, d in zip(a.kwonlyargs, a.kw_defaults) if d is None]
    return {"required": required, "positional": pos,
            "most": None if a.vararg else len(pos),
            # A LIST, NOT A SET. This record is carried in an `Inventory.detail` and inventories
            # get dumped; a set is not something the dump can round-trip.
            "keywords": None if a.kwarg else sorted(set(pos) | {x.arg for x in a.kwonlyargs})}


def _reached_as(shape):
    """The one clause of `how` that says where a call to this definition has to come from."""
    if shape["kind"] == "method":
        return (f"defined as a method of {shape['owner']} ({shape['at']}), so a call to it goes "
                f"through an instance of that")
    return (f"defined at module level in {shape['module']} ({shape['at']}), so a call to it comes "
            f"through an import of that module or of the name itself")


def host_emits(root, tool, declared=()):
    """Inventory of the host's draw paths. `tool` is what the REPOSITORY calls its own package.

    NO NAME OF ANY REPOSITORY APPEARS HERE. `tool` arrives from `DEVPOINTS.yaml`, which is where
    `sch dev` reads everything else about a repository, and the name of the emit path is measured
    out of the package that names. `declared` overrides the measurement for a repository whose
    emit path this rule cannot see - it is the same escape hatch `r_namespace` gives its pattern,
    and the answer says which of the two produced it.

    THE MEASUREMENT. A function in the host package that writes a figure file AND carries a
    parameter defaulting to the empty string is an emit path: it saves a panel, and it has a slot
    it cannot fill itself. That is the same sentence the R rule uses, applied to the other
    language, which is why the two halves of this extractor agree about what a draw site is.

    COULD NOT LOOK IS AN ANSWER. A root with no such package returns `complete=False`, never an
    empty inventory - a plugin scanned against zero known emit paths reports zero Python draw
    sites, and that is the exact shape of "found nothing" standing in for "did not look".
    """
    if declared:
        names = [str(x) for x in declared]
        return Inventory(str(tool), names,
                         "declared by this repository in its own DEVPOINTS.yaml",
                         detail={n: {"legend": "", "at": [], "params": [],
                                     "how": "declared, so the legend slot is whatever the "
                                            "call sites agree on"} for n in names})
    key = (str(root), str(tool))
    if key in _EMITS:
        return _EMITS[key]
    if not tool:
        return Inventory("", [], "", complete=False,
                         why_not="this repository's DEVPOINTS.yaml names no `tool:`, so there is "
                                 "no host package to measure an emit path out of. That is a gap "
                                 "in the declaration, not a plugin with no Python draw sites.")
    base = Path(root)
    pkg = base / str(tool)
    files = []
    if pkg.is_dir():
        files = sorted(pkg.rglob("*.py"))
    elif (base / f"{tool}.py").is_file():
        files = [base / f"{tool}.py"]
    if not files:
        return Inventory(str(tool), [], "", complete=False,
                         why_not=f"no package named {tool!r} under {base}, so the host's own emit "
                                 f"path could not be measured. An answer of zero Python draw "
                                 f"sites from here would be a fact about this checkout.")
    found = {}
    for f in files:
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        rel = f.relative_to(base)
        mod = ".".join(rel.with_suffix("").parts)
        if mod == "__init__":
            mod = str(tool)
        elif mod.endswith(".__init__"):
            mod = mod[:-len(".__init__")]
        for owner, node in _defs(tree):
            saves = any(
                isinstance(n, ast.Call)
                and ((isinstance(n.func, ast.Attribute) and n.func.attr in PY_SAVES)
                     or (isinstance(n.func, ast.Name) and n.func.id in PY_SAVES))
                for n in ast.walk(node))
            if not saves:
                continue
            params = _py_params(node)
            legend, why = _legend_param([(n, d) for n, d in params])
            if not legend and not why:
                continue
            # ONE NAME, EVERY DEFINITION OF IT. This repository defines its emit path twice - the
            # context method every plugin calls, and the compare panel's own - and keyed on the
            # name alone the second one to be read was thrown away. The name is what a call site
            # matches on, so it stays the key; WHERE it is defined is a list, and a disagreement
            # about which parameter is the legend is reported rather than resolved by file order.
            #
            # AND HOW IT IS REACHED IS MEASURED WITH IT. See `_reaches`: the name alone made any
            # `x.<name>(...)` in any plugin a draw site.
            rec = found.setdefault(node.name, {
                "legend": "", "at": [], "params": [n for n, _d in params],
                "slots": [], "shapes": [], "how": ""})
            rec["at"].append(f"{rel}:{node.lineno}")
            rec["slots"].append((legend, why))
            rec["shapes"].append({"at": f"{rel}:{node.lineno}", "module": mod,
                                  "kind": "method" if owner else "function",
                                  "owner": owner or "", "call": _call_shape(node, bool(owner))})
    for rec in found.values():
        slots = rec.pop("slots")
        whys = [w for _n, w in slots if w]
        named = sorted({n for n, _w in slots if n})
        reached = "; ".join(sorted({_reached_as(sh) for sh in rec["shapes"]}))
        if whys:
            rec["legend"] = ""
            rec["how"] = (f"writes a figure file, but {whys[0]}: {', '.join(rec['at'])}")
        elif len(named) > 1:
            rec["legend"] = ""
            rec["how"] = (f"defined more than once and the definitions disagree about which "
                          f"parameter carries the legend, so this extractor names none of "
                          f"them: {', '.join(rec['at'])}")
        else:
            rec["legend"] = named[0]
            rec["how"] = (f"writes a figure ({'/'.join(PY_SAVES[:2])}…) and takes "
                          f"{named[0]}=\"\", a slot it cannot fill itself; {reached}")
    if not found:
        return Inventory(str(tool), [], "", complete=False,
                         why_not=f"nothing in {tool} both writes a figure file and carries a "
                                 f"parameter defaulting to the empty string, so this rule cannot "
                                 f"say where the host emits a panel. Declare the emit path on the "
                                 f"point rather than letting an empty answer stand.")
    _EMITS[key] = Inventory(str(tool), sorted(found),
                            f"measured in {tool}: functions that write a figure file and carry a "
                            f"parameter defaulting to \"\" - a RULE, not a list, so a host that "
                            f"emits some other way is invisible to it",
                            detail=found)
    return _EMITS[key]




def _py_params(node):
    """[(name, default source or None)] for a Python def, keyword-only included."""
    a = node.args
    out = []
    positional = list(getattr(a, "posonlyargs", [])) + list(a.args)
    pad = [None] * (len(positional) - len(a.defaults)) + list(a.defaults)
    for arg, dflt in zip(positional, pad):
        out.append((arg.arg, _const(dflt)))
    for arg, dflt in zip(a.kwonlyargs, a.kw_defaults):
        out.append((arg.arg, _const(dflt)))
    return out


def _const(node):
    """A default rendered the way R's are - as source text - or None when there is no default."""
    if node is None:
        return None
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return '"' + node.value + '"'
    try:
        return ast.unparse(node)
    except Exception:                                                     # noqa: BLE001
        return "?"


# -----------------------------------------------------------------------------------------------
# THE SCAN
# -----------------------------------------------------------------------------------------------

def _r_sites(rtext, base_line, where, wrappers):
    """Every call to one of `wrappers` in one embedded R script."""
    masked = _mask(rtext)
    sites = []
    # ONE WRAPPER PER NAME PER SCRIPT. R has no overloads: a second definition of a name in the
    # same script replaces the first, and scanning both would report every call to it twice -
    # doubling the one number this extractor exists to produce. The three scripts of the plugin
    # this was measured on each define their own `npng`, which is why the de-duplication is per
    # script and not across the file.
    seen, unique = set(), []
    for w in wrappers:
        if w.name in seen:
            continue
        seen.add(w.name)
        unique.append(w)
    for w in unique:
        rx = re.compile(r"(?<![\w.$@])" + re.escape(w.name) + r"\s*\(")
        # NO GUARD AGAINST "THE DEFINITION, NOT A USE" IS NEEDED, AND THE ONE THAT WAS HERE COST
        # A SITE. An R definition is `name <- function(...)`, which never matches `name\s*(` -
        # the character after the name is `<`. So a `<-\s*$` test in front of the match
        # suppressed no definition anywhere; what it suppressed was `keep <- draw("x", plot(m))`,
        # a draw site whose result is assigned, which vanished from the count while the same site
        # written with R's other assignment operator - `keep = draw(...)` - was found. Pure false
        # negative: removing it left this corpus's counts unchanged and found the assigned case.
        for mo in rx.finditer(masked):
            op = mo.end() - 1
            cl = _closing(masked, op)
            if cl < 0:
                continue
            args = _split_args(rtext[op + 1:cl])
            named, positional = {}, []
            for piece in args:
                am = re.match(r"\s*([.\w]+)\s*=(?!=)", piece)
                if am:
                    named[am.group(1)] = piece[am.end():].strip()
                else:
                    positional.append(piece.strip())
            sites.append(_site(w, where, base_line + rtext[:mo.start()].count("\n") + 1,
                               named, positional, rtext, op, cl,
                               defined_at=f"{where}:{base_line + w.line}"))
    return sites


def _site(w, where, line, named, positional, text, op, cl, defined_at=""):
    """One draw site, with the answer to the only question this extractor asks."""
    panel = positional[0] if positional else (
        named.get(w.params[0][0], "") if w.params else "")
    call = " ".join(text[op + 1:cl].split())
    # THE RAW EXPRESSION AND THE ONE-LINE ONE ARE DIFFERENT THINGS AND BOTH ARE NEEDED. Collapsing
    # first and reading the calls out of the result put a `#` comment and the whole rest of the
    # expression on one line, so the mask blanked everything after it and three of these sites
    # reported no plotting call at all - the three whose authors had explained themselves.
    raw = ""
    if len(positional) > 1:
        raw = positional[1]
    elif len(w.params) > 1 and w.params[1][0] in named:
        raw = named[w.params[1][0]]
    drawn = " ".join(_code_only(raw).split())
    has = None
    if w.legend is not None:
        has = _passes(w, named, positional)
    return {"file": where, "line": line, "wrapper": w.name, "lang": w.lang,
            "panel": " ".join(str(panel).split()), "draws": drawn,
            # WHAT IS ACTUALLY BEING PLOTTED, pulled out of the expression, because that is the
            # first thing somebody writing a legend needs and it is buried inside a brace block
            # forty characters in. Reported, never decided: naming `netVisual_circle` does not
            # say what the panel shows, it says which page to open.
            "calls": _called(raw),
            "legend_param": w.legend or "", "has_legend": has,
            "legend": named.get(w.legend, "") if w.legend else "",
            "call": call[:400], "wrapper_at": defined_at, "how": w.how}


#: Called inside a plotting expression and not the thing being plotted: the plugin's own helpers
#: and R's own scaffolding. A DENYLIST, and it is one because nothing here can measure the
#: difference - see `_called` for what was tried and why it does not work. It only ever removes
#: rows from a worksheet column; the debt count and the file and line do not depend on it.
_NOT_A_PLOT = ("paste", "paste0", "sprintf", "c", "list", "as.numeric", "as.character", "table",
               "print", "force", "return", "function", "if", "for", "invisible", "length",
               "names", "seq_len", "seq_along", "nrow", "ncol", "rev", "sort", "which", "max",
               "min", "sum", "round", "format", "gsub", "sub", "grepl", "levels", "factor",
               "unlist", "par", "layout", "tryCatch", "try", "stop", "warning", "message",
               "suppressWarnings", "suppressMessages", "withCallingHandlers", "on.exit",
               "do.call", "Filter", "Reduce", "Map", "Negate", "is.null", "is.na", "identical",
               "nzchar", "setNames", "vapply", "sapply", "lapply", "mapply", "apply", "rep",
               "head", "tail", "abs", "sqrt", "mean", "median", "range", "dim", "assign", "get",
               "exists", "local", "stopifnot", "nchar", "trimws", "signif", "get0", "match.arg",
               "union", "intersect", "setdiff", "xlim", "ylim", "coord_fixed", "theme", "labs")


def _called(expression):
    """Names called in a drawn expression, outermost first, minus `_NOT_A_PLOT`. A GUESS.

    IT IS NOT A MEASUREMENT AND THE COLUMN THAT PRINTS IT SAYS SO. Measured on the plugin this
    was built against, 2 of its 35 rows name the wrong function: one names ggplot scaffolding
    and one a base-R count, because the plotting call is not always the first name in the
    expression and is sometimes not in the expression at all - it was assigned to a variable on
    the line above and the wrapper is handed the variable.

    WHAT WAS TRIED. An R brace block evaluates to its last top-level expression, so reading the
    column off that is a real measurement rather than a list. It moves three rows of the 35: one
    to a better answer, one to a differently-wrong one, and one from a correct plotting function
    to its neighbour. Not an improvement, so it was not taken. What WOULD settle it is the
    wrapped package's own exported names - which this repository already measures elsewhere -
    but that measurement needs the package installed, and a worksheet column that says something
    different depending on whether a reader has the upstream on their machine is worse than one
    that is consistently approximate. The debt, the file and the line are exact either way.
    """
    got = []
    for name in re.findall(r"(?<![\w.$@])([A-Za-z.][\w.]*)\s*\(", _mask(expression)):
        head = name.split("::")[-1]
        if head in _NOT_A_PLOT or head.startswith(".") or head in got:
            continue
        got.append(name)
    return got[:4]


def _passes(w, named, positional):
    """Did this call supply the legend? Named, PARTIALLY named, or positionally.

    R MATCHES ARGUMENT NAMES BY PREFIX, so `leg = "..."` fills `legend` and a scan looking only
    for the exact name would report a described panel as silent. And a call long enough to reach
    the slot positionally has supplied it without naming anything - rarer, and the same answer.
    """
    if w.legend in named:
        return True
    if any(w.legend.startswith(k) for k in named):
        return True
    consumed = set(named)
    slots = [n for n, _d in w.params if n not in consumed]
    return w.legend in slots and len(positional) > slots.index(w.legend)


def _imports(tree):
    """`{local name: the dotted thing it is bound to}` for every import in a module.

    Function-local imports included: a plugin that imports inside the function that draws is the
    common shape here, and a scan of the module header only would resolve none of them.
    """
    out = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for al in node.names:
                if al.asname:
                    out[al.asname] = al.name
                else:
                    head = al.name.split(".")[0]
                    out[head] = head
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            for al in node.names:
                out[al.asname or al.name] = f"{node.module}.{al.name}"
    return out


def _dotted(node):
    """`a.b.c` for a chain of plain attribute accesses on a name, else None."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return None
    parts.append(node.id)
    return ".".join(reversed(parts))


def _fits(node, shape):
    """Could this call be a call to something with that measured signature?

    Not a type check - there is nothing to type-check against here - but the arithmetic of a
    signature is measured, and it rules out the calls that made the bare-name match unsafe:
    a one-argument call cannot be a call to a function with three required parameters, and a
    keyword the signature does not have belongs to some other function of the same name.
    """
    if any(isinstance(a, ast.Starred) for a in node.args) or any(
            k.arg is None for k in node.keywords):
        return True                    # splatted at the call site: the shape cannot be read
    given = {k.arg for k in node.keywords}
    n = len(node.args)
    if shape["most"] is not None and n > shape["most"]:
        return False
    if shape["keywords"] is not None and not given <= set(shape["keywords"]):
        return False
    supplied = set(shape["positional"][:n]) | given
    return all(r in supplied for r in shape["required"])


def _reaches(node, rec, aliases, tool):
    """The measured definition this call could be reaching, or None if it reaches none of them.

    THE NAME ALONE IS NOT THE EMIT PATH, AND MATCHING ON IT MANUFACTURES DEBT. This host emits
    through a module-level function whose name is four common letters; keyed on the attribute
    name with no receiver check, a plugin that writes a checkpoint and a table and draws nothing
    at all was reported as two undescribed panels. That is the exact failure the third answer
    (UNKNOWN) exists to avoid, arrived at from the other side.

    SO HOW THE HOST IS REACHED IS MEASURED TOO, in `_defs`, and matched against how the call is
    written:

      A METHOD is reached through an instance. The instance is handed to the plugin and its type
      cannot be read off the plugin's source, so any receiver is accepted - which is a limit of
      this rule and is written down rather than papered over.

      A MODULE-LEVEL FUNCTION is reached through an import, and THAT the plugin's own source
      does say: `<alias>.<name>(...)` where the alias is bound to the defining module, or a bare
      `<name>(...)` where the name itself was imported from it.

    A path this repository DECLARED rather than let be measured has no shape to match, and is
    accepted however it is written - the same escape hatch, with the same consequences.
    """
    shapes = rec.get("shapes")
    if not shapes:
        return {}
    fn = node.func
    for sh in shapes:
        if not _fits(node, sh["call"]):
            continue
        if sh["kind"] == "method":
            if isinstance(fn, ast.Attribute):
                return sh
            continue
        if isinstance(fn, ast.Name):
            if aliases.get(fn.id) in (f"{sh['module']}.{fn.id}", f"{tool}.{fn.id}"):
                return sh
            continue
        dotted = _dotted(fn.value) if isinstance(fn, ast.Attribute) else None
        if dotted is None:
            continue
        head, _, rest = dotted.partition(".")
        dotted = aliases.get(head, head) + (f".{rest}" if rest else "")
        if dotted in (sh["module"], str(tool)):
            return sh
    return None


def _py_sites(source, where, emits):
    """Every call to one of the host's emit paths, from the plugin's own Python.

    PARSED, NOT GREPPED, AND THAT CHANGED THE ANSWER. A line-window scan of these nine plugins
    reported two sites as passing no legend. Both pass one: the argument sits six and seven lines
    below the opening parenthesis, behind a comment explaining what the legend had been getting
    wrong. A scan that reads three lines of a multi-line call invents debt in the plugins that
    documented their captions most carefully.

    AND A CALL IS MATCHED ON MORE THAN THE NAME - see `_reaches`.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    detail = getattr(emits, "detail", None) or {}
    want = set(getattr(emits, "names", ()) or ())
    aliases = _imports(tree)
    tool = getattr(emits, "tool", "") or ""
    sites = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = (node.func.attr if isinstance(node.func, ast.Attribute)
                else getattr(node.func, "id", None))
        if name not in want:
            continue
        d = detail.get(name) or {}
        if _reaches(node, d, aliases, tool) is None:
            continue
        slot = d.get("legend") or ""
        kw = {k.arg: k.value for k in node.keywords if k.arg}
        panel = ""
        if node.args:
            try:
                panel = ast.unparse(node.args[0])
            except Exception:                                             # noqa: BLE001
                panel = ""
        has = None
        legend = ""
        if slot:
            has = slot in kw
            if has:
                try:
                    legend = ast.unparse(kw[slot])
                except Exception:                                         # noqa: BLE001
                    legend = "?"
        try:
            call = " ".join(ast.unparse(node).split())
        except Exception:                                                 # noqa: BLE001
            call = ""
        drawn = ""
        if len(node.args) > 1:
            try:
                drawn = " ".join(ast.unparse(node.args[1]).split())
            except Exception:                                             # noqa: BLE001
                drawn = ""
        sites.append({"file": where, "line": node.lineno, "wrapper": name, "lang": "python",
                      "panel": " ".join(panel.split()), "draws": drawn, "calls": [],
                      "legend_param": slot, "has_legend": has, "legend": legend[:200],
                      "call": call[:400], "wrapper_at": ", ".join(d.get("at") or ()),
                      "how": d.get("how", "")})
    return sites


def draw_sites(name, source, where="", emits=None):
    """Inventory of one plugin's draw sites. `names` are `file:line`; `detail` is the record.

    COULD NOT PARSE IS NOT ZERO DRAW SITES. A plugin whose Python will not parse gets
    `complete=False` and says so; returning an empty list would file it as a plugin that draws
    nothing, and the legends stage would then report it finished.
    """
    where = where or f"{name}.py"
    try:
        ast.parse(source)
    except SyntaxError as e:
        return Inventory(name, [], "", complete=False,
                         why_not=f"{where} will not parse ({e.msg} at line {e.lineno}), so its "
                                 f"draw sites could not be read. That is not a plugin with no "
                                 f"figures.")
    sites, hows = [], []
    py = _py_sites(source, where, emits) if emits is not None else None
    if py is not None:
        sites += py
        if getattr(emits, "complete", False):
            hows.append(f"Python: calls to {', '.join(getattr(emits, 'names', ()))} - "
                        f"{getattr(emits, 'how', '')}")
        elif emits is not None and not getattr(emits, "complete", True):
            hows.append(f"Python: NOT LOOKED AT - {getattr(emits, 'why_not', '')}")
    nwrap = 0
    for rtext, base in embedded_r(source):
        ws = r_wrappers(rtext)
        nwrap += len(ws)
        sites += _r_sites(rtext, base, where, ws)
    if nwrap:
        hows.append(f"R: {nwrap} wrapper definition(s) found by what they do - a function defined "
                    f"in the embedded R that opens a graphics device, evaluates an expression and "
                    f"closes it")
    sites.sort(key=lambda s: (s["file"], s["line"]))
    ids = [f"{s['file']}:{s['line']}" for s in sites]
    detail = {}
    for i, s in enumerate(sites):
        # TWO SITES CAN SHARE A LINE - `npng(...); npng(...)` on one line is legal R and this
        # family writes it. Keyed on the line alone the second overwrites the first and the count
        # quietly drops by one, which is the one number this whole extractor exists to produce.
        key = ids[i]
        if key in detail:
            key = f"{key}#{i}"
            ids[i] = key
        detail[key] = s
    return Inventory(name, ids, "; ".join(hows) or "no draw wrapper of any known kind was found",
                     complete=True, detail=detail,
                     # MEASURED FROM THE SAME READ OF THE SAME SOURCE. A legend that is
                     # present and will not evaluate is not a described site, and every
                     # reader above this one counted it as one.
                     defects=empty_argument_slots(source),
                     defects_read=slots_read(source))


def sites_of(inv):
    """The records of one inventory, in source order. `names` is sorted; a file is not."""
    return sorted((getattr(inv, "detail", None) or {}).values(),
                  key=lambda s: (s.get("file", ""), s.get("line", 0)))


def silent(inv):
    """The sites that offer a legend and were not given one."""
    return [s for s in sites_of(inv) if s.get("has_legend") is False]


def unknown(inv):
    """The sites whose wrapper has no findable legend slot. NOT the same as silent."""
    return [s for s in sites_of(inv) if s.get("has_legend") is None]


def _slots_mask(text):
    """`text` with comments blanked and string CONTENT replaced by `s`, LENGTH PRESERVED.

    NOT `_mask`, and the difference is the whole check. `_mask` blanks a string to spaces, which
    is right when you are looking for brackets and wrong when you are looking for emptiness: it
    turns `cat("database:", n, "genes")` into a call whose every argument is blank, and the first
    version of this scan reported seven hundred and forty-two defects in a plugin that has one.
    A string is an argument that is THERE, so it has to survive as something visible.
    """
    out, i, n, quote = [], 0, len(text), None
    while i < n:
        c = text[i]
        if quote:
            if c == "\\" and i + 1 < n:
                out.append("ss")
                i += 2
                continue
            out.append("\n" if c == "\n" else "s")
            if c == quote:
                quote = None
            i += 1
            continue
        if c in "'\"`":
            quote = c
            out.append("s")
            i += 1
            continue
        if c == "#":
            while i < n and text[i] != "\n":
                out.append(" ")
                i += 1
            continue
        out.append(c)
        i += 1
    return "".join(out)


def empty_argument_slots(source):
    """[(line, snippet)] for every call in this file's embedded R holding an argument that is
    not there - `paste0(a,, b)`, `plot(x, y, )`.

    WHY THIS IS NOT A PARSE CHECK: R PARSES IT. `f(a,, b)` is a well-formed call carrying a
    missing argument, and R objects only when the call is EVALUATED - "argument is missing, with
    no default". So `parse(text = ...)` comes back clean, the module imports, the environment
    installs and the selftest passes. Measured: a legend this maker placed carried
    `paste0("...", name_a,,` at a draw site only the COMPARE phase reaches. All eighteen units
    drew all thirty-four of their panels, the plugin selftested ok, and the run then lost all six
    arm-pair comparisons one at a time, forty minutes in.

    WHY THE LEGENDS STAGE DID NOT ALREADY CATCH IT: it asks whether a site was GIVEN a legend,
    and this site was. `_split_args` drops blank pieces, so the empty slot is invisible to every
    reader above it - the legend is present, it is long, and it is not a thing R can run.

    AND WHY IT IS NOT A REGEX. `x[cond, , drop = FALSE]` is the ordinary way to stop a data frame
    collapsing to a vector; an empty slot in `[` means "every column" and is legitimate, common,
    and textually identical to the defect. The two are told apart ONLY by the delimiter that
    opened the list, so this carries a stack of openers. The regex written first reported four of
    this one plugin's `, , drop = FALSE` lines beside the single real defect - the same shape as
    the false positive `unguarded-grep-substitution` in sch/dev/jobcheck.py was fixed for, found
    the same way, on the same night.

    A NAMED SLOT IS NOT AN EMPTY ONE. `switch(x, a =, b = "both")` leaves `a =` deliberately
    valueless so that branch falls through; the text between those commas is `a =`, which is not
    blank, so it does not fire.
    """
    return _slots(source)[0]


def slots_read(source):
    """What `empty_argument_slots` actually looked at, as a sentence.

    FOUND-NOTHING IS NOT LOOKED-AND-FOUND-NOTHING, and this check has already been reported the
    wrong way round once - by me, in the commit that added it. "One hit across all nine plugins,
    the eight held-out ones clean" is true and means nothing: EIGHT OF THE NINE EMBED NO R AT ALL,
    so the scan read zero calls in them. The evidence is 1,645 calls inside the ninth. Every other
    reader in this package carries this distinction - `Inventory.complete`, freshness's CANNOT
    SAY, the LOWER BOUND line on a borrowed report - and a silent empty list here was the one
    place it was missing.
    """
    _, scripts, calls = _slots(source)
    if not scripts:
        return "no embedded R in this file, so no call was read for a missing argument"
    return f"{calls} call(s) in {scripts} embedded R script(s)"


def _slots(source):
    """(defects, number of R scripts read, number of calls read)."""
    out, scripts, calls = [], 0, 0
    for rtext, base in embedded_r(source):
        scripts += 1
        masked = _slots_mask(rtext)
        calls += masked.count("(")
        stack = []                                  # (opener, index after the last separator)
        for i, c in enumerate(masked):
            if c in "([{":
                stack.append([c, i + 1, 0])
            elif c in ")]}":
                if stack:
                    opener, last, commas = stack.pop()
                    if opener == "(" and commas and not masked[last:i].strip():
                        out.append(_where(rtext, base, i))
            elif c == "," and stack:
                opener, last, commas = stack[-1]
                if opener == "(" and not masked[last:i].strip():
                    out.append(_where(rtext, base, i))
                stack[-1][1] = i + 1
                stack[-1][2] = commas + 1
    return out, scripts, calls


def _where(rtext, base, i):
    """(line in the PYTHON file, the offending line as written).

    THE ARITHMETIC LIVES HERE ONCE. Both branches of the scan report a position and the first
    version spelled the conversion out in each; a mutation that reverted one of the two survived
    the suite untouched, because the fixture reaches only the other. A number computed in two
    places is a number that can be wrong in one of them.
    """
    return base + rtext[:i].count("\n") + 1, _around(rtext, i)


def _around(rtext, i):
    """The offending line, as written, trimmed for a report."""
    a = rtext.rfind("\n", 0, i) + 1
    b = rtext.find("\n", i)
    line = rtext[a:b if b >= 0 else len(rtext)].strip()
    return line if len(line) <= 110 else line[:107] + "..."


def ceiling_guards(source, token, returns="return", also=()):
    """Which draw wrappers CONSULT the declared ceiling, and which only carry it.

    A CEILING THE DRAWING CODE DOES NOT READ IS A COMMENT. Measured, on the plugin this was
    written for: 49 families each declaring `at_most`, the whole build phase green - `placement`
    reporting every family bounded, `status` reporting build 7 of 7 complete - and every guard
    removed from the embedded R. The declaration said what may be drawn and nothing stopped the
    drawing. Deleting a DECLARATION turns the maker red at once; deleting the code that honours
    it turned nothing red at all, which is the asymmetry this closes.

    WHAT IS CHECKED IS A SHAPE, NOT A MEANING. A wrapper passes when its body contains a
    conditional that MENTIONS the token and RETURNS - the early exit that refuses a panel. That
    cannot prove the arithmetic is right; `capacity --promised` holds a finished run against the
    declaration and is what proves the outcome. This is the build-phase half: it fails a plugin
    that declares ceilings and never reads them, which is the state that was green.

    THE TOKEN IS NOT KNOWN HERE. `ceiling`, `at_most`, `budget` - whatever the repository's own
    format calls the thing, it declares it, exactly as it declares which field holds a legend.

    THE SCAN IS ON THE MASK, so a guard that exists only inside a STRING LITERAL does not pass.
    (A commented-out guard is already excluded by the line having to start with `if`.)

    `also` IS THE R THAT DOES NOT LIVE INSIDE THE PYTHON. A plugin may keep its wrapper in a file
    beside itself and prepend it at run time - which is what `scprofile scaffold` now generates,
    one definition instead of one copy per embedded script. Read only from the Python, this check
    reported "no draw wrapper was found" for exactly those plugins and the stage called them done:
    the generated form would have been invisible to the check that demands it.
    """
    out = []
    for rtext, base in list(embedded_r(source)) + [(t, 0) for t, _n in (also or ())]:
        for w in r_wrappers(rtext):
            body = _mask(w.body or "")
            guarded = False
            for line in body.splitlines():
                s = line.strip()
                if not s.startswith("if") or token not in s:
                    continue
                # THE CONDITIONAL MUST LEAVE. `if (full) count <- count + 1` mentions the token
                # and draws the panel anyway.
                if returns in s:
                    guarded = True
                    break
            out.append({"wrapper": w.name, "line": base + w.line, "guarded": guarded})
    return out


def guard_report(rows, token):
    """A sentence for `ceiling_guards`: what was read, so silence is not mistaken for a pass."""
    if not rows:
        return ("no draw wrapper was found in this plugin's embedded scripts, so nothing was "
                "read for a ceiling guard")
    n = sum(1 for r in rows if r["guarded"])
    return (f"{n} of {len(rows)} draw wrapper(s) refuse past the declared ceiling, by a "
            f"conditional naming {token!r} that returns")
