# ADR-0017 — the run drives its own writing: one driver, one selection, one carry-in

**Date** 2026-09-13. **Status** accepted; executing. **Follows** ADR-0015 (one spine), ADR-0016
(the plan carries the call). **Rules in force** the four top rules (a plugin is maker output;
the eight are held out; mechanism and the agentic layer are fixed in place; end to end is
cellchat), the HPC rules (H1: nothing authored on the cluster, every tool invocation through
`qsub`, no compute on a login node, runs under `~/projects/SAMBO/runs/scprofile/04_profile/`),
and scProfile's DEVELOPMENT.md. **The brief for this round**, in the user's words: analyse
scProfile layer by layer, find what failed to drive a cold agent end to end - the writing above
all - and make it self-driving; a selection of figures for the agent to read is proper; trim or
adjust what is unreasonable; add no step to scProfile.

## Context — what a cold agent meets, layer by layer

The evidence is three blind conversions (docs/blind/0002, 0003), five reproductions of the real
cohort (ADR-0016), and the maker's own reading of the newest sealed run,
`20260912T163648Z__scprofile-344993d__04_profile__plan` (PBS 710985), through
`sch dev convert status --run`. The build phase drives a cold agent to 8 of 8 alone (0003). The
test phase has never been driven by anyone past `promised`: on every run the maker read,
`audited`, `looked_at`, `written` and `delivered` OWE, and no agent has been asked to clear them.
Reading what they say, and what the run already holds, finds why an agent could not:

1. **Two drivers for the agent's half, and they disagree.** `scprofile agenda` (the run's task
   list, written by the job as its last act: run, account, brief, look, write, carry, defend)
   and the loop's stations 7-9 (`looked_at`, `written`, `delivered`, read by the maker) each
   name a command per step, and the commands differ: the agenda carries the section in with
   `scprofile run --section` (a new run), the station with `scprofile paper --write` then
   `--render` (into the run); the agenda's brief is `scprofile write` (WRITING_BRIEF.md, the
   design's questions, the contrasts, the figure list, the skill and the template), the
   station's is `scprofile paper --brief` (a second brief, composed differently). ADR-0015 left
   "two oracles with a stated boundary"; the boundary is the seam a cold agent falls through.
2. **Station 8 cannot pass on any run.** It reads the run-level claims ledger and looks for
   `report/paper.html`; every plugin's claims live in `kernels/<plugin>/PAPER_CLAIMS.<plugin>.jsonl`
   and its page at `report/<plugin>_paper.html`. The newest run carries 24 composed claims and a
   rendered page, and the station says "no claim written from the newest run".
3. **Station 9 cannot pass on any run.** It resolves `report/<plugin>_paper.html` under
   `kernels/<plugin>/`, where the reporter never writes it. It names the page missing on a run
   that has it.
4. **Two selections of figures, two definitions of a kind.** Station 7 asks for every kind's
   largest and smallest instance (149 of 945 on this cohort) and prints eight names then "and
   141 more"; the agenda asks for the figures the paper cites (90, of which 62 outstanding);
   `review --shards` defaults to the paper's list; `--per-kind` samples by `review.kind_of`,
   the station counts by its own `_kind`. An agent that does exactly what one says is still told
   by the other that nothing was done.
5. **A sealed run cannot be written to.** The seal (`chmod a-w` on every file) is right: a run
   is the bytes its commit produced. But the writing layer appends to ledgers and rewrites the
   section and the page, so on the run it is asked about, every writing command dies on the
   first file. `jobs/writing_sambo.pbs` already answers this for the reporter - a writable
   replay of the sealed run, heavy objects excluded, under its own run key - and nothing said
   the writing phase should use the same answer. The agenda tells the agent to bring the
   figures across and record looks "against the run directory", which for an agent on the
   workstation is a directory it cannot write.
6. **The reviewer is unspecified.** `paper --round` records a verdict and who gave it, and
   nothing keeps the author of a claim from being its reviewer; PAPER_TEST.md's own list says a
   project with no reviewer has no test. For agents this is the whole test: a claim survives a
   second agent that was given the figures and told to refute it, or it does not.
7. **`measure` is a dead end.** On a run whose instances shared one job it OWES ("records no
   memory mode") and its stage names no way out; the two memory terms cannot be fitted from such
   a run and the status says so forever.
8. **The build's status reads complete while the repository's validator refuses** (per-unit
   plugin, no `report.unit_metrics`; 0003). The `truth:` column says three keys are
   validator-established; the validator itself is never run by the status.
9. **The tool's own seal of an exported tree reads `commit=unidentified`.** The export carries
   `HEAD.txt` and no git.

What is NOT weak: the plan (ADR-0016), the run's own status contract, the reporter's pages, the
composed section and claims (the tool's measured skeleton, `author=composed`, which is exactly
the starting point a writing agent needs), the review ledger's three properties, and the
figure audit. The failure is between the pieces, not in them.

## Decision

**One driver.** The maker's `sch dev convert status --run RUNDIR` remains the one answer to "is
this plugin finished", and the run's agenda becomes the same list in the run's own words: every
task on the agenda names the command the corresponding station's `finished_by` names, and
nothing else. Concretely:

- **One brief.** `scprofile write` (WRITING_BRIEF.md) is the brief. `scprofile paper --brief`
  prints that file, writing it first if the run has none; `paper.brief()`'s own composition goes.
- **One carry-in.** The section enters the run with `scprofile paper --write <file>` and is
  rendered with `--render`. `scprofile run --section` goes; the agenda's carry task names the
  paper command.
- **One selection, one kind.** `review.kind_of` is the definition of a kind; the loop's `_kind`
  goes. The set an agent reads is `review.scan_set`: every figure the paper numbers
  (`FIGURES.txt`) plus, for every kind the paper does not show, that kind's largest instance -
  139 of 945 on this cohort. Station 7 counts it, `review --shards` splits it, the agenda's look
  task names it, and `--all-figures` remains the audit of everything drawn. The "largest and
  smallest" pair is trimmed to the largest: the paper's own instances already cover the
  per-contrast layouts, and one instance per kind is what a look establishes about a kind.
- **Stations 8 and 9 read per plugin**, the ledger under `kernels/<plugin>/` and the page under
  the run's `report/`, as the reporter writes them.
- **A round needs a reviewer who is not the author.** `paper --round` refuses a verdict whose
  reviewer is empty or equal to the claim's author. Composed claims have the author `composed`,
  so any named agent may review them; an agent's own claims need a second agent. No new step:
  the same command, one more refusal, the one PAPER_TEST.md already names as the gap.
- **The written layer lives in a writing run.** A sealed run is never written to. The agent
  works on a replay - the run's light half, heavy objects excluded, files writable, under the
  same run key on the agent's side - and the written layer (the review ledger, the claims, the
  section, the rendered section and panel) is sent back to the cluster as
  `<stamp>__scprofile-<commit>__04_profile__written`, a run directory holding the replay, graded
  and sealed by a job (`jobs/writing_seal.pbs`). The agenda's pbs-mode text says exactly this.
