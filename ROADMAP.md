# Roadmap

> **2026-11-09 (ADR-0028):** [`GOALS.md`](GOALS.md) is the project goal. Where this roadmap's
> ordering conflicts with it, GOALS.md wins. The three rules that governed this plan until then
> are replaced below ([ADR-0029](docs/adr/0029-inherited-constraints-removed.md)). The tools are
> developed by the program in [`autodev/`](autodev/), under rule 1's gate. The phases remain the
> runtime's internal order.

The order in which this gets built, and **how each step can fail.**

How the plan is read. These rules replace the three that governed it until 2026-11-09. Each old
rule, what it protected and what was given up are recorded in
[ADR-0029](docs/adr/0029-inherited-constraints-removed.md).

**A phase is a claim with a test.** A phase is not a task list. The phases are ordered by
*cheapest disproof first*, so the thesis is attacked before anything is built on it. A failed test
is a finding. It is recorded as a gap against GOALS.md (`autodev/ledger/gaps.tsv`), with what was
learned, and its owner works it. It never stops the project or any other lane. Where a phase below
says "stop", read: the claim is not met, and the gap is not carried silently into the next phase.
*(Until 2026-11-09 the rule was "every phase can stop the project".)*

**The tools are developed under rule 1, not frozen.** Adapters live in this repository where the
contract allows it. A tool that does not expose what an adapter needs is still **a finding about
the contract**, but the fix may land in the tool, as a registered wave through rule 1's gate
([`autodev/RULES.md`](autodev/RULES.md)). *(Until 2026-11-09 the rule was "the four tools are not
touched".)*

**A phase is graded, not declared.** Whether a phase's claim holds is the audit's grade on its
test, PASS or not, with evidence. A doc claim is not evidence, and no agent's declaration ends one;
the PI may override a grade (RULES tier I). *(Until 2026-11-09 the rule was "a phase ends when it is declared finished".)*

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

> **PASSED, 2026-08-19; re-run as a SEALED run 2026-09-06.** Measured at 100k and at 1M
> observations: materialisation 0.01 s and 0.06 s against a 30 s target, stack 0.3 KB, unmount
> digest-identical, downstream invalidated without being re-run, observation writes raise. The
> first run wrote its evidence into a project's scratch tree — a directory the site layout says
> anyone may delete without asking — so this phase cited numbers nobody could check twice. It is
> now run key `20260906T124032Z__sch-2138f75__00_phase0`, sealed `exit=0`, with a
> `STATUS.json` carrying every claim and what the phase **cannot** show. Four findings in
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
> violation in `tests/test_companions.py`. 66 tests pass on the workstation (three skip without
> anndata) and on the cluster: run key `20260906T100104Z__sch-62a08a5__00_kernel`, PBS job
> 706136, sealed `exit=0`, `STATUS.json` `ok`, after three sealed FAILED runs that each found a
> real defect in the h5ad reader. `sch conform --run` over the three promoted stage runs of the
> reference project reported one gap each — no `STATUS.json` — and nothing else, which is the
> gap `docs/STATUS_CONTRACT.md` exists to close. Phase 1 is declared finished on that evidence.

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
| tool commits | each passed rule 1's gate; "`git log` in scQC is unchanged across the phase" was withdrawn by ADR-0029 |
| **F3, the cost Phase 0 did not measure** | materialising to a **file** a real tool reads, timed and recorded — and a second run under an unchanged tuple pays it **once** (**D6**) |
| unmount | restores every masked observation, by digest |
| split-ready | each criterion's mask is separately addressable while still mounting as one plugin |
| numbers | a mounted run reproduces a standalone scQC run **exactly**, not approximately |

**Falsifier.** An adapter thicker than a rewrite means the contract is wrong. **Stop and fix the
contract**, do not write three more adapters against it.

> **BUILT, NOT YET GRADED, 2026-11-09 (W010, branch `autodev/W010-qc-adapter`).**
> `plugins/single-cell/qc@scqc` runs scQC's real CLI (`describe`, then `run`) over the libraries a
> stack declares. They are declared as **a parts manifest**: scQC's own samplesheet, one row per
> library, scoped by `{sample}`. The kernel took one observation file, and no cohort is one. The
> adapter contributes one whole mask per criterion, the measured columns, and scQC's tables and
> objects referenced in place. It adopts scQC's `STATUS.json` and seal: ok is contributed, refused
> is the mount's refusal with scQC's fix, anything else is a death. Ambient correction stays a
> checkpoint beneath the mount, read as delivered (D1).
>
> Graded on a synthetic cohort, through the `sch` CLI against a stand-in scQC
> (`tests/test_the_harness_runs_scqc.py`):
> - **unmount** holds: every observation is restored, and the view's digest equals the pre-mount
>   digest;
> - **split-ready** holds: one mask per criterion, each addressable.
>
> Not yet graded:
> - **numbers** waits on the pre-declared reproduction on the reference cohort (W010's job, which
>   compares every scQC table with the promoted run);
> - **F3** is not timed;
> - **ADR-0004's test** has no rewrite estimate written before the adapter. The adapter is 242
>   lines, and its companion 69.
>
> **BUILT, NOT YET GRADED ON THE COHORT, 2026-11-09 (W026, branch `autodev/W026-anno-adapter`): the
> second adapter, `anno@scanno`.** `plugins/single-cell/anno@scanno` runs scAnno's real CLI over the
> libraries a parts stack declares: `describe`, then `cluster`, `annotate` once per library and
> `rescue`, each only when the stage declares it. Every flag is the stage's, by scAnno's name. Its
> labels are a **layer**: every obs column scAnno's delivered object carries that the library did
> not, and every one scAnno rewrote with other values. They are read back by identity with h5py,
> so anndata is not needed. Unmounting removes exactly those columns. scAnno's
> `STATUS.<cmd>.json` and seals are adopted, each only when it names the call's own argv.
>
> Graded on a synthetic cohort through the `sch` CLI (`tests/test_the_harness_runs_scanno.py`):
> - against a stand-in scAnno: the exact calls in scAnno's order, the layer, rule 2, every refusal,
>   and every death;
> - against the real scAnno 0.12.0: mounted, then unmounted to the pre-mount digest.
>
> Not yet graded: **numbers**, by the reference cohort's stage-2 reproduction through the harness
> against scAnno run alone at the same commit (written before it runs).
>
> **BUILT, NOT YET GRADED ON THE COHORT, 2026-11-10 (W034, branch `autodev/W034-int-adapter`): the
> third adapter, `int@scintegrate`.** `plugins/single-cell/int@scintegrate` runs scIntegrate's real
> CLI (`python -m scintegrate.cli`, the declared checkout on PYTHONPATH and nothing else) over the
> one object a parts stack declares, the cohort's joint object, read in place: `describe`, `doctor`,
> then one `integrate`. Every flag is the stage's, by scIntegrate's name; the assay and the species
> are the stack's `--context`. Its result is a **layer**: every obsm and obsp entry and every obs
> column scIntegrate's object carries that the part did not, or carries with other values, read back
> by identity with h5py (`embeddings/<key>.npy` and `graphs/<key>.npz`, each beside `barcodes.txt`).
> scIntegrate's `STATUS.json` and seal are adopted when they name the call's own argv. The view's
> digest now covers embedding and graph contributions by their content, so a layer of embeddings
> alone is visible at mount and E4 can see it taken back; a view without them hashes as before.
>
> Graded on a synthetic object through the `sch` CLI (`tests/test_the_harness_runs_scintegrate.py`):
> - against a stand-in scIntegrate: the exact calls and argv, the layer (added, rewritten, copied
>   entries left out, compared by identity), rule 2 and the species, every refusal and every death;
> - against the real scIntegrate 0.5.0: mounted, then unmounted to the pre-mount digest.
>
> Not yet graded: **numbers**, by the reference cohort's stage-3 run through the harness against
> scIntegrate run alone at the same commit in the same job (written before it runs).
>
> **BUILT, NOT YET GRADED ON THE COHORT, 2026-11-11 (W036, branch `autodev/W036-prof-adapter`): the
> fourth adapter, `prof@scprofile`.** `plugins/single-cell/prof@scprofile` runs scProfile's real CLI
> (`python -m scprofile.cli`, the declared checkout on PYTHONPATH and nothing else) over the one object
> a parts stack declares, the cohort's integrated object, read in place: `doctor` (a record), then one
> `run`. Every flag is the stage's, by scProfile's name, `--kernel` included: which plugins run is
> scProfile's own plan, and one it skipped is named with its reason. The design sheet, the assay and
> the organism are the stack's; the family's `scrna`/`snrna` are written in scProfile's words
> (`cell`/`nucleus`), because a word it does not reason about switches its assay caveats off. Its
> result is a **layer**: the tables and the object scProfile wrote, referenced where they lie, and
> exactly what its `report.json` says it merged into the object, read back by identity. Differential
> expression and abundance are per population, so their mount leaves the view's digest as it was.
>
> Graded on the synthetic fixture through the `sch` CLI (`tests/test_the_harness_runs_scprofile.py`):
> against a stand-in, the calls and argv, the layer, rule 2, every refusal and death; against the real
> scProfile (de and abundance), the three tables byte-identical to scProfile run alone. Not yet graded:
> the reference cohort's stage 4 through the harness against scProfile alone in the same job; the
> plugins beyond de and abundance (a later run).

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
| tool commits | each passed rule 1's gate ("still zero" withdrawn by ADR-0029) |
| refusals | a stack missing a prerequisite refuses with the fix named, at plan time, before compute |

**Falsifier.** A number that moves and cannot be explained is a defect in the harness, the adapter
or the original — and finding out which is the phase's real work. **A difference nobody can account
for stops the phase.**

---

## Phase 6 — One plugin format, read and mounted by the harness

> **Amended 2026-11-09 by [ADR-0030](docs/adr/0030-one-plugin-format.md).** Until then this phase
> was "Dissolve scProfile". Its claim was that scProfile's kernels become harness plugins with
> nothing lost, and it required an ADR amending 0004 that gave up "scProfile as an independently
> installable tool". GOALS.md gives PROF.1–PROF.4 to scProfile, as the family's universal tool
> runner, so the tool is not dissolved. The aim of the phase, one contract rather than two, is kept
> as one *format*: the maker's layout, which ADR-0030 adopts as the Universal Plugin Format (UPF).

**Claim.** Every plugin in the family either is in the UPF or maps onto it. The harness lists
every plugin, and mounts a UPF plugin with nothing lost.

**Build.**
1. `sch catalogue`, which reads every layout without importing a tool.
2. The mount: the harness runs a UPF plugin, velocity or cellcycle first, either through an
   adapter over scProfile's CLI (ADR-0004) or by reading the `PLUGIN` literal itself. It runs both
   of the format's execution phases: `run(ctx)` per unit, and `compare(ctx)` per arm pair where
   the plugin defines it, as cellchat does.
3. The maker makes ADR-0030's added keys required (`assays`, an exact `wraps.version`,
   `wraps.doi`).

