# ROUTE: the finite list from here to HAPPY

Written 2026-11-11 by the coordinator (the PI: "find the best and most efficient way towards our goal"; the diagnosis:
[audits/DIAGNOSIS_20261111_efficiency.md](audits/DIAGNOSIS_20261111_efficiency.md)). **The queue is this file.** An item
becomes a registered wave (`waves/W###.md`, one row in `ledger/waves.tsv`) when what it waits for is done. A gap enters a
wave only if it blocks an item here, or is a wrong result in a promoted output. An item that turns out not to move its
test is struck, with the reason.

HAPPY = the mean of the 20 scores is at least 0.9 (a sum of 18.0) and no test is below 0.5. The tally today is 5.85.
Everything below done gives 19.9, so about 1.9 points may be missed. The expensive fractions that HAPPY does not need:
A3.4 past two stages at scale (0.63), A4.2 past three tools (0.6), A2.1's fourth stage if it is not promoted (0.75).

## 1. Where each test stands and what closes it

| test | now | closes with | items |
|---|---|---|---|
| A1.1 one request, every stage | 4/8 | SAMBO stage 4; C46 stages 1, 3, 4 | R02 R14 R21 R35 |
| A1.2 ten steps mapped | 6/10 | DE, DA and the plugins through the adapter; ambient removal declared upstream by name | R02 R03 |
| A1.3 fresh environments | 2/5 | scAnno, scIntegrate, the harness build from `main` on a fresh prefix | R05 R16 R20 |
| A2.1 promoted runs reproduced | 2/4 | stage 3 counts when W012 + W025 merge; stage 4 needs a promoted run (the PI) | R19 R34 |
| A2.2 no false claim in the docs | 1/8 | a docs-truth pass per repository, after its code settles | R39 |
| A2.3 cold reproduction | 0/4 | a context-free agent reproduces four sealed stage runs | R11 |
| A3.1 held-out cohorts | 0.25 | the four stages above; each tool leak-clean with the fixture's axes reaching its pipeline | R06 R13 R16 R20 R23-R30 |
| A3.2 designs | 1/4 | interaction contrast, covariates modelled or refused by name, the declared-control direction | R22 R32 |
| A3.3 assay rule sets | 4/5 | scProfile's rule sets | R33 |
| A3.4 scale | 0 | the 1,263,676-cell cohort through the stages (0.316 a stage) | R15 |
| A4.1 plugins in the maker's layout | 0/9 | cellchat, de and the seven held-out, each passing the cluster's dev suite and conform | R23-R31 |
| A4.2 never-seen tools | 0/5 | a draw rule, then tools converted by agents alone | R36 |
| A4.3 source and pinned version | 3/9 | a DOI and an exact pin in each plugin, set through the maker in its own wave | R24-R30 |
| A4.4 cold agent uses a plugin | 2/4 | the catalogue's dead rows fixed, then the trial | R10 |
| A5.1 claims that survive review | 12/13 | nothing: kept | - |
| A5.2 hypotheses | 0 | hypothesis records, a falsifying test, a follow-up run through the loop | R09 |
| A6.1 the UI's five acts | 0/5 | a local UI over the driver | R08 |
| A6.2 the object opens in Studio | 0/2 | W017 and W028 verified and deployed (the PI's go); the family's final object converted | R38 |
| A6.3 the request runs | 2/3 | the harness takes the request as the driver's input | R04 |
| A7.1 agents drive it | 0/5 | a cohort-run skill, then a cold agent on a held-out cohort | R07 |

## 2. The items

Size: S is a run of about 80 calls, M about 150 (the cap; larger is split before launch). "v" = a verifier, "job" = a
cluster job the coordinator submits with `gate.py`, "trial" = a cold agent.

| id | repository | the item | moves | waits for | size | status |
|---|---|---|---|---|---|---|
| R01 | harness | verify W029 + W034 as one batch on `autodev/train-harness-1`; re-run their three jobs at the train head; merge | A1.1 on `main` | - | v + 3 jobs | gating |
| R12 | scQC | verify W020 (`b255e45`); merge | unblocks R13 R14 R15 | - | v | merged |
| R19 | scIntegrate | verify W012 + W025 (`b148030`); merge; then ask the PI about stage 3's moved ranking | A2.1 3/4 | - | v | merged |
| R22 | scProfile | verify W013 + W032 + W023 (`6f970e5`); merge | A3.2 (direction) | - | v | merged |
| R40 | cohort C46 | verify W033's jobs and records (no tool change) | A1.1 (stands) | - | v, S | open |
| R23 | scProfile | **W035**: the maker's prose verb; cellchat's leak hit; cellchat and de through the cluster's dev suite | A4.1 2/9 | - (stacked on `6f970e5`) | M + job | building |
| R31 | scProfile | isolated groups' x86_64 locks, a cluster build, `selftest` (GAP-C88) | A4.1 (the suite needs the environments) | R23 | S + job | open |
| R24-R30 | scProfile | the seven held-out plugins through the maker, one wave each (abundance, cellcycle, decoupler, liana, pseudotime, scenic, velocity): migrate, DOI and pin, comment hits, the cluster's dev suite | A4.1 +7/9, A4.3 +6/9, A3.1 | R23 R31; one at a time until two in a row need no maker change, then in pairs | S-M each + job | open |
| R32 | scProfile | designs: the interaction contrast. The verifier found the rest done at `6f970e5` (a covariate modelled or refused by name; the declared-control direction); what is left is abundance fitting one factor at a time, and abundance is held out, so this is part of abundance's own wave (R24), through the maker | A3.2 4/4 | R24 | in R24 | open |
| R33 | scProfile | assay rule sets, not captions (GAP-050, GAP-C51) | A3.3 5/5 | R22 | S-M | open |
| R42 | scProfile | leak-clean under the generated site shapes (GAP-C89: 101 and 95 hits, bare job ids and queue names in the host's docs, runner, cli, setup, tests and DEVPOINTS); the 12 in kernels/ go through the prose verb, the held-out ones in their own waves | A3.1 +0.1 | R23 | S-M | open |
| R34 | scProfile + SAMBO | a full stage-4 run at merged `main`; ask the PI to promote; reproduce it | A2.1 4/4 | R22 R02 | 2 jobs + the PI | open |
| R02 | harness | **W036**: `prof@scprofile`, SAMBO stage 4 through the harness (DE, abundance, the plugins the design admits), with the run-alone twin | A1.1 5/8, A1.2 9/10 | - (stacked on the train head; scProfile at `6f970e5`) | M + job | building |
| R03 | harness | the stage driver: one request (matrices + design sheet) plans and runs the four mounts in order, user-owned decisions declared, ambient removal declared upstream by name; a job generated, not hand-written | A1.2 10/10; needed by R04 R07 R08 R15 | R02 (starts on three stages) | M, split in two | open |
| R04 | harness | the Service request as the driver's input (GAP-P06) | A6.3 3/3 | R03 | S | open |
| R05 | harness | an installer and a lock; a fresh-prefix build and self-test on the cluster (GAP-127) | A1.3 +1/5 | R01 | S-M + job | open |
| R06 | harness | leak-clean under its own generated shapes (GAP-C66), `anno@scanno` takes W021's flags (GAP-C84); the commit gate runs only the ledger tests and conform when a commit touches record paths alone (measured 2026-11-11: every records commit runs the whole suite, minutes each) | A3.1 +0.1 | R01 | S | open |
| R10 | harness | the catalogue's dead `scprofile:<name>` rows (GAP-122); then the cold-agent trial of the four acts | A4.4 4/4 | R02 | S + trial | open |
| R07 | harness | a cohort-run skill (assemble, submit, recover, audit, record: GAP-003); then a cold agent on a held-out cohort | A7.1 5/5 | R03 | M + trial | open |
| R08 | harness | a local UI over the driver: ask, see the plan, approve, follow, open the reports and the record | A6.1 5/5 | R03 | M x 2 | open |
| R09 | harness + scProfile | hypothesis records with evidence, a falsifying test and a runnable follow-up; one follow-up through the loop | A5.2 | R02 | M x 2 | open |
| R11 | all | four cold reproductions of sealed stage runs from the record and the docs | A2.3 4/4 | R01 R12 R19 R22 merged | 4 trials + jobs | open |
| R13 | scQC | leak-clean under the generated lists (GAP-C78), the fixture's axes; the removal audit can stop a run (GAP-119, a wrong-result defect) | A3.1 +0.1 | R12 | M, split in two | open |
| R14 | cohort C46 | stage 1 through the harness | A1.1 +1/8 | R12 | job | open |
| R15 | cohort (scale) + scQC | **W031**: stage the 1,263,676-cell cohort; stage 1, then each next stage as its adapter lands | A3.4 0.316 a stage | R12; R03 for the later stages | jobs, S-M | building |
| R16 | scAnno | the environment pin (GAP-C82), a fresh-prefix build and self-test; leak-clean (36 hits), the fixture's axes; `build-markers` field (GAP-C83) | A1.3 +1/5, A3.1 +0.1 | - | M, split in two + job | building |
| R17 | scAnno | `tree propose` keeps the tissue's own lineages (GAP-C85); C46's tree re-proposed; ask the PI to approve it | C46's labels | R16 | S-M + the PI | open |
| R20 | scIntegrate | a fresh-prefix build and self-test; leak-clean (12 hits), the fixture's axes; withheld cells out of the PCA (GAP-128, a wrong-result defect, with its predicted difference); W022's constraints only where a wave meets them | A1.3 +1/5, A3.1 +0.1 | R19 | M, split in two + job | building |
| R21 | cohort C46 | stage 3 through the harness (labels marked draft until R17's approval) | A1.1 +1/8 | R01 R19 | job | open |
| R35 | cohort C46 | stage 4 through the harness (one factor, n = 2) | A1.1 +1/8 | R02 R21 | job | open |
| R36 | harness + scProfile | a draw rule over the scRNA-tools catalogue; five never-seen tools converted by agents alone, each passing the dev suite and its published example | A4.2 (0.2 a tool) | R24-R30 mostly done (the maker stable) | 5 x M + jobs | open |
| R38 | Lab + Studio | W017's last re-check, W028's verification; the family's final object through Lab's converter (GAP-P20); ask the PI's deploy go | A6.2 2/2 | - | v x 2, S + the PI | open |
| R39 | all eight | a docs-truth pass per repository (the audit's known-false lines first, then a claim sweep) | A2.2 8/8 | each repository's last route item | S each | open |
| R41 | Studio | **W037** (the PI, 2026-11-11: "improve the studio UI design and layout to be top level"): an audit against a written rubric, a design file with tokens and a layout model, the shell and every screen rebuilt to it, a before-and-after gallery; three runs | the PI's direction (PLAT.3, G6; A6.2's surface) | - (stacked on W028's `099a085`); the deploy is the PI's go | M x 3 + a verifier by looking | registered |

Parked (not on the route; they stay in the ledgers): W030 (Service local reads: moves no score), W022 as a wave of its
own, the 73 queued constraints of the B1 register (removed by the wave that meets one), every gap not named above.

## 3. The PI's steps (asked once each, with the numbers, the moment the precondition is met)

| step | precondition | test |
|---|---|---|
| stage 3: re-promote or keep, now that harmony is deterministic and its rank moved (2nd to 5th; the top method unchanged) | R19 merged (done 2026-11-11) AND W039 merged (withheld cells out of the PCA, GAP-128), so one re-promotion carries both | A2.1 |
| stage 4: promote a run | R22 and R02 merged, R34's run sealed | A2.1 |
| C46's cell-type tree: approve the re-proposed tree | R17 built | A1.1's labels, A3.1 |
| deploy Lab, then Studio (with R41's before-and-after gallery) | R38's verifications PASS; R41 verified by looking | A6.2, the PI's direction |

## 4. The order

1. **Now, in parallel:** the verifiers (R01, R12, R19, R22), and the two builders that need no merge (R23 = W035, R02 = W036).
2. **As each verifier passes:** its merge (the harness through its train), then that repository's next item
   (R05 or R06; R13 with R14 and R15's staging; R20 with R21; R32 or R33), and R16 at the first free slot.
3. **When R02 is built:** R03 (the driver), then R04, R07, R08, R09, R10 in parallel where their files are disjoint.
4. **The plugin line** (R31, R24-R30) runs the whole time, one at a time; R36 follows it.
5. **The Studio line** (R41 = W037, then R38's verifications) runs beside the rest; R08's harness UI takes its tokens from R41's design file.
6. **Last:** R11's cold reproductions, R39's docs-truth passes, then one full audit.
