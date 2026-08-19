# single-cell-harness

A plugin runtime for the whole life cycle of a single-cell dataset.

Decisions are **mounted**, not applied. A filter, a correction, an annotation or an embedding is a
plugin contributing to a stack over immutable observations — so any of them can be removed, and
everything downstream knows when one does.

> **Status: design.** This repository currently contains the architecture and its rationale.
> [`VISION.md`](VISION.md) is the specification; there is no implementation yet.

---

## The model

Three layers, with different rules.

| layer | contents | mutability |
|---|---|---|
| **stack** | filters, corrections, labels, embeddings, annotations | mounted and unmounted; each plugin returns its own undo |
| **checkpoints** | alignment, ambient correction — operations producing genuinely new numbers | rebuilt from, never unmounted; invalidation stops here |
| **observations** | reads as delivered | immutable, never written |

The `.h5ad` is a **view** — a materialisation of the stack, generated on demand. The stack is the
artifact, and it is also the provenance: an object cannot exist without the record of what produced
it.

## What it does

```console
$ sch stack
  observations   10 libraries, 39,037 droplets      immutable
  ▸ align@celescope       2.7.3                     checkpoint
  ▸ ambient@cellbender    lr=5e-5 fpr=0             checkpoint
  ▸ qc@scqc               0.4.0   masks 6,851 obs   mounted
  ▸ annotate@scanno       0.10.0  labels 4 columns  mounted
  ▸ integrate@scintegrate 0.4.0   5 embeddings, default X_scanvi
  ▸ profile@velocity      REFUSED — no spliced layer beside this object
```

Remove a decision and see the cost before paying it:

```console
$ sch unmount qc@scqc --dry-run
  would restore 6,851 observations
  would invalidate, in order:
    annotate@scanno          labels were fitted on the masked set
    integrate@scintegrate    5 embeddings, all of them
    12 figures, 3 tables, 1 report
  checkpoints are unaffected: ambient@cellbender does not rebuild
```

Fork the stack to hold everything else constant:

```console
$ sch fork no-qc --without qc@scqc && sch run no-qc
$ sch diff main no-qc --on composition
  cell type           main      no-qc     Δ
  Cardiomyocyte      37.3%     34.9%   -2.4pp
  Endothelial        24.3%     24.1%   -0.2pp
```

## Everything is a plugin

| class | examples |
|---|---|
| **method** | QC, annotation, integration, velocity, regulons, communication |
| **executor** | local, PBS, SLURM, cloud |
| **storage** | local filesystem, object store, tiered |
| **gate** | reversibility, freshness, design confounding, sentinel handling |
| **report** | HTML, notebook, manuscript figures |
| **provenance** | the event stream |
| **decision-maker** | a person at a prompt, or an agent proposing the next step |

Gates are plugins, so they can be listed, audited and reported, and every override is logged. An
agent is a plugin, so it is subject to gates it cannot disable.

## The plugin format

```yaml
name: qc@scqc
version: 0.4.0
provides:  [obs_mask, "obs/qc_*"]
needs:     [{checkpoint: ambient}]
declares:
  reversible: true               # tested at mount, not trusted at unmount
  differential_check: required   # removal rate measured per design arm
cannot_show:
  - A cell passing QC is not a cell that is intact; it is one whose summary
    statistics fall inside chosen thresholds.
executor: {cost: high}
```

Specified in full in [`PLUGIN_FORMAT.md`](PLUGIN_FORMAT.md), with
[`docs/AUTHORING.md`](docs/AUTHORING.md) for converting a public tool into one and a
[`plugin-maker`](skills/plugin-maker/SKILL.md) skill that performs the conversion.

`needs` and `provides` are capability contracts — *something that provides an embedding*, not
*harmony* — so implementations are swappable and the runtime can resolve what is runnable, what is
invalid, and what is missing to answer a given question.

## Building methods

New methods are plugins and inherit the substrate: object reading and key detection, a pinned
environment with a selftest, execution placement, provenance, reports with vector figures and
per-panel source data, and comparison against every existing method on identical data and metrics.

A method moves from `scratch` (mounted live, no install, nothing quotable) to `dev` (locked,
selftested, benchmarkable) to `shipped` — without being rewritten. Only its manifest changes.

Methods written by this project use the same contract as any other, with no private hooks, and
every plugin remains runnable standalone outside the harness.

**Evaluation contract.** One comparison plugin scores every method on identical data, metrics,
figures and weighting. The do-nothing baseline always runs and runs first. A method that saw the
labels, the design or the evaluation split declares it, and that declaration is printed wherever
the ranking appears. Metrics are recorded in the event stream before results are seen, and held-out
splits are withheld by the data layer rather than by the method's good behaviour.

## Orchestration, not absorption

[scQC](https://github.com/JiaenLin/scQC) ·
[scAnno](https://github.com/JiaenLin/scAnno) ·
[scIntegrate](https://github.com/JiaenLin/scIntegrate) ·
[scProfile](https://github.com/JiaenLin/scProfile)

Each keeps its own repository, lock, version and users, and mounts through a thin adapter over the
contract it already has. scProfile implements a single-stage version of the model — declared
`needs`/`provides`, prerequisite resolution before compute is spent, guards with logged escapes,
cross-environment isolation, and a required `cannot_show` on every plugin.

## Documentation

| | |
|---|---|
| [`VISION.md`](VISION.md) | architecture, rationale, order of proof, failure modes |
| [`PLUGIN_FORMAT.md`](PLUGIN_FORMAT.md) | the plugin specification |
| [`docs/AUTHORING.md`](docs/AUTHORING.md) | converting a public tool into a plugin |
| [`GLOSSARY.md`](GLOSSARY.md) | precise definitions of the terms above |
| [`NOTICE.md`](NOTICE.md) | attribution and licence commitments |

## Attribution

Inspired by [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) (MIT) and the
[Cordis](https://github.com/cordiverse/cordis) plugin kernel, which contribute the "everything is a
plugin" model and the disposer convention that makes unmounting reliable. §17 of the vision
itemises what is borrowed, adapted and original.
