# 0030 — One plugin format: the maker's layout, and a catalogue that reads every layout

**Status** Accepted 2026-11-09 by the program's pre-decider. Choosing the standard layout is a
design decision, not one of the PI's (autodev RULES tiers II and IV; GAP-006's `blocked_by`). The
coordinator adopts it and reports it to the PI, and the PI's reading wins.
**Date** 2026-11-09
**Affects**
- No ARCHITECTURE.md invariant is amended. L3, C4, E1 and D6 are read below for the adopted
  layout, and X2 for the migration.
- This record amends ADR-0004 and ROADMAP Phase 6, and adds a preface to PLUGIN_FORMAT.md.
- Wave W016: gaps GAP-006 and GAP-005; goals PROF.1, A4.1, A4.4 and HARN.2.

## Context

**Three layouts, measured.** The counts come from `sch catalogue` (this wave), run at harness
`c19802e` and scProfile `main` `f5175ea`.

| layout | where it lives | what defines it | plugins at the measured commits |
|---|---|---|---|
| **`plugin.yml` directory** | the harness's `plugins/` | PLUGIN_FORMAT.md and `sch plugin new`. The kernel mounts nothing else (`Stack.resolve_plugin`, `sch/kernel.py:97-128`) | 12. Seven are written against the toy `table` profile. Five are single-cell probes, gates and one mask. None declares `wraps`, so none wraps a published method |
| **one-file `PLUGIN`** | scProfile's `kernels/<name>.py` | `scprofile/plugin.py` and `scprofile/declare.py` (`API = 1`). Read without import by `FileKernel` (`scprofile/kernels.py:559`) | 9, each a published method |
| **the maker's layout** | the same file after the maker (`sch dev convert`) has finished with it. No field that the maker's declaration marks outstanding is set: `outstanding_if`, scProfile `DEVPOINTS.yaml:360` and `:405`. The maker's companions sit beside it: `<name>.signatures.json` (ADR-0026), and `<name>.draw.R` for an R upstream | scProfile `DEVPOINTS.yaml`, `points.kernel.convert`; harness ADR-0016 and ADR-0026 | 1: cellchat |
| `kernel.yml` directory | scProfile's `kernels/<name>/` | `Kernel` in `scprofile/kernels.py`: the six-file shape the one-file layout replaced, still loaded | 0 |

The maker's layout is not a third schema. It is the one-file layout in a finished state: the same
`PLUGIN` keys, with three differences:
- the figure plan is in ADR-0016's form;
- there is no admission of unreviewed plots;
- the generated companions sit beside it.

**Measured at `f5175ea`.**
- All 9 plugins read, and none is unreadable.
- 3 name an exact upstream version:
  - velocity: `wraps.version` 0.3.4;
  - scenic: `requires.packages` `pyscenic==0.12.1`;
  - cellchat: `requires.r`, CellChat at commit `75253cd`.
- 6 declare only a range.
- None declares a DOI, and the nine `PLUGIN` literals contain no DOI-shaped string.
- One is in the maker's layout: cellchat.
- No plugin declares the assays it supports. Four read the run's assay in their code: cellchat at
  2 sites, cellcycle at 3, liana at 1 and velocity at 4.

**Neither host reads the other's layout.** The harness's kernel resolves only `plugin.yml`
directories. scProfile's `discover()` reads its own two shapes (`scprofile/kernels.py:693`). Until
this wave, the harness's agent surface could not see any of the nine methods (GAP-005).

**The goals name the format by the maker.**
- PROF.1 asks for "a plugin in the Universal Plugin Format" (GOALS.md:63).
- A4.1 asks for the pool "in the maker's layout" (GOALS.md:100).
- A4.3 asks for a "peer-reviewed source and pinned version" (GOALS.md:102).
- A4.4 asks for an agent that lists the catalogue (GOALS.md:103).

The maker itself does not prefer a format. `sch dev convert` reads the target repository's
DEVPOINTS.yaml, and in scProfile that declaration describes the one-file layout.

**Two inherited constraints stand in the way.**
- ROADMAP Phase 6 ("Dissolve scProfile") asked this record to give up "scProfile as an
  independently installable tool". But GOALS.md layer 2 gives PROF.1–PROF.4 to scProfile, as the
  universal tool runner, and under ADR-0028 GOALS.md wins over the roadmap's ordering.
