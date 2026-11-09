# STATE: where the program stands

Updated 2026-11-09T11:17Z by the coordinator. This is the living page. Every LOOP TICK that changes
something refreshes it, and so does every PERIODIC CHECK and every BLOCKER SWEEP.

## Verdict

**NOT HAPPY: 0 of 20 tests PASS (7 PARTIAL, 13 FAIL)** at audit pass 0002
([`audits/0002-audit.md`](audits/0002-audit.md)). Pass 0001 had 5 PARTIAL and 15 FAIL. A1.3 and A3.3
moved FAIL → PARTIAL. All 16 claimed closures were re-checked and hold. 47 gaps of size M or larger
remain open.

## Scoreboard (GOALS.md layer 3; pass 0002)

| test | grade | the main reason (gap ids) |
|---|---|---|
| A1.1 one request, every stage | FAIL | The kernel runs none of the four tools: there is no adapter, and the `pbs` executor is refused. SAMBO ran stage by stage with glue at every boundary (GAP-001, GAP-002). |
| A1.2 the ten steps mapped | PARTIAL | No map exists, and differential abundance has never run (GAP-058, GAP-041). |
| A1.3 environments from main | PARTIAL | scProfile builds from its lock on a fresh prefix (PBS 782609). No fresh-prefix PBS build from main yet for scQC, scAnno or scIntegrate (GAP-107). |
| A2.1 pre-declared reproduction | PARTIAL | Stages 1 and 3 reproduce. Stage 2's promoted run has never been reproduced (GAP-033). Stage 4 has no promoted run (GAP-055). |
| A2.2 documentation true | FAIL | Every tool has false docs (GAP-009, -022, -031 → **W003**, -037 → **W004**, -052). |
| A2.3 cold reproduction | FAIL | Never attempted (GAP-004). |
| A3.1 held-out cohorts | FAIL | C46 stopped after stage 1. Fixtures reach only scIntegrate's pipeline. The leak list misses factor levels (GAP-056, -007, -023, -008). |
| A3.2 design-aware | PARTIAL | DE contrasts levels in alphabetical order. Covariates are neither modelled nor refused (GAP-039, -040). |
| A3.3 assay rule sets | PARTIAL | scQC, scAnno and scIntegrate have per-assay rules with no silent default. scProfile changes captions only. |
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
| QC | scQC | **W007 MERGED** (`0a9d2ce`). **W014** built (`a2c8471`): the installer pins the denoiser and the R doublet stack, the core lock carries pyarrow, and build_reference.sh requires its reference. **PBS 782920** builds all three environments on a fresh prefix and reruns stage 1 against PBS 782673. The verifier is running. Measured: the torch pin does NOT fix CellBender's checkpoint error (GAP-C49). **W020** queued: scQC's 19 inherited constraints (B1) | gating; 1 queued |
| ANNO | scAnno | **W003 merged** (`a126756`). **W011**: 782899 IDENTICAL as predicted. The C17 fix-up (`d0ee926`, strings only: 59 leaks to 0) gets **job 25 resubmitted unchanged as PBS 782921**, and the verifier re-checks C17. **W018** queued: the promoted stage 2 at `bd45f5d` (GAP-033). **W021** queued: scAnno's 18 inherited constraints, including `scanno build-markers` (B1-030). GAP-028 is unblocked: the human CellMarker data is in the PI's archive | gating; 2 queued |
| INT | scIntegrate | **W004 merged** (`9a2d7d1`). **W012** (`69a54b2`): verifier PASS; job 29 AS PREDICTED. Job 28 (PBS 782882, stage 3) is running, and the merge follows its grade. **W022** queued: 6 remaining inherited constraints (B1-056 was done by W012) | gating; 1 queued |
| PROF | scProfile | **W002 MERGED** (`f5175ea`). **W013** (`0f4ff9e`): PBS 782918 AS PREDICTED. The verifier FAILED it on D1 (a hand-edited caveat) and D2 (undeclared design columns dropped under `--factor`), and the ladder is red on resource measurements (harness GAP-C41). A fix-up is building; D1 goes through the maker's design worksheet. **W023** queued: scProfile's 24 inherited constraints | fixing; 1 queued |
| HARN | single-cell-harness | **W010**: job 31 AS PREDICTED. The fix-up of the second verifier's D1-D3 and E2's silent re-baseline is building, and **job 33** (inputs read-only, as LAYOUT requires) follows. **W016** building: one plugin format (ADR) and `sch catalogue`. **W019** building: the maker's H1-H6, C41 first | fixing; 2 building |
| PLAT | studio, lab, service | **W005**, **W008** and **W009** are verified PASS and **held** for the PI's deploy (BLK-005). **W015** (`418ffad`): the verifier FAILED it on D1 (a hand-typed species bypasses the species/build check), and the fix is building. **W017** (`1703e16`, on W005): crossed conditions kept, the run's record carried, real embeddings only; the verifier is running | 3 held (PI); 1 fixing; 1 verifying |
| AUDIT | — | Pass 0002 done (NOT HAPPY, 0/20). Merges since: W007, W002 (both before 0002's grading closed) plus the coming W011, W012, W013 and W010. **Pass 0003** runs after the third of those merges | waiting |
| BLOCKER | — | **Sweep 2026-11-09:** 68 inherited constraints sat queued since B1. They are now waves W020-W023, one per tool, each starting when that tool's current wave merges. GAP-028's data blocker is REMOVED (the PI's `all_cell_marker.zip` holds 1,779,944 human rows). Still the PI's: BLK-002, BLK-005, BLK-007, decisions 0-5 | sweeping |

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
   720930's are gone, along with the promoted stage-3 run's directory and the CellChat reference
   `20260906T120759Z__scprofile-de199d0`. None is in `~/_archive`. The `results/` deliverables are
   intact. No autodev session deletes cluster runs. **Was this a deliberate cleanup, or can the
   cluster's backups restore them?** Nothing waits: the reproductions use the verified copies that
   survive.
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
| ~~B1's ASK-1~~ | **withdrawn 2026-11-09T08:40:57Z**: B1's verifier showed the settlement amended tier-I rule 1, which only the PI changes, and that the precedent does not fit (ADR-0027's P1 had no promoted run, and its merge was reserved to the PI). The question is now **decision 0b** above | the RULES amendment is reverted |
| B1's ASK-2: SAMBO DE direction | already decided (slide 15) | Each contrast is the treatment against its declared control (aged vs young, HFD vs chow). The stage-4 RUNLOG names each earlier run's direction. |
| B1's ASK-3: single-cell count floors | already decided (QC.1; D8/D9) | Derive them on cells within D8's bounds, falling back to the lower bound where there is no valley. A cohort's declared floors apply and are reported beside the derived ones. |
| A vendor name in rnaseq-service's scanner ("Novogene" in protected files) | the pre-decider (tier II's 'cohort data' means a cohort's names, levels, numbers and paths) | A sequencing vendor's name used as file-naming vocabulary in a generic scanner is not cohort data. The two hits stay, in the PI's protected files. |
| The audit-agent cap; the builder cap | the pre-decider (tier IV, rule 5) | 1 → 3 audit agents. The editing cap went 3 → 4 → 5, the last step for W005, a light Node project, on a 36 GB machine. |
| Service waves vs your uncommitted `rnaseq-service` work (82 lines in `scan.ts`, `request.ts`, `types.ts`, `test-scan.mjs`) | the pre-decider (protect the owner's work; the reviewer's own first move) | The single-cell mode is built in new files only and never touches those four files. |
| Where the run record lives (0001b, blocker B2) | the pre-decider (design) | Each stage appends to the object's `uns`; it never replaces (P20). Lab copies the record verbatim into an additive `meta.run`, and Studio shows it in a Run card. |
| Where Lab conversion runs (0001b, blocker B3) | the pre-decider (rule 3 covers cluster compute only) | On the workstation, as Lab was designed. |
