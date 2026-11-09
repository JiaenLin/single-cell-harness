#!/usr/bin/env python3
"""Companion: the layer is labels, over every observation, and nothing else.

Two relationships this plugin owns, asserted on the run that is mounted:
  - a labelling removes nothing: the layer carries no mask, and no observation is set aside by it;
  - every column of the layer covers every observation the stack holds. scAnno's chain is declared
    to remove nothing, and every library is labelled under one declaration. So a column short of the
    stack's count means an observation lost between a library and scAnno's object for it, or a
    library labelled differently from the rest. Either way the layer would not be the stage's labels
    for the cohort the stack declares.
"""
import importlib.util
import os
import sys
from pathlib import Path


def _protocol():
    """The stdlib-only protocol helper: where the kernel says it is, or a copy beside this file."""
    for c in (os.environ.get("SCH_PROTOCOL"), Path(__file__).with_name("protocol.py")):
        if c and Path(c).exists():
            spec = importlib.util.spec_from_file_location("sch_protocol", str(c))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    sys.exit("protocol.py not found; set SCH_PROTOCOL or copy sch/plugin/protocol.py beside run.py")


protocol = _protocol()


def register(inv):
    @inv.check("the layer removes nothing: no mask, no observation set aside")
    def _(run):
        masks = [c["name"] for c in run.contributions() if c["slot"] == "mask"]
        if masks or run.masked_observations():
            inv.fail(f"a labelling contributed mask(s) {masks} and set aside "
                     f"{len(run.masked_observations())} observation(s)")

    @inv.check("every column of the layer covers every observation the stack holds")
    def _(run):
        n = run.observation_count()
        short = [(c["name"], c["coverage"]) for c in run.contributions()
                 if c["slot"] == "column" and c["coverage"] != n]
        if short:
            inv.fail(f"{len(short)} column(s) of the layer cover fewer than the stack's {n:,} "
                     f"observations: " + "; ".join(f"{name} {cov:,}" for name, cov in short[:5])
                     + " - scAnno's objects lost observations, or labelled some libraries "
                       "differently from the rest")


if __name__ == "__main__":
    sys.exit(protocol.companion(register))
