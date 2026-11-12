# Direction review, 2026-11-12 (RULES item 21b)

By the direction reviewer (a Fable agent, read-only on every repository). Read: GOALS, ROUTE, STATE, RULES (tier I, the 2026-11-11 block), the
sufficiency check, scores.tsv, the waves.tsv rows of 2026-11-11 and 2026-11-12, the open gaps on the nine tests, ATTACKS, BRIEFS 0, 1, 2a, W054
to W056. Measured here: `passrate.py`, `costs.py --since 2026-11-11`. "(inf.)" marks an inference. The tally is 7.89 of 20; HAPPY needs 18.0.

## 1. The queue: the next 12 Opus slots, to act on line by line
Running now, not counted: the builders of W056's fix round 1 and W055's second half. A failed check takes the next slots (fix round, lean re-check).

1. **W056's lean re-check** (harness). Beside it on the cluster, in order: a ten-minute preflight of the regenerated subset job (change 3,
   section 3), the subset, the first cohort's full chained run, the merge. A1.2 to 8/10; it releases items 8 to 10 and the scale cohort.
2. **R31, a builder** (scProfile: the isolated groups' locks, a cluster build, the self-test; S). ROUTE's own row says R24 waits for R31, and
   W055 was launched without it: W055's dev-suite gate cannot count until this lands (inf.). Its build job is the slowest step on the plugin line.
3. **W055's verification** (scProfile), bounded by check 10 (change 4). A3.2 to 4/4.
4. **Cold reproduction 1**: the first cohort's stage 1 from the record and the docs alone (a fresh agent writes the job, the coordinator submits
   it). A2.3 +0.25. Its hand-back lists every doc line that misled it.
5. **The grade wave, a builder** (scProfile, stacked on W055's head): the blind grade of decoupler, scenic and velocity, recorded first; then only
   their comment hits through the prose verb and their sources through the source stage. A4.3 to 6/9; the repository's conform green, so A4.1
   can count 3/9 on the dev-suite job and A3.1 gains scProfile's 0.1 (with R46).
6. **One lean verification of the scProfile batch** (R31 and the grade wave).
7. **W050's lean verification** (scAnno: the library key the second cohort's stage 4 needs).
8. **R07, the skill's builder** (harness, to design D1). Item 9 is its verification; no verifier is spent on it.
9. **The cold-agent trial on the second cohort**: its chained run from one request, one planted failure declared before it starts. This one run
   is R14 + R21 + R35 and A7.1's trial: A7.1 up to 5/5, A1.1 +3/8, A3.1 +0.19.
10. **R08, the data-layer builder** (harness, to the designer's file D2; the Fable designer builds what is seen; a Fable check by looking, as
    W053 had). A6.1 up to 5/5.
11. **Cold reproduction 2**: stage 2. A2.3 reaches its bar.
12. **R09 run 1, a builder** (harness + scProfile, to design D3): hypothesis records only. A5.2 to 0.5.

**Beside them, with no Opus slot:**
- a. **Docs-truth sweeps by a Fable reviewer**, read-only, one repository a run: Studio, Lab, scQC and scAnno first (their route items are done
  or nearly). Each returns the false lines with the corrected text; a verifier's pen or that repository's next builder applies them; a seeded
  draw of 12 claims by another agent writes the row. A2.2 +0.125 a repository; three more reach its bar. (Item 21d's reading is the coordinator's.)
- b. **A6.2's missing half is a measurement, not a wave** (scores.tsv, the coord row of 2026-11-11T14:07Z: "no cohort object was converted"): the
  first cohort's real final object through Lab's converter, opened in the deployed Studio. Fold it into W057's independent check. +0.5.
- c. **Cluster only:** the scale cohort's parts and a two-library stage-1 subset the hour W056 merges; a full stage-4 run of the first cohort at
  scProfile's `main` after W055 (for the PI's promotion); stage 3's reproduction if re-promoted.
- d. **Designs D1 to D4** (section 2), at most two Fable agents at once.

If every line lands: about +4.7 from the slots and +1.4 beside them, a tally near 14.0; at the measured first-pass rate, about half the slot part (inf.).

**Stop, strike or shrink.**
- No further Opus slot for Studio or Lab unless a user can get a wrong result. W054 was right to run (a live wrong result) and took six Opus
  runs and 73 M of context reads for no score; W057's check should be a Fable check.
- Move down scIntegrate's installer (STATE's queued item 6) and R05: A1.3 is over its bar, and each is 0.2 for a builder and a verifier. Park
  R33 and R13's run 3 the same way (A3.3 is at 0.8). Keep the two planned stops (A3.4 at two stages, A4.2 at three tools).
