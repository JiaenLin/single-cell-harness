#!/usr/bin/env python3
"""The coordinator's gate runner (RULES, 2026-11-11): submit a pre-declared job, grade it when it lands.

  python3 -I setup/autodev/gate.py submit --wave W### --project <PROJECT> --stage <NN_stage> --job <file.pbs>
                                          [--tool <Tool>=<40-hex commit>|<Tool>=keep ...] [--set NAME=VALUE ...]
                                          [--no-subset REASON] [--go]
  python3 -I setup/autodev/gate.py grade <jobid> --status <gating|verifying|failed> [--verdict "AS PREDICTED"] [--note TEXT]
  python3 -I setup/autodev/gate.py checkout --tool <Tool>=<40-hex commit> [--go]

submit, in one call: (1) the job file is read from the cohort folder, `bash -n`, copied to the cluster, md5 compared;
(2) each --tool checkout is moved to its commit (`keep` records where it is), refused while a live watched job uses that
tool at another commit; (3) the site's validator; (4) the submit recipe in the job's own header is run on the login
node: the lines between `# SUBMIT-BEGIN` and `# SUBMIT-END`, or, in an older job, the commented lines after the last
header line that says "Submit", up to its qsub. Every check line (`... && echo X-CLEAN`, `... && echo PIPELINE-SAME`) is made fatal when it does not hold;
(5) the watch row, a RUNLOG entry, and its copy on the cluster. Without --go it prints what it would run and stops.

Subset before full (RULES 2026-11-11, item 14): a job file `X.pbs` with a sibling `X.subset.pbs` is refused until that
subset job has been graded AS PREDICTED at the same tool commits; a job that asks for more than 2 hours and has no
sibling is refused unless --no-subset gives the reason, which goes into the RUNLOG.

grade: reads the mirror's verdict file, writes the job's own lines verbatim into the RUNLOG, comments the watch row and
appends the wave's ledger row. The verdict is the job's own `GATE:` line, or --verdict for a job that prints none.

Site facts come from autodev/.machinery/site.env (git-ignored): PBS_HOST, COHORTS (the workstation's cohort folder),
R_PROJECTS, R_TOOLS, R_VALIDATE (paths on the cluster, expanded there). This file names no site and no cohort.
"""
import argparse
import datetime
import hashlib
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
MACH = ROOT / "autodev" / ".machinery"
PBS = MACH / "pbs"
WATCH = PBS / "watch.tsv"
WAVES = ROOT / "autodev" / "ledger" / "waves.tsv"
HEX40 = re.compile(r"^[0-9a-f]{40}$")


def stamp():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def site():
    env = {}
    path = MACH / "site.env"
    if not path.is_file():
        sys.exit(f"missing {path}: PBS_HOST, COHORTS, R_PROJECTS, R_TOOLS, R_VALIDATE")
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip()
    for key in ("PBS_HOST", "COHORTS", "R_PROJECTS", "R_TOOLS", "R_VALIDATE"):
        if key not in env:
            sys.exit(f"site.env lacks {key}")
    return env


def remote(host, script, stdin_bytes=None):
    """Run a bash script on the login node; returns (rc, stdout). The script is the command, stdin stays free."""
    if stdin_bytes is None:
        proc = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=30", host, "bash -s"],
                              input=script.encode(), capture_output=True)
    else:
        proc = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=30", host, script],
                              input=stdin_bytes, capture_output=True)
    out = "\n".join(l for l in (proc.stdout.decode(errors="replace") + proc.stderr.decode(errors="replace")).splitlines()
                    if not l.startswith("tput:"))
    return proc.returncode, out


def live_rows():
    rows = []
    if WATCH.is_file():
        for line in WATCH.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.startswith("#"):
                rows.append(line.split("\t"))
    return rows


def tool_args(pairs):
    tools = []
    for pair in pairs or []:
        name, _, commit = pair.partition("=")
        if not name or not (commit == "keep" or HEX40.match(commit)):
            sys.exit(f"--tool {pair}: give <Tool>=<40-hex commit> or <Tool>=keep")
        tools.append((name, commit))
    return tools


def refuse_if_in_use(tools):
    """One checkout per tool: never switch it under a live job (the rule that used to live in memory)."""
    for row in live_rows():
        used = dict(p.split("=", 1) for p in row[3].split(",") if "=" in p) if len(row) > 3 else None
        for name, commit in tools:
            if commit == "keep":
                continue
            if used is None:
                sys.exit(f"REFUSED: watch row {row[0]} names no tools; grade or comment it before moving {name}")
            if name in used and used[name] != commit:
                sys.exit(f"REFUSED: {name} is at {used[name][:7]} under live job {row[0]}; {commit[:7]} waits for it")


