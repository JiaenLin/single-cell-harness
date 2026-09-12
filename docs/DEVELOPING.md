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
| `rules` | do the rules this round declared still hold? (§10) — skipped where none are declared | ms |
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
| `enforced_by` | the drawing code must READ the ceiling: a conditional naming the token that returns |
| `generated_by` | a command that writes the stage's mechanism, so the check can regenerate it and compare |
| `every_requirement_declared` | no package the artefact LOADS is one only its neighbours declare |
| `version_is_current` | the field this repository calls its reuse key moved when the artefact did |

`places_every` takes one entry per declaration that names figure families, each saying how to read
an id out of it — a key, a value at a path, or filenames inside prose — and, where the format
marks a family drawn once per data item, which sub-key carries its ceiling. The worksheet then
lists what is unplaced, what has no axis and what is unbounded, and prints the edit for each.

The stage is a BUILD stage: it reads declarations and source only, so it cannot be shaped around
one cohort.

### Demanded, checked and generated are three different claims

`enforced_by` closes an asymmetry: deleting a DECLARATION turned the maker red at once, while
deleting the code that honoured it turned nothing red — one plugin declared 49 ceilings, enforced
none of them, and reported `build: 7 of 7 complete`. The stage now requires that a draw wrapper
refuses past its ceiling, in whatever language the plugin draws in, and a wrapper that DELEGATES
is guarded by what it delegates to — otherwise the check would be demanding the guard be written
twice.

`generated_by` closes the next one. A stage that requires mechanism, and finds mechanism, still
does not know the mechanism is the maker's OUTPUT rather than a hand-written file that satisfies
the check. The command is run into a scratch directory and the result compared byte for byte;
`{out}` is that directory and `{python}` is the HOST's interpreter, because a generator is the
repository's own tool whatever language the artefact is written in. A companion that has been
edited in place reads as `DRIFTED`, one that is absent as `MISSING`, and a generator that cannot
run as `cannot say` — never as a pass.

This was not a hypothetical gap. In the repository it was written for, the command named there
**crashed for every artefact in the repository**: it wrote a six-file layout that repository had
replaced, and took a one-file artefact's path for a directory. The file it was said to generate
had never been generated once, while being given as the reason the mechanism was no longer
hand-written.

A generated companion belongs to ONE artefact and is named for it — `kernels/cellchat.draw.R`,
never a bare `draw.R` beside nine plugins that would answer the requirement for all of them.

### A command with no stage gates on nothing

Two of this suite's own checks were commands and not stages, and both had already been paid for.

`sch dev convert borrowed` resolves a plugin alone, resolves it with its family and subtracts, so
a plugin that USES a package its own declaration never asks for is answerable with no run at all.
It was a command. A plugin spent its whole life in a seven-member environment depending on two
packages it declared neither of; its selftest passed, because neither is imported at module scope;
`build: 7 of 7 complete` was printed over it; and two drawing paths died forty minutes into a
cohort run. `every_requirement_declared` makes it a stage. **A lent package is exposure and a
LOADED one is a debt** — a shared environment lends its members a hundred names each and a stage
owing on a loan would be red on every member of every shared environment at once.

`sch dev convert freshness` asks git whether the reuse key moved when the artefact did. It was a
command. A commit rewrote a plugin's drawing protocol and left the key standing still, and an
audit found it *afterwards* — which as a stage is found before. `version_is_current` makes it a
stage. **STALE is the only debt**: `CANNOT SAY` — uncommitted, computed, no history — is a fact
about the checkout, not about the plugin.

### What the stages cover, which is not whether they are done

`sch dev convert status` prints a coverage block whenever a key in the point's `must_declare` is
filled by no stage. Measured on the repository this was written for: seventeen required keys,
**nine** filled by a stage, and `build: 7 of 7 complete` printed over the other eight. A
complete build and a covered declaration are two different claims and only one of them was ever
shown. An unowned field is not automatically a defect — a conversion's *input* cannot be its
output — but not saying so is.

