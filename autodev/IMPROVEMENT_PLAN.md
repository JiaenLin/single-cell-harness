# Improvement plan: five lessons from ScientistTwo

The PI, 2026-11-11, after comparing ScientistTwo (arXiv 2609.19644) with this program's development harness and the
VCC harness: "make a improvement plan doc and to do list. and go ahead." The comparison found this harness already
stricter on rigor (a prediction written before the run and graded as written; an adversarial verifier that runs the
code; held-out plugins and a second cohort; human gates on promotion). The five lessons below are about spending
cheaply first, learning from failures, and stopping by rule. Each has what changes, where it is written, and how its
effect is measured.

## The five lessons

### 1. Subset before full
- **What they do:** no idea runs on the full benchmark before it passes on a subset.
- **Our gap:** the local fixture plays that role, but cluster gates go straight to full size. Two full jobs died on a
  precondition today (a wrong path; a file mode), and the 1,263,676-cell cohort has never run at any size.
- **The change:** a job that asks for more than 2 hours ships with a subset job, `<name>.subset.pbs`: the same steps on
  a declared subset (a few libraries, or a fraction of cells), with its own prediction, sized to finish in minutes. The
  full job is submitted only after the subset is graded AS PREDICTED at the same tool commits. The subset's measured
  wall time and peak memory size the full job's request. `setup/autodev/gate.py` refuses otherwise.
- **First use:** the scale cohort's stage 1 runs on 2 of its 88 libraries before the 88.
- **Measured by:** full-size jobs that fail before their first result (2 today; the target is 0), from the ledger.

### 2. Failures as first-class input
- **What they do:** every failed run is read by the agent that proposes the next idea.
- **Our gap:** a verifier's finding becomes a ledger row the next builder never sees. Of the 9 waves built on
  2026-11-11, 5 failed first verification, on causes that repeat.
- **The change:** [`ATTACKS.md`](ATTACKS.md), one screen of the attacks that broke a wave here, each with the wave it
  broke. Every builder runs the ones that apply against its own change before hand-back and says which it ran. A
  verifier that breaks a wave a new way adds a line.
- **Measured by:** `setup/autodev/passrate.py`: waves that pass their first verification. Baseline 4 of 9 (44 %) on
  2026-11-11. Read at every daily check; if it has not passed 60 % after 15 more waves, the list is not working and is
  reworked.

### 3. A pool rule for idea-driven work
- **What they do:** each round tests the candidates evolved from all earlier results plus a few untried ones, and the
  search stops at S successes or K rounds.
- **Where it applies here:** not the route (an engineering list), but the items that search: the hypothesis loop
  (R09), the never-seen tools (R36), and any wave that has to FIND a rule (the tree rule of W044 was one).
