# The status contract — what every run leaves behind

Every tool the harness orchestrates, and every plugin the kernel runs, ends in one of four states
that must be distinguishable **from the filesystem alone**, by a reader who did not watch the run:

| state | means | what is on disk |
|---|---|---|
| `ok` | it ran and produced what it declared | `STATUS.json` with `status: ok`, `SEALED.txt` |
| `partial` | it ran and produced some of what it declared, and says which | `STATUS.json` with `status: partial` and `absent[]`, `SEALED.txt` |
| `refused` | it declined to run, and named the fix | `STATUS.json` with `status: refused` and `refusal{reason, fix}`, `FAILED.txt` |
| `died` | it stopped without saying anything | **no** `STATUS.json` beyond the initial `partial` stub, `FAILED.txt` or no seal at all |

A host that globbed the output directory would collapse `died` and `partial`, and those are
opposite facts. That is why the contract is three files, not a glob.

## 1. `STATUS.json`

Written **first**, as soon as the run has a directory, with `status: partial` and no products — so
a crash leaves a file that says *partial*, not silence — and rewritten **last**.

```json
{
  "contract": "1.0",
  "tool": "scqc", "version": "0.4.0", "commit": "51dc1a429f88",
  "state_version": 3,
  "status": "ok",
  "headline": "masked 6,851 of 39,037 observations on six criteria",
  "started": "2026-09-06T08:41:12Z", "finished": "2026-09-06T09:09:40Z",
  "job": {"scheduler": "pbs", "id": "684955", "host": "compute1006"},
  "inputs":   [{"path": "objects/cohort.h5ad", "sha256": "…", "relative_to": "run"}],
  "products": [{"path": "tables/masks.csv", "sha256": "…"}, {"path": "reports/report.json", "sha256": "…"}],
  "absent":   [{"what": "latent_time", "why": "only the dynamical mode fits it"}],
  "refusal":  null,
  "sees":     ["design"],
  "escapes":  [{"ask": {"gate": "differential_check", "number": 3.4, "refused": "…"},
                "decision": {"by": "a person", "why": "…", "when": "…", "flag": "--escape differential_check"}}],
  "cannot_show": ["…"],
  "wrapped_versions": {"scanpy": "1.10.2"}
}
```

Rules:

- **`commit` is read by the tool** from `.git/HEAD` (and `packed-refs`) as files, never by running
  `git`: compute nodes have none, and a run keyed on a commit the tool did not record is a run
  keyed on a guess.
- **Paths are relative to the run directory** so it can be moved or hard-linked without every
  manifest inside it becoming a lie. An absolute path in `STATUS.json` is a finding `sch conform`
  reports.
- **`refusal.fix` is required when `status` is `refused`.** A refusal naming the fix is a good
  outcome; a refusal without one is an error message.
- **`sees` is a positive claim.** An empty list means *this tool was shown nothing beyond the data*;
  it is not an omission.
- **An escape is a pair.** An ask without a decision, or a decision without a person, is not an
  escape and the run is not `ok`.

## 2. `RUNNING.txt` → `SEALED.txt` | `FAILED.txt`

Written **by the tool**, not only by the job script. The job's exit trap is the second witness,
never the only one, because a run launched any other way is otherwise unsealed — and unsealed
runs accumulate.

```
exit=0
jobid=684955
commit=51dc1a429f88
started=2026-09-06T08:41:12Z
finished=2026-09-06T09:09:40Z
host=compute1006
products=tables/masks.csv reports/report.json
```

`FAILED.txt` carries the same lines plus `missing=` naming every declared product that is absent
or empty. **A seal checks the products, not just the exit status**: a job whose report step died
still reaches its trap, and a trap reading only `$?` writes a green seal on a run with no report.

## 3. The plugin protocol is the same contract in miniature

Inside the harness, `out.json` **is** `STATUS.json` for one plugin run: `status` ∈ `ok | partial
| refused`, `absent[]`, `answer.refusal{reason, fix}`, `wrapped_versions`, and the three
distinguishable outcomes (no file · empty file · entries). A child tool that writes `STATUS.json`
as above needs no translation to become a plugin; the adapter copies the fields.

## 4. The numeric environment, and why it belongs here

**Proposed, not yet required.** A run should record the environment its arithmetic happened in:

```json
"environment": {
  "threads": {"OMP_NUM_THREADS": "24", "MKL_NUM_THREADS": "24", "torch": 24},
  "imported": ["numpy 2.4.6", "scipy 1.18.0", "torch 2.13.0", "harmonypy 0.0.10"],
  "host": "compute1007", "cpu": "..."
}
```

The reason is a real diagnosis that the records could not support. Two runs of one tool, with a
bit-identical input, identical recorded parameters, identical wrapped versions and a method that
seeds itself, produced embeddings differing by 0.06 on a scale of 16.7 — and the only way to find
out why was to read the wrapped library's source and submit two probes. `wrapped_versions` was
identical in both; what differed was **which packages had been imported before the method ran**,
and therefore what threading and which OpenMP runtime were in force.

A version is not an environment. Two processes running the same versions compute different
floating-point results when their thread pools differ, and an iterative method amplifies that.
Recording the environment turns *why did this number move* from a source read into a diff, and
`sch conform --against` can then compare it the way it compares parameters.

## 5. What this contract does not do

It does not make a run correct. It makes *died*, *refused* and *partial* three different facts, and
it makes the commit, the person and the fix part of the record rather than part of the memory
of whoever ran it.
