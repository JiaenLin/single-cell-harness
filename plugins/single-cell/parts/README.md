# parts

## What it does

The harness's own step (W045, ROUTE R43, GAP-C90). A cohort can arrive as ONE object holding every
library, as public atlases deliver it: the counts in a slot that may not be `X`, stable gene ids as
`var_names`, the gene symbols in a column, and libraries that each pool several donors. The family's
first stage reads libraries, so the driver runs this step as stage `00_parts` whenever a request
declares `object:`. It is a stage like any other: its own stack (a one-row manifest naming the
object, so the view holds identities and never the matrix), the executor, a report with its cost,
a seal.

## What the request declares (nothing is guessed)

| declaration | what it names |
|---|---|
| `observations` | the one `.h5ad` |
| `object.counts` | the slot holding the integer counts: `X`, `raw/X` or `layers/<name>` (csr only) |
| `object.symbols` | the column of that slot's genes (`raw/var` for `raw/X`, else `var`) naming each symbol |
| `object.carry` | further obs columns carried into every part (optional) |
| `object.chunk_values` | the most stored values held at once (optional; default 2^23) |
| `keys.sample` | the obs column naming each library: one part per value |
| `keys.replicate` | the obs column naming the unit the design sheet is keyed on (donor or sample) |
| `parts` | the samplesheet column the step writes each part's path into (the first stage's tool reads it) |

The driver refuses, before any tool, a slot, column or symbol column the object does not hold, by
name. The step refuses a slot holding any stored value that is not a non-negative integer, naming
the first observation and gene, and keeps no part.

## Report surface

What it writes (`out/`, every file read-only), and the numbers its report states (`n_obs`, `n_var`,
`n_stored`, `n_libraries`, `n_replicates`, `libraries_holding_several_replicates`,
`replicates_in_several_libraries`, `n_duplicate_symbols`, `peak_rss_kb`):


- `parts/<library>.h5ad`: `X` the slot's stored values and dtype for that library's rows, unchanged;
  `var_names` the symbols, the stable ids in `var.gene_ids`; obs the object's barcodes in the object's
  order, with the library, replicate and carried columns (categoricals re-coded to the levels present).
- `parts/samplesheet.tsv`: one row per library: `sample` and keys.sample (the library), the `parts`
  column (the part's path), and every context axis - the samplesheet `qc@scqc` mounts.
- `tables/libraries.tsv` (cells, stored values, counts sum, replicates and carried levels per library),
  `tables/replicates.tsv` (cells and libraries per replicate), `tables/duplicate_symbols.tsv`.
- `PARTS.json`: every declaration, the counts, the duplicate rule and each name it wrote, the chunks,
  the step's wall time and its own peak resident memory (`getrusage`).

**Duplicate symbols:** the first gene carrying a symbol, in the object's gene order, keeps it; the
k-th repeat is written `SYMBOL-k`; a written name that is already another gene's symbol is refused.

## Cost

One pass over the slot in chunks; each library's rows are appended to its own file. The step holds
one chunk and, for every cell, its library code, row length, row number and carried obs values: flat
in the stored values, growing with the cells. Measured (W045: 573 MB peak at 20 M stored values, 558 MB
at 80 M, chunks of 2^23 values, where the chunk dominates; wall time linear in the stored values). Per
cell, measured on synthetic objects of the scale cohort's shape (the tests' builder, chunks of 10^6
values), as the step's peak resident memory between two sizes: about 230 bytes per added cell from
50,000 to 200,000 cells (84.6 to 119.2 MB), about 93 bytes from 100,000 to 400,000 cells (148.3 to
176.1 MB; W056's builder and verifier). An inference, not a measurement: at a million cells and more
the per-cell part is some hundreds of MB. The report's `cost` is the executor's, like any stage's;
`PARTS.json` adds the step's own peak resident memory.

## Known limitations

- Only a row-compressed (csr) counts slot streams; a dense or csc slot is refused, not loaded.
- The parts are as large as the slot's stored values (compressed); nothing is subsampled.
- A carried nullable integer or boolean column is refused, not converted.
- An index or a string column is read as anndata writes it: a `string-array`, or the
  `nullable-string-array` group anndata 0.11 onwards writes for pandas 3's strings (its defaults); a
  name the mask marks as missing is refused. A library of more than 250 characters, or two that differ
  only by case, is refused by name before any part is written.
- What the publisher did before publishing (its cell call, its filters) is in every part, unseen.
