# 0010 — the last turn on cellchat: the author's pass, three reruns, every stage done

**Date** 2026-09-15. **Follows** docs/blind/0009 (the figure set) and ADR-0025 (the last turn on
cellchat). **What is being tested** whether a cold author can close what the layout left open
through the maker's gates, whether the loop then reaches a run on which the maker reads every
stage done, and what that costs.

**The runs** `20260915T011642Z__scprofile-ad1b76d__04_profile__rerun` (PBS 711706, cellchat
0.37.0, SEALED, 122 plates), `20260915T023343Z__scprofile-a7f247b__04_profile__rerun` (PBS
711745, 0.38.0, SEALED by the seal and failed in substance: 110 plates, the differential heatmaps
refused on every contrast), `20260915T032050Z__scprofile-789b0b4__04_profile__rerun` (PBS
711759, 0.39.0, SEALED, 122 plates - the run the turn ends on); the writing runs
`20260915T044935Z…written` (FAILED W3), `20260915T045830Z…written` (3 of 3, `audited` todo on
the replay) and `20260915T051032Z__scprofile-c1e92c2__04_profile__written` (PBS 711781, 3 of 3,
build 9 of 9, test 8 of 8).

**The agents** Claude Sonnet, cold, in clean rooms under the session's `blind13/`: scProfile as a
cellchat-only `git archive` copy with a pristine twin for the diff, re-exported at each commit
the round made; the harness at HEAD; no git anywhere; the run's copy. The roles: an author (three
exchanges), three lookers, a writer, a reviewer.

## Measured before any agent starts

- the plan at 0.36.0: 24 entries, every axis under budget, the host's list declared; the audit
  owed 5 findings on 3 kinds, two of them answered by the host for a fresh look;
- the four items the layout decided by its own order, listed in the ADR;
- the mechanism the writing needed first: a section is stale when the set changes (8d9ab65).

## Cost, filled in after

| | |
|---|---|
| the author: items answered, version, gates, exchanges | five items in one pass, then two more exchanges on the fresh look's worksheet; 0.36.0 to 0.37.0, 0.38.0, 0.39.0; every gate green each time (validate 0/0, build 9 of 9, layout every axis under budget with the interaction at 19 of 20, rules 4 held, 0 fitted literals, 0 cohort terms); one refusal-equivalent (two of the repository's own tests held a legend to its capitals); 33 stated records and 0 `--answer` records written; 534k tokens, 194 tool uses, 71 min |
| the reruns: job, wall time, seal | three: 711706 (34 min, SEALED, 122 plates, cores peak 2.18 on 2); 711745 (34 min, SEALED with 110 plates - the author's palette name refused by the tool on every contrast, invisible to the seal and to `capacity --promised`, which read the promise per function); 711759 (31 min, SEALED, 122 plates, cores peak 4.9 on 2, sustained 1.2) |
| lookers: figures handed, recorded, refusals, defects marked | 40 + 11 handed (40 carried by content hash on the first, 69 on the last); 51 recorded, 0 refused, 32 marked defect; 578k tokens, 120 tool uses, 36 min |
| audited after the fresh look | 33 findings on 12 kinds - every disclosure a stated answer had closed came back when the legends were rewritten; after the author's re-statement: 0 open; on the final run: 0 open, with one finding the third looker names as hidden by a kind-level closure that says something else |
| writer | started from the earlier run's section; every citation re-checked against the new brief, every described plate against the plate; 1,860 words carried in on the first `--write`, 4 claims, 0 refusals, 1 defect reported (the hint after `--write` without `--plugin`); 241k tokens, 38 tool uses, 21 min |
| reviewer | 13 verdicts: 12 standing, 1 narrowed - the per-arm totals plate is unrestricted while the two-scale ratios are on shared populations, so the cited plate does not reproduce the quoted fold; 0 refusals; 303k tokens, 66 tool uses, 17 min |
| defects of the mechanism | 4 fixed test-first the same day; 1 recorded open (below) |
| agents, tokens, wall time | 6 cold agents: 1.66M tokens, 418 tool uses, 145 min of agent time; three reruns (99 min on the node), three writing seals; about six hours of wall clock |

## Defects of the mechanism, as they came

1. Two of the repository's own tests held a legend to "RED means" and "NO interaction" in
   capitals, so the author's legends in register broke the gate; the tests match in any case
   now (ad1b76d).
2. `capacity --promised` read a promise as kept when the upstream function had drawn for any
   entry: twelve differential heatmaps failed on every contrast and the run sealed with 110
   plates of 122. A promise is per entry now (7 commits later than it should have been; the
   run found it, the seal did not).
3. The hint printed after `paper --write` omitted `--plugin` (the writer of the final run).
4. The carry of looks across sibling runs is a read-time view and does not travel: the run's
   replay on the cluster, with no sibling beside it, read 69 looks and 38 stated answers as
   never taken, and the first writing seal FAILED W3. `scprofile review --adopt` appends what a
   run relies on to its own ledger, by bytes and - the second seal showed - by entry for a
   kind's disclosure whose words still stand (42230d8, d2e4bfb, c1e92c2).
5. **Recorded, not fixed.** A stated disclosure closes every later finding on its kind, whatever
   the finding says: the third looker's label-overlap finding on a paired scatter was closed by
   the disclosure about population rosters. The worksheet prints these as "DISCLOSED, AND THE EYE
   SAYS MORE", so the words are not lost, but `audited` reads done over them.

And a cost that is not a defect: a legend rewritten in register unbinds every disclosure stated
in its old words. The author re-stated 22 by hand; a verb that re-binds a kind's disclosure to
its new sentence would have made that one command.

## Results

| prediction | held? | what happened |
|---|---|---|
| A1 | held | one refusal-equivalent, 0.36.0 to 0.37.0 once, interaction 19 of 20, no hand edit by the dispatcher |
| R1 | held | 122 plates, SEALED, promised answered, cores peak 2.18 on 2 |
| E1 | **failed** on the letter | 33 open after the fresh look, not two; 0 after the author's re-statement; the two host kinds carried no finding |
| W1 | **failed** on the letter | the staleness built and exercised in the suite, not on a live run; the re-carried section cites the re-lettered panels; 12 standing and 1 narrowed, not 13 standing |
| M1 | held | writing seal 3 of 3; build 9 of 9, test 8 of 8 on the run's own replay - the first run of the arc with every stage done |
| B1 | **failed** | four fixed against three predicted, one recorded open |

Three reruns for one predicted, three writing seals for one. The plugin is at 0.39.0 and the loop
names nothing left on it. The eight held-out plugins are next, and this record is what they are
measured against.
