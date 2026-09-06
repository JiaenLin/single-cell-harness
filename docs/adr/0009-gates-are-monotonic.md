# 0009 — A gate may refuse or abstain, never approve

**Status** accepted
**Date** 2026-08-20
**Affects** G1 G2 G3 — adds **G4**

## Context

G1 says a gate is a plugin, G2 that every escape is logged, G3 that it measures with a probe the
caller can run. None of the three says where a gate sits in the mount path, or what happens when
two gates disagree. As written, a gate is a listener on a waterfall, and a waterfall listener that
returns a value can replace what an earlier one decided — which means the last plugin to run wins,
and the moment a refusal became a pass is recorded nowhere.

`VISION.md` §19 names the failure this produces: *the gates get switched off*. Not by anyone
deciding to switch them off — by whatever runs last.

DeepSeek Harness rc.8 splits tool policy into two stages for this reason. `tools/pre-execute` is a
reorderable waterfall where a listener may allow, deny or ask; `ctx.tools.guard()` registers
**monotonic** guards evaluated after it, and their contract is stated as a negative: *"later
waterfall listeners cannot turn a guard denial back into permission."* A denial there is a result
rather than an exception — it flows on through the pipeline, is logged, and is reported like any
other outcome, so a refused call and a failed call are distinguishable afterwards.

## Decision

**G4 — a gate is monotonic.** It may REFUSE, or abstain; it may not approve.

- `PASS` is the abstention. It means *this gate has nothing to refuse on*, never *this is fine,
  disregard the others*.
- `REVIEW` is an abstention carrying a note that travels to the report. It is not a weak pass.
- The verdict of a set of gates is the strongest refusal any of them returns, so **order does not
  change the outcome.** That is what monotonicity buys: a gate cannot be defeated by re-ordering
  the stack, and there is no last-listener-wins.
- No plugin may convert a refusal into a pass. The only thing that lifts a refusal is the declared
  `escape` (G2), and an escape is a **recorded pair**: the ask — what was refused, by which gate,
  with the probe's number — and the decision — who, when, and why. An escape with no pair recorded
  in the stream is not an escape, and the mount fails. The pairing is asserted by a companion
  (ADR-0008), not left to whoever wrote the gate.
- **A refusal is a result, not an exception.** It is appended to the stream with the number that
  caused it and reported like any other outcome. A gate that raises out of the mount path leaves
  nothing behind to audit.

## Consequences

Gates compose without an ordering rule, and the audit question "when did this stop firing?" has an
answer in the stream rather than in someone's memory of the plugin order.

**Given up:** a gate can no longer vouch. There is a real case for vouching — a removal that is
sample-specific *by design*, where a plugin that knows the design could say so and spare a human
the interruption — and under G4 that case must be handled as an escape with a person's name
against it. That is heavier, and it is the intended cost: the alternative is a plugin able to
approve on a human's behalf, which is the mechanism by which a gate is switched off without anyone
choosing to switch it off.

Architecture version **1.0 → 1.1** (a new invariant is a MINOR bump, §7).
