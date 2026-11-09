# autodev: the autonomous development program

The program that moves the family toward [`GOALS.md`](../GOALS.md): `single-cell-harness`, the four tools
`scQC`, `scAnno`, `scIntegrate` and `scProfile`, and the platform `scrnaseq-studio`, `scrnaseq-lab` and
`rnaseq-service`. The PI started it on 2026-11-09. Its rules are in [RULES.md](RULES.md), and its state
is in [STATE.md](STATE.md). [BRIEFS.md](BRIEFS.md) holds the role briefs, and [ledger/](ledger/) the
append-only records. It borrows the VCC development harness's core rules 3 and 5 (the PI skipped rule 4)
and its practices (see [RULES.md](RULES.md) tiers I and IV).

## Start here (a new session, or after a restart)

1. Read [STATE.md](STATE.md): the scoreboard, the running waves, the blockers and the decisions needed.
   Then read the newest rows of [`ledger/waves.tsv`](ledger/waves.tsv) and [`ledger/blockers.tsv`](ledger/blockers.tsv).
2. Re-create the reminders below with CronCreate. They live only in the session that made them and
   expire after 7 days. Run `CronList` first.
3. Resume any wave marked `running` in `waves.tsv`. Its row names its branch and PBS ids. Read any landed
   result by its registered prediction before starting anything new.

## The design in one paragraph

One **coordinator** (the main Claude Code session) owns the ledgers, the merges, the cluster deploy
lanes and the PI's questions. It runs a loop. An **audit** pass grades every GOALS.md layer-3 test
and writes the gap register. The coordinator turns the open gaps into **waves**, each one registered
change to one repository, and short-lived **development builders** build them in parallel in their
own clones. Each wave goes through the **gate** (rule 1: suite, leak guard, fixture, pre-declared PBS
reproduction). A fresh **verifier** then checks the wave's claims against its evidence before the wave
is merged. When a batch of waves has landed, a fresh **audit** pass re-grades everything. The loop runs
until the audit says **HAPPY**. Whenever anything waits, the **blocker remover** clears it.
**Housekeeping** keeps the repositories and the cluster lean on a timer.

## The roles

