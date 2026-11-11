# Rules of the autonomous development program: the canonical index

Written 2026-11-09 on the PI's order: "we are going to have an autonomous development and upgrade and
integration of current single cell harness, and its scqc, scanno, scintegrate and scprofile ... learn
from vcc harness especially the key rule 3-5".

**How to read an entry.** Each rule has four parts.
- **Source**: the PI's words, quoted and dated. **(C)** means the rule is the coordinator's own design.
  A (C) rule has no PI source, can be adjusted at once, and is never cited as the PI's rule.
- **Requires**: what the rule asks for.
- **Does NOT require**: the limit of the rule. A rule is never read more widely than this line.
- **Applied in**: the files that carry it.

**Rules about rules** (C), learned from the VCC harness, whose owner asked for it there: "DO NOT
OVERSTATE ANY RULES"; "AVOID ANY BLOCKERS". A rule says exactly what the source says, no more and no
less, and means nothing else. The PI's reading of their own rule wins. When a (C) rule collides with a
PI rule, the (C) rule yields. Outside tiers I–III the coordinator adjusts at once and reports.

---

## TIER I: the goal and the five core rules (fixed; only the PI changes them)

**THE GOAL** is [`GOALS.md`](../GOALS.md): the report's mission, outcomes and capabilities. The PI's words
(2026-11-09): "set the goal as the project goal that we are moving towards". The audit grades progress
against GOALS.md's layer-3 tests. The program ends when the audit is HAPPY (see [README](README.md)).
The PI owns the goals and may override any verdict.

Slots 1–2 hold the two PI rules this project already treated as non-negotiable. The placement is (C);
the PI may swap them. Slots 3 and 5 are the VCC harness's core rules 3 and 5, adopted on the PI's order
of 2026-11-09. VCC's rule 4 ("a real trained model") was skipped by the PI the same day. Slot 4 stays
empty, so that "rule 3" and "rule 5" mean the same thing in both projects.

| # | rule | source | requires | does NOT require |
|---|---|---|---|---|
| **1** | **No overfit, no in-house script. Reproduction is the test.** | 2026-09-06: "pass the SAMBO test without overfit or in-house script" | A change to a tool is accepted only when four things hold. (a) Its own suite passes, and a leak guard finds no cohort or site string anywhere in the repository: no sample names, factor levels, site paths or queue names. (b) A run on a synthetic fixture enters the real CLI path. (c) A PBS reproduction against each promoted run the change touches is identical on its deterministic outputs, and the prediction was written into the `.pbs` **before** submission. (d) The comparison reads the tool's own output layout, with no reshaping script in between. | Identical floating-point output from a method that varies between executions (harmony). Such an output is named with its measured spread, and is never called "not reproducible" (2026-09-06). For a new capability with no promoted run yet: the promoted runs it touches still reproduce, and its first sealed run becomes the reference once promoted. |
| **2** | **Single cells are not single nuclei.** | 2026-10-02: "do not run cellbender for single cell"; "single cell and single nuclei is fundamentally different!" | Every tool whose behaviour depends on the assay has separate, declared rule sets for `scrna` and `snrna`. CellBender never runs on single cells. No rule calibrated on nuclei is lent to cells. There is no silent default assay. | Separate repositories or pipelines for code that is genuinely independent of the assay. A ban on ambient methods other than CellBender: the PI's words name CellBender. A cohort may still decline every denoiser, as BrainOrganoid_C46's D6 does (B1). |
| **3** | **The HPC rules.** | VCC rule 3 (2026-09-29): "respect HPC rules"; this site's rules: the `duke-nus-hpc` skill and its `LAYOUT.md` | PBS only. Never compute on a login node: no `nohup`, `&` or local executors. Code is authored on the workstation and pushed; the cluster never originates code (H1). A tool is installed once, in `~/tools/<Tool>/`, and called from inside a project. It writes only into `runs/<tool>/<stage>/<RUNKEY>/`, and the job seals that directory. Read `LAYOUT.md` before writing anything to the cluster. Never switch `~/tools/<Tool>` under a running job. Never run two conda builds that share a package cache at the same time. | (C) Anything on the workstation. Unit tests and small fixture runs on the Mac are not cluster compute. (C) On the login node, reads use `ls`, `grep`, `head`, `cat`, `qstat` and `git` only. A `python -c` or `Rscript -e` one-liner is a child process, which LAYOUT sends to PBS, however short it is. |
| **4** | *(skipped)* | 2026-11-09, on the coordinator's translation of VCC's rule 4 ("a real trained model"): "can skip this rule" | Nothing. The slot is empty. | Any substitute. No (C) rule re-imposes what the PI skipped. |
| **5** | **Time and efficiency.** | VCC rule 5. 2026-10-14: "make the time spent and effciency as the 5th core rules"; 10-17: "you will need to fix immidiately"; 10-25: "The bans: no trivial tweaks", "DO NOT WASTE RESOURCE ON TRIVIALS!" | Never leave a lane idle or a step slower than it needs to be. Idle means: a development lane with no wave, a result landed but unread, a wave waiting on a blocker that could be removed, or a deciding job queued behind exploratory work. Fix an efficiency regression the moment it is seen, in the same turn. **No track sits behind a blocker**: the blocker remover clears it. **No trivial tweaks**: every wave must move a GOALS.md id. A lane, agent or PBS job spent on polish that moves no goal breaks rule 5 just as an idle lane does. | (C) Parallelism beyond the Mac's memory or the cluster's per-user queue limits. Exceeding them fails jobs: ADR-0027's Q11 was a refusal at the queue limit. Skipping rule 1's gate to save time: a failed reproduction costs more than the gate. What counts as "trivial" is the (C) working definition: a parameter nudge, cosmetic churn, or a re-run that cannot change a decision. Structural fixes, new capabilities and test reach are never trivial. |

