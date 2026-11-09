#!/usr/bin/env python3
"""A stand-in for `scqc_cli.py`, for tests that drive `qc@scqc` through `sch` without scanpy or R.

It honours the parts of scQC's contract the adapter reads, and nothing more, as scQC's own
`tests/fixtures/fake_rscript.py` stands in for its doublet detector:

    describe                  the declaration, as JSON (`state_version` is what the adapter checks)
    run --project P ...       the `run` subcommand's flags, parsed as scQC's parser declares them, so
                              a flag scQC does not have fails here as it would there

`run` writes scQC's layout under P: `results/<digest>/` with STATUS.json, SEALED.txt or FAILED.txt,
INPUTS.json, `tables/<sample>.percell.csv` (one row per barcode of each library's part, a
`fail_*` column per criterion, `removed`, `keep`), `tables/removal_ledger.csv` keyed
`<sample>|<barcode>`, `reports/report.json` and `objects/cohort.deliverable.h5ad`; plus
`results/INDEX.tsv` and the `latest` pointer, which nothing should read. The criteria fire on a
fixed pattern of each barcode's position, so every library of the same size removes the same
share. It scores nothing: a test using it checks the harness around scQC, never scQC.

Environment:
    FAKE_SCQC_LOG             append {"argv", "cwd"} as one JSON line per call
    FAKE_SCQC_MODE            ok (default) | refuse | fail | unsealed | disagree | short
    FAKE_SCQC_STATE_VERSION   what `describe` and STATUS.json report (default 1)
"""
import argparse
import csv
import hashlib
import json
import os
import sys
from pathlib import Path

MODE = os.environ.get("FAKE_SCQC_MODE", "ok")
STATE_VERSION = int(os.environ.get("FAKE_SCQC_STATE_VERSION", "1"))


def log_call():
    path = os.environ.get("FAKE_SCQC_LOG")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"argv": sys.argv[1:], "cwd": os.getcwd()}) + "\n")


def read_sheet(path):
    lines = [ln for ln in Path(path).read_text(encoding="utf-8").splitlines()
             if ln.strip() and not ln.lstrip().startswith("#")]
    delim = "\t" if lines[0].count("\t") > lines[0].count(",") else ","
    return list(csv.DictReader(lines, delimiter=delim))


def barcodes(part):
    import h5py
    with h5py.File(part, "r") as f:
        obs = f["obs"]
        idx = obs.attrs.get("_index", "_index")
        idx = idx.decode() if isinstance(idx, bytes) else str(idx)
        return [x.decode() if isinstance(x, bytes) else str(x) for x in obs[idx][()]]


def describe():
    print(json.dumps({"contract": "1.0", "name": "scqc", "version": "0.0.0-fake",
                      "state_version": STATE_VERSION, "layer": "stack", "reversible": True,
                      "sees": ["design"], "cannot_show": ["a stand-in shows nothing"]}))
    return 0


