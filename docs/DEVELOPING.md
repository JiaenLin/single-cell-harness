# Developing the family

How the five repositories are extended, and why the machinery for extending them is shaped the
way it is. [`skills/harness-developer`](../skills/harness-developer/SKILL.md) is the procedure;
this is the reasoning and the reference.

## 1. The problem this addresses

Every tool in this family was developed by an agent against one real cohort on one cluster. That
arrangement produces four failures reliably, and produced all four during September 2026:

**Overfitting is the default, not a mistake.** A tool developed against one dataset learns that
dataset — that the sample column is called `sample`, that there are ten libraries, that two arms
exist. None of it is true of the next dataset and none of it fails a test, because the only
dataset the tests have is the one the assumptions came from.

**Proof is expensive, so it is deferred.** The only honest proof was a cluster run against the
real cohort: an hour and a queue slot. A change therefore reached the queue carrying three
defects instead of one, most of which a laptop could have found in four seconds.

**Five idioms, no map.** scProfile loads a kernel directory carrying `kernel.yml`, or a
`kernels/<name>.py` with a `PLUGIN` dict. scIntegrate adds a key to `METHODS` and another to
`SEES`. scQC adds one to `CRITERIA` and one to `GATES`. scAnno has no registry and wires
functions in its CLI. The harness validates a `plugin.yml` against a profile. An agent's first
half hour on any of them goes to finding where the new thing plugs in.

**Rules without mechanisms are predictions.** "Do not pull into a tool checkout while a run is
using it" was written down, and then broken twice in one afternoon by the person who wrote it.

## 2. The one design decision

`sch dev` knows nothing about kernels, methods, criteria, mechanisms or plugins. Each repository
declares its extension points in `DEVPOINTS.yaml`, and every command reads the declaration.

This is the same split the harness already makes between `PLUGIN_FORMAT.md` and
`docs/profiles/single-cell.md`, for the same reason: a suite that hard-codes one repository's
idiom is a suite for one repository, and the sixth kind of extension — or the fifth tool's
second point — should be a file, not a change to the suite.

It has a second effect worth naming. Because the suite can only check what the declaration says,
**declaring an extension point is how it becomes checkable at all**. A point missing from
`DEVPOINTS.yaml` is a point nothing verifies.

## 3. `DEVPOINTS.yaml`

```yaml
tool: scintegrate            # the name a run record will carry
devpoints: 1                 # schema version
terms: docs/forbidden_terms.txt          # optional: the leak tier's word list
baseline_dir: tests/baselines            # optional: default tests/baselines

tests:
  command: ["{python}", "tests/run_all.py", "--jobs", "{jobs}"]   # whatever THIS repo uses

fixture:                     # may also be given per point, overriding this
  command: ["{python}", "-m", "scintegrate.cli", "integrate",
            "--h5ad", "{observations}", "--out", "{out}",
            "--batch-key", "{role_sample}", "--label-key", "{role_cell_type}",
            "--methods", "none,{name}"]
  products: ["report.json"]              # relative to {out}; checked for existence and size
  accepts_refusal: false                 # true where a refusal on the fixture is correct
  timeout: 1800

points:
  method:
    what: <one line a reader would recognise>
    lives: scintegrate/methods.py         # a file, or a directory the new thing goes into
    register:                             # optional; checked by PARSING, never written
      - {file: scintegrate/methods.py, table: METHODS}
      - {file: scintegrate/methods.py, table: SEES}
    must_declare: [...]                   # printed by `new` and `map`; prose, for the author
    example: harmony
    template: templates/method.py.in      # optional
    tests: [tests/test_methods.py]
    proves: <what a green ladder establishes for this point>
    cannot_prove: <what it does not — required, and the field people skip>
```

Placeholders available in a command: `{python}`, `{observations}`, `{design}`, `{out}`,
`{name}`, `{shape}`, `{root}`, and one per role — `{role_sample}`, `{role_condition}`,
`{role_batch}`, `{role_cell_type}`, `{role_subject}`, `{role_covariate}`, `{role_counts}`.

`command` may be one command or a list of them, run in order, stopping at the first non-zero.
A tool whose end-to-end exercise is three invocations should not have to hide them in a shell
script to be checkable — a shell script is exactly where the pipeline-exit-code trap lives.

**`register` is checked, not written.** An earlier draft edited the registry dict. Text-editing
a Python literal is guesswork the moment the file is laid out differently from the way the
guesser expects, and a scaffolder that half-registers something creates a defect that looks like
a typo. `sch dev new` prints the edit and `sch dev check` parses the file with `ast` to see
whether it landed. A registry built by a comprehension is reported as **unreadable**, not as
empty — "I cannot see it" and "it is not there" are different facts.

## 4. The fixture, and the two shapes

