#!/usr/bin/env python3
"""Companion: every masked observation is named in the removal record, and only those."""
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



def register(inv):
    @inv.check("every masked observation is named in the removal record")
    def _(run):
        masked = run.masked_observations()
        idc = run.facts.get("identity", "barcode")
        recorded = {row[idc] for row in run.table("removal_record")}
        if masked - recorded:
            inv.fail(f"{len(masked - recorded)} observations masked without a record")
        if recorded - masked:
            inv.fail(f"{len(recorded - masked)} records name observations that are not masked")


if __name__ == "__main__":
    sys.exit(protocol.companion(register))
