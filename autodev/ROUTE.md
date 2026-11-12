# ROUTE: the finite list from here to HAPPY

Written 2026-11-11 by the coordinator (the PI: "find the best and most efficient way towards our goal"; the diagnosis:
[audits/DIAGNOSIS_20261111_efficiency.md](audits/DIAGNOSIS_20261111_efficiency.md)). **The queue is this file.** An item
becomes a registered wave (`waves/W###.md`, one row in `ledger/waves.tsv`) when what it waits for is done. A gap enters a
wave only if it blocks an item here, or is a wrong result in a promoted output. An item that turns out not to move its
test is struck, with the reason.

HAPPY = the mean of the 20 scores is at least 0.9 (a sum of 18.0) and no test is below 0.5. The tally was 5.85 on the morning of 2026-11-11 and 7.79 (mean 0.389) that evening, by verifiers' and the coordinator's rows; 7.89 (mean 0.395) on 2026-11-12 with scIntegrate's merge; 8.14 (mean 0.407) the same day with scProfile's batch (A3.2 4/4).
**Sufficiency, checked 2026-11-11** by an independent reader ([audits/ROUTE_SUFFICIENCY_20261111.md](audits/ROUTE_SUFFICIENCY_20261111.md); RULES item 19).
As first written the route reached 18.77 only if every item landed in full, and 17.9994 (NOT HAPPY, by 0.0006) with the two
stops planned here: A3.4 at two stages (0.63) and A4.2 at three tools (0.6). Five tests were capped below what the route
assumed: A6.3 0.667, A4.3 0.778, A1.2 0.8, A3.1 0.8, A7.1 0.8. The additions marked **(suff.)** below close them: 19.05
with the two stops (mean 0.953), 19.82 with none. So the slack is about 1.0 point, and the two stops stay.

## 1. Where each test stands and what closes it

