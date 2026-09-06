# Roadmap

The order in which this gets built, and **how each step can fail.**

Two rules govern the whole plan.

**Every phase can stop the project.** A phase is not a task list; it is a claim with a test. If the
test fails, the honest outcome is to stop and say what was learned, not to carry the failure into
the next phase where it becomes expensive. The phases are ordered by *cheapest disproof first* —
the thesis is attacked before anything is built on it.

**The four tools are not touched.** No commit lands in `scQC`, `scAnno`, `scIntegrate` or
`scProfile` for any phase below. Adapters live in this repository. Where a tool does not expose
something an adapter needs, **that is a finding about the contract**, recorded and worked around —
not a reason to reach into the tool.

A phase ends when it is declared finished, not when its tests pass. Passing tests are evidence for
that decision; they are not the decision.

---

## Phase 0 — Disprove it

**Claim.** A decision can be mounted and unmounted cleanly, and materialising a view from a stack
is fast enough that nobody bypasses it.

**Build.** The smallest possible thing: an immutable observation set, one mask plugin, mount,
unmount, materialise. No adapters, no profile machinery, no agent, no report.

**Evaluation.**

| | pass |
|---|---|
| unmount restores | the materialised view after mount→unmount is **identical** to before, by digest |
| downstream invalidates | mounting B on A, then unmounting A, marks B invalid without B being consulted |
| materialisation cost | a 5-deep stack over ~100k observations materialises in **< 30 s**, warm |
| stack size | the stack that regenerates it is **< 1 MB** |

**Falsifier.** If materialisation is slow, people will bypass the stack and keep a filtered `.h5ad`
on the side — and the property that justifies the entire design becomes optional. This is the
largest risk in `VISION.md` §19 and it is why this phase is first.

**If it fails:** stop. Write what the cost actually was. The remaining phases are worth nothing
without this one.

> **PASSED, 2026-08-19.** Measured at 100k and at 1M observations: materialisation 0.01 s and
> 0.06 s against a 30 s target, stack 0.3 KB, unmount digest-identical, downstream invalidated
> without being re-run, observation writes raise. Four findings in
> [`spike/phase0/README.md`](spike/phase0/README.md) — the load-bearing ones being **F2**, the
> kernel costs three orders of magnitude less than the work it orchestrates, so what the design
> buys is free *invalidation* rather than fast analysis; and **F3**, the target was tested against
> view construction and not serialisation, which Phase 3 must measure against a real tool rather
> than inherit.

---

## Phase 1 — The kernel, domain-free

**Claim.** The core can be built without knowing what a cell is (**L2**).

**Build.** `Context`, `Service`, `inject`, effect/disposer, registry → runtime, the typed event bus,
`stack.yml` loading with overlay composition. Also: the materialisation **fold** keyed by
`state_version` (**D6**), `service/invariant` and the four kernel companions
([ADR-0008](docs/adr/0008-runtime-conformance-companions.md)), and `sch stack --dump`.

**Evaluation.**

| | pass |
|---|---|
| **L2, the real test** | the same kernel runs a **toy non-biological profile** — a table of rows with a filter plugin — with no change to `core/` or `registry/` |
| L1 | no import from a higher layer, checked statically |
| L3 | the kernel imports no plugin module |
| C4 | the process boundary carries JSON only |
| E3 | disposers run in exactly reverse mount order, asserted |
| composition | `sch stack --dump` and a real mount call the **same** composition function — a dump that can drift from what mounts is a dump nobody can trust |
| D6 | a contribution concerning no view costs one comparison; a bumped `state_version` invalidates the cache and nothing else does |
| companions | the four kernel companions mount, and each **fails on a planted violation** — A1, A2, D4, P2 |

**Falsifier.** If the toy profile needs a core change, L2 is already broken and the single-cell
assumptions are load-bearing in the engine. Fix it here; it never gets cheaper.

> **BUILT, 2026-09-06.** `sch/core`, `sch/registry`, the fold (`sch/registry/fold.py`), the
> services and `sch/kernel.py`. The toy profile is `sch/profile/table.yml`; every kernel test in
> `tests/test_kernel_table.py` runs on it, and `sch doctor --architecture` asserts L1, L2 and L3
> over the source. The four kernel companions and the plugin companion each fail on a planted
> violation in `tests/test_companions.py`. A 63-test suite passes on the workstation; the cluster
> run is recorded under the project's `runs/single-cell-harness/00_kernel/`. Declared finished
> only when that run is sealed — passing tests are evidence, not the decision.

---

## Phase 2 — The profile and the validator

**Claim.** The contract is precise enough to be checked mechanically.

**Build.** The single-cell profile — slots, key map, identity rule, sentinels, merge — plus
`sch plugin validate` (15 static checks) and `sch plugin test` (env, selftest, fixture,
mount/snapshot/unmount/compare, companion).

**Evaluation.** A deliberately broken plugin per rule, and the validator catches each:

