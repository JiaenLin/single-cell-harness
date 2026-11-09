> Copied 2026-11-09T13:55:14Z from the W027 research agent's report. Every number in candidate 1 was second-read by the coordinator against the CELLxGENE curation API and the CELLxGENE data submission policy (see the decision at the end).

# W027 scale cohort for A3.4: three candidates, ranked

Research agent report, 2026-11-09. Nothing was downloaded except metadata: the CELLxGENE dataset index
(JSON, 9.9 MB), Explorer obs schemas (column names and categories only), collection records, GEO and
HCA records, two Allen tables under 40 KB, and paper texts. All of it is in `meta/`, `geo/`, `allen/` and
`papers/` beside this file.

**How the field was searched.** The CELLxGENE curation API lists 2,269 public datasets. 68 of them have
at least 1M cells. 14 of those are single studies with a disease or exposure arm and a normal arm across
donors, and all 14 are human. The rest are atlases, integrations, subsets or non-primary copies. Outside
CELLxGENE I checked GEO, HCA, Allen ABC, Parse and EasySci.

**Evidence shared by the three CELLxGENE candidates.**
- **Licence.** The contribution page says: "anyone will be able to access it subject to a CC-BY 4.0
  license". https://cellxgene.cziscience.com/docs/032__Contribute%20and%20Publish%20Data
- **Raw counts.** Schema 7.1.0, matrix table, line 199: "scRNA-seq (UMI, e.g. 10x multiome, 10x v3,
  Slide-seqV2) | REQUIRED. Values MUST be de-duplicated molecule counts ... | `AnnData.raw.X` unless no
  "normalized" is provided, then `AnnData.X`". The contribution page also says "raw counts are required".
  All three datasets are at schema 7.1.0.
  https://github.com/chanzuckerberg/single-cell-curation/blob/main/schema/7.1.0/schema.md
- **Cell set.** The schema says "any cell filtering MUST be applied to both" matrices. So each h5ad holds
  the authors' filtered cells, not droplet-level matrices.

---

## 1. SLE lupus PBMC, Perez et al. 2022 Science

- **Accession.** CELLxGENE dataset 218acb0f-9f2f-4f76-b90b-15a4b7c7f629, in collection
  https://cellxgene.cziscience.com/collections/436154da-bcf1-4130-9c8b-120ff9a888f2
  - GEO GSE174188 holds metadata only. Its sample GSM5288728 lists its supplementary file as NONE.
  - HCA project 9fc0064b-84ce-40a5-a768-e6eb3d364ee0 holds 800 FASTQ files (5,890.58 GB). Azul reports
    `accessible: true` and no data-use restriction.
  - dbGaP phs002812 holds the genotypes.
- **Licence.** CC BY 4.0 (CELLxGENE).
- **Cells.** 1,263,676, all primary (from metadata).
- **Samples and donors (obs).** 261 `donor_id`, 274 `sample_uuid`, 291 `suspension_uuid` and 88
  `library_uuid`. The 88 libraries match GEO's 88 samples, which are 10x wells of pools.
  - The paper gives 264 unique samples and 91 replicates, run in 23 pools across 4 batches.
- **Assay, species, tissue.** 10x 3' v2, cells, human, blood (PBMC).
- **Design.** The `disease` column is SLE against normal. The collection and paper give 162 SLE and 99
  healthy controls.
  - The SLE arm includes 19 flare cases and 10 matched post-flare-treatment samples, recorded in
    `disease_state` (flare, managed, treated, na).
  - Covariates: `self_reported_ethnicity` (4 levels), sex, age stage, `Processing_Cohort` (4 levels).
- **Replicates per arm.** 162 donors against 99 donors.
- **Format and size.** h5ad, 12,218,105,530 bytes. It has 30,172 genes, mapped to GENCODE 19; GEO says
  hg19.
- **Raw counts.** Required by the schema (see above). There is no other public matrix, because GEO has no
  files.
