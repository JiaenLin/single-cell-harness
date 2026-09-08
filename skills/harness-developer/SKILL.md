---
name: harness-developer
description: How a working agent EXTENDS the single-cell-harness family — adding a scProfile kernel, a scAnno annotation mechanism, a scQC criterion, a scIntegrate method, a harness plugin or profile. Covers the `sch dev` suite (map, new, fixture, check, baseline, job), the two-shape fixture that makes overfitting a test failure instead of a review opinion, the six-tier ladder and what a green ladder does not prove, and the rule that a change touching numbers is merged only on a reproduction predicted in writing beforehand. Use whenever asked to add a mechanism to any of the five repositories, or to decide whether a change is ready to merge. Operating the tools is harness-agent; site rules are the site skill.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# Extending the family

`harness-agent` is how you OPERATE these tools. This is how you CHANGE them. Read
[`docs/DEVELOPING.md`](../../docs/DEVELOPING.md) once for the reasoning; this is the procedure.

## Start by asking the repository, not by reading it

```
sch dev map --root <repo>            # what can be added here, and how it is registered
sch dev map --root <repo> --json     # the same, for you
```

Every repository declares its own extension points in `DEVPOINTS.yaml`, because the five extend
in five different ways — scProfile loads a kernel directory, scIntegrate adds a key to two
dicts, scQC adds one to `CRITERIA` and one to `GATES`, scAnno has no registry at all, the
harness validates a `plugin.yml` against a profile. **If the point you want is not declared,
declare it before you write code for it.** A point that is not in `DEVPOINTS.yaml` is a point
nothing can check.

Each point tells you three things you should read before anything else: what it must declare,
what a green check **proves**, and what it **cannot prove**. The third is the one that decides
how much cluster time this change is going to cost you.

## The order of work, and why it is this order

**1. Write the SPEC before the mechanism.**

```
sch dev new <point> <name> --root <repo>
```

This writes the skeleton, a `SPEC.<name>.md`, and a test stub. Fill in the SPEC first — what it
sees, what it cannot show, what would make it wrong, and what `state_version` means for it. An
agent that writes the code first writes claims that describe the code. Writing them first is the
cheapest design review available, and if a line in the SPEC changes while you are writing the
mechanism, **that is a finding to report, not an edit to tidy away**.

It does **not** edit the registry. It prints the edit; `sch dev check` verifies by parsing that
it landed. The writer is not the checker, on purpose.

**2. Run the ladder while the change is still in your head.**

```
sch dev check --root <repo> --point <point> --name <name>
```

Seven tiers, cheapest first, stopping at the first failure (`--keep-going` runs them all):

| tier | what fails here |
|---|---|
| `declaration` | not registered, or the point does not exist |
| `contract` | `sch conform` on the repository — leak guard, output defaults, status contract |
| `unit` | the repository's own suite, run the way the repository runs it |
| `fixture_a` | it does not run end to end on a synthetic cohort |
| `fixture_b` | **it runs on shape a and not on shape b — you hard-coded a column name** |
| `leak` | a cohort or site term reached the repository — source, tests, docs, jobs |

The word list and the shape list both live **outside** the repository being checked — `$<TOOL>_FORBIDDEN_TERMS` for names, `$SCH_SITE_SHAPES` for hostname and job-id patterns. A tool that ships the cohort's vocabulary in order to prove it does not ship the cohort's vocabulary has shipped it, and a tool that knows one cluster's hostnames is blind to every other cluster's. Both checks say plainly when they were given nothing.
| `baseline` | a number moved that was not supposed to move |

**What the exit code means.** Three outcomes, and the third is the one worth branching on:

| code | meaning |
|---|---|
| `0` | what ran, passed |
| `2` | a check failed, or your input was refused — something is wrong and the message names it |
| `3` | nothing could be run: no `DEVPOINTS.yaml`, a dependency absent, no baseline to compare against. **Nothing was proved either way**, which is not the same as passing |

A `sch dev check` whose every tier skipped exits 3, not 0. A green that established nothing is
the one result an agent must never read as permission.

**3. Read what it says it did not prove.** Every tier prints that, and the run ends with the
union. A green ladder is permission to spend an hour on the cluster with a reasonable
expectation the hour will not be wasted. It is not a merge.

