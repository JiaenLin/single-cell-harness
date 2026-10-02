#!/usr/bin/env python3
"""What the data says it is, beside what the stack declares it is (harness ADR-0027).

The declared axes arrive in `profile_context`, written once when the stack was initialised. The
measured ones come from the object's feature table, read through h5py - the matrix is never
opened. G3: this is the instrument; `gate_axes_declared` adds the verdict and measures nothing.

WHY. The second cohort found three tools that took an axis without checking it against the data:
an assay defaulted to the first cohort's, a species string used only as a filter, an organism
"taken as declared". Each would have run a human cohort as the first cohort's mouse and said
nothing. A species is in the gene identifiers; asking costs one pass over the feature table.
"""
import importlib.util
import os
import re
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

import h5py  # noqa: E402

#: Ensembl gene-identifier prefixes, LONGEST FIRST: `ENSGALG` is chicken and starts with `ENSG`.
ENSEMBL = sorted({"ENSG": "homo_sapiens", "ENSMUSG": "mus_musculus", "ENSRNOG": "rattus_norvegicus",
                  "ENSDARG": "danio_rerio", "ENSMMUG": "macaca_mulatta", "ENSGALG": "gallus_gallus",
                  "ENSSSCG": "sus_scrofa", "ENSBTAG": "bos_taurus"}.items(), key=lambda kv: -len(kv[0]))
#: The symbol convention each species writes in - a hint, never a measurement.
CONVENTION = {"homo_sapiens": "upper", "macaca_mulatta": "upper", "sus_scrofa": "upper",
              "bos_taurus": "upper", "mus_musculus": "title", "rattus_norvegicus": "title",
              "danio_rerio": "lower", "gallus_gallus": "upper"}
_ID = re.compile(r"^(ENS[A-Z]*G)\d{6,}")
DECISIVE = 0.9


def _decode(x):
    return x.decode() if isinstance(x, bytes) else str(x)


def read_strings(node):
    """A string array however this anndata encoding wrote it (as probe_differential reads obs)."""
    if isinstance(node, h5py.Group):
        if "categories" in node and "codes" in node:
            cats = read_strings(node["categories"])
            return [cats[c] if c >= 0 else None for c in node["codes"][()]]
        if "values" in node:
            return [_decode(v) for v in node["values"][()]]
        return None
    if node.dtype.kind in ("S", "O", "U"):
        return [_decode(v) for v in node[()]]
    return None


run = protocol.Run.from_argv()
declared = {str(k): str(v) for k, v in (run.inp.get("profile_context") or {}).items()}

columns = {}
with h5py.File(run.data, "r") as f:
    var = f["var"]
    idx = _decode(var.attrs.get("_index", "_index"))
    for name in var.keys():
        vals = read_strings(var[name])
        if vals is not None:
            columns["index" if name == idx else name] = vals

# SPECIES FROM IDENTIFIERS: the column whose values are most often Ensembl gene identifiers.
best = None
for name, vals in columns.items():
    hits = {}
    for v in vals:
        m = _ID.match(v or "")
        if m:
            sp = next((s for p, s in ENSEMBL if m.group(1).startswith(p)), None)
            hits[sp] = hits.get(sp, 0) + 1
    n = sum(hits.values())
    if n and (best is None or n > best[1]):
        best = (name, n, hits, len(vals))
species = {"measured": None, "basis": "no Ensembl gene identifiers in the feature table", "evidence": {}}
if best:
    name, n, hits, total = best
    top, k = max(hits.items(), key=lambda kv: kv[1])
    share = k / n
    species["evidence"] = {"column": name, "identifiers": n, "features": total,
                           "by_species": {str(s): c for s, c in sorted(hits.items(), key=lambda kv: -kv[1])}}
    if top and share >= DECISIVE:
        species.update(measured=top, basis=f"{k:,} of {n:,} Ensembl identifiers in var[{name!r}] are {top}")
    else:
        species["basis"] = (f"identifiers in var[{name!r}] are mixed ({share:.0%} {top}) - a "
                            f"multi-species reference, or no single species")

# THE SYMBOL CONVENTION: a hint, reported as one.
symbols = columns.get("index") or []
case = {"upper": 0, "title": 0, "lower": 0}
mito = {"MT-": 0, "mt-": 0}
for s in symbols:
    if not s or _ID.match(s):
        continue
    if s.startswith("MT-"):
        mito["MT-"] += 1
    elif s.lower().startswith("mt-"):
        mito["mt-"] += 1
    core = re.sub(r"[^A-Za-z]", "", s)
    if len(core) < 3:
        continue
    if core.isupper():
        case["upper"] += 1
    elif core[0].isupper() and core[1:].islower():
        case["title"] += 1
    elif core.islower():
        case["lower"] += 1
tot = sum(case.values())
reads_as = max(case, key=case.get) if tot and max(case.values()) / tot >= 0.6 else ("mixed" if tot else None)
convention = {"reads_as": reads_as, "counts": case, "mitochondrial": mito,
              "expected_for_declared": CONVENTION.get(declared.get("species", ""))}

answer = {
    "declared": declared,
    "species": species,
    "convention": convention,
    "assay": {"declared": declared.get("assay"), "measured": None,
              "basis": "a count matrix carries no intronic fraction; whether it came from cells or "
                       "nuclei is the experiment's to declare, and this probe does not guess it"},
}
run.answer(**answer)
sys.exit(run.finish(headline=f"species measured {species['measured'] or 'not decisively'}"
                             f" (declared {declared.get('species') or 'nothing'}); symbols read {reads_as}"))
