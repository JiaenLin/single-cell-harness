# 0001 — Follow Cordis

**Status** accepted
**Date** 2026-08-19
**Affects** L1 L2 C1 C2 E1

## Context

Two independent lines reached the same two properties. Cordis names temporal and spatial
composability as the foundation of a plugin system; this project arrived at the same pair by
writing gates after being burned — a removal checklist and a freshness audit. Cordis is MIT and
published, so it can be read, argued with and ported.

An earlier draft described an architecture of my own invention in my own words. That loses the
convergence: if the two designs cannot be read against each other, the fact that they agree
proves nothing.

## Decision

Follow Cordis by name rather than by paraphrase. `Context`, `Service`, `inject`, effect,
disposer, fork, the typed event bus and the declarative plugin tree are used with their own
names and semantics.

## Consequences

Anyone who knows Cordis can read this design without translating, and the convergence argument
stays checkable.

**Given up:** freedom to shape the core around single-cell convenience, and independence from a
design this project does not control. The open question is how thin the port should be — a
literal port tracks upstream for free and inherits a TypeScript design's assumptions; an
independent implementation of the same model diverges slowly and silently.
