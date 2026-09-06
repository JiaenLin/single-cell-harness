#!/usr/bin/env python3
import random
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
idc = run.inp.get("identity", {}).get("column", "id")
rng = random.Random(int(run.params.get("seed", 0)))
rows = run.read_csv(run.data)
run.column("regenerated", {r[idc]: round(rng.random(), 6) for r in rows}, id_field=idc)
sys.exit(run.finish(headline=f"regenerated {len(rows)} values from seed {run.params.get('seed', 0)}"))
