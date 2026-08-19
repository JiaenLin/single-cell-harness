# 0007 — Split the generic format from the domain profile

**Status** accepted
**Date** 2026-08-19
**Affects** L2 C3 X2

## Context

The plugin format carried both the generic contract and single-cell vocabulary in one document:
`obs`, `obsm`, `layers`, barcodes, sentinels, cell types. That violates **L2** — the core and the
contract must be testable against a domain they were not designed for — and it made every domain
assumption look like a property of the architecture.

It also hid a real question. `matrix` meaning *observation x feature on the object's own feature
set* is a domain rule with teeth: it is why a result computed on a selected gene set must ship as
an object rather than a padded layer. Buried in a generic document, that rule reads as an
implementation detail.

## Decision

Two documents. `PLUGIN_FORMAT.md` is domain-free: layout, manifest, classes, layer, the capability
**grammar**, effects and disposers, the runtime protocol with **abstract slots**, sourcing, `sees`,
wrapping, environment, validation, compatibility.

`docs/profiles/single-cell.md` binds it: what an observation is, the slot **vocabulary**, the key
map, the identity rule, sentinels, checkpoint kinds, merge rules, the probe library, `stack.yml`
and the on-disk layout.

A plugin declares `profile: single-cell/1.0` in its first three lines. A kernel asked to mount a
plugin under an unknown profile refuses rather than guessing.

## Consequences

The same kernel can host another domain without touching the core, and the generic contract becomes
testable against a fixture that is not single-cell — which is the only real check that L2 holds.
Domain rules are now stated as domain rules, where they can be argued with by people who know the
domain.

**Given up:** one document became two, and a plugin author reads both. A rule in the wrong document
is now a category error rather than a wording problem, and the boundary will be tested by the first
capability that is arguably either — the profile version exists so that argument has somewhere to
be recorded.
