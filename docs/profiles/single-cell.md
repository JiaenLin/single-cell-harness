# Profile: single-cell — v1.0-draft

Binds [`PLUGIN_FORMAT.md`](../../PLUGIN_FORMAT.md) to single-cell and single-nucleus data. The
generic contract knows nothing of what follows; everything domain-specific lives here, which is
invariant **L2**.

A plugin declares `profile: single-cell/1.0`. A kernel asked to mount a plugin under an unknown
profile refuses rather than guessing at its vocabulary.

---

## 1. The observation

**An observation is one barcode: one cell or one nucleus.**

Its identity is the barcode string. Barcodes are **unique only within a sample** — the same 10x
barcode legitimately recurs across libraries of one experiment — so every merge, every join and
every external source match is scoped by `{sample}` where one exists.

An observation is never deleted. A removal is a **mask** (**D4**), and the masked observation keeps
its identity, its metadata and its position in the object.

### Observations that arrive as libraries

A cohort is never one file. It is N libraries, each with its own barcodes. A stack may therefore
declare its observations as a **parts manifest** (W010):

```console
$ sch init stack --profile single-cell/1.0 --observations samplesheet.tsv \
      --parts <column naming each library's object> --key sample=<column naming the library>
```

The manifest is a table with one row per part, separated by tabs or by commas; `#` lines are
skipped. For a QC stage it is the QC tool's own samplesheet, as delivered. Each part is the
library's object at the stack's floor: the denoised object an ambient checkpoint delivered, or the
aligner's call.

- **Identity.** An observation is `<sample>|<barcode>`: the barcode within its `{sample}`, joined by
  the profile's `identity.joiner`. A sample name containing the joiner is refused.
- **Reading.** Identities are read from each part (`.h5ad`, through h5py; no matrix is loaded).
- **Digest.** It covers the manifest and every part, so a write to any library is a write the A1
  companion sees.
- **The view.** It is identity-level: `view.csv`, holding the identity, `{sample}`, the contributed
  columns, `keep` and every mask. Matrices stay in their parts and are read in place, and a
  plugin finds them through `in.json` `observations`. A contributed embedding or graph stays in
  its own file beside its identity file; the view's digest covers each by its content, so a layer
  of embeddings alone is visible to a mount and to its unmount (W034).
- **One part.** A cohort's joint object, its libraries already in one file, is a manifest of one
  row: the object is then read in place like any part, and never copied into a view.
- **Refused at `init`, before anything is written:** a manifest that names one sample twice, a
  missing part, a part in a form no reader is written for (a 10x `.h5` or a MEX directory, for
  now), or a missing scope key.
- **Refused at `init` and at every plugin run:** a manifest or a part that the running user can
  write. A plugin is handed the parts themselves. Delivered data are immutable: `chmod a-w` them
  before `init`. The remedy is printed for a shell, and for a file someone else owns it names the
  owner or a read-only copy. A file made writable after `init` has had its ctime moved, so the
  printed remedy adds that a new `init` must follow the chmod.
- **Pinned at `init`, never rewritten:** one digest over the manifest and every part, and each
  file's (dev, inode, size, mtime_ns, ctime_ns), recorded as an `observations/pinned` event. The
  fingerprint is checked before a command first reads any part and after every plugin run,
  whatever its outcome, with what the declared path resolves to now and the pin itself: a
  manifest reached through a re-pointed `latest` symlink, and a pin a plugin deleted or rewrote
  before dying, are changes too. It catches what permissions cannot: a part renamed over through
  its directory, or chmod'ed and written by its owner. A change is an A1 error naming the file,
  so a chmod after `init` is a change too; where only ctime moved (a chmod, a chown, a new hard
  link) the error says so and the remedy is a new stack over the same files. A stack from before
  pins existed is pinned once, on its first read, and that is recorded.

## 2. Slot bindings

| abstract slot | here | on disk, from a plugin |
|---|---|---|
| `column` | `obs` — one value per observation | `columns/<name>.csv`, two columns `barcode,value` |
| `feature_column` | `var` — one value per gene | `features/<name>.csv`, `feature,value` |
| `embedding` | `obsm` — observation × k | `embeddings/<name>.npy` + `barcodes.txt` |
| `matrix` | `layers` — observation × feature, on the object's own feature set | `matrices/<name>.npz` |
| `graph` | `obsp` — a neighbour graph | `graphs/<name>.npz` (compressed sparse) + `barcodes.txt` |
| `mask` | a boolean keep-vector with a reason | `masks/<name>.csv`, `barcode,keep,reason` |
| `object` | a side-car `.h5ad` | `objects/<name>.h5ad` |
| `table`, `figure`, `answer` | as the generic contract defines | |

