# ADR-0026: the maker under random edits - what makes a plugin slow to change, removed; every element of cellchat edited at random through the maker, and the maker measured

**Date** 2026-09-15. **Follows** ADR-0025 (the last turn on cellchat). **Status** complete; the
table at the end records each step and the results table grades the predictions. **Displaces** the eight held-out plugins to ADR-0027: they
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

## Step 3, measured: the 42 edits through the maker

Every declaration edit (1-30, 37-41) went through `sch dev edit` in ONE command: the verb 0.44-0.52 s
including its three followers (validate, scaffold, the baseline record), the build status 1.8 s
after. Verb defects found and fixed as they came: `--list-add` on a list whose bracket closes on
the last element's line left the file unparseable (7; test added); a string replacing a
double-quoted span took single quotes (10; the quote style now follows the span); the followers
ran validate last, so a refused plan was regenerated and recorded before it was refused (20-22;
validate first, stop at the first refusal, print what it refused).

| n | what the maker said, locally, in the seconds above | as the draw expected? |
|---|---|---|
| 1 axis contrast->group | OVER group 6 of 5; build 8 of 9 (layout) | yes |
| 2 config default | build 9 of 9; nothing about the cache | no reading of the cache (K-e) |
| 3 legend rewrite | build 9 of 9; nothing about stated disclosures | no reading of the disclosures (K-c) |
| 4 at_most 1->2 | OVER contrast 11 of 10 | yes |
| 5 position | changed, 9 of 9 | yes |
| 6 w,h | changed, the companion follows, 9 of 9 | yes |
| 7 produces path never written | contract `done` | DEAD (K-a) |
| 8 subject | changed, 9 of 9 | yes |
| 9 rename side-effect id | the literal follows; no site to follow | yes |
| 10 config key rename | the literal and `C["dotplot_n"]` in code follow | yes |
| 11 rename a drawn id | the literal and the draw site follow, no site left | yes |
| 12 produces: the primary table removed, a path never written added | contract `done` | DEAD (K-a) |
| 13 swap | changed, counts unchanged | yes |
| 14 duplicate | OVER contrast 11 of 10, 25 entries, companion follows | yes |
| 15 add from the skips | the skip lifted (14 used, 21 skipped), OVER contrast, companion gains the site | yes |
| 16 produces: the object removed | contract `done` | DEAD (K-a) |
| 17 host kind added | OWES `report.host_panels`: the layout keeps four and the plugin declares five | the layout decides, not the plugin - right by ADR-0024 |
| 18 remove an entry | 23 entries, the fn still drawn elsewhere so no skip owed, 9 of 9 | yes |
| 19 an R argument the function lacks (side-effect entry) | 9 of 9; nothing | no formals (K-d); and `args` on a `generated: False` entry has no site and nobody says so (K-h) |
| 20 unknown axis | validate refuses by name; build 7 of 9 | yes |
| 21 unknown kind | validate refuses, names the registered kinds | yes |
| 22 unknown position | validate refuses, names the four | yes |
| 23 duplicate id | the verb refuses before writing, 0.09 s | yes |
| 24 a cohort word in a legend | verb, validate, build 9 of 9 all pass; the portability suite refuses (9 s), when somebody runs it | SILENT at the maker (K-f) |
| 25 no state_version | validate refuses | yes |
| 26 no axis | plan stage PART, 1 of 24 not ruled on; the layout counts it under sample (OVER 3 of 2) | readable; the layout's count is wrong (K-j) |
| 27 no requires.packages | environment todo | yes |
| 28 no host_panels | OWES `report.host_panels` | yes |
| 29 a parameter with no default | defaults `done`, validate passes, 9 of 9 | DEAD (K-b) |
| 30 no version | freshness todo | yes |
| 31 a panel writes an extra file (patch) | nothing local reads code | the run's (step 5) |
| 32 the companion edited by hand (patch) | the companion test FAILs; plan stage todo | yes |
| 33 a comment in the recipe span (patch) | nothing about the cache | no reading (K-e); the run's (step 5) |
| 34 a plan change by hand, baseline not re-recorded (patch) | the baseline test refuses (164 -> 170); freshness, plan and layout todo | yes, three ways |
| 35 a plan change by hand, version not bumped (patch) | freshness STALE, the commit to raise it in named | yes |
| 36 an expr changed to another measure (patch) | nothing | no reading of the disclosures at risk (K-c) |
| 37 a bundled reference's package name | references `done` | cannot be proven without R; by the point's own declaration |
| 38 cores 2->4 | RUN?; against the last run's copy: done (the declaration may exceed the peak) | by design |
| 39 cost high->low | RUN?; against the run: cost todo | yes |
| 40 memory base halved | RUN?; against the run: measure todo | yes |
| 41 a writing template that does not exist | 9 of 9; against the run: written and delivered done | DEAD (K-g) |
| 42 a fitted literal in a `when` clause (patch) | rules held, overfit 0 (it reads the maker's own elements, not the plugin's) | no static gate; the two-shape fixture run is the gate (K-i, recorded) |

