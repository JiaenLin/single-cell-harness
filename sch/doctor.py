"""`sch doctor --architecture` — what ARCHITECTURE.md §8 says is checkable statically.

    L1  no import from a higher layer          (AST over sch/)
    L2  no domain term in core/ or registry/   (terms from every shipped profile)
    L3  the kernel imports no plugin module    (nothing under sch/ imports from plugins/)
    C2  every plugin dependency is declared     (plugin dirs: inject/needs present)
    C4  the boundary carries JSON only          (protocol.py writes json; no pickle)
    D2  nothing opens an observation path for writing   (grep open(..., "w") on observations)
    D6  every contributing plugin declares state_version (validator rule 12 over plugins/)
    G1  every gate resolves to a plugin         (profile required gates exist under plugins/)
    G3  every gate names a probe that exists
    G4  every gate declares an escape, verdicts within the three
    X1  the version comparison reads the major only (registry.admit)

`sch doctor --runtime <stack>` runs the kernel companions over an existing stack's stream.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

from .profile import known_profiles, load_profile

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
LAYER = {"core": 1, "registry": 2, "services": 3, "profile": 2.5, "stack": 3, "plugin": 4,
         "kernel": 4, "doctor": 4, "cli": 4, "conform": 4, "yamlish": 0}


def _layer_of(path: Path) -> float:
    rel = path.relative_to(ROOT)
    top = rel.parts[0].replace(".py", "")
    return LAYER.get(top, 4)


def _imports(path: Path) -> list:
    tree = ast.parse(path.read_text(), filename=str(path))
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if node.level:
                # relative: resolve against the file's package
                pkg = list(path.relative_to(ROOT).parts[:-1])
                base = pkg[: len(pkg) - node.level + 1] if node.level <= len(pkg) else []
                mod = ".".join(["sch"] + base + ([mod] if mod else []))
            out.append(mod)
    return out


def check_architecture() -> list:
    findings = []
    files = sorted(p for p in ROOT.rglob("*.py") if "__pycache__" not in p.parts)
    # L1, L3
    for f in files:
        mine = _layer_of(f)
        for imp in _imports(f):
            if imp.startswith("sch."):
                parts = imp.split(".")
                target = ROOT / parts[1]
                tl = LAYER.get(parts[1], 4)
                if tl > mine and not (mine == 2.5):
                    findings.append({"rule": "L1", "ok": False,
                                     "where": str(f.relative_to(REPO)),
                                     "message": f"imports {imp} (layer {tl}) from layer {mine}"})
            if imp.startswith("plugins") or ".plugins." in imp:
                findings.append({"rule": "L3", "ok": False, "where": str(f.relative_to(REPO)),
                                 "message": f"the kernel imports a plugin module: {imp}"})
    if not any(x["rule"] == "L1" for x in findings):
        findings.append({"rule": "L1", "ok": True, "message": "no import from a higher layer"})
    if not any(x["rule"] == "L3" for x in findings):
        findings.append({"rule": "L3", "ok": True, "message": "the kernel imports no plugin module"})
    # L2
    terms = set()
    for p in known_profiles():
        terms |= set(load_profile(p).domain_terms)
    bad = []
    for f in files:
        if _layer_of(f) > 2 and f.parent.name not in ("core", "registry"):
            continue
        if f.parent.name not in ("core", "registry"):
            continue
        src = f.read_text()
        for t in sorted(terms):
            for m in re.finditer(rf"\b{re.escape(t)}(?:s|es|al|ial|rial|rials|ed|ing)?\b", src, re.I):
                bad.append(f"{f.relative_to(REPO)}: {m.group(0)!r}")
    findings.append({"rule": "L2", "ok": not bad,
                     "message": "no domain term in core/ or registry/" if not bad else f"domain terms: {bad[:10]}"})
    # C4
    proto = (ROOT / "plugin" / "protocol.py").read_text()
    findings.append({"rule": "C4", "ok": "pickle" not in proto and "json" in proto,
                     "message": "the boundary is JSON (protocol.py)"})
    # D2
    ds = (ROOT / "services" / "dataset.py").read_text()
    writes_obs = re.search(r"open\(self\.observations,\s*[\"'][wa]", ds) is not None
    findings.append({"rule": "D2", "ok": not writes_obs,
                     "message": "the dataset service never opens observations for writing"})
    # X1
    reg = (ROOT / "registry" / "runtime.py").read_text()
    findings.append({"rule": "X1", "ok": "contract_major" in reg and "contract_minor" not in reg,
                     "message": "the registry compares the contract major only"})
    # plugins/: C2, D6, G1, G3, G4
    from .plugin.validate import validate
    from .registry.manifest import load_manifest, ManifestError
    plugin_dirs = [d for d in (REPO / "plugins").rglob("plugin.yml")]
    gates, probes, errs = [], set(), []
    for pf in plugin_dirs:
        d = pf.parent
        try:
            m = load_manifest(d)
        except ManifestError as e:
            errs.append(str(e))
            continue
        if m.cls == "gate":
            gates.append(m)
        if m.cls == "probe":
            probes.add(m.name)
        for p in validate(d):
            if p["level"] == "error":
                errs.append(f"{d.relative_to(REPO)}: [{p['rule']}] {p['message']}")
    findings.append({"rule": "C2/D6/G4", "ok": not errs,
                     "message": "every shipped plugin validates" if not errs else f"{errs[:8]}"})
    g3 = [g.name for g in gates if str(g.data.get("measures_with", "")).split("/")[-1] not in probes
          and str(g.data.get("measures_with", "")) not in probes]
    findings.append({"rule": "G3", "ok": not g3,
                     "message": "every gate names a probe that exists" if not g3 else f"gates naming no probe: {g3}"})
    required = set()
    for p in known_profiles():
        for slot, req in load_profile(p).required.items():
            required |= set((req.get("gates") or {}).keys())
    missing = sorted(g for g in required if g not in {x.name for x in gates})
    findings.append({"rule": "G1", "ok": not missing,
                     "message": "every profile-required gate resolves to a plugin" if not missing else f"missing gate plugins: {missing}"})
    return findings


def check_runtime(stack_dir) -> list:
    from .kernel import Stack
    from .services.invariant import InvariantFailure
    st = Stack.open(stack_dir)
    findings = []
    for name, fn in (("G2", st.inv.g2_escapes_paired), ("G4", st.inv.g4_verdicts_monotonic),
                     ("A1", lambda: st.inv.a1_no_undeclared_write(st.dataset))):
        try:
            fn()
            findings.append({"rule": name, "ok": True, "message": "held"})
        except InvariantFailure as e:
            findings.append({"rule": name, "ok": False, "message": str(e)})
    try:
        st.report()
        findings.append({"rule": "P2/A2", "ok": True, "message": "report renders; every number resolves"})
    except InvariantFailure as e:
        findings.append({"rule": "P2/A2", "ok": False, "message": str(e)})
    st.close()
    return findings


def format_findings(findings: list) -> str:
    lines = []
    for f in findings:
        lines.append(f"  {'ok  ' if f['ok'] else 'FAIL'} {f['rule']:<9} {f['message']}" +
                     (f"  ({f['where']})" if f.get("where") else ""))
    n = sum(1 for f in findings if not f["ok"])
    return "\n".join(lines) + f"\n{'architecture holds' if not n else f'{n} finding(s)'}"