**A `matrix` MUST be on the object's own feature set.** A result computed on a selected gene set is
an `object`, not a `matrix`: padding the unselected features with zeros asserts *no effect* where
the truth is *not computed*, and nothing downstream can tell the two apart.

## 3. The key map

Column names are not portable. A plugin uses the key; the kernel resolves it per dataset and passes
the resolution in `in.json["keys"]`.

| key | is | resolved from |
|---|---|---|
| `{label}` | the cell-type annotation being used | declared, or detected |
| `{sample}` | the biological unit; the identity scope | declared, or detected |
| `{batch}` | the technical grouping to correct or test against | declared; defaults to `{sample}` |
| `{counts}` | raw integer counts | a layer, never `X` unless declared |
| `{lognorm}` | library-size-normalised, log1p | a layer or `X`, stated |
| `{embedding}` | the embedding in use | declared, or the stack's default |
| `{compartment}` | a coarse label level, where the annotation ships one | declared |

**A plugin naming a real column instead of a key is invalid** and `sch plugin validate` rejects it.

`X` has no key, deliberately. Its scale is not discoverable from the file, so a plugin needing
counts asks for `{counts}` and gets a layer whose integrality was verified.

## 4. Sentinels

A **sentinel** is a label value meaning *the annotator declined to call this observation* — not a
cell type. The profile's defaults are `EXCLUDED` and `UNRESOLVED`; the set is declared per stack
and passed in `in.json`.

Plugins MUST:

- treat a sentinel as **not a cell type**: never a population in a composition, a denominator, a
  per-label statistic or a legend entry as though it were one;
- **never drop sentinel observations** — they are cells, and a plugin that removes them has made an
  undeclared removal;
- state, in `caveats`, how many carried a sentinel and what was done with them.

## 5. Checkpoint kinds

Operations producing genuinely new numbers, which cannot be unmounted (**D1**, **D5**):

| kind | why it is a checkpoint |
|---|---|
| `align` | produces a count matrix from reads. Nothing above it can reconstruct it |
| `ambient` | replaces counts with corrected counts; the correction cannot be decomposed back out |
| `impute` | writes values where there was no measurement |
| `integrate:corrected-counts` | only where a method writes corrected counts rather than an embedding |

**An embedding is not a checkpoint.** It is derived from data still present, so it mounts and
unmounts.

## 6. Merge rules

- Observation-level results merge **by barcode within `{sample}`**, never by position.
- A positional array MUST ship `barcodes.txt` beside it, in row order.
- A plugin returning a different observation count is **refused with both counts**, not truncated
  or padded.
- A merge covering fewer observations than the object fills the remainder with the profile's
  missing value — **`NaN`, never `0`** — and the plugin declares the coverage. A zero sorts first,
  averages into every summary, and looks like a measurement.

## 7. Required declarations

Beyond the generic contract, a single-cell plugin MUST:

- **declare a differential check on any removal.** A plugin providing a `mask` declares
  `gates: {differential_check: required}`, and the gate measures the removal rate **per arm of the
  declared design**. A filter taking 53% of one sample and 6% of another has converted a technical
  property into an apparent biological difference, and nothing downstream can undo it.
- **name what a removal removes, not the category it belongs to.** A mask's `reason` carries the
  actual criterion and the count; the enumerated identities are recoverable from the mask file.
- **declare `{counts}` rather than assume `X`** where it models counts.
- **never assume a cohort axis** (ADR-0027). What makes one dataset differ from another before
  any biology - `species`, `organism`, `assay`, `platform`, `chemistry`, `mt_prefix`,
  `ribo_pattern`, `reference`, `genome`, `tissue`, the profile's `axes:` - is declared once, in the
  stack's `profile_context` (`sch init --context species=homo_sapiens --context assay=scrna`), and
  every plugin receives it there. A name that is not an axis is refused at `init`. A plugin that
  depends on an axis declares `gates: {axes_declared: required}`; `sch conform` S13 refuses a tool
  that gives any axis a literal default. The case that put this here: a mitochondrial step read
  `assay` with a default of the first cohort's single-nucleus value, from a task never given it, and
  bounded a whole-cell cohort as nuclei with every test green.
