# ADR-0026: the maker under random edits - what makes a plugin slow to change, removed; every element of cellchat edited at random through the maker, and the maker measured

**Date** 2026-09-15. **Follows** ADR-0025 (the last turn on cellchat). **Status** proposed; the
table at the end records each step. **Displaces** the eight held-out plugins to ADR-0027: they
are measured against a maker that has been through this first.

## Context

The user's finding, after ADR-0024 and ADR-0025: adjusting cellchat through the maker and the
dev suite takes hours, so the maker and the suite are still messy and carry states nobody can
read. The standing rule (2026-09-14) is that anything in a plugin that cannot be edited easily
from the maker is a suite or maker defect. This round tests that rule directly. Cellchat is the
crash-test dummy and not the subject: nothing here is a decision about its design, and the
plugin returns to what it was.

Where the hours went, measured before this file was written (records: the commit logs of both
repositories since 2026-09-14, `report.json` and `phase.json` of the runs on the cluster, the
job files, the suites timed on the workstation):

1. **Every rerun of the arc re-inferred CellChat on all eighteen units.** `sch dev job` copies
   the reference run's argv verbatim, as it should; the reference is the audit reproduction of
   2026-09-13, which ruled the cache out with `--no-cache` on purpose, and every rerun job since
   `jobs/rerun_0006.pbs` carries that flag at column ~900 of one line. The cache beside the runs
   (14 GB, written 2026-08-30, its stamp still matching the current inference span and the
   current config key `011991c86a`) has not been offered since 2026-09-02. Unit times: 250-700 s
   without it, 85-210 s with it. Every unit log of every run says `NO cache offered; every run
   will re-infer`, eighteen times per run, read by nobody. Cost: about eight minutes of every
   thirty-minute rerun, fourteen reruns since 2026-09-14.
2. **The compare phase runs its seven R launches one after another** (`_launch_or_record` in a
   loop in `report.py`), each given all 64 cores and using one: 7 x ~72 s = 505 s of R, 13.5
   minutes of phase by file times. Pooled like the units, about two minutes.
3. **The report is built twice** - by `run` and again by the emitted job's after-step; about two
   minutes.
4. **The commit gate runs 98 suites serially**: 138 s on the workstation, about fifty scProfile
   commits in 37 hours, about two hours in the gate; the author's own gate runs on top.
5. **A cold author edits a 5,454-line file by hand** (2,004 comment lines; the declaration is a
   pure literal of 24 entries x 22 keys): an id rename touched four sites, the interaction fix
   was 250 lines from its entry; 71 minutes, 194 tool uses, three exchanges, a 1,267-word
   prompt. There is no verb that sets, renames, adds, removes or re-legends an entry.
6. **States knowable locally and learned downstream**: an R argument the tool refuses (`RdBu`,
   found by a 30-minute run); a legend rewrite unbinding 33 stated disclosures (a rerun, a look
   pass and an exchange to learn what a diff already said); the carry not travelling (a seal).
   Two of three reruns and two of three seals of ADR-0025 were these.
7. **A false green, live now**: the `contract` stage reads `done` while every unit of every run
   prints seven `[declaration]` lines about `produces` - 260 lines per run - and nobody can say
   from the maker whether the declaration or the host's check is wrong.
8. **Choreography by hand**: rooms by `git archive` with a pristine twin, the cellchat-only
   export by an ssh sequence, the rsync copy, lookers writing 100-line scripts to record twenty
   looks because a run's paths carry `|` and spaces, about 25 record commits in 37 hours.

## Goal

**Any single element of cellchat can be changed from the maker in one verb, the local state
after the change is true, and a rerun that checks it costs about ten minutes, not thirty.**
Measured, not asserted: 36 seeded random edits over the plugin's enumerated surface and six
targeted ones, each applied through the maker (a verb built test-first where none exists),
each timed, each checked against the stage or gate that must turn red, and six cluster runs
(one control, one per runnable class) that say whether the run agrees with what the maker said
locally. A cold agent replays six fresh edits at the end, as the measure of "easy".

## Decisions (the user's, 2026-09-15)

- **Fix first, then attack**: the three run-side causes (1-3) and the serial gate (4) are
  removed before the campaign, test-first; one control rerun measures the difference.
- **Build the verb, then apply**: a drawn edit with no verb gets one, proven on the neutral
  fixture, never on the eight held-out plugins; the verb set is the round's deliverable. I
  never hand-edit `kernels/cellchat.py`; a mutation with no verb is a finding, not a thing I type.
- **One control run plus one per runnable class** (A, B, C, F, G; D and E must be refused
  before a job can be emitted - that refusal is their run).
