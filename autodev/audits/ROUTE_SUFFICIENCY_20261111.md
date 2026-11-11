# Route sufficiency check, 2026-11-11 (RULES item 19)

An independent, read-only reader. Read: GOALS.md and ROUTE.md whole; the last row per test in ledger/scores.tsv and
per gap in ledger/gaps.tsv (117 open gaps name a scored test); waves.tsv; decisions.tsv (D-014, D-025, D-031); RULES
16-19; 0004-audit.md:124-131 (the ten-step map); W028.md; W031.md. "rN" = scores.tsv line N. **Strict** = only the
numerator parts an item's own text delivers; where the text leaves a part open, the row says what it must state.
Inferences are labelled.

## 1. Verdict

- **If every item lands as written:** 18.77, mean 0.938, by the formulas. HAPPY is reachable only if every item lands
  in full, A3.4's four stages at scale and A4.2's five tools included. The slack is 0.77, not the 1.9 of ROUTE line 10.
- **With the stops ROUTE line 11 plans** (A3.4 at two stages, A4.2 at three tools): 17.9994, mean 0.89997. **Not
  HAPPY**, 0.0006 short. Read A4.3 as r17 does (8/9) and it is 18.11. Also leave A2.1's fourth stage unpromoted: 17.75.
- **No test is projected below 0.5.** Below ROUTE's assumed 1.0: A6.3 0.667, A4.3 0.778, A1.2 0.800, A3.1 0.800,
  A7.1 0.800.
- **ROUTE §1's "now" column is stale** for A2.1 (says 2/4; r34 is 3/4) and A3.2 (says 1/4; r33 is 3/4). The 7.19
  tally (line 9) already uses the ledger. R16, R19 and R22's moves are already inside "now": do not count them twice.

## 2. The 20 tests (bar: each ≥ 0.5 and the 20 together ≥ 18.0; "plan" = what ROUTE lines 10-11 assume)

