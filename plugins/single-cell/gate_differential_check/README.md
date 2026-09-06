# differential_check (single-cell)

## What it does
Reads the `differential` probe's answer and refuses a mount when a mask's removal rate differs
by three times or more between the extreme arms of the design; reviews at two times, or when
the probe says the test is inert. It never measures: the number is the probe's.

## Report surface
The verdict, the ratio and the reason, recorded as a gate result event. An escape is recorded
as an ask and a decision pair with who lifted it and why.

## Cost
One probe run per guarded mount. Nothing to unmount.

## Known limitations
One factor at a time, and only the extreme arms. Thresholds are parameters; the 3x line is a
convention borrowed from one project's rule, not a derived quantity, and is printed as such.
