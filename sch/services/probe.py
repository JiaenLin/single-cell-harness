"""Probes: read-only questions with bounded answers.

A probe is a plugin of `class: probe`. It receives the current view and a `subject` — usually
another plugin's output directory — and returns `answer` in out.json. It contributes nothing
to the stack; the service refuses to merge anything a probe writes beyond its answer.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..core import Service


class ProbeResult:
    def __init__(self, name, answer, facts, out):
        self.name, self.answer, self.facts, self.out = name, answer, facts, out

    @property
    def died(self) -> bool:
        return self.out is None

    def to_dict(self):
        return {"probe": self.name, "answer": self.answer, "facts": self.facts, "died": self.died}


class ProbeService(Service):
    def __init__(self, runner):
        self.runner = runner        # registry.run_plugin(manifest, params, extra) -> (facts, out)

    def ask(self, manifest, params: dict, subject: dict, run_dir: Path) -> ProbeResult:
        if manifest.cls != "probe":
            raise ValueError(f"{manifest.name} is class {manifest.cls}, not probe")
        if not manifest.reversible:
            raise ValueError(f"probe {manifest.name} must declare reversible: true")
        facts, out = self.runner(manifest, params, {"subject": subject}, run_dir)
        answer = (out or {}).get("answer", {}) if out else {}
        for slot in ("columns", "masks", "embeddings", "matrices", "objects"):
            if out and out.get(slot):
                raise ValueError(f"probe {manifest.name} tried to contribute {slot}; a probe "
                                 f"contributes nothing")
        return ProbeResult(manifest.name, answer, facts, out)
