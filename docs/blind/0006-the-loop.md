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
| the author: kinds edited, kinds answered, version, gates | 28 kinds edited, 10 answered (21 ledger records), 8 host kinds skipped; 0.28.0 to 0.29.0; validate 0 errors, build 8 of 8; first answer refused by the portability scan, amended in 7 comment lines; 473k + 538k tokens, 173 + 40 tool uses, 51 + 8 min |
| the rerun: job, wall time, seal, L1-L6 | PBS 711051 FAILED in 25 s (defects 5, 6); PBS 711058 FAILED in 50 s (defect 7); PBS 711059 - filled in below |
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

4. **The emitted job named its reference by the path it was read at** (harness d7af719). The
   replay lives under the workstation's scratch directory, and `sch conform` refused the job as
   using node-local `/tmp`: a run's identity is its key, the same on every machine, and the
   header and the seal now carry that. Test-first in `Job`.

The rerun was first submitted as PBS 711051 at 08:23 UTC by `jobs/submit_rerun.sh` (validator
OK, queue super, 64 cores, 360 GB, walltime 4 h). It sealed FAILED after 25 seconds, and two
defects fell out of it:

5. **The emitted job rewrote every flag named like an output** (harness ce480cb). The reference
   argv carried `--prefix <site>/env`, where this tool keeps its plugin environments; the
   emitter's name list treated `--prefix` as an output and sent it to the new, empty run
   directory, so all 18 instances failed in a second with "no environment at ...". The flag
   rewritten is now the one whose value is the reference run itself (its directory or its key),
   whatever it is called; the name list is the fallback. The rest of the job did what defects 1
   and 2 were fixed for: the after-lines recorded their verdicts (`capacity --promised` exit 2,
   `--memory` exit 2), the maker's status was written, and the seal read FAILED on 514 expected
   products. Test-first in `Job`.
6. **A run that ran nothing sealed ok** (scProfile, the commit after 3ee26e7). The tool's own
   seal said `status=ok`, exit 0, "kernels ran, results merged, report written", with a run card
   of zero instances, while its report said "NO OBJECT WRITTEN: no plugin ran". `run` now exits
   1 with that sentence as its headline when no plugin ran; the report, the card and the
   capacity record are still written. Test-first in `test_status_contract.py`, on a fixture
   with no environment at the prefix.

