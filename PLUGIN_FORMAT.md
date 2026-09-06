# Plugin format

**Specification, v1.0-draft. Domain-free.** The contract every plugin conforms to, in any domain.
Normative words — MUST, SHOULD, MAY — carry their usual meaning.

Nothing here knows what a cell is. That is invariant **L2** of
[`ARCHITECTURE.md`](ARCHITECTURE.md): the core and the contract must be testable against a domain
they were not designed for. What an observation *is*, what slots exist and what may be measured are
defined by a **profile** (§14) — for this project,
[`docs/profiles/single-cell.md`](docs/profiles/single-cell.md).

A plugin is a **directory**. The kernel never imports it: it reads the manifest, resolves an
interpreter, runs an entry point as a subprocess, and merges what the plugin declares it produced.
That boundary is what lets a plugin pin numpy 1.26 while the host runs 2.4, and what lets one be
written in R.

**This follows [Cordis](https://github.com/cordiverse/cordis)**, the plugin kernel under DeepSeek
Harness, and uses its vocabulary wherever a concept already exists there:

| Cordis | here |
|---|---|
| a plugin is a function receiving a **Context** | `in.json` is that Context, serialised for a subprocess |
| **Service**, attached to the Context | `dataset`, `executor`, `storage`, `probe`, `provenance`, `report` |
| **`inject`** — demand-driven dependency declaration | `inject:` in the manifest |
| **effect / disposer** — registrations undone on unload | `provides:`, from which the kernel synthesises the undo (§5) |
| **fork / scope** — branched, isolated contexts | a stack fork: one plugin swapped, everything else identical |
| typed **event bus**, broadcast + waterfall | observers broadcast; gates short-circuit |
| **`cordis.yml`** plugin tree, overlay composition | `stack.yml`, layered site → project → run |

---

## 1. Layout

```
<name>/
  plugin.yml        manifest — REQUIRED, and the only file the kernel reads directly
  run.py|run.R|run  entry point — REQUIRED unless the plugin is provides-only
  lock.yml          environment specification — REQUIRED if needs_env
  selftest.py|.R    proves the environment works — REQUIRED if needs_env
  guard.py          refuse inputs where the output would mislead — OPTIONAL
  invariant.py      runtime checks on the relationship it owns — REQUIRED unless declared
                    absent in the manifest, §16
  references.yml    reference data with checksums — OPTIONAL
  README.md         REQUIRED — the four sections in §15
  CHANGELOG.md      REQUIRED once published
```

---

## 2. The manifest

```yaml
contract: "1.0"
profile: single-cell/1.0          # the vocabulary this plugin is written against
name: velocity
version: 0.1.0
summary: RNA velocity from spliced/unspliced counts — the direction of change
when_to_use: >
  your data carries spliced and unspliced layers and you want direction of
  change, not just position

class: method                     # method | probe | gate | executor | storage | report | publish
layer: stack                      # stack | checkpoint
reversible: true
state_version: 3                  # bumped when the NUMBERS change; see §3b

wraps:
  tool: scvelo
  version: "0.3.4"
  homepage: https://scvelo.readthedocs.io
  license: BSD-3-Clause
  cite: "Bergen et al., Nat Biotechnol 2020"

inject:  [dataset, probe/differential]     # SERVICES required from the Context
needs:   [matrix/spliced, matrix/unspliced, column/{label}]   # DATA capabilities
provides:
  - column/velocity_confidence
  - embedding/velocity_*
  - object/velocity
  - table/*
optional:   [embedding/{embedding}]
sourceable: [matrix/spliced, matrix/unspliced]

sees: []                          # what it was shown; see §8

language: python
entry: run.py
needs_env: true
executor: {cost: high, gpu: optional}
gates: {differential_check: required}
invariant: invariant.py           # or: no_runtime_invariant: <reason>. §16

cannot_show:
  - Velocity is a DIRECTION, not a rate. Arrow length is not speed, and two
    datasets' arrow lengths are not comparable.
```

| field | required | meaning |
|---|---|---|
| `contract` | ✅ | manifest format version. The kernel compares the MAJOR only |
| `profile` | ✅ | the domain vocabulary this plugin uses. A kernel without it refuses to mount |
| `name`, `version`, `summary`, `when_to_use` | ✅ | identity. `version` is the plugin's, never the wrapped tool's |
| `class` | | default `method`. §2b |
| `layer` | ✅ | `stack` or `checkpoint`. §3 |
| `state_version` | ✅ if it contributes | integer. What the plugin computes, versioned. §3b |
| `reversible` | ✅ | a claim the kernel tests. §5 |
| `wraps` | if wrapping | the upstream tool, pinned, with licence and citation. §9 |
| `inject` | | services required from the Context |
| `needs` | ✅ | data capabilities that MUST be present. Empty list is valid and explicit |
| `provides` | ✅ | what it contributes. Held to it. §6 |
| `optional` | | used if present, never a prerequisite |
| `sourceable` | | needs it MAY fetch from beside the data. §7 |
| `sees` | ✅ | information asymmetry. Empty list is a claim, not an omission. §8 |
| `language`, `entry`, `needs_env` | ✅ | how it runs |
| `executor` | | scheduling hints; advisory |
| `gates` | | gates it submits to beyond the defaults |
| `invariant` | ✅ one of the two | the companion, or `no_runtime_invariant:` with a reason. §16 |
| `cannot_show` | ✅ | non-empty. §10 |

### 2b. Plugin classes

**`class: probe`** — a read-only inspection answering one question and returning a bounded result.
MUST declare `reversible: true` and contribute nothing to the stack. Returns its answer in
`out.json` under `answer`, and MAY return `figures` — a probe that draws is how an agent looks at
data it cannot hold.

**`class: gate`** — refuses an operation. MUST name the probe it measures with:

```yaml
class: gate
measures_with: probe/differential
verdict: [PASS, REVIEW, REFUSE]
escape: --allow                   # logged as a pair; never absent
```

A gate whose measurement the refused party cannot independently run is a black box that gets routed
around. One instrument, two consumers.

**A gate is monotonic (G4).** It may REFUSE, or abstain; it may not approve. `PASS` is the
abstention — *this gate has nothing to refuse on*, never *this is fine, disregard the others* — and
`REVIEW` is an abstention carrying a note that travels to the report. The verdict of a set of gates
is the strongest refusal any of them returns, so **order does not change the outcome** and no
plugin may turn another's refusal into a pass.

The only thing that lifts a refusal is `escape`, and an escape is a **recorded pair**: the ask —
what was refused, by which gate, with the probe's number — and the decision — who, when, why. An
escape with no pair in the stream is not an escape, and the mount fails. A refusal is a **result**,
appended to the stream with the number that caused it, never an exception that unwinds and leaves
nothing to audit.

**`class: executor`** — decides where work physically runs. Its teardown MUST reach quiescence
(**E5**): closing the plugin's output registration before signalling, awaiting termination, and
reporting requested / stopped / timed-out / exit status as **independent facts** — a job can time
out *and* exit 0 because it trapped the signal, and a flag nested inside another's branch reads a
cut-short run as a clean one. An executor that cannot confirm termination fails the unmount.

---

## 3. Layer: stack or checkpoint

**`layer: stack`** — the effect is a view over data that already exists. It can be unmounted, and
invalidation propagates through it.

**`layer: checkpoint`** — the plugin produces genuinely new numbers that are not a function of what
is already present. It CANNOT be unmounted; invalidation propagates down to it and stops. It MUST
declare:

```yaml
layer: checkpoint
rebuild_from:
  inputs: [observations/raw]
  params: [fpr, learning_rate]
```

Declaring `stack` for something that is really a checkpoint is the most damaging error in this
format: the kernel will offer an unmount that silently produces different data. **When in doubt,
declare `checkpoint`** — that error costs a rebuild; the other costs a wrong answer nobody can see.

### 3b. `state_version`: what the plugin computes, versioned

`version` tracks the wrapper. **`state_version` tracks the numbers.** It is an integer, bumped
whenever what the plugin computes changes for the same inputs and the same parameters — a new
upstream version, a corrected formula, a changed default, a different random draw.

The kernel keys every cached materialisation on the exact tuple — observations digest, the ordered
stack of `(plugin, version, state_version, params)`, profile version — and a tuple that does not
match is a **miss, never a partial hit** (**D6**). A plugin that changes what it computes without
bumping `state_version` serves stale numbers that look correct and match their own provenance;
there is no cheaper place to catch that than here, and the kernel's companion (§16) catches the
rest by raising when a re-run differs under an unchanged tuple.

Contribute a **whole value, never a delta** — the full mask, the full column. A delta cannot be
removed from the middle of a stack, which is the operation the entire design is for.

---

## 4. Capability grammar

`needs` and `provides` name **capabilities**, not implementations. The grammar is fixed here; the
**vocabulary of slots is defined by the profile.**

| form | means |
|---|---|
| `<slot>/<name>` | a named thing in a slot the profile defines |
| `<slot>/*` | glob, for names decided at runtime |
| `{key}` | resolved through the profile's key map at mount |
| `capability:<name>` | an abstract capability any implementation may satisfy |
| `checkpoint:<name>` | the output of a checkpoint plugin |
| `service/<name>` | a service on the Context (`inject` only) |

**Prefer the abstract form.** `capability:embedding` lets any implementation satisfy the need;
naming one couples two plugins silently.

**A plugin MUST NOT hard-code a domain identifier** — a column name, a field name, a species. The
key map resolves `{label}`, `{sample}` and the rest per dataset. A plugin naming a real column has
bound itself to one project.

---

## 5. Effects and disposers, across a process boundary

In Cordis every registration is an **effect**, undone automatically when the plugin unloads:
`register()` returns a **disposer**, a closure reversing exactly that contribution. A plugin
running as a subprocess cannot return a closure.

**So the declaration IS the disposer.** A plugin states precisely what it contributed; the kernel
synthesises the undo by removing exactly those contributions, in reverse mount order. The
substitution only works if the declaration is exact, which is why `provides` is enforced rather
than documented:

- output not covered by `provides` is reported at every level and recorded in the provenance;
- a plugin writing outside its declaration has made a change the kernel cannot reverse;
- `reversible: true` is **tested at mount** — mount, snapshot, unmount, compare. A false claim is
  caught when nothing depends on the plugin, not when everything does.

A plugin MAY declare `reversible: false` on the stack layer. It is then mountable, but unmounting
requires rebuilding everything above it, and the kernel says so first.

A plugin that starts work outliving its own process — a scheduler job, a server, a temporary mount
— is undone only when that work has **stopped**, not when its stop was requested (**E5**, §2b).

---

## 6. The runtime protocol

The kernel writes `in.json`, runs the entry point, reads `out.json`. Both are plain JSON — they
cross every version boundary the data itself cannot.

**`in.json`**

```json
{
  "contract": "1.0",
  "profile": "single-cell/1.0",
  "data": "/abs/path/to/input",
  "out_dir": "/abs/path/to/output",
  "keys": {"label": "cell_type", "sample": "sample"},
  "design": "/abs/path/design.csv",
  "references": {"cistarget": "/abs/path/..."},
  "params": {"mode": "stochastic"},
  "upstream": {"cellcycle": "/abs/path/to/its/out_dir"},
  "provenance": {"tools": [], "search_paths": []},
  "profile_context": {}
}
```

Every path absolute. `profile_context` carries whatever the profile defines and the generic
contract does not know about.

**`out.json`**

```json
{
  "contract": "1.0", "plugin": "velocity", "version": "0.1.0", "state_version": 3,
  "status": "ok",
  "headline": "fitted on 2,000 features; median confidence 0.84",
  "wrapped_versions": {"scvelo": "0.3.4"},
  "columns":   {"velocity_confidence": "columns/velocity_confidence.csv"},
  "embeddings":{"velocity_umap": "embeddings/velocity_umap.npy"},
  "matrices":  {},
  "masks":     {},
  "objects":   {"velocity": "objects/velocity.h5ad"},
  "tables":    ["tables/by_label.csv"],
  "figures":   [{"path": "figures/F1.png", "vector": "figures/F1.pdf",
                 "source": "figures/source_data/F1.csv", "caption": "..."}],
  "answer":    {},
  "absent":    [{"what": "latent_time", "why": "only the dynamical mode fits it"}],
  "caveats":   ["..."]
}
```

**Abstract slots.** `columns`, `embeddings`, `matrices`, `masks`, `graphs`, `objects`, `tables`,
`figures`, `answer`. A profile binds each to a concrete representation.

`status` is `ok`, `partial` or `refused`. Three states are deliberately distinguishable:

| | means |
|---|---|
| no `out.json` | the plugin **died**. The kernel keeps stderr and says so |
| `out.json`, nothing in it | it ran and found nothing. **That is a result** |
| `out.json` with entries | it produced these, and only these are merged |

A host that globbed the output directory would collapse the first two, and those are opposite
facts.

**Merging.** Observation-level results merge **by identity, never by position**. A plugin returning
a different order merges correctly or is refused with the counts. Positional arrays MUST ship the
identity list beside them.

**Paths are relative to `out_dir`**, so a run directory can be moved or hardlinked without every
manifest in it becoming a lie.

---

## 7. Sourceable inputs

Some inputs cannot be derived from the data at hand and are not in it. A need listed under
`sourceable` is not blocked by the prerequisite check; the plugin receives
`provenance.search_paths` and searches them itself.

A sourcing plugin MUST:

- recognise sources by **content**, not filename convention;
- match by **identity**, and print the match rate for every source tried, including those that
  matched nothing;
- **refuse a source below a declared threshold** rather than applying it partially — a partial
  match fills some observations and leaves the rest at zero, which fits perfectly well and means
  nothing;
- respect the profile's grouping rule where identity is only unique within a group;
- refuse with the list of every directory searched.

---

## 8. `sees`

```yaml
sees: [labels]
```

Declares what the plugin was **shown** that others were not: `labels`, `design`, `heldout`, or any
value the profile adds. Any plugin that will be **compared against others** MUST declare it, and an
empty list is a positive claim rather than an omission.

A method trained on the thing it is later scored against will beat methods that were not, partly
for having been told the answer. The code is correct, the metric is correct, and the ranking is not
like-for-like. The kernel prints the declaration wherever a ranking appears.

---

## 9. Wrapping a public tool

A wrapping plugin MUST record it under `wraps` with a **pinned** version, licence and citation;
**pin that version in `lock.yml`** — an upstream lower bound is not an upper bound; **record the
version again at runtime**, read from the tool, in `wrapped_versions`; reproduce the tool's
recommended settings by default and mark every deviation; and never silently repair its output.

The plugin's `version` tracks the wrapper. The tool's version lives in `wraps`.

---

## 10. `cannot_show`

Required, non-empty, printed beside the plugin's results.

A result whose limits were never written down reads exactly as authoritative as one whose limits
were thought about. If the list is short, the plugin has not been thought about.

---

## 11. Environment

```yaml
name: harness-velocity
channels: [conda-forge]
dependencies:
  - python=3.11
  - pip
  - pip: [numpy==1.26.4, scvelo==0.3.4]
```

Every dependency pinned with `==`. A lock with ranges is not a lock.

`selftest` MUST exercise the real computation on synthetic input, not merely import the package —
the failures worth catching all import cleanly and die inside the first real call. It MUST assert
shapes and finiteness, never a domain answer: the fixture is synthetic, and a selftest asserting a
result is testing the fixture.

---

## 12. Validation

`sch plugin validate <dir>` checks, without running anything:

1. `plugin.yml` parses; `contract` major supported; `profile` known
2. every required field present; `cannot_show` non-empty; `sees` present
3. `layer` valid; a checkpoint declares `rebuild_from`
4. `needs`/`provides` are well-formed under the grammar **and** the declared profile's vocabulary
5. entry point exists and is executable
6. `needs_env` implies `lock.yml` and a selftest
7. every lock dependency pinned with `==`
8. `wraps` carries version, licence, citation
9. `references.yml` entries carry checksums
10. the reversibility claim is consistent with the layer
11. no hard-coded domain identifier where the profile defines a key
12. a contributing plugin declares an integer `state_version` (§3b)
13. a gate declares an `escape`, and no verdict outside `PASS` `REVIEW` `REFUSE` — there is
    no approving verdict to declare (**G4**)
14. `invariant:` names a file that exists, or `no_runtime_invariant:` gives a reason naming a
    relationship — an empty companion and an unexplained absence are both rejected (§16)
15. `README.md` carries all four required sections, none of them empty (§15)

`sch plugin test <dir>` additionally builds the environment, runs the selftest, runs the plugin on
a synthetic fixture, mounts its companion (§16) against that run, and — for `reversible: true` —
mounts, snapshots, unmounts and compares.

---

## 13. Compatibility

The kernel compares the **major** of `contract`. Fields are added; meanings do not change. A field
whose meaning must change gets a new name and the old one is deprecated with notice
(**X2**).

A **profile** carries its own version. A plugin declares which it was written against, and a kernel
asked to mount a plugin under an unknown profile refuses rather than guessing at the vocabulary.

Whether those promises should bind *before* an adapter has ever been written against this contract
is open: [ADR-0012](docs/adr/0012-pre-release-stance-for-the-contract.md) proposes deferring them
until Phase 5 closes. It is **proposed, not accepted** — until it is, everything above holds as
written.

---

## 14. Profiles

A profile binds this contract to a domain. It defines, and nothing else may:

| the profile defines | example |
|---|---|
| what an **observation** is | a cell barcode |
| the **slot vocabulary** — how abstract slots map to concrete storage | `columns` → `obs`, `embeddings` → `obsm` |
| the **key map** | `{label}`, `{sample}`, `{batch}`, `{counts}` |
| the **identity rule** for merging, and any grouping it needs | barcode, unique within a sample |
| the **checkpoint kinds** | alignment, ambient correction |
| **sentinel** semantics | values meaning *not a call*, never dropped |
| the **probe library** | the questions askable without writing code |
| additional **required declarations** | a differential-effect check on removals |
| the **on-disk layout** of a stack and its materialisations | |

The generic contract does not know any of it. That separation is what lets one kernel host a
different domain without touching the core — and it is the reason a plugin declares `profile:` in
its first three lines.

**This project's profile:** [`docs/profiles/single-cell.md`](docs/profiles/single-cell.md).

---

## 15. The README

Required, four sections, none of them empty. `when_to_use` and `cannot_show` are for the kernel and
the report; this is for the person deciding whether to mount the thing.

| section | what goes in it |
|---|---|
| **What it does** | the operation, in the terms a user of the wrapped tool would recognise |
| **Report surface** | what this plugin makes report-visible — every number, table and figure a reader could end up quoting, and the `cannot_show` line each one travels with |
| **Cost** | what it costs to run and what it costs to *unmount*: the declared `executor` cost, and what invalidates when it is removed |
| **Known limitations** | what it does badly, what it does not do yet, and the case where its answer should be distrusted |

**Known limitations is the load-bearing one.** A section that is empty, or that reads as marketing,
is the plugin telling you it has not been used in anger. The convention is borrowed from DeepSeek
Harness, where every package README carries *Model Experience* — what the model sees, verbatim —
and *Known Limitations and Deferred Work*, and both are filled in with real admissions. The
equivalent here is what a *reader of the report* sees, because that is our model: the report is the
surface where an unstated limit becomes a claim nobody made on purpose.

---

## 16. The invariant companion

A relationship the plugin owns, asserted while it runs — not on a fixture, not in CI, but on the run
whose results someone will publish
([ADR-0008](docs/adr/0008-runtime-conformance-companions.md)).

```python
# invariant.py
def register(inv):
    @inv.check("every masked observation is named in the removal record")
    def _(run):
        masked   = run.masked_observations()
        recorded = {row["observation"] for row in run.table("removal_record")}
        if masked - recorded:
            inv.fail(f"{len(masked - recorded)} observations masked without a record")
```

- The kernel provides `service/invariant`. A check that fails raises, naming **this** plugin and
  the fact that failed. It does not silently degrade.
- A companion asserts something **observable at runtime** that this plugin **owns**: a conservation
  law, an ordering, a relationship between what it declared and what it wrote. That a field is
  present, that an entry point is executable, that a pure function returns a fixed value — those
  are §12 and selftest concerns, and a companion that checks them is theatre.
- **Every plugin declares one or the other.** A plugin with no runtime relationship writes
  `no_runtime_invariant:` with the reason — *pure transformation of a declared input, nothing
  observable between calls* — and the validator rejects a reason that names no relationship. The
  point of the exhaustive form is that "we didn't think about it" and "there is nothing to check"
  stop being indistinguishable.
- A companion is a plugin like any other: it contributes nothing to the stack, nothing it computes
  is quotable (**A2**), and it declares its cost.
- A check only checks if the regression actually fails it. Introduce the regression, watch it fail,
  revert — and if it cannot be made to fail, the check is decoration.
