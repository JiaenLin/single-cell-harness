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
column = run.params.get("column") or run.keys.get("group")
by = run.params.get("by")
rows = run.read_csv(run.data)
if not rows or column not in rows[0]:
    sys.exit(run.refuse(f"column {column!r} not in the view", fix="pass params.column naming a column the view carries"))
counts = {}
for r in rows:
    g = r.get(by, "all") if by else "all"
    counts.setdefault(g, {})
    counts[g][r[column]] = counts[g].get(r[column], 0) + 1
shares = {g: {k: v / sum(c.values()) for k, v in c.items()} for g, c in counts.items()}
run.answer(column=column, by=by, counts=counts, shares=shares,
           denominator=f"rows kept in the view when the probe ran ({len(rows)})")
sys.exit(run.finish(headline=f"composition of {column} over {len(rows)} rows"))
