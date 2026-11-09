#!/usr/bin/env python3
"""Companion: the stack's fold of the masks delivers exactly what scQC delivered.

Two relationships this plugin owns, asserted on the run that is mounted:
  - the observations the per-criterion masks remove are exactly those scQC's own `keep` column
    drops - so a criterion scQC applied and did not tabulate, or a keep column scQC wrote with no
    criterion behind it, fails the mount instead of moving the view silently;
  - they are exactly the identifiers in scQC's removal ledger, its record of what left and why.
"""
import csv
import importlib.util
import os
import sys
from pathlib import Path


def _protocol():
    """The stdlib-only protocol helper: where the kernel says it is, or a copy beside this file."""
    for c in (os.environ.get("SCH_PROTOCOL"), Path(__file__).with_name("protocol.py")):
        if c and Path(c).exists():
            spec = importlib.util.spec_from_file_location("sch_protocol", str(c))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    sys.exit("protocol.py not found; set SCH_PROTOCOL or copy sch/plugin/protocol.py beside run.py")


protocol = _protocol()


def _tables(run, suffix):
    return [run.out_dir / rel for rel in (run.out.get("tables") or []) if rel.endswith(suffix)]


def _scoped(run, library, barcode):
    ans = run.out.get("answer") or {}
    return f"{ans['scope_of'][library]}{ans['identity_joiner']}{barcode}"


def register(inv):
    @inv.check("the masks remove exactly what scQC's own keep column drops")
    def _(run):
        masked = run.masked_observations()
        dropped = set()
        for p in _tables(run, ".percell.csv"):
            with open(p, newline="", encoding="utf-8") as fh:
                for row in csv.DictReader(fh):
                    if row["keep"] != "True":
                        dropped.add(_scoped(run, row["sample"], row["barcode"]))
        if masked != dropped:
            inv.fail(f"{len(masked - dropped)} masked that scQC's keep column keeps; "
                     f"{len(dropped - masked)} dropped by scQC's keep column that no mask removes")

    @inv.check("the masked observations are exactly scQC's removal ledger")
    def _(run):
        masked = run.masked_observations()
        ledger = set()
        for p in _tables(run, "removal_ledger.csv"):
            with open(p, newline="", encoding="utf-8") as fh:
                for row in csv.DictReader(fh):
                    library, _, barcode = row["identifier"].partition("|")
                    ledger.add(_scoped(run, library, barcode))
        if masked != ledger:
            inv.fail(f"{len(masked - ledger)} masked with no ledger row; "
                     f"{len(ledger - masked)} ledger rows not masked")


if __name__ == "__main__":
    sys.exit(protocol.companion(register))