```
hard-codes a column name        → rejected (C3 / profile key map)
declares stack, behaves as checkpoint → rejected at mount (E4)
lock with a range not ==        → rejected
cannot_show empty               → rejected
sees absent                     → rejected
merges by position              → rejected with both counts
gate names a probe that does not exist → rejected (G3)
gate declares a verdict outside the three → rejected (G4)
contributes without state_version → rejected (D6)
neither invariant.py nor a stated reason → rejected (ADR-0008)
README with an empty Known limitations → rejected
```

**Every rejection is proved by regression, not by inspection.** A check only checks if the broken
plugin actually fails it: write the break, watch it fail, keep the pair. A validator rule with no
plugin that trips it is a rule nobody has run.

**Falsifier.** A rule that cannot be checked and cannot be tested adversarially is a rule that will
be violated silently. Either make it checkable or delete it from the format.

> **BUILT, 2026-09-06.** `sch plugin validate` (`sch/plugin/validate.py`) and `sch plugin test`.
> `tests/test_validator.py` trips every one of the fifteen rules with a broken plugin. The
> single-cell profile is `sch/profile/single-cell.yml` with an h5ad reader and materialiser;
> the toy-profile plugins and a single-cell mask, probe and gate ship under `plugins/`.

---

## Phase 3 — One adapter: `qc@scqc`

**Claim.** An existing tool mounts without being modified, and the adapter is thinner than a
rewrite.

**Why scQC first:** it is the hardest. It exercises masks, a gate, a recorded approval, and a
checkpoint boundary (ambient) all at once. Any of the other three would pass more easily and prove
less.

**Build.** A coarse mount — one plugin — that **declares fine**: one mask *per criterion*, not one
opaque mask. scQC's `build_removal_record()` already pairs every removed observation with the
criteria that fired, so this costs nothing now and is the difference between a later split being a
move and being a rewrite.

**Evaluation.**

| | pass |
|---|---|
| **ADR-0004's own test** | adapter is **< 40%** of the estimated lines of a rewrite |
| no tool commits | `git log` in scQC is unchanged across the phase |
| **F3, the cost Phase 0 did not measure** | materialising to a **file** a real tool reads, timed and recorded — and a second run under an unchanged tuple pays it **once** (**D6**) |
| unmount | restores every masked observation, by digest |
| split-ready | each criterion's mask is separately addressable while still mounting as one plugin |
| numbers | a mounted run reproduces a standalone scQC run **exactly**, not approximately |

**Falsifier.** An adapter thicker than a rewrite means the contract is wrong. **Stop and fix the
contract**, do not write three more adapters against it.

---

## Phase 4 — Probes, and the gates that share them

**Claim.** A gate and its probe are one implementation, and an agent can reproduce any refusal.

**Build.** The probes behind existing gates first — `differential`, `integrality`, `freshness` —
then `composition`, `distribution`, `disagreement`, and `render`. Gates mount monotonically
(**G4**) and escapes are recorded as ask/decision pairs.

**Evaluation.**

| | pass |
|---|---|
| G3 | gate and probe return the **same number** on the same input, asserted, not by inspection |
| **G4** | the verdict of a set of gates is the same under **every permutation** of their order |
| G2 | every escape in a run has an ask *and* a decision in the stream; the companion fails a run where one is missing |
| refusal is a result | a gate that refuses and a gate that **dies** are distinguishable afterwards, and a refusal carries the number that caused it |
| `render` | returns an image a multimodal reader can act on — tested by having one describe a planted defect |
| cost | every probe declares a cost and the declared cost is within 2× of measured |

**Falsifier.** If a gate's measurement cannot be reused as a probe, G3 is unimplementable and gates
stay black boxes that get routed around.

---

## Phase 5 — The remaining adapters, and a full stack

**Claim.** The whole current pipeline runs as a stack and reproduces its own results.

**Build.** `annotate@scanno`, `integrate@scintegrate`. Then one real cohort end to end.

**Evaluation.**

| | pass |
|---|---|
| **reproduction** | every headline number matches the current pipeline's promoted results **exactly** |
| provenance | the stack alone regenerates every figure and table |
| no tool commits | still zero |
| refusals | a stack missing a prerequisite refuses with the fix named, at plan time, before compute |

**Falsifier.** A number that moves and cannot be explained is a defect in the harness, the adapter
or the original — and finding out which is the phase's real work. **A difference nobody can account
for stops the phase.**

---

## Phase 6 — Dissolve scProfile

**Claim.** scProfile's kernels are harness plugins, and nothing is lost in the move.

**Requires** an ADR amending 0004, naming what is given up: scProfile as an independently
installable tool.

**Build.** `velocity` first — it is built, tested and already conforms to a contract that is nearly
this one. Then `cellcycle`. scProfile's host becomes the reference kernel rather than a second one.

**Evaluation.**

| | pass |
|---|---|
| identical output | `velocity` mounted produces byte-identical results to `velocity` under scProfile |
| no second contract | one manifest, one merge path, one report engine |
| the roadmap survives | `ROADMAP.md`'s tier-1 plugins remain buildable under the harness contract |

**Falsifier.** If a scProfile kernel cannot be expressed as a harness plugin without loss, the
harness contract is narrower than the one it is replacing — which is a serious finding, since that
contract was written first and against real use.

---

