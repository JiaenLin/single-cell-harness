# ADR-0020: the loop converges - the host's ten, the author's second answer, the two seams, and what nobody checks

**Date** 2026-09-13. **Follows** ADR-0019 (the loop closes). **Status** in progress; the table at
the end is filled as each step lands.

## Context

ADR-0019 closed with the loop running end to end and no person in it, and with the audit still
owing: 66 findings on 36 kinds after a fresh look, owners HOST 10, PLUGIN 4, TOOL 22, seventeen
defects of the mechanism met on the way, fifteen fixed and two open. The eye's verdict was the
finding: a rerun does not clear a finding, a fresh look does, and the author's first answers cured
some of what the eye named and not the rest, while the host's own panels earned ten new findings.
Two seams stayed open: the composed section routes a total-strength sentence to the count figure,
and a writing run's replay has no siblings, so the looks that carry by content hash are invisible
from inside it. And two declaration keys the kernel point requires, `cores` and `cost`, are
printed by the maker's status as checked by nobody on every run.

## The goal, in one number

A second turn of the same loop in which the fresh look clears the audit: the count of kinds that
survive a fresh look goes from 36 toward zero, the pen writes from a clean figure set, and the
writing seal holds its three predictions. Same rules as before: the plugin is maker output and
the author's answers are pasted, never written by hand; the eight held-out plugins untouched;
every change to the mechanism general and test-first; every run through the scheduler; the
predictions below committed before any change.

## Decisions

- **A. The host's ten first, as mechanism.** Every finding on a host-composed panel is the
  host's debt: a failing test in the looker's words on the drawing as it was, then the change in
  the panel module or the repertoire, so every plugin gets it. Three of the ten are the same
  defect - a text clipped at the canvas edge (two colour-bar titles, an axis title) - which the
  drawing audit does not detect: the audit gains `text_clipped` and the repertoire a repair, and
  the eye stops being the only check for it. The rest are keys and notes a panel owes (a dagger
  and a band, two colours, an asterisk, a sum that is not the whole), a callout placed over data,
  and two clumps of labels the declutter did not clear.
- **B. The 26 plugin and tool kinds through the worksheet**, by a cold author, as in blind 0006,
  with the eye's fresh look on the rerun as the judge. Nothing else touches the plugin.
- **C. The composer's route carries the quantity.** A sentence about total strength cites the
  strength figure; a figure answers a need for a quantity, not a need alone.
- **D. Carried looks are found from inside a writing run.** The review's siblings are the runs
  under the nearest ancestor that holds any, and a writing run stands for the replay it holds.
- **E. `cores` and `cost` are measured.** Each becomes a measuring command on a completed run
  with an `apply:` that writes the declaration, the way `measure` got `--memory` in ADR-0018;
  the maker's status stops printing them as checked by nobody.
- **F. Blind 0007 grades the round**: a cold author, two lookers, a writer, a reviewer, the
  rerun through the emitted job, the writing seal.

## Predictions, before any change

- **H1** each of the ten host kinds has a test that fails on the drawing as it was, in the
  looker's words, and passes after; the audit reports `text_clipped` on a synthetic panel whose
  title runs past the canvas, and the repair brings it inside.
- **H2** after the rerun, a fresh look records no finding on any of the ten host kinds.
- **A1** the cold author answers the 26 kinds without a question, edits at least half, bumps the
  version once, and passes validate and the build status.
- **A2** after the rerun and the fresh look, at most eight kinds survive (36 now).
- **D1** the composed section cites the strength figure for the strength range, and a claim
  copied from it is not withdrawn for the figure.
- **D2** the rerun's writing seal holds W3: `looked_at` reads done from inside the writing run.
- **C1** the maker's status reads `cores` and `cost` answered on a completed run, the values
  written by the tool's own command, none by hand.
- **B1** the agents meet at most six defects of the mechanism, each fixed test-first the same day.

## What must not be done

No hand edit of `kernels/cellchat.py` except the paste of the author's answer; nothing to the
eight held-out plugins; no fix beside the mechanism that exists; no run on a login node; no
prediction rewritten after the numbers are in.

## Status

