# single-cell-harness

*A harness for the whole life cycle of a single-cell dataset.*

*Vision. No code yet, deliberately — the thesis should survive being attacked before anything is
built on it.*

*Inspired by [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) (MIT) and the
[Cordis](https://github.com/cordiverse/cordis) plugin kernel. §17 lists exactly what is borrowed.*

---

## 1. The claim

Every single-cell platform in use today models an analysis as **a pipeline that transforms files**.
Reads become a matrix, the matrix becomes a filtered matrix, the filtered matrix becomes an
embedding. Each step overwrites or replaces what came before.

That model is wrong, and most recurring failures in this field are downstream of it.

An analysis is **a stack of reversible decisions mounted over an immutable set of observations**.
The `.h5ad` everyone treats as the result is not the artifact — it is a *view*, the materialisation
of the stack at one moment. The artifact is the stack.

Take that seriously and three currently-impossible things become structural:

- **A decision can be unmounted.** Remove the QC plugin and the cells return, because they were
  never deleted — they were masked by a plugin that declared what it masked and why.
- **Staleness cannot happen.** Change a threshold and everything downstream is invalidated by the
  runtime, not by a person remembering.
- **"What did this remove?" is answerable by construction**, because removal is a declared,
  inspectable mask rather than a `del`.

Everything below is consequence.

---

## 2. The receipts

These are not hypothetical failures. Each happened while building the four tools this harness is
meant to unify, and each was caught by hand, late, and partly by luck.

| what happened | what it really was |
|---|---|
| A ribosomal-gene regex excluded `Rps6ka2` — an mTOR **kinase**, correlation with the ribosome module r = +0.046 — from gene selection in a high-fat-diet study. Nothing objected; the exclusion looked routine. | An **irreversible decision with undeclared scope.** Nothing knew what the filter would remove until a human printed it. |
| A report was presented as a stage deliverable whose assembler had never run. A table was quoted from a local copy while the compute host held a newer file of the same name. Four times in two days. | **No reactive invalidation.** A stale artifact opens, renders and reads exactly like a correct one. Staleness has no symptom. |
| An integration assessment may have been computed on a *stitched* concatenation of per-sample embeddings rather than a joint one — measured offset spread 0.000000. Still unresolved. | **A dependency nothing modelled**, so nothing could warn that the input was not what the consumer assumed. |
| A pinned plugin could not read an object written by a newer `anndata`. The error named an IO registry and pointed nowhere near the cause: pandas 3 changed a default string dtype. | **Version skew between components sharing one object** — invisible until fatal. |
| A benchmark ranked a supervised method first, on metrics computed against the very labels it was trained on. Correct code, correct metrics, not a like-for-like ranking. | **No model of what a result MEANS**, only of how it was computed. |
| A filter removed 53% of one sample and 6% of another, converting a technical property into an apparent biological difference. | A transformation whose **differential effect across the design** nothing checked. |

Every one is a *composability* failure — not a bug in a method, but a gap in the runtime between
methods. That gap is what this is for.

---

## 3. Three layers, and only one of them is mutable

The model needs to be honest that not everything can be taken back. Three layers, with different
rules:

```
  ┌──────────────────────────────────────────────────────────┐
  │ STACK          mounted decisions — filters, corrections,  │  reversible
  │                labels, embeddings, annotations            │  by disposer
  ├──────────────────────────────────────────────────────────┤
  │ CHECKPOINTS    outputs that are genuinely new numbers:    │  rebuild only,
  │                alignment, ambient correction, base counts │  never unmount
  ├──────────────────────────────────────────────────────────┤
  │ OBSERVATIONS   the reads as delivered                     │  immutable,
  │                                                           │  never written
  └──────────────────────────────────────────────────────────┘
```

**Observations** are what an instrument produced. Never modified, never regenerated, and the
provenance boundary between what was delivered and what was computed lives here — once lost it
cannot be reconstructed.

**Checkpoints** are the honest limit of the thesis. Alignment does not mask reads, it produces a
count matrix. Ambient correction does not hide counts, it replaces them with different numbers.
You cannot unmount these; you can only **rebuild from them**. A checkpoint declares its inputs and
parameters so it can be reproduced, and the runtime knows it is a floor: invalidation propagates
*down to* the nearest checkpoint and stops.

**The stack** is everything that can be expressed as a mask, a derived column, a derived matrix, or
a graph — which is nearly everything after the count matrix. Filters, doublet calls, labels,
embeddings, corrections that add a layer rather than overwrite one.

Being explicit about the middle layer is what stops this being a fantasy. A system claiming
everything is reversible would be lying about alignment, and a reader who caught it would be right
to distrust the rest.

---

## 4. The two properties, and why they are the right two

[Cordis](https://github.com/cordiverse/cordis) — the kernel under DeepSeek Harness — names exactly
two properties as the foundation of a plugin system:

- **Temporal composability** — every side effect a plugin produces on load is *automatically rolled
  back* when it unloads.
- **Spatial composability** — plugins declare dependencies, and the runtime wires and re-wires them
  *reactively*.

Those are, precisely, the two rules this project wrote by hand after being burned:

| Cordis | what we independently arrived at | how it is enforced today |
|---|---|---|
| temporal composability | before removing anything, assess what it destroys; prefer the reversible form; a seal removes the possibility of a *label*, never an *observation* | a Python gate plus a pre-write hook — a checklist at the door, skippable by anyone who does not run it |
| spatial composability | no artifact may be older than its inputs; check every arrow of the chain, not the last one | a freshness audit run by hand, which once reported "0 stale" while the middle of a three-link chain was broken |

**That convergence is the argument for building this at all.** Two independent lines — a systems
meta-framework and a biology project accumulating scar tissue — reached the same two properties. We
got there by writing gates that fire after the fact. Cordis says they belong in the kernel, where
they cannot be skipped.

### The mechanism, borrowed intact

Reversibility is easy to state and hard to implement. DeepSeek Harness already has the answer:
contributions go through `ctx.effect()` / `ctx.on()`, and **a registry's `register()` returns the
disposer**.

That one convention makes reversibility structural rather than aspirational. A plugin *cannot*
register a side effect without simultaneously producing the means to reverse it, so "forgot to
clean up" is not a reachable state.

Our existing rule has no such mechanism. It tells you what you are about to destroy; it says
nothing about taking it back. The disposer means you did not destroy it.

Read into single-cell:

```python
# a plugin never mutates the dataset — it contributes, and receives the undo
undo = ctx.mask_obs(keep, reason="min_umi=350", differential=by_design)
undo = ctx.provide("obsm/X_harmony", emb, needs=["obsm/X_pca", "obs/sample"])
undo = ctx.label("cell_type", labels, sentinels=["EXCLUDED", "UNRESOLVED"])
```

The kernel holds the disposers. Unmounting calls them in reverse order. Nothing else needs to know
how to undo a QC filter — the QC plugin already said.

### What "spatial" buys

A plugin declares what it **needs** and what it **provides**. The kernel resolves the graph and
knows, continuously:

- which plugins *can* run on the current state, and which cannot and exactly why;
- what becomes invalid the moment anything upstream is mounted, unmounted or reconfigured;
- what is **missing** to answer a question the user asked.

That last one is what makes the harness feel like it is thinking: *"you have labels but no design
table, so you can have an interaction map but not a between-condition comparison — here is what to
add."*

---

## 5. Everything is a plugin — including the parts that usually are not

Analysis steps being plugins is the obvious half. The half that matters:

| plugin class | examples | why it must be swappable |
|---|---|---|
| **method** | QC, annotation, integration, velocity, regulons, communication | the obvious one |
| **executor** | local, PBS, SLURM, cloud | the same stack must run on a laptop and a cluster. Where compute happens is not part of what the analysis *is* |
| **storage** | local FS, object store, tiered/online-only | a multi-GB object inside a syncing folder is a real problem, already hit |
| **gate** | reversibility, freshness, design confounding, sentinel handling | a gate that is a plugin can be listed, audited and reported. A gate hard-coded in a script is one nobody knows fired |
| **report** | HTML, notebook, manuscript figures | one dataset, several audiences |
| **provenance** | the event stream itself | §8 |
| **decision-maker** | a human at a prompt; an agent proposing the next step | an agent is another plugin, subject to gates it cannot disable — the only safe way to let one near this |

The last row is deliberate. An agent that inspects the mounted tree, proposes a step, and is
*refused by a gate it cannot switch off* is a fundamentally different thing from an agent writing
pipeline scripts.

---

## 6. What it looks like

The thesis is only worth anything if using it is obviously better. A reviewer asks the question
every single-cell paper eventually gets: *how sensitive is this to your QC?*

```console
$ sch stack
  observations   10 libraries, 39,037 droplets      immutable
  ▸ align@celescope       2.7.3                     checkpoint
  ▸ ambient@cellbender    lr=5e-5 fpr=0             checkpoint
  ▸ qc@scqc               0.4.0   masks 6,851 obs   mounted
  ▸ annotate@scanno       0.10.0  labels 4 columns  mounted
  ▸ integrate@scintegrate 0.4.0   provides 5 embeddings, default X_scanvi
  ▸ profile@velocity      REFUSED — no spliced layer beside this object

$ sch unmount qc@scqc --dry-run
  would restore 6,851 observations
  would invalidate, in order:
    annotate@scanno          labels were fitted on the masked set
    integrate@scintegrate    5 embeddings, all of them
    12 figures, 3 tables, 1 report
  checkpoints are unaffected: ambient@cellbender does not rebuild

$ sch fork no-qc --without qc@scqc
$ sch run no-qc && sch diff main no-qc --on composition
  cell type           main      no-qc     Δ
  Cardiomyocyte      37.3%     34.9%   -2.4pp
  Endothelial        24.3%     24.1%   -0.2pp
  ...
  one population moves more than 1pp. The QC decision is load-bearing for it
  and not for the rest; the report says so.
```

Today that costs a full re-analysis, which is why nobody does it, which is why nobody knows how
sensitive their results are to their own decisions. Here it costs one command and the compute for
what actually became invalid.

The same shape answers other questions that are currently out of reach:

- *Which of our four QC decisions is this finding sensitive to?* — unmount each in turn.
- *A reviewer wants it without ambient correction.* — that is a fork from a checkpoint, not a
  re-run from FASTQ.
- *Two labs disagree.* — diff the stacks, not the results.

---

## 7. The plugin contract

Specified in full in [`PLUGIN_FORMAT.md`](PLUGIN_FORMAT.md); the shape of it here.

**Vocabulary.** *Kernel* means the runtime core — the one thing that mounts, unmounts and resolves.
Everything mounted on it is a **plugin**. A plugin is a directory with a manifest and an entry
point; the kernel never imports it.

```yaml
# plugins/qc/scqc/plugin.yml
name: qc@scqc
version: 0.4.0
provides:
  - obs_mask                    # it masks observations
  - obs/qc_*                    # and adds columns matching this pattern
needs:
  - checkpoint: ambient         # or `counts` if no ambient step is mounted
declares:
  reversible: true              # returns a disposer; the kernel can unmount it
  differential_check: required  # removal rate must be measured across design arms
cannot_show:
  - A cell passing QC is not a cell that is intact; it is one whose summary
    statistics fall inside chosen thresholds.
executor:
  cost: high                    # the scheduler plugin decides where this lands
```

Three fields carry the weight:

- **`provides` / `needs`** are how spatial composability works. They are capability *contracts* —
  "something that provides an embedding", not "harmony" — so implementations are swappable.
- **`reversible`** is a claim the kernel tests. A plugin declaring `true` that fails to return a
  working disposer fails at mount, not silently at unmount.
- **`cannot_show`** is required, not optional. A plugin must state what its output does *not*
  establish, and the report prints it beside the result. This exists because a result whose limits
  were never written down reads exactly as authoritative as one whose limits were thought about.

`scProfile` already implements a single-stage version of all of this — declared `needs`/`produces`,
prerequisite resolution before anything is spent, guards with logged escapes, cross-environment
subprocess isolation, a validated JSON manifest, and `cannot_show` on every plugin. **The harness is
that contract promoted from one stage to the life cycle.** That it already works is the strongest
evidence available that this is buildable.

---

## 8. The provenance inversion

Today provenance is a **log written after the fact** — run logs, provenance files, `uns` blocks. It
describes what happened, is written by the thing that did it, and is wrong whenever someone forgets.

Here the relationship inverts. **The stack IS the provenance**, and the object is generated from it.
There cannot be an object with missing provenance, because the object does not exist independently
of the stack that produced it.

- A dataset ships as **a stack plus a pointer to the observations** — kilobytes, not gigabytes.
- Two labs **diff their analyses**, not just their results.
- A published result carries a stack a reader can **re-materialise and perturb**.

The invariant, borrowed from DeepSeek Harness's *model-visible ⟺ logged*: **report-visible ⟺
replayable.** Every number in a report must be reconstructible from the event stream. Anything that
cannot be is not allowed on the page.

---

## 9. What already exists, and why none of it is this

| | what it does | why it is not this |
|---|---|---|
| **Nextflow / nf-core, Snakemake, CWL, WDL** | orchestrate jobs over files, with resume and containers. Mature, excellent, widely used | They model **files and jobs**, not a dataset with revertible operations. A DAG runner knows file A produced file B; it cannot tell you step 3 removed 8,427 cells unevenly across your design arms, because it does not know what a cell is |
| **Galaxy** | GUI, reproducible histories, a large tool library | A history is a linear record, not a mountable stack. You cannot unmount step 2 and keep steps 3–6 |
| **scverse (scanpy / anndata / muon)** | the object model and the algorithms all of this stands on | A library, not a runtime. AnnData is deliberately mutable and has no notion of an operation that can be reverted |
| **Seurat / Bioconductor** | the R half of the same | same |
| **Terra, Latch, Pluto, Cellenics** | managed execution, provenance, sharing | Platform-as-a-service around the pipeline model — better hosting of the same abstraction |
| **MLflow / W&B / DVC** | experiment tracking, data versioning | Tracks runs and files. Does not model the *semantics* of operations, so it cannot invalidate reactively or say what a step destroyed |

**The gap in one sentence:** existing systems reproduce *what you ran*; none can tell you *what it
cost you*, or let you take it back.

---

## 10. What the harness decides, and what it must never decide

**It decides:** which plugins are runnable given the current stack; the order they must run in;
what is now invalid; where each should execute given cost and available executors; and what is
missing to answer a stated question.

**It proposes, and never decides:** which method is *right* — it may rank, and must show the
figures a ranking cannot substitute for; whether a stage is finished; whether to accept a removal,
a correction, or a stale artifact.

**The refusal is a first-class output, not an error.** Most datasets reaching this system will lack
spliced counts, ATAC, spatial coordinates, or a design table. A harness whose commonest output is a
clear refusal naming the fix is working correctly — and that is precisely the behaviour most likely
to be removed later as unhelpful.

---

## 11. A platform for methods, not only a runner of them

The four tools it orchestrates are its first users. They are not the point.

The point is that **the next method — one we write — is a plugin, and gets the substrate for
free.** A platform earns that name only if building on it is less work than not building on it, and
that is a testable claim, not a slogan: *if writing a new method as a plugin is harder than writing
it as a script, the platform has failed and should be told so.*

### What a method author should never have to write again

| the substrate provides | which today is re-written every time |
|---|---|
| reading and validating an object; detecting label, sample, batch, counts keys; organism and assay | ~200 lines of key-guessing per project, wrong in a new way each time |
| an isolated, pinned environment with a selftest that runs the real thing | a `requirements.txt` that resolved differently last Tuesday |
| execution placement — laptop, cluster, cloud — from the same declaration | a hand-written job script per method per site |
| provenance: what ran, at what version, on what, with which parameters | a run log written afterwards from memory |
| a report with captions, vector figures at column width, and source data per panel | the week before submission |
| **comparison against every existing method on identical data, metrics and figures** | a bespoke benchmark, usually written by the person who wants to win it |
| refusal when the data cannot support the method, naming the fix | a crash, or worse, a number |

What the author writes is the method. That is the whole deal.

### The graduation path

A method should move from idea to published tool without being rewritten at any step. Only its
manifest changes.

```
  scratch      a directory with a run.py and a hand-written manifest
               mounted live, no install, reload on save
      ↓        (nothing here is quotable; nothing downstream may read it)
  dev          a lock, a selftest, a cannot_show, a declared reversibility claim
               now benchmarkable against every shipped method
      ↓
  shipped      versioned, its own repository if it deserves one
               mounted by name like any other plugin
```

The first row matters most and is the easiest to under-build. **A method under development must be
mountable without installation**, because the loop between changing a line and seeing its effect on
real data is where all the time goes. A platform that requires a package build per iteration will be
abandoned for a notebook, and the work will leave the system that was supposed to hold it.

The third row is where most platforms quietly fail their users: a plugin that graduates should keep
running. See below.

### What the platform owes, and what that costs it

A platform makes promises a library does not. These are the ones worth making:

- **A versioned contract.** A plugin that mounted a year ago still mounts, or the breakage is
  announced, dated, and has a migration.
- **Deprecation with notice**, never silent behaviour change. A parameter that quietly changes
  meaning is worse than one that is removed loudly.
- **The substrate is not privileged.** Our own methods use the same contract as anyone else's, with
  no private hooks. The moment the platform's authors have access a third party does not, everyone
  else is a second-class citizen and the plugin model is decoration.
- **The escape hatch stays open.** Any plugin can be run standalone, outside the harness, from its
  own CLI. If the harness is the only way to run something, it has stopped being a platform and
  become a dependency.

The cost is real and should be stated: **these promises take away the freedom to change our minds
cheaply.** That is what it means to be a foundation rather than a project, and it is the reason the
contract has to be got roughly right before there are plugins depending on it — which is why this
document exists before the code.

---

## 12. How a platform lets you fool yourself

**The most dangerous user of a benchmarking platform is the author of the method being benchmarked.**

This is not hypothetical. In the integration tool that will mount here, a supervised method ranked
first on biological-conservation metrics computed against the very label column it was trained on.
The code was correct, the metrics were correct, the ranking was not like-for-like, and it took a
deliberate adversarial read to notice. Nobody was being careless.

Once our own methods are developed here, we will make that mistake again in a form we do not
recognise — because we will be the ones who chose the metric, chose the baseline, and knew what we
hoped to see. A platform that makes benchmarking easy without making self-deception hard is a
machine for producing convincing wrong results.

So the evaluation contract ships **guards aimed at the platform's own owners**:

- **The comparison is a plugin, not a script.** Identical data, metrics, figures and weighting for
  every entrant, ours included. Nobody hand-writes the benchmark their method appears in.
- **The baseline is mandatory and always runs first.** *Doing nothing* is an entrant. Without it a
  comparison can only say which method is strongest, never whether any was warranted.
- **Information asymmetry must be declared.** A method that saw the labels, the design, or the
  evaluation split says so in its manifest, and the report states it wherever the ranking appears —
  not in a methods appendix.
- **The metric is recorded before the result is seen.** The event stream is ordered, so *when* a
  metric was chosen relative to when a result was looked at is a fact on disk, not a memory.
- **Held-out by construction.** The platform can withhold a split a method never sees, because it
  owns the data access layer and the method does not.
- **Ablation is cheap, so it is expected.** Fork the stack, swap one plugin, hold everything else
  constant.

That last point is the deepest reason to develop methods here rather than in a notebook. **A decision
stack is a controlled experiment.** Method development normally spends most of its effort building
that control by hand — matching preprocessing, matching gene sets, matching seeds — and most
published comparisons are weaker than their authors believe because some of it silently did not
match. Here, everything except the swapped plugin is the same object by construction.

---

## 13. Architecture

```
                    ┌────────────────────────────────────────────┐
                    │  KERNEL                                    │
                    │   mount · unmount · reconfigure            │
                    │   dependency graph + reactive invalidation │
                    │   event stream (append-only, replayable)   │
                    └────────────────────────────────────────────┘
                          │ services
  ┌──────────────┬────────┴───────┬───────────────┬────────────────┐
  │ observations │ executor       │ storage       │ gates          │
  │ (immutable)  │ local/PBS/…    │ fs/object/…   │ auditable      │
  └──────────────┴────────────────┴───────────────┴────────────────┘
                          │
        ┌─────────────────┴──────────────────┐
        │  MOUNTED STACK                      │
        │   qc@scqc          mask + reason    │
        │   annotate@scanno  label columns    │
        │   integrate@…      embeddings       │
        │   profile@…        per-plugin       │
        └─────────────────────────────────────┘
                          │  materialise on demand
              ┌───────────┴────────────┐
              │ .h5ad · report · figures · notebook
              └────────────────────────┘
```

**Adapters, not rewrites.** scQC, scAnno, scIntegrate and scProfile keep their own repositories,
locks, versions and users. The harness mounts each through a thin adapter over the CLI and manifest
contract it already has. Nothing built so far is discarded, each tool stays independently
installable, and if an adapter is ever thicker than a rewrite the contract is wrong — which is
worth finding out early and cheaply.

---

## 14. The order of proof

Not a roadmap. The sequence in which the thesis is tested, cheapest disproof first.

1. **Can a decision be unmounted?** QC alone. Mount a filter as a mask, unmount it, show the cells
   return and every downstream view updates. **If this is not clean the thesis is wrong**, and
   everything after it is wasted. Do this first and try hard to break it.
2. **Can invalidation be reactive?** Change one threshold; watch every dependent artifact go invalid
   with nobody remembering.
3. **Do the four existing tools mount unchanged?** If an adapter is thicker than a rewrite, the
   contract is wrong.
4. **Can the executor be swapped?** Same stack, laptop and cluster, same result.
5. **Can a stack be shipped and re-materialised** by someone else, from observations plus kilobytes?
6. **Can an agent be a plugin** that a gate refuses and it cannot disable the gate?
7. **Is writing a new method here less work than writing it as a script?** Take a real method we
   want anyway, build it both ways, and count. If the plugin version is longer, the substrate is
   not paying for itself and §11 is a claim we have not earned.
8. **Does a benchmark of our own method survive an adversarial read** by someone told to find the
   asymmetry? Run it against §12's guards before believing any result they produce.

---

## 15. Non-goals

- **Not a new object model.** AnnData and `.h5ad` stay. A harness needing its own format has
  already lost.
- **Not new methods — in the harness itself.** The kernel contributes zero algorithms; its value is
  entirely in composition. Methods we develop live in plugins, on the same contract as everyone
  else's, with no privileged access.
- **Not a GUI first.** The event stream makes a UI easy later; building the UI first makes the
  kernel bend around it.
- **Not a replacement for Nextflow.** If someone wants a DAG runner underneath as an executor
  plugin, good.
- **Not cloud-first, and not cloud-hostile.** The executor is a plugin.
- **Not an autonomous analyst.** An agent may propose; gates it cannot disable stand between it and
  the data.

---

## 16. How this fails

Stated in advance so it can be checked later.

- **Reversibility turns out expensive.** If materialising a view from a deep stack is slow, people
  bypass the stack and the property justifying the whole design becomes optional. *The biggest
  risk, and why step 1 of the order of proof exists.*
- **Adapters rot.** Four tools evolving independently behind adapters is four chances for a term to
  quietly change meaning. The contract must be versioned and tested or it becomes folklore.
- **The checkpoint layer swallows everything.** If in practice most interesting operations turn out
  not to be maskable, the stack is thin and the thesis is mostly the checkpoint graph — which is
  Nextflow with extra words.
- **The gates get switched off.** A gate that fires on correct behaviour gets disabled; this
  project has the escape logs to prove it. Gates as plugins must be auditable and their escapes
  recorded, never merely absent.
- **It becomes a workflow manager with extra words.** If a year in the only thing it does is run
  four tools in order, the thesis was wrong and it should say so plainly rather than accrete
  features.
- **The platform serves its authors first.** The fastest way to kill the plugin model is a private
  hook only our own methods use. It will be tempting exactly once, at the moment our method needs
  something the contract does not offer, and the honest move then is to extend the contract for
  everyone or do without.
- **The benchmark becomes a machine for confirming what we hoped.** §12 exists because this is the
  most likely way this project produces something wrong and convincing, and guards that inconvenience
  their own authors are the first ones quietly relaxed.

---

## 17. What is borrowed, and from where

**Inspired by [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) (MIT) and the
[Cordis](https://github.com/cordiverse/cordis) kernel it is built on.** Several load-bearing ideas
below are theirs, and the honest thing is to name which.

| borrowed | theirs | what it becomes here |
|---|---|---|
| **"Everything is a plugin"** | model adapter, tool registry, session log and *the agent loop itself* are all plugins | method, executor, storage, gate, report, provenance and decision-maker are all plugins |
| **`register()` returns the disposer** | contributions via `ctx.effect()` / `ctx.on()`; every side effect yields its own undo | **the mechanism for reversible analysis.** A filter returns the mask that lifts it |
| **Capability seams** — definition / provider / consumer as separate roles | how their packages are organised | a plugin declares a capability contract, not an implementation |
| **Manifest-driven resolution with overlay composition** | plugins mount from declarative config that layers | a stack is a layered manifest: site overlay, project overlay, run overlay |
| **"Model-visible ⟺ logged"** | anything reaching a model request must be reconstructible from the session log | **"report-visible ⟺ replayable"** — our evidence rule, made structural |
| **Monotonic `SCHEMA_VERSION`** | on the session format, with pre-release compatibility explicitly not promised | the same for the stack format; scProfile already does this with `CONTRACT_VERSION` |
| **Agents as plugins** | other coding agents mount as sub-agent plugins | an agent proposing a step is a plugin, subject to gates it cannot disable |

**Concepts, not code.** DeepSeek Harness is TypeScript/Node organised around an agent loop over a
session. This is Python organised around a dataset — the scientific stack is Python and that is not
negotiable. No source is vendored. If any is later, its MIT notice travels with it and
`NOTICE.md` records the file, the upstream commit and the licence.

**What we add, because their plugins contribute behaviour and ours contribute claims a scientist
will publish:**

- a **differential-effect check** on every removal — a filter taking 53% of one sample and 6% of
  another is a technical property masquerading as biology, and no general-purpose kernel has reason
  to care
- **`cannot_show`** as a required field
- **checkpoints** — the honest admission that part of the stack is rebuild-only (§3)
- **gates as auditable plugins with logged escapes**

---

## 18. The name

**`single-cell-harness`.** Decided, not proposed.

It says what the thing is in the words a biologist would use, and nobody has to learn a coined term
before telling a colleague what they are running. The four tools underneath keep their `sc*` prefix
and their own identities; the umbrella does not compete with them for that space.

Two costs, recorded so the question is not re-opened by accident. It names the **mechanism** rather
than the thesis — `scStack` would have put the decision stack, the genuinely new idea, in the name,
and legibility won that trade. And **"harness"** is DeepSeek's word for this class of system, which
is deliberate: it *is* that class of system applied to single-cell data, and §17 says how much of it
is theirs.

---

## 19. What I want argued with

- **Reversibility or invalidation?** They are separable. If forced to build one I would build
  invalidation — staleness is the failure that has actually cost this project the most. Reversibility
  is the more beautiful property; invalidation is the one that has been bleeding.
- **Is the checkpoint layer bigger than §3 admits?** If most real operations are not maskable, the
  thesis shrinks to a checkpoint graph and this becomes a workflow manager.
- **Is agent-as-plugin load-bearing or decoration?** It is the most fashionable part of this and
  therefore the part I trust least.
- **Is "orchestrate, don't absorb" right long-term**, or does it defer a migration that gets harder
  every month?
- **Should the kernel be a thin Python port of Cordis** rather than an independent design, so the
  two stay compatible as Cordis evolves?
- **Which failure mode is missing from §16** — and is it the one that will actually happen?
