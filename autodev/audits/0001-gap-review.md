# Gap review 0001: the single-cell harness family against GOALS.md

**Pass** 0001 (the gap review), audit team, read-only. **Stamp** 2026-11-09T06:29Z.
**Graded against** `GOALS.md` at harness `59db2a9`: twenty layer-3 tests, A1.1 to A7.1, including A6.3. The
file changed during the pass. A3.4 gained the 1,000,000-cell bar, A6.1 now takes "the report's words" as its
design, A6.2 now requires that "Studio shows the run", and A6.3 and PLAT.1–3 are new. Every grade below
follows the committed text. The brief used the old layer-2 ids; drop the `G2.` prefix to get the current
ones (G2.QC.1 → QC.1).

**What was read.**
- The harness: `single-cell-harness` main, `59db2a9`.
- scQC main `cf0b750`, plus `origin/single-cell-route` `0e6a5f6`.
- scAnno main `c16c56a`.
- scIntegrate main `722bc79`.
- scProfile main `f294c89`, plus `origin/second-cohort` `48aaeba`. All four were freshly cloned with every branch.
- The SAMBO and BrainOrganoid_C46 record mirrors.
- `scrnaseq-lab`'s README, for A6.2.
- The cluster, through three read-only ssh connections (ls, cat, head, git, find, qstat; nothing written).

**Evidence conventions.**
- **[v]**: the reviewer re-read it in the code, ran the command, or read it on the cluster.
- Unmarked `file:line`: found by one of this pass's read-only sub-audits, at the commit named above. There
  were four sub-audits (scQC; scAnno with scIntegrate; scProfile's plugins and maker; scProfile's workflow
  and reports) and a records audit. The reviewer spot-checked 23 of their load-bearing citations, and all
  held.
- **INFERRED**: an inference.

**Paths.** Tool paths are relative to that tool's repository. **S** is the SAMBO mirror and **C** the
BrainOrganoid_C46 mirror. `RL` is RUNLOG.md and `DE` is DECISIONS.md.

**Numbers about data.** Every such number is copied from a sealed run's own table, or from a record that
quotes one. The reviewer computed none, so each is "tool-reported" and comes with the stage it describes.

---

## 1. Verdict and scoreboard

**NOT HAPPY.** No test passes. 6 are PARTIAL, 13 FAIL, and A6.3 is UNKNOWN (deferred to pass 0001b).

The family today is four capable stage tools and a well-tested runtime kernel that cannot run any of them.
**SAMBO has been through all four stages, but only by hand.**
- Each stage ran from a hand-written project job script.
- Project glue sat at every boundary:
  - CellBender, and its conversion, ran outside scQC;
  - the marker tree and the CellMarker corpus were made by the project;
  - stage 3 rebuilt the design with awk;
  - stage 4's controls were declared by hand;
  - every promotion was made by hand.
- Stage 4 has no promoted run, and stage 2's promoted run was never reproduced.

**The second cohort stopped after stage 1, on 2026-10-02.**
- Its stage 1 was a scQC branch run. That branch reproduced SAMBO's promoted stage 1 IDENTICAL (PBS
  `720930`, read on the cluster today) and sealed C46 in apply mode (PBS `720932`).
- Neither result reached the records, and the branch was never merged.
- So scQC `main` still schedules CellBender for single cells, against the PI's rule 2.
- `~/tools/scQC` on the cluster is checked out on that unmerged branch.
- No SAMBO or C46 run has been made since 2026-10-03 [v].

**scProfile is the furthest behind.**
- Its environment cannot be built from `main`.
- Differential abundance has never run.
- No plugin covers pathways.
- DE on `main` contrasts in the wrong direction.
- Only CellChat is in the maker's layout, and it was migrated by hand.
- The PI's 2026-09-10 rule holds the other eight plugins "held out", and keeps two of them broken on purpose.
  That rule is enforced by scProfile's `sch dev rules`, but it is missing from `autodev/RULES.md`.

**Nothing exists for the co-scientist (A5.2) or the UI (A6.1).**

**Slide 16 is ahead of the code on three ticks.**
- "End-to-end automated": there is no orchestrator.
- "Automated running environment setup": scProfile cannot build its environment, and scQC's CellBender
  environment broke on C46.
- "Design-aware": on `main`, DE runs in the wrong direction, covariates are unsupported, and abundance drops
  the interaction.

**The code is ahead of GOALS.md in places.**
- scQC's evidence mode cannot remove cells, and every threshold carries a class.
- scProfile measures peak memory and cores for every instance. It also keeps a claims ledger that binds each
  claim to a figure's hash and refuses a reviewer who is the author. Slide 16 calls interpretation "To be
  done", which understates this.
- scAnno refuses a declared species that the gene identifiers contradict.
- The harness's development suite is stronger than any layer-3 test asks for: 606 tests green [v], an
  adversarial suite, a two-shape fixture, and a scan for literal defaults.

| test | grade | one-line reason |
|---|---|---|
| A1.1 one request, every stage | **FAIL** | No orchestrator. SAMBO ran stage by stage with glue, and stage 4 is unpromoted. C46 stopped at stage 1. |
| A1.2 the ten steps mapped | **PARTIAL** | Steps 1–7 and 10 have a component that has run. Step 8 has run only for DE, never for abundance. Step 9 has no pathway component, and its trajectory plugins have never run. No checked mapping exists. |
| A1.3 environments from main | **FAIL** | scProfile cannot build from `main` (PBS 720377). scQC's torch is unpinned (PBS 720477 failed). Two self-tests are import-only. |
| A2.1 pre-declared reproduction | **PARTIAL** | Stage 1 is IDENTICAL six times. Stage 3 is DIFFERENT, with its spread measured. Stage 2's promoted run was never reproduced, and stage 4 has no promoted run. |
| A2.2 documentation true | **FAIL** | False claims were found in all five repositories. |
| A2.3 cold reproduction | **FAIL** | Never attempted. |
| A3.1 held-out cohorts | **FAIL** | C46 stopped at stage 1. scProfile fails the leak guard. The fixture axes reach a pipeline in 1 of 4 tools. |
| A3.2 design-aware | **PARTIAL** | One factor and the interaction run in DE. Covariates are neither modelled nor refused. DE runs in the wrong direction on `main`. Abundance drops the interaction. |
| A3.3 assay rule sets | **FAIL** | scQC `main` runs CellBender on single cells. scAnno, scIntegrate and scProfile have one rule set and nucleus wording. |
| A3.4 scale | **FAIL** | No cohort of 1M cells or more. Peak memory is recorded only by scProfile. |
| A4.1 the existing pool in one format | **FAIL** | 1 of 9 plugins is in the maker's layout, and that one was hand-migrated. The other eight are held out by rule. |
| A4.2 the maker on new tools | **FAIL** | No draw rule and no catalogue tool converted. Two blind conversions were never merged. |
| A4.3 provenance of methods | **PARTIAL** | 9 of 9 cite a paper as free text, with no DOI. 3 of 9 pin their upstream exactly. |
| A4.4 AI-native | **FAIL** | No catalogue. The harness cannot see scProfile's plugins. |
| A5.1 report from evidence | **PARTIAL** | The claims ledger and review exist for CellChat only. A withdrawn claim stays in the rendered page, and the run is unpromoted. |
| A5.2 hypotheses | **FAIL** | No code. |
| A6.1 Harness UI | **FAIL** | No code. |
| A6.2 Studio hand-off | **PARTIAL** | Lab and Studio worked once, on the stage-2 joint object (PI, 2026-08-19). The final object has never been tried, and Studio shows no run. |
| A6.3 Service takes single-cell requests | **UNKNOWN** | Outside this brief; deferred to pass 0001b. |
| A7.1 agents drive it | **FAIL** | No skill runs a cohort. C46 is no longer held out. |

---

## 2. The acceptance tests, one by one

### A1.1 one request, every stage — FAIL

**There is no orchestrator.**
- The kernel finds a plugin only as a directory holding `plugin.yml`, under `$SCH_PLUGINS` or `plugins/`
  (`sch/kernel.py:97-117` [v]).
- The `pbs` executor is refused as "not shipped before ROADMAP Phase 9" (`sch/services/executor.py:147-148` [v]).
- "Phases 3 and 5–9 are not built" (`ROADMAP.md:326-331` [v]). Phase 3 is the first adapter, `qc@scqc`.
- `plugins/` holds only gate, probe, table and toy single-cell plugins [v].

**SAMBO ran stage by stage, with glue at every boundary.**
- Stage 1's input was CellBender run outside scQC, then converted by
  `S stages/01_qc/cellbender_to_h5ad.py`. That script writes `cellbender_cell` at line 110.
- Stage 2 read a hand-made `S stages/02_annotate/mouse_heart_tree.json` and a project-built
  `cellmarker3_mouse.db` (`S 02_annotate/RL:127-188`).
- Stage 3 rebuilt the design with awk (`S 03_integrate/jobs/21_scintegrate_integrate.pbs:113-127`), because
  stage 2 had dropped age and diet (`S 02_annotate/RL:1750-1752`).
- Stage 4 used a hand-written `design.csv` and hand-declared `--control` flags (`S 04_profile/RL:23`;
  `scprofile_cellchat.pbs:180-214`).
- Every promotion was a `cp -al` plus a hand-written `PROMOTED.md` (`S 01_qc/RL:2666-2675`).

**Profiling is incomplete.**
- Abundance has never run (`S 04_profile/RL:189, 313, 817`).
- DE ran once (PBS 720487). That run is unpromoted, and it contrasts against the declared controls
  (`kernels/de.py:1392-1404` [v]; `S 04_profile/RL:767`).
- Stage 4 has no promoted run (`S 04_profile/RL:756`).

**C46 stopped at stage 1.**
- Its stage 1 sealed in apply mode: PBS `720932`, `exit=0`, "4 libraries; deliverable written" [v, cluster].
- The run used the unmerged scQC `0e6a5f6`, and `results/` is empty [v].
- Stages 2 to 4 have not started.

**What is missing.** GAP-001, -002, -028, -039 to -041, -055, -056.

### A1.2 the ten steps mapped — PARTIAL

No document declares the mapping. The reviewer's mapping, read from the code:

| step | component | has it run on a cohort? |
|---|---|---|
| 1 alignment, cell calling | upstream: Cell Ranger or CeleScope. scQC can run CeleScope's alignment (`engine/steps.py:853`) and gates the call. scQC's single-cell route takes Cell Ranger's call. | yes (SAMBO through CeleScope; C46 through Cell Ranger) |
| 2 ambient RNA | scQC (CellBender) for nuclei; none for cells on the branch (`modules/01_ambient/ambient.py:59` [v]) | SAMBO: CellBender ran outside scQC, and scQC's accept-and-audit route ran. CellBender inside scQC has never completed (C46, PBS 720477, failed). |
| 3 quality control | scQC steps 5–7 | yes |
| 4 doublets | scQC (scDblFinder) | yes |
| 5 normalisation, feature selection | scAnno `cluster` (`scanno/cluster.py:136-141` [v]) | yes |
| 6 batch integration | scIntegrate | yes (SAMBO) |
| 7 clustering, annotation | scAnno | yes (SAMBO) |
| 8 differential abundance and expression | scProfile `abundance` and `de` | abundance **never**; DE once, unpromoted |
| 9 pathways, trajectories | trajectories: `pseudotime` (CellRank) and `velocity`. Pathways: **no component** (`kernels/decoupler.py:209-212` [v]) | **no** |
| 10 other advanced analyses | cellchat, liana, SCENIC, cellcycle | cellchat only (about 35 runs, none promoted) |

