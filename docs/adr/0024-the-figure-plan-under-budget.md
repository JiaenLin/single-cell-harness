# ADR-0024: the figure plan under budget - four axes, hard budgets, built-in first, and the maker holds it

**Date** 2026-09-14. **Follows** ADR-0023 (the cellchat arc concluded). **Status** in progress; the
table at the end is filled as each step lands.

## Context

The cellchat arc closed with 945 figures a run, 58 plan entries, 80 kinds, 105 numbered on the
paper page, file names carrying the upstream's function names, directories with spaces and
pipes, and a written result whose register was the tool's rather than a journal's. The
instruction: trim and reorganise the plan into per-sample, per-group, per-contrast and
interactions with hard budgets; built-in plots first, customised only where a built-in cannot;
professional names, order, legends and writing. And a standing rule, saved to memory: anything in
a plugin that cannot be modified easily from the maker level is a development suite defect or a
maker design defect.

## Decisions (the user's, from the options put to them)

1. **Axes and budgets.** `sample` at most 2 per sample; `group` at most 5 per group, a group being
   one of the four design arms (the marginal pools get no figures of their own); `contrast` at
   most 10 per contrast over all six (two marginal, four conditional); `interaction` at most 10
   per interaction direction (two directions in a 2 by 2, 20). Budgets count FILES; a per-item
   family takes a ceiling inside the budget.
2. **Built-in first.** The upstream's own plots fill each budget first. Customised panels stay
   only where the upstream has no plot: the design grid, the population census, per-sample totals,
   the difference matrices, the interaction panel, database coverage and permutation power. The
   host's N series goes.
3. **Per sample, two figures:** one quality figure (populations present, their counts and power)
   and one network overview (interaction strength).
4. **Names.** `figures/<axis>/<subject>/<NN>_<what>.png`; no spaces, pipes or tool prefixes in
   paths; the two-digit number is the figure's order; sample and arm names are the cohort's own;
   who drew a plate is in its caption record.
5. **Composition.** The paper page shows composite figures with lettered panels; every plate is
   also its own file under the same naming, as supplementary material.
6. **Standard.** Nature-style legends: a bold title sentence, then per panel what is shown, n per
   arm, scale, what colour and size encode, exclusions. Results in journal register, one finding
   per paragraph with its numbers and figure reference; Methods composed from the declarations;
   no tool names, run keys or "this run" anywhere on the page.
7. **The maker holds it.** A `layout` declaration in DEVPOINTS.yaml (axes, budgets, naming and
   ordering rules) applies to every plugin; a maker stage refuses a plan over budget or off the
   naming rule; a maker verb trims a plan to the layout. cellchat's new plan is that verb's output.
8. **The restart is accepted.** New figure ids; the audit begins again on about 130 figures.

## What the rule makes of this

Every one of the eight decisions is a declaration the maker reads or a verb the maker runs. If any
step below needs a hand edit of `kernels/cellchat.py`, the step is wrong and the mechanism is
fixed first. The eight held-out plugins stay untouched; they inherit the layout when they migrate.

## Predictions, before any change

- **L1** the layout declaration exists once, in DEVPOINTS.yaml; `sch dev convert layout` on
  cellchat's current plan refuses it, naming every axis over budget and every name off the rule,
  before any plan changes.
- **L2** `sch dev convert layout --apply` writes cellchat's plan under budget with no hand edit;
  validate, the build status, the rules of the round and the overfit scan stay green.
- **L3** the rerun draws at most 2 x 10 + 5 x 4 + 10 x 6 + 10 x 2 = 120 figures, every path on
  the naming rule, and the paper page numbers its figures in reading order.
- **L4** the host composes figures with lettered panels from the plan, and legends in the
  standard, from declarations alone; Methods composes from declarations alone.
- **L5** a cold writer and reviewer produce a Results section in the standard on the new run and
  every claim stands or is narrowed for a reason the figure shows.
- **B1** at most four defects of the mechanism, each fixed test-first the same day.

## Status

