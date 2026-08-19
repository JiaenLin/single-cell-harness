# 0004 — Orchestrate, do not absorb

**Status** accepted
**Date** 2026-08-19
**Affects** L3 C3

## Context

scQC, scAnno, scIntegrate and scProfile exist, are installed, have their own users and their own
locks. Absorbing them into one repository is a large migration that breaks existing paths and
promoted trees.

## Decision

The harness mounts each through a thin adapter over the CLI and manifest contract it already
has. Each keeps its own repository, lock, version and users.

## Consequences

Nothing built is discarded, adoption is incremental, and each tool stays independently
installable — which is the only honest test of whether the contract is real. An adapter thicker
than a rewrite proves the contract wrong, cheaply and early.

**Given up:** a single coherent codebase, and four chances for a term to change meaning behind
an adapter. The contract has to be versioned and tested or it becomes folklore.
