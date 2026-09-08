"""Inventory the plotting surface of an installed R package.

THIS IS CELLCHAT'S FOUR LINES, TAKEN OUT OF CELLCHAT. The only inventory extractor this family has
ever had lived inside `kernels/cellchat.py` as `_R_INVENTORY`:

    ex <- sort(getNamespaceExports("CellChat"))
    plotting <- grep("^(netVisual|netAnalysis|plot|show|StackedVln)", ex, value = TRUE)

It worked, and it produced the accounting that took that plugin from one upstream plot used to
thirty-two. It was also unreachable by anything else, and the pattern in it is CellChat's own
naming convention written as if it were a general rule.

WHAT IS GENERAL AND WHAT IS NOT. `getNamespaceExports` is general. The grep is not: a package that
names its plots `ggXxx` or `draw_*` is invisible to CellChat's pattern. So the pattern is an
ARGUMENT with a documented default, and the answer says which pattern produced it - because an
inventory a maintainer cannot argue with is one they will accept without reading.
"""
from __future__ import annotations

import shutil
import subprocess

from . import Inventory

EXTRACT = {
    "reads": "r-package",
    "summary": "exported plotting functions of an installed R package",
}

#: The default pattern. Union of the conventions this family has met plus the ones ggplot-based
#: packages use. Overridable, because no pattern is general and pretending otherwise is how an
#: inventory comes back empty and gets believed.
DEFAULT_PATTERN = "^(netVisual|netAnalysis|plot|Plot|show|draw|gg|Stacked|vis|Vis)"

#: R RETURNS ONLY WHAT ONLY R KNOWS - the matching export names. The first version had R build
#: the whole answer including a `how` sentence containing the pattern, and the pattern's own quotes
#: broke the JSON it was being written into. Anything Python already knows is built in Python.
_PROBE = r"""
args <- commandArgs(trailingOnly = TRUE)
pkg <- args[1]; pat <- args[2]
ok <- suppressWarnings(suppressMessages(requireNamespace(pkg, quietly = TRUE)))
if (!ok) { cat("SCH_NO_NAMESPACE"); quit(status = 0) }
hit <- grep(pat, sort(getNamespaceExports(pkg)), value = TRUE)
cat("SCH_OK"); cat(paste(c("", hit), collapse = "\n"))
"""


def inventory(tool, rscript=None, pattern=DEFAULT_PATTERN, timeout=180):
    """Inventory `tool` through R. `rscript` defaults to whatever is on PATH."""
    exe = rscript or shutil.which("Rscript") or shutil.which("R")
    if not exe:
        return Inventory(tool, [], "", complete=False,
                         why_not="no Rscript on PATH, so this package was not looked at. That is "
                                 "a fact about this machine and not about the package.")
    try:
        p = subprocess.run([exe, "--vanilla", "-e", _PROBE, tool, pattern],
                           capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        return Inventory(tool, [], "", complete=False,
                         why_not=f"could not run {exe}: {type(e).__name__}: {e}")
    txt = (p.stdout or "").strip()
    if txt.startswith("SCH_NO_NAMESPACE"):
        return Inventory(tool, [], "", complete=False,
                         why_not=f"R cannot load the namespace {tool!r}. Install it in the "
                                 f"environment this plugin runs in, then ask again - an empty "
                                 f"inventory here would read as a package with no plots.")
    if not txt.startswith("SCH_OK"):
        return Inventory(tool, [], "", complete=False,
                         why_not=f"{exe} produced no answer: {(p.stderr or txt)[-200:]}")
    names = [ln.strip() for ln in txt[len("SCH_OK"):].splitlines() if ln.strip()]
    return Inventory(tool, names,
                     f"exports of {tool} matching {pattern!r}, which is a PATTERN and not a "
                     f"definition - a package naming its plots some other way is invisible to it",
                     complete=True)
