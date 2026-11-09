# ADR-0027: the second cohort - a held-out dataset that differs from SAMBO on every axis, used to find what the family only does right because SAMBO happened to be SAMBO

**Date** 2026-10-02. **Follows** ADR-0026. **Status** accepted by the PI 2026-10-02, in
progress; the step record at the end says what has been done. **Displaces** the eight held-out
plugins (named as ADR-0027 by ADR-0026) to ADR-0028.

## Context

Every test, fixture, reproduction and promoted result in this family rests on one cohort.
SAMBO is mouse, Singleron/CeleScope, single-**nucleus**, heart, ten libraries, two factors
(age, diet), and it always arrived with its ambient correction already done. A defect whose
trigger is "the input is not SAMBO" has never had a chance to fire.

On 2026-10-02 the PI supplied a second cohort and asked for it to be used to upgrade the
harness: **BrainOrganoid_C46** (`~/projects/BrainOrganoid_C46/`). Human, 10x Genomics
Single Cell 3' v4, cellranger-8.0.1 against GRCh38-2020-A with introns counted, single-**cell**,
brain organoids, four libraries (`H9WT_1`, `H9WT_2`, `C46Mut_1`, `C46Mut_2`), one factor
(genotype, n=2 per arm), and Cell Ranger outs only: no FASTQ, no BAM, no `metrics_summary.csv`.
It differs from SAMBO on species, platform, assay, tissue, design and delivery shape at once.

Before anything was run, the four children and the harness were read for what this cohort will
do to them (three read-only passes against the GitHub tips: scQC 817e8c9, scAnno c4edaa9,
scIntegrate 722bc79, scProfile f294c89). **V** = re-read and confirmed by the coordinator in the
code; **A** = the reading pass's claim, not yet re-verified; **U** = the pass itself marked it
unconfirmed.

### What will be silently wrong

| id | where | what this cohort gets | why SAMBO never showed it | |
|---|---|---|---|---|
| Q1 | scQC `engine/graph.py:323-329`, `steps.py:1436-1438` | The `05_quality` task is built without `assay`, so the mito step's `task.params.get("assay", "snrna")` returns `snrna` whatever the samplesheet declares: the derived mito ceiling is clamped to the **nuclei** bound (5-10%) on whole cells, and the report says "DECLARED for assay snrna". `mito_bounds` and `mito_bound_declared_by` are read two lines later and **written nowhere in the repository** - a declared bound cannot be supplied at all | SAMBO's value is the default. `tests/test_wiring.py:178` declares `snrna` too, so the test cannot tell a wire from a default | V |
| Q2 | scQC `modules/00_ingest/ingest.py:49` | `assay` is not in `REQUIRED`, against the module's own rule "Missing means fail, never a default" | every SAMBO row carried it | V |
| P1 | scProfile `kernels/de.py:1394-1411` | DE contrasts `sorted(levels)[-1]` vs `[0]`: here **WT vs Mut, with Mut the reference**, while the host's `control_for` resolves WT as control (`design_panel.py`, hint `wt`) and every comparison panel runs Mut vs WT. The `contrast` column is labelled correctly, so the table reads right and disagrees in sign with the page it sits on. `--control` never reaches the plugin | whether it bit SAMBO depends on how its levels sort; nothing compares DE's direction with the host's | V |
| P2 | scProfile `kernels/abundance.py:1525` | scCODA `formula=term` with default treatment coding: alphabetical baseline (Mut) | as P1 | A/U |
| N1 | scAnno `classify.py:111-133`, `cli.py:2120-2134` | The tree walk scores the relative gap between siblings with no absolute floor, and `--resolve` forces every unresolved cell to a leaf: a tree that does not fit (a carried-over heart tree) still labels every organoid cluster, and nothing refuses | SAMBO's tree fitted SAMBO | A |
| N2 | scAnno `cli.py:632-646`, `corpus.py:48-80` | The species string is an SQL filter, never checked against the data; symbols are upper-cased on both sides, so `--species Mouse` on human genes clears the gene floor and scores with mouse markers | one species | A |
| P3 | scProfile `scprofile/inputs.py:212-237` | A declared `--organism` is taken as declared, never checked; detection reads the first 5,000 `var_names` only and ignores `var["gene_ids"]`, whose ENSG/ENSMUSG prefix names the species outright. decoupler then returns "a small, plausible table" on the wrong species (`decoupler.py:340-342`) | one species | A |
| P4 | scProfile `cli.py:1864, 1996-2030` | The plan prints "BELOW 3 PER GROUP: compositional and pseudobulk tests refuse" while de and abundance run at n=2 (`min_samples_per_level=2`) | ten libraries | A |
| Q5 | scQC `graph.py:198-199` vs `adapters/cellbender.py:486-491` | The graph expects `<s>_cellbender_cell_barcodes.csv`, CellBender writes `<s>_ambient_cell_barcodes.csv`; the cross-check is skipped without a word | SAMBO's ambient was supplied, so this path never ran | A |
| Q6 | scQC `steps.py:243-259`, `ambient.py:54,120-130` | `plan_ambient` - the declared-vs-measured intronic check - is never called on the run path | as Q5 | A |
| T1 | scQC report, scIntegrate wording, scProfile `evidence.py:65`, `units.py:117`, `cellchat.py:1320,1350` | "nuclei", "per nucleus", "animal", and cellchat's nuclei-specific `cannot_show`, printed on a whole-cell cohort of cell-line differentiations | true of SAMBO | A |

