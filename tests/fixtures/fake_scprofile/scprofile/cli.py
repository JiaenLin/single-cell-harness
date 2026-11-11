"""A stand-in for scProfile's CLI (`python -m scprofile.cli`), for tests that drive `prof@scprofile`
through `sch` without anndata, pydeseq2, pertpy or any plugin environment.

It honours the parts of scProfile's contract the adapter relies on, and nothing more:

    doctor      one line per declared environment; exit 0 (1 in mode doctor_fail)
    run         parsed with the flags scProfile's own parser declares for it (0.1.0, 6f970e5), so a
                flag scProfile does not have fails here as it would there

`run` keeps scProfile's status contract in `--out`: `STATUS.json` written first as `partial` with
`sys.argv`, `RUNNING.txt`, then the outcome with its products and `SEALED.txt` or `FAILED.txt`. For
each plugin named in `--kernel` it writes `kernels/<plugin>/out.json` and one table,
`kernels/<plugin>/tables/<plugin>_by_population.csv` (copied to `tables/`, as scProfile places a
plugin's tables beside its object): a count of observations per label level and
declared control, read from the object - a fixed pattern of the input, never an analysis. Then
`objects/<--object-name>`: the input copied byte for byte, plus an `uns/scprofile` group, and in mode
`merge` one obs column and one obsm entry (`report.json` `merged` names them, as scProfile's does).
`report.json` carries `ran`, `skipped`, `merged`, `object`, `design`, `reused` and `state_version`.
The plugin names are the caller's; none is known here.

Environment:
    FAKE_SCPROFILE_LOG              append {"argv", "argv0", "cwd", "pythonpath"} per call
    FAKE_SCPROFILE_MODE             ok (default) | refuse | fail | unsealed | other_argv | skip (the last
                                    plugin of --kernel is skipped with a reason) | merge | doctor_fail
    FAKE_SCPROFILE_STATE_VERSION    what STATUS.json and report.json record (default 1)
"""
import argparse
import csv
import json
import os
import shutil
import socket
import sys
import time
from pathlib import Path

MODE = os.environ.get("FAKE_SCPROFILE_MODE", "ok")
STATE_VERSION = int(os.environ.get("FAKE_SCPROFILE_STATE_VERSION", "1"))
VERSION, COMMIT = "0.0.0-fake", "f" * 40
OWN = ("kernels", "report", "tables", "objects")


def log_call():
    path = os.environ.get("FAKE_SCPROFILE_LOG")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"argv": sys.argv[1:], "argv0": sys.argv[0], "cwd": os.getcwd(),
                                 "pythonpath": os.environ.get("PYTHONPATH")}) + "\n")


def _products(out):
    res = []
    for p in sorted(out.iterdir()):
        if p.is_file():
            cand = [p]
        elif p.is_dir() and p.name in OWN:
            cand = sorted(q for q in p.rglob("*") if q.is_file())
        else:
            cand = []
        for q in cand:
            if q.suffix in (".json", ".csv", ".h5ad", ".html", ".md") and not q.name.startswith(
                    ("STATUS", "RUNNING", "SEALED", "FAILED")):
                res.append({"path": str(q.relative_to(out)), "bytes": q.stat().st_size})
    return res


def _labels(h5ad, key):
    """The label column's values, as text, from an obs categorical or string array."""
    import h5py
    with h5py.File(h5ad, "r") as f:
        node = f["obs"][key]
        if isinstance(node, h5py.Group):
            cats = [c.decode() if isinstance(c, bytes) else str(c) for c in node["categories"][()]]
            return [cats[int(i)] if int(i) >= 0 else None for i in node["codes"][()]]
        return [v.decode() if isinstance(v, bytes) else str(v) for v in node[()]]


def _merge(obj, n):
    import h5py
    import numpy as np
    with h5py.File(obj, "a") as f:
        g = f["obs"]
        d = g.create_dataset("phase", data=np.array(["G1" if i % 3 else "S" for i in range(n)],
                                                    dtype=object), dtype=h5py.string_dtype())
        d.attrs["encoding-type"], d.attrs["encoding-version"] = "string-array", "0.2.0"
        g.attrs["column-order"] = list(g.attrs["column-order"]) + ["phase"]
        m = f.require_group("obsm")
        s = m.create_dataset("X_fake", data=np.arange(n * 2, dtype="float32").reshape(n, 2))
        s.attrs["encoding-type"], s.attrs["encoding-version"] = "array", "0.2.0"


