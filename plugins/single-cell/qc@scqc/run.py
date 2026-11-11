#!/usr/bin/env python3
"""qc@scqc: scQC's quality control, mounted as a removal the stack can take back (harness W010).

It runs scQC's REAL command line - `scqc_cli.py describe`, then `scqc_cli.py run` - over the
libraries the stack declares as its observations, and contributes what scQC decided in the
harness's form: one WHOLE mask per criterion over every observation, the per-cell values the
criteria were evaluated on, and scQC's own tables and objects referenced where scQC wrote them.
It re-implements nothing. Every number is read from scQC's per-cell tables, and the stage's record
is scQC's own STATUS.json and seal, adopted rather than rewritten.

Nothing about a site or a cohort is here. Where scQC is, the project's registry, which queue
scQC's own tasks go to: each is declared with `--param`. An absent one is refused (scQC's path, the
registry) or left to scQC's own default; the adapter never chooses one.
"""
import csv
import importlib.util
import json
import os
import subprocess
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

#: The numbers this adapter's masks and columns mean. It must equal `state_version` in plugin.yml
#: AND the STATE_VERSION scQC declares (`scqc describe`): a scQC whose numbers moved without this
#: moving would be served from a cached view keyed on the old ones (D6).
STATE_VERSION = 1
#: scQC's `run` flags this adapter forwards, by scQC's own names (`-` written `_`), in the order
#: scQC's parser declares them (scqc_cli.py, `run`). True is a bare flag; false or null is absent.
FORWARDED = ("mode", "decisions", "executor", "allow_local", "queue", "pbs_project", "gpu_queue",
             "python", "celescope", "cellranger", "cellbender", "rscript", "cpu", "light_floor",
             "dbr", "dbr_sd", "mito_bounds", "mito_bound_declared_by", "dbr_sd_sweep", "resolution",
             "extra_resolutions", "seed", "force", "jobs")
#: Required, with no default: scQC's CLI (`<checkout>/scqc_cli.py`) and the project's registry.
REQUIRED = ("scqc", "registry")
#: The adapter's, from the stack: scQC's project is this run's out_dir, its samplesheet the
#: stack's observation manifest. A parameter naming either is refused, not obeyed.
OWNED = ("project", "samplesheet")
#: Read by the kernel, not by scQC.
KERNEL_PARAMS = ("timeout",)
#: The per-cell values scQC evaluated its criteria on, carried onto the view as columns.
MEASURED = ("total_counts", "n_genes", "pct_counts_mt", "pct_counts_ribo", "nuclear_fraction",
            "doublet_score", "doublet_class")
#: scQC names each library by its samplesheet's `sample` column, and its per-cell tables say which
#: library a barcode came from in a column of the same name. scQC's word, not the stack's key.
SCQC_LIBRARY = "sample"
#: The seals scQC's run writes beside its STATUS.json (engine/status.py): one or the other.
SEALS = ("SEALED.txt", "FAILED.txt")

run = protocol.Run.from_argv()
out_dir = Path(run.inp["out_dir"])
idc = run.inp["identity"]["column"]
obs = run.inp.get("observations") or {}
params = dict(run.params)


def refuse(reason, fix):
    sys.exit(run.refuse(reason, fix=fix))


# ---------------------------------------------------------------------------- what was declared
unknown = sorted(set(params) - set(FORWARDED) - set(REQUIRED) - set(OWNED) - set(KERNEL_PARAMS))
if unknown:
    refuse(f"parameter(s) {', '.join(unknown)} are not scQC `run` flags",
           f"forward only scQC's own flags: {', '.join(FORWARDED)}")
owned = sorted(set(params) & set(OWNED))
if owned:
    refuse(f"parameter(s) {', '.join(owned)} are set by the adapter from the stack: scQC's project "
           f"is this run's out_dir and its samplesheet is the stack's observation manifest",
           "remove them; declare the samplesheet as the stack's observations (sch init --parts)")
absent = [k for k in REQUIRED if not params.get(k)]
if absent:
    refuse(f"no {', '.join(absent)} declared; the adapter knows no site's scQC and no project's "
           f"references", "--param scqc=<scQC checkout>/scqc_cli.py --param registry=<registry.tsv>")
scqc = Path(str(params["scqc"]))
if not scqc.is_file():
    refuse(f"scqc={scqc} is not a file", "--param scqc=<scQC checkout>/scqc_cli.py")
if not obs.get("parts"):
    refuse("the stack's observations are one file; scQC reads a cohort as libraries, from its "
           "samplesheet", "sch init --observations <samplesheet> --parts <column naming each "
                          "library's object> --key sample=<the samplesheet's sample column>")

# The view the kernel handed over: a parts stack's view names every mask mounted beneath this one.
with open(run.data, newline="", encoding="utf-8") as fh:
    beneath = [c for c in (next(csv.reader(fh), None) or []) if c.startswith("mask__")]
