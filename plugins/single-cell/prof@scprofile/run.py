#!/usr/bin/env python3
"""prof@scprofile: scProfile's profiling, mounted as a layer of tables, an object and whatever it
merged into the observations, which the stack can take back (harness W036).

It runs scProfile's REAL command line over the one object the stack declares as its observations:
the cohort's integrated object, the one part of a parts manifest, read in place. The calls are a
stage-4 job's: `doctor` (what the node holds for the run's environments, kept as a record), then one
`run`. Every flag of `run` is the stage's, by scProfile's own name - including `--kernel`: which
plugins run, and which the design admits, is scProfile's own plan, never this adapter's. A plugin
the plan skipped is named with scProfile's reason; nothing is added and nothing is dropped.

The result comes back in the harness's form: a LAYER, never an edit of the observations:
  - every table scProfile lists among its products (`tables/` and `kernels/<plugin>/.../tables/`),
    referenced where it lies - differential expression and abundance are per population and per
    contrast, not per observation, so they are tables and the view over the observations does not
    move;
  - the object scProfile wrote, referenced where it lies;
  - exactly what scProfile's own record (`report.json` `merged`) says it merged into that object:
    obs columns (`columns/<name>.csv`) and obsm embeddings (`embeddings/<key>.npy` beside
    `barcodes.txt`), read back by identity (`<part>|<obs name>`). An entry the part already carried
    with the same values is the observation's own and is not attributed to scProfile.

Nothing about a site or a cohort is here. Where scProfile is, and every flag, are declared with
`--param`. The assay, the organism and the design sheet are the stack's declaration: never a
parameter, never a default (rule 2).
"""
import csv
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import h5read   # this plugin's own reader, beside this file

try:            # read here, before any scProfile process: a host without them would find out
    import h5py         # noqa: F401   after the profiling had run, which takes hours
    import numpy as np
except ImportError as e:
    sys.exit(f"prof@scprofile: reading the object needs h5py and numpy in this interpreter ({e})")


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

#: The numbers this adapter's layer means. It must equal `state_version` in plugin.yml AND the host
#: STATE_VERSION scProfile records in its STATUS.json and report.json (the merge, the fold, the design
#: resolver). scProfile has no `describe`, so it is checked on the run's own record.
STATE_VERSION = 1
#: scProfile's command line, as a stage-4 job runs it: `python -m scprofile.cli`, with the checkout
#: on PYTHONPATH.
MODULE = "scprofile.cli"
#: `scprofile run`'s flags, in the order its parser declares them (scprofile/cli.py at 0.1.0),
#: `-` written `_`. The flags the adapter sets itself are in the list, so every call is written in
#: scProfile's order.
FLAGS = ("control", "covariate", "figures_for", "section", "no_cache", "reuse_from", "reuse_min_grade",
         "unit_by", "resume", "force_all", "h5ad", "out", "kernel", "all", "prefix", "references",
         "label_key", "compartment_key", "sample_key", "batch_key", "counts_layer", "lognorm_layer",
         "embedding", "layout", "sentinels", "organism", "assay", "factor", "design", "params", "cores",
         "timeout", "no_validate", "search", "object_name", "allow", "force")
#: The flags the adapter sets and a parameter may not, each with the reason.
OWNED = {"h5ad": "the stack's one part, which scProfile reads in place",
         "out": "a path inside the run, which the adapter sets",
         "design": "the stack's design sheet (`sch init --design`), never a parameter",
         "assay": "the stack's declaration (`sch init --context assay=`), never a parameter (rule 2)",
         "organism": "the stack's declaration (`sch init --context organism=`), never a parameter"}
