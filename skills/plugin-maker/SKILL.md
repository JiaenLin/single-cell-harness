---
name: plugin-maker
description: Convert a tool that lives in somebody else's codebase into a plugin of this family, and pick up a half-built one where it was left. Use when asked to wrap, package, port or add a tool (scVelo, CellChat, pySCENIC, CellRank, Milo, LIANA, decoupler, hdWGCNA…), to finish a plugin that is declared but incomplete, or to work out what a plugin still owes. Drives `sch dev convert`, which reads the target repository's own declaration — so this never assumes which plugin format is wanted.
allowed-tools: Read, Write, Edit, Bash, WebFetch, WebSearch, Grep, Glob
---

# Converting a tool into a plugin

## Do not assume the format. Ask the repository.

This family has more than one. The harness's own plugins are directories with a `plugin.yml`
([`PLUGIN_FORMAT.md`](../../PLUGIN_FORMAT.md)). scProfile's kernels are ONE FILE with a `PLUGIN`
dict and a `run(ctx)` — and that format exists because the six-file one was an assembly kit; see
the "WHY THIS REPLACED SIX FILES" note in `scprofile/plugin.py`. A skill that names a layout up
front teaches whichever one it was written against, which is what the previous version of this file
did for months after the format it described stopped being the one anybody wanted.

So the first command is always the same, from inside the repository you are adding to:

```
PYTHONPATH=/path/to/single-cell-harness python3 -m sch dev map --root .
```

That prints the extension points, what each must declare, and the scaffolding command for each. If
the repository has its own maker, `sch dev new` defers to it — use it, because it renders the
template from the format's own knowledge and a generic skeleton does not.

## The whole job, in one command

```
sch dev convert --root . --point <point> --name <plugin>
```

Six stages, in dependency order, each either something a machine extracts from the tool's own
source or something only you can answer — never both. It prints which are done, which are not, and
what the next one is.

**There is no separate "start" and "resume".** A raw tool and a half-built plugin are the same
input at different points on one line; converting a repository is resuming from zero. Nothing is
remembered between invocations — no journal, no lock file — so what remains is computed from the
declaration every time. A conversion picked up on another machine four months later reads the same
answer. Run `sch dev convert` and believe it.

## The mechanical stages: run the command, read the answer

**`inventory` — what the tool already draws.**

```
sch dev convert inventory --root . --point kernel --name <plugin> --python <the plugin's own interpreter>
```

Extractors are plugins: one reads a Python package's `pl`/`plotting` submodule, one reads an R
namespace. `$SCH_EXTRACTORS` adds a site one for an in-house tool. Pass the interpreter the PLUGIN
runs in, not yours — a tool pins versions the harness does not have, and inventorying it in the
wrong environment reports a surface the plugin will never see.

**If no extractor could look, that is not an empty inventory.** The command says so and exits 2.
Build the plugin's environment (`scprofile install <name> --prefix DIR`) and ask again. Never write
`"native_plots": {}` because the import failed — it certifies a wrapper as having nothing to
account for, which is the one claim that is never true.

**`account` — turn the inventory into decisions.**

```
sch dev convert account --root . --point kernel --name <plugin> --python <...>
```

Prints a paste-ready block with every exported function: the ones already decided carried through
unchanged, the rest as placeholders. Re-runnable after a version bump — the answer is then the
diff, plus anything the upstream has stopped exporting.

This is the stage that is worth the most. cellchat used **1** of its tool's 30-odd plots until
somebody went through them; after the accounting it uses **32 of 35**, and four of those answer a
design comparison directly.

**`measure` — the memory the plugin actually costs.**

```
sch dev convert measure --root . --point kernel --run <a completed run>
```

Fitted from a real run, never estimated. Two terms, always: a fixed cost plus a per-cell one. **A
rate with no baseline is worse than declaring nothing** — absent, the allocator assumes
conservative values and prints that it is guessing; a pure rate attributes the fixed cost to the
cells and asks for less than the import costs on a small object, so the job is sized to be killed.
Where the run had one size only, the command prints the rate commented out. Leave it commented.

**`contract`, `defaults`, `references`** — read from the tool's own source. Declare the wrapped
tool's OWN defaults rather than inheriting them silently; declare every resource consulted that did
not come from the user's object, with its tier. If there are genuinely none, declare the empty
container: `"references": {}` says you looked, absent says nobody has.

## The judgement stage: what no command can do

`summary`, `when_to_use`, `cannot_show`, and the question under each figure. Do this LAST, because
every earlier stage is evidence for it.

- **`summary`** — what a user reads in the plan to decide whether they want this at all.
- **`when_to_use`** — the situation someone should reach for it in. Not what it does; when.
- **`cannot_show`** — a conclusion this result does not support, however it looks. Write the
  reading a reader would take that the method cannot carry. If you cannot think of one, you have
  not understood the method yet; go back to its documentation. This field is an ERROR when absent
  because a result whose limits were never written down reads exactly as authoritative as one whose
  limits were thought about.
- **each figure's `question`** — printed above the panel, so a reader knows what it is for before
  deciding whether it answers them.

**Read the tool's documentation and record having read it** in `upstream.docs`, with the date and
what defaults you changed. That record is what catches a default that is wrong rather than absent.

## When you are done

```
scprofile validate <name>          # the declaration, without running anything
sch dev check --root . --point kernel --name <name>
```

`validate` refuses a declaration whose fields still carry the scaffold's marker, and names them —
a plugin whose every human-readable field says TODO is not a plugin the tool can act on. The ladder
adds the two-shape fixture: the same synthetic cohort written twice with every column renamed, so
code that asks for a capability passes both and code that knows a column name passes one.

Every tier prints what it does **not** prove. A green ladder does not say the numbers are right.

## What good looks like

cellchat is the only finished conversion in the family and the standard the rest are measured
against: 35 upstream plots accounted, 10 declared figures all drawn, both memory terms measured, 9
entries in `cannot_show`. Point `sch dev convert` at it and it prints 6 of 6.

Point it at any other and it prints where that one stopped.
