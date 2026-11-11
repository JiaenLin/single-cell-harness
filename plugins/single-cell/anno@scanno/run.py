#!/usr/bin/env python3
"""anno@scanno: scAnno's annotation chain, mounted as a layer of label columns the stack can take
back (harness W026).

It runs scAnno's REAL command line over the libraries the stack declares as its observations:
`describe`, then `cluster` over every library, `annotate` once per library, and `rescue` over the
annotated objects, in that order. It runs only the commands the stage declares, and `annotate` is
always one of them. Every flag is the declaration's, by scAnno's own name.

The labels come back in the harness's form: a LAYER of columns over the observations. The layer is
exactly what scAnno changed. A column the delivered object carries and the library did not is in
it. So is a column the library carried that scAnno rewrote with other values. A column the library
carried unchanged is not: it is the observation's own, and it is not attributed to scAnno.

Nothing is re-implemented and nothing of scAnno's is reshaped. scAnno writes into the run, in the
layout a stage-2 job gives the same commands. Its STATUS.<cmd>.json and seals are adopted as the
stage's record, and its objects and tables are referenced where they lie.

Nothing about a site or a cohort is here. Where scAnno is, its references, its flags: each is
declared with `--param`. An absent one is refused (scAnno's path, `annotate`) or left to scAnno's
own default. The assay is the stack's declaration (rule 2), never a parameter and never a default.
"""
import csv
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import h5obs   # this plugin's own reader, beside this file


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

#: The numbers this adapter's layer means. It must equal `state_version` in plugin.yml AND the
#: STATE_VERSION scAnno declares (`scanno describe`): a scAnno whose labels moved without this
#: moving would be served from a cached view keyed on the old ones (D6).
STATE_VERSION = 1
#: scAnno's commands this adapter runs, in the order it runs them. Each lists the command's flags
#: in the order its parser declares them (scanno/cli.py at 0.12.0), `-` written `_`. The flags
#: the adapter sets itself are in the same lists, so every call is written in scAnno's order.
FLAGS = {
    "cluster": ("h5ad", "out", "split_by", "out_dir", "resolutions", "n_top_genes", "n_pcs",
                "n_neighbors", "seed", "status_dir", "by"),
    "annotate": ("h5ad", "cluster_key", "tree", "resolve", "scope", "l1_tree", "species", "tissue",
                 "assay", "db", "store", "background_from_clusters", "exclude_flag", "no_exclude",
                 "gap_min", "min_tier", "out_gene_key", "gene_key", "use_raw", "out", "out_h5ad",
                 "report", "sample_key", "condition_key", "label_suffix", "label_prefix",
                 "status_dir", "by"),
    "rescue": ("h5ad", "label_key", "sweep_prefix", "cluster_prefix", "unit_key", "from_resolution",
               "to_resolution", "out_key", "out_dir", "out", "out_table", "out_report",
               "status_dir", "by"),
    # scAnno's `embed` (harness W041): ONE embedding over every library, the joint object a stage-3
    # job reads. Run only when the stage declares it, after the chain, over the chain's objects.
    "embed": ("h5ad", "out", "sample_key", "label_obs", "gene_key", "n_hvg", "n_pcs", "n_neighbors",
              "min_dist", "seed", "status_dir", "by"),
}
#: The flags the adapter sets and a parameter may not, each with the reason. Inputs and outputs
#: live in the run (the kernel's out_dir), and the assay is the stack's declaration.
_IN_RUN = "a path inside the run, which the adapter sets"
OWNED = {
    "cluster": {"h5ad": "the stack's libraries", "out": _IN_RUN, "out_dir": _IN_RUN,
                "split_by": "a library is one unit already, and split outputs are named by group",
                "status_dir": "scAnno's record stays beside its output"},
    "annotate": {"h5ad": "cluster's output for the library, or the library itself",
                 "assay": "the stack's declaration (`sch init --context assay=`), never a parameter",
                 "out": "a table this adapter does not write", "out_h5ad": _IN_RUN,
                 "report": "a document this adapter does not write",
                 "status_dir": "scAnno's record stays beside its output"},
    "rescue": {"h5ad": "annotate's outputs", "out_dir": _IN_RUN, "out": _IN_RUN,
               "out_table": _IN_RUN, "out_report": _IN_RUN,
               "status_dir": "scAnno's record stays beside its output"},
    "embed": {"h5ad": "the chain's objects, every library", "out": _IN_RUN,
              "status_dir": "scAnno's record stays beside its output"},
}
#: A flag scAnno's parser takes several values for (`nargs`), written as separate words.
SPREAD = ("h5ad", "label_obs")
#: A flag scAnno's parser takes again for each value (`action="append"`).
APPEND = ("cluster_key",)
#: scAnno's flags that take NO argument (`action="store_true"`, d0ee926's parser): written bare, or
#: not at all, so each takes only true, false or null. Any other value would be written after the
#: flag and argparse would read it as an option of its own. Verifier W026 D1, through the real
#: scAnno: `resolve: "--report=<the libraries' directory>/x.html"` wrote a report beside the
#: observations (E2), and `background_from_clusters: "--assay=snrna"` overrode the stack's assay
#: (rule 2). For the same reason no value at all may begin with "-".
BARE = {"cluster": (), "annotate": ("resolve", "background_from_clusters", "no_exclude", "use_raw"),
        "rescue": (), "embed": ()}
