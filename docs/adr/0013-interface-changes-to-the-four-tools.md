# 0013 — Interface changes to the four tools, proved by reproduction

**Status** accepted
**Date** 2026-09-06
**Affects** ROADMAP "the four tools are not touched"; ADR-0004; Phase 3's adapter test

## Context

`ROADMAP.md` says no commit lands in scQC, scAnno, scIntegrate or scProfile for any phase, and
that where a tool does not expose what an adapter needs, *that is a finding about the contract*.
The rule exists so that Phase 3's test — an adapter thinner than 40 % of a rewrite — measures the
contract and not the amount of tool surgery done to make the adapter thin.

A scan of the four tools on 2026-09-06 found the same six gaps in every one of them, none of
which is about the contract and all of which are about what a run leaves on disk: a refusal that
is prose on stderr, a run the tool never seals, a commit only a shell script records, no `sees`
or `state_version` declaration, escapes logged without the ask, and keys sniffed from column
names that belong to one pipeline. An adapter can work around each of these. Four adapters
working around the same six things is not thinness; it is the same code four times, in the
place where it is least testable.

## Decision

The rule is split.

- **Numbers are not touched.** No commit to a child changes what any run computes for the same
  inputs and parameters. That part of the rule stands, and it is now checkable: every change to a
  child ships with a pre-declared reproduction against the tool's current promoted run on the
  reference cohort, identical by identity and by table, with the prediction written before the run.
- **The interface may be.** A child may gain the things in
  [`docs/CHILD_CONFORMANCE.md`](../CHILD_CONFORMANCE.md): a status file, a self-written seal, a
  recorded commit, declared `sees` / `cannot_show` / `state_version`, escapes as ask/decision pairs,
  keys from declarations, `--out` required, a leak guard over the whole tree. `sch conform` is the
  test that says whether it has them; the harness ships that tool so the child does not have to
  write it.
- **The adapter still consumes the tool's own layout**, unreshaped. Conformance is measured on what
  the tool already writes plus `STATUS.json` and the seal beside it, never on a reshaped copy.

## Consequences

Phase 3's 40 % test now measures the contract alone, because the interface it expects of a tool is
written down once and the same for all four. A child that conforms is a child whose adapter is a
field mapping.

**Given up:** the clean statement "we never touched the tools", and with it the cheapest possible
proof that a discrepancy found in Phase 5 belongs to the harness rather than the tool. The
reproduction requirement is the price paid for that: a number that moves after an interface
change is a defect in the change, found before it is merged, not a mystery found in Phase 5.
Also given up: some independence of the four tools' maintainers, who now share a contract they
did not each write.
