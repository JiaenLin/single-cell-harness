"""Inventory the plotting surface of an installed Python package.

THE PACKAGE IS IMPORTED IN ITS OWN INTERPRETER, NEVER THIS ONE. A wrapped tool pins versions the
harness does not have, and importing scvelo into the process that is trying to inventory it either
fails or - worse - succeeds against whatever happens to be installed here and reports a surface
that is not the one the plugin will run against.

THREE WAYS TO FIND PLOTS, TRIED IN ORDER, AND THE ANSWER SAYS WHICH ONE ANSWERED.

  1. A PLOTTING SUBMODULE. scanpy, scvelo, cellrank, decoupler and liana all put their figures
     behind `pl` or `plotting`. Where one exists it IS the surface, and nothing needs guessing.
  2. NAMES, SIGNATURES AND BODIES. Without a submodule, public callables whose names begin the way
     plotting functions are named, or that take an axes or a figure, or that write a figure file -
     read at the top level, AS METHODS of every public class the package defines (its own methods
     only), and IN every public submodule (autodev W019: pydeseq2 draws with two classes' methods
     and a function in `utils`, and none of the three is at its top level). The name rule is a
     heuristic and is reported as one; each name says which rule found it.
  3. NOTHING FOUND. Reported as incomplete, never as an empty inventory - "this package exports no
     plots" and "I could not find where its plots live" are different findings and only the first
     is about the tool.
"""
from __future__ import annotations

import json
import subprocess

from . import Inventory

EXTRACT = {
    "reads": "python-package",
    "summary": "public plotting callables of an installed Python package",
}

#: Prefixes a plotting function's name begins with, used only when there is no plotting submodule.
#: Deliberately short: a long list finds more and means less, and every name it returns has to be
#: read by a person deciding whether the wrapper should be using it.
_NAMEY = ("plot", "pl_", "draw", "scatter", "heatmap", "violin", "umap", "embedding",
          "dotplot", "barplot", "matrixplot", "rank_genes", "show")

#: A CALLABLE THAT TAKES AN AXES OR A FIGURE DRAWS ON IT. This is the second rule, and it is a
#: SIGNATURE rule rather than a name one - the same class of evidence as the legend slot this
#: family already finds in two languages by one language-neutral property ("the parameter whose
#: default is the empty string"). `ax=` is matplotlib's ecosystem convention and belongs to no
#: single package, which is the whole difference between it and the prefix list above.
#:
#: WHY A SECOND RULE AT ALL. In R, a name-only rule missed six of the thirty-seven upstream plots
#: one plugin accounts for - measured by a blind conversion - and every one of them draws. This
#: family's Python prefix list is the union of five packages' conventions, which is exactly the
#: shape that stops working on the sixth.
#:
#: TWO ROUTES THAT DID NOT WORK, BOTH MEASURED, BOTH WORTH THE RECORD. Looking for the graphics
#: package in the BODY - `gca(`, `plt.`, `matplotlib` - reported 133 of matplotlib.pyplot's 141
#: public callables, because every helper touches the module; that is "touches" reported as
#: "draws", the same substring-for-a-name error this suite has paid for elsewhere. Tightening it
#: to figure-PRODUCING calls - `savefig(`, `subplots(` - then returned `ioff`, `gcf` and `xkcd`
#: and MISSED `imshow`, `hexbin` and `radviz`, because a Python plotting function typically
#: neither creates nor saves a figure: it draws on an axes it was handed. Which is what this rule
#: reads instead.
#:
#: MEASURED ON pandas.plotting, which has no `pl` submodule: 13 of 15 public callables carry one
#: of these, and the two that do not - `register_matplotlib_converters` and its inverse - are
#: correctly not plotting functions. It reaches `radviz`, `andrews_curves` and
#: `parallel_coordinates`, which the prefix list misses entirely.
#:
#: WHAT IT CANNOT REACH: a plotting LIBRARY's own drawing layer, where the axes is implicit -
#: `matplotlib.pyplot.imshow` takes no `ax`. The subjects of this extractor are analysis packages
#: that USE such a library, and for those the convention holds.
#: `axis` IS NOT ON THIS LIST AND THE OMISSION IS MEASURED. In matplotlib `axis=` overwhelmingly
#: means WHICH AXIS - `tick_params(axis="x")`, `autoscale(axis="both")`, `grid(axis=...)` - a
#: string, not an object to draw on. Including it added five helpers of pyplot and no plotting
#: function anywhere.
_AXIS_PARAMS = ("ax", "axes", "fig", "figure")

