# ADR-0018 — the audit repairs what it finds, the run measures what it costs, and the eye comes before the pen

**Date** 2026-09-13. **Status** accepted; executing. **Follows** ADR-0017 (the run drives its own
writing). **Rules in force** the four top rules (a plugin is maker output; the eight are held out;
mechanism and the agentic layer are fixed in place; end to end is cellchat), the HPC rules (H1:
nothing authored on the cluster, every tool invocation through `qsub`, no compute on a login
node, runs under `~/projects/SAMBO/runs/scprofile/04_profile/`), and scProfile's DEVELOPMENT.md
(every check seen to fail; smallest change; fix the mechanism that exists, never one beside it;
commit only when green; cost recorded). **The brief for this round**, in the user's words:
`audited` is the design that keeps figure quality up under varying data - make it a mechanism
independent of the maker and of any plugin, so it applies to every plugin, design before
change, and make its findings addressable seamlessly and efficiently with no redundant
mechanism; make `measure` a proper mechanism, efficiency first, no hand edits, as general as
possible; the lookers are a design inconsistency - reorder the actions.

## Context — what the three stages are, measured on PBS 710985

The evidence is the newest sealed run, `20260912T163648Z__scprofile-344993d__04_profile__plan`
(PBS 710985, 26 minutes of wall time on 64 cores), its writing run (PBS 711001, blind 0004's 139
looks, 33 claims), and the code that produced them.

### 1. The audit measures, records, and repairs almost nothing

`figure.audit(fig)` runs in `emit_figure` on every panel a plugin draws through the host, after
`fit_column` has shrunk the canvas to the declared column and after `resolve_overlaps` has
re-solved the label sets a plugin registered with `spread_labels`. It finds three classes - text
over text, an artist off the canvas, a size channel with no key - and records them on the
panel's manifest entry. Station 6b (`audited`) reads them back and says "FIX THESE FIRST, they
need no eye". The only repair in the path is that re-solve, and it reaches only annotations a
plugin registered.

On 710985 the station reads 43 `text_overlap` on five panel ids. Read one by one, they are not
five defects of drawing intent; they are two, and both are the host's:

| panel | count | what collides | why |
|---|---|---|---|
| F1_database_coverage | 18 | a tick of the main x axis over a tick of the twin x axis ('4000' over '25', 92%) | two axes on one side; the canvas shrank, the type did not |
| F2_population_power | 14 | the first log-axis tick over the y axis's origin ('10^4' over '0.0') | the shared corner; the canvas shrank |
| F10_pathway_similarity | 6 | a tick label over the host's own provenance stamp ('−0.8' over 'Aging1 · one sample') | the stamp is placed at a fixed y below the figure box; a bottom tick label reaches it |
| F10_pathway_similarity | 3 | two ticks of one axis ('−0.8' over '−0.6'; '−0.4' over itself twice) | dense or duplicated ticks after the shrink |
| F9_patterns | 1 | corner ('0' over '0.955') | as F2 |
| F6_signaling_roles | 1 | a placed label over a legend's text | a data-placed label; the legend inside the axes |

Every one is a layout that depends on the data - how many ticks, how long a label, where a
point fell - and on what the host did to the canvas after the plugin finished. That is exactly
the class the brief names: under varying inputs the text varies, and a fix in the plugin's code
holds for one dataset. The stage sends it to the plugin, the top rule keeps this round out of the
plugin, and a rerun is the only way to see whether a fix held. The stage's own words -
"they need no eye" - are right; "fix them in the plugin" is the wrong address.

**765 of the 945 panels never pass the audit** - the companion draws them in R. A raster check
was measured before deciding anything: the ink on the outermost two pixels of the thirteen
figures the lookers called cut, clipped or truncated is 0.0 to 1.3 per cent (R clips text at the
plot region, inside a white margin), and a sound panel (`native_patterns_incoming`) carries 45
per cent on its bottom edge (a legend bar). A border check would miss every real case and
condemn a correct one. **No raster audit.** The R plates stay the eye's, and the station goes on
counting them as such.

