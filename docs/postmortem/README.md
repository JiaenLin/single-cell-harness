# Post-mortems

A decision record says why something is the way it is. A post-mortem says **why the process let a
defect through** — and the two are different enough that mixing them loses both. `docs/adr/` is
forward-looking and argues; this directory is backward-looking and reports.

```
NNNN-short-title.md
```

Numbered, never renumbered, never deleted.

## When to write one

Three conditions, all of them:

- **Subtle** — the mechanism is non-obvious, and a careful person would re-derive it the hard way.
- **Systemic** — the reason it escaped is a gap in the tests, the validator or a convention, not a
  typo. "We forgot" is a finding about the process, not an excuse for skipping the record.
- **Costly to rediscover** — it cost real debugging time and would cost it again.

A defect caught by a check that was doing its job does not need one. A defect that reached a
result, a report or a merged phase does.

The four findings in [`spike/phase0/README.md`](../../spike/phase0/README.md) are the shape of the
prose, and F1 — enforcing D2 naively made the invariant unusable — is the shape of the *finding*: a
post-mortem is worth writing when the interesting part is what the failure says about the design.

## The format

```markdown
# NNNN — Title

**Date** YYYY-MM-DD
**Phase** the roadmap phase it surfaced in
**Invariants** the ones involved, by number

## Executive summary
One paragraph a reader absorbs in thirty seconds: what broke, the mechanism in plain terms, why it
escaped, and the durable lesson.

## What broke
Observable behaviour, and what was believed instead.

## The mechanism
Why it happened. Named parts, in order.

## Why every check missed it
The static check, the validator, the companion, the suite — each one, and why it did not fire.
This is the section the record exists for.

## Guardrails
What was added so this class fails loudly next time, linked: a validator rule, a companion
(ADR-0008), a test, an amended invariant. A post-mortem with no guardrail is an anecdote.
```

Borrowed from DeepSeek Harness's `docs/postmortem/`, including the trigger rule and the
thirty-second summary; the honest reason it is here is that this repository has records for every
decision and none for a failure, and the roadmap is built entirely out of ways to fail.

## Index

| # | Title |
|---|---|
| [0001](0001-a-reproduction-that-was-not-like-for-like.md) | A reproduction that was not like-for-like |