---

## TIER II: the PI's standing rules for this project (not blockers; only the PI changes them)

| rule | source | requires | does NOT require |
|---|---|---|---|
| **Measure before claiming** | 2026-10-02, after "are you sure all cell above 1.2k? is it before qc or after qc" | A number about data is stated only after it has been measured on the object it describes, with the stage named (raw, the aligner's call, after QC). An inference from a summary is labelled as an inference. | Measuring what nobody is claiming. |
| **The maker round's top rules** | 2026-09-10, recorded "as the user set them": "1. A plugin is MAKER OUTPUT ... Never hand-edit `kernels/*.py`; change the maker, re-run it"; "2. The other eight plugins are HELD-OUT TEST RESOURCES — do not touch them at all. They are the only evidence the maker is general ... They stay broken." Also the PI's words: "NO NEED TO COMPLETE ALL PLUGIN NOW, THE GOAL IS A GOOD PLUGIN MAKER" | No hand edit of any plugin, ever. A plugin changes only through the maker. The eight are the maker's test set. **Pre-decider's reading (2026-11-09):** they were held for exactly this use, and ADR-0022 planned "the eight held-out plugins migrate one at a time through the maker". The program therefore spends them that way, one at a time, DE and abundance first. Each migration is a blind test of the maker and is graded before the maker changes. A maker fix found on one plugin is tested on the next. | Keeping them broken once the maker is ready to be tested on them. Their purpose was to test the maker, and the goals (A1.1, A4.1) need them working. An exclusive allow-list of paths that may change (scProfile's `in_place`, B1-066). End-to-end equality with the complement of the held-out set (B1-062): only a held-out plugin declared end to end is a breach. |
| **Edit through the maker** | 2026-09-14: anything in a plugin that cannot be edited easily from the maker is a suite or maker design defect | Plugin changes go through the maker. A change that cannot be made that way is recorded as a maker defect. | Freezing the maker. The maker itself is developed like any tool. |
| **The user's decisions stay the user's** | ADR-0027: "the merge, and the sign convention it gives SAMBO's DE ... are the PI's"; cohort DECISIONS D6–D9 | Design, contrast and sign conventions, thresholds the data cannot decide, and what is promoted are the PI's. They are prepared with their numbers and a recommendation. | Asking about anything a rule already decides. See the pre-decider (tier III). |
| **Merges into a tool's `main`: a standing yes** | 2026-11-09: "yes , you have a standing yes, use predecider for decision". Before that, 2026-10-02: a fast-forward was "held for the PI's review" | The coordinator merges a wave into a tool's `main` without asking once two things hold: its gate passed (rule 1, a–d) and its verifier's verdict is PASS. The merge is logged in `waves.tsv` and pushed. | A merge whose gate failed or is missing, or whose verdict is FAIL: that wave is never merged. A PI-owned decision carried inside a branch, such as a sign convention or a promoted threshold. That decision is still the PI's, asked on its own with its numbers. The merge yes does not answer it. |
| **Housekeeping keeps the project lean** | 2026-11-09: "a regular housekeeping to keep project lean and efficient" | A standing yes to delete outdated material at the regular pass, logging each deletion. Outdated material includes merged branches and worktrees, scratch clones, superseded job scripts, dead code (with its test), and stale docs. | Deleting records: ADRs, post-mortems, sealed runs, promoted results, ledgers, RUNLOGs, or anything a pending read needs. Those stay. Never anything outside our own folders. |
| **Cohort data never enters a tool** | 2026-09-06 (rule 1); the BrainOrganoid_C46 README | Nothing from SAMBO or BrainOrganoid_C46 (names, levels, numbers, paths) lands in a tool's repository. | Keeping cohort names out of the harness's own records. ADRs and these ledgers name cohorts. |

---

## TIER III: the PI's directions for this program (2026-11-09, verbatim)

| direction | the PI's words | requires |
|---|---|---|
| **The goal** | "extract goals in layers. set the goal as the project goal that we are moving towards. current single cell harness family is way behind our goals" | [`GOALS.md`](../GOALS.md) (layers 0–3). Every wave names the goal ids it moves. |
| **The gap review** | "send an agent to review and identify the gaps" | Audit pass 0001: [`ledger/gaps.tsv`](ledger/gaps.tsv) and [`ledger/audits.tsv`](ledger/audits.tsv). |
| **The loop** | "a loop between development teams and audit team which keep evaluating the goal achiveing quality and remaining gaps, until the audit teams is happy" | Development waves alternate with audit passes. The audit grades quality and the remaining gaps. The program stops only on an audit verdict of HAPPY ([README](README.md)). |
| **The blocker remover** | "generate a blocker remover part to remove any blockers" | A role that clears every blocker it can, at once, and prepares the PI's decision for the rest ([BRIEFS](BRIEFS.md) §3). |
| **Remove inherited constraints; the remover is ON** | "it is very important to remove unreasonalble designs, and remove blockers and constrains from previous single cell harness family. enable the blocker remover" | Every rule, gate, freeze, ladder and refusal inherited from the earlier rounds is classified. A PI rule is kept, read no wider than its words. A guard is kept where it protects a goal, and trimmed where it protects nothing. Anything unreasonable is removed at once and recorded in ADR-0029. The remover runs continuously: pass B1 over the inheritance, then the BLOCKER SWEEP every 3 h ([README](README.md)). |
| **Housekeeping** | "a regular housekeeping to keep project lean and efficient" | A recurring pass ([BRIEFS](BRIEFS.md) §4) and the tier-II standing yes. |
| **Learn from the VCC harness** | "learn from vcc harness especially the key rule 3-5"; on rule 4: "can skip this rule" | Rules 3 and 5 in tier I. Rule 4 is skipped. The VCC practices below appear as (C) designs, each credited to its lesson. |
| **The platform is in scope** | "yes include Studio, Lab and Service" | `scrnaseq-studio`, `scrnaseq-lab` and `rnaseq-service` are developed in the program (lane PLAT). `rnaseq-service`'s bulk path keeps working. |
| **The bars are targets** | "this is goals we are developing towards. keep developing" | GOALS.md's layer-3 bars are what the audit grades. They never stop or hold development. |
| **The pre-decider** | "use predecider for decision" | Every decision goes through the pre-decider (tier IV gives its steps) before anything is asked. A decision that a rule or a (C) design settles is made, acted on and reported, never asked. |

---

## TIER IV: the coordinator's designs (C). Adjustable at once; none may block development.

| design | what | lesson it comes from | must not block |
|---|---|---|---|
| **No standing agents** | One coordinator (the main session) owns the ledgers, merges, the cluster deploy lanes and the PI's questions. Short-lived **builders** each take one registered wave, in a fresh context, then end. Auditors are fresh and read-only. | VCC 10-26: "reduce the agent use"; VCC 10-27: short-lived wave builders | Rule 5: start more builders when that is faster and the Mac allows it. |
| **Concurrency** | SUPERSEDED 2026-11-10 (the block at the end: 2 builders, 1 verifier per merge batch). Was: at most 5 editing agents (builders, and the blocker remover when it edits) and 4 audit agents (verifiers and full-pass auditors) at once on the Mac, which has 36 GB. The audit cap went from 3 to 4 on 2026-11-09 at a load of about 9, with four verifiers ready. Both caps were raised on 2026-11-09 under rule 5. The audit cap went from 1 because a verifier was waiting behind the two gap reviews. The builder cap went from 3 to 4 because three lanes were idle while the blocker remover held one slot, then to 5 for the platform lane's first wave, a light Node project. One cluster deploy lane per tool, because `~/tools/<Tool>` has one checkout: a deploy waits only for that tool's running jobs. | VCC "do not abuse use mac"; ADR-0027's queue limit and environment race | Raise the cap as soon as an idle lane is waiting on it. |
| **Registered before numbers** | Each wave states its goal ids, its acceptance check and its prediction before any run. A PBS job carries its prediction in the script. It is graded by its own rule, and a miss is recorded as a miss. | This project's rule 1; VCC "registrations before numbers" | A registration takes minutes and is never a reason to hold a run. |
| **A merge rests only on what was written before the run** | Every comparison or exception a merge relies on is written into the job script before submission. A comparison designed after the result is evidence for the PI, never a gate. | Audit pass 0002, GAP-102: W007 was merged on an isolating comparison designed after submission | Isolating comparisons are written up front (job 31 shows how). |
| **The pre-decider** | v2 (2026-11-10): [PRE_DECIDER.md](PRE_DECIDER.md), the form, the user-only list, the catalogue, the test. Before asking the PI anything: (1) does a tier I–III rule decide it? Then act. (2) Is it a tier-IV design? Then decide, act and report. (3) Only a PI-owned decision, or an outward-facing and hard-to-reverse action that no rule covers, goes to the PI, with its numbers and a recommendation. Each decision made this way is recorded in STATE.md together with the rule that decided it. | The PI's direction (tier III); the steps are (C), from VCC 11-01: "add a pre-decider design" | Never a reason to idle a lane while waiting for an answer. |
| **No blocking questions while work is in flight** | Questions go to the PI in plain text at the end of a turn. Every lane keeps working meanwhile. | VCC no-blocking-questions-in-flight | — |
| **The amplifier** | A defect class found in one tool is checked in all five. For example ADR-0027's thesis: a default that equals SAMBO's value hides a bug. The audit carries each lesson as a row in `gaps.tsv`. | VCC 10-25 AMPLIFIER | Checking is not copying: each tool fixes the defect in its own design. |
| **Fix bugs always** | A bug found is fixed with a test that fails on the old code. | VCC fix-bugs-always; this repo's practice (ADR-0027 tests) | — |
| **Honest records** | Ledgers and RUNLOGs are append-only. A correction is a dated addition. Stamps come from `date -u`. A failure is reported as a failure. | VCC "log honestly"; ADR README "never renumbered, never deleted" | — |
| **Worktrees** | Builders work in their own clone or worktree and push only their own branch. A linked worktree of the harness may commit again: the pre-commit hook unsets git's repository variables (`2a6f77b`, BLK-004), and a guard test fails if the suite changes the real repository's config or HEAD. Never run `git config` against the shared repository. The coordinator never `cd`s into a builder's worktree; it reads files by absolute path. | VCC repository habits | — |
| **One cohort per question** | A wave that touches a tool reproduces SAMBO's promoted run, and exercises BrainOrganoid_C46 when the cohort reaches that stage. | ADR-0027 | — |

## Added 2026-11-09 by the PI's decisions

- **Tier II, decision 0b ("go", 2026-11-09), option (b):** a change MEANT to move a promoted run's outputs may merge under
  the standing yes when its PBS run matches a difference predicted output by output BEFORE submission, graded by its
  written criterion. Re-promoting the moved run stays the PI's. The W007 merge (GAP-102) is accepted under this rule.
- **Tier IV, the throttle (the PI: "agree", 2026-11-09):**
  - at most 2 builders and 1 verifier at a time;
  - at most 2 fix rounds per change, after which the leftover issue is recorded as a gap, never looped on;
  - re-checks look only at the fix, not the whole change;
  - no polishing of changes that wait on the PI's deploy;
  - the LOOP TICK fires every 3 hours.

- **Tier IV, the pre-decider tightened (the PI, 2026-11-10: "where is predecider, why need my decision, review rules and goals and decide"):** four items had been left as questions that the rules already settled. Hence: (3a) declining an outward-facing or hard-to-reverse action is the default, and it is decided, not asked; only a REQUEST to take such an action goes to the PI. (3b) A fact about a cohort is looked up in its delivery and records, and measured where it can be, before it is asked. What stays unknown is written as a limit in the report, never left as a question that holds a lane. (3c) A design that a cohort's own names declare is used, with its unknowns labelled. (3d) An item goes to "Decisions needed" only when it is PI-owned by tier III (a promotion, a sign convention, a threshold the data cannot decide) or needs the PI's hand (a permission, an account, a collaborator). It carries a recommendation, and the lane carries on meanwhile.

## Added 2026-11-10 by the PI's "agree, proceed with all" (the diagnosis: [audits/DIAGNOSIS_20261110_vs_vcc.md](audits/DIAGNOSIS_20261110_vs_vcc.md))

All tier IV (C) unless a line says otherwise.
1. **Agent use, as VCC's tier-II row:** the coordinator plans, reads, grades and merges itself. At most 2 short-lived
   builders at a time, each one registered wave, then end. The adversarial verifier runs **once per merge batch per
   repository** (a batch = the waves merged into that repository since its last verification, at most one batch a day),
   never per change; at most 2 rounds, then the residue is a gap. Fix-only re-checks look at the fix. Every wave is still
   gated by its suite, the leak guard, the fixture and its pre-declared reproduction (rule 1) before it merges.
2. **One number:** each layer-3 test has a measured score (GOALS.md, "Layer 3, scored"); the program's progress is the
   mean, read at every audit; HAPPY = mean >= 0.9 and no test < 0.5. A wave must name the score it moves and by how much
   it predicts to move it; a wave that moves none is trivial (rule 5) and is not built. **The PI decided this (D-006).**
3. **Watching by machinery:** `setup/autodev/pbs_mirror.sh` polls the cluster (one ssh every 5 min, login-node reads only) over a
   watch list of submitted jobs and writes one verdict file per sealed run and one held file per held job;
   `setup/autodev/monitor_verdicts.sh` turns them into Monitor events. The coordinator reads verdict lines, not run directories;
   the LOOP TICK (3-hourly) is the fallback.
4. **A cheaper gate:** a fix-up after a gating run does not resubmit when the job's runtime-file manifest (the sha256 of
   every file the job executes, as job 26 declares it) is unchanged by the fix-up; the comparison of manifests is
   recorded in the wave. Any other fix-up resubmits the same job. Never an AST or code diff. Infrastructure failures
   (held nodes, missing directories) are retried unchanged with a dated note, as a script's job when one exists.
5. **The budget (the PI owns the number, D-005; provisional (C) until the PI states one):** this loop spends at most
   8 M output tokens and 2.5 B context-read tokens a day, 40 M output a week, and 1.5 M output per wave including its
   verification; past a wave's cap the residue is a gap. `setup/autodev/usage.py` measures it at every PERIODIC CHECK and the
   number goes into STATE.md. **Token mode = LIMITED** since the throttle of 2026-11-09; only the PI's words switch it
   ("no token limit" / "full speed" to UNLIMITED; "save tokens" / "token limited" back), as VCC's TOKEN_MODE. Past 80 %
   of a cap, no new builder starts.
6. **Lanes take turns:** at most two lanes build at once (the two builders), in a fixed rotation QC, ANNO, INT, PROF,
   HARN, PLAT; a lane's next wave starts only when its previous one is merged, held or failed; a tool's cluster checkout
   follows its one gating wave.
7. **The pre-decider is enforced** ([PRE_DECIDER.md](PRE_DECIDER.md) v2, the PI: "improve it"): a form in
   `ledger/decisions.tsv` for every candidate question, a user-only list, a catalogue of stated answers that grows with
   every answered ASK, and `tests/test_autodev.py` fails a question that reaches STATE without an ASK row or that the
   catalogue answers.

## Added 2026-11-10 by the PI: "you are here to fix harness. the development will be carried by opus 5.5 max"

- **Tier II, the development model:** every development agent (builder, verifier, auditor, blocker remover, research
  helper) is launched with the Agent tool's `model: "opus"` (Claude Opus 5.5) and `effort: "max"`. The coordinating
  session's own job is the harness: the rules, the machinery, the records and the loop; its model is whatever the PI set.
  An agent that inherited another model is stopped and relaunched (the harness batch's verifier, 2026-11-10T01:5xZ).
- **Tier IV, one coordinator and a hand-off:** one session coordinates at a time. A hand-off to a new session: the old
  session's agents hand back first (their transcripts belong to it), its records are committed and pushed, its crons,
  mirror and Monitor die with it; the new session runs `bash setup/autodev/bootstrap.sh check`, then `print`, and starts
  what is missing. Machinery state lives at `<HARNESS>/autodev/.machinery/` (git-ignored), not in a session's scratchpad,
  so the mirror's verdict files survive a hand-off.

## Added 2026-11-10 by the coordinator (measured; tier IV, adjustable)

- **An agent resumes on the session's model.** W020's and W029's builders, resumed by SendMessage at 01:34Z while the
  coordinating session ran Fable, ran on claude-fable-5-1 at xhigh until 02:2xZ (their transcripts' own fields; 5 and 2
  commits). So: resume an agent only while the session runs Opus 5.5 at max; otherwise launch a FRESH agent with
  `model: "opus"`, `effort: "max"`, briefed with its branch, its clone and the commits to review. Every LOOP TICK runs
  `bash setup/autodev/agent_models.sh <tasks folder>`; an agent that is not opus/max is stopped and relaunched (BLK-011).
- **The coordinator's scripts are code, so they live where the leak guard reads them:** `setup/autodev/` (moved from
  `autodev/tools/`, which LEAK_SCOPE excuses as a record path and S1 therefore never read). The mirror reads the queue
  for the remote account's own user and names none.
- **A clone's commit gate reads the cohorts' generated term lists** through `setup/githooks/conform.local` (git-ignored;
  the lists sit in `autodev/.machinery/terms/`, also ignored). `shapes=` stays unset until GAP-C66's site-string lines
  are gone, because S1 with the shapes is red today.

## Added 2026-11-10 after audit pass 0004 (the first scored pass: mean 0.271, NOT HAPPY)

- **The queue follows the score (tier IV, C):** the next builder slot goes to the open wave whose closing moves the mean
  most, as the last audit ranks them (pass 0004, section 9: the eight plugins through the maker +0.11; the remaining
  adapters and a stage driver +0.08; the three missing components +0.05 each; false documentation +0.044; C46's stages
  2-4 +0.04), ahead of the fixed lane rotation; the rotation breaks ties. A correctness defect the audit finds (GAP-119:
  a failed removal audit in scQC stops nothing) goes first in its lane.
- **Rule 6 relaxed (D-016):** a lane may start its next wave once its previous wave's code is done (gating or verifying);
  the cluster's one checkout per tool is still taken by one gating job at a time, in submission order.

## Added 2026-11-10 by the PI: "turn on token limit mode. focus on key processes", then "focus on development first. validation later"

**TOKEN-LIMITED mode** (as VCC's; only the PI's words switch it: "no token limit" or "full speed" to UNLIMITED; the PI's
word resumes validation):
- **One builder at a time, on the key path,** in score order (STATE's queue): W033 (running), then W034, W023, the eight
  plugins. No other builder, except a short repair the key path needs.
- **Validation later:** no verifier and no audit run until the PI resumes validation. Built waves wait, unmerged (a merge
  still needs a verifier's PASS, tier II); the next waves stack on their heads (D-016). PBS gate jobs are still submitted
  and graded when they land: they cost the cluster, not tokens, and they are each wave's own test (rule 1).
- **Paused:** the LOOP TICK and the BLOCKER SWEEP (their prompts stay in README); the verdict Monitor (the mirror runs on
  and its files are read at every wake-up). **On:** one PERIODIC CHECK every 6 hours, with a short prompt.
- **Short replies;** no registration or housekeeping beyond what the key path needs.
- The 8 M output a day cap stays as the ceiling (D-005 answered by the mode, D-017).

**Housekeeping corrected (2026-11-10):** before deleting a merged wave's scratch, grep the open waves' records
(waves/W0xx.md of every wave not merged) and the running agents' briefs for the path; a path any of them names stays.
The 05:02Z pass deleted verify_W010c while W029's verifier was reading W010's probes there.

## Added 2026-11-11 by the PI: "evaluate and improve current development harness towards our goal ... after that, launch full development"

The diagnosis is [audits/DIAGNOSIS_20261111_efficiency.md](audits/DIAGNOSIS_20261111_efficiency.md) (measured with
`setup/autodev/costs.py`). All tier IV (C) unless a line quotes the PI. This block supersedes the 2026-11-10 lines it
names; nothing in tiers I to III changes.

1. **Mode FULL (the PI: "launch full development to reach our goal!").** The pause (D-020) and TOKEN-LIMITED (D-017) end;
   validation runs again. There is no daily cap in this mode; the meter is read at every heartbeat and written into
   STATE, with `costs.py`'s table by role once a day. The PI's words switch it back ("save tokens", "token limited",
   "pause"). The account's weekly limit can stop every agent at any moment, so rule 9 holds always.
2. **The queue is [ROUTE.md](ROUTE.md)** (supersedes "the queue follows the score" and the lane rotation). It is the
   finite list of items that take the 20 scores to HAPPY. A wave is registered from a route item when what it waits for
   is done. A gap enters a wave only if it blocks a route item or is a wrong result in a promoted output; every other
   gap is recorded and parked. A builder's hand-back names at most 3 new gaps of those two kinds; other observations go
   in the wave file. The B1 register's queued constraints are removed by the wave that meets one (the PI's standing
   order of 2026-11-09 is the authority); there is no constraints-only wave and no blocker sweep.
3. **Small runs.** A builder run is sized for about 150 tool calls (measured: a run's context reads grow with the square
   of its length; the 5 runs over 300 calls were 29 % of all builders' context reads). A registration bigger than that
   is split before launch. A builder that reaches about 150 calls commits, pushes, hands back what is done and returns
   the rest as a follow-up; that is a normal hand-back, not a failure.
4. **Verify first; gate at the head that merges** (supersedes the order "gate, then verify" and rule 4's per-fix-up
   resubmission). The order is build, preflight (the suite, the test that fails on the base, the shadowing package,
   `sch conform` with both lists, the fixture), verify, then ONE gate run on the commit that becomes `main`. When a
   repository takes more than one branch, the coordinator merges them into `autodev/train-<repo>-N` (merge commits only)
   and the member waves' jobs run at the train head, re-pinned as dated copies with their predictions unchanged; all AS
   PREDICTED, then `main` fast-forwards to it. A job before verification is written only when the wave adds a new
   cluster path, or the builder needs the cluster's answer to finish. A gate result at exactly the merged commit, or at a
   commit whose runtime-file manifest equals it, stands (the manifest rule, unchanged).
5. **Verification in parallel, with a pen for the mechanical** (supersedes "1 verifier"). One verifier per repository
   batch, every repository at once. A verifier may fix what is mechanical (a doc line, a missing assertion, a leaked
   string, a job-header line), at most 20 lines in all, each listed in its verdict; anything that changes behaviour goes
   back to a builder (at most 2 rounds, then a gap). Each verifier writes the score rows of the tests its batch moves
   (`scores.tsv`, pass `v-W###`), by GOALS's formulas, with evidence.
6. **Lanes in parallel** (supersedes "2 builders" and "lanes take turns"). One builder per repository at a time; a
   second in the same repository only when the two registrations name disjoint files. At most 6 development agents at
   once (builders and verifiers together). Every one is launched fresh with model opus and effort max (tier II), never
   resumed under another session model, and measured with `agent_models.sh` at launch.
7. **The cluster by script.** `setup/autodev/gate.py submit` and `grade` are how a job goes in and how its result is
   recorded: the checks, the copy and md5, the checkout move (refused while a live watched job uses that tool at
   another commit), the validator, the job's own submit recipe, the watch row, the RUNLOG entry with the job's lines
   verbatim, and the ledger row. A new job carries its recipe between `# SUBMIT-BEGIN` and `# SUBMIT-END` and prints one
   final line `GATE: AS PREDICTED` or `GATE: MISSED (n)`; the coordinator still reads a MISSED run's lines itself.
8. **Audits at checkpoints** (supersedes "the next pass after 3 more merges or 24 h"). A full scored pass runs when the
   tally says HAPPY is near (mean at least 0.85 and no test under 0.5) or after every 10 merges. Between passes the
   verifiers' rows are the score; the coordinator's `coord` rows are provisional.
9. **Stop-proof.** Agents push after every commit. ROUTE and STATE always say what is next. The coordinator commits
   records at every hand-back. One HEARTBEAT every 2 hours replaces the LOOP TICK, the BLOCKER SWEEP and the PERIODIC
   CHECK; hand-backs and verdict files drive everything else.
10. **The PI's steps are asked once, early** (ROUTE section 3): each becomes an ASK row, with the numbers and a
    recommendation, the moment its precondition is met. No lane waits on one.
11. **The PI, 2026-11-11: "also, improve the studio UI design and layout to be top level".** A direction of the PI's
    (tier III in weight): ROUTE item R41, wave W037. "Top level" is the ten-point rubric in `waves/W037.md`; the builder
    designs to it and a verifier judges it by looking. It is built on a branch from the synthetic fixture only; Studio's
    `main` is still the PI's go (BLK-005), asked with the before-and-after gallery. It launches at the first free slot (corrected the same day: at 6
    agents the workstation measured saturated, so the cap of 6 holds for it too; D-024).
12. **Threads (measured 2026-11-11: 6 agents plus another session put the 12-core workstation at a load average of
    140 to 163).** Every agent runs its tests and tools with `OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
    VECLIB_MAXIMUM_THREADS=2 NUMBA_NUM_THREADS=2` exported, and runs one suite at a time. The coordinator commits records
    at hand-backs, not after every step: the harness's commit gate runs the whole suite on each commit (ROUTE R06 narrows
    it for record-only commits). One commit at a time: a second commit started while the first one's hook is still running
    has its staged files swept into the first, and is then blocked by the suite's own guard when HEAD moves (measured
    2026-11-11, commit 53cb948).