**4. If the change touches numbers, reproduce it on the real cohort.**

```
sch dev job --root <repo> --ref <REFERENCE RUN> --rundir <NEW RUN> --tool <TOOL CHECKOUT> \
            --queue <QUEUE> --select 'select=1:ncpus=24:mem=64gb' \
            --predict 'what each output should do, and what a difference would mean' \
            --out <repo-or-project>/jobs/<n>_reproduce.pbs
sch conform --run <NEW RUN> --against <REFERENCE RUN>     # is the comparison even meaningful?
```

The emitted job takes its command from **the reference run's own recorded argv**, freezes the
tool checkout and refuses if it moved, derives expected products from the reference directory,
and refuses to be written at all without a prediction. Submit it; do not hand-edit the derived
sections without saying so in the header.

## Shape b is the part you will be tempted to skip

The fixture is one cohort written twice: identical numbers, every role renamed —
`sample`→`library_id`, `condition`→`arm`, `cell_type`→`celltype_final`, the counts layer
`counts`→`raw_counts`. A mechanism that RESOLVES a role gives the same answer on both. A
mechanism that KNOWS a name gives an answer on one.

If shape b fails, the answer is almost never to special-case the name. It is that the mechanism
should have been told which column holds the role — the fixture command can pass
`{role_sample}`, `{role_cell_type}` and the rest, and being told is correct behaviour. Fix the
mechanism, not the fixture.

Sixteen structural hazards are built in and named in `HAZARDS.json`: a sample of seven cells, a
population in one arm only, a population of one cell, NaN in a numeric column, a category no
cell has, a barcode repeated across samples, an empty cell, an empty gene, a gene with no
variance, a gene symbol colliding with a column name, `S1` beside `S10`, a label containing a
space and a slash, an object column holding `None`, a design row for a sample with no cells,
mitochondrial genes, and a covariate that is constant inside one arm. If your mechanism breaks
on one, it is a defect in the mechanism — every one of those exists in real data.

**Nothing measured on the fixture is quotable.** It is synthetic. It proves shape and contract;
it proves nothing biological, and a SPEC that claims accuracy on the strength of it is wrong.

## The five rules that were paid for

Each of these cost a wasted cluster hour or a wrong answer in September 2026. The suite enforces
the first five mechanically; you still have to hold the sixth.

1. **A reproduction takes its parameters from the record of the run it reproduces**, not from a
   stage script and not from documentation. `sch dev job` reads the argv.
2. **Never pull into a tool checkout while a run is using it.** The emitted job refuses on drift.
   A rule without a mechanism is a prediction — this one was broken twice in one afternoon by
   the person who wrote it.
3. **Never pipe a command whose exit code you care about.** `| tee` and `| tail` return the last
   command's status. Nothing in `sch dev` pipes, and neither should your jobs.
4. **A host pin only works in a queue whose pool contains that host**; elsewhere PBS says
   "Insufficient amount of resource: host", which reads like the node does not exist.
5. **Expected products come from what the reference run actually wrote**, not from what you
   expect it to have written.
6. **A difference is measured against something else, never argued away.** A reproduction that
   reports DIFFERENT may still be sound — but only after the difference has been attributed by
   measurement. Leave the verdict standing in the record when it is; it was right about what it
   measured.

## Before you say a mechanism is done

- [ ] `SPEC.<name>.md` filled in, and any line that changed while coding is reported
- [ ] registered in every table the point declares — `sch dev check` says so by parsing
- [ ] `sch dev check` green, and you have read what it says it did not prove
- [ ] shape b passes for the right reason (the mechanism is told, not that you special-cased it)
- [ ] a baseline recorded and committed, if the mechanism produces numbers — `sch dev check
      --record-baseline` runs the fixture twice and keeps only what both runs agreed on,
      naming the rest as `not_execution_stable`. Read that list: it is telling you which of
      your outputs a reproduction must not predict identical
- [ ] if numbers a run has quoted could move: a reproduction, predicted in writing beforehand,
      and `sch conform --run … --against …` saying the comparison was meaningful
- [ ] anything the fixture could not establish, said out loud in the PR rather than left implied
