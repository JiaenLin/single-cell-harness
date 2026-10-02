# axes (single-cell)

## What it does
What the data says it is, beside what the stack declares it is. The declaration is the stack's
`profile_context` (`sch init --context species=... --context assay=...`), whose names are the
profile's `axes:`. The measurement reads the feature table through h5py, never the matrix: the
species from Ensembl gene identifiers in any `var` column (decisive at 90% agreement, prefixes
matched longest first), the symbol convention from the index (upper-, title- or lower-case, and
`MT-` against `mt-`) - reported as a convention, never as a species - and the assay as not
measurable, because a count matrix carries no intronic fraction.

## Report surface
A bounded answer: `declared`, `species` (`measured`, `basis`, per-species identifier counts),
`convention` (`reads_as`, counts, what the declared species would write) and `assay`. The gate
`axes_declared` reads it; an agent asks it directly with `sch ask axes`. It travels with: *a
species read from symbol case is a convention, not evidence.*

## Cost
One read of `var`; seconds. It contributes nothing and can be re-run against any view.

## Known limitations
Eight Ensembl species are known by prefix; an object keyed only by symbols is read by convention,
which cannot tell mouse from rat or human from macaque. A multi-species reference (a barnyard
experiment) reads as mixed and measures no species. The assay is never measured: cells and nuclei
differ in their intronic fraction, which lives in the aligner's output, not in the counts.