| test | now | bar | items | projected if all land as written | missing |
|---|---|---|---|---|---|
| A1.1 | 0.625 = 5/8 (r38: SAMBO 1-4, C46 2) | 0.5; plan 1.0 | R14 R21 R35 (R01, R02 run 1 counted) | 5+1+1+1 = 8/8 = **1.000** | GAP-C103 (no owner) can leave C46's chained stage 4 with no matching library (inference). R35 names no plugin, though the test says "DE, DA and the plugins the design admits"; r38 counted SAMBO's stage 4 on DE + DA alone |
| A1.2 | 0.700 = 7/10 (r39; steps 1, 3-8) | 0.5; plan 1.0 | R02 run 2, R03 | 7 + step 10 (cellchat through prof@scprofile, R02 run 2) = 8/10 = **0.800**; 0.900 if step 2 "declared upstream" is accepted; 1.000 also needs step 9 | **Step 9** (pathways, trajectories): no pathway plugin (GAP-042, no owner), and no item names a trajectory plugin a design admits, so R02's "9/10" does not follow. **Step 2**: the test reads "declared upstream (alignment)" (GOALS:91); pass 0004 scored CellBender run outside the family as 0; no D- row admits ambient removal. R03 is in its last fix round |
| A1.3 | 0.600 = 3/5 (r35) | 0.5; plan 1.0 | R05; R20 (W046); R16 counted | 3+1+1 = 5/5 = **1.000** | scQC's and scProfile's credits are builds of older heads (98504bd, 27e254f, r35); no item rebuilds them at the final `main` |
| A2.1 | 0.750 = 3/4 (r34) | 0.5; plan 0.75-1.0 | R34 + the PI's promotion | 3+1 = 4/4 = **1.000** | If the PI re-promotes stage 3 (§3 row 1), no item reproduces the new promoted run: 3/4. R34's prediction must name the spreads that GAP-C35 and GAP-057 (no owner) say are unnamed or do not hold |
| A2.2 | 0.125 = 1/8 (r9) | 0.5; plan 1.0 | R39 | 8/8 = **1.000** if the final audit's draw finds nothing false (an outcome, not a deliverable) | R39 waits for each repository's last item, so scProfile's draw comes after R36, the largest item |
| A2.3 | 0 = 0/4 (r10) | 0.5; plan 1.0 | R11 | 4/4 = **1.000** | R11's waits-for omits R05 (GAP-127: a cold reproducer meets a red harness suite); §4 runs R11 last, so the order holds |
| A3.1 | 0.4125 (r41) | 0.5; plan 1.0 | R14 R21 R35; R13 R20 R42 R44 R24-R27 R06 | 0.5 x 8/8 + 0.5 x 3/5 (scAnno done, scQC R13, scIntegrate R20) = **0.800**; 1.000 needs scProfile and the harness | **The fixture half.** scProfile's fixture "pins --organism human --assay cell and accepts a refusal" (r11; GAP-054, no owner). The harness's reaches only "init + stack dump" (r11; no item, no gap row). R42's "+0.1" also needs R44 and R24-R27 (D-025) |
| A3.2 | 0.750 = 3/4 (r33) | 0.5 | R32 inside R24 | 3+1 = 4/4 = **1.000** | R24 waits on R23 (held). "Refused by name" counts, so abundance refusing the interaction with its reason suffices |
| A3.3 | 0.800 = 4/5 (r13) | 0.5 | R33 | 4+1 = 5/5 = **1.000** | Risk: GAP-C104 (scQC silently accepts single cells denoised elsewhere) can be read as a silent default. Its first move names "R13's next run"; R13's text does not |
| A3.4 | 0 (r25) | 0.5; plan 0.632 | R15 (+R43, R03) | 1,263,676 x s / 4,000,000: s=1 0.316, s=2 0.632, s=3 0.948, s=4 min(1, 1.264) = **1.000** | Stage 1 needs R43 (absent from R15's waits-for), which waits for W041 (last fix round). Stage 1's `dbr` threshold is the PI's (W031.md:127-128), not in §3. Stage 2 needs a tree for the cohort's tissue (C46's needed the PI): no step |
| A4.1 | 0 (r15) | 0.5 | R23 R31 R24-R30, with R42 R44 | 2 + 7 = 9/9 = **1.000** | R23's "2/9" does not follow alone: by D-025, A4.1 counts only when W040 and the held-out waves are done. R23 is held; R31, R45 and R24-R30 wait on it; nothing says what releases it |
| A4.2 | 0 (r16) | 0.5; plan 0.6 | R36 | 0.2 a tool: 3 = 0.600; 5 = **1.000** | Outside sources no item names: the scRNA-tools catalogue, each tool's published example and its data |
| A4.3 | 0.333 = 3/9 (r17) | 0.5 | R24-R30, R45 | R24-R30 = 7 plugins, 2 (scenic, velocity) already count: 3+5 = 8/9 = 0.889 by r17's reading; by RULES 18 (a source is a DOI from its own record) 7/9 = **0.778** | ROUTE's "+6/9" does not follow: `de` (no pin, no DOI) and `cellchat` (a pin, no DOI) are in no DOI/pin item. Under RULES 18, r17's 3 count 0 until DOIs land |
| A4.4 | 0.500 = 2/4 (r18) | 0.5 | R10 | 2+2 = 4/4 = **1.000** | - |
| A5.1 | 0.923 = 12/13 (r19) | 0.5 | none (kept) | **0.923** | GAP-126 (no owner): the sealed run A5.1 is scored on holds entries it did not write; there is no second run to fall back on (GAP-047) |
| A5.2 | 0 (r20) | 0.5 | R09 | 0.5 x h/h + 0.5 x 1 = **1.000** if every hypothesis carries all three parts | The follow-up "through the loop" is a job; R09's size lists none |
| A6.1 | 0 (r21) | 0.5 | R08 | 5/5 = **1.000** | R08 takes its tokens from R41 (§4.5), which moves no test. How a local UI "follows the run" on the cluster is unstated |
| A6.2 | 0 (r22) | 0.5 | R38 | 1+1 = 2/2 = **1.000**; W028's Run card shows uns/scintegrate/provenance (W028.md:23), which the final object keeps | W028's verifier is stopped by the account's weekly limit until 2026-11-14T01:00Z (BLK-010, waves.tsv); no item. W017's merge deploys Lab, so part 1 needs the PI's go, which §3 ties to R41's gallery. If "the run" means the whole stack, GAP-P20's harness half has no owner (R38 is Lab and Studio) |
| A6.3 | 0.667 = 2/3 (r23) | 0.5 | R04 (R43 also claims it) | part 2 needs a run of a request Service wrote; R04 is S with no job: 2/3 = **0.667** | R04 must name the delivery and the job. R43's claim does not follow: a published object is not a Cell Ranger or CeleScope delivery |
| A7.1 | 0 (r24) | 0.5 | R07 | 4/5 = **0.800** unless a failure occurs to recover from; R07 plants none | The cold agent needs cluster rights and the layout rules, inside "the harness's skills" |

## 3. Sums, shortfall, holds

- **Strict sum:** 14 x 1.000 + A1.2 0.800 + A3.1 0.800 + A4.3 0.778 + A5.1 0.923 + A6.3 0.667 + A7.1 0.800 = 18.768.
  Line 11's stops cost 0.368 (A3.4: 1 - 0.632) + 0.400 (A4.2): 17.9994.
- **Shortfall against ROUTE's 19.92** (= 19 x 1.0 + 0.923): A1.2 -0.200, A3.1 -0.200, A4.3 -0.222, A6.3 -0.333,
  A7.1 -0.200, total -1.155. Even with every ambiguity settled for the route, A4.3 stops at 7/9: 19.70.
- **Two holds carry most of the remainder** (inference from the waits-for column). **R03** (W041 and W042 in their
  last fix round; W042's re-check FAILED) gates 2.4-2.9 of the planned 18.0: A6.1, A7.1, A3.4 via R43, A6.3 part 2 and
  A1.2 step 2. **R23** (held, release unstated) gates about 2.3: A4.1, A3.2's 0.25, A4.3's +0.444, A4.2 via R36.
- **No cycle.** R44 waits on R23's fix round 2 (built) and R23 on R44's residue; the route should say R23 is released
  when R44 merges.

## 4. Open gaps on a scored test that no item names

89 of the 117 are named by no route item and no route wave's gap list; 32 of the 89 are covered by plain content.

**Would cap or risk a score:**
- **GAP-042 (A1.2):** no pathway plugin; caps step 9 (-0.1) unless a trajectory plugin runs in A1.1.
- **GAP-054 (A3.1):** scProfile's fixture never reaches DE or abundance; caps scProfile's tool credit (-0.1).
- **GAP-C103 (A1.1, A3.1):** through the harness, scAnno's embed names libraries by file stem, so a chained stage 4
  keyed on the library column finds none (inference): -0.125 and -0.0625 on C46's stage 4.
- **GAP-C35, GAP-057 (A2.1):** varying outputs' spreads unnamed or not holding; a risk to R34's reproduction (-0.25).
- **GAP-126 (A5.1):** the scored run's seal holds foreign entries; a risk to 0.923; the fix is S, records.
- **GAP-C104 (A3.3):** scQC silently accepts single cells denoised elsewhere; -0.2 if read as a silent default.
- **GAP-026 (A3.3):** single cells get no data-derived floors; a risk only if the fallback is read as a silent default
  (inference).
- **GAP-C87 (A4.1):** velocity's migration meets two portability checks; only its own first move names
  "velocity's A4.1 wave", R24-R30's text does not.
- **GAP-C53 (A6.2):** Lab's split drops cells whose split value is missing; a risk only if the final object's split
  column has missing values (cannot be computed from the route).

**No cap by the formulas (47):** A1.1 C105, C70 · A1.2 058 · A1.3 C27, 125, C23, 036 · A2.1 C07, C12, C32, C33, 112,
118, C69, C61, C67, C15, 106, 124, 021, 035, C11, C50, P18 · A2.2 059, 104, C25 · A3.1 C101 (a limit of the measure, to
state in the audit), C13, C68 (a report limit), 053, 007, 121, 027 · A3.2 C48 · A3.3 011, C37, C18, C24 · A4.1 C47, 114
· A4.4 123, C56, C77 · A5.1 048, 047 · A6.3 P07.

**Covered by plain content (32):** R03 002, 015 · R05/R16/R20 107 · R34 055 · R39 052, 109, 105, 116, 009, 129, P08,
P17, 117, 115, C16 · R11 004 · R13/R16/R20 023, C26, C45, 120, 032 · R36 046 · R24-R30/R45 045 · R38 014 ·
R17 C106-C108 · R09 012 · R08 013 · R06 C62 · R02 041, 043.

## 5. Tests whose bar waits on the PI

- **In §3:** A2.1's stage-4 promotion is askable when R34's run seals; R22 and R02 are merged, so it can start now.
  A2.1's stage-3 re-promote-or-keep is askable when W039 merges; re-promoting costs 0.25 unless P8 is added. A6.2's
  deploy is askable only after R41 is verified, though the formula needs no Studio deploy: ask for Lab's go (W017's
  merge is the deploy) as soon as W017's re-check passes. No score depends on C46's tree.
- **Missing from §3:** the scale cohort's `dbr` threshold (W031.md:127-128, "the PI's") gates A3.4's stage 1 (0.316)
  and is askable now (R15's staging is done, ROUTE:72). The reading of A1.2's "declared upstream (alignment)" for
  ambient removal gates 0.1; the PI's reading wins (GOALS:11); askable now. A tree approval for the scale cohort's
  tissue, if anno@scanno needs one as C46's did (inference), gates stage 2 (0.316). D-031's by-name question applies if
  a single-cell cohort arrives already denoised (conditional).

## 6. Cheapest additions (P1-P6 add +1.055: strict 19.82; with line 11's stops 19.05, mean 0.953)

| # | repository | item | moves | size | waits for |
|---|---|---|---|---|---|
| P1 | harness | R04 runs one Service-written request (the CeleScope or Cell Ranger delivery + questionnaire) as SAMBO's or C46's chained run, under a pre-declared job, so no extra cohort job | A6.3 part 2, +1/3 (+0.333) | S | R03, R04 |
| P2 | scProfile | through the maker: `de` gets a DOI (with its own record's title and year) and an exact upstream pin; `cellchat` gets its DOI | A4.3 +2/9 (+0.222) | S | nothing; R45 checks it when it lands |
| P3 | harness | R07's trial meets one planted failure, declared in its protocol before it starts, that the skill must detect, fix and resubmit | A7.1 act 3, +1/5 (+0.2) | S, inside R07 | R07's skill |
| P4 | scProfile | GAP-054: the fixture's dev point runs DE and abundance on the built environment and accepts no refusal; `sch dev check fixture_a` green | A3.1 +0.5 x 1/5 (+0.1), with the leak half | S | R31, if run on the cluster |
| P5 | harness | the fixture's axes reach a harness pipeline beyond init and a stack dump (a mount's run, or the driver's plan, on the two-shape fixture) as a `sch dev check` point | A3.1 +0.1 | S | R06 |
| P6 | harness + scProfile | R35 or R02 run 2 names a trajectory plugin its design admits (pseudotime or velocity) and runs it through prof@scprofile; failing that, a pathway plugin through the maker (GAP-042) | A1.2 step 9, +0.1 | S (M if a new plugin) | R35 or R02 run 2 |
| P7 | scAnno | GAP-C103: embed takes the library name from the object or the manifest, never a file stem, with a test that fails at `main` | protects A1.1 +1/8 and A3.1 +1/16 | S | W044's fix round 2 |
| P8 | SAMBO records | if the PI re-promotes stage 3: a pre-declared reproduction of the new run; GAP-126's foreign entries removed under recorded unsealings | protects A2.1 +1/4 and A5.1's 0.923 | S + 1 job | the PI's stage-3 answer |

A1.2's step 2, by the PI's reading, adds 0.1 more.

## 7. Candidates to drop or defer

- **R40:** moves no score (C46's stage 2 already counts, r38) and blocks nothing; R14, R21 and R35 re-run C46's
  stages anyway. Drop.
- **R17:** moves no score by any formula; R21 runs with draft labels and the tree approval gates nothing. End it at its
  last fix round.
- **R06's commit-gate part:** speed only; moves no score and blocks nothing. Defer unless it costs a few calls.
- **R45 as its own run:** adds nothing to any numerator, and by RULES 18 it can lower A4.3. RULES 18 names it, so fold
  it into R24's first step.
- **R41 (W037):** moves no score; the PI's direction, so the PI's call. Take it off A6.2's and A6.1's path (§3's
  deploy, §4.5's tokens).
- **R36's 4th and 5th tools, and R15's stages 3-4:** safe to stop as line 11 plans only with P1-P6; without them the
  planned route ends at 17.9994.
- **Keep R02 run 2:** it gives A1.2's step 10 and protects SAMBO's stage 4 under A1.1's words.

## 8. Not checked

No tool repository was opened, so the feasibility of each item's code is unchecked. Also unchecked: which plugins the
designs of SAMBO, C46 and the scale cohort admit; whether the r35 builds still pass at today's `main`; whether C46's
chained stage 4 really meets GAP-C103 (inference); W039-W047 and IMPROVEMENT_PLAN.md beyond the lines cited; BRIEFS,
ATTACKS and the DIAGNOSIS files. No score was re-measured.
