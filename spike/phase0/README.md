# Phase 0 — the disproof

The smallest thing that can falsify the thesis, built before anything else so that a failure costs
days rather than months. See [`../../ROADMAP.md`](../../ROADMAP.md).

```bash
python evaluate.py --n 100000 --g 2000
```

## What it claims

| | pass |
|---|---|
| unmount restores | the view after mount → unmount is identical to before, **by digest** |
| downstream invalidates | unmounting A marks B invalid **without B being consulted** |
| materialisation cost | a 5-deep stack over 100k observations materialises in **< 30 s** warm |
| stack size | the declaration that regenerates the view is **< 1 MB** |
| observations immutable | writing to the observation layer **raises**, rather than succeeding |
| subprocess cost | measured, not claimed — what Phase 1 adds per plugin |

## What it is not

In-process, one hard-coded profile, no manifests, no gates, no report, synthetic data. Phase 1
replaces every line of it.

Two things it deliberately does **not** establish, and neither should be inferred from a pass:

- that materialisation stays cheap at ten times the scale — the job runs 1M observations for that
  reason, and a failure there is a finding rather than an error;
- that any of this survives the subprocess boundary a real plugin needs. That cost is measured
  here so Phase 1 cannot be surprised by it.

## Why these five plugins

Each exercises exactly one property: two masks that must compose rather than overwrite, a plugin
contributing columns, one that **reads** a column so unmounting its input must invalidate it, and
an embedding — the expensive kind of contribution, padded with `NaN` and never `0`, because a
masked observation has no embedding and a zero would sort, average and plot as though it did.

## Findings

**F1 — an immutable layer must be immutable in a *canonical* form.**
The first run failed with `ValueError: WRITEBACKIFCOPY base is read-only` inside `(X > 0)`. scipy
mutates its own internal representation as a side effect of reading: a comparison calls
`sum_duplicates()` → `sort_indices()`, which writes to the data array in place. Freezing an
un-canonical matrix therefore breaks plugins that never intended to write.

The fix is to canonicalise on load and then freeze, which makes the later calls no-ops. The
finding is worth more than the fix: **enforcing D2 naively makes the invariant unusable, and an
unusable invariant gets relaxed.** That is the erosion path `ARCHITECTURE.md` §7 exists to close,
and it was found in the first eight seconds of the first run rather than in an adapter six months
later.
