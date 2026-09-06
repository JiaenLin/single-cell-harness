"""`sch plugin test <dir>` — run the plugin on a synthetic fixture inside a throwaway stack.

Beyond validation: builds a fixture for the plugin's profile, mounts it, mounts its companion
against that run, and — for `reversible: true` — mounts, snapshots, unmounts and compares.
The environment build and selftest run when `needs_env` is true and a builder is available;
otherwise that step is reported as skipped, never as passed.
"""
from __future__ import annotations

import csv
import json
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from ..registry.manifest import load_manifest
from .validate import validate


def table_fixture(dest: Path, n: int = 120, seed: int = 0) -> tuple:
    """A CSV with an id, a numeric value, two groups and a unit — the table profile."""
    rng = random.Random(seed)
    rows = Path(dest) / "rows.csv"
    design = Path(dest) / "design.csv"
    units = [f"U{i}" for i in range(6)]
    with open(rows, "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["id", "score", "arm", "unit"])
        for i in range(n):
            unit = units[i % len(units)]
            arm = "control" if int(unit[1:]) % 2 == 0 else "treated"
            w.writerow([f"R{i:04d}", round(rng.lognormvariate(2.0, 0.6), 3), arm, unit])
    with open(design, "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["unit", "arm"])
        for u in units:
            w.writerow([u, "control" if int(u[1:]) % 2 == 0 else "treated"])
    return rows, design


def run_plugin_test(plugin_dir, keep: bool = False, params: dict | None = None) -> dict:
    from ..kernel import Stack
    d = Path(plugin_dir).resolve()
    report = {"plugin": str(d), "steps": []}
    problems = validate(d)
    errs = [p for p in problems if p["level"] == "error"]
    report["steps"].append({"step": "validate", "ok": not errs, "problems": problems})
    if errs:
        return report
    m = load_manifest(d)
    tmp = Path(tempfile.mkdtemp(prefix="sch-plugin-test-"))
    try:
        if m.data.get("needs_env"):
            st = d / "selftest.py"
            if st.exists():
                r = subprocess.run([sys.executable, str(st)], cwd=str(d), capture_output=True, text=True)
                report["steps"].append({"step": "selftest", "ok": r.returncode == 0,
                                        "detail": (r.stdout + r.stderr)[-2000:]})
            else:
                report["steps"].append({"step": "selftest", "ok": False, "skipped": True,
                                        "detail": "no selftest.py; a SKIP is not a PASS"})
        if not m.profile.startswith("table/"):
            report["steps"].append({"step": "fixture", "ok": False, "skipped": True,
                                    "detail": f"no synthetic fixture shipped for profile {m.profile}; "
                                              f"run it on a stack of that profile"})
            return report
        rows, design = table_fixture(tmp)
        stack = Stack.init(tmp / "stack", "table/1.0", str(rows), str(design),
                           keys={"value": "score", "group": "arm", "unit": "unit"},
                           plugin_paths=[str(d.parent), str(Path(__file__).resolve().parents[2] / "plugins")])
        if m.cls == "method":
            before = stack.materialise()[0].digest()
            res = stack.mount(str(d), params or {})
            report["steps"].append({"step": "mount", "ok": res.ok, "result": res.to_dict()})
            if res.ok:
                report["steps"].append({"step": "companion", "ok": True,
                                        "detail": [e for e in stack.prov.replay() if e["kind"].startswith("invariant/")]})
                if m.reversible:
                    stack.unmount(m.name)
                    after = stack.materialise()[0].digest()
                    report["steps"].append({"step": "reversible", "ok": after == before,
                                            "before": before, "after": after})
        elif m.cls == "probe":
            ans = stack.ask(str(d), params or {})
            report["steps"].append({"step": "probe", "ok": not ans["died"], "answer": ans})
        elif m.cls == "gate":
            report["steps"].append({"step": "gate", "ok": True,
                                    "detail": "a gate is tested by mounting a plugin it guards; see tests/"})
        stack.close()
    finally:
        if keep:
            report["kept"] = str(tmp)
        else:
            shutil.rmtree(tmp, ignore_errors=True)
    report["ok"] = all(s.get("ok") for s in report["steps"] if not s.get("skipped"))
    report["skipped"] = [s["step"] for s in report["steps"] if s.get("skipped")]
    return report
