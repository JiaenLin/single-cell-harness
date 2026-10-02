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
| 4 | 2026-10-02 | **scQC `--registry`** (branch `registry`, `12f319f`): ingest read the registry beside the project's parent, else the one shipped with scQC - a single example row, the first cohort's mouse reference - so a second species could not be declared without editing the tool. That is the same overfit as Q1 one level up: a default that is the first cohort's value. `scqc run --registry FILE` (absent: lookup unchanged, run key unchanged); wiring section N accepts a human row with a project registry and refuses it without one, and fails on the old ingest. The cohort's registry is project content (`stages/01_qc/registry.tsv`). Reproduction PBS `720101` (`26_stage1_registry_reproduce.pbs`), predicted IDENTICAL | pending |
| 4 | 2026-10-02 | **scProfile** (branch `second-cohort`, `48aaeba`): the plan's contrast decision carries each term's control, resolved by the host's own `control_for`; DE orders each term control-first (the fit's categories too - PyDESeq2 0.5.2 measured: the interaction's sign follows the base level, -1.97 vs +1.97); abundance builds the term control-first and caveats a fit that ignores it; four first-cohort names out of tests and docs; a geometry test that measured a closed figure (matplotlib 3.11 replaces a closed figure's canvas) now re-attaches Agg. 110 suites green, through the repository's own gate, which notes the figures change and want a look | reproduction pending - prediction 2 above |
