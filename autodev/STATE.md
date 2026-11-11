# STATE: where the program stands

Updated 2026-11-11T05:47:04Z by the coordinator. This is the living page. Every LOOP TICK that changes
something refreshes it, and so does every PERIODIC CHECK and every BLOCKER SWEEP.

**FULL development since 2026-11-11T05:47:04Z** (the PI: "first, evaluate and improve current development harness towards our goal ... after that, launch full development to reach our goal!"). The pause (D-020) and TOKEN-LIMITED (D-017) are over (D-021); validation runs again. The harness was changed first: the diagnosis is [`audits/DIAGNOSIS_20261111_efficiency.md`](audits/DIAGNOSIS_20261111_efficiency.md), the rules are RULES.md's 2026-11-11 block, and **the queue is [`ROUTE.md`](ROUTE.md)**: about 40 items from a tally of 5.85 to HAPPY's 18.0. In short: small runs (about 150 calls), verify first and gate at the head that merges, verifiers in parallel, up to 6 development agents, the cluster through `setup/autodev/gate.py`, audits at checkpoints, one HEARTBEAT every 2 hours.

**NOT HAPPY: mean 0.271 of 20 measured scores at audit pass 0004** (the first scored pass; [`audits/0004-audit.md`](audits/0004-audit.md)): 0 PASS, 13 PARTIAL, 7 FAIL; 14 of 20 below 0.5. HAPPY needs a mean of at least 0.9 with no test below 0.5. Under D-014's corrected A3.4 formula (only a cohort of at least 1,000,000 cells counts) the mean is 0.269. Moved since pass 0003: A1.1 1/8 -> 2/8 and A1.2 3/10 -> 5/10 (W026), A1.3 1/5 -> 2/5 (W014), A6.3 0 -> 2/3 (the deployed Service), A5.1 0.923 (the run's own claim ledger), A4.4 0.5. All 29 closures since 0003 hold; 11 gaps are new (GAP-119..129), among them GAP-119 (scQC: a failed removal audit stops nothing) and GAP-128 (scIntegrate: withheld cells stay in the PCA the docs say they leave). The leak guard is red in 7 of 8 repositories under the generated lists.

## Scoreboard (GOALS.md layer 3, scored; pass 0004)