- **Removed outright, not only recorded**: the second report build; the serial commit gate
  (same 98 suites, `--jobs` after the result is measured identical); the pristine-twin rooms;
  the per-row record commits (one commit per step, predictions still before any change).
- **Defaults not asked**: N = 36 drawn with seed 20260915, stratified so every sub-kind of a
  class is drawn once before any twice, no element twice; six targeted edits for the stages the
  draw left untouched; the mutants live on a scProfile branch `attack-0026` (pushed, exported
  cellchat-only on the cluster by commit as before), main receives only mechanism and the
  restored plugin; the restored plugin is equal to 0.39.0 as a literal (AST) and its companion
  byte-identical - a verb that normalises formatting is allowed, the diff is shown; the one
  edit that stays is whatever the `produces` false green turns out to owe, because a stale
  declaration corrected by the maker's own write is the maker doing its job (0.40.0).
- **The rules hold**: no hand edit of the plugin; the eight held-out plugins untouched; the
  verbs live in `sch dev convert` and scProfile's maintainer commands, the campaign is this
  file and a seeded draw, no framework beside the mechanism; every run through a validated job
  by the submitter, pinned to compute1016; cellchat-only end to end.

## The steps

0. **Record.** This file, with the draw and the predictions, before any change.
1. **The run made cheap** (test-first, each its own commit): the emitter prints every flag it
   carries from the reference and strips `--no-cache` from a redraw unless asked for by name;
   the compare launches pooled under the same permits as the units, each at the plugin's
   declared share; the after-step's second `report` dropped; `run_all.py --jobs` measured equal
   to serial on three runs, then the gate uses it. Then the **control rerun** of the unchanged
   0.39.0 through `sch dev job --redraw`, with the prediction in the job.
2. **The surface and the verbs** (test-first on the fixture): whatever the 42 edits need -
   `sch dev convert edit` with set / rename / add / remove / duplicate / swap / legend / host /
   produces / config actions that rewrite the literal by its source spans and keep the prose,
   run the followers (companion, baseline, version), and print the state after; and the local
   readings the edits need before a job - the cache stamp (hit or miss), the disclosures
   unbound by a legend change, the R arguments against formals recorded once from the cluster
   by a validated job, the plates and products expected.
3. **The editability pass**: the 42 edits in order, each applied by a verb, timed (commands,
   seconds), the local state read, reverted by the verb or by `git checkout` of the file; the
   table filled as it goes. A verb missing is built here, not worked around.
4. **The kill pass**: for each of the 9 build stages, 8 test stages and 8 gates (validate,
   rules, overfit, portability, layout, baseline, generated, the commit gate), the edit that
   must turn it red, and whether it did, and how long it took to say so. A stage that stays
   green is dead and is fixed here; the `contract` stage is the first.
5. **The runs that check the maker**: A, B, C, F and G as five mutant runs on `attack-0026`,
   each job carrying the local predictions for every edit it stacks; the run's own replay
   (`status --run`, `capacity --promised`, the plate list) read against them.
6. **The cold replay**: one cold agent, the maker's own documents, six fresh edits (seed
   20260916, same generator), timed; `docs/blind/0011-the-cold-replay.md`.
7. **Restore and record**: cellchat back to its literal at 0.39.0 (plus the `produces` owing),
   `attack-0026` kept as the record, this file's table filled, memory updated. Stop before
   ADR-0027.

## The draw (seed 20260915; the generator is in the session's scratchpad and reprinted in the blind record)

