"""Inventory the plotting surface of an installed Python package.

THE PACKAGE IS IMPORTED IN ITS OWN INTERPRETER, NEVER THIS ONE. A wrapped tool pins versions the
harness does not have, and importing scvelo into the process that is trying to inventory it either
fails or - worse - succeeds against whatever happens to be installed here and reports a surface
that is not the one the plugin will run against.

THREE WAYS TO FIND PLOTS, TRIED IN ORDER, AND THE ANSWER SAYS WHICH ONE ANSWERED.

  1. A PLOTTING SUBMODULE. scanpy, scvelo, cellrank, decoupler and liana all put their figures
     behind `pl` or `plotting`. Where one exists it IS the surface, and nothing needs guessing.
  2. NAMES. Without a submodule, public callables whose names begin the way plotting functions are
     named. This is what cellchat's R extractor does and it is a heuristic; it is reported as one.
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

    def by_signature(v):
        try:
            ps = inspect.signature(v).parameters
        except Exception:
            return False
        return any(n in DRAWS for n in ps)

    pub = public_callables(mod)
    byname = {a for a in pub if any(a.lower().startswith(p) for p in NAMEY)}
    bybody = {a for a, v in pub.items() if by_signature(v)}
    got = {a: pub[a] for a in sorted(byname | bybody)}
    if got:
        out["names"] = list(got)
        out["detail"] = {a: describe(v) for a, v in got.items()}
        for a in got:
            out["detail"][a]["found_by"] = ("both" if a in byname and a in bybody
                                            else "name" if a in byname else "signature")
        only_body = sorted(bybody - byname)
        out["how"] = ("public callables of %s whose names begin like plotting functions - a "
                      "HEURISTIC, because this package has no pl/plotting submodule - or whose "
                      "signature takes an axes or a figure to draw on. %d of %d were "
                      "reached by the signature rule%s"
                      % (name, len(bybody), len(got),
                         (", and %d ONLY by it: %s" % (len(only_body), ", ".join(only_body[:8])))
                         if only_body else ""))
        out["complete"] = True
    else:
        out["why_not"] = ("%s has no pl/plotting submodule, no public callable named like a "
                          "plotting function, and none whose signature takes an axes or a "
                          "figure, so this extractor "
                          "cannot say where its figures live. It is not evidence that there are "
                          "none." % name)
print(json.dumps(out))
""".replace("__NAMEY__", repr(list(_NAMEY))).replace("__DRAWS__", repr(list(_AXIS_PARAMS)))


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
