"""The kernel: a Stack over a directory, orchestrating registry and services.

    stack = Stack.open(dir)              # reads stack.yml, profile, state
    stack.plan(plugin_dir, params)       # what would run; refuses at plan time, before compute
    stack.mount(plugin_dir, params)      # materialise → gates → execute → merge → companions
    stack.unmount(name, dry_run=True)    # the invalidation list, and the cost, before paying it
    stack.materialise()                  # a view — derived, disposable
    stack.scratch(script)                # arbitrary code against a read-only view; unquotable
    stack.report()                       # numbers that resolve to events, or no report

Imports L1–L3. Imports NO plugin module (L3): plugins are directories it runs as subprocesses.
"""
from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path

from . import CONTRACT, __version__, yamlish
from .core import Context
from .profile import load_profile, Profile
from .registry import Manifest, MountResult, Registry, fold_key, FoldCache
from .registry.manifest import load_manifest, parse_capability, ManifestError
from .services.dataset import Dataset, Contribution, DatasetError
from .services.executor import make_executor
from .services.gate import GateService
from .services.invariant import InvariantService, InvariantFailure
from .services.probe import ProbeService
from .services.provenance import Provenance
from .services.report import ReportService
from .stack import compose, load_layers, StackError

CONTRACT_MAJOR = int(CONTRACT.split(".")[0])


