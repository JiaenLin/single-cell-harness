"""Executors: where an entry point physically runs, and how it is stopped.

E5  A disposer reaches quiescence. `Handle.stop()` requests termination, waits, escalates, and
    reports four INDEPENDENT facts — requested, stopped, timed_out, exit — because a job can time
    out AND exit 0 by trapping the signal, and a flag nested inside another's branch reads a
    cut-short run as a clean one.

`local` runs a subprocess. `pbs` (harness W010; ADR-0029 withdrew the "Phase 9" stop that refused
it) submits each run as a PBS job:

  - nothing about a site is in here. The queue, the `select` and the walltime come from the stack's
    `pbs:` block - the site layer or the project - and a missing one is refused before any qsub;
  - the run directory exists before qsub (the kernel made it), and the executor's own `pbs/` inside
    it is made with a bare mkdir, so a second writer aborts instead of sharing it;
  - the JOB seals: an EXIT trap writes SEALED.txt or FAILED.txt with its exit, its job id and any
    expected product that is missing. Once a job has ended - by qstat's word, or, while qstat says
    nothing, by its seal being there - the exit is the seal's; without a seal, qstat's
    Exit_status; with neither, unknown. The kernel treats every exit but 0, unknown included, as a
    death, even when the run left an out.json (verifier W010 F1);
  - a qstat that cannot say - failing, timing out (`pbs.qstat_timeout_s`, 60), or answering 0 with
    nothing in it - is not the job ending. A job that sealed meanwhile has ended, by its seal
    (W010b D1). Otherwise, after `pbs.qstat_outage_polls` such polls in a row (5, at least 1)
    `wait` stops with `stopped: false` and leaves the handle live (W010 F2);
  - a stop is a qdel (with the same timeout) CONFIRMED by qstat or by the job's seal (E5). A job
    that cannot be confirmed ended within `pbs.stop_grace_s` reports `stopped: false`, and the
    kernel fails the disposal on it, as an error the command reports;
  - qsub itself has a timeout (`pbs.qsub_timeout_s`, 120). One that times out - or exits 0 and
    prints no job id - may already have queued the job, so nothing is submitted again until the
    scheduler is asked BY JOB NAME (`qstat -x -w -u <user>`), each job of that name confirmed by
    the submission's own token (`#PBS -v SCH_SUBMISSION=...`, in `qstat -x -f`). Found, that job
    is the run's. Absent - twice in a row, from a listing that showed the user's jobs - it is
    submitted again, at most `pbs.qsub_retries` (2) times. If the scheduler cannot say, nothing is
    resubmitted: the run is refused naming the job and the token, and the executor keeps the
    submission, so its disposer asks again and qdels the job if it is there, or fails E5 (autodev
    W029, GAP-C59). A qsub refused with an exit status - a full queue - created no job, and is
    retried as before.

The kernel itself still runs inside a scheduler job (nothing computes on a login node); `pbs`
sends each plugin run to its own job, the shape a tool's own `--executor pbs` has.
"""
from __future__ import annotations

import getpass
import os
import re
import secrets
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

from ..core import Service

SCRATCH_ENV_ALLOW = ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "TERM")


class ExecutorError(ValueError):
    """An executor that cannot run what it was asked to, said before anything ran. A ValueError,
    so a mount records it as a refusal with its reason instead of unwinding."""


class Handle:
    def __init__(self, proc, log, started, timeout):
        self.proc = proc
        self.log = log
        self.started = started
        self.timeout = timeout
        self.facts = {"requested": False, "stopped": False, "timed_out": False,
                      "exit": None, "seconds": None}

    def wait(self) -> dict:
        try:
            self.proc.wait(timeout=self.timeout)
        except subprocess.TimeoutExpired:
            self.facts["timed_out"] = True
            self.stop()
        self.facts["exit"] = self.proc.returncode
        self.facts["stopped"] = self.proc.poll() is not None
        self.facts["seconds"] = round(time.perf_counter() - self.started, 3)
        return self.facts

    def running(self) -> bool:
        return self.proc.poll() is None

    def stop(self, grace: float = 3.0) -> dict:
        """Request, wait, escalate, confirm. Never returns while the process is running."""
        self.facts["requested"] = True
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=grace)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                try:
                    self.proc.wait(timeout=grace)
                except subprocess.TimeoutExpired:
                    pass
        self.facts["stopped"] = self.proc.poll() is not None
        self.facts["exit"] = self.proc.returncode
        self.facts["seconds"] = round(time.perf_counter() - self.started, 3)
        return dict(self.facts)


