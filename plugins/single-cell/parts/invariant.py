#!/usr/bin/env python3
"""Companion: the parts are the object's observations, every one, and the step removed nothing.

Two relationships this step owns, asserted on the run that is mounted:
  - splitting removes nothing: the run carries no mask, and no observation is set aside by it;
  - the parts hold every observation the stack holds, each once: their cells sum to the stack's
    count. A shortfall is an observation lost between the object and its library's part.
"""
import importlib.util
import json
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
    @inv.check("splitting removes nothing: no mask, no observation set aside")
    def _(run):
        masks = [c["name"] for c in run.contributions() if c["slot"] == "mask"]
        if masks or run.masked_observations():
            inv.fail(f"the step contributed mask(s) {masks} and set aside "
                     f"{len(run.masked_observations())} observation(s)")

    @inv.check("the parts hold every observation of the object, each once")
    def _(run):
        rec = json.loads((Path(run.out_dir) / "PARTS.json").read_text(encoding="utf-8"))
        cells = sum(p["cells"] for p in rec["parts"].values())
        if cells != run.observation_count() or cells != rec["n_obs"]:
            inv.fail(f"the parts hold {cells:,} observations; the stack holds "
                     f"{run.observation_count():,} and the object {rec['n_obs']:,}")


if __name__ == "__main__":
    sys.exit(protocol.companion(register))
