> Archived 2026-11-09T10:06:15Z from audit pass 0002. Local paths are written as placeholders (the harness's leak guard).

# Audit pass 0002: the single-cell harness family against GOALS.md layer 3

**Pass** 0002 (full pass), auditor, read-only and adversarial. **Stamp** 2026-11-09T10:00Z.
**Graded against** `GOALS.md` as committed at harness `3860507`: twenty tests, A1.1 to A7.1.

## What was read

**Fresh clones** in `…/scratchpad/audit_0002/clones/`. Two mains moved during the pass. Main is graded at its
final state, and both SHAs are given below.

| repository | main at clone (09:13Z) | main graded (09:58Z) | what moved it |
|---|---|---|---|
| single-cell-harness | `00b63a3` | `3860507` | records only (`git diff --stat` shows `autodev/` files only) |
| scQC | `a51c38a` | **`0a9d2ce`** | W007 merged at 09:22:03Z |
| scAnno | `a126756` | `a126756` | — |
| scIntegrate | `9a2d7d1` | `9a2d7d1` | — |
| scProfile | `f294c89` | **`f5175ea`** | W002 merged at 09:35:01Z |
| scrnaseq-studio / scrnaseq-lab / rnaseq-service | `92ef97f` / `c4347b3` / `a42b747` | unchanged | — |

**Unmerged branches**, inspected by diff:
- Lab `autodev/W005-lab-cli` `51a00fa`;
- Studio `autodev/W008-studio-truth` `1d591f9`;
- Service `autodev/W009-sc-delivery` `99d872f`.

The harness branch `autodev/W010-qc-adapter` is not on GitHub or in the local refs. Its base clone and
notes are in `…/scratchpad/autodev/W010-*`, so it could not be graded.

**Records.**
- **S** = "<COHORTS>/SAMBO".
- **C** = "<COHORTS>/BrainOrganoid_C46".
- `RL` = RUNLOG.md.

**Cluster.** Four read-only connections out of the five allowed: `qstat -x`, `cat`, `ls`, `grep`,
`head` and `git rev-parse`. LAYOUT.md was read first. Nothing was written there.

**Run locally**, with an existing verifier venv and `TMPDIR` inside the scratch directory:
- `sch conform` on all eight repositories, with both cohorts' term lists and SAMBO's site shapes;
- the harness suite on a scratch copy: 616 tests, OK, 1 skipped;
- scAnno `tests/test_assay_rules.py` and `tests/test_docs_run.py`: 0 FAIL;
- scIntegrate `tests/test_statements_true.py` and `tests/test_cohort_axes.py`: PASS.

**Sub-audit.** One read-only sub-auditor drew claims for A2.2 by a seeded rule. Its files are in
`…/audit_0002/sub_a22/`. Three of its findings were re-read here, and all three held.

**Conventions.** Every PBS result quoted below was read from the run's own `SEALED.txt`, `FAILED.txt` or
`COMPARISON.txt` on the cluster, or from a RUNLOG line that quotes it. This pass computed no number about
data.

**Process note.** One transient file, `/tmp/x_old.py`, was written outside the scratch directory during an AST
comparison and deleted at once. Every other write is under `audit_0002/`.

---

## 1. Verdict

**NOT HAPPY.** 0 of 20 tests pass. 7 are PARTIAL and 13 FAIL. With this pass's rows applied, the register
holds 128 gap ids: 107 open, 2 in a wave and 19 closed. **47 of the gaps not closed are of size M or larger**,
and any one of them blocks HAPPY on its own.

The family moved today, but only at its edges:
- Three merges put rule 2 on scQC's and scAnno's `main`, gave scIntegrate a checked species, and let scProfile
  build its shared environment from a lock.
- Stage 3's promoted run now reproduces as predicted.

**The centre has not moved.**
- The harness still cannot run a tool: `sch/services/executor.py:147-148` refuses `pbs`, and no adapter exists.
- The second cohort is still at stage 1.
- Eight of nine plugins are still outside the maker's layout.
- There is no catalogue, no co-scientist and no UI.
- The platform's three verified branches wait on the PI's deploy (BLK-005).

## 2. Scoreboard

The pass-0001 column combines 0001 and 0001b, as STATE.md does. In 0001, A6.2 was PARTIAL and A6.3 UNKNOWN;
0001b set both to FAIL.

| test | 0001 | **0002** | reason for the change, or why it holds |
|---|---|---|---|
| A1.1 one request, every stage | FAIL | **FAIL** | unchanged: no stage driver; `pbs` is refused; C46 has no stage 2 |
| A1.2 the ten steps mapped | PARTIAL | **PARTIAL** | unchanged: no map; differential abundance never run; no pathway plugin |
| A1.3 environments from main | FAIL | **PARTIAL** | **up:** scProfile `f5175ea` builds its shared group from a 161-pin lock on a fresh prefix, PBS 782609 (selftest 7/7). The other three tools have no PBS build from `main` and still leave pieces unpinned |
| A2.1 pre-declared reproduction | PARTIAL | **PARTIAL** | holds. Stage 3 now reproduces as predicted (782587). Stage 1's full-table reproduction (782673) **missed as written**. Stage 2's promoted run was never reproduced, and stage 4 is unpromoted |
| A2.2 documentation true | FAIL | **FAIL** | holds. False claims remain in the harness, scIntegrate, scProfile, Studio and Lab. The sample found 0 false in scQC and scAnno |
| A2.3 cold reproduction | FAIL | **FAIL** | unchanged: never attempted |
| A3.1 held-out cohorts | FAIL | **FAIL** | holds. C46 is at stage 1. Studio fails the leak guard, three guards pass over 0 terms, and fixtures reach 1 of 4 pipelines |
| A3.2 design-aware | PARTIAL | **PARTIAL** | unchanged: the scProfile kernels are byte-identical to pass 0001 |
| A3.3 assay rule sets | FAIL | **PARTIAL** | **up:** scQC (`0a9d2ce`), scAnno (`a126756`) and scIntegrate (`9a2d7d1`) now meet it with no silent default. scProfile still changes captions only |
| A3.4 scale | FAIL | **FAIL** | unchanged: no cohort of 1M cells or more; three tools record no memory |
| A4.1 existing pool in one format | FAIL | **FAIL** | unchanged: 1 of 9 plugins is in the maker's layout (W013 is building `de`) |
| A4.2 maker on new tools | FAIL | **FAIL** | unchanged: no draw rule, and no catalogue tool converted |
| A4.3 provenance of methods | PARTIAL | **PARTIAL** | unchanged: no DOI field; 3 of 9 plugins pinned exactly in their declarations |
| A4.4 AI-native | FAIL | **FAIL** | unchanged: no catalogue, and `sch` cannot see scProfile's plugins |
| A5.1 report from evidence | PARTIAL | **PARTIAL** | unchanged: `paper.py` still prints withdrawn claims; CellChat only |
| A5.2 hypotheses | FAIL | **FAIL** | unchanged: no code |
| A6.1 Harness UI | FAIL | **FAIL** | unchanged: no UI code in any repository |
| A6.2 Studio hand-off | FAIL | **FAIL** | holds: Lab and Studio `main` are unchanged. W005 and W008 are held. Neither carries the run, so A6.2 would still fail after both merge |
| A6.3 Service single-cell requests | FAIL | **FAIL** | holds: Service `main` is unchanged. W009 is held, and the design, samplesheet writer and harness intake are still missing |
| A7.1 agents drive it | FAIL | **FAIL** | unchanged: no cohort-run skill |

**Tally: PASS 0, PARTIAL 7 (was 5), FAIL 13 (was 15), UNKNOWN 0.**

---

## 3. Per-test evidence

### A1.1 one request, every stage: FAIL
- **No stage driver.** At harness `3860507`, `sch/services/executor.py:147-148` returns
  `RefusedExecutor("pbs", "not shipped before ROADMAP Phase 9 …")`.
- **No tool adapter.** `sch/kernel.py:97-108` searches only `plugin.yml` directories, and `plugins/` holds
  only `gate`, `probe`, `single-cell` (five gates, probes and masks) and `table`.
- W010, which registered the `qc@scqc` adapter and a `pbs` executor at 08:57Z, has no pushed branch.
- **SAMBO** ran stage by stage from hand-written jobs. Its results directory has no `04_profile`.
- **C46** stopped at stage 1. On the cluster, `~/projects/BrainOrganoid_C46/results/` is empty and `runs/`
  holds only `measure/` and `scqc/`.

### A1.2 the ten steps mapped: PARTIAL
- **No map.** No table maps the ten steps to components in README, ARCHITECTURE, `docs/` or GOALS.
  GOALS.md:39 and :91 only name the steps.
- **What has run.** The components for steps 1–7 and 10 have run on a cohort, but outside A1.1.
- **Step 8.** Differential abundance has never run. W002's lock built its environment (782609 selftest 7/7),
  but no cohort run followed.
- **Step 9.** Pathways have no plugin.
- **The second clause** ("every mapped component runs in A1.1") cannot hold until A1.1 exists.

### A1.3 environments from main: PARTIAL (was FAIL)
**scProfile meets it** at `main` `f5175ea`:
- The lock is
  `setup/locks/x86_64-manylinux_2_17/abundance+cellchat+cellcycle+de+decoupler+liana+pseudotime.txt`, with
  161 `==` pins.
- PBS 782609 is SEALED with `exit=0`. P1 HELD: fresh prefix, 161/161 pins installed,
  `scprofile-env-6046e232ee`. P2 HELD: selftest 7 passed, 0 failed.
- 782609 built `27e254f`. Between `27e254f` and `f5175ea`, `setup/` and the lock differ only in comment lines
  of `constraints.txt`. The rest of the diff is a docstring and a help string in `scprofile/cli.py` (checked
  as text and by AST).
- Open: GAP-C27 (the glibc floor).

**The other three tools have no record of a fresh-prefix PBS build from `main`** (GAP-107):
- **scQC.** Torch is unpinned (`setup/install_env.sh:311-316`, GAP-018). The core lock lacks pyarrow, so its own
  suite fails in the environment it builds (`conf/env/requirements.lock.txt`, GAP-C05).
- **scAnno.** `_selftest` runs only `tests/test_adversarial.py` (GAP-032).
- **scIntegrate.** `--add-to` installs `scib scvi-tools bbknn harmonypy` unpinned (`setup/install_env.sh:144`,
  GAP-036).

### A2.1 pre-declared reproduction: PARTIAL
Every prediction below was in its job file before submission. Job-file mtimes, all UTC: job 27 at 07:34:46,
job 30 at 08:49:19 (submitted 08:49:41), the scProfile job at 08:48:26.

| stage | promoted run | today's reproduction | grade |
|---|---|---|---|
| 1 QC | `6e3b4b97cb38` (`133a951`); the run directory is gone (BLK-007), and `results/01_qc` is intact | **720930** (`0e6a5f6`, code-identical to `a51c38a`): IDENTICAL as predicted on kept barcodes, criteria and names (`COMPARISON.txt:14`). **782673** (`0a9d2ce`, every table): FAILED `exit=1`, **VERDICT DIFFERENT**. Kept, criteria and names IDENTICAL (100,713). 94 of 117 tables byte-identical. `cell_col` and `n_not_tabled` appear only in the new run, in all 10 `apply_measure.metrics.json`, from main's `0e6a5f6`. UMAP spread in 2 of 10 libraries (Aging1 x max \|Δ\| 26.18) | values reproduce; **the full-table prediction missed** (GAP-C33, GAP-102) |
| 2 annotation | `bd45f5d` | 782626: IDENTICAL, but against the **non-promoted** `c16c56a` rescue run (`S/stages/02_annotate/jobs/24_rescue_assayrules_reproduce.pbs:35,61`) | promoted run never reproduced (GAP-033) |
| 3 integration | `713d918` (`results/03_integrate`) | **782587: AS PREDICTED**, A to E (`COMPARISON.txt:53-54`). Deterministic parts identical. Harmony within its named spread (≤0.2138 on the embedding, total 0.6839 against 0.6868). scvi and scanvi within 0.0001. LISI spread measured for the first time (≤2.6e-4) | **meets the test** |
| 4 profiling | none (cluster `results/` has no `04_profile`) | 782672 is a W002 check against an unpromoted reference: 72 of 90 tables byte-identical, 18 `cellchat_centrality.csv` within ≤1.03e-15; FAILED, missed as written | no promoted run (GAP-055) |
| C46 1–4 | none (`results/` empty) | 782632: IDENTICAL to the unpromoted 720932 (53,534 kept) | nothing promoted (GAP-056) |

### A2.2 documentation true: FAIL
**Seeded draws, 12 claims per repository** (`sub_a22/draw_*.txt`):

| repository | false of checkable |
|---|---|
| scQC (`a51c38a`) | 0 of 11 |
| scAnno | 0 of 9 |
| scIntegrate | 1 of 11 |
| harness | 2 of 12 |

**False claims re-read here:**
- **harness** `README.md`:
  - `:25` says "most recently PBS 707628, every tier green". ADR-0027:146-165 records PBS 719917 with failures.
  - `:48-75` is a transcript that mounts `qc@scqc`, and `:75` runs `sch diff`, which is not a subcommand.
  - `:209` says the children mount "through a thin adapter".
  - `:227` says "144 tests". 616 ran.
- **scIntegrate** `README.md:203`: `sch dev new` is said to write "a skeleton". On this DEVPOINTS it writes none
  (`sch/dev/scaffold.py:119-129`; GAP-109).
- **scProfile** `docs/EXECUTION.md:259-271` documents `pbs` and `slurm` executors. `scprofile/` has no `qsub`,
  no `sbatch` and no `--executor` (GAP-052).
- **Studio** `src/components/Methods.tsx:150` writes "was tested with DESeq2", against `Stats.tsx:470` and
  `:509` (GAP-P22).
- **Lab** `README.md:12-17` says it asks "two questions … Nothing else is asked" (GAP-P17).

**Also:** `scanno report --help` crashes on a bare `%` (`scanno/cli.py:2542`; GAP-C30). An AST scan of every help
string in the five Python repositories found no other bare `%`.

### A2.3 cold reproduction: FAIL
No record of an attempt. grep finds none in S's RUNLOGs, `autodev/waves/` or C46's records.

### A3.1 held-out cohorts: FAIL
**C46 is at stage 1** (see A1.1).

**The leak guard,** run with both lists and SAMBO's site shapes:
- scQC, scAnno, scIntegrate and scProfile `f5175ea` now pass S1. GAP-051 is closed.
- Studio `main` fails S1 at `DESIGN.md:738`.
- The harness fails only on records: `GOALS.md` and `autodev/STATE.md` (GAP-110).
- The three platform repositories have no guard at all (S2 FAIL; GAP-104).

**What the guards cannot see:**
- The lists hold no factor level and no queue name (GAP-008). Whole-word levels remain in scQC, scAnno and
  scProfile tests (59 lines in scProfile).
- scProfile's own guard spells the first cohort's design (`tests/test_portability.py:81-82`).
- The guards of scAnno, scIntegrate and scProfile pass over 0 terms (GAP-C26).
- The harness's conform drops a single missing term file (GAP-101).

**The fixture reaches the pipeline in 1 of 4 tools:**
- scQC runs `describe` (`DEVPOINTS.yaml:17-19`).
- scAnno runs `cluster`.
- scProfile accepts "are not ready" (`DEVPOINTS.yaml:59`), and `jobs/dev_suite.pbs` sets no `SCH_DEV_PREFIX`.

### A3.2 design-aware: PARTIAL
`git diff f294c89 f5175ea -- kernels/` is empty.
- DE contrasts `sorted(levels)[-1]` against `[0]` (`kernels/de.py:1394,1403`).
- Abundance fits `formula=term` one factor at a time, so the interaction is dropped
  (`kernels/abundance.py:1520-1524`).
- Covariates are neither modelled nor refused by name.

What holds: one factor at n = 2, and DE fits the interaction. W013 (`de` through the maker) is building.

### A3.3 assay rule sets: PARTIAL (was FAIL)
**scQC `0a9d2ce`** meets it:
- `modules/01_ambient/ambient.py:59` sets `DENOISE = {"snrna": True, "scrna": False}`, and `:170` plans no denoiser
  for cells.
- `engine/graph.py:123` refuses mixed assays, `:183` takes `_ambient_none` for cells, and `:72` strips the value.
- The bounds are per assay (`modules/05_quality/quality.py:68, 92, 410`).
- Ingest refuses an absent assay.
- 720930 is IDENTICAL and 782632 is IDENTICAL.

**scAnno `a126756`** meets it:
- `scanno/assay.py:35-62` has no default, and RULES is published per assay.
- `cli.py:420-480` refuses a store of the other assay.
- The tests pass locally.
- Open: scope and rescue ignore the assay (GAP-C29).

**scIntegrate `9a2d7d1`** meets it: no rule depends on the assay (`axes.py:68 ASSAY_RULES = {}`). The assay is
optional with no default (`cli.py:1142-1150`), and the species is required and checked.

**scProfile `f5175ea`** does not:
- `detect_assay` "changes the CAVEATS, never the code path" (`scprofile/inputs.py:275-276`).
- A nuclei caveat is printed for every cohort (`kernels/cellchat.py:1350`).

**Service `main`** has no assay at all. W009 adds one with no default.

### A3.4 scale: FAIL
- No cohort of 1,000,000 cells or more has been chosen or run (GAP-016).
- No peak-memory code exists in scQC, scAnno or scIntegrate (GAP-015).

### A4.1 the existing pool in one format: FAIL
- 8 of 9 kernels carry `plots_unreviewed`. Only cellchat has `cellchat.draw.R` and `cellchat.signatures.json`.
- `DEVPOINTS.yaml:135-139` still holds all eight out.
- The cluster's harness, which runs the dev suite that grades this test, is at `40e187e`, behind `main`
  (GAP-108).

### A4.2 the maker on new tools: FAIL
No draw rule, and no catalogue conversion. ADR-0029 R11 now lets a conversion that meets A4.2 join the
shipped set; that is a rule, not a conversion.

### A4.3 provenance of methods: PARTIAL
- No `doi` key in any `kernels/*.py`.
- Exact pins in the declarations: scenic `pyscenic==0.12.1`, velocity, and cellchat (by commit).
- W002's host lock pins the seven shared-group members' packages, but in the environment, not in the plugin.

### A4.4 AI-native: FAIL
- scProfile's 23 subcommands include no list or catalogue (`scprofile/cli.py`).
- `sch` sees `plugin.yml` directories only (GAP-005).

### A5.1 report from evidence: PARTIAL
- The claims ledger exists for CellChat only.
- `scprofile/paper.py:799-800` appends the author's body verbatim, so a withdrawn claim stays on the page
  (GAP-048).
- The report is CellChat-only (GAP-047).

### A5.2 hypotheses: FAIL
"Hypothesis" appears only in guidance text (`scprofile/brief.py:320`, `compose.py:1114`). The harness has
none (GAP-012).

### A6.1 Harness UI: FAIL
No web, server or UI code in the harness or the four tools (GAP-013).

### A6.2 Studio hand-off: FAIL
Lab `c4347b3` and Studio `92ef97f` are unchanged on `main`. The branches, if merged:
- **W005 (Lab)** gives a tested `scrnaseq-lab convert` CLI, carries every design factor, reads nullable
  strings and makes bundles byte-reproducible. That closes P09, P11, P13 and P16.
- **W008 (Studio)** gives true DESeq2 wording and sentinel handling. That closes P22, P23 and P12.

Neither carries `uns` provenance into a run record, and Studio gets no Run card (P10, P19, P20). So
"Studio shows the run" fails even after both deploys.

### A6.3 Service takes single-cell requests: FAIL
Service `a42b747` is unchanged on `main`.

**W009 (`99d872f`, verified PASS, held)** would recognise Cell Ranger and CeleScope deliveries, require an
assay with no default, and keep the bulk JSON byte-identical. That closes P01 and P02.

**Still missing:**
- the factorial design (P03);
- scQC's samplesheet, registry and design writer (P04);
- the harness intake that runs a request as A1.1's input (P06, which waits on GAP-001);
- a species/build check (GAP-C34).

### A7.1 agents drive it: FAIL
- `skills/` holds `harness-agent`, `harness-developer` and `plugin-maker`.
- `skills/harness-agent/SKILL.md:90` still says the kernel refuses `pbs`.
- No skill assembles or submits a cohort (GAP-003).

---

## 4. The register's changes (`gaps_0002.tsv`: 68 rows, 16 closed, 50 open, 2 in_wave)

### Closed, with evidence re-checked in this pass
The five closures the brief named, plus the eleven that W007 and W002 claimed during the pass:

| gap | evidence (summary; full text in the TSV) |
|---|---|
| GAP-017 / GAP-C01 | the scQC `0a9d2ce` rule set (A3.3 above); 720930 and 782632 IDENTICAL; `~/tools/scQC` on `main` |
| GAP-029 | `scanno/assay.py`; store refusal at `cli.py:420-480`; `test_assay_rules` 0 FAIL locally; 782626 IDENTICAL |
| GAP-031 | `test_docs_run`: 19 commands as written, locally; sample 0 of 9 false. The residual is GAP-C30 |
| GAP-034 | `--species` required and checked; assay optional, no rule; `test_cohort_axes` PASS; 782587 part E |
| GAP-037 | `test_statements_true` PASS locally. A new false line is GAP-109 |
| GAP-038 | the lock plus 782609 (P1 and P2 held); kernels untouched |
| GAP-051 | S1 ok on `f5175ea` with both lists. The factor-level remainder moves to GAP-008 |
| GAP-022, GAP-025, GAP-C03, GAP-C04, GAP-C06, GAP-C08, GAP-C09, GAP-C10 | each read at scQC `0a9d2ce`, file:line in the TSV |

**Not re-written** (their ledger rows stand, accepted rather than re-proved):
- GAP-024: W007's commit 3da4bca and its tests.
- GAP-C02: read from `C/stages/01_qc/RUNLOG.md:146-176`.
- GAP-010.

**None of the claimed closures was disputed.** One caveat: GAP-051's text also covered first-cohort wording outside
the lists. That part is folded into GAP-008, with new evidence.

### Still open, re-checked (40 rows plus 2 in_wave; the brief asked for at least 15)
GAP-001, 003, 005, 008, 009, 015, 018, 019, 023, 032, 033, 036, 039, 040, 044, 045, 048, 050, 052, 054, 055, 056,
057, 058, 059, C05, C16, C23, C26, C29, C30, C31, C32, C33, C35, P09, P10, P17, P19 and P22, plus P01 and P02
(in_wave, held).

Notable updates:
- **GAP-059.** Since ADR-0029 R2, `sch conform` G1 passes a repository that versions no gate
  (`checks.py:253-266`), so this gap is now invisible to conform.
- **GAP-057.** Stage 1's UMAP spread has now been measured once, by 782673.
- **GAP-C23.** No `tests.` import remains anywhere, but only scAnno guards against one.

### New rows (GAP-101 to GAP-110)

| id | size | gap |
|---|---|---|
| GAP-101 | S | the harness's `sch conform` silently drops a single missing term file (`checks.py:96-107`, against its own docstring), so S1 passes over 0 terms. This is the GAP-C06 class, in the instrument every tool is graded by |
| GAP-102 | S | **W007 merged on a gate missed as written.** 782673 FAILED with VERDICT DIFFERENT. The deciding comparison (against 720930) and the F1 reading were written after submission and in the RUNLOG. That is outside the standing yes, so it is for the PI (decision 0b's family). W002's P3 miss is within rule 1's text, since no promoted stage-4 run exists |
| GAP-103 | S | C46's stage-1 RUNLOG ends at 782632's submission (`C/stages/01_qc/RUNLOG.md:179-181`), and its grade is only in SAMBO's RUNLOG |
| GAP-104 | S | the three platform repositories have no leak-guard test (S2 FAIL), and Studio `main` carries a first-cohort level combination (`DESIGN.md:738`) |
| GAP-105 | S | VERSION is never bumped across behaviour changes in scQC (0.4.0, 42 commits), scAnno (0.12.0, 26) and scProfile (0.1.0, 756). This is the GAP-C20 class |
| GAP-106 | S | scProfile's planner caches under `~/.cache/scprofile` (`scprofile/provenance.py:178-187`), outside the project (rule 3), and S3b does not see it |
| GAP-107 | M | no fresh-prefix PBS build from `main` exists for scQC, scAnno or scIntegrate, so A1.3 holds for scProfile only |
| GAP-108 | S | `~/tools/single-cell-harness` is at `40e187e`, behind `main`. A4.1's dev-suite grader and W010 would run without B1's changes |
| GAP-109 | S | scIntegrate `README.md:203` says `sch dev new` writes "a skeleton"; it writes none on this DEVPOINTS |
| GAP-110 | S | the harness fails its own S1 on records that tier II permits, and its pre-commit runs conform without terms (`setup/githooks/pre-commit:25`) |

### The amplifier, class by class
- **Leak guard passing over 0 terms** (C06): fixed in scQC. Open in scAnno, scIntegrate and scProfile (C26), and in
  the harness (GAP-101). The platform repositories have no guard (GAP-104).
- **`tests.` imports** (C23): 0 violations in five repositories. Only scAnno has a guard.
- **First-cohort reference default** (C31): only scQC's `build_reference.sh`. No other tool defaults species,
  organism or reference.
- **Bare `%` in help** (C30): only `scanno/cli.py:2542` and `:2587`.
- **VERSION not bumped** (C20): found in all four tools (GAP-105).
- **Scratch keyed on a name** (C10): fixed in scQC; no instance elsewhere. The nearby rule-3 finding is GAP-106.
- **Narrow reproductions** (C08, C28, C32): stage 1 now compares every table. Stage 2 still compares rescue
  columns (C28). Stage 4's P3 compared numeric tables only, so the CellChat layout spread is unmeasured
  (GAP-057).

### Records corrections for the coordinator
- **STATE.md decision 0c** says the promoted stage-3 run directory is gone. On the cluster,
  `runs/scintegrate/03_integrate/20260820T022842Z__scintegrate-713d918__03_integrate/` exists with 8 entries but
  no seal, report or tables. INFERRED: runs before 2026-09-06 were never sealed by the tool.
- **`~/tools/single-cell-harness`** is at `40e187e` (GAP-108).
- **C46's RUNLOG** lacks the grade of 782632 (GAP-103).

---

## 5. The five gaps whose closing would move the most tests next

1. **GAP-001: the stage driver** (`qc@scqc` adapter and `pbs` executor, W010). It is the spine of A1.1. Through
   GAP-003, GAP-P06 and GAP-016 it gates A7.1, A6.3, A3.4 and A1.2's second clause, and A6.1 needs a run to show.
   **About 6 tests.**
2. **GAP-044 with GAP-039, GAP-040 and GAP-041: the eight through the maker, DE and abundance first** (W013).
   Moves A4.1, A3.2, A1.2 (step 8), A1.1's profiling clause and A4.3 (pins and DOIs at migration).
   **5 tests.**
3. **GAP-056 with GAP-028: C46 stages 2–4.** Needs the PI's promotion of 720932 and a tool-built human corpus.
   Moves A1.1 and A3.1, A2.1's second cohort, and A7.1's held-out run. **4 tests.**
4. **GAP-002: one design sheet through the stages.** Removes the awk and the hand-written controls. Moves A1.1
   and A3.2, A6.3 (P03 and P04 write it), and A6.2 (factors survive into the final object). **4 tests.**
5. **GAP-005: the catalogue.** Moves A4.4, and is the prerequisite of A4.2 (GAP-046) and A5.2 (GAP-012).
   **3 tests.**

Close behind, all needing the PI, not development:
- **BLK-005**, the deploys of W005, W008 and W009. They close 9 platform gaps but move no grade alone.
- **GAP-033 and GAP-055**, which move A2.1.