class LocalExecutor(Service):
    kind = "local"

    def __init__(self, interpreters: dict | None = None):
        self.interpreters = dict(interpreters or {})
        self.handles: list[Handle] = []

    def interpreter(self, language: str, plugin_name: str = "") -> list:
        env_key = "SCH_INTERP_" + plugin_name.upper().replace("-", "_").replace("@", "_")
        if os.environ.get(env_key):
            return [os.environ[env_key]]
        if plugin_name in self.interpreters:
            return [self.interpreters[plugin_name]]
        if language in self.interpreters:
            return [self.interpreters[language]]
        if language == "python":
            return [sys.executable]
        if language == "r":
            return ["Rscript"]
        if language in ("sh", "bash"):
            return ["bash"]
        return []

    def launch(self, argv: list, cwd, log_path, env: dict | None = None,
               timeout: float | None = None, scrub: bool = False, name: str | None = None,
               expect: list | None = None) -> Handle:
        Path(log_path).parent.mkdir(parents=True, exist_ok=True)
        base = {k: v for k, v in os.environ.items() if not scrub or k in SCRATCH_ENV_ALLOW
                or k.startswith("SCH_")}
        if env:
            base.update(env)
        log = open(log_path, "ab")
        proc = subprocess.Popen(argv, cwd=str(cwd), env=base, stdout=log, stderr=subprocess.STDOUT)
        h = Handle(proc, log, time.perf_counter(), timeout)
        self.handles.append(h)
        return h

    def run(self, argv, cwd, log_path, env=None, timeout=None, scrub=False, name=None,
            expect=None) -> dict:
        h = self.launch(argv, cwd, log_path, env, timeout, scrub)
        try:
            return h.wait()
        finally:
            h.log.close()

    def quiesce(self) -> dict:
        """Disposer: stop everything this executor started and report the facts (E5)."""
        facts = {"requested": False, "stopped": True, "handles": []}
        for h in self.handles:
            if h.running():
                facts["requested"] = True
                f = h.stop()
                facts["handles"].append(f)
                if not f["stopped"]:
                    facts["stopped"] = False
            try:
                h.log.close()
            except Exception:
                pass
        self.handles = []
        return facts


class RefusedExecutor(Service):
    """Stands in for an executor this kernel does not ship, and says so."""
    kind = "refused"

    def __init__(self, name: str, why: str):
        self.why = f"executor {name!r}: {why}"

    def launch(self, *a, **k):
        raise RuntimeError(self.why)

    def run(self, *a, **k):
        raise RuntimeError(self.why)

    def quiesce(self):
        return {"requested": False, "stopped": True}


# ---------------------------------------------------------------------------- pbs
#: What a `pbs:` block must declare. The harness holds no value for any of them: a queue name or a
#: resource written here would be one site's, and wrong - silently - at the next.
PBS_REQUIRED = ("queue", "select", "walltime")
#: The scheduler's three commands: from PATH, unless the block declares them (`pbs.commands`).
PBS_COMMANDS = ("qsub", "qstat", "qdel")
#: The two seals a job's EXIT trap may write, in the order they are looked for.
SEALS = ("SEALED.txt", "FAILED.txt")
#: A qsub refused because a queue's per-user limit is full, not because the job is wrong. It clears
#: when any of the user's jobs leaves the queue, so it is waited for (scQC's lesson: ADR-0027 Q11).
QUEUE_FULL = re.compile(r"would exceed|maximum number of jobs", re.I)
_JOB_ID = re.compile(r"^\s*(\d+\S*)\s*$", re.M)
#: A job id as qstat's listing writes it in its first column: `1234.server`, an array's `1234[]`.
_JOB_ROW = re.compile(r"^\d+(\[\d*\])?(\.[\w.-]+)?$")
#: The environment variable a job's script declares (`#PBS -v`) to carry its submission's token.
SUBMISSION = "SCH_SUBMISSION"
#: A HOLD THE SCHEDULER PUTS ON A JOB IT COULD NOT START, measured on PBS 783349 (2026-11-10): after
#: four failed attempts to run it, PBS Pro held it (`job_state = H`, `comment = job held, too many
#: failed attempts to run`), and it stays held until a person releases or deletes it. Waiting on it
#: is waiting for ever: the handle returns at once with the hold in its facts and the exit unknown,
#: which the kernel reads as a death, and the disposer qdels it, which a held job allows.
HELD_FOR_GOOD = re.compile(r"too many failed attempts", re.I)