def run(a):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    argv = list(sys.argv)
    if MODE == "other_argv":
        argv = argv[:1] + ["run", "--h5ad", "someone_else.h5ad"]
    rec = {"contract": "1.0", "tool": "scprofile", "command": "run", "version": VERSION,
           "commit": COMMIT, "state_version": STATE_VERSION, "status": "partial", "headline": "started",
           "argv": argv, "products": [], "refusal": None}
    (out / "STATUS.json").write_text(json.dumps(rec, indent=1) + "\n")
    (out / "RUNNING.txt").write_text("started\n")

    def finish(status, rc, headline, refusal=None, seal=True):
        rec.update({"status": status, "headline": headline, "exit": rc, "refusal": refusal,
                    "products": _products(out)})
        (out / "STATUS.json").write_text(json.dumps(rec, indent=1) + "\n")
        if seal:
            name = "SEALED.txt" if status == "ok" and rc == 0 else "FAILED.txt"
            (out / name).write_text(f"exit={rc}\nstatus={status}\nhost={socket.gethostname()}\n")
            (out / "RUNNING.txt").unlink()
        return rc

    if MODE == "refuse":
        why = {"reason": "the design table has no column the run's --control names",
               "fix": "declare --control <factor>=<level> with a factor of the design"}
        print(f"scprofile: {why['reason']}", file=sys.stderr)
        return finish("refused", 2, why["reason"], refusal=why)
    if MODE == "fail":
        return finish("failed", 1, "run returned 1: a plugin crashed")
    if a.sample_key:                     # the real scProfile refuses here (harness W042 fix 1, E)
        import h5py
        with h5py.File(a.h5ad, "r") as f:
            have = sorted(k for k in f["obs"].keys() if not k.startswith("_"))
        if a.sample_key not in have:
            why = {"reason": f"--sample-key {a.sample_key!r} is not present in the object's obs "
                             f"(columns: {', '.join(have)})",
                   "fix": "name the object's column for each sample, or carry it into the object"}
            print(f"REFUSE - {why['reason']}", file=sys.stderr)
            return finish("refused", 2, why["reason"], refusal=why)
    plugins = [k for k in (a.kernel or "").split(",") if k]
    skipped = []
    if MODE == "skip" and plugins:
        skipped.append({"kernel": plugins[-1], "why": ["the design admits no contrast for it"]})
        plugins = plugins[:-1]
    labels = _labels(a.h5ad, a.label_key) if a.label_key else []
    controls = list(a.control or []) or ["(recommended)"]
    for k in plugins:
        d = out / "kernels" / k
        (d / "tables").mkdir(parents=True, exist_ok=True)
        with open(d / "tables" / f"{k}_by_population.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(["population", "control", "n"])
            for lv in sorted({x for x in labels if x is not None}):
                for c in controls:
                    w.writerow([lv, c, sum(1 for x in labels if x == lv)])
        (d / "out.json").write_text(json.dumps({"status": "ok", "kernel": k}) + "\n")
        # scProfile copies a plugin's tables beside its object, at the run's top level
        (out / "tables").mkdir(exist_ok=True)
        shutil.copyfile(d / "tables" / f"{k}_by_population.csv", out / "tables" / f"{k}_by_population.csv")
    obj, merged = None, {}
    if plugins:
        obj = out / "objects" / a.object_name
        obj.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(a.h5ad, obj)
        if MODE == "merge":
            _merge(obj, len(labels))
            merged[plugins[0]] = {"obs": ["phase"], "obsm": ["X_fake"], "layers": []}
        for k in plugins[1 if MODE == "merge" else 0:]:
            merged[k] = {"obs": [], "obsm": [], "layers": []}
    design = {}
    if a.design:
        with open(a.design, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        key = a.sample_key or (list(rows[0])[0] if rows else "sample")
        design = {r[key]: {f: v for f, v in r.items() if f != key} for r in rows}
    report = {"version": VERSION, "tool_commit": COMMIT, "state_version": STATE_VERSION,
              "input": str(a.h5ad), "ran": plugins, "skipped": skipped, "merged": merged,
              "reused": [], "design": design, "object": str(obj) if obj else None,
              "describe": {"assay": a.assay, "organism": a.organism}}
    (out / "report.json").write_text(json.dumps(report, indent=1) + "\n")
    (out / "RUN_CARD.json").write_text(json.dumps({"ran": plugins}) + "\n")
    if MODE == "unsealed":
        return finish("ok", 0, "kernels ran, results merged, report written", seal=False)
    return finish("ok", 0, "kernels ran, results merged, report written")


def parser():
    ap = argparse.ArgumentParser(prog="scprofile")
    sub = ap.add_subparsers(dest="cmd")
    d = sub.add_parser("doctor")
    d.add_argument("--prefix")
    d.add_argument("--references")
    d.add_argument("--organism")
    r = sub.add_parser("run")
    r.add_argument("--control", action="append")
    r.add_argument("--covariate", action="append")
    r.add_argument("--figures-for", default="")
    r.add_argument("--section")
    r.add_argument("--no-cache", action="store_true")
    r.add_argument("--reuse-from")
    r.add_argument("--reuse-min-grade", choices=("full", "provisional", "retrospective"))
    r.add_argument("--unit-by", choices=("group", "sample", "both"), default="both")
    r.add_argument("--resume", action="store_true")
    r.add_argument("--force-all", action="store_true")
    r.add_argument("--h5ad", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--kernel")
    r.add_argument("--all", action="store_true")
    for f in ("prefix", "references", "label-key", "compartment-key", "sample-key", "batch-key",
              "counts-layer", "lognorm-layer", "embedding", "layout", "sentinels", "organism", "assay"):
        r.add_argument(f"--{f}")
    r.add_argument("--factor", action="append")
    r.add_argument("--design")
    r.add_argument("--params")
    r.add_argument("--cores", type=int)
    r.add_argument("--timeout", type=int)
    r.add_argument("--no-validate", action="store_true")
    r.add_argument("--search")
    r.add_argument("--object-name", default="cohort_profiled.h5ad")
    r.add_argument("--allow")
    r.add_argument("--force", action="store_true")
    return ap


def main():
    log_call()
    a = parser().parse_args()
    if a.cmd == "doctor":
        print(f"scprofile doctor (stand-in): prefix {a.prefix or '(none)'}")
        return 1 if MODE == "doctor_fail" else 0
    if a.cmd == "run":
        return run(a)
    return 2


if __name__ == "__main__":
    sys.exit(main())
