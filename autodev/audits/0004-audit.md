# Audit pass 0004: the first scored pass

**Pass** 0004 (full pass), auditor, read-only and adversarial. **Stamp** 2026-11-10T04:50Z.
**Graded against** `GOALS.md` layer 3 and its section "Layer 3, scored" as committed at harness `7ca2515` (unchanged at
`f3f0de8`). Each test's score is the numerator and denominator fixed there; label PASS = 1, FAIL = 0, PARTIAL between.
Placeholders: `<HARNESS>` the harness checkout, `<COHORTS>` the cohort mirrors, `<SCRATCH>` this pass's scratch folder
(`.../scratchpad/autodev/audit0004`), `~` the cluster account's home.

## 0. What was read

**Fresh clones** in `<SCRATCH>/clones/`, made 03:05Z, each verified at the SHA graded. At 04:45Z `git ls-remote`
showed only the harness moved (`7ca2515` → `f3f0de8`): ten `autodev:` record commits and `setup/autodev/pbs_mirror.sh`
(18 lines). `git diff --stat 7ca2515 f3f0de8 -- . ':!autodev'` touches that one script, so the graded code is the final
`main`; S1 was re-run at `f3f0de8` with the same result (0 term hits, 37 site-string lines).

| repository | main graded | moved since pass 0003 by |
|---|---|---|
| single-cell-harness | `7ca2515` (code; records to `f3f0de8`) | W019 (`70c25b9`), W026 (`b26b643`), W024 (`e87b533`), `.mailmap` withdrawn (`1d7f303`), coordinator scripts to `setup/autodev/` (`2fc727d`) |
| scQC | `98504bd` | W014 (environments only: `git diff 0a9d2ce 98504bd -- engine modules adapters scqc_cli.py report` is empty) |
| scAnno | `68233f0` | W021 |
| scIntegrate | `9a2d7d1` | — |
| scProfile | `f5175ea` | — |
| scrnaseq-lab / scrnaseq-studio / rnaseq-service | `51a00fa` / `1d591f9` / `997d132` | W005 / W008 / W009 + W015, deployed by the PI |

**Unmerged branches**, context only, never graded: scQC W020 (`b255e45`), harness W029 (`006b72c`), scProfile W013/W032
(`b39ca4a`, `157ed9d`), scIntegrate W012/W025 (`b148030`), Lab W017, Studio W028.

**Cluster.** LAYOUT.md read first. **3 of the 5 allowed connections** used (04:17Z, 04:37Z, 04:37Z), login-node reads
only: `ls`, `cat`, `grep`, `head`, `qstat -x` (`-f` for four jobs) and `git` (`rev-parse`, `branch`, `status`, `remote`,
`log`). Scripts and raw outputs: `<SCRATCH>/cluster/batch{1,2,3}.{sh,out}`. Every PBS result below was read from the
run's own `SEALED.txt`, `FAILED.txt`, `*GRADED*.txt`, `COMPARISON.txt`, `VERDICT.txt` or `OBSERVATIONS.txt`.

