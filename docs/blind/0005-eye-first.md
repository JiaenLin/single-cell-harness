# 0005 — the eye before the pen, driven by cold agents on the audit reproduction's replay

**Date** 2026-09-13. **Follows** docs/blind/0004 (the test phase of a sealed run, cold) and
ADR-0018 (the audit repairs, the run measures, the eye comes before the pen). **What is being
tested** whether the reordered test phase drives itself: cold lookers mark what must change from
the tool's own words alone, the maker's `audited` names the eye's findings as the plugin's debt,
and a writer cannot rest a claim on a plate the run's own record calls wrong.

**The run** `20260913T035511Z__scprofile-2b1038e__04_profile__audit` (PBS 711028, the audit
reproduction of ADR-0018 step 5, cellchat on the cohort against 710985). Its light half is
brought to the workstation writable under its own run key by the rsync the agenda prints; that
copy is the replay every agent works on. The predictions below are written while the job runs
and before any agent starts.

**The agents** Claude Sonnet, cold, each rooted in a clean room under the session scratchpad
(`blind5/`): the harness at c8c6fc8 and scProfile at 2b1038e as `git archive` copies, no git;
the replay; the scratch Python. Three roles, light on purpose - the round's proof is the order,
not the volume:

- **the dispatcher** is the round's author and does nothing an agent could not: runs the maker's
  `status --run` on the replay, runs the review command the station prints to obtain two shards
  of the scan set, launches one looker per shard, then the writer. Every command the dispatcher
  runs is one the status or the agenda printed.
- **lookers** (two): open every figure of their shard from the replay and record a look per
  figure with the review command exactly as the tool printed it. They are told nothing about
  `--defect`; the tool's own printout is what says when to pass it.
- **the writer**: reads the brief and the agenda, records claims with `--claim --cites` on
  figures of the scan set, including at least one on a figure a looker marked; carries in a
  section. Does not review.

## Measured before any agent starts

To be filled from the maker's status on the replay before the lookers start: `measure`,
`promised`, `looked_at`, `audited` (with the repaired count and the residue), `written`,
`delivered`.

## Predictions, written before the agents start

- **B1** Two cold lookers, given the run's status and the review command's shards, record
  looks with `--defect` on the panels that must change without asking a question; at least one
  defect is marked (the two-panel heatmaps with no arm label are still the plugin's). The
  lookers learn the flag from the tool's printout alone.
- **B2** After the looks, the maker's status reads `looked_at` done and `audited` owing, naming
  at least one eye defect by kind in the looker's own words.
- **B3** The writer's `--claim --cites <a marked plate>` is refused and the refusal quotes the
  finding; a claim on a clean plate is recorded.
- **B4** The brief marks every figure with an open finding, and the agenda's write task is
  BLOCKED naming them while `scprofile next` says the same first.
- **B5** The agents meet at most two defects of the mechanism, each fixed test-first the same
  day.

## Cost, filled in after

| | |
|---|---|
| lookers, figures per looker, refusals, defects marked | |
| writer: claims attempted, refused, recorded; words carried in | |
| maker or host defects found | |
| dispatcher commands | |
| edits outside the clean rooms | |
| agents, tokens, wall time | |

## Results

To be written after the agents finish.
