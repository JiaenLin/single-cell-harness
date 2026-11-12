#!/usr/bin/env python3
"""A stand-in for `scqc_cli.py`, for tests that drive `qc@scqc` through `sch` without scanpy or R.

It honours the parts of scQC's contract the adapter reads, and nothing more, as scQC's own
`tests/fixtures/fake_rscript.py` stands in for its doublet detector:

    describe                  the declaration, as JSON (`state_version` is what the adapter checks, and
                              `files`, what `run` opens: its flags and the samplesheet's columns)
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
    FAKE_SCQC_MODE            ok (default) | refuse | fail | unsealed | disagree | short | two_prefixes (a second
                              output prefix: two candidates per library) | no_joint (no deliverable)
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


#: THE FILES scQC OPENS, as its `describe` would declare them (`files`; scQC's own `describe` declares none and its
#: parser types none of its flags a path: the gap harness autodev W056 wave B names): each flag of a command naming
#: a file or a folder it READS, by its dest, with its kind, and the samplesheet's columns it opens, each cell as
#: written (adapters/cellbender.py:1284, engine/steps.py:496, :508, :655, :788, ingest.py:162, the align route's
#: celescope.py:1049). What it writes (`--project`) is not an input. `run` refuses an absent one, as scQC does; the
#: adapter's `files:` and `owned:` are tied to this by tests/test_the_adapters_declare_what_their_tools_open.py.
FILES = {"flags": {"run": {"samplesheet": "file", "registry": "file", "decisions": "file", "python": "path",
                           "rscript": "path", "cellbender": "path", "celescope": "path", "cellranger": "path"}},
         "columns": {"run.samplesheet": {c: "path" for c in (
             "matrix", "ambient_h5", "aligner_cells", "cellbender_barcodes", "cellreads_stats", "fastq_r1",
             "ambient_log", "ambient_metrics")}}}
IS = {"file": os.path.isfile, "dir": os.path.isdir, "path": os.path.exists}


def absent(cmd, a, rows=()):
    """The first file this call's declared flags and columns name that is not here, said as scQC says it, or None."""
    for dest, kind in FILES["flags"].get(cmd, {}).items():
        v = getattr(a, dest, None)
        if v and not IS[kind](str(v)):
            return f"--{dest.replace('_', '-')} {str(v)!r} is not a {'file or folder' if kind == 'path' else kind}"
    for col, kind in FILES["columns"].get(f"{cmd}.samplesheet", {}).items():
        for r in rows:
            v = str(r.get(col) or "").strip()
            if v and not IS[kind](v):
                return f"the samplesheet's {col} of {r.get('sample')} ({v!r}) names no file here"
    return None


def describe():
    print(json.dumps({"contract": "1.0", "name": "scqc", "version": "0.0.0-fake",
                      "state_version": STATE_VERSION, "layer": "stack", "reversible": True,
                      "sees": ["design"], "cannot_show": ["a stand-in shows nothing"], "files": FILES,
                      # scQC's own escapes (engine/declare.py:78-85 at c5b1a1b); harness W042 fix 1, D
                      "escapes": [{"what": "a DERIVED threshold", "how": "decisions.yml with value, class, "
                                   "approved_by, verbatim", "recorded": "reports/payload.json parameters[].decided_by"},
                                  {"what": "a REVIEW finding", "how": "proceed; the finding stays in gates[]",
                                   "recorded": "reports/payload.json gates[]"},
                                  {"what": "the apply step", "how": "--mode evidence runs no removal",
                                   "recorded": "INPUTS.json described.mode"}]}))
    return 0


#: As scQC (modules/01_ambient/ambient.py): a library supplied already denoised (`ambient_h5`) names who
#: denoised it, how and by whom, or it is refused; CellBender itself runs on nuclei only (CELLBENDER_RUNS).
SUPPLIED_REQUIRED = ("tool", "version", "params", "produced_by")
CELLBENDER_RUNS = {"snrna": True, "scrna": False}


