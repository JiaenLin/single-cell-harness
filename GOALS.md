# Goals: what the single-cell harness family is for

**Status** the project goal, set 2026-11-09 by the PI ("set the goal as the project goal that we are
moving towards"). **Source** `report/Single-Cell Harness.pdf` (Lin Jiaen, November 2026, 17 slides).
The current family is far behind these goals. [`autodev/`](autodev/) is the program that closes the
gap, and [`autodev/STATE.md`](autodev/STATE.md) records how far it has got.

The goals are in four layers. **Layers 0–2 are the report's words** (slide numbers in brackets):
they change only when the PI changes the report or says so. **Layer 3 is the coordinator's
draft (C)**. It lists the tests the audit uses to decide whether a layer-2 capability exists. The
coordinator may adjust it and must say so. The PI's reading of a goal always wins over layer 3.

Every goal also states what it does **not** require. A goal is never read more widely than its
words. Being too strict is a defect, and so is being too loose.

**Scope of the development program.** The program covers eight repositories: the harness
(`single-cell-harness`); the four tools (`scQC`, `scAnno`, `scIntegrate`, `scProfile`); and the
scRNA-seq Studio platform, made of `scrnaseq-studio`, `scrnaseq-lab` and `rnaseq-service`. The PI
added the platform on 2026-11-09: "yes include Studio, Lab and Service". The bulk RNA-seq products
`rnaseq-studio` and `rnaseq-lab` are not part of it. `rnaseq-service` also serves bulk requests, and
that path must keep working.

---

## Layer 0: the mission

> **"Single-Cell Harness: autonomous agentic workflow for unlimited single cell analysis"** [1]
> **"Single-Cell harness aims to be all you need for single cell analysis"** [4]

The report gives two reasons. **Scale** calls for AI automation [2]: more than 500 million public cells
(scBaseCount: 27 organisms, 75 tissues) and 1,856 analysis tools (scRNA-tools catalogue, November 2026).
**Reproducibility** is the community's requirement [3]: reproducible code and workflow, proper
documentation, and easy reproduction.

## Layer 1: outcomes (what a user gets)

| id | outcome | source | does NOT require |
|---|---|---|---|
| **G1** | **Automated end to end.** The typical analysis runs from processed data to reports without hand work, and the tools' environments set themselves up. | [2] the ten typical steps; [16] "End-to-end automated data processing", "Automated running environment setup" | That the family performs alignment itself. Step 1 output (Cell Ranger / CeleScope) is an accepted input. |
| **G2** | **Reproducible.** Reproducibility code and workflow, proper documentation, easy reproduction. | [3]; [16] "reproducible workflow" | Identical floating-point output where a method itself varies between runs. Such an output is named, with its measured spread. |
| **G3** | **Unlimited and design-aware.** Works on any cohort: organism, tissue, assay, platform and experimental design. | [1] "unlimited"; [2] 27 organisms, 75 tissues; [16] "Design-aware/customized analysis" | One pipeline for every assay. Single cells and single nuclei are separate rule sets (PI, 2026-10-02). |
| **G4** | **Expandable tool pool built from published methods.** Turns the 1,856 published tools into standardised plugins that are plug-and-run and AI-native. | [8] the ultimate aim; [16] "Based on peer-reviewed published methods", "expandable plugin pools (Ongoing)"; [17] "A Scientific tool pool with standardized format for agentic use" | That all 1,856 tools are converted. The goal is a maker that can convert them, and a measured success rate. |
| **G5** | **Interpretation and hypothesis generation.** A built-in AI co-scientist writes the report, interprets the results, generates hypotheses, validates and audits them, and feeds back into the analysis plan. | [9] "AI Scientist (Agent) (TBD)"; [16] "To be done"; [17] "Build-in AI Co-Scientist" | That the agent's conclusions are accepted unchecked. Every claim is audited against the data (G5's own "Audit"). |
| **G6** | **A user-facing platform.** Results reach wet-lab users. A web interface like Codex or Claude Code lets a user ask for an analysis and follow it. | [4] scRNA-seq studio, "Harness UI (TBD)"; [17] "A Codex/Claude code like user-interface (web based)" | Uploading data. Studio and Lab work in the browser with "nothing uploaded", and that property stays. |
| **G7** | **Agent-operated.** Working agents assemble the workflow, coordinate it, audit it and record it. | [4] "Working agents: Assemble workflow, coordinate, audit and record"; [1] "autonomous agentic workflow" | That every decision is the agent's. Decisions declared as the user's stay the user's: design, sign conventions, thresholds the data cannot decide. |

