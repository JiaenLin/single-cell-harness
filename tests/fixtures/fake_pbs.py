#!/usr/bin/env python3
"""A stand-in for PBS Pro's `qsub`, `qstat` and `qdel`, for testing the `pbs` executor anywhere.

    fake_pbs.py qsub SCRIPT          prints a job id; by default RUNS the script now, with bash,
                                     as a job that finishes before qsub returns
    fake_pbs.py qstat -x -f JOBID    `job_state = R|F` and `Exit_status = N`, PBS Pro's words;
                                     an unknown job is refused as PBS refuses one
    fake_pbs.py qdel JOBID           ends a held job (Exit_status 271, as a signal-killed job)

It schedules nothing and enforces no resource: a test using it checks the executor around the
scheduler - the run directory before qsub, the seal the job writes, the exit read from the seal,
qdel confirmed - never a scheduler.

Environment:
    FAKE_PBS_STATE   the JSON file holding the jobs and every call (required)
    FAKE_PBS_MODE    run (default) | hold | undeletable | lost | full:N
                     hold: queued and never started until qdel; undeletable: qdel is accepted
                     and the job keeps running; lost: the job never runs and qstat forgets it;
                     full:N: the first N qsub calls are refused for a queue's per-user limit
"""
import json
import os
import subprocess
import sys
from pathlib import Path

STATE = Path(os.environ["FAKE_PBS_STATE"])
MODE = os.environ.get("FAKE_PBS_MODE", "run")


def load():
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {"next": 1000, "jobs": {}, "calls": []}


def save(s):
    STATE.write_text(json.dumps(s, indent=1))


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
        jid = f"{s['next']}.server"
        s["next"] += 1
        script = args[-1]
        job = {"script": script, "state": "Q", "exit": None}
        s["jobs"][jid] = job
        save(s)
        if MODE == "run" or MODE.startswith("full:"):
            r = subprocess.run(["bash", script], env={**os.environ, "PBS_JOBID": jid})
            s = load()
            s["jobs"][jid].update(state="F", exit=r.returncode)
        elif MODE in ("hold", "undeletable"):
            s["jobs"][jid]["state"] = "R"
        save(s)
        print(jid)
        return 0
    if cmd == "qstat":
        jid = args[-1]
        job = s["jobs"].get(jid)
        save(s)
        if job is None or MODE == "lost":
            print(f"qstat: Unknown Job Id {jid}", file=sys.stderr)
            return 153
        lines = [f"Job Id: {jid}", f"    job_state = {job['state']}"]
        if job["state"] == "F" and job["exit"] is not None:
            lines.append(f"    Exit_status = {job['exit']}")
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
            job.update(state="F", exit=271)
        save(s)
        return 0
    print(f"fake_pbs: unknown command {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
