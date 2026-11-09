# 0029 — Inherited constraints removed: what the blocker remover withdrew, narrowed and kept

**Status** accepted 2026-11-09 under the PI's direction of that day (below). Applied on branch
`worktree-agent-ad2872878d156abfa`; its first two commits are on main as 2a6f77b and 4afad34, and
the rest merges after a fresh verifier's PASS
**Date** 2026-11-09
**Affects** no ARCHITECTURE.md invariant. It withdraws or narrows:
- ROADMAP.md's three governing rules;
- ADR-0013's "numbers are not touched";
- ADR-0016's standing rules and step ceremony, and their repetition in ADR-0017 to ADR-0026;
- ADR-0023's G1, as written;
- how `sch dev rules` reads `end_to_end`, and how the ladder treats a repository with no round;
- how VISION.md §18 is read;
- the plugin-maker skill's serial and held-out rules;
- docs/blind's shipped-set exclusion.

## Context

The PI, 2026-11-09: "it is very important to remove unreasonalble designs, and remove blockers and
constrains from previous single cell harness family. enable the blocker remover".

The family was built in serial rounds (ADR-0013 to ADR-0027), and each round left rules, gates,
freezes and ceremonies behind. ADR-0028 made GOALS.md the project goal. It replaced rounds with
parallel waves, a standing yes to merge, the pre-decider, and "keep developing". But it withdrew
only one inherited rule by name ("the four tools are not touched"). This record withdraws the rest
that protect no goal. It narrows the PI's own rules where the inherited reading was wider than the
words, and it records what is kept and why.

Pass B1 swept these sources:
- the harness: ROADMAP, ARCHITECTURE, VISION §18, PLUGIN_FORMAT, DEVPOINTS, docs/, ADR-0001 to
  ADR-0027, the skills, `sch dev` and the tests;
- the four tools: fresh clones of each `main`, read only;
- the coordinator's record of the PI's rules;
- the cohort projects' rules.

It classed every constraint one of four ways:
- **K-PI**: the PI's own rule. Kept, and read no wider than its words.
- **K-GUARD**: a design that protects a GOALS.md outcome. Kept, with any part that protects
  nothing trimmed.
- **REMOVE**: unreasonable now.
- **ASK**: a PI rule that itself blocks a goal. Put to the PI, and not changed.

The register (one row per constraint, with evidence) goes to `autodev/ledger/blockers.tsv`. Changes
to the tools and the platform are not made here. Each is written as a precise change for a wave.

Two measurements framed the sweep. Both were taken on 2026-11-09, on fresh clones of the four
tools' `main`:
- **Conform.** `sch conform` exited 2 on all four, and on each the ONLY failing row was G1.
- **The dev check.** `sch dev check` could never exit 0 on scQC, scAnno, scIntegrate or the harness
  itself, because its rules tier reported "could not run" wherever no round had declared rules.

So GOALS.md A4.1 ("passes `sch dev` and `sch conform`") was out of reach by construction for every
repository.

## Decision

### Withdrawn from the harness (applied)

