# 0006 — Reads open, writes declared

**Status** accepted
**Date** 2026-08-19
**Affects** A1 A2 A3 E2

## Context

An agent restricted to sequencing existing plugins buys safety by removing most of the value —
sequencing is the easy part of an analysis. But ad-hoc code is not a declared plugin, so on the
face of it none of the guarantees hold.

## Decision

Reads are unconstrained: arbitrary code, any library, against a materialised view. Writes go
only through the contribution API, as a mounted plugin, subject to every gate. Ad-hoc code runs
as a **scratch plugin** — Cordis's temporary in-memory plugin, not a new mechanism — and nothing
in scratch is quotable.

## Consequences

Every guarantee holds **without the agent cooperating**, because the dataset service hands out a
read-only materialisation and no plugin can tell the difference.

**Given up:** the simple claim that everything is a declared plugin. And a standing obligation:
the promotion path must stay light enough that nobody works around it at 11pm, because a rule
that slows someone down under deadline is a rule that gets worked around.