**A required key no stage fills is one of four things, and the point says which.** Under
`truth:` a point maps each such key to `input` (the conversion's input, never its output),
`validator` (the repository's own validator refuses it when wrong) or `measured` (read back from
a run by a named command). A key with no stage and no entry is **CHECKED BY NOBODY**, printed in
those words on every status. That is the state `cores` and `cost` were in for the whole life of
the repository this was measured on — required, present-checked, trusted by the scheduler, and
true by nobody's account — while the coverage line listed them beside the validator's keys with
nothing to tell the two apart. A `truth:` entry naming a key the point does not require, or a
value outside the three, is refused when the declaration loads; an entry for a key a stage also
fills is reported as two answers to one question, not resolved silently.

---

## 10. `sch dev rules` — the rules of a development round, checked

A round of work on a maker has rules, and the reason is not tidiness. A maker's only real evidence
that it generalises is an artefact it has never seen; ordinary helpfulness destroys that evidence.
Repair the plugins that are broken and there is nothing left to test the maker on. Hand-edit the
one being converted and the maker is no longer what produced it. Both feel like progress.

So the round declares its rules in the repository's own `DEVPOINTS.yaml`, under `rules:`, and this
command checks them. It reports and never writes.

| rule | what it reduces to |
|---|---|
| `maker_output` | no block of `min_block`+ significant lines is repeated inside an artefact or shared between two |
| `held_out` | the named artefacts are unchanged over the range |
| `in_place` | every changed path is declared mechanism, or the artefact the round is converting (or a companion generated beside it) |
| `end_to_end` | what runs end to end is exactly the complement of the held-out set |

**Duplication is the signal for hand-written mechanism.** Method is written once because it is
about one method; mechanism appears twice because it is about all of them. Measured: one plugin
carried three near-identical copies of a ceiling reader and six draw wrappers in three variants,
and one of those copies recorded, in its own comment, a run lost because a function present in two
of them was missing from the third. A generated definition cannot have that defect; three
hand-written ones cannot avoid it.

**The range is pinned in the declaration.** Two of these rules are answered from git, so whoever
chooses the range chooses the answer, and the flattering range is always available. `rules.since`
makes the range part of the claim: moving it is a diff a reader can see. `--since` still overrides,
and the report says which it used. Comments and blank lines are dropped before comparison, in
every language the artefact is made of — two copies of one mechanism differ in their comments far
more than in their code.

Silence is never a pass: no `rules:` block, or a range that is not a commit, reports `cannot say`
and exits 3.

It is also a **tier of the ladder**, because a command you have to remember to type is not
enforcement. A repository declaring no rules is not failed by that tier and is not passed by it
either: the tier reports that it could not run, and the ladder ends with `COULD NOT run: rules —
so this is not a full check`. Inventing rules for a repository that has declared none would be
this tool deciding how somebody else's round works.

---

## 11. `sch dev convert overfit` — is the maker general, or fitted to the one it was built on?

The gold standard is a conversion of an artefact the maker has never seen, and that evidence is
spent the moment it is used. Between conversions there is nothing to appeal to but the maker's own
source. This measures the two things that can be read off a family with no run and no conversion,
and refuses to pretend they are the third.

**Corpus** — how many artefacts each instrument could actually look at. A check whose corpus is
ONE was fitted by construction, however carefully it was written, and no change to it is
falsifiable. It is measured per instrument and not per stage: `placement` asks three questions with
three instruments, two of which read a declaration and one of which has to find code in whatever
language the plugin draws in.

**Discrimination** — how many distinct answers an instrument has ever given. One answer over a wide
corpus may be a constant wearing a check's clothes. A family in which every artefact is *finished*
is reported separately, because calling that vacuity would be a false alarm on every completed
conversion; the evidence that fills that gap is a scaffolded artefact asked at once.

**Fitted literals** — constants in the maker naming the upstream vocabulary of exactly one member,
where that vocabulary is the tool name and the symbols the artefact itself accounts for. A general
maker may name a convention; it may not name a member's tool. The corpus composition is printed
beside the findings, because a family one member dominates cannot distinguish that member's
vocabulary from the family's.

It exits 2 on a finding, 3 on a point holding fewer than two artefacts — generality is a fact about
a family or about nothing — and it says in its own output that it is not a substitute for held-out
conversion and does not spend it.

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

