# STATE: where the program stands

Updated 2026-11-09T05:5xZ by the coordinator. The living page. Refreshed by every LOOP TICK that changes
something and by every PERIODIC CHECK.

## Verdict

**NOT HAPPY.** No full audit pass has graded the family yet. Pass 0001, the gap review, is running.

## Scoreboard (GOALS.md layer 3)

| test | grade | evidence | test | grade | evidence |
|---|---|---|---|---|---|
| A1.1 one request, every stage | — | pass 0001 running | A4.1 existing pool in one format | — | |
| A1.2 the ten steps mapped | — | | A4.2 maker on new tools | — | |
| A1.3 environments from main | — | | A4.3 provenance of methods | — | |
| A2.1 pre-declared reproduction | — | | A4.4 AI-native | — | |
| A2.2 documentation true | — | | A5.1 report from evidence | — | |
| A2.3 cold reproduction | — | | A5.2 hypotheses | — | |
| A3.1 held-out cohorts | — | | A6.1 Harness UI | — | |
| A3.2 design-aware | — | | A6.2 Studio hand-off | — | |
| A3.3 assay rule sets | — | | A7.1 agents drive it | — | |
| A3.4 scale (set by PI) | — | | | | |

## Lanes

| lane | repository | wave | status |
|---|---|---|---|
| QC | scQC | — | waiting for pass 0001 |
| ANNO | scAnno | — | waiting for pass 0001 |
| INT | scIntegrate | — | waiting for pass 0001 |
| PROF | scProfile | — | waiting for pass 0001 |
| HARN | single-cell-harness | — | waiting for pass 0001 |
| PLAT | scrnaseq-studio, scrnaseq-lab, rnaseq-service | — | waiting for pass 0001b |
| AUDIT | — | pass 0001 (the harness and four tools); pass 0001b (the platform) | both running |

## Machinery (session-only; re-create on resume, see README)

| job | id | cron | created | expires |
|---|---|---|---|---|
| LOOP TICK | `3892e3da` | `7 * * * *` | 2026-11-09 | 2026-11-16 |
| PERIODIC CHECK | `c5bc935a` | `23 */6 * * *` | 2026-11-09 | 2026-11-16 |

## Blockers

None recorded yet.

## Decisions needed from the PI

None open.

## Decided (2026-11-09)

| question | decided by | outcome |
|---|---|---|
| Merges into a tool's `main` | the PI: "yes , you have a standing yes, use predecider for decision" | standing yes after gate PASS and verifier PASS (RULES tier II) |
| VCC rule 4 ("real"), as translated | the PI: "can skip this rule" | rule 4 dropped; slot 4 empty (RULES tier I) |
| Studio, Lab and Service | the PI: "yes include Studio, Lab and Service" | in scope, lane PLAT; GOALS PLAT.1–3 and A6.3 |
| The scale bar and the maker bar | the PI: "this is goals we are developing towards. keep developing"; the pre-decider set the numbers (C) | A3.4: ≥ 1,000,000 cells through A1.1; A4.2: ≥ 4 of 5 |
| The Harness UI's design | the pre-decider (a (C) layer-3 clause, not a PI rule) | the report's words are the specification; the PI may redirect at any point |
