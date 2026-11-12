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

#: WHAT A MOUNT RECORDED IS WHAT ITS LAYER IS (harness W052 fix 1). A mount records the identity of
#: what computed its layer: the plugin's version, its state_version (its numbers, versioned) and the
#: layer kind it was mounted as. A stack reopened later rebuilds each runtime from the plugin.yml it
#: names, and that file can have moved since (a pull, a checkout, an edit). The identity a runtime
#: is folded, keyed, saved and shown under is therefore the RECORDED one, never the declared one;
#: and where the two differ the runtime carries the difference, and the kernel serves nothing that
#: reads its layer until it is unmounted and mounted again.
IDENTITY = ("version", "state_version", "layer")


def identity_of(manifest) -> dict:
    """What a plugin.yml declares now, in the fields a mount records."""
    return {"version": manifest.version, "state_version": manifest.state_version, "layer": manifest.layer}


def same_value(a, b) -> bool:
    """Equal AND of one type: a state_version 2 is not 2.0, 1 is not True, and "2" is not 2."""
    return type(a) is type(b) and a == b


def differences(record: str, recorded: dict, declared: dict) -> list:
    """Each field `record` holds that differs from what is declared now, by name."""
    return [{"record": record, "field": k, "recorded": recorded[k], "declared": declared.get(k)}
            for k in recorded if not same_value(recorded[k], declared.get(k))]


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
    recorded: dict = field(default_factory=dict)       # IDENTITY as the mount recorded it
    mismatch: list = field(default_factory=list)       # differences(): a record against plugin.yml

    def __post_init__(self):
        if not self.recorded:                          # a fresh mount records what it is mounted under
            self.recorded = identity_of(self.manifest)

    @property
    def version(self) -> str:
        return self.recorded.get("version")

    @property
    def state_version(self):
        return self.recorded.get("state_version")

    @property
    def layer(self) -> str:
        return self.recorded.get("layer")

    @property
    def is_checkpoint(self) -> bool:
        return self.layer == "checkpoint"

    @property
    def declared(self) -> dict:
        return identity_of(self.manifest)

    def fold_entry(self) -> tuple:
        return (self.name, self.version, self.state_version, self.params)

    def to_state(self) -> dict:
        return {"name": self.name, "state": self.state, "params": self.params,
                "plugin_dir": str(self.manifest.dir) if self.manifest.dir else None,
                "version": self.version, "state_version": self.state_version,
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
    def admit(self, manifest: Manifest, profile_accepts, reopening: bool = False) -> tuple:
        """X1: compare the contract MAJOR only. Profile: refuse an unknown one rather than guess.
        A declared state_version is an integer exactly: 2.0, "2" and true are refused (D6)."""
        sv = manifest.state_version
        if sv is not None and type(sv) is not int:
            return False, (f"{manifest.name}: declares state_version {sv!r}, which is not an integer"),\
                "declare state_version as an integer (D6)"
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
        if not reopening and prior and prior[-1]["layer"] == "checkpoint" and manifest.layer == "stack":
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

    def load(self, path, manifest_loader, profile_accepts=None):
        """Each runtime as its mount recorded it, beside what its plugin.yml declares now.

        The manifest is read from the plugin directory the mount named, so it is the CURRENT one;
        the identity is the recorded one (absent fields recorded as None, which differ from any
        declaration). Every difference is kept on the runtime, and so is a refusal of the
        admission the mount passed, asked again of the current manifest: what `admit` refuses at a
        mount it refuses at every reopening (ATTACKS 21: the same check at another moment)."""
        data = json.loads(Path(path).read_text())
        self.history = list(data.get("history", []))
        for s in data["runtimes"]:
            m = manifest_loader(s["plugin_dir"])
            rec = {k: s.get(k) for k in IDENTITY}
            rt = Runtime(name=s["name"], manifest=m, params=s["params"], state=s["state"],
                         provides=m.provides, reads_from=s.get("reads_from", []),
                         invalid_reason=s.get("invalid_reason", ""), mounted_at=s.get("mounted_at", 0),
                         escapes=s.get("escapes", {}), recorded=rec)
            rt.mismatch = differences("state.json", rec, identity_of(m))
            if profile_accepts is not None:
                ok, reason, _fix = self.admit(m, profile_accepts, reopening=True)
                if not ok:
                    rt.mismatch.append({"record": "admission", "field": "plugin.yml",
                                        "recorded": "admitted at its mount", "declared": reason})
            rt.fork = self.ctx.fork(f"plugin:{rt.name}")
            self.runtimes.append(rt)

    def mismatched(self, upto: str | None = None) -> list:
        """The runtimes a view up to `upto` would fold whose record is not their plugin.yml."""
        out = []
        for r in self.runtimes:
            if r.name == upto:
                break
            if r.state == "mounted" and r.mismatch:
                out.append(r)
        return out
