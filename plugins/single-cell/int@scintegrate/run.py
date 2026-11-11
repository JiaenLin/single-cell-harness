#!/usr/bin/env python3
"""int@scintegrate: scIntegrate's integration, mounted as a layer of embeddings, graphs and columns
the stack can take back (harness W034).

It runs scIntegrate's REAL command line over the one object the stack declares as its observations:
the stage's joint object, the one part of a parts manifest, read in place. The calls are a stage-3
job's: `describe` (whose `state_version` this layer means), `doctor` (what the node holds, kept as a
record), then one `integrate`. Every flag of `integrate` is the stage's, by scIntegrate's own name.

The result comes back in the harness's form: a LAYER over the observations, never an edit of them.
The layer is exactly what scIntegrate changed, read back from its object against the part, by
identity (`<part>|<obs name>`):
  - every obsm entry the object carries and the part did not, or carries with other values
    (`embeddings/<key>.npy` beside `barcodes.txt`, the profile's binding);
  - every obsp entry likewise (`graphs/<key>.npz`, compressed sparse, beside `barcodes.txt`);
  - every obs column likewise (`columns/<name>.csv`).
An entry the part carries with the same values is the observation's own, and it is not attributed to
scIntegrate because scIntegrate copied it. What the object no longer carries is recorded and never
removed from the view, which never held it.

Nothing is re-implemented and nothing of scIntegrate's is reshaped. It writes into the run, its
STATUS.json and seal are adopted as the stage's record, and its object and tables are referenced
where they lie.

Nothing about a site or a cohort is here. Where scIntegrate is, and every flag, are declared with
`--param`. The assay and the species are the stack's declaration (`--context`): never a parameter,
never a default (rule 2).
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

try:            # read here, before any scIntegrate process: a host without them would find out
    import h5py         # noqa: F401   after the integration had run, which takes hours
    import numpy as np
except ImportError as e:
    sys.exit(f"int@scintegrate: reading the object needs h5py and numpy in this interpreter ({e})")


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
#: STATE_VERSION scIntegrate declares (`scintegrate describe`): an object whose embeddings moved
#: without this moving would be served from a cached view keyed on the old ones (D6).
STATE_VERSION = 2
#: scIntegrate's command line, as a stage-3 job runs it: `python -m scintegrate.cli`, with the
#: checkout on PYTHONPATH.
MODULE = "scintegrate.cli"
#: `scintegrate integrate`'s flags, in the order its parser declares them (scintegrate/cli.py at
#: 0.7.0: `_common`, then integrate's own), `-` written `_`. The flags the adapter sets itself are
#: in the list, so every call is written in scIntegrate's order.
FLAGS = ("h5ad", "out", "batch_key", "label_key", "species", "assay", "l1_key", "drop_labels",
         "score_against", "colour_by", "scanvi_max_epochs", "coarse_from_path", "label_sentinel",
         "design", "design_sample_col", "bio_factor", "k", "n_pcs", "seed", "min_per_k", "min_dist",
         "indicates_below", "methods", "keep_input_pca", "n_latent", "max_epochs", "w_bio",
         "n_cores", "scib_resolutions", "no_fast_leiden", "object_name")
#: The flags the adapter sets and a parameter may not, each with the reason.
OWNED = {"h5ad": "the stack's one part, which scIntegrate reads in place",
         "out": "a path inside the run, which the adapter sets",
         "species": "the stack's declaration (`sch init --context species=`), never a parameter",
         "assay": "the stack's declaration (`sch init --context assay=`), never a parameter (rule 2)"}
#: A flag scIntegrate's parser takes again for each value (`action="append"`).
APPEND = ("label_sentinel", "bio_factor")
#: The flags that take NO argument (`action="store_true"`): written bare or not at all, so each
#: takes only true, false or null. Any other value would be written after the flag and argparse
#: would read it as an option of its own (verifier W026 D1, through scAnno). For the same reason no
#: value at all may begin with "-".
BARE = ("coarse_from_path", "keep_input_pca", "no_fast_leiden")
#: Flags an earlier scIntegrate had, with what happened to them: a declaration written for 0.4.x is
#: told why, not only that the flag is unknown.
REMOVED = {"lisi_subsample": "it was removed in scIntegrate 0.5.0, which scores iLISI and cLISI on "
                             "every cell because scIB draws that subsample from an unseeded source"}
#: Read by the kernel, not by scIntegrate.
KERNEL_PARAMS = ("timeout",)
#: scIntegrate's status contract (scintegrate/status.py): the record and its seals, in --out.
STATUS, SEALED, FAILED, RUNNING = "STATUS.json", "SEALED.txt", "FAILED.txt", "RUNNING.txt"
#: scIntegrate's run inside the plugin's out_dir, and the adapter's logs inside that. `logs/` is not
#: a directory scIntegrate lists among its products, so the products are the ones a run alone lists.
RESULTS, LOGS = "scintegrate", "logs"
#: The layer's kinds: the profile's slot directory, and where the object holds each.
LAYER = (("columns", "obs"), ("embeddings", "obsm"), ("graphs", "obsp"))
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
    sys.stderr.write(f"int@scintegrate: {why}\n")
    sys.exit(1)


def rel(p):
    return str(Path(p).relative_to(out_dir))


# ---------------------------------------------------------------------------- what was declared
unknown = sorted(set(params) - {"scintegrate", "integrate"} - set(KERNEL_PARAMS))
if unknown:
    refuse(f"parameter(s) {', '.join(unknown)} are neither scIntegrate's checkout nor the flags of "
           f"integrate", "declare scintegrate=<the checkout holding the scintegrate package> and "
                         "integrate as an object of its flags")
if not params.get("scintegrate"):
    refuse("no scintegrate declared; the adapter knows no site's scIntegrate",
           "--param scintegrate=<the scIntegrate checkout, the directory holding scintegrate/cli.py>")
if "integrate" not in params:
    refuse("no integrate declared; its flags (the batch and label columns, the design, the methods) are "
           "the stage's, not the adapter's", "--param 'integrate={\"batch_key\": ..., \"label_key\": ..., ...}'")
block = params["integrate"]
if not isinstance(block, dict):
    refuse(f"integrate={block!r} is not an object of scintegrate integrate's flags",
           "--param 'integrate={\"<flag>\": <value>, ...}' with scIntegrate's flag names, - written _")
gone = sorted(set(block) & set(REMOVED))
if gone:
    refuse(f"integrate: {gone[0]} is not a flag of scintegrate integrate: {REMOVED[gone[0]]}",
           f"remove {', '.join(gone)}; nothing else in the declaration changes")
bad = sorted(set(block) - set(FLAGS))
if bad:
    refuse(f"integrate: {', '.join(bad)} {'is not a flag' if len(bad) == 1 else 'are not flags'} of "
           f"scintegrate integrate", "forward only scintegrate integrate's own flags: "
                                     + ", ".join(k for k in FLAGS if k not in OWNED))
owned = sorted(set(block) & set(OWNED))
if owned:
    refuse(f"integrate: {', '.join(owned)} {'is' if len(owned) == 1 else 'are'} set by the adapter - "
           + "; ".join(f"{k}: {OWNED[k]}" for k in owned), f"remove {', '.join(owned)}")
# Each flag takes the kind of value scIntegrate's parser gives it, and no value can be read as an
# option: what a parameter cannot set through its own name, it cannot set through another's.
for k, v in sorted(block.items()):
    if v is None or v is False:
        continue
    flag = "--" + k.replace("_", "-")
    if k in BARE and v is not True:
        refuse(f"integrate: {k}={v!r}; scintegrate integrate {flag} takes no argument, so a value "
               f"written after it would be read as an option of its own",
               f"declare {k} true (the flag), false or null (absent)")
    if k not in BARE and v is True:
        refuse(f"integrate: {k}=true; scintegrate integrate {flag} takes a value",
               f"declare {k} with its value, or null to keep scIntegrate's default")
    items = v if isinstance(v, list) else [v]
    if isinstance(v, dict) or any(isinstance(x, (dict, list)) for x in items):
        refuse(f"integrate: {k}={v!r} is not a value a command line carries",
               f"declare {k} as text, a number, or a list of them")
    dashed = [x for x in items if x is not True and x is not False and x is not None
              and str(x).startswith("-")]
    if dashed:
        refuse(f"integrate: {k}={dashed[0]!r} begins with '-', which scintegrate would read as an "
               f"option, not as the value of {flag}", f"no value begins with '-'; declare {k} as "
                                                       f"scIntegrate documents it")
name = block.get("object_name")
if name not in (None, False) and ("/" in str(name) or "\0" in str(name) or str(name).startswith(".")
                                  or not str(name).endswith(".h5ad")):
    refuse(f"integrate: object_name={name!r} is not a file name ending .h5ad; the object is written "
           f"inside the run, where its record names it", "declare object_name as <name>.h5ad, or leave "
                                                         "it to scIntegrate's default")
checkout = str(params["scintegrate"])      # verbatim: it is scIntegrate's PYTHONPATH, as alone
if checkout.startswith("-"):
    refuse(f"scintegrate={checkout!r} begins with '-'", "--param scintegrate=<the scIntegrate checkout>")
cli_file = Path(checkout) / "scintegrate" / "cli.py"
if not cli_file.is_file():
    refuse(f"scintegrate={checkout} holds no scintegrate/cli.py",
           "--param scintegrate=<the scIntegrate checkout, the directory holding scintegrate/cli.py>")

# ---------------------------------------------------------------------------- the observations
if not obs.get("parts"):
    refuse("the stack's observations are one file, which the kernel hands a plugin only as a copy; "
           "scIntegrate reads the object itself, in place, as the one part of a manifest",
           "sch init --observations <a manifest of one row> --parts <the column naming the object> "
           "--key sample=<the column naming the part>")
# The view the kernel handed over: a parts stack's view names every mask mounted beneath this one.
with open(run.data, newline="", encoding="utf-8") as fh:
    beneath = [c for c in (next(csv.reader(fh), None) or []) if c.startswith("mask__")]
if beneath:
    refuse(f"observations are already masked beneath this mount ({', '.join(beneath)}); scIntegrate "
           f"reads the object itself and would integrate observations the stack has set aside",
           "mount int@scintegrate on a stack whose observations are the object to integrate: the "
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
    refuse(f"the stack declares {len(parts)} parts; scIntegrate integrates ONE object, the cohort's "
           f"libraries already joined in one file", "sch init over a manifest of one row naming the joint "
                                                    "object, the deliverable of the stage that joined them")
scope, part = parts[0]
joiner = obs["joiner"]

# ---------------------------------------------------------------------------- rule 2: the axes
# Passed through verbatim, never defaulted. The assay is checked only against the assays scIntegrate
# itself declares (`describe`), once that has run; the species, scIntegrate checks against the object.
context = dict(run.inp.get("profile_context") or {})
assay = str(context.get("assay") or "").strip()
if not assay:
    refuse("the stack declares no assay; single cells and single nuclei are separate rule sets, and "
           "neither is a default", "sch init ... --context assay=<scrna|snrna>")
species = str(context.get("species") or "").strip()
if not species:
    refuse("the stack declares no species; scIntegrate requires one and checks it against the object's "
           "gene identifiers, and the adapter holds no default",
           "sch init ... --context species=<the species, as Ensembl names it>")
for axis, value in sorted({"assay": assay, "species": species}.items()):
    if value.startswith("-"):
        refuse(f"the stack declares {axis} {value!r}, which begins with '-' and would be read as an "
               f"option", f"sch init ... --context {axis}=<its value>")

# ---------------------------------------------------------------------------- scIntegrate's calls
P = out_dir / RESULTS
(P / LOGS).mkdir(parents=True, exist_ok=True)
# PYTHONPATH IS THE CHECKOUT, AND ONLY IT: what a stage-3 job gives scIntegrate alone. The kernel's
# own path would put the harness's packages beside scIntegrate's.
env = dict(os.environ, PYTHONPATH=checkout)


def call(cmd, flags=(), capture=False):
    """Run one scIntegrate command, its output in logs/<cmd>.log; (process, wall seconds, log)."""
    argv = [sys.executable, "-m", MODULE, cmd, *flags]
    argvs[cmd] = argv[1:]
    log = P / LOGS / f"{cmd}.log"
    t0 = time.monotonic()
    with open(log, "w", encoding="utf-8") as fh:
        p = subprocess.run(argv, cwd=str(P), env=env, stderr=fh if capture else subprocess.STDOUT,
                           stdout=subprocess.PIPE if capture else fh, text=True)
    return p, round(time.monotonic() - t0, 3), log


p, wall, log = call("describe", capture=True)
(P / LOGS / "describe.json").write_text(p.stdout or "", encoding="utf-8")
try:
    described = json.loads(p.stdout)
except ValueError:
    described = None
if not isinstance(described, dict):
    died(f"scintegrate describe exited {p.returncode} with no declaration; read {log}")
record["describe"] = {"exit": p.returncode, "version": described.get("version"),
                      "commit": described.get("commit"), "state_version": described.get("state_version"),
                      "wall_s": wall, "log": rel(log)}
if described.get("state_version") != STATE_VERSION:
    refuse(f"scIntegrate declares state_version {described.get('state_version')!r}; this adapter's layer "
           f"means state_version {STATE_VERSION}, and a cached view keyed on one would serve the other's "
           f"embeddings (D6)", "update the adapter to scIntegrate's numbers and bump its state_version")
accepted = ((described.get("axes") or {}).get("assay") or {}).get("accepted")
if isinstance(accepted, list) and assay not in accepted:
    refuse(f"the stack declares assay {assay!r}; scIntegrate {described.get('version')} accepts "
           f"{', '.join(map(str, accepted))} (its describe), and would stop at its own parser with no "
           f"record", f"sch init ... --context assay=<{'|'.join(map(str, accepted))}>")

p, wall, log = call("doctor")
record["doctor"] = {"exit": p.returncode, "wall_s": wall, "log": rel(log)}
if p.returncode != 0:
    died(f"scintegrate doctor exited {p.returncode}; read {log}")

values = {**block, "h5ad": part, "out": str(P), "species": species, "assay": assay}
flags = []
for k in FLAGS:
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
p, wall, log = call("integrate", flags)
rc = p.returncode
st = P / STATUS
try:
    status = json.loads(st.read_text(encoding="utf-8")) if st.is_file() else None
except ValueError:
    status = None
# THIS CALL'S OWN RECORD, OR NONE: STATUS.json names the argv scIntegrate was given, and its first
# word is the cli.py that ran - the declared checkout's, or another scintegrate the interpreter found.
mine = status is not None and list(status.get("argv") or [])[1:] == argvs["integrate"][2:]
if not mine:
    record["integrate"] = {"status": None, "exit": rc, "wall_s": wall, "log": rel(log)}
    died(f"scintegrate integrate exited {rc} with no STATUS.json of its own in {P}; read {log}")
ran = Path(str((status.get("argv") or [""])[0]))
if ran.resolve() != cli_file.resolve():
    died(f"the scintegrate that ran is {ran}, not the declared checkout's {cli_file}")
seal = next((s for s in (SEALED, FAILED) if (P / s).is_file()), None)
record["integrate"] = {"status": status.get("status"), "seal": seal, "exit": rc,
                       "headline": status.get("headline"), "version": status.get("version"),
                       "commit": status.get("commit"), "state_version": status.get("state_version"),
                       "wall_s": wall, "record": rel(st), "log": rel(log)}
if status.get("status") == "refused" and rc == 2:
    ref = status.get("refusal") or {}
    refuse(f"scIntegrate integrate refused: {ref.get('reason') or status.get('headline')}",
           ref.get("fix") or f"read {log}")
# THE NUMBERS AGAIN, from the run's own record: `describe` is asked first and could be another process's
# word than the integrate that ran (a checkout moved between the calls); the layer is keyed on this one.
if status.get("state_version") != STATE_VERSION:
    died(f"scintegrate integrate recorded state_version {status.get('state_version')!r} in its STATUS.json, where "
         f"its describe declared {described.get('state_version')!r}; this adapter's layer means state_version "
         f"{STATE_VERSION} (D6), so its object is not read; read {log}")
if not (rc == 0 and status.get("status") == "ok" and seal == SEALED and not (P / RUNNING).exists()):
    # scIntegrate's record says what happened; it is quoted, not interpreted
    died(f"scintegrate integrate did not finish ok: exit {rc}, STATUS {status.get('status')!r} "
         f"({status.get('headline')!r}), seal {seal or 'none'} in {P}; read {log}")
made = [str(x.get("path")) for x in status.get("products") or []
        if str(x.get("path", "")).startswith("objects/") and str(x.get("path")).endswith(".h5ad")]
if len(made) != 1:
    died(f"scintegrate integrate sealed ok and its record lists {len(made)} objects ({made}); the "
         f"adapter reads exactly one")
obj = P / made[0]

# ---------------------------------------------------------------------------- what scIntegrate changed
# Read back from scIntegrate's object, by identity, and compared with the part as delivered.
kinds = {kind: {"added": [], "rewritten": [], "unchanged": [], "dropped": []} for kind, _w in LAYER}


def same_array(a, b):
    if a.shape != b.shape:
        return False
    if a.dtype.kind in "fc" and b.dtype.kind in "fc":
        return bool(np.array_equal(a, b, equal_nan=True))
    return bool(np.array_equal(a, b))


def safe(name):
    if "/" in name or "\0" in name or name in (".", "..") or not name.strip():
        died(f"scIntegrate wrote an entry named {name!r}, which cannot name the layer's file")
    return name


try:
    with h5py.File(part, "r") as fp, h5py.File(obj, "r") as fo:
        p_idx, o_idx = h5read.index(fp), h5read.index(fo)
        if len(set(o_idx)) != len(o_idx) or set(o_idx) != set(p_idx) or len(o_idx) != len(p_idx):
            only_o, only_p = len(set(o_idx) - set(p_idx)), len(set(p_idx) - set(o_idx))
            died(f"scIntegrate's object holds {len(o_idx):,} observations ({len(set(o_idx)):,} distinct) "
                 f"and the part {len(p_idx):,}: {only_o:,} only in the object, {only_p:,} only in the "
                 f"part - the layer would not be over the stack's observations")
        p_pos = {n: i for i, n in enumerate(p_idx)}
        same_order = p_idx == o_idx
        # the part's row for each of the object's rows, and the object's position for each part row
        take = None if same_order else np.array([p_pos[n] for n in o_idx])
        to_obj = None
        if not same_order:
            to_obj = np.empty(len(o_idx), dtype=np.int64)
            to_obj[take] = np.arange(len(o_idx))
        ids = [f"{scope}{joiner}{n}" for n in o_idx]

        # obs: columns, as text, compared by name
        p_cols, o_cols = h5read.columns(fp), h5read.columns(fo)
        for c in o_cols:
            mine_v = h5read.column(fo, c)
            if c not in p_cols:
                kinds["columns"]["added"].append(safe(c))
            else:
                theirs = h5read.column(fp, c)
                if take is not None:
                    theirs = [theirs[i] for i in take]
                kinds["columns"]["rewritten" if mine_v != theirs else "unchanged"].append(safe(c))
            if c in kinds["columns"]["added"] or c in kinds["columns"]["rewritten"]:
                run.column(c, dict(zip(ids, mine_v)), id_field=idc)
        kinds["columns"]["dropped"] = [c for c in p_cols if c not in o_cols]

        # obsm: embeddings, compared over the object's rows
        p_m, o_m = h5read.keys(fp, "obsm"), h5read.keys(fo, "obsm")
        for k in o_m:
            a = h5read.array(fo, k)
            if k in p_m:
                b = h5read.array(fp, k)
                b = b if take is None else b[take]
                kind = "unchanged" if same_array(a, b) else "rewritten"
            else:
                kind = "added"
            kinds["embeddings"][kind].append(safe(k))
            if kind != "unchanged":
                (out_dir / "embeddings").mkdir(parents=True, exist_ok=True)
                np.save(out_dir / "embeddings" / f"{k}.npy", a)
                run.embedding_at(k, f"embeddings/{k}.npy")
        kinds["embeddings"]["dropped"] = [k for k in p_m if k not in o_m]

        # obsp: graphs, compared entry by entry over the object's rows and columns
        p_g, o_g = h5read.keys(fp, "obsp"), h5read.keys(fo, "obsp")
        for k in o_g:
            g = h5read.graph(fo, k)
            kind = "added"
            if k in p_g:
                h = h5read.graph(fp, k)
                kind = "rewritten"
                if g.shape == h.shape:
                    mine_t, theirs_t = g.triples(), h.triples(to_obj)
                    if all(same_array(x, y) for x, y in zip(mine_t, theirs_t)):
                        kind = "unchanged"
            kinds["graphs"][kind].append(safe(k))
            if kind != "unchanged":
                (out_dir / "graphs").mkdir(parents=True, exist_ok=True)
                np.savez(out_dir / "graphs" / f"{k}.npz", data=g.data, indices=g.indices,
                         indptr=g.indptr, format=np.array(g.fmt), shape=np.array(g.shape))
                run.graph_at(k, f"graphs/{k}.npz")
        kinds["graphs"]["dropped"] = [k for k in p_g if k not in o_g]
except h5read.Unreadable as e:
    died(str(e))
# Every embedding and graph of the layer is bound to its observations by one identity file per
# slot, in the object's row order (the profile: `<slot>/<name>` beside barcodes.txt).
for kind, _w in LAYER[1:]:
    if kinds[kind]["added"] or kinds[kind]["rewritten"]:
        (out_dir / kind / IDENTITIES).write_text("".join(f"{i}\n" for i in ids), encoding="utf-8")

# ---------------------------------------------------------------------------- the record
try:
    chosen = (json.loads((P / "report.json").read_text(encoding="utf-8")).get("chosen") or {}).get("default")
except (OSError, ValueError):
    chosen = None
run.wrapped("scIntegrate", f"{described.get('version')} ({described.get('commit')})")
run.object_at(Path(made[0]).stem, rel(obj))
for x in status.get("products") or []:
    t = str(x.get("path", ""))
    if t.startswith("tables/") and t.endswith(".csv") and (P / t).is_file():
        run.table_at(rel(P / t))
layer = {kind: {k: v for k, v in kinds[kind].items()} for kind, _w in LAYER}
n_in = {kind: len(kinds[kind]["added"]) + len(kinds[kind]["rewritten"]) for kind, _w in LAYER}
run.number("n_observations", len(ids))
run.number("n_layer_columns", n_in["columns"])
run.number("n_layer_embeddings", n_in["embeddings"])
run.number("n_layer_graphs", n_in["graphs"])
for label, r in record.items():
    if r.get("wall_s") is not None:
        run.number(f"wall_s/{label}", r["wall_s"])
run.answer(stage_record=record, argv=argvs, pythonpath=checkout, assay=assay, species=species,
           part=scope, identity_joiner=joiner, results=RESULTS, object=rel(obj), chosen=chosen,
           layer=layer)
dropped = {kind: kinds[kind]["dropped"] for kind, _w in LAYER if kinds[kind]["dropped"]}
if dropped:
    run.caveat("scIntegrate's object no longer carries " + "; ".join(
        f"{len(v)} {kind} of the part ({', '.join(v[:6])}{', ...' if len(v) > 6 else ''})"
        for kind, v in dropped.items()) + "; the observations still do, so the view keeps them - "
        "nothing in the layer removes an entry")
sys.exit(run.finish(headline=f"scIntegrate describe -> doctor -> integrate: {n_in['embeddings']} "
                             f"embeddings, {n_in['graphs']} graphs and {n_in['columns']} columns over "
                             f"{len(ids):,} observations, {chosen or 'no'} default; nothing removed "
                             f"(results {RESULTS})"))
