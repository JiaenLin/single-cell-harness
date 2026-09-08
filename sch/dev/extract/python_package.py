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

_PROBE = r'''
import importlib, inspect, json, sys
name = sys.argv[1]
out = {"tool": name, "names": [], "how": "", "complete": False, "why_not": ""}
try:
    mod = importlib.import_module(name)
except Exception as e:
    out["why_not"] = f"{type(e).__name__}: {e}"
    print(json.dumps(out)); raise SystemExit(0)
out["version"] = getattr(mod, "__version__", "")

def public_callables(m):
    got = []
    for a in dir(m):
        if a.startswith("_"):
            continue
        try:
            v = getattr(m, a)
        except Exception:
            continue
        if callable(v) and not inspect.isclass(v):
            got.append(a)
    return got

sub = None
for cand in ("pl", "plotting", "plots"):
    s = getattr(mod, cand, None)
    if s is not None and hasattr(s, "__name__"):
        sub = (cand, s); break
    try:
        s = importlib.import_module(f"{name}.{cand}")
        sub = (cand, s); break
    except Exception:
        continue

if sub is not None:
    cand, s = sub
    out["names"] = [f"{cand}.{a}" for a in public_callables(s)]
    out["how"] = f"every public callable of {name}.{cand}, the package's own plotting submodule"
    out["complete"] = True
else:
    NAMEY = %(namey)r
    got = [a for a in public_callables(mod) if any(a.lower().startswith(p) for p in NAMEY)]
    if got:
        out["names"] = got
        out["how"] = ("public callables of %%s whose names begin like plotting functions - a "
                      "HEURISTIC, because this package has no pl/plotting submodule" %% name)
        out["complete"] = True
    else:
        out["why_not"] = (f"{name} has no pl/plotting submodule and no public callable named like "
                          f"a plotting function, so this extractor cannot say where its figures "
                          f"live. It is not evidence that there are none.")
print(json.dumps(out))
''' % {"namey": list(_NAMEY)}


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
    return Inventory(d["tool"], d["names"], d["how"], d["complete"], d["why_not"])