def walltime_hours(text):
    m = re.search(r"^#PBS\s+-l\s+walltime=(\d+):(\d+):(\d+)", text, flags=re.M)
    return int(m.group(1)) + int(m.group(2)) / 60 if m else 0.0


def passed_subset(sibling, tools, watch=None):
    """Has `sibling` (a job file name) been graded AS PREDICTED at these tool commits? Reads the watch list's history."""
    watch = watch or WATCH
    want = {n: c for n, c in tools if c != "keep"}
    if not watch.is_file():
        return False
    for line in watch.read_text(encoding="utf-8").splitlines():
        if not line.startswith("# graded AS PREDICTED"):
            continue
        cells = line.split(": ", 1)[-1].split("\t")
        if len(cells) < 5 or cells[4].strip() != sibling:
            continue
        used = dict(p.split("=", 1) for p in cells[3].split(",") if "=" in p)
        if all(used.get(n) == c for n, c in want.items()):
            return True
    return False


def subset_rule(job, text, tools, no_subset):
    """Returns the sentence the RUNLOG carries; exits when the rule refuses."""
    if job.name.endswith(".subset.pbs"):
        return "This is a subset job."
    sibling = job.with_name(job.name[:-len(".pbs")] + ".subset.pbs")
    if sibling.is_file():
        if passed_subset(sibling.name, tools):
            return f"Its subset job `{sibling.name}` was graded AS PREDICTED at these tool commits."
        if no_subset:
            return f"Submitted WITHOUT its subset job `{sibling.name}` having passed: {no_subset}"
        sys.exit(f"REFUSED: submit {sibling.name} first; the full job goes in when it is graded AS PREDICTED at the same commits")
    hours = walltime_hours(text)
    if hours > 2:
        if no_subset:
            return f"Asks for {hours:g} h and has no subset job: {no_subset}"
        sys.exit(f"REFUSED: this job asks for {hours:g} h and has no {sibling.name}; write the subset job, or pass --no-subset with the reason")
    return "Under 2 h; no subset job is required."


def move_script(env, tools):
    lines = []
    for name, commit in tools:
        t = f'"{env["R_TOOLS"]}/{name}"'
        if commit != "keep":
            lines += [
                f'if [ "$(cat {t}/HEAD.txt 2>/dev/null)" != "{commit}" ]; then',
                f'  git -C {t} fetch -q origin {commit} 2>/dev/null || git -C {t} fetch -q origin',
                f'  git -C {t} checkout -q --detach {commit}',
                f'  git -C {t} rev-parse HEAD > {t}/HEAD.txt',
                'fi',
                f'[ "$(git -C {t} rev-parse HEAD)" = "{commit}" ] || {{ echo "REFUSED: {name} is not at {commit}"; exit 9; }}',
            ]
        lines += [
            f'[ -z "$(git -C {t} status --porcelain)" ] && [ "$(git -C {t} rev-parse HEAD)" = "$(cat {t}/HEAD.txt)" ] '
            f'|| {{ echo "REFUSED: {name} is not clean on its HEAD.txt"; exit 9; }}',
            f'echo "TOOL {name}=$(cat {t}/HEAD.txt)"',
        ]
    return lines


