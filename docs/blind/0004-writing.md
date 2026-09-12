# 0004 — the test phase of a sealed run, driven by cold agents on its writing replay

**Date** 2026-09-13. **Follows** docs/blind/0003 (the build phase, cold) and ADR-0017 (the
analysis this proves or disproves). **What is being tested** whether scProfile's agent half -
looking, writing, defending, delivering - drives itself without a person, through the one
driver the maker prints, on a real sealed run.

**The run** `20260912T163648Z__scprofile-344993d__04_profile__plan` (PBS 710985, the fifth plan
reproduction, identical to the reference on every count). Its light half - report.json, panels,
945 figures, captions, the composed section and its 24 composed claims, the brief, the figure
list, the rendered pages; no objects - was brought to the workstation writable under its own
run key by the rsync the agenda prints. That copy is the replay every agent works on.

**The agents** Claude Sonnet, cold, each rooted in a clean room under the session scratchpad
(`blind4/`): the harness at ee38d5e and scProfile at 8e64eba as `git archive` copies, no git;
the replay; the scratch Python (anndata 0.10, numpy, pandas, matplotlib, scipy, pyyaml). Four
roles, because the agenda says the looking parallelises and the reviewer must not be the author:

- **the dispatcher** is the round's author, and does nothing an agent could not: runs the
  maker's `status --run` on the replay, runs the review command the station prints to obtain
  the shards, launches one looker per shard, then the writer, then the reviewer, then the
  writer's render, then sends the written layer back and submits the seal. Every command the
  dispatcher runs is one the status or the agenda printed; none is invented.
- **lookers** (one per shard): open every figure of their shard from the replay and record a
  note per figure with `scprofile review`. Nothing else.
- **the writer**: reads the brief, the composed section and the agenda; writes the result
  section against the result-section skill; carries it in with `paper --write`; records its
  own claims with `--claim --cites`. Does not review.
- **the reviewer**: given the replay, the figures and the claims ledger; puts every claim -
  composed and the writer's - to a round with `--round --reviewer`, told to refute each. Does
  not write.

**Where the work lands** the replay's written layer goes back to the cluster as the writing run
`<stamp>__scprofile-8e64eba__04_profile__written` (`jobs/submit_writing_seal.sh`), graded by
the maker's status and sealed; this record and the agents' reports.

## Measured before any agent starts

The maker's status on the replay, as it reads now: build 8 of 8 (judgement answered by the
validator); test: `measure` OWES (18 instances shared one job; the stage says so and names the
way out), `promised` done, `audited` OWES (43 text collisions across 5 of the plugin's own
matplotlib panels), `looked_at` OWES 0 of 139 of the scan set, `written` OWES (24 composed
claims, undefended), `delivered` OWES (FIGURE_REVIEW.jsonl absent; the section and the page
present).

## Predictions, written before the agents start

- **W1** The status's `finished_by` texts and the agenda are enough: no agent asks the
  dispatcher a question, and no agent invents a command that the status, the agenda or the
  brief did not print.
- **W2** The scan set is 139 figures and `review --plugin cellchat --shards N` splits exactly
  those; the dispatcher launches N lookers with the printed `--shard K` lists and the union of
  their looks covers the set. Predicted: `looked_at` reads done after the lookers, with at most
  a handful of refusals (short or duplicated notes), all the tool's refusals and none a defect.
- **W3** The writer carries in a section of at least 200 words that follows the brief's
  headings verbatim, states the reference of every contrast, and cites figures of the scan set;
  it records at least 5 claims of its own; the composed claims stay.
