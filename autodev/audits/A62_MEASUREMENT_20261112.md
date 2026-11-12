# A6.2 measured on the first cohort's joint object (m-A6.2, 2026-11-12)
**Asked:** GOALS A6.2, "The family's final object opens in scRNA-seq Studio through Lab's converter, with no manual conversion. Studio shows the run that produced it", two halves of 1. **Done:** two deployed tools run on one real file; nothing built, no repository changed, no cluster touched.
**Result: 1 of 2.** Half 1 YES, half 2 PARTLY. Working notes, scripts, logs and screenshots: `SCRATCH/a62/` (`NOTES.md`, `scripts/`, `work/`, `shots/`, `out/cohort.zip`).

## The object and the tools
`cohort_integrated.h5ad`, 3,212,212,267 bytes, md5 `ff5f5173968b539e8e90a3f2b4e91ab7` before and after (never opened for writing). Read independently with h5py 3.16 (read-only); the bundle read with Python's `zipfile`. Neither check uses the lab's code.
Lab: a fresh worktree at `origin/main` = `fdb8888`, `npm ci`, Node 26.7. Studio: a fresh worktree at `origin/main` = `e475703`, `npm ci`, `npm run build`, served by `vite preview`, opened in headless Chromium at 1440 wide.

## 1. What the object holds
| | measured |
|---|---|
| cells, genes | **100,713** (not about 109 thousand), 34,290 (466 named by accession, the rest by symbol) |
| matrices | `X` float32 log-normalised (expm1 row sums 9,999.998 to 10,000.002); `layers/counts` int64, all integer, 173,783,317 UMIs: the counts; `layers/lognorm` bit-equal to `X`; no `raw`. Each 108,364,306 stored values |
| embeddings | 5 latent spaces (three 50 wide, two 30 wide) and 6 two-column UMAPs; `X_umap` is bit-equal to `X_umap_scanvi`; 2,086 rows are NaN in all 11 (exactly the `EXCLUDED` cells) |
| obs, 9 categorical columns | `sample` 10; four design factors of 2 levels each; `cell_type` 15 (13 types + `EXCLUDED` 2,086 + `UNRESOLVED` 2,139); `cell_compartment` 9; `cell_type_forced` 14; `cell_compartment_forced` 8 |
| compression | none: 289 datasets, no filter on any |
| run records in `uns` | **one**: `uns/scintegrate/provenance`, a group of 32 entries. `uns` has one top-level entry: no `uns/harness_run`, no record of the QC or annotation stage |

The record's six named fields: `tool` = "scintegrate", `version` = "0.7.0", `commit` = "2fc7a6c6e5f80a007de51903b8579e5cb6aa9676" (strings); `job` = a GROUP of three (scheduler "pbs", an id beginning 791471, a host); `stage` and `run_key` ABSENT.
The harness's run key (`20261112T022451Z__sch-133589d__03_integrate__scintegrate-2fc7a6c`) is in the object only inside two path strings (`argv`, `design`), never as a field. `uns/scintegrate/default_method` = "scanvi".

## 2. The conversion
The README's command, inside the clone (allowed there without `npm link`), with **no flag and no `NODE_OPTIONS`**: `node bin/scrnaseq-lab.mjs convert cohort_integrated.h5ad out/cohort.zip`
| | |
|---|---|
| manual steps | **0**: no flag, no edit of the object, no helper script, no retry, no source read |
| exit, wall time, peak memory | 0; 61.27 s; 1,841,053,696 bytes resident (1.84 GB) |
| guesses printed | `--cluster cell_type`, `--sample sample`, `--condition` the first design factor, `--extra` the other three, `--interaction none`, `--embedding X_umap`, both sentinels, `--label` the file name |
| notes, warnings | 14 notes, 0 warnings, 0 errors. "not carried: cell_compartment, cell_type_forced, cell_compartment_forced (each can be added with --extra)" |
| bundle | 836,415,999 bytes; `collection.json` + 10 parts split along `sample` (65.2 to 153.9 MB), each 18 files; no `pseudobulk.tsv`; `hasRawCounts` false |

## 3. Is the bundle the object?
| compared | result |
|---|---|
| cells, genes, gene names | 100,713 = 100,713; 34,290 = 34,290; `genes.txt` equals `var/_index` in every part |
| 20 genes, `random.Random(62).sample(range(34290), 20)`: total in the bundle against `X` (the matrix the converter says it used) | 20 of 20 equal, difference 0.0; their 54,822 stored values equal cell by cell |
| all genes (beyond the draw) | 34,290 totals, largest difference 0.0; stored values 108,364,306 = 108,364,306 |
| 200 cells, `random.Random(62).sample(range(100713), 200)`: `X_umap` coordinates | 200 of 200 bit-equal (9 of them NaN on both sides) |
| all cells (beyond the draw) | 5 carried embeddings x 100,713 rows bit-equal |
| sample by condition | 10 of 10 table cells equal (6 samples at one level, 4 at the other; 7,298 to 14,400 cells) |
| `cell_type` levels; the three extras | 15 of 15 counts equal, 0 cells differ; 2 of 2 counts equal for each extra, 0 cells differ |
| **not in the bundle** | `layers/counts`; three annotation columns; and the per-cell "counts" in `qc.f32` are sums of log-normalised values (831 to 5,573), not UMIs (350 to 141,059) |