### What will refuse, which is the good case

scQC refuses `homo_sapiens/GRCh38-2020-A` at ingest (the registry holds one mouse example row;
**V**); a CellBender-native h5 is probably opened with `read_h5ad` at step 5 after the GPU hours
are spent (**U**); the UMI/gene floor bounds (200-1000 / 100-600) come from SAMBO's nucleus
valleys and a whole-cell valley probably lies above them (**U**); the cell-call gate was
calibrated on CeleScope's ratio (**U**); ingest reads 2.0-2.3 M x 36,601 at 1 cpu / 8 GB (**U**).
scAnno ships no human brain tree or corpus (by design: the tree is the project's). scProfile's
velocity is runnable at plan time and refuses at run time; cellchat refuses only at 0% database
coverage. scenic needs hg38 cisTarget files.

### What the harness could not have caught

- **The fixture varies names, never values (V).** Both shapes are one build with columns renamed
  (`sch/dev/fixture.py:47-65`); both carry human-cased `MT-` genes (`:104-105`, `:380`), called
  cells only, no empty droplets, no MEX/h5 layout, no assay, species or platform. Code that
  hard-codes `MT-` passes both shapes; code that hard-codes `snrna` passes both shapes.
- **The profile has no slot for the axes (V).** `sch/profile/single-cell.yml` keys are
  `label, sample, batch, counts, lognorm, embedding, compartment`; `assay` appears only as a
  forbidden kernel term.
- **No scan looks for a declared field read with a literal default** - the exact shape of Q1 -
  and scQC's fixture tier runs `describe`, not the pipeline (scQC `DEVPOINTS.yaml:17-18, 54`), so
  no wiring defect can fail it (A).
- **The cluster's tool checkouts do not say what they are (V, 2026-10-02).** All five `HEAD.txt`
  differ from their checkouts (scQC `deeb9cc` vs `b8cd517`, scAnno `d9e3bcd` vs `1741ca2`,
  scIntegrate `14ad5e2` vs `1b47c3b`, scProfile `d933b13` vs `f294c89`, harness `bba4de5` vs
  `69da4de`); three checkouts are behind GitHub; five `sch_dev_suite.o*` PBS logs sit inside
  `~/tools/single-cell-harness`, written there by a job whose `-o` was not its run directory.

**The common cause.** Q1 and Q2 hid behind a default that equals SAMBO's value; Q5 and Q6 behind
a path SAMBO never took; P1, N1, N2 and P3 behind a single species, a fitting tree and a factor
nobody compared across tools. None is a SAMBO name inside a tool - the leak guard is clean - and
every one is an overfit to SAMBO all the same. **An overfit that names nothing is invisible to a
name scan; only a second value on the axis shows it.**

## Decision

Use BrainOrganoid_C46 as the family's first held-out cohort, and upgrade the harness so that
each axis it exposed becomes a test - not a fix made once for this dataset. Nothing from the
cohort enters any tool; the standing acceptance rule for child changes holds unchanged (own
suite green, leak guard clean, a synthetic fixture entering the real CLI path, a pre-declared
PBS reproduction against SAMBO's promoted runs).

0. **Hygiene, before any run key is minted.** Refresh the five checkouts to their GitHub tips
   (after `qstat` shows nothing of ours using them), regenerate every `HEAD.txt`, move the five
   stray logs into the run that wrote them, and fix that job's `-o`.
1. **The fixture varies values (harness).** The two-shape fixture gains axes on which the shapes
   differ in VALUE, not name: mito/ribo case (species), assay, delivery layout (a raw droplet
   matrix with empties, as MEX and as 10x h5), and a design whose control level does **not**
   sort first. Regression rule: each axis ships with the defect it catches failing on it -
   Q1 against the assay axis, P1 against the direction axis - before that defect is fixed.
2. **Declared versus measured (harness).** The profile gains `species` and `assay` as declared
   keys, and a probe checks each against the data: species from `gene_ids` prefixes and
   mitochondrial symbol case, assay from the intronic fraction where it exists. A mismatch is a
   gate refusal carrying both values. This is one implementation, where today four tools each
   have none.
3. **A scan for declared fields with literal defaults** (`sch dev`), over all five repositories:
   `.get("<a declared field>", <literal>)` is a finding, the shape of Q1.
4. **The children, smallest blast radius first, each under the standing rule.** scQC Q1/Q2 (assay
   required and threaded; `mito_bounds` wired or removed) and the registry row semantics for a
   matrix-only reference; then Q5/Q6 and the never-run ambient path; scProfile P1/P2 (the
   resolved control reaches DE and abundance), P3, P4; scAnno N1/N2 (an absolute root fit, so
   "none of this tree" is an answer; species checked against the data); T1 last.
5. **Then the cohort, stage by stage**, each submission carrying its prediction in the `.pbs`
   before `qsub`, as every reproduction in this family has.

## Predictions, written before anything ran

| # | prediction | graded by |
|---|---|---|
| 1 | Q1+Q2 fixed reproduce SAMBO stage 1 **IDENTICAL** - SAMBO declares `snrna`, the value the default already gave | the scQC reproduction job |
| 2 | ~~P1 fixed changes SAMBO's DE only by sign, and only for factors whose control level sorts last; magnitudes and p-values identical~~ - **wrong as first written, corrected 2026-10-02 before any scProfile run.** SAMBO declares `--control age=young --control diet=chow` (its run's `report.json` `.controls`), and both controls sort last (`aged` < `young`; `HFD` < `chow` - uppercase first), so DE ran `young vs aged` and `chow vs HFD` against the run's own declared direction. With the interaction in the model a main-effect row is the simple effect at the OTHER factor's reference level, so moving both references changes what the rows are, not only their sign. Under treatment coding the old fit fixes the new one gene by gene: `age` (now aged vs young, within chow) = -(old `age` + old interaction); `diet` (now HFD vs chow, within young) = -(old `diet` + old interaction); the interaction coefficient IDENTICAL in value, renamed `age[T.aged]:diet[T.HFD]`; a population fitted without the interaction flips sign exactly, p-values identical | a base run (scProfile `f294c89`) and a branch run (`48aaeba`) of DE on SAMBO, compared gene by gene |
| 3 | The new fixture axes fail scQC on Q1 and scProfile on P1 **before** their fixes, and pass after | `sch dev check` on each child |
| 4 | scQC on the cohort, with Q1-Q3 fixed, stops next at the ambient run path (Q4/Q5) - the first time CellBender runs inside scQC | stage 01 on BrainOrganoid_C46 |
| 5 | The species/assay probe reads BrainOrganoid_C46 as human/cell and SAMBO as mouse/nucleus with no declaration needed | the probe's own suite, then both cohorts |

## Consequences

- **Easier:** the axes SAMBO fixed become things a check can vary. The next cohort - a third
  species, a 5' kit, a multiome - finds a fixture that already moves on the axes this one did.
- **Harder:** the ROADMAP says the four tools are not touched by its phases. This round touches
  all four, each by the per-change rule the September rounds used, and records it as a departure
  from the ROADMAP rather than as a phase.
- **Given up:** SAMBO stops being the only reference, and with it the comfort that "reproduces
  SAMBO" means "correct". Prediction 2 is a deliberate change to the sign convention of
  SAMBO's DE tables; the SAMBO stage-4 RUNLOG will need a line saying which direction each
  earlier run ran.
- **Not decided here:** what C46 is (an H9 derivative or another line - if another line,
  genotype is confounded with line and no stage can separate them), and what `_1`/`_2` are.
- **The annotation tree follows SAMBO (PI, 2026-10-02):** "follow sambo, i never give you any
  marker in sambo". The PI supplies no markers; the tree for this cohort is derived by the same
  procedure SAMBO's stage 2 used, read from SAMBO's own stage record before stage 2 here, and it
  stays project content.

## Step record

| step | date | what | result |
|---|---|---|---|
| 0 | 2026-10-02 | five stray `sch_dev_suite.o*` logs moved from `~/tools/single-cell-harness` into the five SAMBO `runs/sch/00_devsuite/<key>/logs/` they belong to (each matched by the run directory its log names) | harness checkout clean |
| 0 | 2026-10-02 | `jobs/dev_suite.pbs`: usage passes `-o "$RUNDIR/logs/"`, and the job `exec`s into `$RUNDIR/logs/driver.log` whatever the qsub line said | the cause, not just the five files |
| 0 | 2026-10-02 | the five checkouts fast-forwarded and `HEAD.txt` regenerated from `git rev-parse HEAD`: scQC b8cd517→817e8c9, scAnno 1741ca2→c4edaa9, scIntegrate 1b47c3b→722bc79, scProfile f294c89 and harness 69da4de unchanged; all five `HEAD.txt` equal their checkout, all worktrees clean. Root cause of the drift: no checkout has a post-merge hook, so `HEAD.txt` was only ever as fresh as the last person who remembered | compliance check 3 satisfied for the five |
| 3 | 2026-10-02 | `sch conform` S13 (`432a198`), done before step 1 because it is the cheapest: no cohort axis gets a literal default. The axes are the profile's (`single-cell.yml` `axes:`, `Profile.axes`); the scan reads the syntax tree for `.get/.setdefault/.pop("<axis>", lit)`, `getattr(x, "<axis>", lit)`, `add_argument("--<axis>", default=lit)` and axis-named parameters; `None`, `""` and booleans are absences, not findings. Prototyped across the five repositories before it was written into the harness: 27 raw hits, 8 once absences were excluded, all 8 real | **scQC fails** - `steps.py:1436` and three `assay="snrna"` parameters in `quality.py` (209, 556, 592), the fallbacks Q1's rewiring alone would have left live; **scAnno fails** - `--assay` defaults to `sc` in four subcommands (`cli.py` 2095, 2167, 2593, 2624), the mirror of Q1: a nuclei cohort silently read as cells; scIntegrate, scProfile and the harness pass. The regression test plants each of the four shapes and the three absences |
| 1 | 2026-10-02 | **The shapes differ in values, and a tier compares them.** `fixture.VALUES`: shape b's control is `untreated` (sorts LAST; shape a's `ctrl` sorts first) and its mitochondrial/ribosomal symbols are spelled `mt-Co1`, `Rps4x` (shape a `MT-CO1`, `RPS4X`); applied in `write()`, so the core and its digest - and every baseline, all recorded on shape a - do not move. The ladder fills `{control}`, `{mt_prefix}`, `{ribo_pattern}` beside the roles; `sch dev map --json` lists them. A `spelling` key makes a fixture written before this rebuild rather than be reused. **New tier `agree`** after `fixture_b`: fingerprints `run_a` and `run_b` with the baseline's own reader, reads shape b in shape a's words (repaired only where a name has no partner as written), compares lists as multisets, skips what the tool's baseline measured as unstable, and names a negated column as `SIGN FLIPPED` | 145 tests green on the workstation (8 skip without anndata, among them the written-shape test); measured on the five repositories by the next cluster ladder |
| 1+3 | 2026-10-02 | Measured on the cluster: dev suite PBS `719917.hn-10-03`, run `SAMBO/runs/sch/00_devsuite/20261002T081440Z__sch-b2e79db__00_devsuite`, both projects' word lists, prediction in `jobs/dev_suite.pbs` before submission. The harness's own ladder showed `unit` failing on the compute node, which the prediction did not name; the same suite at the cluster's exact versions (anndata 0.13.2, numpy 2.4.6, pandas 3.0.5) passes 593 of 593 on the workstation, so the failures are of the compute node, not of the code - named by kernel suite PBS `719922.hn-10-03` (`runs/sch/00_kernel/20261002T081736Z__sch-b2e79db__00_kernel`, unittest `-v`) | graded below |

