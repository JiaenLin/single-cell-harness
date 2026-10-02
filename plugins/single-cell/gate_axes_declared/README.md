# axes_declared (single-cell)

## What it does
Reads the `axes` probe's answer and measures nothing. REFUSE where the gene identifiers contradict
the declared species. REVIEW where the species is measurable and undeclared, where only the symbol
convention disagrees (a convention is not proof), or where the assay - which no count matrix can
show - was never declared. PASS where nothing the data can show contradicts the declaration. The
worst verdict over the axes is the gate's; every finding is kept in the answer.

## Why it exists
The second cohort (harness ADR-0027) found three tools that took a cohort axis without checking it
against the data, and each would have run a human cohort as the first cohort's mouse in silence.
A plugin that depends on an axis opts in with `gates: {axes_declared: required}`.

## Report surface
A verdict, a reason built from the findings that carried it, and every finding with its own
verdict - so a REFUSE on the species never hides a REVIEW on the assay. The probe's answer is
beside it in `probe_answer`, so the numbers behind a refusal are on the record with it.

## Cost
Nothing beyond the probe's: one read of the probe's answer, no data opened. It runs wherever the
probe ran and can be re-asked against any mounted plugin's view with the probe.

## Known limitations
It checks only what the probe can measure: the species, and only decisively from gene identifiers.
A declared assay is accepted as declared - nothing here can contradict it. It is opt-in: a plugin
that depends on an axis must name it in its `gates`, and one that does not is not checked.
