# filter_threshold

## What it does
Masks every row whose `{value}` column is below a declared floor. The mask is whole — one keep
flag per row — and every removed row is written to a removal record with the criterion that
removed it, so the removal is a mask, never a delete, and it can be unmounted.

## Report surface
`n_removed` and `n_kept` are recorded as events and are the only quotable numbers. Each travels
with the line: *a row passing the floor is one whose value fell above a number, not a row that is
good.* The `removal_record` table lists the identities removed.

## Cost
Runs in seconds on a hundred thousand rows; declared executor cost low. Unmounting invalidates
every plugin that read the mask or a column computed on the kept rows; the differential gate
reports the removal rate per arm before the mount is accepted.

## Known limitations
The floor is a parameter. The plugin derives nothing and will happily apply a floor that removes
every row in one arm and none in another; only the gate stands between that and the report. A
non-numeric value is treated as below the floor, which is a choice, not a fact.
