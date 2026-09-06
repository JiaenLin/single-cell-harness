#!/usr/bin/env python3
"""Mask observations whose total {counts} is below a floor. A WHOLE mask, merged by identity."""
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

import anndata as ad
import numpy as np

run = protocol.Run.from_argv()
counts_key = run.keys.get("counts")
if not counts_key:
    sys.exit(run.refuse("no {counts} key resolved", fix="declare keys.counts in stack.yml"))
floor = float(run.params.get("min", 0))
idc = run.inp.get("identity", {}).get("column", "barcode")
a = ad.read_h5ad(run.data)
if counts_key in a.layers:
    M = a.layers[counts_key]
elif counts_key == "X":
    M = a.X
else:
    sys.exit(run.refuse(f"layer {counts_key!r} not in the object", fix="point keys.counts at an integer layer"))
tot = np.asarray(M.sum(axis=1)).ravel()
if not np.isfinite(tot).all():
    sys.exit(run.refuse("non-finite totals", fix="check the counts layer"))
ids = list(a.obs_names)
keep = {i: bool(t >= floor) for i, t in zip(ids, tot)}
removed = [[i, "below_floor", float(t)] for i, t in zip(ids, tot) if t < floor]
run.mask("count_floor", keep, reason=f"total {counts_key} < {floor}", id_field=idc)
run.table("removal_record", removed, [idc, "criterion", "total"])
run.number("n_removed", len(removed))
run.number("n_kept", len(ids) - len(removed))
run.wrapped("anndata", ad.__version__)
run.caveat(f"floor {floor} was declared, not derived from the depth distribution")
sys.exit(run.finish(headline=f"masked {len(removed)} of {len(ids)} observations below {floor} total {counts_key}"))
