"""`sch dev` - the development suite the family's own agents use to extend it.

It is deliberately ignorant of what it is extending. Each repository declares its extension
points in DEVPOINTS.yaml and every command below reads that declaration, so scProfile's kernels,
scIntegrate's methods, scQC's steps, scAnno's mechanisms and the harness's plugins are served by
one implementation that names none of them. See `points.py` for why that is not a convenience.
"""
from .baseline import check as baseline_check, fingerprint, record as baseline_record
from .fixture import HAZARDS, ROLES, SHAPES, write as fixture_write, write_both
from .job import emit as job_emit, write as job_write
from .ladder import TIERS, format_run, run as ladder_run
from .points import DevpointsError, existing, load, point, registration
from .scaffold import new

__all__ = ["DevpointsError", "HAZARDS", "ROLES", "SHAPES", "TIERS", "baseline_check",
           "baseline_record", "existing", "fingerprint", "fixture_write", "format_run",
           "job_emit", "job_write", "ladder_run", "load", "new", "point", "registration",
           "write_both"]
