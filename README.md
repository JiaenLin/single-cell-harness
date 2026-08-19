# single-cell-harness

A harness for the whole life cycle of a single-cell dataset.

**No code yet.** [`VISION.md`](VISION.md) is the thesis, written to be argued with before anything
is built.

---

An analysis is not a pipeline that transforms files. It is a **stack of reversible decisions
mounted over an immutable set of observations** — and the `.h5ad` everyone treats as the result is
a view of that stack, not the artifact itself.

Take that seriously and three things that are currently impossible become structural:

- **A decision can be unmounted.** Remove the QC plugin and the cells come back — they were never
  deleted, only masked by a plugin that declared what it masked and why.
- **Staleness cannot happen.** Change a threshold and everything downstream is invalidated by the
  runtime, not by someone remembering.
- **"What did this remove?" is answerable by construction**, because removal is a declared,
  inspectable mask rather than a `del`.

Everything is a plugin: methods, executors, storage, gates, reports, the provenance stream, and
whoever decides what runs next — human or agent.

It **orchestrates** rather than absorbs. [scQC](https://github.com/JiaenLin/scQC),
[scAnno](https://github.com/JiaenLin/scAnno),
[scIntegrate](https://github.com/JiaenLin/scIntegrate) and
[scProfile](https://github.com/JiaenLin/scProfile) keep their own repositories, locks and users,
and mount through thin adapters over the contracts they already have.

Inspired by [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) (MIT) and the
[Cordis](https://github.com/cordiverse/cordis) plugin kernel — see [`NOTICE.md`](NOTICE.md) and
§12 of the vision for exactly what is borrowed.