| n | class | element | edit | what the maker must say locally, and what the run must do | reverse |
|---|---|---|---|---|---|
|  1 | A | `nativecmp_signalingRole_scatter_pair.axis` | contrast -> group | the family moves axis in plan and layout; the R guard and the profile list follow; the run files it under the new axis | set back |
|  2 | A | `config.dotplot_n.default` | another value in its domain | defaults stage re-reads; the reuse key changes; the cache key (if inference-side) changes and the run re-infers | set back |
|  3 | A | `nativecmp_chord_cell.legend` | one sentence rewritten (same facts) | stated disclosures bound to the old words are reported as unbound BEFORE any run; the paper page prints the new legend | set back, or re-state |
|  4 | A | `nativecmp_diff_heatmap_weight.at_most` | 1 -> 2 | plan/layout count changes by the difference x occurrences; baseline refuses until re-recorded; the run draws exactly that many | set back |
|  5 | A | `nativecmp_interaction_flow.position` | conclusion -> overview | the figure set moves the plate between main and supplementary; the section and legends renumber; nothing else changes | set back |
|  6 | A | `nativecmp_diff_heatmap_count.w,h` | 2400x1800 -> 3600x2700 | the companion regenerates with the new device size; the run draws that size; no count changes | set back |
|  7 | B | `produces[...]` | [optional] tables/cellchat_rank_net.csv -> a path the plugin does not write | the contract stage reads red against the last run; the run prints it as declared-not-emitted | set back |
|  8 | B | `report.subject` | cell-cell communication -> intercellular signalling | every composed title and the page title follow; nothing else | set back |
|  9 | B | `estimationNumCluster.id` | estimationNumCluster -> estimationNumCluster_renamed | every site follows (R draw sites, profile list, evidence routes, skips, baseline); files carry the new name; one verb | rename back |
| 10 | B | `config.dotplot_n` | dotplot_n -> dotplot_n_x | the code that reads C["{k}"] must follow or validate refuses; defaults stage re-reads | rename back |
| 11 | B | `native_signalingRole_scatter.id` | native_signalingRole_scatter -> native_signalingRole_scatter_renamed | every site follows (R draw sites, profile list, evidence routes, skips, baseline); files carry the new name; one verb | rename back |
| 12 | B | `produces[...]` | tables/ccc_edges.csv -> a path the plugin does not write | the contract stage reads red against the last run; the run prints it as declared-not-emitted | set back |
| 13 | C | `figures order` | swap nativecmp_signalingRole_scatter_pair and native_circle_weight | nothing changes but the figure-set order within a subject; the baseline holds | swap back |
| 14 | C | `figures[nativecmp_signalingRole_scatter_pair] x2` | duplicate the entry under a new id | a twin family; layout counts twice; overfit/rules see duplicated mechanism | remove the twin |
| 15 | C | `figures[+]` | add an entry drawing netAnalysis_signalingChanges_scatter (from skips) | the skip is lifted; the plan counts it; layout may refuse over budget; the companion gains a draw site; the run draws it or the promise is refused | remove |
| 16 | C | `produces` | remove [optional] objects/cellchat.rds | the contract stage says an emitted file is undeclared | add back |
| 17 | C | `report.host_panels` | add a kind the host implements but the plugin did not keep (e.g. role_shift) | layout host count rises; the run draws it per contrast | remove |
| 18 | C | `figures[nativecmp_signalingRole_scatter_pair]` | remove the entry | plan and layout counts drop; the R draw site and profile mark go; baseline refuses until re-recorded; the run draws exactly the rest | add back from the record |
| 19 | D | `estimationNumCluster.args` | an argument the R function does not take | a LOCAL check refuses it against the recorded formals of the wrapped tool; today only the run finds it | set back |
| 20 | D | `nativecmp_compareInteractions.axis` | an axis the host lacks | validate refuses; layout refuses | set back |
| 21 | D | `nativecmp_compareInteractions_per1k.kind` | an id the host has no kind for | validate refuses by name before anything runs | set back |
| 22 | D | `nativecmp_interaction_flow_log.position` | a position the set has no place for | validate refuses | set back |
| 23 | D | `figures` | a second entry with id nativecmp_aggregate_circle | validate refuses the duplicate id | remove |
| 24 | D | `nativecmp_compareInteractions.legend` | a cohort word in the legend | the portability suite refuses by name | set back |
| 25 | E | `state_version` | delete the key | validate refuses (already an ERROR) | restore |
| 26 | E | `native_signalingRole_scatter.axis` | delete the key | validate refuses; plan cannot count it | restore |
| 27 | E | `requires.packages` | delete the key | environment stage refuses | restore |
| 28 | E | `report.host_panels` | delete the key | the host draws every kind again (undeclared = all); layout host count reads the default | restore |
| 29 | E | `config.min_cells.default` | delete the key | defaults stage refuses | restore |
| 30 | E | `version` | delete the key | freshness refuses | restore |
| 31 | F | `code` | a `_fig_*` panel writes one extra file | promised/output-nobody-asked-for refuses the extra; the plan does not count it | git checkout of the file (not a hand edit) |
| 32 | F | `code` | the generated companion edited by hand (one argument at a draw site) | `generated` reads the companion stale before any run; scaffold --force rewrites it | git checkout of the file (not a hand edit) |
| 33 | F | `code` | a comment inside the RECIPE span of the R inference | the cache stamp changes: the control run re-infers (18 x ~5 min) - the local state must SAY the cache will miss | git checkout of the file (not a hand edit) |
| 34 | F | `code` | a plan change with the baseline not re-recorded | the baseline test refuses; the commit gate blocks | git checkout of the file (not a hand edit) |
| 35 | F | `code` | a plan change with the version not bumped | freshness reads stale against the last run; the reuse key would collide | git checkout of the file (not a hand edit) |
| 36 | F | `code` | an `expr` changed to another measure of the same function | no count changes; the promise holds; only the eye sees the difference - the stated disclosures of that kind are reported as at risk | git checkout of the file (not a hand edit) |
| 37 | G | `references[...].sha256` | one digest altered | the references stage refuses against the fetched file | set back |
| 38 | G | `cores` | 2 -> 4 | the cores stage owes a measurement; the wave plans 4 per instance; the control run's peak decides | set back |
| 39 | G | `cost` | high -> low | the cost stage reads the declaration against the last run's seconds and refuses | set back |
| 40 | G | `memory_gb_base` | halved | the measure stage refuses against the run's measured base | set back |
| 41 | G | `report.writing_template` | a template that does not exist | the written/delivered stages refuse before the writer starts; the brief says so | set back |
| 42 | G | `code` | a numeric literal equal to a count of this cohort, in a `when` clause | `sch dev convert overfit` refuses the fitted literal | git checkout |

