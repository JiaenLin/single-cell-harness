# score

## What it does
Writes `rank_fraction`, the rank of each kept row's `{value}` divided by the number of kept rows.
Rows masked upstream receive no value; the kernel fills them with the profile's missing value.

## Report surface
`median_value` is recorded as an event. It travels with: *a rank is relative to the rows kept at
mount time; unmounting a mask changes every value.*

## Cost
Seconds. Unmounting invalidates anything that read `rank_fraction`. Because it declares
`optional: [mask/*]`, unmounting a mask beneath it invalidates it too.

## Known limitations
Non-numeric values are silently skipped and only counted in a caveat. There is no tie-breaking
beyond shared ranks. It has been run only on the kernel's synthetic fixture.