**What is missing.** GAP-058, -041, -042, -043.

### A1.3 environments from main — FAIL

**scProfile cannot build its shared environment from `main`.**
- The build fails with pip `resolution-too-deep` (PBS `720377`; `ADR-0027:179` [v]).
- The kernels declare ranges, not pins (`kernels/de.py:185`, `abundance.py:178`, `pseudotime.py:164`,
  `decoupler.py:152` [v]).
- The environment's name hashes those ranges (`scprofile/resolve.py:215-219` [v]), and no lockfile exists.

**scQC leaves the denoiser's torch unpinned.**
- The installer pins `cellbender==0.3.2` but never names torch (`setup/install_env.sh:313-316` [v]).
- C46's first run died inside CellBender under torch 2.14.1 (PBS `720477`; `ADR-0027:182` [v]).
- scDblFinder is unpinned too (`install_rdoublet.sh:94-95`).
- The core lock is good: 144 lines, all `==`.

**scIntegrate.**
- `--add-to` installs its four method packages unpinned (`setup/install_env.sh:103,144`).
- Its self-test, `doctor`, is an import probe.

**scAnno.**
- The lock pins 15 packages; their own dependencies are unpinned.
- `scanno selftest` runs only `tests/test_adversarial.py` (`cli.py:28-34`).

**The cluster.** `~/tools/scQC` is checked out on `single-cell-route` `0e6a5f6`, not on `main` [v].

**What is missing.** GAP-038, -018, -036, -032.

### A2.1 pre-declared reproduction — PARTIAL