| test | score (pass 0004) | label | evidence (one line; the full record is the audit) |
|---|---|---|---|
| A1.1 one request, every stage | 0.250 (2/8); coordinator 11:2xZ 0.500 (4/8): SAMBO 1-3 and C46 2 through the harness (784504, 784490) | PARTIAL | SAMBO stage 1 through qc@scqc (PBS 782817, 782922: SEALED exit=0, AS PREDICTED (1'), isolated IDENTICAL) and stage 2 through anno@scanno (PBS 783280, 783363: AS PREDICTED… |
| A1.2 the ten steps mapped | 0.500 (5/10) | PARTIAL | steps 3,4 (scQC via qc@scqc), 5,7 (scAnno cluster/annotate via anno@scanno) run in A1.1; step 1 declared upstream (GOALS G1); step 2 only outside the family (inputs are r… |
| A1.3 environments from main | 0.400 (2/5) | PARTIAL | scQC 98504bd: PBS 783151 P1 HELD (55+165 pins, R stack) P2 HELD selftest 46/0/1; scProfile 27e254f (setup/ = main but comments): PBS 782609 P1 161/161, P2 7/0; scAnno, sc… |
| A2.1 pre-declared reproduction | 0.500 (2/4) | PARTIAL | stage 1 promoted run reproduced (782817/782922 AS PREDICTED (1') vs results/01_qc); stage 2 (783148 PREDICTION HELD vs results/02_annotate); stage 3: 783282 FAILED as wri… |
| A2.2 documentation true | 0.125 (1/8) | PARTIAL | seeded draw Random(4), 12 claims per repository (96 checked) plus 18 known-false re-checks: 9 new FALSE in 5 repositories, 17 known-false STILL FALSE; only rnaseq-service… |
| A2.3 cold reproduction | 0.000 (0/4) | FAIL | no cold reproduction of a sealed stage run was ever attempted (records, waves and RUNLOGs grepped); a cold reproducer would meet a red harness suite (GAP-127, GAP-C64) |
| A3.1 held-out cohorts | 0.125 (0.125/1) | PARTIAL | 0.5 x (2/8: SAMBO stages 1-2 through the harness; C46 none) + 0.5 x (0/5: S1 red under both cohorts' generated lists in scQC 234, scAnno 36, scIntegrate 12, scProfile 204… |
| A3.2 design-aware | 0.250 (1/4) | PARTIAL | scProfile main f5175ea: one factor n=2 runs; two-factor with interaction: DE adds the term but never contrasts it (its cannot_show says so) and kernels/abundance.py has a… |
| A3.3 assay rule sets | 0.800 (4/5) | PARTIAL | scQC (ambient.py:59, quality.py:92, steps.py:1476-1481 refuses), scAnno (assay.py NO DEFAULT; --assay required cli.py:2501), scIntegrate (ASSAY_RULES = {} declared, --ass… |
| A3.4 scale | 0.050 (201426/4000000) (0 under D-014's corrected formula) | PARTIAL | literal formula: 100,713 cells x 2 stages through A1.1 on standard queues (long 782922; short 783363), measured in OBSERVATIONS.txt of both runs; no cohort of 1,000,000 c… |
| A4.1 existing pool in one format | 0.000 (0/9) | FAIL | 1 of 9 in the maker's layout (catalogue: cellchat maker, 8 one-file); no dev-suite run on the cluster since 20261002T081440Z__sch-b2e79db; scProfile fails sch conform S1 … |
| A4.2 maker on new tools | 0.000 (0/5) | FAIL | no draw rule from the scRNA-tools catalogue and no conversion of a never-seen tool (git grep of the harness, autodev/waves) |
| A4.3 provenance of methods | 0.333 (3/9) | PARTIAL | sch catalogue --json at 7ca2515 over scProfile f5175ea: every plugin cites a peer-reviewed source (cite field), doi 'not declared' in 9 of 9; exact upstream pin only cell… |
| A4.4 AI-native | 0.500 (2/4) | PARTIAL | cold agent (this pass, skills + sch only, synthetic fixture): listed the catalogue (23 plugins) and picked scprofile:abundance; run FAILED (sch plan scprofile:abundance -… |
| A5.1 report from evidence | 0.923 (12/13) | PARTIAL | PBS 711781 writing run 20260915T051032Z__scprofile-c1e92c2__04_profile__written: PAPER_CLAIMS.cellchat.jsonl 13 claims, reviewer verdicts 12 standing, 1 narrowed, 0 withd… |
| A5.2 hypotheses | 0.000 (0/1) | FAIL | no hypothesis record, falsifying test or plan-from-hypothesis in harness 7ca2515 or scProfile f5175ea (grep); 0 hypotheses proposed and 0 follow-ups |
| A6.1 Harness UI | 0.000 (0/5) | FAIL | no web or server code in the harness (no http.server/flask/fastapi/aiohttp/websocket; no .html/.ts/.js tracked) |
| A6.2 Studio hand-off | 0.000 (0/2) | FAIL | Studio main 1d591f9 has no Run card or meta.run (git grep src: 0); the family's own final object was never converted by Lab's CLI and opened in Studio (only W005's fixtur… |
| A6.3 Service takes single-cell requests | 0.667 (2/3) | PARTIAL | Service main 997d132: npm test 7 scripts, 338 ok, Cell Ranger and CeleScope deliveries write the request, scQC samplesheet, registry row and design.csv; the bulk request … |
| A7.1 agents drive it | 0.000 (0/5) | FAIL | no cold agent has run A1.1 on a held-out cohort; skills/ holds harness-agent, harness-developer, plugin-maker and none runs a cohort across stages (GAP-003); stages 3-4 h… |

## Lanes

| lane | repository | wave | status |
|---|---|---|---|
| QC | scQC | **W014 MERGED** (`main` `98504bd`). **W020's gate met**: C46 IDENTICAL (PBS 783992) and SAMBO AS PREDICTED (job 35b, PBS 784271, after fix round 1 declared job 33's F1 keys); queued for its verifier after the W013 + W032 batch. Then GAP-119 first in QC's next wave, W031 (scale) and D-008's floors. GAP-C78 (218 leak hits) | verifying next; 1 registered |
| ANNO | scAnno | **W011 and W021 MERGED** (`main` `68233f0`). **W033 gating**: C46's references (job 01, **PBS 784414**, AS PREDICTED); stage 2 through the harness on single cells: job 02 (PBS 784415) failed at its input check before any tool ran (it named the run's layout, not the promoted copy's), so its one-line copy 02b ran as **PBS 784490: SEALED, every run line held** (isolated IDENTICAL, control refused, mount and unmount restored); one label line (L3) missed in H9WT_1, the draft tree's (GAP-C85). Gate met; validation waits; the draft tree stays unapproved, so no label is quoted. Findings GAP-C82..C85 | gating |
| INT | scIntegrate | **W012 + W025 gating** (round 2, the last allowed): iLISI and cLISI now score every cell (scIB's subsample cannot be seeded), bit-identical between runs; re-gate job 30b **PBS 784233 AS PREDICTED** at `b148030` (harmony bit-identical in-job, LISI exact, scvi/scanvi within 0.02). **W034 built** (`int@scintegrate`, harness `eac7860`): its job 31 (stage 3 through the harness) **PBS 784504 AS PREDICTED**: SAMBO stage 3 runs through the harness (gate met; waits for validation). The pair waits for validation. GAP-C65, GAP-C12 and GAP-C61 stay for later; **W022** follows the pair's merge | gating; 1 queued |
| PROF | scProfile | **W002 MERGED** (`f5175ea`). **W013 HELD** (D-012) and **W032 gating** at `157ed9d`: W013's open routes closed (79 attack checks, 67 red on the old code), 4 of 5 gaps closed, the fifth down from 205 real leak hits to 5 in plugin comments that only the maker may change (GAP-C79, GAP-C80); de's job resubmitted UNCHANGED as **PBS 784285** (the manifest rule). The W013 + W032 batch's verifier follows the queue. A4.1 stays 0/9 until GAP-C79 and GAP-C81 (dev_suite.pbs runs only abundance) | held + gating; 1 queued |
| HARN | single-cell-harness | **W010, W016, W019, W026 and W024 MERGED** (`main` `2fc727d`). **W029: both gates AS PREDICTED** at `006b72c` (job 29 stage 2, PBS 784088; job 36 stage 1, PBS 784130, including the new scheduler reconcile); its verifier follows audit 0004 | merged x5; 1 verified-next |
| PLAT | studio, lab, service | **DEPLOYED by the PI's go:** Lab W005 (`51a00fa`), Studio W008 (`1d591f9`), Service W009 + W015 (`997d132`). **W030** (Service: local reads, GAP-P05, GAP-C55, B1-059) **building** (Opus max; the PI's four files untouched). **W017** (Lab, `243783f`) waits for its last re-check; **W028** (Studio) for its verifier. Each platform merge deploys a live app, so it comes to the PI as a go when verified | deployed x4; 1 building; 2 waiting |
| AUDIT | — | **Pass 0004 done (the first scored pass): NOT HAPPY, mean 0.271** (0.269 under D-014). The next pass after 3 more merges or 24 h with one. The queue follows its section 9 (RULES, the 2026-11-10 audit block) | done; next after 3 merges |
| BLOCKER | — | **Sweep 05:1xZ (SWEEP-4):** W022 and W023 made startable under D-016 (stacked on W025's and W032's heads); W023 moved up the builder queue (the eight plugins' path); the scProfile cluster checkout back on main. Still waiting on the PI: the budget (D-005); later, GAP-055's promotion. The verifier queue is the throttle's one slot | watching |

**Read 2026-11-09** (rule 5: these landed 2026-10-02 and were never read):
- PBS 720930 is IDENTICAL, as predicted.
- PBS 720932 (the C46 apply run) kept 53,534 of 59,701 cells. The floors were exact to the prediction. The removal percentage was missed, because of a doublet over-call (GAP-C02).
- The output of PBS 720931 was not located.

The graded results are in both cohorts' `stages/01_qc/RUNLOG.md` and in ADR-0027.

## The queue: [`ROUTE.md`](ROUTE.md)

- **Running now (6):** the Fable 5.2 designer on R41 = W037 (Studio's design); builders W035's fix round 1 (the prose verb's bypass and its record) and R13 = W043 (scQC: a failed removal audit stops the run); R17 = W044 (scAnno: the proposed tree keeps to the tissue; its leak hits); the verifiers of W039 and of the driver (W041 + W042: built at `4e10656`, 891 tests; the first cohort's chained run returned with three unknowns to look up) (scIntegrate: withheld cells out of the PCA, built at `1901611`).
- **Merged 2026-11-11 (the fourth today):** scAnno `main` = `779fd08` (W038: the lock pins its closure, the installer works with the site's conda, one gene reader; the fresh-prefix build PBS 789141 AS PREDICTED; verifier PASS). A1.3 is 3/5 by the verifier's row.
- **The scale cohort's inventory (PBS 789168) AS PREDICTED:** 1,263,676 cells x 30,172 genes, integer counts in raw/X, 261 donors, 88 libraries each a pool of donors. The data stage is done; stage 1 waits for R43 and W042.
- **Verdicts 2026-11-11:** W036 (`prof@scprofile`) PASS, waits for its job at the head that merges; W040 PASS; **W035 FAIL** (two ways past the prose rule), in fix round 1.
- **On PBS:** the harness train's stage 3 (788587), scAnno's fresh-prefix build (789141), the scale cohort's inventory (789168). The scale cohort's data is in place (12,218,105,530 bytes, the published tag recomputed; PBS 789057 graded MISSED (1) on one file's mode, set by hand, D-027) and scQC's environment built AS PREDICTED (789058).
- **Built today, waiting for a verdict or a gate:** W035 (the maker's prose verb), W040 (scProfile's own site strings: 100 hits to 10, all in held-out plugins), W036 (`prof@scprofile`), W041 (the driver's run 1: `sch run --request`, decisions asked by name; 880 tests), W037 run A (Studio: shell, tokens, the Cells screen; the coordinator's review sent four defects into run B).
- **Merged 2026-11-11, each by fast-forward after a verifier's PASS:** scIntegrate `main` = `b148030` (W012 + W025), scProfile `main` = `6f970e5` (W013 + W032 + W023), scQC `main` = `46ffe90` (W020; one comment line fixed by the verifier, the run key's code digest unchanged). Verifier scores: A2.1 3/4, A3.2 3/4. Every batch that waited for validation is now verified; the harness batch waits only for its three gate jobs.
- **W035 built** (the maker's `scprofile prose` verb; cellchat's leaked values removed through it): it waits to be verified as one batch with W040. A4.1 is still 0/9: the ladder's leak and contract tiers read the whole repository, and the held-out plugins abundance, decoupler and velocity hold the last term hits, so they go first in the plugin line (D-025).
- **W036 built** (`prof@scprofile`, harness `dcbc0df`): on the fixture, scProfile through the harness gives the DE and abundance tables byte for byte as alone. Its stage-4 job is written; it runs at the head that merges once the train's stage-1 and stage-3 jobs leave the harness checkout. Verified with the next harness batch.
- **The scale cohort (R15, W031 run 1 built):** the project is on the cluster; the transfer (**PBS 789057**, the 12.2 GB object) and scQC's environment (**PBS 789058**) are running; the inventory job follows. Stage 1 waits for R43 (per-library parts from one object, GAP-C90) and for peak memory in the record (GAP-C91, in the driver's run 2).
- **Next free slots:** R13 (scQC: the removal audit can stop a run, GAP-119; leak-clean), R40 (C46's records), R31 and R33 after W035, R05 and R06 after R01 merges.
- **R01 (harness: W029 + W034): verifier PASS** for both waves and the train head; one README line fixed. The gate at the head that merges, `autodev/train-harness-1` @ `0670f3e`: stage 1 **PBS 788583** (running), stage 2 **PBS 788586: AS PREDICTED** (every line equal to 784088's), stage 3 **PBS 788587** (running) (re-pinned copies 36t, 29t, 31t; predictions unchanged). All AS PREDICTED, then the train merges into `main`. scAnno's cluster checkout is back on `main` (`68233f0`). Heartbeat 06:47Z: 6 builders running; the day's meter 2.77 M output, 413 M context read, 11 launches.
- **Next, as each verifier passes:** its merge (the harness through its train's three jobs), then that repository's next route item; R16 (scAnno) and R40 (C46's records) at the first free slots.
- **The PI's steps** are in ROUTE section 3; none is askable yet.
- **Parked:** W030 (Service; uncommitted work in its clone), W022 as a wave of its own, the B1 register's queued rows.

## Machinery (session-only; re-create on resume, see README)

| job | id | cron | created | expires |
|---|---|---|---|---|
| HEARTBEAT | `d3695b30` | `17 */2 * * *` (the prompt in README's reminders table) | 2026-11-11 | 2026-11-18 |
| LOOP TICK, BLOCKER SWEEP, PERIODIC CHECK | retired 2026-11-11 (RULES, item 9) | - | - | - |
| the PBS mirror | background task `bt2f5k07v` | `bash setup/autodev/pbs_mirror.sh <HARNESS>/autodev/.machinery/pbs 300`; watch.tsv's 4th column is the tool commits a job uses | 2026-11-11 | until the session ends |
| the gate runner | `python3 -I setup/autodev/gate.py submit ... --go`, `grade <id> --status ...` | site facts in `autodev/.machinery/site.env` (git-ignored) | 2026-11-11 | - |
| the verdict waiters | one background `until [ -f <id>.verdict ]` per submitted job | re-invoke the coordinator when a job lands | per job | - |
| bootstrap | `bash setup/autodev/bootstrap.sh check` / `print` | what runs, what is missing, the start lines | 2026-11-10 | - |

## Decisions needed from the PI

None. D-005 (the budget) was answered by the PI's token-limited mode (D-017).

## Decided (2026-11-10, by the pre-decider; the PI: "review rules and goals and decide")

- **2026-11-10, the PI: "agree, proceed with all"** on the diagnosis's seven changes
  ([audits/DIAGNOSIS_20261110_vs_vcc.md](audits/DIAGNOSIS_20261110_vs_vcc.md)), and "for the predecider, improve it".
  Done the same day, in RULES.md's 2026-11-10 block: agent use as VCC's row (2 builders; one verifier per merge batch per
  repository; 2 rounds then a gap); the measured score per test and HAPPY = mean >= 0.9 with no test < 0.5 (D-006);
  the PBS mirror and the verdict Monitor (`setup/autodev/`); the manifest rule for fix-ups; the budget (provisional: 8 M output a
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
