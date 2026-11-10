# W024: the first cohort's job scripts moved out of the harness

**Moved** 2026-11-09 by the W024 fix-up, on the coordinator's decision about the verifier's D1:
"the HPC layout puts a project's jobs in the project". The 29 files below were the scripts of runs
submitted on SAMBO (the ADR-0016 to ADR-0026 rounds). Their paths, hosts and samples are those runs'
provenance, so they belong with the cohort, not in the harness, whose leak guard now declares only the
five tier-II record paths. Nothing was edited on the way: each file is byte-identical to its last
harness commit below, and `git show 45ae11d:<path>` (the W024 branch's base) recovers it.

**Where they go.** The coordinator places them in SAMBO's `stages/04_profile/jobs/`, as a recorded
change to the PI's cohort folder. The harness keeps `jobs/submit_rerun.sh`, now a template that names
no site (`$HOME`), and `jobs/writing_seal.pbs`, whose submitter moved with the cohort's jobs.

**What stops being tested in the harness.** `tests/test_convert.py`'s checker class used to run the
writing job's embedded prediction checker; it now runs a synthetic job with the same shape. The
cohort's own checker is tested where the job now lives.

| file (path at 45ae11d) | last harness commit | date | what it is |
|---|---|---|---|
| `jobs/rerun_0006.pbs` | `437abf7` | 2026-09-14 | an emitted rerun (`sch dev job`) |
| `jobs/rerun_0007.pbs` | `437abf7` | 2026-09-14 | an emitted rerun (`sch dev job`) |
| `jobs/rerun_0008.pbs` | `437abf7` | 2026-09-14 | an emitted rerun (`sch dev job`) |
| `jobs/rerun_0009.pbs` | `437abf7` | 2026-09-14 | an emitted rerun (`sch dev job`) |
| `jobs/rerun_0010.pbs` | `d380cc6` | 2026-09-14 | an emitted rerun (`sch dev job`) |
| `jobs/rerun_0011.pbs` | `4f60ed6` | 2026-09-14 | an emitted rerun (`sch dev job`) |
| `jobs/rerun_0012.pbs` | `eaf7aeb` | 2026-09-14 | an emitted rerun (`sch dev job`) |
| `jobs/rerun_0013.pbs` | `b2e99d7` | 2026-09-15 | an emitted rerun (`sch dev job`) |
| `jobs/rerun_0014.pbs` | `14069a9` | 2026-09-15 | an emitted rerun (`sch dev job`) |
| `jobs/rerun_0015.pbs` | `858cb5f` | 2026-09-15 | an emitted rerun (`sch dev job`) |
| `jobs/rerun_0016.pbs` | `403ce2f` | 2026-09-15 | an emitted rerun (`sch dev job`) |
| `jobs/rerun_0017.pbs` | `f736f2a` | 2026-09-15 | an emitted rerun (`sch dev job`) |
| `jobs/rerun_0018.pbs` | `f736f2a` | 2026-09-15 | an emitted rerun (`sch dev job`) |
| `jobs/rerun_0019.pbs` | `f736f2a` | 2026-09-15 | an emitted rerun (`sch dev job`) |
| `jobs/rerun_0020.pbs` | `7e0b008` | 2026-09-15 | an emitted rerun (`sch dev job`) |
| `jobs/rerun_0021.pbs` | `7e0b008` | 2026-09-15 | an emitted rerun (`sch dev job`) |
| `jobs/rerun_0022.pbs` | `f383255` | 2026-09-15 | an emitted rerun (`sch dev job`) |
| `jobs/rerun_0023.pbs` | `9b1df10` | 2026-09-15 | an emitted rerun (`sch dev job`) |
| `jobs/rerun_0024.pbs` | `3b60227` | 2026-09-15 | an emitted rerun (`sch dev job`) |
| `jobs/audit_reproduction.pbs` | `437abf7` | 2026-09-14 | a one-off run on the cohort |
| `jobs/plan_reproduction.pbs` | `437abf7` | 2026-09-14 | a one-off run on the cohort |
| `jobs/enrichment_test_phase.pbs` | `4dfd9f5` | 2026-09-14 | a one-off run on the cohort |
| `jobs/signatures_probe.pbs` | `344dbca` | 2026-09-15 | a one-off run on the cohort |
| `jobs/writing_sambo.pbs` | `4dfd9f5` | 2026-09-14 | a one-off run on the cohort |
| `jobs/status_on_run.pbs` | `4dfd9f5` | 2026-09-14 | a one-off run on the cohort |
| `jobs/submit_audit_reproduction.sh` | `c8c6fc8` | 2026-09-13 | the submitter of a run on the cohort |
| `jobs/submit_plan_reproduction.sh` | `c00e74d` | 2026-09-12 | the submitter of a run on the cohort |
| `jobs/submit_enrichment_test_phase.sh` | `f0148b1` | 2026-09-12 | the submitter of a run on the cohort |
| `jobs/submit_writing_seal.sh` | `ee38d5e` | 2026-09-13 | the submitter of a run on the cohort |
