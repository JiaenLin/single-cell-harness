"""The report service: report-visible ⟺ replayable (P2).

A report is JSON whose every number carries the sequence number of the event it came from.
Rendering runs the P2 and A2 companions; a number with no event, or with a scratch tag, fails
the render rather than appearing.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..core import Service


class ReportService(Service):
    def __init__(self, provenance, invariant):
        self.prov = provenance
        self.inv = invariant

    def collect(self, include_scratch: bool = False) -> dict:
        numbers = {}
        for e in self.prov.numbers():
            if e.get("scratch") and not include_scratch:
                continue
            numbers[f"{e['plugin']}/{e['key']}"] = {"value": e["value"], "event": e["seq"], "key": e["key"],
                                                    "plugin": e["plugin"], "scratch": bool(e.get("scratch"))}
        return numbers

    def render(self, out_path, stack_declaration: dict, include_scratch: bool = False) -> dict:
        numbers = self.collect(include_scratch=include_scratch)
        self.inv.a2_nothing_scratch_quoted(list(numbers.values()))
        self.inv.p2_numbers_resolve(numbers)
        gates = [e for e in self.prov.of_kind("gate/result")]
        escapes = [e for e in self.prov.of_kind("escape/decision")]
        report = {"stack": stack_declaration, "numbers": numbers,
                  "gates": gates, "escapes": escapes,
                  "cannot_show": stack_declaration.get("cannot_show", {})}
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=1, sort_keys=True, default=str))
        self.prov.append("report/rendered", path=str(out_path), numbers=len(numbers))
        return report
