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
    expected product that is missing. The executor reads the exit from that seal first, then from
    qstat's Exit_status; with neither, the exit is unknown - which is a death, never a zero;
  - a stop is a qdel CONFIRMED by qstat (E5): a job that cannot be confirmed gone reports
    `stopped: false`, and the kernel fails the unmount on it.

The kernel itself still runs inside a scheduler job (nothing computes on a login node); `pbs`
sends each plugin run to its own job, the shape a tool's own `--executor pbs` has.
"""
from __future__ import annotations

import os
import re
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


class PbsHandle:
    """One submitted job. The same four independent facts as a local handle (E5), plus the job id
    and the seal the exit was read from."""

    def __init__(self, job, jobdir, qstat, qdel, timeout, cfg):
        self.job, self.jobdir, self.qstat, self.qdel = job, Path(jobdir), qstat, qdel
        self.timeout = timeout
        self.poll = float(cfg.get("poll_s", 30))
        self.grace = float(cfg.get("stop_grace_s", 120))
        self.visibility = float(cfg.get("seal_visibility_s", 120))
        self.started = time.perf_counter()
        self.log = None
        self.done = False
        self.facts = {"requested": False, "stopped": False, "timed_out": False, "exit": None,
                      "seconds": None, "executor": "pbs", "job": job, "seal": None}

    def state(self) -> tuple:
        """(job_state or None, Exit_status or None, known). `known` is False when qstat failed
        for a reason other than not knowing the job, which confirms nothing either way."""
        r = subprocess.run(self.qstat + ["-x", "-f", self.job], capture_output=True, text=True)
        st = re.search(r"job_state\s*=\s*(\w)", r.stdout or "")
        ex = re.search(r"Exit_status\s*=\s*(-?\d+)", r.stdout or "")
        if r.returncode != 0 and not st:
            return None, None, "unknown job" in ((r.stderr or "") + (r.stdout or "")).lower()
        return (st.group(1) if st else None), (int(ex.group(1)) if ex else None), True

    @staticmethod
    def _ended(st, ex, known) -> bool:
        return st == "F" or ex is not None or (st is None and known)

    def running(self) -> bool:
        if self.done:
            return False
        return not self._ended(*self.state())

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
            unknown = 0 if (st is not None or known) else unknown + 1
            if self._ended(st, ex, known) or unknown >= 5:
                break
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
        if not self._ended(st, ex, known):
            subprocess.run(self.qdel + [self.job], capture_output=True, text=True)
            deadline = time.monotonic() + grace
            while True:
                st, ex, known = self.state()
                if self._ended(st, ex, known) or time.monotonic() >= deadline:
                    break
                time.sleep(min(1.0, max(grace / 20, 0.01)))
        self.facts["stopped"] = self._ended(st, ex, known)
        if self.facts["stopped"]:
            self.done = True
            self._outcome(ex)
        self.facts["seconds"] = round(time.perf_counter() - self.started, 3)
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

    def _script(self, argv, cwd, log_path, env, scrub, name, expect, cfg, jobdir) -> str:
        q = shlex.quote
        lines = ["#!/bin/bash", f"#PBS -N {self._job_name(name)}", f"#PBS -q {cfg['queue']}",
                 f"#PBS -l select={cfg['select']}", f"#PBS -l walltime={cfg['walltime']}",
                 f"#PBS -o {jobdir}/", "#PBS -j oe"]
        if cfg.get("account"):
            lines.append(f"#PBS -P {cfg['account']}")
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

    def _submit(self, qsub: list, script: Path, cfg: dict) -> str:
        budget = float(cfg.get("queue_full_wait_s", 6 * 3600))
        pause = float(cfg.get("queue_full_first_wait_s", 30))
        deadline = time.monotonic() + budget
        while True:
            r = subprocess.run(qsub + [str(script)], capture_output=True, text=True)
            why = (r.stderr or r.stdout or "").strip()
            if r.returncode == 0:
                break
            if not QUEUE_FULL.search(why) or time.monotonic() + pause > deadline:
                raise ExecutorError(f"executor pbs: qsub refused {script}: {why}")
            time.sleep(pause)
            pause = min(pause * 2, 300.0)
        m = _JOB_ID.search(r.stdout or "")
        if not m:
            raise ExecutorError(f"executor pbs: qsub printed no job id: {r.stdout!r}")
        return m.group(1)

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
        script.write_text(self._script(argv, cwd, log_path, env, scrub, name, expect, cfg, jobdir),
                          encoding="utf-8")
        h = PbsHandle(self._submit(qsub, script, cfg), jobdir, qstat, qdel, timeout, cfg)
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