## 4. The Studio
Opens: the tab list after 445 ms, 9 tabs, **0 page errors on every tab** (two passes). Overview: 100,713 cells, 34,290 genes, 10 samples, 2 groups, 13 cell types, 4 fewest samples per group: all true. Five embeddings offered; `X_umap` drawn, split by group.
The Run card, every sentence: "The run that produced this object" / "1 record listed from the object's uns. Of it, this bundle holds up to six fields as recorded: tool, version, commit, stage, run_key and job." / `uns/scintegrate/provenance`, "3 of 6 fields" / "Where the converter looked: uns/harness_run; every entry of uns, and every child of a dict directly under uns, named provenance or *_provenance; every dict directly under uns whose own schema names provenance".
| field | the object's `uns` | the card | |
|---|---|---|---|
| tool | "scintegrate" | scintegrate | equal |
| version | "0.7.0" | 0.7.0 | equal |
| commit | "2fc7a6c6…6aa9676" (40) | the same 40 | equal |
| job | a group: scheduler, id, host | no row (the notes card: "not carried: job (a group) and 28 other entries") | not shown |
| stage, run_key | absent | no row | nothing to show |

**Shown, and false of this object** (screenshots `shots/cohort.Overview.png`, `cohort.Cells.png`, `cohort.w1440.png`):
1. "Batch integration: from your file: harmony", and Methods: "Inter-sample variation was corrected with harmony, as recorded in the object", with the Harmony reference. The object records scanvi, and the UMAP that opens is the scanvi one. The lab says harmony whenever an embedding's name contains it (`src/lib/h5ad.ts:1298`); this object compares five methods.
2. "Raw counts: not found: absent". The object holds them. A split object streams one matrix and the display matrix wins (`src/lib/build.ts:291-294`); no note says counts were present and left out, and no flag brings them.
3. "Wilcoxon runs here; pseudobulk counts can be saved … the counts summed per sample can be saved for DESeq2" (Overview). On this bundle "Pseudobulk · save counts" is disabled.
4. The QC violin "Total counts" plots sums of log-normalised values (the last row of section 3).
5. "Drawn grey: 4,225 cells the annotator did not call": 2,086 of them have no coordinates in the object. INFERENCE from the data; the points on the canvas were not counted.

Imprecise: "Gene identifiers: symbols" (466 are accessions); "Normalization: not found: not recorded" (the object states it in `uns`).

## 5. The browser path
README: "no size limit" (three times), "Any size is accepted"; one known limit, that writing more than a few hundred MB needs `showSaveFilePicker` (Chrome, Edge).
One headless try of the built app, five-minute limit: questions on screen 1.5 s after the file was given; Convert enabled on the app's own picks; "Converted" at 57.2 s, "100,713 cells · 34,290 genes · 836.4 MB"; 0 page errors. **The save was not measured** (a native save dialog cannot be answered headlessly), so the web bundle's bytes were not read.
Said by the app before converting: "Pseudobulk DESeq2: yes: 6 v 4 samples per group" under "nothing turns up empty later", and "All 11 travel in the file" of the embeddings (5 travel).

## The two judgements
1. **The final object opens in the Studio through the lab's converter with no manual conversion: YES.** The documented command with no flag, exit 0 in 61 s; every value the bundle carries equals the object's; the Studio opens it with 0 errors. What it lacks is not a manual step: the counts layer does not travel (so pseudobulk is off for the family's object), and three annotation columns travel only on `--extra`.
2. **The Studio shows the run that produced it: PARTLY.** The card lists one record, and it is the producing tool's own: tool, version and commit, each equal to the object's, the commit being the integration tool's `main`. It shows nothing that identifies the RUN: no job (a group in the object, which the lab does not carry), no run key and no stage (not fields of the object), no date, no input, no harness record (no `uns/harness_run`). A user can tell which code made the object and cannot tell which run: any run of that commit, on any input, gives the same card. To become YES the writers record `job`, `run_key` and `stage` as short strings (or the harness writes its record); the lab at `fdb8888` would then carry them.

## Limits
- One object, one conversion, default guesses only; no flag combination was tried. The cluster's md5 was given, not re-read.
- The gene-chunked copy of the expression (`expr.chunk.bin`, what the Studio reads per gene) was not decoded; the flat copy was.
- No gene was plotted, no marker or contrast run; errors were read about a second after each tab opened.
- The web app's save and its bundle were not measured; the falsehoods in section 5 are the app's words, not a read of its bundle.
- The deployed sites were not opened: both tools were built from the two `main` commits and run locally.
