#!/usr/bin/env python3
"""A declared cohort axis, against what the `axes` probe measured (harness ADR-0027).

A gate is a probe plus a threshold plus a verdict; this one measures nothing. REFUSE where the
gene identifiers contradict the declared species - the case of a first cohort's value carried onto
a second, which is what every tool that took a species "as declared" would have done. REVIEW where
an axis is measurable and undeclared, where only the symbol convention disagrees, or where the
assay - which no count matrix can show - was never declared. The worst verdict over the axes is the
gate's, and every reason is kept.
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
run = protocol.Run.from_argv()
ans = run.probe_answer or {}
declared = ans.get("declared") or {}
sp = ans.get("species") or {}
conv = ans.get("convention") or {}
RANK = {"PASS": 0, "REVIEW": 1, "REFUSE": 2}
found = []

want, got = declared.get("species"), sp.get("measured")
if want and got and want != got:
    found.append(("REFUSE", f"species declared {want!r}, but {sp.get('basis')}"))
elif want and got:
    found.append(("PASS", f"species {want!r} agrees with {sp.get('basis')}"))
elif got:
    found.append(("REVIEW", f"species is undeclared and the data says {got!r} ({sp.get('basis')}): "
                            f"declare it - `sch init --context species={got}`"))
elif want and conv.get("expected_for_declared") and conv.get("reads_as") not in (None, "mixed") \
        and conv["reads_as"] != conv["expected_for_declared"]:
    found.append(("REVIEW", f"species declared {want!r}, whose symbols are written {conv['expected_for_declared']}"
                            f"-case, and these read {conv['reads_as']}-case - a convention, not proof, "
                            f"and no gene identifiers to settle it"))
elif not want:
    found.append(("REVIEW", "species is undeclared and the data cannot settle it: declare it"))

if not declared.get("assay"):
    found.append(("REVIEW", "assay is undeclared, and a count matrix cannot show whether it came from "
                            "cells or nuclei: declare it - `sch init --context assay=...`"))

verdict = max((v for v, _ in found), key=RANK.get, default="PASS")
reason = "; ".join(r for v, r in found if v == verdict) or "nothing declared contradicts the data"
run.answer(verdict=verdict, number=None, reason=reason, findings=[{"verdict": v, "reason": r} for v, r in found])
sys.exit(run.finish(headline=f"{verdict}: {reason}"))