class PbsHandle:
    """One submitted job. The same four independent facts as a local handle (E5), plus the job id
    and the seal the exit was read from."""

    def __init__(self, job, jobdir, qstat, qdel, timeout, cfg):
        self.job, self.jobdir, self.qstat, self.qdel = job, Path(jobdir), qstat, qdel
        self.timeout = timeout
        self.poll = float(cfg.get("poll_s", 30))
        self.grace = float(cfg.get("stop_grace_s", 120))
        self.visibility = float(cfg.get("seal_visibility_s", 120))
        # How many polls in a row qstat may say nothing before `wait` stops waiting for an outage;
        # at least one, or a job qstat could see running was given up on at its first poll.
        self.outage_polls = max(1, int(cfg.get("qstat_outage_polls", 5)))
        # How long one qstat or qdel may take. One that takes longer said nothing (verifier W010b
        # D2): before, a qstat that blocked held wait, stop and quiesce for as long as it blocked.
        self.cmd_timeout = float(cfg.get("qstat_timeout_s", 60))
        self.started = time.perf_counter()
        self.log = None
        self.done = False
        self.comment = None             # the scheduler's last `comment` on the job, if any
        self.facts = {"requested": False, "stopped": False, "timed_out": False, "exit": None,
                      "seconds": None, "executor": "pbs", "job": job, "seal": None}

    def state(self) -> tuple:
        """(job_state or None, Exit_status or None, known).

        `known` is True when the scheduler said something about the job: its state, its exit, or
        that it no longer knows it ("Unknown Job Id"), which a finished job ends as. Anything else -
        qstat failing, or answering 0 with nothing in it - says nothing either way (verifier W010
        F2): an outage is not an ending."""
        try:
            r = subprocess.run(self.qstat + ["-x", "-f", self.job], capture_output=True, text=True,
                               timeout=self.cmd_timeout)
        except subprocess.TimeoutExpired:
            return None, None, False
        st = re.search(r"job_state\s*=\s*(\w)", r.stdout or "")
        ex = re.search(r"Exit_status\s*=\s*(-?\d+)", r.stdout or "")
        cm = re.search(r"^\s*comment\s*=\s*(.+?)\s*$", (r.stdout or "").replace("\n\t", ""), re.M)
        if st or ex:
            self.comment = cm.group(1) if cm else None
            return (st.group(1) if st else None), (int(ex.group(1)) if ex else None), True
        said = ((r.stderr or "") + (r.stdout or "")).lower()
        return None, None, r.returncode != 0 and "unknown job" in said

    @staticmethod
    def _ended(st, ex, known) -> bool:
        return st == "F" or ex is not None or (st is None and known)

    def _sealed(self) -> bool:
        """Has the job written its seal? The seal is the job's EXIT trap's last act, so a job
        with one has ended, whatever the scheduler can be asked (verifier W010b D1)."""
        try:
            names = set(os.listdir(self.jobdir))
        except OSError:
            return False
        return any(n in names for n in SEALS)

    def _over(self, st, ex, known) -> bool:
        """Ended by the scheduler's word, or - when it says nothing - by the job's own seal."""
        return self._ended(st, ex, known) or (not known and self._sealed())

    def running(self) -> bool:
        if self.done:
            return False
        return not self._over(*self.state())

    def _outcome(self, ex):
        """The exit from the job's own seal; else the scheduler's; else unknown. The seal is
        re-listed rather than stat'ed, because a client caches the absence of a name it already
        looked up and a stat answers from that cache (scQC's NFS lesson)."""
        deadline = time.monotonic() + self.visibility
        seal = None
        while seal is None:
            try:
                names = set(os.listdir(self.jobdir))
            except OSError:
                names = set()
            seal = next((self.jobdir / n for n in SEALS if n in names), None)
            if seal is None:
                if time.monotonic() >= deadline:
                    break
                time.sleep(min(1.0, self.visibility))
        if seal is not None:
            self.facts["seal"] = str(seal)
            m = re.search(r"^exit=(-?\d+)\s*$", seal.read_text(encoding="utf-8"), re.M)
            if m:
                self.facts["exit"] = int(m.group(1))
        if self.facts["exit"] is None and ex is not None:
            self.facts["exit"] = ex

    def wait(self) -> dict:
        pause, unknown = min(2.0, self.poll), 0
        while True:
            st, ex, known = self.state()
            if self._over(st, ex, known):
                break
            if st == "H" and self.comment and HELD_FOR_GOOD.search(self.comment):
                # HELD BY THE SCHEDULER FOR GOOD (PBS 783349): not ended, and never going to run.
                # The handle stays live with the exit unknown, so the kernel reads a death and the
                # disposer qdels the job and confirms it, instead of waiting for ever.
                self.facts["held"] = self.comment
                self.facts["seconds"] = round(time.perf_counter() - self.started, 3)
                return dict(self.facts)
            unknown = unknown + 1 if not known else 0
            if unknown >= self.outage_polls:
                # THE SCHEDULER CANNOT SAY, which is not the job ending (verifier W010 F2). Give up
                # waiting with stopped=false and leave the handle live: the exit stays unknown (a
                # death to the kernel), and quiesce sends qdel and confirms it, or fails E5.
                self.facts["seconds"] = round(time.perf_counter() - self.started, 3)
                return dict(self.facts)
            if self.timeout is not None and time.perf_counter() - self.started > self.timeout:
                self.facts["timed_out"] = True
                return self.stop()
            time.sleep(pause)
            pause = min(pause * 2, self.poll)
        self.facts["stopped"] = True
        self.done = True
        self._outcome(ex)
        self.facts["seconds"] = round(time.perf_counter() - self.started, 3)
        return dict(self.facts)

    def stop(self, grace: float | None = None) -> dict:
        """qdel, then CONFIRM through qstat. Never reports stopped on a job it cannot see end."""
        self.facts["requested"] = True
        grace = self.grace if grace is None else grace
        st, ex, known = self.state()
        if not self._over(st, ex, known):
            try:
                subprocess.run(self.qdel + [self.job], capture_output=True, text=True,
                               timeout=self.cmd_timeout)
            except subprocess.TimeoutExpired:
                pass                                # confirmed below, or reported unconfirmed
            deadline = time.monotonic() + grace
            while True:
                st, ex, known = self.state()
                if self._over(st, ex, known) or time.monotonic() >= deadline:
                    break
                time.sleep(min(1.0, max(grace / 20, 0.01)))
        self.facts["stopped"] = self._over(st, ex, known)
        if self.facts["stopped"]:
            self.done = True
            self._outcome(ex)
        self.facts["seconds"] = round(time.perf_counter() - self.started, 3)
        return dict(self.facts)


