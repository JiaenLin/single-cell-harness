# Plugin format

**Specification, v1.0-draft.** The contract every plugin conforms to, and the reason for each
field. Normative words — MUST, SHOULD, MAY — carry their usual meaning.

A plugin is a **directory**. The kernel never imports it: it reads the manifest, resolves an
interpreter, runs an entry point as a subprocess, and merges what the plugin declares it produced.
That boundary is what lets a plugin pin numpy 1.26 while the host runs 2.4, and what lets one be
written in R.

> **Vocabulary.** *Kernel* means the runtime core — the one thing that mounts, unmounts and
> resolves. Everything mounted on it is a **plugin**. scProfile currently calls its units
> "kernels"; those are plugins in this vocabulary and will be renamed when it is adapted.

---

## 1. Layout

```
<name>/
  plugin.yml        manifest — REQUIRED, and the only file the kernel reads directly
  run.py|run.R|run  entry point — REQUIRED unless the plugin is `provides`-only
  lock.yml          environment specification — REQUIRED if needs_env
  selftest.py|.R    proves the environment works — REQUIRED if needs_env
  guard.py          refuse datasets where the output would mislead — OPTIONAL
  references.yml    reference data with checksums — OPTIONAL
  CHANGELOG.md      REQUIRED once published
```

Nothing else is read. A plugin MAY contain any other files.

---

## 2. The manifest

```yaml
# ─── identity ────────────────────────────────────────────────────────────────
contract: "1.0"                  # the format this manifest is written against
name: velocity                   # unique within its namespace; [a-z][a-z0-9_-]*
version: 0.1.0                   # semver; the PLUGIN's version, not the tool's
summary: RNA velocity from spliced/unspliced counts — the direction of change
when_to_use: >
  your object carries spliced and unspliced layers and you want direction of
  change, not just position

# ─── what it wraps, if anything ──────────────────────────────────────────────
wraps:
  tool: scvelo
  version: "0.3.4"               # pinned; recorded again at runtime, from the tool
  homepage: https://scvelo.readthedocs.io
  license: BSD-3-Clause
  cite: "Bergen et al., Nat Biotechnol 2020"

# ─── where it sits in the three layers ───────────────────────────────────────
layer: stack                     # stack | checkpoint
reversible: true                 # tested at mount; see §5

# ─── the dependency graph ────────────────────────────────────────────────────
needs:
  - layers/spliced
  - layers/unspliced
  - obs/{label}                  # {label} resolves through the key map, §4
provides:
  - obs/velocity_confidence
  - obs/velocity_pseudotime
  - obsm/velocity_*              # glob: the basis is a runtime choice
  - objects/velocity_h5ad
  - tables/*
optional:
  - obsm/{embedding}             # used if present, not a prerequisite
sourceable:                      # needs it MAY fetch from beside the object, §7
  - layers/spliced
  - layers/unspliced

# ─── what it is allowed to see ───────────────────────────────────────────────
sees: []                         # labels | design | heldout — see §8

# ─── execution ───────────────────────────────────────────────────────────────
language: python
entry: run.py
needs_env: true
executor:
  cost: high                     # trivial | low | medium | high
  gpu: optional                  # never | optional | required
  memory_hint_gb_per_100k_cells: 12

# ─── gates this plugin submits to ────────────────────────────────────────────
gates:
  differential_check: required   # removal rate measured per design arm

# ─── what its output does NOT establish ──────────────────────────────────────
cannot_show:
  - Velocity is a DIRECTION, not a rate. Arrow length is not speed, and two
    datasets' arrow lengths are not comparable.
  - These counts are not ambient-corrected; correction applies to totals and
    cannot be decomposed into spliced and unspliced parts.
```

### Field reference