### The first measurement, graded (PBS 719917 and 719922, 2026-10-02)

| predicted | observed | verdict |
|---|---|---|
| the three value invariants hold | b's control last, a's first, the same mito genes under each spelling; digests equal | **held** |
| contract fails for scQC and scAnno on S13 | it does - and for every repository on G1 as well (below) | **held**, with a cause not predicted |
| agree fails for scProfile/abundance (P2) | `ok`: the fixture run REFUSES on the fixture's confounded covariate, a declared refusal, so scCODA never ran and there was nothing to compare | **not measurable with this fixture command** - P2 stays a prediction |
| agree passes for scIntegrate and scAnno | both FAILED, on one field each: `STATUS*.json::products[*].bytes` | **wrong, and the defect was the tier's**: a byte count measures a file, and shape b's longer names make longer files. Fixed: `agree` skips sizes, as it skips opaque products; regression test |
| leak fails for the harness | it does: jobs/ and ADRs name the first cohort, ADR-0027 the second | **held** |
| (not predicted) | leak fails for **scProfile**: `tests/test_figure_audit.py`, `tests/test_the_compare_launches_share_the_pool.py` (`Aging1`), `tests/test_one_fact_many_phrasings.py`, `docs/ANATOMY_OF_A_RUN.md` (`sambo`) | **a real leak**, entered after the last clean run (2026-09-08); scProfile work in step 4 |
| (not predicted) | the harness's `unit` fails on the compute node: 4 failures, 1 error | **of the node, not the code**: two tests run `sch conform` on a clone with no `core.hooksPath` (G1); one needs `git`, which compute nodes lack; two ran the word `True` - `command: [true]` parses as a boolean, and only macOS's case-insensitive filesystem finds `/usr/bin/true`. Fixed: a boolean or null argv word is refused with the fix named (`convert.run_stage`), the tests quote it, the git test skips where there is no git, and the harness and scProfile clones on the cluster now carry `core.hooksPath` |
| (not predicted) | scAnno `baseline` fails: `clustered.h5ad` 9,850,736 -> 14,012,896 bytes | **pre-existing**: the fixture grew by exactly 2000 x 520 x 4 bytes, the `lognorm` layer ADR-0016 added after the baseline was recorded (2026-09-08); no ladder had run since to see it. Re-record in step 4 |
| (not predicted) | scProfile `unit`: 3 of 109 suites (`test_contract`, `test_the_cache_is_forecast_before_a_job` - no `git` on the node - and `test_the_hosts_panels_answer_the_eye`) | pre-existing on the node; not diagnosed in this step |
| (not predicted) | G1 fails on every cluster clone; scQC, scAnno and scIntegrate ship no `setup/githooks/pre-commit` at all | the three have no commit gate - a finding for step 4 |