- **The change:** such an item keeps a pool file (`autodev/pools/<item>.tsv`: candidate, where it came from, its
  predicted effect, tested or not, result). A round is the candidates evolved from every earlier trace plus at least
  one untried one. Each is tested on a subset first with a three-way call: good, bad, or engineer (at most 2 tuning
  passes, then bad). The item stops at its registered S or K, both written in its registration. "Bad" is a verdict on a
  variant, never on the idea: an item that reaches K goes back to the route with what its traces showed, as a gap, and
  can be registered again (the same rule VCC's owner holds: one failed variant never closes an idea).
- **Measured by:** each such item's registration states S and K, and its pool file exists when it hands back.

### 4. Ablation before a gain is kept
- **What they do:** after a win, find which component carries it, drop the rest, and keep the change only if it is
  strictly better.
- **Where it applies here:** rarely, since most waves change behaviour, not a score. It applies when a wave claims a
  measured gain (time, memory, a metric, a design measurement).
- **The change:** such a wave's hand-back carries the gain per component, measured by removing each, and keeps only
  the components that carry it.
- **Measured by:** verifiers check it; a claimed gain with no ablation is a FAIL reason.

### 5. A reference check
- **What they do:** every citation is checked to exist; without the check 19 of 1,840 were invented.
- **Our gap:** A4.3 counts a plugin that names a source and a pinned version; nothing checks that the source exists
  and is the method's.
- **The change:** a plugin's declaration carries its source's DOI with the title and year as recorded from the DOI's
  own record; a check resolves each DOI and compares (ROUTE R45). Each plugin's wave (R24-R30) and each docs-truth pass
  (R39) includes it, and a verifier reads one cited claim per plugin against its source.
- **Measured by:** A4.3's count, with "resolves and matches" added to what a verifier must see.

### 6. The search itself (added the same day; the PI: "how about the search part, anything we can learn")
- **What they do:** several candidates tried cheaply before one is built out; the next candidates proposed from every
  earlier result, failures included; a few untried ones in every round; the current best replaced only by something
  strictly better; a check that the list of limitations is sufficient before any idea is generated.
- **Our gap:** a wave carries ONE design, and a failed one is patched. The tree rule of W044 was one design, built in
  full, run on the cluster, and found wrong on nine other tissues by its verifier. The route itself was never checked
  for sufficiency: four of its items were found by accident on 2026-11-11.
- **The change (RULES items 16 and 19):** for an item that searches, the first round tries at least 2 candidates at the
  cheapest test that can tell them apart, against expectations written first; the incumbent stays unless the challenger
  is strictly better; a fix round brings a fresh candidate; every candidate tried is kept and counted. And the route is
  read against the goals by an independent agent after it changes.
- **What is NOT taken:** ranking by novelty; closing an idea at K; and searching analysis choices for an effect, which
  for a result on a cohort would be fishing. The pool's count of candidates is what keeps a search honest there.
- **Measured by:** for items that search, first-verification pass rate against the other waves'; for the route, the
  count of items added after the sufficiency check that it did not name.

## For the VCC harness
Lessons 1, 3 and 4 fit VCC's research waves most (long training runs, a search over ideas, stacked gains), and lesson 2
fits any loop with a verifier. That repository belongs to its own session, so they were sent to it as a proposal on
2026-11-11; nothing in VCC was edited from here.

## To do

| # | task | where | status |
|---|---|---|---|
| 1 | The subset rule in the gate runner: refuse a full job whose subset has not passed; refuse a job over 2 h with no subset unless a reason is given | `setup/autodev/gate.py` | done 2026-11-11 |
| 2 | The rules: subset before full, self-attack, the pool rule, ablation, the reference check | RULES.md, 2026-11-11 items 14-18 | done 2026-11-11 |
| 3 | The attacks list, from every verifier FAIL so far | `ATTACKS.md` | done 2026-11-11 (18 lines) |
| 4 | Every brief: SELF-ATTACK and SUBSET lines; the verifier adds new attacks | BRIEFS.md section 0 and 2a | done 2026-11-11 |
| 5 | The pass-rate meter | `setup/autodev/passrate.py` | done 2026-11-11 (baseline 4 of 9) |
| 6 | The route: the scale cohort's subset run; S and K for R09 and R36; the reference check as R45 and inside R24-R30 and R39 | ROUTE.md | done 2026-11-11 |
| 7 | Tests that keep the above from decaying | `tests/test_autodev.py` | done 2026-11-11 |
| 8 | The proposal to the VCC session | a message to that session | sent 2026-11-11; answered the same day: VCC took ablation (narrowly: a composite arm registers its leave-one-out arm) and its own attacks list (18 attacks from its records, run by every builder); it already had subset-before-full (a launcher-checked smoke and a cheap entry test) and an idea pool; it did NOT take the K-round stop, which conflicts with its owner's standing rule that an idea is a direction and one failed variant never closes it |
| 9 | The scale cohort's stage-1 job written as a subset job and a full job | the wave after W045 | open: waits for W045 and the driver |
| 10 | R45 built: DOIs recorded and checked | a harness and scProfile wave | open: after W035 + W040 merge |
| 11 | First reading of the pass rate after 15 more waves; rework the attacks list if under 60 % | the daily check | open |
| 13 | The search rules (breadth first, the incumbent, a fresh candidate in a fix round, every candidate counted) | RULES item 16 | done 2026-11-11 |
| 14 | The route's first sufficiency check, by an independent agent | RULES item 19 | running since 2026-11-11 (an independent reader; its answer goes to `audits/ROUTE_SUFFICIENCY_20261111.md`) |
| 15 | The search part passed to the VCC session (the PI: "also update vcc on the search part") | a second message to that session: breadth first, the incumbent, a fresh candidate in a fix round, every candidate counted, a sufficiency check of its queue | sent 2026-11-11; answered the same day: VCC took the three points it did not have. The sufficiency check is now a rule of its 5-hourly amplifier pass (project the scalar if every queued wave lands at its prior, against the bar, and name what no wave targets); "a fix round brings a fresh candidate" and "report a winner with how many it was chosen from" are attacks 19 and 20 of its list, which every builder checks. Breadth first and the incumbent rule were already in place there. Carried back here the same day: the same two lines are attacks 19 and 20 of this harness's list, and BRIEFS has a SEARCH line |
| 12 | Agents already running were briefed before this plan; they get the attacks list at their next fix round or re-check | the coordinator, at each launch | open |
