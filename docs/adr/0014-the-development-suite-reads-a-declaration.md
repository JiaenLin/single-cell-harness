# 0014 — The development suite reads a declaration; it does not know the tools

**Status** accepted
**Date** 2026-09-06
**Affects** `sch dev`; `DEVPOINTS.yaml` in all five repositories; ADR-0007

## Context

The family is extended by agents, and the same four failures recur.

**Five repositories extend in five ways.** scProfile loads a kernel directory carrying
`kernel.yml`, or a `kernels/<name>.py` carrying a `PLUGIN` dict. scIntegrate adds one key to
`METHODS` and another to `SEES`. scQC adds one to `CRITERIA` and one to `GATES`. scAnno has no
registry and wires functions in its CLI. The harness validates a `plugin.yml` against a profile.
An agent's first half hour on any of them is spent finding where the new thing goes.

**Overfitting is the default.** Every tool was built against one cohort. A tool built against
one cohort learns its column names, and no test catches that, because the only dataset the tests
have is the one the assumptions came from.

**Proof was expensive, so it was deferred.** The only honest proof of a change was a cluster run
against the real cohort. Changes therefore arrived at the queue carrying several defects at once,
most of which a laptop could have found in seconds.

**Rules without mechanisms are predictions.** "Never pull into a tool checkout while a run uses
it" was written down and then broken twice in one afternoon by its author.

The obvious design is a suite that knows the tools: a `--kernel` mode for scProfile, a `--method`
mode for scIntegrate, and so on. It is obvious, it is smaller to write, and it is wrong for the
same reason ADR-0007 split the plugin format from the single-cell profile.

## Decision

**`sch dev` names no tool, no kernel, no method and no criterion.** Each repository declares its
extension points in `DEVPOINTS.yaml`; every command reads the declaration. Adding a sixth
repository, or a second point to an existing one, is a file rather than a change to the suite.

Three consequences are deliberate, not incidental.

**Declaring a point is how it becomes checkable.** The suite can only verify what the
declaration describes, so a point missing from `DEVPOINTS.yaml` is a point nothing verifies. The
declaration is therefore load-bearing rather than documentary, and every point is required to
state what a green check `proves` and what it `cannot_prove`.

**Registration is checked by parsing, never written.** A scaffolder that text-edits a Python
literal is guessing at the file's layout, and one that half-registers something creates a defect
that looks like a typo. `sch dev new` prints the edit; `sch dev check` reads the file with `ast`
to see whether it landed. A registry built inside a comprehension is reported as *unreadable*,
not as empty — "I cannot see it" and "it is not there" are different answers, and reporting the
second when you mean the first is how a check stops meaning anything.

**The fixture is one cohort under two sets of names.** Identical counts, identical embedding,
every role renamed. Code that resolves a role passes both; code that knows a name passes one.
Overfitting becomes a test failure rather than a reviewer's opinion.

## Consequences

**Easier.** An agent's first command on any repository is `sch dev map`, and it answers where the
new thing goes, what it must declare, and what proving it will cost. A change that was previously
provable only on the cluster is now provable in seconds up to a stated limit, and the limit is
printed rather than assumed. The five failures that cost cluster hours in September 2026 are
enforced by the emitted job rather than remembered.

**Harder.** Every point must be declared before it can be checked, and a declaration that is
wrong produces a check that is confidently wrong — the suite trusts `DEVPOINTS.yaml` completely.
Fixture commands live in a manifest rather than in the tool, so a tool whose CLI changes will
have a stale fixture command until someone runs the ladder. And the suite cannot check anything
a repository declines to declare, which makes an undeclared point invisible rather than merely
unchecked.

**Given up: the suite cannot give tool-specific advice.** It cannot tell you that your
scIntegrate method should pad withheld cells with NaN, or that a scProfile kernel must never name
another kernel, because it does not know what a method or a kernel is. Those statements live in
each point's `proves`, `cannot_prove` and `must_declare` fields, written by whoever maintains the
tool — which means a tool whose declaration is thin gets thin guidance, and the suite will not
notice. A tool-aware suite would have caught that; this one cannot, and the price is paid in
every repository where the declaration is not kept honest.

**Also given up: a green ladder is weaker than it feels.** Six tiers pass in seconds on synthetic
data, and the temptation is to read that as a merge. Every tier therefore prints what it does not
prove, and the run ends by saying that only a reproduction against the real cohort establishes
the thing anyone actually cares about. That is a mitigation, not a fix; the risk is structural to
having a fast check at all.