| step | state | commits | notes |
|---|---|---|---|
| 0 record | done | this commit | |
| 1 the host's ten | done | scProfile 3dbc6f9, 6a988d5, fca2fba | each finding a failing check in the looker's words, then: the column fit and the save use the tight box unioned with every text's extent (C1 x2, P2); the flow panel's dagger and band keyed in its legend (C3); the interaction panel's two colours keyed (C5); the contribution panel says how much its bars carry and how many pairs carry the rest (N7); the design grid's asterisk has its footnote, pinned as an emitter of the aliasing (across the design); the matrix key above the colour bar (N3); touching counts as overlapping and a clump the vertical nudge cannot clear becomes a ladder with leader lines (N4, C4) - the paid-for rule that labels keep their own x now reads: unless a ladder ties them to their point; gate 96 green |
| 2 the author's second answer, the rerun, the fresh look | done; the audit did not clear | scProfile 3ee26e7/4c6112f, db066f3; harness 7736d42, ed34a1c, 6149860; PBS 711115, 711118 (failed on one node), 711119 SEALED | the cold author answered the 26 kinds (0.31.0); the rerun sealed on the third submission, pinned to a node the clean runs used; two lookers recorded 83 looks (56 carried), 39 defects; 25 kinds survive (H2 and A2 failed); eight defects of the mechanism fixed test-first (harness fd33e31; scProfile 8eb7a3b, 7aca925, 32a1bdf, f5b3c22, c1c1346, ac52840), all in the reading of state; the writer wrote 3 claims and a section, the reviewer narrowed 10 of 11; the composed ratio's basis recorded as the next turn's question |
| 3 the composer's route | done | scProfile 8545fa5 | a sentence about a quantity cites the plate whose stem names that quantity first and a stem naming `count` last where the quantity is not a count (`_figs_for` takes `prefer`/`avoid`, the ratio sentence passes the words of the plugin's own quantity name); the known issue closed; test-first in the composer's citation suite |
| 4 a writing run's siblings | done | scProfile a9bb0eb | a run's siblings are the runs beside it, and when its parent is not a run, is named like a run key and holds only this one, the parent's siblings are this run's; a scratch folder holding one run is not a stand-in (the loop-driver fixtures caught the looser rule carrying looks between unrelated runs); test-first: looks and answers carry into a writing run's replay and out of it |
| 5 cores and cost measured | done in the mechanism; measured on the next run | scProfile 5936819 | every instance measures its process tree's CPU beside its memory, and its wall time; the run fits a cores model (the peak one-second reading) and a cost band (the median wall time per 100,000 cells; bands trivial/low/medium/high defined once) per plugin; `capacity --cores` and `--cost` are gates with `--declare` as the way out, writing the value on the line it shares with other keys; two test-phase stages declare them; the maker's status reads test 5 of 8 with `cores` and `cost` owing until a run records them; suites 97 green |
| 6 blind 0007 | done | docs/blind/0007-the-loop-converges.md | H1, A1, D1, D2 held; H2, A2, B1 failed; C1 half (cost by the tool, cores owes on the burst); the writing seal PBS 711120 SEALED, 3 of 3 |

## Closed, 2026-09-14

The loop ran its second turn end to end on cold agents, and the number it was built to move went
from 36 kinds to 25, not toward zero: the audit did not clear, and the goal in one number
failed. What held: the mechanism answered the ten host kinds test-first (H1), the author
answered its 26 without a question (A1), the composed claims cite the strength plate (D1), and
the writing seal held all three predictions including the one that failed last round (D2), so a
writing run now stands for the run it was written from. What failed: three of the ten host
kinds came back with a finding, two of them made by the answers (H2); 25 kinds survive (A2);
eight defects of the mechanism against six predicted (B1); and `cores` owes on a burst the gate
refuses to declare (C1, half). Every one of the eight defects was in the reading of state - a
status line, a listing's headline, a stale brief, a refusal's wording, a next step - and each is
fixed test-first in the mechanism that exists; none was in what a run computes.

What the next turn is about, in order: the seventeen tool kinds and five plugin kinds the fresh
look left, which are the plugin author's; the composed ratio's basis - the host's two-scale table
totals an arm over the pathways shared with one partner and the plugin's `how_much_total` plate
over the pool of all four, so a sentence from one cannot be read off the other (the reviewer's
finding, open in blind 0007); the plugin's cap on its threads so `cores` can be declared; and a
third turn of this same loop, with the same rules, to see whether the number moves toward zero
once the author has the seventeen.

