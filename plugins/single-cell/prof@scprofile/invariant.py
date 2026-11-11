"""Companion: the layer is tables, an object, and columns and embeddings over every observation.

Two relationships this plugin owns, asserted on the run that is mounted:
  - profiling removes nothing: the layer carries no mask, and no observation is set aside by it. A
    population scProfile could not test is a row its tables lack, never an observation removed;
  - every column and embedding of the layer - what scProfile merged into its object - covers every
    observation the stack holds, once each. An embedding is bound to its observations by the
    identity file beside it (`barcodes.txt`); one short of the stack's count means an observation lost
    between the integrated object and scProfile's, and the layer would not be over the stack.
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
IDENTITIES = "barcodes.txt"


def register(inv):
    @inv.check("the layer removes nothing: no mask, no observation set aside")
    def _(run):
        masks = [c["name"] for c in run.contributions() if c["slot"] == "mask"]
        if masks or run.masked_observations():
            inv.fail(f"profiling contributed mask(s) {masks} and set aside "
                     f"{len(run.masked_observations())} observation(s)")

    @inv.check("every column and embedding of the layer covers every observation the stack holds")
    def _(run):
        import numpy as np
        n = run.observation_count()
        short = [(f"column/{c['name']}", c["coverage"]) for c in run.contributions()
                 if c["slot"] == "column" and c["coverage"] != n]
        for c in run.contributions():
            if c["slot"] != "embedding":
                continue
            ids_file = Path(c["path"]).parent / IDENTITIES
            if not ids_file.is_file():
                inv.fail(f"embedding/{c['name']} has no {IDENTITIES} beside it: nothing binds its rows "
                         f"to observations")
            ids = ids_file.read_text(encoding="utf-8").split("\n")[:-1]
            rows = int(np.load(c["path"], mmap_mode="r").shape[0])
            if len(set(ids)) != n or len(ids) != n or rows != n:
                short.append((f"embedding/{c['name']}", min(len(set(ids)), rows)))
        if short:
            inv.fail(f"{len(short)} entr{'y' if len(short) == 1 else 'ies'} of the layer cover other than "
                     f"the stack's {n:,} observations: " + "; ".join(f"{name} {cov:,}" for name, cov in short[:5])
                     + " - scProfile's object lost or repeated observations")


if __name__ == "__main__":
    sys.exit(protocol.companion(register))