class PendingSubmission:
    """A qsub whose outcome nobody could establish: it may have queued a job, which then runs with
    nothing watching it (autodev W029, GAP-C59). Kept by the executor so that its disposer asks the
    scheduler again: the job, found by its token, is stopped and confirmed like any other; found
    absent, there is nothing to stop; and while the scheduler still cannot say, `stopped` is false
    and E5 fails the disposal, loudly."""

    def __init__(self, executor, qstat, qdel, cfg, name, token, jobdir):
        self.executor, self.qstat, self.qdel, self.cfg = executor, qstat, qdel, cfg
        self.name, self.token, self.jobdir = name, token, jobdir
        self.log = None
        self.facts = {"requested": False, "stopped": False, "timed_out": False, "exit": None,
                      "seconds": None, "executor": "pbs", "job": None, "submission": token}

    def running(self) -> bool:
        return True                     # not known to have ended, so a disposer must ask

    def stop(self, grace: float | None = None) -> dict:
        self.facts["requested"] = True
        verdict, jobs, said = self.executor._reconcile(self.qstat, self.cfg, self.name, self.token)
        self.facts["reconcile"] = said
        if verdict == "absent":
            self.facts["stopped"] = True
        elif verdict == "found":
            stops = [PbsHandle(j, self.jobdir, self.qstat, self.qdel, None, self.cfg).stop(grace)
                     for j in jobs]
            self.facts.update(job=",".join(jobs), stopped=all(f["stopped"] for f in stops),
                              exit=stops[0]["exit"])
        else:
            self.facts["stopped"] = False
        return dict(self.facts)


