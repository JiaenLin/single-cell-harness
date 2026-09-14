# 0008 — the loop's third turn: the author's twenty-two, the basis, the cap, the number

**Date** 2026-09-14. **Follows** docs/blind/0007 (the loop's second turn) and ADR-0021 (the third
turn). **What is being tested** whether the number moves when the author is handed the whole
worksheet: the composed ratio on its own basis, a cold author's third answer to the twenty-two
kinds and the thread cap, the rerun through the emitted job, the lookers, the pen and the seal.

**The run the turn starts from** `20260913T170934Z__scprofile-7c188a4__04_profile__rerun` (PBS
711119), whose copy under the session's `blind5/` carries 83 looks and 56 carried, 44 findings on
25 kinds, the writer's section, 11 claims with verdicts and the rendered page; the writing run
`20260913T185809Z__scprofile-7c188a4__04_profile__written` (PBS 711120) beside it.

**The agents** Claude Sonnet, cold, in clean rooms under the session's `blind8/`: scProfile at
ac52840 as a cellchat-only `git archive` copy with a pristine twin for the diff, the harness at
18dade8, no git anywhere;
the rerun's copy; the scratch Python. The roles as before: the author, the dispatcher, two
lookers, a writer, a reviewer.

## Measured before any agent starts

The worksheet on the rerun's copy: 44 open findings on 25 kinds, owners HOST 3, PLUGIN 5, TOOL 17.
The three host kinds are answered in the mechanism (blind 0007 defects 2 and 4, and the third is
the data's) and redraw on the rerun; the 22 are the author's, plus the thread cap the cores gate
names. The maker's status on the rerun's copy: build 8 of 8 (the version at 0.31.0, cost high),
test 6 of 8 with `cores` and `audited` owing.

## Predictions, written before the agents start (the ADR's)

- **R1, R2** the composed ratio's basis; **T1** the cap; **A1** the author answers all
  twenty-three without a question; **A2** at most eight kinds survive (25 now); **A3** no finding
  on the three host kinds; **S1** the seal holds; **B1** at most four defects.

## Cost, filled in after

| | |
|---|---|
| the author: kinds edited, kinds answered, version, gates | 21 of 22 kinds edited, 1 answered (1 ledger record), 3 host kinds skipped, the cap written as one R prelude read by all three entry scripts; 0.31.0 to 0.32.0; two refusals sent back and answered (a comment naming an arm; the cap prelude copied three times and a compare argv passed unread - both the repository's gates, not the dispatcher's eye); validate 0/0, build 8 of 8, 0 vocabulary hits, 0 fitted literals, 4 rules held, gate 97 green; pasted as scProfile 457c98d; 403k tokens, 194 tool uses, 47 min |
| the rerun: job, wall time, seal | PBS 711122 (`20260914T001114Z__scprofile-457c98d__04_profile__rerun`, compute1017) FAILED after 17 minutes: 12 of 18 instances refused, every one on `future.globals.maxSize` (741 MiB of globals exported to the workers the author's cap put CellChat's future plan on; the six smallest units fit under 500 MiB and ran), and the burst unchanged at a peak of 61.7 cores on a share of 4 (sustained 1.13) because the thread variables were set inside R after the BLAS had loaded; memory fitted at 2.9 GB + 6.5 GB per 100,000 cells; sent back to the author - the version stays, the run produced no result at it. Resubmitted as PBS 711127 (`20260914T004319Z__scprofile-b0cfe88__04_profile__rerun`) with the author's correction: the thread variables set in the environment every Rscript is started with, the future plan sequential, only mc.cores and data.table threads set inside R |
| lookers: figures handed, recorded, refusals, defects marked | |
| audited after the fresh look | |
| writer and reviewer | |
| defects of the mechanism | |
| agents, tokens, wall time | |

## Defects of the mechanism, as they came

**1. The portability suite crashed on the author's one-kernel tree** (scProfile, the commit after
365ad3b). The cold author is handed a cellchat-only export, which is also what the cluster runs;
the suite's organism checks indexed `scenic`, `velocity` and `cellcycle` by name and died with
`KeyError: 'scenic'` before printing a verdict, so the author reported "no FAIL line names
cellchat.py" from a suite that had not finished. The checks now skip on a tree without those
kernels and say which they needed; the checks about the tree still run. Found by the author.


## Results

To be written after the agents finish.