#: A flag scProfile's parser takes again for each value (`action="append"`).
APPEND = ("control", "covariate", "factor")
#: The flags that take NO argument (`action="store_true"`): written bare or not at all, so each takes
#: only true, false or null. Any other value would be written after the flag and argparse would read
#: it as an option of its own (verifier W026 D1). For the same reason no value may begin with "-".
BARE = ("no_cache", "resume", "force_all", "all", "no_validate", "force")
#: `scprofile doctor`'s flags that answer for the environments the run is given: doctor is told the
#: run's own values, as a stage-4 job calls it (`doctor --prefix $PREFIX`).
DOCTOR = ("prefix", "references")
#: The family's assays (rule 2) in scProfile's words for them. scProfile reasons about `cell` and
#: `nucleus` and carries any other word as unrecognised, with every assay-specific caveat off; its
#: own reader equates `snrna` with nucleus and `scrna` with cell (scprofile/inputs.py). A declared
#: `snrna` passed verbatim would switch the nucleus caveats off without a word.
ASSAYS = {"scrna": "cell", "snrna": "nucleus"}
#: Read by the kernel, not by scProfile.
KERNEL_PARAMS = ("timeout",)
#: scProfile's status contract (scprofile/status.py): the run's record and its seals, in --out.
STATUS, SEALED, FAILED, RUNNING, REPORT = ("STATUS.json", "SEALED.txt", "FAILED.txt", "RUNNING.txt",
                                           "report.json")
#: scProfile's run inside the plugin's out_dir, and the adapter's logs inside that. `logs/` is not one
#: of scProfile's own trees (kernels, report, tables, objects), so nothing in it is a product.
RESULTS, LOGS = "scprofile", "logs"
IDENTITIES = "barcodes.txt"

run = protocol.Run.from_argv()
out_dir = Path(run.inp["out_dir"])
idc = run.inp["identity"]["column"]
obs = run.inp.get("observations") or {}
params = dict(run.params)
record, argvs = {}, {}


def refuse(reason, fix):
    run.answer(stage_record=record, argv=argvs)
    sys.exit(run.refuse(reason, fix=fix))


def died(why):
    """A death is not a result: no out.json, and stderr says what happened."""
    sys.stderr.write(f"prof@scprofile: {why}\n")
    sys.exit(1)


def rel(p):
    return str(Path(p).relative_to(out_dir))


# ---------------------------------------------------------------------------- what was declared
unknown = sorted(set(params) - {"scprofile", "run"} - set(KERNEL_PARAMS))
if unknown:
    refuse(f"parameter(s) {', '.join(unknown)} are neither scProfile's checkout nor the flags of run",
           "declare scprofile=<the checkout holding the scprofile package> and run as an object of its "
           "flags")
if not params.get("scprofile"):
    refuse("no scprofile declared; the adapter knows no site's scProfile",
           "--param scprofile=<the scProfile checkout, the directory holding scprofile/cli.py>")
if "run" not in params:
    refuse("no run declared; its flags (the plugins, the keys, the controls, the environments) are the "
           "stage's, not the adapter's", "--param 'run={\"kernel\": ..., \"label_key\": ..., ...}'")
block = params["run"]
if not isinstance(block, dict):
    refuse(f"run={block!r} is not an object of scprofile run's flags",
           "--param 'run={\"<flag>\": <value>, ...}' with scProfile's flag names, - written _")
bad = sorted(set(block) - set(FLAGS))
if bad:
    refuse(f"run: {', '.join(bad)} {'is not a flag' if len(bad) == 1 else 'are not flags'} of "
           f"scprofile run", "forward only scprofile run's own flags: "
                             + ", ".join(k for k in FLAGS if k not in OWNED))
owned = sorted(set(block) & set(OWNED))
if owned:
    refuse(f"run: {', '.join(owned)} {'is' if len(owned) == 1 else 'are'} set by the adapter - "
           + "; ".join(f"{k}: {OWNED[k]}" for k in owned), f"remove {', '.join(owned)}")
