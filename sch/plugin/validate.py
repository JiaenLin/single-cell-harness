"""`sch plugin validate <dir>` — the fifteen static checks of PLUGIN_FORMAT.md §12.

Every rule here has a deliberately broken plugin in tests/broken/ that trips it (ROADMAP Phase
2: "a validator rule with no plugin that trips it is a rule nobody has run").
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from .. import CONTRACT, yamlish
from ..profile import load_profile, ProfileError, known_profiles
from ..registry.manifest import (CLASSES, LAYERS, VERDICTS, REQUIRED, ManifestError,
                                 load_manifest, parse_capability)

README_SECTIONS = ("What it does", "Report surface", "Cost", "Known limitations")


def _p(problems, rule, level, msg):
    problems.append({"rule": rule, "level": level, "message": msg})


def validate(plugin_dir) -> list:
    d = Path(plugin_dir)
    problems: list = []
    # 1. parses; contract major supported; profile known
    try:
        m = load_manifest(d)
    except ManifestError as e:
        _p(problems, 1, "error", str(e))
        return problems
    data = m.data
    if m.contract_major is None:
        _p(problems, 1, "error", "contract missing or not a version")
    elif m.contract_major != int(CONTRACT.split(".")[0]):
        _p(problems, 1, "error", f"contract major {m.contract_major} unsupported (kernel {CONTRACT})")
    profile = None
    try:
        profile = load_profile(m.profile) if m.profile else None
        if profile and not profile.accepts(m.profile):
            _p(problems, 1, "error", f"profile {m.profile!r} not served by {profile.id}")
    except ProfileError as e:
        _p(problems, 1, "error", f"profile unknown: {e}; known {known_profiles()}")
    # 2. required fields; cannot_show non-empty; sees present
    for f in REQUIRED:
        if f not in data:
            _p(problems, 2, "error", f"required field missing: {f}")
    if "TODO" in yamlish.dumps(data):
        _p(problems, 2, "error", "manifest still contains TODO")
    cs = data.get("cannot_show")
    if not isinstance(cs, list) or not cs or not all(isinstance(x, str) and x.strip() for x in cs):
        _p(problems, 2, "error", "cannot_show must be a non-empty list of sentences")
    if "sees" in data and not isinstance(data.get("sees"), list):
        _p(problems, 2, "error", "sees must be a list (an empty list is a positive claim)")
    if m.cls not in CLASSES:
        _p(problems, 2, "error", f"class {m.cls!r} not in {CLASSES}")
    # 3. layer valid; a checkpoint declares rebuild_from
    if m.layer not in LAYERS:
        _p(problems, 3, "error", f"layer {m.layer!r} not in {LAYERS}")
    elif m.layer == "checkpoint":
        rb = data.get("rebuild_from") or {}
        if not isinstance(rb, dict) or not rb.get("inputs"):
            _p(problems, 3, "error", "a checkpoint must declare rebuild_from: {inputs: [...], params: [...]}")
    # 4. needs/provides well-formed under the grammar AND the profile vocabulary
    slots = set(profile.slots) if profile else set()
    for field_name in ("needs", "provides", "optional", "sourceable"):
        for raw in data.get(field_name) or []:
            try:
                c = parse_capability(raw)
            except ManifestError as e:
                _p(problems, 4, "error", f"{field_name}: {e}")
                continue
            if c.kind == "slot" and profile and c.slot not in slots and c.slot != "observations":
                _p(problems, 4, "error", f"{field_name}: slot {c.slot!r} is not in profile {profile.id} "
                                         f"({sorted(slots)})")
            if c.kind == "capability" and profile and c.raw not in profile.capabilities \
                    and field_name == "needs":
                _p(problems, 4, "warn", f"{field_name}: {c.raw} is not an alias the profile defines; "
                                        f"only a plugin declaring it verbatim can satisfy it")
    # 5. entry point exists and is executable (or runnable by the declared language)
    entry = m.entry_path()
    if m.cls not in ("companion",):
        if entry is None or not entry.exists():
            _p(problems, 5, "error", f"entry point {data.get('entry')!r} does not exist")
        elif not os.access(entry, os.R_OK):
            _p(problems, 5, "error", f"entry point {entry.name} is not readable")
    # 6. needs_env implies lock.yml and a selftest
    if data.get("needs_env"):
        if not (d / "lock.yml").exists():
            _p(problems, 6, "error", "needs_env: true but no lock.yml")
        if not any((d / f"selftest{ext}").exists() for ext in (".py", ".R", "")):
            _p(problems, 6, "error", "needs_env: true but no selftest")
    # 7. every lock dependency pinned with ==
    lock = d / "lock.yml"
    if lock.exists():
        try:
            ld = yamlish.load(lock) or {}
            for dep in _flatten_deps(ld.get("dependencies") or []):
                if dep.startswith("pip:") or dep in ("pip",):
                    continue
                if not re.match(r"^[A-Za-z0-9_.\-\[\]]+==[^=<>~!]+$", dep) and not re.match(r"^[A-Za-z0-9_.\-]+=[^=<>~!]+$", dep):
                    _p(problems, 7, "error", f"lock.yml: {dep!r} is not pinned with == (a lock with ranges is not a lock)")
        except yamlish.YamlError as e:
            _p(problems, 7, "error", f"lock.yml: {e}")
    # 8. wraps carries version, licence, citation
    w = data.get("wraps")
    if w is not None:
        for k in ("tool", "version", "license", "cite"):
            if not (w or {}).get(k):
                _p(problems, 8, "error", f"wraps.{k} missing")
    # 9. references.yml entries carry checksums
    refs = d / "references.yml"
    if refs.exists():
        try:
            rd = yamlish.load(refs) or {}
            entries = rd if isinstance(rd, list) else list((rd.get("references") or rd).values()) if isinstance(rd, dict) else []
            for e in entries:
                if not isinstance(e, dict) or not (e.get("sha256") or e.get("checksum")):
                    _p(problems, 9, "error", f"references.yml entry without checksum: {e}")
        except yamlish.YamlError as e:
            _p(problems, 9, "error", f"references.yml: {e}")
    # 10. the reversibility claim is consistent with the layer
    if m.layer == "checkpoint" and m.reversible:
        _p(problems, 10, "error", "a checkpoint cannot claim reversible: true — it is rebuilt, never unmounted")
    if m.cls in ("probe", "gate", "companion") and not m.reversible:
        _p(problems, 10, "error", f"a {m.cls} contributes nothing and must declare reversible: true")
    # 11. no hard-coded domain identifier where the profile defines a key
    if profile:
        # a key NAME is how a plugin asks for a column; only real column names are reserved
        reserved = set(profile.reserved_identifiers) - set(profile.keys)
        for field_name in ("needs", "provides", "optional"):
            for raw in data.get(field_name) or []:
                tail = re.sub(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}", "", raw.split("/", 1)[1] if "/" in raw else raw)
                for tok in re.split(r"[^A-Za-z0-9_]+", tail):
                    if tok in reserved:
                        _p(problems, 11, "error", f"{field_name}: {raw!r} names {tok!r}, a real identifier; "
                                                  f"use a key such as {{{_suggest_key(tok, profile)}}}")
        src = entry.read_text(errors="replace") if entry and entry.exists() and entry.suffix in (".py", ".R", "") else ""
        for tok in reserved:
            if re.search(rf"[\"']{re.escape(tok)}[\"']", src):
                _p(problems, 11, "error", f"{entry.name} hard-codes {tok!r}; resolve it from in.json keys")
    # 12. contributing plugin declares an integer state_version
    if m.contributes:
        sv = data.get("state_version")
        if not isinstance(sv, int) or isinstance(sv, bool):
            _p(problems, 12, "error", "a contributing plugin declares an integer state_version")
    # 13. a gate declares escape and only PASS REVIEW REFUSE
    if m.cls == "gate":
        if not data.get("escape"):
            _p(problems, 13, "error", "a gate declares an escape (never absent — a gate with no escape gets switched off)")
        if not data.get("measures_with"):
            _p(problems, 13, "error", "a gate names the probe it measures with (G3)")
        vs = data.get("verdict") or []
        bad = [v for v in vs if v not in VERDICTS]
        if bad or not vs:
            _p(problems, 13, "error", f"gate verdicts must be within {VERDICTS}; got {vs}")
    # 14. invariant names a file that exists, or no_runtime_invariant names a relationship
    inv, no_inv = data.get("invariant"), data.get("no_runtime_invariant")
    if m.cls in ("method", "executor", "storage"):
        if inv and no_inv:
            _p(problems, 14, "error", "declare invariant: OR no_runtime_invariant:, not both")
        elif inv:
            f = d / str(inv)
            if not f.exists():
                _p(problems, 14, "error", f"invariant {inv!r} does not exist")
            elif len(f.read_text(errors="replace").strip().splitlines()) < 3 or "check" not in f.read_text(errors="replace"):
                _p(problems, 14, "error", "an empty companion is decoration")
        elif no_inv:
            if not isinstance(no_inv, str) or len(no_inv.split()) < 6 or not re.search(
                    r"\b(between|every|each|matches|equals|count|record|order|conserv|same|one-to-one|pure|nothing observable)\b", no_inv, re.I):
                _p(problems, 14, "error", "no_runtime_invariant must give a reason naming a relationship (or its absence)")
        else:
            _p(problems, 14, "error", "declare invariant: <file> or no_runtime_invariant: <reason>")
    # 15. README with the four sections, none empty
    readme = d / "README.md"
    if not readme.exists():
        _p(problems, 15, "error", "README.md missing")
    else:
        text = readme.read_text(errors="replace")
        for sec in README_SECTIONS:
            body = _section(text, sec)
            if body is None:
                _p(problems, 15, "error", f"README.md: section '{sec}' missing")
            elif len(body.split()) < 8:
                _p(problems, 15, "error", f"README.md: section '{sec}' is empty or too thin")
    return problems


def _flatten_deps(deps):
    out = []
    for dep in deps:
        if isinstance(dep, dict):
            for k, v in dep.items():
                if isinstance(v, list):
                    out.extend(str(x) for x in v)
                else:
                    out.append(f"{k}:{v}")
        else:
            out.append(str(dep))
    return out


def _section(text: str, name: str):
    m = re.search(rf"^#+\s*{re.escape(name)}\s*$(.*?)(?=^#+\s|\Z)", text, re.M | re.S | re.I)
    return m.group(1).strip() if m else None


def _suggest_key(tok: str, profile) -> str:
    for k in profile.keys:
        if k in tok:
            return k
    return profile.keys[0] if profile.keys else "key"


def format_problems(problems: list) -> str:
    if not problems:
        return "valid: 15 checks, no problems"
    lines = []
    for p in sorted(problems, key=lambda x: (x["rule"], x["level"])):
        lines.append(f"  [{p['rule']:>2}] {p['level'].upper():<5} {p['message']}")
    errs = sum(1 for p in problems if p["level"] == "error")
    return f"{errs} error(s), {len(problems) - errs} warning(s)\n" + "\n".join(lines)