- Shrink R24 to R30 as item 5 says: three blind grades in one run give the maker's base rate on three plugins, and the last three (cellcycle,
  liana, pseudotime) stay as the before-and-after test. This changes the pre-decider's "one at a time"; the PI is told.
- Shrink every verification to about 110 calls, starting from the builder's proof table (change 2). W056's took 182 calls and 45 M.
- The coordinator's own session: 660 calls at a mean context of 514 k on 2026-11-11 is 338 M of context reads, as much as 16 builder runs.
  Restart it from STATE once a day (item 9 makes that safe).

**Where the route's order is wrong today.**
1. ROUTE section 4, step 6 puts R11 and R39 last. They are the cheapest points under a bar (A2.3 at 0.25 a slot; A2.2 with no Opus slot), need no
   merge in a settled repository, and a cold reproduction is the cheapest detector of false doc lines and of what R07's skill must say.
2. R24 ran before R31, against R24's own "waits for"; R31 has no wave.
3. R24 to R30 one at a time, while D-025 keeps A4.1 at 0 until three named plugins lose their comment hits (W055's as-built note).
4. R14, R21 and R35 as the coordinator's jobs, and R07's trial as a second, later cohort run. One run can be both.
5. R08, R09 and R36 wait for R03 or for the plugin line even for their designs. A design takes no Opus slot.
6. R38's remainder names GAP-P20 and W057 for A6.2; the formula's missing half needs neither (b. above).

**The nine tests under their bar, worst first.**

| test | now | the path to its bar | blocked today by | cost |
|---|---|---|---|---|
| A2.3 | 0 | two cold reproductions (items 4, 11); four for 1.0 | only the route's order | 2 to 4 slots; 4 small jobs |
| A3.4 | 0 | W056 merged; the parts step on the scale object; a two-library subset of stage 1; the PI's threshold; stage 1 (0.316); stage 2 (0.632) | W056's R3 (the parts step dies on an object written by the field's own library, as this cohort's is); the PI's threshold | 0 to 2 slots (inf.); tens of cluster hours |
| A4.1 | 0 | R31; W055 verified and its dev-suite job; the grade wave (conform green, 3/9); two more full migrations (5/9) | R31 unbuilt; D-025 | 8 to 10 slots; 3 or 4 dev-suite jobs: the dearest bar |
| A4.2 | 0 | design D4 (the draw rule and the draw); three conversions by agents alone (0.6) | the maker's known defects (GAP-C126; no verb for a figure source's column names); waits for the grade wave | 3 to 5 slots; a job each |
| A5.2 | 0 | design D3; item 12 (0.5); one follow-up through the loop (1.0) | a slot and the design | 2 to 4 slots; 1 job |
| A6.1 | 0 | design D2; item 10; a Fable check | W056's merge; the designer is on W057 | 1 to 2 slots; no new cluster run (inf.) |
| A7.1 | 0 | design D1; items 8 and 9 | W056's merge; W050 | 2 slots; the second cohort's chained run |
| A2.2 | 0.125 | sweeps (a.) on three settled repositories | only the route's order | no Opus slot; a pen |
| A4.3 | 0.333 | W055 (three plugins with a DOI and an exact pin; by the strict count still 3/9); item 5 (6/9) | "one at a time" | inside items 3, 5, 6 |

**What waits only on the PI (one report).**