# Each flag takes the kind of value scProfile's parser gives it, and no value can be read as an
# option: what a parameter cannot set through its own name, it cannot set through another's.
for k, v in sorted(block.items()):
    if v is None or v is False:
        continue
    flag = "--" + k.replace("_", "-")
    if k in BARE and v is not True:
        refuse(f"run: {k}={v!r}; scprofile run {flag} takes no argument, so a value written after it "
               f"would be read as an option of its own", f"declare {k} true (the flag), false or null "
                                                        f"(absent)")
    if k not in BARE and v is True:
        refuse(f"run: {k}=true; scprofile run {flag} takes a value",
               f"declare {k} with its value, or null to keep scProfile's default")
    items = v if isinstance(v, list) else [v]
    if isinstance(v, dict) or any(isinstance(x, (dict, list)) for x in items):
        refuse(f"run: {k}={v!r} is not a value a command line carries",
               f"declare {k} as text, a number, or a list of them")
    dashed = [x for x in items if x is not True and x is not False and x is not None
              and str(x).startswith("-")]
    if dashed:
        refuse(f"run: {k}={dashed[0]!r} begins with '-', which scprofile would read as an option, not "
               f"as the value of {flag}", f"no value begins with '-'; declare {k} as scProfile "
                                          f"documents it")
name = block.get("object_name")
if name not in (None, False) and ("/" in str(name) or "\0" in str(name) or str(name).startswith(".")
                                  or not str(name).endswith(".h5ad")):
    refuse(f"run: object_name={name!r} is not a file name ending .h5ad; the object is written inside "
           f"the run, where its record names it", "declare object_name as <name>.h5ad, or leave it to "
                                                  "scProfile's default")
checkout = str(params["scprofile"])        # verbatim: it is scProfile's PYTHONPATH, as alone
if checkout.startswith("-"):
    refuse(f"scprofile={checkout!r} begins with '-'", "--param scprofile=<the scProfile checkout>")
cli_file = Path(checkout) / "scprofile" / "cli.py"
if not cli_file.is_file():
    refuse(f"scprofile={checkout} holds no scprofile/cli.py",
           "--param scprofile=<the scProfile checkout, the directory holding scprofile/cli.py>")

# ---------------------------------------------------------------------------- the observations
if not obs.get("parts"):
    refuse("the stack's observations are one file, which the kernel hands a plugin only as a copy; "
           "scProfile reads the object itself, in place, as the one part of a manifest",
           "sch init --observations <a manifest of one row> --parts <the column naming the object> "
           "--key sample=<the column naming the part>")
# The view the kernel handed over: a parts stack's view names every mask mounted beneath this one.
with open(run.data, newline="", encoding="utf-8") as fh:
    rows = csv.reader(fh)
    header = next(rows, None) or []
    n_view = sum(1 for _r in rows)
beneath = [c for c in header if c.startswith("mask__")]
if beneath:
    refuse(f"observations are already masked beneath this mount ({', '.join(beneath)}); scProfile "
           f"reads the object itself and would profile observations the stack has set aside",
           "mount prof@scprofile on a stack whose observations are the object to profile: the "
           "deliverable of the stage that removed them")
manifest = Path(obs["path"])
lines = [ln for ln in manifest.read_text(encoding="utf-8").splitlines()
         if ln.strip() and not ln.lstrip().startswith("#")]
delim = "\t" if lines[0].count("\t") > lines[0].count(",") else ","
parts = []
for row in csv.DictReader(lines, delimiter=delim):
    p = (row.get(obs["parts"]) or "").strip()
    parts.append(((row.get(obs["scope"]) or "").strip(), p if Path(p).is_absolute()
                  else str(manifest.parent / p)))
if len(parts) != 1:
    refuse(f"the stack declares {len(parts)} parts; scProfile profiles ONE object, the cohort's "
           f"libraries already integrated in one file", "sch init over a manifest of one row naming the "
                                                        "integrated object, the deliverable of the stage "
                                                        "that wrote it")
scope, part = parts[0]
joiner = obs["joiner"]
if not part.endswith(".h5ad"):
    refuse(f"the stack's one part is {part}, not an .h5ad; scProfile reads an AnnData object",
           "sch init over a manifest naming the integrated .h5ad")

# ---------------------------------------------------------------------------- the stack's declaration
context = dict(run.inp.get("profile_context") or {})
assay = str(context.get("assay") or "").strip()
if not assay:
    refuse("the stack declares no assay; single cells and single nuclei are separate rule sets, and "
           "neither is a default", "sch init ... --context assay=<scrna|snrna>")