**Run locally** (Python 3.12.14 uv venv; Node 26.7.0; everything in `<SCRATCH>`):
- `sch conform` S1 on all eight repositories with both cohorts' generated lists, with and without both cohorts' shapes
  (`logs/leak_terms_hits.tsv`, `logs/leak_shapes_hits.tsv`; full hit lists through `scripts/leakcount.py`, because the
  CLI's text output lists only the first lines of each check);
- the harness suite twice (without and with its `single-cell` extra);
- `npm test` on Service (no install needed), and `npm ci --ignore-scripts` + `npm test` on Lab and Studio;
- `sch catalogue list` and `--json` over scProfile `f5175ea`; a synthetic fixture from `sch dev fixture`.

**Two read-only helpers**, each on Opus 5.5 at max effort, one after the other:
- **A2.2 sub-auditor.** A seeded draw written by this pass before any check (`a22/draw_*.txt`: pass 0003's rule,
  `random.Random(4)`), its walks written 03:18–03:23Z before any code was read (`a22/walk_*.txt`), 96 drawn claims and
  18 known-false re-checks (`a22/verdicts.tsv`). Five of its FALSE findings were re-read here and all hold: harness
  README.md:173, scQC docs/WORKFLOW.md:127, scIntegrate docs/METHODS.md:252, Lab README.md:274 and Studio README.md:113.
- **A4.4 cold agent.** Given only the harness's skills, `sch`, a synthetic fixture and a question stated before it
  started. Two of its four defects were reproduced here (`logs/a44_*.out`).

**Conventions.** A number about data is read from a sealed run's own files and named with its PBS id. A ledger, STATE.md,
an ADR or a blind record is never the evidence; where one is cited, it is named as such.

---

## 1. Verdict

**NOT HAPPY. Mean score 0.271** (the 20 scores sum to 5.423). **14 of 20 tests are below 0.5**; the bar is a mean of at
least 0.9 with none below 0.5. Labels: **PASS 0, PARTIAL 13, FAIL 7, UNKNOWN 0** (one half of A6.2 could not be measured
and earns no credit; see §3).

The ceiling is structural. Two of four stages run through the harness, on one of two cohorts. There is no co-scientist, no
UI and no new-tool conversion, and the plugin pool is not on the cluster ladder. Those four tests score 0, and so do A2.3,
A6.2 and A7.1.

## 2. Scoreboard

| test | score | num / den | label | one line of evidence |
|---|---|---|---|---|
| A1.1 one request, every stage | **0.250** | 2 / 8 | PARTIAL | SAMBO stage 1 (PBS 782817, 782922) and stage 2 (PBS 783280, 783363) through `sch`, AS PREDICTED; stages 3-4 have no adapter; C46 has no `runs/sch` |
| A1.2 the ten steps mapped | **0.500** | 5 / 10 | PARTIAL | steps 3, 4 (qc@scqc) and 5, 7 (anno@scanno) run in A1.1; step 1 declared upstream; 2, 6, 8, 9, 10 do not |
| A1.3 environments from main | **0.400** | 2 / 5 | PARTIAL | scQC (PBS 783151) and scProfile (PBS 782609) build fresh with pins and pass their self-tests; scAnno, scIntegrate and the harness have none |
| A2.1 pre-declared reproduction | **0.500** | 2 / 4 | PARTIAL | stages 1 and 2 reproduce their promoted runs; stage 3 FAILED as written (PBS 783282); stage 4 has nothing promoted |
| A2.2 documentation true | **0.125** | 1 / 8 | PARTIAL | 9 new FALSE in a fresh draw of 96, and 17 of 18 known-false lines still false; only Service is clean |
| A2.3 cold reproduction | **0.000** | 0 / 4 | FAIL | never attempted |
| A3.1 held-out cohorts | **0.125** | 0.5×2/8 + 0.5×0/5 | PARTIAL | 2 of 8 cohort stages through A1.1; under the generated lists the leak guard is red in all four tools, and the harness is red on site shapes |
| A3.2 design-aware | **0.250** | 1 / 4 | PARTIAL | one factor holds; the interaction is not contrasted by DE and is a design-handling defect in DA; covariates silent; contrasts sorted, not SAMBO's |
| A3.3 assay rule sets | **0.800** | 4 / 5 | PARTIAL | scQC, scAnno, scIntegrate and the harness hold; scProfile changes captions only, in its own vocabulary |
| A3.4 scale | **0.050** | 201,426 / 4,000,000 | PARTIAL | 100,713 cells × 2 stages through A1.1 on standard queues (literal formula); no 1M-cell cohort has run |
| A4.1 existing pool in one format | **0.000** | 0 / 9 | FAIL | 1 of 9 in the maker's layout; no dev-suite run on the cluster since 2026-10-02; scProfile fails `sch conform` S1 |
| A4.2 maker on new tools | **0.000** | 0 / 5 | FAIL | no draw rule, no conversion |
| A4.3 provenance of methods | **0.333** | 3 / 9 | PARTIAL | all 9 cite a paper and declare no DOI; exact pins in 3 (cellchat, scenic, velocity) |
| A4.4 AI-native | **0.500** | 2 / 4 | PARTIAL | a cold agent listed and picked; `sch plan scprofile:abundance` died with a traceback, so nothing ran |
| A5.1 report from evidence | **0.923** | 12 / 13 | PARTIAL | PBS 711781's claim ledger: 13 claims, 12 standing, 1 narrowed, 0 withdrawn, by a separate reviewer; CellChat only |
| A5.2 hypotheses | **0.000** | 0 / 1 | FAIL | no co-scientist code; 0 hypotheses |
| A6.1 Harness UI | **0.000** | 0 / 5 | FAIL | no web or server code |
| A6.2 Studio hand-off | **0.000** | 0 / 2 | FAIL | Studio main has no Run card; the family's own final object was never put through Lab → Studio (part 1 UNKNOWN, no credit) |
| A6.3 Service single-cell requests | **0.667** | 2 / 3 | PARTIAL | Service main writes the request and scQC's three files from Cell Ranger and CeleScope deliveries; bulk byte for byte; no harness intake |
| A7.1 agents drive it | **0.000** | 0 / 5 | FAIL | no cold agent has run a held-out cohort; no skill runs a cohort across stages |

**Mean 0.271.** Below 0.5: A1.1, A1.3, A2.2, A2.3, A3.1, A3.2, A3.4, A4.1, A4.2, A4.3, A5.2, A6.1, A6.2, A7.1.

---

## 3. Per-test evidence

### A1.1: 0.250 (2/8), PARTIAL
**Stage 1 through the harness: counted.**
- **PBS 782817** (`runs/sch/01_qc/20261109T100126Z__sch-9748284__01_qc__scqc-0a9d2ce`) `SEALED.txt` exit=0.
  - `COMPARISON_GRADED.txt`: "AS PREDICTED (1') - only F1's two keys, in all 10 call records".
  - `ISOLATED_GRADED.txt`: "IDENTICAL (4)". `UNMOUNT.txt`: MOUNTED, then RESTORED to the pre-mount digest.
- **PBS 782922** (`…20261109T112553Z__sch-b733c7e__01_qc__scqc-a2c8471`), sealed exit=0, the same grades.
  - "REFUSED BY NAME, before anything ran" for the control. "ALL READ-ONLY - the manifest and its 10 parts".
- **Predictions were written before submission.** Job 31: mtime 09:59:56Z, run key 10:01:26Z. Job 33: 11:22:20Z, run key
  11:25:53Z (the `<COHORTS>/SAMBO` copies).
- **The runs represent main.** `git diff b733c7e 7ca2515` changes no file in `sch/services`, `sch/kernel.py`, `sch/stack`
  or `plugins/single-cell/qc@scqc`. scQC's pipeline code is identical from `0a9d2ce` (and `a2c8471`) to `98504bd`.

**Stage 2 through the harness: counted.**
- **PBS 783280** (`runs/sch/02_annotate/20261109T134840Z__sch-88ba42d__02_annotate__scanno-d0ee926`) and **PBS 783363**
  (`…20261109T154529Z__sch-f640455__…`), both `SEALED.txt` exit=0.
  - `ISOLATED_GRADED.txt`: "IDENTICAL (1) - through the harness, scAnno gives exactly what it gives alone at the same
    commit: 1,420 obs columns over 30 objects, impact.csv and rescue.json".
  - The no-assay control is "REFUSED BY THE ADAPTER, naming the assay". The mount is MOUNTED and RESTORED.
- **Predictions were written before submission.** Job 28 (md5 `6f97f510`): mtime 13:44:21Z, qtime 13:48:40Z. Job 28b
  (`f1a8f0de`): 15:26:27Z, qtime 15:45:30Z (`qstat -x -f`).
- **The runs represent main.** `f640455` is merged as `b26b643`, and nothing in the runtime moved after it.

**What fails.**
- **Stages 3 and 4.** `plugins/single-cell/` holds only `qc@scqc` and `anno@scanno` (GAP-001).
- **C46.** `~/projects/BrainOrganoid_C46/runs/` holds `measure/` and `scqc/` only. C46's stage 1 (PBS 720932,
  promoted 2026-11-09) ran through scQC alone.
