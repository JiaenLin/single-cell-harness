#!/usr/bin/env python3
"""A gate is a probe plus a threshold plus a verdict. It receives the probe's answer and never
measures. Monotonic: PASS abstains, REVIEW abstains with a note, REFUSE refuses."""
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
run = protocol.Run.from_argv()
ans = run.probe_answer or {}
refuse_at = float(run.params.get("refuse_ratio", 3.0))
review_at = float(run.params.get("review_ratio", 2.0))
ratio = ans.get("max_ratio")
inert = any(m.get("inert") for m in (ans.get("masks") or {}).values())
if not ans.get("arms_known"):
    verdict, reason = "REVIEW", "no design arms known to the probe; the differential test did not run"
elif ratio is None:
    verdict, reason = "PASS", "nothing removed, or nothing to compare"
elif ratio >= refuse_at:
    verdict, reason = "REFUSE", f"removal rate differs {ratio:.2f}x between arms (refuse at {refuse_at}x)"
elif inert:
    verdict, reason = "REVIEW", "removal magnitude makes the ratio test inert; the number is not evidence"
elif ratio >= review_at:
    verdict, reason = "REVIEW", f"removal rate differs {ratio:.2f}x between arms (review at {review_at}x)"
else:
    verdict, reason = "PASS", f"removal rate differs {ratio:.2f}x between arms"
run.answer(verdict=verdict, number=ratio, reason=reason, refuse_ratio=refuse_at, review_ratio=review_at)
sys.exit(run.finish(headline=f"{verdict}: {reason}"))
