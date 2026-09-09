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

**`legends` — who drew each panel.**

```
sch dev convert legends --root . --point kernel --name <plugin>
```

A build stage: it reads the declaration and no data. Every declared figure says `tool` — the
wrapped tool's own plotting function, unmodified — or `plugin` — this plugin drawing the tool's
NUMBERS itself, a second scale, a derived matrix, an annotation layer. Those are different claims
about provenance and the distinction is what the upstream-plot accounting exists to protect.
Undeclared, the reporter asserted `tool` for anything undescribed, so a plugin-drawn panel was
reported as the tool's own encoding and the accounting was undone at the last step.

Check it against the source rather than guessing: across all nine shipped plugins not one declared
figure calls an upstream plotting function, so all fifty-six are `plugin`. A tenth plugin that
wraps a tool's own figure into its report is the case this stage exists for.

**The legend itself is not declared here, and that is deliberate.** It is written where the figure
is DRAWN, out of numbers no build stage has — the n, the cap that was applied, the populations
that were dropped. A build stage demanding the sentence would be asking for a guess, and a guessed
legend is worse than an absent one because it is believed. So the stage rules the provenance now
and the sentence is proved at test time, by reading back what the run wrote beside its figures.

**Write the sentence at the emit site.** `emit_figure(..., caption=...)`, or the tool's own
`captions.tsv` beside the figures when it draws in its own interpreter. A panel emitted without
one now says so in the log while you are still there to fix it, and the page states plainly that
no legend was written rather than printing the filename with its underscores removed.

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
entries in `cannot_show`. Point `sch dev convert` at it and it prints 7 of 7.

Point it at any other and it prints where that one stopped.

## What the fixture cannot tell you

The two-shape fixture has ONE design factor, so the richest thing a plugin can be asked on it is a
main effect. Four defects in this family live in the branch that reads an INTERACTION — a
subtraction done the wrong way round that stayed self-consistent so no cross-check saw it,
marginals emitted before the strata they average, a marginal arm that was a question the design
enumerated and an object no tool could be handed, and a composed section that named five small
movers as the leading ones. None of them is reachable on one factor. A plugin can be green on
every tier here and meet all four on the first real study.

```
sch dev fixture DIR --crossed
```

writes eight samples in a 2x2 with two in every cell, which is the smallest design in which every
term the reading order distinguishes actually exists. Use it whenever a plugin reads the design at
all. It is a different cohort with its own digest, so it does not disturb any recorded baseline.

And it is still synthetic. What a crossed synthetic cohort proves is that the branch is entered
and the code runs; whether the SENTENCES are true of a real design is a test-stage question, and
the properties that make it interesting — a factor perfectly aliased with the machine that
measured it, cells of unequal size — belong to a cohort, not to a generator.
