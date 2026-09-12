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
| lookers, figures per looker, refusals | |
| writer: words, claims of its own | |
| reviewer: rounds, standing / narrowed / withdrawn | |
| maker or host defects found | |
| dispatcher commands | |
| job submissions | |
| edits outside the clean rooms | |
| agents, tokens | |

## Results

(written after the run)