And one the edits showed about the emitter: `sch dev job` reads the reference run and the tool
commit and never the plugin's build status, so a plan over budget, a refused axis or an unruled
entry can be emitted and submitted (K-l). The kill pass (step 4) fixes K-a to K-h and K-j, K-l;
K-i is recorded.

## Step 5, measured: the runs that check the maker

Each mutant is one verb call (or three recorded patches) on a branch of its own, each run against
its own cellchat-only tree, the predictions in the job's header. The first submission of all
five failed in a second: the emitter turned the reference's script into `-m` only for a tree of
the reference's name, so each mutant job ran the reference's tree, unguarded (harness f736f2a).
Then PBS system-held the four queued behind the first after 21 failed starts on the pinned node
(as ADR-0022 saw); they ran one at a time after it.

| run | node time | reused | what the maker said | what the run did | held? |
|---|---|---|---|---|---|
| control (PBS 711884, 0.39.0 unchanged) | 12 min 9 s | 18 of 18 | cache HIT; 122 plates | 122 plates by name and size, 102 byte-identical; `measure` owes: the base fitted 2.9 GB under reuse against 2.4 declared - a control finding step 1 did not read | S1 held on what it named; the memory base under the cached path is new |
| B (PBS 712289, class B) | 11 min 21 s | 18 of 18 | plan unchanged, HIT, the code's `C["dotplot_n"]` followed, no site unfollowed | 122 plates, the drawn family under its new name and none under the old; the title "Intercellular signalling"; `declared` owes exactly the two edits (never_written.csv declared, ccc_edges.csv undeclared, 18 units each) and nothing else - the four optional tables no longer drift; `promised` OWES: the renamed side-effect entry promised `estimationNumCluster_renamed.png` and the tool wrote twenty `estimationNumCluster` files accounted for by nothing | (1)-(4) held; (5) moot - the dotplot is off the plan; the side-effect rename is a new one, K-p: the maker read 9 of 9 over an id the tool never uses (fixed: the verb refuses to rename a `generated: False` entry) |
| C (PBS 712292, class C, `--anyway`) | 12 min 28 s | 18 of 18 | contrast OVER 11 of 10, host list OWES (role_shift beyond the layout's keep), plan 170 files, HIT | 128 plates: the twin's 6, the host's 6 role-shift plates (the plugin's list is what the host reads at its draw sites; the layout's OWES is the maker's reading), the removed pair scatter's 6 gone; `promised` OWES on exactly the added entry - declared and never drawn, no error in the compare log: its site had been appended inside another entry's else-branch (K-r, the cold maintainer's finding) and its call named `pop`, a variable no script binds (K-n) | (1)-(6) held - the count 128 to the plate; (3) by outcome, the mechanism two defects deep, both fixed |
| F, first cut (PBS 712295, class F) | 11 min 35 s to failure | 0 of 18 (every unit re-inferred, as forecast) | CACHE MISS - the inference span changed; plan unchanged | every unit FAILED after its inference on `NameError: Path` - the campaign's own patch named a module the plugin never imports, and nothing local had read the plugin's Python for free names | (1) held; the rest unmeasured; a new one, K-s: a free name in the plugin's own Python is found by the run - fixed test-first (a scope walk over every function, the last follower of an edit; green on all nine plugins, `Path` on this branch) |
| G, first cut (PBS 712296, class G, `--anyway`) | 14 s | - | validate ERROR on the writing template; the emitter refused; forced | `scprofile run` REFUSED at its door: the same validator runs first and a template that does not exist stops the run before any unit | (6) FAILED in the good direction - the run does say so; the rest unmeasured, re-emitted without the template |
| F, second cut (PBS 712297, class F) | 11 min 52 s | 18 of 18 - the forecast said MISS | CACHE MISS (the span changed since the run named); plan unchanged; the followers green, the extra file now under a bound name | the eighteen `F1_extra_nobody_asked.png` files read as ACCOUNTED FOR BY NOTHING by `promised` (OWES); the six differential strength heatmaps differ in bytes from the control's while the count heatmaps are identical - the expr change is the eye's alone, and the legend still says strength; 122 plates; `declared` done, `measure` owes as before | (2), (3), (4) held; (1) FAILED on the letter and taught something: the first cut had re-inferred under the mutant span and OVERWRITTEN the store's objects, so the second cut hit what the first wrote - the forecast is relative to the run it is compared with and cannot read the store, which holds one object per parameter key stamped by its last writer; its words say so now, and the next run at main's span will miss where it says HIT (one 30-minute re-inference the campaign cost the cache) |
| G, second cut (PBS 712298, class G) | 19 min 46 s | 0 of 18 - the forecast said HIT | build 9 of 9; cores, cost, measure RUN?; HIT | every unit re-inferred: F's first cut had overwritten the store's objects under its span, and this run wrote them back under main's - the consequence the F row names, seen within the hour; the plan line still reads one wave at 4 cores an instance (the pool's permits, 16 at once, are not waves); after the run `cost` owes (declared low, measured high), `measure` owes (base 1.2 against 2.2 fitted on the inference path; 2.9 on the reuse path - the model differs by path and the declaration should be the envelope), `cores` passes (4 above the peak), `declared` owes on two units' memory as well; the `when` literal of 14 skipped nothing - `nrow(pos)` is the paired table's rows, not the population count, so the number was not fitted to anything and the fixture run stays K-i's gate; 122 plates | (1) FAILED for the store's reason, (3) held twice over, (5) held, (2) and (4) unmeasured on the letter - the wording of waves, a literal that did not bite |
| A (PBS 712280, class A) | 12 min 1 s | 18 of 18 | group OVER 6 of 5, plan 168 files, HIT, 4 disclosures unbound | 122 plates, the same set as the control by name; the six count heatmaps 3600x2700; `declared` and `promised` done, `measure` owes as on the control | (1) held; (4) held; (2) FAILED - the pair scatter's `axis` moved nothing, its draw site being in the compare script (K-o, fixed: the companion refuses a site whose script does not draw by the entry's axis; the static half recorded); (3) held in direction - the plan's 168 counted files no run holds (K-m, fixed: a ceiling above one needs items or a file rule) |

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