Classes: A a value inside its domain; B a rename; C add, remove, duplicate, reorder; D a value
outside the domain; E a missing key; F a code-side change; G targeted at a stage the draw left.

## Predictions, before any change

- **S1** the control rerun at the unchanged 0.39.0 reuses all eighteen saved objects (`reusing
  the saved CellChat object` in every unit log), the compare phase takes under three minutes,
  the job seals SEALED with the same 122 plates by name and size, in at most twelve minutes of
  node time against thirty-one.
- **V1** today at most 6 of the 36 drawn edits have a maker verb (`layout --apply`, `--stated`,
  `scaffold --force`, the baseline's `--record`, `capacity --declare`); after step 2, every one
  of the 42 is applied and reverted through a verb or `git checkout`, with no hand edit of the
  plugin by me; the median edit takes at most 2 commands and 30 seconds to a true local state,
  the slowest at most 5 commands.
- **K1** today at least 4 of the 25 stages and gates stay green on the edit that targets them
  (the contract stage is one; the R argument, the unbound disclosures, the cache stamp and the
  unbumped version are the candidates); after step 4, none - every one turns red locally,
  before a job can be emitted, and says which edit.
- **R1** six runs, each at most twelve minutes of node time; every local prediction written
  into a job holds on at least five of the six; a failed prediction names the state the maker
  misread, and that is a defect fixed in the round.
- **C1** the cold agent applies its six edits in at most 5 commands each and 45 minutes in all,
  with 0 hand edits of the plugin and 0 refusals from the repository's own gates it did not
  clear on the next command.
- **B1** at most 15 defects of the mechanism, each fixed test-first the same day, none recorded
  open. (The last two rounds found 14 and 5.)

## Cost, estimated before

Six cluster runs of about ten minutes each after step 1 (the control may re-infer if S1 is
wrong: thirty); one cold agent, about 45 minutes and 300k tokens; the verbs are the bulk: about
ten of them, test-first, and the four fixes of step 1; about twelve hours of wall clock in all,
across more than one session - the table below is what a later session resumes from.

## Status

| step | state | where | what |
|---|---|---|---|
| 0 record | done | this commit | the diagnosis measured, the decisions taken, the draw fixed |
| 1 the run made cheap | done | scProfile dc9bb46, harness 1402fab, 403ce2f; the control rerun `20260915T084449Z__scprofile-dc9bb46__04_profile__rerun` (PBS 711884, compute1016) | Four fixes, each test-first and seen red: the tool declares `run.redraw_drops: [--no-cache]` and the emitter drops it on a redraw, listing every flag it carries in the job's header (`--keep=FLAG` keeps one); the compare launches pooled at the plugin's declared share (2) under the run's budget, 32 at once, the phase record carrying `share` and `at_once`; `run.after` no longer names `report`; `run_all.py --jobs` defaults to 4, measured green serially (138 s) and three times in parallel (49 s) with the same verdict - a correction to the diagnosis: the commit gate had passed `--jobs 4` since ADR-0023, so the serial cost was the author's and the cluster's, not the gate's. **S1 held**: SEALED in 12 min 9 s of node time against 31; 18 of 18 units `reusing the saved CellChat object`, slowest unit 176 s against 699; seven compare launches of 66-80 s at once, the phase 2 min 45 s against 13.5; the figure set built once; the same 122 plates by name and pixel size as PBS 711759, 102 of them byte-identical - the 20 that differ are the permutation test's own randomness between a cached and a re-inferred object, recorded as an observation about reproducibility and not acted on |
| 2 the surface and the verbs | | | |
| 3 the editability pass | | | |
| 4 the kill pass | | | |
| 5 the runs | | | |
| 6 the cold replay | | | |
| 7 restore and record | | | |
