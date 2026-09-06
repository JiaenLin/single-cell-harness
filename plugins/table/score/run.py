#!/usr/bin/env python3
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
idc = run.inp.get("identity", {}).get("column", "id")
rows = run.read_csv(run.data)
vals = []
for r in rows:
    try:
        vals.append((float(r[value_col]), r[idc]))
    except (TypeError, ValueError):
        pass
vals.sort()
n = max(len(vals), 1)
col = {}
rank = 0
prev = None
for i, (v, ident) in enumerate(vals):
    if v != prev:
        rank = i + 1
        prev = v
    col[ident] = round(rank / n, 6)
run.column("rank_fraction", col, id_field=idc)
med = sorted(v for v, _ in vals)[len(vals) // 2] if vals else None
run.number("median_value", med)
run.caveat(f"{len(rows) - len(vals)} rows had a non-numeric {value_col} and got no rank")
sys.exit(run.finish(headline=f"ranked {len(vals)} kept rows on {value_col}"))
