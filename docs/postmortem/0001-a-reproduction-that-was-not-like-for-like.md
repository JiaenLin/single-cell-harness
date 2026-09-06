# 0001 — A reproduction that was not like-for-like

**Date** 2026-09-06
**Phase** the child-interface round (ADR-0013); the class belongs to Phase 5
**Invariants** D6, P3, X2 — and the acceptance rule of [`CHILD_CONFORMANCE.md`](../CHILD_CONFORMANCE.md)

## Executive summary

An interface-only change to a tool was checked by re-running it and comparing the output against
a sealed earlier run. The comparison reported **80 of 96 tables differing and two units missing**,
which reads exactly like *the change moved every number* — the most serious finding this project
can make. It was not that. The two runs had been given **different label columns**, so each unit
held different cells (one arm: 30,119 against 30,831), and separately a `git pull` into the tool's
checkout **while the job was running** made the tool refuse its last two instances. Neither run was
wrong; the comparison was. The durable lesson: **a reproduction must take its parameters from the
reference run's own record, not from a script that happens to run the same tool** — and until the
inputs are shown to match, a difference in the outputs is evidence about nothing.

## What broke

`scprofile_interface_reproduce.pbs` (PBS 706246) ran the tool at the interface commit over the
same object and design as the sealed reference run `20260902T150608Z__scprofile-7836afb`, with
`--no-cache` so every instance was computed rather than adopted. Its `COMPARISON.txt` reported:

```
units 21 new vs 21 ref
identical: 16 of 96 per-unit tables
aged_chow/ccc_edges.csv: 954 rows differ (of 1195 / 1193)
young_HFD: table set differs [] vs ['ccc_edges.csv', ...]
VERDICT: DIFFERENT
```

Believed, on a first reading: the interface change altered the numbers, and ADR-0013 forbids
merging it. Actually true: the numbers were untouched, and every table computed **on the same
cells** reproduced exactly.

## The mechanism

In order, and both halves were mine rather than the tool's.

1. **The reference run was made through a different entry point.** The project drives this tool
   two ways: a stage job script, and the tool's own development-cycle job, which passes the label
   column as a variable. The reference run had been made the second way, with the **forced** label
   column; the reproduction copied the stage script and passed the **unforced** one.
2. **The label column decides which cells exist in a unit.** Cells the annotator declined carry a
   sentinel under one column and a real call under the other. A unit is built by selecting cells
   with a non-sentinel label, so the two runs put different cells into every unit — `aged_chow`
   held 30,119 in one and 30,831 in the other. Every downstream number is computed per unit.
3. **The tell was present and was not read.** Four units — the ones whose cell counts happened to
   coincide — reproduced all five numeric tables *exactly*. A change that moved numbers would not
   spare four units and ruin seventeen.
4. **The reference run's own record said which column it used.** `report.json` carried
   `label_key: cell_type_forced` in plain sight. The reproduction never opened it.
5. **Separately: the tool changed under a running job.** Two commits were pushed and pulled into
   the tool's checkout while 706246 was in flight. The tool's own drift guard noticed and refused
   its last two instances rather than report a run made by two versions — which is why two units
   were missing. The guard was right; the hand on `git pull` was not.

## Why every check missed it

| check | why it did not fire |
|---|---|
| `sch conform <repo>` | reads a repository. It has no notion of two runs, so it cannot ask whether they are comparable |
| `sch conform --run <dir>` | reads one run: run key, seal, commit, logs, status. Every one of those passed on both runs, and every one of them would pass on two runs of completely different analyses |
| the job's own seal | checks that the products exist. It sealed `FAILED` — correctly, but because `COMPARISON.txt` reported a difference, not because the inputs disagreed. A seal that is right for the wrong reason teaches nothing |
| the prediction in the job header | named precisely what should be **identical in the output** and said nothing about what must be **identical in the input**. A prediction about outputs silently presumes the inputs match |
| the tool's drift guard | fired, and only on the second half. It runs *during* a job; nothing asks whether the checkout is quiet *before* one is submitted |
| the tool's `STATUS.json` | said `ok`, truthfully — the run succeeded. It sat beside the job's `FAILED.txt`, and two contradicting seals in one directory is a state a reader must never meet |

The gap is one sentence wide: **nothing in the system compares the two runs' inputs before
comparing their outputs.**

## Guardrails

1. **`sch conform --run NEW --against REF`** — new. Reads both runs' own records and reports
   whether a comparison between them means anything: the same input, the same declared
   parameters, the same `state_version`, a *different* tool commit (that is the point), and
   neither run having adopted a reused result. It refuses to be silent when a run records no
   parameters at all: that is a finding about the tool, and it links back to S7 and S9.
   Implemented in `sch/conform/checks.py`, tested in `tests/test_conform_doctor.py`.
2. **The acceptance rule in [`CHILD_CONFORMANCE.md`](../CHILD_CONFORMANCE.md) now says it**: a
   reproduction takes its parameters from the reference run's own record. A job that hard-codes
   them from a stage script is not a reproduction of that run.
3. **The job's seal supersedes the tool's** when they share a directory, and the tool's verdict
   survives in `STATUS.json`. Two seals disagreeing side by side is now impossible.
4. **A finding for the site layout, recorded here rather than acted on unilaterally:** the layout
   document's rule that *a decision recorded in a document does not reach a process already
   running* applies to a `git pull` exactly as it applies to a retirement. A tool checkout should
   not be updated while a job using it is queued or running, and the tool-drift guard that caught
   this is the only thing that currently notices.

The second submission (PBS 706253), with the reference run's own label column and the checkout
left alone, reported `identical: 90 of 90 numeric per-unit tables` on identical cell counts, and
the change was merged on that evidence.

## What this record does not claim

That the guardrail would have caught it unaided. `--against` compares what the runs recorded; a
tool that records its parameters badly will pass it while remaining incomparable. It moves the
failure from *silent* to *named*, which is the only thing a check can honestly promise.