13. **The PI, 2026-11-11: "use fable 5.2 level designer to design all ui".** Every UI item on the route is designed, and its
    visual layer built, by a designer agent on Fable 5.2 (Agent model `fable`; measured `claude-fable-5-2` at launch with
    `EXPECT_MODEL=claude-fable-5-2 EXPECT_EFFORT=any bash setup/autodev/agent_models.sh ...`). This is the one exception to
    tier II's "Opus 5.5 at max" for development agents, by the PI's own words. It covers Studio (R41), the harness's UI
    (R08) and any change to what a user sees in Lab or Service. The designer owns the design file and every screen; a
    builder on Opus may do the non-visual work a UI needs (data, state, tests), to the designer's file. No effort was
    named, so none is set (measured: xhigh). The Opus builder that had just started Studio's run B was stopped (it had
    only confirmed the baseline) and the run relaunched under a designer.

### Added the same day by the PI: "make a improvement plan doc and to do list. and go ahead" (five lessons from ScientistTwo; [IMPROVEMENT_PLAN.md](IMPROVEMENT_PLAN.md))

14. **Subset before full.** A job that asks for more than 2 hours ships with `<name>.subset.pbs`: the same steps on a
    declared subset, its own prediction in its header, sized for minutes. The full job is submitted only after the
    subset is graded AS PREDICTED at the same tool commits, and the subset's measured wall time and peak memory size the
    full request. `gate.py` refuses otherwise; `--no-subset REASON` is for a job written before this rule, and the reason
    goes into the RUNLOG.
