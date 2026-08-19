# single-cell-harness

*A harness for the whole life cycle of a single-cell dataset.*

**No code yet, deliberately.** [`VISION.md`](VISION.md) is the thesis, written to be argued with
before anything is built on it. [`GLOSSARY.md`](GLOSSARY.md) defines the terms it uses narrowly.

---

An analysis is not a pipeline that transforms files. It is a **stack of reversible decisions
mounted over an immutable set of observations** — and the `.h5ad` everyone treats as the result is
a *view* of that stack, not the artifact.

Take that seriously and three currently-impossible things become structural:

- **A decision can be unmounted.** Remove the QC plugin and the cells return — they were never
  deleted, only masked by a plugin that declared what it masked and why.
- **Staleness cannot happen.** Change a threshold and everything downstream is invalidated by the
  runtime, not by someone remembering.
- **"What did this remove?" is answerable by construction**, because removal is a declared,
  inspectable mask rather than a `del`.

```console
$ sch unmount qc@scqc --dry-run
  would restore 6,851 observations
  would invalidate, in order:
    annotate@scanno          labels were fitted on the masked set
    integrate@scintegrate    5 embeddings, all of them
    12 figures, 3 tables, 1 report
  checkpoints are unaffected: ambient@cellbender does not rebuild
```

Everything is a plugin: methods, executors, storage, gates, reports, the provenance stream, and
whoever decides what runs next — human or agent.

## It orchestrates, it does not absorb

[scQC](https://github.com/JiaenLin/scQC) · [scAnno](https://github.com/JiaenLin/scAnno) ·
[scIntegrate](https://github.com/JiaenLin/scIntegrate) ·
[scProfile](https://github.com/JiaenLin/scProfile)

Each keeps its own repository, lock, version and users, and mounts through a thin adapter over the
contract it already has. If an adapter is ever thicker than a rewrite, the contract is wrong — and
that is worth finding out early.

scProfile already implements a single-stage version of the whole idea: declared `needs`/`provides`,
prerequisite resolution before anything is spent, guards with logged escapes, cross-environment
isolation, and a required `cannot_show` on every plugin. The harness is that contract promoted from
one stage to the life cycle.

## Status

Vision only. The first thing to build is a **disproof**, not a feature: can a QC decision actually
be unmounted, cleanly, with downstream views updating? If that is not clean, the thesis is wrong and
should be abandoned cheaply. See §12, *The order of proof*.

## Attribution

Inspired by [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) (MIT) and the
[Cordis](https://github.com/cordiverse/cordis) plugin kernel. §15 of the vision lists exactly what
is borrowed, what is adapted, and what is ours; [`NOTICE.md`](NOTICE.md) carries the licence
commitment.