if assay not in ASSAYS:
    refuse(f"the stack declares assay {assay!r}; the family's assays are {', '.join(ASSAYS)}, which "
           f"scProfile reasons about as {', '.join(ASSAYS.values())}, and any other word would reach it "
           f"as unrecognised with every assay-specific caveat off",
           f"sch init ... --context assay=<{'|'.join(ASSAYS)}>")
organism = str(context.get("organism") or "").strip()
design = run.inp.get("design")
if design and not Path(design).is_file():
    refuse(f"the stack's design sheet {design} is not a file", "sch init ... --design <the design CSV>")
for axis, value in sorted({"organism": organism, "design": str(design or "")}.items()):
    if value.startswith("-"):
        refuse(f"the stack declares {axis} {value!r}, which begins with '-' and would be read as an "
               f"option", f"sch init ... with the {axis} as its value")

# ---------------------------------------------------------------------------- scProfile's calls
P = out_dir / RESULTS
(P / LOGS).mkdir(parents=True, exist_ok=True)
# PYTHONPATH IS THE CHECKOUT, AND ONLY IT: what a stage-4 job gives scProfile alone. The kernel's own
# path would put the harness's packages beside scProfile's.
env = dict(os.environ, PYTHONPATH=checkout)


def call(cmd, flags=()):
    """Run one scProfile command, its output in logs/<cmd>.log; (process, wall seconds, log)."""
    argv = [sys.executable, "-m", MODULE, cmd, *flags]
    argvs[cmd] = argv[1:]
    log = P / LOGS / f"{cmd}.log"
    t0 = time.monotonic()
    with open(log, "w", encoding="utf-8") as fh:
        p = subprocess.run(argv, cwd=str(P), env=env, stdout=fh, stderr=subprocess.STDOUT, text=True)
    return p, round(time.monotonic() - t0, 3), log


def write(names, values):
    """`--flag value` in the order of `names`; a list on an append flag repeats it."""
    flags = []
    for k in names:
        v = values.get(k)
        if v is None or v is False:
            continue
        flag = "--" + k.replace("_", "-")
        if k in APPEND:
            for x in (v if isinstance(v, list) else [v]):
                flags += [flag, str(x)]
        elif v is True:
            flags.append(flag)
        else:
            flags += [flag, ",".join(map(str, v)) if isinstance(v, list) else str(v)]
    return flags


# doctor is a record: a stage-4 job calls it before the run and reads it, and its exit code says what
# the node lacks for ANY plugin, not for this run - the run itself refuses what it cannot run.
p, wall, log = call("doctor", write(DOCTOR, block))
record["doctor"] = {"exit": p.returncode, "wall_s": wall, "log": rel(log)}

values = {**block, "h5ad": part, "out": str(P), "assay": ASSAYS[assay],
          "organism": organism or None, "design": design or None}
p, wall, log = call("run", write(FLAGS, values))
rc = p.returncode
st = P / STATUS
try:
    status = json.loads(st.read_text(encoding="utf-8")) if st.is_file() else None
except ValueError:
    status = None
# THIS CALL'S OWN RECORD, OR NONE: STATUS.json names the argv scProfile was given, and its first word
# is the cli.py that ran - the declared checkout's, or another scprofile the interpreter found.
mine = status is not None and list(status.get("argv") or [])[1:] == argvs["run"][2:]
if not mine:
    record["run"] = {"status": None, "exit": rc, "wall_s": wall, "log": rel(log)}
    died(f"scprofile run exited {rc} with no STATUS.json of its own in {P}; read {log}")
ran_cli = Path(str((status.get("argv") or [""])[0]))
if ran_cli.resolve() != cli_file.resolve():
    died(f"the scprofile that ran is {ran_cli}, not the declared checkout's {cli_file}")
seal = next((s for s in (SEALED, FAILED) if (P / s).is_file()), None)
record["run"] = {"status": status.get("status"), "seal": seal, "exit": rc,
                 "headline": status.get("headline"), "version": status.get("version"),
                 "commit": status.get("commit"), "state_version": status.get("state_version"),
                 "wall_s": wall, "record": rel(st), "log": rel(log)}