#: Read by the kernel, not by scAnno.
KERNEL_PARAMS = ("timeout",)
#: scAnno's status contract (scanno/status.py): the record and its seals, beside the output.
SEALED, FAILED, RUNNING = "SEALED.{}.txt", "FAILED.{}.txt", "RUNNING.{}.txt"
#: scAnno's directories inside the run (`out_dir/scanno/`): the layout a stage-2 job gives the same
#: commands, so a run through the harness and a run alone compare file for file. `status/` keeps
#: each annotate call's record; `logs/` each call's output.
LAYOUT = ("clustered", "annotated", "rescued", "rescue", "status", "logs")

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
    sys.stderr.write(f"anno@scanno: {why}\n")
    sys.exit(1)


# ---------------------------------------------------------------------------- what was declared
unknown = sorted(set(params) - set(FLAGS) - {"scanno"} - set(KERNEL_PARAMS))
if unknown:
    refuse(f"parameter(s) {', '.join(unknown)} are neither scAnno's path nor a command this adapter "
           f"runs", f"declare scanno=<scAnno's CLI> and the flags of {', '.join(FLAGS)} as objects")
for cmd in FLAGS:
    if cmd in params and not isinstance(params[cmd], dict):
        refuse(f"{cmd}={params[cmd]!r} is not an object of scanno {cmd}'s flags",
               f"--param '{cmd}={{\"<flag>\": <value>, ...}}' with scAnno's flag names, - written _")
if not params.get("scanno"):
    refuse("no scanno declared; the adapter knows no site's scAnno",
           "--param scanno=<scAnno checkout>/bin/scanno")
if "annotate" not in params:
    refuse("no annotate declared; annotate is what labels the observations, and its flags (the "
           "tree, the species, the tissue, the references) are the stage's, not the adapter's",
           "--param 'annotate={\"cluster_key\": [...], \"tree\": ..., ...}'")
for cmd, block in ((c, params[c]) for c in FLAGS if c in params):
    bad = sorted(set(block) - set(FLAGS[cmd]))
    if bad:
        refuse(f"{cmd}: {', '.join(bad)} {'is not a flag' if len(bad) == 1 else 'are not flags'} of "
               f"scanno {cmd}", f"forward only scanno {cmd}'s own flags: "
                                f"{', '.join(k for k in FLAGS[cmd] if k not in OWNED[cmd])}")
    owned = sorted(set(block) & set(OWNED[cmd]))
    if owned:
        refuse(f"{cmd}: {', '.join(owned)} {'is' if len(owned) == 1 else 'are'} set by the adapter - "
               + "; ".join(f"{k}: {OWNED[cmd][k]}" for k in owned), f"remove {', '.join(owned)}")
    # Each flag takes the kind of value scAnno's parser gives it, and no value can be read as an
    # option: what a parameter cannot set through its own name, it cannot set through another's.
    for k, v in sorted(block.items()):
        if v is None or v is False:
            continue
        if k in BARE[cmd] and v is not True:
            refuse(f"{cmd}: {k}={v!r}; scanno {cmd} --{k.replace('_', '-')} takes no argument, so a "
                   f"value written after it would be read as an option of its own",
                   f"declare {k} true (the flag), false or null (absent)")
        if k not in BARE[cmd] and v is True:
            refuse(f"{cmd}: {k}=true; scanno {cmd} --{k.replace('_', '-')} takes a value",
                   f"declare {k} with its value, or null to keep scAnno's default")
        dashed = [x for x in (v if isinstance(v, list) else [v])
                  if x is not True and x is not False and x is not None and str(x).startswith("-")]
        if dashed:
            refuse(f"{cmd}: {k}={dashed[0]!r} begins with '-', which scanno would read as an option, "
                   f"not as the value of --{k.replace('_', '-')}",
                   f"no value begins with '-'; declare {k} as scAnno documents it")
