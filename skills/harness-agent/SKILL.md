---
name: harness-agent
description: How a working agent operates inside single-cell-harness or inside one of the tools it orchestrates — the loop (plan, mount, inspect, unmount, report), the invariants an agent cannot cross (reads open, writes declared; nothing in scratch is quotable; a gate refuses and only a person lifts it), and the acceptance rule for any change to a child tool (leak guard, fixture through the CLI, pre-declared reproduction). Use whenever asked to analyse a dataset through the harness, add or change a plugin, change a child tool's interface, or decide whether a run can be quoted. Site rules (where compute runs, where files land) come from the site skill, never from here.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# Working inside the harness

Read [`ARCHITECTURE.md`](../../ARCHITECTURE.md) once. Everything below is that document from an
agent's side of the screen.

## The two facts that govern everything you do

**Reads are open, writes are not.** You may compute anything against a materialised view and look
at the result. You may not change the dataset except by mounting a plugin that declares what it
changed. The view you are handed is read-only; a write to it raises, and a write to the
observations fails the mount that contained it (A1).

**Nothing in scratch is quotable.** `sch scratch` runs your code with a scrubbed environment
against a read-only view and tags every number it records as scratch. The report refuses them
(A2). Promotion to something quotable needs a lock, a selftest, a `cannot_show` and a **person's
name** — `--by` with an agent's name is refused, and the refusal is in the stream.

## The loop

```
sch plan PLUGIN [--param k=v]          what would run; every missing prerequisite with its fix
sch mount PLUGIN [--param k=v]         materialise → gates → run → merge → companions
sch stack                              what is mounted, what is invalid, what each contributed
sch ask PROBE [--param k=v] [--upto P] a bounded, read-only answer — the default way to look
sch unmount NAME --dry-run             what would be restored and what would be invalidated
sch unmount NAME                       the declaration is the disposer; dependents go invalid
sch report                             numbers that resolve to events, or no report
```

Ask before you code: `composition`, `differential`, `freshness` ship with the kernel; the
single-cell profile lists more. A question you find yourself answering in scratch twice is a
probe you should write once.

**A refusal is a result.** When a gate refuses, the number that caused it is in the stream
(`sch events --kind gate`), and you can reproduce it yourself with the same probe on the same view:
`sch ask differential --upto NAME --subject …`. If you disagree, you do not route around it; you
either change the input or record an escape — `--escape GATE --why "…" --by "a person"` — and an
escape without a person is refused.

## What you cannot do, and will not be able to

- disable a gate, or turn another gate's refusal into a pass (verdicts reduce by strongest, in any order)
- unmount a checkpoint, or re-declare a checkpoint as `stack`
- quote a scratch number, or promote your own scratch work
- land a result by writing a predictable path: outputs are merged only from what `out.json`
  declares, inside `out_dir`, covered by `provides`; the cache is keyed and rebuilt
- read a credential out of the environment a scratch plugin was handed

These are tested adversarially in `tests/test_adversarial.py`. If you find a way through, that is
the most valuable thing you can report; write it as a test that fails, then a post-mortem.

## Adding or changing a plugin

Use the [`plugin-maker`](../plugin-maker/SKILL.md) skill. Then:

```
sch plugin validate DIR     fifteen static checks; every one has a broken plugin that trips it
sch plugin test DIR         fixture, mount, companion, and for reversible: mount/unmount/compare
```

Write the companion (`invariant.py`) for the relationship the plugin owns, break the plugin until
it fails, put it back. A companion that cannot fail is decoration, and the kernel refuses an empty
one at mount.

## Changing a child tool's interface

The four tools keep their repositories. A change to one is an **interface** change only
(ADR-0013): status file, seal, commit, `sees`/`state_version`, escapes as pairs, declared keys.
It is accepted when all three hold:

1. `sch conform REPO --terms SITE_TERMS` reports no failing row and the tool's own suite passes;
2. a synthetic fixture (a few hundred rows, built in the test) runs through the tool's real CLI
   and asserts the status file, the seal and the products;
3. a **pre-declared reproduction** on the reference cohort — the prediction written in the job
   script before submission — is identical by identity and table to the promoted run, with no
   reshaping script between the tool's output and the comparison.

The third is a reproduction, not a validation. One cohort validates nothing; it proves the change
changed no number.

## Where compute runs and where files land

Not decided here. The site skill decides it — whichever one is installed for the cluster in use — and the
kernel refuses `executor: pbs` until Phase 9 rather than pretending. Inside a scheduler job the
kernel runs with `executor: local`, which is the compliant form there. Never author code on the
cluster; never let a tool choose its own output location; never run a matrix on a login node.

## Before you say a phase, a run or a change is done

- `sch doctor --architecture` holds, and `sch doctor --runtime STACK` holds on the stack you used
- every number you intend to quote is in `sch report`, which means it is an event
- every escape has a person on it
- the reproduction, if the change touched a child, is sealed and identical, and its run key is in
  the record you hand over