- **say which assays it supports, if it knows.** The key is `assays: [scrna, snrna]`, values of
  the `assay` axis. It is an optional key added by ADR-0030, and it means the same in a
  `plugin.yml` and in the Universal Plugin Format's `PLUGIN` literal. Single cells are not single
  nuclei (autodev rule 2), so the key is never defaulted. Where it is absent, `sch catalogue`
  reads `not declared` and lists, as evidence, every line of the plugin's own code that reads the
  run's assay. The key states the plugin's scope. It replaces neither `axes_declared` nor the
  stack's declared assay.

## 8. The probe library

The questions askable without writing code. Each is a plugin of `class: probe`, returns a bounded
answer, declares its cost, and states what it cannot establish.

| probe | answers |
|---|---|
| `distribution(column, by=)` | quantiles, modality, per group |
| `composition(label, by=)` | counts and shares, with the denominator named |
| `markers(label, features)` | expression of named features per population |
| `neighbourhood(label, by=)` | kNN purity and mixing, against chance for that population's own composition |
| `disagreement(a, b)` | where two label columns differ, and on which observations |
| `tail(metric, n)` | the actual observations at an extreme, with their identities |
| `observations(n, where=)` | a handful of real rows, not a summary of them |
| `differential(mask, by=)` | removal rate per arm of the design |
| `axes()` | the species from the gene identifiers and the symbol convention, beside the declared `profile_context`; the assay as not measurable |
| `integrality(matrix)` | whether a matrix is counts, measured rather than named |
| `freshness(artifact)` | whether an artifact is older than its inputs |
| `render(view)` | **draws it, and returns the image** |

`render` is the one that changes what an agent can notice. A UMAP shows in one glance what no
statistic reports — a population dispersed rather than aligned, a cluster that is a doublet ridge,
a correction that tore the manifold.

`differential`, `integrality`, `freshness` and `axes` are each the instrument behind a gate
(**G3**); `axes` stands behind `axes_declared`, which refuses a declared species the identifiers
contradict and asks for any axis that is measurable and undeclared.

## 9. The stack

```yaml
# stack.yml
profile: single-cell/1.0
observations: data/                      # immutable; never written
design: design.csv                       # keyed on {sample}
keys:
  label: cell_type
  sample: sample
  counts: counts
sentinels: [EXCLUDED, UNRESOLVED]

plugins:
  align@celescope:      {version: 2.7.3}
  ambient@cellbender:   {fpr: 0, learning_rate: 5e-5}
  qc@scqc:              {min_umi: derived}
  annotate@scanno:      {tree: heart.json}
  integrate@scintegrate:
    methods: [none, harmony, bbknn, scvi, scanvi]
    colour_by: [cell_type, cell_compartment]
  profile@velocity:     {mode: stochastic}
```

Composed by overlay — a site layer, a project layer, a run layer, resolved in order.

## 10. On-disk layout

```
<stack>/
  stack.yml                    the declaration; this is the artifact
  events.jsonl                 append-only, replayable (P1)
  plugins/<name>/              in.json, out.json, and the plugin's own outputs (the name keeps
                               [A-Za-z0-9._-]: qc@scqc runs in plugins/qc_scqc/)
  materialised/
    cohort.h5ad                a VIEW, regenerated on demand, never authoritative
    report/                    report-visible ⟺ replayable (P2)
  scratch/<id>/                agent work; nothing here is quotable (A2)
```

`materialised/` is derived and disposable. Deleting it loses nothing, which is the test of whether
the stack really is the artifact.

## 11. Materialisation

A view written for a consumer:

- string columns and indices as HDF5 string **datasets**, never nullable-string groups — the
  classic encoding is what other readers can open;
- `{counts}` present as an integer layer; `X` stated rather than implied;
- `uns` carries provenance only, never results;
- every masked observation **present**, with its mask columns, unless a consumer explicitly asks
  for the filtered form;
- a `README.md` written by inspecting the directory, so it describes what is there rather than what
  the run intended.

## 12. What this profile does not cover

Spatial coordinates, VDJ chains, paired ATAC, protein panels and perturbation designs are **not**
in v1.0. Each needs slots, keys and probes of its own, and adding them by stretching this
vocabulary is how a profile becomes untestable. They get their own profile, or a versioned
extension of this one, and a plugin declares which it was written against.
