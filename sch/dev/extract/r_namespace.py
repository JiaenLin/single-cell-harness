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
import tempfile
from pathlib import Path

from . import Inventory

EXTRACT = {
    "reads": "r-package",
    "summary": "exported plotting functions of an installed R package",
}

#: The default pattern. Union of the conventions this family has met plus the ones ggplot-based
#: packages use. Overridable, because no pattern is general and pretending otherwise is how an
#: inventory comes back empty and gets believed.
DEFAULT_PATTERN = "^(netVisual|netAnalysis|plot|Plot|show|draw|gg|Stacked|vis|Vis)"

#: R'S OWN PLOTTING ENTRY POINTS - the base graphics verbs, grid, lattice, ggplot2 and the two
#: heatmap packages every bioinformatics package in this family reaches for. These belong to R and
#: its ecosystem; not one of them is a wrapped tool's name, which is the whole difference between
#: this list and the pattern above.
#:
#: WHY A SECOND RULE AT ALL, MEASURED. A blind conversion - the finished plugin hidden, the plugin
#: scaffolded from nothing, the maker pointed at the real namespace - reproduced 31 of the 37
#: upstream plots that plugin accounts for. The six it could not reach were `rankNet`,
#: `rankSimilarity`, `compareInteractions`, `identifyCommunicationPatterns`, `netClustering` and
#: `interaction_lr`: every one of them draws, and not one of them starts with a prefix in the
#: pattern. The pattern is a convention and six functions of one package did not follow their own.
_PRIMITIVES = (
    "plot", "plot.new", "barplot", "boxplot", "hist", "image", "contour", "persp", "pie",
    "matplot", "pairs", "dotchart", "stripchart", "mosaicplot", "smoothScatter", "curve",
    "ggplot", "qplot", "autoplot",
    "grid.draw", "grid.newpage", "pushViewport", "grid.arrange",
    "xyplot", "levelplot", "densityplot",
    "heatmap", "heatmap.2", "pheatmap", "corrplot", "Heatmap",
)

#: MEASURED ON THREE PACKAGES THAT ARE NOT THE ONE THIS WAS WRITTEN FOR, which is the only kind
#: of evidence that says a rule generalises. Exports the BODY rule reaches and the name pattern
#: cannot: ggplot2 15, lattice 6, cluster 1 - `bannerplot`, `panel.violin`, `panel.cloud`,
#: `xyplot.ts`, every one of them a real plotting function. lattice finds NOTHING by name alone.

#: R RETURNS ONLY WHAT ONLY R KNOWS - the matching export names. The first version had R build
#: the whole answer including a `how` sentence containing the pattern, and the pattern's own quotes
#: broke the JSON it was being written into. Anything Python already knows is built in Python.
#:
#: TWO RULES, AND EACH EXPORT SAYS WHICH ONE FOUND IT. A name is a convention and a body is
#: evidence; reporting them together and unlabelled would hide which of the two is doing the work,
#: and it is the labelling that shows when a convention has stopped being followed.
_PROBE = r"""
args <- commandArgs(trailingOnly = TRUE)
pkg <- args[1]; pat <- args[2]; prims <- strsplit(args[3], ",", fixed = TRUE)[[1]]
ok <- suppressWarnings(suppressMessages(requireNamespace(pkg, quietly = TRUE)))
if (!ok) { cat("SCH_NO_NAMESPACE"); quit(status = 0) }
ns <- asNamespace(pkg)
ex <- sort(getNamespaceExports(pkg))
byname <- grep(pat, ex, value = TRUE)
# ONE PATTERN PER PRIMITIVE, built with fixed=TRUE escaping. Assembling them into a single
# alternation needs a backslash count that survives R's string parser, an R regex and a shell
# argument at once, and the first attempt produced an octal escape instead of a group reference.
pats <- paste0("(?<![\\w.])", gsub(".", "\\.", prims, fixed = TRUE), "\\s*\\(")
draws <- function(txt) {
  for (p in pats) if (grepl(p, txt, perl = TRUE)) return(TRUE)
  grepl("(?<![\\w.])geom_", txt, perl = TRUE)
}
bybody <- character(0)
for (nm in ex) {
  f <- tryCatch(get(nm, envir = ns), error = function(e) NULL)
  if (!is.function(f)) next
  txt <- tryCatch(paste(deparse(body(f)), collapse = " "), error = function(e) "")
  if (nzchar(txt) && draws(txt)) bybody <- c(bybody, nm)
}
hit <- sort(union(byname, bybody))
tag <- ifelse(hit %in% byname, ifelse(hit %in% bybody, "both", "name"), "body")
cat("SCH_OK"); cat(paste(c("", paste(hit, tag, sep = "\t")), collapse = "\n"))
"""