## Results

| prediction | held? | what happened |
|---|---|---|
| S1 | held | the control reused 18 of 18 objects, the compare phase took 2 min 45 s, SEALED with the same 122 plates by name and size in 12 min 9 s against 31; one thing it did not name - `measure` owes on the reuse path (base 2.9 GB fitted against 2.4 declared) |
| V1 | held | 4 of 36 drawn edits had a verb before (a host list, the companion, the baseline, a disclosure); after step 2 every one of the 42 went through `sch dev edit` or `git checkout`, one command each, 0.45 s plus the followers, no hand edit of the plugin by the dispatcher; the cold maintainer's six the same |
| K1 | held on the count, failed on the letter | 11 dead or silent readings at step 3 against at least 4 predicted; every one turned red locally by the end of step 4 - and the runs and the replay then found seven more (K-m to K-s), each fixed the same day; K-i stays with the fixture run and the static half of K-o is recorded |
| R1 | **failed** on the letter | three of six runs held every prediction (control, B, C); A misread an axis (K-o), F's second cut and G met the store's semantics the forecast cannot read, G's literal did not bite; every miss named a state the maker had misread, and eight runs were needed for six |
| C1 | held on the measure, failed on the letter | six edits in one command each, 8-9 s each, 18 min 10 s, 0 hand edits of the declaration; four refusals it could not clear were the suite's own (the family checks on a one-kernel tree, K-q), not the edits' |
| B1 | **failed** | 28 defects of the mechanism fixed test-first the same day against at most 15 predicted (4 in step 1, 3 of the verb in step 3, 13 in the kill pass, 6 from the runs, 2 from the replay), and 2 recorded open: the fixture run as the only gate on a fitted literal, and the static reading of which script holds a draw site |

