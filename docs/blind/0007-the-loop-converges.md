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
| the rerun: job, wall time, seal | PBS 711115 FAILED (two instances lost to a segfault and a truncated read; compute1020); PBS 711118 FAILED (five instance processes died with signal 11; compute1020); PBS 711119 pinned to compute1017 SEALED after 35 minutes: 18 of 18 instances done, 945 figures, 249 compare plates, every declared plot produced, memory answered; cores measured sustained 2.67 with one-second bursts to 58.7 on a share of 4 (over its share, the plugin's to cap); cost measured high, 3,285 s per 100,000 cells, against a declared medium |
| lookers: figures handed, recorded, refusals, defects marked | 83 handed in two shards of 42 and 41 (56 of the 139 carried from the sibling run); 83 recorded, 0 refused, 39 marked defect (24 and 15); one looker recorded `--answer` on three answered figures and found the answered state did not clear until it recorded a plain look; 556k tokens, 170 tool uses, 21 and 12 min |
| audited after the fresh look | 44 open findings on 25 kinds (HOST 3, PLUGIN 5, TOOL 17), from 36 kinds; station 6b: 1 machine residue (the across_design footnote, fixed at HEAD, redrawn only by a rerun); station 7: 80 of 80 kinds and 139 of 139 of the scan set looked at |
| writer and reviewer | |
| defects of the mechanism | |
| agents, tokens, wall time | |

## Defects of the mechanism, as they came

**1. The status told the agent to run a command the parser refuses** (harness fd33e31). The
rerun's status, run against the sealed copy, printed `apply it: sch dev convert cost ... --apply`
for the cost stage, which owed (measured high, declared medium), and the maker's parser answered
"invalid choice: 'cost'". The `answer it:` line had been given the rule in 3dec780 - a run-side
stage is not a maker verb, so the way to answer it is the repository's own command, printed
filled - and the `apply it:` line and the advance command had not. The dispatcher ran the
repository's own command instead (`capacity --cost --declare cellchat`), which wrote `"cost":
"high"` into the plugin as the tool's own edit (scProfile 6801c34), and the fix went into both
lines test-first. Found by the maker's status, not by an agent.

**2. The footnote the first look asked for was drawn over the key it sat beside** (scProfile
8eb7a3b). Station 6b's one machine residue on the rerun: the design panel's aliasing footnote
was placed at a fixed y below the figure box, the marker key was anchored there too, and on
twelve samples and three measures the audit found them through each other by two thirds. The
host's own collision, the one `stamp_below` was written for in the repairs round: the footnotes
are now collected while the grid is drawn and placed after the key, each below everything
before it. Reproduced test-first on a synthetic design of the rerun's shape; the rerun's own
table audits clean under the fix.

**3. The review's listing told the reader to open fifty-six figures whose looks had carried**
(scProfile, the commit after 8eb7a3b). The status counted them "reviewed (carried)", the shards
left them out, and the list beneath printed the same names under "have not been looked at, or
were redrawn since ... Open each one". `outstanding` had the rule - a carried look is a look -
and the listing had not. Found on the run after both lookers finished; test-first on the
two-run fixture the carry was written against.

**4. Two labels floated above any point with no leader** (scProfile, the commit after that). The
second look's N4: the vertical solve cleared nine names in one corner within its cap, so the
ladder had nothing to answer, and the two it had carried highest stood a third of the clump's
height above their points. A label the solve moves further than eight points from its point now
gets the ladder's leader, ladder or not. Reproduced test-first through the role panel with
crafted strengths of the run's shape.

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
That submission sealed FAILED too: five of eighteen instance processes died with signal 11
between 23 and 363 seconds in, one contrast's compare aborted with signal 6, and the tool
recorded each as died, named the five `run --resume` would re-run, and exited 0. No error of
this round's code raises a signal; the two failed submissions ran on compute1020 and the four
clean ones on compute1016 and compute1017, and the scheduler reports both nodes free and healthy,
so the node is a correlation and not a finding. The seventh submission is pinned to compute1017
to test it.
It sealed SEALED there, 18 of 18 instances done, which leaves the node as the working explanation
of the two failures and nothing more: two submissions on one node lost instances to signals no
code of this round can raise, and one on another node lost none.

## Results

To be written after the agents finish.
