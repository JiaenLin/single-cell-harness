# STATE: where the program stands

Updated 2026-11-09T07:25Z by the coordinator. This is the living page. Every LOOP TICK that changes
something refreshes it, and so does every PERIODIC CHECK and every BLOCKER SWEEP.

## Verdict

**NOT HAPPY: 0 of 20 tests PASS (5 PARTIAL, 15 FAIL).** These are the grades of audit pass 0001, the
gap review of the harness and the four tools, and of pass 0001b, which reviewed the platform and graded
A6.2 and A6.3. The records are [`audits/0001-gap-review.md`](audits/0001-gap-review.md) and
[`audits/0001b-platform-review.md`](audits/0001b-platform-review.md). Their 59 + 24 gaps are in
[`ledger/gaps.tsv`](ledger/gaps.tsv).

## Scoreboard (GOALS.md layer 3; pass 0001)

| test | grade | the main reason (gap ids) |
|---|---|---|
| A1.1 one request, every stage | FAIL | The kernel runs none of the four tools: there is no adapter, and the `pbs` executor is refused. SAMBO ran stage by stage with glue at every boundary (GAP-001, GAP-002). |
| A1.2 the ten steps mapped | PARTIAL | No map exists, and differential abundance has never run (GAP-058, GAP-041). |
| A1.3 environments from main | FAIL | scProfile cannot build from `main` (GAP-038 → **W002**). scQC and scIntegrate leave packages unpinned (GAP-018, GAP-036). |
| A2.1 pre-declared reproduction | PARTIAL | Stages 1 and 3 reproduce. Stage 2's promoted run has never been reproduced (GAP-033). Stage 4 has no promoted run (GAP-055). |
| A2.2 documentation true | FAIL | Every tool has false docs (GAP-009, -022, -031 → **W003**, -037 → **W004**, -052). |
| A2.3 cold reproduction | FAIL | Never attempted (GAP-004). |
| A3.1 held-out cohorts | FAIL | C46 stopped after stage 1. Fixtures reach only scIntegrate's pipeline. The leak list misses factor levels (GAP-056, -007, -023, -008). |
| A3.2 design-aware | PARTIAL | DE contrasts levels in alphabetical order. Covariates are neither modelled nor refused (GAP-039, -040). |
| A3.3 assay rule sets | FAIL | scQC `main` schedules CellBender on single cells (GAP-017 = GAP-C01 → **W001**). The assay is unused in scAnno, scIntegrate and scProfile (GAP-029 → **W003**, -034 → **W004**, -050). |
| A3.4 scale | FAIL | No cohort of 1M cells or more. Three tools record no memory (GAP-016, -015). |
| A4.1 existing pool in one format | FAIL | Only CellChat is in the maker's layout (GAP-044). |
| A4.2 maker on new tools | FAIL | The maker has never converted a tool drawn from the catalogue (GAP-046). |
| A4.3 provenance of methods | PARTIAL | Provenance is free text, and only 3 of 9 plugins have exact pins (GAP-045). |
| A4.4 AI-native | FAIL | No catalogue that an agent can see (GAP-005). |
| A5.1 report from evidence | PARTIAL | The report is CellChat-only, and the review loop does not remove what it withdraws (GAP-047, -048). |
| A5.2 hypotheses | FAIL | No co-scientist (GAP-012). |
| A6.1 Harness UI | FAIL | No UI (GAP-013). |
| A6.2 Studio hand-off | FAIL | Lab's only automatic converter is a developer script nothing calls, and it guesses the roles. The run's provenance is dropped, and Studio shows no run (GAP-P09 → **W005**, P10, P19, GAP-014). |
| A6.3 Service takes single-cell requests | FAIL | A Cell Ranger or CeleScope delivery yields 0 samples, because only FASTQ is scanned. The bulk path holds: 126 checks (GAP-P01–P04). |
| A7.1 agents drive it | FAIL | No skill teaches a cold agent to run a cohort (GAP-003). |

## Lanes

| lane | repository | wave | status |
|---|---|---|---|
| QC | scQC | **W001 MERGED** (verifier round 2 PASS): scQC `main` cf0b750 → `a51c38a`, the single-cell rule set (rule 2 holds on `main`); `~/tools/scQC` deployed on `main` (HEAD.txt matches). **W006** running: PBS **782541**, scQC's own `--dbr-sd-sweep default,dbr,1` on the second cohort. The doublet over-call (GAP-C02) traces to D5's `dbr_sd = dbr` (a [0, 2×dbr] band that every call sits inside); the sweep measures the alternative for the PI's card. **W007** building: scQC's open defects on the new `main` (C03, C04, C06, C09, C10, GAP-022/024/025) plus a reproduction that compares every table (C08) and an organoid re-run. Next: environment pins (GAP-018, C05) | W006 gating (PBS); W007 building |
| ANNO | scAnno | W003: the assay governs the rules; the docs are true (GAP-029, GAP-031) | building |
| INT | scIntegrate | W004: species checked, assay recorded, first-cohort sentence removed, false statements fixed (GAP-034, GAP-037) | building |
| PROF | scProfile | W002: host-level environment lock, with no kernel edit (GAP-038) | building |
| HARN | single-cell-harness | held until B1 merges: B1 is editing the harness, and parallel edits would conflict. Next: GAP-002 → GAP-001 (the spine), GAP-005, GAP-011, GAP-007, GAP-008 | held (rule 5: a conflict costs more) |
| PLAT | studio, lab, service | **W005** (Lab `convert` command) built, `56fface`: 398/398 checks, the same sha256 twice, Studio's reader opens it. Verifying now; merging redeploys the live app. **W008** (Studio) building: true DESeq2 wording, docs marked shipped or planned, sentinels out of the cell types. Next: the run record (P10 in Lab, then P19 in Studio), the cross-repo contract test (P18), Service's single-cell mode in new files | W005 verifying; W008 building |
| AUDIT | — | W005's verifier | 1 running |
| BLOCKER | the harness (in its worktree) | B1: the inherited constraints (unreasonable designs, freezes, gates), recorded in ADR-0029 | running |