if beneath:
    refuse(f"observations are already masked beneath this mount ({', '.join(beneath)}); scQC reads "
           f"the delivered libraries itself and would derive its thresholds over observations the "
           f"stack has set aside", "mount qc@scqc first, directly on the observations")

manifest = Path(obs["path"])
lines = [ln for ln in manifest.read_text(encoding="utf-8").splitlines()
         if ln.strip() and not ln.lstrip().startswith("#")]
delim = "\t" if lines[0].count("\t") > lines[0].count(",") else ","
libraries = list(csv.DictReader(lines, delimiter=delim))
if SCQC_LIBRARY not in libraries[0]:
    refuse(f"the samplesheet has no {SCQC_LIBRARY!r} column, which is how scQC names a library",
           "use scQC's samplesheet as the stack's observations")
scope_of = {r[SCQC_LIBRARY].strip(): r[obs["scope"]].strip() for r in libraries}

# ---------------------------------------------------------------------------- rule 2: the assay
# Passed through, never defaulted: the stack declares the assay once (profile_context) and every
# library's own declaration must say the same. Nothing is filled in on either side.
context = dict(run.inp.get("profile_context") or {})
declared = str(context.get("assay") or "").strip().lower()
if not declared:
    refuse("the stack declares no assay; scQC's rules for single cells and single nuclei differ "
           "(no denoiser on cells, per-assay bounds) and none of them is a default",
           "sch init ... --context assay=<scrna|snrna>")
for r in libraries:
    lib = r[SCQC_LIBRARY].strip()
    got = str(r.get("assay") or "").strip().lower()
    if got != declared:
        refuse(f"library {lib} declares assay {got or 'nothing'!r}; the stack declares {declared!r}",
               "make the samplesheet and the stack's --context assay agree; one cohort, one assay")
    for axis, value in context.items():
        if axis != "assay" and axis in r and str(r[axis]).strip() != str(value).strip():
            refuse(f"library {lib} declares {axis} {str(r[axis]).strip()!r}; the stack declares "
                   f"{str(value).strip()!r}", f"make the samplesheet and --context {axis} agree")

# ---------------------------------------------------------------------------- scQC's numbers' version
d = subprocess.run([sys.executable, str(scqc), "describe"], capture_output=True, text=True,
                   cwd=str(out_dir))
try:
    described = json.loads(d.stdout)
except ValueError:
    sys.stderr.write(f"scqc describe exited {d.returncode} with no declaration:\n{d.stderr}\n")
    sys.exit(1)
if described.get("state_version") != STATE_VERSION:
    refuse(f"scQC declares state_version {described.get('state_version')!r}; this adapter's masks "
           f"mean state_version {STATE_VERSION}, and a cached view keyed on one would serve the "
           f"other's numbers (D6)", "update the adapter to scQC's numbers and bump its state_version")

# ---------------------------------------------------------------------------- scQC's own run
argv = [sys.executable, str(scqc), "run", "--project", str(out_dir / "scqc"),
        "--samplesheet", str(manifest), "--registry", str(params["registry"])]
for k in FORWARDED:
    v = params.get(k)
    if v is None or v is False:
        continue
    flag = "--" + k.replace("_", "-")
    if v is True:
        argv.append(flag)
    else:
        argv += [flag, ",".join(map(str, v)) if isinstance(v, list) else str(v)]
rc = subprocess.run(argv, cwd=str(out_dir)).returncode

found = [p for p in sorted((out_dir / "scqc" / "results").glob("*/STATUS.json"))
         if not p.parent.is_symlink()]
if len(found) != 1:
    sys.stderr.write(f"scQC exited {rc} and left {len(found)} results/<digest>/STATUS.json; a "
                     f"fresh project holds exactly one\n")
    sys.exit(1)
res = found[0].parent
status = json.loads(found[0].read_text(encoding="utf-8"))
seal = next((n for n in SEALS if (res / n).exists()), None)
record = {"results": str(res.relative_to(out_dir)), "digest": res.name, "status": status.get("status"),
          "seal": seal, "exit": rc, "headline": status.get("headline"), "version": status.get("version"),
          "commit": status.get("commit"), "state_version": status.get("state_version"),
          "escapes": status.get("escapes") or []}
run.answer(stage_record=record, argv=argv[1:], identity_joiner=obs["joiner"], scope_of=scope_of)

if status.get("status") == "refused" and rc == 2:
    ref = status.get("refusal") or {}
    sys.exit(run.refuse(f"scQC refused: {ref.get('reason') or status.get('headline')}",
                        fix=ref.get("fix") or "read reports/report.json in scQC's results"))
if not (rc == 0 and status.get("status") == "ok" and seal == "SEALED.txt"):
    # A death is not a result. scQC's record says what happened; it is quoted, not interpreted.
    sys.stderr.write(f"scQC did not finish ok: exit {rc}, STATUS {status.get('status')!r} "
                     f"({status.get('headline')!r}), seal {seal or 'none'} in {res}\n")
    sys.exit(1)

