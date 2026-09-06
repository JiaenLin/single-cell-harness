"""The runtime protocol from a plugin's side (PLUGIN_FORMAT.md §6). Stdlib only.

    from protocol import Run                     # copied beside run.py, or on SCH_PROTOCOL path
    run = Run.from_argv()                        # reads in.json named on argv[1] or $SCH_IN
    keep = ...                                   # do the work
    run.mask("min_value", rows, reason="value below floor")
    run.finish(headline="masked 12 of 100")      # writes out.json; status ok

Three outcomes are deliberately distinguishable to the kernel: no out.json (the plugin died),
out.json with nothing in it (it ran and found nothing — a result), out.json with entries.
`run.refuse(reason, fix=...)` writes status refused with the fix named.
"""
from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path


class Run:
    def __init__(self, inp: dict, in_path: str):
        self.inp = inp
        self.in_path = in_path
        self.out_dir = Path(inp["out_dir"])
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.keys = dict(inp.get("keys") or {})
        self.params = dict(inp.get("params") or {})
        self.sentinels = list(inp.get("sentinels") or [])
        self.profile = inp.get("profile", "")
        self.data = inp.get("data")
        self.design = inp.get("design")
        self.upstream = dict(inp.get("upstream") or {})
        self.probe_answer = inp.get("probe_answer")
        self._out = {"contract": inp.get("contract", "1.0"), "plugin": inp.get("plugin", ""),
                     "version": inp.get("plugin_version", ""), "state_version": inp.get("state_version"),
                     "status": "ok", "headline": "", "wrapped_versions": {},
                     "columns": {}, "embeddings": {}, "matrices": {}, "masks": {}, "graphs": {},
                     "objects": {}, "tables": [], "figures": [], "answer": {}, "absent": [],
                     "caveats": [], "numbers": {}}

    @classmethod
    def from_argv(cls) -> "Run":
        p = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SCH_IN")
        if not p:
            sys.stderr.write("no in.json: pass its path as argv[1] or set SCH_IN\n")
            sys.exit(2)
        with open(p, encoding="utf-8") as fh:
            return cls(json.load(fh), p)

    # ------------------------------------------------------------- contributions
    def _rel(self, sub: str, fname: str) -> str:
        d = self.out_dir / sub
        d.mkdir(parents=True, exist_ok=True)
        return f"{sub}/{fname}"

    def column(self, name: str, values: dict, id_field: str = "id"):
        """`values` maps identity -> value. Merged by identity, never by position."""
        rel = self._rel("columns", f"{name}.csv")
        with open(self.out_dir / rel, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow([id_field, "value"])
            for k, v in values.items():
                w.writerow([k, "" if v is None else v])
        self._out["columns"][name] = rel

    def mask(self, name: str, keep: dict, reason: str, id_field: str = "id"):
        """A WHOLE mask over every identity: keep True/False, with the criterion as reason."""
        rel = self._rel("masks", f"{name}.csv")
        with open(self.out_dir / rel, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow([id_field, "keep", "reason"])
            for k, v in keep.items():
                w.writerow([k, "1" if v else "0", "" if v else reason])
        self._out["masks"][name] = rel

    def embedding(self, name: str, rows: dict, id_field: str = "id"):
        """`rows` maps identity -> list of floats (CSV form; the profile may bind to npy)."""
        rel = self._rel("embeddings", f"{name}.csv")
        with open(self.out_dir / rel, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh, lineterminator="\n")
            k = len(next(iter(rows.values()))) if rows else 0
            w.writerow([id_field] + [f"d{i}" for i in range(k)])
            for key, vec in rows.items():
                w.writerow([key] + list(vec))
        self._out["embeddings"][name] = rel

    def table(self, name: str, rows: list, header: list):
        rel = self._rel("tables", f"{name}.csv")
        with open(self.out_dir / rel, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(header)
            w.writerows(rows)
        self._out["tables"].append(rel)
        return rel

    def figure(self, path_rel: str, caption: str, source_rel: str = None, vector_rel: str = None):
        self._out["figures"].append({"path": path_rel, "caption": caption,
                                     "source": source_rel, "vector": vector_rel})

    def number(self, key: str, value):
        """A number the plugin wants report-visible. The kernel records it as an event (P2)."""
        self._out["numbers"][key] = value

    def answer(self, **kw):
        self._out["answer"].update(kw)

    def absent(self, what: str, why: str):
        self._out["absent"].append({"what": what, "why": why})

    def caveat(self, text: str):
        self._out["caveats"].append(text)

    def wrapped(self, tool: str, version: str):
        self._out["wrapped_versions"][tool] = version

    # ------------------------------------------------------------- terminal
    def finish(self, headline: str = "", status: str = "ok"):
        self._out["headline"] = headline
        self._out["status"] = status
        with open(self.out_dir / "out.json", "w", encoding="utf-8") as fh:
            json.dump(self._out, fh, indent=1, sort_keys=True)
        return 0

    def refuse(self, reason: str, fix: str = ""):
        self._out["answer"]["refusal"] = {"reason": reason, "fix": fix}
        return self.finish(headline=f"refused: {reason}", status="refused")

    # ------------------------------------------------------------- reading
    def read_csv(self, path) -> list:
        with open(path, newline="", encoding="utf-8") as fh:
            return list(csv.DictReader(fh))

    def read_design(self) -> list:
        return self.read_csv(self.design) if self.design else []


# ---------------------------------------------------------------------------- companions
class CompanionRun:
    """What a companion sees: the facts the kernel wrote about one run of its plugin."""

    def __init__(self, facts: dict):
        self.facts = facts
        self.out = facts.get("out") or {}
        self.out_dir = Path(facts.get("out_dir", "."))
        self.plugin = facts.get("plugin", "")

    def masked_observations(self) -> set:
        return set(self.facts.get("masked") or [])

    def observation_count(self) -> int:
        return int(self.facts.get("observations", 0))

    def contributions(self) -> list:
        return list(self.facts.get("contributions") or [])

    def table(self, name: str) -> list:
        for rel in self.out.get("tables") or []:
            if Path(rel).stem == name:
                with open(self.out_dir / rel, newline="", encoding="utf-8") as fh:
                    return list(csv.DictReader(fh))
        raise FileNotFoundError(f"no table named {name!r} in {self.out_dir}")

    def keyed(self, rel: str, id_field: str = "id") -> dict:
        with open(self.out_dir / rel, newline="", encoding="utf-8") as fh:
            return {r[id_field]: r for r in csv.DictReader(fh)}


class Inv:
    def __init__(self):
        self.checks = []

    def check(self, description: str):
        def deco(fn):
            self.checks.append((description, fn))
            return fn
        return deco

    def fail(self, message: str):
        raise AssertionError(message)


def companion(register) -> int:
    """Entry for invariant.py:  `if __name__ == "__main__": sys.exit(companion(register))`.

    argv[1] = facts.json written by the kernel, argv[2] = where to write the result.
    Exit 1 if any check fails; the result names the check and the fact that failed.
    """
    facts_path, result_path = sys.argv[1], sys.argv[2]
    with open(facts_path, encoding="utf-8") as fh:
        run = CompanionRun(json.load(fh))
    inv = Inv()
    register(inv)
    held, failed = [], []
    for desc, fn in inv.checks:
        try:
            fn(run)
            held.append(desc)
        except AssertionError as e:
            failed.append({"check": desc, "message": str(e)})
        except Exception as e:  # a companion that crashes has not checked anything
            failed.append({"check": desc, "message": f"companion raised {type(e).__name__}: {e}"})
    with open(result_path, "w", encoding="utf-8") as fh:
        json.dump({"plugin": run.plugin, "held": held, "failed": failed}, fh, indent=1)
    return 1 if failed else 0