**Evaluation.**

| | pass |
|---|---|
| one format | `sch catalogue` lists every plugin of the harness and of scProfile, with its format, and none is unreadable |
| identical output | a UPF plugin mounted through the harness produces byte-identical results to the same plugin under scProfile |
| AI-native (A4.4) | a cold agent picks a plugin from `sch catalogue --json` for a stated question and runs it through the agent surface |
| no second format | the harness's `plugin.yml` directory remains only for plugins the kernel itself mounts, until the kernel mounts the UPF |

The old evaluation row "the roadmap survives" is dropped. It said that `ROADMAP.md`'s tier-1
plugins remain buildable under the harness contract. The amended phase rebuilds no plugin under the
directory contract, because the plugins stay in the UPF. The "one format" row replaces it.

**Falsifier.** If a UPF plugin cannot be mounted by the harness without loss, the kernel's
contract is narrower than the format the pool uses. That is the serious finding the original phase
named, and it is kept.

> **BUILT IN PART, 2026-11-09 (W016, branch `autodev/W016-catalogue`): the catalogue.**
> `sch catalogue [show ID] [--scprofile CHECKOUT] [--json]` reads two sources:
> - the harness's `plugin.yml` directories;
> - a scProfile checkout's one-file and legacy `kernel.yml` plugins.
>
> It never imports a tool, and it names every file it cannot read. At scProfile `f5175ea` it
> lists:
> - 9 plugins, 0 of them unreadable;
> - 3 with an exact upstream version (velocity, scenic, cellchat);
> - 0 with a DOI;
> - 1 in the maker's layout (cellchat).
>
> No plugin declares its assays. The mount is not built.

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

