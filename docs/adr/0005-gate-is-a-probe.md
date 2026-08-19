# 0005 — A gate is a probe plus a threshold

**Status** accepted
**Date** 2026-08-19
**Affects** G1 G3

## Context

A gate whose measurement the refused party cannot independently reproduce is a black box, and
will be routed around. A probe with no gate behind it is a number nobody acts on.

## Decision

A gate is a probe plus a threshold plus a verdict, and MUST name the probe it measures with.
One implementation, two consumers.

## Consequences

What refuses and what explains cannot drift apart, and an agent can understand a refusal by
running the same instrument that produced it.

**Given up:** gates that would be cheaper to write than their probe, and any gate whose
measurement is genuinely not reusable — that case now costs a probe nobody else calls.
