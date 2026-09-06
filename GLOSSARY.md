# Glossary

Terms used precisely in `VISION.md` and `ARCHITECTURE.md`. Written because most of them already
mean something looser in everyday use, and the argument depends on the narrow meanings.

**kernel** — the runtime core: the one component that mounts, unmounts, resolves the dependency
graph and holds the event stream. There is exactly one. Everything else is a plugin.

**plugin** — a directory carrying a manifest and an entry point, mounted on the kernel. The unit of
extension for every part of the system: methods, executors, storage, gates, reports. Specified in
[PLUGIN_FORMAT.md](PLUGIN_FORMAT.md).

**observations** — the reads as delivered by an instrument. Immutable, never regenerated. The
provenance boundary between what was measured and what was computed lives here; once lost it cannot
be reconstructed.

**checkpoint** — an operation that produces genuinely new numbers rather than a view of existing
ones: alignment, ambient correction. It cannot be unmounted, only rebuilt from. Invalidation
propagates down to the nearest checkpoint and stops. Being explicit about these is what stops the
thesis being a fantasy.

**stack** — the ordered set of mounted decisions above the last checkpoint. This is the artifact.
Everything else is derived from it.

**mount / unmount** — to add a decision to the stack, or remove it. Unmounting calls the plugin's
disposer and reverts its contribution everywhere, including in every downstream view.

**disposer** — the value a plugin returns when it contributes something. Calling it undoes exactly
that contribution. Borrowed from Cordis; it is the mechanism that makes reversibility structural
rather than aspirational, because a plugin cannot register an effect without producing the undo.

**quiescence** — the state a disposer must reach before it returns: the work its plugin started has
*stopped*, not merely been asked to. The distinction is invisible in one process and decides
whether an unmount is real once the work is a job on a scheduler.

**view** — a materialisation of the stack: an `.h5ad`, a figure, a table, a report. Generated on
demand, never authoritative. A view is to a stack what a rendered page is to its source.

**state_version** — an integer a plugin declares, versioning *what it computes* rather than what it
is. `version` moves when the wrapper changes; `state_version` moves when the numbers would. Every
cached materialisation is keyed on it, so it is the difference between a stale view that raises and
one that quietly agrees with its own provenance.

**capability** — what a plugin declares it `needs` and `provides`, expressed as a contract rather
than an implementation. "Something that provides an embedding", not "harmony". Swapping the
implementation must not require touching the consumer.

**reactive invalidation** — the runtime marking every dependent artifact invalid the moment
anything upstream changes. The opposite of a freshness audit, which asks after the fact and can
only be run by someone who remembers to.

**gate** — a plugin that can refuse an operation. Gates are listed, audited and reported, and every
escape is logged. A gate hard-coded in a script is a gate nobody knows fired; a gate with no escape
gets switched off; a gate whose escapes are all recorded does not.

**monotonic** — of a gate: it may refuse or abstain, never approve. Refusals therefore accumulate
and cannot be cancelled by another plugin, and the verdict of a set of gates does not depend on
their order. The alternative — a gate able to vouch — is how a gate gets switched off without
anyone deciding to switch it off.

**invariant companion** — a runtime check shipped by the plugin that owns the relationship it
asserts, mounted beside it and run against real work. Distinct from the validator, which runs
without running anything, and from the adversarial suite, which runs against fixtures: *the suite
tests the defence, the companion asserts the property.* Borrowed from DeepSeek Harness, where every
package publishes one or states why it has none.

**sentinel** — a label meaning *the annotator declined to call this cell*, not a cell type. Sentinel
cells are never dropped, and never counted as a population.

**differential effect** — the rate at which an operation removes or alters data, measured *per arm
of the design*. A filter taking 53% of one sample and 6% of another has converted a technical
property into an apparent biological difference, and nothing downstream can undo it.

**cannot_show** — a required field on every plugin: what its output does *not* establish. Printed
beside the result, because a result whose limits were never written down reads exactly as
authoritative as one whose limits were thought about.

**report-visible ⟺ replayable** — the invariant that every number in a report must be
reconstructible from the event stream. Adapted from DeepSeek Harness's *model-visible ⟺ logged*.

**executor** — a plugin that decides where work physically runs: local, PBS, SLURM, cloud. Where
compute happens is not part of what the analysis *is*, which is why it is swappable.