- **Author labels.** Yes: `author_cell_type` (11 types), `ct_cov` (15 types), plus CL `cell_type`.
- **Known issues.**
  - The chemistry is v2: the mean is 791.9 genes per cell.
  - Libraries are pools: donors were assigned by freemuxlet (mean doublet rate 22.12%). So the 10x
    library is not the sample.
  - The cells are the authors' post-QC set. After freemuxlet, Scrublet and platelet/RBC removal, 1,444,450
    cells became 1,263,676 (paper).
  - Controls come from two sources, the UCSF clinic and ImmVar. The author contributions list ImmVar
    sequencing as done by different people. How arms spread over the 4 batches (fig. S1B) was not read.
  - GEO says raw and processed data "will be made available in dbGaP ... through controlled access", yet
    CELLxGENE and HCA serve them openly.
- **Sources.** Paper: https://stacks.cdc.gov/view/cdc/119561 (author manuscript PDF, DS1).
  GEO: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE174188

## 2. Parkinson's disease, multi-region single nuclei, Sci Data 2024 (doi 10.1038/s41597-024-04117-y)

- **Accession.** CELLxGENE dataset d3cb449b-c2b1-4b50-a7f1-21203535fe61, in collection
  https://cellxgene.cziscience.com/collections/d5d0df8f-4eee-49d8-a221-a288f50a1590
  - The original deposit is the AMP PD Knowledge Platform (Terra, Release 4). Its access terms were not
    checked.
- **Licence.** CC BY 4.0 (CELLxGENE). The paper is also CC BY.
- **Cells.** 2,096,155 nuclei, all primary.
- **Samples and donors.** 97 `donor_id` in the file. The paper has 100 donors: 75 PD and 25 controls.
- **Assay, species, tissue.** 10x 3' v3, nuclei, human, brain. Five regions: DMNX, medial globus pallidus,
  prefrontal cortex, primary motor cortex and primary visual cortex.
- **Design.** PD against normal (`disease`). Region is a second factor. Covariates: sex, age,
  `Brain_bank` (4), PMI, RIN, `path_braak_lb`.
- **Replicates per arm.** 75 against 25 (paper). The per-region counts were not measured.
- **Format and size.** h5ad, 30,547,659,019 bytes.
- **Raw counts.** Required by the schema.
- **Author labels.** Yes: `derived_class2` (12 classes), plus CL `cell_type` (11).
- **Known issues.**
  - It is twice the target size, at 2.1M nuclei.
  - Only 17,266 genes are present (the other 10x sets here have 27,131 to 35,483), so genes were
    filtered before deposit. This is an inference from the gene count.
  - There is no library or sample column, so a sample would have to be donor × region.
  - The paper says: "four brain banks, each contributing different proportions of cases and controls".
  - The file has 97 donors against the paper's 100, and the reason is not stated.
- **Source.** https://pmc.ncbi.nlm.nih.gov/articles/PMC11585549

## 3. COVID-19 immune atlas, Ren et al. 2021 Cell

- **Accession.** CELLxGENE dataset 9dbab10c-118d-496b-966a-67f1763a6b7d, in collection
  https://cellxgene.cziscience.com/collections/0a839c4b-10d0-4d64-9272-684c49a2c8ba
  - GEO GSE158055: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE158055
  - Raw reads: GSA-human HRA001149. Its access terms were not checked.
- **Licence.** CC BY 4.0 (CELLxGENE). For GEO, NCBI "places no restrictions on the use or distribution
  of the data", but notes that submitters may claim rights. https://www.ncbi.nlm.nih.gov/home/about/policies/
- **Cells.** 1,462,702, of which 1,421,129 are primary. The 41,573 non-primary cells are flagged
  duplicates.
- **Samples and donors.** 196 `donor_id` and 284 `sampleID`. The paper has 171 patients and 25 healthy
  controls.
