# ADR-0028: the report's goals become the project goal, and an autonomous loop works toward them

**Date** 2026-11-09. **Follows** ADR-0027 (the second cohort, in progress; its open items become rows of
the gap register). **Status** accepted by the PI 2026-11-09. **Takes** the number that ADR-0027 had
reserved for the eight held-out plugins. They become waves under GOALS.md test A4.1 rather than a
round of their own.

## Context

The PI's November 2026 report (`report/Single-Cell Harness.pdf`, kept out of the repository because it
carries collaborators' data) sets out what the family is for. Its mission is "autonomous agentic workflow
for unlimited single cell analysis" and "all you need for single cell analysis". Below that it names
seven outcomes and a component for each. The PI's assessment on 2026-11-09 was that "current single cell
harness family is way behind our goals".

Until now the project moved in rounds. Each round was one ADR and one question, and the coordinator
read every line. That produced honest records (ADR-0013 to ADR-0027), but it is serial, and nothing
in it measured distance to a goal. ROADMAP.md orders the work by the cheapest disproof of the
runtime's thesis, and states that "the four tools are not touched". ADR-0013 already broke that rule
for interfaces. The report's goals require development inside all four tools.

## Decision

1. **[`GOALS.md`](../../GOALS.md) is the project goal.** It has four layers: mission, outcomes, capabilities
   and acceptance tests. Layers 0–2 are the report's words. Layer 3 is the coordinator's draft of the
   tests the audit applies. Where ROADMAP.md's ordering conflicts with GOALS.md, GOALS.md wins.
   ARCHITECTURE.md's invariants still bind every change.
2. **[`autodev/`](../../autodev/) runs the loop the PI asked for.** Development teams build registered waves
   in parallel. An audit team verifies each wave and periodically re-grades every acceptance test. The
   loop runs until the audit is HAPPY. A blocker remover clears whatever waits. Housekeeping keeps the
   repositories lean on a timer.
3. **Five core rules govern it** ([`autodev/RULES.md`](../../autodev/RULES.md), tier I):
   1. no overfit, no in-house script, with reproduction as the test;
   2. single cells are not single nuclei;
   3. the HPC rules;
   4. real;
   5. time and efficiency, with no trivial tweaks.

   Rules 3–5 are the VCC development harness's core rules, adopted on the PI's order. Rule 4 is
   translated from "a real trained model" to "a real capability in the tools". The translation is
   the coordinator's, and the PI may correct it.
4. **Audit pass 0001 is the gap review** the PI asked for. Its register seeds `autodev/ledger/gaps.tsv`.

## Consequences

- Progress becomes a number: the share of acceptance tests graded PASS. Every wave must move a goal id.
  Work that moves none is recorded as LEAN and never blocks the verdict.
- Parallel builders replace the coordinator reading every line. Rule 1's gate stands in for that
  reading, together with a verifier that is fresh and not anchored on the builder's account. **What is
  given up** is the single reader who holds the whole family in mind. A defect that crosses repositories
  and that no wave's gate covers can now slip between waves. The full audit pass and the amplifier
  (every defect class checked in all five repositories) exist to catch it. They catch it later than one
  reader would have.
- **ROADMAP.md's "the four tools are not touched" no longer holds** for development toward GOALS.md.
  Adapters still live in the harness where the contract allows it. The phases stay as the runtime's
  internal order.
- Merges into a tool's `main` stay the PI's until the PI grants a standing yes. Until then, a gated wave
  can wait on that answer. That wait is the one blocker the blocker remover cannot clear on its own.
- Rounds as ADRs end for development. ADRs return to their own purpose, which is architectural decisions.
  Waves, audits and blockers are recorded in the ledgers.
