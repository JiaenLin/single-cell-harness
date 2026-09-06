"""Context, Service, effect and disposer.

A plugin receives a Context and reaches everything through it (C1). Dependencies are declared
with `inject` and never discovered by import (C2). Every registration is an effect that returns
a disposer, and disposers run in exactly reverse registration order (E1, E3). A Context can be
forked: a fork sees its parent's services and owns its own effects, so disposing the fork undoes
only what the fork did.

A disposer must reach quiescence (E5): a disposer that returns while work it started is still
running has not disposed anything. The kernel cannot check that in general, so a disposer may
return a `Facts` mapping — `requested`, `stopped`, `timed_out`, `exit` — and a fork records
it. `DisposeError` is raised when a disposer reports it could not confirm termination.
"""
from __future__ import annotations

import json
from typing import Any, Callable, Iterable, Mapping

from .events import EventBus

Disposer = Callable[[], Any]


class InjectError(LookupError):
    """A declared dependency is not on the Context."""


class DisposeError(RuntimeError):
    """A disposer could not confirm the work it started has stopped (E5)."""


class Service:
    """Something attached to a Context by name. Subclasses add behaviour; this adds identity."""

    name: str = ""

    def describe(self) -> dict:
        return {"service": self.name, "kind": type(self).__name__}


class Context:
    def __init__(self, parent: "Context | None" = None, label: str = "root"):
        self.parent = parent
        self.label = label
        self._services: dict[str, Service] = {}
        self._effects: list[tuple[str, Disposer]] = []
        self._forks: list["Context"] = []
        self.bus: EventBus = parent.bus if parent else EventBus()
        self.disposed = False

    # ------------------------------------------------------------------ services
    def provide(self, name: str, service: Service) -> Disposer:
        if name in self._services:
            raise ValueError(f"service {name!r} already provided on {self.label}")
        service.name = name
        self._services[name] = service

        def dispose():
            self._services.pop(name, None)
        self.effect(f"service:{name}", dispose)
        self.bus.emit("service/provided", name=name, context=self.label)
        return dispose

    def get(self, name: str) -> Service:
        ctx: Context | None = self
        while ctx is not None:
            if name in ctx._services:
                return ctx._services[name]
            ctx = ctx.parent
        raise InjectError(f"{name!r} is not provided on {self.label} or any parent")

    def has(self, name: str) -> bool:
        try:
            self.get(name)
            return True
        except InjectError:
            return False

    def inject(self, names: Iterable[str]) -> dict[str, Service]:
        """Demand-driven dependency resolution. Every name must resolve, or nothing does."""
        names = list(names)
        missing = [n for n in names if not self.has(n)]
        if missing:
            raise InjectError(f"{self.label} injects {missing}, which are not provided")
        return {n: self.get(n) for n in names}

    # ------------------------------------------------------------------ effects
    def effect(self, label: str, disposer: Disposer) -> Disposer:
        """Register an effect. Returns the disposer so the caller may run it early."""
        entry = (label, disposer)
        self._effects.append(entry)

        def run_once():
            if entry in self._effects:
                self._effects.remove(entry)
                return disposer()
            return None
        return run_once

    def on(self, event: str, handler: Callable[..., Any]) -> Disposer:
        d = self.bus.on(event, handler)
        return self.effect(f"listener:{event}", d)

    def emit(self, event: str, *a, **kw):
        return self.bus.emit(event, *a, **kw)

    def bail(self, event: str, *a, **kw):
        return self.bus.bail(event, *a, **kw)

    # ------------------------------------------------------------------ fork / dispose
    def fork(self, label: str) -> "Context":
        child = Context(self, label)
        self._forks.append(child)
        self.effect(f"fork:{label}", child.dispose)
        return child

    def dispose(self) -> list[dict]:
        """Run every effect in exactly reverse registration order (E3).

        Returns the list of quiescence facts disposers reported. Raises `DisposeError` if any
        disposer reports work it could not confirm stopped — after every other disposer has run,
        so a failure to stop one thing does not leave everything else registered.
        """
        if self.disposed:
            return []
        facts: list[dict] = []
        failures: list[str] = []
        while self._effects:
            label, d = self._effects.pop()
            r = d()
            if isinstance(r, Mapping):
                rec = {"effect": label, **r}
                facts.append(rec)
                if rec.get("requested") and not rec.get("stopped"):
                    failures.append(label)
        self.disposed = True
        if self.parent and self in self.parent._forks:
            self.parent._forks.remove(self)
        self.bus.emit("context/disposed", context=self.label, facts=facts)
        if failures:
            raise DisposeError(f"{self.label}: could not confirm termination of {failures}")
        return facts

    # ------------------------------------------------------------------ serialisation (C4)
    def to_json(self) -> str:
        """The Context as a plugin across a process boundary receives it: names, not objects."""
        names: list[str] = []
        ctx: Context | None = self
        while ctx is not None:
            names.extend(n for n in ctx._services if n not in names)
            ctx = ctx.parent
        return json.dumps({"context": self.label, "services": sorted(names)}, sort_keys=True)

    def services(self) -> list[str]:
        return json.loads(self.to_json())["services"]
