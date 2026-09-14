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
| 1 the layout declaration and the maker's stage | | | |
| 2 the trim, as the verb's output | | | |
| 3 names, order, composition, legends, Methods | | | |
| 4 the rerun, the looks, the writing | | | |
| 5 the record | | | |
