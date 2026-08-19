# single-cell-harness

*A harness for the whole life cycle of a single-cell dataset.*

*Vision. No code yet, deliberately. This document exists to be argued with.*

*Inspired by [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) (MIT) and the
[Cordis](https://deepwiki.com/cordiverse/cordis) plugin kernel. §12 lists exactly what is borrowed
and what is not.*

---

## 1. The claim, stated so it can be attacked

Every single-cell platform in use today models an analysis as **a pipeline that transforms files**.
Raw reads become a matrix, the matrix becomes a filtered matrix, the filtered matrix becomes an
embedding, and each step overwrites or replaces what came before.

That model is wrong, and almost every recurring failure in this field is downstream of it.

An analysis is not a transformation of files. It is **a stack of reversible decisions mounted over
an immutable set of observations**. The `.h5ad` everyone treats as the result is not the artifact —
it is a *view*, the materialisation of the stack at one moment. The artifact is the stack.

Once you take that seriously, three things that are currently impossible become structural:

- **You can unmount a decision.** Remove the QC plugin and the cells come back, because they were
  never deleted — they were masked by a mounted plugin that declared what it masked and why.
- **Staleness cannot happen.** Change a threshold and everything downstream is invalidated by the
  runtime, not by a person remembering to re-run it.
- **"What did this remove?" is answerable by construction**, because removal is a declared,
  inspectable mask rather than a `del`.

That is the whole idea. Everything below is consequence.

---

## 2. This is not a new problem, and I have the receipts

The failures that motivate this are not hypothetical. Every one of these happened while building
the four tools this harness is meant to unify, and each was caught by hand, late, by luck.

| what happened | what it really was |
|---|---|
| A ribosomal-gene regex excluded `Rps6ka2` — an mTOR **kinase**, correlation with the ribosome module r = +0.046 — from HVG selection in a high-fat-diet study. Nothing objected, because the exclusion looked routine. | An **irreversible decision with no declared scope.** Nothing in the system knew what the filter would remove until someone printed it. |
| A report was presented as a stage's deliverable whose assembler had never run. A table was quoted from a local copy while the compute host held a newer file of the same name. Four times in two days. | **No reactive invalidation.** A stale artifact opens, renders and reads exactly like a correct one. Staleness has no symptom. |
| An integration assessment may have been computed on a *stitched* concatenation of per-sample UMAPs rather than a joint embedding — measured offset spread 0.000000. Still unresolved. | **A dependency the system did not model**, so it could not tell anyone the input was not what the consumer assumed. |
| A pinned kernel could not read an object written by a newer anndata. The error named an IO registry and pointed nowhere near the cause: pandas 3 changed a default string dtype. | **Version skew between components that must share one object** — invisible until it is fatal. |
| A benchmark ranked scANVI first on metrics computed against the very labels scANVI was trained on. Correct code, correct metrics, and not a like-for-like ranking. | **No model of what a result MEANS**, only of how it was computed. |
| Filters removed 53% of one sample and 6% of another, converting a technical property into an apparent biological difference. | A transformation whose **differential effect across the design** nothing checked. |

Every one of these is a *composability* failure. Not a bug in a method — a gap in the runtime
between the methods.

---

## 3. The two properties, and why they are the right two

[Cordis](https://deepwiki.com/cordiverse/cordis) — the kernel under
[DeepSeek Harness](https://deepseek.com/harness/en/) — names exactly two properties as the
foundation of a plugin system:

- **Temporal composability** — every side effect a plugin produces on load is *automatically rolled
  back* when it unloads.
- **Spatial composability** — plugins declare dependencies, and the runtime wires and re-wires them
  *reactively*.

Translate those into single-cell and they are, precisely, the two rules this project wrote by hand
after being burned:

| Cordis | what we independently arrived at | how we enforce it today |
|---|---|---|
| temporal composability | **Rule one** — before removing anything, assess what it destroys; prefer the reversible form; a SEAL removes the possibility of a *label*, never an *observation* | a Python gate + a `PreToolUse` hook, both bypassable by anyone who doesn't run them |
| spatial composability | **Rule six** — no artifact may be older than its inputs; check every arrow of the chain, not the last one | a freshness audit run manually, which reported "0 stale" while the middle of a three-link chain was broken |

**That convergence is the argument.** Two independent lines — a systems meta-framework and a
biology project accumulating scar tissue — arrived at the same two properties. We got there by
writing gates that fire after the fact. Cordis says they belong in the kernel, where they cannot be
skipped.

### The mechanism, borrowed intact

The idea that a decision can be unmounted is easy to state and hard to implement, and DeepSeek
Harness has the answer already: **every contribution a plugin makes returns the thing that undoes
it.** In their words, contributions go through `ctx.effect()` / `ctx.on()`, and *a registry's
`register()` returns the disposer.*

That single convention is what makes reversibility structural rather than aspirational. A plugin
cannot register a side effect without simultaneously producing the means to reverse it, so
"forgot to clean up" is not a state the system can reach.

Our rule one has no such mechanism. It has a *gate* that refuses a removal unless five questions
are answered — which is a checklist, enforced at the door, that says nothing about how to take the
removal back afterwards. The gate tells you what you are about to destroy. The disposer means you
did not destroy it.

A single-cell reading of the same convention:

```python
# a plugin does not mutate the dataset; it contributes, and gets back the undo
undo = ctx.mask_obs(keep, reason="min_umi=350", scope=..., differential=...)
undo = ctx.provide("obsm/X_harmony", emb)
undo = ctx.label("cell_type", labels, provenance=...)
```

The kernel holds the disposers. Unmounting a plugin calls them in reverse order. Nothing else in
the system needs to know how to undo a QC filter — the QC plugin already said.

### What "temporal" means for a dataset

A plugin that filters cells does not delete them. It **mounts a mask** with a declared reason, a
declared scope, and a measured differential effect across the design. Unmount it and the cells are
present again, everywhere, including in every downstream view.

This is not a storage trick. It changes what questions are askable:

- *What would the composition have been without the doublet filter?* — unmount, re-materialise.
- *Which of our four QC decisions is this finding sensitive to?* — unmount each in turn.
- *A reviewer asks for the analysis without the ambient correction.* — that is a configuration, not
  a re-run from FASTQ.

Today every one of those is a full re-analysis, which is why nobody does them, which is why nobody
knows how sensitive their results are to their own decisions.

### What "spatial" means for a dataset

A plugin declares what it **needs** (raw counts, a label column, spliced layers, a design table,
an embedding) and what it **provides**. The kernel resolves the graph and knows, at all times:

- which plugins *can* run on the current state, and which cannot and exactly why;
- what becomes invalid the instant an upstream plugin is mounted, unmounted or reconfigured;
- what is **missing** to answer a question the user has asked.

That last one is the feature that makes the harness feel like it is thinking. "I want cell–cell
communication" is answerable with *"you have labels but no design table, so you can get an
interaction map but not a between-condition comparison; here is what to add."*

Note that scProfile's `unmet()` and its `needs_layers` / `produces` declarations are already a
crude, single-stage version of this. The harness is that idea taken to the whole life cycle.

---

## 4. Everything is a plugin — including the parts that usually aren't

The analysis steps being plugins is the obvious half. The half that matters:

| plugin class | examples | why it must be swappable |
|---|---|---|
| **method** | QC, annotation, integration, velocity, regulons, CCC | the obvious one |
| **executor** | local, PBS, SLURM, cloud | the same decision stack must run on a laptop and on a cluster. Where compute happens is not part of what the analysis *is* |
| **storage** | local FS, object store, tiered/online-only | a multi-GB object inside a syncing folder is a real problem this project has already hit |
| **gate** | rule one, rule six, design-confounding, sentinel handling | a gate that is a plugin can be *listed*, *audited* and *reported* — a gate hard-coded in a script is a gate nobody knows fired |
| **report** | HTML, notebook, manuscript figures | one dataset, several audiences |
| **provenance** | the event stream itself | see below |
| **decision-maker** | a human at a prompt; an LLM agent proposing the next step | an agent is just another plugin, subject to the same gates — which is the only safe way to let one near this |

The last row is deliberate and it is the reason the DeepSeek Harness comparison holds. An agent
that can inspect the mounted plugin tree, propose a step, and be *refused by a gate it cannot
disable* is a fundamentally safer thing than an agent writing pipeline scripts.

---

## 5. The provenance inversion

Today provenance is a **log written after the fact**: `RUNLOG.md`, `PROVENANCE.txt`,
`uns['scanno']`, a `PROMOTED.md`. It is a description of what happened, written by the thing that
did it, and it is wrong whenever someone forgets.

In this model the relationship inverts. **The decision stack IS the provenance**, and the object is
generated from it. You cannot have an object whose provenance is missing, because the object does
not exist independently of the stack that produced it.

Consequences worth naming:

- A dataset can be shipped as **a stack plus a pointer to the raw data** — kilobytes, not gigabytes.
- Two labs can **diff their analyses**, not just their results. "You mounted `ambient@cellbender`
  with `fpr=0.01`, we used `fpr=0`" is a sentence a machine can produce.
- A published result carries a stack that a reader can **re-materialise and perturb**.

---

## 6. What already exists, and why none of it is this

Being honest about the landscape is how this stays credible.

| | what it does | why it is not this |
|---|---|---|
| **Nextflow / nf-core, Snakemake, CWL, WDL** | orchestrate jobs over files, with resume and containers. Mature, excellent, widely used | They model **files and jobs**, not a dataset with revertible operations. A DAG runner knows file A produced file B; it cannot tell you that step 3 removed 8,427 cells unevenly across your design arms, because it does not know what a cell is |
| **Galaxy** | GUI, reproducible histories, huge tool library | Histories are a linear record, not a mountable stack; you cannot unmount step 2 and keep steps 3–6 |
| **scverse (scanpy/anndata/muon)** | the object model and the algorithms this all stands on | A library, not a runtime. AnnData is deliberately mutable and has no notion of an operation that can be reverted |
| **Seurat / Bioconductor** | the R half of the same | same |
| **Terra, Latch, Pluto, Cellenics** | managed execution, provenance, sharing | Platform-as-a-service around the pipeline model. Better hosting of the same abstraction |
| **MLflow / W&B / DVC** | experiment tracking, data versioning | Tracks runs and files. Does not model the *semantics* of the operations, so it cannot invalidate reactively or answer what a step destroyed |

**The gap in one sentence:** existing systems reproduce *what you ran*; none of them can tell you
*what it cost you*, or let you take it back.

---

## 7. What the harness decides, and what it must never decide

This is the boundary that keeps the thing honest, and it is drawn from a rule this project already
enforces: *the user decides stage boundaries and when a stage is finished.*

**The harness decides:**
- which plugins are runnable given the current stack (capability resolution)
- the order they must run in (dependency resolution)
- what is now invalid (reactive invalidation)
- where each should execute, given its cost and the available executors
- what is missing to answer a stated question

**The harness proposes, and never decides:**
- which method is *right* — it can rank, and must show the figures the ranking cannot substitute for
- whether a stage is finished
- whether to accept a removal, a correction, or a stale artifact

**The refusal is a first-class output, not an error.** Most datasets reaching this system will lack
spliced counts, ATAC, spatial coordinates, or a design table. A harness whose commonest output is a
clear refusal that names the fix is working correctly — and that is precisely the behaviour most
likely to be removed later as "unhelpful".

---

## 8. Architecture sketch

Enough to argue about; not a design document.

```
                      ┌──────────────────────────────────────────┐
                      │  KERNEL                                  │
                      │   mount / unmount / reconfigure          │
                      │   dependency graph + reactive invalidate │
                      │   event stream (append-only, replayable) │
                      └──────────────────────────────────────────┘
                            │ services (dependency injection)
    ┌───────────────┬───────┴────────┬────────────────┬──────────────────┐
    │ observations  │  executor      │  storage       │  gates           │
    │ (immutable)   │  local/PBS/... │  fs/object/... │  rule one, six…  │
    └───────────────┴────────────────┴────────────────┴──────────────────┘
                            │
      ┌─────────────────────┴─────────────────────┐
      │  MOUNTED DECISION STACK                    │
      │   qc@scQC         mask, reason, Q1–Q5      │
      │   ambient@cellbender    params             │
      │   annotate@scAnno       label columns      │
      │   integrate@scIntegrate embeddings         │
      │   profile@scProfile/*   kernels            │
      └────────────────────────────────────────────┘
                            │  materialise (a view, on demand)
                      ┌─────┴──────┐
                      │  .h5ad     │  report  │  figures  │  notebook
                      └────────────┘
```

**Adapters, not rewrites.** Per the decision taken with this document: scQC, scAnno, scIntegrate and
scProfile stay in their own repositories, with their own locks, versions and users. The harness
mounts each through a thin adapter over the CLI and manifest contract each already has. Nothing
built so far is thrown away, and each tool remains independently installable — which is also the
only honest test of whether the contract is real.

scProfile is the proof that the contract can work: it already has plugin discovery, declared
`needs`/`produces`, prerequisite resolution, guards with logged escapes, cross-environment
subprocess isolation, and a validated JSON manifest. **The harness is that idea promoted from one
stage to the life cycle.**

---

## 9. The order of proof

Not a roadmap. The sequence in which the thesis gets tested, cheapest disproof first.

1. **Can a decision be unmounted?** Take QC alone. Mount a filter as a mask, unmount it, show the
   cells return and every downstream view updates. If this is not clean, the thesis is wrong and
   everything after it is wasted. **Do this first and try hard to break it.**
2. **Can invalidation be reactive?** Change one threshold; watch every dependent artifact go
   invalid without anyone remembering.
3. **Can the four existing tools mount unchanged?** If an adapter is thicker than a rewrite, the
   contract is wrong.
4. **Can the executor be swapped?** Same stack, laptop and PBS, byte-identical result.
5. **Can a stack be shipped and re-materialised** by someone else, from raw data plus kilobytes?
6. **Can an agent be a plugin** that is refused by a gate it cannot disable?

---

## 10. Non-goals

Naming these now, because scope creep is how platforms die.

- **Not a new object model.** AnnData/`.h5ad` stays. A harness that needs its own format has
  already lost.
- **Not new methods.** Zero novel algorithms. The value is entirely in composition.
- **Not a GUI first.** The event stream makes a UI easy later; building the UI first makes the
  kernel bend around it.
- **Not a replacement for Nextflow.** If someone wants a DAG runner underneath as an executor
  plugin, good.
- **Not cloud-first, and not cloud-hostile.** The executor is a plugin.
- **Not an autonomous analyst.** An agent may propose. Gates it cannot disable stand between it and
  the data.

---

## 11. How this fails

Stated in advance so it can be checked against later.

- **Reversibility turns out to be expensive.** If materialising a view from a deep stack is slow,
  people will bypass the stack, and the property that justifies the whole design becomes optional.
  *This is the biggest risk and step 1 of the order of proof exists to find it early.*
- **Adapters rot.** Four tools evolving independently behind adapters is four chances a term
  quietly changes meaning. The contract has to be versioned and tested, or it becomes folklore.
- **Not every operation is invertible.** Ambient correction and alignment are not maskable — they
  genuinely produce new numbers. The model must be honest that the stack has *checkpoints* it can
  only rebuild from, not unmount past, and must say which.
- **The gates get switched off.** A gate that fires on correct behaviour gets disabled — this
  project has watched it happen and has the escape logs to prove it. Gates as plugins must be
  auditable and their escapes recorded, never merely absent.
- **It becomes a workflow manager with extra words.** If, a year in, the only thing it does is run
  four tools in order, the thesis was wrong and it should say so plainly rather than accrete
  features.

---

## 12. What is borrowed, and from where

**This design is inspired by [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness)
(MIT) and the [Cordis](https://deepwiki.com/cordiverse/cordis) kernel it is built on.** That is not
a nod — several of the load-bearing ideas below are theirs, and the honest thing is to name which.

| borrowed | theirs | what it becomes here |
|---|---|---|
| **"Everything is a plugin"** | the central claim: model adapter, tool registry, session log and *the agent loop itself* are all plugins | method, executor, storage, gate, report, provenance and decision-maker are all plugins |
| **`register()` returns the disposer** | contributions go through `ctx.effect()` / `ctx.on()`; every side effect yields its own undo | **the mechanism for reversible analysis.** A filter returns the mask that lifts it; a correction returns the layer that restores the original |
| **Capability seams** — definition / provider / consumer as three separate roles | how packages are organised | a plugin declares a *capability contract*, not an implementation. "Something that provides an embedding" rather than "harmony" |
| **Manifest-driven plugin resolution with overlay composition** (`cordis.yml`) | plugins mount from declarative config that can be layered | a decision stack is a layered manifest — a site overlay, a project overlay, a run overlay |
| **"Model-visible ⟺ logged"** | anything reaching a model request must be reconstructible from the session log | **"report-visible ⟺ replayable"**: every number in a report must be reconstructible from the event stream. This is our evidence rule, made structural instead of aspirational |
| **Monotonic `SCHEMA_VERSION`** on the session format | with backward compatibility explicitly not promised pre-release | the same, for the decision stack. scProfile already does this with `CONTRACT_VERSION` |
| **Agents as plugins** | other coding agents mount as sub-agent plugins | an LLM proposing an analysis step is a plugin, subject to gates it cannot disable |

**What is not borrowed, and why.** DeepSeek Harness is TypeScript/Node and organised around an
agent loop over a session. This is Python, organised around a dataset — the scientific stack is
Python and nothing else is negotiable. So the borrowing is **concepts and contracts, not code**,
and there is currently no vendored source. If any is vendored later, the MIT notice travels with
it and `THIRD_PARTY_NOTICES.md` records it — the same discipline their own repo uses.

**What we bring that they do not need.** Their plugins contribute behaviour to a running agent.
Ours contribute *claims about data that a scientist will publish*. That difference is where the
additions live:

- a **differential-effect check** on every removal — a filter taking 53% of one sample and 6% of
  another is a technical property masquerading as a biological one, and no general-purpose kernel
  has any reason to care
- **`cannot_show`** as a required field — a plugin must declare what its output does *not*
  establish, and the report prints it beside the result
- **checkpoints**: some operations genuinely are not invertible (alignment, ambient correction),
  and the model has to say so out loud rather than pretend the stack is reversible all the way down
- **gates as auditable plugins with logged escapes** — because we have watched gates that fire on
  correct behaviour get switched off

---

## 13. The name

**`single-cell-harness`.** Decided, not proposed.

It says what the thing is in the words a biologist would use, and it does not make anyone learn a
coined term before they can tell a colleague what they are running. The four tools underneath keep
the `sc*` prefix and their own identities; the umbrella does not need to compete with them for the
same naming space.

Two things it gives up, recorded so nobody re-opens the question by accident:

- it names the **mechanism** rather than the thesis. `scStack` would have put the decision stack —
  the genuinely new idea — in the name. The trade is legibility, and legibility wins for something
  people have to adopt.
- it uses **"harness"**, which is DeepSeek's word for this class of system. That is deliberate and
  it is the honest signal: this *is* that class of system, applied to single-cell data, and §12
  says exactly how much of it is theirs.

## 14. What I want argued with

- Is **reversibility** genuinely the core, or is reactive **invalidation** the more valuable half?
  They are separable, and if forced to build only one I would build invalidation — it fixes the
  failure that has actually cost this project the most.
- Is the **agent-as-plugin** idea load-bearing or decoration? It is the most fashionable part of
  this and therefore the part I trust least.
- Is **"orchestrate, don't absorb"** right for the long run, or does it just defer a migration that
  gets harder every month?
- Is there a **fifth failure mode** in §11 that I have not thought of, and which is the one that
  will actually happen?
- Is **"concepts, not code"** the right relationship to DeepSeek Harness, or should the kernel be a
  thin Python port of Cordis so the two stay compatible as it evolves?
