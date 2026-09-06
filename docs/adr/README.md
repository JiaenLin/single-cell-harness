# Decision records

One file per architectural decision. They exist so a future reader can find out **why** something
is the way it is, and so that changing a locked invariant leaves a trace naming what was lost.

```
NNNN-short-title.md
```

Numbered, never renumbered, never deleted. A superseded record is marked superseded and keeps its
number — the reasoning that was once persuasive is the most useful thing in the file.

A record is forward-looking: it argues, and it names what the decision costs. A **post-mortem** is
backward-looking: a defect reached somewhere it should not have, and the interesting part is why
every check missed it. Those live in [`docs/postmortem/`](../postmortem/), and mixing the two loses
both.

A record may also be `proposed` — decided by nobody yet, written down so the argument is available
when it is. Nothing in the repository changes until it is accepted.

## Template

```markdown
# NNNN — Title

**Status** proposed | accepted | superseded by NNNN
**Date** YYYY-MM-DD
**Affects** the invariants this touches, by number (L2, E1, …)

## Context
What forced the decision. What was tried, or what broke.

## Decision
What was decided, stated so it can be checked.

## Consequences
What this makes easy, what it makes hard, and **what property is given up**.
The last one is the reason the file exists.
```
