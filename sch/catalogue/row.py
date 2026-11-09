"""One catalogue row per plugin, in the terms of the Universal Plugin Format (ADR-0030).

THIS MODULE IS ADR-0030's MAPPING TABLE, EXECUTABLE. Each layout the family has - the harness's
`plugin.yml` directory, scProfile's one-file `PLUGIN` literal, the maker's layout (the one-file
shape after the maker), scProfile's legacy `kernel.yml` directory - is mapped field by field onto
ONE row, so an agent reads one vocabulary whatever the plugin was written in. A field a layout
cannot express is `not declared`, which is a statement about the declaration; a fact nothing here
can establish is `unknown`. Neither is ever filled in from a default.

RULE 2 IS A SHAPE HERE. Single cells are not single nuclei, so a row states which assays a plugin
supports - from its declaration, verbatim - or says `not declared`. It never assumes one. Where
the plugin's own code reads the run's assay, the lines are listed beside the answer as evidence;
they do not become a declaration.
"""
from __future__ import annotations

import re

NOT_DECLARED = "not declared"
UNKNOWN = "unknown"

#: A format is one of these. `maker` is the adopted Universal Plugin Format, complete; `one-file`
#: is the adopted layout not yet through the maker; the other two are legacy layouts, read through
#: the mapping until their plugins migrate.
FORMATS = ("maker", "one-file", "directory", "kernel-yml")

#: The maker's record of the upstream's exported functions (harness ADR-0026, `sch dev convert
#: inventory --record`): the companion only the maker writes.
MAKER_RECORD = ".signatures.json"


class Malformed(ValueError):
    """A field present but not in a shape this format allows. The caller names the file."""


# ----------------------------------------------------------------------------------- helpers
def at(spec, dotted):
    """The value at a dotted path, or None."""
    node = spec
    for part in str(dotted).split("."):
        if not isinstance(node, dict):
            return None
        node = node.get(part)
    return node


def _set(v) -> bool:
    """Is a field SET: present and saying something (not None, not empty, not blank)."""
    if v is None or v is False:
        return False
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, (list, tuple, dict)):
        return bool(v)
    return True


def _strings(v, field):
    if v is None:
        return []
    if isinstance(v, str):
        return [v]
    if isinstance(v, (list, tuple)):
        return [str(x) for x in v]
    raise Malformed(f"`{field}` is a {type(v).__name__}; a list of names is expected")


def _norm(name) -> str:
    return re.sub(r"[-_.]+", "-", str(name).strip().lower())


def assays_of(spec):
    """The assays a plugin declares it supports (the UPF's `assays`), or NOT_DECLARED.

    Verbatim, in declared order. A declaration that is present and malformed is refused rather
    than read as absent: an empty list, a bare string, a non-string member.
    """
    if "assays" not in spec:
        return NOT_DECLARED
    v = spec["assays"]
    if not isinstance(v, (list, tuple)) or not v:
        raise Malformed("`assays` must be a non-empty list of the assays the plugin supports "
                        "(the profile's `assay` axis, e.g. scrna, snrna); omit it and the row "
                        "reads `not declared`")
    if not all(isinstance(x, str) and x.strip() for x in v):
        raise Malformed("every entry of `assays` must be a non-empty string")
    return [str(x) for x in v]


# ------------------------------------------------------------------------------- provenance
_EQ = re.compile(r"^\s*===?\s*([^\s,;*<>=!~@]+)\s*$")
_RANGE = re.compile(r"[<>=!~^*,]")
_COMMIT = re.compile(r"^[0-9a-fA-F]{7,40}$")


def _exact_spec(spec_text):
    """The version a requirement pins EXACTLY (`==1.2.3`), or None for a range or a wildcard."""
    m = _EQ.match(str(spec_text))
    return m.group(1) if m else None