| test | now | closes with | items |
|---|---|---|---|
| A1.1 one request, every stage | 5/8 (the first cohort's four stages on `main` since 2026-11-11; the second cohort's stage 2) | SAMBO stage 4; C46 stages 1, 3, 4 | R02 R14 R21 R35 |
| A1.2 ten steps mapped | 7/10 (DE and DA through the adapter) | step 10 (cellchat through the adapter); step 9 needs a trajectory or pathway plugin RUN in a cohort's stage 4; step 2 by the PI's reading of "declared upstream" | R02 R03 R35 |
| A1.3 fresh environments | 3/5 (scAnno, 2026-11-11) | scAnno, scIntegrate, the harness build from `main` on a fresh prefix | R05 R16 R20 |
| A2.1 promoted runs reproduced | 3/4 (stage 3 counted since W012 + W025 merged) | stage 4 needs a promoted run (the PI); a re-promoted stage 3 needs its own reproduction (R34) | R34 |
| A2.2 no false claim in the docs | 1/8 | a docs-truth pass per repository, after its code settles | R39 |
| A2.3 cold reproduction | 0/4 | a context-free agent reproduces four sealed stage runs | R11 |
| A3.1 held-out cohorts | 0.61 (5 of 8 stages; scAnno, scQC and scIntegrate leak-clean on `main`, 2026-11-12) | the four stages above; each tool leak-clean with the fixture's axes reaching its pipeline | R06 R13 R16 R20 R23-R30 R46 R47 |
| A3.2 designs | 4/4 (2026-11-12) | - | R32 (inside R24) |
| A3.3 assay rule sets | 4/5 | scProfile's rule sets | R33 |
| A3.4 scale | 0 | the 1,263,676-cell cohort through the stages (0.316 a stage) | R15 |
| A4.1 plugins in the maker's layout | 0/9 | cellchat, de and the seven held-out, each passing the cluster's dev suite and conform | R23-R31 |
| A4.2 never-seen tools | 0/5 | a draw rule, then tools converted by agents alone | R36 |
| A4.3 source and pinned version | 3/9 | a DOI and an exact pin in each plugin, set through the maker in its own wave; `de` and `cellchat` too | R24-R30 R45 |
| A4.4 cold agent uses a plugin | 2/4 | the catalogue's dead rows fixed, then the trial | R10 |
| A5.1 claims that survive review | 12/13 | nothing: kept | - |
| A5.2 hypotheses | 0 | hypothesis records, a falsifying test, a follow-up run through the loop | R09 |
| A6.1 the UI's five acts | 0/5 | a local UI over the driver | R08 |
| A6.2 the object opens in Studio | 0/2 | W017 and W028 verified and deployed (the PI's go); the family's final object converted verifying (Studio's batch W028 + W037; Lab's W017 re-check at the next free slot) |
| A6.3 the request runs | 2/3 | the harness takes the request as the driver's input | R04 |
| A7.1 agents drive it | 0/5 | a cohort-run skill, then a cold agent on a held-out cohort | R07 |

## 2. The items

Size: S is a run of about 80 calls, M about 150 (the cap; larger is split before launch). "v" = a verifier, "job" = a
cluster job the coordinator submits with `gate.py`, "trial" = a cold agent.

| id | repository | the item | moves | waits for | size | status |
|---|---|---|---|---|---|---|
| R01 | harness | verify W029 + W034 as one batch on `autodev/train-harness-1`; re-run their three jobs at the train head; merge | A1.1 on `main` | - | v + 3 jobs | merged |
| R12 | scQC | verify W020 (`b255e45`); merge | unblocks R13 R14 R15 | - | v | merged |
| R19 | scIntegrate | verify W012 + W025 (`b148030`); merge; then ask the PI about stage 3's moved ranking | A2.1 3/4 | - | v | merged |
| R22 | scProfile | verify W013 + W032 + W023 (`6f970e5`); merge | A3.2 (direction) | - | v | merged |
| R40 | cohort C46 | verify W033's jobs and records (no tool change). STRUCK 2026-11-11 (the sufficiency check): it moves no score, since C46's stage 2 already counts, and R14, R21 and R35 re-run C46's stages through the harness anyway | - | - | - | struck |
| R23 | scProfile | **W035**: the maker's prose verb; cellchat's leak hit; cellchat and de through the cluster's dev suite | A4.1 2/9 | - (stacked on `6f970e5`) | M + job | merged (scProfile `b5f646a`, 2026-11-12: the batch W035 + W040 + W047; the cluster's dev-suite job for cellchat and de runs with the plugin line, where A4.1 counts) |
| R31 | scProfile | isolated groups' x86_64 locks, a cluster build, `selftest` (GAP-C88) | A4.1 (the suite needs the environments) | R23 | S + job | merged (scProfile `a2694ec`, 2026-11-12: **W058**; both isolated groups built on the cluster, PBS 791942; GAP-C88 closed) |
| R24-R30 | scProfile | the seven held-out plugins through the maker, one wave each, in this order: abundance, decoupler, velocity, scenic (they hold the 10 leak hits that keep every plugin red, D-025; measured at W040's head), then cellcycle, liana, pseudotime: migrate, DOI and pin (the DOI recorded with its own record's title and year and checked, RULES item 18), comment hits, the cluster's dev suite | A4.1 +7/9, A4.3 +6/9, A3.1 | R23 R31; one at a time until two in a row need no maker change, then in pairs | S-M each + job | building (abundance merged at scProfile `a2694ec`, 2026-11-12, **W055** with **W058** and **W065**; next: decoupler, graded blind, one at a time until the PI allows three; before it: D5 with GAP-C128 and GAP-C131) |
| R32 | scProfile | designs: the interaction contrast. The verifier found the rest done at `6f970e5` (a covariate modelled or refused by name; the declared-control direction); what is left is abundance fitting one factor at a time, and abundance is held out, so this is part of abundance's own wave (R24), through the maker | A3.2 4/4 | R24 | in R24 | merged (scProfile `a2694ec`, 2026-11-12: inside **W055**: the interaction named as not fitted with the reason; A3.2 4/4) |
| R33 | scProfile | assay rule sets, not captions (GAP-050, GAP-C51); a refused kernel no longer leaves the run reading ok with no table (GAP-C96, a wrong-result defect) | A3.3 5/5 | R22 | S-M | open |
| R42 | scProfile | **W040**: leak-clean under the generated site shapes (GAP-C89: 101 and 95 hits, bare job ids and queue names in the host's docs, runner, cli, setup, tests and DEVPOINTS); the 12 in kernels/ go through the prose verb, the held-out ones in their own waves | A3.1 +0.1 | R23 | S-M | merged (scProfile `b5f646a`, 2026-11-12) |
| R44 | scProfile | **W047**, with the one residue of W035's last re-check (cellchat's own remaining run values): the host carries no cohort measurement (GAP-C100): the development contract stops asking for run counts in code, the scaffold stops stamping them into every new plugin, the host files and tests lose them | A3.1 +0.1 (with R42 and the held-out plugins' waves), A4.1 | R23's fix round 2 (disjoint files otherwise) | M | merged (scProfile `b5f646a`, 2026-11-12; the 199 files never read whole are GAP-C114, a counted limit, D-040) |
| R45 | harness + scProfile | a reference check (RULES item 18): a plugin's source is a DOI recorded with the title and year from the DOI's own record; `sch dev` resolves it and compares; an offline test uses the recorded values. **(suff.)** Not a run of its own: it is the first step of R24, and it gives `de` a DOI and an exact upstream pin and `cellchat` its DOI, through the maker (no other item names those two) | A4.3 +2/9 | R23 released | S, inside R24 | merged for three plugins (scProfile `a2694ec`, 2026-11-12: **W055**: a source stage in the maker; de, cellchat and abundance); open for the six others, each in its own wave |
| R46 | scProfile | **(suff.)** GAP-054: the fixture's dev point runs DE and abundance on the built environment and accepts no refusal; `sch dev check fixture_a` green (without it scProfile cannot earn its tool credit in A3.1's leak-and-fixture half) | A3.1 +0.1 (with R42, R44) | R23 released; R31 if run on the cluster | S | merged (scProfile `a2694ec`, 2026-11-12: **W055**; de and abundance read ok on the cluster, PBS 793345; its part of A3.1 waits for the held-out plugins' hits) |
| R47 | scAnno | **(suff.)** GAP-C103: `embed` takes the library name from the object or the manifest, never a file stem, with a test that fails at `main` (else a chained stage 4 keyed on the library column finds no library) | protects A1.1 +1/8 and A3.1 +1/16 | W044's fix round 2 (same repository) | S | building (**W050**, from scAnno `main`) |
| R48 | Studio (+ Lab) | **W051**, the PI 2026-11-11: "continue fable designer to improve UI design, check all elements such as work count, wording and other element design": every word and every element of the Studio measured, a written standard (word budgets, one term per concept), every element brought to it; a saved figure names the cells the annotator did not call (GAP-C118). Separately, code: a table whose header is not as wide as its rows is refused, and Lab escapes or refuses a separator inside an id (GAP-C117) | no score; a misleading saved figure and a wrong table on the live app | a free slot; then the PI's go for a re-deploy | S (a Fable designer for the figures) | merged (W051, the words and elements, live since 2026-11-12, D-042; W053, no p for an untested gene, live the same day, D-045); open (GAP-C117, a separator inside an id, with Lab's fix-up 6) |
| R34 | scProfile + SAMBO | a full stage-4 run at merged `main`; ask the PI to promote; reproduce it | A2.1 4/4 | R22 R02 | 2 jobs + the PI | open |
| R02 | harness | **W036**: `prof@scprofile`, SAMBO stage 4 through the harness (DE, abundance, the plugins the design admits), with the run-alone twin | A1.1 5/8, A1.2 9/10 | - (stacked on the train head; scProfile at `6f970e5`) | M + job | merged (run 1); run 2, the plugins, open |
| R03 | harness | **W041** (run 1, built) and **W042** (run 2: the cluster path, each stage's cost, one library key, the first cohort's chained run), the stage driver: one request (matrices + design sheet) plans and runs the four mounts in order, user-owned decisions declared, ambient removal declared upstream by name; a job generated, not hand-written | A1.2 10/10; needed by R04 R07 R08 R15 | R02 (starts on three stages) | M, split in two | gating (the batch W041 + W042 + W049 VERIFIED at `110417c`, 2026-11-12; before it merges: **W056**, registered: its hand merge with W052's branch and W045, then a cohort run through the driver as the gate) |
| R04 | harness | the Service request as the driver's input (GAP-P06); **(suff.)** one request Service wrote (a real delivery and its questionnaire) is RUN as a cohort's chained run under its pre-declared job: without a run the test stays at 2/3 | A6.3 3/3 | R03 | S, no extra job | open |
| R43 | harness | one published object becomes per-library parts (GAP-C90): a declared library column, counts slot and symbol column, and the replicate unit as a second key (measured on the scale cohort, PBS 789168: its 88 libraries are each a pool of donors, so the QC unit and the replicate unit differ); read-only parts and a samplesheet manifest that `qc@scqc` mounts; no cohort script | A3.4 (stage 1 cannot start without it), A6.3 | R03's run 1 (the request names the declarations) | M | verifying |
| R05 | harness | an installer and a lock; a fresh-prefix build and self-test on the cluster (GAP-127) | A1.3 +1/5 | R01 | S-M + job | open |
| R06 | harness | leak-clean under its own generated shapes (GAP-C66), `anno@scanno` takes W021's flags (GAP-C84); `sch dev edit` and `layout --apply` take a version only as N.N.N (GAP-C97); the commit gate runs only the ledger tests and conform when a commit touches record paths alone (measured 2026-11-11: every records commit runs the whole suite, minutes each; this part moves no score: only if it costs a few calls); **(suff.)** the two-shape fixture's axes reach a harness pipeline (a mount's run or the driver's plan) as a `sch dev check` point | A3.1 +0.1 | R01 | S | open |
| R10 | harness | the catalogue's dead `scprofile:<name>` rows (GAP-122); then the cold-agent trial of the four acts | A4.4 4/4 | R02 | S + trial | open |
| R07 | harness | a cohort-run skill (assemble, submit, recover, audit, record: GAP-003); then a cold agent on a held-out cohort; **(suff.)** the trial's protocol plants ONE failure, declared before it starts, that the skill must detect, fix and resubmit (without one the recover act cannot be shown: 4/5) | A7.1 5/5 | R03 | M + trial | open |
| R08 | harness | a local UI over the driver, designed by a Fable 5.2 designer (the PI, 2026-11-11) to Studio's design file: ask, see the plan, approve, follow, open the reports and the record | A6.1 5/5 | R03 | M x 2 | open |
| R09 | harness + scProfile | hypothesis records with evidence, a falsifying test and a runnable follow-up; one follow-up through the loop; a pool with S and K registered, each hypothesis tried on a subset first (RULES item 16) | A5.2 | R02 | M x 2 | open |
| R11 | all | four cold reproductions of sealed stage runs from the record and the docs | A2.3 4/4 | R01 R12 R19 R22 merged | 4 trials + jobs | open |
| R13 | scQC | leak-clean under the generated lists (GAP-C78), the fixture's axes; the removal audit can stop a run (GAP-119, a wrong-result defect) | A3.1 +0.1 | R12 | M, split in two | merged (run 1, the audit, `de62f78`; run 2, **W048**, leak-clean and the fixture's axes, `8106f50`, 2026-11-11); open (run 3: GAP-C104, cells denoised elsewhere become an asked decision) |
| R14 | cohort C46 | stage 1 through the harness (with R21 and R35 this becomes ONE chained run from C46's request once W042 lands) | A1.1 +1/8 | R12 | job | open |
| R15 | cohort (scale) + scQC | **W031**: stage the 1,263,676-cell cohort (done: PBS 789057, 789058, 789168); each stage runs on a subset first (2 of the 88 libraries), then on all, the subset's cost sizing the full request (RULES item 14) | A3.4 0.316 a stage | R12; R03 for the later stages | jobs, S-M | gating |
| R16 | scAnno | the environment pin (GAP-C82), a fresh-prefix build and self-test; leak-clean (36 hits), the fixture's axes; `build-markers` field (GAP-C83) | A1.3 +1/5, A3.1 +0.1 | - | M, split in two + job | merged (run 1; run 2's leak fixes at `9fb561c`, 2026-11-11) |
| R17 | scAnno | `tree propose` keeps the tissue's own lineages (GAP-C85); C46's tree re-proposed; ask the PI to approve it | C46's labels (no score by any formula: R21 runs with draft labels; it ends at this round) | R16 | S-M + the PI | held (ENDED at its last round, D-036: the re-check failed on one reason and the job missed; the branch stays, GAP-C112 and GAP-C113 hold the rest; no score waits on it) |
| R20 | scIntegrate | a fresh-prefix build and self-test; leak-clean (12 hits), the fixture's axes; withheld cells out of the PCA (GAP-128, a wrong-result defect, with its predicted difference); W022's constraints only where a wave meets them | A1.3 +1/5, A3.1 +0.1 | R19 | M, split in two + job | merged (scIntegrate `2fc7a6c` and the harness `1717eed`, 2026-11-12: W039 + W046 and W052; the pair's gate, PBS 791471, AS PREDICTED; A3.1 +0.1). Still open here: the fresh-prefix build (GAP-C116, the installer; A1.3) |
| R21 | cohort C46 | stage 3 through the harness (labels marked draft until R17's approval) | A1.1 +1/8 | R01 R19 | job | open |
| R35 | cohort C46 | stage 4 through the harness (one factor, n = 2); **(suff.)** the run names and runs one trajectory plugin its design admits (pseudotime or velocity) through `prof@scprofile`, else a pathway plugin through the maker (GAP-042) | A1.1 +1/8; A1.2 step 9 +0.1 | R02 R21 R47 | job | open |
| R36 | harness + scProfile | a draw rule over the scRNA-tools catalogue, kept as a pool with S = 5 and K registered (RULES item 16); five never-seen tools converted by agents alone, each passing the dev suite and its published example | A4.2 (0.2 a tool) | R24-R30 mostly done (the maker stable) | 5 x M + jobs | open |
| R38 | Lab + Studio | W017's last re-check, W028's verification; the family's final object through Lab's converter (GAP-P20); ask the PI's deploy go | A6.2 2/2 | - | v x 2, S + the PI | merged (Studio and Lab deployed, D-037, D-038; **W054** deployed 2026-11-12 at Lab `fdb8888`, D-047: the run section a closed reader, one file per conversion, a read guard). **W057** deployed 2026-11-12 at Studio `e475703`, D-051: the Run card true for old and new bundles, a ragged table refused). Left for A6.2: the MEASUREMENT of its first half (the first cohort's real final object through Lab's converter into the deployed Studio), then GAP-P20 for the harness's own record |
| R39 | all eight | a docs-truth pass per repository (the audit's known-false lines first, then a claim sweep; every cited source resolved and one cited claim per document read against it) | A2.2 8/8 | each repository's last route item | S each | open |
| R41 | Studio | **W037** (the PI, 2026-11-11: "improve the studio UI design and layout to be top level"): an audit against a written rubric, a design file with tokens and a layout model, the shell and every screen rebuilt to it, a before-and-after gallery; runs by a Fable 5.2 designer since the PI's "use fable 5.2 level designer to design all ui" (run A was an Opus builder's draft) | the PI's direction (PLAT.3, G6; A6.2's surface) | - (stacked on W028's `099a085`); the deploy is the PI's go | M x 3 + a verifier by looking | merged (deployed on the PI's word, 2026-11-11: Studio `main` = `f7dab0c`; the batch's code verification still running) |

Parked (not on the route; they stay in the ledgers): W030 (Service local reads: moves no score), W022 as a wave of its
own, the 73 queued constraints of the B1 register (removed by the wave that meets one), every gap not named above.

## 3. The PI's steps (asked once each, with the numbers, the moment the precondition is met)

| step | precondition | test |
|---|---|---|
| stage 3: re-promote or keep, now that harmony is deterministic and its rank moved (2nd to 5th; the top method unchanged) | R19 merged (done 2026-11-11) AND W039 merged (withheld cells out of the PCA, GAP-128), so one re-promotion carries both | A2.1 |
| stage 4: promote a run | R22 and R02 merged, R34's run sealed | A2.1 |
| C46's cell-type tree: NOT ready to approve (R17 ended, D-036). The PI is shown the job's walk table and the draft: an organoid's tree may need the PI's own edit of which lineages it can hold (GAP-C113) | told at the next report; no answer is waited for | the labels' standing; no score |
| (no longer a question since D-045: Lab's second deploy follows fix-up 6's re-check, reported right after) | - | A6.2's trust in the Run card |
| the scale cohort's residual-doublet threshold for genotype-demultiplexed pools (stage 1's `dbr` decision; the data cannot decide it) | R15's staging done (it is): asked with the subset run's numbers, so the question carries what each choice removes | A3.4 stage 1 (0.316) |
| A1.2's step 2: does ambient removal "declared upstream by name" count as mapped? (GOALS: the PI's reading of a goal wins) | the driver (R03) merged, so the declaration can be shown | A1.2 +0.1 |
| if stage 3 is re-promoted: its reproduction is one more job (R34), else A2.1 drops to 3/4 until it runs | the PI's stage-3 answer | A2.1 |

## 4. The order

1. **Now, in parallel:** the verifiers (R01, R12, R19, R22), and the two builders that need no merge (R23 = W035, R02 = W036).
2. **As each verifier passes:** its merge (the harness through its train), then that repository's next item
   (R05 or R06; R13 with R14 and R15's staging; R20 with R21; R32 or R33), and R16 at the first free slot.
3. **When R02 is built:** R03 (the driver), then R04, R07, R08, R09, R10 in parallel where their files are disjoint.
4. **The plugin line** (R31, R24-R30) runs the whole time, one at a time; R36 follows it.
5. **The Studio line** (R41 = W037, then R38's verifications) runs beside the rest; R08's harness UI takes its tokens from R41's design file.
6. **Last:** R11's cold reproductions, R39's docs-truth passes, then one full audit.
