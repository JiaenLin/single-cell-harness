# 0003 — The declaration is the disposer

**Status** accepted
**Date** 2026-08-19
**Affects** E1 E2 E4

## Context

Cordis makes reversibility structural because `register()` returns a closure. A plugin running
as a subprocess — which is what lets it pin numpy 1.26 against a 2.4 host, and what lets it be
written in R — cannot return a closure.

## Decision

The declaration **is** the disposer. A plugin states precisely what it contributed and the
kernel synthesises the undo from it. `provides` is therefore enforced rather than documented,
and `reversible: true` is tested at mount by mount → snapshot → unmount → compare.

## Consequences

Reversibility crosses a process boundary, so a plugin can hold any versions it likes.

**Given up:** exactness now rests on a declaration rather than on code. An undeclared write is
unreversible, which is why undeclared output is reported at every level rather than tolerated —
and why the mount-time test exists, so a false claim is caught when nothing depends on it.
