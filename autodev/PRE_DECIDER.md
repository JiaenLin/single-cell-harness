# The pre-decider (v2, 2026-11-10)

The PI, 2026-11-09: "use predecider for decision". 2026-11-10: "where is predecider, why need my decision, review rules
and goals and decide", then "for the predecider, improve it". The VCC owner asked for theirs to be "added back" twice
(11-01, 11-08). Both decayed for one reason: the pre-decider was a rule the coordinator had to remember at the moment of
writing a question, and that moment is exactly when a coordinator defers. Version 2 makes it a form, a ledger, a catalogue
and a test, so a question cannot reach the PI without passing through it.

## 1. The form (filled before any question exists)

Every candidate question, from the coordinator or from an agent's hand-back, becomes one row in
[`ledger/decisions.tsv`](ledger/decisions.tsv) (append-only; stamps from `date -u`):

| column | holds |
|---|---|
| `decision_id` | `D-###` |
| `action` | what would be done, on what (repo, host, run, record) |
| `reversible` | `yes` / `no` (a force-push, a deletion of a record, a vendor request, a promotion: `no`) |
| `outward` | `yes` if it touches anything outside our own folders and branches (a public `main`, a collaborator, a vendor, an account) |
| `rules_searched` | the tier and row, or the catalogue row, that was read |
| `decides` | what that rule decides, or `none` |
| `verdict` | `ACT` / `DECLINE` / `ASK` |
| `decided_by` | the rule or catalogue row for ACT/DECLINE; the tier-III clause for ASK (section 2) |
| `where_recorded` | STATE.md section, or the ledger row, that carries it |

## 2. The user-only list (the only reasons for ASK)

An `ASK` row's `decided_by` names one of these, verbatim, or the test fails:

