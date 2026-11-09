# qc@scqc

The adapter that mounts [scQC](https://github.com/JiaenLin/scQC) on a stack: the first tool of the
family the harness runs (W010, ROADMAP Phase 3).

## What it does
Runs scQC's real command line over the cohort the stack declares. That cohort is a parts manifest:
scQC's own samplesheet, one row per library, each row naming the library's object at the floor.
The floor is the denoised object an ambient checkpoint delivered, or the aligner's call on single
cells. The adapter then contributes scQC's decision in the harness's form:
- one whole mask per criterion (`fail_*`, read from scQC's per-cell tables) over every observation;
- the values each criterion was evaluated on, as columns;
- scQC's tables and objects, referenced where scQC wrote them.

```console
$ sch init stack --profile single-cell/1.0 --observations samplesheet.tsv \
      --parts ambient_h5 --key sample=sample --context assay=snrna
$ sch mount qc@scqc --stack stack --param scqc=<scQC>/scqc_cli.py \
      --param registry=registry.tsv --param executor=pbs --param queue=<queue> ...
$ sch unmount qc@scqc --stack stack --dry-run
```

`scqc` and `registry` are required. Every other `--param` is one of scQC's own `run` flags, written
with `_` for `-`, and is forwarded verbatim in scQC's parser order. A flag left out keeps scQC's own
default. A name scQC does not have is refused. `--project` and `--samplesheet` are refused as
parameters: the adapter sets them to the run's `out_dir/scqc` and to the stack's manifest.

These are refused before any compute:
- a samplesheet or library the running user can write. scQC reads them in place, so they are read-only
  before `init` (E2), as delivered data are. The kernel also pins each file's fingerprint at `init`,
  and names any file that changes;
- an assay the stack did not declare (`--context assay=`);
- a library whose own `assay` disagrees with the stack, or any other declared axis the samplesheet
  also carries;
- a scQC whose declared `state_version` is not this adapter's;
- a view with anything already masked beneath it.

After the run, scQC's `STATUS.json` and seal are adopted as they are:
- `ok`, `SEALED.txt` and exit 0: the decision is contributed;
- `refused`: the mount is refused with scQC's reason and fix;
- anything else (`failed`, `partial`, a missing seal): the plugin died, and stderr quotes scQC's
  record.

## Report surface
These are recorded as events and are quotable through `sch report`:
- `n_observations`, `n_kept` and `n_removed`;
- `n_fired/<criterion>` for each criterion. These overlap: one observation can fail several.

Each travels with this plugin's `cannot_show`. The first line is the one to keep in mind: *an
observation passing QC is not an observation that is intact*.

`answer.stage_record` names scQC's results directory, digest, status, seal, version, commit,
`state_version` and escapes. `answer.argv` is the exact call scQC received. scQC's own report
(`reports/qc_report.html`) and its tables, including `removal_ledger.csv`, are under that results
directory, in scQC's layout.

## Cost
Mounting costs one scQC run: on a ten-library nucleus cohort, about the hours scQC's own job takes,
with its tasks sent to the scheduler by scQC's `--executor pbs`. Around it, the harness reads each
part's barcodes and digests every part. It writes an identity-level view (no matrix), one mask per
criterion and the measured columns.

Unmounting costs nothing to compute. It removes the masks and columns, restores every observation
(the digest of the view returns to its pre-mount value), and marks invalid every plugin above it,
since each one saw the filtered view. scQC's results directory is not deleted.

## Known limitations
- **Not tested at cohort scale.** It has run only on a synthetic cohort, against a stand-in for
  scQC's CLI. The first real run is the reference cohort's stage-1 reproduction (W010).
- **The ambient step is not a mount yet.** Ambient correction is a checkpoint (D1). This adapter
  takes the floor as delivered and does not run it. If scQC denoised a library inside the mount,
  its per-cell universe would no longer be the observations, and the kernel refuses that mount
  with both counts. An `ambient@scqc` checkpoint needs an ambient-only entry in scQC's CLI.
- **Single cells are not readable as parts yet.** On single cells, scQC tabulates the aligner's
  called cells, so their parts would be the called-cell matrix. The kernel reads parts only as
  `.h5ad`; a 10x `.h5` or MEX part is refused with that reason.
- **scQC is pinned by the checkout the stage names, not by a lock.** The adapter records the
  version and commit scQC reports, and refuses a `state_version` it was not written against. A
  checkout swapped under a running job is the stage's problem, not something this adapter can see.
- **A re-mount runs scQC from the beginning.** The kernel clears a run's directory before running
  it, so scQC's own resume of completed tasks is not used.
