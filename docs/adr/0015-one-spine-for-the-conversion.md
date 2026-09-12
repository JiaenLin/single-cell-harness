# 0015 — One spine: the run-side properties of a plugin are test-phase stages of its conversion

**Status** accepted
**Date** 2026-09-12
**Affects** ADR-0014 (`sch dev` reads a declaration); scProfile's `DEVPOINTS.yaml` and its
development guideline; the plugin-maker round rules (`rules:`)

## Context

A plugin-maker round on scProfile ended with four instruments each reporting its own definition
of done about the same commit, all true at once:

| instrument | done means | said |
|---|---|---|
| `sch dev convert status` | every declared stage filled | build complete |
| `sch dev check` | eight tiers green on the fixture | 0 failing |
| `sch dev rules` | the round's four rules hold | 4 held |
| `tests/loop_stations.py` (scProfile) | every figure kind looked at, a result written | BLOCKED at 6b, eye 0 of 149 |

DEVELOPMENT.md is unambiguous that only the fourth is the goal, and the fourth is the only one
the maker could not see. Every defect the round's audit found was a seam between two of these:
rules held while the loop was blocked; `build: 7 of 7 complete` printed over eight required keys
no stage mentioned; the guideline enforced by a hook keyed to the session's root directory while
the round's own rule 1 forced the work to be done from the other repository.

Two more facts were measured while writing this record and had not been measured before.

**Two draw protocols, one audit.** A panel a plugin draws in Python passes through
`emit_figure`: ceiling, caption, `figure.audit`, and a manifest record carrying the audit. A
panel drawn by the wrapped tool in R passes through the generated `.draw_one`: ceiling and
caption, no audit, and no record — the reporter globs it off disk later. Station 6b reads the
manifest, so its "43 issues" is a statement about the ten matplotlib kinds; from the declaration,
about four panels in five have never been measured by a machine, and the station's silence on
them read as clean.

**The declaration has no truth column.** `must_declare` lists seventeen keys; `coverage()`
prints which stage fills each. "Unowned" collapsed four honest states — an input, a key the
validator checks, a key measured from a run, a key nobody checks — into one line, and `cores`
and `cost` sat in the fourth with the scaffold template itself asking for the check.

## Decision

**The loop's run-side stations become test-phase stages of the conversion, invoked as the
loop's own commands.** `measure` and `promised` already have the shape — a `phase: test` stage
with a `command:` reading `{run}`. Four more of the same shape are declared: `audited`,
`looked_at`, `written`, `delivered`, each whose command is `tests/loop_stations.py --run {run}
--station N --json`. One implementation, two callers; the maker learns nothing about a run
directory. `sch dev convert status --run RUNDIR` executes every command stage and reports its
verdict beside the build stages. Two oracles remain, with a stated boundary: *convert* asks
whether the plugin is finished as a plugin; *agenda* asks whether a run is finished as a run.

**Station 6b counts what it did not measure.** Panels on disk that carry no audit record are
reported as *drawn and not measured by any machine*, on the PASS line and the BLOCKED line
alike. The fuller form — the generated R protocol writing the same manifest record `emit_figure`
writes — is deferred, and the cost that defers it is recorded here: the reporter renders
manifest records and globbed native panels as two lists, so a record for a native panel renders
twice until the reporter is changed, and the licence layer enumerates products from the
manifest, so adoption would change shape. Counting from disk closes the silence now; the record
can follow when the reporter is next opened.

**`must_declare` gains a truth column.** A point may declare `truth:` — for each required key,
`input` (the conversion's input, never its output), `validator` (checked by the repository's
own validator), or `measured` (read back from a run by a named command). A key filled by a stage
needs no entry. A key with no stage and no entry is `nobody`, printed red on every status, and
`cores` and `cost` are `nobody` until a measuring command exists.

**Enforcement is keyed to the artefact.** The development-guideline hook is split by axis:
session rules (scratchpad, heredoc, `python -c`) stay a `PreToolUse` hook, because they are
about the session; commit rules (suites, `check`, `check --deep` on figure code) become a git
`pre-commit` under a committed `core.hooksPath`, because they are about the repository, and
fire for any session, editor or terminal. `scprofile check` reports whether the gate is
installed; the session hook denies a commit while it is not.

**The agent layer carries checkable claims.** A skill may not state a stage count or an "N of
N" as a literal; the count is the declaration's and is read from `sch dev convert status`. The
defect-routing loop of a round — host fix in place, maker gap, worksheet answer, held-out record
— is stated in the plugin-maker skill in the vocabulary `rules.py` already has, and `status`
banners a plugin the declaration holds out.

**A tenth tool, outside the family, is the next blind test.** The eight held-out plugins are
finished artefacts: they prove the maker can read a finished plugin, and the overfit scan shows
five of eleven stages cannot discriminate on them. Out-of-sample *making* evidence is produced
only by a conversion of something the maker has never seen, and spending one of the eight buys
one datapoint. The blind job is parameterised by tool and pointed at a tool no kernel wraps, on
the fixture and the ladder, never the cohort.

## Consequences

**Easier.** One status answers "is this plugin finished" in both phases, and prints the loop's
own next command for what is not. A run that measured a fifth of its panels says so. A required
key nobody checks is red on every status rather than a paragraph in KNOWN_ISSUES.md. A commit
from any session runs the same gate.

**Harder.** A test stage needs a run, and a run of this family needs the cluster; the build
phase stays the only thing a workstation can complete. The loop script is now called by two
parties and its flags are an interface. The R protocol still measures nothing — the count is
honest and the panels are still only looked at by eye.

**Given up: the pre-commit gate has an escape nothing records.** `git commit --no-verify` skips
it and leaves no trace, where the session hook's denial could at least be seen in the
transcript. A gate whose escapes are all recorded is the standard this family holds itself to,
and this one falls short of it; the escape is documented where the hook is, which is less.
**Also given up: three readers of one fact.** The gate's installation is reported by
`scprofile check`, by the session hook and by the ladder's declaration tier, and a fresh clone
is not gated until one of them is read. There is no mechanism that exists before installation.
