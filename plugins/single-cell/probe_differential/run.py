#!/usr/bin/env python3
"""Removal rate per arm of the design for every mask in the subject, on the stack's view: an .h5ad
(its obs read through h5py, never the matrix), or the identity-level `view.csv` of a stack whose
observations arrive in parts (harness W010), whose rows carry the identity and its `{sample}`.
G3: this is the instrument; the gate reads this answer and adds a threshold, it does not measure
again."""
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

import csv  # noqa: E402

run = protocol.Run.from_argv()
idc = run.inp.get("identity", {}).get("column", "barcode")
subject = run.inp.get("subject") or {}
masks = subject.get("masks") or {}
sample_key = run.keys.get("sample")


def _decode(x):
    return x.decode() if isinstance(x, bytes) else str(x)


def read_strings(node):
    """A string array however this anndata encoding wrote it: a dataset, a nullable-string
    group with `values`, or a categorical group whose `categories` may itself be a group."""
    import h5py
    if isinstance(node, h5py.Group):
        if "categories" in node and "codes" in node:
            cats = read_strings(node["categories"])
            return [cats[c] if c >= 0 else None for c in node["codes"][()]]
        if "values" in node:
            return [_decode(v) for v in node["values"][()]]
        return None
    return [_decode(v) for v in node[()]]


if str(run.data).endswith(".csv"):
    with open(run.data, newline="", encoding="utf-8") as fh:
        view = csv.DictReader(fh)
        has_sample = bool(sample_key) and sample_key in (view.fieldnames or [])
        rows = list(view)
    ids = [r[idc] for r in rows]
    sample = [r[sample_key] for r in rows] if has_sample else None
else:
    import h5py
    with h5py.File(run.data, "r") as f:
        obs = f["obs"]
        idx = _decode(obs.attrs.get("_index", "_index"))
        ids = read_strings(obs[idx])
        sample = read_strings(obs[sample_key]) if sample_key and sample_key in obs else None

arm_of = {}
factor = run.params.get("factor")
if sample is not None and run.design:
    design = run.read_design()
    cols = [c for c in (design[0].keys() if design else []) if c != sample_key]
    factor = factor or (cols[0] if cols else None)
    unit_arm = {d[sample_key]: d.get(factor) for d in design} if factor else {}
    for i, s in zip(ids, sample):
        arm_of[i] = unit_arm.get(s)
answer = {"masks": {}, "max_ratio": None, "arms_known": bool(arm_of), "factor": factor}
for name, path in masks.items():
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    tot, rem = {}, {}
    for k in rows:
        arm = arm_of.get(k[idc])
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
                             "inert_reason": ("removal magnitude above one third: the ratio test "
                                              "cannot fail" if inert else "")}
    if ratio is not None and (answer["max_ratio"] is None or ratio > answer["max_ratio"]):
        answer["max_ratio"] = ratio
run.answer(**answer)
sys.exit(run.finish(headline=f"measured {len(masks)} mask(s); max ratio {answer['max_ratio']}"))
