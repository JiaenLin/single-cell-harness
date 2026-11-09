> Archived 2026-11-09T13:29:12Z from audit pass 0003. Local paths are written as placeholders (the harness's leak guard).

# Audit pass 0003: the single-cell harness family against GOALS.md layer 3

**Pass** 0003 (full pass), auditor, read-only and adversarial. **Stamp** 2026-11-09T13:25Z.
**Graded against** `GOALS.md` as committed at harness `683ea89` (identical to pass 0002's `3860507`): twenty tests,
A1.1 to A7.1.

## What was read

**Fresh clones** in `…/scratchpad/audit_0003/clones/`, made at 12:22Z. Every `main` was checked again with
`git ls-remote` at 13:04Z and 13:20Z. Only the harness moved, and only in `autodev/` records
(`git diff --stat 683ea89..bcdc6d5 -- . ':!autodev'` is empty). So the graded code is each tool's final `main`.

| repository | main graded | moved since pass 0002 by |
|---|---|---|
| single-cell-harness | `683ea89` (code; records to `bcdc6d5`) | W010 merged (`26f7d01`), W016 merged (`6c81d15`) |
| scQC | `0a9d2ce` | — |
| scAnno | **`d0ee926`** | W011 merged (from `a126756`) |
| scIntegrate | `9a2d7d1` | — |
| scProfile | `f5175ea` | — |
| scrnaseq-studio / scrnaseq-lab / rnaseq-service | `92ef97f` / `c4347b3` / `a42b747` | — |

**Unmerged branches**, inspected by diff, never graded as `main`:
- scProfile W013 `35c6225`;
- scQC W014 `eace091`;
- scIntegrate W012 `69a54b2`;
- scAnno W021 `0b96969`;
- harness W019 `389127e`;
- Lab W005 `51a00fa` and W017 `427df3d` (now `d189655`);
- Studio W008 `1d591f9`;
- Service W009 `99d872f` and W015 `997d132`.

**Records.**
- **S** = `<COHORTS>/SAMBO`.
- **C** = `<COHORTS>/BrainOrganoid_C46`.
- `RL` = a stage's RUNLOG.md.

**Cluster.** Five read-only connections out of the five allowed: `ls`, `cat`, `grep`, `head`, `qstat -x` (with `-f`
for three jobs) and `git rev-parse`. LAYOUT.md was read first. Nothing was written there. Every PBS result below
was read from the run's own `SEALED.txt`, `FAILED.txt`, `COMPARISON*.txt` or `GRADE.txt`.

**Run locally**, in a scratch venv (Python 3.12.14, uv), with `TMPDIR` under the scratch directory:
- `python3 -m sch conform <clone> --terms <SAMBO list>:<C46 list> --shapes <SAMBO site_shapes>`, run from the harness
  clone on all eight repositories (`logs/conform_*.log`).
- The harness suite at `683ea89`, run twice:
  - plain;
  - with a dummy regular `tests` package in the venv's site-packages that `import tests` resolves to
    (`logs/harness_suite*.log`).
- `sch catalogue` over scProfile `f5175ea`.
- An AST scan of scAnno's help strings.

**Sub-audit.** One read-only sub-auditor drew 12 documentation claims per repository by a seeded rule written
before any check (`…/audit_0003/sub_a22/draw_*.txt`, `verdicts.tsv`). Four of its ten FALSE findings were
re-read here, and all four hold: scQC FILTERS.md:533, Studio README.md:106, scProfile README.md:85 and the harness
README.md:101.

**Conventions.** This pass computed no number about data. A number quoted below is read from a sealed run's own
files and named with its PBS id. A ledger's or STATE.md's description is never the evidence.

---

## 1. Verdict

**NOT HAPPY.** 0 of 20 tests pass: 9 are PARTIAL and 11 FAIL.

With this pass's 47 rows applied, the register holds 161 gap ids: 91 open, 39 in a wave and 31 closed.
**46 of the gaps not closed are of size M or larger**, and any one of them blocks HAPPY on its own.

**What moved.**
- Two tests moved up, each on one merged wave:
  - **A1.1**: stage 1 of SAMBO now runs through the harness and reproduces the promoted run (W010);
  - **A4.4**: a static catalogue an agent can list (W016).
- SAMBO's promoted stage 2 now reproduces at its own commit (PBS 783148).

**What weakened.**
- Stage 3's named harmony spread was broken by a second run (PBS 782882). A2.1 stays PARTIAL.

**The centre still has not moved.**
- Three of the four stages have no adapter, and nothing chains the stages.
- The second cohort is still at stage 1. A hand-written Seurat script of its later steps sits at the project root, in
  none of its records (GAP-113; that it stands in for the family is an inference).
- Eight of nine plugins are outside the maker's layout.
- There is no co-scientist and no UI.
- Every platform `main` is unchanged.

## 2. Scoreboard

| test | 0002 | **0003** | the main reason (gap ids) |
|---|---|---|---|
| A1.1 one request, every stage | FAIL | **PARTIAL** | **up:** stage 1 runs through `sch mount qc@scqc` with the pbs executor and reproduces the promoted run (PBS 782817, 782922). Stages 2–4 have no adapter, there is no driver, and C46 has never run through the harness (GAP-001, -002, -056) |
| A1.2 the ten steps mapped | PARTIAL | **PARTIAL** | no map. Step 2 on nuclei has only run outside the tools, step 8's abundance never ran, and step 9 has nothing (GAP-058, C49, -041, -042, -043) |
| A1.3 environments from main | PARTIAL | **PARTIAL** | scProfile only (PBS 782609). scQC's fresh build missed P1 with installer exit 1 (PBS 782920, a branch); scAnno and scIntegrate have none (GAP-107, -018, C05, -032, -036) |
| A2.1 pre-declared reproduction | PARTIAL | **PARTIAL** | stages 1 and **2 (new, PBS 783148)** reproduce. Stage 3's named spread was broken by PBS 782882; stage 4 and C46 have nothing promoted (GAP-C54, -057, -055) |
| A2.2 documentation true | FAIL | **FAIL** | the seeded draw finds 10 false of 96, in 6 of 8 repositories, and every pass-0002 false line stands (GAP-009, -052, -115, -116, -117, P17, -114) |
| A2.3 cold reproduction | FAIL | **FAIL** | never attempted, and the harness suite is red on a fresh clone (GAP-004, -111) |
| A3.1 held-out cohorts | FAIL | **FAIL** | C46 is at stage 1. Fixtures reach 1 of 4 pipelines; the lists hold no factor levels; Studio and Service fail S1 (GAP-056, -007, -023, -008, -104) |
| A3.2 design-aware | PARTIAL | **PARTIAL** | scProfile `main` kernels are unchanged: alphabetical contrasts, the interaction dropped in abundance, covariates silent. W013 fixes DE on a branch (GAP-039, -040) |
| A3.3 assay rule sets | PARTIAL | **PARTIAL** | three tools meet it. scProfile still changes captions only, and Service `main` has no assay (GAP-050, C51, P02) |
| A3.4 scale | FAIL | **FAIL** | no cohort of 1M cells or more; three tools record no memory (GAP-016, -015) |
| A4.1 existing pool in one format | FAIL | **FAIL** | 1 of 9 in the maker's layout. W013 is not merged (verifier FAIL), and no cluster dev-suite run since 2026-10-02 (GAP-044) |
| A4.2 maker on new tools | FAIL | **FAIL** | no draw rule and no catalogue conversion (GAP-046) |
| A4.3 provenance of methods | PARTIAL | **PARTIAL** | the catalogue reads no DOI for 9 of 9 plugins and an exact pin for 3 of 9 (GAP-045) |
| A4.4 AI-native | FAIL | **PARTIAL** | **up:** `sch catalogue` lists 22 plugins statically. A scProfile row cannot be planned or mounted through `sch` (GAP-001, C56) |
| A5.1 report from evidence | PARTIAL | **PARTIAL** | `paper.py` still prints withdrawn claims; CellChat only (GAP-048, -047) |
| A5.2 hypotheses | FAIL | **FAIL** | no code (GAP-012) |
| A6.1 Harness UI | FAIL | **FAIL** | no code (GAP-013) |
| A6.2 Studio hand-off | FAIL | **FAIL** | Lab and Studio `main` are unchanged. No branch gives Studio a Run card, and the final object drops earlier stages' records (GAP-P09, P19, P20, -014) |
| A6.3 Service single-cell requests | FAIL | **FAIL** | Service `main` is unchanged. W009 and W015 are held, and the harness has no intake (GAP-P01–P04, P06) |
| A7.1 agents drive it | FAIL | **FAIL** | no cohort-run skill, and A1.1 does not exist end to end (GAP-003) |

**Tally: PASS 0, PARTIAL 9 (was 7), FAIL 11 (was 13), UNKNOWN 0.**

---

## 3. Per-test evidence

### A1.1 one request, every stage: PARTIAL (was FAIL)
**What holds (W010):**
- **One tool adapter.** `plugins/single-cell/qc@scqc/` (`plugin.yml` wraps scQC 0.4.0). `sch/services/executor.py:439-444`
  ships `local` and `pbs`; pass 0002's refusal of `pbs` is gone.
- **PBS 782817** (job 31; harness `9748284`, scQC `0a9d2ce`): `SEALED.txt` exit=0, 10:29:05Z.
  - `COMPARISON_GRADED.txt`: "AS PREDICTED (1') - only F1's two keys, in all 10 call records".
  - `ISOLATED_GRADED.txt`: "IDENTICAL (4) - through the harness, scQC gives exactly what it gives alone".
  - Mount, then "RESTORED".
- **PBS 782922** (job 33; harness `b733c7e`, the commit merged as `26f7d01`): `SEALED.txt` exit=0, 11:57:19Z.
  - The same two grades.
  - "ALL READ-ONLY".
  - The negative control was "REFUSED BY NAME".
  - The harness's own pbs executor ran 4 child jobs, sealed exit 0. By name and time, they are PBS 783122–783125
    in `qstat -x`.

**What fails:**
- **Stages 2–4 cannot run through the harness.** There is no adapter for scAnno, scIntegrate or scProfile, and nothing
  chains stages (grep of `sch/` and `plugins/`). `skills/harness-agent/SKILL.md:39-41` says so for scProfile. W026
  (`anno@scanno`) is building (per the ledger).
- **C46 has never run through the harness.** On the cluster, `~/projects/BrainOrganoid_C46/` has `stages/` 00–01
  only and an empty `results/`.
- **A hand-written Seurat script of C46's later steps** (`c46.R`, with `c46_org.rds`) sits at the project root, dated
  2026-10-26, in none of C46's records (GAP-113). INFERRED: someone needed those steps and did them outside the family.
- **Each cohort run is a hand-written job.** Jobs 31 and 33 are 40 KB and 49 KB. That is legitimate as a
  reproduction, but there is no "one request".
- **Step 2 on nuclei is upstream of every adapter.** CellBender cannot run inside scQC (PBS 782920's M1), so SAMBO's
  denoised input came from `S/stages/01_qc/cellbender_run.py` (GAP-C49).

### A1.2 the ten steps mapped: PARTIAL
- **No map.** A grep of the harness finds the ten steps only in `GOALS.md:39,91` and in the ledgers.
- **The ten steps** (report, slide 2):
  1. alignment and cell calling;
  2. ambient RNA removal;
  3. QC;
  4. doublet detection;
  5. normalisation and feature selection;
  6. batch integration;
  7. clustering and annotation;
  8. differential abundance and expression;
  9. pathways and trajectories;
  10. other advanced analyses.

| steps | status |
|---|---|
| 3, 4 (scQC) | run inside the family on a sealed cohort run (PBS 782817) |
| 5, 7 (scAnno) | run inside the family (PBS 783148) |
| 6 (scIntegrate) | run inside the family (PBS 782587) |
| 8, DE | run (PBS 720487, `SEALED.txt` exit=0 at `f294c89`, whose kernels equal `main`'s; 782918 on a branch) |
| 10 (CellChat) | run (PBS 712314, `SEALED.txt` exit=0 at `f7e5a0d`) |
| 1 | upstream, as G1 permits |
| 2, on nuclei | only outside the tools (GAP-C49) |
| 2, on cells | declined by the PI's D6 |
| 8, abundance | never run (GAP-041) |
| 9 | no pathway plugin (GAP-042); trajectories never run (GAP-043) |

- **Clause 2** ("every mapped component runs in A1.1") cannot hold until A1.1 exists.

### A1.3 environments from main: PARTIAL
- **scProfile meets it.** PBS 782609 `SEALED.txt` exit=0:
  - P1 HELD: the fresh prefix `env/scprofile-fresh-20261109T080604Z`, 161/161 pins, `scprofile-env-6046e232ee`;
  - P2 HELD: 7 passed, 0 failed.
  - It ran `27e254f`. `git diff 27e254f f5175ea -- setup/` changes comment lines of `setup/locks/constraints.txt`
    only, and `kernels/` is identical (re-checked here).
- **scQC does not.** On `main` `0a9d2ce`:
  - torch is unpinned: `setup/install_env.sh:313-316` installs `cellbender==0.3.2` alone;
  - `conf/env/requirements.lock.txt` holds 0 `pyarrow` lines.
- **scQC's W014 fresh build, PBS 782920** (branch `a2c8471`), `FAILED.txt` exit=1:
  - "P1 MISSED: installer exit 1 … xgboost 1.7.6.1 (pinned 1.7.6)";
  - B1 MISSED (`env/sambo` is python 3.12.12);
  - P2 HELD, 45/0/1;
  - P3 MISSED on `/versions/python` only.
  - Job 34 (PBS 783151, `98504bd`) was still running at 13:25Z (`qstat -x`, R 00:48), so it is not graded here.
- **scAnno does not.** `scanno/cli.py:35-37`: `_selftest` runs `tests/test_adversarial.py` only. No fresh-prefix build.
- **scIntegrate does not.** `setup/install_env.sh:144` runs `pip install scib scvi-tools bbknn harmonypy` with no pins.
  No fresh-prefix build.

### A2.1 pre-declared reproduction: PARTIAL

| stage | promoted run | reproduction (read on the cluster) | meets A2.1? |
|---|---|---|---|
| 1 QC | `6e3b4b97cb38` (`133a951`; its run directory is gone, and `results/01_qc` is intact) | **782817 and 782922: AS PREDICTED (1').** 117 tables in both; 100,713 kept; every criterion and cell name identical. Values differ only by the two record keys `main`'s `0e6a5f6` added, which were predicted before submission. UMAP x/y spread named per library in `COMPARISON.txt` (Aging1 x ≤ 26.6) | yes, in substance |
| 2 annotation | `bd45f5d` (PBS 664864) | **783148: IDENTICAL, "PREDICTION: HELD".** Branch B1 (inputs I0, environment E0). 1,464 obs columns over 31 objects. The joint object's X, layers, obsm, obsp and var are identical; 3/3 scope files and 20+25 tables are byte-identical; UNTRACED 0. The job file's mtime (12:20:34Z) is before its qtime (12:22:48Z) | **yes (new)** |
| 3 integration | `713d918` (its run directory exists, with `SEALED.txt` exit=0) | 782587: AS PREDICTED (harmony total moved 0.0029, named 0.013). Then **782882: "spread: BROKEN - harmony total 0.6589 vs 0.6868, moved 0.0279 (named: 0.013)"**, while "X_harmony max \|diff\| 0.0000"; the ranking flips | no: the variable output's named spread does not hold (GAP-C54, -057) |
| 4 profiling | none (`results/` has no `04_profile`) | W013's DE runs 782918, 782963 and 783150 are AS PREDICTED, on an unmerged branch | no promoted run (GAP-055) |
| C46 1–4 | none (`results/` is empty) | 782632 IDENTICAL to the unpromoted 720932 | nothing promoted (GAP-056) |

### A2.2 documentation true: FAIL
**The seeded draw:** `random.Random(3)`, 12 claims per repository, written before any check.

| repository | TRUE / FALSE / IMPRECISE |
|---|---|
| harness `683ea89` | 9 / **2** / 1 |
| scQC `0a9d2ce` | 8 / **3** / 1 |
| scAnno `d0ee926` | 11 / **1** / 0 |
| scIntegrate `9a2d7d1` | 11 / 0 / 1 |
| scProfile `f5175ea` | 8 / **2** / 2 |
| Studio `92ef97f` | 6 / **1** / 5 |
| Lab `c4347b3` | 11 / **1** / 0 |
| Service `a42b747` | 12 / 0 / 0 |

**False claims re-read in this pass:**
- **scQC** `docs/FILTERS.md:533` names two threshold classes. A third, DECLARED, is recorded at `engine/steps.py:1113`
  and `:1568`, and `quality.py:92` makes every scRNA floor DECLARED.
- **Studio** `README.md:106`: a volcano point "opens in Gene expression". `Stats.tsx:836-843` only pins a label, and
  `:636-645` says the click stopped navigating.
- **scProfile** `README.md:85`: "the template each plugin declares". Only `kernels/cellchat.py:468` declares one.
- **harness** `README.md:101`: "An agent is a plugin". `sch/registry/manifest.py:23` has no such class.

**Every pass-0002 false line still stands:**
- **harness** `README.md`:
  - `:27` "PBS 707628, every tier green";
  - `:82` `sch diff`;
  - `:236` "a thin adapter" (scQC only);
  - `:257` "144 tests" (676 ran).
- **scIntegrate** `README.md:204` ("a skeleton").
- **scProfile** `docs/EXECUTION.md:263-268` documents `pbs` and `slurm` executors; there is no `qsub`, `sbatch` or
  `--executor` in `scprofile/`.
- **Studio** `Methods.tsx:150` ("tested with DESeq2").
- **Lab** `README.md:12-17`.

**One of the false claims hides a behaviour defect** (GAP-114). `docs/DEVELOPING.md:306` says a generator that
cannot run is "never a pass". But `sch/dev/convert.py:1677` leaves "cannot say" out of the debt, so the stage reads
`done` (`:306-307`, `:371-373`).

### A2.3 cold reproduction: FAIL
- **No attempt.** A grep of S's and C's RUNLOGs, `autodev/waves/` and `waves.tsv` finds none.
- **A cold reproducer would first meet a red suite.** On a fresh clone, the harness's suite fails
  `test_conform_doctor.py:149-150` (GAP-111).

### A3.1 held-out cohorts: FAIL
- **C46 is at stage 1.** On the cluster at 13:05Z:
  - `stages/` holds `00_data` and `01_qc` only;
  - `results/` is empty;
  - `runs/` holds `measure` and `scqc` only.
- **The leak guard,** run with both lists and SAMBO's shapes:

| repository | result |
|---|---|
| the four tools | S1 ok |
| harness | S1 FAIL, only on `GOALS.md:90,97` and `autodev/STATE.md` (12 hits) |
| Studio | S1 FAIL at `DESIGN.md:738` ("Young_HFD") |
| Service | S1 FAIL at `README.md:37` (the delivering vendor's name, in a table of file-naming examples, which the pre-decider ruled generic vocabulary) |
| Studio, Lab, Service | S2 FAIL: no guard test (GAP-104) |

- **The guard sees little.** The lists still hold no factor level (GAP-008; W024 is built, its verifier running).
  Three tools' own guards pass over 0 terms (GAP-C26, re-read at the current mains).
- **The fixture reaches the pipeline in 1 of 4 tools:**
  - scQC runs `describe` (`DEVPOINTS.yaml:17-19`);
  - scAnno runs `cluster` (`:17-21`);
  - **scIntegrate runs `integrate`** (`:23-29`), the one that reaches it;
  - scProfile accepts "are not ready in this installation" (`:58-59`), and `jobs/dev_suite.pbs` sets no
    `SCH_DEV_PREFIX` (0 hits).

### A3.2 design-aware: PARTIAL
At scProfile `main` `f5175ea`:
- DE contrasts `levels[-1]` against `levels[0]` of `sorted(...)` (`kernels/de.py:1394,1403`).
- Abundance fits `formula=term` one factor at a time, so the interaction is dropped (`kernels/abundance.py:1518-1525`).
- Covariates are neither modelled nor refused by name.

**What holds:** one factor at n = 2, and DE's interaction.

**On W013's branch** (not `main`), PBS 782963 (`35c6225`) contrasts in the declared-control direction ("aged vs
young", "HFD vs chow", `age[T.aged]:diet[T.HFD]`). Every population is within 0.001 of 720548, at max |dev| 0,
and the caveat "NOT IN THE MODEL" is present (`COMPARISON.txt`). PBS 783150 (`af0f560`) seals "AS PREDICTED".
Its verifier failed D1 (per the ledger), and scProfile `main` is still `f5175ea`.

### A3.3 assay rule sets: PARTIAL
**Meet it:**
- **scQC:** `modules/01_ambient/ambient.py:59` `DENOISE = {"snrna": True, "scrna": False}`; `quality.py:92`
  `FLOOR_METHOD` is per assay.
- **scAnno:** `scanno/assay.py:35-40` has no default. `cli.py:450-471` now also refuses mixed or unknown assays in
  scope and rescue (GAP-C29 closed).
- **scIntegrate:** `axes.py:68` `ASSAY_RULES = {}`, so no rule depends on the assay.

**Do not:**
- **scProfile:** `inputs.py:275` `detect_assay` "changes the CAVEATS, never the code path", and `--assay` takes
  `cell`/`nucleus` (GAP-C51).
- **Service `main`:** no assay anywhere in `src/lib/`.

### A3.4 scale: FAIL
- No cohort of 1,000,000 cells or more has been chosen or run (GAP-016).
- A grep for `ru_maxrss|peak_rss|maxrss|peak_mem|tracemalloc|VmHWM` finds 0 files in scQC, scAnno or scIntegrate
  (GAP-015).

### A4.1 the existing pool in one format: FAIL
- **1 of 9.** `sch catalogue` reads FORMAT `maker` for CellChat and `one-file` for the other 8, which carry
  `plots_unreviewed` (grep).
- **No recent grading.** The cluster's newest dev-suite run is
  `runs/sch/00_devsuite/20261002T081440Z__sch-b2e79db__00_devsuite`. Nothing since.
- **W013** (DE through the maker) has sealed AS PREDICTED three times (PBS 782918, 782963, 783150). Its verifier
  failed D1 at `af0f560` (per the ledger), and it is not on `main`.

### A4.2 the maker on new tools: FAIL
No draw rule in any document (grep), and no conversion of a catalogue tool (GAP-046).

### A4.3 provenance of methods: PARTIAL
`sch catalogue --json` over scProfile `f5175ea`:

| field | result |
|---|---|
| `doi` | None in 9 of 9 |
| exact upstream version | scenic (`pyscenic 0.12.1`), velocity (`scvelo 0.3.4`), cellchat (`75253cd0c9e6`) |
| "(no pin)" | abundance, cellcycle, de, decoupler, liana, pseudotime |
| a citation | free text only, e.g. de: "Muzellec et al., Bioinformatics 2023; Love et al., Genome Biol 2014" |

### A4.4 AI-native: PARTIAL (was FAIL)
- **Lists:** `sch catalogue list --scprofile <scProfile>` at `683ea89` gives 22 plugins (13 harness, 9 scProfile)
  from 2 sources, 0 unreadable. Nothing is imported.
- **Picks:** the skill teaches the catalogue (`skills/harness-agent/SKILL.md:24-41`). The W016 verifier's cold probe
  answered 2 of 3 questions. That is a ledger claim; it was not re-run here.
- **Fails to run:** "A `scprofile:` row cannot be planned or mounted through `sch` yet" (`SKILL.md:39-41`), so the
  pick cannot be run "through the harness's agent surface".
- **Rows mislead** (GAP-C56):
  - every row's assays read "not declared";
  - `qc@scqc` reads COHORT RUN "unknown", although PBS 782817 and 782922 ran it on SAMBO.

### A5.1 report from evidence: PARTIAL
- `scprofile/paper.py:799-800` still appends the author's body after the banners, so a withdrawn claim stays on the
  page (GAP-048).
- Only `kernels/cellchat.py:468` declares a writing template (GAP-047).

### A5.2 hypotheses: FAIL
There is no hypothesis record, falsifying test or plan-from-hypothesis in the harness or scProfile (grep; GAP-012).

### A6.1 Harness UI: FAIL
There is no server or web code in the harness: no `http.server`, `flask`, `fastapi` or `websocket`, and no
`.html`, `.tsx` or `.js` file (GAP-013).

### A6.2 Studio hand-off: FAIL
- **No `main` moved.** Lab `c4347b3` and Studio `92ef97f` are unchanged.
- **The branches add no Run card.** W008 has 0 "Run card" or `meta.run` hits in `src`. Lab's W017 (`d189655`, not
  verified) writes a run record that Studio never reads (GAP-P19).
- **The record is gone before Lab.** scIntegrate `emit.py:138` writes only `uns["scintegrate"]`, so the final object
  arrives without scQC's and scAnno's records (GAP-P20).

### A6.3 Service takes single-cell requests: FAIL
- **No `main` moved.** Service `a42b747` is unchanged.
- **W009+W015** (verified, held, BLK-005) would add:
  - Cell Ranger and CeleScope recognition;
  - a single-cell request with no default assay;
  - scQC's samplesheet, registry and design table (`src/lib/scSheets.ts` on `997d132`).
- **Still missing:** the harness intake that runs such a request as A1.1's input (GAP-P06).

### A7.1 agents drive it: FAIL
- `skills/` holds `harness-agent`, `harness-developer` and `plugin-maker`. `harness-agent` now documents the pbs
  executor (`SKILL.md:108-111`).
- No skill assembles, submits or recovers a cohort across the stages, and A1.1 itself is partial (GAP-003).

---

## 4. What moved since pass 0002, and why

| what | why |
|---|---|
| **A1.1 FAIL → PARTIAL** | W010 merged (`26f7d01`). The harness's first tool adapter and its pbs executor reproduce SAMBO stage 1, both against the promoted run and against scQC alone (PBS 782817, 782922). One stage of four, on one cohort of two |
| **A4.4 FAIL → PARTIAL** | W016 merged (`6c81d15`): ADR-0030 and `sch catalogue`. Listing and picking hold; running a scProfile pick through `sch` does not |
| **A2.1 holds PARTIAL** | stronger: SAMBO stage 2's promoted run now reproduces (PBS 783148), so GAP-033 is closed. Weaker: stage 3's harmony total left its named spread (PBS 782882). That was found by W012's job and predates W012 |
| **A3.3 holds PARTIAL** | scAnno's scope and rescue now refuse mixed assays (W011) |
| **A2.2 holds FAIL** | W011 removed scAnno's first-cohort numbers and fixed `report --help`. But the fresh draw found new false lines in six repositories (GAP-114 to -117; GAP-009, -052, P17 updated) |
| everything else | no `main` that grades it moved |

## 5. The register's changes (`gaps_0003.tsv`: 47 rows)

### Closed (11 rows)

| gap | closure | evidence |
|---|---|---|
| **GAP-033** | new; the coordinator's closure confirmed | PBS 783148, from the run's own files, with the prediction's timing |
| **GAP-C36** | new; closed by this audit | `git diff a126756 d0ee926 -- scanno/classify.py` removes the first-cohort measurement; S1 ok |
| GAP-005, -006, -108, -030 | W016, W010 and W011 claims, re-checked | the catalogue run; ADR-0030 present; the cluster checkout; PBS 782921's TIMINGS block |
| GAP-C17, C19, C28, C29, C30 | W011 claims, re-checked | conform S1; `force.py`; PBS 782921; `cli.py:450-471`; the AST help scan |

None of the claimed closures was disputed.

### Still open, with new evidence (28 rows: 24 open, 4 in a wave)
- **XL/L:** GAP-001 (goal A4.4 added), -002, -012, -013, -028, -044 (in_wave), -056.
- **M:** GAP-003, -004, -015, -032, -035, -045, -052, -055, -107 (in_wave), P19, C49, C54 (in_wave).
- **S:** GAP-009, -057, -104, -105, -110 (in_wave), P17, C23, C26, C56.

**Re-checked and unchanged**, so no row: their `main` or cited lines are byte-identical to pass 0002's.
- GAP-007 and -011 (`sch/dev/fixture.py` and `sch/conform/checks.py` unchanged since `3860507`).
- GAP-021, -023, -026, -027 (`classify.py:132`), -036, -040, -041 (no abundance run in `runs/scprofile`), -042,
  -043, -046, -047, -048, -049, -050, -053, -054, -058, -059 (no `setup/githooks` in three tools), -102 (STATE
  decision 0b still open), -106, -109.
- P05 to P08, P18, P20 (`emit.py:138`), P21, P24.
- C07, C11, C13, C15, C16, C18, C24, C25, C27, C32, C33, C35, C37 (`rescue.py:192-196`, `KNOWN_ISSUES.md:59`), C45,
  C47, C48, C50 to C53, C55, C57 to C60.
- The in-wave rows of W005, W008, W009, W012 and W015, whose branches are unchanged.

### New (GAP-111 to GAP-118)

| id | size | gap |
|---|---|---|
| GAP-111 | S | **The harness's suite is red on every fresh clone.** `test_conform_doctor.py:149-150` asserts this clone's own `core.hooksPath`, the state ADR-0029 made a warning. Measured: 676 tests, 1 failure (this one), 1 skipped, with and without a shadowing `tests` package |
| GAP-112 | S | **SAMBO's stage-3 runs are left writable after their seal**, and a failed grade leaves two contradictory seals. Jobs 27–29 hold 0 `chmod` lines. Every file of 782587, 782882, 782883 and the promoted `713d918` run is `-rw-------`. 782882 holds the tool's `SEALED.txt` (exit=0) beside the job's `FAILED.txt` (exit=1). The other tools' runs are `-r--------` with one seal |
| GAP-113 | S | **A hand-written analysis of C46 sits outside the family and its records.** `c46.R` (Seurat: hand thresholds, CCA integration, clusters, a "Fig2E") and `c46_org.rds` (1.24 GB), 2026-10-26, sit at the project root. They are outside LAYOUT's depth-1 list and in none of C46's records. Amplifier: SAMBO's root holds 14 such entries from August–September |
| GAP-114 | S | **The maker's `convert` passes a stage whose generator cannot run** (`convert.py:1677`, `:306-307`, `:371-373`), against `DEVELOPING.md:306` |
| GAP-115 | S | **scQC's docs make three false claims:** `REPORT_DESIGN.md:7` and `:193`, `FILTERS.md:533` |
| GAP-116 | S | **scAnno** `docs/DIRECTIONS.md:26` denies what `scanno rescue` does |
| GAP-117 | S | **Studio** `README.md:106` (the volcano click). It is still present on W008 |
| GAP-118 | S | **STATE decision 0c (BLK-007) and pass 0002's records correction misstate the promoted stage-3 run.** It exists, sealed (exit=0, PBS 671045) |

### The amplifier, class by class
- **A suite red by construction on a fresh clone** (GAP-111): harness only. No other suite references `hooksPath`.
- **A run not sealed read-only, or with two seals** (GAP-112): only SAMBO's stage-3 jobs. The runs of stage 1, of
  stage 2 (W011, W018), of stage 4 and of `sch` read `-r--------` with one seal file each on the cluster, and stage
  2's job 25 carries `chmod a-w` at `:116`.
- **Files outside a project's depth-1 list** (GAP-113): in both cohorts on the cluster.
- **`tests` package shadowing** (GAP-C23):
  - 0 imports in all five Python repositories;
  - the harness suite measured immune;
  - only scAnno guards.
- **A guard passing over 0 terms** (GAP-C26): still in scAnno, scIntegrate and scProfile, and in the harness's
  single-file case (GAP-101, W024).
- **VERSION not bumped** (GAP-105, C20): all four tools. scAnno is now 34 commits past its last bump.
- **A false doc line**: 6 of 8 repositories in this draw. The two at 0 false were scIntegrate (whose `:204` stands
  from pass 0002) and Service.
- **A status that reads done or ok while something failed**:
  - the maker's `convert` (GAP-114);
  - stage 3's double seal (GAP-112);
  - scQC's evidence-mode STATUS (GAP-C16).

  scAnno and scProfile showed no instance in this pass's reads.

## 6. The held branches: how each would change a grade if merged

| branch | state | grade change if merged |
|---|---|---|
| scProfile W013 | 3× AS PREDICTED (read on the cluster); verifier FAIL D1 (per the ledger) | A4.1 stays FAIL (2 of 9). A3.2 stays PARTIAL: abundance still drops the interaction, and covariates are not refused |
| scQC W014 | job 34 running; verifier PASS on fix-up 3 (per the ledger) | A1.3 stays PARTIAL (2 of 4 tools) if job 34 holds P1 |
| scIntegrate W012 | job 28 missed line B (read on the cluster) | no grade; W025 must first make harmony's metrics reproducible |
| Lab W005 + W017 | W005 verified, W017 not (per the ledger) | A6.2 stays FAIL: no Studio Run card, and GAP-P20 drops earlier records |
| Studio W008 | verified (per the ledger) | A2.2 still FAIL (README.md:106 stays); no A6.2 change |
| Service W009 + W015 | verified (per the ledger) | **A6.3 FAIL → PARTIAL** (a single-cell request writes scQC's inputs; the harness intake is still missing) |
| harness W024 | built; verifier running (per the ledger) | A3.1 truer, still FAIL: its lists make more repositories fail S1 |
| harness W019 | verifier FAIL (per the ledger) | none directly |
| scAnno W021 | building (per the ledger) | unblocks C46 stage 2 (GAP-028), later A3.1 |

## 7. Records corrections for the coordinator
- **STATE decision 0c is wrong about stage 3.** `runs/scintegrate/03_integrate/20260820T022842Z__scintegrate-713d918__03_integrate`
  exists, with `SEALED.txt` exit=0 (PBS 671045, 2026-08-20T06:10:58Z), `report.json`, `tables/` and `objects/`.
  Pass 0002's "no seal, report or tables" was wrong too (GAP-118). The other three absences in 0c hold.
- **The cluster's tool checkouts are on unmerged branches.** At 13:22Z and 13:25Z:
  - `~/tools/scQC` on W014 `98504bd` (job 34 running);
  - `~/tools/scProfile` on W013 `190fcf4` (PBS 783236, `sambo_04_dethroughmaker`, running);
  - `~/tools/scIntegrate` on W012 `69a54b2`, gate missed, with no job running since 11:31Z.

  A cohort run started now would get unmerged code for three of four tools.
- **LEAN** (no goal): four `.ipynb_checkpoints` directories sit inside `~/projects/SAMBO/runs/<tool>/<stage>/`,
  dated 2026-11-08.

## 8. The five gaps whose closing would move the most, by leverage
1. **GAP-001, the remaining adapters and a stage driver.** W026 is the next step.
   - Moves A1.1 to its end, A4.4's run clause, A1.2's second clause and A7.1.
   - A6.3 needs it (P06), and A3.4 and A6.1 need a run to show. **About 6 tests.**
2. **GAP-056 with GAP-028 and GAP-113: C46 stages 2–4 through the family.**
   - Needs W021's `build-markers`, the PI's promotion of PBS 720932, and a word on `c46.R`.
   - Moves A1.1, A3.1, A2.1's second cohort and A7.1. **4 tests.**
3. **GAP-044 with GAP-040 and GAP-041: the eight through the maker, with W013's D1 fixed first.**
   - Moves A4.1, A3.2, A1.2's step 8, A4.3 (pins and DOIs at migration) and A5.1's coverage. **5 tests.**
4. **GAP-C54 with GAP-057: harmony reproducible, and spreads named from two or more runs** (W025).
   - Restores stage 3 for A2.1. A2.1 then needs stage 4's promotion (GAP-055) and C46's promoted stages.
   - Unblocks W012, whose wording and version fixes are A2.2's scIntegrate lines. **2 tests.**
5. **GAP-107 with GAP-C49: every tool's environment from `main`, and CellBender inside scQC.**
   - Moves A1.3, A1.2's step 2, and A1.1's first stage on raw nuclei. **3 tests.**

Close behind, needing the PI rather than development:
- **BLK-005**, the deploys of W005, W008, W009 and W015. A6.3 moves to PARTIAL on W009+W015.
- **Decision 0b and GAP-102.**