| field | required | meaning |
|---|---|---|
| `contract` | ✅ | manifest format version. The kernel compares the MAJOR only |
| `name`, `version`, `summary` | ✅ | identity. `version` is the plugin's, never the wrapped tool's |
| `when_to_use` | ✅ | one line letting a user or an agent judge relevance without reading further |
| `wraps` | if wrapping | the upstream tool, pinned, with licence and citation. §9 |
| `layer` | ✅ | `stack` (mountable, reversible) or `checkpoint` (rebuild-only). §3 |
| `reversible` | ✅ | a claim the kernel tests. §5 |
| `needs` | ✅ | capabilities that MUST be present. Empty list is valid and explicit |
| `provides` | ✅ | what it contributes. Held to it. §6 |
| `optional` | | used if present, never a prerequisite |
| `sourceable` | | needs it may fetch from beside the object rather than refuse. §7 |
| `sees` | ✅ | information asymmetry declaration. Empty list is a claim, not an omission. §8 |
| `language`, `entry` | ✅ | `python` \| `r` \| `shell`; the executable |
| `needs_env` | ✅ | `false` runs in the host interpreter — only for plugins with no dependency the host lacks |
| `executor` | | scheduling hints. Advisory; the executor plugin decides |
| `gates` | | gates this plugin submits to beyond the defaults |
| `cannot_show` | ✅ | non-empty. §10 |

---

## 3. Layer: stack or checkpoint

Every plugin declares which layer it operates on, and the kernel treats the two differently.

**`layer: stack`** — the plugin's effect is a view over data that already exists: a mask, a derived
column, a derived matrix, a graph. It can be unmounted. Invalidation propagates through it.

**`layer: checkpoint`** — the plugin produces genuinely new numbers that are not a function of what
is already in the object: alignment from reads, ambient correction, any model whose output replaces
counts. It CANNOT be unmounted. Invalidation propagates down to it and stops.

A checkpoint plugin MUST declare `rebuild_from`:

```yaml
layer: checkpoint
rebuild_from:
  inputs: [observations/fastq]
  params: [fpr, learning_rate]   # the parameters that change the output
```

Declaring `layer: stack` for something that is really a checkpoint is the most damaging error in
this format: the kernel will offer an unmount that silently produces a different dataset. When in
doubt, declare `checkpoint` — the cost is a rebuild, and the cost of the other mistake is a wrong
answer nobody can see.

---

## 4. Capabilities

`needs` and `provides` name **capabilities**, not implementations.

| form | means |
|---|---|
| `obs/<name>` | a cell-level column |
| `var/<name>` | a gene-level column |
| `obsm/<name>` | a cell × k matrix |
| `layers/<name>` | a cell × gene matrix on the object's own var set |
| `graph/<name>` | a neighbour graph |
| `mask` | an observation mask |
| `objects/<name>` | a side-car file |
| `tables/<name>`, `figures/<name>` | files beside the object |
| `checkpoint:<name>` | the output of a checkpoint plugin |
| `capability:<name>` | an abstract capability — `capability:embedding`, `capability:design` |
| `{key}` | resolved through the key map: `{label}`, `{sample}`, `{batch}`, `{counts}`, `{embedding}` |
| `*` | glob, for names decided at runtime |

**Prefer the abstract form.** `capability:embedding` lets any integration plugin satisfy the need;
`obsm/X_scanvi` names one implementation and silently couples two plugins.

**The key map exists because column names are not portable.** A plugin MUST NOT hard-code
`cell_type`. The kernel resolves `{label}` per dataset and passes the resolution in; a plugin
naming a real column has bound itself to one project.

---

## 5. Reversibility, across a process boundary

Cordis makes reversibility structural by having `register()` return a **disposer** — a closure that
undoes exactly that contribution. A plugin running as a subprocess cannot return a closure.

**So the declaration IS the disposer.** A plugin states precisely what it contributed; the kernel
synthesises the undo by removing exactly those contributions, in reverse mount order. This is the
one place the format departs from its inspiration, and the substitution only works if the
declaration is exact — which is why `provides` is enforced rather than documented:

- output not covered by `provides` is reported at every level and recorded in the provenance;
- a plugin that writes outside its declaration has, by definition, made a change the kernel cannot
  reverse, so an unmount would leave the dataset altered;
- `reversible: true` is **tested at mount**, not trusted at unmount. The kernel mounts, snapshots
  the declared slots, unmounts, and compares. A plugin failing that check is rejected at mount —
  when nothing depends on it — rather than at unmount, when everything does.

A plugin MAY declare `reversible: false` on the stack layer. It is then mountable but its unmount
requires rebuilding everything above it, and the kernel says so before doing it.

---

## 6. The runtime protocol