| step | askable | recommendation |
|---|---|---|
| stage 3: re-promote or keep | now | re-promote from the run at `main` (STATE's own recommendation) and submit its reproduction the same day, so A2.1 stays 3/4 |
| stage 4: promote a run | after W055 merges | promote the first full run at that `main`, not the earlier one: W055 changes how abundance takes its base level (inf.) |
| A1.2 step 2: does "declared upstream by name" count? | when W056 merges | yes (+0.1) |
| the scale cohort's residual-doublet threshold | with the subset's numbers | none possible before the numbers |
| told, not asked | - | three blind grades in one run; the PI's "do not block anything if unnecessary" written into the verifier's brief; docs sweeps by Fable reviewers; the second cohort's tree shown as a walk table |

## 2. The design queue (item 21a)
| # | wave | the ONE question | the design agent reads |
|---|---|---|---|
| D1 | R07, the cohort-run skill and its trial | What is "recover" as a closed list: which failures the skill must tell apart (a pins miss, an absent input, a tool's refusal, a kill at the time limit, a prediction that missed), the one act allowed for each, the request being the only thing the agent may change; and through which command a cold agent submits. Answered wrongly: a skill that retries, or a planted failure it cannot classify | GOALS A7.1; the sufficiency check's P3; W049 and W056 (the driver's verbs, the pins); `gate.py`; ATTACKS 12, 33, 47 |
| D2 | R08, the harness UI (the PI's rule anyway) | Where the UI reads a run's state when the run is on the cluster and the UI is local: a read-only mirror of the run folder, refreshed by the existing mirror, no server on the cluster; and what turns plain language into a request: a filled request shown as the plan, free text only choosing among analyses the catalogue declares | A6.1's five acts; Studio's design file (R41); the driver's request schema, plan and ask output; `pbs_mirror.sh` |
| D3 | R09, hypothesis records | Is a follow-up a typed request fragment the driver validates unchanged (a plugin, a contrast, a subset), with the falsifying test as a prediction line of its generated job, so "executed through the loop" is one graded job | A5.2 and G5; scProfile's claims ledger and docs/PAPER_TEST.md; the request schema; RULES 16 |
| D4 | R36, the draw rule (design only, now) | The sampling frame and the exclusion rule, written before the draw, that keep five tools convertible in principle (a published example on public data that fits the standard queues; installable) without fitting the rule to what the maker does well; and what "reproduces its published example within a declared tolerance" means per kind of output | A4.2; the plugin-maker skill; MIGRATIONS (three blind grades); RULES 16 |
| D5 | the maker, after item 5's grades (the grade comes first) | Which of the grades' failures are one maker defect to fix once (the inventory's empty-submodule read; the worksheet's vocabulary; a figure source's column names) and which are a plugin's own debt | W055's grade and the three new ones |
| D6 | the driver's generated check, only if item 1 fails (its sixth failed check) | Does a job compare against the machine it was generated on, or state expectations the submit recipe records where each fact exists | W049, W056, ATTACKS 33 |

**No design needed** (a design step here adds nothing): W056's and W050's re-checks; W055's verification; R31 (the facts are the cluster's, and
the preflight finds them); the cold reproductions; item 5 before its grades; the two installers (the pattern exists in three tools); R10; the
docs sweeps; every cohort job. R04 (S) needs only THE CLASS in its brief (Service's request read as a closed schema) and a proof table.

## 3. Why verifications fail
From the ledger's outcome cells (and the wave files of W054 to W056). The classes are my reading (inf.). 23 failed checks carried 52 blocking reasons.

| component (waves) | failed checks | DESIGN | BUILD | ENVIRONMENT | OUTSIDE |
|---|---|---|---|---|---|
| scProfile's maker (W035, W047) | 5 | 3 | 8 | 0 | 0 |
| the driver (W041, W042, W049) | 5 | 8 | 3 | 2 | 0 |
| scAnno's tree rule (W044) | 3 | 2 | 4 | 2 | 0 |
| scQC (W043, W048) | 3 | 2 | 4 | 0 | 0 |
| scIntegrate (W046) | 1 | 1 | 1 | 0 | 0 |
| Lab (W017's last re-check; W054 twice) | 3 | 2 | 1 | 2 | 1 |
| the harness (W052; W056 with its job) | 2 | 0 | 3 | 1 | 1 |
| scProfile (W055, handed back half built) | 1 | 1 | 0 | 0 | 0 |
| **all** | **23** | **19** | **24** | **7** | **2** |

| kind | reasons | what it looked like | cure |
|---|---|---|---|
| K1: a set stated by its cases (DESIGN) | 15 | what is pinned, and when an answer may apply (8, the driver, over five checks); what counts as a cohort's value (5, until D-040 bounded it); what a reader may follow (2, Lab) | change 1 |
| K2: a judge never shown right and wrong (11 BUILD, 2 ENVIRONMENT: the deployed consumer) | 13 | W056's check script tried only on an empty run; a subset predicted identical with no arithmetic; a parts step fed only hand-made fixtures; a fixture read-back that stays green with its factor emptied; a graded line that cannot fail; a field the deployed Studio reads with one fixed sentence | change 2 |
| K3: an input spelled around, spliced or tampered (BUILD) | 8 | a ban on one exact name; a version spliced raw; a repeated key in a record only a developer writes | change 4, and one merged ATTACKS row |
| cluster facts (ENVIRONMENT) | 5 | no git where a job runs; pins of the generating machine; two jobs that missed on a cohort's own data | change 3 |
| the rest | 11 | a search run as engineering (2); a contract's version (1); size (1); doc lines and slips (5); outside (2) | - |

The cures are already measured here: the two redesigns by construction held at their first check on the designed part (W049's one set "by one
parser for run, plan and job, at every moment"; W054's run section, "holds by construction"), and the one fix round that handed back a truth
table (W054's second: 25 states, 52 openings in the deployed Studio) passed its lean re-check on the verifier's own states.

**Change 1, a section every registration and every fix-round brief carries** (written by the design step where section 2 names one, by the
coordinator otherwise):
```
THE CLASS. One sentence naming the set this change must hold for, as a rule and not as cases ("every file a tool reads
between the plan and the seal", not "the request and the design sheet"). The ONE place in the code that defines the set.
The ONE test that walks the set from that place, so a new member needs no new test. What is outside, as counted limits.
A fix round's brief restates THE CLASS before the failing case: if the failure showed a set stated by cases, the fix is
the rule. A registration that can only list cases goes to a design read first.
THE SIZE. One route item; at most three numbered changes; a change that writes a cluster job is a wave of its own.
```
**Change 2, BRIEFS section 1, HAND-BACK** (replaces SELF-ATTACK's "say which you ran"), with `setup/autodev/proof.py <wave file>`: it prints
`PROOF: n rows, k incomplete` and exits 1 when the section is missing or a RIGHT or WRONG cell is empty; run before any verifier is launched:
```
PROOF TABLE (in the wave file). One row per thing this wave adds that JUDGES: a test, a refusal, a check script's line, a
job's graded line, a prediction, a sentence a deployed app will show. Columns: the judge | a RIGHT input and what the
judge printed | a WRONG input that differs in that one respect and what it printed | who made the inputs (by hand; the
real tool's or library's writer; the deployed build). A judge is done when its WRONG row fails only that judge and one
RIGHT row came from the real writer. A job's rows are two fake run folders graded by the job's own check on the
workstation. A prediction's row shows its arithmetic from the tool's code. A field a deployed app reads has one row per
state of the field, each opened in the deployed build.
```
**Change 3, `gate.py preflight <job>`** (the contract; no tokens, minutes of cluster, run at hand-back):
```
Submits the job file itself with CHECK_ONLY=1 and a ten-minute request on a compute node. Under CHECK_ONLY a job runs
everything it does before its first tool call and stops: its pins, every input and reference run present and readable,
and its check script graded on the reference runs themselves (each reference line must read AS PREDICTED against its
own reference). Last line: PREFLIGHT: OK or PREFLIGHT: MISSED (n). `submit` refuses a job that asks for more than 30
minutes with no PREFLIGHT: OK for the same job md5 and tool commits. The driver's generator and the job template write
the CHECK_ONLY branch.
```
It would have read MISSED on W056's R0 and R1 before a 182-call verification was spent, and on the driver batch's pins gap.
**Change 4, BRIEFS 2a, check 10** (D-041 is in decisions.tsv and STATE only; no verifier is told it today):
```
(10) WHAT FAILS A WAVE (the PI, 2026-11-11: "do not block anything if unnecessary"). FAIL only on: a wrong result a
user can get by a route the tools or the docs offer; rule 1 or rule 2; a sentence shown to a user that is false; a
check, a gate line or a record that can read success on a miss; the registration's acceptance check not met. COUNT and
report with a severity, and do not fail on: a defect that is on `main` too and that this wave neither causes nor makes
reachable; a route that needs a hand-made file or a deliberate hand edit of a record and changes no user's output;
wording. Name for each FAIL reason which of the five it is.
```
By it W054's R1 (on `main` too) is a gap with its own wave and W047's lean re-check a PASS with two gaps, which is what the coordinator did
with both afterwards; W052's reason stays a FAIL (the wave made it reachable).
**Change 5, `passrate.py`'s pattern.** It reads only outcomes that begin "verifier"; W054's and W056's begin "verification", W053's "its
check". Today it prints one first verification for 2026-11-12; there were four. Contract: `^(verifier|verification|its check)\b[^:]{0,60}:\s*(PASS|FAIL|READY)`,
READY counted as PASS; and one more line a day: Opus runs per merged wave.

**To make room.** ATTACKS has 49 rows and its own header asks for one screen. Rows 11, 12, 23, 24, 37, 45, 47, 48 are replaced by the proof
table: drop them. Merge 2, 6, 25, 27, 31, 38 into one row (a value spelled around, spliced or switched off); 8, 14, 26, 32, 33, 42, 43 into one
(an input, an answer or a tool that reaches a step by a channel or at a moment the check does not walk); 5, 16, 22, 35, 36, 41 into two (a
removed value that survives; a record's integrity); 1 and 49 into one. Move 30 and 44 to Lab's own notes. Drop 4, 19 and 20: BRIEFS' SEARCH
block says them. Keep 3, 7, 9, 10, 13, 15, 17, 18, 21, 39, 40. That is 16 rows. In BRIEFS block 0, REMOVED NUMBERS, SEARCH, WALLTIME, SUBSET and
A NEW JOB FILE leave the block every brief carries and go into the registrations they apply to; THREADS becomes one sentence.

## 4. The loop's shape
| measured since 2026-11-11 | n | calls | output | context read |
|---|---|---|---|---|
| a builder run | 58 | 110 | 143 k | 20.9 M |
| a verifier run | 28 | 110 | 119 k | 18.6 M |
| a verifier run under 100 calls (mostly lean re-checks); over 140 calls | 11; 5 | - | 99 k; 153 k | 10.4 M; 32.7 M |
| a fix round with its lean re-check (W054's two) | 2 | 124, 117 | 238 k, 186 k | 19.0 M, 14.5 M |
| a Fable check or designer run (W053's, W057's) | 2 | 49, 44 | 88 k, 108 k | 7.0 M, 6.3 M |
| a wave that failed its first check, whole | 11 | - | - | mean 107 M (73 to 186); 3 to 11 Opus runs |
| a wave that passed it, whole | 3 | - | - | 25, 39, 54 M; 2 to 3 runs |
| all agent runs | 109 | - | 14.4 M | 2,022 M |

First pass, waves built since 2026-11-11: 4 of 14 by `passrate.py`, 4 of 16 with W054 and W056. A first fix round's re-check passed 4 times in 10
(my count from the ledger). So a wave costs 2 + 0.75 x 2 + 0.75 x 0.6 x 2 = 4.4 Opus slots today. Builder runs per wave: 2.3 (55 over 24
waves), against the diagnosis's estimate of 1.3. The tally moved +2.04 for 14.4 M of agent output; at that rate the 10.1 points left cost
about 70 M, three times the diagnosis's estimate (inf.). The shape, not the cap, is what to change.

| option | costs | reaches | on the numbers |
|---|---|---|---|
| (i) a design read by a Fable agent before the build | about 6 M of context reads; no Opus slot | K1 and the other DESIGN reasons: 19 of 52, and the ones that repeat over rounds | pays in tokens when it saves one fix round in three designed waves (6 M against 14 to 19 M); in slots it always pays |
| (ii) a proof table before any verifier is spent | 10 to 20 builder calls, about 3 M (inf.) | K2 (13 of 52); with the preflight, the 5 cluster facts | the measured case passed its re-check in 48 calls |
| (iii) smaller waves | one more registration | W055 (seven steps, half built); W056 (five; 208 calls and 54 M; its verifier 45 M) | a call costs 161 k of context under 100 calls a run, 255 k over 170 |

**Recommended: one shape that holds all three and cuts the second fix round.** A design read where section 2 names one; a build of at most
three changes carrying THE CLASS and a PROOF TABLE; `proof.py` and the cluster preflight; ONE verification of about 110 calls under check 10;
at most ONE fix round with a lean re-check; a second failed check goes to a design read (item 21a's own words), never to a patch.
**Expected.** First pass from about 25 % to at least 50 %: of the 12 waves that failed first, six (W044, W046, W048, W049, W054, W056) failed
only on K1, K2 or cluster facts (inf.). A fix round's re-check from 40 % to about 60 %, because its brief states THE CLASS. Then a wave costs
about 2 + 0.5 x 2 + 0.5 x 0.4 x 2 = 3.4 slots, and 12 slots carry 3.5 waves where they carry 2.7 today.
**Wrong if, in a week** (read with the corrected `passrate.py`): fewer than four of the first eight waves registered with THE CLASS and a proof
table pass their first check; or K1 is still a quarter of the blocking reasons in designed waves; or Opus runs per merged wave stay at 4 or
more; or an Opus slot waits idle for a design more than two slot-hours a day; or a wave merged under check 10 is later shown by a job or an
audit to give a wrong result (one case reopens the bound).

## 5. Not determined
- No tool repository was opened. Whether the prose verb and the source stage run on a held-out plugin straight after its blind grade is inferred
  from W055's as-built note (abundance did exactly that). Whether abundance's group needs R31's lock on the cluster is ROUTE's claim, not measured.
- The 52 classes come from outcome cells, not from each wave's registration (W054 to W056 excepted). 14 agent runs since 2026-11-11 (239 M of
  context reads) carry no wave in `costs.py`'s table.
- Cluster hours per run; what is left of the week's token budget; whether a cold trial may run on a Fable agent; whether anything but not
  having been tried stands between the first cohort's final object and Lab's converter.
