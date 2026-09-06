# 0011 — A disposer reaches quiescence, it does not merely request it

**Status** accepted
**Date** 2026-08-20
**Affects** E1 E3 — adds **E5**

## Context

E1 says every contribution yields a disposer; E3 says disposers run in exactly reverse mount order.
Neither says when a disposer is *finished*. In a single process that is not a question — the
closure returns and the contribution is gone.

It becomes a question at Phase 9. A mounted plugin's work is then a PBS job, and a disposer that
calls `qdel` and returns leaves a job that is still writing into the output directory the kernel
has just declared unmounted. Everything downstream of that moment is built on a race: E4's
mount → snapshot → unmount → compare test compares a digest against something still being written,
and reports a pass.

DeepSeek Harness rc.8 states the rule as a bug class it has already shipped: *"A teardown that
issues kills/aborts but returns before the work stops leaves orphans. Make cleanup async and await
the children's exit (kill → await done), and close listener/notification registries BEFORE killing
so late completions stay silent."* Alongside it, the reason a hurried teardown reports success:
*"a process can time out AND exit 0 because it trapped the signal"* — orthogonal outcomes must be
reported independently, never one nested inside another's branch.

## Decision

**E5 — an unmount is not complete until the work it started has stopped.** A disposer that requests
cancellation and returns is in breach of E1.

- The kernel **closes the plugin's output registration before it signals**, so a late write lands
  nowhere rather than into a stack that has moved on.
- The disposer **awaits termination** and reports the outcome as independent facts — requested,
  stopped, timed out, exit status — never one nested inside another's branch.
- A disposer that **cannot confirm** termination **fails the unmount** and says what is still
  running. It does not report success and leave the confirmation to whoever reads the stack next.

## Consequences

E3's ordering guarantee becomes real across a process boundary: the *n*th disposer starts after the
(*n*+1)th has finished, not after it was asked to.

**Given up:** unmount is no longer instantaneous, and it is no longer infallible — it can now block
behind a scheduler queue, and it can fail. An unmount that hangs is a worse experience than one
that returns immediately, and this record chooses it deliberately: E4's digest comparison, and
every reversibility claim resting on it, is worthless if the thing being compared is still being
written.

Architecture version **1.0 → 1.1** (a new invariant is a MINOR bump, §7).