- RULES tier II: a plugin changes only through the maker, and the eight held-out plugins migrate
  one at a time.

## Options

1. **Adopt the `plugin.yml` directory.**
   - For it: it is domain-free (ADR-0007), language-neutral, and carries the kernel's semantics
     (layer, reversibility, gates, companions). A 15-rule validator checks it.
   - Against it: not one published-method plugin uses it. Every one of the nine would have to be
     re-declared, either by hand (which tier II forbids) or by re-targeting the maker at a format
     it has never emitted. Re-targeting fits the maker again, against the very plugins held out as
     its test set. scProfile's host would also need a second reader.
2. **Adopt the maker's layout.**
   - For it: the maker emits it, all nine methods are written in it, and A4.1 names it.
   - Against it: it has no keys for the kernel's semantics today, every plugin needs a Python host
     file, and there is no separate README.
3. **Keep one schema with two serialisations.**
   - For it: no migration.
   - Against it: every reader in every tool (the catalogue, the validators, the maker) would need
     both forms, for good. That is the defect class `tests/test_agent_surface.py` exists for: two
     descriptions of one interface, maintained by hand, drift apart.

## Decision

1. **The Universal Plugin Format (UPF) is the maker's layout.** A plugin is one Python file,
   `<name>.py`, made of five parts:
   - **`PLUGIN = {...}`** at module level: a literal read with `ast.literal_eval`, never imported
     by a host or a catalogue;
   - **`run(ctx)`**, the first execution phase. The host's shared entry point runs it as a
     subprocess, once per unit, in the plugin's own environment;
   - **`compare(ctx)`**, the second execution phase, optional. A plugin that defines it is called
     after every unit's `run` has finished. The host asks which phases the plugin implements
     (`_entry.py --phases`). It then runs `compare` in the plugin's own environment, once per arm
     pair of the design, in the direction the declared controls set. Where the design crosses more
     than two arms, it also runs `compare` once over all of them (`scprofile/report.py:853`).
     - The `CompareContext` holds the finished units' output directories, a directory to write
       into, the pair's label, the config, the core share and the figure context. It holds nothing
       of the object (`scprofile/_entry.py:432`, `scprofile/plugin.py:1321`).
     - A refusal exits 1 and is recorded. A failure is logged and never stops the report.
     - cellchat, the one plugin in the maker's layout, implements it for CellChat's own
       between-arm figures (`kernels/cellchat.py:5337`). A host for the UPF runs both phases;
   - **`guard(g)` and `selftest()`**, both optional;
   - **the maker's generated companions** beside it, each named `<name>.<what>`.

   A plugin is **complete** (format `maker`) when no field the maker's declaration marks
   outstanding is set and the maker's record `<name>.signatures.json` is present. Its keys are
   scProfile's api 1 (`scprofile/declare.py`), with the additions in point 2.
2. **Nothing the directory contract says is lost.**
   - Its kernel fields become optional keys, with PLUGIN_FORMAT.md's meanings: `profile`, `class`,
     `layer`, `reversible`, `rebuild_from`, `gates`, `measures_with`, `verdict`, `escape`,
     `invariant` (a function in the file) or `no_runtime_invariant`, and `sourceable`.
   - The directory's services list, which it calls `inject`, becomes `services`. In the UPF,
     `inject` keeps scProfile's meaning: capabilities.
   - Three keys that neither layout has are added: `assays` (rule 2), an exact `wraps.version`
     (A4.3) and `wraps.doi` (A4.3).

   All of these are optional today, and `sch catalogue` reads them from either layout. They become
   required only through the maker, in the maker's own waves (GAP-045's first move).
3. **Every layout has a name, in the catalogue's format column.**

   | name | meaning |
   |---|---|
   | `maker` | the UPF, complete |
   | `one-file` | the UPF's layout, not yet through the maker |
   | `directory` | legacy for the tool pool; still the kernel's mount contract (point 5) |
   | `kernel-yml` | legacy |
4. **`sch catalogue` is this mapping in executable form** (`sch/catalogue/row.py`). It reads
   every layout statically and lists each plugin as one row in the UPF's terms.
   - A field the layout cannot express reads `not declared`.
   - A fact nothing records reads `unknown`.
   - A file it cannot read is an error that names the file.
5. **Until the harness's kernel can mount a UPF plugin, a plugin the kernel itself must mount is
   still written as a `plugin.yml` directory.** That covers probes, gates and adapters such as
   `qc@scqc`. The catalogue reads such plugins through the mapping. The tool pool is UPF from now
   on: the published methods, PROF.3 and the A4.2 conversions.
