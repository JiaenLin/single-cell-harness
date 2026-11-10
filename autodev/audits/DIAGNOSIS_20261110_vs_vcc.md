# Diagnosis, 2026-11-10: why this loop did not reach efficient, sustainable autonomous development

Asked by the PI: "diagnosis compare to vcc harness, why this project's development harness can not reach efficient and
sustainable autonomous development". Measured from the session transcripts (API usage fields), the task outputs, the
ledgers and the VCC devharness folder (`~/Desktop/developing/my_virtual_cell_model/devharness`). Cache reads are the
context re-read on every call; output tokens are what the model wrote. How the account's weekly limit weighs them is not
known to me.

## 1. The measured burn

| | autodev, 2026-11-09 (06:31Z to 16:00Z, one day) | VCC, 2026-10-14 to 11-10 (27 days) |
|---|---|---|
| API calls | 25,648 (coordinator 1,802; agents 23,846) | 126,972 |
| cache-read tokens | 8.65 B (coordinator 0.91 B; agents 7.74 B) | 65.8 B; 2.4 B per day; peak 5.2 B (11-07) |
| output tokens | 38.8 M (coordinator 3.4 M; agents 35.3 M) | 177 M; 6.6 M per day; peak 17.2 M (11-08) |
| agent launches | 90 in one day | 757; 28 per day |
| per agent | median 0.44 M output, 82 M cache-read; the big builders 1.0-1.4 M output, 0.2-0.4 B cache-read | — |
| outcome | 29 waves, 15 merged, 3 done; audit 0 of 20 after three passes; 55 of 169 gaps closed | one scalar moved (the four-board mean, stacked) |

One autodev day cost 3.6x VCC's average day and 1.7x VCC's heaviest day in context, and 2.3x VCC's heaviest day in output.
The account's weekly limit is shared: VCC itself ran in UNLIMITED mode at 12-17 M output a day on 11-06 to 11-09, so the
loop started with part of the week already spent, and stopped at 15:57Z on its first day.

## 2. The causes, in order of weight

1. **The verifier ratchet has no price.** Every wave is verified by an adversarial agent whose success is a hole found,
   then re-verified after each fix. 52 verifier-FAIL rows over 29 waves; W013 and W017 went five rounds each; each round
   re-clones, builds a venv and reruns the full suite (about 0.5 M output a round). The verifier was usually right (it
   caught the AST-diff carry-over, planted terms, option smuggling), but nothing bounded the rounds until the PI's
   throttle. VCC verifies by a NUMBER on a registered board, and audits periodically (a candidate audit every 6 h), not
   per change.
2. **The one VCC rule that mattered was not carried over.** VCC's tier II row AGENT USE holds the owner's corrections of
   10-26 ("reduce the agent use. you take turns"), 10-27 ("the agents are just wasting all resources") and 10-29 ("do not use
   so many agents if you can not handle"): at most about 2 builders in flight, the reasoning the coordinator's own, the
   mechanical tails on shell machinery. This loop took rules 3 and 5 and then set its own cap, 5 builders plus 4 audit
   agents, and ran at it.
3. **Nothing watches without tokens.** VCC's mirror, dispatcher, feeder, registry and Monitor poll the hosts, fire reads
   when a run seals, and feed the next wave, as shell scripts; a day of VCC progress is GPU hours. Here every PBS read,
   hand-back, grade and merge is a coordinator turn in a context of about 0.5 M tokens (1,802 turns, 0.91 B cache-read in
   a day), and the transcript (26 MB) compacted repeatedly; the ledgers carry only part of what each compaction drops.
4. **The goal is 20 binary tests, not one number.** VCC has one scalar (the four-board mean against P22's 0.362), so each
   wave's value is measurable, "trivial" is definable (no measured gain), small gains stack, and the amplifier can rank
   transfers. Here the auditor grades PASS/PARTIAL/FAIL on 20 tests, 5 of them XL; after 15 merges the score is 0 of 20,
   progress inside a test is invisible, and the loop optimises what it can see: closing S gaps (117 of 169) and removing
   inherited constraints (73 REMOVE rows). The gap register grew 59 to 169 in three passes, because an adversarial
   auditor has no stopping rule either. There is no convergence signal, so "HAPPY" is not approachable.
5. **The gate is slow and rarely informative.** Rule 1(c-d) asks a pre-declared PBS reproduction for every behaviour
   change on a promoted path, and tier IV adds "resubmit after any fix". Of 25 gating runs graded since 11-09, 16
   confirmed their prediction, 1 missed, 1 differed as predicted, and 5 failed on infrastructure (held nodes, missing run
   directories). W013 has 9 PBS ids and was held four times by failing long-queue starts. W021's test-only fix-up was
   resubmitted and reproduced identically: a run with no information. In VCC the run is the product, so its latency is the
   development itself; here it is a proof of no change.
6. **Scope per coordinator.** VCC: one repository, one product, four tracks, two hosts. Here: five tool repositories,
   three platform apps, two cohorts and the cluster, one coordinator, and one checkout per tool on the cluster, so W021
   and W026 waited on each other's checkout.
7. **No budget rule.** VCC has TOKEN MODES, switched only by the owner, and even UNLIMITED says "never more builders than
   I can merge and read". Here the only cost signal was the PI's complaint.
8. **The pre-decider decays in both harnesses.** VCC's owner had to say "add it back" on 11-01 and 11-08; here four
   decided items sat as questions on day one. Both because it is a rule the coordinator reads, not a step the harness
   enforces.

## 3. What worked and stays
Registered predictions before numbers; append-only ledgers with `date -u` stamps; the standing yes with a real gate; the
blocker remover (73 inherited constraints removed in a day); the leak guard; the one-spine rule; the verifier's catches.

## 4. The changes proposed (tier IV, the coordinator's; the PI may redirect)
1. **Agent use as VCC's row:** the coordinator plans, reads and grades itself; at most 2 short-lived builders; the
   adversarial verifier runs once per merge batch per repository (or once a day), not per change; at most 2 rounds, then a
   gap (the PI's throttle, kept).
2. **One number.** Each of the 20 tests gets a measured 0-1 score written by the auditor (A1.1 = stages through the
   harness / 4; A4.2 = tools converted / 5; A3.4 = cells run / 1,000,000; ...). The program's progress is their mean,
   read at every audit; a wave that moves no score is trivial (rule 5's ban) and is not built.
3. **Watching by machinery:** a PBS mirror script and a Monitor that runs each job's grading script on seal and writes one
   verdict line; the coordinator reads lines, not run directories.
4. **A cheaper gate:** a fix-up that changes no file the job executes (decided by the job's runtime-file manifest, as job
   26 does, never by an AST diff) does not resubmit; infrastructure failures are retried by a script, not by a turn.
5. **A budget:** a weekly token budget from the PI; a per-wave cap (about 1.5 M output including verification; past it,
   the residue is a gap); a token mode switched only by the PI's words, as VCC's.
6. **One repository at a time** on the cluster's single checkouts: lanes take turns by day instead of running five at
   once.
7. **The pre-decider as a test:** `tests/test_autodev.py` fails when a "Decisions needed" entry does not name the tier-III
   clause that makes it the PI's.
