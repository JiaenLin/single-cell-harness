#!/usr/bin/env python3
import os
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
artifact = run.params.get("artifact") or (run.inp.get("subject") or {}).get("out_dir")
inputs = run.params.get("inputs") or [run.data]
if not artifact or not Path(artifact).exists():
    sys.exit(run.refuse(f"artifact {artifact!r} does not exist", fix="pass params.artifact"))
a_m = max((os.path.getmtime(p) for p in Path(artifact).rglob("*") if p.is_file()), default=os.path.getmtime(artifact)) \
    if Path(artifact).is_dir() else os.path.getmtime(artifact)
newest = max(os.path.getmtime(p) for p in inputs)
run.answer(artifact=str(artifact), artifact_mtime=a_m, newest_input_mtime=newest, stale=a_m < newest)
sys.exit(run.finish(headline="stale" if a_m < newest else "fresh"))