if status.get("status") == "refused" and rc == 2:
    ref = status.get("refusal") or {}
    refuse(f"scProfile run refused: {ref.get('reason') or status.get('headline')}",
           ref.get("fix") or f"read {log}")
if not (rc == 0 and status.get("status") == "ok" and seal == SEALED and not (P / RUNNING).exists()):
    # scProfile's record says what happened; it is quoted, not interpreted
    died(f"scprofile run did not finish ok: exit {rc}, STATUS {status.get('status')!r} "
         f"({status.get('headline')!r}), seal {seal or 'none'} in {P}; read {log}")
try:
    report = json.loads((P / REPORT).read_text(encoding="utf-8"))
except (OSError, ValueError):
    died(f"scprofile run sealed ok and {P / REPORT} cannot be read")
if status.get("state_version") != STATE_VERSION or report.get("state_version") != STATE_VERSION:
    refuse(f"scProfile records state_version {status.get('state_version')!r} (STATUS.json) and "
           f"{report.get('state_version')!r} (report.json); this adapter's layer means state_version "
           f"{STATE_VERSION}, and a cached view keyed on one would serve the other's numbers (D6)",
           "update the adapter to scProfile's numbers and bump its state_version")

# ---------------------------------------------------------------------------- what scProfile wrote
products = [str(x.get("path", "")) for x in status.get("products") or []]
tables = [t for t in products if t.endswith(".csv") and Path(t).parent.name == "tables"
          and Path(t).parts[0] in ("tables", "kernels") and (P / t).is_file()]
made = [t for t in products if t.startswith("objects/") and t.endswith(".h5ad")]
if len(made) > 1:
    died(f"scprofile run's record lists {len(made)} objects ({made}); the adapter reads at most one")
obj = P / made[0] if made else None
said = report.get("object")
if (obj is None) != (said is None) or (obj is not None and Path(said).resolve() != obj.resolve()):
    died(f"report.json names the object {said!r} and STATUS.json lists {made}; they must agree")
merged = {k: v for k, v in (report.get("merged") or {}).items() if isinstance(v, dict)}
want = {"obs": [], "obsm": [], "layers": []}
for kname in sorted(merged):
    for where in want:
        for x in merged[kname].get(where) or []:
            if x not in want[where]:
                want[where].append(str(x))
if (want["obs"] or want["obsm"]) and obj is None:
    died(f"report.json says scProfile merged {want['obs'] + want['obsm']} into an object it did not "
         f"write")

layer = {"columns": {"added": [], "rewritten": [], "unchanged": []},
         "embeddings": {"added": [], "rewritten": [], "unchanged": []}}


def same_array(a, b):
    if a.shape != b.shape:
        return False
    if a.dtype.kind in "fc" and b.dtype.kind in "fc":
        return bool(np.array_equal(a, b, equal_nan=True))
    return bool(np.array_equal(a, b))


def safe(name):
    if "/" in name or "\0" in name or name in (".", "..") or not name.strip():
        died(f"scProfile merged an entry named {name!r}, which cannot name the layer's file")
    return name


