# ADR-0019 — the loop closes: findings become a worksheet, a rerun, and a second look

**Date** 2026-09-13. **Status** accepted; executing. **Follows** ADR-0018 (the audit repairs, the
run measures, the eye before the pen). **Rules in force** the four top rules (a plugin is maker
output - the only edits of `kernels/cellchat.py` this round are an author's worksheet answers
pasted and the tool's own `--declare`; the eight are held out; mechanism and the agentic layer
are fixed in place; end to end is cellchat), the HPC rules (H1: nothing authored on the cluster,
every tool invocation through `qsub` after `validate.sh`, no compute on a login node, runs under
`~/projects/SAMBO/runs/scprofile/04_profile/`), and scProfile's DEVELOPMENT.md (every check seen
to fail; smallest change; fix the mechanism that exists; commit only when green; cost recorded).
**The brief for this round**, in the user's words: integrate the rerun that clears `audited` as
a formal end-to-end workflow; the order of actions may be adjusted for consensus, efficiency and
harmony; scProfile runs end to end without a human, purely for agents.

## Context — where the loop is open, measured on blind 0005

On the replay of PBS 711029 two cold lookers marked 70 of 139 figures as needing a change, the
maker read `audited` owing and named the findings in the lookers' words, and the writer could
not rest a claim on any of them. Then nothing happened, because nothing could: the stage says
"fix in the plan or the plugin, rerun, look again" and none of those three is a command anyone
can run. Read against the mechanism:

1. **A finding is not yet work.** Seventy findings on 46 figure kinds have three different
   owners and the ledger names none of them. Eight kinds are the HOST's own composed panels
   (`cellchat_N2_chord`, `N3_matrix`, `N4_role`, `N6_role_heatmap`, `C4_role_shift`,
   `P1_population_presence`, `P2_unit_totals`, `across_design`) - mechanism, fixed in
   `scprofile/`, nothing to paste. Twelve kinds are the TOOL's plates (`native_*`) drawn by
   CellChat's own functions with the plan entry's arguments, size and legend - the plan is
   where those are adjusted, by the author. The rest are the PLUGIN's own drawing: its
   matplotlib panels and its compare-phase plates (`nativecmp_*`, six of them `drawn_by: plugin`),
   at an emit or draw site in `kernels/cellchat.py`. An author handed the ledger must work all
   of that out before touching anything; an author handed a worksheet pastes.
2. **A finding that should stay has no answer.** CellChat's colour key reads "min" and "max"
   by the upstream's design, and a chord diagram's ribbon has no numeric key in any version of
   it. The loop's rule is "every finding becomes a change, or it did not happen"; the only way
   to make one not happen is a later look on the same bytes, and the author is not a looker.
