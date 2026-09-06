"""Executors: where an entry point physically runs, and how it is stopped.

E5  A disposer reaches quiescence. `Handle.stop()` requests termination, waits, escalates, and
    reports four INDEPENDENT facts — requested, stopped, timed_out, exit — because a job can time
    out AND exit 0 by trapping the signal, and a flag nested inside another's branch reads a
    cut-short run as a clean one.

The local executor runs a subprocess. A PBS executor is Phase 9 and is not shipped here; the
kernel refuses `executor: pbs` with that sentence rather than pretending.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from ..core import Service

SCRATCH_ENV_ALLOW = ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "TERM")


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
               timeout: float | None = None, scrub: bool = False) -> Handle:
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

    def run(self, argv, cwd, log_path, env=None, timeout=None, scrub=False) -> dict:
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


def make_executor(kind: str, interpreters=None) -> Service:
    if kind in ("local", None, ""):
        return LocalExecutor(interpreters)
    if kind == "pbs":
        return RefusedExecutor("pbs", "not shipped before ROADMAP Phase 9; run the kernel inside "
                               "a PBS job with executor local, as the site rules require")
    return RefusedExecutor(kind, "unknown executor")
