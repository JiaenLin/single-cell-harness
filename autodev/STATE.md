# STATE: where the program stands

Updated 2026-11-11T09:05:50Z by the coordinator. This is the living page. Every LOOP TICK that changes
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

Rewritten whole at 2026-11-11T10:23:25Z (the earlier text, of 09:05, had gone stale).

- **The account's weekly limit stopped all six agents at about 10:50Z on 2026-11-11** (it resets 2026-11-15T21:00Z). The PI
  then said CONTINUE, and requests are accepted again. Nothing was lost that was pushed; each builder's uncommitted work
  stayed in its clone. No agent was resumed (an agent resumes on the session's model): each was launched fresh with its
  brief from `<scratchpad>/relaunch/` and told to read its predecessor's clone and wave-file plan first. Today's meter
  before the stop: 16.3 M output tokens, 46 launches.
- **THE CAP IS TWO OPUS AGENTS (D-039), beside at most one Fable designer or reviewer.** The heartbeat's prompt and RULES
  item 6 carry it. Stopped items' briefs are in `<scratchpad>/relaunch/q_*.txt`; their clones keep what they wrote.
- **THE PI, 2026-11-12 (D-043): "USE PREDECIDER, REDUCE THE DECISION REQUIRED".** The order of fixes and what takes a slot
  is decided and reported, never asked. A question that is the PI's (a promotion, a threshold the data cannot decide)
  is held for the day's report with its numbers and a recommendation; no work waits on it.
- **DEPLOYS OF STUDIO AND LAB ARE NOT ASKED since 2026-11-12 (D-045, the PI's own answer: "Deploy, and stop asking"):** once
  an independent check says ready and the deploy workflow's own tests succeed, deploy and report right after with what
  went live and its limits. The PI can withdraw this at any time. Service is never touched.
- **THE PI, 2026-11-12 (D-046): "when the fine tune did not work for many times, use fable to check root design".** RULES
  item 20: after a component's third failed verification no further fix round is launched until a Fable agent has
  reviewed its root design; the next round builds the recommendation. Running now for Lab's run section (W017, five
  failed fix-ups). Next in line if their re-checks fail again: scProfile's maker record; the driver's pinned set.
- **THE PI, 2026-11-11 (D-041): "keep the bound as set. do not block anything if unnecessary"** (D-040's bound on the
  cohort-value class).
- **Running now (2 Opus):** the VERIFIER of **W054** (Lab: the run section rebuilt as a closed reader, one file per
  conversion; built at `5b4b42e`, suite 496 of 496, the fixture's digest as predicted; on PASS Lab deploys without a
  question, D-045); the builder of **W055** (scProfile, the plugin line's first wave: `abundance` graded blind
  through the maker, then the maker fixed; a DOI and a pin for `de`, `cellchat` and `abundance`). No Fable agent is running.
- **QUEUED for an Opus slot, in this order** (launch the next only when fewer than 2 Opus agents run):
  0. **W056, the driver's integration** (the batch is VERIFIED at `110417c`): REGISTERED 2026-11-12
     ([waves/W056.md](waves/W056.md); brief `q_w056build.txt`): from W052's branch at `133589d`, the driver merged by
     hand, W045 brought on, the first cohort's chained request finished (its label-column unknown is a design the
     builder decides and labels), the subset and full jobs generated with `--tool` for all four tools. It launches
     at the next free Opus slot. A1.2, A6.3, A7.1 and A3.4 wait on this line.
  0b. W054's verification is running; then Lab's deploy, reported, not asked (D-045). After it: Studio's Run-card
      sentences brought in line with what a bundle now carries (a Fable designer's small pass, then a deploy).
  1. **W052 PASSED its lean re-check** (the harness at `133589d`). Waiting only for the cluster: its subset 791374, then
     the full job (4 h); on AS PREDICTED both mains move in one step (scIntegrate `2fc7a6c` first, then the harness by
     its train's three guards), A3.1 +0.1; the stage-3 question goes into the day's report.
  5. **W050's verification** (scAnno `f456431`): brief `q_w050verify.txt`.
  6. **scIntegrate's installer** (GAP-C116), for A1.3: brief `q_w046fix2.txt`, clone `W046g-scIntegrate`.
- **Studio's `main` is `8fb0d0a` since 2026-11-12T01:39Z (D-045)**: W053 is live: an untested gene carries no p in a saved
  DE file, the table or the volcano; the volcano follows the cutoff's own correction; a cutoff is rounded to two figures
  before it is applied. Before it the same day: W051, the words and elements (`192057b`, D-042). Lab's `main` is
  `ca0cc73` (D-038), with three known exotic-input defects (fix-up 6 is queued; its deploy needs no question now).
- **Merged 2026-11-12, the tenth: scProfile `b5f646a`** (the batch W035 + W040 + W047; last re-check PASS; DE gate 791483
  AS PREDICTED): the maker's prose verb; the host writes no run into a plugin; the site strings gone; a design record is
  read only in the maker's own form. No score moves by itself: it releases the plugin line.
- **The route's first sufficiency check is done** ([audits/ROUTE_SUFFICIENCY_20261111.md](audits/ROUTE_SUFFICIENCY_20261111.md)):
  as written the route ended 0.0006 short of HAPPY with its two planned stops. Applied to ROUTE.md: six additions (R04,
  R06, R07, R35 and R45 widened; R46 and R47 new), R40 struck, three PI steps added. Projected now: 19.05 with the stops.
- **W045 built** (`4fb23df`: one object becomes per-library parts, streaming at about 560 MB whatever the object's size; 899 tests): it waits for the driver's re-check, then is brought onto the fixed driver.
- **Next harness slots, in order:** W045 (one object into per-library parts, built on the old driver) brought onto W049's
  head; the adapter's state version 2 and the scIntegrate stand-in (GAP-C109), to land with scIntegrate's batch; if the
  driver batch passes, its gate: the first cohort's chained request finished and its generated job, a subset first.
- **On PBS:** **791471**, the FULL first-cohort stage 3 through the harness at W052's fix head `133589d` and scIntegrate
  `2fc7a6c` (asks 4 h; on AS PREDICTED both mains move in one step). Checkouts on the cluster: the harness `133589d`;
  scQC at `main`; scAnno `f456431`; scIntegrate `2fc7a6c`; scProfile `5c1a3ff` (its `main` is one docs commit ahead).
- **Merged 2026-11-11, the seventh: scAnno `9fb561c`** (W044's leak fixes, split from its failed tree rule, D-028): scAnno's
  own files carry no cohort or site string under either cohort's generated lists (38 hits to 0). A3.1 is 0.41.
- **Merged 2026-11-11, the sixth: the harness `1d1031b` (W036, `prof@scprofile`).** The first cohort's stage 4 through the harness read AS PREDICTED (PBS 789593) at the commit that merged. **All four of that cohort's stages now run through the harness on `main`.**
- **The tally: 7.79 of 20** (mean 0.389; 0.292 this morning, 0.271 at audit pass 0004): A1.1 5/8, A1.2 7/10, A1.3 3/5, A2.1 3/4, A3.2 3/4, A3.1 0.51, A6.2 1/2 moved today. Nine tests are still under 0.5: A2.2, A2.3, A3.4, A4.1, A4.2, A4.3, A5.2, A6.1, A7.1. Counting on a merge, not yet on `main`: A3.1 +0.1 for scIntegrate.
- **Merged 2026-11-11, five batches before those:** scIntegrate `b148030` (W012 + W025), scProfile `6f970e5` (W013 + W032 + W023), scQC `46ffe90`
  (W020), scAnno `779fd08` (W038), and **the harness `a677e8f` (W029 + W034)**: its train's three jobs all AS PREDICTED at the
  merged commit (stages 1, 2 and 3; PBS 788583, 788586, 788587), the merged tree's runtime files equal the gated head's, the
  suite OK.
- **Merged 2026-11-11, the ninth: scQC `8106f50`** (W048 with two fix rounds; last re-check PASS; PBS 790672 and 790673 AS
  PREDICTED): scQC's own files carry none of the two cohorts' generated terms (224 hits to 0), its guard reads the lists,
  each gate records the design it computed on and a dropped factor is told to the user. **A3.1 is 0.51, over its bar.**
- **Merged 2026-11-11, the eighth: scQC `de62f78`** (W043: a failed removal audit stops the run before any object is written;
  its integrity checks are never acceptable by name). Both cohorts' promoted stage-1 runs reproduced IDENTICAL at the gated
  commit (PBS 789673, 789675). GAP-119, a wrong-result defect, is closed. scQC's leak-clean half of R13 is still open.
- **Held to merge together (D-033, D-034):** **W039** (scIntegrate; verified PASS, its gate 789561 AS PREDICTED) moves
  numbers at state version 1. W046's verifier measured that the harness cannot serve a stale view (a mismatch refuses), so
  nothing wrong can be served; but the contract needs version 2 in the tool AND in the harness's adapter. Order: W046's
  fix round, its re-check and jobs; a small harness wave (GAP-C109: the adapter at 2, the stand-in as strict as the tool);
  the first cohort's stage 3 through the harness at both new heads; both mains in one step. The PI's stage-3 question follows.
- **Held (D-035): the driver, W041 + W042.** Its last re-check failed on ONE reason and judged all eight of the builder's
  left items limits; five of the first verifier's six reasons are closed. W049 carries the residue, then one verification
  of the whole batch. 
- **Ended (D-036): W044's tree rule.** Its last re-check failed on one reason (a draft with every test switched off by a
  zero threshold is recorded as checked) and its job missed (790197). On a fresh, unfitted set of 147 expectations the
  branch scores 111 against fix round 1's 106 and main's 103, so the rule is better than main's; but two fix rounds are
  spent and no score waits on the tree. The branch `autodev/W044-fix2` stays; GAP-C112 and GAP-C113 hold the rest. **The
  second cohort's tree is not ready for the PI to approve**; the PI is shown the walk table instead.
- **Held:** the scProfile batch, W035 + W040 (D-032: the last re-check failed on one point, cellchat's own remaining run
  values); W047 carries that residue, and one verification of the whole batch follows it.
- **The second cohort's tree** is not yet one to take to the PI: the first job missed (PBS 789434, MISSED (2)), and the job
  copy written in fix round 1 was NOT submitted, because its re-check found it could not fail where the first one missed.
- **The scale cohort:** the data is in place and inventoried (1,263,676 cells x 30,172 genes, 88 pooled libraries holding both
  arms; PBS 789057, 789058, 789168). Stage 1 waits for W045 and the driver's fix: a subset job (2 of the 88) before the full one.
- **The improvement plan of 2026-11-11** ([`IMPROVEMENT_PLAN.md`](IMPROVEMENT_PLAN.md); RULES items 14-19): a job over 2 hours runs on a subset first (`gate.py` refuses otherwise); every builder runs [`ATTACKS.md`](ATTACKS.md) (24 lines) against its own change before hand-back; items that search try at least two candidates and keep a pool; a claimed gain needs its ablation; a plugin's source is a DOI that resolves (R45). The measure: `passrate.py`, 4 of 9 waves built on 2026-11-11 passed first verification.
- **A bound on the cohort-value class (D-040, 2026-11-11).** Seven verification rounds across three tools failed on ever
  wider readings of "a cohort's measured value". From the scProfile batch on: a generated-list hit, an exact survivor in a
  touched file, or a value a user would see or a test depends on FAILS; counts in words, rounded magnitudes and unread
  files are counted limits (GAP-C114). BRIEFS 2a check 9. The PI is told and can widen it.
- **A preflight for removed numbers** (`setup/autodev/survivors.py`, 2026-11-11; since W048's re-check also `--words` for counts written in words and `--near` for rounded copies): every number a wave's diff removed that is
  still at the head, one line each. W035 (twice) and W048 failed verification on exactly this; a builder runs it before
  hand-back (BRIEFS section 0) and the coordinator before launching a verifier. To run on W047's head before its batch verification.
- **A records commit says whether it landed** (`setup/autodev/commit.sh`, 2026-11-11): two records commits were blocked by
  the suite's leak guard (a site path an agent wrote into a wave file) and were reported as landed. The helper stages only
  the paths it is given and prints `COMMITTED <sha> pushed` or `BLOCKED: <reason>`; every brief now says a wave file takes no site path.
- **Next free slots, in order:** the re-checks of the driver's and W044's last rounds as they
  hand back; one verification of the scProfile batch after W047; then the scProfile plugin line (abundance first), R05 and
  R06 (harness: installer and lock; small fixes), the first cohort's chained run and the scale cohort's stage 1 once the
  driver passes.
- **Studio is DEPLOYED (D-037).** The PI opened the gallery and said "good, deploy." on 2026-11-11; scrnaseq-studio's `main`
  went from `1d591f9` to `f7dab0c` (W028 + W037) at 13:14Z; the Pages workflow (lint, the 1,861 checks, the build, the
  publish) finished with success and the live site answers with the new build. The go covered the Studio only: Lab's W017 is asked when its re-check has passed. The batch's
  code verification was still running when `main` moved; it continues, and a blocking finding goes to the PI at once.
  Told to the PI: six limits (the first: a saved figure drops the note about uncalled cells) and four taste calls.
  **The batch's code verification PASSED afterwards** (the Run card under 23 rewritten run sections, the parser under 13
  probes, no existing check weakened); it judged the uncalled-cells finding a limit, to fix before the next deploy (R48).
- **Lab is DEPLOYED (D-038).** Asked with the facts on 2026-11-11, the PI chose "Deploy now": scrnaseq-lab's `main` went
  from `51a00fa` to `ca0cc73` (W017) at 14:05Z. It stops the silent relabelling of cells in crossed designs. LIVE AND
  KNOWN (GAP-C119): three defects that need a hand-made HDF5 file. Fix-up 6 is being built; after its re-check the PI is
  asked for a second deploy. The Pages run succeeded and the site answers with the new build: A6.2 is 1/2 from now.
- **The PI's steps** (ROUTE section 3): stage 3's re-promotion waits for scIntegrate's batch to merge (D-034); the second
  cohort's tree is not ready (D-036); the scale cohort's doublet threshold waits for the subset run's numbers.
- **Parked:** W030 (Service; uncommitted work in its clone), W022 as a wave of its own, the B1 register's queued rows.

## Machinery (session-only; re-create on resume, see README)

| job | id | cron | created | expires |
|---|---|---|---|---|
| HEARTBEAT | `1fecbd4b` | `17 */2 * * *` (the prompt in README's reminders table; since 2026-11-11T14:10Z it carries the cap of 2 Opus agents) | 2026-11-11 | 2026-11-18 |
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
