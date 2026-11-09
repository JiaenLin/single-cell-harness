# anno@scanno

The adapter that mounts [scAnno](https://github.com/JiaenLin/scAnno) on a stack: the second tool of
the family the harness runs (W026, after `qc@scqc`).

## What it does
It runs scAnno's real command line over the cohort the stack declares. The cohort is a parts
manifest: one row per library, each row naming the library's object after QC.

The commands run in scAnno's order, and each one only when the stage declares it:
1. `describe` (always);
2. `cluster` over every library;
3. `annotate` once per library (always);
4. `rescue` over the annotated objects.

Every flag is the stage's, by scAnno's own name.

The labels come back as a **layer**: columns over the observations, never an edit of them. The
layer is exactly what scAnno changed in each library's annotation, read back from scAnno's
objects by identity (`<sample>|<barcode>`):
- every obs column the delivered object carries and the library did not;
- every column the library carried that scAnno rewrote with other values.

A column the library carried unchanged is the observation's own, and stays out of the layer.

```console
$ sch init stack --profile single-cell/1.0 --observations libraries.tsv \
      --parts h5ad --key sample=sample --context assay=snrna
$ sch mount anno@scanno --stack stack --param scanno=<scAnno>/bin/scanno \
      --param 'cluster={"resolutions": "1.0,2.0", "seed": 0}' \
      --param 'annotate={"cluster_key": ["leiden_1p0", "leiden_2p0"], "resolve": true,
               "tree": "<tree.json>", "scope": "<scope.json>", "db": "<corpus.db>",
               "store": "<store.npz>", "species": "<species>", "tissue": "<tissue>"}' \
      --param 'rescue={"label_key": "scanno_resolved_path", "unit_key": "sample",
               "sweep_prefix": "scanno_resolved_path_r", "cluster_prefix": "leiden_"}'
$ sch unmount anno@scanno --stack stack --dry-run
```

### Parameters
- `scanno` (the CLI, used verbatim) and `annotate` are required.
- `cluster`, `annotate` and `rescue` are objects of the command's own flags. They are written in
  scAnno's parser order:
  - a list on `cluster_key` repeats the flag;
  - `true` is a bare flag;
  - an absent flag keeps scAnno's default.
- A name the command does not have is refused.

### What the adapter sets itself
- **Inputs and outputs**, all inside the run, in the layout a stage-2 job gives the same commands:
  - `clustered/`;
  - `annotated/<sample>.ladder.h5ad`;
  - `rescued/`;
  - `rescue/rescue.json`, `rescue/impact.csv` and `rescue/rescue.html`.
- **`annotate --assay`**: the stack's declared assay, verbatim.

A parameter naming any of these is refused.

### Refused before any compute
- a stack that declares no assay (rule 2);
- a view with anything masked beneath this mount;
- two libraries whose objects share a file stem, because `cluster` names its outputs by stem;
- a scAnno whose `state_version` is not this adapter's.

scAnno itself refuses an assay it does not know, and objects annotated under two.

### The stage record
After each call, scAnno's `STATUS.<cmd>.json` and seal are adopted, provided the record names the
call's own argv:
- `ok` and `SEALED`: the chain goes on;
- `refused`: the mount is refused with scAnno's reason and fix;
- anything else, including no record of the call: the plugin died, and stderr says why.

Each annotate call's STATUS is kept as `status/annotate_<sample>.STATUS.json`, because the next
call replaces it.

## Report surface
These are recorded as events and are quotable through `sch report`:
- `n_libraries`, `n_observations_labelled`;
- `n_layer_columns`, `n_columns_added` and `n_columns_rewritten`;
- `wall_s/<call>`, from each STATUS's own `timings`.

Each travels with this plugin's `cannot_show`. The first line is the one to keep in mind: *a label
is the best-supported node of the declared tree, not evidence that the cell type is present*.

`answer` carries:
- `stage_record`: every call's status, seal, exit, version, commit, escapes and wall time;
- `argv`: the exact calls scAnno received;
- `layer`: the columns added, rewritten and dropped.

The objects and tables are scAnno's, referenced where scAnno wrote them under `out/scanno/`.

## Cost
Mounting costs one run of each declared command: the time scAnno's own job takes for the same
commands on the same resources.

Around the run, the harness:
- reads the obs of each library and of its delivered object, never a matrix;
- writes one column file per label column.

Unmounting costs nothing to compute. It removes the columns, so the view's digest returns to its
pre-mount value, and marks invalid every plugin above it, since each one saw the labels. scAnno's
objects are not deleted.

## Known limitations
- **Not yet reproduced at cohort scale.** It has run against a stand-in for scAnno's CLI and against
  the real scAnno on a synthetic cohort. The reference cohort's stage-2 reproduction through the
  harness (W026) is the first real run.
- **Three commands of scAnno's, not all of them.** It runs `cluster`, `annotate` and `rescue`. The
  scope vote (a first annotate, `scope`, then annotate against the vote), `background`, `embed`,
  `report` and `lab` are not run. The vote and the store are references the stage declares.
- **Annotate's own table and report** (`--out`, `--report`) are not written.
- **One stack, one stage.** A view with a removal mounted beneath it is refused. scAnno reads the
  libraries themselves, so the libraries it labels must be the stack's observations. To label a QC
  stage's output, use its deliverable as this stack's observations.
- **A re-mount runs scAnno from the beginning.** The kernel clears a run's directory before running
  it.
- **scAnno is pinned by the checkout the stage names, not by a lock.** The adapter records the
  version and commit scAnno reports, and refuses a `state_version` it was not written against.