class PbsExecutor(LocalExecutor):
    kind = "pbs"

    def __init__(self, interpreters: dict | None = None, config: dict | None = None):
        super().__init__(interpreters)
        self.config = dict(config or {})

    def settings(self, name: str | None = None) -> dict:
        """The `pbs:` block, with `pbs.plugins.<name>` laid over it for this run."""
        base = {k: v for k, v in self.config.items() if k != "plugins"}
        return {**base, **dict((self.config.get("plugins") or {}).get(name or "") or {})}

    @staticmethod
    def _command(cfg: dict, which: str) -> list:
        found = (cfg.get("commands") or {}).get(which) or shutil.which(which)
        if not found:
            raise ExecutorError(f"executor pbs: {which!r} is not on PATH and pbs.commands.{which} "
                                f"is not declared; load the scheduler's environment where sch runs, "
                                f"or declare the command")
        return [str(found)]

    @staticmethod
    def _job_name(name) -> str:
        return "sch_" + re.sub(r"[^A-Za-z0-9_]", "_", str(name or "run"))[:11]

    def _script(self, argv, cwd, log_path, env, scrub, name, expect, cfg, jobdir,
                token: str | None = None) -> str:
        q = shlex.quote
        lines = ["#!/bin/bash", f"#PBS -N {self._job_name(name)}", f"#PBS -q {cfg['queue']}",
                 f"#PBS -l select={cfg['select']}", f"#PBS -l walltime={cfg['walltime']}",
                 f"#PBS -o {jobdir}/", "#PBS -j oe"]
        if cfg.get("account"):
            lines.append(f"#PBS -P {cfg['account']}")
        if token:
            # WHICH SUBMISSION THIS IS, where qstat shows it (its Variable_List): a job name is
            # shared by every run of one plugin, so a qsub that timed out is told apart from an
            # earlier job of the same name by this, and by nothing else (GAP-C59)
            lines.append(f"#PBS -v {SUBMISSION}={token}")
        if not scrub:
            lines.append("#PBS -V")     # the run sees the environment sch runs in, as `local`'s does
        products = " ".join(q(str(p)) for p in (expect or []))
        lines += [
            "set -euo pipefail",
            f"JOBDIR={q(str(jobdir))}",
            "# THE JOB SEALS ITS RUN: the exit, the job id and every expected product, checked -",
            "# a seal reading only $? writes a green light on a run whose product never appeared.",
            "finish() {",
            "  s=$?",
            "  set +e",
            "  miss=''",
            f"  for p in {products}; do [ -s \"$p\" ] || miss=\"$miss $p\"; done" if products else "",
            "  if [ -n \"$miss\" ] && [ \"$s\" -eq 0 ]; then s=97; fi",
            "  seal=SEALED.txt; [ \"$s\" -eq 0 ] || seal=FAILED.txt",
            "  { echo \"exit=$s\"; echo \"jobid=${PBS_JOBID:-none}\"; echo \"host=$(hostname)\"",
            "    echo \"finished=$(date -u +%Y-%m-%dT%H:%M:%SZ)\"",
            "    if [ -n \"$miss\" ]; then echo \"missing=$miss\"; fi; } > \"$JOBDIR/$seal\"",
            "  exit \"$s\"",
            "}",
            "trap finish EXIT",
            "# killed is not clean: the scheduler's TERM at walltime, an INT or a HUP seal FAILED",
            "trap 'exit 143' TERM; trap 'exit 130' INT; trap 'exit 129' HUP",
            f"exec >> {q(str(log_path))} 2>&1",
            f"cd {q(str(cwd))}",
        ]
        exported = dict(env or {})
        if scrub:
            exported = {**{k: v for k, v in os.environ.items()
                           if k in SCRATCH_ENV_ALLOW or k.startswith("SCH_")}, **exported}
        lines += [f"export {k}={q(str(v))}" for k, v in exported.items()]
        lines.append(" ".join(q(str(a)) for a in argv))
        return "\n".join(x for x in lines if x != "") + "\n"

    def _by_name(self, qstat: list, cfg: dict, name, token) -> tuple:
        """One look at the scheduler: ("found", job, said), ("absent", None, said) or
        ("unknown", None, said). The user's jobs are listed (`qstat -x -w -u`, finished ones
        included), those with this run's job name kept, and each confirmed by the submission's
        token in its `qstat -x -f`. An empty listing says nothing: the kernel runs inside a job,
        so its user always has one, and an answer with none in it may be an outage."""
        limit = float(cfg.get("qstat_timeout_s", 60))
        jobname = self._job_name(name)
        user = os.environ.get("USER") or os.environ.get("LOGNAME")
        if not user:
            try:
                user = getpass.getuser()
            except (KeyError, OSError):
                return "unknown", None, "no user to ask qstat about"
        try:
            r = subprocess.run(qstat + ["-x", "-w", "-u", user], capture_output=True, text=True,
                               timeout=limit)
        except subprocess.TimeoutExpired:
            return "unknown", None, f"qstat -u {user} did not answer within {limit:g}s"
        if r.returncode != 0:
            return "unknown", None, (f"qstat -u {user} failed: "
                                     f"{(r.stderr or r.stdout or '').strip()[:160]}")
        rows = [ln.split() for ln in (r.stdout or "").splitlines()]
        listed = [x for x in rows if x and _JOB_ROW.match(x[0])]
        if not listed:
            return "unknown", None, (f"qstat listed no job of {user}'s, and an answer with nothing "
                                     f"in it may be an outage")
        mine = []
        for job in [x[0] for x in listed if len(x) > 3 and x[3] == jobname]:
            try:
                f = subprocess.run(qstat + ["-x", "-f", job], capture_output=True, text=True,
                                   timeout=limit)
            except subprocess.TimeoutExpired:
                return "unknown", None, f"qstat -f {job} did not answer within {limit:g}s"
            # a long attribute is wrapped onto lines that begin with a tab; joined, it is whole
            text = (f.stdout or "").replace("\n\t", "")
            if f.returncode != 0 or "Job_Name" not in text:
                return "unknown", None, f"qstat -f {job} said nothing about it"
            if re.search(rf"(^|[\s,=]){SUBMISSION}={re.escape(token)}(,|\s|$)", text):
                mine.append(job)
        mine.sort(key=lambda j: int(re.match(r"\d+", j).group(0)))
        said = (f"{len(listed)} job(s) of {user}'s listed; {len(mine)} carry this submission's "
                f"token {token}")
        if mine:
            return "found", mine, said
        return "absent", None, said

    def _reconcile(self, qstat: list, cfg: dict, name, token) -> tuple:
        """Ask the scheduler whether this submission queued a job, until it can say: found at
        once (the jobs carrying its token, oldest first); absent only when two looks in a row say
        so (a job a slow server has not yet listed must not be submitted twice); unknown after
        `pbs.qstat_outage_polls` looks."""
        polls = max(2, int(cfg.get("qstat_outage_polls", 5)))
        poll = float(cfg.get("poll_s", 30))
        pause, absent, said = min(2.0, poll), 0, ""
        for i in range(polls):
            verdict, jobs, said = self._by_name(qstat, cfg, name, token)
            if verdict == "found":
                return verdict, jobs, said
            absent = absent + 1 if verdict == "absent" else 0
            if absent >= 2:
                return "absent", None, said
            if i + 1 < polls:
                time.sleep(pause)
                pause = min(pause * 2, poll)
        return "unknown", None, said

    def _submit(self, qsub: list, script: Path, cfg: dict, qstat: list | None = None, name=None,
                token: str | None = None, qdel: list | None = None) -> tuple:
        """(job id, what reconciling found or None). A qsub refused with an exit status created no
        job: a full queue is waited for and the job submitted again, as before. A qsub that timed
        out, or exited 0 with no id, may have queued it, and is never followed by another before
        the scheduler has been asked (`_reconcile`)."""
        budget = float(cfg.get("queue_full_wait_s", 6 * 3600))
        pause = float(cfg.get("queue_full_first_wait_s", 30))
        limit = float(cfg.get("qsub_timeout_s", 120))
        retries = max(0, int(cfg.get("qsub_retries", 2)))
        deadline = time.monotonic() + budget
        unsure = 0
        while True:
            try:
                r = subprocess.run(qsub + [str(script)], capture_output=True, text=True,
                                   timeout=limit)
            except subprocess.TimeoutExpired:
                r, why = None, f"qsub did not answer within {limit:g}s (pbs.qsub_timeout_s)"
            else:
                why = (r.stderr or r.stdout or "").strip()
                if r.returncode == 0:
                    m = _JOB_ID.search(r.stdout or "")
                    if m:
                        return m.group(1), None
                    r, why = None, f"qsub exited 0 and printed no job id: {r.stdout!r}"
            if r is not None:                       # refused: the scheduler created no job
                if not QUEUE_FULL.search(why) or time.monotonic() + pause > deadline:
                    raise ExecutorError(f"executor pbs: qsub refused {script}: {why}")
                time.sleep(pause)
                pause = min(pause * 2, 300.0)
                continue
            if not (qstat and token):               # nothing to ask: never submit twice blind
                raise ExecutorError(f"executor pbs: {why}; it may have queued the job, and "
                                    f"nothing here can ask, so nothing was submitted again")
            verdict, jobs, said = self._reconcile(qstat, cfg, name, token)
            if verdict == "found":
                # two jobs of one submission would be a double already: the oldest is the run's,
                # and every other is stopped now, and kept, so a disposer confirms it (E5)
                for extra in jobs[1:]:
                    h = PbsHandle(extra, script.parent, qstat, qdel or [], None, cfg)
                    h.stop()
                    self.handles.append(h)
                return jobs[0], {"after": why, "found": jobs[0], "stopped": jobs[1:],
                                 "said": said}
            if verdict == "absent" and unsure < retries:
                unsure += 1
                continue
            if verdict == "unknown":
                self.handles.append(PendingSubmission(self, qstat, qdel or [], cfg, name, token,
                                                      script.parent))
                raise ExecutorError(
                    f"executor pbs: {why}, and the scheduler cannot say whether it queued the job "
                    f"({said}). Nothing was submitted again, so no job is doubled. Look for job "
                    f"{self._job_name(name)} with {SUBMISSION}={token} (qstat -x -f): qdel it, or "
                    f"let it end, before mounting again")
            raise ExecutorError(f"executor pbs: {why}; the scheduler holds no such job ({said}), "
                                f"and {unsure + 1} submission(s) have gone unanswered "
                                f"(pbs.qsub_retries {retries})")

    def launch(self, argv: list, cwd, log_path, env: dict | None = None,
               timeout: float | None = None, scrub: bool = False, name: str | None = None,
               expect: list | None = None) -> PbsHandle:
        cfg = self.settings(name)
        missing = [k for k in PBS_REQUIRED if not cfg.get(k)]
        if missing:
            raise ExecutorError(
                f"executor pbs: the declaration gives no {', '.join('pbs.' + k for k in missing)}. "
                f"The harness knows no site's queues or resources; declare them in the `pbs:` block "
                f"of the stack or of the site layer ($SCH_SITE/stack.yml)")
        qsub, qstat, qdel = (self._command(cfg, c) for c in PBS_COMMANDS)
        log_path = Path(log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        jobdir = log_path.parent / "pbs"
        try:
            jobdir.mkdir()          # bare: a second writer in one run directory stops here
        except FileExistsError:
            raise ExecutorError(f"executor pbs: {jobdir} exists; another job wrote this run, and a "
                                f"run has one writer") from None
        script = jobdir / "job.pbs"
        token = secrets.token_hex(6)
        script.write_text(self._script(argv, cwd, log_path, env, scrub, name, expect, cfg, jobdir,
                                       token), encoding="utf-8")
        job, reconciled = self._submit(qsub, script, cfg, qstat, name, token, qdel)
        h = PbsHandle(job, jobdir, qstat, qdel, timeout, cfg)
        if reconciled:                    # said in the run's facts; a plain submission is as before
            h.facts["reconciled"] = reconciled
        self.handles.append(h)
        return h

    def run(self, argv, cwd, log_path, env=None, timeout=None, scrub=False, name=None,
            expect=None) -> dict:
        return self.launch(argv, cwd, log_path, env, timeout, scrub, name, expect).wait()


def make_executor(kind: str, interpreters=None, config: dict | None = None) -> Service:
    if kind in ("local", None, ""):
        return LocalExecutor(interpreters)
    if kind == "pbs":
        return PbsExecutor(interpreters, config)
    return RefusedExecutor(kind, "unknown executor; this kernel ships local and pbs")
