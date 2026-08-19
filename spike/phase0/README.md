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

## Results

Measured on a compute node, numpy 2.4.6 / scipy 1.18.0, 1m33s walltime, 4.5 GB peak.

| | 100,000 obs | 1,000,000 obs |
|---|---|---|
| materialise 5-deep stack, warm | **0.01 s** | **0.06 s** |
| materialise + realise the matrix | 0.03 s | 0.13 s |
| stack declaration | 0.3 KB | 0.3 KB |
| unmount restores the view | ✅ digest identical | ✅ digest identical |
| downstream invalidated | ✅ `score`, `embed` | ✅ `score`, `embed` |
| invalidated without re-running | ✅ 0 calls | ✅ 0 calls |
| observation write raises | ✅ | ✅ |
| subprocess round-trip | 29 ms | 28 ms |

Against a 30-second target, materialisation at ten times the claimed scale costs 0.06 s.

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

**F2 — the kernel is free; the plugins are not.**
Materialising a 5-deep stack over a million observations costs 0.06 s, while one plugin in that
stack — a truncated SVD — costs 58 s. The kernel's overhead is three orders of magnitude below the
work it orchestrates.

That reframes what the design buys. It does **not** make analysis cheap. It makes *invalidation*
free, so the only thing that has to be recomputed is what actually became invalid. The value of an
ablation is therefore proportional to how much of the stack it does **not** touch — and the
roadmap's Phase 7 claim, that a fork costs only what was invalidated, is the one that matters
rather than any statement about materialisation speed.

**F3 — "materialise" here means constructing the view, not serialising it.**
The measurement above builds the view and realises the matrix in memory. It does not write an
`.h5ad`, which is I/O-bound and would dominate every number in the table.

That is honest for the thesis — the point of a generated view is that a consumer often needs no
file at all — but it means **the 30-second target was tested against the cheaper half.** A
consumer that does need a file pays a cost this phase did not measure, and Phase 3 must measure it
against a real tool rather than inherit a pass from here.

**F4 — the subprocess boundary is affordable.**
28–29 ms per round-trip, against 58 s of plugin work in the same stack. Phase 1's move to
out-of-process plugins will not be what makes this slow.