**What the measurement says about the round's premise.** The ladder had not run since 2026-09-08,
and in three weeks five unrelated defects had accumulated where no one was looking - a stale
baseline, a leak, a node-only test failure, a boolean run as a word, a check that cannot pass on a
clone it was never configured on. The cohort did not cause any of them; it was the reason to look.

| 4 | 2026-10-02 | **scAnno**: `--assay` required in background, annotate, calibrate and agent (S13); `tests/run_all.py` reported `r.returncode` where only `code` exists, so any red suite killed the runner before it said why. Regression test fails on the old default (its first draft did not: argparse's usage line names the flag either way). 30 suites green locally; S1 and S13 clean with both word lists. Reproduction PBS `719992` (`22_rescue_assay_reproduce.pbs`) against `20260906T114824Z__scanno-deb48ad__02_annotate__interface` (no package change between `deb48ad` and the branch base) | **IDENTICAL** - 10 libraries x 18 label/cluster columns, the rescue, `impact.csv`, `rescue.json`. Merged: scAnno `main` = `7502c88` |
| 4 | 2026-10-02 | **scQC**: `assay` required at ingest and threaded to 05_quality (`_cohort_assay` refuses a mixed or missing assay); no `assay="snrna"` default left; `--mito-bounds`/`--mito-bound-declared-by` wired, as `docs/FILTERS.md` always said. Wiring test section M fails on the old graph and passes on the new. Selftest on the cluster PBS `719987`: 33 passed, 0 failed, 1 skipped (`719948` on `~/scqc/env/core` failed `test_native_io.py` for want of `pyarrow` in that frozen env - a finding of its own). Reproduction PBS `719947` (`25_stage1_assay_reproduce.pbs`), predicted IDENTICAL | **IDENTICAL** - 10 libraries, every kept barcode and all six criterion columns, 100,713 = 100,713. Merged: scQC `main` = `848496a` |
| 4 | 2026-10-02 | **scQC `--registry`** (branch `registry`, `12f319f`): ingest read the registry beside the project's parent, else the one shipped with scQC - a single example row, the first cohort's mouse reference - so a second species could not be declared without editing the tool. That is the same overfit as Q1 one level up: a default that is the first cohort's value. `scqc run --registry FILE` (absent: lookup unchanged, run key unchanged); wiring section N accepts a human row with a project registry and refuses it without one, and fails on the old ingest. The cohort's registry is project content (`stages/01_qc/registry.tsv`). Reproduction PBS `720101` (`26_stage1_registry_reproduce.pbs`), predicted IDENTICAL | **IDENTICAL** - 10 libraries, 100,713 = 100,713. Merged: scQC `main` = `12f319f` |
| 4 | 2026-10-02 | **scProfile** (branch `second-cohort`, `48aaeba`): the plan's contrast decision carries each term's control, resolved by the host's own `control_for`; DE orders each term control-first (the fit's categories too - PyDESeq2 0.5.2 measured: the interaction's sign follows the base level, -1.97 vs +1.97); abundance builds the term control-first and caveats a fit that ignores it; four first-cohort names out of tests and docs; a geometry test that measured a closed figure (matplotlib 3.11 replaces a closed figure's canvas) now re-attaches Agg. 110 suites green, through the repository's own gate, which notes the figures change and want a look | reproduction pending - prediction 2 above |
| 2 | 2026-10-02 | **Declared versus measured, with no change to the generic contract.** PLUGIN_FORMAT §6 already reserved `profile_context` - "whatever the profile defines and the generic contract does not know about" - and the kernel already passed it to every plugin; nothing filled it. `Stack.init(context=)` / `sch init --context AXIS=VALUE` fills it, refusing any name not in the profile's `axes:` (a misspelt declaration is a missing one that looks present). New probe `axes`: species from Ensembl gene identifiers in any `var` column (decisive at 90%, prefixes longest first so `ENSGALG` is not read as human), the symbol convention as a hint only, and the assay reported as NOT measurable from counts. New gate `axes_declared`: REFUSE a declared species the identifiers contradict; REVIEW an axis measurable and undeclared, a convention mismatch, or an undeclared assay. Opt-in (`gates: {axes_declared: required}`), so no existing mount changes its gate list. Profile §7/§8 state the rule | both plugins valid (15 checks); `doctor --architecture` holds; `tests/test_axes_declared.py`: the gate's five verdict paths through the real protocol, and end to end on an object carrying human identifiers in a stack declared mouse - the probe measures `homo_sapiens`, the gate REFUSES naming both |
| 4 | 2026-10-02 | **An environment race, of my making.** The scProfile reproduction's first base run (PBS `720083`) refused honestly in 8 s - no `de`/`abundance` environment - and the two builds submitted for it (`720088`, `720089`) both failed: the two kernels resolve to ONE environment, and two concurrent `conda create`s extracted the same packages into the shared `~/.conda/pkgs`, leaving `libgfortran-16.2.0` unreadable. Debris removed (two empty extraction directories and the doubly-written archive, all timestamped at the failure); one build resubmitted (`720377`). The cohort's own build (`720386`) runs scQC's installer, which bootstraps micromamba with its cache inside the project | rule: never run two conda builds that share a package cache, nor two kernels that may share an environment hash, at once |
| 5 | 2026-10-02 | **The cohort's stage 1, prepared.** PI decisions: build the project's own interpreters (`stages/01_qc/jobs/00_env.pbs`); declare the doublet rate per library as 10x's GEM-X 0.4% per 1,000 cells times Cell Ranger's call (0.052-0.069). A new finding while declaring it: scQC's design discovery skips only `sample, platform, species, reference, assay, fastq_*, matrix` - not its own per-library parameters (`dbr`, `dbr_sd`, `mt_prefix`, `ribo_pattern`, `ambient_*`) - so a parameter column with few enough distinct values becomes a design factor. Four distinct rates are excluded here only by the n-1 ceiling | finding Q7, for the next scQC change |
| 4 | 2026-10-02 | **scQC `ambient-run-path`** (`cf0b750`), read against the run route no cohort had taken: Q4 **confirmed in code** - CellBender's native .h5 sat under `<sample>_ambient.h5`, which `scanpy_ops._load` opens with `read_h5ad`; now CellBender writes `<sample>_cellbender.h5` (so its barcode CSV is the one step 2 reads - Q5) and a new `convert` op, in the analysis environment as wiring section E requires, writes the object through the tool's own reader. `--gpu-queue` (each task checked against the queue it enters). Q7 `NOT_FACTORS`, shared by run and validate - on the old code a per-library `dbr` WAS discovered as a factor. Q8 the installers refuse a half-built environment (on the old code `[skip] already exists`, exit 127 on every rerun - PBS 720421). Two new suites fail on the old code (7 findings) and pass; 35 green | reproduction `27_stage1_ambrun_reproduce.pbs` written, held until the cohort's environment build (which runs scQC's installer from `~/tools/scQC`) finishes - a checkout is never switched under a running job |
| 4 | 2026-10-02 | **scAnno `species-checked`** (`c16c56a`, N2): `annotate` compares `--species` with the object - an Ensembl contradiction refused naming both, a symbol-case disagreement a note. On the old code `annotate --species Mouse` on human identifiers exited 0 with mouse-marker labels; the new suite fails there and passes here; 31 green | reproduction PBS `720434` against the branch's base executed (`…__scanno-7502c88__02_annotate__assay`), predicted IDENTICAL with no refusal or note |
| 4 | 2026-10-02 | **scAnno `species-checked`: IDENTICAL** (PBS `720434`, 22 of 22 comparisons, no species message in any log). Merged: scAnno `main` = `c16c56a` | merged |
| 5 | 2026-10-02 | **The cohort's first stage 1** (`BrainOrganoid_C46/runs/scqc/01_qc/20261002T111059Z__scqc-cf0b750__01_qc__evidence`, PBS `720477`, evidence mode, scQC `cf0b750` under reproduction as `720466`). The project's own environments built first (`720424`, core/cellbender/rdoublet verified). Graded so far against the job's prediction: `validate` 4 of 4, the design discovered is `genotype` alone (on the old code it would also have been `dbr`, `dbr_sd` - Q7); **ingest passed on all four** (prediction (a), a 2 M-barcode matrix at 1 cpu / 8 GB, **falsified**); the four CellBender tasks went to `gpu-h200` with `ngpus=1`, the first time the denoiser was ever submitted from inside scQC | running |
| 4 | 2026-10-02 | **scProfile cannot build its shared kernel environment from `main`** (PBS `720377`): pip `resolution-too-deep` through pertpy's arviz 1.x split; the group's requirements are ranges, not pins, and `scprofile-env-b13883e6c5` is a hash never built before - so de, abundance, cellchat, cellcycle, decoupler, liana and pseudotime cannot be installed on a fresh prefix. The DE pair runs on an existing interpreter through scProfile's documented `SCPROFILE_<KERNEL>_PYTHON` route, the same for base and branch. BASE PBS `720487` | finding P5 for scProfile: pin the group's environment |
| 4 | 2026-10-02 | **scQC `ambient-run-path`: IDENTICAL** (PBS `720466`): 100,713 = 100,713, every criterion column; the report's design factors the predicted four. Merged: scQC `main` = `cf0b750` - the commit the cohort's stage 1 already runs on | merged |
| 4 | 2026-10-02 | **scProfile `second-cohort`: DIFFERENT by its written criterion; not merged** (PBS `720548` against BASE `720487`). Held: every contrast name, and all 29 population x term fold-change identities within 1e-3 on >= 99.97% of genes - the interaction rows reparametrised exactly as computed. Missed: p-values on the one additive population, predicted identical to a relative 1e-6; measured median 1.6e-6, max 6.0e-5, Wald statistics correlated with the negated branch at 1.00000000 - the tolerance was set below the fit's own precision. Recorded as a miss, not re-graded | the merge, and the sign convention it gives SAMBO's DE (to its declared controls young/chow), are the PI's |
| 5 | 2026-10-02 | **The cohort's first stage 1 FAILED inside CellBender** (PBS `720477`, sealed 13:14Z, exit 1): ingest passed, and every CellBender task died at its first checkpoint - `TypeError: cannot pickle 'weakref.ReferenceType' object`, then `Checkpoint file ckpt.tar.gz does not exist` (children `720482`, `720483` after 20 min; `720484` deleted at 16 min with the same error logged; `720485` deleted while queued). The project's `env/cellbender` holds torch 2.14.1; SAMBO's working one holds 2.5.1, and scQC's installer pins no torch at all - finding **Q9**, a fix drafted (pin 2.5.1 / numpy 1.26.4, refuse any other) and held unpushed. Asked whether to fix or stop, the PI: **"do not run cellbender for single cell"** - then **"single cell and single nuclei is fundamentally different!"** | cohort DECISIONS D6; the question became what single cells get instead |
| 4 | 2026-10-02 | **What scQC gave single cells, read whole.** The assay changed two numbers - the mitochondrial bounds and how k is chosen - and nothing else. On a single-cell cohort the code would have: scheduled CellBender anyway (Q6 - `plan_ambient` was never called on the run path); taken "has counts after denoising" as the cell call, which on a raw matrix calls every droplet; bounded the count floors by nuclear valleys (largest measured 473 UMI); counted ribosomal markers against whole cells in criterion C; and stopped at step 6 for a `cellbender_cell` column nothing in scQC writes - only SAMBO's supplied objects carried it, from SAMBO's own conversion (**Q10**, which would have stopped a nucleus denoised inside scQC too). PI decisions, asked: the cell call is Cell Ranger's (D7); the whole-cell count bounds are DECLARED now from published practice, UMI 500-2,000 and genes 250-1,500, not left uncalibrated (D8) | the change below |
| 4 | 2026-10-02 | **scQC `single-cell-route`** (`1771876`, `cb89eea`): `DENOISE` per assay is a policy - nuclei always, single cells never; the graph reads it before submitting anything; a single-cell library takes `_ambient_none` (raw counts, every droplet kept, Cell Ranger's call written in as `aligner_cell`; `aligner_cells` required, apply mode refused since step 7's first criterion carries the denoiser's name); steps 4, 5 and 6 select cells by the column; step 2 says NOT RUN instead of "0 lost"; the audit names the libraries unmeasured; count bounds and criterion C's classes per assay, no default; the denoiser's conversion writes `cellbender_cell` (Q10). `tests/test_single_cells_are_not_nuclei.py`: the graph, the conversion, step 5's measurement, and the CLI on a synthetic single-cell cohort - **all 19 of its checks fail on `cf0b750`** (A9 only because the per-assay parameter did not exist) and pass; selftest 35 passed, 1 failed, 1 skipped locally - the failure `test_native_io`, which fails identically on `main` in this interpreter (its own message: the environment cannot tell the two storages apart), the skip the COHORT_DIR audit; leak guard clean on both word lists | reproduction PBS `720697` (`28_stage1_singlecell_reproduce.pbs`), predicted IDENTICAL; the cohort's stage 1 as single cells PBS `720698` (`11_scqc_evidence_nodenoise.pbs`), whose prediction (a) is that the valley procedure, calibrated on denoised objects, finds empties-versus-debris on a raw whole-cell matrix and refuses below 500 |
| 4 | 2026-10-02 | **scQC `single-cell-route` `cb89eea`: IDENTICAL** on SAMBO (PBS `720697`, 100,713 = 100,713, every criterion column). The fast-forward of `main` was **held for the PI's review** (the merge was not made) | merge pending the PI |
| 5 | 2026-10-02 | **The cohort's stage 1 as single cells** (PBS `720698`, scQC `cb89eea`, evidence): steps 1-2 exactly as predicted (four conversions, no GPU, no denoiser; calls 14,007 / 15,619 / 17,184 / 12,891); prediction (a) **held**: the count "valley" over 2.0-2.3 M raw droplets was 2.5 UMI, bimodal False in all eight - the density has three populations (barcode noise ~1 UMI, empties ~114, cells ~6,600-13,000) and the two tallest were both noise. The run itself failed at step 4: two qsubs refused "would exceed queue generic's per-user limit" because the SAMBO reproduction was queuing beside it - my choice to run both at once; scQC failed a task on a queue state (**Q11**) | the valley procedure does not apply to raw single-cell matrices |
| 5 | 2026-10-02 | **A claim corrected by measurement.** From the raw barcode-rank curve read at rank N, I told the PI every called cell had >= ~1,200 UMI. The PI: "are you sure all cell above 1.2k? is it before qc or after qc". It was before QC, and wrong: PBS `720840` read Cell Ranger's call itself through scQC's `qc_metrics` - 725-1,420 called cells per library sit below the rank-N UMI (EmptyDrops-style rescue) and the call's minimum is 500 UMI in all four; median ~8,000 UMI / ~3,400 genes; mito median 1.7-1.9%. The job's prediction (the claim is wrong) held. PI, on the floors: "it looks like all high quality cells. make reasonable QC, do not be too harsh, avoid removing true signal" (cohort D9) | measure before claiming |
| 4 | 2026-10-02 | **An audit of the single-cell route** (a separate agent, read-only, then each claim checked against the code): step 5 stops before the mito ceiling; apply would call every raw droplet a cell, list two million "removals" and rebuild a set per droplet; step 6 refuses a cohort with no uninformative marker and labels healthy clusters high-mito at a p95 of 4%; the doublet sweep scores uncalled droplets; the nuclear-fraction criterion points the wrong way on cells; report texts call single-cell numbers the denoiser's. Then the PI: "audit and upgrade scQC to be robust enough to handle different condition". **`tests/test_conditions.py`** runs the real `scqc run`, evidence and apply, with a stand-in detector, on synthetic cohorts that differ as cohorts do; it found five more: antibody-capture features read as genes (a CITE-seq raw matrix rejected at ingest as already cell-called); `aligner_cells` as 10x HDF5 read as text; the deliverable refusing barcodes shared between libraries (one whitelist - never met because SAMBO's converter had prefixed them); a mixed-assay cohort starting a denoiser before refusal; a two-cell cluster stopping step 6. FAIL lines printed no reason | fixed in `0e6a5f6` |
| 4 | 2026-10-02 | **scQC `0e6a5f6`**: declared floors on cells (`FLOOR_METHOD`, 500/250, classed DECLARED); ceiling over called cells at the floor, k >= 3; step 7 for cells (`fail_not_aligner_cell`, called cells only, criteria from the tables' header); step 6: C absent is "cannot fire", B >= 10% on cells, tiny clusters C unknown; sweep on called cells; nf criterion refused on cells; Gene Expression only; HDF5 `aligner_cells`; `<sample>_<barcode>` in the deliverable; mixed assays refused up front; Q11 qsub waits on a full queue; FAIL prints its reason. `test_conditions.py` 8 of 8 (human, mouse, one library, HDF5 + antibodies + duplicated symbol, mixed depths, two refusals by name); `test_a_full_queue_is_waited_for.py` fails on the old executor; selftest 37 / 1 environmental / 1 skip; leak guard clean on both lists. Open from the audit: step 6 and step 7 resolve the floors through different functions when decisions.yml overrides them; some report captions still say "nucleus"; no ambient estimate or library-level metrics are reported for cells | reproduction PBS `720930` (`29_stage1_robust_reproduce.pbs`, IDENTICAL predicted, deliverable names included); cluster selftest `720931`; the cohort in APPLY mode `720932` (`13_scqc_apply_cells.pbs`) |
| 4 | 2026-11-09 | **Read five weeks late** (autodev, rule 5). `720930` is **IDENTICAL, as predicted**: 100,713 = 100,713; keep-diff 0 in every library; every criterion column identical; the deliverable's cell names reproduce. `720931`'s output was never located: `scqc_selftest.pbs` writes `logs/` beside wherever it was submitted, outside `runs/` | the merge became autodev wave W001 (ADR-0028), under the PI's standing yes once its verifier passes |
| 5 | 2026-11-09 | **`720932` graded against its prediction.** Held exactly: the UMI floor removes nothing; the gene floor 0 / 0 / 1 / 10; the mito ceiling 89 / 79 / 123 / 98. Missed: 8.8-12.3% removed per library (6-8% predicted), 53,534 of 59,701 kept (about 55,000-56,500 predicted). The doublet step calls 8.3-11.7% of called cells against declared rates of 5.2-6.9% | finding GAP-C02 in `autodev/ledger/gaps.tsv`; the cohort's RUNLOG has the table |

### The predictions, graded at the end of 2026-10-02

| # | prediction | outcome |
|---|---|---|
| 1 | Q1+Q2 reproduce SAMBO stage 1 IDENTICAL | **held** - PBS 719947 |
| 2 | P1 changes SAMBO's DE as the reparametrisation of the base fit (corrected before any run) | **held on every fold change and contrast name; missed on its own p-value tolerance** - PBS 720548 |
| 3 | the fixture's value axes fail scQC on Q1 and scProfile on P1 before their fixes | **not measured as worded**: scQC's fixture tier runs `describe`, and scProfile's fixture point refuses on the covariate before DE - the fixture could not reach either defect. Both were caught instead by repository tests that fail on the old code (scQC wiring section M; scProfile `test_the_kernels_take_the_control`). The fixture tier that cannot reach a tool's pipeline is itself a finding (A, from the first reading) |
| 4 | scQC on the cohort stops next at the ambient run path | **pre-empted**: the run path was read before the run, Q4/Q5 confirmed in code and fixed; the first run (PBS 720477) passed ingest - its own prediction (a) falsified - and then **stopped at step 1 after all, inside CellBender itself** (torch 2.14.1, Q9), a failure no reading of scQC's code could have found. The PI then took single cells off the denoiser entirely |
| 5 | the axes probe reads the second cohort human and the first mouse | **held on the synthetic object** (human identifiers in a stack declared mouse: REFUSE); not yet asked of either cohort's real object |
