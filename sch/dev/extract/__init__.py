"""Extractors: the part of a conversion that reads somebody else's codebase.

WHY THIS IS A DIRECTORY AND NOT A FUNCTION. The only working inventory extractor this family has
ever had is four lines of R inside `kernels/cellchat.py`:

    ex <- sort(getNamespaceExports("CellChat"))
    plotting <- grep("^(netVisual|netAnalysis|plot|show|StackedVln)", ex, value = TRUE)

`scprofile/native.py` is already domain-free and says so - "Nothing here knows what tool is being
wrapped. The inventory is the plugin's, measured from its environment" - so the ACCOUNTING half of
the mechanism has been general and shipped for weeks. The half that reads the foreign package was
never extracted from the plugin it was written for, and that is why eight of nine plugins owe an
accounting: not because nobody did the work, but because there is no command that does it.

An extractor declares what kind of upstream it can read and returns an inventory. Adding one for a
new kind of tool - a CLI, a Nextflow module, a Bioconductor package - is a file dropped in here.

WHAT AN EXTRACTOR MUST NEVER DO is return an empty inventory when it could not look. "This package
exports no plotting functions" and "I could not import this package" are different findings and
only the first is about the tool; conflating them would file an accounting of zero as complete.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

#: What an extractor module declares. `reads` is the kind of upstream it can inventory.
REQUIRED = ("reads", "summary")


class Inventory:
    """What one extractor found, and how it decided. Never a bare list.

    `how` is carried because the accounting stage has to be arguable: a maintainer looking at 34
    function names needs to know whether they came from a plotting submodule, a name pattern, or a
    guess, before deciding which of them this wrapper should be using.
    """

    def __init__(self, tool, names, how, complete=True, why_not="", detail=None,
                 defects=()):
        self.tool = tool
        self.names = sorted(names)
        self.how = how
        #: {name: {signature, summary, deprecated}} where the extractor could get it. A NAME IS
        #: THE ONE THING THE DECIDER ALREADY HAS; what they need is what the function draws.
        self.detail = dict(detail or {})
        #: [(line, text)] the extractor read and the LANGUAGE WILL NOT RUN. Not a name it
        #: found and not a debt of any one call - a plugin can be complete, described and
        #: unable to execute, which is how a legend carrying `paste0(a,, b)` passed every
        #: gate this repository had and killed six comparisons on the cohort.
        self.defects = list(defects)
        #: False when the extractor could not look. NOT the same as an empty inventory.
        self.complete = bool(complete)
        self.why_not = why_not

    def __bool__(self):
        return self.complete

    def __len__(self):
        return len(self.names)

    def as_dict(self):
        return {"tool": self.tool, "names": self.names, "how": self.how,
                "complete": self.complete, "why_not": self.why_not, "detail": self.detail,
                "defects": self.defects}


def _load(path: Path, here: bool):
    """Import one extractor. BUILT-INS GO THROUGH THE PACKAGE, so relative imports work.

    Loading `python_package.py` by file path gave it no package context, so its `from . import
    Inventory` raised - and `discover()` swallowed that and returned an empty dict, which reads as
    "there are no extractors" rather than "the only two could not be loaded". The same
    found-nothing-versus-looked-wrongly defect this family has now fixed in four other places, in
    the loader written to fix it in a fifth.
    """
    if here:
        return importlib.import_module(f"{__name__}.{path.stem}")
    spec = importlib.util.spec_from_file_location(f"_sch_extract_{path.stem}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def discover(strict=False) -> dict:
    """{name: module} for every extractor here and on $SCH_EXTRACTORS.

    A site directory, for the same reason every other search path in this family has one: reading
    an in-house tool's plotting surface is exactly the kind of thing a site knows and this
    repository cannot.

    `strict` raises on an extractor that will not load, instead of leaving it out. The default is
    lenient because one broken site extractor must not stop the built-in ones working; the test
    suite passes strict, so a broken one is never merely quiet.
    """
    out = {}
    mine = Path(__file__).resolve().parent
    dirs = [mine]
    dirs += [Path(p) for p in (os.environ.get("SCH_EXTRACTORS") or "").split(os.pathsep) if p]
    for d in dirs:
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.py")):
            if f.stem.startswith("_"):
                continue
            try:
                mod = _load(f, here=(d == mine))
            except Exception as e:                                        # noqa: BLE001
                if strict:
                    raise RuntimeError(f"{f}: will not load: {type(e).__name__}: {e}") from e
                continue
            decl = getattr(mod, "EXTRACT", None)
            if isinstance(decl, dict) and all(k in decl for k in REQUIRED):
                out[f.stem] = mod
            elif strict:
                raise RuntimeError(f"{f}: no EXTRACT declaring {REQUIRED}")
    return out


def for_kind(kind):
    """[module] able to read this kind of upstream, in a stable order."""
    return [m for _n, m in sorted(discover().items()) if m.EXTRACT.get("reads") == kind]
