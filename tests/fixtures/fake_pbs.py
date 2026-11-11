#!/usr/bin/env python3
"""A stand-in for PBS Pro's `qsub`, `qstat` and `qdel`, for testing the `pbs` executor anywhere.

    fake_pbs.py qsub SCRIPT          prints a job id; by default RUNS the script now, with bash,
                                     as a job that finishes before qsub returns
    fake_pbs.py qstat -x -f JOBID    `job_state = R|F`, `Exit_status = N`, `Job_Name` and
                                     `Variable_List` (wrapped as PBS wraps a long value, onto
                                     tab-led lines), PBS Pro's words; an unknown job is refused as
                                     PBS refuses one
    fake_pbs.py qstat -x -w -u USER  every job, one row each, in PBS Pro's alternate format:
                                     job id, user, queue, job name, ..., state
    fake_pbs.py qdel JOBID           ends a held job (Exit_status 271, as a signal-killed job)

It schedules nothing and enforces no resource: a test using it checks the executor around the
scheduler - the run directory before qsub, the seal the job writes, the exit read from the seal,
qdel confirmed, a qsub that did not answer reconciled - never a scheduler.

Environment:
    FAKE_PBS_STATE   the JSON file holding the jobs and every call (required); a test may seed
                     it with jobs of its own ({"next", "jobs": {id: {...}}, "calls": []}); a job
                     with a "comment" prints it, as a held job's `comment = ...`
    FAKE_PBS_MODE    run (default) | hold | undeletable | lost | full:N | hang:queued:N |
                     hang:lost:N | noid:ran:N
                     hold: queued and never started until qdel; undeletable: qdel is accepted
                     and the job keeps running; lost: the job never runs and qstat forgets it;
                     full:N: the first N qsub calls are refused for a queue's per-user limit;
                     hang:queued:N: the first N qsub calls QUEUE the job - it runs when qstat
                     first asks about it - and then never answer: they hang FAKE_PBS_HANG_S
                     (default 5) and exit 1, as a client that lost the server; hang:lost:N: the
                     same, with no job queued; noid:ran:N: the first N qsub calls queue the job and
                     run it to its end - its seal written - then exit 0 printing no job id, as a
                     client whose reply was lost. Later qsub calls run as `run` does.
    FAKE_PBS_HISTORY 1 (default) | 0: whether the server keeps ended jobs. At 0, a job that has
                     ended is neither listed by `qstat -u` nor known to `qstat -f` (Unknown Job
                     Id), as on a server with job history disabled.
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

STATE = Path(os.environ["FAKE_PBS_STATE"])
HISTORY = os.environ.get("FAKE_PBS_HISTORY", "1") != "0"
MODE = os.environ.get("FAKE_PBS_MODE", "run")


def load():
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {"next": 1000, "jobs": {}, "calls": []}


def save(s):
    STATE.write_text(json.dumps(s, indent=1))


def directives(script: str) -> dict:
    """The job's name and the variables its `#PBS -v` lines declare."""
    name, env = "", {}
    for line in Path(script).read_text().splitlines():
        m = re.match(r"#PBS\s+-N\s+(\S+)", line)
        if m:
            name = m.group(1)
        m = re.match(r"#PBS\s+-v\s+(\S+)", line)
        if m:
            for kv in m.group(1).split(","):
                k, _, v = kv.partition("=")
                env[k] = v
    return {"name": name, "vars": env}


def run_job(s, jid):
    job = s["jobs"][jid]
    r = subprocess.run(["bash", job["script"]], env={**os.environ, "PBS_JOBID": jid})
    s = load()
    s["jobs"][jid].update(state="F", exit=r.returncode, lazy=False)
    return s


def wrapped(key: str, value: str) -> list:
    """`key = value` as PBS Pro prints a long attribute: cut at 78 characters, each further piece
    on a line of its own that begins with a tab."""
    text = f"    {key} = {value}"
    out = [text[:78]]
    text = text[78:]
    while text:
        out.append("\t" + text[:77])
        text = text[77:]
    return out