`sch dev fixture DIR` writes one synthetic cohort twice. Identical counts, identical embedding,
identical assignment of cells to samples and populations — under different names:

| role | shape a | shape b |
|---|---|---|
| sample | `sample` | `library_id` |
| condition | `condition` | `arm` |
| batch | `batch` | `chip` |
| cell type | `cell_type` | `celltype_final` |
| subject | `subject` | `donor_id` |
| covariate | `age_weeks` | `age_at_collection` |
| counts layer | `counts` | `raw_counts` |

Both digests are equal, and that invariant is what the trick rests on: if the two shapes ever
differ numerically, the fixture is at fault and no conclusion drawn from a shape comparison is
worth anything.

`X_pca` is deliberately the **same** in both. It is a scanpy convention, not a property of a
cohort, and a tool may legitimately expect it. The point is to catch assumptions the tool was
never promised, not to fail it for using the ones it was.

Sixteen structural hazards are built in and named in `HAZARDS.json`, each drawn from a defect
this family has had or a trap the format sets. Two of them collide by construction — an all-zero
cell makes every gene non-constant — so `constant_gene` is constant among the cells that have
any counts, which is the realistic form: the variance is zero after QC drops the empty cell,
which is exactly when a scaling step reaches it.

**Nothing measured on the fixture is quotable.** `FIXTURE_<shape>.json` says so, and says what
it cannot prove.

## 5. The ladder

| tier | question | cost |
|---|---|---|
| `declaration` | is the point declared, and is the thing registered in every table it names? | ms |
| `contract` | `sch conform` on the repository | ms |
| `unit` | the repository's own suite, run the way the repository runs it | seconds |
| `fixture_a` | does it run end to end and leave a valid status behind? | seconds |
| `fixture_b` | does it still, with every role renamed? | seconds |
| `leak` | any cohort or site term anywhere in the repository? | ms |
| `baseline` | did a number move that was not supposed to? | ms |

Every tier prints what it does **not** prove, and the run ends with the union of those plus the
line that matters most: *a green ladder does not establish that the tool reproduces the real
cohort — only a cluster run against the reference does that.* Stating it on every passing run is
the difference between a gate and a rubber stamp. The whole risk of a fast local check is that
it starts to feel like the answer.

