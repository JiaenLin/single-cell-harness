"""The typed event bus: broadcast and waterfall.

Cordis has two dispatch modes and the harness needs both. `emit` is broadcast — every listener
hears it, order is not a contract, and no listener can stop the others (observers, provenance).
`bail` is waterfall — listeners run in registration order and the first non-None return ends
the dispatch (a gate refusing). Both return a disposer; nothing is registered without one.
"""
from __future__ import annotations

from typing import Any, Callable


class EventBus:
    def __init__(self):
        self._listeners: dict[str, list[tuple[int, Callable]]] = {}
        self._seq = 0

    def on(self, event: str, handler: Callable[..., Any]) -> Callable[[], None]:
        self._seq += 1
        entry = (self._seq, handler)
        self._listeners.setdefault(event, []).append(entry)

        def dispose():
            lst = self._listeners.get(event, [])
            if entry in lst:
                lst.remove(entry)
        return dispose

    def emit(self, event: str, *args, **kw) -> list[Any]:
        """Broadcast. Every listener runs; their return values are collected, none short-circuits."""
        return [h(*args, **kw) for _, h in list(self._listeners.get(event, []))]

    def bail(self, event: str, *args, **kw) -> Any:
        """Waterfall. The first listener returning non-None ends the dispatch."""
        for _, h in list(self._listeners.get(event, [])):
            r = h(*args, **kw)
            if r is not None:
                return r
        return None

    def listeners(self, event: str) -> int:
        return len(self._listeners.get(event, []))