class Stack:
    def __init__(self, stack_dir, overrides: dict | None = None):
        self.dir = Path(stack_dir).resolve()
        self.decl = compose(load_layers(self.dir, overrides))
        if "profile" not in self.decl:
            raise StackError(f"{self.dir}/stack.yml declares no profile")
        self.profile: Profile = load_profile(self.decl["profile"])
        obs = self.decl.get("observations")
        if not obs:
            raise StackError("stack.yml declares no observations")
        design = self.decl.get("design")
        self.ctx = Context(label=f"stack:{self.dir.name}")
        self.prov = Provenance(self.dir / "events.jsonl")
        self.ctx.provide("provenance", self.prov)
        self.dataset = Dataset(self._abs(obs), self.profile, self.dir, self._abs(design) if design else None)
        self.ctx.provide("dataset", self.dataset)
        self.executor = make_executor(str(self.decl.get("executor", "local")),
                                      self.decl.get("interpreters") or {})
        self.ctx.provide("executor", self.executor)
        self.ctx.effect("executor:quiesce", self.executor.quiesce)
        self.inv = InvariantService(self.prov, self._run_argv)
        self.ctx.provide("invariant", self.inv)
        self.probes = ProbeService(self._run_plugin)
        self.ctx.provide("probe", self.probes)
        self.gates = GateService(self._run_plugin, self.probes, self.prov)
        self.ctx.provide("gate", self.gates)
        self.reports = ReportService(self.prov, self.inv)
        self.ctx.provide("report", self.reports)
        self.registry = Registry(self.ctx, CONTRACT_MAJOR)
        self.cache = FoldCache(self.dir / "materialised")
        self.plugin_paths = self._plugin_paths()
        state = self.dir / "state.json"
        if state.exists():
            self.registry.load(state, self._manifest)
            self._restore_contributions()

    def _restore_contributions(self):
        """Rebuild the contribution list from each mounted plugin's own out.json on disk.

        The declaration is the disposer: what a plugin declared it produced is exactly what is
        restored, read from its run directory, never from the materialised cache.
        """
        for rt in self.registry.runtimes:
            if rt.state not in ("mounted", "invalid", "rebuild"):
                continue
            rt.dir = self.dir / "plugins" / rt.name
            out_path = rt.dir / "out" / "out.json"
            if not out_path.exists():
                continue
            out = json.loads(out_path.read_text())
            contribs, _ = self._collect(rt, rt.manifest, out, restoring=True)
            for c in contribs:
                self.dataset.add(c)

    # ------------------------------------------------------------- helpers
    def _abs(self, p) -> Path:
        p = Path(str(p))
        return p if p.is_absolute() else (self.dir / p).resolve()

    def _plugin_paths(self) -> list:
        paths = []
        for p in str(self.decl.get("plugin_paths", "")).split(":"):
            if p:
                paths.append(self._abs(p))
        for p in os.environ.get("SCH_PLUGINS", "").split(":"):
            if p:
                paths.append(Path(p))
        paths.append(Path(__file__).resolve().parent.parent / "plugins")
        return paths

    def _manifest(self, plugin_dir) -> Manifest:
        return load_manifest(plugin_dir)

    def resolve_plugin(self, ref: str) -> Manifest:
        """A path, or a name searched under the plugin paths (site plugins override shipped)."""
        p = Path(ref)
        if p.exists() and (p / "plugin.yml").exists():
            return load_manifest(p)
        found = []
        for root in self.plugin_paths:
            for cand in (root / ref, *sorted(root.glob(f"*/{ref}")), *sorted(root.glob(f"*/*_{ref}")), *sorted(root.glob(f"*/{ref}_*"))):
                if (cand / "plugin.yml").exists() and cand not in found:
                    found.append(cand)
        for cand in found:                       # site plugins override shipped ones by name
            m = load_manifest(cand)
            if m.name == ref and self.profile.accepts(m.profile):
                return m
        if found:
            raise ManifestError(f"plugin {ref!r} exists ({[str(f) for f in found]}) but none declares a "
                                f"profile this stack serves ({self.profile.id})")
        raise ManifestError(f"plugin {ref!r} not found as a path or under {[str(x) for x in self.plugin_paths]}")

    def keymap(self) -> dict:
        return dict(self.decl.get("keys") or {})

    def sentinels(self) -> list:
        return list(self.decl.get("sentinels") or self.profile.sentinels)

    @classmethod
    def open(cls, stack_dir, overrides=None) -> "Stack":
        return cls(stack_dir, overrides)

    @classmethod
    def init(cls, stack_dir, profile: str, observations: str, design: str | None = None,
             keys: dict | None = None, plugin_paths: list | None = None) -> "Stack":
        d = Path(stack_dir)
        d.mkdir(parents=True, exist_ok=True)
        prof = load_profile(profile)
        decl = {"profile": prof.id, "observations": str(observations)}
        if design:
            decl["design"] = str(design)
        decl["keys"] = dict(keys or {})
        decl["sentinels"] = list(prof.sentinels)
        if plugin_paths:
            decl["plugin_paths"] = ":".join(str(p) for p in plugin_paths)
        decl["plugins"] = {}
        yamlish.dump(decl, d / "stack.yml")
        st = cls(d)
        st.prov.append("stack/init", profile=prof.id, observations=str(observations),
                       kernel=__version__)
        return st

    # ------------------------------------------------------------- persistence
    def _save(self):
        self.registry.save(self.dir / "state.json")
        decl = dict(self.decl)
        decl.pop("composed_from", None)
        decl["plugins"] = {r.name: {"plugin": str(r.manifest.dir), "version": r.manifest.version,
                                    "state_version": r.manifest.state_version,
                                    "params": r.params, "state": r.state,
                                    **({"escapes": r.escapes} if r.escapes else {})}
                           for r in self.registry.runtimes}
        yamlish.dump(decl, self.dir / "stack.yml")
        self.decl = compose(load_layers(self.dir))

    def declaration(self) -> dict:
        """The stack itself: what regenerates the view. This is the artifact."""
        return {"profile": self.profile.id, "observations": self.dataset.digest(),
                "keys": self.keymap(), "sentinels": self.sentinels(),
                "plugins": [{"name": r.name, "version": r.manifest.version,
                             "state_version": r.manifest.state_version, "params": r.params,
                             "layer": r.layer, "state": r.state, "reads_from": r.reads_from}
                            for r in self.registry.runtimes],
                "cannot_show": {r.name: r.manifest.data.get("cannot_show", [])
                                for r in self.registry.runtimes}}

    # ------------------------------------------------------------- materialisation
    def fold_key_for(self, upto: str | None = None) -> str:
        return fold_key(self.dataset.digest(), self.registry.fold_entries(upto), self.profile.id)

    def materialise(self, upto: str | None = None, filtered: bool = True):
        """The fold, cached on the exact tuple (D6). Returns (View, cache_dir)."""
        key = self.fold_key_for(upto) + ("" if filtered else "-full")
        hit = self.cache.lookup(key)
        contribs = self._contributions(upto)
        if hit is not None:
            view = self._view_from(contribs, hit, filtered)
            cached = json.loads((hit / "key.json").read_text()).get("digest")
            self.inv.d6_same_tuple_same_result(key, cached, view.digest())
            return view, hit
        out = self.cache.dir_for(key)
        if out.exists():
            shutil.rmtree(out)
        view = self.dataset.materialise(contribs, out, filtered=filtered)
        self.cache.commit(key, {"digest": view.digest(), "kept": view.n, "total": view.n_total,
                                "stack": [list(e[:3]) for e in self.registry.fold_entries(upto)]})
        return view, out

    def _contributions(self, upto=None) -> list:
        names = []
        for r in self.registry.runtimes:
            if r.name == upto:
                break
            if r.state == "mounted":
                names.append(r.name)
        return [c for c in self.dataset.contributions if c.plugin in names]

    def _view_from(self, contribs, cache_dir, filtered):
        keep, columns, masks = self.dataset.fold(contribs)
        from .services.dataset import View
        f = cache_dir / ("view.csv" if filtered else "view_full.csv")
        if not f.exists():
            f = cache_dir / ("view.h5ad" if filtered else "view_full.h5ad")
        return View(self.dataset.ids, keep, columns, masks, f)

    # ------------------------------------------------------------- running plugins
    def _run_argv(self, argv, cwd, log) -> dict:
        env = {"SCH_CONTRACT": CONTRACT,
               "SCH_PROTOCOL": str(Path(__file__).resolve().parent / "plugin" / "protocol.py")}
        return self.executor.run(argv, cwd, log, env=env)

    def _run_plugin(self, manifest: Manifest, params: dict, extra: dict, run_dir: Path,
                    upstream: dict | None = None, view=None, scrub: bool = False,
                    name: str | None = None) -> tuple:
        """Write in.json, run the entry point, read out.json. Died / empty / entries are distinct."""
        run_dir = Path(run_dir)
        if run_dir.exists():
            shutil.rmtree(run_dir)
        out_dir = run_dir / "out"
        out_dir.mkdir(parents=True)
        if view is None:
            view, _ = self.materialise()
        inp = {"contract": CONTRACT, "profile": self.profile.id, "plugin": name or manifest.name,
               "plugin_version": manifest.version, "state_version": manifest.state_version,
               "data": str(view.path), "out_dir": str(out_dir), "keys": self.keymap(),
               "design": str(self.dataset.design) if self.dataset.design else None,
               "references": dict(self.decl.get("references") or {}),
               "params": params, "upstream": upstream or {},
               "provenance": {"tools": [], "search_paths": list(self.decl.get("search_paths") or [])},
               "sentinels": self.sentinels(), "identity": self.profile.identity,
               "profile_context": dict(self.decl.get("profile_context") or {}), **extra}
        (run_dir / "in.json").write_text(json.dumps(inp, indent=1, sort_keys=True, default=str))
        entry = manifest.entry_path()
        if entry is None or not entry.exists():
            self.prov.append("plugin/died", plugin=manifest.name, reason=f"entry {entry} missing")
            return {"exit": None, "stopped": True, "requested": False, "timed_out": False}, None
        interp = self.executor.interpreter(str(manifest.data.get("language", "python")), manifest.name)
        argv = interp + [str(entry), str(run_dir / "in.json")]
        env = {"SCH_IN": str(run_dir / "in.json"), "SCH_CONTRACT": CONTRACT,
               "SCH_PROTOCOL": str(Path(__file__).resolve().parent / "plugin" / "protocol.py")}
        timeout = params.get("timeout") if isinstance(params, dict) else None
        timeout = timeout or self.decl.get("timeout")
        facts = self.executor.run(argv, manifest.dir, run_dir / "stderr.log", env=env,
                                  timeout=float(timeout) if timeout else None, scrub=scrub)
        (run_dir / "facts.json").write_text(json.dumps(facts, indent=1))
        out_path = out_dir / "out.json"
        if not out_path.exists():
            self.prov.append("plugin/died", plugin=manifest.name, facts=facts,
                             stderr=str(run_dir / "stderr.log"))
            return facts, None
        try:
            out = json.loads(out_path.read_text())
        except ValueError as e:
            self.prov.append("plugin/died", plugin=manifest.name, reason=f"out.json unreadable: {e}")
            return facts, None
        return facts, out

    # ------------------------------------------------------------- plan
    def plan(self, plugin_ref: str, params: dict | None = None, name: str | None = None) -> dict:
        """What would run, and what is missing — before any compute is spent."""
        params = dict(params or {})
        m = self.resolve_plugin(plugin_ref)
        name = name or m.name
        ok, reason, fix = self.registry.admit(m, self.profile.accepts)
        plan = {"plugin": m.name, "name": name, "dir": str(m.dir), "admitted": ok,
                "reason": reason, "fix": fix, "needs": [], "missing": [], "gates": [],
                "cannot_show": m.data.get("cannot_show", []), "layer": m.layer,
                "reversible": m.reversible, "state_version": m.state_version}
        if not ok:
            return plan
        if m.cls != "method":
            plan.update(admitted=False, reason=f"{m.name} is class {m.cls}; only methods mount",
                        fix="ask it through the probe or gate service")
            return plan
        if self.registry.get(name):
            plan.update(admitted=False, reason=f"{name} is already mounted", fix="choose --name")
            return plan
        if m.layer == "checkpoint" and not m.data.get("rebuild_from"):
            plan.update(admitted=False, reason="a checkpoint must declare rebuild_from", fix="add rebuild_from")
            return plan
        resolved, reads_from, missing = self.registry.resolve(
            m, self.keymap(), self.dataset.observation_capabilities(), self.profile.capabilities)
        plan["needs"] = [c.raw for c in resolved]
        plan["reads_from"] = reads_from
        plan["missing"] = [{"need": n, "fix": f} for n, f in missing]
        gates, gate_missing = self._gates_for(m)
        plan["gates"] = [g.name for g in gates]
        plan["missing"] += [{"need": f"gate {g}", "fix": f} for g, f in gate_missing]
        plan["admitted"] = not plan["missing"]
        if plan["missing"]:
            plan["reason"] = "prerequisites missing"
        return plan

    def _gates_for(self, m: Manifest) -> tuple:
        wanted = dict(m.gates)
        for slot, req in self.profile.required.items():
            if any(p.kind == "slot" and p.slot == slot for p in m.provides):
                for g, mode in (req.get("gates") or {}).items():
                    wanted.setdefault(g, mode)
        gates, missing = [], []
        for g, mode in wanted.items():
            try:
                gm = self.resolve_plugin(g)
                if gm.cls != "gate":
                    missing.append((g, f"{g} is class {gm.cls}, not gate"))
                else:
                    gates.append(gm)
            except ManifestError:
                if mode == "required":
                    missing.append((g, f"provide a gate plugin named {g!r} on the plugin path"))
        return gates, missing

    # ------------------------------------------------------------- mount
    def mount(self, plugin_ref: str, params: dict | None = None, escapes: dict | None = None,
              name: str | None = None) -> MountResult:
        t0 = time.perf_counter()
        params = dict(params or {})
        escapes = dict(escapes or {})
        plan = self.plan(plugin_ref, params, name)
        name = plan["name"]
        if not plan["admitted"]:
            fix = plan.get("fix") or "; ".join(x["fix"] for x in plan["missing"])
            self.prov.append("mount/refused", plugin=name, reason=plan["reason"], fix=fix,
                             missing=plan["missing"])
            return MountResult(name, "refused", plan["reason"], fix)
        m = self.resolve_plugin(plugin_ref)
        rt = self.registry.register(name, m, params, [parse_capability(n) for n in plan["needs"]],
                                    plan.get("reads_from", []))
        rt.escapes = escapes
        rt.dir = self.dir / "plugins" / name
        try:
            view, _ = self.materialise()
            n_before = view.n_total
            obs_digest_before = self.dataset.digest()
            upstream = {dep: str(self.dir / "plugins" / dep / "out") for dep in rt.reads_from}
            facts, out = self._run_plugin(m, params, {}, rt.dir, upstream=upstream, view=view, name=name)
            if out is None:
                self.registry.mark(rt, "died")
                self.registry.drop(rt)
                self._save()
                return MountResult(name, "died", "no out.json: the plugin died",
                                   f"read {rt.dir / 'stderr.log'}", facts=facts)
            status = str(out.get("status", "ok"))
            if status == "refused":
                ref = (out.get("answer") or {}).get("refusal", {})
                self.prov.append("mount/refused", plugin=name, by="plugin",
                                 reason=ref.get("reason", out.get("headline", "")), fix=ref.get("fix", ""))
                self.registry.mark(rt, "refused")
                self.registry.drop(rt)
                self._save()
                return MountResult(name, "refused", ref.get("reason", out.get("headline", "")),
                                   ref.get("fix", ""), facts=facts)
            # A1: nothing wrote to the observations
            self.inv.a1_no_undeclared_write(self.dataset)
            # collect declared contributions, enforce provides, refuse foreign/short identity
            contribs, undeclared = self._collect(rt, m, out, view_n=view.n)
            # gates measure the plugin's output BEFORE it is merged
            gates, _ = self._gates_for(m)
            subject = {"plugin": name, "out_dir": str(rt.dir / "out"), "out": out,
                       "masks": {c.name: str(c.path) for c in contribs if c.slot == "mask"},
                       "columns": {c.name: str(c.path) for c in contribs if c.slot == "column"}}
            verdict, results = self.gates.evaluate(gates, subject, rt.dir, escapes, name, self.resolve_plugin)
            gate_dicts = [r.to_dict() for r in results]
            if verdict == "REFUSE":
                reasons = "; ".join(f"{r.gate}: {r.reason}" for r in results if r.verdict == "REFUSE" and not r.escaped)
                self.prov.append("mount/refused", plugin=name, by="gate", reason=reasons,
                                 gates=gate_dicts)
                self.registry.mark(rt, "refused")
                self.registry.drop(rt)
                self._save()
                return MountResult(name, "refused", reasons,
                                   "record an escape with --escape GATE --why ... --by ..., or change the input",
                                   gates=gate_dicts, facts=facts)
            # E4: reversible is tested at mount — snapshot, apply, remove, compare
            before = view.digest()
            for c in contribs:
                self.dataset.add(c)
            if m.reversible:
                self.dataset.remove(name)
                restored = self.dataset.materialise(self._contributions(), self.dir / "materialised" / "_e4", filtered=True).digest()
                shutil.rmtree(self.dir / "materialised" / "_e4", ignore_errors=True)
                if restored != before:
                    self.prov.append("mount/refused", plugin=name, by="kernel",
                                     reason="reversible: true is false — removing the contribution did not restore the view")
                    self.registry.mark(rt, "refused")
                    self.registry.drop(rt)
                    self._save()
                    return MountResult(name, "invalid-claim", "reversible claim false",
                                       "declare reversible: false, or fix the contribution", gates=gate_dicts)
                for c in contribs:
                    self.dataset.add(c)
            self.registry.mark(rt, "mounted")
            after, _ = self.materialise()
            self.inv.d4_count_never_decreases(n_before, after.n_total)
            # the plugin's own companion, on this run
            self._companion(rt, m, out, contribs)
            # numbers become events (P2)
            for k, v in (out.get("numbers") or {}).items():
                self.prov.record_number(name, k, v)
            self.prov.append("mount", plugin=name, version=m.version, state_version=m.state_version,
                             params=params, layer=m.layer, contributes=[c.capability() for c in contribs],
                             undeclared=undeclared, gates=gate_dicts, facts=facts,
                             headline=out.get("headline", ""), wrapped=out.get("wrapped_versions", {}),
                             cannot_show=m.data.get("cannot_show", []), status=status)
            self._save()
            return MountResult(name, "mounted", gates=gate_dicts, facts=facts,
                               headline=out.get("headline", ""), undeclared=undeclared,
                               seconds=round(time.perf_counter() - t0, 3))
        except (DatasetError, InvariantFailure, ValueError) as e:
            self.prov.append("mount/refused", plugin=name, by="kernel", reason=str(e))
            self.dataset.remove(name)
            if rt in self.registry.runtimes:
                self.registry.mark(rt, "refused")
                self.registry.drop(rt)
            self._save()
            return MountResult(name, "refused", str(e), "")

    def _collect(self, rt, m: Manifest, out: dict, view_n: int | None = None,
                 restoring: bool = False) -> tuple:
        out_dir = rt.dir / "out"
        contribs, undeclared = [], []
        idc = self.profile.identity.get("column", "id")
        slot_map = {"columns": "column", "masks": "mask", "embeddings": "embedding",
                    "matrices": "matrix", "graphs": "graph", "objects": "object"}
        for field_name, slot in slot_map.items():
            for name, rel in (out.get(field_name) or {}).items():
                path = (out_dir / rel).resolve()
                if out_dir.resolve() not in path.parents:
                    raise DatasetError(f"{m.name}: output {rel!r} is outside out_dir; paths are relative to out_dir")
                if not path.exists():
                    raise DatasetError(f"{m.name}: declared {slot}/{name} at {rel}, which does not exist")
                cap = parse_capability(f"{slot}/{name}")
                if not any(p.matches(cap) for p in m.provides):
                    undeclared.append(cap.raw)
                    self.prov.append("plugin/undeclared_output", plugin=rt.name, output=cap.raw)
                    continue
                coverage = 0
                if slot in ("column", "mask"):
                    rows = self.dataset.check_identity(path, idc, whole=(slot == "mask" and not restoring), view_n=view_n)
                    coverage = len(rows)
                contribs.append(Contribution(rt.name, slot, name, path, coverage))
        for rel in (out.get("tables") or []):
            p = (out_dir / rel).resolve()
            if out_dir.resolve() not in p.parents:
                raise DatasetError(f"{m.name}: table {rel!r} is outside out_dir")
        return contribs, undeclared

    def _companion(self, rt, m: Manifest, out: dict, contribs):
        idc = self.profile.identity.get("column", "id")
        masked = []
        for c in contribs:
            if c.slot == "mask":
                from .services.dataset import read_keyed_csv
                rows = read_keyed_csv(c.path, idc)
                masked.extend(i for i, r in rows.items() if r["keep"] not in ("1", "true", "True"))
        facts = {"plugin": rt.name, "out_dir": str(rt.dir / "out"), "out": out,
                 "masked": sorted(set(masked)), "observations": len(self.dataset.ids),
                 "contributions": [{"slot": c.slot, "name": c.name, "path": str(c.path),
                                    "coverage": c.coverage} for c in contribs],
                 "identity": idc}
        interp = self.executor.interpreter(str(m.data.get("language", "python")), m.name)
        return self.inv.run_companion(m, facts, rt.dir / "companion", interp)

    # ------------------------------------------------------------- unmount
    def unmount(self, name: str, dry_run: bool = False) -> dict:
        rt = self.registry.get(name)
        if rt is None:
            return {"name": name, "status": "refused", "reason": f"{name} is not mounted"}
        if rt.is_checkpoint:
            self.prov.append("unmount/refused", plugin=name, reason="a checkpoint cannot be unmounted (D1)")
            return {"name": name, "status": "refused",
                    "reason": "a checkpoint cannot be unmounted; it is rebuilt from rebuild_from",
                    "would_invalidate": []}
        plan = self.registry.invalidation_plan(name)
        masks = [c for c in self.dataset.contributions_of(name) if c.slot == "mask"]
        restored = 0
        if masks:
            keep, _, _ = self.dataset.fold(self.dataset.contributions)
            keep_without, _, _ = self.dataset.fold([c for c in self.dataset.contributions if c.plugin != name])
            restored = sum(1 for i in self.dataset.ids if keep_without[i] and not keep[i])
        result = {"name": name, "status": "planned" if dry_run else "unmounted",
                  "would_restore": restored, "would_invalidate": [{"name": n, "state": s} for n, s in plan],
                  "order": self.registry.unmount_order(name)}
        if dry_run:
            self.prov.append("unmount/dry-run", plugin=name, **{k: v for k, v in result.items() if k != "name"})
            return result
        # E3 / E5: dispose this plugin's fork (its executor work) and confirm quiescence
        facts = rt.fork.dispose() if rt.fork else []
        for f in facts:
            self.inv.e5_disposer_quiesced(f, owner=name)
        self.registry.apply_invalidation(name)
        self.dataset.remove(name)
        self.registry.remove(name)
        self.prov.append("unmount", plugin=name, restored=restored,
                         invalidated=result["would_invalidate"], facts=facts)
        self._save()
        return result

    # ------------------------------------------------------------- probes for agents
    def ask(self, probe_ref: str, params: dict | None = None, subject: dict | None = None,
            upto: str | None = None) -> dict:
        """Ask a probe. `upto` materialises the view BELOW a mounted plugin, which is the view a
        gate saw when that plugin mounted — so an agent can reproduce any refusal's number."""
        m = self.resolve_plugin(probe_ref)
        if upto:
            view, _ = self.materialise(upto=upto)
            runner = lambda mf, p, extra, rd: self._run_plugin(mf, p, extra, rd, view=view)  # noqa: E731
            from .services.probe import ProbeService
            pr = ProbeService(runner).ask(m, dict(params or {}), subject or {}, self.dir / "probes" / m.name)
        else:
            pr = self.probes.ask(m, dict(params or {}), subject or {}, self.dir / "probes" / m.name)
        self.prov.append("probe", probe=m.name, params=params or {}, answer=pr.answer, died=pr.died,
                         cannot_show=m.data.get("cannot_show", []))
        return pr.to_dict()

    # ------------------------------------------------------------- scratch (A1, A2)
    def scratch(self, script: str, label: str | None = None, params: dict | None = None) -> dict:
        """Run arbitrary code against a READ-ONLY view. Nothing it produces is quotable."""
        script = Path(script).resolve()
        sid = f"{int(time.time())}-{script.stem}" if not label else label
        run_dir = self.dir / "scratch" / sid
        run_dir.mkdir(parents=True, exist_ok=True)
        view, _ = self.materialise()
        m = Manifest({"name": f"scratch:{sid}", "version": "0", "language": "python",
                      "entry": script.name, "profile": self.profile.id, "contract": CONTRACT},
                     dir=script.parent)
        facts, out = self._run_plugin(m, dict(params or {}), {"scratch": True}, run_dir,
                                      view=view, scrub=True, name=f"scratch:{sid}")
        # A1 again: the observations and the view must be untouched
        self.inv.a1_no_undeclared_write(self.dataset)
        numbers = (out or {}).get("numbers") or {}
        for k, v in numbers.items():
            self.prov.record_number(f"scratch:{sid}", k, v, scratch=True)
        self.prov.append("scratch", id=sid, script=str(script), facts=facts, died=out is None,
                         headline=(out or {}).get("headline", ""))
        return {"id": sid, "dir": str(run_dir), "facts": facts, "out": out, "died": out is None}

    def promote(self, scratch_id: str, by: str | None, plugin_dir: str | None) -> dict:
        """Scratch → dev needs a lock, a selftest, a cannot_show and a PERSON. The kernel refuses
        otherwise, and an agent cannot supply the person (A3)."""
        if not by or by.startswith("agent") or by.startswith("scratch"):
            self.prov.append("promote/refused", scratch=scratch_id, reason="no human named")
            return {"status": "refused", "reason": "promotion requires a person (--by), not an agent"}
        if not plugin_dir:
            return {"status": "refused", "reason": "promotion requires a plugin directory with plugin.yml, lock.yml, selftest and a non-empty cannot_show"}
        from .plugin.validate import validate
        problems = [p for p in validate(plugin_dir) if p["level"] == "error"]
        if problems:
            self.prov.append("promote/refused", scratch=scratch_id, reason="plugin does not validate",
                             problems=problems)
            return {"status": "refused", "reason": "plugin does not validate", "problems": problems}
        self.prov.append("promote", scratch=scratch_id, by=by, plugin=str(plugin_dir))
        return {"status": "promoted", "by": by, "plugin": str(plugin_dir),
                "note": "scratch numbers stay scratch; mount the plugin to produce quotable ones"}

    # ------------------------------------------------------------- report, fork
    def report(self, include_scratch: bool = False) -> dict:
        return self.reports.render(self.dir / "report" / "report.json", self.declaration(),
                                   include_scratch=include_scratch)

    def fork(self, new_dir, without: list | None = None) -> "Stack":
        """A new stack: same observations, same plugins except `without`, nothing run yet."""
        without = set(without or [])
        new = Path(new_dir)
        new.mkdir(parents=True, exist_ok=True)
        decl = {k: v for k, v in self.decl.items() if k not in ("plugins", "composed_from")}
        decl["observations"] = str(self.dataset.observations)
        if self.dataset.design:
            decl["design"] = str(self.dataset.design)
        decl["plugin_paths"] = ":".join(str(p) for p in self.plugin_paths[:-1]) or None
        decl["forked_from"] = str(self.dir)
        decl["plugins"] = {r.name: {"plugin": str(r.manifest.dir), "params": r.params}
                           for r in self.registry.runtimes if r.name not in without and r.state == "mounted"}
        if decl["plugin_paths"] is None:
            decl.pop("plugin_paths")
        yamlish.dump(decl, new / "stack.yml")
        st = Stack(new)
        st.prov.append("stack/fork", from_stack=str(self.dir), without=sorted(without))
        return st

    def run_declared(self) -> list:
        """Mount every plugin listed in stack.yml that is not yet mounted, in order."""
        results = []
        for name, spec in (self.decl.get("plugins") or {}).items():
            if self.registry.get(name):
                continue
            results.append(self.mount(spec["plugin"], spec.get("params") or {},
                                      spec.get("escapes") or {}, name=name))
        return results

    def close(self):
        facts = self.ctx.dispose()
        return facts
