# Converting a public tool into a plugin

The process `sch plugin new` automates and an author checks. It exists because the mechanical parts
of wrapping a tool — the manifest, the lock, the selftest, the merge — are the same every time, and
the parts that need judgement are always the same three.

**The mechanical parts should cost minutes. The judgement should cost an afternoon**, and it is
what makes the difference between a plugin and a subprocess call.

---

## 1. Scaffold

```bash
sch plugin new velocity --wraps scvelo --language python
```

Writes the directory, a manifest with every required field present and unanswered ones marked
`TODO`, a `run.py` implementing the protocol with the computation left blank, a `lock.yml` seeded
from the tool's own requirements, and a `selftest.py` that builds a synthetic fixture and runs the
full path.

A manifest containing `TODO` fails `sch plugin validate`. The scaffold is deliberately not
runnable.

## 2. Answer the seven questions

These are the admission gate, and their answers become manifest fields. A tool that cannot answer
them is not ready to be a plugin.

| question | becomes |
|---|---|
| What does it answer that nothing already mounted answers? | `summary`, `when_to_use` |
| What does it need beyond counts, labels and samples? | `needs`, `sourceable` |
| Can it be installed reproducibly and proven to work? | `lock.yml`, `selftest` |
| What can its output **not** show? | `cannot_show` |
| Is there independent evidence it works on data like this? | `CHANGELOG`, and whether to ship at all |
| What breaks silently if the input is wrong? | `guard.py` |
| What relationship does this plugin own that could break silently **while it runs**? | `invariant.py`, or `no_runtime_invariant:` with the reason |

The fourth is the one that takes an afternoon and the one worth it. Read the tool's own paper for
its stated limits, then its issue tracker for the limits its users found, then decide which of
those a reader of *your* report needs to meet.

## 3. Decide the layer

Does the tool produce a **view** of data that already exists, or **new numbers**?

- A filter, a score, a label, an embedding, a graph → `layer: stack`.
- Alignment, ambient correction, imputation, anything replacing counts → `layer: checkpoint`.

**When in doubt, declare `checkpoint`.** The cost of that mistake is an unnecessary rebuild; the
cost of the other is an unmount that silently produces a different dataset.

Then set `state_version: 1`, and treat it as part of releasing: it goes up whenever the plugin
computes something different for the same inputs — including when the wrapped tool's version moves.
`version` is the wrapper; `state_version` is the numbers, and every cached view is keyed on it.

## 4. Map capabilities

Write `needs` and `provides` as capabilities, not implementations, and never hard-code a column
name — `{label}` and `{sample}` resolve per dataset.

If an input cannot come from the object at all — spliced counts, a BAM, a design table — list it
under `sourceable` and implement the search, or leave it in `needs` and let the plugin refuse
cleanly. **A refusal naming the fix is a good outcome.** Most datasets will hit it.

## 5. Pin the tool

Read the tool's declared requirements, then ignore their lower bounds. `pandas>=1.1.1` is honest
about what a tool was written against and says nothing about what it still works with; resolved
today it pulls a major that may have removed the function the tool calls.

Pin the stack the tool was released alongside. Then make the selftest run a real computation, so
the pin is proven rather than asserted.

## 6. Write the guard, if the tool can mislead

A guard is not a prerequisite check — those are structural and live in `needs`. A guard is about
**interpretability**: the run would succeed, produce numbers, and those numbers would not support
the sentence a reader will write under them.

Velocity's guard refuses when the assay is undeclared, because velocity means different things on
nuclei and whole cells and every caveat it writes depends on knowing which. Abundance's guard
refuses when the tested factor is nested in the batch key, because the test returns clean p-values
for a contrast that is not identifiable.

Every override is logged, as a pair — what was refused and with what number, then who lifted it and
why. A gate with no escape gets switched off; a gate whose escapes are all recorded does not. A
guard refuses or abstains; it never approves on another guard's behalf.

## 7. Assert what you own, while it runs

The guard runs before. The companion runs *during*, on real work, and asserts a relationship this
plugin owns: every removed observation appears in the removal record, every barcode written back
was one that came in, the count of masked cells matches the mask.

Write it in `invariant.py`, or write `no_runtime_invariant:` in the manifest with the reason there
is nothing observable to assert. Both are answers; leaving it out is not, because *nothing to
check* and *nobody thought about it* have to be distinguishable. Then break the plugin until the
check fails and put it back — a check that cannot be made to fail is decoration.

## 8. Validate, then test

```bash
sch plugin validate .      # static: manifest, lock, capabilities, claims
sch plugin test .          # builds the env, runs the selftest, runs on a fixture, mounts the
                           # companion, and for reversible:true mounts / snapshots / unmounts /
                           # compares
```

## 9. Ship

Add `README.md` with its four sections — what it does, report surface, cost, known limitations
([`PLUGIN_FORMAT.md`](../PLUGIN_FORMAT.md) §15) — and `CHANGELOG.md`. **Known limitations is the
one to write last and honestly**; an empty one is the plugin telling a reader it has not been used
in anger, and the validator rejects it.

Publish in your own repository or point `$SCH_PLUGINS` at a directory. Site plugins override
shipped ones by name, and `doctor` reports when that happens rather than letting a run silently use
code nobody mentioned.

---

## What conversion does not fix

Wrapping a tool does not validate it. If it has never been run on your assay, the plugin inherits
that gap and `cannot_show` must say so. The format makes a tool **composable and honest about its
limits** — it does not make it correct.