- **W4** The reviewer rounds every claim (24 composed + the writer's) with a named reviewer, and
  at least one verdict is `narrowed` or `withdrawn` - the composed claims are measured
  skeletons a reader can push on, and the loop's own smell is "no claim was ever withdrawn".
- **W5** After the render, the maker reads `looked_at`, `written` and `delivered` DONE on the
  replay; `audited` and `measure` still OWE, for the reasons they state.
- **W6** The written layer sent back and sealed: `writing_seal.pbs` W1-W3 hold on the cluster -
  the same three stages done under the same status, on a run of its own.
- **W7** Maker or host defects the agents find: at most 3, at least one in the writing flow
  (a refusal whose message did not say what to do; a path a command printed that does not
  exist on the replay; a stage whose text and tool disagree). Every one is fixed in the maker
  or the host, never worked around by the dispatcher.
- **W8** Zero edits outside the clean rooms; both real checkouts clean after; nothing on the
  sealed run changed.
- **W9** Cost: the whole test phase completes in under two hours of agent time, and the
  dispatcher's own commands number under twenty.

## Cost, filled in after

| | |
|---|---|
| lookers, figures per looker, refusals | 6 lookers, 23-24 figures each, 139 of 139 recorded, **0 refusals** |
| writer: words, claims of its own | 2,893 words carried in; 9 claims |
| reviewer: rounds, standing / narrowed / withdrawn | 33 of 33 rounded by a named second agent: 1 standing, 25 narrowed, 7 withdrawn |
| maker or host defects found | **5**, all fixed test-first the same day: the review status listing every unreviewed figure of the run (ab7f15d); the brief printed as a stale snapshot (22e13ed); the `NEXT:` command without `--plugin`, the run-level summary denying per-plugin claims, and composed claims citing plates that do not show what they say (243b300). One venue defect: the session's file-writing tool refused the agents' report files, so every report came back as the agent's final message and was saved by the dispatcher |
| dispatcher commands | 14 - status, agenda, the review split, the six shard lists, the writing run's prepare, the eye check, status again, the rsync back, the seal |
| job submissions | 1 (PBS 711001, the writing run's seal: 3 of 3 held) |
| edits outside the clean rooms | 0; both checkouts clean; 0 files newer than the seal on the sealed run |
| agents, tokens | 8 cold Sonnet agents, about 1.69 M tokens: lookers 1.05 M, writer 0.28 M, reviewer 0.36 M; about 65 minutes wall, 105 minutes of agent time |

## Results

Written 2026-09-13 after the run. The writing run is
`20260912T214825Z__scprofile-8e64eba__04_profile__written` (PBS 711001, sealed 3 of 3); the
agents' reports are beside this record in the session's `blind4/work/`.

- **W1 HELD.** No agent asked anything; every tool command an agent ran was one the status,
  the agenda, the brief or a refusal printed. Three lookers and the writer wrote small scripts
  around printed commands - to batch 23 review calls, and to verify the brief's look marks
  against the ledger when the brief said 62 figures were unopened - the second forced by a
  defect (below), not by a gap in the instructions.
- **W2 HELD.** The scan set was 139; the agenda said six agents, the review command split
  exactly those 139 six ways, and the union of the six ledgers covered the set: `looked_at`
  read 80 of 80 kinds and 139 of 139 within eleven minutes of wall time. Zero refusals, against
  "at most a handful".
- **W3 HALF HELD.** 2,893 words carried in; the reference arm stated in every contrast's
  opening sentence; every cited figure confirmed against the ledger; nine claims of its own; the
  composed claims kept. The headings were not the brief's: the printed brief was the one the
  reporter had written at report time, before this round gave the brief the panel's headings,
  and `paper --brief` printed the file as it lay - the same defect that marked 62 of 90 figures
  unopened. The writer took the composed section's own headings, which are the template's. A
  fresh brief carries the panel's labels; the writer never saw one.
- **W4 HELD, harder than predicted.** All 33 claims rounded by a named second agent; 1
  standing, 25 narrowed, 7 withdrawn. The reasons were the tool's, not the writer's: thirteen
  composed totals cited plates on which no total appears, seven claims about elements detected
  in one arm cited the population-presence grid, and every "measured against the reference"
  claim cited two-panel heatmaps that never say which panel is which arm - the lookers' finding
  from the other side. The composer's citations are fixed; the unlabelled heatmaps are the
  plugin's debt, with the 43 text collisions.
- **W5 HELD.** After the render the maker reads `looked_at`, `written` and `delivered` done
  on the replay; `audited` and `measure` owe, for the reasons they state.
- **W6 HELD.** The written layer went back as a writing run and sealed with the same three
  stages done under the same status.
- **W7 FAILED on the count, in the right direction: five, not at most three**, every one in the
  writing flow and every one fixed the same day (the cost table names them). The looker's was
  the largest: asked for its plugin's status, an agent was handed 918 file names.
- **W8 HELD.** Nothing outside the clean rooms changed; the sealed run has no file newer than
  its seal.
- **W9 HELD.** About 65 minutes of wall time and 105 of agent time; 14 dispatcher commands.

Seven of nine held. What the round proves: on a real sealed run, cold agents driven by the
maker's status and the run's agenda cleared the eye, the writing and the delivery without a
question, and the test they ran killed or narrowed 32 of 33 claims for reasons the tool could
act on. What it does not prove: `audited` and `measure` were not cleared - the first is the
plugin's own figure code (the top rule keeps this round's author out of it) and needs a rerun,
the second a per-instance job - and the section's headings were never the panel's on this run.