15. **Self-attack.** [ATTACKS.md](ATTACKS.md) lists the attacks that broke a wave here. A builder runs each one that
    applies against its own change before hand-back and says which it ran and what happened. A verifier that breaks a
    wave a new way adds a line to its inbox. The measure is `setup/autodev/passrate.py` (waves that pass their first
    verification; 4 of 9 on 2026-11-11), read at every daily check.
16. **A pool for items that search.** An item that has to find something (a rule, a hypothesis, a tool to convert) keeps
    `autodev/pools/<item>.tsv` and registers S (successes that end it) and K (rounds that end it). A round is the
    candidates evolved from every earlier trace plus at least one untried one; each is tried on a subset first and
    called good, bad, or engineer (at most 2 tuning passes, then bad). Bad is a verdict on a variant, never on the idea: an
    item that reaches K returns to the route as a gap, with what its traces showed, and can be registered again.
17. **Ablation before a gain is kept.** A wave that claims a measured gain (time, memory, a metric) reports the gain per
    component, measured by removing each, and keeps only what carries it. A claimed gain with no ablation is a verifier's
    FAIL reason.
18. **A source that exists.** A plugin's source is a DOI recorded with the title and year its own record gives, and a
    check resolves it (ROUTE R45). A verifier reads one cited claim per plugin against its source.
