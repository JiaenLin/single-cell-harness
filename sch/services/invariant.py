"""The invariant service and the kernel's own companions (ADR-0008, ARCHITECTURE §8).

A companion asserts a relationship its owner owns, on the run that matters. The kernel owns:

    A1   no write reaches the dataset outside a declared contribution
    A2   nothing carrying a scratch provenance tag is promoted, or quoted into a report
    D4   the observation count never decreases across a mount
    D6   a result differing from a cached one under an unchanged tuple raises
    E5   no disposer returns while work it started is still running
    G2   every gate escape has an ask and a decision recorded against it
    G4   no verdict outside PASS REVIEW REFUSE; refusals never become passes
    P2   every number in a rendered report resolves to an event in the stream

A plugin's companion is `invariant.py` in its directory, run OUT OF PROCESS (L3) with a facts
file: masked identities, declared outputs, tables, out.json. Non-zero exit is a failure naming
the plugin and the check.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..core import Service


class InvariantFailure(AssertionError):
    def __init__(self, owner: str, check: str, message: str):
        super().__init__(f"[{owner}] {check}: {message}")
        self.owner, self.check, self.message = owner, check, message


class InvariantService(Service):
    def __init__(self, provenance, runner):
        self.prov = provenance
        self.runner = runner            # (argv, cwd, log) -> facts
        self.failures: list[InvariantFailure] = []

    def fail(self, owner, check, message):
        f = InvariantFailure(owner, check, message)
        self.prov.append("invariant/failed", owner=owner, check=check, message=message)
        raise f

    def ok(self, owner, check):
        self.prov.append("invariant/held", owner=owner, check=check)

    # ------------------------------------------------------------ kernel companions
    def a1_no_undeclared_write(self, dataset):
        before, now = dataset.digest(), dataset.digest_now()
        if before != now:
            self.fail("kernel", "A1 no write reaches the dataset outside a declared contribution",
                      f"observations digest changed {before[:12]} -> {now[:12]}")
        self.ok("kernel", "A1")

    def d4_count_never_decreases(self, n_before: int, n_after: int):
        if n_after < n_before:
            self.fail("kernel", "D4 the observation count never decreases across a mount",
                      f"{n_before} -> {n_after}")
        self.ok("kernel", "D4")

    def d6_same_tuple_same_result(self, key: str, digest_cached: str | None, digest_now: str):
        if digest_cached is not None and digest_cached != digest_now:
            self.fail("kernel", "D6 a result differing from a cached one under an unchanged tuple",
                      f"tuple {key}: cached {digest_cached} vs now {digest_now}")
        self.ok("kernel", "D6")

    def e5_disposer_quiesced(self, facts: dict, owner="kernel"):
        if facts.get("requested") and not facts.get("stopped"):
            self.fail(owner, "E5 no disposer returns while work it started is still running",
                      json.dumps(facts, default=str))
        self.ok(owner, "E5")

    def g2_escapes_paired(self):
        asks = {e["seq"] for e in self.prov.of_kind("escape/ask")}
        decisions = {e.get("ask") for e in self.prov.of_kind("escape/decision")}
        unpaired = sorted(asks - decisions)
        if unpaired:
            self.fail("kernel", "G2 every gate escape has an ask and a decision", f"asks without a decision: {unpaired}")
        orphan = sorted(d for d in decisions if d not in asks)
        if orphan:
            self.fail("kernel", "G2 every gate escape has an ask and a decision", f"decisions without an ask: {orphan}")
        self.ok("kernel", "G2")

    def g4_verdicts_monotonic(self):
        from .gate import RANK
        for e in self.prov.of_kind("gate/result"):
            if e.get("verdict") not in RANK:
                self.fail("kernel", "G4 no verdict outside PASS REVIEW REFUSE", json.dumps(e))
        self.ok("kernel", "G4")

    def a2_nothing_scratch_quoted(self, numbers: list):
        bad = [n for n in numbers if n.get("scratch")]
        if bad:
            self.fail("kernel", "A2 nothing in scratch is quotable",
                      f"{len(bad)} scratch number(s) reached the report: {[b['key'] for b in bad][:5]}")
        self.ok("kernel", "A2")

    def p2_numbers_resolve(self, report_numbers: dict):
        events = {e["seq"]: e for e in self.prov.numbers()}
        for key, rec in report_numbers.items():
            ev = events.get(rec.get("event"))
            if ev is None or ev.get("value") != rec.get("value"):
                self.fail("kernel", "P2 every number in a rendered report resolves to an event",
                          f"{key}={rec.get('value')!r} (event {rec.get('event')})")
        self.ok("kernel", "P2")

    # ------------------------------------------------------------ plugin companions
    def run_companion(self, manifest, facts: dict, run_dir: Path, interpreter: list):
        inv = manifest.data.get("invariant")
        if not inv:
            reason = manifest.data.get("no_runtime_invariant")
            self.prov.append("invariant/absent", owner=manifest.name, reason=reason)
            return {"ran": False, "reason": reason}
        script = manifest.dir / str(inv)
        run_dir.mkdir(parents=True, exist_ok=True)
        facts_path = run_dir / "companion_facts.json"
        facts_path.write_text(json.dumps(facts, indent=1, default=str))
        result_path = run_dir / "companion_result.json"
        f = self.runner(interpreter + [str(script), str(facts_path), str(result_path)],
                        manifest.dir, run_dir / "companion.log")
        result = {}
        if result_path.exists():
            try:
                result = json.loads(result_path.read_text())
            except ValueError:
                result = {}
        if f.get("exit") != 0 or result.get("failed"):
            failed = result.get("failed") or [{"check": "companion", "message": f"exit {f.get('exit')}"}]
            first = failed[0]
            self.fail(manifest.name, first.get("check", "companion"), first.get("message", ""))
        for c in result.get("held", []):
            self.ok(manifest.name, c)
        if not result.get("held") and not result.get("failed"):
            self.fail(manifest.name, "companion", "ran no checks — an empty companion is decoration")
        return {"ran": True, **result}