def _exact_version(v):
    """`wraps.version` is exact when it is a bare version: no operator, no wildcard, no range."""
    s = str(v).strip()
    if not s or _RANGE.search(s) or " " in s:
        return None
    return s.lstrip("v") if re.match(r"^v\d", s) else s


def _remote(entry):
    """(name, ref, how) for an R requirement: `owner/Pkg@ref`, `Pkg==1.2`, `Pkg@ref` or `Pkg`."""
    s = str(entry).strip()
    if "@" in s:
        left, ref = s.rsplit("@", 1)
        return left.rsplit("/", 1)[-1], ref, "@"
    if "==" in s:
        left, ref = s.split("==", 1)
        return left.rsplit("/", 1)[-1], ref, "=="
    return s.rsplit("/", 1)[-1], "", ""


def pin_of(tool, spec, lock=None):
    """(exact | NOT_DECLARED, where, declared_as) for the upstream a plugin wraps.

    EXACT MEANS ONE VERSION, IDENTIFIED. A bare `wraps.version`, a requirement `==X`, an R remote at a
    commit (`owner/Pkg@<sha>`), or a lock line `tool==X`. A range is honest about what the plugin
    was written against and says nothing about what ran (PLUGIN_FORMAT.md §9), so it is reported
    as what was declared, never as the version. A branch or tag ref (`@main`) moves and is a
    range by another name.
    """
    wraps = spec.get("wraps") if isinstance(spec.get("wraps"), dict) else {}
    declared = []
    v = wraps.get("version")
    if _set(v):
        exact = _exact_version(v)
        if exact:
            return exact, "wraps.version", str(v)
        declared.append(f"{v} (wraps.version)")
    if not _set(tool):
        return NOT_DECLARED, None, (declared[0] if declared else NOT_DECLARED)
    want = _norm(tool)
    req = spec.get("requires") if isinstance(spec.get("requires"), dict) else {}
    pk = req.get("packages") if isinstance(req.get("packages"), dict) else {}
    for name, rng in pk.items():
        if _norm(name) == want:
            exact = _exact_spec(rng)
            if exact:
                return exact, f"requires.packages.{name}", str(rng)
            declared.append(f"{rng} (requires.packages.{name})")
    for entry in (req.get("r") or []) if isinstance(req.get("r"), (list, tuple)) else []:
        name, ref, how = _remote(entry)
        if _norm(name) != want:
            continue
        if how == "@" and _COMMIT.match(ref):
            return ref, "requires.r", str(entry)
        if how == "==" and _exact_spec("==" + ref):
            return ref, "requires.r", str(entry)
        declared.append(f"{entry} (requires.r)")
    conda = req.get("conda") if isinstance(req.get("conda"), dict) else {}
    for name, rng in conda.items():
        if _norm(name) == want:
            exact = _exact_spec(rng)
            if exact:
                return exact, f"requires.conda.{name}", str(rng)
            declared.append(f"{rng or 'any'} (requires.conda.{name})")
    # `==` ONLY: conda's single `=` is a prefix match (`python=3.12` takes any 3.12.x), and
    # PLUGIN_FORMAT.md §11 pins every lock line with `==` for that reason.
    for line in lock or []:
        m = re.match(r"^\s*([A-Za-z0-9_.\-]+)\s*==\s*([^\s,;*<>=!~]+)\s*$", str(line))
        if m and _norm(m.group(1)) == want:
            return m.group(2), "lock.yml", str(line)
    return NOT_DECLARED, None, (declared[0] if declared else NOT_DECLARED)


def doi_of(spec):
    """`wraps.doi`, verbatim (a string, or a list for several papers), or NOT_DECLARED.

    Only the field counts. A DOI inside the free-text `cite` is a citation somebody can read,
    not a declaration a catalogue can check, and reading one out of prose is a guess."""
    wraps = spec.get("wraps") if isinstance(spec.get("wraps"), dict) else {}
    if "doi" not in wraps:
        return NOT_DECLARED
    v = wraps["doi"]
    if isinstance(v, str) and v.strip():
        return v.strip()
    if isinstance(v, (list, tuple)) and v and all(isinstance(x, str) and x.strip() for x in v):
        return [x.strip() for x in v]
    raise Malformed("`wraps.doi` must be a DOI string, or a list of them for several papers")


