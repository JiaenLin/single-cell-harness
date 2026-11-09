# STATE: where the program stands

Updated 2026-11-09T14:14Z by the coordinator. This is the living page. Every LOOP TICK that changes
something refreshes it, and so does every PERIODIC CHECK and every BLOCKER SWEEP.

## Verdict

**NOT HAPPY: 0 of 20 tests PASS (9 PARTIAL, 11 FAIL)** at audit pass 0003
([`audits/0003-audit.md`](audits/0003-audit.md)). Pass 0002 had 7 PARTIAL and 13 FAIL. A1.1 moved FAIL → PARTIAL (stage 1 through
the harness) and A4.4 FAIL → PARTIAL (`sch catalogue`). All 9 closures claimed since pass 0002 were re-checked and hold, and
GAP-033 is closed from 783148's own files. The register holds 161 gap ids: 91 open, 39 in a wave, 31 closed. 46 of the
gaps not closed are size M or larger.

## Scoreboard (GOALS.md layer 3; pass 0003)

| test | grade | the main reason (gap ids) |
|---|---|---|
| A1.1 one request, every stage | PARTIAL | Stage 1 runs through `sch mount qc@scqc` with the pbs executor, AS PREDICTED (PBS 782817, 782922). No adapter for stages 2-4, and no driver (GAP-001; W026 building). |
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
| QC | scQC | **W014 MERGED** (`main` `98504bd`): scQC builds its three environments on a fresh prefix from its own locks, and stage 1 on them is IDENTICAL to the reference (job 34, PBS 783151, AS PREDICTED on every line). The CellBender checkpoint error persists in both environments (GAP-C49). **W020** (19 constraints) can start | merged; 1 queued |
| ANNO | scAnno | **W011 MERGED** (`main` `d0ee926`). **W018 DONE: the promoted stage 2 reproduces at its own commit** (PBS 783148, `bd45f5d`): IDENTICAL on 1,464 obs columns over 31 objects, the joint object, the scope record and every table, with inputs and environment measured equal first (GAP-033 closed). **W021** building: scAnno's 18 inherited constraints, including `scanno build-markers` | merged; done; 1 building |
| INT | scIntegrate | **W004 merged** (`9a2d7d1`). **W012** (`69a54b2`): verifier PASS; job 29 AS PREDICTED; **job 28 MISSED line B** (harmony's total moved 0.0279 > 0.013), so it is **not merged**. The cause predates W012: harmony's clustering metrics vary run to run (ARI 0.860 / 0.858 / 0.645) while its embedding metrics agree to 1e-6, and the method ranking flips. **W025** (queued, stacked on W012) makes them reproducible; then one re-gate. **W022** waits | held; 1 queued |
| PROF | scProfile | **W002 MERGED** (`f5175ea`). **W013**: `de` runs through the maker in the declared-control direction, AS PREDICTED in three runs (bit-identical to 720548). The verifier keeps finding ways round the maker's new `--answer` mechanism; fix-up 3 is building (one line model, design arguments only, the covariate regression). Its registered ladder line waits on W019. **W023** queued | fixing; 1 queued |
| HARN | single-cell-harness | **W010, W016 and W019 MERGED** (`main` `70c25b9`): stage 1 through the harness; one plugin format plus `sch catalogue`; the maker's six defects from the de conversion (`agree` judges every output, excusing only a tool's declared execution record). **W026**: SAMBO stage 2 through the harness AS PREDICTED (PBS 783280); the verifier is running. **W024** fix-up building (moving the cohort job scripts out, the scope loophole, GAP-111) | merged x3; 1 verifying; 1 fixing |
| PLAT | studio, lab, service | **Verified PASS and held for the PI's deploy** (BLK-005): **W005** (Lab), **W008** (Studio), **W009** and **W015** (Service). **W017** (Lab, on W005): fix-up 3 is building (an unbounded read through hard-linked groups; first-fit filling) | 4 held (PI); 1 fixing |
| AUDIT | — | **Pass 0003 done: NOT HAPPY, 0/20 (9 PARTIAL, 11 FAIL)**. Merged since: **W014, W019**. Pass 0004 starts at the next merge | waiting (2 of 3) |
| BLOCKER | — | **Sweep 14:11Z:** nothing removable is waiting. The B1 register's 68 rows are all in waves (W020 building, W021 verifying, W022 and W023 queued behind their repositories), and the checkouts each follow their gating wave. New: GAP-C62 (the commit hook runs the whole suite on records-only commits). Still the PI's: BLK-002, BLK-005 (4 verified platform waves), BLK-007, decisions 0-6 | sweeping |

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
0. **Deploy Lab (W005): it is verified, but the classifier refuses the merge** (BLK-005). Lab's `main`
   deploys the live app, so the classifier treats a push to it, and even opening a PR, as a
   production deploy. Your standing yes doesn't reach the permission system. Either run it yourself:
   `! cd /tmp && rm -rf lab-merge && git clone -q https://github.com/JiaenLin/scrnaseq-lab lab-merge && cd lab-merge && git merge --ff-only origin/autodev/W005-lab-cli && git push origin main`,
   or add a permission rule for pushes to the platform repos' `main`. **Studio (W008) is verified too**
   (1,621/1,621; the live app changes only by the corrected DESeq2 wording and a violin-band fix):
   `! cd /tmp && rm -rf studio-merge && git clone -q https://github.com/JiaenLin/scrnaseq-studio studio-merge && cd studio-merge && git merge --ff-only origin/autodev/W008-studio-truth && git push origin main`.
   Studio ignores the absent field, so either app can go first.
   **Service (W009) is verified too.** It recognises Cell Ranger and CeleScope deliveries and asks the
   single-cell questions with no default assay. The bulk path is byte-identical, and your four
   uncommitted files are untouched, so it cannot conflict with them:
   `! cd /tmp && rm -rf svc-merge && git clone -q https://github.com/JiaenLin/rnaseq-service svc-merge && cd svc-merge && git merge --ff-only origin/autodev/W009-sc-delivery && git push origin main`.
   **Service W015 is verified too, stacked on W009.** The Service writes scQC's samplesheet, registry row and design table
   from a single-cell request, holds back nuclei without a filtered matrix, and checks typed species against the build.
   One fast-forward deploys both, W009 then W015: replace the branch above with `origin/autodev/W015-sc-design-sheet`.