def main():
    cmd, args = sys.argv[1], sys.argv[2:]
    s = load()
    s["calls"].append([cmd] + args)
    if cmd == "qsub":
        n_qsub = sum(1 for c in s["calls"] if c[0] == "qsub")
        if MODE.startswith("full:") and n_qsub <= int(MODE.split(":")[1]):
            save(s)
            print("qsub: would exceed queue testq's per-user limit of jobs", file=sys.stderr)
            return 38
        hang = MODE.startswith("hang:") and n_qsub <= int(MODE.split(":")[2])
        script = args[-1]
        if hang and MODE.split(":")[1] == "lost":
            save(s)
            time.sleep(float(os.environ.get("FAKE_PBS_HANG_S", "5")))
            print("qsub: connection to server lost", file=sys.stderr)
            return 1
        jid = f"{s['next']}.server"
        s["next"] += 1
        job = {"script": script, "state": "Q", "exit": None, "user": os.environ.get("USER", "u"),
               **directives(script)}
        s["jobs"][jid] = job
        if MODE.startswith("noid:") and n_qsub <= int(MODE.split(":")[2]):
            save(s)                               # queued, run to its end, and no id printed
            save(run_job(s, jid))
            return 0
        if hang:                                  # queued, and run when qstat first asks
            job["lazy"] = True
            save(s)
            time.sleep(float(os.environ.get("FAKE_PBS_HANG_S", "5")))
            print("qsub: connection to server lost", file=sys.stderr)
            return 1
        save(s)
        if MODE in ("run", "lost") or MODE.startswith(("full:", "hang:", "noid:")):
            if MODE != "lost":
                s = run_job(s, jid)
        elif MODE in ("hold", "undeletable"):
            s["jobs"][jid]["state"] = "R"
        save(s)
        print(jid)
        return 0
    if cmd == "qstat":
        if "-u" in args:
            save(s)
            rows = ["", "server:", "Job ID                         Username        Queue           "
                    "Jobname         SessID   NDS  TSK   Memory Time  S Time",
                    "------------------------------ --------------- --------------- "
                    "--------------- -------- ---- ----- ------ ----- - -----"]
            for jid, job in s["jobs"].items():
                if job["state"] == "F" and not HISTORY:
                    continue                      # ended, and the server keeps no history
                rows.append(f"{jid:<30} {job.get('user', 'u'):<15} {'testq':<15} "
                            f"{job.get('name', ''):<15} {'1234':>8} {'1':>4} {'1':>5} "
                            f"{'1gb':>6} {'00:10':>5} {job['state']} 00:00")
            print("\n".join(rows))
            return 0
        jid = args[-1]
        job = s["jobs"].get(jid)
        if job is not None and job.get("lazy") and MODE != "lost":
            save(s)
            s = run_job(s, jid)
            job = s["jobs"][jid]
        save(s)
        if job is None or MODE == "lost" or (job["state"] == "F" and not HISTORY):
            print(f"qstat: Unknown Job Id {jid}", file=sys.stderr)
            return 153
        lines = [f"Job Id: {jid}", f"    Job_Name = {job.get('name', '')}",
                 f"    job_state = {job['state']}"]
        if job["state"] == "F" and job["exit"] is not None:
            lines.append(f"    Exit_status = {job['exit']}")
        if job.get("comment"):                    # as a seeded held job carries one
            lines += wrapped("comment", job["comment"])
        env = {"PBS_O_HOME": "/var/pbs/u", "PBS_O_LANG": "C", "PBS_O_LOGNAME": "u",
               "PBS_O_PATH": "/usr/local/bin:/usr/bin:/bin:/opt/pbs/bin:/opt/site/bin",
               **job.get("vars", {}),
               "PBS_O_WORKDIR": "/var/pbs/u/work", "PBS_O_SYSTEM": "Linux"}
        lines += wrapped("Variable_List", ",".join(f"{k}={v}" for k, v in env.items()))
        print("\n".join(lines))
        return 0
    if cmd == "qdel":
        jid = args[-1]
        job = s["jobs"].get(jid)
        if job is None:
            save(s)
            print(f"qdel: Unknown Job Id {jid}", file=sys.stderr)
            return 153
        if MODE != "undeletable":
            job.update(state="F", exit=271, lazy=False)
        save(s)
        return 0
    print(f"fake_pbs: unknown command {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
