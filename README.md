# single-cell-harness

A plugin runtime for the whole life cycle of a single-cell dataset.

Decisions are **mounted**, not applied. A filter, a correction, an annotation or an embedding is a
plugin contributing to a stack over immutable observations — so any of them can be removed, and
everything downstream knows when one does.

> **Status: the kernel exists, and the development suite around it is in daily use.** `sch`
> implements Phase 1 (the domain-free core, proved on a toy profile), Phase 2 (the profile and the
> 15-check validator, every rule tripped by a broken plugin), the gate-is-a-probe machinery of
> Phase 4, and the agent surface of Phase 10 with its adversarial suite. Phases 3, 5–9 and 11 are
> not built.
>
> `sch conform` checks a child tool against
> [`docs/CHILD_CONFORMANCE.md`](docs/CHILD_CONFORMANCE.md) without touching it; all four pass with
> no failing row, each change proved by a pre-declared reproduction (ADR-0013). `sch dev` serves
> all five repositories and is run on the cluster after every change to any of them — most
> recently PBS 707628, every tier green in all five.
> [`ARCHITECTURE.md`](ARCHITECTURE.md) is normative and **locked** — the layers and the invariants
> that may not be broken. [`VISION.md`](VISION.md) is the thesis, written to be argued with.
> [`PLUGIN_FORMAT.md`](PLUGIN_FORMAT.md) is the contract every plugin conforms to.

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

