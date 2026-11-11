# Diagnosis 2026-11-11: is this development harness the efficient way to the goal?

The PI, 2026-11-11: "first, evaluate and improve current development harness towards our goal. improve it or change it to
find the best and most efficient way towards our goal. after that, launch full development to reach our goal!"

Everything below is measured from the session's transcripts with `setup/autodev/costs.py` (the per-agent token fields of
every agent run since 2026-11-09) and from the ledgers. Nothing is estimated unless it says so.

## 1. What the program spent, and on what

| role | runs | calls | output (M) | context read (M) | per run: output, context read, calls |
|---|---|---|---|---|---|
| builder | 45 | 8,762 | 11.76 | 3,144 | 261 k, 70 M, 195 |
| verifier | 18 | 1,964 | 2.20 | 379 | 122 k, 21 M, 109 |
| auditor | 14 | 2,059 | 1.81 | 549 | 129 k, 39 M, 147 |
| blocker remover | 4 | 644 | 0.80 | 189 | 199 k, 47 M, 161 |
| coordinator (11-09 and 11-10) | - | 962 | 1.58 | 437 | average context 505 k on 11-09, 320 k on 11-10 |

About 18 M output tokens and 4.7 B context-read tokens in two days. For that: 17 waves merged, 7 batches built and gated
but unmerged, and a mean score of 0.271 at the first scored audit (pass 0004), 0.292 by the coordinator's tally now.

## 2. Findings

**F1. The cost is in builders, and it grows with the square of a run's length.** Builders are 64 % of the output and 67 %
of the context reads. Every call re-reads the whole conversation, so a run's context-read cost is about (calls squared) x
(growth per call) / 2. The 5 builder runs over 300 calls (W013 480, W024 351, W021 336, W019 327, W020 327) are 11 % of
builder runs and 29 % of builders' context reads (914 M of 3,144 M). W013's first run alone read 235 M. A run under 150
calls reads about 25 M. The rule files are not the cost: RULES, BRIEFS, PRE_DECIDER and GOALS together are about 13 k
tokens, 4 % of a typical run.

**F2. Half the waves were built twice.** 14 of 29 waves needed a second or third builder run (W011, W013, W014, W015,
W016, W017, W019, W020 x3, W021, W024, W025 x3, W026, W028, W029). A fix run averages about 140 k output. The causes were
not recorded per run, so their split is unknown; the fix rounds that the manifest rule then sent back to the cluster
(W013, W020, W025) each cost a job cycle as well.

**F3. The queue followed gaps, not the score.** 200 gaps are registered (109 open, 29 in a wave, 62 closed); every
hand-back and audit opened more than a wave closed. The scored tests arrived only on 2026-11-10. Eight of the 20 tests
are still at 0 (A2.3, A3.4, A4.1, A4.2, A5.2, A6.1, A6.2, A7.1), and six of those are capabilities no wave has started.
HAPPY needs a sum of 18.0 over the 20 tests; the tally is 5.85. No list said which waves, in which order, reach 18.

**F4. Finished work does not merge.** Seven batches are gated and wait for a verifier; scProfile is three waves deep on
one unmerged stack. Verification ran one at a time, then not at all (TOKEN-LIMITED). A wave was gated on the cluster
before verification, so every verifier fix that touched a runtime file re-ran the job.

**F5. The cluster is driven by hand.** One checkout per tool is switched by the coordinator under a rule kept in memory
("never switch it under a running job"). Each job cycle cost the coordinator 10 to 15 calls (clean checks, copy, md5,
validate, submit, watch row, RUNLOG prose, ledger row, STATE edit).

**F6. Audits cost as much as all verification.** 14 auditor runs wrote 1.81 M output, against 2.20 M for 18 verifier
runs. Passes 0001 to 0003 produced gaps; only pass 0004 produced the score.

**F7. Timers woke the coordinator whether or not anything had changed.** Three recurring prompts (two 3-hourly, one
6-hourly) plus the events. On 11-09 the coordinator made 714 calls at an average context of 505 k tokens (359 M read).

