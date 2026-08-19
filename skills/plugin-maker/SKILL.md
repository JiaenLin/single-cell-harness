---
name: plugin-maker
description: Convert a public single-cell tool into a single-cell-harness plugin. Use when asked to wrap, package, port or add a tool (scVelo, CellChat, pySCENIC, CellRank, Milo, LIANA, decoupler, hdWGCNA…) as a plugin, or to fix a plugin failing `sch plugin validate`. Produces a conforming directory: manifest, entry point, lock, selftest and guard.
allowed-tools: Read, Write, Edit, Bash, WebFetch, WebSearch, Grep, Glob
---

# Converting a tool into a plugin

Read [`PLUGIN_FORMAT.md`](../../PLUGIN_FORMAT.md) before writing anything. This skill is the
procedure; that file is the contract.

## What you are producing

```
<name>/
  plugin.yml   run.py|run.R   lock.yml   selftest.py   guard.py?   references.yml?
```

## Order of work

**Do not start with the manifest.** Start by finding out what the tool actually is, because three
manifest fields cannot be written without that and they are the three that matter.

### 1. Measure the tool, do not remember it

Read the **installed** signatures, not the documentation and not your own recollection:

```bash
python -c "import inspect, TOOL; print(inspect.signature(TOOL.main_function))"
```

APIs move between minor versions, and a function that lost a parameter two releases ago will accept
it through `**kwargs` and fail somewhere unrelated. If the tool is not installed, fetch its
repository and read the source of the entry points you intend to call.

Record: the exact version, the entry points, their real signatures, the **recommended settings from
the tool's own tutorial**, and the licence.

### 2. Decide the layer, and bias toward `checkpoint`

Does it produce a view of existing data, or new numbers? A wrong `stack` declaration means the
kernel will offer an unmount that silently produces a different dataset. A wrong `checkpoint` costs
a rebuild. These are not symmetric.

### 3. Write `cannot_show` before writing any code

This is the field that takes the longest and the one that makes the plugin worth having. Sources,
in order: the tool's paper (stated limits), its issue tracker (limits its users found), and
benchmark papers that included it (limits its authors did not mention).

Write what the output does **not** establish, in the terms a reader will use. If the list has fewer
than three entries, you have not finished.

### 4. Capabilities, never column names

`{label}`, `{sample}`, `{batch}`, `{counts}` resolve per dataset. A plugin naming a real column has
bound itself to one project. Prefer `capability:embedding` over `obsm/X_scanvi`.

### 5. Pin hard, and prove it

Take the tool's declared requirements and **ignore the lower bounds** — they say what it was written
against, not what it still works with. Pin the stack it was released alongside, with `==` on every
line.

Then write a `selftest.py` that runs the **whole path** on a synthetic fixture: preprocessing, the
model, the outputs the plugin will merge. Assert shapes and finiteness, never a biological answer.
Importing the package proves nothing — every failure worth catching imports cleanly and dies inside
the first real call.

### 6. Implement the protocol

Read `in.json`, do the work, write declared outputs and `out.json`. Import nothing from the host
except its stdlib-only manifest helper.

- resolve keys from `in.json["keys"]`; treat `sentinels` as *not a cell type*, and never drop them
- obs columns are `barcode,value` CSV; obsm are `.npy` with a `barcodes.txt` beside them
- if the result does not fit the merged object — a matrix on a selected gene set — ship it under
  `objects`. Padding with zeros asserts *no effect* where the truth is *not computed*
- refuse with a reason and a fix rather than producing a number on unsuitable input
- record the wrapped tool's version **at runtime**, read from the tool

### 7. Guard only where the output could mislead

Not a prerequisite check. A guard is for a run that would succeed and produce numbers that do not
support the sentence a reader will write.

### 8. Validate

```bash
sch plugin validate <dir> && sch plugin test <dir>
```

## Refusals

Decline to produce a plugin when:

- the tool cannot be pinned to a working environment — say so rather than shipping a lock that
  resolves differently each week;
- `cannot_show` cannot be written because nobody has established what the tool does not show;
- the tool needs a modality this pipeline does not produce **and** the plugin cannot refuse cleanly
  and name the fix.

A tool that is not ready is a finding. Report it with what is missing.

## Do not

- copy the tool's source into the plugin — wrap it, pin it, cite it
- silently repair the tool's output
- hard-code a column name, an organism, a species or a design
- write `cannot_show: []`
- claim `reversible: true` without knowing what would be removed to undo it