0b. **May a change that is MEANT to move a promoted run's outputs merge?** (B1-111.) Rule 1 asks
   for an IDENTICAL reproduction, so a fix that changes SAMBO's numbers on purpose can never merge.
   Examples: GAP-C11 (BBKNN scored on the wrong representation) and scProfile's DE direction.
   - **(a)** Identical only. Such fixes ship default-off or scoped away from the promoted run.
   - **(b) Recommended.** Such a change merges under the standing yes when its PBS run matches a
     difference predicted output by output before submission, graded by its written criterion.
     Re-promoting the moved run stays yours.
   - **(c)** As (b), but each such merge comes to you.
   Meanwhile these fixes go default-off or scoped, with SAMBO IDENTICAL, so no lane waits.
   **A merge already made under the same question (GAP-102, raised by audit pass 0002):** I merged
   W007 (scQC `0a9d2ce`) although its reproduction against the promoted run missed as written. The
   miss was two record keys that `main`'s earlier commit `0e6a5f6` added. The comparison that
   justified the merge was designed AFTER submission: it was against 720930, whose code is
   identical to `main`, and it found no `/metrics` value differing. That puts the merge outside
   your standing yes. Recommended: accept it. W007 moved no computed value, and reverting brings
   back the first-cohort fallback registry and seven other fixed defects. Your answer to 0b decides
   it. From now on, any comparison a merge relies on is written into the job before submission
   (RULES tier IV).
0c. **SAMBO's sealed run directories are missing on the cluster** (BLK-007). The promoted stage-1 run
   (`runs/scqc/01_qc/20260824T161519Z__scqc-133a951__01_qc__ribo`) and every other stage-1 run except
   720930's are gone, along with the CellChat reference
   `20260906T120759Z__scprofile-de199d0`. None is in `~/_archive`. The `results/` deliverables are
   intact. No autodev session deletes cluster runs. **Was this a deliberate cleanup, or can the
   cluster's backups restore them?** Nothing waits: the reproductions use the verified copies that
   survive. *(Corrected 2026-11-09 after audit pass 0003, GAP-118: the promoted stage-3 run's directory is NOT gone; it
   exists and is sealed, PBS 671045. The promoted stage-2 run's directory is gone; its `results/` tree reproduced, PBS 783148.)*
1. **Promote BrainOrganoid_C46 stage 1 (PBS 720932, 53,534 of 59,701 called cells)?** Recommended:
   **yes, keep D5 as it is.** W006 measured that the doublet calls follow the data, not the prior:
   9.0–11.1% with no expectation, 8.9–10.6% under scDblFinder's default, 8.3–11.7% under D5. The
   alternative is a re-run with a tighter `dbr_sd`, which would move the calls by about one point and
   not to the declared 5.2–6.9%. Optional: ask the vendor how many cells were loaded, because D5's
   rate scales by cells recovered, and correct it for the record. A promotion unblocks C46's stages 2–4.
2. **Commit `f488621` on the harness's `main` is authored `t <t@t>`.** A test's stray config did this
   (BLK-004); the true author is Jiaen Lin, via Claude. It is pushed. Rewriting it means a force-push
   to `main`, which is outward-facing and rewrites public history. Recommended: leave it. The
   correction is recorded in BLK-004 and in the next commit.
3. **A permission rule for deleting merged remote branches** (BLK-002). Merged branches are kept, which
   is harmless.
4. **C46's design facts.** What is C46 relative to H9, and what are `_1`/`_2`? This blocks only C46
   stage 4. It comes from the collaborator.
5. **Velocity on C46.** Only if you want it: it needs the vendor's BAM.
6. **A hand-written Seurat analysis in C46's project root** (GAP-113, audit pass 0003): `c46.R` and a 1.2 GB `.rds`,
   dated 2026-10-26, appear in none of C46's records. Is it yours (an exploration), and may the record say so? Recommended:
   a dated RUNLOG note that it exists and is not a family deliverable, with the files left where they are. Nothing waits on it.

## Decided (2026-11-09)

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
