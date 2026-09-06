# Child conformance — what a tool exposes before an adapter is written

`sch conform <repo>` checks a tool's repository; `sch conform --run <dir>` checks a finished run.
Both print a checklist naming the fix for every failure. This page is the checklist in prose, so
an agent working inside a child knows what to change and can prove it changed — **without the
harness having to reach into the tool** (ADR-0004, ADR-0013).

Nothing here is specific to a project, a cohort or a site. Site strings a scan should refuse live
in a file **outside** the repository (`--terms FILE`, `$SCH_SITE_TERMS`, or
`$SCH_SITE/forbidden_terms.txt`), so the guard never spells what it guards against.

## Repository checks

| id | the tool… | why | fix |
|---|---|---|---|
| **S1** | carries no site or cohort identifier anywhere — not in tests, setup, jobs or docs | a tool validated on one cohort is separated in custody, not validated elsewhere; a leaked name is how a default gets fitted to one dataset | remove or generalise; keep the forbidden list outside the repo |
| S1b | has a leak guard that does not itself spell the site | the guard is in the repo | load terms from an untracked file or an environment variable |
| **S2** | ships a leak-guard test that scans the whole tree | `tests/`, `setup/` and `jobs/` are exactly where cohort names land | a regex ratchet over `git ls-files`, exempting only itself |
| **S3** | requires `--out`; never defaults it; never writes relative to `cwd` or `$HOME` | a tool's default output once put 28 GB inside its own install | refuse rather than default |
| **S4** | runs no compute outside the scheduler in any script it ships | a login-node run is a policy breach and ten times slower | no `nohup`, no trailing `&`, no `--executor local` in scripts; refuse on a login node without `--allow-local` |
| S5 | ships job scripts (if any) that set `-euo pipefail`, a walltime, an EXIT-trap seal that checks products, and no queue name | three hand-written scripts once passed the site validator and could not run | copy the site template; queue and `-o` come from the caller |
| **S6** | has one version string | `CITATION.cff` at 0.3.0 beside `VERSION` at 0.4.0 | one source of truth and a test |
| **S7** | writes a machine-readable status: `ok` · `partial` · `refused` · `died` | a crash and a refusal look the same from stderr | [`STATUS_CONTRACT.md`](STATUS_CONTRACT.md) §1 |
| **S8** | seals its own run: `RUNNING` → `SEALED` or `FAILED`, products listed | seals written only by job scripts leave every other run unsealed | §2 of the same |
| **S9** | records its own commit at runtime, without a git binary | compute nodes have no git; a shell-copied `HEAD.txt` drifts | read `.git/HEAD` by file into the status |
| **S10** | declares `sees`, `cannot_show` and `state_version` | a method that saw the labels beats one that did not, partly for having been told the answer | one declaration block per tool or method |
| S11 | resolves keys from a declaration, never by sniffing column names | `("cluster_FLAG", "scqc_flag", "FLAG")` is the upstream pipeline's vocabulary, i.e. one project's | keys declared in the call or the object; hints may suggest, never decide |
| S12 | records every escape as an ask/decision pair with who and why | a gate with no recorded escapes gets switched off | `{ask:{gate, number, refusal}, decision:{by, why, when}}` |

Bold rows fail the scan; the others warn.

## Run-directory checks

| id | the run… | fix |
|---|---|---|
| R1 | is named by a run key `<UTCSTAMP>__<tool>-<commit>__<stage>[__purpose]` | the submitting script creates it |
| R2 | is sealed, and the seal records exit status and products | tool and job trap both write it |
| R3 | records a commit that matches the run key | `TOOL_HEAD.txt` copied at start |
| R4 | carries a machine-readable status with a status or verdict | `STATUS.json` |
| R5 | keeps its logs inside itself | `-o/-e` and the driver log under `<run>/logs/` |
| R6 | bakes no `/tmp` or foreign home path into its status or report | paths relative to the run |
| R7 | names who and why on every escape | ask/decision pairs |

## The acceptance rule for a change to a child

A change to a child's interface is accepted when all three hold:

1. **its own suite passes and `sch conform` reports no failing row** — no cohort strings anywhere;
2. **a synthetic fixture enters the real CLI path** — a few hundred rows, built in the test, through
   `main()`, asserting the status file, the seal and the products;
3. **a pre-declared reproduction on the reference cohort is identical** — the prediction (which
   identities, which tables, what may legitimately differ and why) is written into the job script
   *before* submission, and the comparison reads the tool's own output layout with no reshaping
   script in between.

The third is a reproduction, not a validation: one cohort cannot validate anything. It proves that
an interface change changed no number.

## What conformance does not fix

A tool that passes every row above can still be wrong. Conformance makes *died*, *refused* and
*partial* distinguishable, makes the commit and the person part of the record, and makes the
leak checkable. It does not make the biology right, and it says nothing about whether the tool's
defaults transfer to a second dataset — that needs a second dataset.
