# regenerate

## What it does
Writes a column of pseudo-random values from a seed. It exists to exercise the checkpoint layer:
it produces numbers that are not a function of anything above it, so it declares
`layer: checkpoint` and `rebuild_from`, and the kernel refuses to unmount it.

## Report surface
Nothing quotable. It records no numbers; the column is data for plugins above it.

## Cost
Negligible to run. It cannot be unmounted: removing it is a rebuild of everything above it,
which is the cost of being a checkpoint and the reason to declare one when in doubt.

## Known limitations
It is a stand-in. A real checkpoint — alignment, ambient correction — costs hours and its
rebuild_from lists real inputs; this one lists a seed and proves only the kernel's behaviour.
