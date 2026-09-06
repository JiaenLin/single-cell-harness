# differential

## What it does
For every mask in the subject, the removal rate per arm of the declared design and the ratio of
the largest to the smallest rate. Arms come from the `{group}` column if the view carries one,
otherwise from the design table joined on `{unit}`.

## Report surface
The answer is bounded: rates, counts, ratio, an `inert` flag and its reason. A gate reads it; an
agent may call it directly to see what a filter would do before mounting it. Its number travels
with: *an equal rate across arms means not differential, not harmless.*

## Cost
One pass over the mask and the view; seconds. It contributes nothing and can always be re-run.

## Known limitations
It knows one factor: the first non-unit column of the design. A crossed design needs one probe
call per factor. When more than a third of rows are removed the ratio test is inert and the
answer says so; it does not invent a different test.
