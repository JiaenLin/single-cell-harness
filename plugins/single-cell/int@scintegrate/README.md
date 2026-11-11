# int@scintegrate

The adapter that mounts [scIntegrate](https://github.com/JiaenLin/scIntegrate) on a stack: the third
tool of the family the harness runs (W034, after `qc@scqc` and `anno@scanno`).

## What it does
It runs scIntegrate's real command line over the object the stack declares as its observations: the
cohort's joint object, its libraries already in one file, declared as the one part of a parts
manifest. The object is read in place and never copied.

The calls are a stage-3 job's, in this order:
1. `describe`, whose `state_version` must be this adapter's;
2. `doctor`, kept as a record of what the node holds;
3. one `integrate`, with every flag the stage declares, by scIntegrate's own name.

Each runs as `python -m scintegrate.cli <command>` with `PYTHONPATH` set to the declared checkout and
nothing else, as a stage-3 job runs scIntegrate alone. `python` is the interpreter the stack runs this
plugin with.

The result comes back as a **layer** over the observations, never an edit of them. The layer is exactly
what scIntegrate changed, read back from its object against the part by identity (`<part>|<obs name>`):
- every obsm entry the object carries and the part did not, or carries with other values:
  `embeddings/<key>.npy` beside `barcodes.txt`, the profile's binding;
- every obsp entry likewise: `graphs/<key>.npz` (compressed sparse rows, as stored) beside
  `barcodes.txt`;
- every obs column likewise: `columns/<name>.csv`.

An entry the part already carries with the same values is the observation's own and stays out of the
layer, even where scIntegrate copied it (the obs columns it keeps; the uncorrected PCA when it is kept as
delivered). What the object no longer carries, such as the obs columns scIntegrate's slim leaves out, is
recorded as `dropped` and is never removed from the view.

Since scIntegrate 0.6.0, when `--drop-labels` withholds cells that have rows in the part's `X_pca`, the PCA
is refit on the retained cells: `X_pca` is then in the layer as rewritten, NaN on the withheld rows
(`keep_input_pca` keeps the part's). Since 0.7.0 the design's key column travels under the design's own
name, last: the batch column itself when the key is `batch_key` (nothing added), added from the batch
column when the part lacks it, the part's own kept when it equals the batch column. This adapter means
state version 2, which is 0.7.0's.

```console
$ sch init stack --profile single-cell/1.0 --observations joint.tsv \
      --parts h5ad --key sample=part --context assay=snrna --context species=<species>
$ sch mount int@scintegrate --stack stack --param scintegrate=<scIntegrate checkout> \
      --param 'integrate={"batch_key": "<batch column>", "label_key": "<label column>",
               "design": "<design.csv>", "methods": "none,harmony,bbknn", "seed": "0"}'
$ sch unmount int@scintegrate --stack stack --dry-run
```

### Parameters
- `scintegrate` (the checkout holding `scintegrate/cli.py`, used verbatim) and `integrate` are required.
- `integrate` is an object of `scintegrate integrate`'s own flags, written in scIntegrate's parser order
  (0.7.0):
  - a list on `label_sentinel` or `bio_factor` repeats the flag; a list elsewhere is joined with commas;
  - `true` writes a flag that takes no argument, and nothing else does: `coarse_from_path`,
    `keep_input_pca` and `no_fast_leiden`;
  - `false` or `null` leaves the flag out, so it keeps scIntegrate's default;
  - `object_name`, when declared, is a file name ending `.h5ad`.
- A name `integrate` does not have is refused, including `lisi_subsample`, which 0.5.0 removed.

### What the adapter sets itself
- `--h5ad`: the stack's one part, the path its manifest names.
- `--out`: the run, `out/scintegrate/`. scIntegrate's own layout is below it, file for file, and the
  adapter's logs are in `out/scintegrate/logs/`, a directory scIntegrate does not list as a product.
- `--assay` and `--species`: the stack's declaration (`--context`), verbatim.

A parameter naming any of these is refused. Nor can a parameter set one through another flag's value:
a flag that takes no argument takes only `true`, `false` or `null`, a flag that takes a value is never
written bare, and no value begins with `-`, the checkout and the stack's axes included.

### Refused before any compute
- any parameter that breaks the rules above, by name, before any scIntegrate process;
- a stack that declares no assay (rule 2), or no species: scIntegrate requires one and checks it, and
  the adapter holds no default;
- a view with anything masked beneath this mount: scIntegrate reads the object itself;
- a stack of more than one part, since scIntegrate integrates one object;
- after `describe`: a `state_version` that is not this adapter's, and an assay scIntegrate's own
  declaration does not accept.

scIntegrate itself refuses a species the object's gene identifiers contradict, and, before anything is
computed, a design key whose column the object holds with other values and a name the object's writer
forbids (a `/`, `_index`, an empty name); each becomes the mount's refusal, with scIntegrate's words.

### The stage record
scIntegrate's `STATUS.json` and seal are adopted, provided the record names the call's own argv and
its first word is the declared checkout's `cli.py`:
- `ok` and `SEALED.txt`: the layer is read;
- `refused`: the mount is refused with scIntegrate's reason and fix;
- anything else, including no record of the call: the plugin died, and stderr says why.

The object read is the one `objects/*.h5ad` the record lists.

## Report surface
These are recorded as events and are quotable through `sch report`:
- `n_observations`;
- `n_layer_embeddings`, `n_layer_graphs` and `n_layer_columns`;
- `wall_s/describe`, `wall_s/doctor` and `wall_s/integrate`, timed by the adapter around each call.

Each travels with this plugin's `cannot_show`. The first line is the one to keep in mind: *a default
embedding ranked first on chosen weights over chosen metrics; it is not evidence that what it removed
was technical*.

`answer` carries:
- `stage_record`: every call's exit and wall time, and integrate's status, seal, version and commit;
- `argv`: the exact calls, and `pythonpath`, the checkout they ran from;
- `chosen`: the method scIntegrate's benchmark ranked first;
- `layer`: per kind, the entries added, rewritten, unchanged and dropped.

The object and the tables are scIntegrate's, referenced where scIntegrate wrote them under
`out/scintegrate/`.

## Cost
Mounting costs one `integrate`, which is the time and memory scIntegrate's own job takes for the same
flags on the same resources: hours for five methods and the scIB benchmark on a cohort of 10^5 cells.

Around the run, the harness reads the obs, obsm and obsp of the part and of the object (never a matrix
of expression), and writes one file per entry of the layer: on such a cohort, some tens to a few hundred
megabytes of embeddings and graphs.

Unmounting costs nothing to compute. It removes the layer, so the view's digest returns to its
pre-mount value, and it marks invalid every plugin above it, since each one saw the embeddings.
scIntegrate's object is not deleted.

## Known limitations
- **Not yet reproduced at cohort scale.** It has run against a stand-in for scIntegrate's CLI and
  against the real scIntegrate on a synthetic object. The reference cohort's stage-3 run through the
  harness (W034's job) is the first real one.
- **One command of scIntegrate's chain.** `integrate` runs; `assess`, `score` and `report` do not.
- **One object.** The stack's observations are the joint object, as the one part of a manifest. No
  stage driver yet joins an annotation stage's libraries into that object.
- **The stack's keys and design are not read.** Each column is named by scIntegrate's own flag in the
  declaration, and `--design` is the declared file, as anno@scanno takes its references.
- **The cohort axes are spelt as scIntegrate accepts them** (`scrna`, `snrna`); a stack declaring the
  annotation tool's other spelling of an assay is refused here, naming what scIntegrate accepts.
- **A re-mount runs scIntegrate from the beginning.** The kernel clears a run's directory first.
- **scIntegrate is pinned by the checkout the stage names, not by a lock.** The adapter records the
  version and commit scIntegrate reports, and refuses a `state_version` it was not written against.