# ---------------------------------------------------------------------------- what scQC decided
run.wrapped("scQC", f"{status.get('version')} ({status.get('commit')})")
inputs = json.loads((res / "INPUTS.json").read_text(encoding="utf-8")) \
    if (res / "INPUTS.json").exists() else {}
mode = ((inputs.get("described") or {}).get("mode")) or ""
tables = sorted((res / "tables").glob("*.csv"))
for t in tables:
    run.table_at(str(t.relative_to(out_dir)))
for o in sorted((res / "objects").glob("**/*.h5ad")):
    run.object_at(o.stem, str(o.relative_to(out_dir)))
# WHAT THE NEXT STAGE READS (harness W041), in scQC's own layout: each library's kept observations
# (`objects/<prefix>_per_sample/<sample>.filtered.h5ad`, what annotation reads) and the joint
# deliverable (`objects/<prefix>.deliverable.h5ad`, what integration and DE read). Named, not copied.
# Two candidates for one library, or two joint deliverables, are refused by name: picking one of them
# would hand the next stage an object nobody chose (harness W042 fix 1, observation 5).
per, cand = {}, {}
for o in sorted((res / "objects").glob("*_per_sample/*.filtered.h5ad")):
    lib = o.name[:-len(".filtered.h5ad")]
    if lib in scope_of:
        cand.setdefault(scope_of[lib], []).append(str(o.relative_to(out_dir)))
two = {k: v for k, v in cand.items() if len(v) > 1}
if two:
    refuse(f"scQC wrote {len(next(iter(two.values())))} kept objects for library {next(iter(two))}: "
           + "; ".join(f"{k}: {', '.join(v)}" for k, v in sorted(two.items()))
           + " - which one the next stage reads is not this adapter's to choose",
           "run scQC with one output prefix, so each library has one kept object")
per = {k: v[0] for k, v in cand.items()}
joint = sorted((res / "objects").glob("*.deliverable.h5ad"))
if len(joint) > 1:
    refuse(f"scQC wrote {len(joint)} joint deliverables: {', '.join(str(j.relative_to(out_dir)) for j in joint)}"
           f" - which one the next stage reads is not this adapter's to choose",
           "run scQC with one output prefix, so the run has one deliverable")
run.answer(hands_on={"libraries": per, "joint": str(joint[0].relative_to(out_dir)) if joint else None})

percell = {lib: res / "tables" / f"{lib}.percell.csv" for lib in scope_of}
if not any(p.exists() for p in percell.values()):
    run.absent("mask/fail_*", f"scQC ran in {mode or 'a'} mode, which writes no per-cell criteria: "
                              f"it measures and removes nothing")
    sys.exit(run.finish(headline=f"scQC {mode or 'run'}: measured, removed nothing (results {res.name})"))
lost = [lib for lib, p in percell.items() if not p.exists()]
if lost:
    sys.stderr.write(f"scQC sealed ok with no per-cell table for {', '.join(lost)}\n")
    sys.exit(1)

criteria, fails, keep_col, values = None, {}, {}, {m: {} for m in MEASURED}
for lib, p in percell.items():
    with open(p, newline="", encoding="utf-8") as fh:
        r = csv.DictReader(fh)
        mine = [c for c in (r.fieldnames or []) if c.startswith("fail_")]
        if criteria is None:
            criteria = mine
            fails = {c: {} for c in criteria}
        elif mine != criteria:
            sys.stderr.write(f"{p.name}: criteria {mine} differ from {criteria}\n")
            sys.exit(1)
        present = [m for m in MEASURED if m in (r.fieldnames or [])]
        for row in r:
            ident = f"{scope_of[row[SCQC_LIBRARY]]}{obs['joiner']}{row['barcode']}"
            for c in criteria:
                fails[c][ident] = row[c] == "True"
            keep_col[ident] = row["keep"] == "True"
            for m in present:
                values[m][ident] = row[m] if row[m] != "" else None

total = len(keep_col)
removed = {i for c in criteria for i, f in fails[c].items() if f}
for c in criteria:
    n = sum(1 for f in fails[c].values() if f)
    run.mask(c, {i: not f for i, f in fails[c].items()}, reason=f"{c} (fired on {n} of {total})",
             id_field=idc)
    run.number(f"n_fired/{c}", n)
for m, col in values.items():
    if col:
        run.column(m, col, id_field=idc)
run.number("n_observations", total)
run.number("n_kept", total - len(removed))
run.number("n_removed", len(removed))
run.answer(criteria=criteria, mode=mode)
sys.exit(run.finish(headline=f"scQC {mode}: kept {total - len(removed):,} of {total:,} observations "
                             f"on {len(criteria)} criteria (results {res.name})"))