### 2. `measure` cannot be answered in the shape every run has

`_entry.py` measures an instance as RUSAGE self plus the largest reaped child - a floor, since
concurrent workers are undercounted - and beside it the job's cgroup counter, which is exact for
the job and belongs to no single instance. `feedback.peak_measurement` takes the larger, so on a
run whose eighteen instances shared one job every point carries the same job-wide figure; the fit
sees identical peaks at differing sizes, refuses (correctly - an earlier version printed "45 GB
fixed, 0 per 100k" from exactly that), and `capacity --memory` exits non-zero. The stage OWES on
every shared-job run for good. The way out it names is one instance per job: eighteen jobs to
measure one plugin, which is the opposite of efficiency, and the fitted numbers then reach the
declaration by somebody pasting them - the one edit of a plugin the top rule allows and the one
the brief now forbids. cellchat's declaration carries `3.1 + 5.7`, fitted in some earlier shape
on some earlier machine; nothing has been able to check it since.

### 3. The lookers look after the pen has been picked up

The contract already states the order (AGENT_CONTRACT.md: "settle the figure set before writing
the section"; TEST_LOOP.md: "scan the whole set on one build, fix them all in one commit,
rebuild, re-scan; the station passes when a complete scan produces no fix"). The mechanism does
not enforce it, in four places:

1. **A look has no verdict a machine can read.** A note is prose. On 710985's writing run 58 of
   139 notes name a defect (14 overlaps, 9 missing legends, 9 colour scales with no numbers, 13
   cut or clipped, 5 identical panels, 5 illegible) and nothing can count them: `looked_at`
   counts looks, not findings.
2. **`audited` precedes the eye and reads only the machine.** The eye's findings reach no stage.
   The stage's own text says "the unmeasured count is the eye's work" and then nothing collects
   that work.
3. **The pen opens on coverage.** The agenda's `write` task is PENDING the moment every look is
   recorded, whatever the looks said; `paper --claim --cites` binds a claim to a figure's digest
   and asks nothing about the figure. Blind 0004 wrote a section from figures its own lookers
   had condemned an hour earlier, and the reviewer narrowed or withdrew 32 of 33 claims - three
   of the reasons ("two-panel heatmaps that never say which panel is which arm") were the
   lookers' findings read from the other side.
4. **The findings reach the author by a file, not by the driver.** A look is bound to the
   image's digest, so the next build clears it (right), and `carried_findings` shows what was
   last seen (right); but nothing in the maker's status names the eye's defects as debt. The
   agenda tells the author where the ledger is.

The inconsistency, in one sentence: the loop's own rule is look → fix → rebuild → look again →
write, and the mechanism's order is look → write, with the fix left to a file nobody is driven to.

## Decision

Three changes, each to a mechanism that exists. No new stage, station, command or file kind. Two
flags and one stage key are added; one stage moves.

### A. The audit repairs at the emit, then records what is left

`figure.audit_and_repair(fig)` - audit, repair, audit again, at most three passes - replaces the
audit call in `emit_figure` and in `figure.save` (the two save paths; one implementation). The
repertoire is fixed, ordered, bounded, and keyed to the finding it answers; each repair is generic
to matplotlib and knows no plugin:

| finding | repair | bound |
|---|---|---|
| a tick label over the provenance stamp | the stamp is placed below the lowest artist's rendered box, not at a fixed y (`_stamp_provenance`, at the source) | never above the figure |
| tick labels of two axes on one side overlap | the second axis's spine is moved outward by the overlap plus a pad | once per axis |
| an x tick over a y tick at the shared corner | the y axis's corner label is hidden | one label |
| two ticks of one axis on one baseline overlap | numeric: the axis's major locator is thinned by one bin, down to three; categorical: the labels are rotated 45° and right-aligned | three thinnings |
| two ticks with the same text at the same place | the later one is hidden | - |
| a placed label over a legend's text | the legend is moved outside the axes (`legend_outside`) | once |
| two placed annotations overlap | `_separate` on the pair (offset-point annotations only; a text in data coordinates is never moved) | the existing shift cap |
| anything else | residue, recorded with the repairs tried | - |

No font shrinks, the canvas never widens past the column, no number moves. The manifest entry
carries `audit` (the residue, an empty list when clean) and `repairs` (what was applied; absent
when nothing was); the serialiser carries both and the existing check that every key `emit_figure`
writes is one the serialiser keeps guards the pair. The log line per panel says found, repaired,
remaining. Station 6b prints "N found, R repaired by the host, S remain on K panel(s)" and names
the residue with the repair tried; its BLOCKED state reads the residue alone. The stage's
`finished_by` says what a residue is: a collision the repertoire does not answer - fix it in the
plan or the plugin, or, if the class is general, extend the repertoire in the host so no plugin
meets it again.

Why this is independent of the maker and of the plugins: every one of the nine plugins emits
through `emit_figure` and none is told the repertoire exists; the maker reads a station line; a
held-out plugin gets every repair on its next run without a line changed. Why it is the whole of
"addressed seamlessly": the machine-repairable classes are addressed in the run that finds them,
before any eye or pen, and the residue is named with what was tried. Why no raster half: measured
above.

### B. The run measures each instance in the job it shares, and the fill is applied by the tool

- **A sampler in `_entry.py`**: a daemon thread started before `run(ctx)` and stopped after
  `_dispose`, every second summing the instance's own process tree - PSS from
  `/proc/<pid>/smaps_rollup` where the kernel offers it, RSS from `statm` otherwise - and keeping
  the peak. `ctx.measured` gains `tree_peak_gb`, `tree_basis` and `samples`. Where `/proc` does
  not exist (macOS) nothing is added and the floor stands, named as before. Cost: one `/proc`
  walk per second per instance.
- **`peak_measurement` prefers the tree peak** - it is attributable and it includes concurrent
  workers, the two properties the floor and the cgroup counter each lack. The cgroup figure stays
  recorded beside it; the fit reads the tree; the identical-peaks guard stays as a guard.
- **`capacity --memory` becomes a gate with a way out.** It prints the fitted terms and the
  declaration to make of them (the fit plus ten per cent headroom; a named constant), and exits 0
  only when the plugin declares both terms at or above the fit. Under-declaration is the killing
  direction and is what the exit code refuses. With `--declare <plugin>` it writes the two terms
  into the plugin's executor block, reloads the declaration, and refuses - restoring the file - if
  the values did not take. This is the repository's own tool editing its own artefact, as
  `scaffold --force` already regenerates the companion.
- **The stage declares how its fill is applied.** `measure` gains `apply:` beside `command:`,
  an argv the maker runs on `sch dev convert measure --run RUNDIR --name X --apply` and never on
  a status. The maker learns nothing of the format: `apply:` is a key any stage may declare, read
  the way `command:` is, and a stage that owes and declares one is printed with the line to run.
  `finished_by` says the whole of it: measured in any run, applied by one command, and until then
  the allocator's conservative default with the words that say so.

"Efficiency first": one job measures, the declaration follows the measurement, and the allocator
packs waves by a measured demand instead of 24 GB per 100k cells.

### C. The eye comes before the pen, and its findings are a stage's debt

- **A look carries a verdict.** `scprofile review --figure F --note "..." --defect` marks a look
  that says the panel must change; without the flag a look describes. `review.defects(out,
  plugin)` returns the looks marked defect whose image is unchanged - digest-bound like every look,
  superseded by a later look on the same bytes, cleared by a redraw. The agenda, the station, the
  skill and the command's help say when to pass it.
- **`looked_at` moves before `audited`** in DEVPOINTS, and `audited` reads two things: the
  machine's residue after repair, and the eye's open defects, deduplicated by kind, printed with
  the looker's own words. It owes while either exists, and while the eye's half is unasked - a
  scan set nobody has looked at is not a clean audit, and the line says "the eye has looked at N
  of M". The maker's status is therefore the one place the author reads what to fix, in the
  order: look at everything, then the audit names the debt, then build, then look again.
- **The pen waits.** The agenda's `write` task is BLOCKED while any figure of the scan set
  carries an open finding (machine residue or eye defect), naming them; `scprofile next` says the
  same first; `paper --claim --cites` refuses a figure with an open finding, quoting it; the brief
  marks each such figure. `paper --write` still accepts a draft - a section may be drafted while
  the figures are rebuilt - but no claim rests on a plate the run's own record calls wrong.

What "reorder" means here, exactly: the action order printed by the maker and the agenda
becomes run → look (whole set) → audit (machine residue + eye) → fix → rerun → look at what
was redrawn → write → review → deliver. Nothing new is asked of the agent; the second half is
refused until the first half is clean.

## What must not be done

- No new stage, station, command or file kind in scProfile. `--defect`, `--declare` and `apply:`
  are a flag, a flag and a stage key on things that exist; `looked_at` moves; nothing is added
  beside anything.
- No hand edit of `kernels/cellchat.py`. The one write into it this round is the tool's
  `--declare`, run through the maker's `measure --apply`, and it is recorded as such.
- No raster audit (measured; above). No repair that shrinks type, widens past the column or
  moves a number.
- No writing into a sealed run; every job through `qsub` with `rule-one: no-removal`; validated
  first; nothing authored on the cluster.
- No claim in a record that states a count the declaration owns.

## Steps

0. This record, committed before any change.
1. **The audit repairs** (scProfile): `_stamp_provenance` placed from the rendered box;
   `figure.repair` and `figure.audit_and_repair`; `emit_figure` and `figure.save` call it;
   manifest `repairs`; station 6b prints found/repaired/remaining; `audited.finished_by`;
   TEST_LOOP.md. Tests: each repair fires on the shape it answers and is silent on the sound
   version (test_figure_audit, test_audit_control); the emit records both keys; the serialiser
   keeps them; the station's wording.
2. **The run measures** (scProfile): the sampler; `peak_measurement`; `capacity --memory` as a
   gate; `--declare`; `measure` gains `apply:` and a new `finished_by`; KNOWN_ISSUES.md. Tests: a
   reconstructed `/proc` tree; the preference; the gate's exit codes; `--declare` on a copied
   plugin file, verified by reload, refused and restored on a file it cannot edit.
3. **The maker applies** (harness): `apply:` accepted and printed; `measure --apply`; DEVELOPING
   §8; the skill's `measure` paragraph. Tests: a widget stage with `apply:`; the status line; the
   action refuses without `--run` and without `apply:`.
4. **The eye before the pen** (scProfile): `--defect`; `review.defects`; `looked_at` before
   `audited`; station 6b reads the eye; the agenda's `write` gate; `next`; the claim refusal; the
   brief's marks; AGENT_CONTRACT.md, TEST_LOOP.md, the result-section skill; the maker skill's
   paragraph. Tests: a defect look is counted and superseded; the station names it; the claim is
   refused with its words; the agenda blocks and names; the brief marks.
5. **The reproduction** (harness): `jobs/audit_reproduction.pbs` and its submitter, cellchat on
   the cohort against 710985, predictions A0-A9 in the job before it runs; the tool tree exported
   to the cluster at the commit; validated; submitted; graded; the record here.
6. **The fill on cellchat**: `sch dev convert measure --run <the run> --name cellchat --apply`
   on the workstation against the run's report; the diff is the two numbers; committed as the
   tool's edit.
7. **Blind 0005, light**: cold Sonnet agents on the new run's writing replay - two lookers
   given the review command's shards, one writer given the brief; predictions B1-B5 written
   before they start; every defect they meet fixed test-first; the record in docs/blind/0005.

## Predictions

Reproduction A, graded by the job against 710985 (the reference):

- **A0** the run produced panels; 945 PNG and 24 PDF under `kernels/`, the same names.
- **A1** the audit's residue on the run is at most 3 findings in total (43 on the reference),
  and at least 40 repairs are recorded across the five panel ids.
- **A2** no panel's residue exceeds its own count before repair: a repair never adds a
  collision.
- **A3** 90 of 90 numeric per-unit tables identical to the reference: no repair moves a number.
- **A4** `measure` is answered on this run: `report.json` holds a memory model for cellchat
  fitted on the instances' process trees, 18 points at 3 or more distinct sizes, both terms
  present, the per-instance peaks not all identical; `capacity --memory` prints them.
- **A5** every instance's tree peak is at or below the job's cgroup counter, where the counter
  was read: the sampler never exceeds what the scheduler billed.
- **A6** the maker's status on the run reads `promised` done, `looked_at` owing (0 of the scan
  set), `audited` owing and saying the eye has looked at 0 of N, `written` and `delivered`
  owing; `measure` owes or is answered by the declaration gate alone - it is answered only if
  cellchat's declared terms are at or above the fit, which this record does not predict.
- **A7** `capacity --against` the reference: identical counts.
- **A8** the environment is reused: the same `scprofile-env-<hash>` as the reference's install
  log.
- **A9** the job's own grading writes PREDICTIONS.txt with one line per prediction, and seals
  only when none failed.

Blind 0005:

- **B1** two cold lookers, given the run's status and the review command's shards, record looks
  with `--defect` on the panels that must change without asking a question; at least one defect
  is marked (the two-panel heatmaps with no arm label are still the plugin's).
- **B2** after the looks, the maker's status reads `looked_at` done and `audited` owing, naming
  at least one eye defect by kind in the looker's words.
- **B3** the writer's `--claim --cites <a marked plate>` is refused and the refusal quotes the
  finding; a claim on a clean plate is recorded.
- **B4** the brief marks every figure with an open finding.
- **B5** the agents meet at most two defects of the mechanism, each fixed test-first the same
  day.

## Consequences

Easy: a collision the host or the data made is repaired where it happens and never reaches an
eye or an author; every plugin gets it; a plugin's memory is measured in the runs it already
makes and declared by one command; a wrong figure cannot carry a claim. Hard: the pen waits for
the figures, so a build with a real figure defect costs a rerun before a section - which is the
loop's own rule, now enforced. **Given up**: a repair the audit applies is a change to the panel
the plugin drew, recorded but not asked for; the repertoire is the host's judgement about layout,
bounded so it can be read in one table, and a plugin that wants a collision (none does) cannot
keep it.

## Status

| step | state | commits | notes |
|---|---|---|---|
| 0 record | done | this commit | |
| 1 the audit repairs | done | scProfile c817bca | `figure.audit_and_repair`: nine repairs keyed to their findings, three passes, the column re-fitted; the stamp placed from the rendered box after the fit; `emit_figure` and `figure.save` share it; the manifest carries `repairs`; station 6b prints repaired beside remaining; suites 91 green |
| 2 the run measures | done | scProfile b59bf7d | `_entry._TreeSampler` (PSS from `smaps_rollup`, RSS otherwise, one /proc walk a second); `peak_measurement` prefers the tree; `capacity --memory` exits 0 only at or above the fit and `--declare` writes the fit plus 10% into the plugin, read back; `measure` declares `apply:`; suites 92 green |
| 3 the maker applies | done | harness: this commit | `apply:` read beside `command:`; `sch dev convert <stage> --run R --name X --apply` runs it; a status names the apply line for an owing stage and never runs it; the advance command is the apply when the stage owes; DEVELOPING §8 and the skill; harness suite green |
| 4 the eye before the pen | | | |
| 5 the reproduction | | | |
| 6 the fill on cellchat | | | |
| 7 blind 0005 | | | |
