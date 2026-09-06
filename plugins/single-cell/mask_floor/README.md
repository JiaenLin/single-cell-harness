# mask_floor

## What it does
Masks every observation whose total over the `{counts}` layer is below a declared floor. The
mask is whole — one keep flag per observation, merged by identity — and every removed
observation is written to a removal record with the criterion, so the removal is a mask, never a
delete, and can be unmounted with everything above it knowing.

## Report surface
`n_removed` and `n_kept` are recorded as events. Each travels with: *an observation passing the
floor is one whose total fell above a number, not one that is intact.* The removal record lists
the identities removed and their totals.

## Cost
One pass over the counts layer; minutes at a hundred thousand observations, dominated by reading
the object. Unmounting invalidates every plugin above it, since every one of them saw the
filtered view; the differential gate measures the removal rate per arm before the mount is
accepted.

## Known limitations
The floor is a parameter. Nothing here derives it, and a floor above the depth valley of most
libraries removes real observations and calls it quality; the reference tool derives the valley
per library and this plugin does not. It has been run only on synthetic objects.