def provenance(spec, lock=None):
    wraps = spec.get("wraps") if isinstance(spec.get("wraps"), dict) else {}
    tool = wraps.get("tool")
    exact, where, declared_as = pin_of(tool, spec, lock)
    return {"upstream": str(tool) if _set(tool) else NOT_DECLARED,
            "version": exact,
            "version_from": where,
            "version_declared_as": declared_as if exact == NOT_DECLARED else str(declared_as),
            "doi": doi_of(spec),
            "cite": str(wraps.get("cite")) if _set(wraps.get("cite")) else NOT_DECLARED,
            "license": str(wraps.get("license")) if _set(wraps.get("license")) else NOT_DECLARED,
            "homepage": str(wraps.get("homepage")) if _set(wraps.get("homepage")) else NOT_DECLARED}


# --------------------------------------------------------------------------- one-file rows
def maker_format(spec, stem, companions, markers):
    """(format, evidence) for a one-file plugin, from the maker's own declaration.

    `maker` needs both halves, and each is the maker's word, not this module's: no field the
    maker's declaration marks as outstanding (`outstanding_if`, read from the checkout's
    DEVPOINTS.yaml) is set, and the record only the maker writes is beside the plugin. `markers`
    None means the maker's declaration could not be read, and then the answer is not `maker`.
    """
    record = f"{stem}{MAKER_RECORD}"
    has_record = record in {c.rsplit("/", 1)[-1] for c in companions}
    if markers is None:
        return "one-file", ["the maker's declaration (DEVPOINTS.yaml, a point living in this "
                            "plugin's directory, with `convert` stages) could not be read, so "
                            "whether it went through the maker is unknown"]
    set_ = [m for m in markers if _set(at(spec, m))]
    ev = [f"`{m}` is set: the maker marks this stage outstanding" for m in set_]
    if not has_record:
        ev.append(f"no {record}: the record of the upstream's functions only the maker writes")
    if ev:
        return "one-file", ev
    return "maker", [f"no outstanding marker of the maker is set ({', '.join(markers) or 'none declared'})",
                     f"{record} is beside it"]


def _capabilities(spec):
    """(required, optional) capability names a one-file declaration asks the host for."""
    inj = spec.get("inject")
    if inj is not None and not isinstance(inj, dict):
        raise Malformed("`inject` must be a mapping {required: [...], optional: [...]}")
    inj = inj or {}
    req = _strings(inj.get("required"), "inject.required")
    opt = _strings(inj.get("optional"), "inject.optional")
    needs = spec.get("needs")
    if needs is not None and not isinstance(needs, dict):
        raise Malformed("`needs` must be a mapping {obs, obsm, layers, kernels, design}")
    needs = needs or {}
    for role in ("obs", "obsm", "layers"):
        for x in _strings(needs.get(role), f"needs.{role}"):
            if x not in req:
                req.append(x)
    if needs.get("design") and "design" not in req:
        req.append("design")
    return req, opt


def _classify(names, vocab, kind):
    if vocab is None:
        return UNKNOWN
    return [n for n in names if (vocab.get(n) or {}).get("resolve") == kind]