def recipe_of(text, job_name, sets):
    lines = text.splitlines()
    header = []
    for line in lines[1:]:
        if line.strip() and not line.startswith("#"):
            break  # a blank line does not end a header (a job of 2026-11-12 had one above its recipe)
        header.append(line.rstrip())
    if "# SUBMIT-BEGIN" in header:
        body = header[header.index("# SUBMIT-BEGIN") + 1:header.index("# SUBMIT-END")]
    else:
        starts = [i for i, l in enumerate(header) if "Submit" in l]
        if not starts:
            sys.exit("no submit recipe in the job's header (no SUBMIT-BEGIN block, no line that says Submit)")
        body = [l for l in header[starts[-1] + 1:] if re.match(r"^#\s{3,}\S", l)]
    recipe, cont, done = [], False, False
    for raw in body:
        line = re.sub(r"^#\s*", "", raw).rstrip()
        if not cont and (not line or line.startswith("(")):
            continue
        recipe.append(line)
        cont = line.endswith("\\")
        if "qsub" in " ".join(recipe[-3:]) and not cont:
            done = True
            break
    if not done:
        sys.exit("the recipe has no qsub line")
    if job_name not in " ".join(recipe):
        sys.exit(f"the recipe does not submit {job_name}: fix the header's file name in this copy")
    out = []
    for line in recipe:
        for item in sets or []:
            name, _, value = item.partition("=")
            line = re.sub(rf"\b{re.escape(name)}=<[^>]*>", f"{name}={value}", line)
        if "<" in line and re.search(r"=<[^>]+>", line):
            sys.exit(f"the recipe has an unfilled placeholder: {line.strip()[:120]} (use --set NAME=VALUE)")
        if re.search(r"&& echo [A-Z][A-Z0-9-]+\s*$", line):   # a check line: X-CLEAN, PIPELINE-SAME, ...
            line = f'{{ {line}; }} || {{ echo "REFUSED: not clean: {line.split("echo")[-1].strip()}"; exit 9; }}'
        out.append(line)
    out.append('echo "RUNDIR=$RUNDIR"')
    return out


def runlog(env, project, stage, entry, go=True):
    local = pathlib.Path(env["COHORTS"]) / project / "stages" / stage / "RUNLOG.md"
    if not go:
        return
    with open(local, "a", encoding="utf-8") as handle:
        handle.write(entry)
    rc, out = remote(env["PBS_HOST"], f'cat > "{env["R_PROJECTS"]}/{project}/stages/{stage}/RUNLOG.md"', local.read_bytes())
    if rc:
        print(f"WARNING: the RUNLOG copy failed ({out[:200]}); the workstation's copy has the entry")


def submit(args):
    env = site()
    tools = tool_args(args.tool)
    job = pathlib.Path(env["COHORTS"]) / args.project / "stages" / args.stage / "jobs" / args.job
    if not job.is_file():
        sys.exit(f"no job file {job}")
    if subprocess.run(["bash", "-n", str(job)], capture_output=True).returncode:
        sys.exit("bash -n fails on the job file")
    data = job.read_bytes()
    if b"\r" in data:
        sys.exit("the job file has CR line ends")
    md5 = hashlib.md5(data).hexdigest()
    recipe = recipe_of(data.decode("utf-8"), args.job, args.set)
    subset_note = subset_rule(job, data.decode("utf-8"), tools, args.no_subset)
    refuse_if_in_use(tools)
    rdir = f'{env["R_PROJECTS"]}/{args.project}/stages/{args.stage}/jobs'
    script = ["set -e", f'cd "{rdir}"',
              f'[ "$(md5sum {args.job} | cut -d" " -f1)" = "{md5}" ] || {{ echo "REFUSED: md5 differs on the cluster"; exit 9; }}']
    script += move_script(env, tools)
    script += [f'v=$(bash "{env["R_VALIDATE"]}" {args.job} 2>&1 | tail -1); echo "VALIDATE $v"',
               'case "$v" in *"within queue limits"*) ;; *) echo "REFUSED: the validator"; exit 9;; esac']
    script += recipe
    if not args.go:
        print("\n".join(script))
        print(f"\n(dry run: md5 {md5}; subset rule: {subset_note}; add --go to copy the job and run this on the login node)")
        return
    rc, out = remote(env["PBS_HOST"], f'cat > "{rdir}/{args.job}"', data)
    if rc:
        sys.exit(f"the copy failed: {out[:300]}")
    rc, out = remote(env["PBS_HOST"], "\n".join(script) + "\n")
    jobid = re.search(r"^(\d+\.[\w.-]+)\s*$", out, flags=re.M)
    rundir = re.search(r"^RUNDIR=(\S+)", out, flags=re.M)
    if rc or not jobid or not rundir:
        sys.exit(f"NOT SUBMITTED (rc={rc}):\n{out[-1500:]}")
    used = ",".join(f"{n}={c}" for n, c in re.findall(r"^TOOL (\S+)=([0-9a-f]{40})", out, flags=re.M))
    with open(WATCH, "a", encoding="utf-8") as handle:
        handle.write(f"{jobid.group(1)}\t{rundir.group(1)}\t{args.wave}\t{used}\t{args.job}\n")
    validate = (re.search(r"^VALIDATE (.*)$", out, flags=re.M) or [None, "?"])[1]
    rel = rundir.group(1).split(f"/{args.project}/", 1)[-1]
    runlog(env, args.project, args.stage,
           f"\n## {stamp()} — {args.wave}: `jobs/{args.job}` submitted (gate.py)\n\n"
           f"- The job file: md5 `{md5}`, equal on both sides; the validator: {validate}.\n"
           f"- The tool checkouts, each clean on its HEAD.txt: {used.replace(',', ', ') or 'none named'}.\n"
           f"- Subset before full: {subset_note}\n"
           f"- **PBS `{jobid.group(1)}`**, run `{rel}`. The prediction is the job header's, written before submission.\n")
    print(f"SUBMITTED {jobid.group(1)} wave={args.wave} run={rel} tools={used}")


