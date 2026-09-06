# 0012 — A pre-release stance for the plugin contract

**Status** proposed
**Date** 2026-08-20
**Affects** X2 X3

## Context

`PLUGIN_FORMAT.md` is marked *v1.0-draft* and its manifests carry `contract: "1.0"`, while X2
promises that fields are only ever added and meanings never change, and X3 that a plugin mounting
on 1.x mounts on any later 1.y. Those promises are live today, and no adapter exists yet. Phase 3
exists *precisely* to discover that the contract is wrong — its falsifier says so: an adapter
thicker than a rewrite means "stop and fix the contract". Phase 5 is where the contract first meets
three tools at once. Between here and there, X2 converts every discovery into a deprecated field
carried forever.

DeepSeek Harness rc.8 takes the opposite stance explicitly, in a section of `AGENTS.md` headed
*"Remove this section at the first tagged release"*: with no external consumers, prefer the correct
foundation over compatibility shims, rename or repackage freely and update every reference
together, backends reject old on-disk formats, and the session format sits at version `0` with no
compatibility promise. They are at `0.1.0-rc.8` and say so on the front page.

## Decision — proposed, not applied

Until Phase 5 closes, the plugin contract carries no compatibility promise. X2's "meanings never
change" and X3's "1.x mounts on 1.y" bind from the version tagged at Phase 5's close. Before then,
a breaking change is a numbered record plus a MAJOR bump of `contract`, no shim is written, and
every plugin in this repository is updated in the same change.

## Consequences

The contract can absorb what Phase 3 and Phase 5 find without accumulating a deprecated field per
finding, which is the state a format is in when it stops being worth building on.

**Given up:** the promise itself, for the length of the pre-release. §7 calls X2 the invariant that
costs the most, and its value is that someone outside can build on the format without reading the
commit log. Deferring it asserts that nobody outside is building on it yet — true today, and the
only person who can say when it stops being true is the author.

**Why this record is proposed and not accepted.** Applying it is an amendment to X2 and X3 and
therefore runs the full §7 procedure against two invariants that are currently load-bearing for
anyone reading `PLUGIN_FORMAT.md` as a promise. The scan that produced ADRs 0008–0011 is not
authority for that; the decision is the author's alone. Nothing in this repository is changed until
this record is accepted.
