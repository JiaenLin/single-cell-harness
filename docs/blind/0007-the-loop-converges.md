# 0007 — the loop's second turn: the host's ten answered, the author's second answer, the fresh look

**Date** 2026-09-13. **Follows** docs/blind/0006 (the loop end to end) and ADR-0020 (the loop
converges). **What is being tested** whether a second turn of the same loop clears the audit:
the host's ten findings fixed in the mechanism, a cold author's second answer to the 26 plugin
and tool kinds, the rerun through the emitted job, the lookers on what was redrawn, and the pen
and the seal after.

**The run the turn starts from** `20260913T100732Z__scprofile-4c6112f__04_profile__rerun` (PBS
711062), whose copy under the session's `blind5/` carries the second look's 121 looks and 66
findings on 36 kinds, the writer's section, the 29 rounded claims and the rendered page.

**The agents** Claude Sonnet, cold, in clean rooms under the session's `blind7/`: scProfile at
fca2fba (the host's ten answered) as a cellchat-only `git archive` copy with a pristine twin for
the diff, the harness at e7ddb54, no git anywhere; the rerun's copy; the scratch Python. The
roles as in blind 0006: the author, the dispatcher, two lookers, a writer, a reviewer.

## Measured before any agent starts

The worksheet on the rerun's copy (`blind7/work/worksheet.txt`): 66 open findings on 36 kinds,
owners HOST 10, PLUGIN 4, TOOL 22. The ten host kinds are answered in the mechanism (ADR-0020
step 1) and will redraw on the rerun; the 26 are the author's. The maker's status
(`blind7/work/status_before.txt`): build 8 of 8 (`freshness` done, the version at 0.30.0), test 5
of 6 with `audited` owing.

## Predictions, written before the agents start (the ADR's)

- **H2** after the rerun, a fresh look records no finding on any of the ten host kinds.
- **A1** the cold author answers the 26 kinds without a question, edits at least half, bumps the
  version once, and passes validate and the build status.
- **A2** after the rerun and the fresh look, at most eight kinds survive (36 now).
- **D1, D2, C1** are graded in their own steps (the composer's route, the writing run's siblings,
  cores and cost).
- **B1** the agents meet at most six defects of the mechanism, each fixed test-first the same day.

## Cost, filled in after

| | |
|---|---|
| the author: kinds edited, kinds answered, version, gates | 16 of 26 kinds edited (3 plugin, 13 tool), 10 answered (21 ledger records), 10 host kinds skipped; 0.30.0 to 0.31.0; scaffold, validate, build 8 of 8 green; the portability scan refused one comment and the author generalised six lines itself; the dispatcher's vocabulary check found two more (a pathway, an arm level), sent back; 291k tokens, 98 tool uses, 27 min |
| the rerun: job, wall time, seal | |
| lookers: figures handed, recorded, refusals, defects marked | |
| audited after the fresh look | |
| writer and reviewer | |
| defects of the mechanism | |
| agents, tokens, wall time | |

## Defects of the mechanism, as they came

(none so far this turn: the author met no refusal it could not act on)

**The first submission of the rerun** (PBS 711115, `20260913T160311Z__scprofile-db066f3__04_profile__rerun`,
27 minutes) sealed FAILED on one unit's products. Two instances failed on the upstream, each recorded
as refused by the tool: one segfaulted inside CellChat's bootstrap, one could not read back the
matrix it had just been handed ("scan(file, nmax = nz)"), and the second wrote no object, so the
three contrasts that needed it exited in a tenth of a second with no plate and `promised` named
the one plot never drawn. Neither failure is in code this round touched; the same units ran clean
on the four runs before. The run measured what nothing had measured before: every instance
carries wall and CPU time, and the cores model reads a sustained 2.4 cores on a share of 4 with
one-second bursts of 49 to 61 - threads or workers the plugin does not cap, on a node eighteen
instances share, which is the likeliest cause of the two flakes. The cost band reads high at 3,062
seconds per 100,000 cells against a declared medium. The cores gate was refined from that
(scProfile 7c188a4): the declaration is held against the sustained use, and a burst past twice
the share is named as the plugin's to cap, never a number to declare. Resubmitted as PBS 711118
(`20260913T163928Z__scprofile-7c188a4__04_profile__rerun`).

## Results

To be written after the agents finish.