#: A FUNCTION THAT WRITES ITS OWN FIGURE FILE DRAWS. The third rule, and the Python twin of the R
#: behaviour rule: it reads what the body DOES, not what the function is called or takes. Found
#: by the second blind conversion (docs/blind/0002-gseapy.md): gseapy's `gseaplot` and
#: `gseaplot2` build their own figure inside a class and take `ofname=` to save it - suffix
#: names, no axes - and both the name rule and the signature rule missed them, so the extractor
#: reported 3 of the tool's 5 drawing functions with a confident, complete-looking line. A cold
#: agent found the other two by reading the package's `__init__`, which is the check this rule
#: makes for it.
#:
#: MEASURED BEFORE IT WAS ADDED, on the three packages the venue held: gseapy +2 (exactly the two
#: missed; `enrichment_map`, which returns tables for an external layout, correctly not);
#: pandas.plotting +0; matplotlib.pyplot +1, and that one is `savefig` itself. The earlier
#: body-substring attempts recorded above failed by matching what a function TOUCHES; this
#: matches the one call that means a figure left the process.
_SAVES = ("savefig(",)

#: WHAT A DECISION NEEDS, not just what exists. The first version returned names, and a name is
#: the one thing the person deciding already has. Thirty-two of cellchat's thirty-five accounting
#: entries say WHERE THE OUTPUT LANDS and the other three say why the data cannot support the
#: plot - so the questions are "what does this draw" and "does this wrapper call it", and an
#: inventory of bare names makes somebody open thirty-five documentation pages to answer the first.
#: The signature and the summary line are in the package. Bring them.
_PROBE = r"""
import importlib, inspect, json, sys
name = sys.argv[1]
out = {"tool": name, "names": [], "detail": {}, "how": "", "complete": False, "why_not": ""}
try:
    mod = importlib.import_module(name)
except Exception as e:
    out["why_not"] = "%s: %s" % (type(e).__name__, e)
    print(json.dumps(out)); raise SystemExit(0)
out["version"] = getattr(mod, "__version__", "")

def describe(v):
    d = {"signature": "", "summary": "", "deprecated": False}
    try:
        d["signature"] = str(inspect.signature(v))
    except Exception:
        pass
    doc = inspect.getdoc(v) or ""
    for line in doc.splitlines():
        if line.strip():
            d["summary"] = line.strip()
            break
    d["deprecated"] = "deprecated" in doc[:400].lower()
    return d

def public_callables(m):
    got = {}
    for a in dir(m):
        if a.startswith("_"):
            continue
        try:
            v = getattr(m, a)
        except Exception:
            continue
        if callable(v) and not inspect.isclass(v):
            got[a] = v
    return got

sub = None
for cand in ("pl", "plotting", "plots"):
    s_ = getattr(mod, cand, None)
    if s_ is not None and hasattr(s_, "__name__"):
        sub = (cand, s_); break
    try:
        sub = (cand, importlib.import_module("%s.%s" % (name, cand))); break
    except Exception:
        continue

if sub is not None:
    cand, s_ = sub
    got = public_callables(s_)
    out["names"] = ["%s.%s" % (cand, a) for a in got]
    out["detail"] = {"%s.%s" % (cand, a): describe(v) for a, v in got.items()}
    out["how"] = ("every public callable of %s.%s, the package's own plotting submodule"
                  % (name, cand))
    out["complete"] = True
else:
    NAMEY = __NAMEY__
    DRAWS = __DRAWS__

    SAVES = __SAVES__

    def by_signature(v):
        try:
            ps = inspect.signature(v).parameters
        except Exception:
            return False
        return any(n in DRAWS for n in ps)

    def by_saves(v):
        try:
            src = inspect.getsource(v)
        except Exception:
            return False
        return any(s in src for s in SAVES)

    # WHERE A PACKAGE WITHOUT A PLOTTING SUBMODULE KEEPS ITS PLOTS (autodev W019, GAP-C39). Its
    # top level is not the whole of it: pydeseq2 exports nothing at the top, draws with METHODS of
    # its two classes (`DeseqDataSet.plot_dispersions`, `DeseqStats.plot_MA`) and with a function
    # in a SUBMODULE (`utils.make_MA_plot`), and this extractor read only the top level - "no
    # extractor could look at pydeseq2". So the same three rules also read every public class the
    # package defines, by its OWN methods (pydeseq2's DeseqDataSet is an AnnData, and AnnData's
    # methods are not pydeseq2's plots), and every public submodule, by what it defines. A name is
    # relative to the package, one per function, the shortest public path to it.
    import pkgutil
    hits = {}                  # id(function) -> [name, function, rules]
    classes, submodules, unimportable = set(), [], []

    def consider(qual, short, v):
        rules = [r for r, hit in (
            ("name", any(short.lower().startswith(p) for p in NAMEY)),
            ("signature", by_signature(v)), ("saves", by_saves(v))) if hit]
        if not rules:
            return
        have = hits.get(id(v))
        if have is None or (len(qual), qual) < (len(have[0]), have[0]):
            hits[id(v)] = [qual, v, rules]

    def methods_of(cls, prefix):
        classes.add(cls)
        for a, raw in vars(cls).items():
            if a.startswith("_"):
                continue
            fn = raw.__func__ if isinstance(raw, (staticmethod, classmethod)) else raw
            if inspect.isfunction(fn):
                consider("%s.%s" % (prefix, a), a, fn)

    def defined_in(v, modname):
        return getattr(v, "__module__", "") == modname

    for a, v in public_callables(mod).items():
        consider(a, a, v)
    for a in dir(mod):
        if a.startswith("_"):
            continue
        try:
            v = getattr(mod, a)
        except Exception:
            continue
        if inspect.isclass(v) and str(getattr(v, "__module__", "")).split(".")[0] == name.split(".")[0]:
            methods_of(v, a)
    if hasattr(mod, "__path__"):
        _skip = ("tests", "test", "testing", "conftest")
        for info in pkgutil.walk_packages(mod.__path__, name + ".",
                                          onerror=lambda n: unimportable.append(n)):
            rel = info.name[len(name) + 1:]
            if any(p.startswith("_") or p in _skip for p in rel.split(".")):
                continue
            try:
                sub = importlib.import_module(info.name)
            except Exception as e:
                unimportable.append("%s (%s)" % (rel, type(e).__name__))
                continue
            submodules.append(rel)
            for a in dir(sub):
                if a.startswith("_"):
                    continue
                try:
                    v = getattr(sub, a)
                except Exception:
                    continue
                if inspect.isclass(v):
                    if defined_in(v, info.name):
                        methods_of(v, "%s.%s" % (rel, a))
                elif callable(v) and defined_in(v, info.name):
                    consider("%s.%s" % (rel, a), a, v)

    got = {q: (v, rules) for q, v, rules in sorted(hits.values(), key=lambda t: t[0])}
    byname = {q for q, (_v, r) in got.items() if "name" in r}
    bybody = {q for q, (_v, r) in got.items() if "signature" in r}
    bysaves = {q for q, (_v, r) in got.items() if "saves" in r}
    read = ("; read: the top level, %d public class(es) by their own methods and %d public "
            "submodule(s)%s" % (len(classes), len(submodules),
                                (", %d submodule(s) would not import: %s"
                                 % (len(unimportable), ", ".join(unimportable[:6])))
                                if unimportable else ""))
    if got:
        out["names"] = list(got)
        out["detail"] = {q: describe(v) for q, (v, _r) in got.items()}
        for q, (_v, rules) in got.items():
            out["detail"][q]["found_by"] = "+".join(rules)
        only_sig = sorted(bybody - byname - bysaves)
        only_saves = sorted(bysaves - byname - bybody)
        out["how"] = ("public callables of %s whose names begin like plotting functions - a "
                      "HEURISTIC, because this package has no pl/plotting submodule - or whose "
                      "signature takes an axes or a figure to draw on, or whose body writes a "
                      "figure file. %d of %d were reached by the signature rule%s; %d by the "
                      "body rule%s%s"
                      % (name, len(bybody), len(got),
                         (", %d ONLY by it: %s" % (len(only_sig), ", ".join(only_sig[:8])))
                         if only_sig else "",
                         len(bysaves),
                         (", %d ONLY by it: %s" % (len(only_saves), ", ".join(only_saves[:8])))
                         if only_saves else "", read))
        out["complete"] = True
    else:
        out["why_not"] = ("%s has no pl/plotting submodule, and no public callable - at its top "
                          "level, as a method of a class it defines, or in a submodule - named "
                          "like a plotting function, taking an axes or a figure, or writing a "
                          "figure file, so this extractor cannot say where its figures live. It "
                          "is not evidence that there are none%s." % (name, read))
print(json.dumps(out))
""".replace("__NAMEY__", repr(list(_NAMEY))).replace("__DRAWS__", repr(list(_AXIS_PARAMS))) \
   .replace("__SAVES__", repr(list(_SAVES)))