The kernel writes `in.json`, runs the entry point, and reads `out.json`. Both are plain JSON: they
cross every version boundary the object itself cannot.

**`in.json` — kernel → plugin**

```json
{
  "contract": "1.0",
  "h5ad": "/abs/path/to/input.h5ad",
  "out_dir": "/abs/path/to/this/plugin/output",
  "keys": {"label": "cell_type", "sample": "sample", "counts": "counts"},
  "organism": "mouse",
  "assay": "nucleus",
  "design": "/abs/path/design.csv",
  "sentinels": ["EXCLUDED", "UNRESOLVED"],
  "references": {"cistarget": "/abs/path/..."},
  "params": {"mode": "stochastic"},
  "upstream": {"cellcycle": "/abs/path/to/its/out_dir"},
  "provenance": {"tools": [...], "search_paths": [...], "sample_hints": [...]}
}
```

Every path is absolute — a plugin runs with its own working directory.

**`out.json` — plugin → kernel**

```json
{
  "contract": "1.0",
  "plugin": "velocity",
  "version": "0.1.0",
  "status": "ok",
  "headline": "fitted on 2,000 genes; median confidence 0.84",
  "wrapped_versions": {"scvelo": "0.3.4", "numpy": "1.26.4"},
  "obs":     {"velocity_confidence": "obs/velocity_confidence.csv"},
  "obsm":    {"velocity_umap": "obsm/velocity_umap.npy"},
  "objects": {"velocity_h5ad": "objects/velocity.h5ad"},
  "tables":  ["tables/velocity_by_label.csv"],
  "figures": [{"path": "figures/F1.png", "vector": "figures/F1.pdf",
               "source": "figures/source_data/F1.csv", "caption": "..."}],
  "absent":  [{"what": "latent_time", "why": "only the dynamical mode fits it"}],
  "caveats": ["..."]
}
```

`status` is `ok`, `partial` or `refused`. The three states a plugin can leave behind are
deliberately distinguishable:

| | means |
|---|---|
| no `out.json` | the plugin **died**. The kernel keeps stderr and says so |
| `out.json`, nothing in it | it ran and found nothing. **That is a result** |
| `out.json` with entries | it produced these, and only these are merged |

A convention-based host that globbed the output directory would collapse the first two, and those
are opposite facts.

**Merging.** Cell-level results merge **by barcode**, never by position. A plugin returning a
different cell order merges correctly or is refused with the counts. `obsm` arrays merge by
position and MUST be accompanied by `obsm/barcodes.txt` unless the plugin asserts the order is
unchanged.

**Paths in `out.json` are relative to `out_dir`**, so a run directory can be moved or promoted by
hardlink without every manifest in it becoming a lie.

---

## 7. Inputs that are not in the object

Some inputs cannot be derived from a counts matrix — spliced/unspliced counts come from the
aligner, and an object that has been through QC and annotation has lost them, while the aligner
output is usually still on disk.

A plugin listing a need under `sourceable` is not blocked by the kernel's prerequisite check.
Instead it receives `provenance.search_paths` — directories harvested from what the upstream tools
recorded — and searches them itself.

A sourcing plugin MUST:

- recognise sources by **content**, not filename convention;
- match by identity, not position, and **print the match rate for every source tried**, including
  those that matched nothing;
- **refuse a source below a declared threshold** rather than applying it partially. A partial match
  fills some cells and leaves the rest at zero, which fits perfectly well and means nothing;
- match **within sample** where the object is a cohort — the same barcode legitimately recurs
  across samples;
- refuse with the list of every directory it searched.

---

## 8. `sees` — the information asymmetry declaration

```yaml
sees: [labels]          # this plugin is TRAINED on the label column
```

| value | means |
|---|---|
| `labels` | the plugin is given the label column |
| `design` | it is given the design table |
| `heldout` | it is given data withheld from other plugins |

Any plugin that will be **compared against others** MUST declare this, and an empty list is a
positive claim rather than an omission.

The reason is specific. A semi-supervised integration method trained on the label column will be
scored on metrics computed against that same column, and will beat unsupervised methods partly
because it was told the answer. The code is correct, the metrics are correct, and the ranking is
not like-for-like. The kernel prints the declaration wherever a ranking appears — not in a methods
appendix.

---

## 9. Wrapping a public tool

