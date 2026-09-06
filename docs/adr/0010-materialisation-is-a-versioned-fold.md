# 0010 — Materialisation is a fold, and a plugin versions its own semantics

**Status** accepted
**Date** 2026-08-20
**Affects** D1 D3 P3 E1 X2 — adds **D6**

## Context

Phase 0 measured materialisation at 0.06 s over a million observations and recorded two findings
that constrain what comes next. **F2**: the kernel costs three orders of magnitude less than the
work it orchestrates, so what the design buys is free *invalidation*, not fast analysis. **F3**:
the number was measured against view construction, not serialisation, and Phase 3 has to pay the
cost this phase did not measure.

When Phase 3 pays it, the answer is a cache — and a cache needs a key that fails loudly rather
than quietly. Nothing in the format supplies one. A plugin can change what it computes — a new
upstream minor, a corrected formula, a different default — while its `provides`, its `needs` and
its manifest stay byte-identical. Every cached view built on it is then stale and indistinguishable
from fresh. `VISION.md` §19 calls this *adapters rot*: a term quietly changing meaning behind a
contract that did not change.

DeepSeek Harness rc.8 has the shape. A session projection is `{key, schema, init, apply, view,
stateVersion}` — three pure synchronous functions the framework folds over the append-only log,
under four rules: the framework drives and the domain computes; `apply` MUST return the same state
reference for an event that does not concern it, so a non-matching event costs one call and nothing
downstream; a state-carrying event MUST carry the **complete post-change state, never a delta**;
and `stateVersion` is the invalidation anchor of the persisted `(session, key, ver, seq, value)`
cache rows, *"bumped whenever the state shape or the fold semantics change so stale rows are
discarded instead of forward-applied into garbage."*

## Decision

**D6 — materialisation is a fold over the stack, and every cached materialisation is keyed by
declared semantics.**

- The kernel drives the fold; a plugin contributes a **whole value, never a delta**. This is
  already true of every Phase 0 plugin — a mask is a full vector, a column is a full column — and
  D6 forbids the delta optimisation that becomes attractive at cohort scale and would make D3's
  invalidation unsound, because a delta cannot be dropped from the middle of a stack.
- A contribution that does not concern a view costs **one comparison and nothing more**. That is
  what makes D3's "invalidate down to the nearest checkpoint" cheap rather than merely correct.
- Every contributing plugin declares **`state_version`**, an integer, bumped whenever what it
  computes changes for the same inputs and the same parameters. `version` tracks the wrapper;
  `state_version` tracks the numbers. A wrapped tool's version moving is the ordinary reason to
  bump it.
- A cached materialisation is valid only for the exact tuple — observations digest, the ordered
  stack of `(plugin, version, state_version, params)`, profile version. Anything else is a **miss,
  never a partial hit**: a cache that reuses part of a stack it cannot key is the mechanism by
  which a view stops matching its provenance, and P3 says the stack *is* the provenance.

## Consequences

Phase 3 gets a defensible cache instead of an ad-hoc one, and the F3 cost is paid once per changed
tuple rather than per materialisation.

**Given up:** an author can no longer fix a formula quietly. A `state_version` bump invalidates
every cached view standing on it — correct, and sometimes expensive enough to argue about. The
worse case is the opposite: forgetting to bump serves stale numbers that look right. D6 makes that
possible, and the companion from ADR-0008 is what makes it detectable — the kernel records the
tuple with the result, and a re-run producing different numbers under an unchanged tuple raises
instead of overwriting.

Architecture version **1.0 → 1.1** (a new invariant is a MINOR bump, §7).
