> Archived 2026-11-09 from audit pass 0001b. Home paths quoted as evidence are redacted to `<dev>` (the harness's leak guard).

# Platform review 0001 (audit pass 0001b): Studio, Lab and Service against GOALS.md

**Reviewer** platform gap reviewer, read-only and adversarial. **Date** 2026-11-09 (UTC stamps below).
**Scope** `scrnaseq-studio`, `scrnaseq-lab`, `rnaseq-service`, and where they meet the family.
**Goals** G6; PLAT.1–PLAT.3; A6.2, A6.3; A2.2; A2.1/A1.3 in web-app form.

**What was read and run (all at `main`):**

| repository | SHA | how |
|---|---|---|
| scrnaseq-studio | `92ef97f` (2026-08-20) | fresh clone; `npm ci`, `lint`, `test`, `build` run locally |
| scrnaseq-lab | `c4347b3` (2026-08-20) | fresh clone; the same four steps; headless converter run on synthetic objects |
| rnaseq-service | `a42b747` (2026-08-22) | fresh clone; the same steps without lint, as its CI does; its modules run on single-cell file lists |
| scQC / scAnno / scIntegrate / scProfile | `cf0b750` / `c16c56a` / `722bc79` / `f294c89` | read only, from the other reviewer's clones; `scintegrate/emit.py` copied byte-identical (sha256 `e6f74830…`) to write the fixtures |
| single-cell-harness | `dcc7f45` | read only |

The clones are under `…/scratchpad/platform_review/clones/`, the scripts under `…/scripts/`, the logs under `…/logs/`, and the fixtures and bundles under `…/fixture/`.

**Not done.** No cluster access. No real cohort object was converted, because the family's final objects live on the cluster. No browser UI was driven. The Desktop checkouts were not touched. The other reviewer's clones were left clean: `git status --porcelain` is empty for all four.

---

## 1. Verdict and grades

**Verdict: NOT HAPPY.** No platform acceptance test passes. The apps build and their own tests pass. None of the three is connected to the family:

- the Service rejects every single-cell delivery;
- Lab's only automatic converter is a developer script nobody calls, and it drops the run's provenance;
- Studio shows nothing about the run that produced an object, and nothing of the harness's own results.

| test | grade | evidence |
|---|---|---|
| **A6.2** Studio hand-off | **FAIL** (2 of 3 clauses fail) | **(a) Opens through Lab's converter: holds on the family's object *shape*.** A synthetic object written by scIntegrate's own `emit.build`/`write_h5ad` (3,000 cells; X lognorm; `layers['counts']`, `layers['lognorm']`; `obsm` X_pca, X_harmony, X_umap_*; `uns['scintegrate']` with provenance) was converted by `scripts/convert-node.mjs` (rc 0, 3 s). Studio's own `openCollection` opened the result: 3,000 cells, 1,500 genes, 8 samples. Not shown on a real family object: UNKNOWN there. **(b) "No manual conversion": fails.** The converter is a developer script outside `npm test` (`convert-node.mjs:1-14`). It picks roles by guessing column names (`:53-60`), and nothing in the harness or the tools calls it. The browser path is a person clicking through four steps (`Review.tsx:235-276`, `:380`). **(c) "Studio shows the run": fails.** Lab reads four heuristic fields (`h5ad.ts:585-594`) and ignores `uns['scintegrate']['provenance']` (tool, version, commit, job, argv, seed; `scintegrate/cli.py:633-648`). The bundle's `meta.provenance` came out as `{normalization:null, integration:'harmony', doublets:null, ambient:null, clustering:'cell_type', condition:'age', sample:'sample'}`. Studio's provenance table has no run, commit or job row (`Overview.tsx:50-67`). Its Methods paragraph says "Everything between the counts and those labels is unknown to this app" (`Methods.tsx:122`). Cross-ref GAP-014: the only recorded hand-off is SAMBO's stage-2 joint object, done by hand. |
| **A6.3** Service takes single-cell requests | **FAIL** | The Service keeps FASTQ files only (`scan.ts:6`, `App.tsx:105-128`). A Cell Ranger delivery of 40 files and a CeleScope delivery of 16 files, run through the app's own modules, both gave **0 FASTQ and 0 samples**, and step A blocks with "Add your sequencing folder to continue." (`App.tsx:150`; `scripts/service_sc_probe.mjs`). The request model is bulk-only: layout, strandedness, library, genome, one `condition` per sample, and contrasts of every group against one control (`types.ts:15-20`, `:68-96`; `request.ts:67-72`). It has no assay, platform, chemistry, reference key, mt/ribo pattern or doublet rate. Its only consumer is the bulk `rnaseq-hpc-request` skill (nf-core/rnaseq). **The bulk clause holds:** 126 checks pass locally (rc 0, 2026-11-09T06:24Z) and in CI run 32572564606 on `a42b747`. |
| **A2.2** documentation true: rnaseq-service | **PARTIAL** | 17 claims sampled. None is false, and one is imprecise: the strandedness row says "never guessed", but `infer.ts:130-133` fills it in when a token such as `dUTP` is spelled out, and `test-infer.mjs:53-56` tests that. The README states inputs, outputs and how to run. It does not say how to reproduce a request. |
| **A2.2**: scrnaseq-lab | **FAIL** | 14 sampled, 3 false. (1) "asks the two questions … Nothing else is asked" (`README.md:12-17`), but the UI has four step cards: cell type, condition, sample, and embedding with label (`Review.tsx:235-276`). (2) "`.rds` is still read whole … save as `.h5ad` if yours is big" (`README.md:188-190`), but `ff09722`, `47838db` and `c4347b3` (2026-08-20) stream the .rds and convert it in shards. (3) "Output: `bundle.zip`, schema `scrnaseq-studio/bundle@1`" (`README.md:156-162`), but the file written is a `scrnaseq-studio/collection@1` container (`collection.ts:17`), written as `.scstudio` and then renamed (`App.tsx:243-262`); only its parts are bundle@1. The headless converter is not in the README, and nothing says how to reproduce a conversion. |
| **A2.2**: scrnaseq-studio | **FAIL** | 13 sampled, 4 false. (1) "Pseudobulk → DESeq2 is offered above three samples per group" (`README.md:72`), but that path only exports counts: "No pretend DESeq2" (`Stats.tsx:470`), "DESeq2 itself is not in the browser" (`:509`). The app's own Methods paragraph writes "was tested with DESeq2" when pseudobulk is selected (`Methods.tsx:146-153`), and Overview says so too (`Overview.tsx:101`). (2) "keeps the bundle at ~83 kB gzipped" (`README.md:169`), but the build of `92ef97f` emits `index-*.js` at **156.97 kB gzip**. (3) "We already ship **webR** (for DESeq2)" (`DESIGN.md:44`) and §1.1–1.2, which describe reading .h5ad/.rds directly. The dependencies are only fflate, react and react-dom (`package.json:14-18`), and README:140-141 lists direct opening as not done. (4) Studio "reads the thresholds already applied from `uns` … offers a preview filter (MAD-based or manual)" (`DESIGN.md:283-286`): no such code exists in `src/`. |
| **A2.1/A1.3, web form** (builds, own tests pass from `main`) | **PASS ×3** | Fresh clones, Node v26.7.0, npm 11.19.0, 2026-11-09T06:24Z, all steps rc 0. Studio: 17 test files, 1,512 checks passing, build 4 s. Lab: 6 files, 320 checks, build 3 s. Service: 4 files, 126 checks, build 2 s. CI at the same SHAs ran ci, lint, test, build and deploy, all successful: Studio 32352972481, Lab 32345705051, Service 32572564606. All three Pages sites answer 200. **Limit:** CI covers modules only. No Lab-to-Studio round trip runs in CI (GAP-P18), and no browser test can run: 31 scripts import an undeclared `playwright-core`, and 33 hard-code `C:/Users/<dev>/…`. |

---

## 2. The three capabilities: what exists, where, and how far from the goal

### PLAT.1: Service, request handling (`rnaseq-service`). Far from the goal.

**What exists.** A careful **bulk FASTQ** request builder: 5 commits and 126 regression checks. It drops a folder and walks it in the browser, reading names and sizes only. It recognises seven FASTQ naming schemes, skips OS sidecars, and treats folders as sample identity (`scan.ts`). It guesses groups from names (`groups.ts`). It fills the questionnaire from evidence, labelling each answer detected or assumed (`infer.ts`). It writes `rnaseq-request-<id>.json` and an nf-core `sample,condition,fastq_1,fastq_2` sheet (`request.ts:46-98`). All of this can be reused for single-cell: the folder walk, the naming helpers, the evidence labels, the gating.

**What is missing.** Everything single-cell:

- **Intake.** FASTQ only (`scan.ts:6`). This was run on a Cell Ranger `outs/` list and a CeleScope `outs/{raw,filtered}` list, with synthetic names. The family has received two real layouts: Cell Ranger with `outs/` flattened by the vendor (BrainOrganoid_C46 `data/DELIVERY.md`), and CeleScope nested as `<s>/<s>/outs/{raw,filtered}` (SAMBO's stage-1 samplesheet). Neither real layout was run. They would fail the same way because the filter tests only the file extension, but that is an inference.
- **Questions.** No assay, platform, chemistry, reference, mt/ribo pattern or doublet rate.
- **Design.** One factor only. The bulk skill's own scaffold warns that "The request form gets 2×2 designs wrong: it emits contrasts that move two factors at once" (`scaffold.py:423-425`).
- **Hand-off.** The final step points users at the **bulk** Studio (`StepRequest.tsx:16`) and offers bulk deliverables (`request.ts:7-14`).
- **Consumer.** No harness-side consumer of a single-cell request exists (GAP-001: no stage driver).

**The request it should produce.** These are the inputs the harness and its tools actually take today. The BrainOrganoid_C46 stage-1 samplesheet and registry (`stages/01_qc/samplesheet.tsv`, `registry.tsv`, `DECISIONS.md` D1–D5) are exactly what had to be written **by hand**.

| field | consumer (file:line) | where it is in a delivery | can the browser know it from names? | whose decision |
|---|---|---|---|---|
| `sample` | scQC `ingest.py:49` (REQUIRED) | the library folder | yes | the user confirms |
| `platform` = `10x` or `singleron` | `ingest.py:59`, `:87-90` | the layout (`raw_feature_bc_matrix` against `outs/raw`) | yes | detected |
| `matrix` = **raw** droplets | `ingest.py:130-141`; `verify_raw` P2 refuses a cell-called matrix | `raw_feature_bc_matrix/` or `.h5`; CeleScope `outs/raw` | yes | detected |
| `aligner_cells` = **filtered** | `steps.py:508-577` (step 2 refuses without it) | `filtered_feature_bc_matrix/`; CeleScope `outs/filtered` | yes | detected |
| `assay` = `scrna` or `snrna` | `ingest.py:49-59`; PI rule 2, no default | not in names. Intronic fraction is only a hint | no | **user**, with no default |
| `species`, `reference` = `species/build` plus a registry row | `ingest.py:96-100`; the project `--registry` | the Cell Ranger h5 `/matrix/features/genome`, `web_summary.html`, the CeleScope report | no: needs the file contents | the user confirms a detected value |
| `mt_prefix`, `ribo_pattern` | QUICKSTART:61 ("nothing guesses them"); `steps.py:93-97` | a species convention, or the gene list | suggestion only, marked assumed | the user confirms |
| `dbr`, `dbr_sd` | `pipeline.py:543-546` (declared, no default) | chemistry multiplet rate × the aligner's cell count (D5) | no: needs a barcode count and the chemistry | the user, pre-filled with the computed value |
| design factors (N), covariates, reference level per factor | scQC `_design` (`steps.py:100`); scIntegrate `--design`; scProfile `read_design` (`inputs.py:706`) | the questionnaire | — | **user** (tier II: sign conventions) |
| `profile_context` axes | `sch init --context` (`kernel.py:141-170`; `single-cell.yml:31`) | derived from the fields above | — | derived |
| the delivery root on the cluster | the intake: it rebases relative paths, as `scaffold.py` does | not knowable in a browser | no | the intake or agent |

### PLAT.2: Lab, data formatting (`scrnaseq-lab`). Near on the mechanics, far on the contract.

**What exists.**

- **Two readers.** A lazy, block-cached `.h5ad` reader over h5wasm, and a streaming `.rds` reader.
- **Choices made by measurement.** Matrices are classified by their values: scaled data is refused, log1p counts are recovered (`build.ts:183-233`). Gene aliases are kept. Every embedding is carried. Objects above 50 M nonzeros are split (`shard.ts:23`).
- **A headless path.** `scripts/convert-node.mjs` uses the app's own functions in the app's own order.
- **What an object must carry.** A categorical cell annotation, an embedding with at least two columns, and a matrix that is not scaled (`build.ts:354`, `:429`, `:183-233`). Sample and condition are optional. scIntegrate's object meets all three, which the fixture confirmed.
- **Size.** The family delivers `.h5ad`, so Lab's sharded `.rds` path (`c4347b3`) is not on the family's route. The `.h5ad` path splits above 50 M nonzeros (`shard.ts:146`). scIntegrate's own comment mentions "the 3 GB object" (`cli.py:671`). Two things are inferences, not measurements: that this was SAMBO's stage-3 object, and that such an object would be split. Neither was run here. In the browser, writing an output beyond a few hundred MB needs `showSaveFilePicker`, which only Chrome and Edge provide (`README.md:195-196`).

**Measured on the family's object shape** (scIntegrate's emitter, pinned anndata 0.13.2, pandas 3.0.5):

- **Conversion.** Works, and Studio's reader opens the result.
- **Label guess.** Lands on `cell_type` or `scanno_cell_type`, as scAnno's QUICKSTART:113-116 promises.
- **Design factors.** One factor survives:
  - neutral names (`factor_a`, `factor_b`) give **condition null**, a single-group bundle;
  - `age` with `diet` gives condition `age`, while **`diet` is dropped** without a note (extras `[]`).
- **Sentinels.** **`EXCLUDED` and `UNRESOLVED` become clusters**: `clusters: ['EXCLUDED','TypeA',…,'UNRESOLVED']`.
- **Latent spaces.** 30-D spaces are carried as "2-D embeddings" by slicing their first two dimensions (`h5ad.ts:574-579`).
- **QC.** The mitochondrial fraction is a flat zero, because scIntegrate narrows obs.
- **Provenance.** None from the run.
- **Default string encoding.** An object written with anndata's default encoding (nullable strings) **crashes the reader**: `TypeError: Cannot read properties of undefined (reading 'map')` at `h5ad.ts:67` via `readVar` `:172`. scIntegrate, scAnno and scProfile avoid it (`classic_string_encoding`). scQC's writers do not; that it fails on scQC's own objects is an inference from the shared pins, not run.
- **Reproducibility.** Two conversions of the same input give identical entries, but the zip files differ (sha256 `3984ac12…` against `0a112df5…`), because only the zip entry timestamps differ.

**How far.** About two weeks of S and M work: a tested CLI with explicit roles, every design factor, sentinels and a `meta.run`. Then the hand-off becomes automatic. Real-object proof needs a SAMBO or C46 final object (blocker B4).

### PLAT.3: Studio, data explorer (`scrnaseq-studio`). Far from the goal.

**What exists.** A strong explorer **of the object**. It opens 292 k cells in a few seconds and reads genes on demand (the README's figures; not re-measured here). It has markers, Wilcoxon DE with Seurat's gates, enrichment, module scores, co-expression and composition. Its provenance table separates "from your file" from "computed here" (`Overview.tsx:50-67`). It prints the exporter's notes, and its Methods paragraph follows the selected test.

**What is missing.**

- **The run.** No commit, job, run key, sealed state or stage chain. Methods declares all of that "unknown to this app" (`Methods.tsx:122`).
- **The harness's results.** Studio accepts only `.zip` and `.scstudio` bundles (`Landing.tsx:102`) and gene-set files (`SetEditor.tsx:141`). scProfile's tables (DE, communication edges), `report.json` and report pages have no way in.
- **scProfile's cell-level results.** These are numeric columns, and Lab carries categorical extras only (`build.ts:404-410`).
- **Studio's own DE.** It replaces scProfile's DE instead of showing it.
- **The QC decisions** (thresholds, who decided). Absent, although DESIGN.md says Studio reads them.
- **Sentinels.** Treated as populations, against the profile's sentinel rule (`docs/profiles/single-cell.md` §4).

**How far.** L in total, after PLAT.2's run record exists.

### What the family delivers at the end, and what the platform does with it today

| deliverable | written by | Lab and Studio today |
|---|---|---|
| `objects/cohort_integrated.h5ad`: X lognorm, `layers` counts and lognorm, `obsm` X_pca, X_<m>, X_umap_<m> and X_umap; obs narrowed; `uns['scintegrate']` (benchmark, choice, **provenance**) | scIntegrate `emit.py:87-139`, `cli.py:633-667` | converts with the headless dev script. Roles are guessed. Provenance, upstream `uns` and the QC columns are lost (`emit.py:104` rebuilds the AnnData) |
| `scanno_cell_type`, `scanno_path` and related obs columns, with sentinels | scAnno README:186-204 | the label is guessed correctly. Sentinels become clusters |
| `objects/cohort_profiled.h5ad`, `tables/*.csv`, `report/`, `report.json`, `uns['scprofile']` | scProfile README:195-214 | only the object's categorical columns can travel. The tables, report and numeric results have no path in |

---

## 3. The gap register

The same rows, tab-separated, are in `gaps_0001b.tsv`. Sizes: S ≤ 1 day, M ≤ 3 days, L ≤ 2 weeks, XL above that. IDs written `GAP-0xx` refer to the other reviewer's pass 0001 rows in `autodev/ledger/gaps.tsv`.

| gap_id | goal_ids | repo | gap | evidence | size | depends_on | blocked_by | first_move (and how success is measured) |
|---|---|---|---|---|---|---|---|---|
| GAP-P01 | PLAT.1 A6.3 G6 | rnaseq-service | A single-cell delivery (Cell Ranger outs, flat or under `outs/`, or CeleScope `<s>/<s>/outs/{raw,filtered}`) yields 0 samples and is blocked at step A, because only FASTQ files are kept. | `scan.ts:6`; `App.tsx:105-128`, `:150`; `service_sc_probe.mjs`: 40 and 16 files gave 0 FASTQ, 0 samples | M | — | — | Add `detectDelivery(files)` returning fastq, cellranger or celescope, plus a single-cell scanner that groups each library's raw and filtered matrices, h5 files and summary by the folder holding them. Leave the bulk `scan.ts` untouched. **Success:** new tests on synthetic lists for the three layouts (flat, `outs/`, CeleScope nested) pass, and all 126 existing checks pass unchanged. |
| GAP-P02 | PLAT.1 A6.3 A3.3 G6 | rnaseq-service | The request model and questionnaire are bulk-only. There is no assay (scRNA or snRNA, no default, PI rule 2), platform, chemistry, species/reference key, mt/ribo pattern or doublet rate. The hand-off link and the deliverables point at the bulk products. | `types.ts:15-20`, `:68-96`; `StepDesign.tsx:46-176`; `request.ts:7-14`; `StepRequest.tsx:16` | M | P01 | — | Version `ServiceRequest` with a `kind` field: `bulk`, the default and byte-identical, or `single-cell`, with typed single-cell fields. Add a single-cell question set in which assay has no default and blocks Continue. **Success:** a test refuses a single-cell request without an assay, and the demo's bulk request JSON is byte-identical before and after. |
| GAP-P03 | PLAT.1 A6.3 A3.2 | rnaseq-service | Designs are one factor with every group compared against one control. A two-factor factorial, its interaction, covariates and a per-factor reference level (a user-owned sign convention) cannot be expressed. | `request.ts:67-72`; `App.tsx:156`; `types.ts:15-20`; `scaffold.py:421-430` ("gets 2×2 designs wrong") | M | P02, GAP-002 (the shared design sheet) | — | A sample × factor table: N factors, their levels, the reference level of each, and covariates flagged. It is written as a `design.csv` keyed on sample. For single-cell no contrasts are emitted; scProfile enumerates them. **Success:** a 2×2 with n = 2 per arm round-trips, and scProfile's `read_design` (`inputs.py:706`) accepts it in the harness lane's test. |
| GAP-P04 | PLAT.1 A6.3 A1.1 | rnaseq-service | Nothing writes what the first stage takes: scQC's samplesheet (`sample`, `platform`, `species`, `reference`, `assay`, `matrix`=raw, `aligner_cells`=filtered, `mt_prefix`, `ribo_pattern`, `dbr`, `dbr_sd`, the factors), the registry row and the `profile_context` axes. C46's were written by hand. | scQC `ingest.py:49`, `:96-103`; `steps.py:93-97`, `:536`, `:575`; `pipeline.py:543-546`; C46 `stages/01_qc/samplesheet.tsv`, `registry.tsv`, `DECISIONS.md` D1–D5 | S | P02, P03 | — | Add `buildScSamplesheet`, `buildRegistryRow` and `buildDesignCsv`, with golden-file tests. The header is checked against scQC's REQUIRED and NOT_FACTORS lists, copied in as a contract fixture. **Success:** the golden tests pass, and `scqc validate` exits 0 on the golden sheet, run in the QC or harness lane. |
| GAP-P05 | PLAT.1 A6.3 | rnaseq-service | Values the request needs cannot be known from file names: each library's cell count (for the doublet rate), the chemistry and the genome build. The app promises that "only names and sizes are read". | `README.md:12-13`; C46 `DECISIONS.md` D5 (doublet rate = chemistry rate × the aligner's cell call); Cell Ranger h5 `/matrix/features/genome` | M | P01 | — (pre-decider: G6 forbids uploading, not reading locally) | Count lines in `filtered_feature_bc_matrix/barcodes.tsv.gz` with DecompressionStream, read the Cell Ranger h5 attributes lazily, and pre-fill these values marked detected, uploading nothing. Update the README's promise. **Success:** synthetic gz and h5 fixtures give the right counts and build, with no network calls (a test stubs `fetch` to throw). |
| GAP-P06 | PLAT.1 A6.3 A1.1 HARN.1 | single-cell-harness | No consumer turns a single-cell request into the harness run (A1.1's input) without hand editing. The only consumer is the bulk skill, and the harness has no intake. | `rnaseq-hpc-request/scaffold.py:157-197` (FASTQ R1/R2 only); grep: no `studio`, `service` or `request` intake in `sch/` or `skills/` at `dcc7f45`; GAP-001 | L | P04, GAP-001, GAP-002 | GAP-001 (no stage driver) | An intake (an `sch` verb or a skill) that reads a single-cell `request.json`, rebases its relative paths onto the delivery root, and writes the stage-1 samplesheet, the registry, `design.csv` and `stack.yml` (`sch init --context …`). It refuses on any missing user-owned field. **Success:** on a synthetic request, `scqc validate` passes and `sch init` succeeds with zero hand edits. |
| GAP-P07 | PLAT.1 A6.3 | rnaseq-hpc-request skill (outside the 8 repositories) | A single-cell request handed to the bulk skill dies with a misleading message ("a lane is missing its R1 or R2") instead of a clear refusal. | `scaffold.py:100-103` | S | P02 | outside program scope: `~/.claude/skills` (PI) | Keep bulk requests byte-identical, with no `kind` field, so the skill needs no change. Optionally the skill refuses `kind != bulk` by name. **Success:** the Service's 126 checks are unchanged, and a single-cell request is refused with a message that names its kind. |
| GAP-P08 | A2.2 G2 | rnaseq-service | The README does not say how to reproduce a request. The strandedness row ("never guessed") hides the detection of spelled-out tokens. There is no single-cell scope yet. | `README.md:59-72`; `infer.ts:130-133`; `test-infer.mjs:53-56` | S | — | — | A "Reproduce" section (the request JSON is the record; re-drop the folder and answers to regenerate it) and an exact strandedness row. **Success:** 10 resampled claims, 0 false. |
| GAP-P09 | PLAT.2 A6.2 G1 | scrnaseq-lab | Lab's only automatic converter is an undocumented developer script outside `npm test`. It reads .h5ad only, guesses the cell-type, sample, condition and embedding roles from names with no flags to set them, and no harness or tool step calls it. A person must convert. | `convert-node.mjs:1-14`, `:53-60`; `package.json` has no `bin`; my run converted a family-shaped object with rc 0 | M | — | — | Promote it to `scrnaseq-lab convert` (a package `bin`) with `--cluster --sample --condition --extra --embedding --label --sentinel`. Guesses are used only when a flag is absent, and are printed. Add exit codes, and an `npm test` that converts a committed fixture of the family's shape and opens it with Studio's reader. **Success:** CI is green with that test. |
| GAP-P10 | PLAT.2 PLAT.3 A6.2 G2 | scrnaseq-lab | The run's provenance is dropped. Lab reads four heuristic fields and ignores `uns['scintegrate']['provenance']` (tool, version, commit, job, argv, seed) and `uns['scprofile']`. The bundle has no run field. | `h5ad.ts:585-594`; `build.ts:572-577`; scIntegrate `cli.py:633-648`; my bundle's `meta.provenance` has no commit or job | S | — | — | Copy `uns/<tool>/provenance`, and any `uns['harness_run']` JSON string, verbatim into an additive `meta.run`, which bundle@1 readers ignore. **Success:** a fixture with uns provenance gives an equal `meta.run`, and Studio's reader still opens it. |
| GAP-P11 | PLAT.2 A6.2 A3.2 | scrnaseq-lab | Design factors are lost in conversion. One condition column is kept and the other factors are dropped without a note; neutral factor names give a single-group bundle; no interaction column exists. | measured: `factor_a`/`factor_b` gave condition null; `age`/`diet` gave condition `age`, extras `[]`; `scan.ts:227-230`; `build.ts:380-410` | S | P09 | — | The CLI takes the design's factors explicitly (`--condition` plus `--extra` for each other factor, `--interaction a,b`) and notes any design factor it does not carry. **Success:** the 2×2 fixture carries both factors and the interaction; Studio can choose either one as Group. |
| GAP-P12 | PLAT.2 PLAT.3 A6.2 | scrnaseq-lab + scrnaseq-studio | The annotator's sentinels `EXCLUDED` and `UNRESOLVED` become clusters, and Studio treats them as cell types in composition, markers, DE scopes and legends, against the profile's sentinel rule. | measured: `clusters ['EXCLUDED','TypeA',…,'UNRESOLVED']`; `docs/profiles/single-cell.md` §4; no sentinel handling in either `src/` (grep) | M | P09 | — | Lab `--sentinel` (defaulting to the profile's EXCLUDED and UNRESOLVED) writes `meta.sentinels`. Studio keeps those cells drawn (grey) and excludes them from denominators, legends and marker or DE populations. **Success:** tests on both sides; composition fractions sum over real types only, and the number of sentinel cells is stated. |
| GAP-P13 | PLAT.2 A6.2 | scrnaseq-lab | Lab crashes on .h5ad written with the anndata default (nullable-string groups), which is what anndata 0.13.2 with pandas 3.0.5 (the family's pins) writes unless a tool opts out. | reproduced: `TypeError … reading 'map'` at `h5ad.ts:67` via `readVar` `:172` (`logs/lab-convert-default-encoding.log`); scQC has no `allow_write_nullable_strings` (grep) | S | — | — | Read `encoding-type: nullable-string-array` (values plus mask) in `readObs` and `readVar`. **Success:** the default-encoded fixture converts, plus a regression test. |
| GAP-P14 | PLAT.2 A6.2 | scrnaseq-lab | When the sample and condition columns cross, every cell of a sample is silently relabelled to its first cell's condition. The UI only shows a note, and the headless path never checks. Studio's Python exporter already splits such samples. | `build.ts:385-389`; `Review.tsx:186`, `:274`, `:380`; `convert-node.mjs` has no `crossCheck`; `export_h5ad.py` spanning split | S | — | — | Apply the same split rule (or refuse in the CLI) in `buildBundle`. **Success:** a crossed fixture keeps each cell's condition, with a test. |
| GAP-P15 | PLAT.2 PLAT.3 | scrnaseq-lab | Latent spaces are carried as 2-D embeddings (the first two dimensions of 30-D X_harmony, X_none and X_pca), and identical copies (X_umap = X_umap_harmony) are offered as separate views. Studio's Methods lists them all as drawn embeddings. | `h5ad.ts:574-579`; measured `meta.embeddings` = 6 entries; `Methods.tsx:112-121` | S | — | — | Carry only 2-column obsm (PCA only when chosen, flagged as now), drop byte-identical duplicates, and note what was skipped. **Success:** the fixture carries X_umap, X_umap_none and X_umap_harmony, and the note names the rest. |
| GAP-P16 | PLAT.2 A2.1 G2 | scrnaseq-lab | Conversion is content-deterministic but the files are not byte-reproducible: zip entry times change, so two conversions of one input have different sha256. | measured: entries identical; zip `3984ac12…` against `0a112df5…` (`scripts/cmp_bundles.py`) | S | — | — | A fixed `mtime` in `zipSync` and `collectionPieces`, and per-entry sha256 values in `collection.json`. **Success:** two conversions give an identical sha256 (a test). |
| GAP-P17 | A2.2 G2 | scrnaseq-lab | The README is false or stale in three places (two questions, `.rds` read whole, `bundle.zip` output). The headless converter is undocumented, and nothing says how to reproduce a conversion. | `README.md:12-17`, `:156-162`, `:188-190` against `Review.tsx:235-276`, `collection.ts:17`, `c4347b3` | S | P09 | — | Rewrite those three sections, and add a CLI section and a reproduce section. **Success:** 10 resampled claims, 0 false. |
| GAP-P18 | PLAT.2 A6.2 A2.1 | scrnaseq-lab + scrnaseq-studio | No cross-repository contract test runs in CI. The bundle meta is defined twice. The only round-trip checks are developer scripts that import a sibling checkout by relative path, and the browser end-to-end scripts cannot run. | `build.ts:79-118` against `bundle.ts:61-122`; `check-studio-open.mjs:12`; `check-collection.mjs:19`; 31 scripts import `playwright-core` (undeclared) and 33 hard-code `C:/Users/<dev>` paths | S | P09 | — | A Lab CI job that checks out scrnaseq-studio@main, converts the committed fixture and opens it with `openCollection`. **Success:** the job is green, and a field renamed in either repository turns it red. |
| GAP-P19 | PLAT.3 A6.2 G6 | scrnaseq-studio | Studio shows nothing of the run that produced an object: no commit, job, run key, sealed state, stage chain or user-owned decisions. Methods calls all upstream steps "unknown to this app". | `Overview.tsx:50-67`; `Methods.tsx:122`; `bundle.ts:82` (provenance is a flat string map) | M | P10 | — | A Run card on Overview rendered from `meta.run`: each stage's tool@commit, run key, PBS job, sealed state, the decisions with who made them, and the report paths. Methods cites the run's parameters when present. **Success:** a bundle with `meta.run` shows the card rows; without one, the card says "no run recorded" (component tests). |
| GAP-P20 | PLAT.3 A6.2 G2 | scIntegrate (+ scProfile, harness) | The final object carries only its last stage's provenance. `emit.build` rebuilds the AnnData and keeps only `uns['scintegrate']`, dropping the scQC and scAnno records, and narrows obs so that the QC covariates are gone (Studio then recomputes counts and shows no mitochondrial fraction). | scIntegrate `emit.py:97-104`, `:138`; measured: "no mitochondrial fraction in the metadata"; scAnno `uns['scanno_cluster']`, `['scanno_embed']`; GAP-021 | M | — | where the run record lives: (C), the pre-decider decides | The harness writes a `uns['harness_run']` JSON string at seal time (stages: tool, version, commit, run key, job, sealed; decisions), and `emit.build` and scProfile carry it and the QC columns forward. **Success:** a fixture run's final object lists all four stages, and Lab copies the record (P10). |
| GAP-P21 | PLAT.3 G6 PROF.4 | scrnaseq-studio + scrnaseq-lab | The harness's own results cannot be explored. scProfile's tables (DE, communication edges), `report.json` and reports have no path in. Numeric cell-level results are dropped (categorical extras only). Studio computes its own Wilcoxon DE instead of showing scProfile's. | `Landing.tsx:102` (`.zip`/`.scstudio` only); `SetEditor.tsx:141`; `build.ts:404-410`; scProfile README:195-214 | L | P09, P10, P19 | GAP-055 (no promoted stage-4 run, for a real test) | An additive `results/` entry in the collection (method, contrast, unit, schema) built from `report.json` and `tables/*.csv`. A Studio Results tab lists them per contrast in the run's own words. Start with one DE table. **Success:** a fixture `report.json` renders, and the gene rows link to Gene expression. |
| GAP-P22 | A2.2 G2 PLAT.3 | scrnaseq-studio | Studio claims a DESeq2 test it never runs, in the README, the Overview copy and the generated Methods text in pseudobulk mode. That last is the paragraph users copy into papers. | `README.md:72`; `Overview.tsx:101`; `Methods.tsx:146-153`; against `Stats.tsx:470-473`, `:508-510` | S | — | — | Pseudobulk copy becomes "summed counts exported for DESeq2; no test was run here". **Success:** a test renders Methods in pseudobulk mode and asserts that "tested with DESeq2" is absent; the README is fixed. |
| GAP-P23 | A2.2 G2 | scrnaseq-studio | Studio's docs present unbuilt features and stale numbers as current: the bundle size (83 against 157 kB gzip), "we already ship webR", direct .h5ad/.rds reading, and thresholds read from `uns` with a MAD preview filter. | `README.md:169`; build log; `DESIGN.md:44`, `:24-64`, `:283-286`; `package.json:14-18` | S | — | — | Mark DESIGN sections as shipped or planned, and re-measure the README numbers with the existing `scripts/bench-bundle.mjs`. **Success:** 10 resampled claims, 0 false. |
| GAP-P24 | PLAT.3 QC.2 | scrnaseq-studio + scrnaseq-lab | Studio cannot show the QC decisions behind the cells (each threshold, who decided it, removal per arm), which are what produced the object. DESIGN.md claims it reads them. | `DESIGN.md:283-286`; no threshold code in `src/`; GAP-020 (scQC's `decided_by` reaches `report.json` only) | M | P10, P20 | — | Lab copies scQC's parameter block from the run record into `meta.run.qc`, and Studio's QC card draws each threshold with its class (DERIVED, DECLARED, ADJUDICATED). **Success:** a fixture record renders its lines on the violins. |

---

## 4. Blockers

None of these needs to stop a platform wave from starting; P01–P05 and P09–P18 can begin today.

| id | blocks | what | who clears it |
|---|---|---|---|
| **B1** | A6.3's last clause (GAP-P06) | "The harness runs it as A1.1's input" needs a single entry point that runs a cohort. GAP-001: no stage driver, and the kernel refuses PBS. The Service can produce correct inputs before that exists. | HARN lane (GAP-001) |
| **B2** | A6.2's "shows the run" in full (GAP-P20) | Where the run record lives (embedded in the object as `uns['harness_run']`, or a sidecar file) and who writes it at seal time. Embedding keeps "nothing uploaded" and needs no folder drop. | (C) design: the pre-decider decides; HARN with INT and PROF lanes |
| **B3** | "no manual conversion" inside a sealed run | Lab's converter needs Node 24 or later. Whether Node can run under PBS on the cluster is UNKNOWN (no access in this review); no tool environment declares Node. Alternative: run the conversion on the workstation after pulling the object, which rule 3 exempts as workstation work. | (C) design: the pre-decider decides; HARN lane |
| **B4** | grading A6.2 PASS on a real object | The final objects (SAMBO stage 3 `cohort_integrated.h5ad`, size not measured here; C46 has not reached stage 3, GAP-056) live on the cluster. A real conversion needs a pull or a PBS run. Until then the real-object result is UNKNOWN. | coordinator (a cluster deploy lane) |
| **B5** | GAP-P07 only | The bulk consumer is `~/.claude/skills/rnaseq-hpc-request`, outside the eight repositories. The safe path needs no change to it: bulk requests stay byte-identical. | PI, only if the skill is to be edited |

---

## 5. Leanness (concrete items only)

1. **Unrunnable browser scripts.** 31 scripts import `playwright-core`, which neither `package.json` declares, and 33 hard-code `C:/Users/<dev>/…` paths. In Studio, 23 do both (22 `probe-*.mjs` and `shot-names.mjs`). In Lab, 8 do both (`browser-*.mjs` ×5, `convert-atlas.mjs`, `verify.mjs`, `which-cluster.mjs`), and `e2e.mjs` and `check-names.mjs` carry Windows paths only. They run on no machine but one. Delete them, or port the few still wanted into one declared, portable end-to-end check (GAP-P18).
2. **`scrnaseq-lab/probe_2`.** An empty file tracked at the repository root since `c866245`.
3. **Three writers of one format, already diverged.** Lab's `build.ts`, Studio's `tools/export_h5ad.py` and Studio's `tools/export_seurat.R` all write bundle@1. The Python exporter splits samples that span conditions and Lab does not (GAP-P14). The Python exporter writes no `expr.chunk.bin`, so it is slow on large objects. With Lab as the converter A6.2 names, retire the Studio exporters or make them thin wrappers around Lab's CLI.
4. **Demo-specific code in general paths.** `s.replace(/^(SVZ|TC)_/, '')` in `Overview.tsx:200` and `Composition.tsx:65` applies the built-in demo's sample-id prefixes (`demo.ts:126-145`) to every object, so a real sample named `TC_…` loses its prefix in the QC and composition axes.
5. **The bundle schema is declared twice** (`scrnaseq-lab/src/lib/build.ts:79-118`, `scrnaseq-studio/src/lib/bundle.ts:61-122`). Keep one module or JSON Schema, vendored with a checksum test (GAP-P18).
6. **`docs/prototype.html`.** Studio 105 kB, Service 57 kB. Both READMEs say `src/` supersedes them. Candidates for the housekeeping pass unless someone still uses them for layout trials.

---

## 6. The order of the first platform waves

| wave | gaps | lane | why first, in one line |
|---|---|---|---|
| **P-1** | P09, P11, P13, P16 | PLAT (Lab) | One tested, flagged, deterministic Lab CLI turns the hand-off that works today by hand into an automatic one, and every later platform wave builds on it. No other lane is needed. |
| **P-2** | P10, P19 | PLAT (Lab, then Studio) | The scIntegrate provenance already in the object is enough to make Studio "show the run": the cheapest route to A6.2's second clause. |
| **P-3** | P22, P23, P17, P08 | PLAT (all three, docs) | All S. Clears every A2.2 FAIL found, and stops Studio writing a false DESeq2 sentence into users' Methods. |
| **P-4** | P01, P02, P03, P04 | PLAT (Service) | A single-cell mode that emits scQC's samplesheet, `design.csv`, the registry row and the axes, with the bulk path byte-identical. This makes A6.3's half on the platform side real. |
| **P-5** | P12, P14, P15, P18 | PLAT (Lab and Studio) | The contract fixes (sentinels, crossed designs, latent dimensions) and the cross-repository CI that keeps them fixed. |
| **P-6** | P05 | PLAT (Service) | Pre-fills the doublet rate, chemistry and build from small local files, after the single-cell model exists. |
| **P-7** | P20, P24 | INT, PROF, HARN with PLAT | Carries the whole stage chain and the QC decisions in the final object. It needs B2 decided. |
| **P-8** | P06 | HARN | The intake that runs a Service request as A1.1's input. It waits on GAP-001 (B1). |
| **P-9** | P21 | PLAT (Studio and Lab) | The harness's own results in Studio. This is the largest item, and it is worth most once stage 4 has a promoted run (GAP-055). |

---

## Appendix: how to re-run the evidence

All paths are under `/private/tmp/claude-501/-Users-admin-Desktop-single-cell-harness/8e478647-376c-4355-a6e1-64df5e358036/scratchpad/platform_review/`.

- **CI steps.** `scripts/run_ci.sh <clone> logs`. Per-step return codes are in `logs/<repo>.summary`; outputs are in `logs/<repo>.{ci,lint,test,build}.log`.
- **Family-shaped objects.**
  - `venv/bin/python scripts/sci/make_final_object.py OUT.h5ad --factors name:l1,l2 [--factors …] [--label-key …]` uses scIntegrate's own `emit.py` (copied byte-identical) and the pinned anndata 0.13.2 and pandas 3.0.5.
  - Four objects are in `fixture/`: two-factor with neutral names, two-factor with conventional names, one-factor genotype, and an scAnno-labelled object.
- **Lab.**
  - `node scripts/convert-node.mjs IN OUT`, run in `clones/scrnaseq-lab`. Logs: `logs/lab-convert-*.log`.
  - Studio opening the result: `node scripts/check-studio-open.mjs OUT`, with the two clones side by side.
  - Bundle metadata: `scripts/inspect_bundle.py`.
  - Byte reproducibility: `scripts/cmp_bundles.py`.
  - Default string encoding: `scripts/sci/rewrite_default_encoding.py`, which reproduces the crash.
- **Service.** `node scripts/service_sc_probe.mjs clones/rnaseq-service` runs the app's own `isFastq`, `isJunk` and `buildSamples` on Cell Ranger and CeleScope file lists with synthetic names.
