# prof@scprofile

The adapter that mounts [scProfile](https://github.com/JiaenLin/scProfile) on a stack: the fourth tool of
the family the harness runs (W036, after `qc@scqc`, `anno@scanno` and `int@scintegrate`).

## What it does
It runs scProfile's real command line over the object the stack declares as its observations: the
cohort's integrated object, declared as the one part of a parts manifest. The object is read in place
and never copied.

The calls are a stage-4 job's, in this order:
1. `doctor`, told the run's own `--prefix` and `--references`, kept as a record of what the node holds
   (its exit code is about every plugin scProfile knows, not this run, so it is recorded, not fatal);
2. one `run`, with every flag the stage declares, by scProfile's own name.

Each runs as `python -m scprofile.cli <command>` with `PYTHONPATH` set to the declared checkout and
nothing else, cwd the run, as a stage-4 job runs scProfile alone. `python` is the interpreter the stack
runs this plugin with.

**Which plugins run is scProfile's.** `--kernel` (or `--all`) is the stage's flag, passed through; the
design admits what scProfile's own plan admits. A plugin the plan skipped is named in a caveat with
scProfile's reason, and listed in the answer (`skipped`). The adapter adds none and drops none.

The result comes back as a **layer**, never an edit of the observations:
- every `.csv` table scProfile's record lists under `tables/` or `kernels/<plugin>/.../tables/`,
  referenced where it lies (differential expression and abundance are per population and per contrast,
  so they are tables, and the view over the observations does not move when they mount);
- the object scProfile wrote (`objects/<name>.h5ad`, the input plus its provenance), referenced where it
  lies, a contribution `object/<name>`;
- exactly what scProfile's own record (`report.json` `merged`) says it merged into that object, read back
  by identity (`<part>|<obs name>`): obs columns as `columns/<name>.csv`, obsm entries as
  `embeddings/<key>.npy` beside `barcodes.txt`. One the part already carried with the same values is the
  observation's own and is not in the layer.

### Parameters
- `scprofile`: the checkout holding the `scprofile` package (the directory with `scprofile/cli.py`).
  Required; no default.
- `run`: an object of `scprofile run`'s own flags, by scProfile's names with `-` written `_`. Required.
  A list on `control`, `covariate` or `factor` repeats the flag; a list elsewhere is written
  comma-separated. `true` writes a bare flag, and only on `no_cache`, `resume`, `force_all`, `all`,
  `no_validate` and `force`; `false` or `null` leaves the flag out. No value may begin with `-`.
- `timeout`: the kernel's, not scProfile's (scProfile's own is `run.timeout`).

### What the adapter sets itself
- `--h5ad`: the stack's one part, in place.
- `--out`: `<out_dir>/scprofile`, the run.
- `--design`: the stack's design sheet (`sch init --design`), in place; none declared, none passed.
- `--assay`: the stack's `--context assay=`, in scProfile's words: `scrna` is written `cell` and `snrna`
  `nucleus` (scProfile's own reader equates them). Passed verbatim, `snrna` would reach scProfile as an
  unrecognised word and switch off every assay-specific caveat without a word.
- `--organism`: the stack's `--context organism=`, verbatim. Undeclared, it is not passed, scProfile
  infers it as it documents, and a caveat says so.

A parameter naming any of these is refused by name.

### Refused before any compute
No declared assay, or one outside `scrna`/`snrna` (rule 2); an unknown parameter or flag; an owned flag;
a value of the wrong kind for its flag; a value beginning with `-`; an `object_name` that is not a file
name ending `.h5ad`; a checkout with no `scprofile/cli.py`; a stack whose observations are not one part
of a manifest, or are masked beneath this mount; a part that is not an `.h5ad`; a design sheet that is
not a file.

### The stage record
scProfile's own `STATUS.json` is adopted only when it names this call's argv and the declared checkout's
`cli.py`. `ok` with `SEALED.txt`, exit 0 and no `RUNNING.txt` goes on; `refused` with exit 2 is the
mount's refusal, with scProfile's reason and fix; anything else is a death quoting scProfile's headline.
A `state_version` other than this adapter's in `STATUS.json` or `report.json` refuses the mount (D6).

## Report surface
- numbers: `n_observations`, `n_plugins_ran`, `n_plugins_skipped`, `n_tables`, `n_layer_columns`,
  `n_layer_embeddings`, `wall_s/doctor`, `wall_s/run`;
- answer: the stage record, every argv, the PYTHONPATH, the assay as declared and as written, the
  organism, the design, the plugins that ran and those skipped with scProfile's reasons, what it merged,
  the tables, the layer;
- caveats: each skipped plugin; a merged matrix layer that is in the object and not carried; an
  undeclared organism.

## Cost
`executor: {cost: high}`. The run is scProfile's (its plugins in their own environments, under
`--prefix`); the adapter adds the reading of the object's index and of what scProfile merged.

## Known limitations
- A matrix scProfile merges into `layers` stays in the object this mount references; it is named, not
  carried as a `matrix/*` contribution.
- Tables are referenced in the plugin's record, not kernel contributions: the kernel registers objects,
  columns, embeddings, graphs, matrices and masks, so a downstream plugin cannot yet need a table.
- The stack's keys are not read: the label, sample and batch columns are `run`'s flags in the
  declaration (as `int@scintegrate`'s are), because a parts stack's `sample` key names the manifest's
  part column, not the object's.
- Run 1 of W036 grades `de` and `abundance`; the other plugins the design admits go through the same
  call (`kernel` or `all`) and are graded by a later job.