3. **The rerun has no printed command.** The agenda's run task says "submit as a batch job";
   the maker's status prints the station. The maker already emits a job from a reference run's
   own recorded command (`sch dev job`, DEVELOPING §6), but it reads the tool's commit from
   `.git` - the cellchat-only tree on the cluster is an export with `HEAD.txt` - rebuilds the
   argv without an interpreter (the record's argv[0] is `scprofile/cli.py`), runs nothing after
   the command (no report, no status), and expects every figure of the reference as a product,
   which a redraw is allowed to change.
4. **A third of the figures no machine ever measured.** The compare phase writes no manifest,
   so its 249 plates are recorded nowhere; the host's own panels save through `_Shim`,
   `_save` and `design_panel.draw` with a plain `savefig` - no column fit, no audit, no repair,
   a stamp at a fixed y. Station 6b reports "333 recorded by nothing" and means it.
5. **The order is written in three places and enforced in none.** The contract, the loop and
   the skill each say look, fix, rebuild, look again, write; the agenda's tasks and the maker's
   stages stop at "audited owes".

## Decision — the workflow, and what makes each step a printed command

The end-to-end workflow, as the tools print it, for an agent and nobody else:

| step | who | the command that prints the next |
|---|---|---|
| 1 run | the job | the agenda's run task; the job writes AGENDA.md and seals |
| 2 promised, measure | machine | `sch dev convert status --run`; `measure` applied by `--apply` |
| 3 look | lookers | `scprofile review --shards N`; `--figure --note [--defect]` |
| 4 audit | machine | the status: `audited` clean, or owing with "answer it: ..." |
| 5 worksheet | the author | `scprofile review --worksheet`: edits pasted into the plan or the plugin, the version bumped; `--answer` for a plate that should stay |
| 6 rerun | the job | `sch dev job --ref <this run> --redraw ...`, validated, submitted; the new run's replay beside the old |
| 3' look again | lookers | `review --shards N` lists only what was redrawn or answered; unchanged looks carry |
| 7 write | the writer | `paper --brief`, `--claim`, `--write` - refused on a plate with an open finding |
| 8 review | a second agent | `paper --round --reviewer` on every claim |
| 9 render, deliver | the writer | `paper --render`; `delivered` |
| 10 seal the writing | the job | `submit_writing_seal.sh --prepare / --seal` |

The loop is 3 → 4 → 5 → 6 → 3', repeated until 4 is clean; the pen (7) opens only then. No
new stage, station or file kind. What changes, each to a mechanism that exists:

- **A. Every figure a run holds is measured and recorded.** The compare phase writes its
  manifest (`out.json` with the companion's records, `measured: False`, as a unit does); the
  host's own panels go through one audited save - the column fit, the stamp placed from the
  rendered box, the re-solve, `audit_and_repair`, the record - and `panels.json` carries each
  panel's `audit` and `repairs`; station 6b reads `panels.json` beside `report.json`. On this
  cohort "recorded by nothing" goes from 333 to 0.
- **B. The findings become a worksheet.** `scprofile review --out RUN --plugin P --worksheet`
  groups the open findings by kind, names the owner of each kind - host panel (the module and
  function), tool plate (the plan entry, printed as declared), plugin drawing (the file and
  line of the emit or draw site) - quotes the eye, and prints the two answers: edit the entry or
  the code and bump the version; or `--answer` (below). It ends with the prediction the rerun
  is submitted with. The `audited` stage declares it as its `worksheet:`; the maker prints
  "answer it:" with the repository's own command filled for the owing stage - a run-side
  stage is not a maker verb, on purpose - and runs a verb stage's worksheet on `--worksheet`,
  as it does `apply:`.
- **C. The answer path.** `scprofile review --figure F --answer "..." --reviewer <author>`
  records why a plate stays as it is. The finding stays open - the eye's verdict is the
  eye's - until a looker's fresh look on the same bytes; `outstanding` lists answered figures
  as needing a look, the shard split includes them, station 6b counts them.
- **D. The rerun is the maker's emitted job.** `sch dev job` gains: the tool's commit read from
  `HEAD.txt` when there is no `.git`, and given with `--tool-commit` when the tree is not
  readable where the job is written (the job verifies at start and refuses a moved tree); the
  argv rebuilt with the interpreter when the record's argv[0] is a script under the tool; the
  repository's declared `run.after` commands appended after the command (`report`, `status`,
  `capacity --promised`, `--memory`) and the maker's own `status --run` written to the run's
  logs; `--redraw`, under which figures are not expected products - the plan's promise and the
  eye judge them. The agenda's run task and the `audited` stage's text name it.
- **E. The host's eight findings are fixed**, as the host's own debt: a width key on the chord,
  the grey cross keyed on the matrix and the role heatmap, the role scatter and the role shift
  decluttered, the sentinel row blanked from the presence ranking, the mixed-arm bars keyed on
  the unit totals, the dot size keyed on the design grid.
- **F. One order, written once.** TEST_LOOP.md carries the table above; the contract and the
  two skills point at it; the agenda's write task, `next`, the `audited` and `looked_at` stage
  texts say the same words.

## What must not be done

- No hand edit of `kernels/cellchat.py` beyond pasting a cold author's worksheet answers and the
  tool's own `--declare`; the held-out eight untouched; no new layer, stage, station or file kind.
- No run made on a login node; every job through `qsub` after `validate.sh`; nothing authored
  on the cluster; the tool tree on the cluster an export at a named commit.
- No prediction rewritten after the numbers are in; a wrong prediction is recorded as wrong.

## Steps

0. This record.
1. **Every figure measured** (scProfile): the compare manifest; the host's panels through the
   audited save; `panels.json` with audits; station 6b reads it. Tests: a compare run leaves
   `out.json`; a shim-drawn panel is audited and repaired and its record carries both; the
   station counts `panels.json`; a run with every figure recorded prints no "recorded by
   nothing".
2. **The host's eight findings** (scProfile): each fixed with a test that fails on the old
   drawing and passes on the new; the audit control's sound half unchanged.
3. **The answer path and the worksheet** (scProfile): `--answer`; `review.answered`;
   `outstanding` and the shards include answered figures; `--worksheet` with the three owners;
   the `audited` stage's `worksheet:` and texts; `looked_at`'s text.
4. **The maker** (harness): `worksheet:` beside `command:` and `apply:`; `sch dev job` as in D;
   `run.after` read from the declaration; DEVELOPING §6 and §8; the skill.
5. **The order, written once** (scProfile, harness): TEST_LOOP.md's table, the contract, the
   result-section and maker skills, the agenda's texts.
6. **Blind 0006, the loop end to end**: on the replay of 711029 with its 70 findings - a cold
   author answers the worksheet in a clean room (the real plugin file, no git); the dispatcher
   pastes the answer into the repository as the author's; the rerun through the emitted job
   (predictions L1-L6 in the job); the new run's replay beside the old; two lookers on what is
   outstanding; the maker's `audited`; a writer, a reviewer, the render, the delivery, the
   writing seal. Predictions B1-B5 written before any agent starts, in docs/blind/0006.

## Predictions

The rerun, graded by the emitted job:

- **L1** the emitted job runs the reference's command with the interpreter, the tree's commit
  verified at start, and seals SEALED with every non-figure product of the reference present.
- **L2** every raster figure the new run holds carries an audit in `report.json` or
  `panels.json`: station 6b prints no "recorded by nothing".
- **L3** on the replay beside the old, looks carry: a figure whose bytes did not change is not
  outstanding; every redrawn or answered figure is.
- **L4** the host's eight panel kinds carry no machine finding after repair.
- **L5** `promised` done and `measure` answered on the new run without a hand on the file.
- **L6** the maker's status on the new run reads `audited` owing only on what the eye has not
  yet re-looked, and names it.

Blind 0006:

- **B1** a cold author, given the worksheet and nothing else, answers every kind without a
  question: edits for at least half the kinds, answers for the rest, the version bumped, and
  the plugin passes `scprofile validate` and the maker's build status afterwards.
- **B2** after the rerun the lookers are handed only what was redrawn or answered - fewer than
  the 139 of the first look - and record it without a refusal.
- **B3** `audited` clears, or names at most five kinds that survived a fresh look, in the
  lookers' words.
- **B4** the writer writes without a claim or a section resting on an open finding; a second
  agent rounds every claim; the section renders; `delivered` reads done; the writing seal holds
  its three predictions.
- **B5** the agents meet at most three defects of the mechanism, each fixed test-first the same
  day.

## Consequences

Easy: a finding is work with an owner and a command; a plate the upstream draws as it should
can be answered and settled by a looker, not by the author; the rerun is one printed command
from the run it replaces; every figure is measured. Hard: the loop costs a run per iteration and
an author's judgement per kind; on this cohort 46 kinds. **Given up**: the pen waits for as many
iterations as the eye demands, and a plugin whose upstream draws badly by design will carry
answers rather than fixes - recorded, in the ledger, with a looker's agreement.

## Status

| step | state | commits | notes |
|---|---|---|---|
| 0 record | done | this commit | |
| 1 every figure measured | done | scProfile 0841e7a | one audited save (`figure.save` with the stamp from the rendered box, `fit=False` for a caller that fitted its own width) serves `_Shim.emit_figure`, the contrast and interaction panels and the design panel; their records carry `audit` and `repairs`; a compare plate's record says the companion drew it; `panels.json` carries all of it and station 6b reads it beside report.json; suites 94 green |
| 2 the host's eight findings | done | scProfile 0f4236a | a width key on the chord; the grey cross keyed on the matrix and the role heatmap; the declutter's cap grows with the clump and the registered sets are re-solved after each repair pass (labels keep their own x - the sideways phase tried first broke a paid-for rule and was withdrawn); the sentinel row last and blank; the pooled arms keyed on the unit totals; the marker size keyed on the design grid; suites 95 green |
| 3 the answer path and the worksheet | done | scProfile 4628047 | `review --answer` and `review.answered` (the finding stays open until a looker's fresh look; the outstanding list and the shards carry the figure as needing one); `review --worksheet` with the three owners, the plan entry as declared or the code site, the eye's words, the answer given, the two answers and the rerun's prediction; `audited` declares `worksheet:`; station 6b names it; suites 96 green |
| 4 the maker | done | harness: this commit | `worksheet:` read beside `command:` and `apply:`, run on `--worksheet`, named "answer it:" for an owing stage, advanced by apply over worksheet over the command; `sch dev job` reads `HEAD.txt` where there is no `.git`, takes `--tool-commit` and verifies it at start, runs a script argv through its interpreter as a module, leaves figures out of a `--redraw`'s products, appends the repository's `run.after` and the maker's own status; `points.run_after`; harness suite green |
| 5 the order, written once | done | scProfile d7b6d37; harness d338fde, b59db9e, 3dec780 | the workflow table in docs/TEST_LOOP.md as the tools print it; the contract, the result-section skill and the agenda's blocked write task point at it; the repository declares `run: after:` (report, status, capacity --promised, capacity --memory); the developing guide and the maker skill carry the rerun and the worksheet; the surface test caught that `sch dev convert audited --worksheet` was not a parseable command - the maker's verbs stay its own and a run-side stage's answer-it line is the repository's own command, printed filled; suites 96 and the harness suite green |
| 6 blind 0006 | done | scProfile 3ee26e7, 4c6112f (the author's two answers); harness 72ce582 .. cb5dc99; docs/blind/0006-the-loop.md | the loop ran end to end with no person in it: a cold author answered the worksheet (28 kinds edited, 10 answered; refused once by the portability scan and amended), the emitted job reran the plugin (four submissions - three sealed FAILED for the job's own reasons, fixed test-first; the fourth SEALED), the lookers were handed 120 figures and marked 66, the audit named 36 surviving kinds with owners (HOST 10, PLUGIN 4, TOOL 22), the writer wrote from the 48 clean figures and was refused on a flagged one, the reviewer rounded 29 claims, the section rendered, two writing seals held W1-W2 and failed W3. L1, L4, L5 held; L2, L3, L6 held after fixes; B1, B2 held; B3 failed (36 kinds survived); B4 held up to the seal; B5 failed on the count: seventeen defects, fifteen fixed test-first the same day, two open |

## What the round found

The loop closes, and it closes on the seams. Every step ran as a command the tools printed, with
no person in it; what the round paid for was seventeen defects of the mechanism, twelve of them
at a seam between runs or between machines: a look, an answer, a record that did not carry from
the run beside; a job that verified one tree and imported another; a prefix, a path, a readers'
file that a directory holds and a run does not; a rebuild that dropped what the run had recorded;
a station that read only its own ledger. Each is fixed test-first except two recorded open - the
composer's route for a total-strength sentence, and the writing run's replay that has no
siblings - and each fix is general: the output flag by value, the code that runs verified against
the tree, an answer bound to bytes like a look, a rebuild that records what is on disk.

The eye's verdict is the second finding. A rerun does not clear a finding; a fresh look does,
and on this cohort the author's first answers cured some of what the eye named and not the rest
- the fused ring labels after a smaller font, a caption the edit itself added and then clipped -
while the host's own panels earned ten new findings. B3 predicted five surviving kinds and
thirty-six survived. That is not the loop failing; it is the loop measuring the plugin's next
build, with its owners named. The rule the round refined is the pen's: the agenda said the pen
waits for the run, the gates waited for the figure, and the writer proved the gates right - a
section written from the figures the eye accepted was accepted, a claim on a flagged one was
refused. The pen waits for the figures.

Open for the next round, in the order the loop names them: the 36 kinds of the worksheet
(ten host kinds first, mechanism); the composer's route; the writing run's siblings; and the
pre-existing debt the status still prints - `cores` and `cost` checked by nobody.