**Site shapes come from the site, not from the tool.** `sch conform` carried three patterns it
called generic — one cluster's login node, one scheduler's head node, and that scheduler's job-id
format. A general instrument that knows the naming of the site it happened to be written at is
overfitted twice over: it reports a leak the next site does not have, and it stays silent on the
leak that site does have. The built-in list now holds only what is true anywhere (a user home
path, an address, this family's dated-scratch convention), and the rest arrives through
`--shapes FILE` or `$SCH_SITE_SHAPES`, one `<regex> :: <what it is> :: <literal>` per line, from
the project that owns the cluster. When no file is supplied the scan says so (`S1d`) rather than
implying it looked; when a line will not load, that is reported too (`S1e`), because a shape that
silently fails to load is a check that silently does not run.

The `leak` tier asks its question of the **repository**, not of what a run produced. The first
version scanned both, on the reasoning that a tool can be clean in its source and still write a
cohort's vocabulary into a result — true, but the site list that catches a cohort also contains
the site: the cluster's user, its group, its scheduler head node. A run record is *supposed* to
say where it ran. Scanning run output reported three of five repositories as leaking because
their runs recorded the machine they ran on. Paths and job ids are provenance in an output and
defects in a repository, and no word list tells them apart; the tier therefore asks where the
answer is unambiguous, and says so in its `cannot_prove`.

Exit codes are `0` passed, `2` failed, `3` could not run. The separation matters because a
check that skipped every tier used to exit `0`, and an agent reads that as proof. It also means a
missing baseline, a missing declaration and an absent dependency are all `3` — setup, not defect.

A **baseline** is the numeric fingerprint of a fixture run: numeric leaves of every JSON,
per-column statistics of every CSV, bytes of everything else, with volatile fields (times, job
ids, paths, commits) excluded. Floats compare with a relative tolerance rather than bit-equality,
because bit-equality across machines is not a property this family has — 0.214 was measured
between two nodes of the same model on 2026-09-06.

**Recording runs the fixture twice, and keeps only what the two executions agreed on.** Anything
that moved is excluded and *named* in the file under `not_execution_stable`. The second execution
writes to a different directory on purpose: two runs into one directory cannot tell a value the
tool computed from a value that is really its own output path, and a baseline full of paths fails
the first time anyone checks from somewhere else. This is the same rule the reproduction
discipline reached from the other side — a prediction is per output, and an output that is not
execution-stable is named with its spread rather than predicted identical.

Two limits, stated because they are easy to forget. Two runs on one node is the weakest evidence
of stability that is still evidence: it says nothing about a third execution and nothing about
another machine, so a baseline recorded where harmony is stable may still fail where it is not.
And a baseline is worth recording only for a tool whose fixture output carries numbers; for one
that writes nothing to `{out}`, the tier correctly reports that there is nothing to fingerprint.

A difference is a **stop**, not a verdict. Either the number should not have moved, or
`state_version` must be bumped to say it did, on purpose, and the baseline re-recorded.

## 6. What the emitted job does that a hand-written one did not

`sch dev job` was written from five failures, each of which cost a cluster hour in September
2026 and each of which is recorded in `docs/CHILD_CONFORMANCE.md` or
`docs/postmortem/0001-a-reproduction-that-was-not-like-for-like.md`:

- the command comes from the **reference run's own recorded argv**, with only the destination
  changed — not from a stage script, which is how a reproduction ran with `--label-key
  cell_type` while the run it reproduced had used `cell_type_forced`;
- the tool checkout is **frozen**: the commit is read at submission and the job refuses at start
  if it moved;
- expected products are **derived from the reference directory**, not typed — a job once checked
  `rescue/` while the tool writes `rescued/`;
- nothing is piped, and a `FAILED` seal exits non-zero, so the scheduler's record and the
  directory's record cannot disagree;
- the queue is required and never defaulted, and a `host=` pin carries the finding that the pin
  only works in a queue whose pool contains that host;
- and it refuses to be written **without a prediction**. A prediction made after the numbers are
  in is not a prediction.

Two defects in that job were found by running it rather than by reading it: `set -u` killed the
drift guard before it could compare — a guard that fails open is worse than none, because the
header claims it ran — and a `FAILED` seal exited 0. Both are fixed and both are tested.

## 7. What each repository declares

| repository | points |
|---|---|
| `single-cell-harness` | `plugin`, `profile`, `companion` |
| `scQC` | `criterion`, `step`, `adapter` |
| `scAnno` | `mechanism`, `sentinel` |
| `scIntegrate` | `method` |
| `scProfile` | `kernel`, `panel` |

`sch dev map --root <repo>` prints the current answer, which is the one to trust.

---

## 8. Conversion stages that rule on a declaration's entries

A `convert:` stage names the fields it fills. Some stages rule on the field's PRESENCE; others
rule on every entry of it, and a stage of the second kind reports itself unfinished while any
entry is unanswered. The keys below are read from the target repository's own `DEVPOINTS.yaml` —
nothing in `sch/` knows what a figure family or an upstream plot is.

| key | what the stage then requires |
|---|---|
| `each_item_declares` | every entry of the filled field carries the named sub-keys |
| `each_draw_site_describes` | every place the plugin's source produces a panel passes a legend |
| `places_every` | every figure family named in the listed fields is placed by a rule in the field this stage fills |
| `positions` / `axes` | the values those rules may take |
| `axis_field` | the field mapping a family to what it multiplies over |

`places_every` takes one entry per declaration that names figure families, each saying how to read
an id out of it — a key, a value at a path, or filenames inside prose — and, where the format
marks a family drawn once per data item, which sub-key carries its ceiling. The worksheet then
lists what is unplaced, what has no axis and what is unbounded, and prints the edit for each.

The stage is a BUILD stage: it reads declarations and source only, so it cannot be shaped around
one cohort.

---

## 9. `sch dev jobcheck` — the shell defects this family has paid for

Five job checks existed as assertions inside `tests/test_convert.py`, and every one of them
globbed `<repo>/jobs/*.pbs`. They therefore guarded the jobs kept in a repository and nothing
else, while the job actually being submitted is very often written beside a run and gets none of
them. A job authored that way reproduced a documented defect — an exit code read into an echo,
displayed and kept nowhere — and carried on past a refused install.

`sch dev jobcheck` reads any job script named on the command line, and every `jobs/*.pbs` under `--root` when none is. The rules are one definition shared by the
command and the ratchet, so the two cannot drift. Each exists because it once cost a submission;
none is a style opinion:

| rule | defect |
|---|---|
| `exit-displayed` | an exit code read into an echo is reset and kept nowhere |
| `status-not-kept` | a command's status captured into a message and never tested |
| `tee-without-pipefail` | `cmd \| tee log` exits with tee's status, so a failure reads as ok |
| `unguarded-grep-substitution` | a substitution whose grep finds nothing ends a `set -e` shell |
| `apostrophe-in-parameter-error` | an apostrophe inside `${VAR:?...}` ends the word |
| `no-seal` | a job that writes no seal cannot be told from one that never ran |
| `does-not-parse` | `bash -n` refuses it |

A job may silence one rule by name with `jobcheck: allow <rule-id>` in the file, where a reader
will see it. Anonymous suppression is how a check stops meaning anything.