- **`measure` names its way out**: a `finished_by` saying a run whose instances shared one
  process records no per-instance memory, that the two terms come from a run with one instance
  per process, and that until then they stay undeclared and the allocator's conservative default
  applies - which is the tool's existing rule for an absent declaration.
- **The build's status runs the validator.** The `judgement` stage declares
  `command: scprofile validate {name}`; the maker runs a BUILD stage's command without `--run`
  (a test stage's still verifies a run), and the stage reads done only if the validator exits
  0. Not a
  new stage: the judgement is still the agent's, and the validator says whether it is well formed.
- **The seal reads `HEAD.txt`** where there is no git.

**The proof is a fourth blind record**, `docs/blind/0004-writing.md`: a cold Sonnet agent given
the replay of PBS 710985 on the workstation, both repositories, the plugin-maker and
result-section skills, told only to finish the run's test phase through the maker's status; a
second cold agent as the reviewer of its claims. Predictions before either starts. What holds
and what does not is the record; a failed prediction is a finding to fix in the maker or the
host, never a reason to help the agent by hand.

## What must not be done

- No new stage, station, command or file kind in scProfile. Everything above is a deletion, a
  merge of two things into one, or a refusal added to a command that exists.
- No hand-edit of `kernels/cellchat.py` (top rule 1): station 6b's 43 text collisions in the
  plugin's own matplotlib panels are the plugin's debt, recorded here, and a cold agent in the
  author's role may fix them in its next build; this round does not.
- No writing into a sealed run; no run made on a login node; every job through `qsub` with
  `rule-one: no-removal` and `validate.sh` first.
- No claim in a skill or a record that states a count the declaration owns.

## Steps

0. This record. **Done.**
1. The two debts: the validator on the judgement stage (harness `run_stage` for `{run}`-free
   commands; DEVPOINTS `judgement.command`); `status.commit()` reads `HEAD.txt`. Tests first.
2. Stations 8 and 9 read per plugin; `loop_stations._kind` goes; `review.kind_of` is the kind;
   `review.scan_set` is the selection; station 7 counts it and prints the command that lists
   it; `review --shards` splits it by default for `--plugin`; the agenda's look task counts it.
3. One brief and one carry-in: `paper --brief` prints WRITING_BRIEF.md; `run --section` goes;
   the agenda's carry task, the result-section skill and PAPER_TEST.md name `paper --write` and
   `--render`.
4. The reviewer rule in `paper.review`; `measure`'s `finished_by`; the agenda's pbs-mode text
   for the replay; the loop's `finished_by` texts brought into line (DEVPOINTS).
5. Harness: `jobs/writing_seal.pbs` + submitter (the written run from the sealed run and the
   pushed written layer; grades `looked_at`, `written`, `delivered` through the maker; seals);
   the plugin-maker skill's test-phase section says the replay flow in five lines.
6. Gates: both suites green; `sch dev rules` 4 held; the maker's `status --run` on the replay
   of 710985 reads `written` and `delivered` as the run's real state (24 composed claims,
   undefended; the page present; the ledger absent), not "no claim written".
7. Blind 0004: predictions, the replay pulled, the writer agent, the reviewer agent, the written
   run pushed and sealed, the record filled, the memory updated.

## Status

| step | state | commits | notes |
|---|---|---|---|
| 0 record | done | this commit | |
| 1 the two debts | done | harness 8d2321d; scProfile 6a3f5b3 | a build stage's command runs on every status; `judgement` declares `scprofile validate`; the seal reads HEAD.txt |
| 2 stations 7-9, one kind, one selection | done | scProfile af5c48f | `review.scan_set` (139 of 945 on the cohort); station 8 per plugin; station 9 at the run's report dir; the loop's `_kind` gone |
| 3 one brief, one carry-in | done | scProfile a3ce98f | `paper --brief` prints WRITING_BRIEF.md, which gained the panel's headings and the contrasts' references; every text names `paper --write`; `run --section` stays for a rerun |
| 4 reviewer rule, measure, agenda text | done | scProfile 8e64eba | a round needs a named reviewer who is not the author; `measure` names its way out; the agenda's pbs look task is the replay; the stages' `finished_by` in one vocabulary |
| 5 the writing run's job, the skill | done | harness: this commit | `jobs/writing_seal.pbs` + `submit_writing_seal.sh --prepare/--seal`; the skill's test-phase paragraph |
| 6 gates on the replay of 710985 | | | |
| 7 blind 0004 | | | |
