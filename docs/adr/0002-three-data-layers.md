# 0002 — Three data layers

**Status** accepted
**Date** 2026-08-19
**Affects** D1 D2 D3 D5

## Context

A model claiming every analysis step is reversible would be lying about alignment and ambient
correction, which produce genuinely new numbers rather than a view of existing ones. A reader
who noticed would be right to distrust everything else in the document.

## Decision

Three layers: **observations** immutable, **checkpoints** rebuild-only, **stack** mountable.
Invalidation propagates down to the nearest checkpoint and stops. A plugin unsure which layer it
belongs to declares `checkpoint`.

## Consequences

The thesis survives contact with alignment.

**Given up:** the clean claim that everything is reversible. And a real risk: if most
interesting operations turn out not to be maskable, the stack is thin and this is a checkpoint
graph with an unusual vocabulary.