| step | state | where | what |
|---|---|---|---|
| 0 record | done | this commit | |
| 1 the layout declaration and the maker's stage | done | harness ebb4d92 (`sch/dev/layout.py`, the verb, the status rule); scProfile a79966c (the `layout` stage in DEVPOINTS with the budgets, the axes sample/group/interaction, a trimmed plan still runs: tolerant companion, axis filter, the host's gate, the over_budget ruling) | L1 held: the verb on cellchat's plan before any change read OVER on sample (36 against 2), group (36 against 5) and contrast (39 against 10), under on interaction (15 against 20) and cohort; the trim would keep 23 entries and drop 35 |
| 2 the trim, as the verb's output | done | scProfile 0ec4852 (cellchat 0.35.0); harness 2f05642, 83d94f0, f1537e6 (what the tool's gate found on the first three trims: one skip per dropped function, the draw sites, the profile marks and the R guard's list, the version) | `sch dev convert layout --apply` wrote every change: 58 entries to 23 - 2 per sample (population power, interaction-count circle), 5 per group, 10 per contrast, 15 over the interaction - 35 dropped with their draw sites, 18 upstream functions accounted for as over_budget, version raised by the verb; validate 0/0, build 9 of 9, rules 4 held, 0 fitted literals, gate 98 green, the plan baseline re-recorded deliberately. L2 held. Noted for the author's next pass: the two circle entries are equal on every declared field, so the count circle was kept by declared order where the decision named strength; `shows: result` on the strength entry is the declaration that decides it |
| 3 names, order, composition, legends, Methods | done | scProfile 25d5f2f (the figure set: `scprofile/figureset.py`, the index the prose and the page cite through, the composed section in register, the composed Methods, the page, the register check on `--write`, the brief by figure and panel, the skill), 6e8b58a (the host's panels follow `report.host_panels`, a marginal pool draws nothing, the plugin-side axis gate, the plan counted per axis), ffa9c5c (cellchat 0.36.0, the trim re-applied as the corrected verb's output, DEVPOINTS: the host table, `host_keep`, `host_list`, `side_effect`); harness 2cacda2 (the layout counts the host's files, owes and writes the list, leaves a side-effect entry alone, `--as-version`; a redraw expects nothing that belongs to a figure) | Every plate under `report/figures/<axis>/<subject>/<NN>_<what>.png`; figures of at most six lettered panels in the order cohort, arms (reference first), contrasts (design order), interaction, then the supplementary (per-sample and appendix-position plates) as S1, S2, ...; `Figure N \| title sentence. n. (a) ... (b) ...` legends composed from the plugin's subject, the design and the plates' own legends with the unit tag and the provenance sentence removed; `Fig. 3b` citations; `Effect of <factor> within <stratum>` headings; Methods from `wraps`, the settings every unit recorded, the design, the declared test, the sentinels, the functions the plan names; no run key, no "this run", no tool naming itself on the page or in a section carried in. L4 held on the mechanism (the composer's fixture and one real composite looked at); its measure on a run is step 4. On the host's panels the decision's letter ("keep the C1 difference matrices") is NOT followed: the option text called them something CellChat cannot draw, and CellChat draws them (`netVisual_heatmap` on the merged object, kept on the plan as the differential heatmap); under the user's own rule - built-in first - the host's twins go, and keeping them would have cost the tool's strength heatmap two of a contrast's ten. `host_keep` in DEVPOINTS is the one word that restores them |
| 4 the rerun, the looks, the writing | first half done | PBS 711438 (`20260914T133714Z__scprofile-0ec4852__04_profile__rerun`, compute1016, cellchat 0.35.0, 33 min) | The count half of L3: 227 PNG files against 945 (per sample 2, per contrast 10, the interaction 15, per arm SIX against five - the host's own emit path did not hold a plugin-drawn panel to its axis, so every arm drew the per-sample census; the four marginal pools drew 6 each, which the layout never counted; the host's 84 panels beside all of it); cores peak 2.28 on 2, `over_share` false, procs_peak 6, cost high - the cores half of L3 held. The seal read FAILED on 163 products of the reference that belong to figures a trimmed plan no longer draws (the F-series source tables, the per-sample page), and `capacity --promised` refused 24 files of the tool's NMF rank estimation whose accounting entry the trim had dropped. Four defects of the mechanism, each fixed test-first the same day: the axis gate, the margins, the redraw rule, the side-effect entry. **Second rerun** PBS 711528 (`20260914T145501Z__scprofile-ffa9c5c__04_profile__rerun`, compute1016, cellchat 0.36.0, 29 min): SEALED, every after-step exit 0 - `capacity --promised` answered, memory 2.1 + 13.3 per 100k at or under the declaration, cores peak 2.46 on 2 with `over_share` false and procs_peak 6, cost high (2246 s per 100k). 119 plates exactly as predicted: 2 x 10 samples, 5 x 4 arms (the axis gate held), 10 x 6 contrasts, 16 over the interaction, 3 for the cohort; the four marginal pools drew nothing; the host drew the four declared kinds and no other. The figure set built by the report: 119 plates under `report/figures/<axis>/<subject>/<NN>_<what>.png`, no space, pipe or drawing-side prefix in any path, 15 main figures (cohort, the four arms with the reference first, the six contrasts in the design's order, the interaction) and 20 supplementary, each with a composed legend; the brief lists every plate as `Figure 3b`. L3 held in full; L4 held on the run, with four defects of composition found on the page and fixed test-first (49c8613): an interaction heading naming one pair twice, a contrast title without the factor bracketed, a seven-plate subject laid greedily into six and one, the cohort's n missing - and the render now rebuilds the set and the brief. B1 fails: eight mechanism defects against a prediction of four, every one found by the run or the page rather than by a reader, every one fixed the same day. 50 looks carried by content hash from the earlier runs, 27 plates of the scan set outstanding, 12 open findings carried |
| 4 (continued) the looks, the writing, the seal | done | the cold agents' account is docs/blind/0009-the-figure-set.md; the writing run `20260914T171426Z__scprofile-d318075__04_profile__written` (PBS 711584, compute1003) | Two cold lookers: 27 plates handed (50 of the scan set's 77 carried by content hash), 27 recorded, 0 refused, 10 marked defect; the audit: 5 open findings on 3 kinds after 6 closed by disclosure - two host-owned (the run's colour map gave fourteen labels hues 0.6 degrees apart: three populations in one blue and three in one magenta on every ring; the colour-map sentence on every caption, false on a per-programme scatter), one the tool's (a role heatmap's colour floor 0.1 on one arm and 0 on another), both host kinds fixed test-first (dc48927) and answered on the ledger for a fresh look at the next rerun. The cold writer: the brief's headings verbatim - which the brief itself had been printing as `SIMPLE age \| diet = chow` (the source of the user's "not professional"; fixed, 6c5d947) - four claims citing clean plates, a 1,226-word Results in the register carried in on the first `--write`, 0 refusals, 0 defects; it wrote around four whole figures because the citation check keyed on the figure number (fixed to the panel, b0a8260). The cold reviewer: 13 of 13 claims standing against the run's own tables, 0 refusals, 0 defects. The page: Results, Methods composed, 15 figures and 20 supplementary with composed legends, no run key, no "this run", no tool naming itself; the colour-map sentence on the legends put in the register and only where true (8c30092). Writing seal SEALED, 3 of 3 held; the maker reads build 9 of 9, test 7 of 8 (`audited` owes the one tool-owned kind and the fresh look) |
| 5 the record | done | this commit; memory | L1 held; L2 held; L3 held (119 plates, every path on the rule, cores 2.46 peak on 2); L4 held (composites, legends and Methods from declarations alone, with four composition defects found on the run and fixed); L5 held (a cold writer's Results in the standard, 13 of 13 claims standing); B1 **failed**: fourteen mechanism defects against a prediction of four, every one found by a run, a page or a cold agent rather than by a reader of the code, every one fixed test-first the same day. What the layout did not decide is recorded for the author's next pass: `shows: result` on the strength circle; the interaction family's item order (three files fell in one direction); the role heatmap's colour floor as a legend disclosure; the plan legends' capitalised emphasis, which a journal's legend does not carry |