def grade(args):
    env = site()
    files = sorted(PBS.glob(f"{args.jobid.split('.')[0]}.verdict"))
    if not files:
        sys.exit(f"no verdict file for {args.jobid} yet (the mirror writes it when the run seals, fails or is gone)")
    lines = files[0].read_text(encoding="utf-8").splitlines()
    head = dict(p.split("=", 1) for p in lines[0].split(" ") if "=" in p)
    body = [l.rstrip() for l in lines[1:] if l.strip() and not l.strip().startswith("RECORD")]
    gate_line = next((l for l in body if l.startswith("GATE:")), None)
    verdict = args.verdict or (gate_line[5:].strip() if gate_line else None)
    if not verdict:
        print("\n".join(body))
        sys.exit("\nthis job prints no GATE: line; read the lines above against its header and pass --verdict")
    parts = head["rundir"].split("/")
    i = parts.index("runs")
    project, stage, rel = parts[i - 1], parts[i + 2], "/".join(parts[i:])
    num = head["job"].split(".")[0]
    runlog(env, project, stage,
           f"\n## {stamp()} — {head.get('wave', '?')}: PBS {num} graded {verdict} (gate.py)\n\n"
           f"- State {head.get('state')}; run `{rel}`.\n- The job's own lines, verbatim:\n"
           + "".join(f"  - {l.strip()}\n" for l in body))
    text = WATCH.read_text(encoding="utf-8").splitlines()
    WATCH.write_text("\n".join(f"# graded {verdict} {stamp()}: {l}" if l.startswith(head["job"]) else l for l in text) + "\n",
                     encoding="utf-8")
    wave = head.get("wave", "")
    last = None
    for row in WAVES.read_text(encoding="utf-8").splitlines()[1:]:
        cells = row.split("\t")
        if len(cells) == 14 and cells[1] == wave:
            last = cells
    if last:
        ids = last[11] if last[11] != "-" else ""
        outcome = (f"PBS {num} {head.get('state')}, {verdict}: " + "; ".join(l.strip() for l in body)).replace("\t", " ")[:1200]
        new = [stamp(), wave] + last[2:7] + ["-", "-", args.status, last[10], (ids + " " + num).strip(), outcome,
                                             (args.note or "-").replace("\t", " ")]
        with open(WAVES, "a", encoding="utf-8") as handle:
            handle.write("\t".join(new) + "\n")
    print(f"GRADED {num} wave={wave} state={head.get('state')} verdict={verdict} status={args.status if last else 'no ledger row'}")
    for l in body[:12]:
        print("  " + l.strip()[:200])


def checkout(args):
    env = site()
    tools = tool_args(args.tool)
    refuse_if_in_use(tools)
    script = "\n".join(["set -e"] + move_script(env, tools)) + "\n"
    if not args.go:
        print(script)
        return
    rc, out = remote(env["PBS_HOST"], script)
    print(out)
    sys.exit(rc)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("submit")
    for name in ("--wave", "--project", "--stage", "--job"):
        s.add_argument(name, required=True)
    s.add_argument("--tool", action="append")
    s.add_argument("--set", action="append")
    s.add_argument("--no-subset", dest="no_subset", help="the reason a long job goes in without a passed subset job")
    s.add_argument("--go", action="store_true")
    g = sub.add_parser("grade")
    g.add_argument("jobid")
    g.add_argument("--status", required=True, choices=["gating", "verifying", "failed", "held"])
    g.add_argument("--verdict")
    g.add_argument("--note")
    c = sub.add_parser("checkout")
    c.add_argument("--tool", action="append", required=True)
    c.add_argument("--go", action="store_true")
    args = parser.parse_args()
    {"submit": submit, "grade": grade, "checkout": checkout}[args.cmd](args)


if __name__ == "__main__":
    main()
