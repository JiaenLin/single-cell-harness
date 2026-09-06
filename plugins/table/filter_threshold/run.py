#!/usr/bin/env python3
"""Mask rows below a floor on the {value} column. Contributes a WHOLE mask and a removal record."""
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
run = protocol.Run.from_argv()
value_col = run.keys.get("value")
if not value_col:
    sys.exit(run.refuse("no {value} key resolved", fix="declare keys.value in stack.yml"))
floor = float(run.params.get("min", 0))
idc = run.inp.get("identity", {}).get("column", "id")
rows = run.read_csv(run.data)
keep, removed = {}, []
for r in rows:
    i = r[idc]
    try:
        v = float(r[value_col])
    except (TypeError, ValueError):
        v = float("nan")
    k = v >= floor
    keep[i] = k
    if not k:
        removed.append([i, "below_floor", r[value_col]])
run.mask("threshold", keep, reason=f"{value_col} < {floor}", id_field=idc)
run.table("removal_record", removed, [idc, "criterion", "value"])
run.number("n_removed", len(removed))
run.number("n_kept", len(rows) - len(removed))
run.caveat(f"floor {floor} was declared, not derived")
sys.exit(run.finish(headline=f"masked {len(removed)} of {len(rows)} rows below {value_col} = {floor}"))
