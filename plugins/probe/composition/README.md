# composition

## What it does
Counts the values of one column, optionally per group, and reports shares with the denominator
named: the rows kept in the view when the probe ran.

## Report surface
Counts and shares, as an answer. Nothing is merged into the stack. Each share travels with: *a
share is relative to the rows kept when the probe ran.*

## Cost
One pass over the view; seconds even at a million rows. It contributes nothing to the stack and can always be re-run without invalidating anything.

## Known limitations
It reads the view as text, so numeric columns are grouped by their printed form. It does not
test whether two compositions differ; it reports them.
