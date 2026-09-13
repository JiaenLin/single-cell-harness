# 0005 — the eye before the pen, driven by cold agents on the audit reproduction's replay

**Date** 2026-09-13. **Follows** docs/blind/0004 (the test phase of a sealed run, cold) and
ADR-0018 (the audit repairs, the run measures, the eye comes before the pen). **What is being
tested** whether the reordered test phase drives itself: cold lookers mark what must change from
the tool's own words alone, the maker's `audited` names the eye's findings as the plugin's debt,
and a writer cannot rest a claim on a plate the run's own record calls wrong.

**The run** `20260913T042903Z__scprofile-c260046__04_profile__audit` (PBS 711029, the second
submission of ADR-0018 step 5's audit reproduction, cellchat on the cohort against 710985; the
tool's own seal on it, the job's FAILED.txt for one arithmetic clause of a prediction, every
substantive prediction held). Its light half is
brought to the workstation writable under its own run key by the rsync the agenda prints; that
copy is the replay every agent works on. The predictions below are written while the job runs
and before any agent starts.

**The agents** Claude Sonnet, cold, each rooted in a clean room under the session scratchpad
(`blind5/`): the harness at 091f09f and scProfile at c260046 as `git archive` copies, no git;
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

The maker's status on the replay, before the lookers started (`blind5/work/status_before.txt`):
build 7 of 8 (`freshness` owes: the plugin's version was set four commits ago - the plugin's
pre-existing debt); test 1 of 6: `measure` OWES with its apply line printed (the fitted 2.2 +
13.0 against a declared 3.1 + 5.7 - applied to the real plugin as step 6, scProfile ad6a691,
after this reading), `promised` done, `looked_at` OWES 0 of 139, `audited` BLOCKED "no drawing
issue remains after the host repaired 5 on 2 panel(s); the eye has looked at 0 of 139 - the
audit is not clean until the eye has", `written` and `delivered` OWE. `scprofile next` on the
replay says: open the figures, 139 outstanding. The review command split the 139 into two
shards of 70 and 69 and printed, beneath them, the record command with `[--defect]` and one line
saying what the flag means; that printout is the whole of what the lookers were told about it.

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
| lookers, figures per looker, refusals, defects marked | 2 lookers, 70 and 69 figures, 139 of 139 recorded (one figure recorded twice), **0 refusals**, **70 marked `--defect`** (29 + 41), the flag learned from the review command's printout alone |
| writer: claims attempted, refused, recorded; words carried in | 4 attempted, 1 refused (the one citing a marked plate, on purpose), 3 recorded; a 1,553-word section carried in - accepted by the tool as it then was (defect 3 below) |
| maker or host defects found | **5**, all fixed test-first the same day, none worked around: by the dispatcher, `next` printing a blocked task's "do: write it" and every seal reading "no exit recorded" (scProfile d83c85e); by the writer, `paper --write` accepting a section resting on marked plates while the agenda called the task blocked, the agenda's `defend` task reading done with 27 claims unreviewed so `next` said "defended", and the brief's two orders of the same contrasts (this round's last scProfile commit) |
| dispatcher commands | 10 - the maker's status before, the review split, the status after the looks, `next`, `agenda`, the brief on disk, and after the fixes the verifying `--write`, `next` and `--brief` |
| edits outside the clean rooms | 0; the real checkouts changed only by commits; nothing on the cluster's run changed |
| agents, tokens, wall time | 3 cold Sonnet agents, about 1.05 M tokens: lookers 0.41 M and 0.44 M, writer 0.20 M; the lookers 23 and 25 minutes in parallel, the writer 16; about 45 minutes of wall time |

## Results

Written 2026-09-13 after the agents finished; their reports are beside this record in the
session's `blind5/work/`.

- **B1 HELD.** Both lookers recorded every figure of their shard and marked what must change
  with `--defect` - 29 and 41 of 139 - having been told nothing about the flag beyond the one
  line the review command prints under the shard list. Neither asked a question; neither was
  refused a note. Looker 1 batched its seventy calls in a small script around the printed
  command, as blind 0004's lookers did.
- **B2 HELD.** After the looks the maker's status read `looked_at` done and `audited` owing:
  "no drawing issue remains after the host repaired 5 on 2 panel(s); 70 eye finding(s) on 70
  panel(s); the eye has looked at 139 of 139", with "FIX THESE, the eye's findings" naming the
  panels in the lookers' own words. The eye's findings are the stage's debt, as designed.
- **B3 HELD.** The writer's claim on Figure 1, marked by a looker, was refused with the
  looker's words quoted, and nothing was recorded for it; three claims on clean plates were
  recorded. The writer checked the ledger's count rose by exactly three.
- **B4 HELD in two places and failed in the third.** The brief printed by `paper --brief` marked
  45 of the paper's 90 figures with their findings and ended "the pen waits on them"; the
  agenda's write task was BLOCKED naming them. `scprofile next` printed "NEXT: Write the
  result" over that same reason and "do: write it" - the dispatcher met it before the writer,
  and it is one of the five defects.
- **B5 FAILED on the count, in the right direction: five, not at most two**, and every one was
  fixed test-first the same day. Two were the dispatcher's: a blocked first task printed as the
  next thing to do, and a seal reader that never parsed the seal's own `exit=` line. Three were
  the writer's, and the largest is the round's real finding: **the pen did not fully wait.** The
  agenda called the write task blocked and `--claim` refused a marked plate, but `paper --write`
  accepted a section resting on the same plates and the agenda then printed the task done with
  the blocked reason under it; `next` went on to say the result was "defended" because a claims
  file existed, while the tool's own strict check and the maker said 27 claims had no verdict;
  and the brief listed the same four contrasts in two orders because its table asked the design
  panel with the run's controls and its headings asked without. Now a section citing a figure
  with an open finding is refused naming the figure and the finding, a task is done only when
  its evidence is, `defend` means every claim has a verdict, and the brief has one order. Each
  was verified on the replay by the dispatcher after the fix: the writer's own section is
  refused naming Figure 90 and the looker's words; `next` says 27 claims await a verdict; the
  brief's two lists agree.

What the round proves: on a real run of the reordered mechanism, cold lookers mark what must
change from the tool's words alone, the maker names their findings as the plugin's debt in
their words, and a claim cannot rest on a plate the run's own record calls wrong. What it found:
the section could, and two of the tool's own readers disagreed with the maker about what was
done - closed the same day. What it does not prove: that an author fixes the seventy findings and
a rerun clears `audited` - the plugin's next build, under the top rule.

One observation stands: the cluster job's `FAILED.txt` (its grading verdict) and the tool's own
`SEALED.txt` (the run completed) sit side by side in one directory, and the tool's `next` reads
the run as FAILED. Two writers of one name is a layout matter for a later round, recorded here.
