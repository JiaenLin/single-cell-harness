"""Registration → a Runtime per plugin; lifecycle; state transitions; invalidation.

This module depends on `sch.core` only (L1). It never runs a plugin and never opens the data:
what a mount physically does — materialise, execute, merge — is the kernel's (`sch.kernel`),
which reaches the services through the Context. Here live the parts that must be right
regardless of domain: order, dependency, invalidation, and disposal in exactly reverse order.

States:   registered → mounted → invalid | rebuild | unmounted
          registered → refused          (a gate refused, or a prerequisite was missing)
          registered → died             (no out.json)
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from ..core import Context
from .manifest import Capability, Manifest, ManifestError, parse_capability

STATES = ("registered", "mounted", "invalid", "rebuild", "unmounted", "refused", "died")


class RegistryError(RuntimeError):
    pass


@dataclass
class MountResult:
    name: str
    status: str                       # mounted | refused | died | invalid-claim
    reason: str = ""
    fix: str = ""
    gates: list = field(default_factory=list)
    facts: dict = field(default_factory=dict)
    headline: str = ""
    undeclared: list = field(default_factory=list)
    seconds: float = 0.0

    @property
    def ok(self) -> bool:
        return self.status == "mounted"

    def to_dict(self) -> dict:
        return {"name": self.name, "status": self.status, "reason": self.reason, "fix": self.fix,
                "gates": self.gates, "facts": self.facts, "headline": self.headline,
                "undeclared": self.undeclared, "seconds": self.seconds}


@dataclass
class Runtime:
    name: str
    manifest: Manifest
    params: dict
    state: str = "registered"
    needs: list = field(default_factory=list)          # resolved Capabilities
    provides: list = field(default_factory=list)       # Capabilities as declared
    reads_from: list = field(default_factory=list)     # names of runtimes it depends on
    invalid_reason: str = ""
    mounted_at: float = 0.0
    escapes: dict = field(default_factory=dict)
    dir: Path | None = None
    fork: Context | None = None

    @property
    def layer(self) -> str:
        return self.manifest.layer

    @property
    def is_checkpoint(self) -> bool:
        return self.layer == "checkpoint"

    def fold_entry(self) -> tuple:
        return (self.name, self.manifest.version, self.manifest.state_version, self.params)

    def to_state(self) -> dict:
        return {"name": self.name, "state": self.state, "params": self.params,
                "plugin_dir": str(self.manifest.dir) if self.manifest.dir else None,
                "version": self.manifest.version, "state_version": self.manifest.state_version,
                "layer": self.layer, "reads_from": self.reads_from, "escapes": self.escapes,
                "invalid_reason": self.invalid_reason, "mounted_at": self.mounted_at}


class Registry:
    """Owns the ordered list of runtimes and every transition between their states."""

    def __init__(self, ctx: Context, contract_major: int):
        self.ctx = ctx
        self.contract_major = contract_major
        self.runtimes: list[Runtime] = []
        self.history: list[dict] = []          # (name, layer) as first mounted — A3 conversion check

    # ------------------------------------------------------------- lookup
    def get(self, name: str) -> Runtime | None:
        for r in self.runtimes:
            if r.name == name:
                return r
        return None

    def mounted(self) -> list:
        return [r for r in self.runtimes if r.state in ("mounted", "invalid", "rebuild")]

    def valid(self) -> list:
        return [r for r in self.runtimes if r.state == "mounted"]

    def order(self) -> list:
        return [r.name for r in self.runtimes]

    # ------------------------------------------------------------- admission
    def admit(self, manifest: Manifest, profile_accepts) -> tuple:
        """X1: compare the contract MAJOR only. Profile: refuse an unknown one rather than guess."""
        if manifest.contract_major is None:
            return False, f"{manifest.name}: manifest has no contract version", "add `contract: \"1.0\"`"
        if manifest.contract_major != self.contract_major:
            return False, (f"{manifest.name}: contract major {manifest.contract_major} is not "
                           f"{self.contract_major}"), "port the plugin to the current contract major"
        if not profile_accepts(manifest.profile):
            return False, (f"{manifest.name}: declares profile {manifest.profile!r}, which this stack "
                           f"does not serve"), "mount it on a stack declaring that profile"
        if manifest.layer not in ("stack", "checkpoint"):
            return False, f"{manifest.name}: layer {manifest.layer!r} is not stack|checkpoint", "declare layer"
        prior = [h for h in self.history if h["name"] == manifest.name]
        if prior and prior[-1]["layer"] == "checkpoint" and manifest.layer == "stack":
            return False, (f"{manifest.name}: was mounted as a checkpoint and now declares stack; "
                           f"a checkpoint cannot be converted to stack (A3)"), "keep layer: checkpoint"
        return True, "", ""

    # ------------------------------------------------------------- resolution
    def resolve(self, manifest: Manifest, keymap: dict, external_caps: list,
                capability_aliases: dict) -> tuple:
        """Resolve `needs` against what observations and mounted, VALID runtimes provide.

        Returns (resolved_needs, reads_from, missing) where missing is [(need, fix)].
        """
        providers: list[tuple[str, Capability]] = [("observations", parse_capability(c)) for c in external_caps]
        for r in self.valid():
            for p in r.provides:
                providers.append((r.name, p))
                # a plugin providing an abstract capability is discoverable by the alias too
        resolved, reads_from, missing = [], [], []
        for need in manifest.needs:
            try:
                n = need.resolve(keymap)
            except ManifestError as e:
                missing.append((need.raw, f"declare the key in stack.yml keys: — {e}"))
                continue
            candidates = self._expand(n, capability_aliases)
            hit = None
            for cand in candidates:
                for owner, p in providers:
                    if p.matches(cand) or (p.kind == "capability" and cand.kind == "capability" and p.slot == cand.slot):
                        hit = owner
                        break
                if hit:
                    break
            if hit is None:
                missing.append((need.raw, f"mount something that provides {n.raw}"))
            else:
                resolved.append(n)
                if hit != "observations" and hit not in reads_from:
                    reads_from.append(hit)
        # `optional`: used if present, never a prerequisite — but a dependency when present
        for opt in manifest.optional:
            try:
                o = opt.resolve(keymap)
            except ManifestError:
                continue
            for cand in self._expand(o, capability_aliases):
                for owner, p in providers:
                    if owner != "observations" and p.matches(cand) and owner not in reads_from:
                        reads_from.append(owner)
        # a plugin receives a view FILTERED by every mask beneath it, so every mask is a dependency
        for r in self.valid():
            if any(p.kind == "slot" and p.slot == "mask" for p in r.provides) and r.name not in reads_from:
                reads_from.append(r.name)
        return resolved, reads_from, missing

    @staticmethod
    def _expand(cap: Capability, aliases: dict) -> list:
        """`capability:x` may be satisfied by the profile's alias slot pattern as well."""
        out = [cap]
        if cap.kind == "capability":
            alias = aliases.get(cap.raw)
            if alias:
                try:
                    out.append(parse_capability(alias))
                except ManifestError:
                    pass
        return out

    # ------------------------------------------------------------- transitions
    def register(self, name: str, manifest: Manifest, params: dict, needs, reads_from) -> Runtime:
        if self.get(name):
            raise RegistryError(f"{name} is already registered")
        rt = Runtime(name=name, manifest=manifest, params=dict(params), needs=list(needs),
                     provides=manifest.provides, reads_from=list(reads_from))
        rt.fork = self.ctx.fork(f"plugin:{name}")
        self.runtimes.append(rt)
        return rt

    def mark(self, rt: Runtime, state: str, reason: str = ""):
        if state not in STATES:
            raise RegistryError(f"unknown state {state}")
        rt.state = state
        if state == "mounted":
            rt.mounted_at = time.time()
            self.history.append({"name": rt.name, "layer": rt.layer})
        if reason:
            rt.invalid_reason = reason

    def drop(self, rt: Runtime):
        """Remove a runtime that never mounted (refused / died) from the order."""
        if rt in self.runtimes:
            self.runtimes.remove(rt)
        if rt.fork and not rt.fork.disposed:
            rt.fork.dispose()

    # ------------------------------------------------------------- dependency & invalidation
    def dependents(self, name: str) -> list:
        """Transitive closure of runtimes that read from `name`, in mount order."""
        out, frontier = [], {name}
        for r in self.runtimes:
            if r.name != name and set(r.reads_from) & frontier:
                out.append(r)
                frontier.add(r.name)
        return out

    def invalidation_plan(self, name: str) -> list:
        """What unmounting `name` invalidates (D3): every dependent, stopping at a checkpoint,
        which is marked for rebuild and shields what is above it."""
        plan, shielded = [], set()
        for r in self.dependents(name):
            if set(r.reads_from) <= shielded and r.name != name:
                continue
            if r.is_checkpoint:
                plan.append((r.name, "rebuild"))
                shielded.add(r.name)
            else:
                plan.append((r.name, "invalid"))
        return plan

    def unmount_order(self, name: str) -> list:
        """E3: disposers run in exactly reverse mount order — this runtime last."""
        idx = [i for i, r in enumerate(self.runtimes) if r.name == name]
        if not idx:
            raise RegistryError(f"{name} is not mounted")
        return [r.name for r in reversed(self.runtimes[idx[0]:])]

    def apply_invalidation(self, name: str) -> list:
        applied = []
        for dep, state in self.invalidation_plan(name):
            rt = self.get(dep)
            if rt and rt.state == "mounted":
                self.mark(rt, state, f"{name} was unmounted")
                applied.append((dep, state))
        return applied

    def remove(self, name: str) -> Runtime:
        rt = self.get(name)
        if rt is None:
            raise RegistryError(f"{name} is not mounted")
        self.runtimes.remove(rt)
        self.mark(rt, "unmounted")
        return rt

    # ------------------------------------------------------------- persistence
    def fold_entries(self, upto: str | None = None) -> list:
        out = []
        for r in self.runtimes:
            if r.name == upto:
                break
            if r.state in ("mounted",):
                out.append(r.fold_entry())
        return out

    def snapshot(self) -> list:
        return [r.to_state() for r in self.runtimes]

    def save(self, path):
        Path(path).write_text(json.dumps({"runtimes": self.snapshot(), "history": self.history},
                                         indent=1, sort_keys=True, default=str))

    def load(self, path, manifest_loader):
        data = json.loads(Path(path).read_text())
        self.history = list(data.get("history", []))
        for s in data["runtimes"]:
            m = manifest_loader(s["plugin_dir"])
            rt = Runtime(name=s["name"], manifest=m, params=s["params"], state=s["state"],
                         provides=m.provides, reads_from=s.get("reads_from", []),
                         invalid_reason=s.get("invalid_reason", ""), mounted_at=s.get("mounted_at", 0),
                         escapes=s.get("escapes", {}))
            rt.fork = self.ctx.fork(f"plugin:{rt.name}")
            self.runtimes.append(rt)
