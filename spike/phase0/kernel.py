"""Phase 0 kernel — the smallest thing that can disprove the thesis.

This is a SPIKE. It exists to produce four numbers, not to be the kernel. It is deliberately
in-process, single-profile and about 200 lines, because the question it answers is cheap to get
wrong by building too much first:

    can a decision be unmounted cleanly, and is materialising a view from a stack fast enough
    that nobody keeps a filtered copy on the side?

If the answer is no, everything after it is wasted. See ROADMAP.md, Phase 0.

WHAT IS REAL HERE AND WHAT IS NOT

Real: observations are immutable, a contribution carries its own undo, unmount reverses in
reverse order, invalidation propagates without consulting the invalidated plugin, and a view is
generated rather than stored.

Not real, and deliberately: plugins are in-process callables rather than subprocesses; there is
one hard-coded profile; there is no manifest, no gate, no report. Phase 1 replaces all of it. The
subprocess cost that Phase 1 adds is measured separately in `evaluate.py` so it is not a surprise
later.
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field


class Observations:
    """The immutable layer. Loaded once, never written (ARCHITECTURE D2).

    Immutability is enforced rather than promised: the arrays are marked read-only, so a plugin
    that tries to write in place raises instead of succeeding quietly. A promise nothing checks is
    the failure this whole design is about.
    """

    def __init__(self, X, ids, features):
        import numpy as np
        self.X = X
        self.ids = np.asarray(ids)
        self.features = np.asarray(features)
        for a in (self.ids, self.features):
            a.flags.writeable = False
        if hasattr(X, "data"):
            X.data.flags.writeable = False
        self.n = len(self.ids)

    def digest(self):
        h = hashlib.sha256()
        h.update(self.ids.tobytes())
        h.update(self.features.tobytes())
        d = self.X.data if hasattr(self.X, "data") else self.X
        h.update(memoryview(d).tobytes() if hasattr(d, "tobytes") else bytes(d))
        return h.hexdigest()[:16]


@dataclass
class Contribution:
    """One thing a plugin added. The DISPOSER IS THIS OBJECT: removing it is the undo.

    Cordis returns a closure from register(). Out of process a closure cannot cross the boundary,
    so the declaration is the disposer (ADR-0003). This spike keeps the same shape in-process so
    the two cannot diverge: nothing mutates the view, everything is a recorded contribution the
    kernel can drop.
    """
    slot: str          # mask | column | embedding
    name: str
    payload: object
    plugin: str


@dataclass
class Runtime:
    """One mounted plugin and everything it contributed."""
    name: str
    params: dict
    contributions: list = field(default_factory=list)
    reads: set = field(default_factory=set)     # slots it consumed, for invalidation
    valid: bool = True
    seconds: float = 0.0


class Stack:
    """The mounted decision stack. The artifact; the view is derived from it."""

    def __init__(self, observations):
        self.obs = observations
        self.runtimes: list[Runtime] = []
        self.events: list[dict] = []

    # ---------------------------------------------------------------- mount / unmount
    def mount(self, plugin, **params):
        rt = Runtime(name=plugin.NAME, params=params)
        t0 = time.perf_counter()
        view = self.materialise()                       # what the plugin sees
        rt.reads = set(plugin.READS)
        for slot, name, payload in plugin.run(view, **params):
            rt.contributions.append(Contribution(slot, name, payload, plugin.NAME))
        rt.seconds = time.perf_counter() - t0
        self.runtimes.append(rt)
        self._event("mount", plugin=plugin.NAME, params=params,
                    contributes=[f"{c.slot}/{c.name}" for c in rt.contributions])
        self._invalidate_after(rt)
        return rt

    def unmount(self, name):
        """Drop a plugin's contributions and invalidate whatever depended on them.

        Reverse mount order (ARCHITECTURE E3): later plugins are removed from the view before
        earlier ones, so nothing is ever asked to exist without what it read.
        """
        idx = [i for i, r in enumerate(self.runtimes) if r.name == name]
        if not idx:
            raise KeyError(f"{name} is not mounted")
        i = idx[0]
        removed = self.runtimes[i]
        provided = {f"{c.slot}/{c.name}" for c in removed.contributions}
        for rt in reversed(self.runtimes[i + 1:]):
            if rt.reads & provided or rt.reads & {c.slot for c in removed.contributions}:
                rt.valid = False                         # WITHOUT consulting the plugin
        self.runtimes.pop(i)
        self._event("unmount", plugin=name, released=sorted(provided))
        return removed

    def _invalidate_after(self, rt):
        pass                                             # nothing above a fresh mount yet

    def invalid(self):
        return [r.name for r in self.runtimes if not r.valid]

    # ---------------------------------------------------------------- the view
    def materialise(self):
        """Apply the stack to the observations. Generated on demand, never stored.

        Masks compose by AND, in mount order. Nothing here mutates the observation layer: the mask
        is carried beside it and applied at the boundary, which is what makes an unmount free.
        """
        import numpy as np
        keep = np.ones(self.obs.n, dtype=bool)
        columns, embeddings = {}, {}
        for rt in self.runtimes:
            for c in rt.contributions:
                if c.slot == "mask":
                    keep &= c.payload
                elif c.slot == "column":
                    columns[c.name] = c.payload
                elif c.slot == "embedding":
                    embeddings[c.name] = c.payload
        return View(self.obs, keep, columns, embeddings)

    # ---------------------------------------------------------------- provenance
    def _event(self, kind, **kw):
        self.events.append(dict(kind=kind, **kw))

    def declaration(self):
        """The stack itself: what regenerates the view. This is the artifact."""
        return {"observations": self.obs.digest(),
                "plugins": [{"name": r.name, "params": r.params} for r in self.runtimes]}


class View:
    """A materialisation. Disposable by construction — deleting it loses nothing."""

    def __init__(self, obs, keep, columns, embeddings):
        self.obs, self.keep = obs, keep
        self.columns, self.embeddings = columns, embeddings

    @property
    def n(self):
        return int(self.keep.sum())

    def X(self):
        return self.obs.X[self.keep]

    def digest(self):
        """A digest of what a consumer would receive.

        Over the KEPT ids, the mask, and every contributed column — so a mount that changes
        nothing a consumer sees produces the same digest, and a mount that does changes it.
        """
        import numpy as np
        h = hashlib.sha256()
        h.update(self.obs.ids[self.keep].tobytes())
        h.update(np.packbits(self.keep).tobytes())
        for k in sorted(self.columns):
            h.update(k.encode())
            h.update(np.ascontiguousarray(self.columns[k][self.keep]).tobytes())
        for k in sorted(self.embeddings):
            h.update(k.encode())
            h.update(np.ascontiguousarray(self.embeddings[k][self.keep]).tobytes())
        return h.hexdigest()[:16]