The model is [Cordis](https://github.com/cordiverse/cordis)'s, by its own names: a plugin is a
function receiving a **Context**; **Services** attach to it; dependencies are declared with
**`inject`** rather than passed in; every registration is an **effect** whose **disposer** runs on
unload; a Context can be **forked**; and a stack is a declarative plugin tree composed by overlay,
in the shape of `cordis.yml`. Across a process boundary the Context is serialised, so a plugin in
R receives the same one as a plugin in Python.

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

Specified in full in [`PLUGIN_FORMAT.md`](PLUGIN_FORMAT.md) — which is **domain-free**; what an
observation is, and the vocabulary of slots, keys, sentinels and probes, live in the
[single-cell profile](docs/profiles/single-cell.md). With
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

## Agents

An agent writes and runs code against the data, as a coding agent does — sequencing plugins is the
easy part of an analysis. The safety comes from an asymmetry rather than from restraint: **reads
are open, writes are not.** Arbitrary code may compute anything and look at the result; changing
the dataset requires mounting something that declares what it changed, which puts every gate,
every provenance record and reversibility itself in the path.

Ad-hoc code runs as a **scratch plugin** — mounted live, no install, nothing quotable. Promotion
to a plugin whose numbers may appear in a report requires a lock, a selftest, a `cannot_show` and
a person.

## Extending it

Operating these tools and changing them are different jobs, and the second one has its own
suite. `sch dev` serves all five repositories in the family without knowing what any of them
extends with: each declares its own extension points in `DEVPOINTS.yaml`, and every command
reads the declaration.

```
sch dev map                          where a new thing plugs in here, and what it must declare
sch dev new POINT NAME               a skeleton, a SPEC written before the code, and a test
sch dev fixture DIR                  a synthetic cohort in two shapes (below)
sch dev check --point P --name N     seven tiers, cheapest first, each saying what it cannot prove
sch dev baseline record RUN --path FILE   record a fingerprint over two executions
sch dev baseline check RUN --path FILE    "the numbers did not move", in seconds
sch dev job --ref REF --predict ...  a reproduction written from the reference run's own argv
```

**The fixture is one cohort written twice** — identical numbers, every role renamed
(`sample`→`library_id`, `cell_type`→`celltype_final`, the counts layer `counts`→`raw_counts`).
Code that resolves a role passes both shapes; code that knows a name passes one. Overfitting
becomes a test failure rather than a reviewer's opinion. Sixteen structural hazards are built in,
each drawn from a defect this family has had. Nothing measured on it is quotable.

[`docs/DEVELOPING.md`](docs/DEVELOPING.md) is the reference;
[`skills/harness-developer/`](skills/harness-developer/SKILL.md) is the procedure.

## Evaluation

A benchmark suite ships with the platform, because "the agent proposed a good analysis" and "the
new method is better" are the same unverifiable sentence without one. Three kinds — independently
labelled reference data, constructed truth, and simulation — each declaring how its truth was
established and what it cannot establish.

## The last mile

A project ends in a submission bundle (methods prose, column-width figures, per-panel source data,
and the stack that regenerates them), an archive-ready deposit, and a published result a
collaborator opens without installing anything. Each is a plugin, and each is generated from the
stack rather than assembled by hand under deadline.

## Orchestration, not absorption

| tool | does |
|---|---|
| [scQC](https://github.com/JiaenLin/scQC) | quality control, and who set each threshold |
| [scAnno](https://github.com/JiaenLin/scAnno) | cell-type labels, only as deep as the evidence goes |
| [scIntegrate](https://github.com/JiaenLin/scIntegrate) | whether you need batch integration, and which method |
| [scProfile](https://github.com/JiaenLin/scProfile) | communication, velocity, pseudotime, differential expression |

Each keeps its own repository, lock, version and users, and works perfectly well on its own. They
mount here through a thin adapter over the contract each already has — nothing was rewritten to
join. scProfile implements a single-stage version of the model — declared
`needs`/`provides`, prerequisite resolution before compute is spent, guards with logged escapes,
cross-environment isolation, and a required `cannot_show` on every plugin.

## Running it

```console
$ pip install -e .                       # stdlib kernel; add [single-cell] for h5py/anndata
$ sch init stack --profile table/1.0 --observations rows.csv --design design.csv \
      --key value=score --key group=arm --key unit=unit
$ sch plan filter_threshold --param min=5     # what would run; every missing prerequisite named
$ sch mount filter_threshold --param min=5    # materialise → gate → run → merge → companion
$ sch unmount filter_threshold --dry-run      # the cost before it is paid
$ sch report                                  # numbers that resolve to events, or no report
$ sch doctor --architecture                   # L1 L2 L3 C4 D2 X1 G1 G3 and every shipped plugin
$ sch conform ../scQC --terms ~/site/forbidden_terms.txt
$ sch conform --run runs/new --against runs/reference   # is a comparison between them meaningful?
$ python -m unittest discover -s tests        # 144 tests, all synthetic
```

## Documentation

| | |
|---|---|
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | **locked** — the layers and the invariants |
| [`ROADMAP.md`](ROADMAP.md) | the build order, and how each step can fail |
| [`VISION.md`](VISION.md) | the thesis, rationale, order of proof, failure modes |
| [`docs/adr/`](docs/adr/) | why each invariant is what it is, and what it cost |
| [`docs/postmortem/`](docs/postmortem/) | defects that got through, and why every check missed them |
| [`PLUGIN_FORMAT.md`](PLUGIN_FORMAT.md) | the plugin specification |
| [`docs/profiles/single-cell.md`](docs/profiles/single-cell.md) | the single-cell profile: observations, slots, keys, sentinels, probes |
| [`docs/AUTHORING.md`](docs/AUTHORING.md) | converting a public tool into a plugin |
| [`docs/STATUS_CONTRACT.md`](docs/STATUS_CONTRACT.md) | what every run leaves behind: status, seal, commit |
| [`docs/CHILD_CONFORMANCE.md`](docs/CHILD_CONFORMANCE.md) | what a child tool exposes before an adapter is written; `sch conform` |
| [`docs/DEVELOPING.md`](docs/DEVELOPING.md) | how the five repositories are extended: `sch dev`, the two-shape fixture, the ladder |
| [`skills/harness-agent/`](skills/harness-agent/SKILL.md) | how a working agent operates inside the harness or a child |
| [`skills/harness-developer/`](skills/harness-developer/SKILL.md) | how a working agent **extends** the family, as opposed to operating it |
| [`skills/plugin-maker/`](skills/plugin-maker/SKILL.md) | an agent skill that performs the conversion |
| [`GLOSSARY.md`](GLOSSARY.md) | precise definitions of the terms above |
| [`NOTICE.md`](NOTICE.md) | attribution and licence commitments |

## Attribution

Inspired by [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) (MIT) and the
[Cordis](https://github.com/cordiverse/cordis) plugin kernel, which contribute the "everything is a
plugin" model and the disposer convention that makes unmounting reliable. §17 of the vision
itemises what is borrowed, adapted and original.
