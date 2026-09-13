# 0006 — the loop end to end: a cold author answers the worksheet, the job reruns, the eye looks again

**Date** 2026-09-13. **Follows** docs/blind/0005 (the eye before the pen) and ADR-0019 (the loop
closes). **What is being tested** whether the loop drives itself with no person in it: an author
who has only the audit's worksheet answers it, the maker's emitted job reruns the plugin, the
lookers are handed only what changed, the audit clears or names what survived, and the pen opens.

**The run the loop starts from** `20260913T042903Z__scprofile-c260046__04_profile__audit` (PBS
711029), whose replay under the session's `blind5/` carries the 70 findings two lookers marked on
46 kinds, the writer's section and its three claims. The rerun's key is filled in below when the
job is submitted.

**The agents** Claude Sonnet, cold, in clean rooms under the session's `blind6/`: the harness at
3dec780 and scProfile at d7b6d37 as `git archive` copies, no git; the replay of 711029 (the same
copy the lookers wrote in); the scratch Python. Roles, in the loop's order:

- **the author**: given the worksheet the tool prints and the clean-room copy of scProfile,
  which holds the real `kernels/cellchat.py`. Answers every kind once: an edit of the plan entry
  or the code with the version bumped, or `review --answer` for a plate the upstream draws as
  it should. Runs the build gates the worksheet names. Reports which kinds it edited and which
  it answered, and why.
- **the dispatcher**: pastes the author's answer into the repository as the author's (the one
  edit of the plugin the top rule allows), commits it under the author's words, exports the
  tree, emits the rerun with `sch dev job --ref <the replay> --redraw ...` and the worksheet's
  prediction, validates and submits it; brings the new run's light half beside the old; runs
  the review split; launches the lookers, the writer, the reviewer; sends the written layer
  back. Every command it runs is one a status, an agenda, a worksheet or a refusal printed.
- **lookers** (two): handed the review command's shards - only what was redrawn or answered -
  and told nothing else.
- **the writer** and **the reviewer**: as in blind 0004, once `audited` reads clean.

## Measured before any agent starts

The maker's status on the replay of 711029 (`blind6/work/status_before.txt`): build 7 of 8,
`freshness` owing (`version` 0.28.0 set by eabe490, five commits since, one of them the tool's own
memory declaration); test 4 of 6: `measure`, `promised`, `looked_at` (139 of 139) and `delivered`
done, `audited` owing - "no drawing issue remains after the host repaired 5 on 2 panel(s); 70 eye
finding(s) on 70 panel(s); the eye has looked at 139 of 139; 765 drawn and NOT measured by any
machine (432 recorded by the plugin's companion ..., 333 recorded by nothing)" - with "answer it:"
naming the worksheet; `written` owing behind it (27 claims undefended). The worksheet, as printed
(`blind6/work/worksheet.txt`): 70 open findings on 46 kinds; owners HOST 8, PLUGIN 7, TOOL 31. The
host's eight are already fixed in the mechanism (ADR-0019 step 2, scProfile 0f4236a) and are not
the author's; the rerun redraws them. The 333 "recorded by nothing" are the old tool's: the rerun
at d7b6d37 records every host panel (step 1).

## Predictions, written before the agents start (the ADR's L1-L6 and B1-B5)

The rerun, graded by the emitted job:

- **L1** the emitted job runs the reference's command with the interpreter, the tree's commit
  verified at start, and seals SEALED with every non-figure product of the reference present.
- **L2** every raster figure the new run holds carries an audit in `report.json` or
  `panels.json`: station 6b prints no "recorded by nothing".
- **L3** on the replay beside the old, looks carry: a figure whose bytes did not change is not
  outstanding; every redrawn or answered figure is.
- **L4** the host's eight panel kinds carry no machine finding after repair.
- **L5** `promised` done and `measure` answered on the new run without a hand on the file.
- **L6** the maker's status on the new run reads `audited` owing only on what the eye has not
  yet re-looked, and names it.

Blind 0006:

- **B1** a cold author, given the worksheet and nothing else, answers every kind without a
  question: edits for at least half the kinds, answers for the rest, the version bumped, and
  the plugin passes `scprofile validate` and the maker's build status afterwards.
- **B2** after the rerun the lookers are handed only what was redrawn or answered - fewer than
  the 139 of the first look - and record it without a refusal.
- **B3** `audited` clears, or names at most five kinds that survived a fresh look, in the
  lookers' words.
- **B4** the writer writes without a claim or a section resting on an open finding; a second
  agent rounds every claim; the section renders; `delivered` reads done; the writing seal holds
  its three predictions.
- **B5** the agents meet at most three defects of the mechanism, each fixed test-first the same
  day.

## Cost, filled in after

| | |
|---|---|
| the author: kinds edited, kinds answered, version, gates | |
| the rerun: job, wall time, seal, L1-L6 | |
| lookers: figures handed, recorded, refusals, defects marked | |
| audited after the second look | |
| writer and reviewer: claims, rounds, verdicts, words | |
| maker or host defects found | |
| dispatcher commands | |
| agents, tokens, wall time | |

## Results

To be written after the agents finish.