## Layer 2: capabilities (who delivers what)

### The in-house analysis modules [4]

| id | capability | owner | source |
|---|---|---|---|
| **QC.1** | Data-aware automated QC in declared steps: ingest, ambient handling, cell call, light floor, doublets, quality (count floors derived from the data, mitochondrial ceiling per library), cluster check, and apply, which is the only step that removes cells. Working out a threshold is kept separate from applying it. | scQC | [5], [11] |
| **QC.2** | A QC report that shows the thresholds, who decided each one (data or user), and figures. The results tree has a `figures/` directory: "nothing writes one yet" [5]. | scQC | [5], [11] |
| **ANNO.1** | Consensus-based, scope-based hierarchical annotation (all cells, then lineage, then type) that stops at the depth the markers support ("the label stays at Lymphoid"), using CellMarker 3.0. | scAnno | [6], [12], [13] |
| **ANNO.2** | "Ultra-fast, consistent" annotation: the same labels from the same input, and a measured speed. | scAnno | [6] |
| **INT.1** | Benchmark-guided batch integration: batch-effect evaluation, multi-algorithm runs, an scIB benchmark, and a final integrated object with a report (by cell type and by batch). | scIntegrate | [7], [14] |

### The universal tool runner [4], [8], [9]

| id | capability | owner | source |
|---|---|---|---|
| **PROF.1** | **Plugin maker.** Agentic processing of a paper and codebase into a plugin in the Universal Plugin Format: plug and run, AI-native, a peer-reviewed standard protocol. | scProfile (+ harness `skills/plugin-maker`) | [8] |
| **PROF.2** | **The workflow:** processed data → design resolver → analysis planner → self-assembled analysis pipeline → runner → results → reproducibility suite → report generation. | scProfile | [9] |
| **PROF.3** | **Plugin coverage:** cell cycle, scVelo, CellRank, SCENIC, decoupler, scCODA, PyDESeq2, CellChat [9]. The families named: cell cycle, velocity, regulon, cell communication, trajectory [4], plus differential abundance and expression and pathways [2]. | scProfile | [2], [4], [9] |
| **PROF.4** | **Report generator.** Per-contrast reports such as the CellChat report [15]: aged vs young, HFD vs chow at each level of the other factor. | scProfile | [4], [15] |

### The harness, the agents and the platform

| id | capability | owner | source |
|---|---|---|---|
| **HARN.1** | The family integrated: one stack (QC → annotation → integration → profiling) assembled and run on a cohort, with every stage's record kept. | harness | [4], [10] |
| **HARN.2** | Working agents: assemble the workflow, coordinate, audit, record. | harness (`skills/`, `sch` agent surface) | [4] |
| **HARN.3** | The AI co-scientist: hypothesis generation, validation and audit, closing the loop from the report back to the planner. | harness + scProfile | [9], [17] |
| **HARN.4** | The Harness UI: a web interface like Codex or Claude Code. | harness | [4], [17] |
| **PLAT.1** | **Service: request handling.** A single-cell delivery and the questionnaire become a request the harness can run. | rnaseq-service | [4] |
| **PLAT.2** | **Lab: data formatting.** The family's final objects become the file Studio opens. | scrnaseq-lab | [4] |
| **PLAT.3** | **Studio: data explorer.** The harness's results are explored, together with what produced them. | scrnaseq-studio | [4], [10] |

## Layer 3: acceptance tests (C) — what the audit checks

A capability **exists** when each of its tests passes with evidence: a commit, a sealed run, a PBS job
id, or a file and line. A claim with no evidence is **UNKNOWN**, never PASS. The audit is **happy** when
every in-scope test below passes, or the PI has deferred it by name. The bars in this layer are targets
we develop toward, not gates on development. In the PI's words (2026-11-09): "this is goals we are
developing towards. keep developing". Each bar is (C), set by the pre-decider, and the PI may move it.