def run(a):
    project = Path(a.project)
    rows = read_sheet(a.samplesheet)
    if not Path(a.registry).is_file():
        print(f"scqc run: --registry {a.registry!r} is not a file", file=sys.stderr)
        return 2
    described = {"samplesheet": rows, "mode": a.mode,
                 "args": {k: v for k, v in sorted(vars(a).items()) if k not in ("project", "fn")}}
    digest = hashlib.sha256(json.dumps(described, sort_keys=True, default=str).encode()).hexdigest()[:12]
    res = project / "results" / digest
    for sub in ("tables", "reports", "objects"):
        (res / sub).mkdir(parents=True, exist_ok=True)
    (project / "work" / digest).mkdir(parents=True, exist_ok=True)
    (project / "logs" / digest).mkdir(parents=True, exist_ok=True)
    (res / "INPUTS.json").write_text(json.dumps({"digest": digest, "described": described},
                                                default=str, indent=1))
    (project / "results" / "INDEX.tsv").write_text(f"digest\tmode\n{digest}\t{a.mode}\n")
    latest = project / "results" / "latest"
    if not latest.exists():
        os.symlink(digest, latest, target_is_directory=True)
    status = {"contract": "1.0", "tool": "scqc", "version": "0.0.0-fake", "commit": "0" * 12,
              "state_version": STATE_VERSION, "status": "partial", "headline": "started",
              "inputs": [], "products": [], "absent": [], "refusal": None, "escapes": [],
              "sees": ["design"], "cannot_show": [], "wrapped_versions": {}}
    (res / "STATUS.json").write_text(json.dumps(status, indent=1))
    (res / "RUNNING.txt").write_text("started\n")

    def seal(name, code, extra=""):
        (res / "RUNNING.txt").unlink()
        (res / name).write_text(f"exit={code}\nstatus={status['status']}\njobid=none\n{extra}")

    if MODE == "refuse":
        status.update(status="refused", headline="05_quality: no valley in one library",
                      refusal={"reason": "05_quality: no valley in one library",
                               "fix": "record an adjudicated floor in decisions.yml"})
        (res / "STATUS.json").write_text(json.dumps(status, indent=1))
        seal("FAILED.txt", 2)
        print("REFUSED\n05_quality: no valley in one library")
        return 2
    if MODE == "fail":
        status.update(status="failed", headline="RuntimeError: a task died")
        (res / "STATUS.json").write_text(json.dumps(status, indent=1))
        seal("FAILED.txt", 1)
        print("scqc: RuntimeError: a task died", file=sys.stderr)
        return 1

    removed_ids, total, kept = [], 0, 0
    if a.mode == "apply":
        for r in rows:
            sample = r["sample"]
            assay = r.get("assay", "").strip().lower()
            cell_col = "aligner_cell" if assay == "scrna" else "cellbender_cell"
            criteria = ["fail_not_" + cell_col, "fail_umi_floor", "fail_gene_floor",
                        "fail_mito_ceiling", "fail_doublet", "fail_mito_nf"]
            bcs = barcodes(r["ambient_h5"])
            if MODE == "short":
                bcs = bcs[1:]
            with open(res / "tables" / f"{sample}.percell.csv", "w", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(["barcode", "sample", cell_col, "total_counts", "n_genes",
                            "pct_counts_mt", "nuclear_fraction", "doublet_score", "doublet_class",
                            "doublet_scored", *criteria, "removed", "keep"])
                for i, b in enumerate(bcs):
                    fires = [i % 10 == 9, i % 7 == 3, i % 11 == 5, i % 13 == 6, i % 17 == 8, False]
                    removed = any(fires)
                    keep = not removed
                    if MODE == "disagree" and i == 0:
                        keep = not keep
                    w.writerow([b, sample, not fires[0], 100 + i, 50 + i % 40, f"{(i % 9) / 3:.6f}",
                                "", f"{(i % 5) / 10:.6f}", "doublet" if fires[4] else "singlet",
                                True, *fires, removed, keep])
                    total += 1
                    kept += keep
                    if removed:
                        removed_ids.append((f"{sample}|{b}", [c for c, f in zip(criteria, fires) if f],
                                            criteria))
        with open(res / "tables" / "removal_ledger.csv", "w", newline="") as fh:
            w = csv.writer(fh, lineterminator="\n")
            crit = removed_ids[0][2] if removed_ids else []
            w.writerow(["identifier", "n_criteria", "criteria", *crit])
            for ident, why, crits in removed_ids:
                w.writerow([ident, len(why), "|".join(why), *[1 if c in why else 0 for c in crits]])
        import h5py
        with h5py.File(res / "objects" / "cohort.deliverable.h5ad", "w") as f:
            f.create_group("obs").attrs["_index"] = "_index"
            f["obs"].create_dataset("_index", data=[str(i).encode() for i in range(kept)])
    (res / "reports" / "report.json").write_text(json.dumps({"kept": kept, "total": total}))
    status.update(status="ok", headline=f"{len(rows)} libraries; deliverable written",
                  products=[{"path": "reports/report.json", "bytes": 1}])
    (res / "STATUS.json").write_text(json.dumps(status, indent=1))
    if MODE == "unsealed":
        (res / "RUNNING.txt").unlink()
    else:
        seal("SEALED.txt", 0, "products=reports/report.json\n")
    print(f"report   : {res / 'reports' / 'report.json'}")
    return 0


def main(argv=None):
    log_call()
    p = argparse.ArgumentParser(prog="scqc")
    sub = p.add_subparsers(dest="cmd")
    d = sub.add_parser("describe")
    d.add_argument("--json", action="store_true")
    r = sub.add_parser("run")
    r.add_argument("--project", required=True)
    r.add_argument("--mode", choices=["evidence", "apply"], default="apply")
    r.add_argument("--samplesheet")
    r.add_argument("--registry")
    r.add_argument("--decisions")
    r.add_argument("--executor", choices=["local", "pbs"], default="local")
    r.add_argument("--allow-local", dest="allow_local", action="store_true")
    r.add_argument("--queue")
    r.add_argument("--pbs-project", dest="pbs_project")
    r.add_argument("--gpu-queue", dest="gpu_queue")
    r.add_argument("--python")
    r.add_argument("--celescope")
    r.add_argument("--cellranger")
    r.add_argument("--cellbender")
    r.add_argument("--rscript")
    r.add_argument("--cpu", action="store_true")
    r.add_argument("--light-floor", dest="light_floor", type=int, default=200)
    r.add_argument("--dbr", type=float)
    r.add_argument("--dbr-sd", dest="dbr_sd", type=float)
    r.add_argument("--mito-bounds", dest="mito_bounds")
    r.add_argument("--mito-bound-declared-by", dest="mito_bound_declared_by")
    r.add_argument("--dbr-sd-sweep", dest="dbr_sd_sweep")
    r.add_argument("--resolution", type=float, default=2.0)
    r.add_argument("--extra-resolutions", dest="extra_resolutions", default="1.0,3.0")
    r.add_argument("--seed", type=int, default=0)
    r.add_argument("--force", action="store_true")
    r.add_argument("--jobs", "-j", type=int, default=0)
    a = p.parse_args(argv)
    if a.cmd == "describe":
        return describe()
    if a.cmd == "run":
        return run(a)
    p.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