- **Assay, species, tissue.** 10x 3' v3 and 10x 5' v2, cells, human. Tissues: blood (PBMC, including
  sorted B/T fractions), lung (12 BALF and 1 PFMC) and saliva (22 sputum).
- **Design.** Three explicit columns:
  - `disease`: COVID-19 against normal.
  - `CoVID-19 severity`: control, mild/moderate, severe/critical.
  - `Sample time`: control, progression, convalescence.
  - The COVID samples fall into moderate convalescence 89, moderate progression 33, severe convalescence
    51 and severe progression 83. The other 28 of the 284 are not assigned in the text read.
- **Replicates per arm.** 25 control donors against 171 patients.
- **Format and size.** h5ad, 13,970,529,362 bytes. GEO also has
  `GSE158055_covid19_counts.mtx.gz` (8,171,063,470 bytes), plus barcodes, features, cell annotation
  (9.4 MB) and sample metadata.
- **Raw counts.** Required by the schema. GEO says separately: "processed data (raw counts in sparse
  matrix format)".
- **Author labels.** Yes: `celltype` (64 types), `majorType` (12), plus CL `cell_type` (18).
- **Known issues.** Heavy technical heterogeneity:
  - 37 centres (12 `City` values) and three sequencing platforms (DIPSEQ, BGISEQ, Illumina).
  - Two chemistries, and 10 `Sample type` values (fresh/frozen PBMC, sorted B/T, BALF, sputum, PFMC).
  - "186 out of 284 samples were unpublished", so 98 are reused from other studies.
  - Quantified with kallisto, not Cell Ranger.
  - The control arm is small: 25 donors.
- **Source.** https://pmc.ncbi.nlm.nih.gov/articles/PMC7857060

---

## Ranking reasons

1. **Lupus.** It is the only candidate with one tissue, one assay and one suspension type, and the whole
   design is in obs. It has 162 against 99 donors, and it is the smallest file and lightest matrix above
   1M.
2. **Parkinson's.** It is the cleanest two-arm single-nucleus design (75 against 25), with region as a
   second factor, so it exercises the `snrna` rules. Against it: 2.1M nuclei, filtered genes and no
   library IDs.
3. **COVID-19.** Its control, severity and stage columns are explicit, and it has two public sources (h5ad
   and GEO MTX). Against it: centre, chemistry, tissue and sorting are tangled with the design, and only
   25 donors are controls.

**Load estimate (inference, not measured).** Nonzeros ≈ cells × the metadata's mean genes per cell.
| | estimated nonzeros | multiple of 2^31−1 (2,147,483,647) |
|---|---|---|
| Lupus | 1.00e9 | 0.47 |
| COVID-19 | 2.30e9 | 1.07 |
| Parkinson's | 6.61e9 | 3.08 |

