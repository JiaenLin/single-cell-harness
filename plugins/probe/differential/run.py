#!/usr/bin/env python3
"""Removal rate per arm of the design for every mask in the subject. G3: this is the instrument;
the gate reads this answer and adds a threshold, it does not measure again."""
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
subject = run.inp.get("subject") or {}
masks = subject.get("masks") or {}
group_key = run.keys.get("group")
unit_key = run.keys.get("unit")
rows = run.read_csv(run.data)
arm_of = {}
if group_key and any(group_key in r for r in rows[:1]):
    for r in rows:
        arm_of[r[idc]] = r[group_key]
elif unit_key and run.design:
    design = run.read_design()
    cols = [c for c in (design[0].keys() if design else []) if c != unit_key]
    factor = cols[0] if cols else None
    unit_arm = {d[unit_key]: d.get(factor) for d in design} if factor else {}
    for r in rows:
        arm_of[r[idc]] = unit_arm.get(r.get(unit_key))
answer = {"masks": {}, "max_ratio": None, "arms_known": bool(arm_of)}
if not masks:
    run.answer(**answer, note="no masks in subject")
    sys.exit(run.finish(headline="nothing to measure"))
for name, path in masks.items():
    keep = run.read_csv(path)
    tot, rem = {}, {}
    for k in keep:
        i = k[idc]
        arm = arm_of.get(i)
        if arm is None:
            continue
        tot[arm] = tot.get(arm, 0) + 1
        if k["keep"] not in ("1", "true", "True"):
            rem[arm] = rem.get(arm, 0) + 1
    rates = {a: (rem.get(a, 0) / tot[a] if tot[a] else None) for a in tot}
    vals = [v for v in rates.values() if v is not None]
    overall = sum(rem.values()) / max(sum(tot.values()), 1)
    ratio = None
    if vals and min(vals) > 0:
        ratio = max(vals) / min(vals)
    elif vals and max(vals) > 0:
        ratio = float("inf")
    inert = overall > 1 / 3
    answer["masks"][name] = {"rates": rates, "removed": rem, "total": tot, "ratio": ratio,
                             "overall": overall, "inert": inert,
                             "inert_reason": ("removal magnitude above one third: a 3x arm ratio "
                                              "cannot occur, so this test cannot fail" if inert else "")}
    if ratio is not None and (answer["max_ratio"] is None or ratio > answer["max_ratio"]):
        answer["max_ratio"] = ratio
run.answer(**answer)
sys.exit(run.finish(headline=f"measured {len(masks)} mask(s); max ratio {answer['max_ratio']}"))
