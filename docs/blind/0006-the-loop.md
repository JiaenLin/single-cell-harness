# 0006 — the loop end to end: a cold author answers the worksheet, the job reruns, the eye looks again

**Date** 2026-09-13. **Follows** docs/blind/0005 (the eye before the pen) and ADR-0019 (the loop
closes). **What is being tested** whether the loop drives itself with no person in it: an author
who has only the audit's worksheet answers it, the maker's emitted job reruns the plugin, the
lookers are handed only what changed, the audit clears or names what survived, and the pen opens.

**The run the loop starts from** `20260913T042903Z__scprofile-c260046__04_profile__audit` (PBS
711029), whose replay under the session's `blind5/` carries the 70 findings two lookers marked on
46 kinds, the writer's section and its three claims. The rerun is `20260913T082230Z__scprofile-3ee26e7__04_profile__rerun`, emitted by `sch dev job`
from the replay (`jobs/rerun_0006.pbs`, 514 non-figure products expected, the tree frozen at
the author's commit scProfile 3ee26e7) and submitted by `jobs/submit_rerun.sh`.

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

## Defects of the mechanism, as they came (B5 counts them)

1. **`sch dev job` and `sch dev baseline` unreachable through the CLI** (harness 736243f). The
   dispatcher's first command, the dry emit of the rerun, died on `a.action`: since fe5ecae the
   convert-only branches (`account`, `build`, the command stage) sat at the top of `cmd_dev`, and
   the last one returned for every subcommand after it. The module functions were tested; the
   command a person types was not. With it, the emitter's summary reported the tree's commit it
   could not read (None) instead of the one it was given, and counted the figures a redraw does
   not expect. Test-first: `ReachableThroughTheCli`, `test_the_summary_says_what_the_job_says`.
2. **An after-line's verdict sealed the run FAILED** (harness d3f6388). The declared `run.after`
   commands ran under the job's `set -e`, so `status` owing or `capacity --memory` refusing a
   declaration would have aborted a job whose products were all there, and the maker's status
   would never have been written. Now each after-line records `after: exit N` in the log; the
   seal reads the products. Test-first: the emitted script run in bash with a failing after-line
   seals SEALED.

3. **The worksheet cut the eye's words and split one plan entry in two** (scProfile, the
   commit after the author's answer). Named by the author: the note was cut at 300 characters,
   which cut the actionable half of a two-clause finding often enough that it read the run's
   ledger instead of the sheet; and a per-item entry (`native_patterns`, drawn as
   `_incoming` and `_outgoing`) surfaced as two headings, so a reader answering "each kind
   once" would fix the same entry twice. Now a finding is grouped under the plan entry that
   claims its file, and the words are printed whole; on the real sheet 46 kinds became 43.
   Test-first in `test_findings_become_work.py`.

The author's answer met the gate before it met the repository: the portability scan refused
`kernels/cellchat.py:774` - the comments quoted this cohort's population labels where they said
what was found - and the refusal went back to the author with the rule ("no project, person,
machine or cohort appears anywhere") to amend, the version left alone. What the gate could not
name: the labels the built-in shapes do not know (the cohort's other populations), which the
dispatcher's vocabulary check found on three more comment lines; the site's own term list
(`SCPROFILE_FORBIDDEN_TERMS`) is the mechanism for those and is not set on this machine.

The round's own checks before the author's answer is pasted: `sch dev rules --since f127a2b`
4 held, 0 broken; `sch dev convert overfit` 0 fitted literals; the cohort's own vocabulary (106
terms read from the run: populations, pathways, units, contrasts) is held against the author's
diff before the paste, and the repository's portability scan runs in the commit gate.

## Results

To be written after the agents finish.
