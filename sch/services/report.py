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

    def cost(self) -> dict:
        """WHAT THE STAGE COST (GOALS A3.4: cells, wall time and peak memory per stage; autodev
        W042), from the events that measured it: `cells` counted on the stage's observations; `wall_s`
        the sum over the stage's runs of each run's wall time (the scheduler's `resources_used` under
        pbs, the clock under local); `peak_mem_kb` the largest run's peak as the scheduler accounted
        it. Every figure names its events; a run that measured nothing is named with the reason, and
        no figure is filled in for it."""
        keep = ("plugin", "run", "executor", "job", "exit", "from", "wall_s", "peak_mem_kb", "ncpus",
                "cput_s", "unknown")
        runs = [dict({k: e.get(k) for k in keep}, event=e["seq"]) for e in self.prov.of_kind("run/cost")]
        cells = (self.prov.of_kind("cost/cells") or [None])[-1]
        wall = [r for r in runs if r["wall_s"] is not None]
        mem = [r for r in runs if r["peak_mem_kb"] is not None]
        top = max(mem, key=lambda r: r["peak_mem_kb"]) if mem else None
        return {"cells": ({"value": cells["cells"], "event": cells["seq"]}
                          if cells else None),
                "wall_s": ({"value": round(sum(r["wall_s"] for r in wall), 3),
                            "events": [r["event"] for r in wall]} if wall else None),
                "peak_mem_kb": ({"value": top["peak_mem_kb"], "run": top["run"], "event": top["event"]}
                                if top else None),
                "measured_by": sorted({str(r["from"]) for r in runs}),
                "unmeasured": [{"run": r["run"], "plugin": r["plugin"], "event": r["event"],
                                "missing": [k for k in ("wall_s", "peak_mem_kb") if r[k] is None],
                                "why": r["unknown"]}
                               for r in runs if r["wall_s"] is None or r["peak_mem_kb"] is None],
                "runs": runs}

    def render(self, out_path, stack_declaration: dict, include_scratch: bool = False) -> dict:
        numbers = self.collect(include_scratch=include_scratch)
        self.inv.a2_nothing_scratch_quoted(list(numbers.values()))
        self.inv.p2_numbers_resolve(numbers)
        gates = [e for e in self.prov.of_kind("gate/result")]
        escapes = [e for e in self.prov.of_kind("escape/decision")]
        report = {"stack": stack_declaration, "numbers": numbers,
                  "gates": gates, "escapes": escapes, "cost": self.cost(),
                  "cannot_show": stack_declaration.get("cannot_show", {})}
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=1, sort_keys=True, default=str))
        self.prov.append("report/rendered", path=str(out_path), numbers=len(numbers))
        return report
