#!/usr/bin/env python3
"""Companion: the layer is embeddings, graphs and columns over every observation, and nothing else.

Two relationships this plugin owns, asserted on the run that is mounted:
  - an integration removes nothing: the layer carries no mask, and no observation is set aside by it.
    Cells scIntegrate withholds from the fit stay in the object with NaN in every embedding;
  - every column, embedding and graph of the layer covers every observation the stack holds, once
    each. An embedding or a graph is bound to its observations by the identity file beside it
    (`barcodes.txt`), and its rows are those identities: one short of the stack's count means an
    observation lost between the joint object and scIntegrate's, and the layer would not be the
    stage's integration of the cohort the stack declares.
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
CARRIED = ("embedding", "graph")


def _rows(path, slot):
    """(rows, columns) of one embedding (.npy) or graph (.npz, compressed sparse), from its header."""
    import numpy as np
    if slot == "embedding":
        shape = np.load(path, mmap_mode="r").shape
        return int(shape[0]), (int(shape[1]) if len(shape) > 1 else 1)
    with np.load(path) as z:
        n, m = (int(x) for x in z["shape"])
        if len(z["indptr"]) - 1 != (n if str(z["format"]) == "csr" else m):
            raise AssertionError(f"{Path(path).name}: indptr does not match its shape {n} x {m}")
        return n, m


def register(inv):
    @inv.check("the layer removes nothing: no mask, no observation set aside")
    def _(run):
        masks = [c["name"] for c in run.contributions() if c["slot"] == "mask"]
        if masks or run.masked_observations():
            inv.fail(f"an integration contributed mask(s) {masks} and set aside "
                     f"{len(run.masked_observations())} observation(s)")

    @inv.check("every column, embedding and graph of the layer covers every observation the stack holds")
    def _(run):
        n = run.observation_count()
        short = [(c["name"], c["coverage"]) for c in run.contributions()
                 if c["slot"] == "column" and c["coverage"] != n]
        for c in run.contributions():
            if c["slot"] not in CARRIED:
                continue
            ids_file = Path(c["path"]).parent / IDENTITIES
            if not ids_file.is_file():
                inv.fail(f"{c['slot']}/{c['name']} has no {IDENTITIES} beside it: nothing binds its rows "
                         f"to observations")
            ids = ids_file.read_text(encoding="utf-8").split("\n")[:-1]
            rows, cols = _rows(c["path"], c["slot"])
            if len(set(ids)) != n or len(ids) != n or rows != n or (c["slot"] == "graph" and cols != n):
                short.append((f"{c['slot']}/{c['name']}", min(len(set(ids)), rows)))
        if short:
            inv.fail(f"{len(short)} entr{'y' if len(short) == 1 else 'ies'} of the layer cover other than "
                     f"the stack's {n:,} observations: " + "; ".join(f"{name} {cov:,}" for name, cov in short[:5])
                     + " - scIntegrate's object lost or repeated observations")


if __name__ == "__main__":
    sys.exit(protocol.companion(register))
