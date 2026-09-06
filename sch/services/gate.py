"""Gates: refusals that are monotonic (G4), measured with a probe (G3), escaped as pairs (G2).

The kernel runs the gate's `measures_with` probe ONCE and hands the answer to the gate in
`in.json["probe_answer"]`. The gate cannot measure differently from the probe because it does
not measure at all — one instrument, two consumers, structurally.

The verdict of a set of gates is the strongest refusal any of them returns. PASS is the
abstention; REVIEW is an abstention with a note; REFUSE is the only thing that stops a mount,
and only a recorded escape lifts it. A refusal is a RESULT in the stream, never an exception.
"""
from __future__ import annotations

from pathlib import Path

from ..core import Service
from ..registry.manifest import VERDICTS

RANK = {"PASS": 0, "REVIEW": 1, "REFUSE": 2}


def reduce_verdicts(verdicts) -> str:
    """Order-independent by construction: max over a total order."""
    best = "PASS"
    for v in verdicts:
        if v not in RANK:
            raise ValueError(f"verdict {v!r} is not one of {VERDICTS}")
        if RANK[v] > RANK[best]:
            best = v
    return best


class GateResult:
    def __init__(self, gate, verdict, number, reason, probe_answer, escaped=False, died=False):
        self.gate, self.verdict, self.number, self.reason = gate, verdict, number, reason
        self.probe_answer, self.escaped, self.died = probe_answer, escaped, died

    def to_dict(self):
        return {"gate": self.gate, "verdict": self.verdict, "number": self.number,
                "reason": self.reason, "probe_answer": self.probe_answer,
                "escaped": self.escaped, "died": self.died}


class GateService(Service):
    def __init__(self, runner, probe_service, provenance):
        self.runner = runner
        self.probes = probe_service
        self.prov = provenance

    def evaluate(self, gates: list, subject: dict, run_root: Path, escapes: dict,
                 mounting: str, resolve_plugin) -> tuple:
        """`gates` is a list of gate manifests. `escapes` maps gate name → {why, by}.

        Returns (verdict, [GateResult]). Every gate runs; nothing short-circuits, so the order
        cannot change what is recorded.
        """
        results = []
        for gm in gates:
            probe_name = str(gm.data.get("measures_with", ""))
            if not probe_name:
                raise ValueError(f"gate {gm.name} names no probe (measures_with)")
            pm = resolve_plugin(probe_name)
            pr = self.probes.ask(pm, dict(gm.data.get("probe_params") or {}), subject,
                                 run_root / f"probe-{pm.name}-for-{gm.name}")
            if pr.died:
                res = GateResult(gm.name, "REFUSE", None, f"probe {pm.name} died", None, died=True)
                self.prov.append("gate/died", gate=gm.name, probe=pm.name, mounting=mounting)
                results.append(res)
                continue
            facts, out = self.runner(gm, dict(gm.data.get("params") or {}),
                                     {"subject": subject, "probe_answer": pr.answer},
                                     run_root / f"gate-{gm.name}")
            if out is None:
                res = GateResult(gm.name, "REFUSE", None, "gate died", pr.answer, died=True)
                self.prov.append("gate/died", gate=gm.name, mounting=mounting)
                results.append(res)
                continue
            ans = out.get("answer", {}) or {}
            verdict = str(ans.get("verdict", "")).upper()
            if verdict not in RANK:
                verdict = "REFUSE"
                ans["reason"] = f"gate returned verdict {ans.get('verdict')!r}, not one of {VERDICTS}"
            res = GateResult(gm.name, verdict, ans.get("number"), ans.get("reason", ""), pr.answer)
            self.prov.append("gate/result", gate=gm.name, verdict=verdict, number=ans.get("number"),
                             reason=ans.get("reason", ""), probe=pm.name, mounting=mounting)
            if verdict == "REFUSE" and gm.name in escapes:
                esc = escapes[gm.name]
                if not esc.get("why") or not esc.get("by"):
                    raise ValueError(f"escape for {gm.name} needs both why and by")
                ask = self.prov.append("escape/ask", gate=gm.name, mounting=mounting,
                                       refused=ans.get("reason", ""), number=ans.get("number"))
                self.prov.append("escape/decision", gate=gm.name, mounting=mounting, ask=ask,
                                 by=esc["by"], why=esc["why"], flag=str(gm.data.get("escape", "")))
                res.escaped = True
            results.append(res)
        effective = [r.verdict for r in results if not r.escaped]
        return reduce_verdicts(effective), results