- **Limit.** Stage 2 read the promoted stage-2 tree (`reads_from=results/02_annotate/clustered`), not stage 1's
  harness output. The stages are not chained (GAP-001 driver, GAP-002 design sheet).

### A1.2: 0.500 (5/10), PARTIAL
| step | mapped to, and does it run in A1.1? | counts |
|---|---|---|
| 1 alignment, cell call | upstream by GOALS G1 ("Step 1 output ... is an accepted input") | 1 |
| 2 ambient removal | stage 1's inputs are `results/00_prealign/objects/*_cellbender_*.h5ad`, made outside the family (782922 `READONLY.txt`); CellBender cannot run inside scQC (783151 M1 FAILS in both environments; GAP-C49) | 0 |
| 3 QC, 4 doublets | scQC via qc@scqc (criteria `fail_umi_floor`…`fail_doublet` in 783151's comparison; 782922 mounted) | 2 |
| 5 normalisation, features; 7 clustering, annotation | `scanno cluster` (normalize_total/log1p when given counts, HVG, PCA, neighbours, leiden; `scanno/cluster.py:108-153`) and annotate/rescue via anno@scanno (783363) | 2 |
| 6 integration; 8 DA/DE; 9 pathways, trajectories; 10 advanced | no adapter for scIntegrate or scProfile; no pathway plugin; trajectories never run | 0 |

No document maps the steps. The mapping above is this pass's measurement.

### A1.3: 0.400 (2/5), PARTIAL
**scQC holds.** PBS 783151, `runs/scqc/01_qc/20261109T123625Z__scqc-98504bd__01_qc__envbuild-fix`, at main
`98504bd`, `SEALED.txt` exit=0. Its `VERDICT.txt`:
- "P1 HELD: installer exit 0; core: python 3.12.12 (pinned 3.12.12); 55 of 55 pinned versions installed | cellbender:
  python 3.10.22 … 165 of 165";
- the R doublet stack is checked as R reports it;
- "P2 HELD: 46 passed, 0 failed, 1 skipped";
- "P3 HELD: IDENTICAL";
- "VERDICT: AS PREDICTED (P1, P2, P3, B1)".

**scProfile holds.** PBS 782609, `…04_profile__envbuild` at `27e254f`: "P1 HELD … 161 locked versions … P2 HELD: 7 passed,
0 failed". From `27e254f` to `f5175ea`, `setup/` changes in comment lines only, and `scprofile/lock.py` and `cli.py` in
docstrings and help text only.

**Three fail.**
- **scAnno and scIntegrate.** No fresh-prefix build on PBS: `runs/scanno` and `runs/scintegrate` hold no envbuild run.
- **The harness** has no installer and no lock for its `single-cell` extra. On a fresh venv its suite is red (GAP-127):
  - 804 tests, 22 errors without the extra (tests that import numpy do not skip);
  - 1 error with the extra (anndata 0.13.4: `KeyError 'structure'`, GAP-C64).

### A2.1: 0.500 (2/4), PARTIAL
| stage | reproduction, read on the cluster | counts |
|---|---|---|
| 1 | 782817 and 782922 graded "as promoted": AS PREDICTED (1') against `results/01_qc` (117 tables in both; kept 100,713). The UMAP spread is declared before the run | 1 |
| 2 | **783148**: `SEALED.txt` exit=0; `COMPARISON.txt` "BRANCH: B1 …", G1–G4 identical against `results/02_annotate` (PBS 664864), 0 untraced | 1 |
| 3 | **783282** (W025 job 30, against promoted `713d918`): `FAILED.txt` exit=1. "lisi: BROKEN - none: iLISI 0.30806 vs 0.30615 … (predicted within 1e-3)". Reported: harmony ARI 0.650 vs 0.860. This follows 782882's broken named spread. Round 2 (PBS 784233) is running | 0 |
| 4 | `~/projects/SAMBO/results/` has no `04_profile` | 0 |

The run also carries the tool's own `SEALED.txt` (exit=0) beside the job's `FAILED.txt`, and its files are `-rw-------`:
GAP-112's class again.

### A2.2: 0.125 (1/8), PARTIAL
| repository | draw: TRUE / FALSE / IMPRECISE (lines walked) | known-false lines still false |
|---|---|---|
| harness `7ca2515` | 10 / **2** / 0 (21) | **6** of 6 |
| scQC `98504bd` | 8 / **3** / 1 (14) | **3** of 3 |
| scAnno `68233f0` | 10 / **1** / 1 (41) | **1** of 1 |
| scIntegrate `9a2d7d1` | 10 / **2** / 0 (18) | **1** of 1 |
| scProfile `f5175ea` | 10 / 0 / 2 (20) | **3** of 3 |
| Lab `51a00fa` | 10 / **1** / 1 (16) | **2** of 2 (one is also the drawn FALSE) |
| Studio `1d591f9` | 11 / 0 / 1 (20) | **1** of 2 (`Methods.tsx` "tested with DESeq2" REMOVED, :164-170) |
| Service `997d132` | 11 / 0 / 1 (15) | none known |

**The new FALSE lines.** They are listed in GAP-129, plus GAP-119 (scQC `WORKFLOW.md:127`, which hides a code defect)
and GAP-128 (scIntegrate `METHODS.md:252`, which also hides one).

**The score counts a repository only when no checked claim is false**, whether it came from the draw or from the
re-check. A re-checked known-false line is a claim this pass checked and found false. By the draw alone the score would
be 3/8 (scProfile, Studio, Service). This pass does not use that reading, because scProfile keeps three false lines and
Studio one.

### A2.3: 0.000 (0/4), FAIL
- **No attempt.** A grep of `autodev/waves/`, `waves.tsv`, STATE.md and both cohorts' RUNLOGs finds none.
- **ADR-0026's "cold replay" is not one.** It replayed maker edits; it did not reproduce a sealed stage run.
- **A cold reproducer would first meet a red harness suite** (GAP-127).

### A3.1: 0.125, PARTIAL
**First half: 2/8.** SAMBO stages 1 and 2 ran through A1.1. C46 has none.

**Second half: 0/5.** The full leak guard was used: both cohorts' generated term lists and both cohorts' generated
shapes. Rule 1(a) names site strings, and the shapes' bare job ids are taken from the cohort's own records.

| repository | term hits (files) | with shapes | fixture tier |
|---|---|---|---|
| harness | **0** | **74 hits on 37 lines**: bare PBS ids in `sch/dev/*.py`, tests, docs and README; `-q` queues in 8 `jobs/*.pbs` (GAP-C66) | `sch init` + `stack --dump` only |
| scQC | 234 (43) | 236 | `describe` only (GAP-023) |
| scAnno | 36 (13) | 38 | `cluster` |
| scIntegrate | 12 (4) | 14 | `integrate` |
| scProfile | 204 (42) | 395 | `run` with `--organism human --assay cell` pinned, and a refusal accepted |
| Lab / Studio / Service (amplifier) | 25 / 37 / 62 | the same | — |

- **Genuine first-cohort numbers sit in every tool.**
  - scQC `CALIBRATION.md:11`: "305,425 droplets analysed, 244,968". 305,425 is the stack 782922 measured.
  - scIntegrate `KNOWN_ISSUES.md:141`: the promoted harmony total 0.6868.
  - scProfile: "7,374 to 11,985 cells", the per-library kept counts of PBS 783151.
- **There are also false positives** (GAP-121), so part of each count is the generator's.
- **Lab and Studio scripts** hard-code a Windows user profile path (21 and 23 lines; GAP-120).

### A3.2: 0.250 (1/4), PARTIAL
At scProfile main `f5175ea`:
- **One factor at n = 2 per arm: handled.** The planner runs; DE fits `~ term`.
- **Two-factor factorial with interaction: not counted.**
  - DE adds the term (`kernels/de.py:1367-1376`), but its declared `cannot_show` says "the interaction term itself is not
    contrasted, so no gene here is evidence for or against one".
  - `kernels/abundance.py` has a design-handling defect (GAP-040).
  - No plugin refuses the design by name.
- **Covariates: not counted.** Every term in `use` is contrasted as a factor (`de.py:1361-1394`). Nothing models a
  covariate or refuses one by name (GAP-040).
- **Contrasts: not SAMBO's.** They are sorted: `levels = sorted(...)`, contrast `levels[-1]` vs `levels[0]`
  (`de.py:1394-1411`). That gives "young vs aged" and "chow vs HFD", the reverse of slide 15's "Aged vs Young",
  "HFD vs Chow" (GAP-039).

**Context, not credit.** The Service's request now captures a factorial with interaction and covariates (GAP-P03,
closed), but no resolver consumes it.

### A3.3: 0.800 (4/5), PARTIAL
| tool | evidence | counts |
|---|---|---|
| scQC | `modules/01_ambient/ambient.py:59` `DENOISE = {"snrna": True, "scrna": False}`; `05_quality/quality.py:92` `FLOOR_METHOD = {"snrna": "valley", "scrna": "declared"}` with declared cell floors `:95`; `engine/steps.py:1476-1481` refuses when no assay reaches the step | 1 |
| scAnno | `scanno/assay.py:29-31` "NO DEFAULT. An absent or unrecognised assay raises"; `--assay` `required=True` (`cli.py:2501`, `:2585`) | 1 |
| scIntegrate | `scintegrate/axes.py:27-31,68` `ASSAY_RULES = {}` declared; `--assay` optional and recorded as "not declared" (`cli.py:1145-1148`) | 1 |
| harness | `plugins/single-cell/qc@scqc/run.py:115-128` and anno@scanno (`run.py:21,208`) refuse a stack that declares no assay; PBS 783363 `CONTROL.txt` "REFUSED BY THE ADAPTER, naming the assay" | 1 |
| scProfile | `scprofile/inputs.py:275-307`: the assay "changes the CAVEATS, never the code path"; `--assay` takes free text and reasons only on `cell`/`nucleus` (`cli.py:4330`), so the family's `snrna` is "unrecognised"; cellchat's static caveat list speaks of nuclei for every cohort (`kernels/cellchat.py:1350-1352`) (GAP-050, GAP-C51) | 0 |

### A3.4: 0.050, PARTIAL
**The literal formula: 100,713 cells × 2 stages = 201,426 cell-stages, of 4,000,000.**
- **Stage 1** (PBS 782922, queue `long`): "mounted 100713 of 305425".
- **Stage 2** (PBS 783363, queue `short`): "the stack 100,713". It used 11 min 9 s and 10.2 GB (`resources_used.mem`
  10,223,604 kb).
- **The cell count used.** These are cells after QC. The 305,425 that entered stage 1 are droplets, not cells, so they
  are not counted.

**No cohort of 1,000,000 cells has run.** The lupus atlas was chosen (W027); W031 is registered (GAP-016).

**This differs from the coordinator.** Its 0 in `scores.tsv` reads the formula as "a 1M-cell cohort only". The formula
as written does not say that, so this pass applies it literally. If that reading is intended, the formula should say so;
it is (C). The other reading moves the mean by 0.0025.

### A4.1: 0.000 (0/9), FAIL
- **1 of 9 is in the maker's layout.** `sch catalogue` reads FORMAT `maker` for cellchat. The other 8 are `one-file`,
  with "`wraps.plots_unreviewed` is set".
- **No grading on the cluster.** The newest dev-suite run is `runs/sch/00_devsuite/20261002T081440Z__sch-b2e79db__00_devsuite`.
- **`sch conform` fails on scProfile.** S1 is red under the generated lists: 204 hits, 6 of them in
  `kernels/cellchat.py`, all database statistics (GAP-121).
- **`jobs/dev_suite.pbs` on main does grade every maker-output plugin** (`:229-262`, `rules.maker_output`; W019,
  GAP-C44). GAP-C81, registered at 04:41Z, misstates this and is closed in `gaps_0004.tsv`.

### A4.2: 0.000 (0/5), FAIL
No rule for drawing tools from the scRNA-tools catalogue, and no conversion of a never-seen tool. A `git grep` of the
harness and `autodev/waves` finds the catalogue only in GOALS.md (GAP-046).

### A4.3: 0.333 (3/9), PARTIAL
`sch catalogue --json` over scProfile `f5175ea`, field `provenance`:
- **A cited source:** all 9 cite a peer-reviewed paper (for example de: "Muzellec et al., Bioinformatics 2023 (PyDESeq2);
  Love et al., Genome Biol 2014 (DESeq2)").
- **A DOI:** `doi` reads "not declared" in all 9.
- **An exact pinned version:** 3 of 9.
  - cellchat `75253cd0c9e68410e6e721a6d3a0419a1d7e358f`;
  - scenic `pyscenic 0.12.1`;
  - velocity `scvelo 0.3.4`.

  The other six read "not declared", although scProfile's environment lock pins every package. The plugin does not name
  the pin (GAP-045).

### A4.4: 0.500 (2/4), PARTIAL
**The probe.** A cold agent with only the skills, `sch` and a synthetic fixture was given a question the auditor stated
before it started: "which cell types change in their share of cells between the two conditions?"
- **List: done.** `sch catalogue list --scprofile …` gave "23 plugin(s) from 2 source(s)".
- **Pick: done.** It picked scprofile:abundance, a correct choice, from `catalogue show`.
- **Run: failed.** All three attempts died with an uncaught traceback (`sch plan scprofile:abundance` →
  `ManifestError: plugin 'scprofile:abundance' not found …`; reproduced here, `logs/a44_plan.out`). A fallback to the
  harness's own composition probe also died: by name it is a traceback on the profile, and by path it ran on the wrong
  profile and died (GAP-123; reproduced here).
- **Read: failed.** No plugin produced a result, so there was nothing to read and no answer.
- The skill says the run would fail (`skills/harness-agent/SKILL.md:39-41`); the CLI never does (GAP-122).

### A5.1: 0.923 (12/13), PARTIAL
**The evidence: the writing run of the CellChat arc.**
- PBS 711781, `runs/scprofile/04_profile/20260915T051032Z__scprofile-c1e92c2__04_profile__written`. `SEALED.txt` exit=0:
  "VERDICT: 3 of 3 predictions held".
- Its `incoming/kernels/cellchat/PAPER_CLAIMS.cellchat.jsonl` holds **13 `"kind": "claim"` records**. The reviews by
  `"reviewer": "reviewer"`, separate from the writer, are **12 "standing", 1 "narrowed", 0 "withdrawn"**.
- Every claim cites a figure: `scprofile/paper.py:167` refuses a claim with none.

**Scoring.** A narrowed claim did not survive as written, so it is not counted.

**The generator on main is the one that ran.** `c1e92c2` is an ancestor of `f5175ea`, and `scprofile/paper.py` is
unchanged between them.

**Limits.**
- **CellChat only.** DE and abundance get no composed section (GAP-047).
- **A withdrawn claim's sentence would still print** (GAP-048). It mattered nowhere here, because none was withdrawn.
- **The reviewed run is no longer pristine.** It holds Jupyter checkpoints written 2026-11-05 (GAP-126).

### A5.2: 0.000, FAIL
`grep` of harness `7ca2515` and scProfile `f5175ea` finds no hypothesis record, no falsifying-test field and no
plan-from-hypothesis code (GAP-012). 0 hypotheses proposed and 0 follow-ups, so both halves are 0.

### A6.1: 0.000 (0/5), FAIL
The harness has no `http.server`, `flask`, `fastapi`, `aiohttp` or `websocket` import, and no tracked `.html`, `.ts`,
`.tsx` or `.js` file (GAP-013).

### A6.2: 0.000 (0/2), FAIL
- **Part 2 (Studio shows the run): 0.** `git grep -i "run card\|meta.run"` over Studio `src` at `1d591f9` finds nothing.
  Lab main has no `meta.run` either (W017 and W028 are held). scIntegrate `emit.py:138` keeps only `uns['scintegrate']`
  (GAP-P20).
- **Part 1 (the family's final object opens in Studio through Lab): UNKNOWN, so no credit.**
  - Lab's CLI converts W005's fixture "shaped like a family object … in scIntegrate's layout": `npm test` 406 ok here.
  - Opening it in Studio is the W008 verifier's ledger claim.
  - The family's own final object (SAMBO's `results/03_integrate`) has never been put through. Transferring it is
    outside this pass's read-only cluster rule.

### A6.3: 0.667 (2/3), PARTIAL
- **Part 1, delivery to request: 1.** Service main `997d132`, `npm test`: 7 scripts, 338 ok, rc 0.
  - "Cell Ranger, flat / under outs/ / h5 files only -> cellranger" and "CeleScope … -> celescope".
  - The request is written with "no network call", and so are scQC's samplesheet, registry row and design.csv
    ("byte for byte").
  - `src/lib/scSheets.ts:1-26` refuses rather than writes a sheet it cannot write truly. A blank doublet rate becomes
    scQC's `--dbr` at run time: a run parameter, not a hand edit.
- **Part 2, the request runs as A1.1's input: 0.** No harness intake reads a Service request: no `scRequest`,
  `request.json` or intake in `sch/`, `skills/` or `plugins/` (GAP-P06).
- **Part 3, the bulk path: 1.** "THE BULK REQUEST IS UNCHANGED … writes a42b747's request byte for byte (sha256
  4545ba5752ec…)".

### A7.1: 0.000 (0/5), FAIL
- **No attempt.** No cold agent has run A1.1 on a held-out cohort.
- **No skill for it.** `skills/` holds harness-agent, harness-developer and plugin-maker; none runs a cohort across
  stages, and harness-agent does not mention anno@scanno (GAP-003).
- **Not possible yet.** Stages 3-4 have no adapter (GAP-001).
- **The cluster checkouts are on unmerged branches**, so a cold agent submitting now would run them:
  - `~/tools/single-cell-harness` on W029 `006b72c`;
  - `~/tools/scProfile` on W013 `b39ca4a`;
  - `~/tools/scIntegrate` on W025 `b148030`.

---

## 4. The closures claimed since pass 0003, re-checked (29 rows): all hold

| rows | re-check |
|---|---|
| W014: GAP-018, C05, C31 | `conf/env/install_cellbender.sh:41` and `cellbender.lock.txt` pin torch 2.5.1, numpy 1.26.4, cellbender 0.3.2; `requirements.lock.txt:50` pyarrow; `build_reference.sh:43-67` requires all three with no default; PBS 783151 P1/P2 HELD |
| W019: GAP-C39, C40, C41, C42, C43, C44 | each has its test, and the suite passes them; `jobs/dev_suite.pbs:229-262`. **C41 in part:** its h5ad shape fingerprint errors under anndata 0.13 (the one red test; GAP-C64, in a wave) |
| PI: GAP-102, GAP-113 | decision 0b (STATE "Decided"); C46 `stages/01_qc/RUNLOG.md` "a note on files outside this record" (2026-11-09T15:40:14Z) |
| PI (Service): GAP-P01, P02, P03, P04, C34 | 338 ok, including the single-cell delivery, request and design tests and "C34's own scenario" |
| PI (Lab): GAP-P09, P11, P13, P16 | 406 ok: the CLI, "DESIGN FACTORS ARE TOLD BY WHAT THEY ARE", nullable strings scan, the fixed zip mtime (`src/lib/build.ts:38`) |
| PI (Studio): GAP-P22, P23, P12 | 1,621 ok; `Methods.tsx:164-170` "No test was run here"; README.md:151 lists direct `.h5ad`/`.rds` as an unchecked box, :184 the measured bundle; the sentinel tests pass |
| W021: GAP-028 | `scanno/markers.py`, `build-markers`, `tree propose` (`cli.py:556-564`, `:2375`); `tests/test_build_markers.py` 31 checks ok here, 1 needs scanpy (not installed here) |
| W024: GAP-008, C46, 101, 110, C38, 111 | the generated lists hold levels and the shapes hold queues; S1 reads every git-listed file; a missing or empty `--terms` list is refused with exit 2 (both reproduced); the harness's S1 is ok with the five record paths excused; `test_the_ladder_reads_every_status_a_command_writes` passes; `test_conform_doctor` passes on a clone with `core.hooksPath` unset. **The suite is still red on a fresh clone for other reasons** (GAP-127) |

None is re-opened.

## 5. The register's changes (`gaps_0004.tsv`: 12 rows)

### New (11)
| id | size | gap |
|---|---|---|
| **GAP-119** | S | **scQC's step-7 removal audit is a gate in name only.** `verdict()` returns FAIL, while `pipeline.gate` stops only on REFUSE, and `enforce()` has no caller |
| **GAP-120** | M | **The amplifier of GAP-C75 and C78.** Under the generated lists S1 is also red in scAnno (36) and scIntegrate (12), and Lab and Studio scripts hard-code a user profile path |
| GAP-121 | S | **The generated lists' false positives:** the stem 'Mut' matches CSS `--mut`, 'WT' matches wild-type wording, and CellChatDB statistics count as cohort numbers |
| GAP-122 | S | Catalogue IDs `scprofile:` are refused by every `sch` verb with a Python traceback, not by name |
| GAP-123 | S | A stack's profile is not enforced by path (`sch ask <path>`) or at `init --profile table` |
| GAP-124 | S | PBS 783282 has no stage-3 RUNLOG entry of its own |
| GAP-125 | S | Nine extra scProfile directories under `~/tools` (six without a repository; LAYOUT §6 check 2) |
| GAP-126 | S | Jupyter checkpoints inside two sealed stage-4 runs (2026-11-05), and 712314's files are writable |
| GAP-127 | S | The harness has no environment of its own, and its suite is red on a fresh venv (22 errors, or 1 with the extra) |
| **GAP-128** | S | **scIntegrate fits every method on a PCA that includes the withheld cells** when the input carries `X_pca`; the docs say they are not in it |
| GAP-129 | S | Draw 0004's seven further false doc lines (harness 2, scQC 2, scAnno 1, scIntegrate 1, plus the two code defects above) |

### Closed (1)
- **GAP-C81** (registered 04:41:50Z): not reproduced at main. `jobs/dev_suite.pbs` grades every maker-output plugin
  (W019, GAP-C44).

### Still open, re-checked this pass (no row: status unchanged)
- **XL/L:** GAP-001 (two of four adapters), -002, -012, -013, -016 (in a wave), -043, -044 (in a wave), -047, -056.
- **M:** GAP-003, -015, -040 (in a wave), -045, -048, -050, -055, -107 (now scAnno and scIntegrate only), -P05 (in a
  wave), -P06, -P19 (in a wave), -P20, -C49, -C75, -C78.
- **S, with new evidence:**
  - GAP-112: PBS 783282 is writable and holds two seals; 712314 is writable.
  - GAP-104: Lab now also fails S1.
  - GAP-C26, -C51, -C56: catalogue rows still read COHORT RUN "unknown" for qc@scqc and anno@scanno.
  - GAP-C64, -C66: 37 lines, unchanged at `f3f0de8`.
  - GAP-009, -052, -115, -116, -117, -109, -P17: their known-false lines stand.

## 6. The amplifier, class by class

| class (found in) | checked in the other repositories | result |
|---|---|---|
| a gate whose verdict word its caller never stops on (scQC step 7) | grep of `== "REFUSE"`/`"FAIL"` gating in all five Python repositories | scQC's other four gates emit REFUSE. The harness validates verdicts (`sch/services/gate.py:18-26`, `:79-81`). scAnno, scIntegrate and scProfile have no string-verdict gate. **scQC only** |
| cohort strings under the generated lists (scProfile, GAP-C75) | S1 on all eight | **red in 7 of 8**; the harness is clean on terms and red on shapes |
| a user home path in code | the same scan | **Lab 21, Studio 23** (scripts); 0 in the five Python repositories |
| a run left writable, or with two seals (stage 3, GAP-112) | the recent runs of every tool, plus the stage-4 deliverables | W020, W013 and W029 runs of 2026-11-10 are `-r--------` with one seal. **783282 (stage 3) and 712314 (stage 4) are writable**; 783282 has two seals |
| entries a sealed run did not write (LAYOUT §3.4) | the two stage-4 runs read | **both**: Jupyter, 2026-11-05 (GAP-126) |
| a CLI failure as a traceback, not a refusal (harness `plan`/`ask`) | the tools | **not measured**: their CLIs need scanpy and R stacks this venv lacks |
| a false doc line | the draw in all eight | 7 of 8 have at least one (A2.2) |
| a graded job with no RUNLOG entry (783282) | every PBS job of 2026-11-09/10 against its stage RUNLOG | 783282 only. Today's 783991, 783992, 784088, 784130 and 784233 are recorded |

## 7. What moved since pass 0003, and why

Pass 0003 had no scores; its labels were 0 PASS, 9 PARTIAL, 11 FAIL. Applying today's formulas to 0003's evidence gives,
roughly: A1.1 1/8, A1.2 3/10, A1.3 1/5, A6.3 0/3 and A3.1 0.0625. That is a mean near 0.2.

| test | moved | why |
|---|---|---|
| A1.1 | 1/8 → **2/8** | W026 merged: stage 2 through anno@scanno (PBS 783280, 783363) |
| A1.2 | 3/10 → **5/10** | steps 5 and 7 now run inside A1.1 (W026) |
| A1.3 | 1/5 → **2/5** | W014 merged: scQC's environments from main on a fresh prefix (PBS 783151) |
| A3.1 | 0.0625 → **0.125**, FAIL → PARTIAL | the cohort half gains stage 2. The tool half stays 0: W024's generated lists show that all four tools carry cohort strings the old lists missed (truer, not a regression) |
| A6.3 | 0/3 → **2/3**, FAIL → PARTIAL | W009 + W015 deployed by the PI; the bulk path unchanged |
| A3.4 | FAIL → PARTIAL (0.050) | a reading, not progress: the literal formula credits SAMBO's two stages |
| A2.2 | FAIL → PARTIAL (0.125) | the formula, not progress: Service alone is clean, as it was in 0003 |
| A3.3 | PARTIAL, now 4/5 | scored against the fixed five, the harness counts: both adapters refuse a missing assay (W010, W026) |
| A4.4, A5.1, A4.3, A2.1, A3.2 | PARTIAL, now scored | no main that grades them moved. A4.4 was re-measured with a fresh cold agent, A5.1 from the run's own ledger |
| A2.3, A4.1, A4.2, A5.2, A6.1, A6.2, A7.1 | FAIL, 0 | nothing that grades them merged |

## 8. Readings, and what could not be measured

- **A3.4.** The literal formula is used (0.050). The coordinator's reading would give 0.
- **A2.2.** The known-false re-checks count as checked claims (1/8). The draw alone would give 3/8.
- **A3.1.** The full guard is used: terms and shapes. With terms only the harness passes S1. Its fixture tier still stops
  at `init`, so the score is the same.
- **A6.2 part 1: UNKNOWN.** The family's own final object would have to be transferred, which this pass's cluster rule
  forbids. It earns no credit.
- **A5.1.** A narrowed claim is counted as not surviving.
- **The amplifier for CLI tracebacks in the four tools was not run** (their dependency stacks are not installed here).
- **Cluster connections: 3 of 5 used.** A reproduction or a fresh environment build needs `qsub`, which this pass may not
  do, so A1.3's missing tools and A2.3 are measured as "never done", not tried.

## 9. The five gaps whose closing moves the mean most

1. **The eight through the maker, onto the cluster ladder, with scProfile's S1 green.**
   - GAP-044 with GAP-039, -040, -041, C72–C76, C79 and C80.
   - Moves A4.1 (up to +1.0), A3.2 (+0.5 to 0.75) and A4.3 (+0.67, the pins named at migration). **About +0.11.**
2. **Adapters for scIntegrate and scProfile, a stage driver and one design sheet** (GAP-001, -002, GAP-122).
   - Moves A1.1 (+0.25 on SAMBO), A1.2 (+0.3), A4.4 (+0.5), A6.3 part 2 (+0.33), A3.1, A3.4 and A6.2.
   - Unblocks A7.1. **About +0.08.**
3. **The three zero tests that need a new component:** GAP-012 (co-scientist, A5.2), GAP-013 (UI, A6.1) and GAP-003 (a
   cohort-run skill, A7.1, after item 2). **+0.05 each.**
4. **The false documentation in seven repositories** (GAP-129, -119, -128, -009, -052, -115 to -117, -109, -P17).
   - Moves A2.2 (+0.875). **About +0.044.**
5. **C46 stages 2-4 through the family** (GAP-056).
   - Moves A1.1 (+0.5), A3.1 (+0.25) and gives A7.1 its held-out cohort. **About +0.04, and more with A7.1.**

## 10. Records corrections for the coordinator

- **GAP-C81 misstates main** (`jobs/dev_suite.pbs:229-262`); it is closed in `gaps_0004.tsv`.
- **`scores.tsv`'s coordinator row for A3.4** (0) uses a narrower reading than GOALS.md's formula. Restate the formula if
  that reading is meant.
- **Three cluster checkouts are on unmerged branches** (harness `006b72c`, scProfile `b39ca4a`, scIntegrate `b148030`).
  A cohort run started now would get unmerged code for three of five.
- **`autodev/STATE.md` says "3 of 20 measured by the coordinator"**; this pass measures all 20.