scanno = str(params["scanno"])           # verbatim: it is the path scAnno records as its argv[0]
if scanno.startswith("-"):
    refuse(f"scanno={scanno!r} begins with '-', which the interpreter would read as an option",
           "--param scanno=<scAnno checkout>/bin/scanno")
if not Path(scanno).is_file():
    refuse(f"scanno={scanno} is not a file", "--param scanno=<scAnno checkout>/bin/scanno")
if not obs.get("parts"):
    refuse("the stack's observations are one file; scAnno's chain reads a cohort as libraries, one "
           "object each", "sch init --observations <manifest> --parts <column naming each library's "
                          "object> --key sample=<the manifest's column naming the library>")

# The view the kernel handed over: a parts stack's view names every mask mounted beneath this one.
with open(run.data, newline="", encoding="utf-8") as fh:
    beneath = [c for c in (next(csv.reader(fh), None) or []) if c.startswith("mask__")]
if beneath:
    refuse(f"observations are already masked beneath this mount ({', '.join(beneath)}); scAnno reads "
           f"the libraries themselves and would label observations the stack has set aside",
           "mount anno@scanno on a stack whose observations are the libraries to label: the "
           "deliverable of the stage that removed them")

# The libraries, in the manifest's order, each path as the kernel resolves it.
manifest = Path(obs["path"])
lines = [ln for ln in manifest.read_text(encoding="utf-8").splitlines()
         if ln.strip() and not ln.lstrip().startswith("#")]
delim = "\t" if lines[0].count("\t") > lines[0].count(",") else ","
parts = []
for row in csv.DictReader(lines, delimiter=delim):
    p = (row.get(obs["parts"]) or "").strip()
    parts.append(((row.get(obs["scope"]) or "").strip(), p if Path(p).is_absolute()
                  else str(manifest.parent / p)))
for lib, _p in parts:
    if not lib or "/" in lib or "\0" in lib or lib.startswith("."):
        refuse(f"library {lib!r} cannot name a file, and each library's annotated object is named "
               f"by it", f"rename it in the manifest's {obs['scope']!r} column")
stems = {}
for lib, p in parts:
    stems.setdefault(Path(p).stem, []).append(lib)
alike = {s: libs for s, libs in stems.items() if len(libs) > 1}
if alike and "cluster" in params:
    refuse("libraries " + "; ".join(f"{', '.join(v)} share the file stem {s!r}" for s, v in alike.items())
           + ": scanno cluster names each output <stem>_clustered.h5ad, so one library's object "
             "would overwrite another's", "give each library's object its own file name")

# ---------------------------------------------------------------------------- rule 2: the assay
# Passed through, never defaulted, never checked here: scAnno refuses an assay it does not know, and
# objects annotated under two (W011). `cluster` and `rescue` take none.
context = dict(run.inp.get("profile_context") or {})
assay = str(context.get("assay") or "").strip()
if not assay:
    refuse("the stack declares no assay; scAnno's gene background and its words differ between single "
           "cells and single nuclei, and neither is a default", "sch init ... --context assay=<scrna|snrna>")
if assay.startswith("-"):
    refuse(f"the stack declares assay {assay!r}, which begins with '-' and would be read as an option",
           "sch init ... --context assay=<scrna|snrna>")

# ---------------------------------------------------------------------------- scAnno's numbers' version
d = subprocess.run([sys.executable, scanno, "describe"], capture_output=True, text=True,
                   cwd=str(out_dir))
try:
    described = json.loads(d.stdout)
except ValueError:
    died(f"scanno describe exited {d.returncode} with no declaration:\n{d.stderr}")
if described.get("state_version") != STATE_VERSION:
    refuse(f"scAnno declares state_version {described.get('state_version')!r}; this adapter's layer "
           f"means state_version {STATE_VERSION}, and a cached view keyed on one would serve the "
           f"other's labels (D6)", "update the adapter to scAnno's labels and bump its state_version")

# ---------------------------------------------------------------------------- scAnno's own chain
P = out_dir / "scanno"
for sub in LAYOUT + (("joint",) if "embed" in params else ()):
    (P / sub).mkdir(parents=True, exist_ok=True)