6. **No code moves between repositories, and no plugin is edited.** Every migration is a later
   wave, through the maker.

## The mapping, field by field

"—" means the layout has no field for it. The maker's layout is the one-file layout, plus what
its column adds. The catalogue column names the field of a `sch catalogue --json` row. `details`
is the block that `sch catalogue show ID` adds.

**Identity and versions**

| concept | `plugin.yml` directory | one-file `PLUGIN` (api 1) | the maker's layout adds | UPF | catalogue |
|---|---|---|---|---|---|
| name | `name` | the file's stem | — | the stem | `id` (`<source>:<profile family>/<name>`, or `<source>:<stem>`), `name` |
| format version | `contract: "1.0"`, compared by major (X1) | `api: 1`; a higher api is refused by name | — | `api`. `contract` is kept as an optional key for plugins the kernel mounts | `details` |
| wrapper version | `version` | `version`, which is also the reuse key | the `freshness` stage: raised with every change | `version` | `version` |
| numbers version | `state_version` (D6) | `state_version` | — | `state_version` | `details` |
| vocabulary | `profile`, required | — (the host's own `CAPABILITIES`) | — | `profile`, optional; absent means the host's vocabulary | `details` |

**What it answers**

| concept | `plugin.yml` directory | one-file `PLUGIN` (api 1) | the maker's layout adds | UPF | catalogue |
|---|---|---|---|---|---|
| question | `summary`, `when_to_use` | the same | the `judgement` stage | the same | `question` |
| kind | `class`, default `method` | — (every one-file plugin is a method) | — | `class`, optional, default `method` | `details` |
| stack semantics | `layer`, `reversible`, `rebuild_from` (§3, §5) | — | — | optional, with §3 and §5's meanings; required before the kernel mounts the plugin | `details` |

**What it needs**

| concept | `plugin.yml` directory | one-file `PLUGIN` (api 1) | the maker's layout adds | UPF | catalogue |
|---|---|---|---|---|---|
| data | `needs` and `optional`, in the capability grammar (`matrix/{counts}`, `column/{label}`, `capability:x`) | `inject.required` and `inject.optional`: capability names, each resolved by `CAPABILITIES` as data, design or derived. Also `needs.{obs, obsm, layers, design}` | the `contract` stage | one-file's. A grammar entry becomes its key's capability name (`matrix/{counts}` → `counts`); a literal slot becomes `needs.<binding>` | `inputs.requires`, `inputs.optional` |
| layers | `needs` entries in a slot the profile binds to layers (`matrix/...`) | `needs.layers`, and `sees` entries of the form `layers[...]` | — | the same | `inputs.layers` |
| design | — (`sees: [design]` means *shown*, not *required*) | a capability that resolves to `design` (`design`, `contrast`); `design_aware` | the `design` stage (W013) | one-file's | `inputs.design` |
| another plugin's output | `checkpoint:<name>` | a capability that resolves to `derived` (`ordering`, `velocity`, ...) | — | one-file's | `inputs.from_plugins` |
| assay | — | — (the code reads `ctx.assay`; the host's `--assay` takes `cell` or `nucleus`) | — | **new**: `assays: [scrna, snrna]`, values of the profile's `assay` axis. Absent means `not declared`, never a default | `inputs.assays`, with `inputs.assay_read_at` as evidence |
| services | `inject`, the services on the Context | — (`inject` means capabilities here) | — | `services` | `inputs.services` |
| inputs fetched from outside | `sourceable` | `can_source_layers: true`: the layers in `needs.layers` may be fetched | — | `sourceable` | `inputs.sourceable` |
| what it was shown | `sees`: `labels`, `design`, `heldout` (§8) | `sees`: the object slots it reads (`obs[{label}]`, `layers[{counts}]`) | — | `sees` in slot form, with `design` and `heldout` as entries (`labels` → `obs[{label}]`) | `inputs.design.shown`, `details.sees` |
| per unit | — | `per_unit`, `also_cohort` | — | one-file's | `details` |

**What it produces**

| concept | `plugin.yml` directory | one-file `PLUGIN` (api 1) | the maker's layout adds | UPF | catalogue |
|---|---|---|---|---|---|
| outputs | `provides` (`mask/x`, `column/x`, `table/*`) | `produces` (`obs[x]`, `tables/x.csv`, with a trailing `?` when only some runs make it); `provides`, the capabilities offered to other plugins | the `declared` test stage reads a run back against `produces` | one-file's. A directory `provides` entry becomes a `produces` slot form; `capability:x` becomes `provides` | `outputs.provides`, `outputs.produces` |
| limits | `cannot_show`, required and non-empty | the same | the `judgement` stage | the same | `cannot_show` |

**Method provenance**

| concept | `plugin.yml` directory | one-file `PLUGIN` (api 1) | the maker's layout adds | UPF | catalogue |
|---|---|---|---|---|---|
| upstream | `wraps.tool` | `wraps.tool` | `wraps` is the conversion's input | the same | `provenance.upstream` |
| exact version | `wraps.version` (required, validate rule 8), and `lock.yml` with every line `==` | — in `wraps` (the template seeds none, `scprofile/onefile.py:33`). A pin, if any, sits in `requires` | as one-file (cellchat pins an R remote at a commit) | **`wraps.version`, exact** | `provenance.version`, with `version_from` and `version_declared_as` |
| DOI | — | — | — | **new**: `wraps.doi`, a string or a list | `provenance.doi` |
| citation, licence, homepage | `wraps.cite`, `wraps.license`, `wraps.homepage` | the same | — | the same | `provenance` |
| what was read upstream | — | `upstream.{docs, read, defaults_changed, not_used, gotchas}` | the `judgement` stage | one-file's | `details` |
| unreviewed plots | — | `wraps.plots_unreviewed`, an admission | absent: the `inventory` and `plan` stages are done | one-file's | `format`, `format_evidence` |

**Running it**

| concept | `plugin.yml` directory | one-file `PLUGIN` (api 1) | the maker's layout adds | UPF | catalogue |
|---|---|---|---|---|---|
| environment | `needs_env`; `lock.yml` (`==`); `selftest.py` or `.R` | `requires {python, packages, r, conda}`, as ranges; the host resolves one lock per environment group (W002). `def selftest()` | the `environment` stage: every package the code loads is declared | one-file's | — |
| entry point | `language`, `entry` (`run.py`, `run.R`, `run`) | the file itself. `run(ctx)` goes through the host's `_entry.py`; another language goes through a bridge inside the plugin (cellchat runs `Rscript`) | `<name>.draw.R`, generated | one-file's | `details` |
| second phase: compare | — | `def compare(ctx)`, optional. It runs after every unit's `run`, once per arm pair and once over all crossed arms when there are more than two, on the finished units' outputs, in the plugin's own environment (`_entry.py:432`, `report.py:853`) | cellchat implements it (`kernels/cellchat.py:5337`) | one-file's: a UPF host runs both phases | — |
| scheduling | `executor: {cost, gpu}`, advisory | `cost`, `cores`, `memory_gb_per_100k`, `memory_gb_base`, `gpus` | the `measure`, `cores` and `cost` test stages | one-file's | `details.executor` |
| parameters | — (`--param k=v`, checked by the plugin) | `config`: type, default, bounds, help | the `defaults` stage | one-file's | `details.parameters` |
| references | `references.yml`, with checksums | `references`, inside `PLUGIN` | the `references` stage | one-file's | `details.references` |

**Checks**

| concept | `plugin.yml` directory | one-file `PLUGIN` (api 1) | the maker's layout adds | UPF | catalogue |
|---|---|---|---|---|---|
| guard | `guard.py` | `def guard(g)` | — | one-file's | — |
| gates | `gates`; `class: gate` with `measures_with`, `verdict`, `escape` (§2b) | — | — | optional, with §2b's meanings | `details` |
| runtime companion | `invariant` or `no_runtime_invariant` (§16, ADR-0008) | — | — | optional: `invariant` names a function in the file, or `no_runtime_invariant` | `details` |
| report | — (the kernel's report service) | `report.{figures, reads_with, ...}` | the figure plan (ADR-0016): each entry carries `fn`, `axis`, `position`, `legend`, `drawn_by`, `at_most` | one-file's | `details.figures` |
| prose | `README.md` in four sections (§15); `CHANGELOG.md` | the module docstring | — | the docstring; §15 is not carried over (see *What is given up*) | — |

**Records**

| concept | `plugin.yml` directory | one-file `PLUGIN` (api 1) | the maker's layout adds | UPF | catalogue |
|---|---|---|---|---|---|
| finished by the maker | — (`sch dev check`'s ladder) | — | no `outstanding_if` field is set, and `<name>.signatures.json` is present | the same | `format`, `format_evidence`, `companions` |
| ran on a cohort | — | — (the tool's `DEVPOINTS.yaml` `rules.end_to_end` names the round's end-to-end plugin) | — | — (open: a run register) | `ran_on_cohort`: `recorded` or `unknown`, never `no` |

**Every other api-1 key carries over unchanged, with scProfile's meaning.** These are the keys the
shipped plugins declare, or that scProfile's api-1 validation (`scprofile/declare.py`) reads,
without a row above:
- `cache` (cellchat): the source span and the config keys of the saved object that a rerun may
  reuse (`declare.py:843`).
- `native_plots` (liana and velocity): the accounting of upstream plots written before the figure
  plan carried the call. `scprofile/native.py:109` still reads it as the fallback.
- `env`: the older, fully pinned environment shape (`declare.py:1044`).
- A nested `executor` mapping, the older spelling of the scheduling keys (`declare.py:796`).

**Read for the invariants.** The adopted layout keeps every ARCHITECTURE invariant in force.
- **L3.** A host reads the declaration as a literal and imports nothing. It runs `run(ctx)`, and
  `compare(ctx)` where the plugin defines it, as subprocesses.
- **C4.** The boundary is `in.json` and `out.json` (`scprofile/_entry.py`).
- **E1.** The declaration can be the disposer: `produces` names every output, a trailing `?`
  marks one that only some runs make, and the maker's `declared` stage reads a run back against
  it. Whether the kernel's undo works from it is the mount wave's test, not this record's claim.
- **D6.** `state_version` is a required key of the maker's kernel point (scProfile
  `DEVPOINTS.yaml:172`).

## The constraints the two formats forced, and what this record does with each

1. **The harness could list only `plugin.yml` directories** (`sch/kernel.py:97-128`), so nine
   methods were invisible to the agent surface.
   - Removed for listing, by `sch catalogue`.
   - Mounting a UPF plugin is a later wave.
2. **"One format" was read as "one codebase".** Phase 6 tied a single contract to dissolving
   scProfile, and so to giving up an independently installable tool.
   - Removed. The format is one, the tools stay separate (ADR-0004), and the harness reads the
     format statically.
3. **A method wrapper had to be a directory** of up to nine files: a manifest, an entry point, a
   lock, a selftest, a guard, a companion, references, a README and a CHANGELOG. scProfile had
   already found that shape to be an assembly kit (`scprofile/plugin.py`, "WHY THIS REPLACED SIX
   FILES").
   - No longer imposed on the pool.
   - Kept for kernel plugins until the kernel can mount the UPF.
4. **The two layouts disagreed on whether provenance is required.** The directory requires
   `wraps.version` (validate rule 8). The one-file template seeds neither a version nor a DOI
   (`scprofile/onefile.py:33`). As a result, 3 of 9 methods name an exact upstream version and
   none names a DOI.
   - Named, and moved into the UPF as an exact `wraps.version` and `wraps.doi`.
   - Making them required is the maker's change (GAP-045). scProfile is read-only in this wave.
5. **Two keys mean different things in the two layouts.**
   - `inject` means services in one layout and capabilities in the other.
   - `sees` means categories in one and object slots in the other.
   - Resolved in the UPF by point 2 of the decision and the table above.
6. **One axis has two spellings.** The program's assay vocabulary is `scrna`/`snrna` (rule 2; the
   profile's `assay` axis). scProfile's `--assay` takes `cell`/`nucleus`
   (`scprofile/cli.py:4330`).
   - The UPF's `assays` uses `scrna`/`snrna`.
   - Aligning scProfile's flag is queued for scProfile.
7. **scProfile's host reads an unreadable plugin as an empty one.** A syntax error, or a `PLUGIN`
   that is not a literal, gives `spec = {}` and the status `planned`
   (`scprofile/kernels.py:571-598`). This is the GAP-101 class: "could not read" reported as
   "nothing declared".
   - The catalogue refuses each such file by name.
   - The host's own fix is queued for scProfile.

## What is given up

1. **The directory as the unit of a pool plugin, and with it the language-neutral entry point.**
   A method written in R, or shipped as a binary, still has a Python file around it. cellchat
   shows the cost: two file round-trips, and `Rscript` on the PATH, inside the plugin.
2. **README §15 as a separate file, checked to have four sections** (validate rule 15). A UPF
   plugin carries its limits in `cannot_show`, which is required and non-empty, and in
   `upstream.gotchas`. For the pool, a separately written "Known limitations" section is given up,
   and so is the check that it is not empty.
3. **The per-plugin `lock.yml` as the unit of reproducibility** (§11, validate rule 7). The UPF
   declares requirements as ranges, and the host resolves one lock per environment group (W002).
   What stays with the plugin is the method's exact version (`wraps.version`), not the
   environment's.
4. **Phase 6's "one manifest, one merge path, one report engine".** Two hosts remain, sharing one
   declaration format: the harness's kernel for stack plugins, and scProfile's host for methods. A
   merge path that both share waits on the mount wave.
5. **For a plugin that migrates, the directory's meanings of `inject` and `sees`.** X2 ("fields
   are added; meanings never change") binds within a contract, and the directory contract is not
   changed: `plugin.yml` keeps every meaning it has. A migration translates a plugin into another
   format, following the table above. That is why no invariant is amended here.

## ADR-0004, amended

ADR-0004 stands. The four tools keep their repositories, locks, versions and users, and the
harness orchestrates them through thin adapters. It is amended in two respects.
- **The plugin format is one, and the harness reads it directly.** The format is this record's.
  The harness reads it statically from a tool's checkout (`sch catalogue`), as well as mounting
  the tool through an adapter. For scProfile, "the manifest contract it already has" is the UPF.
- **One more thing is given up.** The harness now depends on a tool's declarations staying
  literals. A computed `PLUGIN` is refused by name rather than read.

## ROADMAP Phase 6, amended

Phase 6 is no longer "Dissolve scProfile". It becomes "One plugin format, read and mounted by the
harness".
- **Claim.** Every plugin either is in the UPF or maps onto it, and the harness lists every plugin
  and mounts a UPF plugin with nothing lost.
- **Evaluation.** Three checks:
  - `sch catalogue` lists every plugin, with none unreadable. Built in W016.
  - A UPF plugin mounted through the harness gives byte-identical results to the same plugin under
    scProfile, from both of its phases: `run`, and `compare` where it defines one.
  - A cold agent picks a plugin and runs it through the agent surface (A4.4).
- **Falsifier.** If a UPF plugin cannot be mounted without loss, the kernel's contract is narrower
  than the format the pool uses. That is the finding the original phase named, and it is kept.
- **Dropped:** the old evaluation row "the roadmap survives" (`ROADMAP.md`'s tier-1 plugins remain
  buildable under the harness contract). The amended phase rebuilds no plugin under the directory
  contract, because the plugins stay in the UPF. The "one format" row replaces it.

ROADMAP.md is edited in this wave to say so.

## Consequences

**What becomes easier.**
- An agent can list every method the family has with one command, without any tool's environment.
  That is the first half of A4.4, and it closes GAP-005 for listing.
- A4.1 and A4.2 now have one target: the format the maker already emits.
- A4.3 now has a field to fill and a column that counts it. At `f5175ea` it counts 3 exact pins of
  9 and 0 DOIs.
- Self-assembly (GAP-049) and the co-scientist (GAP-012) now have a catalogue to choose from.

**What becomes harder.**
- Two hosts remain, and until the mount wave a kernel plugin is still written in the legacy
  layout.
- The catalogue reads scProfile's vocabulary from `scprofile/declare.py` and its maker markers
  from `DEVPOINTS.yaml`. When either cannot be read, the catalogue says so and falls back to
  `unknown`, never to a guess.

**The next waves this record creates.**
- **The mount.** The harness runs a UPF plugin, velocity or cellcycle first, through both
  phases: `run` per unit, and `compare` per arm pair where the plugin defines it, as cellchat does.
- **Required keys.** The maker makes `assays`, an exact `wraps.version` and `wraps.doi` required,
  so every plugin shows as owing (GAP-045).
- **No silent empty plugins.** scProfile refuses an unreadable plugin instead of listing it empty.
- **One assay spelling.** scProfile spells the assay `scrna`/`snrna`.
- **A run register** kept by each tool, so that the cohort-run column can read more than one rule.

**What property is given up** is stated item by item above. In one line: the directory as the
shape of a method plugin, and the plan to make the harness the only host.
