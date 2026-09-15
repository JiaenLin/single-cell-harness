# ADR-0025: the last turn on cellchat - the author's pass on what the layout left open, one rerun, every stage green

**Date** 2026-09-15. **Follows** ADR-0024 (the figure plan under budget). **Status** proposed; the
table at the end is filled as each step lands. **Stops before** the eight held-out plugins, which
are the round after this one.

## Context

ADR-0024 left the plan under budget, named, composed and written to: 119 plates, 15 figures and
20 supplementary, a cold writer's Results in the register, 13 of 13 claims standing, the writing
seal 3 of 3. One stage still owes on that run: `audited`, with 5 open findings on 3 kinds - two
of them the host's own defects wearing the tool's and the plugin's names (the colour map, the
caption suffix), fixed and answered on the ledger for a fresh look; one the tool's (a role
heatmap's colour floor, 0.1 on one arm and 0 on another). And the layout decided four things by
its own order that a decision had named otherwise, recorded rather than done: the per-sample
network overview was to be the strength circle and the trim kept the count circle by plan
order; the interaction family's three files fell in one direction; the role heatmap's floor
wants a disclosure; the plan's legends carry capitalised emphasis a journal's legend does not.

No run of the arc has ever read every stage done. That is what this turn is for.

## Goal

**One sealed run on which the maker reads build 9 of 9 and test 8 of 8**, reached the way the
arc says: a cold author answers the worksheet and the four items in the plan, the maker's verb and
gates hold the plan, the rerun goes through the emitted job, cold lookers take the fresh look the
palette change forces on every plate, the section is re-carried against the set it now cites,
the reviewer defends the claims again, the writing seal holds. Nothing in the eight held-out
plugins is touched; nothing in `kernels/cellchat.py` is edited by anyone but the author and the
maker's verbs.

## The steps

0. **Record.** This file, with the predictions below, before any change.
1. **The author's pass** (a cold agent in a clean room, the cellchat-only export at HEAD, the
   worksheet and this list; every answer pasted through the gates - vocabulary, `sch dev rules`,
   the overfit scan, validate, the suite, and `sch dev convert layout` still ok - and the version
   raised by the author):
   - the per-sample and per-arm network overview is the **strength** circle, as decided: the one
     kept circle entry draws `measure = "weight"` (the trim keeps the first circle in plan order,
     so the plan carries one, the strength one);
   - the interaction family's ceiling within the budget: `at_most` 6 on `nativecmp_interaction`
     so each direction carries count, weight and probability (16 of 20 becomes 19 of 20), or the
     items reordered so no direction is empty - the author's choice, checked by the layout;
   - the role heatmap's colour floor: one sentence in the legend saying the key's floor is the
     plate's own minimum, closed with `--stated`;
   - every kept entry's legend in the register a journal prints - no capitalised emphasis, no
     "NOT", no tool naming itself; what a colour, a width or a size encodes stated plainly. The
     check is the reviewer's eye and the writer's brief; it is not mechanised in this round;
   - the lookers' unmarked notes read and answered where cheap (the census panel's axis range,
     the count heatmap's missing column title).
2. **The rerun** through `sch dev job --redraw`, pinned to compute1016, with the prediction in
   the job; the run copied beside its siblings.
3. **The fresh look.** The palette change redraws every plate, so no look carries: cold lookers
   on the whole scan set, in the tool's shards; the audit's worksheet after.
4. **The section against the set it cites.** Three more plates in one direction of the
   interaction re-letter two figures, and the section carried in on the second run cites them by
   letter. The mechanism first (test-first): the draft record carries the figure set's digest,
   and the page and `next` mark a section STALE when the set has changed since it was carried in
   - the same rule the claims already keep. Then a cold writer re-reads the brief and re-carries
   the section; the claims, stale on the redraw, go to a cold reviewer again.
5. **The writing seal**, and the maker's status on the run.
6. **Record**, and stop. The eight held-out plugins are ADR-0026.

## Predictions, before any change

- **A1** the cold author answers the five items in one pass with at most two refusals from the
  repository's own gates, raises 0.36.0 to 0.37.0 once, and the layout check reads every axis
  under budget with the interaction at 19 of 20; no hand edit by the dispatcher.
- **R1** the rerun draws 122 plates (2 x 10, 5 x 4, 10 x 6, 19 over the interaction, 3 for the
  cohort), seals SEALED with `capacity --promised` answered, cores peak under 3 on a share of 2.
- **E1** after the fresh look the two host-answered kinds carry no finding, the role heatmap's
  kind closes by disclosure, and at most two kinds stay open, none of them the host's.
- **W1** the page marks the section STALE on the set's change before anyone reads it; the
  re-carried section cites the re-lettered panels; the reviewer leaves 13 of 13 standing, the
  numbers being unchanged.
- **M1** the writing seal reads 3 of 3 and `sch dev convert status --run` reads build 9 of 9,
  test 8 of 8 - the first run of the arc with every stage done.
- **B1** at most three defects of the mechanism, each fixed test-first the same day.

## Cost, estimated before

Five cold agents (an author, two or three lookers, a writer, a reviewer), about 1.3M tokens and
two hours of agent time; one rerun of about 30 minutes on the node and one writing seal; about
three hours of wall clock.

## Status

| step | state | where | what |
|---|---|---|---|
| 0 record | done | this commit | |
| 1 the author's pass | done | scProfile ad1b76d (cellchat 0.37.0) | A cold author answered the five items in one pass: the strength circle (`native_circle_weight`, the profile list and the draw site following), the interaction family at 6 with the hand-written dedup that had kept the second framing from drawing removed (the ceiling alone would have changed nothing - the author found the real gate 250 lines below the entry), the role heatmap's floor stated, all 24 legends in register, the three unmarked notes answered. One exchange back: two of the repository's own tests held a legend to "RED means" and "NO interaction" in capitals - the tests corrected, the author lifted the exception. A1 held: one refusal-equivalent, 0.36.0 to 0.37.0 once, interaction 19 of 20, no hand edit by the dispatcher |
| 2 the rerun | done | PBS 711706 (`20260915T011642Z__scprofile-ad1b76d__04_profile__rerun`, compute1016, 34 min) | SEALED, every after-step exit 0; 122 plates exactly, both interaction directions drawn, 16 main figures and 20 supplementary; cores peak 2.18 on 2, cost high. R1 held |
| 3 the fresh look | in progress | two cold lookers on the 40 plates the palette redrew (40 carried); scProfile a7f247b (cellchat 0.38.0); PBS 711745 (`20260915T023343Z__scprofile-a7f247b__04_profile__rerun`) | 40 recorded, 0 refused, 28 marked defect; the worksheet: 33 findings on 12 kinds - because the legends rewritten in register had unbound every disclosure a stated answer was tied to, the findings those had closed came back. The author, in a second exchange: 22 re-stated in the legends' new words, four legends given one sentence, and the two differential heatmaps given the tool's own diverging palette (their key ran in one colour over a grid holding both) - the one edit that needs a redraw, so a second rerun of this turn was submitted for it. E1 is graded on that run |
| 4 the section against the set | | | |
| 5 the writing seal, the status | | | |
| 6 the record | | | |