def call(cmd, values, label, where):
    """Run one scAnno command, written in its parser's order, and adopt its own record of it."""
    argv = [sys.executable, scanno, cmd]
    for k in FLAGS[cmd]:
        v = values.get(k)
        if v is None or v is False:
            continue
        flag = "--" + k.replace("_", "-")
        if k in SPREAD:
            argv += [flag, *(str(x) for x in (v if isinstance(v, list) else [v]))]
        elif k in APPEND:
            for x in (v if isinstance(v, list) else [v]):
                argv += [flag, str(x)]
        elif v is True:
            argv.append(flag)
        else:
            argv += [flag, ",".join(map(str, v)) if isinstance(v, list) else str(v)]
    argvs[label] = argv[1:]
    log = P / "logs" / f"{label}.log"
    with open(log, "w", encoding="utf-8") as fh:
        rc = subprocess.run(argv, cwd=str(P), stdout=fh, stderr=subprocess.STDOUT).returncode
    st = Path(where) / f"STATUS.{cmd}.json"
    status = json.loads(st.read_text(encoding="utf-8")) if st.exists() else None
    # THIS CALL'S OWN RECORD, OR NONE. The annotate calls share one directory, so a call that died
    # before scAnno's status contract began (an argument error) leaves the PREVIOUS call's record
    # there, sealed ok. A record is this call's only when it names this call's argv.
    if status is None or status.get("argv") != argv[1:]:
        record[label] = {"status": None, "exit": rc, "log": str(log.relative_to(out_dir))}
        died(f"scanno {cmd} exited {rc} with no STATUS.{cmd}.json of its own in {where}; read {log}")
    if cmd == "annotate":     # the next library's call replaces it; kept as job 25 keeps it
        kept = P / "status" / f"annotate_{label[len('annotate_'):]}.STATUS.json"
        shutil.copyfile(st, kept)
        st = kept
    seal = next((n.format(cmd) for n in (SEALED, FAILED) if (Path(where) / n.format(cmd)).exists()), None)
    t = status.get("timings") or {}
    record[label] = {"status": status.get("status"), "seal": seal, "exit": rc,
                     "headline": status.get("headline"), "version": status.get("version"),
                     "commit": status.get("commit"), "state_version": status.get("state_version"),
                     "escapes": status.get("escapes") or [], "wall_s": t.get("wall_s"),
                     "record": str(st.relative_to(out_dir)), "log": str(log.relative_to(out_dir))}
    if status.get("status") == "refused" and rc == 2:
        ref = status.get("refusal") or {}
        refuse(f"scAnno {cmd} refused: {ref.get('reason') or status.get('headline')}",
               ref.get("fix") or f"read {log}")
    if not (rc == 0 and status.get("status") == "ok" and seal == SEALED.format(cmd)
            and not (Path(where) / RUNNING.format(cmd)).exists()):
        # scAnno's record says what happened; it is quoted, not interpreted
        died(f"scanno {cmd} did not finish ok: exit {rc}, STATUS {status.get('status')!r} "
             f"({status.get('headline')!r}), seal {seal or 'none'} in {where}; read {log}")
    return argv


def produced(path, cmd):
    if not Path(path).is_file():
        died(f"scanno {cmd} sealed ok without {path}")
    return Path(path)


source = {lib: Path(p) for lib, p in parts}
if "cluster" in params:
    call("cluster", {**params["cluster"], "h5ad": [p for _l, p in parts],
                     "out_dir": str(P / "clustered")}, "cluster", P / "clustered")
    # scAnno's rule for several inputs and --out-dir: each written as <stem>_clustered.h5ad
    source = {lib: produced(P / "clustered" / f"{Path(p).stem}_clustered.h5ad", "cluster")
              for lib, p in parts}
annotated = {}
for lib, _p in parts:
    target = P / "annotated" / f"{lib}.ladder.h5ad"
    call("annotate", {**params["annotate"], "h5ad": [str(source[lib])], "assay": assay,
                      "out_h5ad": str(target)}, f"annotate_{lib}", P / "annotated")
    annotated[lib] = produced(target, "annotate")
final = dict(annotated)
if "rescue" in params:
    call("rescue", {**params["rescue"], "h5ad": [str(annotated[lib]) for lib, _p in parts],
                    "out_dir": str(P / "rescued"), "out": str(P / "rescue" / "rescue.json"),
                    "out_table": str(P / "rescue" / "impact.csv"),
                    "out_report": str(P / "rescue" / "rescue.html")}, "rescue", P / "rescued")
    # scAnno's rule for rescue --out-dir: each written as <input stem>.rescued.h5ad
    final = {lib: produced(P / "rescued" / f"{annotated[lib].stem}.rescued.h5ad", "rescue")
             for lib, _p in parts}
