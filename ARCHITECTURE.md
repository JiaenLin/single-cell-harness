# Architecture — LOCKED, v1.0

**This document is normative and frozen.** Everything else in this repository may be revised
freely; the invariants below may not be changed by writing a different document. They change only
through the amendment procedure in §7, which requires a numbered decision record saying what broke
and what it cost.

The reason for the lock is specific. This design's value is that a small number of properties hold
*everywhere* — reversibility, reactive invalidation, provenance that cannot go missing. Each is
worth nothing if a single later plugin is allowed the exception it will certainly ask for. An
architecture that erodes one convenience at a time ends up as a workflow manager with an unusual
vocabulary, and nobody can point at the commit where that happened.

The model is [Cordis](https://github.com/cordiverse/cordis) (MIT), the plugin kernel under
[DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness). It is followed by name.

---

## 1. The layers

```
  ┌───────────────────────────────────────────────────────────────┐
  │ 4  PLUGINS    methods, probes, gates, executors, reports,     │
  │               the decision-maker, the agent loop itself       │
  ├───────────────────────────────────────────────────────────────┤
  │ 3  SERVICES   dataset · executor · storage · probe ·          │
  │               provenance · report · gate                      │
  ├───────────────────────────────────────────────────────────────┤
  │ 2  REGISTRY   registration → a Runtime per plugin;            │
  │               lifecycle, cleanup, state transitions           │
  ├───────────────────────────────────────────────────────────────┤
  │ 1  CORE       Context · Service · effect / disposer           │
  └───────────────────────────────────────────────────────────────┘
```

**L1** — A layer may depend only on layers below it. No exceptions, including for performance.

**L2** — **The core knows nothing about single-cell biology.** No domain type, no gene, no cell, no
assay appears at layer 1 or 2. The domain lives entirely in services and plugins. A core that knows
what a cell is cannot be tested against anything else, and every domain assumption baked into it
becomes unremovable.

**L3** — The kernel never imports a plugin. It reads a manifest, resolves an interpreter, runs an
entry point, and merges declared output.

---

## 2. Context and services

**C1** — A plugin receives a **Context** and reaches everything through it. No plugin imports
another plugin.

**C2** — Dependencies are **declared** (`inject`), never passed positionally and never discovered
by import. Demand-driven, as in Cordis.

**C3** — A service is addressed by **capability**, never by implementation. `capability:embedding`,
not `obsm/X_scanvi`. This is what makes a plugin swappable, and it is the invariant most often
worth breaking for one urgent case.

**C4** — Across a process boundary the Context is **serialised as JSON**. No interchange that
requires the two sides to share a library version. This exists because a pinned plugin and a
current host cannot read the same `.h5ad` encodings, and JSON is the only thing both are certain
to read.

---

## 3. Effects and disposers

**E1** — Every contribution yields a **disposer**. Out of process, the *declaration is* the
disposer: the kernel synthesises the undo from what the plugin declared it produced.

**E2** — A plugin **cannot mutate the dataset** except through a declared contribution. This is
enforced by the dataset service handing out a read-only materialisation, not by inspection or
convention.

**E3** — Unmount runs disposers in **exactly reverse mount order**.

**E4** — `reversible: true` is **tested at mount** — mount, snapshot, unmount, compare — never
trusted at unmount, when everything depends on it.

---

## 4. The data layers

**D1** — Exactly three, with different rules:

| | | |
|---|---|---|
| **observations** | the reads as delivered | immutable, never written |
| **checkpoints** | operations producing genuinely new numbers | rebuild-only, never unmounted |
| **stack** | masks, derived columns, matrices, graphs | mounted and unmounted |

**D2** — **Nothing writes to observations.** Ever, for any reason, including a correction. The
provenance boundary between what was measured and what was computed cannot be reconstructed once
lost.

**D3** — Invalidation propagates **down to the nearest checkpoint and stops**.

**D4** — **A removal is a mask, never a delete.** A plugin that deletes observations has made a
change the kernel cannot reverse, and is in breach of E1 and E2.

**D5** — A checkpoint declares `rebuild_from`. A plugin unsure which layer it belongs to declares
`checkpoint`: the cost of that error is a rebuild, and the cost of the opposite is an unmount that
silently produces a different dataset.

---

## 5. Provenance and gates

**P1** — The event stream is **append-only and replayable**.

**P2** — **report-visible ⟺ replayable.** Any number that reaches a report must be reconstructible
from the stream. A number that is not cannot be shown.

**P3** — **The stack is the provenance.** An object is generated from it, so an object with missing
provenance is not a state the system can reach.

**G1** — A gate is a **plugin**. No gate is hard-coded in the kernel, because a gate nobody can
enumerate is a gate nobody can audit.

**G2** — Every gate escape is **logged**, with the reason. A gate with no escape gets switched off;
a gate whose escapes are all recorded does not.

**G3** — A gate **measures with a probe the caller can independently run**. One implementation, two
consumers. A gate whose measurement cannot be reproduced by the party it refuses is a black box
that will be routed around.

---

## 6. Agents

**A1** — **Reads are open, writes are not.** Arbitrary code may compute anything and look at the
result; altering the dataset requires mounting something that declares what it changed.

**A2** — **Nothing in scratch is quotable.** No number produced there may enter a report, and
nothing in a published stack may read from it.

**A3** — An agent cannot disable a gate, promote its own work past one, unmount a checkpoint, or
convert a `checkpoint` declaration to `stack`.

---

## 7. Compatibility, and how to change this document

**X1** — Only the **MAJOR** of a contract version is compared.

**X2** — **Fields are added; meanings never change.** A field whose meaning must change gets a new
name, and the old one is deprecated with notice. This is the promise that makes the format safe to
build on, and it is the one that costs the most.

**X3** — A plugin that mounted on 1.x mounts on any later 1.y.

### Amending an invariant

An invariant is not amended by editing this file. It is amended by:

1. writing a decision record in [`docs/adr/`](docs/adr/) naming the invariant, what forced the
   change, and **what property is lost**;
2. finding every place the lost property was relied on — the failure modes in `VISION.md` §19 are
   the starting list;
3. bumping the architecture version; a changed invariant is a MAJOR bump, a new one is MINOR;
4. only then editing this file, with the record linked from the invariant.

**A pull request that breaks an invariant without a record is rejected on that basis alone**, and
not on the merits of what it was trying to do. The merits are usually good — that is how an
architecture erodes.

---

## 8. Conformance

`sch doctor --architecture` checks what is checkable statically:

| | |
|---|---|
| L1 | no import from a higher layer |
| L2 | no domain term in `core/` or `registry/` |
| L3 | the kernel imports no plugin module |
| C2 | every plugin dependency is declared in a manifest |
| C4 | the boundary carries JSON only |
| D2 | nothing opens an observation path for writing |
| E4 | every `reversible: true` plugin passes mount/unmount/compare |
| G1 | every gate resolves to a plugin |
| G3 | every gate names a probe that exists |
| X1 | the version comparison reads the major only |

A1, A2, D4 and P2 are not statically checkable and are covered by the adversarial suite: code
written to break them, not code written to confirm them.
