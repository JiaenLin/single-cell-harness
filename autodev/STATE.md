# STATE: where the program stands

Updated 2026-11-10T01:38Z by the coordinator. This is the living page. Every LOOP TICK that changes
something refreshes it, and so does every PERIODIC CHECK and every BLOCKER SWEEP.

**RESUMED 2026-11-10T01:3xZ (the PI: "WE HAVE TOKENS. GO!"; BLK-010 closed)** under the 2026-11-10 block of RULES.md:
2 builders (W020, W029 resumed from their transcripts), 1 verifier (the harness batch W026 + W024), token mode LIMITED
(8 M output a day; only the PI's words switch it), the PBS mirror watching 783740.

## Verdict

**NOT HAPPY: 0 of 20 tests PASS (9 PARTIAL, 11 FAIL)** at audit pass 0003; **score: pending pass 0004** (the mean of the 20 measured scores, GOALS.md "Layer 3, scored"; 3 of 20 measured by the coordinator on 2026-11-10: A1.1 0.25, A3.4 0, A4.2 0)
([`audits/0003-audit.md`](audits/0003-audit.md)). Pass 0002 had 7 PARTIAL and 13 FAIL. A1.1 moved FAIL → PARTIAL (stage 1 through
the harness) and A4.4 FAIL → PARTIAL (`sch catalogue`). All 9 closures claimed since pass 0002 were re-checked and hold, and
GAP-033 is closed from 783148's own files. The register holds 161 gap ids: 91 open, 39 in a wave, 31 closed. 46 of the
gaps not closed are size M or larger.

## Scoreboard (GOALS.md layer 3; pass 0003)

| test | grade | the main reason (gap ids) |
|---|---|---|
| A1.1 one request, every stage | PARTIAL | Stage 1 runs through `sch mount qc@scqc` with the pbs executor, AS PREDICTED (PBS 782817, 782922). Stage 2 runs through `sch mount anno@scanno` AS PREDICTED twice (W026: PBS 783280, and 783363 at the fix-up); its merge waits on a fix-only re-check. No adapter for stages 3-4, and no driver (GAP-001). |
| A1.2 the ten steps mapped | PARTIAL | No map of the ten steps. Step 2 on nuclei runs only outside the tools (GAP-C49). Differential abundance has never run, and step 9 has nothing. |
| A1.3 environments from main | PARTIAL | Only scProfile builds from main on a fresh prefix (782609). scQC's fresh build reproduced stage 1 in every value but missed its interpreter pin (782920); job 34 is gating (GAP-107). |
| A2.1 pre-declared reproduction | PARTIAL | Stages 1 and 2 reproduce; stage 2's promoted run reproduces at its own commit (783148). Stage 3's harmony spread broke (782882; W025). Stage 4 and C46 have nothing promoted. |
| A2.2 documentation true | FAIL | A seeded draw of 96 doc claims found 10 false, in 6 of 8 repositories (GAP-115..117, plus pass 0002's). |
| A2.3 cold reproduction | FAIL | Never attempted, and the harness suite fails on any fresh clone (GAP-111, GAP-004). |
| A3.1 held-out cohorts | FAIL | C46 is still at stage 1. Fixtures reach the pipeline in 1 of 4 tools. The leak guard was nearly blind: 802 leaks across the tools (W024). |
| A3.2 design-aware | PARTIAL | scProfile's main kernels are unchanged; W013 fixes DE's direction on a branch only. |
| A3.3 assay rule sets | PARTIAL | Three tools have per-assay rules. scProfile changes only captions, and the Service's main has no assay. |
| A3.4 scale | FAIL | No cohort of 1M cells or more (W027 choosing one). Three tools record no memory (GAP-015). |
| A4.1 existing pool in one format | FAIL | 1 of 9 plugins is in the maker's layout (W013, de, not merged). The cluster dev suite has not run since 2026-10-02. |
| A4.2 maker on new tools | FAIL | No draw rule and no conversion (GAP-046). |
| A4.3 provenance of methods | PARTIAL | The catalogue shows no DOI for 9 of 9 plugins and an exact pin for 3 of 9 (GAP-045). |
| A4.4 AI-native | PARTIAL | `sch catalogue` lists 22 plugins. A scProfile plugin cannot yet be planned or mounted through `sch`. |
| A5.1 report from evidence | PARTIAL | paper.py:799-800 still prints withdrawn claims; CellChat only (GAP-047, GAP-048). |
| A5.2 hypotheses | FAIL | No co-scientist code (GAP-012). |
| A6.1 Harness UI | FAIL | No UI code (GAP-013). |
| A6.2 Studio hand-off | FAIL | Lab and Studio main are unchanged (W005, W008 and W017 are held for the PI's deploy). scIntegrate's emit.py:138 drops earlier stages' records (GAP-P20). |
| A6.3 Service takes single-cell requests | FAIL | Service main is unchanged. It is PARTIAL once W009 and W015 are deployed; the harness intake is still missing (GAP-P06). |
| A7.1 agents drive it | FAIL | No skill runs a cohort (GAP-003). |

## Lanes

| lane | repository | wave | status |
|---|---|---|---|
| QC | scQC | **W014 MERGED** (`main` `98504bd`): scQC builds its three environments on a fresh prefix from its own locks, and stage 1 on them is IDENTICAL to the reference (job 34, PBS 783151, AS PREDICTED on every line). The CellBender checkpoint error persists in both environments (GAP-C49). **W020** (19 constraints) building again (resumed 2026-11-10T01:3xZ at B1-042) | merged; 1 building |
| ANNO | scAnno | **W011 MERGED** (`main` `d0ee926`). **W018 DONE: the promoted stage 2 reproduces at its own commit** (PBS 783148, `bd45f5d`): IDENTICAL on 1,464 obs columns over 31 objects, the joint object, the scope record and every table, with inputs and environment measured equal first (GAP-033 closed). **W021 MERGED** (`main` `68233f0`): scAnno's 18 inherited constraints removed or trimmed; `scanno build-markers` rebuilds SAMBO's corpus row for row and `scanno tree propose` drafts a tree (GAP-028 closed); stage 2 IDENTICAL on SAMBO's path (PBS 783253, 783345) | merged x2; done |
| INT | scIntegrate | **W012 + W025 held:** job 30 (PBS 783282) MISSED on LISI's unseeded subsample for `none` (0.0019 > 1e-3). Harmony's own lines held, and the cause is fixed (threaded KMeans). Next, round 2: make LISI reproducible (GAP-C67), then one re-gate. GAP-C65 and GAP-C12 (harmony on the fixture) follow | held |
| PROF | scProfile | **W002 MERGED** (`f5175ea`). **W013**: `de` runs through the maker in the declared-control direction, AS PREDICTED in three runs (bit-identical to 720548). Fix-up 5 (`b39ca4a`) is gated by its job: PBS 783296, 783344, 783347 and 783349 never ran (long-queue starts held, BLK-009); resubmitted unchanged and unpinned as **PBS 783740** (2026-11-10T01:37Z), watched by the mirror. Its ladder line with merged W019 is verified green. **W023** queued | gating; 1 queued |
| HARN | single-cell-harness | **W010, W016 and W019 MERGED** (`main` `70c25b9`): stage 1 through the harness; one plugin format plus `sch catalogue`; the maker's six defects from the de conversion (`agree` judges every output, excusing only a tool's declared execution record). **W026**: SAMBO stage 2 through the harness AS PREDICTED at the fix-up too (job 28b, PBS 783363); the merge waits on the fix-only re-check of `f640455`. **W024**: the merge waits on the fix-only re-check of `ca4825f`. **W029** building again (resumed 2026-11-10T01:3xZ). The harness batch (W026 `f640455` + W024 `ca4825f`) is under its one fix-only re-check | merged x3; 2 verifying (one batch); 1 building |
| PLAT | studio, lab, service | **DEPLOYED by the PI's go:** Lab W005 (`51a00fa`), Studio W008 (`1d591f9`), and Service W009 + W015 (`997d132`). W017 (Lab) and W028 (Studio) are now stacked on deployed mains. Under the throttle, W017 gets at most one more fix-only re-check (`243783f`). The W028 verifier resumes after the harness batch (one audit agent at a time) | deployed x4; 2 open |
| AUDIT | — | **Pass 0003 done: NOT HAPPY, 0/20 (9 PARTIAL, 11 FAIL)**. Merged since: **W014, W019, W021**. Pass 0004 is due: it starts when the harness batch's verifier hands back (one audit agent at a time), and writes scores.tsv for all 20 tests | due |
| BLOCKER | — | **Sweep 14:11Z:** nothing removable is waiting. The B1 register's 68 rows are all in waves (W020 building, W021 verifying, W022 and W023 queued behind their repositories), and the checkouts each follow their gating wave. New: GAP-C62 (the commit hook runs the whole suite on records-only commits). **BLK-010 CLOSED 2026-11-10T01:3xZ** (the PI lifted the limit). **BLK-009:** W013's job resubmitted unchanged and unpinned as PBS 783740; the mirror reports its start, hold or seal. Nothing waits on the PI | watching |

**Read 2026-11-09** (rule 5: these landed 2026-10-02 and were never read):
- PBS 720930 is IDENTICAL, as predicted.
- PBS 720932 (the C46 apply run) kept 53,534 of 59,701 cells. The floors were exact to the prediction. The removal percentage was missed, because of a doublet over-call (GAP-C02).
- The output of PBS 720931 was not located.

The graded results are in both cohorts' `stages/01_qc/RUNLOG.md` and in ADR-0027.

## Machinery (session-only; re-create on resume, see README)

| job | id | cron | created | expires |
|---|---|---|---|---|
| LOOP TICK | `2635520c` | `7 */3 * * *` (the 2026-11-10 prompt: mirror files first, the pre-decider sweep, 2 builders, 1 verifier per batch) | 2026-11-10 | 2026-11-17 |
| PERIODIC CHECK | `9b5a55ca` | `23 */6 * * *` (adds the budget meter) | 2026-11-10 | 2026-11-17 |
| BLOCKER SWEEP | `8fbcd2dc` | `41 */3 * * *` | 2026-11-10 | 2026-11-17 |
| the PBS mirror | background task `bq07hdiji` | `bash autodev/tools/pbs_mirror.sh <scratchpad>/pbs 300`; watch.tsv holds 783740 (W013) | 2026-11-10 | with the session |
| the verdict Monitor | `bmjowp93d` | `bash autodev/tools/monitor_verdicts.sh <scratchpad>/pbs`, 30 min, re-armed at expiry | 2026-11-10 | re-arm |

## Decisions needed from the PI

None. The four that were listed here (2-5) were decided by the pre-decider on 2026-11-10, below.

## Decided (2026-11-10, by the pre-decider; the PI: "review rules and goals and decide")

- **2026-11-10, the PI: "agree, proceed with all"** on the diagnosis's seven changes
  ([audits/DIAGNOSIS_20261110_vs_vcc.md](audits/DIAGNOSIS_20261110_vs_vcc.md)), and "for the predecider, improve it".
  Done the same day, in RULES.md's 2026-11-10 block: agent use as VCC's row (2 builders; one verifier per merge batch per
  repository; 2 rounds then a gap); the measured score per test and HAPPY = mean >= 0.9 with no test < 0.5 (D-006);
  the PBS mirror and the verdict Monitor (`tools/`); the manifest rule for fix-ups; the budget (provisional: 8 M output a
  day, 40 M a week, 1.5 M a wave; token mode LIMITED; D-005 holds the PI's number); lanes in turn; the pre-decider v2
  ([PRE_DECIDER.md](PRE_DECIDER.md): the form, `ledger/decisions.tsv`, the catalogue, the test).
- **2, commit `f488621` authored `t <t@t>`: left as it is, and attributed by `.mailmap`.** Rewriting it needs a force-push
  to a public `main`. Declining that is the default and needs nobody (RULES tier IV, the pre-decider's step 3a). `.mailmap`
  maps it to Jiaen Lin, so `git log` and `git shortlog` show the true author without rewriting history (BLK-004).
- **3, deleting merged remote branches: they are kept.** The tool's permission refuses the delete, and that is not routed
  around. No goal needs the deletion, because a merged branch costs nothing. Housekeeping stops trying (BLK-002 closed).
- **4, C46's design: genotype, with `H9WT` as the control and `C46Mut` as the condition, n = 2 libraries per arm.** The
  delivery's own names declare it (C46 README). The two unknowns are stated in the stage-4 report as limits, not asked:
  whether C46 is isogenic to H9 (if not, line and genotype are confounded), and whether `_1`/`_2` are independent
  differentiations. One of them can be measured: H9 is 46,XX, so Y-gene counts in `C46Mut` would show it is not an H9
  derivative. Stage 4 measures that first (GAP-C68).
- **5, velocity on C46: not run.** The delivery holds Cell Ranger outputs only, with no FASTQ or BAM, so there are no
  spliced and unspliced counts. Asking the vendor is outward-facing, and no goal needs it: PROF.3's scVelo coverage is tested
  on scVelo's own published example when that plugin migrates (A4.2's rule).

## Decided (2026-11-09)

- **2026-11-09T15:40Z, the PI: "go"** on decisions 0, 0b, 0c, 1 and 6:
  - **0, the deploys, done by fast-forward:** Lab `main` 51a00fa (W005), Studio `main` 1d591f9 (W008), and Service
    `main` 997d132 (W009 + W015). The PI's four protected files are unchanged.
  - **0b:** option (b), now a tier-II rule. The W007 merge is accepted, and GAP-102 is closed.
  - **0c:** proceed on the verified surviving copies, with no restoration.
  - **1, C46 stage 1 promoted:** PBS 720932, 53,534 cells, D5 kept, a `cp -al` tree with its PROMOTED.md.
  - **6:** c46.R recorded as outside the family's records.
- **The PI: "agree" to the throttle:** 2 builders and 1 verifier; at most 2 fix rounds per change; re-checks on the fix
  only; no polishing of deploy-held changes; a loop tick every 3 h (RULES tier IV).

- **The A3.4 scale cohort: the lupus PBMC atlas** (Perez 2022; CELLxGENE 218acb0f; 1,263,676 cells; SLE 162 vs healthy 99 donors; CC-BY 4.0). Decided by the pre-decider: a public cohort choice is a (C) design (gap review table A7). It was second-read against the curation API. See `autodev/scale/CANDIDATES.md`.

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
| ~~B1's ASK-1~~ | **withdrawn 2026-11-09T08:40:57Z**: B1's verifier showed the settlement amended tier-I rule 1, which only the PI changes, and that the precedent does not fit (ADR-0027's P1 had no promoted run, and its merge was reserved to the PI). The question is now **decision 0b** above | the RULES amendment is reverted |
| B1's ASK-2: SAMBO DE direction | already decided (slide 15) | Each contrast is the treatment against its declared control (aged vs young, HFD vs chow). The stage-4 RUNLOG names each earlier run's direction. |
| B1's ASK-3: single-cell count floors | already decided (QC.1; D8/D9) | Derive them on cells within D8's bounds, falling back to the lower bound where there is no valley. A cohort's declared floors apply and are reported beside the derived ones. |
| A vendor name in rnaseq-service's scanner ("Novogene" in protected files) | the pre-decider (tier II's 'cohort data' means a cohort's names, levels, numbers and paths) | A sequencing vendor's name used as file-naming vocabulary in a generic scanner is not cohort data. The two hits stay, in the PI's protected files. |
| The audit-agent cap; the builder cap | the pre-decider (tier IV, rule 5) | 1 → 3 audit agents. The editing cap went 3 → 4 → 5, the last step for W005, a light Node project, on a 36 GB machine. |
| Service waves vs your uncommitted `rnaseq-service` work (82 lines in `scan.ts`, `request.ts`, `types.ts`, `test-scan.mjs`) | the pre-decider (protect the owner's work; the reviewer's own first move) | The single-cell mode is built in new files only and never touches those four files. |
| Where the run record lives (0001b, blocker B2) | the pre-decider (design) | Each stage appends to the object's `uns`; it never replaces (P20). Lab copies the record verbatim into an additive `meta.run`, and Studio shows it in a Run card. |
| Where Lab conversion runs (0001b, blocker B3) | the pre-decider (rule 3 covers cluster compute only) | On the workstation, as Lab was designed. |