| test | checks | for |
|---|---|---|
| **A1.1 one request, every stage** | From one cohort's processed matrices and a design sheet, the family runs QC → annotation → integration → profiling (DE, DA and the plugins the design admits), writes every stage's report, and seals the run. No glue script is written for the cohort, and nobody steps in by hand between stages except for decisions the tools declare as the user's. Shown on **SAMBO** and on **BrainOrganoid_C46**. | G1, HARN.1, G7 |
| **A1.2 the ten steps mapped** | Each of the ten typical steps [2] maps to the component that performs it, or is declared upstream (alignment). Every mapped component runs in A1.1. | G1 |
| **A1.3 environments from main** | Every tool's environment builds from `main` on a fresh prefix through its own installer, with pins, on the cluster (PBS). It then passes its own self-test. | G1 [16] |
| **A2.1 pre-declared reproduction** | Each stage's promoted run reproduces under a PBS job whose prediction was written before submission. Deterministic outputs must be identical. Outputs that vary between runs are named with their measured spread. | G2 |
| **A2.2 documentation true** | Each repository's README and docs state inputs, outputs, how to run and how to reproduce. An auditor samples at least 10 claims per repository against the code, and none is false. | G2 |
| **A2.3 cold reproduction** | An agent with no prior context reproduces a sealed stage run from its record and the docs alone. | G2 |
| **A3.1 held-out cohorts** | Both cohorts (mouse, snRNA, Singleron, heart, two factors; human, scRNA, 10x, organoid, one factor) run end to end through A1.1. The leak guard finds no cohort-specific string in any tool. The fixture's value axes reach each tool's pipeline, not only `describe`. | G3 |
| **A3.2 design-aware** | The design resolver handles one factor (n = 2 per arm), a two-factor factorial with interaction, and a covariate, or refuses each by name with the reason. Contrasts are labelled in the report as SAMBO's are [15]. | G3 |
| **A3.3 assay rule sets** | Every tool whose behaviour depends on the assay has separate, declared rules for `scrna` and `snrna`, with no silent default. | G3 |
| **A3.4 scale** | A cohort of at least 1,000,000 cells completes A1.1 on the cluster's standard queues. Cells, wall time and peak memory are reported per stage. | G3 |
| **A4.1 the existing pool in one format** | Every current plugin (the eight held-out plugins and CellChat) is in the maker's layout and passes `sch dev` and `sch conform`, graded by the dev suite on the cluster (`jobs/dev_suite.pbs`). | G4 |
| **A4.2 the maker on new tools (at least 4 of 5)** | Published tools the family has never seen, drawn from the scRNA-tools catalogue by a rule written before the draw, are converted by agents alone. Each passes the dev suite and reproduces the tool's own published example within a declared tolerance. Success rate and time per conversion are reported. | G4 |
| **A4.3 provenance of methods** | Every plugin names its peer-reviewed source and pinned version. | G4 |
| **A4.4 AI-native** | A cold agent lists the catalogue, picks a plugin for a stated question, and runs it through the harness's agent surface without reading the plugin's code. | G4, G7 |
| **A5.1 report from evidence** | The report generator writes a Results section in which every claim cites a figure or table of the run. An independent reviewer removes unsupported claims, and the section survives that review. | G5 |
| **A5.2 hypotheses** | The co-scientist proposes hypotheses from a run. Each gives its evidence, a test that could falsify it, and a follow-up analysis the planner can run. At least one follow-up is executed through the loop. | G5, HARN.3 |
| **A6.1 Harness UI** | A web interface where a user asks for an analysis in plain language, sees the plan, approves the user-owned decisions, follows the run, and opens the reports and the record. The report's words are the specification. The PI may redirect the design at any point. | G6, HARN.4 |
| **A6.2 Studio hand-off** | The family's final object opens in scRNA-seq Studio through Lab's converter, with no manual conversion. Studio shows the run that produced it. | G6, PLAT.2, PLAT.3 |
| **A6.3 Service takes single-cell requests** | A single-cell delivery (Cell Ranger or CeleScope outputs) and the questionnaire become a request that the harness runs as A1.1's input, with no hand editing. The bulk path's own tests still pass. | G6, PLAT.1 |
| **A7.1 agents drive it** | A cold agent equipped only with the harness's skills runs A1.1 on a held-out cohort: assembling, submitting, recovering from failures, auditing and recording. | G7 |

## How the goals are used

- [`autodev/ledger/gaps.tsv`](autodev/ledger/gaps.tsv) holds one row per gap against a layer-2
  capability or a layer-3 test.
- Every development wave names the goal ids it moves. Rule 5 bans waves that move none.
- The audit grades each layer-3 test PASS, PARTIAL, FAIL or UNKNOWN, with evidence, and gives a verdict
  of HAPPY or NOT HAPPY. Its history is in [`autodev/ledger/audits.tsv`](autodev/ledger/audits.tsv).
- VISION.md argues the runtime's thesis and ARCHITECTURE.md binds its invariants. This file says what
  the whole family is *for*. Where ROADMAP.md's ordering conflicts with these goals, this file wins
  ([ADR-0028](docs/adr/0028-the-goals-and-the-loop.md)).