def run(a):
    project = Path(a.project)
    why = absent("run", a) or (None if a.registry else "--registry is required")
    rows = [] if why else read_sheet(a.samplesheet)
    why = why or absent("run", a, rows)
    if why:
        print(f"scqc run: {why}", file=sys.stderr)
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

    supplied = [(r.get("sample"), [k for k in SUPPLIED_REQUIRED if not str(r.get(f"ambient_{k}") or "").strip()])
                for r in rows if str(r.get("ambient_h5") or "").strip()]
    bad = [(s_, m) for s_, m in supplied if m]
    if bad:                                      # scQC's 01_ambient refusal (plan_ambient), before any step
        why = (f"01_ambient ({bad[0][0]}): a SUPPLIED ambient correction is missing {', '.join(bad[0][1])}; an "
               f"object merely asserted to be denoised is an anonymous matrix")
        status.update(status="refused", headline=why, refusal={
            "reason": why, "fix": "name ambient_tool, ambient_version, ambient_params and ambient_produced_by"})
        (res / "STATUS.json").write_text(json.dumps(status, indent=1))
        seal("FAILED.txt", 2)
        print("REFUSED\n" + why)
        return 2
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

    removed_ids, total, kept, kept_of = [], 0, 0, {}
    if a.mode == "apply":
        for r in rows:
            sample = r["sample"]
            assay = r.get("assay", "").strip().lower()
            cell_col = "aligner_cell" if assay == "scrna" else "cellbender_cell"
            criteria = ["fail_not_" + cell_col, "fail_umi_floor", "fail_gene_floor",
                        "fail_mito_ceiling", "fail_doublet", "fail_mito_nf"]
            # scQC's two columns for a library's object: a supplied denoised `ambient_h5`, or the
            # `matrix` it ingests itself (engine/graph.py); one of them, AS scQC READS EACH (autodev W056 D6 fix
            # round, ATTACKS 1): `ambient_h5` stripped (graph.py:132), `matrix` as written (graph.py:119)
            bcs = barcodes(str(r.get("ambient_h5") or "").strip() or str(r["matrix"]))
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
                    if keep:
                        kept_of.setdefault(sample, []).append(b)
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
        # scQC's other shape (adapters/scanpy_ops.py, the apply step): each library's kept barcodes
        # in `objects/cohort_per_sample/<sample>.filtered.h5ad`, named `<sample>_<barcode>`, with
        # scQC's `sample` column - what annotation reads (harness W041)
        import numpy as np
        for sample, mine in kept_of.items():
            names = [b if b.startswith(f"{sample}_") else f"{sample}_{b}" for b in mine]
            one = res / "objects" / "cohort_per_sample" / f"{sample}.filtered.h5ad"
            one.parent.mkdir(parents=True, exist_ok=True)
            with h5py.File(one, "w") as f:
                g = f.create_group("obs")
                g.attrs.update({"_index": "_index", "column-order": ["sample"],
                                "encoding-type": "dataframe", "encoding-version": "0.2.0"})
                g.create_dataset("_index", data=[n.encode() for n in names])
                c = g.create_group("sample")
                c.attrs.update({"encoding-type": "categorical", "encoding-version": "0.2.0", "ordered": False})
                c.create_dataset("categories", data=[sample.encode()])
                c.create_dataset("codes", data=np.zeros(len(names), dtype="int8"))
        if MODE == "two_prefixes":       # two output prefixes in one run: two candidates for each
            import shutil
            for o in sorted((res / "objects").glob("cohort*")):
                dst = res / "objects" / o.name.replace("cohort", "other", 1)
                (shutil.copytree if o.is_dir() else shutil.copy)(o, dst)
        if MODE == "no_joint":           # a run that writes no deliverable
            (res / "objects" / "cohort.deliverable.h5ad").unlink()
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