What the round leaves for the plugin, recorded and not done, because the plugin is not the
subject: the stated disclosure the 0.39.0 register rewrite dropped (three kinds when step 4
first read it; one kind on the binding as it stands - the outgoing signalling-role heatmaps, three
plates, the colour key's floor - read by the worksheet against the run copy on 2026-09-15); four tables the R writes and never registers; a memory declaration
that should be the envelope of the reuse path and the inference path; and the cache store that
keeps one object per parameter key, overwritten by whichever run wrote it last.

## The open items, closed (2026-09-15, after the round)

The user read the six open items above and their impact and said close them all, housekeeping
included, then run cellchat once more for review. Each close was test-first and seen red; the
plugin was written only by the tool's verbs (`capacity --memory --declare`, `sch dev edit
--legend`) and never by hand.

| item | what closed it | where |
|---|---|---|
| a fitted literal has no static gate (K-i) | the fixture tiers RUN the plugin, and the emitted job runs both shapes before the cohort (`run.fixture_first`), refusing the cohort if either fails - and the finding under it: the gate had never existed. scProfile's fixture tiers planned and refused "not ready in this installation" on every ladder, the cluster's included (`{out}/prefix` was a fresh directory); no plugin of the repository had ever been executed on the two-shape cohort; and had cellchat run, the fixture's neutral gene names would have given a ligand-receptor database nothing to match. So: the fixture's marker blocks carry real ligand-receptor symbols in place of GENExxxx from the second type on - a rename, the counts byte-identical, the digest moved to ae50a42592c02c25 deliberately with no baseline recorded on the old names; `{prefix}` fills from the site's SCH_DEV_PREFIX; the fixture command runs `scprofile run` on each shape with the fixture's own role names, `--factor` naming its one factor, organism human, then `capacity --promised` on that run; a declared refusal ends the command list; exit 3 (could not run) is told from exit 2 (failed) and the seal says `incomplete_checks=`. Running the tiers on the workstation before any job found two tool debts: `run` launched twenty instances that each failed "no environment" where `plan` refuses once at its door - it refuses at its door now, in the plan's words; and every column of a design table was a factor - `--factor COLUMN` names the factors a run is about | harness f7e7c5e, f383255, a473e0e; scProfile f5d3955, 581dbba |
| the maker cannot say which script holds a draw site (the static half of K-o) | `declare.draw_site_phase`: the plugin's own Python says which R string `run(ctx)` and `compare(ctx)` launch (`ctx.rscript(_R_RUN, ...)`; a literal beneath the `.replace` splice is read to its text), the strings say where each `.draw` site is, and `PHASE_AXES` - the two sets the companion holds a site to at run time - says what each phase draws by; the validator refuses the mismatch by id, script, phase and way out, so the maker's first follower prints it. Run A's edit, replayed on a scratch copy, is refused in a second; cellchat as it stands passes | scProfile b17949e |
| one kind's disclosure the register rewrite dropped | `sch dev edit --legend nativecmp_signalingRole_heatmap ...` put the author's recorded sentence back in place of the rephrased one (the author's own words, pasted); the worksheet against the 0.39.0 run reads 0 open findings on 0 kinds; cellchat 0.42.0 | scProfile 58b7338 |
| four tables the R writes and never registers | the host registers, when `run(ctx)` returns, every file under `tables/` that a `produces` table declaration names and nothing else (`manifest.declared_tables`, stdlib-only: it runs in the plugin's environment); the plugin's R untouched | scProfile 11b0240 |
| the memory declaration should be the envelope of both paths | `capacity --memory --declare` raises a term the fit exceeds and keeps one it does not, saying so - a run on another path is not evidence the ceiling was wrong; lowering one on purpose is the maker's `--set`. Applied to the control run by the tool's own verb: base 2.4 -> 3.2, rate 14.3 kept (the existing test that asserted replacement now asserts the envelope) | scProfile 4461be5 |
| the cache store keeps one object per parameter key, last writer wins | the unit's cache directory is keyed by a digest of the declared inference span (`landscape.span_key`): a run of another span writes beside, never over, and the stamp inside the object still decides validity; the forecast's HIT no longer hedges about overwrites and names the one thing that still defeats it (clearing); and it says MISS, once, when the store's key itself changed since the run named - which this very change did, so the first run after it re-infers and the job says so | scProfile dcfe2ac, 6aed091 |
| housekeeping | the cluster's harness and cellchat-only trees at the pushed heads (the old tree retired under `~/_archive/`); the stray `Rplots.pdf` of 2026-09-13 out of the harness root | - |

The runs that check the closes, each with its prediction in the job:

| run | node time | fixture gate | reuse | plates | the stages | against the prediction |
|---|---|---|---|---|---|---|
| (filled below as the runs seal) | | | | | | |

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
| 2 the surface and the verbs | done | harness 935fea7 (the verb, 1065 lines: `sch/dev/edit.py`, the `sch dev edit` handler, 20 tests on the neutral fixture, each seen red first); the readings the edits need before a job were built where the kill pass found them owing (step 4: the cache forecast, the disclosures a legend edit unbinds, the recorded signatures) | `sch dev edit` with `--set`, `--delete`, `--list-add`, `--list-remove`, `--rename`, `--remove [--skip]`, `--add`, `--duplicate`, `--swap`, `--rename-key`, `--legend`, `--dry`, `--as-version`: the literal rewritten by its `ast` source spans (byte offsets), the prose untouched, the version bumped once a call, a value that breaks the literal refused with nothing written, the followers the tool declares (`plan.after_edit`) run in order and the state after printed; a rename follows the routes, the draw site and the profile list, and names a code site it cannot follow (`NOT FOLLOWED`). Two limits stated at the time: the R-argument check waits on the signatures the cluster records (step 4), and the site an `--add` writes is placed by the axis kind (its placement inside an unrelated block was the cold maintainer's finding, K-r) |
| 3 the editability pass | done | scProfile branch `attack-0026` (the edits applied and reverted, none kept); harness 935fea7 and the verb fixes in the next commit; the per-edit table above | 35 declaration edits in one verb each (0.44-0.52 s plus 1.8 s of status), 7 code-side patches; 3 verb defects fixed as they came; the maker read the state truly on 24 of 42, was silent or wrong on 11 (K-a to K-l), and 7 belong to a run |
| 4 the kill pass | done | harness 2ef4a0d, 30afaf7, 5cd3279, 344dbca, 14e8cb3; scProfile 30a80b2, 26a6cc9, 6eb7611, b31e4c0 (cellchat 0.40.0 -> 0.41.0 by the verb: `produces` in its readers' grammar plus the table it registered without declaring, and the `cache` declaration); PBS 712273 (the signatures probe, 18 s) | Every silent or dead reading from step 3 turns red locally now, each test-first: (K-a) the validator holds `produces` to the grammar its readers read, a new `declared` test stage reads the run's declaration drift back (`capacity --drift`), and a unit's own gate records what it declined so a marginal pool is not four broken promises; (K-b) a parameter without a default is an ERROR unless `required`; (K-c) a stated disclosure closes a finding only while the entry's legend in THIS tree carries its words, the worksheet prints STATED, AND THE LEGEND NO LONGER SAYS IT, and `sch dev edit --run` reads it after the edit - on the 0.39.0 run this reads three kinds whose disclosures the register rewrite had dropped, closed until now by the plates' bytes; (K-d) the maker records the wrapped tool's signatures once where it is installed and the validator refuses an argument a function has not got, by name, for the 33 of 43 functions without `...`; (K-e) a plugin declares what keys its saved object (`cache.span`, `cache.keyed_on`) and `scprofile cache --forecast` says HIT or MISS before a job - the verb prints it after an edit, the emitter writes it into the header; (K-f) the vocabulary guard is the last follower of an edit (9 s); (K-g) a writing template that does not exist is an ERROR; (K-h) `args` on an entry with no site is a WARN; (K-j) an entry with no axis counts nowhere and is named PART; (K-l) `sch dev job --plugin` refuses over a build that owes. K-i (a fitted literal) is recorded: the fixture run is its gate, a static rule would be a heuristic. Two limits stated: the palette VALUE of ADR-0025 is not an argument name and needs a draw (the selftest reaching every site, recorded); the four tables the R writes and never registers are the author's, read by the new stage on the next run. Along the way: `check()` shadowed the plugin's name with a package's; the recipe test searched its markers anywhere in the file |
| 5 the runs | done | the control and the mutants A, B, C, F, G (PBS 711884, 712280, 712289, 712292, 712297, 712298) and the first cuts of F and G (712295, 712296); jobs/rerun_0016 to 0021; the table above | Eight runs for six planned: the first submission of all five failed on the emitter (a tree of another name ran the reference's tree; fixed), the batch was system-held behind the first on the pinned node and chained one at a time, F's first cut fell on the campaign's own patch (K-s, fixed), G's first cut on the run's own door (the validator runs first - a control that existed and the prediction had not credited). Against the predictions the runs found K-m, K-n, K-o, K-p, K-s and the store's semantics, each fixed test-first the same day; the plate counts held to the plate on A, B, C, F; **R1 failed on the letter** - three of six runs held every prediction; each miss named a state the maker had misread |
| 6 the cold replay | done | scratchpad blind14 (the maker at 21233dc, cellchat 0.41.0 at ea700a4); docs/blind/0011; harness 4d98ee9, scProfile 2a77bea | A cold Sonnet maintainer, given the maker's own documents and six fresh edits (seed 20260916): one maker command per declaration edit, 8-9 s each, 18 min 10 s in all, 0 hand edits of the declaration, every count the verb printed exact to the file. **C1 held.** It reported three verb defects and one suite defect, each fixed test-first: the added site placed inside an unrelated block (K-r), the `--add` quoting (`@FILE`), the layout's "ok" above a refusal, and the vocabulary guard's five family checks failing on a one-kernel tree before any edit (K-q) |
| 7 restore and record | done | scProfile main at 51c81a8 (cellchat 0.41.0), harness at this commit; docs/blind/0011; memory | cellchat on main differs from 0.39.0 in exactly three declared things, all the verb's writes: `produces` in its readers' grammar plus the table it registered without declaring (0.40.0), the `cache` declaration the forecast reads (0.41.0), and the version; the companion regenerated with the axis guard. Build 9 of 9, every axis under budget, validate clean, the round's rules 4 held, 0 fitted literals. The five mutant branches stay pushed as the record; the cluster's per-class trees stay beside the main export. Cost: eight cluster runs (about 110 min of node time), one cold agent (217k tokens, 18 min), about ten hours of wall clock in one session against twelve estimated |