The second submission: `20260913T091745Z__scprofile-03210cd__04_profile__rerun`, the tree at scProfile 03210cd (the author's answer plus the
run's verdict fix), the emitted command now moving only `--out` and keeping `--prefix` at the site's
environment directory. It failed the same way in a minute (PBS 711058), and the seventh defect
fell out of it:

7. **The job verified the tree and ran something else** (harness, the commit after ce480cb). The
   host interpreter resolves `scprofile` from the full checkout beside the cellchat-only export,
   so a nine-plugin resolver demanded the shared environment, which does not exist at the site's
   prefix, and every instance failed with "no environment". The record shows it: the run's
   argv[0] is under the full checkout while the seal says the tree's commit matched. The tree
   now goes first on PYTHONPATH and a module command is asked where its package imports from
   before it runs; anything outside the tree is refused with both paths named. Test-first in
   `Job`, with a decoy package that must not run.

The third submission: `20260913T092545Z__scprofile-03210cd__04_profile__rerun` (PBS 711059), the
same tree (scProfile 03210cd). It ran: the import guard reported the tool's code from the verified
tree, all 18 instances computed, 879 figures, the tool's own seal ok, `capacity --memory` answered
(fit 2.2 + 13.1 against the declared 2.4 + 14.3), the maker's status written to the run's logs.
Two things it found:

8. **The job expected what the directory held, not what the run recorded** (harness 6bc800e).
   The seal read FAILED on four `STATUS.<reader>.json` files that the reference's hand-written
   job had left by running `agenda`, `next`, `paper` and `review` there, with every product of
   the run itself present. The expectation now comes from the reference run's own `STATUS.json`
   record; the directory scan is the fallback for a reference without one. Test-first in `Job`.
   So L1's "seals SEALED" failed on this submission for a reason that was the job's, not the
   run's; it is graded again on the next.
- **The author's answer broke two plates**, which the loop caught where it should: `promised`
  owes, exit 2, naming `netVisual_chord_cell` (h 1800 to 1300 left circlize no room: "not
  enough space for cells at track index '1'" on every pathway and arm) and
  `showDatabaseCategory` (par/mtext around a function that returns a plot object: "plot.new has
  not been called yet"). The maker's status names them and points at the plugin's own log,
  which says why; the two entries went back to the author with those lines, for a fix and a
  further version bump - the loop's own path, not the dispatcher's hand.

The author's second round (scProfile 4c6112f, cellchat 0.30.0): `native_database_category` fixed
(the object captured, printed, titled with grid), `nativecmp_chord_cell` reverted to its proven
size with the eye's finding answered in the ledger instead; gates green; the same checks before
the paste (0 cohort terms in the added lines). The fourth submission: `20260913T100732Z__scprofile-4c6112f__04_profile__rerun`, with the
expectation now the run's own record (507 products).
It sealed SEALED (PBS 711062, 27 minutes): the tree's commit matched and its code ran, every
product the reference recorded present, every after-line exit 0, `capacity --promised` reading
"every declared plot produced at least one file" (945 figures, the reference's count), `measure`
answered; the maker's status on the run: build 8 of 8, test 2 of 6 with `measure` and `promised`
done and `looked_at` owing 0 of 95. L1 and L5 hold on this submission.

9. **The drawing station named the pen before the eye** (scProfile b10f8a7). On a rerun's copy
   beside the old replay, station 6b read "17 eye finding(s) on 17 panel(s); the eye has looked
   at 0 of 93" and told the agent to answer the worksheet: the branch for open findings sat
   before the branch for an unlooked scan set. The look now comes first while any figure of the
   scan set has none, and the carried findings are named as waiting for it; the worksheet is for
   what survives. Test-first in `test_every_figure_is_measured.py`. (Seen on the third run's copy,
   which the network then cut short; graded again on the fourth's.)
10. **An answer did not carry to the run beside** (scProfile d903eb3). On the fourth run's copy the
    review carried 37 looks and 19 findings from the old replay by content hash and not one of the
    author's 21 answers, so the answered plates were not outstanding for a fresh look and the
    worksheet would have asked the same ten kinds again. An answer is bound to the bytes like a
    look: on the same bytes it carries, with the run it was given on named; on other bytes it does
    not. Test-first in `test_findings_become_work.py`. With it the review reads "19 answered -
    needs a look, 37 reviewed (carried), 913 unreviewed" and hands the lookers 70 of the 95.
11. **A rebuild of the pages dropped the compare plates' records** (scProfile 2129082). The
    run's own report recorded the compare phase's 249 plates as the companion's; the declared
    after-line `scprofile report --out` then rebuilt the pages with no `--prefix`, resolved no
    interpreter, returned before the pair loop and wrote `panels.json` with `native: []`, so
    station 6b read 249 figures "recorded by nothing" (L2 failed as the run came off the
    cluster). A rebuild now records what is on disk and launches nothing without an interpreter.
    Test-first in `test_every_figure_is_measured.py`. With the pages rebuilt on the copy, the
    station reads "681 drawn and NOT measured by any machine (681 recorded by the plugin's
    companion ..., 0 recorded by nothing)": L2 holds after the fix.

**L6 on the fourth run's copy** (after defects 9 and 10): the maker's status reads test 3 of 6,
`looked_at` owing with "OPEN THESE AND RECORD WHAT YOU SEE", `audited` owing with "no drawing
issue remains after the host repaired 4 on 2 panel(s); 19 eye finding(s) on 19 panel(s), 18 of
them answered by the author and awaiting a looker's fresh look; the eye has looked at 6 of 139"
and the arrow "look at the scan set first ... the findings that carry over wait for it". L6 holds.
The rebuild also regenerated the paper's list, so the scan set grew from 95 to 139 while the
lookers were on the first 70; the remainder is handed out after them, by the same command.

**The second look, first shards** (two cold lookers, 35 figures each, tool at the fixes): 70 of
70 opened and recorded, 0 notes refused, 36 marked as needing a change, 34 plain. Looker 1
marked 13, mostly the host's own panels (an unexplained dagger and band on three flow panels,
labels crowding on three role-shift panels, an unkeyed colour pair on the interaction panel, a
"no edge" callout drawn over real cells on the matrix, the role scatter's nine labels piled at
the origin, a cut axis title on the unit totals, an unexplained asterisk on the design grid) and
one of the author's (the database-category banner clipped on both edges); it settled the
author's answered F10 with a fresh look. Looker 2 marked 23, among them plates the author's edit
did not cure (the circle plots' two long labels still fused at the top of the ring after
`vertex.label.cex = 0.65`; the heatmap's second column label still clipped; the stacked rankNet's
new caption itself clipped at the left edge) and new findings (two arms printed as the same
rounded value "0.8"; a value label under its own replicate dot); it confirmed two answered plates
as they stand. The dispatcher's own page rebuild on the copy redrew the host's panels under the
lookers - 4 looks went stale and one was re-recorded - which is a cost of rebuilding beside a
live review, not of the mechanism. Looker 1 also noted that the open-findings digest counts one
instance per kind, so its defects on other instances of `C3_flow` and `C4_role_shift` are in the
ledger but not in the digest until the scan set points at them.

**The second look, second shards** (24 and 26 figures): 50 of 50 opened and recorded, 0 refused,
30 marked. Looker 1 re-looked at six answered plates, settled three and kept three (the
asymmetric colour bar, the unlabelled bubble columns, the two marginal scales are still on the
page whatever the upstream's reason). Looker 2 found the fused ring labels on four more
instances and the clipped rankNet caption on three, a right-margin bar drawn backwards for one
pathway, and a contribution panel whose shares sum to about 80% with nothing saying so. In all:
120 figures handed out over the two rounds, 0 refusals, 66 marked, every figure of the
139-figure scan set looked at.

12. **The eye station counted only this run's ledger** (scProfile 15a939c). With every figure
    looked at, the maker still read `looked_at` owing "102 of 139": the 37 looks carried from
    the old replay on identical bytes were not counted, though the review listed them as
    "reviewed (carried)". A carried look is a look. Test-first in
    `test_every_figure_is_measured.py`.

**The audit's verdict**: with the eye complete, the maker's status reads test 4 of 6 (`measure`,
`promised`, `looked_at`, `delivered` done), `audited` owing - "no drawing issue remains after the
host repaired 4 on 2 panel(s); 66 eye finding(s) on 66 panel(s); the eye has looked at 139 of
139" - and names the worksheet: 66 open findings on 36 kinds, owners HOST 10, PLUGIN 4, TOOL 22.
L6 holds. **B3 fails**: 36 kinds survived a fresh look, not five. Of the author's 28 edits, the
eye confirmed some cured (the axis ticks restored, the compare-interaction labels no longer
covered, the flow subtitle no longer clipped) and found others not (the circle plots' fused
labels after `vertex.label.cex`, the heatmap's clipped column label after the smaller font, the
rankNet caption the edit itself added, clipped). Ten host kinds carry new findings, the next
build of the mechanism.

The round's own checks before the author's answer is pasted: `sch dev rules --since f127a2b`
4 held, 0 broken; `sch dev convert overfit` 0 fitted literals; the cohort's own vocabulary (106
terms read from the run: populations, pathways, units, contrasts) is held against the author's
diff before the paste, and the repository's portability scan runs in the commit gate.

## Results

To be written after the agents finish.
