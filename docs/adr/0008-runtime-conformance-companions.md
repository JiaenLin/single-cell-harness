# 0008 — Runtime conformance: the invariant companion

**Status** accepted
**Date** 2026-08-20
**Affects** §8 A1 A2 D4 P2 G2

## Context

`ARCHITECTURE.md` §8 splits conformance in two: ten rules `sch doctor --architecture` can check
statically, and A1, A2, D4 and P2 handed to an adversarial suite. That split has a hole in it, and
the roadmap already names it — Phase 10's own risk is that the suite "is run confirmatorily", by
the person who wrote the defence, against the failure modes they thought of. A suite also runs in
CI against fixtures. The four rules it carries are exactly the four that fail silently on the run
that matters: a scratch number quoted into a report, an observation deleted rather than masked.

DeepSeek Harness rc.8 has a third mechanism. `ctx.invariants` is a registry of **package-owned
runtime checks**: the package that owns a relationship ships a companion that asserts it, mounted
beside it, running during every real session, failing with an error bound to the package that
registered it. Publication is exhaustive — a package either registers a real check or ships an
empty installer with a stated reason, and `verify-package-invariants` rejects an unexplained empty
one, a wrong registration name, or an installer that ignores the reporter. Their `dsh-session`
companion asserts the rule we call P2; `dsh-user-approval` asserts that every approval asked has a
decision recorded against it, which is our G2.

The convergence argument of ADR-0001 applies again: they arrived at runtime companions from an
agent loop, we arrive at the same need from `sch doctor`'s residue.

## Decision

A third conformance tier, between the static check and the adversarial suite: the **companion** —
a check owned by whoever owns the relationship, asserted against every real run.

- The kernel provides `service/invariant`. A plugin registers checks against it and receives a
  disposer; a failing check raises, naming the plugin that registered it and the fact that failed.
- **Publication is exhaustive.** Every plugin either ships `invariant.py` or declares
  `no_runtime_invariant:` in its manifest with a reason. `sch plugin validate` rejects an absent
  companion with no declared reason, an empty companion, and a reason that names no relationship.
- A companion asserts a relationship the plugin *owns* and that is observable at runtime. That a
  required field exists, that an entry point is executable, that a pure function returns a fixed
  value — those are validation and test concerns, and a companion that checks them is theatre.
- A companion is subject to the rules every other plugin is: it contributes nothing to the stack,
  nothing it computes is quotable (A2), and it declares its cost.
- The kernel ships the companions for the four rules §8 could not check: **P2** at report render
  (every number resolves to an event in the stream), **D4** at every mount (the observation count
  never decreases), **A2** at promotion (nothing carrying a scratch provenance tag is promoted),
  **A1** at write (no write reaches the dataset outside a declared contribution).
- `sch doctor --runtime` mounts the service with every companion the current stack provides, and
  is the gate a stack passes before it is published.

## Consequences

The suite does not go away, and the division is now clean: **the adversarial suite tests the
defence, the companion asserts the property.** One is written against imagined attacks and proves
the defence holds against those; the other holds during the run a reviewer will later read.

**Given up:** a per-run cost on every plugin, and a new failure mode — a check that is wrong now
fails a run that would have completed, at the least convenient moment. It also invites exactly the
theatre this repository is written against: a companion authored to pass. The counter is Phase 2's
rule, which this record extends to companions — a check only checks if the regression actually
fails it: introduce the regression, watch it fail, revert.