| stage | promoted run | its reproduction | outputs that vary between runs |
|---|---|---|---|
| 1 QC | `6e3b4b97cb38`, scQC `133a951`, PBS 684955 | **IDENTICAL** six times: 706147, 719947, 720101, 720466, 720697 (`S 01_qc/RL:2710-2796`) and 720930 (on the cluster, 100,713 = 100,713, every criterion column and the deliverable's names [v]; not yet in the RUNLOG) | UMAP coordinates: named, spread **not measured** (`RL:2571`) |
| 2 annotation | scAnno `bd45f5d`, PBS 664864 | **never**. 706249, 719992 and 720434 reproduce a non-promoted rescue run (`S 02_annotate/RL:2064`). 664864 has no RUNLOG entry. | none named |
| 3 integration | scIntegrate `713d918`, PBS 671045 | **DIFFERENT** on harmony only (706190). The prediction failed, and the spread was then measured: node-to-node 0.214, same process 1.6e-12, harmony's total about ±0.013 run to run (`S 03_integrate/RL:406-435`) | harmony: named and measured |
| 4 profiling | **none** | 706253 IDENTICAL, but against the non-promoted 703240 (`S 04_profile/RL:722, 746`) | the CellChat network embedding is unseeded; no spread |
| C46, any stage | **none** [v] | — | — |

**What is missing.** GAP-033, -055, -057, -010.

### A2.2 documentation true — FAIL

Each repository was sampled. Every one has false claims. Examples:

**The harness.**
- README shows `sch diff main no-qc --on composition`, but `sch diff` is not a command [v].
- Its `sch stack` transcript mounts `qc@scqc`, `annotate@scanno` and `integrate@scintegrate`. No adapter
  provides any of them [v].
- It says "144 tests"; 606 run [v].
- It says "all four pass with no failing row". Today scProfile fails S1, and three tools fail G1 [v].
- It says "most recently PBS 707628, every tier green", but PBS 719917 had failures (`ADR-0027:153-161`).

**scQC.**
- `README.md:84` calls single-cell ambient "optional"; CellBender is scheduled for every assay
  (`engine/graph.py:104-127` [v]).
- `README.md:163` says a stale report is refused; `refuse_if_stale` has no caller (`report/build.py:2631`).
- `QUICKSTART.md:79`; `USER_GUIDE.md:61,78`.

**scAnno.**
- Every `annotate` example omits the now-required `--assay`.
- `scanno/corpus.py:5-8` documents `scanno build-markers`, which does not exist (0 hits in `cli.py` [v]).

**scIntegrate.**
- `README.md:26` says a run goes on without scib, but the import is unguarded (`benchmark.py:175` [v]).
- The wrapped versions recorded in STATUS are always `{}` (`status.py:91,124`).

**scProfile.**
- The README quickstart cannot launch without `--prefix` (`runner.py:118`, `cli.py:606-623`).
- "Pathway activity" has no code behind it (`decoupler.py:209-212` [v]).
- `docs/EXECUTION.md:259-271` documents PBS and SLURM executors, but the runner is local threads only.

**What is missing.** GAP-009, -022, -031, -037, -052. The sampling protocol is in §7.

### A2.3 cold reproduction — FAIL

Neither project records a cold reproduction (records audit). The nearest attempts are not reproductions:
- `docs/blind/0004-writing.md`: cold agents drove the test phase of a sealed scProfile run's replay, 7 of 9.
- ADR-0026: a cold maintainer replayed six maker edits in 18 minutes.

Neither reproduces a run from its record [v].

**What is missing.** GAP-004, -003, -010.

### A3.1 held-out cohorts — FAIL

**C46 stopped at stage 1** (see A1.1).

**The leak guard.** Run with both cohorts' word lists [v]:
- scProfile fails S1 on four hits: `tests/test_figure_audit.py:330`,
  `tests/test_the_compare_launches_share_the_pool.py:6`, `tests/test_one_fact_many_phrasings.py:26` and
  `docs/ANATOMY_OF_A_RUN.md:7`.
- scQC, scAnno and scIntegrate pass S1, but only because the word list holds no factor levels or queue names
  [v]. Their tests do carry them:
  - scQC `tests/test_figure_collection.py:176-178` (young/aged, chow/hfd) and
    `tests/test_parameters_are_not_factors.py:27-29` (WT/Mut);
  - scAnno `tests/test_embed.py:87-88`;
  - scIntegrate `tests/test_methods_settings.py:53`.
- Queue names are hard-coded in scAnno `jobs/TEMPLATE.pbs:3` and in five of scProfile's `setup/*.pbs`. S5
  reports them only as a WARN [v].

**The fixture's value axes reach a tool's pipeline in 1 of 4 tools.**
- scQC: `describe` only (`DEVPOINTS.yaml:12-21` [v]).
- scAnno: `cluster` only.
- scProfile: ends at "are not ready in this installation" (`DEVPOINTS.yaml:58-59`; the dev-suite job sets
  no `SCH_DEV_PREFIX`).
- scIntegrate: runs its real `integrate`.
- ADR-0027's prediction 3 was "not measured as worded" for this reason (`ADR-0027:197` [v]).

**What is missing.** GAP-008, -051, -007, -023, -032, -054, -056.

### A3.2 design-aware — PARTIAL

**One factor, n = 2 per arm.**
- DE and abundance run at n = 2 (`kernels/de.py:134`, default 2 [v]).
- Meanwhile `plan` prints "BELOW 3 PER GROUP: compositional and pseudobulk tests refuse"
  (`scprofile/cli.py:1862-1866` [v]).
- A factor with arms of 1 and 2 is planned RUN and then refused at run time (`planner.py:401-404` vs
  `de.py:1243-1248`).

**Two factors with an interaction.**
- DE fits the interaction and contrasts it (`de.py:1369-1503`).
- Abundance fits `formula=term`, one factor at a time, and silently drops the interaction
  (`abundance.py:1516-1525` [v]).
- DE's caveat says the interaction "is not contrasted" when it was (`de.py:1700-1711`).

**A covariate.** Neither modelled nor refused by name (`scprofile/inputs.py:756-769, 921`).

**Labels.**
- The host labels contrasts per stratum on the CellChat pages (`design_panel.py:537-568`), as slide 15 does.
- On `main`, DE contrasts `sorted(levels)[-1]` against `[0]` (`de.py:1394, 1403` [v]). So SAMBO's DE ran
  young vs aged and chow vs HFD, against its own declared controls (`S 04_profile/RL:767`).
- The fix, `48aaeba`, is unmerged. It held every fold change but missed its own p-value tolerance
  (PBS `720548`).

**What is missing.** GAP-039, -040, -047.

### A3.3 assay rule sets — FAIL

**scQC `main`.**
- `ambient` is scheduled with `gpu=True` for every library that was not supplied, whatever its assay
  (`engine/graph.py:104-127` [v]). That violates rule 2.
- The count bounds were calibrated on nuclei and apply to every assay (`quality.py:57, 62`).
- The fix exists on the branch: `DENOISE = {"snrna": True, "scrna": False}` (`modules/01_ambient/ambient.py:59`
  [v]) and `_ambient_none` (`engine/graph.py:178` [v]).
- The branch reproduces SAMBO IDENTICAL (720930 [v]) and sealed C46 (720932 [v]), but is unmerged.

**scAnno.**
- `--assay` is required but changes no rule (`cli.py:80, 207, 619, 1223` [v]).
- The report says "nuclei" whatever the assay (`report.py:318, 369`).

**scIntegrate.**
- It takes no assay.
- It prints "a design with one library per animal" on every cohort (`cli.py:739-742` [v]).

**scProfile.**
- `detect_assay` "changes the CAVEATS, never the code path" (`inputs.py:274-276` [v]).
- CellChat's `cannot_show`, written for nuclei, is printed on every cohort (`cellchat.py:1349-1351`).
- Its memory models were fitted on nuclei (`de.py:199`).

**What is missing.** GAP-017, -024, -029, -034, -050, -011.

### A3.4 scale — FAIL

**No cohort of 1,000,000 cells or more has run.** The largest is SAMBO's stage 1: "100,713 delivered of
305,425", a record quoting the sealed run (`S 01_qc/RL:2633`).

**What each tool records per stage.**
- scProfile records `peak_rss_gb`, `wall_s` and `n_cells` for every instance (`_entry.py:762-787`).
- scQC records task seconds and cell counts, but no memory (`engine/pipeline.py:439, 478-480`).
- scAnno records only start and finish stamps.
- scIntegrate records nothing.
- For stages 1 to 3, peak memory exists only as PBS requests written into RUNLOG prose.

**What is missing.** GAP-016, -015.

### A4.1 the existing pool in one format — FAIL

**1 of 9 plugins is in the maker's layout: CellChat.**
- It has a generated companion (`kernels/cellchat.draw.R:3`), a signatures file, and plan entries that carry
  their call.
- It was migrated "by hand-pasted worksheets" (`docs/blind/0003-deseq2.md:8`).

**The other eight** carry `wraps.plots_unreviewed` (for example `abundance.py:47`) and owe the inventory and
plan stages.

**scProfile's round rule 2 keeps them held out, and two of them broken.** It reads: "abundance's
pertpy/statsmodels ImportError and de's unsatisfiable pin STAY BROKEN" (`DEVPOINTS.yaml`, `rules.held_out` [v]).
`sch dev rules` reports today: 4 held, 0 broken [v].

**`sch conform` is repository-level**, so it cannot certify a single plugin (§7).

**What is missing.** GAP-044, plus the PI's decision on the held-out rule (§5).

### A4.2 the maker on new tools (at least 4 of 5) — FAIL

- No draw rule exists, and no tool from the catalogue has been converted.
- Two cold conversions exist, but neither was merged (both are test material in `tests/smoke/plugins/`), and
  neither reproduced a published example:
  - gseapy (blind 0002): build 9/9, and test 6/6 on the fixture (PBS 710976);
  - DESeq2 (blind 0003): build 8/8, on the workstation only.
- The maker reads code (`python_package`, `r_namespace`, `shared_env`) and never the paper. INFERRED: no
  extractor takes a paper.

**What is missing.** GAP-046.

### A4.3 provenance of methods — PARTIAL

- All nine plugins cite a paper as free text in `wraps.cite`. There is no DOI field anywhere.
- 3 of 9 pin their upstream exactly: velocity `scvelo==0.3.4`, scenic `pyscenic==0.12.1`, cellchat a git
  commit. The other six pin ranges (`de.py:185`, `abundance.py:178`, `cellcycle.py:196`, `decoupler.py:152`,
  `pseudotime.py:164`, `liana.py:244` [v]).
- The maker's template seeds a range and has no DOI or version field (`scprofile/onefile.py:33, 74`).
- The cite and licence checks never run for one-file plugins (`validate.py:72-110` returns before
  `:239-241`).
- abundance cites pertpy as "Büttner et al., 2024". INFERRED misattribution: pertpy's paper is Heumos et al.
  Check pertpy's own CITATION file.

**What is missing.** GAP-045.

### A4.4 AI-native — FAIL

- scProfile has 23 subcommands, and none of them lists the catalogue [v].
- `doctor` prints `when_to_use` for each kernel. `plan --report` needs an h5ad.
- The harness's agent surface cannot see scProfile's plugins at all (`sch/kernel.py:97-117` [v]).
- Nearby evidence: cold agents did drive CellChat's test phase through scProfile's own agenda (blind 0004).

**What is missing.** GAP-005, -006.

### A5.1 report from evidence — PARTIAL

**What exists, for CellChat on SAMBO.**
- `scprofile paper --claim … --cites <figure>` refuses a claim whose figure does not exist, and binds the
  figure's sha256 (`paper.py:165-177, 193`).
- The reviewer must not be the author (`paper.py:221-227`).
- SAMBO's ledger reads "2 withdrawn, 1 narrowed, 1 standing" (`S 04_profile/RL:599`).

**What is missing.**
- **Generality.** Only network plugins get a composed section (`compose.py:62`), and there is one writing
  template.
- **Removal.** The rendered page prints the author's body verbatim, after banners for stale or unreviewed
  claims only. A withdrawn claim is not removed (`paper.py:755-802` [v]).
- **Tables cannot be cited** (`paper.py:976`).
- **Independence** is only a different name string.
- **The run is unpromoted.**

Gaps: GAP-047, -048, -055.

### A5.2 hypotheses — FAIL

No code generates a hypothesis, a falsifying test or a follow-up. `brief.py:319-321` is guidance text, and
`feedback.py` diagnoses the tooling.

**What is missing.** GAP-012.

### A6.1 Harness UI — FAIL

None of the five repositories has UI code [v]. Slide 4 says "Harness UI (TBD)".

**What is missing.** GAP-013.

### A6.2 Studio hand-off — PARTIAL

**What exists.** The Lab-to-Studio route worked once, on a family object. The PI attested it: SAMBO's stage-2
joint h5ad "was opened in scRNA-seq Lab and Studio and works" (`S 02_annotate/DE:949`, 2026-08-19).

**What is missing.**
- No record shows the final object (stage 3's `cohort_integrated.h5ad`, or stage 4's) being opened.
- Nothing shows Studio displaying the run that produced an object.
- Lab converts in the browser after two interactive questions (`scrnaseq-lab/README.md:3-16` [v]).

Gap: GAP-014. The platform side belongs to pass 0001b.

### A6.3 Service takes single-cell requests — UNKNOWN

Not reviewed: this brief covered the platform for A6.2 only, and pass 0001b covers the rest. INFERRED likely
FAIL: the only Service path on record is bulk RNA-seq into nf-core/rnaseq (the `rnaseq-hpc-request` skill's
description).

### A7.1 agents drive it — FAIL

**The skills cover other jobs.**
- `harness-agent` covers the kernel's plan, mount and ask loop, and leaves PBS to the site skill
  (`skills/harness-agent/SKILL.md:24-34, 92-96` [v]).
- `harness-developer` covers extending the family.
- `plugin-maker` covers converting a plugin.

**None of them assembles or submits a cohort's stages.** SAMBO and C46 were driven by the coordinator,
through project job scripts.

**C46 is no longer a held-out cohort.** It was used to upgrade the tools (ADR-0027).

**What is missing.** GAP-003 and -001, plus a held-out cohort (§7).

---

## 3. The layer-2 capabilities

| id | what exists, and where | distance from the report's words |
|---|---|---|
| **QC.1** | scQC steps 0–7 (`engine/steps.py`). Derivation is separate from removal: step-7 tasks exist only in apply mode (`engine/graph.py:371`), and evidence mode removes nothing. Per-library valleys give the count floors, then one cohort constant (`quality.py:164`). The mito ceiling is per library and per assay (`quality.py:330`). | **Nuclei: close.** **Cells, on `main`: wrong**, because CellBender is scheduled and the bounds are for nuclei. **Cells, on the branch:** the floors are declared (PI D8/D9), not derived. On C46 the declared lower bound set all four mito ceilings (tool-reported `mito_clamped=lower` [v]), so "data-aware" holds for nuclei only. The default `--mode apply` derives and removes in one command (`scqc_cli.py:791` [v]), while the report says "PROPOSED, not applied… needs approval" (`quality.py:202`). |
| **QC.2** | `reports/qc_report.html` and `report.json`. A threshold table per library, plus a class table "What was decided, and by whom". 18 matplotlib figures, embedded in the HTML. | `figures/` is still empty: 0 files on PBS 720932 [v], so slide 5's "nothing writes one yet" is still true. Who approved never reaches the HTML. Declared floors are labelled DERIVED. Parameters that have CLI defaults are reported as having "no default". |
| **ANNO.1** | A hierarchical walk with a truncation rule: `if gap < gap_min: break  # TRUNCATE` (`classify.py:132-133` [v]). The label stops at the parent, the "stays at Lymphoid" behaviour. A scope vote across samples, unanimous by default (`scope.py:54`). | "Consensus" here is agreement across samples, not across sources. There is no root-fit floor. CellMarker 3.0 is only whatever SQLite file the project built: no version, no builder. The tree must be supplied and none is shipped. |
| **ANNO.2** | Seed 0, and the classifier is deterministic (INFERRED). Three IDENTICAL reproductions of the rescue route (18 columns × 10 libraries). | Speed is never measured. No test runs annotate twice. `0.12.0` names more than one code state. |
| **INT.1** | `assess` (foreign-neighbour share), five methods (none, harmony, bbknn, scvi, scanvi), the real `scib.metrics`, `cohort_integrated.h5ad`, and `reports/integration.html` with figures F1 by label and F2 by batch (`cli.py:796, 807`). These match slide 14. | `assess` advises and never gates. A winner is chosen even when the totals are not comparable. Harmony's measured spread is not shown. There is no assay or species, the "per animal" wording is printed everywhere, and the code is untouched since 2026-09-08. |
| **PROF.1** | `sch dev` (convert, edit, rules, scaffold, ladder), `skills/plugin-maker`, and scProfile's `scaffold`/`onefile`. Tested by blind conversions (gseapy, DESeq2) and by ADR-0026's random edits. | No shipped plugin was produced by the maker; CellChat was hand-migrated. The maker reads code, never a paper. "Universal Plugin Format" is two formats (harness `plugin.yml`, scProfile `PLUGIN` dict). "Peer-reviewed standard protocol": the format is in-house and has not been peer reviewed. |
| **PROF.2** | Design resolver (`inputs.py`, `units.py`, `design_panel.control_for`). Planner (`planner.py`). Scheduler (`kernels.schedule`). Runner (`runner.run`, local threads). Results, report. | Not self-assembled: the user names the plugins (`cli.py:245` [v]), and the scheduler only orders them along one edge. There is no "reproducibility suite building" step. On `main` the control never reaches DE or abundance. |
| **PROF.3** | All eight named methods exist as kernels, plus liana (CellRank is real, `pseudotime.py:1146-1161`). | Pathways have no plugin. Abundance has never run, and two of the plugins are kept broken by rule. Six have never run on a cohort. Slide 4's "Now support" means "the code exists". |
| **PROF.4** | Per-plugin pages with per-stratum sections ("F given G = g") and between-arm panels from `unit_network`. Slide 15's three CellChat panels come from these runs. | CellChat only in practice; DE and abundance get no per-contrast report. Nothing is promoted. |
| **HARN.1** | None in code. The SAMBO stack exists as four hand-run stages with records (RUNLOG, DECISIONS, PROTOCOL; tools seal their own runs since 2026-09-06). | The whole capability is missing (GAP-001, -002). |
| **HARN.2** | `sch scratch`/`promote`/`ask`, with 8 adversarial attacks (`tests/test_adversarial.py`). Three skills. The `sch dev` suite. `autodev/` (created 2026-11-09; no wave has run). | No agent assembles or coordinates a cohort's workflow. The coordinator does it by hand. |
| **HARN.3** | Nothing. | Missing (GAP-012). |
| **HARN.4** | Nothing. | Missing (GAP-013). |
| **PLAT.1–3** | Lab converts `.h5ad`/`.rds` in the browser. Studio explores the bundle (last commits 2026-08-20). Service: not read. | Pass 0001b. On record: one stage-2 object opened (A6.2). |
| *(no id)* slide 16 "Figure generation and configuration ✓" | All four tools draw figures. scProfile's figure plan is a declaration, edited through the maker (`ctx.draws`, `--figures-for`). | Partly true. scQC writes no figure files, and no tool has a per-run figure plan a user edits. GOALS.md has no capability or test for this tick (§7). |

---

## 4. The gap register

Every row below is also in `gaps_0001.tsv`. The ledger `autodev/ledger/gaps.tsv` has three more columns (stamp,
pass, status). When copying a row in, use stamp 2026-11-09T06:29Z, pass 0001 and status open.

**Size.**
- **S**: up to 1 day of agent development.
- **M**: up to 3 days.
- **L**: up to 2 weeks.
- **XL**: more than 2 weeks.

**depends_on** names only the direct prerequisites for closing the gap.

| gap_id | goal_ids | repo | gap | evidence | size | depends_on | blocked_by | first_move |
|---|---|---|---|---|---|---|---|---|
| GAP-001 | A1.1, HARN.1, G1, G7 | single-cell-harness | The harness cannot run any of the four tools: it has no adapter or stage driver, its kernel loads only plugin.yml directories and refuses the pbs executor, so the integrated family exists only as hand-written per-stage project job scripts. | sch/kernel.py:97-117 (search paths; a plugin is a dir with plugin.yml) [v]; sch/services/executor.py:147-148 pbs refused 'not shipped before ROADMAP Phase 9' [v]; ROADMAP.md:326-331 'Phases 3 and 5-9 are not built' [v]; plugins/ holds only gate, probe, table and toy single-cell plugins [v] | XL | GAP-002 | none | Build ROADMAP Phase 3's qc@scqc adapter: a harness plugin that calls scQC's real CLI inside one PBS job and adopts scQC's STATUS/SEALED as the stage record. Success: SAMBO stage 1 through the adapter reproduces 6e3b4b97cb38 IDENTICAL (kept barcodes and the six criterion columns) under a pre-declared PBS job. |
| GAP-002 | A1.1, A3.2, HARN.1 | all five | No single design sheet travels through the stages: the stage-2 joint object lost age and diet, stage 3 rebuilt design.csv with awk, and stage 4's design.csv and controls were written by hand, so every stage boundary needs project glue. | S 03_integrate/jobs/21_scintegrate_integrate.pbs:113-127 (awk) and 02_annotate/RL:1750-1752; S 04_profile/RL:23; scprofile_cellchat.pbs:180-214 (hand-declared --control); scProfile in.json carries no controls (manifest.py:78-84) | L | - | none | Declare one design sheet (sample to factors, controls, covariates, assay, species) through the profile_context axes ADR-0027 added, and make scAnno carry its columns into the joint object. Success: SAMBO's stage-3 job runs with the awk block deleted and reproduces 713d918's run within harmony's named spread. |
| GAP-003 | A7.1, HARN.2, G7 | single-cell-harness | No skill teaches a cold agent to run a cohort through the four tools (assemble the stage jobs, submit, recover, audit, record); the three skills cover the kernel's toy mount loop, extending the family, and plugin conversion. | skills/harness-agent/SKILL.md:24-34 (plan/mount/ask loop on the kernel) and :92-96 (PBS left to the site skill) [v]; skills/harness-developer, skills/plugin-maker [v] | M | GAP-001 | none | Write a cohort-run skill from the stage job templates and rule 1's reproduction procedure. Success: a cold agent given only the skill and SAMBO's stage-1 record authors a reproduction job whose argv equals PBS 720930's (argv diff), without submitting. |
| GAP-004 | A2.3, G2 | single-cell-harness + records | No cold reproduction of a sealed stage run from its record has ever been attempted; blind 0004 and the ADR-0026 replay were cold agents driving scProfile's writing loop and maker edits, not reproductions. | records audit: none in SAMBO or C46; docs/blind/0004-writing.md:1-8 [v]; docs/adr/0026-the-maker-under-random-edits.md:112-113 [v] | M | GAP-003, GAP-010 | none | Run A2.3 on SAMBO stage 1: a cold agent with only the stage RUNLOG and scQC's README reproduces 6e3b4b97cb38. Success: COMPARISON IDENTICAL, with wall clock and tokens recorded. |
| GAP-005 | A4.4, PROF.1, HARN.2 | scProfile + single-cell-harness | No plugin catalogue exists for an agent: scProfile has no list or catalogue command, and the harness's sch cannot see scProfile plugins at all. | scProfile cli.py add_parser list (doctor ... standard; no list/catalogue) [v]; sch/kernel.py:97-117 (plugin.yml dirs only) [v]; doctor prints when_to_use (cli.py:74-75); plan --report needs an h5ad (plan_report.py:46-54) | M | - | none | Add 'scprofile catalogue --json' generated from the PLUGIN dicts (question answered, needs, provides, cannot_show, cite, pin) and list it from sch through scProfile's DEVPOINTS. Success: a cold agent picks the right plugin for at least 4 of 5 questions written beforehand, with no Read of kernels/ in its tool log. |
| GAP-006 | PROF.1, A4.1, A4.4 | single-cell-harness + scProfile | The Universal Plugin Format is two incompatible formats, the harness's plugin.yml directory contract and scProfile's one-file PLUGIN dict, and ROADMAP Phase 6 (dissolve scProfile) needs an ADR naming what is given up. | PLUGIN_FORMAT.md; docs/AUTHORING.md:15 (sch plugin new, plugin.yml); scProfile kernels.py:706-716 (one-file discovery); ROADMAP.md:217-238 [v] | L | - | PI decision: which format is the standard (an ADR amending ADR-0004) | Write the ADR with a field-by-field mapping, tested by a translator that round-trips cellchat's declaration. Success: sch plugin validate passes the translated cellchat and scProfile's declare.check passes the round-tripped one. |
| GAP-007 | A3.1, G3 | single-cell-harness | The fixture's value axes stop short of ADR-0027's decision: only control order and mito/ribo spelling vary; assay, species identifiers and the raw-droplet delivery layout (empties, MEX, 10x h5) were never built. | docs/adr/0027-the-second-cohort.md:89-93 (decision) vs :145 (step 1 built control and spelling only) [v]; sch/dev/fixture.py | M | - | none | Add the delivery-layout axis (a raw matrix with empties, as MEX and 10x h5) and an assay axis. Success: scQC cf0b750 fails sch dev check on the scRNA shape (CellBender scheduled for cells) and 0e6a5f6 passes. |
| GAP-008 | A3.1, A3.3 | single-cell-harness | The leak guard is narrower than rule 1: the site word list holds sample names, site strings and counts but no factor levels or queue names, and a hard-coded queue is only a WARN, so factor levels in the tools' tests and queues in their job scripts pass sch conform. | sch conform on the four clones with both word lists: S1 ok for scQC, scAnno, scIntegrate; S5 WARN for scAnno jobs/TEMPLATE.pbs and five scProfile setup/*.pbs [v]; word list has no aged/young/chow/HFD/WT/Mut/workq [v]; scQC tests/test_figure_collection.py:176-178, test_parameters_are_not_factors.py:27-29; scAnno tests/test_embed.py:87-88; scIntegrate tests/test_methods_settings.py:53 | S | - | none | Generate the term list from each cohort's own design sheet (sample ids and factor levels as whole words) plus the site's queue names, and scan all five repositories. Success: S1 lists the test fixtures above, then 0 hits after their fixes. |
| GAP-009 | A2.2, G2 | single-cell-harness | The harness README presents unbuilt behaviour and stale facts as current. | README.md:39-70 shows 'sch diff main no-qc --on composition' (sch diff is not a command) and a sch stack transcript with qc@scqc etc. that no adapter provides [v]; README.md:221 '144 tests' (606 run, 14 skipped) [v]; README.md:11-21 'all four pass with no failing row' (today scProfile fails S1; three tools fail G1 with no hook file) and 'most recently PBS 707628, every tier green' (PBS 719917 had failures, ADR-0027:153-161) [v] | S | - | none | Mark the transcripts as the Phase 7 target (or move them to VISION.md) and correct the three facts. Success: a seeded 10-claim sample of README finds no false claim. |
| GAP-010 | A2.1, A2.3, G2 | records (harness ADR-0027, SAMBO, C46) | The newest results exist only on the cluster: PBS 720930 (scQC 0e6a5f6 against SAMBO's promoted stage 1: IDENTICAL) and 720932 (C46 stage 1 as single cells, apply mode, sealed exit 0) are missing from ADR-0027's step record and both RUNLOGs, and 720931's selftest cannot be located. | cluster SAMBO runs/scqc/01_qc/20261002T144323Z__scqc-0e6a5f6__01_qc__robust/COMPARISON.txt 'VERDICT: IDENTICAL', SEALED.txt jobid=720930 [v]; C46 runs/scqc/01_qc/20261002T144323Z__scqc-0e6a5f6__01_qc__applycells/SEALED.txt exit=0 jobid=720932 [v]; no run dir carries 720931 [v]; S 01_qc/RL:2800-2814 and C 01_qc/RL:112 say 'submitted' only | S | - | none | Append dated rows to ADR-0027, SAMBO 01_qc/RUNLOG and C46 01_qc/RUNLOG quoting both seals and the COMPARISON verdict; locate 720931's log or record it as lost. Success: every job id named in ADR-0027 has an outcome row. |
| GAP-011 | A3.3, rule 2 | single-cell-harness | No check catches an axis that is required but never read: S13 finds only literal defaults, so scQC main passes S13 while its ambient step ignores the assay it is handed, and scAnno passes while --assay changes no rule. | sch conform S13 ok on scQC cf0b750 and scAnno c16c56a [v]; scQC engine/graph.py:121 passes 'assay', steps._ambient never reads it [v]; scAnno cli.py:80,207,619,1223 store assay in a context only [v] | M | - | none | Add a sch conform row that follows each declared axis from the CLI to a branch or keyed lookup (syntax tree). Success: it fails scQC cf0b750 and scAnno c16c56a and passes scQC 0e6a5f6. |
| GAP-012 | HARN.3, A5.2, G5 | single-cell-harness + scProfile | No co-scientist exists: nothing proposes hypotheses, states a falsifying test, or turns a follow-up into a planner request. | scProfile brief.py:319-321 (guidance text only); feedback.py diagnoses the tooling (cli.py:653); slide 9 'AI Scientist (Agent) (TBD)' | XL | GAP-005, GAP-048, GAP-049 | none | Define a hypothesis record (claim, cited figure/table ids, a falsifying test written as a plan request) produced from one sealed run's claims ledger, and 'plan --from-hypothesis' as a dry run. Success: one follow-up from a SAMBO cellchat claim is planned and run as a sealed job. |
| GAP-013 | HARN.4, A6.1, G6 | single-cell-harness | No user interface exists in any repository. | no web UI code in the five repositories [v]; slide 4 'Harness UI (TBD)' | XL | GAP-001 | none | A thin read-only web view over one sealed run's record (plan, decisions, stage status, reports), built from the report's words. Success: a user opens SAMBO's stage reports and record from the page with no terminal. |
| GAP-014 | A6.2, PLAT.2, PLAT.3 | single-cell-harness (+ platform, see pass 0001b) | The family's final object has never been opened in Studio; the only hand-off on record is the stage-2 joint object, and nothing shows Studio displaying the run that produced an object. | S 02_annotate/DE:949 (PI, 2026-08-19: the joint h5ad works in Lab and Studio); scrnaseq-lab README.md:3-16 (browser converter, two questions) [v]; no record for cohort_integrated.h5ad or stage-4 objects | S | - | none | Convert SAMBO's promoted stage-3 cohort_integrated.h5ad through Lab and open it in Studio. Success: cell type, condition and the default embedding show for all cells, recorded with the bundle digest and run key. |
| GAP-015 | A3.4, G3 | scQC, scAnno, scIntegrate | Only scProfile records peak memory; scQC records task seconds without memory, scAnno only start and finish stamps, scIntegrate nothing. | scProfile _entry.py:762-787 (peak_rss_gb, wall_s, n_cells); scQC engine/pipeline.py:439,478-480; scAnno status.py:114,146; scIntegrate (no timing code) | M | - | none | Add measured {wall_s, peak_rss_gb, n_cells} per step to docs/STATUS_CONTRACT.md with a conform row; implement in scIntegrate first (its stage took 3 h 42 m). Success: SAMBO stage-3 STATUS.json carries all three numbers. |
| GAP-016 | A3.4, G3 | all five + cohorts | No cohort of 1,000,000 cells or more has been chosen or run; the largest run is SAMBO's stage 1 (100,713 delivered of 305,425). | S 01_qc/RL:2633 (a record quoting the sealed run); GOALS.md A3.4 [v]; C46 tool-reported Cell Ranger calls 14,007 / 15,619 / 17,184 / 12,891 (thresholds_per_sample.csv of PBS 720932) [v] | L | GAP-001, GAP-015 | data: no public >=1M-cell cohort chosen yet (the pre-decider can choose) | Write the selection rule (public, Cell Ranger outputs, >=1M cells, one assay) and measure stage-by-stage peak memory on a 10% subsample in sealed runs. Success: an extrapolated per-stage memory table that fits the standard queues, or names the stage that does not. |
| GAP-017 | A3.3, QC.1, rule 2 | scQC | On main scQC schedules CellBender for every library not supplied, single cells included, and applies nucleus-calibrated count bounds to every assay; the fix (single-cell-route 0e6a5f6) reproduced SAMBO IDENTICAL and ran C46, but is unmerged, and ~/tools/scQC is checked out on that branch. | engine/graph.py:104-127 (fn=steps._ambient, gpu=True, no assay test) [v]; modules/05_quality/quality.py:57,62; branch modules/01_ambient/ambient.py:59 DENOISE = {snrna: True, scrna: False} and graph.py:178 _ambient_none [v]; PBS 720930 IDENTICAL, 720932 sealed [v]; cluster ~/tools/scQC branch=single-cell-route [v] | S | GAP-010 | the merge gate: verifier PASS and the selftest outcome (720931 unlocated); no PI ask under the standing yes | Run the verifier on 0e6a5f6 (suite, leak guard S1/S13 ok [v], fixture through the CLI, 720930), rerun the cluster selftest if 720931 stays lost, then fast-forward main and switch ~/tools/scQC to main. Success: all five HEAD.txt equal main and C46 reruns record a main commit. |
| GAP-018 | A1.3, G1 | scQC | The installer leaves the denoiser's torch and the R doublet stack unpinned, which broke the first C46 run; the drafted pin (finding Q9) was never pushed. | setup/install_env.sh:313-316 (cellbender==0.3.2, torch unnamed) [v]; install_rdoublet.sh:94-95 (scDblFinder unpinned); PBS 720477 FAILED in CellBender under torch 2.14.1 (ADR-0027:182) [v] | S | - | none | Push the Q9 branch (torch 2.5.1, numpy 1.26.4, refuse others) and pin bioconductor-scdblfinder. Success: a fresh-prefix build on PBS, scqc selftest green, and one SAMBO nucleus library through CellBender inside scQC. |
| GAP-019 | QC.2 | scQC | Nothing writes to the results tree's figures/: the 18 figures exist only as PNGs embedded in the HTML, so slide 5's 'nothing writes one yet' is still true. | report/build.py:1537-1545 (data:image/png); engine/pipeline.py:170 creates figures/; C46 run 720932 results/138cd412ff4a/figures holds 0 files [v] | S | - | none | Write each figure as a file into figures/ and list it in STATUS products. Success: the synthetic-cohort test asserts one file per figure id, and the SAMBO reproduction stays IDENTICAL. |
| GAP-020 | QC.2, G7 | scQC | The report does not fully show who decided each threshold: decided_by and the verbatim approval reach report.json only, declared-informed floors are labelled DERIVED, and parameters with CLI defaults are reported as having no default. | report/build.py:2377-2383 and :795-796; engine/pipeline.py:608 vs modules/05_quality/quality.py:206 (provenance dropped at steps.py:661-663); pipeline.py:580 vs scqc_cli.py:812,840,851 | S | - | none | Carry class, decided_by and the verbatim approval into the HTML table and print the real default where one exists. Success: a test renders a run with one DECLARED, one DERIVED and one CLI-default value and checks all three rows. |
| GAP-021 | G2, A2.1, QC.1 | scQC | The run record cannot prove what a run used: STATUS inputs is empty, wrapped_versions is unfilled, decisions.yml is not in the run key, and the seal checks only the two report files. | STATUS.json 'inputs': [] on PBS 720932 [v]; status.py:69,72; engine/pipeline.py:114-115; scqc_cli.py:702 | M | - | none | Fill STATUS inputs with sha256 of the samplesheet, matrices and decisions.yml, and put decisions.yml in the key. Success: two apply runs differing only in decisions.yml get different digests, and the SAMBO reproduction stays IDENTICAL. |
| GAP-022 | A2.2 | scQC | Several documented behaviours are false on main. | README.md:84 (single-cell ambient optional; it is scheduled for every assay); :150-152 (decisions not keyed); :158 (who-set not in ledger or object); :163 (refuse_if_stale has no caller, build.py:2631); QUICKSTART.md:79 (validate takes no positional); USER_GUIDE.md:61,78; setup/install_env.sh:390 (--env-root does not exist) | S | GAP-017 | unmerged branch (fix the docs at the merged commit) | Correct each line against the merged code. Success: a seeded 10-claim sample of scQC's docs finds none false. |
| GAP-023 | A3.1, rule 1 | scQC | The fixture tier runs describe only, so no value axis can reach the pipeline (ADR-0027 prediction 3 was 'not measured as worded'); the declared baseline_dir does not exist. | DEVPOINTS.yaml:12-21 [v]; docs/adr/0027-the-second-cohort.md:197 [v] | M | GAP-007 | none | Point the fixture at 'scqc run --mode evidence' on a two-library synthetic project built by tests/test_conditions.py's builder. Success: sch dev check runs scQC's pipeline on both shapes, and re-planting Q1 fails it. |
| GAP-024 | A3.3, QC.1 | scQC | The single-cell route leaves audit findings open: steps 6 and 7 resolve floors through different functions when decisions.yml overrides them, captions still say nucleus, and cells get no ambient estimate or library metrics. | docs/adr/0027-the-second-cohort.md:189 'Open from the audit' [v] | S | GAP-017 | unmerged branch | A test with a decisions.yml override asserting steps 6 and 7 apply the same floor. Success: it fails on 0e6a5f6 and passes after the fix. |
| GAP-025 | A3.1, rule 1 | scQC | A first-cohort default survives as a fallback: the shipped registry's only row is the first cohort's mouse reference, read when a project supplies none. | registry.tsv:2; engine/steps.py:143-148; scqc_cli.py:796 | S | - | none | Refuse ingest when no project registry is supplied. Success: wiring section N refuses without --registry, and the SAMBO reproduction stays IDENTICAL with its registry passed explicitly. |
| GAP-026 | QC.1, A3.3 | scQC | For single cells no count floor or mito ceiling is derived from the data: floors are declared (PI decisions D8/D9), the valley procedure does not apply to raw whole-cell matrices, and on C46 all four mito ceilings were set by the declared lower bound. | C 01_qc/DE D8, D9; ADR-0027:186 (PBS 720698: valley 2.5 UMI, bimodal False in all eight); 720932 tables/thresholds_per_sample.csv mito_ceiling_pct 10.0 with mito_clamped=lower for all four libraries (tool-reported) [v] | M | GAP-017 | PI decision: whether single cells should get data-derived thresholds beyond the declared bounds | A written proposal of a called-cell procedure (per-library MAD over Cell Ranger-called cells), run in evidence mode on C46 beside the declared bounds. Success: the PI's ruling recorded in C46 DECISIONS. |
| GAP-027 | ANNO.1, A3.1 | scAnno | There is no absolute fit floor at the root, so 'none of this tree' cannot be returned, and --resolve and FORCE push calls below the bar (finding N1, open). | scanno/classify.py:104-135 (relative gap only; 'TRUNCATE, do not abstain') [v]; force.py:285-405, 426-525; KNOWN_ISSUES.md:6-19 | M | - | none | Add an absolute root-fit floor with a 'none of this tree' outcome. Success: a heart tree on a synthetic non-heart cohort returns it for every cluster, and the rescue reproduction (720434's base) stays IDENTICAL. |
| GAP-028 | ANNO.1, A1.1, A3.1 | scAnno | scAnno cannot build its own inputs for a new tissue or species: the documented 'scanno build-markers' does not exist, the corpus has no version or digest, and no command derives a tree, so SAMBO's tree and corpus were project-made and C46 has neither. | scanno/corpus.py:5-8 documents 'scanno build-markers'; 0 occurrences in cli.py [v]; corpus.py:30-34 (any SQLite with an assertion table); report.py:177 (path only); --tree required (cli.py:2135); S stages/02_annotate/mouse_heart_tree.json and results/02_annotate_corpus/cellmarker3_mouse.db (02/RL:127-188) | L | - | data: a CellMarker 3.0 human release file (access and licence to check); the PI's rule keeps each tree project content, so the tool builds it and the project keeps it | Add 'scanno corpus build' from a CellMarker 3.0 release file (species, tissue) writing version and sha256 into the store. Success: rebuilding SAMBO's mouse corpus reproduces cellmarker3_mouse.db's assertion table row for row. |
| GAP-029 | A3.3, rule 2 | scAnno | --assay is required but changes no rule, a single-nucleus store is accepted for a single-cell run, and the report says nuclei for any assay. | scanno/cli.py:80,207,619,1223 (assay only stored) [v]; report.py:318,369; agent.py:333 | S | GAP-011 | none | Refuse a store whose context assay differs from the run's, word the report per assay, and document which rules are assay-independent. Success: tests for the refusal and both wordings, with the rescue reproduction IDENTICAL. |
| GAP-030 | ANNO.2 | scAnno | 'Ultra-fast, consistent' is unmeasured: no test runs annotate twice for identical labels, no step time is recorded, and VERSION 0.12.0 spans two behaviour changes with no tags. | cli.py:2094 (seed 0); no timing code in scanno/ (status.py:114,146 stamps only); VERSION set in 1126e5d, unchanged through 7502c88 and c16c56a | S | GAP-015 | none | A test that runs annotate twice on the synthetic cohort and compares every label column, plus per-step wall time in STATUS and a release tag per behaviour change. Success: the test is green and SAMBO stage 2's per-step time is recorded. |
| GAP-031 | A2.2 | scAnno | README examples fail on main and several documented behaviours are false. | README.md:44-46,147-149,168-171 and QUICKSTART.md:69-75 omit the required --assay (cli.py:2186); README.md:42; :197 and :209 (classify.py:144); QUICKSTART.md:58-60 (corpus.py:142) and :102 (cli.py:1006-1007); KNOWN_ISSUES 'steps 0,1,3 not built' is stale | S | - | none | Fix each line and run the README examples as a test on the synthetic cohort. Success: the examples run green. |
| GAP-032 | A3.1, A1.3 | scAnno | The fixture never runs annotation (cluster only), the selftest runs only the adversarial file, and the job template hard-codes a queue and reads $TOOL before it is set. | DEVPOINTS.yaml fixture 'cluster --resolutions 0.5 --seed 0'; cli.py:28-34; jobs/TEMPLATE.pbs:3,17,42,52 (S5 WARN [v]) | M | GAP-028 | none | Point the fixture at annotate with a tiny synthetic tree and corpus shipped as test data, and make selftest run the whole suite. Success: sch dev check exercises annotate on both shapes. |
| GAP-033 | A2.1, G2 | scAnno + SAMBO records | SAMBO stage 2's promoted run (bd45f5d, PBS 664864) has never been reproduced and 664864 has no RUNLOG entry; the three IDENTICAL reproductions are of a non-promoted rescue run. | S results/02_annotate/PROMOTED.md:5-9; 02_annotate/RL:2064 ('Not the promoted run ... changed labels on purpose'); 706249, 719992, 720434 | M | - | PI decision: reproduce at bd45f5d, or promote a run of the current scAnno as stage 2 | Recommend a pre-declared reproduction at bd45f5d, then a PI promotion of the current route. Success: COMPARISON IDENTICAL on 18 label/cluster columns x 10 libraries. |
| GAP-034 | A3.3, INT.1 | scIntegrate | scIntegrate takes no assay or species and prints a first-cohort design sentence ('one library per animal') on every cohort; its last commit (2026-09-08) predates the ADR-0027 sweep. | scintegrate/cli.py:739-742 [v]; no assay or species reference in scintegrate/; main 722bc79 dated 2026-09-08 [v] | S | GAP-011 | none | Require --assay and --species (checked against the object with the harness's axes rule) and word the constraint from the design. Success: a human scRNA synthetic test, and the SAMBO stage-3 reproduction within harmony's named spread. |
| GAP-035 | INT.1, A2.1 | scIntegrate | The default method is chosen even when totals rest on different metric counts, and harmony's measured node-to-node spread is not reported beside the ranking (KNOWN_ISSUES, open). | scintegrate/benchmark.py:274,333; cli.py:579 (NOTE only); S 03_integrate/RL:408-435 (node-to-node 0.214; total about 0.013 run to run) | M | - | none | Refuse or flag a non-comparable winner and print each method's measured spread beside its total. Success: report.json carries a spread per method, and a test with a missing metric shows the refusal. |
| GAP-036 | A1.3, A2.2 | scIntegrate | The environment and its claims are weaker than stated: --add-to installs scib, scvi-tools, bbknn and harmonypy unpinned, the self-test is an import probe, the scib import is unguarded although the README says the run proceeds without scib, and STATUS wrapped versions are always {}. | setup/install_env.sh:103,144; doctor; scintegrate/benchmark.py:175 [v]; README.md:26; status.py:91,124 | M | - | none | Pin --add-to to the lock, guard the import as the README says (or change the README), and fill wrapped versions. Success: a fresh-prefix PBS build plus a functional selftest on the synthetic object. |
| GAP-037 | A2.2 | scIntegrate | Further false or dead statements remain in code and tests. | cli.py:855 (score docstring) and :868 (BBKNN dropped); cli.py:1162 vs metrics.py:131 (veto vs classify); DEVPOINTS names missing tests/test_methods.py; tests/test_cli_path.py:77 ends 'or True'; benchmark.py:169 cluster_seed unused | S | - | none | Fix each. Success: the 'or True' test fails when its condition is false, and DEVPOINTS names an existing test. |
| GAP-038 | A1.3, PROF.3 | scProfile | The shared kernel environment cannot be built from main: requirements are ranges, nothing records resolved versions, and the environment's name hashes the ranges. | PBS 720377 resolution-too-deep (ADR-0027:179) [v]; scprofile/resolve.py:215-219 [v]; ranges at kernels/de.py:185, abundance.py:178, cellcycle.py:196, decoupler.py:152, pseudotime.py:164, liana.py:244 [v] | M | - | none for a host-level lock; pins inside the held-out kernels would need the PI | A host-level lock per environment group (resolved versions of the interpreter that ran PBS 720487) consumed by scprofile install, with no kernel edit. Success: a fresh-prefix PBS build of the shared group and scprofile selftest green for all seven members. |
| GAP-039 | A3.2, PROF.2 | scProfile | On main DE contrasts the alphabetically last level against the first and scCODA uses an alphabetical baseline, against the run's declared control; the fix (48aaeba) missed its own p-value tolerance and is unmerged. | kernels/de.py:1392-1404 [v]; abundance.py:1516-1525 [v]; S 04_profile/RL:767 (earlier DE ran young vs aged and chow vs HFD); PBS 720548 vs 720487 DIFFERENT (ADR-0027:181) [v] | S | GAP-038 | PI decisions: SAMBO DE's sign convention (RULES tier II), and the 2026-09-10 held-out rule (48aaeba edits de.py and abundance.py) | Re-grade 48aaeba with a tolerance set from the fit's own measured precision, declared before the run, and add --control to plan (the branch leaves plan on hints, INFERRED). Success: the identities hold within the declared tolerance, and plan and run name the same control. |
| GAP-040 | A3.2 | scProfile | Covariates are neither modelled nor refused by name, abundance silently drops the planned interaction, DE's caveat denies an interaction it ran, and plan and run disagree at n < 3 and on (1, 2) arms. | scprofile/inputs.py:756-769, 921; kernels/abundance.py:1516-1525 [v]; de.py:1700-1711; cli.py:1862-1866 [v] vs de.py:134 [v]; planner.py:401-404 vs de.py:1243-1248 | M | GAP-039 | PI decision: the held-out rule covers de.py and abundance.py (the host side is free) | Host side first: the planner refuses a covariate by name and plan and run share one per-level minimum. Success: tests for one factor n=2, a 2x2 with interaction and a covariate, each ending in RUN or a named refusal. |
| GAP-041 | PROF.3, A1.2, A1.1 | scProfile | Differential abundance has never run on any cohort, and the round rule keeps it broken. | S 04_profile/RL:189, 313, 817 (mudata, statsmodels, plugin failure in 720487); scProfile DEVPOINTS.yaml rule 2 held_out ('STAY BROKEN') [v] | M | GAP-038 | PI decision: the 2026-09-10 held-out rule (not in autodev/RULES.md) against GOALS A1.1 | Once the PI rules, convert abundance through the maker. Success: a sealed SAMBO abundance run with a pre-declared prediction. |
| GAP-042 | PROF.3, A1.2 | scProfile | No plugin covers pathways: decoupler is TF activity only, while the README claims pathway activity. | kernels/decoupler.py:209-212 ('get_progeny: pathway activity ... would be a second plugin') [v]; README.md:66-67, 105 | L | GAP-038 | none (a new plugin is not one of the held-out eight) | Make a pathway plugin through the maker (PROGENy through decoupler, or promote the gseapy blind conversion in tests/smoke/plugins/enrichment.py). Success: the maker's build stages green and a sealed SAMBO run. |
| GAP-043 | PROF.3, A1.1 | scProfile | Six of nine plugins have never run on a cohort (cellcycle, decoupler, liana, pseudotime/CellRank, velocity, SCENIC), although slide 4 lists their families as supported. | records audit: S 04_profile/RL:127 (members of the shared env only), :460 (SCENIC references 829 MB, no run); no velocity or CellRank run on record | L | GAP-038 | data: velocity needs spliced counts (C46 has Cell Ranger outs only, no BAM, ADR-0027:18) and SCENIC needs cisTarget files; the held-out rule for any kernel repair | After the environment lock, one sealed SAMBO run of cellcycle and decoupler (no extra references) as their first references. Success: sealed, report pages written, prediction graded. |
| GAP-044 | A4.1, PROF.1 | scProfile | Only cellchat is in the maker's layout, and it was migrated by hand; the other eight carry plots_unreviewed and the old figure form. | docs/blind/0003-deseq2.md:8 (hand-pasted worksheets); kernels/cellchat.draw.R:3 (generated); kernels/abundance.py:47 plots_unreviewed; scProfile DEVPOINTS.yaml:357,402 | XL | GAP-038, GAP-045 | PI decision: spend the held-out set now (rule of 2026-09-10) | Convert cellcycle (the smallest) through the maker by a cold agent. Success: every build stage of sch dev check --point kernel --name cellcycle green, sch dev rules records the spend, and a sealed SAMBO run. |
| GAP-045 | A4.3 | scProfile | Provenance is free text: no DOI field, exact upstream pins in 3 of 9 plugins, the maker's template seeds a range, and the cite and licence checks are skipped for one-file plugins. | wraps.cite in all nine (e.g. de.py:39-40), no DOI anywhere; exact pins only velocity, scenic, cellchat; scprofile/onefile.py:33,74; validate.py:72-110 returns before :239-241; abundance cites pertpy as 'Buttner et al., 2024' (INFERRED misattribution; pertpy's paper is Heumos et al.) | M | - | none (required keys in DEVPOINTS do not edit the eight) | Make wraps.doi and an exact wraps.version required keys of the kernel point and the template, so the eight show as owing. Success: sch dev check lists eight owing and cellchat complete. |
| GAP-046 | A4.2, PROF.1, G4 | scProfile + single-cell-harness | The maker has never converted a tool drawn from the catalogue: there is no draw rule, no published example reproduced, no success rate or time per conversion, and the maker reads code, never the paper. | docs/blind/0002-gseapy.md (build 9/9; test 6/6 on the fixture, PBS 710976) and 0003-deseq2.md (build 8/8, workstation), neither merged (tests/smoke/plugins/); extractors python_package, r_namespace, shared_env (INFERRED: no paper intake) | XL | GAP-005, GAP-045 | none (bar now 4 of 5); the draw becomes the maker's new held-out set once the eight are spent | Commit a draw rule before drawing (seeded sample of scRNA-tools entries with an installable package and a published example dataset, excluding the nine), then one cold conversion end to end. Success: the plugin reproduces the tool's own example within the pre-declared tolerance, with time and tokens recorded. |
| GAP-047 | PROF.4, A5.1 | scProfile | The report generator is cellchat-only in practice: between-arm panels need unit_network (cellchat, liana), only cellchat has compare(), the only writing template is cell-cell communication, and DE and abundance get no composed section. | kernels/cellchat.py:542, 5337, 493; liana.py:282; templates/ holds one file; scprofile/compose.py:62 | L | GAP-039 | none | Give DE a declared per-contrast table panel and a composed section, by declaration rather than plugin code. Success: a SAMBO DE report with one section per contrast in slide 15's labelling. |
| GAP-048 | A5.1 | scProfile | The review loop does not remove what it withdraws: the rendered section prints the author's body verbatim, tables cannot be cited, and reviewer independence is a different name string. | scprofile/paper.py:755-802 (body printed after banners for stale or unreviewed claims only) [v]; :976; :221-227 | M | - | none | Render strikes or drops any sentence bound to a withdrawn claim, and allow table citations. Success: a test where a withdrawn claim's sentence is absent from the rendered page. |
| GAP-049 | PROF.2 | scProfile | The pipeline is not self-assembled: the user names the plugins, the scheduler only orders them (one edge), there is no reproducibility-suite step, and the runner is local threads although EXECUTION.md documents PBS and SLURM executors. | scprofile/cli.py:245 (want = the user's list) [v]; kernels.py:1509-1512 ('a single edge between them') [v]; cli.py:939-964; docs/EXECUTION.md:259-271 | L | GAP-005 | none | A 'plan --question' step that selects plugins from the design and a stated question through the catalogue, printing why each was chosen or skipped. Success: on SAMBO's design it selects DE, abundance, cellchat and cellcycle and refuses velocity by name. |
| GAP-050 | A3.3, rule 2 | scProfile | The assay changes captions only; cellchat's nucleus-specific cannot_show, the 'animals' wording and nucleus-fitted memory models apply to every cohort. | scprofile/inputs.py:274-276 ('changes the CAVEATS, never the code path') [v]; kernels/cellchat.py:1349-1351; units.py:117; evidence.py:65; de.py:199, cellchat.py:435 | M | - | none for cellchat and the host; the held-out rule for the other kernels | Make cellchat's cannot_show and the host's unit wording per assay through the maker's edit verbs. Success: a scRNA synthetic run prints no nucleus wording. |
| GAP-051 | A3.1, rule 1 | scProfile | main fails the leak guard (4 first-cohort hits); the fix rides on the unmerged 48aaeba with held-out edits, and more first-cohort wording sits outside the word list. | sch conform S1 FAIL: tests/test_figure_audit.py:330, tests/test_the_compare_launches_share_the_pool.py:6, tests/test_one_fact_many_phrasings.py:26, docs/ANATOMY_OF_A_RUN.md:7 [v]; tests/test_composed_section.py:100; ANATOMY:87; TEST_LOOP.md:376; .claude/skills/result-section/SKILL.md:314 | S | GAP-008 | none (a leak-only branch touches no kernel) | A leak-only branch with 48aaeba's four removals and the others. Success: S1 ok with both cohorts' generated word lists. |
| GAP-052 | A2.2 | scProfile | The README quickstart cannot run as written, and sampled doc claims are false or stale. | README.md:14-19 (no interpreter without --prefix: runner.py:118, cli.py:606-623); README.md:103, 151-155, 191-193, 212; RUN_PLAN.md:123-127; EXECUTION.md:28-34, 259-271; AGENT_CONTRACT.md:53; PAPER_TEST.md:48-52; BUILD_PLAN.md:3, 37-38; DESIGN.md:100-111 | M | GAP-038 | none | Make the quickstart a test that runs on the synthetic object with --prefix, then correct the rest. Success: a seeded 10-claim sample finds none false. |
| GAP-053 | A3.1, A3.3 | scProfile | A declared --organism is taken on trust: detection reads the first 5,000 var_names and ignores gene_ids, so a wrong species yields a plausible table (finding P3). | scprofile/inputs.py:218-221 [v]; ADR-0027:37 | S | - | none | Reuse the harness axes rule (Ensembl prefixes in any var column, decisive at 90%) to refuse a contradiction. Success: a test with human identifiers declared mouse refuses, naming both. |
| GAP-054 | A3.1 | scProfile | The fixture never reaches DE or abundance: the dev-suite job sets no SCH_DEV_PREFIX, and DEVPOINTS accepts 'are not ready in this installation' as the fixture's outcome. | harness jobs/dev_suite.pbs:202; scProfile DEVPOINTS.yaml:58-59; ADR-0026:299 | S | GAP-038 | none | Point the prefix at the locked environment and drop the accepted refusal. Success: sch dev check --point kernel --name de runs DE on both shapes, and the control-order axis fails f294c89. |
| GAP-055 | A2.1, PROF.4 | scProfile + SAMBO records | SAMBO stage 4 has no promoted run: about 35 cellchat runs and one DE run, none promoted; the one IDENTICAL reproduction (706253) is against a non-promoted run. | S 04_profile/RL:756 ('results/04_profile/ still does not exist'); :722, 746 (706253 vs 703240); :815 (DE 720487) | M | GAP-039, GAP-047 | PI decision: promotion | Prepare a stage-4 promotion packet (cellchat and DE on one commit, with the sign convention stated). Success: a PROMOTED.md under results/04_profile by the PI's decision, then a pre-declared reproduction. |
| GAP-056 | A3.1, A1.1 | cohorts (BrainOrganoid_C46) | The second cohort stopped after stage 1 five weeks ago: its sealed apply run is not promoted, stages 2 to 4 have not started, and its design (what C46 is; what _1/_2 are) is undecided. | cluster C46 run 720932 SEALED, results/ empty, no run after 2026-10-03 [v]; C README.md:22-28 [v]; ADR-0027:130-131 | L | GAP-017, GAP-027, GAP-028 | PI decisions: promote C46 stage 1; the collaborator's facts on C46 and _1/_2 (stage 4 design only) | Put 720932's report, thresholds and removal ledger before the PI as a promotion packet. Success: PROMOTED.md for C46 stage 1, then stage 2 runs on the tool-built human corpus. |
| GAP-057 | A2.1 | scQC, scProfile + records | Outputs that vary between runs are named but not all measured: stage 1's UMAP coordinates and cellchat's network embedding have no spread on record. | S 01_qc/RL:2571; 04_profile/RL:750-753; kernels/cellchat.py:193, 1879 (unseeded) | S | - | none | Measure each spread from two existing sealed runs (no new compute) and record it beside the reproduction's prediction. Success: every output a reproduction may call DIFFERENT carries a number. |
| GAP-058 | A1.2, G1 | single-cell-harness | No document maps the ten typical steps to the components that perform them, and two steps have no component that has run (differential abundance never; pathways have no plugin). | slide 2; no mapping in README, ARCHITECTURE or GOALS [v]; scAnno cluster.py:136-141 performs normalisation and HVG [v] | S | GAP-041, GAP-042 | none | A checked table: step, tool command, the test that runs it, the sealed run that exercised it. Success: a unit test asserts every row names an existing command. |
| GAP-059 | A2.2, rule 1 | scQC, scAnno, scIntegrate | Three tools ship no commit gate, so rule 1(a) 'own suite passes, leak guard clean' is checked by habit only. | sch conform G1 on the clones: 'hook MISSING at setup/githooks/pre-commit' for scQC, scAnno, scIntegrate [v]; ADR-0027:161 | S | - | none | Copy the harness's pre-commit (suite plus conform, with site terms read from an untracked file). Success: G1 ok on a clone after git config core.hooksPath setup/githooks. |

---

## 5. Blockers: what stops development today

### Only the PI can remove these

| # | blocker | evidence | it blocks | recommendation |
|---|---|---|---|---|
| P1 | **The held-out rule collides with the goals.** On 2026-09-10 the PI ruled: the eight plugins other than CellChat "are HELD-OUT TEST RESOURCES — do not touch them at all"; "abundance's pertpy/statsmodels ImportError" and "de's unsatisfiable … pin" stay broken; "End-to-end SAMBO is CELLCHAT-ONLY". | scProfile `DEVPOINTS.yaml` `rules.held_out` ("STAY BROKEN"), enforced by `sch dev rules` [v]. The rule appears in the memory record of the 2026-09-10 round. It is **absent from `autodev/RULES.md`** [v], so the program would break a standing PI rule without knowing it. | A1.1 (DE and DA), A1.3 (pins inside the kernels), A3.2, A4.1. GAP-039, -040, -041, -044, and the merge of `48aaeba`, which edits `de.py` and `abundance.py` by hand. | Spend the eight now, through the maker, starting with DE and abundance, so that A4.1 and A1.1 move together. A4.2's catalogue draw then becomes the maker's new held-out set. Also record the rule, or its retirement, in `autodev/RULES.md` tier II. |
| P2 | **The sign convention of SAMBO's DE.** | `ADR-0027:181`: "the merge, and the sign convention it gives SAMBO's DE … are the PI's". RULES tier II: a PI decision carried inside a branch is not answered by the standing merge yes. | GAP-039, -055. | Adopt the declared controls (young, chow). Then the main-effect rows become simple effects at the other factor's control, as ADR-0027's prediction 2 states. |
| P3 | **Promotions.** C46 stage 1: PBS 720932 is sealed and `results/` is empty [v]. SAMBO stage 2: reproduce at `bd45f5d`, or promote a run of the current scAnno. SAMBO stage 4: nothing promoted. | LAYOUT: "A stage is not finished until PROMOTED.md exists". RULES tier II: what is promoted is the PI's. | GAP-033, -055, -056; A2.1. | Packets prepared by an agent, with their numbers. |
| P4 | **C46's design facts**: what C46 is (an H9 derivative, or another line), and what `_1` and `_2` are. | `C README.md:22-28` [v]; `ADR-0027:130-131`. | C46 stage 4 only. Stages 2 and 3 can run. | Ask the collaborator, through the PI. |
| P5 | **Which format is the standard plugin format.** | GAP-006. ROADMAP Phase 6 needs an ADR that amends ADR-0004. | A4.1 and A4.4 across the harness and scProfile. | An agent drafts the ADR with a mapping table; the PI chooses. |
| P6 | **Thresholds for single cells**: should they be derived from the data, beyond the declared bounds D8/D9? | GAP-026; on C46 the declared bound set all four mito ceilings [v]. | QC.1's "data-aware" for single cells. | Keep D8/D9 for now, and look at an evidence-mode proposal first. |

### An agent can remove these today

| # | blocker | evidence | who | it unblocks |
|---|---|---|---|---|
| A1 | **The scQC branch is unmerged.** Under the standing yes, a merge needs the gate (rule 1 a–d) plus a verifier PASS. On the branch, S1 and S13 are ok [v]; `tests/test_conditions.py` runs the real CLI; PBS 720930 is IDENTICAL [v]. **Outstanding:** the cluster selftest 720931 (no run directory carries it [v]) and the missing commit hook (G1). | §4 GAP-017 | coordinator and verifier | rule 2 on `main`; C46; GAP-022, -024, -026 |
| A2 | **scProfile's environment cannot be built from `main`** (finding P5). Lock the group at host level; no kernel is edited. | PBS 720377 | builder (PROF lane) | every stage-4 run; GAP-041 to -043, -052, -054 |
| A3 | **scQC's denoiser environment**: the torch pin (Q9) was drafted and never pushed. | PBS 720477 | builder (QC lane) | any nuclei cohort that runs CellBender inside scQC |
| A4 | **Records lag the cluster**: 720930, 720932 and 720931. | GAP-010 | coordinator | A1, A2.1, A2.3 |
| A5 | **`~/tools/scQC` is on the unmerged branch**, and the harness checkout is behind `main` [v]. | cluster `git -C ~/tools/*` | coordinator, after A1 | every new run's provenance |
| A6 | **The queue.** `generic` has a per-user limit, which Q11 hit when two jobs ran together (`ADR-0027:186`). On 2026-11-09, 10 jobs from this user were queued, with `curation_*` on workq in state W [v]. INFERRED: they count against the same per-user limits. The single running slot on gpu-h200 was held by another project (ADR-0027 as committed at `c564e33`, line 198). | qstat [v] | coordinator (schedule the work; rules 3 and 5) | throughput |
| A7 | **Data.** C46 stage 2 needs a human CellMarker 3.0 release (check access and licence). A3.4 needs a public cohort of 1M cells or more. SCENIC needs cisTarget files (public). | GAP-028, -016, -043 | builder, or the pre-decider | C46 stage 2, A3.4, SCENIC |
| A8 | **Data that only the vendor holds.** Velocity on C46 needs spliced counts. C46 arrived as "Cell Ranger outs only: no FASTQ, no BAM" (`ADR-0027:18`). | GAP-043 | **the PI or the vendor**, if velocity on C46 is wanted | velocity on C46 |
| A9 | **Idle lanes.** No run has been made on the cluster after 2026-10-03 [v]. That is a rule 5 finding, not a blocker. | cluster `find -newermt` | coordinator | — |

---

## 6. Leanness

**Merged branches that were never deleted (GitHub)** [v]:
- scQC: `ambient-run-path`, `assay-declared`, `interface`, `registry`.
- scAnno: `assay-required`, `interface`, `species-checked`.
- scIntegrate: `interface`.
- scProfile: `interface`.

**scProfile's mutant branches.** `attack-0026-A`, `-B`, `-C`, `-F` and `-G` are one mutant commit each, and
"not for main". They are kept only so the runs `rerun_0017` to `rerun_0021` can be re-checked-out. A tag per
commit would do the same job (INFERRED).

**scQC.**
- Dead code:
  - `adapters/apply_filter.py` (1,839 lines, no importer);
  - `report/build.py:2631` `refuse_if_stale` (no caller);
  - `requirements.hpc.lock.txt` (no script reads it);
  - `install_scdblfinder.sh`;
  - tools keys that nothing writes (`cellbender_bin`, `learning_rate`, `mito_derivation_max`, `celescope_bin`).
- Duplicated machinery:
  - two CellBender recipes, Python 3.10 in `install_env.sh` and 3.9 in `install_cs_cb.sh`;
  - two design-discovery functions (`scqc_cli.py:136`, `engine/steps.py:100`);
  - two removal implementations.
- Stale: on the branch, `README.md:88` still says apply mode is not built for cells.

**scAnno.**
- `missing_nodes()` is called only by a test.
- `cli.py:3-5` says "no report".
- `emit.py:308` cites a removed `resolution.consensus`.
- `store.py:47` cites a missing test.
- `KNOWN_ISSUES.md` says "steps 0,1,3 not built".

**scIntegrate.**
- `benchmark.py:169` `cluster_seed` is unused.
- `tests/test_cli_path.py:77` ends in `or True`.
- DEVPOINTS names a missing `tests/test_methods.py`.

**scProfile.**
- Dead code:
  - the directory-shaped `Kernel` class and `validate.py:112-246`;
  - the `figure_axis`/`figure_position` readers, which no plugin declares;
  - the unused `progeny` reference.
- Stale docs:
  - `BUILD_PLAN.md`, which says "COMPLETE" and describes the old directory shape;
  - `DESIGN.md:100-111`;
  - `DEVLOG.md`, which ends 2026-08-29;
  - `ROADMAP.md:41`;
  - `docs/REFERENCES.md:157`;
  - `docs/PLUGIN_DESIGN.md:331`;
  - `UPSTREAM.md`;
  - `setup/install_kernel.pbs:39`, which points at a `lock.yml` that does not exist.
- Three leak guards: `tests/test_portability.py`, conform S1, and the ladder's `t5_leak`.
- Three fixtures: `tests/make_fixture.py`, `Context.fixture`, and `sch/dev/fixture.py`.
- Two scaffolders: `scprofile/scaffold.py` with `onefile.py`, and `sch/dev/scaffold.py`.
- Its two figure skills exist byte for byte in both `.claude/skills` and `~/.claude/skills`.

**Harness.**
- `jobs/rerun_0006.pbs` to `rerun_0024.pbs` are 19 per-run scripts from ADR-0026; 14 of them are named by no file
  under `docs/`, `README.md` or `ROADMAP.md` [v]. Retire those 14, after checking ADR-0026's run table, and
  keep the five that a record cites.
- `spike/phase0/` (Phase 0's spike).
- `sch conform . --terms <both lists>` now fails S1 on `GOALS.md` and `autodev/` (12 hits) [v]. The commit
  hook runs conform without `--terms`, so nothing catches it. Either keep cohort names out of those two
  files, or give the guard a records exemption as the rule intends.
- README (GAP-009).

**Records.**
- `S docs/SUPERSEDED.md` is itself out of date.
- The local `S results/` mirror is stale (its `results/01_qc/README.md` describes the 109,140 generation).
- `S 01_qc/DE` T20 still reads "PENDING… not promoted" for the run that fed stages 2 and 3.
- `C README.md:18` says "(not yet run)", and C46's DECISIONS header says "Nothing here has been run yet".
- The cluster has `.ipynb_checkpoints` inside four `runs/<tool>/<stage>/` directories [v]. LAYOUT §3.4
  names exactly this hazard.

---

## 7. Feedback on GOALS.md layer 3

**A1.1.**
- "No glue script" needs a definition. Proposed: *the only cohort-authored inputs are the samplesheet, the
  design sheet, the project registry and marker inputs, and decisions files; every stage job is generated
  by the harness from them.* Without this, hand-written per-stage `.pbs` files are themselves cohort glue.
- "the plugins the design admits" can only be measured if the planner says which plugins it admits.
  Proposed: *…and the plugins the planner admits for the design and the data (each skip named with its
  reason).* C46 cannot run velocity: it has no BAM.

**A1.2.** Add *"as a checked table in the repository"*. As written, the mapping can live in someone's head.

**A1.3.**
- Add *"from a lock that records the resolved versions"*. P5 failed because the requirements were ranges.
- Add *"the self-test exercises the pipeline on a synthetic object, not only imports"*.
- Add a re-check: *"rebuilt at least monthly"*. Environments rot as their dependencies move.

**A2.1.** Stage 2's promoted run cannot reproduce at current `main`, by design: labels changed on purpose
since then. Proposed: *"…reproduces at its own tool commit; when `main` changes a stage's outputs on
purpose, a run of `main` is reproduced and re-promoted."*

**A2.2.** Specify the sample, or the reviewer picks claims that confirm. Proposed: *"10 claims per
repository, drawn by a seed from the sentences in README and docs that name a command, flag, file or output,
before any code is read"*.

**A2.3.** Name the agent's inputs and the outcome. Proposed: *"given only the stage RUNLOG, the tool's
README and the cluster, with no transcript, the agent writes and submits the reproduction job, and its
COMPARISON is IDENTICAL on deterministic outputs; time and tokens are reported."*

**A3.1.**
- Its first clause repeats A1.1's "shown on SAMBO and BrainOrganoid_C46". Keep A3.1 for the two clauses
  only it has.
- Define the leak word list: *"generated from every cohort's design sheet (sample ids and factor levels)
  and the site's queue names"*. Today's list cannot see the factor levels in the tools' tests.
- Name the axes: *"assay, species identifiers, control order, raw-droplet delivery layout"*.

**A3.2.**
- Make the covariate concrete: *"a continuous covariate (e.g. library size or age in weeks)"*.
- Add *"and the sign of every DE and DA table equals the declared control (checked across tools)"*. P1 was
  a direction error under a correct label, and a label check would pass it.
- Slide 15 shows per-stratum contrasts ("HFD vs Chow | Young"). Say they are required for DE and DA, not
  only for CellChat.

**A3.3.**
- "Whose behaviour depends on the assay" is ambiguous. scAnno and scIntegrate do not branch on the assay,
  but they print nucleus wording. Proposed: *"each tool publishes a table of its rules with scrna and snrna
  columns, refuses a missing assay, refuses an input made under the other assay, and words its output per
  assay; CellBender never runs on scrna."*
- QC.1's layer-2 words, "count floors derived from the data", conflict with the PI's declared single-cell
  floors (D8/D9). Only the PI can reword layer 2: a suggestion is *"derived from the data for nuclei;
  declared for cells until a data-derived procedure is accepted."*

**A3.4.** The new bar (1M cells through A1.1) can only be measured once A1.1 exists. Until then, report each
stage's scaling separately: *"each stage completes on ≥ 1M cells on the standard queues"*. Then the
memory wall at scAnno's joint clustering is found early.

**A4.1.**
- `sch conform` is repository-level and cannot certify a plugin. Proposed: *"passes every stage of
  `sch dev check --point kernel --name <p>`, and the repository passes `sch conform`"*.
- The test collides with the PI's held-out rule (§5 P1). Say whether A4.1 retires it.

**A4.2.**
- Require the draw rule and the tolerance to be committed before the draw.
- Report tokens and cost alongside time.
- Say what happens to the maker's held-out evidence once the eight are spent: the draw is the new test set.

**A4.3.**
- "Names its peer-reviewed source" should mean *a DOI or PMID field*.
- "Pinned version" should mean *an exact version of every wrapped package*, R packages included.
- Say whether a preprint counts. pertpy's paper is a preprint (INFERRED).

**A4.4.** Fix the questions in advance: *"five questions written before the test"*. Measure "without
reading the plugin's code" from the agent's tool log: *"no read under kernels/"*.

**A5.1.**
- Define "survives": *"after the review, every withdrawn claim is absent from the rendered section, and at
  least one claim stands"*.
- Define "independent": *"a reviewer with no access to the author's context"*.
- Allow tables to be cited.
- Note that slide 16's "To be done" understates what already exists for CellChat.

**A5.2.** Add *"the follow-up's result is written back to the hypothesis as supported or refuted"*.
Otherwise the loop has no end state.

**A6.1.** Add one measurable bar: *"a user who has not used the harness completes the SAMBO request from the
page, with no terminal"*.

**A6.2.**
- "No manual conversion" conflicts with Lab's design, which asks two questions in the browser that it cannot
  answer for the user. Proposed: *"through Lab's converter, answering only Lab's own two questions"*.
- Name the object: *"stage 3's integrated object, carrying stage 2's labels and stage 4's per-cell outputs"*.

**A7.1.** C46 is no longer held out; it was used to upgrade the tools. Name *"a third cohort, unseen by the
skills' authors"*. One public cohort of 1M cells or more could serve both A3.4 and A7.1.

**Missing tests.**
- **Figure generation and configuration.** Slide 16 ticks it, and GOALS has no id or test. Proposed A2.4:
  *"every stage writes its figures as files in its results tree, and a user changes the figure plan by a
  declared edit that redraws without recomputing."* scQC fails this today.
- **ANNO.2, "ultra-fast, consistent".** No test. Proposed: *"annotate twice gives identical labels, and wall
  time per 100k cells is reported"*.
- **Slide 4's "audit and record".** Proposed A7.2: *"an independent agent audits a sealed cohort run, and
  every decision in it resolves to a recorded who and why."*
- **ADR-0027's thesis**, that a default equal to SAMBO's value hides a bug. Proposed for A3.1: *"no declared
  axis has a literal default (S13), and every declared axis is read by a branch (GAP-011)."*

---

## 8. A suggested order for the first waves

Order by how much each step unblocks. Each reason is one line.

**Wave 0. Hours, coordinator, no PI.**
1. **GAP-010** (records): puts 720930 and 720932 in the record, which A1 (the scQC merge) and A2.1 need.
2. **GAP-008** (generated word lists): every later leak claim depends on a guard that can see factor levels.
3. **GAP-059** (commit gates in three tools): rule 1(a) becomes enforced rather than remembered, before any
   wave lands.

**Wave 1. Four lanes at once.**
1. **GAP-017** (merge the scQC branch; switch `~/tools/scQC` to `main`): restores rule 2 on `main`, and
   unblocks C46 and four scQC gaps.
2. **GAP-038** (scProfile environment lock): unblocks every stage-4 run, the DE fixture and A1.3.
3. **GAP-011 with GAP-007** (axis-read check, fixture axes): one harness change makes A3.1 and A3.3 testable
   in all five repositories at once.
4. **GAP-005** (catalogue): prerequisite for A4.4, self-assembly (GAP-049), the co-scientist (GAP-012) and
   the A4.2 conversions.

**PI, in parallel, asked once with recommendations.**
- P1: the held-out rule. It unblocks DE, DA, A4.1 and the `48aaeba` merge.
- P2: the DE sign convention.
- P3: the promotions.

**Wave 2.**
1. **GAP-002, then GAP-001** (one design sheet, then the `qc@scqc` adapter): the spine of A1.1, A7.1 and A2.3.
   Prove it on SAMBO stage 1 first.
2. **GAP-028** (scAnno corpus builder) **and GAP-027** (root floor): C46 stage 2 without project glue.
3. **GAP-039 to GAP-041** (DE control, the design cases, abundance), after P1: closes A1.1's profiling
   clause and A3.2.
4. **GAP-023, -032, -054** (fixtures that reach each pipeline): makes every later tool wave cheap to verify.

**Wave 3.**
1. **GAP-003, then GAP-004** (cohort-run skill, then the cold reproduction): A7.1 and A2.3 as soon as the
   adapter exists.
2. **GAP-047 and GAP-048** (a generic report generator, a review that removes): A5.1 beyond CellChat.
3. **GAP-015, then GAP-016** (measurements, then a 1M-cell cohort): A3.4.
4. **GAP-045, then GAP-044** (provenance keys, then the eight through the maker): A4.3 and A4.1.

**Wave 4.**
1. **GAP-046** (catalogue draw, A4.2).
2. **GAP-049** (self-assembly).
3. **GAP-012** (co-scientist).
4. **GAP-013** (UI).

These four rest on the catalogue, the review loop and the orchestrator, so they come last.

**Through every wave.** Run the docs-truth gaps (GAP-009, -022, -031, -037, -052) inside the wave that
touches each repository, not as waves of their own. Rule 5 bans trivial waves, and fixing docs alongside the
code they describe is the cheapest way to keep A2.2 green.
