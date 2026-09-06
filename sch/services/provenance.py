"""The event stream: append-only, replayable (P1). The stack is the provenance (P3).

Every mount, unmount, refusal, escape, number and disposal is an event with a sequence number.
A number becomes report-visible only by being an event here, which is what makes P2 checkable.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from ..core import Service


class Provenance(Service):
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._seq = self._last_seq()

    def _last_seq(self) -> int:
        if not self.path.exists():
            return 0
        last = 0
        with open(self.path, encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    last = json.loads(line)["seq"]
        return last

    def append(self, kind: str, **payload) -> int:
        self._seq += 1
        rec = {"seq": self._seq, "ts": time.time(), "kind": kind, **payload}
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, sort_keys=True, default=str) + "\n")
        return self._seq

    def replay(self) -> list:
        if not self.path.exists():
            return []
        with open(self.path, encoding="utf-8") as fh:
            return [json.loads(l) for l in fh if l.strip()]

    def find(self, seq: int) -> dict | None:
        for e in self.replay():
            if e["seq"] == seq:
                return e
        return None

    def of_kind(self, kind: str) -> list:
        return [e for e in self.replay() if e["kind"] == kind]

    # -------------------------------------------------------------- numbers (P2)
    def record_number(self, plugin: str, key: str, value, scratch: bool = False) -> int:
        return self.append("number", plugin=plugin, key=key, value=value, scratch=scratch)

    def numbers(self) -> list:
        return self.of_kind("number")