> **`pbs` BUILT, NOT YET GRADED ON A SCHEDULER, 2026-11-09 (W010).** `executor: pbs` reads queue,
> select and walltime from the stack's or the site layer's `pbs:` block. The kernel holds no
> value for any of them and refuses a missing one before qsub. For each run:
> - the run directory exists before qsub;
> - the job's EXIT trap seals it, with the exit, the job id and any missing product;
> - the exit is read from that seal, then from qstat. A run that exits non-zero, is killed, or ends
>   with nobody recording how is a death, even after writing `out.json`;
> - a qstat outage is not an ending, and neither is a qstat call that times out
>   (`pbs.qstat_timeout_s`; qdel has the same bound). A job that sealed meanwhile has ended, and its
>   exit is its seal's. Otherwise the wait stops with `stopped: false`, and quiesce sends qdel. It
>   reports the job stopped only once qstat or the job's seal confirms it. Unconfirmed, it reports
>   `stopped: false`, and the command ends in an E5 error, never a success;
> - a full queue is waited for;
> - a stop is a qdel confirmed through qstat or the job's seal;
> - qsub has a timeout (`pbs.qsub_timeout_s`), and a qsub that did not answer - it timed out, or
>   exited 0 with no job id - is reconciled before anything is submitted again (autodev W029): the
>   scheduler is asked by job name, each job confirmed by the submission's token
>   (`#PBS -v SCH_SUBMISSION=...`) - or, for a job that has already ended on a server that keeps
>   no history, by the seal it wrote in the run; found, that job is the run's; absent from two
>   looks in a row, it is submitted again, at most `pbs.qsub_retries` (2) times; and when the
>   scheduler cannot say, nothing is resubmitted, the mount is refused naming the job, and the
>   disposer asks again or fails E5. A job the scheduler held for
>   "too many failed attempts to run" is not waited for: the wait returns with the hold in its
>   facts, and the disposer qdels it.
>
> Against a stand-in qsub/qstat/qdel (`tests/test_the_pbs_executor_submits_waits_and_seals.py`),
> **E5** holds: an unconfirmable stop reports `stopped: false`, and the companion fails on it.
> **Orthogonal facts** holds: a timeout reports timed-out, requested, stopped and the exit
> independently.
>
> Open:
> - identical results under `local` and `pbs` on one stack;
> - E5 against a real job;
> - "late writes land nowhere".

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
> 5–9 are not built; the executor refuses `pbs` rather than pretending. *(2026-11-09: Phase 3's
> first adapter and Phase 9's `pbs` executor are built by W010 and not yet graded; see their notes.)*

---

## Phase 11 — The last mile

**Claim.** A project ends in something submittable, generated from the stack.

**Build.** `publish` plugins: submission bundle, archive deposit, interactive result.

**Evaluation.** A real manuscript's figures, methods paragraph and source data regenerate from the
stack alone, and a reviewer opens the published result without installing anything.

---

## Not in this roadmap

Spatial, VDJ, ATAC, protein and perturbation profiles; multi-user and a shared registry; plugin
signing or a marketplace. Each is a real question and none is answered here. Adding any of them by
stretching what exists is how a design becomes untestable — they get their own record first.

The web interface is no longer on this list. It is GOALS.md HARN.4 and A6.1, the Harness UI, with
its own lane and record. It reads the event stream, and the kernel does not bend around it
(VISION.md §18; ADR-0029).

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