**F8. The account's weekly limit has already stopped work once** (W028's verifier, mid-check, 2026-11-10). The program
must survive a stop at any moment and spend the week's allowance on score.

**F9. The PI-held steps were never laid out ahead.** Three tests cannot reach 1.0 without the PI: A2.1 (stage 4 has no
promoted run; stage 3's ranking moved), A6.2 (a platform merge is a live deploy), and C46's labels (the tree needs a
person's approval). They are asked one at a time, late.

## 3. The changes (RULES.md, "Added 2026-11-11"; all tier IV unless the PI's words are quoted)

| # | change | answers | expected effect (an estimate until `costs.py` measures it) |
|---|---|---|---|
| 1 | **A finite route.** [`ROUTE.md`](../ROUTE.md) lists every item that takes the 20 tests to HAPPY, with what each moves and what it waits for. The queue is the route; a gap enters a wave only if it blocks a route item or is a wrong result in a promoted output | F3 | no wave that moves no score; the backlog stops growing |
| 2 | **Small runs.** A builder run is sized for about 150 calls; a larger registration is split before launch, and a builder at that length pushes, hands back what is done and returns the rest | F1 | about 40 % fewer context reads per unit of work (the square law) |
| 3 | **Verify first, gate at the head that merges.** Build, preflight, verify, then one gate run on the commit that becomes `main` (a train when a repository takes more than one branch). A per-wave job before verification only when the wave adds a new cluster path | F2, F4 | no re-gate per fix round; the evidence is at the merged commit |
| 4 | **Verifiers in parallel, and they fix what is mechanical.** One verifier per repository batch, all repositories at once. A verifier may apply a mechanical fix of at most 20 lines and lists it; a behaviour change goes back to a builder | F2, F4 | the backlog clears in one round; fewer 140 k fix runs |
| 5 | **Lanes in parallel.** One builder per repository at a time, a second one when its registered files are disjoint; at most 6 development agents at once | F4 | throughput bounded by the cluster and the dependencies, not by a slot count |
| 6 | **The cluster by script.** `setup/autodev/gate.py submit` and `grade` do the checks, the copy, the submission, the watch row, the RUNLOG entry (verdict lines verbatim) and the ledger row; it refuses to switch a checkout a live job uses | F5 | 2 to 3 coordinator calls per job instead of 10 to 15 |
| 7 | **Audits at checkpoints.** Each verifier writes the score rows of the tests its batch moves. A full pass runs when the tally says HAPPY is near (mean at least 0.85, no test under 0.5) or every 10 merges | F6 | about two full passes saved before HAPPY |
| 8 | **Events, not timers.** One heartbeat every 2 hours replaces the three prompts; agent hand-backs and verdict files drive the rest. The blocker sweep is retired: its 73 queued constraints are removed by the wave that meets them | F7 | fewer idle wake-ups |
| 9 | **Stop-proof.** Every agent pushes after every commit; ROUTE and STATE say what is next; `costs.py` reports the cost per role at each daily check | F8 | a limit stop loses at most one agent's uncommitted hour |
| 10 | **The PI's steps laid out.** ROUTE marks each PI-held step and when it becomes askable; each is asked once, with the numbers, the moment its precondition is met | F9 | no test waits on a question nobody asked |

## 4. What it should cost to reach HAPPY (an estimate, stated as one)

ROUTE.md has about 40 items. At the measured averages (a builder run 261 k output, a verifier 122 k), with changes 2 to 4
(estimated 1.3 builder runs per item instead of 1.55, runs 40 % cheaper in context reads), the route is about 20 to 30 M
output tokens and 4 to 6 B context-read tokens: about what the last two days spent, for 12 points of score instead of
one. Wall time is set by the cluster and the dependency chain (the adapter, then the driver, then the scale cohort and the
cold-agent trials), about 4 to 6 days at six agents. `costs.py` checks this estimate daily.