2^31−1 is R's vector-length limit (32-bit indices). The spam package documents the same ceiling for
sparse nonzeros (https://rdrr.io/cran/spam/man/large_matrix.html). Any R step that holds the whole matrix
in memory would need 64-bit or on-disk storage for candidates 2 and 3.

## Also considered, not ranked

| dataset | why not ranked |
|---|---|
| Allen aging mouse brain, Jin 2025 Nature (s3://allen-brain-cell-atlas, Zeng-Aging-Mouse-10Xv3) | The best mouse option. ~1.2M cells (stated, not counted) in a raw h5ad of 13.85 GB, CC BY-NC 4.0, 847 clusters. `donor.csv` gives 64 adult donors (2 months) against 44 aged donors (18 months) and 287 libraries. But 63 of the 64 adult donors come from the earlier Whole Mouse Brain study, so age is confounded with study. 88 of the 108 donors are Snap25-Cre;Ai14 reporter mice with mixed FACS enrichment. Its factor label "aged" is shared with SAMBO's age factor, which weakens held-out leak detection. |
| KPMP kidney v2 (CELLxGENE 7ff0197b) | 1.39M nuclei, 223 donors, 308 libraries, 13.82 GB, AKI/CKD against reference. Two nuclear assays. The per-arm counts could not be measured because bioRxiv returned 403. It is a preprint, and the reference tissue comes from different collection routes. |
| SEA-AD MTG/DLPFC (c2876b1b / 6f7fd0f1) | 50.8 to 53.2 GB. The collection itself warns that the CELLxGENE copy has "dramatically reduced metadata and a reduced number of genes". The design is a pathology continuum. |
| IBDverse (0e5c75da) | 1.85M cells, 32.26 GB. Rectum has controls only (275 non-IBD donors); ileum has 243 non-IBD against 119 Crohn's. |
| PsychAD HBCC (5c97eeeb) | 40 combined diagnosis strings, and ages range from 1 month to adulthood. |
| ALTRA RA (789ad837) | 2.03M cells, 89 donors, 139 samples. The groups are at-risk, early RA and control (HC1). Samples span 12 visit types, including flu-vaccine and COVID-19 visits, and their balance across groups was not measured. Longitudinal. |
| Cerebellum ET (24921392) | 1,004,112 nuclei, so post-QC it would fall below 1M. SPLiT-seq. |
| Parse 10M PBMC cytokines | 9,697,974 cells, 12 donors, 90 cytokines against PBS, CC BY-NC 4.0, 41 GB h5ad. About 10 times the target. |
| EasySci mouse brain, Sziraki 2023, GSE212606 | About 1.5M nuclei, WT n = 4 per age. But the counts are one text sparse matrix inside a 13 GB tar that also holds ATAC data. |
| OneK1K, AIDA, Sound Life, Immune aging | No control arm. |
| PD multiome 4.5M, PsychAD MSSM 4.14M, Crownlands 4.03M, Immunobiology of Aging 3.76M | Larger than needed. |

## Could not establish

- **Donors per arm from the files themselves.** These need per-cell obs and were not fetched. The arm
  counts above come from the papers and collection pages.
- **Which slot holds the counts.** Not checked in any h5ad (raw.X or X).
- **Lupus.** How the arms spread over the 4 batches, and why there are 274 sample IDs against the paper's
  264.
- **Parkinson's.** Why the file has 97 donors against the paper's 100, and the AMP PD access terms.
- **COVID-19.** The HRA001149 access terms, and which tissues the 25 controls supplied.
- **Allen aging.** The exact cell count and the genes per cell.
- **Memory and time on the cluster.** These are estimates only.

## Decision, 2026-11-09T13:55:14Z (the coordinator, under the pre-decider: a (C) design choice, gap review table A7)

**The A3.4 scale cohort is candidate 1, the lupus PBMC atlas** (Perez et al. 2022, Science; CELLxGENE dataset
218acb0f-9f2f-4f76-b90b-15a4b7c7f629). It was chosen because it has one tissue, one assay and one suspension type;
the whole design is in the cell table (SLE 162 vs healthy 99 donors); the authors' labels are present; and at about
1.0e9 nonzeros it stays under the 32-bit sparse-index ceiling that would break whole-matrix R steps on candidates 2
and 3.

**The second read** (curation API, collection 436154da-bcf1-4130-9c8b-120ff9a888f2):
- cell_count 1263676, all primary;
- assay 10x 3' v2; suspension_type cell; Homo sapiens; blood;
- disease normal and systemic lupus erythematosus; 261 donor_id values;
- schema 7.1.0; h5ad 12,218,105,530 bytes.

The licence: the data submission policy says "anyone will be able to access it subject to a CC-BY 4.0 license".

**What staging needs:**
- The file holds the authors' FILTERED cells, not droplet matrices, so stage 1 needs scQC to accept called-cell input
  (B1-046, in W020).
- Libraries are donor pools demultiplexed by freemuxlet, so sample = donor and a library is not a sample.
- The download (12.2 GB) and transfer follow the HPC layout's transfer rules, in a later wave.