**Read 2026-11-09** (rule 5: these landed 2026-10-02 and were never read):
- PBS 720930 is IDENTICAL, as predicted.
- PBS 720932 (the C46 apply run) kept 53,534 of 59,701 cells. The floors were exact to the prediction. The removal percentage was missed, because of a doublet over-call (GAP-C02).
- The output of PBS 720931 was not located.

The graded results are in both cohorts' `stages/01_qc/RUNLOG.md` and in ADR-0027.

## Machinery (session-only; re-create on resume, see README)

| job | id | cron | created | expires |
|---|---|---|---|---|
| LOOP TICK | `3892e3da` | `7 * * * *` | 2026-11-09 | 2026-11-16 |
| PERIODIC CHECK | `c5bc935a` | `23 */6 * * *` | 2026-11-09 | 2026-11-16 |
| BLOCKER SWEEP | `94a2c268` | `41 */3 * * *` | 2026-11-09 | 2026-11-16 |

## Decisions needed from the PI

None of these blocks a running lane.
0. **A permission rule for deleting merged remote branches** (BLK-002). The classifier refused `git push origin --delete` on a merged branch. Merged branches are kept, which is harmless; housekeeping lists them instead.
1. **Promotions.**
   - C46 stage 1 (720932). The doublet over-call follows from D5's `dbr_sd = dbr`. When W006's sweep lands, you get a card: keep D5 and promote 720932 (53,534 cells), or set `dbr_sd` to scDblFinder's default and re-run apply. Both options come with their cell counts.
   - SAMBO stage 4, once a full DE/DA run exists.
   - "the PI promotes" (cohort records).
2. **C46's design facts.** What is C46 relative to H9, and what are `_1`/`_2`? This comes from the collaborator, and it blocks only C46 stage 4.
3. **Velocity on C46.** Only if you want it: it needs the vendor's BAM, because Cell Ranger outputs carry no spliced counts.

## Decided (2026-11-09)

| question | decided by | outcome |
|---|---|---|
| Merges into a tool's `main` | the PI: "yes , you have a standing yes, use predecider for decision" | A standing yes after gate PASS and verifier PASS (RULES tier II). |
| VCC rule 4 ("real"), as translated | the PI: "can skip this rule" | Rule 4 is dropped, and slot 4 stays empty. |
| Studio, Lab and Service | the PI: "yes include Studio, Lab and Service" | In scope, as lane PLAT: PLAT.1–3 and A6.3. |
| The scale bar and the maker bar | the PI: "this is goals we are developing towards. keep developing"; the pre-decider set the numbers (C) | A3.4: at least 1,000,000 cells. A4.2: at least 4 of 5. |
| The Harness UI's design | the pre-decider (a (C) layer-3 clause) | The report's words are the specification. The PI may redirect. |
| Inherited constraints | the PI: "remove unreasonalble designs ... enable the blocker remover" | B1 is running. The BLOCKER SWEEP runs every 3 h. Removals are recorded in ADR-0029. |
| **The held-out rule vs the goals** (pass 0001's PI decision 1) | the pre-decider: the rule's own purpose ("the only evidence the maker is general"), ADR-0022's plan to "migrate one at a time through the maker", and the PI's 2026-11-09 directive | The eight are spent through the maker, one at a time, DE and abundance first. Each migration is a blind test of the maker. Hand edits stay forbidden. |
| **SAMBO DE's sign convention** (pass 0001's decision 2) | the PI's own report, slide 15: "Aged vs Young \| Chow", "HFD vs Chow \| Young" | Each contrast is the treatment against its declared control. 48aaeba's missed tolerance stays a miss, and a new run is predicted before it runs. |
| Which plugin format is the standard (decision 5) | the pre-decider: a design decision, not a PI-owned one (RULES tier II) | A design wave compares the two formats and adopts one in an ADR. |
| Single-cell QC thresholds (decision 6) | the pre-decider; QC.1 ("count floors derived from the data"); cohort decisions D8/D9 | The tool develops data-derived floors for cells. The PI's declared values remain the cohort's decision, and the report shows both and who decided. |
| SAMBO stage 2 (decision 3, in part) | the pre-decider | Reproduce `bd45f5d` at its own commit first; that is a measurement. Promotion is asked only if it fails. |
| The audit-agent cap; the builder cap | the pre-decider (tier IV, rule 5) | 1 → 3 audit agents. The editing cap went 3 → 4 → 5, the last step for W005, a light Node project, on a 36 GB machine. |
| Service waves vs your uncommitted `rnaseq-service` work (82 lines in `scan.ts`, `request.ts`, `types.ts`, `test-scan.mjs`) | the pre-decider (protect the owner's work; the reviewer's own first move) | The single-cell mode is built in new files only and never touches those four files. |
| Where the run record lives (0001b, blocker B2) | the pre-decider (design) | Each stage appends to the object's `uns`; it never replaces (P20). Lab copies the record verbatim into an additive `meta.run`, and Studio shows it in a Run card. |
| Where Lab conversion runs (0001b, blocker B3) | the pre-decider (rule 3 covers cluster compute only) | On the workstation, as Lab was designed. |