A plugin that wraps someone else's tool MUST:

- record it under `wraps`, with a **pinned** version, its licence and its citation;
- **pin that version in `lock.yml`** — an upstream lower bound is not an upper bound. A tool
  declaring `pandas>=1.1.1` resolves today to pandas 3 and may call something removed two majors
  ago, failing in a way that returns a plausible number instead of an error;
- **record the version again at runtime**, read from the tool rather than from the lock, in
  `wrapped_versions`;
- reproduce the tool's **recommended settings** by default, and mark every deviation in the
  manifest and the report;
- never silently repair the tool's output.

The plugin's `version` tracks the wrapper. The tool's version lives in `wraps` and
`wrapped_versions`.

---

## 10. `cannot_show`

Required, non-empty, and printed beside the plugin's results.

A result whose limits were never written down reads exactly as authoritative as one whose limits
were thought about. This field is the difference, and it is the field most worth spending time on:
if the list is short, the plugin has not been thought about.

Write what the output does **not** establish, in the terms a reader will use — not the method's
assumptions in the method's vocabulary.

---

## 11. Environment

```yaml
# lock.yml
name: harness-velocity
channels: [conda-forge]
dependencies:
  - python=3.11
  - pip
  - pip:
      - numpy==1.26.4
      - scvelo==0.3.4
```

Every dependency pinned with `==`. A lock with ranges is not a lock.

`selftest` MUST exercise the real computation on synthetic data, not merely import the package. The
failures worth catching — a numpy that removed an alias, a pandas that dropped a method, a numba
that will not compile — all import cleanly and die inside the first real call. It MUST assert
shapes and finiteness, never a biological answer: the fixture is synthetic and a selftest asserting
a result is testing the fixture.

Installation runs the selftest. An environment that fails it is not usable and the kernel says so
before a run is spent on it.

---

## 12. Validation

`sch plugin validate <dir>` checks, without running anything:

1. `plugin.yml` parses and declares a supported `contract` major
2. every required field present; `cannot_show` non-empty; `sees` present
3. `layer` is `stack` or `checkpoint`; a checkpoint declares `rebuild_from`
4. `needs` / `provides` are well-formed capabilities
5. entry point exists and is executable
6. `needs_env` implies `lock.yml` and a selftest
7. every `lock.yml` dependency is pinned with `==`
8. `wraps` carries version, licence and citation where present
9. `references.yml` entries carry a checksum
10. the reversibility claim is consistent with the layer

`sch plugin test <dir>` additionally builds the environment, runs the selftest, runs the plugin on
a synthetic fixture, and — for `reversible: true` — mounts, snapshots, unmounts and compares.

---

## 13. Compatibility

The kernel compares the **major** of `contract`. A plugin written against 1.0 runs on a 1.x kernel
and simply does not read fields added later. Fields are added; meanings do not change. A field
whose meaning must change gets a new name and the old one is deprecated with notice.

---

## Appendix: a minimal plugin

```yaml
# plugin.yml
contract: "1.0"
name: cellcycle
version: 0.1.0
summary: cell-cycle phase per cell
when_to_use: any dataset, and before any trajectory claim
layer: stack
reversible: true
needs: []
provides: [obs/phase, obs/S_score, obs/G2M_score]
sees: []
language: python
entry: run.py
needs_env: false
executor: {cost: trivial}
cannot_show:
  - Phase is SCORED from a gene set, not measured. A cell called G2M is one whose
    G2M genes are relatively high, which is not the same as a cell in G2M.
  - On single nuclei the signal is weaker, so a low score is as consistent with the
    assay as with a resting population.
```

```python
# run.py
import json, sys
from pathlib import Path

inp = json.loads(Path(sys.argv[1]).read_text())
out = Path(inp["out_dir"]); (out / "obs").mkdir(parents=True, exist_ok=True)

# ... compute, write out/obs/phase.csv as barcode,value ...

(out / "out.json").write_text(json.dumps({
    "contract": "1.0", "plugin": "cellcycle", "version": "0.1.0", "status": "ok",
    "headline": "12.4% of cells score S or G2M",
    "obs": {"phase": "obs/phase.csv"},
    "caveats": ["Scored from 41 S and 52 G2M panel genes present in this object."],
}))
```