ids = []
if obj is not None:
    try:
        with h5py.File(part, "r") as fp, h5py.File(obj, "r") as fo:
            p_idx, o_idx = h5read.index(fp), h5read.index(fo)
            if len(set(o_idx)) != len(o_idx) or set(o_idx) != set(p_idx) or len(o_idx) != len(p_idx):
                died(f"scProfile's object holds {len(o_idx):,} observations ({len(set(o_idx)):,} "
                     f"distinct) and the part {len(p_idx):,}: {len(set(o_idx) - set(p_idx)):,} only in "
                     f"the object, {len(set(p_idx) - set(o_idx)):,} only in the part - the layer would "
                     f"not be over the stack's observations")
            take = None if p_idx == o_idx else np.array([{n: i for i, n in enumerate(p_idx)}[n]
                                                          for n in o_idx])
            ids = [f"{scope}{joiner}{n}" for n in o_idx]
            p_cols, o_cols = h5read.columns(fp), h5read.columns(fo)
            for c in want["obs"]:
                if c not in o_cols:
                    died(f"report.json says scProfile merged obs column {c!r}; its object has none")
                mine_v = h5read.column(fo, c)
                kind = "added"
                if c in p_cols:
                    theirs = h5read.column(fp, c)
                    theirs = theirs if take is None else [theirs[i] for i in take]
                    kind = "rewritten" if mine_v != theirs else "unchanged"
                layer["columns"][kind].append(safe(c))
                if kind != "unchanged":
                    run.column(c, dict(zip(ids, mine_v)), id_field=idc)
            p_m, o_m = h5read.keys(fp, "obsm"), h5read.keys(fo, "obsm")
            for k in want["obsm"]:
                if k not in o_m:
                    died(f"report.json says scProfile merged obsm {k!r}; its object has none")
                a = h5read.array(fo, k)
                kind = "added"
                if k in p_m:
                    b = h5read.array(fp, k)
                    kind = "unchanged" if same_array(a, b if take is None else b[take]) else "rewritten"
                layer["embeddings"][kind].append(safe(k))
                if kind != "unchanged":
                    (out_dir / "embeddings").mkdir(parents=True, exist_ok=True)
                    np.save(out_dir / "embeddings" / f"{k}.npy", a)
                    run.embedding_at(k, f"embeddings/{k}.npy")
    except h5read.Unreadable as e:
        died(str(e))
if layer["embeddings"]["added"] or layer["embeddings"]["rewritten"]:
    # bound to its observations by one identity file, in the object's row order (the profile)
    (out_dir / "embeddings" / IDENTITIES).write_text("".join(f"{i}\n" for i in ids), encoding="utf-8")

# ---------------------------------------------------------------------------- the record
ran = [str(x) for x in report.get("ran") or []]
skipped = [x for x in report.get("skipped") or [] if isinstance(x, dict)]
run.wrapped("scProfile", f"{status.get('version')} ({status.get('commit')})")
if obj is not None:
    run.object_at(obj.stem, rel(obj))
for t in tables:
    run.table_at(rel(P / t))
n_cols = len(layer["columns"]["added"]) + len(layer["columns"]["rewritten"])
n_emb = len(layer["embeddings"]["added"]) + len(layer["embeddings"]["rewritten"])
run.number("n_observations", n_view)
run.number("n_plugins_ran", len(ran))
run.number("n_plugins_skipped", len({str(x.get("kernel")) for x in skipped}))
run.number("n_tables", len(tables))
run.number("n_layer_columns", n_cols)
run.number("n_layer_embeddings", n_emb)
for label, r in record.items():
    if r.get("wall_s") is not None:
        run.number(f"wall_s/{label}", r["wall_s"])
run.answer(stage_record=record, argv=argvs, pythonpath=checkout, assay=assay,
           assay_as_scprofile_says_it=ASSAYS[assay], organism=organism or None, design=design or None,
           part=scope, identity_joiner=joiner, results=RESULTS, object=rel(obj) if obj else None,
           ran=ran, skipped=skipped, merged=merged, tables=[rel(P / t) for t in tables], layer=layer)
for x in skipped:
    why = x.get("why")
    why = "; ".join(map(str, why)) if isinstance(why, list) else str(why)
    run.caveat(f"scProfile's plan did not run {x.get('kernel')}"
               + (f" on {x.get('unit')}" if x.get("unit") else "") + f": {why}")
if want["layers"]:
    run.caveat(f"scProfile merged layer(s) {', '.join(want['layers'])} into its object; they are in "
               f"the object this mount references, not carried as matrices of the layer")
if not organism:
    run.caveat("the stack declares no organism, so scProfile was told none and inferred it; its "
               "report.json `describe` says from what")
sys.exit(run.finish(headline=f"scProfile doctor -> run: {len(ran)} plugin(s) ran "
                             f"({', '.join(ran) or 'none'}), {len(skipped)} skipped by its plan; "
                             f"{len(tables)} tables, {n_cols} columns and {n_emb} embeddings over "
                             f"{n_view:,} observations; nothing removed (results {RESULTS})"))