| # | what it was | from | why it is unreasonable now | what is given up |
|---|---|---|---|---|
| R1 | G1 accepted only `core.hooksPath == "setup/githooks"` | ADR-0023; `sch/conform/checks.py` | The shared config held the ABSOLUTE path of the same directory. The gate ran, yet G1 failed, three tests failed and a commit was blocked. A spelling protects nothing. Fixed in 4afad34 on main: G1 resolves the path (relative to the working tree's root, or absolute) and requires a byte-identical `pre-commit`. | nothing |
| R2 | G1 failed every repository that versions no gate, and every clone that had not installed one | ADR-0023 | It was the only failing conform row on fresh clones of all four tools, so it blocked A4.1 and the program's gate. Fixed in 32384bd: not applicable where no gate is versioned, and a warning where one is versioned but not installed. | Conform no longer fails a clone that would commit without its gate. The harness's own suite still fails a harness clone with none. |
| R3 | The ladder's rules tier "could not run" where no `rules:` block is declared, so a full `sch dev check` exited 3 for ever | ADR-0015/0016; `sch/dev/ladder.py` | Having no round has been the normal state since ADR-0028, so "passes `sch dev`" was unreachable for four of five repositories. Fixed in 81a36ad: the tier is not applicable there. Not applicable means the `rules` key is absent; a `rules:` that is present but not a mapping fails the tier. | nothing a repository declared |
| R4 | ROADMAP: "every phase can stop the project" | ROADMAP | It contradicts tier III ("the bars are targets ... never stop or hold development") and rule 5. A failed phase test is now a recorded gap. | A failed claim no longer halts the other lanes. Its gap still blocks HAPPY. |
| R5 | ROADMAP: "the four tools are not touched", and Phases 3 and 5's "no tool commits" rows | ROADMAP; already split by ADR-0013 | GOALS.md requires development in all four tools. ADR-0028 lifted the rule for that work, but the text still imposed it. | The cheapest proof that a discrepancy found in Phase 5 belongs to the harness rather than a tool. ADR-0013 already gave this up for interfaces. |
| R6 | ROADMAP: "a phase ends when it is declared finished" | ROADMAP | A single declarer is the serial reader ADR-0028 replaced. The audit grades with evidence. | A person's judgement as the closing step of a phase |
| R7 | ROADMAP's "not in this roadmap: ... a GUI" | ROADMAP | GOALS.md G6, HARN.4 and A6.1 | none |
| R8 | ADR-0013: "Numbers are not touched. No commit to a child changes what any run computes" | ADR-0013 (2026-09-06) | It is wider than rule 1, which requires only that the PROMOTED runs a change touches reproduce, and which admits new capabilities. As written it forbids every capability that QC.1, ANNO.1, INT.1 and PROF.1–4 need. ADR-0027's merges already departed from it. | The guarantee that no tool output ever changes. What stays is rule 1(c). |
| R9 | ADR-0016's "Standing rules — these do not relax ... must read 4 held after every commit" and its step ceremony ("not done until ... pushed. Update the status table ... in the same commit"), repeated as "Rules in force" in ADR-0017 to ADR-0026 | ADR-0016 to ADR-0026 | This is round ceremony, and ADR-0028 ended rounds as ADRs. The rules themselves are narrowed below. The ADR texts stand as records. | The per-commit "4 held" reading as a standing rule. The rules tier still checks whatever a repository declares. |
| R10 | The plugin-maker skill: "Convert ONE. Finish it. Have a person check it ... Then start the next" | skill (2026-09-10) | It serialised every conversion, while A4.2 asks for conversion "by agents alone" and tier III runs parallel waves. What it protects (no reader sees a family's surfaces before deciding any of them) holds per wave, so never-seen tools may convert in parallel. The eight held-out plugins still migrate one at a time, each graded before the maker changes, as RULES tier II reads the maker round's top rules. | A person's read of each conversion. A fresh verifier's read stands in. |
| R11 | `docs/blind/README.md`: a converted tool lands "never in its shipped set" | blind README | It kept every conversion out of the expandable pool that G4 is for. | The bright line between test material and the shipped set. A conversion that meets A4.2 joins the set through its wave's gate. |
| R12 | THE_CELLCHAT_ARC's eight "held out" with no stated end, read as "stay broken" | 2026-09-14 | Not withdrawn as a serial order: RULES tier II keeps the eight migrating one at a time. Withdrawn is the reading that they stay unrepaired: each is repaired through the maker in its own migration wave, and a dated note says so. | nothing tier II keeps |
| R13 | VISION.md §18's non-goals "Not a GUI first", "Not an autonomous analyst" and "Not built for a reader who cannot evaluate the evidence", read wider than GOALS.md | VISION.md:728-748 | Layer 0 calls the workflow autonomous and agent-operated (G7). G6 brings results to wet-lab users through a web interface (HARN.4, A6.1). A dated reading under §18 now says what each non-goal still binds. | The UI waiting behind the kernel; the non-autonomous scope; the computational-only audience. **Kept:** A1–A3 (an agent writes only through a declared mount; promotion and escapes are the user's), and approvals put to someone who can judge what they rest on. |

### The PI's rules, narrowed to their words (K-PI)

- **Held out.** The round's top rule 2 (2026-09-09/10), as recorded: "The other eight plugins are
  HELD-OUT TEST RESOURCES — do not touch them at all". The same week it was bounded twice:
  "held-out plugins untouched until their migration" (the 2026-09-14 record) and "the eight are
  held out until their own migration" (THE_CELLCHAT_ARC.md). The PI accepted ADR-0028, which makes
  that migration GOALS.md A4.1's waves.

  scProfile's reading has no end: "From this commit forward the eight are untouched", with the range
  pinned at f127a2b (DEVPOINTS.yaml:99-113, 131-139). That is wider than the words. **Narrowed:** a
  plugin's freeze ends when its migration wave starts, and the plugin is then repaired through the
  maker, not kept broken. The coordinator's tier-II reading of the same day agrees, and keeps the
  order: one at a time, DE and abundance first, each migration a blind test of the maker graded
  before the maker changes. The harness's skill says so now, and scProfile's declaration change is
  queued. If the PI reads the rule otherwise, the PI's reading wins.
- **End to end.** "End-to-end SAMBO is CELLCHAT-ONLY, the other eight UNPLUGGED" (same round). The
  words govern what that round ran on SAMBO. `sch dev rules` read them as an equality over the whole
  kernel list, so any new artefact broke the rule just by existing. **Narrowed** to disjointness
  (06cd34c): nothing held out runs end to end, and an artefact in neither list is named.
  **Given up:** the rule no longer forces every artefact that is not held out onto the end-to-end
  list. What that equality used to carry stays: `sch dev convert status` banners every artefact
  not held out as MAKER OUTPUT, never hand-edited. Until the verifier's finding the banner went to
  `end_to_end` names only, so a migrated plugin on neither list lost it. That weakened the PI's
  top rule 1 and is fixed.
- **In place.** "General mechanism and the agentic layer are fixed IN PLACE: scprofile/*.py,
  sch/**, jobs/, tests/" (same round). The words say where mechanism is fixed. scProfile reads them
  as an exclusive allow-list of paths, so committing a citation file or a lock breaks its rules
  tier. **Narrowing queued** in scProfile: drop the allow-list. A wave's registration and its
  verifier now say what a change may touch.
- **Rule 1.** "pass the SAMBO test without overfit or in-house script" (2026-09-06). Kept. Its
  wider reading in ADR-0013 is withdrawn (R8). Whether a change meant to move a promoted output may
  merge on a predicted difference is put to the PI, not decided here.
- **Rule 2.** "do not run cellbender for single cell"; "single cell and single nuclei is
  fundamentally different!" (2026-10-02). Kept. scQC's single-cell route reads it as "no ambient
  handling of any kind on cells", but the words ban CellBender. **Narrowing queued** in scQC.

### The shared-config hazard of isolated worktrees (two incidents, 2026-11-09)

1. **The absolute hooks path.** About 07:2xZ the shared `.git/config` held an absolute
   `core.hooksPath` to the main checkout's own `setup/githooks`. The gate still ran, but G1's
   literal comparison failed: three tests failed and the pre-commit hook blocked the
   coordinator's commit (BLK-001). This pass did not establish what wrote the absolute value. R1
   makes that value pass.
2. **The suite reaching the real repository.** At 07:35Z this pass committed in its linked
   worktree, and the gate ran the suite. In a linked worktree, git hands a hook an absolute
   `GIT_DIR` and `GIT_INDEX_FILE`; in the main checkout it hands only `GIT_INDEX_FILE=.git/index`,
   relative, and no `GIT_DIR` (measured with git 2.55.0). So every test's `git -C <tmpdir> ...`
   acted on the real repository instead of its temporary one:
   - `git init` set `core.bare=true`, and the main checkout stopped being a work tree (BLK-003);
   - `git config user.email t@t` and `user.name t`
     (tests/test_the_rules_of_a_round_are_checked_not_promised.py:197-198) wrote a `[user]`
     section, so f488621 on main (07:35:44Z, already pushed) is authored "t <t@t>";
   - the tests' fixture commits advanced this pass's branch;
   - this pass's new G1 test created a branch, `side`.

   **Repair.** The coordinator restored `core.bare` and removed the `[user]` section. This pass
   reset its branch and deleted `side`. Rewriting f488621 needs a force-push, which is the PI's
   call.

   **The fix** is 2a6f77b on main:
   - the hook unsets `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`, `GIT_COMMON_DIR`,
     `GIT_OBJECT_DIRECTORY`, `GIT_ALTERNATE_OBJECT_DIRECTORIES`, `GIT_PREFIX` and `GIT_NAMESPACE`
     before anything runs, and writes its logs to mktemp files;
   - a guard module, sorted last, removes the same variables at discovery. It fails if the suite
     changed the real repository's `core.bare`, `core.hooksPath`, `core.worktree`, local
     `user.name` or `user.email`, or this checkout's HEAD.

   It was rehearsed first on a scratch replica. There the guard failed on a planted config write,
   and a commit from a linked worktree left the replica's config and branches unchanged. Each real
   commit since has left `git config --local --list` byte-identical.

   **The rule it leaves:** a test that runs git names its own temporary repository, and nothing
   inherited may name another.

### Kept (K-GUARD), and why

- **ARCHITECTURE.md's invariants** protect the runtime's correctness:
  - reversibility and reactive invalidation (E1–E5, D1–D5), for G2;
  - provenance that cannot go missing (P1–P3, D6), for G2 and for G5's audit;
  - gates that are auditable and monotonic, with their escapes recorded (G1–G4), for G2 and G7;
  - an agent that writes only through a declared mount, while promotion and escapes stay the
    user's (A1–A3), for G7's "decisions declared as the user's stay the user's" and tier II.

  Amending an invariant costs a record. That is an ADR's own purpose under ADR-0028, not round
  ceremony.
- **The commit gate itself** (the suite and conform on every commit). It protects rule 1(a) on
  `main`, where the coordinator commits directly.
- **Rule 1's mechanisms:** the leak guard, whose terms live outside the repository; the prediction
  written before submission; reproduction as the test.
- **Refusals that stop a silent wrong answer.** For G2, G3 and G7:
  - no default assay (conform S13);
  - a refusal names its fix;
  - `sch dev job` refuses a build that owes, except under a recorded `--anyway`.
- **The four round-era submitters' "exactly one kernel" refusal** (`jobs/submit_*.sh`). It keeps a
  cellchat reproduction in the environment its reference ran in, because environment identity
  depends on group membership. Trimming it to an environment-identity check waits on scProfile's
  per-plugin isolation, which is queued.
- **X2 and X3, the plugin contract's compatibility promise.** ADR-0012 stays proposed and is the
  PI's to decide. No wave waits on a change of meaning.

### Put to the PI (ASK; nothing changed)

1. **Predicted differences.** May a change that is meant to move a promoted run's deterministic
   outputs merge on a difference predicted before submission? Re-promoting the moved run would
   stay the PI's. **Open.** Answering it amends tier-I rule 1, which only the PI changes.
2. **SAMBO's DE sign convention.** scProfile's `second-cohort` branch has been open since
   2026-10-02. GOALS.md PROF.4 quotes the report's own direction ("aged vs young, HFD vs chow"), so
   the pre-decider may find it already decided.
3. **scRNA count floors.** Should they stay fixed at 500/250, or be derived within the PI's
   declared bounds of 500–2000 UMI and 250–1500 genes (D8)? GOALS.md QC.1 asks for "count floors
   derived from the data". D9's declared floors were a decision about one cohort.

## Consequences

**Easier.** The four tools can now reach A4.1, because conform and the rules tier no longer fail a
repository for having no round or no hook. The eight held-out plugins can migrate, each in its own
wave, and a conversion that meets A4.2 can join the pool. A failed phase test no longer halts the
other lanes.

**Harder.** Nothing new is required of anyone, but three things no longer happen by default:
- a fresh clone without its gate installed now only warns;
- the eight plugins lose their protection from repair once their wave starts;
- a tool may change the outputs of runs that are not promoted.

Rule 1's gate, the wave's registration and its verifier carry those instead.

**What property is given up** is stated item by item above. In one line: the September guarantees
that the tools never change, that eight plugins never change, that a phase stops at its first
failed test, and that a person reads every conversion. Rule 1's gate, the wave's registration and
verifier, and the audit's graded evidence replace them.