def inventory(tool, python="python3", timeout=180):
    """Inventory `tool` using the interpreter its plugin actually runs in."""
    try:
        p = subprocess.run([python, "-c", _PROBE, tool], capture_output=True, text=True,
                           timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        return Inventory(tool, [], "", complete=False,
                         why_not=f"could not run {python}: {type(e).__name__}: {e}")
    line = (p.stdout or "").strip().splitlines()
    if not line:
        return Inventory(tool, [], "", complete=False,
                         why_not=f"{python} produced no answer: {(p.stderr or '')[-200:]}")
    try:
        d = json.loads(line[-1])
    except ValueError:
        return Inventory(tool, [], "", complete=False,
                         why_not=f"unreadable answer from {python}: {line[-1][:160]}")
    return Inventory(d["tool"], d["names"], d["how"], d["complete"], d["why_not"],
                     detail=d.get("detail") or {})


# -----------------------------------------------------------------------------------------------
# THE OTHER QUESTION AN UPSTREAM CAN ANSWER. The inventory above asks what a package DRAWS; this
# asks what one of its functions TAKES. A plugin calls a handful of a tool's functions, and every
# parameter of those it does not pass is a default it has inherited without looking - which is the
# defect `config` exists to prevent, and the reason DEVPOINTS names decoupler's `min_n` and
# cellrank's terminal-state method.
# -----------------------------------------------------------------------------------------------

_PARAMS = r"""
import importlib, inspect, json, sys
out = {}
for path in sys.argv[1:]:
    root = path.split(".")[0]
    try:
        _v = getattr(importlib.import_module(root), "__version__", "")
    except Exception:
        _v = ""
    mod, _, attr = path.rpartition(".")
    rec = {"found": False, "why_not": "", "params": [], "summary": "", "installed": _v}
    fn = None
    while mod and fn is None:
        try:
            m = importlib.import_module(mod)
        except Exception as e:
            rec["why_not"] = "%s: %s" % (type(e).__name__, e)
            mod, _, head = mod.rpartition(".")
            attr = head + "." + attr if head else attr
            continue
        obj = m
        try:
            for part in attr.split("."):
                obj = getattr(obj, part)
            fn = obj
        except Exception as e:
            rec["why_not"] = "%s: %s" % (type(e).__name__, e)
            break
    if fn is None:
        out[path] = rec
        continue
    rec["found"] = True
    rec["why_not"] = ""
    doc = inspect.getdoc(fn) or ""
    for line in doc.splitlines():
        if line.strip():
            rec["summary"] = line.strip(); break
    try:
        sig = inspect.signature(fn)
    except Exception as e:
        rec["why_not"] = "no signature: %s" % e
        out[path] = rec
        continue
    for nm, prm in sig.parameters.items():
        if prm.kind in (prm.VAR_POSITIONAL, prm.VAR_KEYWORD):
            continue
        rec["params"].append({
            "name": nm,
            "default": "" if prm.default is prm.empty else repr(prm.default),
            "required": prm.default is prm.empty,
            "annotation": "" if prm.annotation is prm.empty else str(prm.annotation)[:60],
        })
    out[path] = rec
print(json.dumps(out))
"""


def parameters(paths, python="python3", timeout=180):
    """{dotted path: {found, why_not, summary, params:[{name, default, required, annotation}]}}.

    Resolved in the interpreter the PLUGIN runs in, for the same reason the inventory is: a
    signature read from a different version of the package is a signature the plugin will never
    see, and a default that has since changed is exactly what this exists to catch.
    """
    if not paths:
        return {}
    try:
        p = subprocess.run([python, "-c", _PARAMS, *paths], capture_output=True, text=True,
                           timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        return {k: {"found": False, "why_not": f"could not run {python}: {e}", "params": [],
                    "summary": ""} for k in paths}
    txt = (p.stdout or "").strip().splitlines()
    if not txt:
        return {k: {"found": False, "params": [], "summary": "",
                    "why_not": f"{python} produced no answer: {(p.stderr or '')[-160:]}"}
                for k in paths}
    try:
        return json.loads(txt[-1])
    except ValueError:
        return {k: {"found": False, "params": [], "summary": "",
                    "why_not": f"unreadable answer: {txt[-1][:160]}"} for k in paths}