def onefile_inputs(spec, vocab, assay_lines):
    req, opt = _capabilities(spec)
    needs = spec.get("needs") if isinstance(spec.get("needs"), dict) else {}
    layers = [{"layer": x, "from": "needs.layers"} for x in _strings(needs.get("layers"), "needs.layers")]
    sees = _strings(spec.get("sees"), "sees") if "sees" in spec else None
    for s in sees or []:
        m = re.match(r"^layers\[(.+)\]$", s.strip())
        if m and m.group(1) not in [x["layer"] for x in layers]:
            layers.append({"layer": m.group(1), "from": "sees"})
    if not layers and sees is None and "layers" not in needs:
        layers = NOT_DECLARED
    unknown = [] if vocab is None else [n for n in req + opt if n not in vocab]
    aware = spec.get("design_aware")
    d_req, d_opt = _classify(req, vocab, "design"), _classify(opt, vocab, "design")
    # SHOWN THE DESIGN = HANDED IT. A one-file plugin is given the design table exactly when it
    # asks the host for a design capability; its `sees` lists object slots, never the design.
    shown = UNKNOWN if vocab is None else bool(d_req or d_opt or "design" in (sees or []))
    return {
        "assays": assays_of(spec),
        "assay_read_at": assay_lines,
        "requires": req,
        "optional": opt,
        "design": {"required": d_req, "optional": d_opt,
                   "per_arm": bool(aware) if aware is not None else NOT_DECLARED,
                   "shown": shown},
        "layers": layers,
        "from_plugins": (UNKNOWN if vocab is None else
                         _classify(req, vocab, "derived") + _classify(opt, vocab, "derived")),
        "not_in_vocabulary": unknown,
    }


def onefile_row(spec, *, source, name, rel, fmt, evidence, companions, vocab, assay_lines, ran):
    prov = provenance(spec)
    return {
        "id": f"{source}:{name}",
        "name": name,
        "source": source,
        "path": rel,
        "format": fmt,
        "format_evidence": evidence,
        "companions": companions,
        "version": str(spec["version"]) if _set(spec.get("version")) else NOT_DECLARED,
        "question": {"summary": str(spec.get("summary") or NOT_DECLARED),
                     "when_to_use": str(spec.get("when_to_use") or NOT_DECLARED)},
        "inputs": onefile_inputs(spec, vocab, assay_lines),
        "outputs": {"provides": _strings(spec.get("provides"), "provides"),
                    "produces": _strings(spec.get("produces"), "produces")},
        "provenance": prov,
        "ran_on_cohort": ran[0],
        "ran_on_cohort_record": ran[1],
        "cannot_show": _strings(spec.get("cannot_show"), "cannot_show"),
    }


def onefile_details(spec):
    """What `show` adds: everything an agent needs to call it, still read from the declaration."""
    cfg = spec.get("config") if isinstance(spec.get("config"), dict) else {}
    rep = spec.get("report") if isinstance(spec.get("report"), dict) else {}
    figs = [f for f in (rep.get("figures") or []) if isinstance(f, dict)]
    refs = spec.get("references")
    up = spec.get("upstream") if isinstance(spec.get("upstream"), dict) else {}
    return {
        "api": spec.get("api", NOT_DECLARED),
        "state_version": spec.get("state_version", NOT_DECLARED),
        "class": "method (the one-file host runs methods only)",
        "parameters": {k: {"type": (v or {}).get("type", NOT_DECLARED),
                           "default": (v or {}).get("default", NOT_DECLARED),
                           "help": (v or {}).get("help", "")}
                       for k, v in cfg.items() if isinstance(v, dict) or v is None},
        "sees": _strings(spec.get("sees"), "sees") if "sees" in spec else NOT_DECLARED,
        # None and absent run the same way in the host (once over the cohort); only one of them
        # is a declaration.
        "per_unit": (spec["per_unit"] if spec.get("per_unit") else
                     "none: once over the cohort" if "per_unit" in spec else NOT_DECLARED),
        "also_cohort": bool(spec.get("also_cohort")) if "also_cohort" in spec else NOT_DECLARED,
        "executor": {"cost": spec.get("cost", NOT_DECLARED), "cores": spec.get("cores", NOT_DECLARED),
                     "memory_gb_per_100k": spec.get("memory_gb_per_100k", NOT_DECLARED),
                     "memory_gb_base": spec.get("memory_gb_base", NOT_DECLARED)},
        "references": sorted(refs) if isinstance(refs, dict) else NOT_DECLARED,
        "figures": [str(f.get("id")) for f in figs if f.get("id")],
        "upstream_docs": str(up.get("docs")) if _set(up.get("docs")) else NOT_DECLARED,
        "gotchas": len(up.get("gotchas") or []) if "gotchas" in up else NOT_DECLARED,
    }