- `promotion` (what becomes a promoted result);
- `sign convention` (the direction of a contrast, or how a difference is signed);
- `threshold the data cannot decide`;
- `core rule or goal` (tier I, the goal, a scope relaxation);
- `budget or token mode` (section 5 of RULES tier IV);
- `permission` (the tool's permission layer refused the action; see step 5);
- `collaborator or vendor` (a fact or an act that needs a person outside the program);
- `account` (a credential, a login, a subscription).

Everything else is decided here.

## 3. The steps

1. **State it:** the action, what it touches, `reversible`, `outward`.
2. **The user-only list:** if the action is on it, `ASK`, with a recommendation and the numbers. If it is on the NEVER list
   (a force-push to a public `main`; editing the four protected rnaseq-service files; cohort data into a tool; a home path
   into a repo; a rewrite of a sealed record), `DECLINE` without asking.
3. **Search:** tier I-III of RULES.md, tier IV, then the catalogue (section 4). Write the row you read in `rules_searched`.
4. **Decide:**
   - a rule or catalogue row covers it: `ACT` (or `DECLINE` if it says no), and name it;
   - nothing covers it and it is internal and reversible: `ACT`, labelled (C), and ADD a catalogue row;
   - nothing covers it and it is `outward` or not `reversible`: `DECLINE` is the default, recorded; only a REQUEST to take the
     action, with the reason it is needed for a goal, is an `ASK`;
   - a cohort fact: look it up in the delivery and the records, measure what can be measured, and write what stays unknown
     as a limit in the report. It is never a question that holds a lane (3b of 2026-11-10);
   - a design the cohort's names declare is used, with its unknowns labelled (3c);
   - a rule conflict: `ASK`, naming both rules.
5. **A permission block is not a rule question.** When the tool's permission layer refuses an action the rules allow, never
   route around it. The row is `ASK` with `decided_by = permission`, and the message gives the exact command the PI can run.
6. **An answered ASK becomes a catalogue row,** so the same question is never asked twice.

## 4. The catalogue of stated answers (grows; a question matching a row is never asked)

| class of question | answer | source |
|---|---|---|
| merge a wave into a tool's `main` | yes, when the gate passed and the verifier's verdict is PASS | tier II standing yes (2026-11-09) |
| merge a change meant to move promoted outputs | yes, when the run matches the difference predicted before submission; re-promotion stays the PI's | tier II decision 0b |
| delete outdated material at housekeeping | yes, logged; never records, ADRs, sealed runs, promoted results, ledgers, RUNLOGs | tier II housekeeping |
| delete a merged remote branch when the permission layer refuses | no: keep it, it costs nothing | D-002 (2026-11-10) |
| rewrite public history (a force-push) | never; attribute by `.mailmap`, correct by a dated addition | D-001 (2026-11-10) |
| resubmit a job the queue held or a node failed to start | yes, unchanged, with a dated RUNLOG note; the prediction stands | BLK-008, BLK-009 |
| re-pin a job's tool commit after a fix-up, or correct an input path its own precondition refused before any tool ran | yes, as a copy with a dated header note written before submission; the prediction stands | job 28b (W026); D-018 |
| carry a gating result over to a fixed commit by a code or AST diff | never; resubmit, unless the job's runtime-file manifest is unchanged (tier IV, 2026-11-10) | W011, W021 |
| choose a public cohort, a plugin format, a data-derived floor, a tool to convert | a design: decide, record, report | pass 0001 |
| a cohort fact the delivery does not state | look up, measure, then a stated limit in the report | D-003 (2026-11-10) |
| a cohort's design when only the library names declare it | use the declared design; label the unknowns | D-003 (2026-11-10) |
| an analysis the data cannot support (velocity without BAM) | not run; no vendor request unless a goal needs it | D-004 (2026-11-10) |
| run CellBender on single cells | never (rule 2) | the PI, 2026-10-02 |
| the SAMBO DE direction | treatment vs the declared control (slide 15) | pass 0001 |
| spend a held-out plugin through the maker | yes, one at a time, graded before the maker changes | tier II, pre-decider's reading 2026-11-09 |
| exceed the agent cap, or the budget | ask, with the numbers | tier IV (2026-11-10), `budget or token mode` |
| promote a run, re-promote a moved run | ask, with the numbers and a recommendation | tier III |
| an agent running on a model other than Opus 5.5 at max | stop it and launch a fresh one (model opus, effort max) on its branch; never resume it under another session model. A UI designer is the exception: Fable 5.2 | D-010; tier II (the PI 2026-11-10); D-026 (the PI 2026-11-11) |
| a job misses only on a file mode its own freeze step set, its data lines all held | set the mode by hand with a dated note saying who; the grade stays as the job wrote it; the next job goes on | D-027 (C) |
| who designs a user interface | a designer agent on Fable 5.2, for every UI item on the route; the design decided there, shown to the PI before any deploy | D-026 (the PI 2026-11-11) |
| deploy a verified platform wave (its merge into Lab, Studio or Service main publishes the live app) | ask the PI's go, per wave, with the verifier's verdict; the build itself never waits for it | BLK-005; `permission` |
| count floors or ceilings on single cells | derived from the called cells within the PI's declared bounds; the bound's lower end where no valley exists, said so | D-008 |
| edit the PI's own skills, settings or config outside the program's repositories | decline; fix the program's side | D-009 |

## 5. Where it is enforced

- `tests/test_autodev.py`: `decisions.tsv` is rectangular; every `ASK` names a user-only clause; every "Decisions needed"
  entry in STATE.md cites a `D-###` whose verdict is `ASK`; no `ASK` row's class matches a catalogue row's class string.
- Every brief (BRIEFS.md section 0) tells agents: a hand-back may carry a question only as a filled form; a hand-back
  question without the form is returned to the catalogue by the coordinator, never forwarded.
- The LOOP TICK re-runs the steps over STATE's "Decisions needed" and removes what a row decides.
- The VCC devharness carries the same v2 (`docs/round13/PRE_DECIDER.md` v2, `PRE_DECIDER.tsv`, its guard checks; 2026-11-10,
  the PI: "also improve the vcc pre-decider"). A lesson found in one copy is carried to the other (the amplifier).