| role | who | owns | brief |
|---|---|---|---|
| coordinator | the main session | the ledgers, STATE.md, wave planning, merges, cluster deploys and PBS submission, the PI's questions | this file |
| development teams | one short-lived builder per wave; lanes **QC**, **ANNO**, **INT**, **PROF**, **HARN** (one per repository) and **PLAT** (Studio, Lab and Service; one wave per repository at a time) | one registered wave on one branch: code, tests, the reproduction `.pbs` with its prediction, the hand-back | [BRIEFS §1](BRIEFS.md#1-development-builder) |
| audit team | fresh, read-only agents: a **verifier** per wave, an **auditor** per full pass | the grades, the gap register, the HAPPY / NOT HAPPY verdict | [BRIEFS §2](BRIEFS.md#2-audit-team) |
| blocker remover | the coordinator for quick blockers; a short-lived agent for deep ones | `blockers.tsv`: diagnosis, removal, or the PI's decision prepared | [BRIEFS §3](BRIEFS.md#3-blocker-remover) |
| housekeeper | the coordinator, on a timer | `housekeeping.tsv`: the rule-5 check, deletions, docs and memory current | [BRIEFS §4](BRIEFS.md#4-housekeeping-pass) |

## The loop

```
AUDIT pass N ──► gaps.tsv + verdict ──► HAPPY? ── yes ──► stop; report to the PI
                                          │ no
                                          ▼
PLAN: the coordinator picks waves in unblocking order, one per idle lane;
      each is registered in waves.tsv with goal ids, acceptance check and prediction
                                          ▼
BUILD: builders, in parallel, in isolated clones ──► branch pushed + hand-back
                                          ▼
GATE (rule 1): suite · leak guard · fixture on the real CLI · `sch conform` / `sch dev`
      · PBS reproduction whose prediction was written before submission (the coordinator deploys
        and submits: one lane per tool)
                                          ▼
VERIFY: a fresh verifier checks the hand-back's claims against the evidence
                                          ▼
MERGE (the PI's yes until a standing yes exists) ──► gaps.tsv / STATE.md updated
                                          ▼
next AUDIT pass when ≥ 3 waves have merged since the last pass, or 24 h have passed with ≥ 1 merge

BLOCKER REMOVER: on demand, whenever any step waits.  HOUSEKEEPING: every 6 h.
```

**HAPPY** means the latest full audit pass grades every in-scope GOALS.md layer-3 test PASS, or the
PI has deferred it by name, and lists no open gap of size M or larger. A PARTIAL or UNKNOWN grade is
NOT HAPPY. The audit may add gaps, but only with evidence tied to a goal id. A finding that moves no
goal is recorded as LEAN and never blocks HAPPY (rule 5, no trivial tweaks). The PI can override any
verdict.

**A wave** is the unit of development: one repository, one branch (`autodev/W###-slug`), one or more
goal ids, one acceptance check, and one prediction. A wave with no goal id breaks rule 5. Each wave
gets a row in `waves.tsv` with status `registered`, `building`, `gating`, `verifying`, `merged`,
`held` or `failed`. A failed wave stays recorded as failed. Its gap is then re-planned, never
silently retried.

## The reminders (session-only; re-create on every resume)

The prompts are verbatim as created on 2026-11-09, except that the checkout's path is written as
`<HARNESS>` ([BRIEFS.md](BRIEFS.md)). Background agents and Monitor watches re-invoke the
coordinator as soon as they finish, so the tick is the fallback for state nothing else announces: PBS
jobs and lanes that have gone idle.

| name | cron (local) | prompt |
|---|---|---|
| LOOP TICK | `7 * * * *` | "autodev LOOP TICK (<HARNESS>/autodev/README.md). Quick and non-blocking: (1) read every landed result (builder hand-backs, PBS jobs named in autodev/ledger/waves.tsv) by its registered prediction, then gate, verify or merge as the loop says; (2) for every idle lane with an open, unblocked gap in autodev/ledger/gaps.tsv: register the next wave and start one builder (within the RULES.md tier-IV caps; brief from BRIEFS.md §1); (3) for any wave waiting on something: run the blocker remover (BRIEFS.md §3); (4) if the audit trigger is met (≥ 3 waves merged since the last pass, or 24 h with ≥ 1 merge), start a full audit pass (BRIEFS.md §2b). Log each change in the ledgers and update autodev/STATE.md. No blocking questions. Report only what changed." |
| BLOCKER SWEEP | `41 */3 * * *` | "autodev BLOCKER SWEEP (every 3 h; the PI 2026-11-09: "it is very important to remove unreasonalble designs, and remove blockers and constrains from previous single cell harness family. enable the blocker remover"; <HARNESS>/autodev/BRIEFS.md §3). (1) List everything waiting: waves not moving (autodev/ledger/waves.tsv), gaps whose blocked_by is not "none" (gaps.tsv), open rows of blockers.tsv, decisions pending in STATE.md. (2) For each: remove it now if an agent can (environment pins, queue routing, stale checkouts, flaky or environment-bound tests, an inherited design that protects no goal); otherwise prepare the PI's decision card. Start a blocker-remover agent (BRIEFS §3) for anything that needs more than a few minutes. (3) The inherited-constraints register (pass B1 and later): apply its next REMOVE items, and queue its tool or platform changes as waves. Log each action in blockers.tsv, update STATE.md, and report only what changed." |
| PERIODIC CHECK | `23 */6 * * *` | "autodev PERIODIC CHECK (every 6 h; <HARNESS>/autodev/BRIEFS.md §4; the PI 2026-11-09: "a regular housekeeping to keep project lean and efficient"). One pass: (1) RULE 5: idle lanes, unread results, stalled or failed PBS jobs (one batched read-only ssh), waves waiting, trivial work; act at once. (2) LEAN: delete merged autodev/* branches, finished builders' clones and worktrees, and our own cluster scratch older than 14 days; delete superseded job scripts and stale docs only when no record cites them; never delete records. (3) DOCS: STATE.md current; commit and push the harness's main. (4) MEMORY: verify the notes against STATE.md; keep MEMORY.md lean. (5) GITHUB: every running wave's branch is pushed. Log each action in autodev/ledger/housekeeping.tsv. Report only what changed: per lane, then the fixes, then the decisions needed." |

## Records

| file | holds |
|---|---|
| [STATE.md](STATE.md) | the living page: scoreboard, lanes, blockers, decisions needed |
| [ledger/gaps.tsv](ledger/gaps.tsv) | the gap register: one row per gap, updated by each audit pass (a status change is a new row) |
| [ledger/waves.tsv](ledger/waves.tsv) | every wave: goal ids, repository, branch, prediction, PBS ids, outcome |
| [ledger/audits.tsv](ledger/audits.tsv) | every audit pass: grades per layer-3 test, verdict |
| [ledger/blockers.tsv](ledger/blockers.tsv) | every blocker: what, evidence, removed by whom and how, or the PI's decision asked |
| [ledger/housekeeping.tsv](ledger/housekeeping.tsv) | every housekeeping action, including each deletion |
| [`../docs/adr/0028-the-goals-and-the-loop.md`](../docs/adr/0028-the-goals-and-the-loop.md) | why the program exists, and what it gives up |

The cohort projects keep their own records (`stages/NN/{PROTOCOL,DECISIONS,RUNLOG}.md`). A wave's
reproduction job is authored in the cohort's `stages/NN/jobs/` on the workstation and pushed, as
LAYOUT.md requires. `tests/test_autodev.py` keeps the ledgers well-formed and every goal id real.