def inventory(tool, rscript=None, pattern=DEFAULT_PATTERN, timeout=180):
    """Inventory `tool` through R. `rscript` defaults to whatever is on PATH."""
    exe = rscript or shutil.which("Rscript") or shutil.which("R")
    if not exe:
        return Inventory(tool, [], "", complete=False,
                         why_not="no Rscript on PATH, so this package was not looked at. That is "
                                 "a fact about this machine and not about the package.")
    # THE PROBE GOES IN A FILE, NOT THROUGH `-e`. A backslash does not survive that route: the
    # probe's `"(?<![\\w.])"` reached R as `"\\w"` with one backslash and R refused the whole
    # script with "unrecognized escape in character string" - on a script that runs correctly when
    # the identical text is in a file. The earlier version had no backslashes in it and so never
    # met this. A temporary file removes the layer instead of counting backslashes through it.
    try:
        with tempfile.TemporaryDirectory(prefix="sch-r-probe-") as tmp:
            f = Path(tmp) / "probe.R"
            f.write_text(_PROBE, encoding="utf-8")
            p = subprocess.run([exe, "--vanilla", str(f), tool, pattern,
                                ",".join(_PRIMITIVES)],
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
        # SAY WHAT ACTUALLY HAPPENED, INCLUDING WHEN NOTHING DID. This read
        # `produced no answer: {stderr or stdout}` and the case it met was BOTH STREAMS EMPTY -
        # so it rendered as "produced no answer: " with nothing after the colon, which is the
        # least informative output possible for the one failure that most needs explaining.
        # An R that exits without writing anything is a different problem from an R that writes
        # an error, and the exit status is what tells them apart.
        # THE TRUNCATION IS FOR CAPTURED OUTPUT, NOT FOR THE SENTENCE EXPLAINING IT. `[-300:]`
        # applied to the whole thing took the front off this module's own advice and produced
        # "nd stderr were empty" - a message about unreadable output, made unreadable.
        captured = ((p.stderr or "").strip() or txt)[-300:]
        detail = captured or (
            f"both stdout and stderr were empty. An R that produces nothing at all usually "
            f"cannot start: check that {exe} runs outside this tool, and that R_HOME and the "
            f"shared libraries its build needs are reachable from a non-interactive shell.")
        return Inventory(tool, [], "", complete=False,
                         why_not=f"{exe} produced no answer (exit {p.returncode}): {detail}")
    rows = [ln.strip().split("\t") for ln in txt[len("SCH_OK"):].splitlines() if ln.strip()]
    names = [r[0] for r in rows]
    by = {r[0]: (r[1] if len(r) > 1 else "name") for r in rows}
    n_body = sum(1 for v in by.values() if v in ("body", "both"))
    only_body = sorted(k for k, v in by.items() if v == "body")
    return Inventory(tool, names,
                     f"exports of {tool} that either match {pattern!r} - a CONVENTION, not a "
                     f"definition - or call one of R's own plotting entry points in their body. "
                     f"{n_body} of {len(names)} were reached by the body rule"
                     + (f", and {len(only_body)} ONLY by it: "
                        + ", ".join(only_body[:8])
                        + (f" and {len(only_body) - 8} more" if len(only_body) > 8 else "")
                        if only_body else ""),
                     complete=True, detail=by)