## Phase 7 — Fork, diff, ablate

**Claim.** The worked example in the README actually runs.

**Build.** `sch fork`, `sch diff`, `sch unmount --dry-run` with the invalidation list.

**Evaluation.** The transcript in `README.md` is executed as a test and its output matches — a
QC-ablated fork, run, and diffed on composition, with the cost paid being only what was invalidated.

**Falsifier.** If a fork costs a full re-analysis, ablation is not cheap, and §12's claim that a
decision stack *is* a controlled experiment is false.

---

## Phase 8 — Benchmarks

**Claim.** A result can be scored rather than admired.

**Build.** The three kinds — independently labelled reference data, constructed truth, simulation —
each with `truth.yml` naming how each fact was established, and `LIMITS.md` naming what it cannot
establish.

**Evaluation.**

| | pass |
|---|---|
| **sensitivity** | a deliberately degraded stack scores **worse**, and the ranking matches what a person would give |
| independence | no benchmark's truth came from the class of method it scores — stated per fact, not assumed |
| the supervision guard | a label-supervised method's advantage is visible in the report without being told to look |

**Falsifier.** A suite that cannot separate a planted regression from an improvement measures
nothing, and every later claim about a method or an agent rests on it.

---

## Phase 9 — Executors

**Claim.** Where compute happens is not part of what the analysis is.

**Build.** `local` and `pbs` executor plugins.

**Evaluation.** The same stack run under each produces results identical to the tolerance each
method's own seeding allows — and where it does not, the difference is attributed before the phase
closes.

| | pass |
|---|---|
| **E5** | unmounting a plugin whose job is still queued or running **blocks until it has stopped**, and a job that cannot be confirmed stopped **fails the unmount** |
| late writes land nowhere | a job killed mid-write leaves nothing in the stack it was unmounted from |
| orthogonal facts | timed-out, stopped, and exit status are reported independently — a job that traps the signal and exits 0 is not read as a clean run |

**Falsifier.** If quiescence cannot be confirmed on a real scheduler, E5 is unimplementable there
and every digest comparison across an executor boundary is comparing against a moving file. Say so
before Phase 10 builds on it.

---

## Phase 10 — The agent surface

**Claim.** Reads are open and writes are not, and that holds against someone trying to break it.

**Build.** Scratch plugins, the read-only materialisation, the dataset summary, the propose → run →
inspect → promote loop.

**Evaluation.** **Adversarial, not confirmatory.** Code written to break the asymmetry:

```
write to the object directly from scratch code
mount past a gate without an escape being logged
turn another gate's refusal into a pass
quote a scratch number into a report
convert a checkpoint declaration to stack
promote scratch work without a human
read a credential out of the environment a scratch plugin was handed
land a result by writing a predictable path the kernel will later read
```

Each must fail. **Verify the world, not the self-report:** every assertion re-reads the object, the
stream or the report externally — a probe on the agent's own account of what it did is passed by an
agent that says the right thing. A1, A2, D4 and P2 are not statically checkable
(**ARCHITECTURE §8**); the companions assert them during a run, and this suite is what proves the
companions are not decoration.

**Falsifier.** One success is enough. §13 is decoration if any of these lands.

> **BUILT AHEAD OF ORDER, 2026-09-06**, because it is cheap and the children's interface work
> needed it: `sch scratch`, `sch promote`, the read-only materialisation, and
> `tests/test_adversarial.py` with the eight attacks above. Each fails against the world, not the
> self-report. The gates (Phase 4) exist as far as G3 and G4 are concerned: a gate receives the
> probe's answer and never measures, and the verdict is proved order-independent. Phases 3 and
> 5–9 are not built; the executor refuses `pbs` rather than pretending.

---

## Phase 11 — The last mile

**Claim.** A project ends in something submittable, generated from the stack.

**Build.** `publish` plugins: submission bundle, archive deposit, interactive result.

**Evaluation.** A real manuscript's figures, methods paragraph and source data regenerate from the
stack alone, and a reviewer opens the published result without installing anything.

---

## Not in this roadmap

Spatial, VDJ, ATAC, protein and perturbation profiles; multi-user and a shared registry; plugin
signing or a marketplace; a GUI. Each is a real question and none is answered here. Adding any of
them by stretching what exists is how a design becomes untestable — they get their own record
first.

## Where this plan is most likely to go wrong

- **Phase 0 passes on a toy and fails at scale.** The 100k-observation figure is in the test for
  that reason; a 5,000-cell spike proves nothing about the property that matters.
- **Phase 3's adapter is judged generously.** "Thinner than a rewrite" needs the rewrite estimated
  *before* the adapter is written, by someone willing to be wrong.
- **Phase 5 finds a discrepancy and it gets rounded off.** A number that moves without explanation
  is the most valuable finding in the whole plan and the easiest to wave through.
- **Phase 10 is run confirmatorily.** A suite written by the person who wrote the defence tests the
  defence they thought of.
- **The companions get written to pass.** An invariant check authored alongside the thing it checks
  is written against the same misunderstanding. The counter is the regression rule — every check
  ships with the break that fails it — and it is exactly the rule that feels redundant at the time.
