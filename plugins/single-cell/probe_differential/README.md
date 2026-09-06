# differential (single-cell)

## What it does
For every mask in the subject, the removal rate per arm of the declared design and the ratio of
the largest to the smallest rate. Arms come from the design table joined to the `{sample}`
column of the view's `obs`, read through h5py without loading the matrix.

## Report surface
A bounded answer: rates, counts, ratio, an `inert` flag and its reason. The gate reads it; an
agent may call it directly with `--upto` to reproduce any refusal's number. It travels with: *an
equal rate across arms means not differential, not harmless.*

## Cost
One read of `obs` and one pass over the mask; seconds. It contributes nothing and can always be
re-run against any mounted plugin's view.

## Known limitations
One factor per call, the first non-sample column of the design unless `factor` is passed. It
does not know that a factor is aliased with a batch; a confounded design gives a clean ratio.
When more than a third of observations are removed the ratio test is inert and the answer says so.
