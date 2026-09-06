"""single-cell-harness kernel — `sch`.

Layers, from ARCHITECTURE.md §1, enforced by `sch doctor --architecture`:

    sch.core       L1  Context · Service · effect / disposer · event bus.   Knows nothing.
    sch.registry   L2  manifest → Runtime; lifecycle; the materialisation fold.
    sch.services   L3  dataset · executor · provenance · gate · probe · invariant · report.
    plugins/       L4  directories the kernel never imports.

The domain lives in `sch/profile/*.yml` and in plugins. Nothing under `sch.core` or
`sch.registry` names a cell, a gene or an assay (L2).
"""
__version__ = "0.1.0"
CONTRACT = "1.0"