joint = None
if "embed" in params:
    joint = P / "joint" / "joint.h5ad"
    call("embed", {**params["embed"], "h5ad": [str(final[lib]) for lib, _p in parts], "out": str(joint)},
         "embed", P / "joint")
    produced(joint, "embed")

# ---------------------------------------------------------------------------- what scAnno changed
# Read back from scAnno's own objects, by identity, and compared with each library as delivered.
joiner = obs["joiner"]
ABSENT = object()           # a name the library does not have: equal to no value
added, rewritten, dropped, carried, names = {}, {}, {}, {}, {}
for lib, p in parts:
    f = final[lib]
    try:
        p_cols, f_cols = h5obs.columns(p), h5obs.columns(f)
        p_idx, f_idx = h5obs.index(p), h5obs.index(f)
        names[lib], carried[lib] = f_idx, set(f_cols)
        for c in f_cols:
            if c not in p_cols:
                added.setdefault(c, []).append(lib)
                continue
            mine, theirs = h5obs.column(f, c), h5obs.column(p, c)
            if f_idx != p_idx:      # compared by name, never by position
                was = dict(zip(p_idx, theirs))
                theirs = [was.get(n, ABSENT) for n in f_idx]
            if mine != theirs:
                rewritten.setdefault(c, []).append(lib)
        for c in p_cols:
            if c not in f_cols:
                dropped.setdefault(c, []).append(lib)
    except h5obs.UnreadableColumn as e:
        died(str(e))
order = []
for lib, _p in parts:
    order += [c for c in h5obs.columns(final[lib]) if c not in order]
layer = [c for c in order if c in added or c in rewritten]
for c in layer:
    if "/" in c or "\0" in c or c in (".", "..") or not c.strip():
        died(f"scAnno wrote an obs column named {c!r}, which cannot name the layer's file")
    values = {}
    for lib, _p in parts:
        if c in carried[lib]:
            try:
                col = h5obs.column(final[lib], c)
            except h5obs.UnreadableColumn as e:
                died(str(e))
            values.update(zip((f"{lib}{joiner}{n}" for n in names[lib]), col))
    run.column(c, values, id_field=idc)

# ---------------------------------------------------------------------------- the record
run.wrapped("scAnno", f"{described.get('version')} ({described.get('commit')})")
for lib, _p in parts:
    run.object_at(lib, str(final[lib].relative_to(out_dir)))
if joint is not None:
    run.object_at("joint", str(joint.relative_to(out_dir)))
for t in (P / "rescue" / "impact.csv",):
    if t.is_file():
        run.table_at(str(t.relative_to(out_dir)))
n_obs = sum(len(v) for v in names.values())
run.number("n_libraries", len(parts))
run.number("n_observations_labelled", n_obs)
run.number("n_layer_columns", len(layer))
run.number("n_columns_added", sum(1 for c in layer if c in added))
run.number("n_columns_rewritten", sum(1 for c in layer if c in rewritten and c not in added))
for label, rec in record.items():
    if rec.get("wall_s") is not None:
        run.number(f"wall_s/{label}", rec["wall_s"])
chain = [c for c in FLAGS if c in params]
run.answer(stage_record=record, argv=argvs, chain=chain, assay=assay, identity_joiner=joiner,
           results=str(P.relative_to(out_dir)),
           hands_on={"libraries": {lib: str(final[lib].relative_to(out_dir)) for lib, _p in parts},
                     "joint": str(joint.relative_to(out_dir)) if joint is not None else None},
           layer={"added": [c for c in layer if c in added],
                  "rewritten": [c for c in layer if c in rewritten and c not in added],
                  "dropped": sorted(dropped)})
if dropped:
    run.caveat(f"scAnno's objects no longer carry {', '.join(sorted(dropped))}; the observations "
               f"still do, so the view keeps them - nothing in the layer removes a column")
sys.exit(run.finish(headline=f"scAnno {' -> '.join(chain)}: {len(layer)} label columns over "
                             f"{n_obs:,} observations in {len(parts)} libraries "
                             f"({sum(1 for c in layer if c in added)} added, "
                             f"{sum(1 for c in layer if c in rewritten and c not in added)} rewritten); "
                             f"nothing removed (results {P.relative_to(out_dir)})"))