# -------------------------------------------------------------------------- directory rows
def directory_inputs(data, layer_slots, assay_lines):
    needs = _strings(data.get("needs"), "needs")
    opt = _strings(data.get("optional"), "optional")
    src = _strings(data.get("sourceable"), "sourceable")
    sees = _strings(data.get("sees"), "sees") if "sees" in data else None
    if layer_slots is None:
        layers = UNKNOWN
    else:
        layers = []
        for field, vals in (("needs", needs), ("optional", opt), ("sourceable", src)):
            for v in vals:
                slot, _, item = v.partition("/")
                if slot in layer_slots and item:
                    layers.append({"layer": item, "from": field})
    return {
        "assays": assays_of(data),
        "assay_read_at": assay_lines,
        "requires": needs,
        "optional": opt + [s for s in src if s not in opt],
        # THE DIRECTORY CONTRACT HAS NO "REQUIRES A DESIGN TABLE". `sees: [design]` says the
        # plugin is SHOWN the design (§8, information asymmetry), which is not the same claim.
        "design": {"required": NOT_DECLARED, "optional": NOT_DECLARED,
                   "per_arm": NOT_DECLARED,
                   "shown": ("design" in sees) if sees is not None else NOT_DECLARED},
        "layers": layers,
        "from_plugins": [v for v in needs + opt if v.startswith("checkpoint:")],
        "services": _strings(data.get("inject"), "inject"),
        "not_in_vocabulary": [],
    }


def directory_row(data, *, source, rel, fmt, evidence, companions, layer_slots, assay_lines,
                  ran, lock=None):
    name = str(data.get("name") or "")
    family = str(data.get("profile") or "").split("/")[0]
    prov = provenance(data, lock)
    return {
        "id": f"{source}:{family}/{name}" if family else f"{source}:{name}",
        "name": name,
        "source": source,
        "path": rel,
        "format": fmt,
        "format_evidence": evidence,
        "companions": companions,
        "version": str(data["version"]) if _set(data.get("version")) else NOT_DECLARED,
        "question": {"summary": str(data.get("summary") or NOT_DECLARED),
                     "when_to_use": str(data.get("when_to_use") or NOT_DECLARED)},
        "inputs": directory_inputs(data, layer_slots, assay_lines),
        "outputs": {"provides": _strings(data.get("provides"), "provides"),
                    "produces": NOT_DECLARED},
        "provenance": prov,
        "ran_on_cohort": ran[0],
        "ran_on_cohort_record": ran[1],
        "cannot_show": _strings(data.get("cannot_show"), "cannot_show"),
    }


def directory_details(data):
    return {
        "profile": data.get("profile", NOT_DECLARED),
        "contract": data.get("contract", NOT_DECLARED),
        "class": data.get("class", "method (the format's default, PLUGIN_FORMAT.md §2)"),
        "layer": data.get("layer", NOT_DECLARED),
        "reversible": data.get("reversible", NOT_DECLARED),
        "state_version": data.get("state_version", NOT_DECLARED),
        "gates": data.get("gates", NOT_DECLARED),
        "measures_with": data.get("measures_with", NOT_DECLARED),
        "invariant": data.get("invariant") or (
            {"none": data["no_runtime_invariant"]} if data.get("no_runtime_invariant") else NOT_DECLARED),
        "sees": data.get("sees", NOT_DECLARED),
        "language": data.get("language", NOT_DECLARED),
        "entry": data.get("entry", NOT_DECLARED),
        "executor": data.get("executor", NOT_DECLARED),
    }
