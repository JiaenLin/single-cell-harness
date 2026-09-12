# 0016 — The figure plan carries the call, and the draw sites are generated from it

**Status** accepted
**Date** 2026-09-12
**Affects** ADR-0015 (one spine); scProfile's plugin format (`report.figures`, `native_plots`,
`report.figure_axis`, `report.figure_position`); the generated R companion; the plugin maker's
`legends` and `placement` stages and its draw-site extractor
**Execution** §"The instruction" below is written so that whoever picks this up — a later
session, another agent — can continue from any step without re-deriving it. **Update the status
table at the end as each step lands.** Nothing above that table changes after acceptance.

## Context

The figure plan already governs three things from a plugin's declaration — how many of a family
(`at_most`), the axis it multiplies over (`figure_axis`), where a result places it
(`figure_position`) — and `scprofile plan` prints the count before a queue slot is spent. What the
plan does not carry is **the call**: which upstream function, with which arguments, over which
items, under which legend. That lives in 47 hand-written R draw sites inside
`kernels/cellchat.py` (`_R_RUN` 21, `_R_COMPARE` 19, `_R_COHORT` 7) and ten Python figure
functions. To change a heatmap's measure or add `top = 20` to a dotplot, one edits R inside the
method body — the thing rule 1 of the maker round forbids — and to stop drawing a panel one
cannot: a `skip` in the accounting does not reach the R site.

The plan is also spread across four fields, figure ids are parsed by regex out of English
(`use: "figures/native_heatmap_{count,weight}.png per unit, …"`), and the two prefix maps have
already cost a defect (`native_` against `nativecmp_`). The maker's largest module — the
draw-site extractor, 1,205 lines — exists only to find sites somebody wrote by hand and ask
whether they carry a legend.

The goal set for this round: **the maker has full control of what a plugin draws; adjusting a
figure is done at the plan, never in method code.** The constraint: adjust or remove mechanism;
**add no layer.**

## Decision

**The plan carries the call, and the draw sites are generated from the plan** — exactly as the
draw protocol (`kernels/cellchat.draw.R`) already is, and proved the same way (`generated_by`).

1. **The plan is `report.figures`.** It already exists. Each entry gains the fields it was
   missing (`by`, `fn`, `axis`, `args`, `items`, `at_most`, `legend`, `kind`). `native_plots`
   collapses into it: a used upstream function is a `by: tool` entry; an unused one is a
   `report.skips` entry. The accounting is unchanged in strength — *used* is the set of `fn` in
   the plan, *skipped* is `skips`, and `native.account` checks the inventory against both.
2. **One reader.** `planner.figure_families` reads an entry's own fields. Where an entry has no
   `fn`/`axis` (the eight held-out plugins, untouched by rule 2) it reads the prefix maps and the
   `use:` prose as it does today. That fallback is the current code, not a second reader, and it
   is retired by the last conversion.
3. **Generated sites.** `scprofile scaffold` writes, into the companion it already writes, one
   function per axis — `.draw_unit()`, `.draw_contrast()`, `.draw_cohort()` — with one literal
   `npng`/`ndev` call per entry, a loop where the entry names `items`, and the legend filled from
   the entry's template. The method body computes, exposes the objects the entries name, and
   calls the function for its axis. Every ceiling, legend, colour, audit record and manifest
   record is then structural.
4. **The host launches R.** `ctx.rscript(body, args, name=…)` prepends the companion, writes the
   figure-context file, runs the interpreter under the plugin's environment, keeps the whole log,
   and **reads back the records the companion wrote** into the manifest. This is the plugin-side
   glue cellchat carries today (`_draw_r`, `_write_figure_context`, `_log_r`, `_RS`) moved to the
   host, and it closes the deferred half of ADR-0015 — a panel drawn in R gets a manifest record
   — with no new mechanism.
5. **Retired:** the draw-site extractor and its ceiling-guard instrument; the two prefix maps and
   longest-prefix-wins; filename-from-prose parsing (`named_by: use`, `per_item`); cellchat's own
   inventory code (`_R_INVENTORY`, `plot_inventory`, `check_plot_accounting`); the plugin-side R
   glue. The maker's `legends` and `placement` stages become one `plan` stage that rules on the
   entries with the `each_item_declares` key it already has.
6. **Adjusting a figure is three commands and no method code:** edit the entry; `scprofile plan`
   for the count; `scprofile scaffold <plugin> --force` to regenerate; `sch dev convert status`
   confirms the companion is *generated*, not *drifted*.

### The entry, normatively

```python
"report": {
  "figures": [
    # an upstream plot, drawn once per unit
    {"id": "native_heatmap_count",            # the family; files are <id>.png or <id>__<item>.png
     "by": "tool",                            # tool | plugin  (who draws; provenance on the page)
     "fn": "netVisual_heatmap",               # the upstream function (by: tool) or the plugin's own (by: plugin)
     "axis": "unit",                          # unit | contrast | cohort - what it multiplies over, and which script draws it
     "args": 'cc, measure = "count", color.heatmap = "Blues", color.use = .cols_for(levels(cc@idents))',
                                              # R, verbatim, pasted inside fn(...). The maker does not parse it.
     "at_most": 1,                            # files per occurrence of the axis; REQUIRED when `items` is set
     "position": "contrast",                  # overview | contrast | conclusion | appendix
     "kind": "matrix",                        # one of panels.KINDS, or "other" - what rules bind
     "legend": "Interaction counts between every ordered pair of populations in {unit}; "
               "row sends, column receives; {n_pops} populations.",
                                              # filled at draw time: {unit} {contrast} {item} from the host, {name} from .fact(name = ...)
     "profile": True},                        # unchanged meaning
    # one panel per item the method exposes
    {"id": "nativecmp_chord_cell", "by": "tool", "fn": "netVisual_chord_cell", "axis": "contrast",
     "items": "pathways_shared",              # an R name the method defines; NA and "" are dropped; the loop variable is .item
     "args": "merged, signaling = .item, lab.cex = 0.6", "at_most": 8, "position": "appendix",
     "kind": "chord", "legend": "The {item} pathway in both arms …"},
    # a plugin-drawn Python panel: the host's emit path is the site, the plan governs the rest
    {"id": "F1_database_coverage", "by": "plugin", "fn": "_fig_coverage", "axis": "unit",
     "kind": "coverage", "position": "appendix", "shows": "diagnostic", "required": False,
     "question": "…", "source": "figures/F1_database_coverage.csv"},
  ],
  "skips": {                                  # every upstream export not named by an entry's fn
    "ggPalette": {"skip": "not_applicable", "evidence": "returns colours; draws nothing"},
  },
}
```

Optional per entry: `w`, `h`, `res` (device size, default the protocol's); `device: "png" |
"ndev"` (`ndev` for a function that draws as a side effect — the wrapper the existing site used
says which); `file: "<R expression>"` (the file stem of a per-item panel, verbatim from the
site — `paste0("chord__", pw)`, `paste0("interaction_flow__", safe)` — evaluated in the frame
the draw is called from, so a migrated family names its files exactly as its run did; default
the id); `generated: False` (the tool writes this file as a side effect of a call the method makes —
`estimationNumCluster` from `netClustering` — so the plan accounts for it and generates no
site); `when: "<R expression>"` for a site the method guards with a condition; `expr:
"<R expression>"` in place of `fn` + `args` for the few sites that are a brace block of several
statements — still in the plan, still generated, and the worksheet marks each one so it can be
reduced to a call later.

*Amendment, 2026-09-12, before step 2:* the provenance field is **`drawn_by`**, the name
`report.figures`, `native_plots` and `captions.tsv` already use — `by` in the examples above reads
as `drawn_by`. A new name for an existing fact would have been the drift this record removes.

What is **not** in the plan: the host's own panels (declared by `unit_network`, drawn by
`panels.py` — unchanged); the method's numbers; the upstream function's internal encoding. The
plan controls what is called, with what, how often, where it lands and how it is described.

*Amendment, 2026-09-12, before step 4, from reading the 46 sites:* the generated R is a
**plan interpreter, not one function per axis**. The companion carries the entries as data
(`.plan`) and two functions: `.draw(id, item = NULL, env = parent.frame())`, which draws one
entry with its `fn(args)`/`expr` and its `file` **evaluated in the caller's frame** — so a site
inside a method loop becomes `.draw("nativecmp_interaction_flow", item = fr)` at the same
point, seeing the loop's own locals — and `.draw_all(axis, env = parent.frame())`, which draws
every entry of an axis that names `items`, binding `.item`. A unit script whose sites are plain
calls on the fitted object becomes one `.draw_all("unit")`; a script whose sites sit inside
computations keeps its structure and calls `.draw` where the site stood. Method logic never
moves into the plan; the plan never needs the method's loop.

### The generated R, per entry

```r
.draw_unit <- function() {
  npng("native_heatmap_count", netVisual_heatmap(cc, measure = "count", ...),
       legend = .legend("native_heatmap_count"), by = "tool")
  for (.item in .items(pathways_top))
    npng(paste0("native_chord_gene__", .item), netVisual_chord_gene(cc, signaling = .item),
         legend = .legend("native_chord_gene", item = .item), by = "tool")
}
```

A legend's `{...}` placeholders are **R expressions evaluated in the frame the draw is
called from** — `{pw}`, `{length(vr)}`, `{as.character(rows$reference[1])}` — so a migrated
legend says exactly what its site said, and a method exposes nothing it did not already have in
scope. A placeholder that does not evaluate refuses the legend loudly, the way `scp_legend`
already refuses a short one. (Superseded: an earlier draft of this record had `.fact()` and a
`facts` field; the calling frame makes both unnecessary.) `.draw_one` additionally appends
one row to `figures/figures.tsv` — `file id fn by axis item caption` — which `ctx.rscript` reads
back into the manifest as `{id, path, caption, drawn_by, native_function, measured: False}`.

## Consequences

**Easier.** A figure is adjusted in one place, checked by `plan`, regenerated by `scaffold`,
and proved by `generated_by`. The next conversion writes zero draw sites: the agent fills
entries, and the `account` worksheet prints their skeletons with the upstream function's
parameters beside them. Station 6b's "drawn and NOT measured" count keeps its meaning and gains
a record per panel. The maker loses its largest module and two stages.

**Harder.** The migration touches the declaration format, the planner, the reporter, the
validator, the composer, capacity, the scaffold, the maker's stages and cellchat's declaration
and R — in that order, each behind an acceptance gate. The reproduction is the only proof that
the R step changed nothing, and it costs a cluster run.

**Given up.** `args` is an opaque string: the maker checks that it is present, not that it is
right; R will say at run time, as it does today. The prefix-map fallback stays alive until the
eighth held-out plugin is converted, and that is a dual read held open on purpose by rule 2. The
R side is still one plugin in nine, so the generator is proved on one; the plan format is general
and the generator's corpus is not.

---

# The instruction

Read this whole section before doing anything. Then work the steps in order; each has a gate,
and a step is not done until its gate is green and its commit is pushed. **Update the status
table at the bottom when a step lands, in the same commit.**

## Standing rules — these do not relax

- **Top rules of the round** (scProfile `DEVPOINTS.yaml`, `rules:`): a plugin is maker output —
  never hand-edit `kernels/cellchat.py` except to paste a worksheet answer the maker printed; the
  eight held-out plugins are not touched; mechanism changes in place (`scprofile/`, `sch/`,
  `tests/`, `docs/`, `jobs/`, `setup/`, `.claude`, `DEVPOINTS.yaml`); end to end is cellchat only.
  `sch dev rules --root <scProfile>` must read 4 held after every commit.
- **HPC rule H1**: nothing is authored on the cluster; every tool invocation there goes through
  `qsub`; job scripts carry `rule-one: no-removal`. Read the `duke-nus-hpc` skill's `LAYOUT.md`
  before submitting anything.
- **Development guideline** (scProfile `DEVELOPMENT.md`): the repository is the only home; no
  scProfile material in a scratchpad; no `python -c`/heredoc importing scprofile; the commit gate
  is installed (`git config core.hooksPath setup/githooks`) and every commit goes through it;
  every check must be seen to fail; the smallest change; cost recorded in the code.
- **Predictions before runs.** A cluster reproduction is submitted with its predictions in the
  job script. A blind conversion has its record in `docs/blind/` written first.
- **No new layer.** Declaration → generated companion → host protocol → method. If a step needs
  a fifth thing, stop and rewrite the step.

## Where things are

| | |
|---|---|
| harness (this repo) | `<harness>` — the checkout this file is in — `sch/dev/convert.py`, `sch/dev/extract/`, `sch/dev/ladder.py`, `skills/plugin-maker/SKILL.md`, `docs/DEVELOPING.md` |
| scProfile | `<scProfile>` — the checkout beside it (`~/tools/scProfile` on the workstation this was written on) — `scprofile/{planner,report,declare,native,compose,capacity,scaffold,plugin,_entry,manifest,captions,figure_context}.py`, `kernels/cellchat.py`, `kernels/cellchat.draw.R`, `DEVPOINTS.yaml`, `tests/` |
| sealed reference run | cluster, `runs/scprofile/04_profile/20260910T130619Z__scprofile-9211f81__04_profile__legends` (PBS 710085): 945 PNG + 24 PDF, 90 of 90 tables byte-identical to 710080; `cellchat_net_embedding.csv` differs by design (UMAP unseeded — always exclude it) |
| how a cellchat-only cohort run is submitted | `tools/scProfile-cconly-jobs/submit_legends.sh` on the cluster (refuses a tree with more than one kernel); env `scprofile-env-d077909e49` is cellchat alone and reused when declarations are unchanged |
| the loop on the cluster | scProfile `setup/loop.pbs`; the ladder `jobs/dev_suite.pbs` |
| memory | the session memory file `one-spine-round-2026-09-12.md` (its index is `MEMORY.md`), and this file |

## How to resume from any point

```
cd <harness>   && git log --oneline -8 && git status --short
cd <scProfile> && git log --oneline -8 && git status --short && git config --get core.hooksPath
python3 -m sch.cli dev rules --root <scProfile>          # from <harness>: 4 held, or stop
python3 -m unittest discover -s tests -p 'test_*.py'     # harness, ~20 s
cd <scProfile> && python3 tests/run_all.py --jobs 4      # ~90 s
```

Then read the status table below, find the first step not `done`, and read that step's gate
before touching anything.

## Step 0 — this record

Commit and push this file. Add a one-line pointer to the memory file.

**Gate:** pushed. **No mechanism changes.**

## Step 1 — prove the spine on a sealed run (reads only, no compute)

`sch dev convert status --run` has only ever been run against `true`/`false` and synthetic run
directories. Point it at the sealed reference.

Write `jobs/status_on_run.pbs` in the harness (copy the preamble of `jobs/blind_convert.pbs`:
`source /etc/profile; module load anaconda3/3.0.0`, seal function, `rule-one: no-removal`). It
runs, inside `$RUNDIR/logs`:

```
PYTHONPATH=$HARNESS python3 -m sch dev convert status --root $TOOL --point kernel --name cellchat --run $SEALED
PYTHONPATH=$TOOL python3 $TOOL/tests/loop_stations.py --run $SEALED --json
```

**Predictions in the job header**, before submission: `audited` OWES (43 text_overlap across 5
panels; the line names ~745 panels drawn and NOT measured); `looked_at` OWES (0 of 149);
`written` OWES; `delivered` OWES (2 required outputs missing); `measure` answered;
`promised` answered (0 declared-and-never-drawn). Exit of the status command is 0 (it reports;
it does not fail), and the loop JSON's `first_blocked` is `6b drawing`.

Push both repositories, `qsub -v RUNDIR=…,HARNESS=…,TOOL=…,SEALED=… jobs/status_on_run.pbs`,
pull `$RUNDIR/logs` back, grade the predictions in the job's own seal.

**Gate:** sealed; predictions graded in `docs/blind/`-style prose appended to the memory file
and the results line of this step. Record what did not hold. If `status --run` crashed on the
real run directory, fix the maker first — that is the finding.

## Step 2 — the plan schema, one reader, the validator, the migration worksheet

All in scProfile unless marked *harness*. Tests first where a shape is stated.

2a. **`declare.py`** — `REPORT_KEYS` gains `"skips"`. `_check_report` validates entries: `id`
    required; `by` in `("tool", "plugin")` when present; `axis` in `("unit", "contrast",
    "cohort")` when present; `position` in the four; `kind` in `panels.KINDS` ids ∪ `{"other"}`
    when present; `items` ⇒ `at_most` required (ERROR otherwise: "a per-item family with no
    ceiling draws without bound"); `by: tool` ⇒ `fn` required; `args`/`legend`/`items` must be
    strings. `skips` values validated with `native.VALID`/`native.REJECTED` exactly as
    `native_plots` skip entries are today (move that check, do not copy it). Line 658's "declare
    `native_plots` or `plots_unreviewed`" becomes "declare `report.figures` entries with `by:
    tool`, or `report.skips`, or `wraps.plots_unreviewed`".
2b. **`native.py`** — `account(inventory, declared)` unchanged in signature; add
    `declared_from(spec)` that builds `{fn: {"use": [ids]}} ∪ skips` from plan entries and,
    where a plugin has no `fn` entries, returns `spec["native_plots"]` as today. Every caller
    that reads `spec.get("native_plots")` — `cli.py:1515/1538/3453`, `report.py:1995`,
    `compose.py:215/595` — calls `native.declared_from(spec)` instead. `function_for(declared,
    filename)` first matches plan entries (longest `id` prefix → `fn`), then the prose route.
2c. **`planner.figure_families`** — an entry with `fn` or `axis` supplies its own `(id,
    at_most or 1, axis, position, own=by=="plugin")`; brace expansion and prose parsing run
    only for plugins whose entries have neither. `over_ceiling`, `figure_plan` unchanged.
2d. **`compose.py`** `_positions` and **`_entry.py`** `figure_position=` — read position per
    entry first, prefix map second. `_wants_vector` in `plugin.py` likewise.
2e. ***harness*** `sch/dev/convert.py` — a `plan` action in `ACTIONS` (it is an action of the
    existing command, not a layer): prints the plan as one table — id, by, fn, axis, items,
    at_most, position, kind, legend present?, and for `by: tool` the function's parameters from
    the inventory. `--migrate` prints a **paste-ready** `report.figures` + `report.skips` block
    built from the current `native_plots` (ids via the existing `_families` parser, `at_most`
    dict → per id, `profile`), `report.figures`, and the two prefix maps; `args` and `legend`
    for each `by: tool` entry are transcribed from the draw-site inventory (`draw_sites.sites_of`
    — its `call` and `legend` fields — used one last time, for this). It prints; it never edits
    the plugin. The R probe in `extract/r_namespace.py` gains `formals()` so `detail[fn]` carries
    a signature, as the Python probe's does.
2f. **DEVPOINTS.yaml** (scProfile) — the `legends` and `placement` stages become one stage:

```yaml
- name: plan
  phase: build
  fills: [report.figures]
  each_item_declares:
    by: [tool, plugin]
    axis: [unit, contrast, cohort]
    position: [overview, contrast, conclusion, appendix]
    legend: []          # present, any text - the sentence is filled at draw time
  outstanding_if: wraps.plots_unreviewed
  generated_by: {command: ["{python}", "-m", "scprofile.cli", "scaffold", "{name}", "--dir", "{out}", "--force"]}
  finished_by: "`sch dev convert plan --root . --point kernel --name <plugin>` prints every entry and what it lacks; `--migrate` prints the block for a plugin still on native_plots"
  why: >
    which figures a result is written from, how many of each, drawn by what with which
    arguments, and how each is described - the whole plan, in one list the maker reads and
    the scaffold generates from
```

    `inventory` keeps `fills: [native_plots]` only until cellchat is migrated (step 3), then
    `fills: [report.figures]` with `outstanding_if` as above. `places_every`, `axis_field`,
    `enforced_by`, `each_draw_site_describes` are removed from the declaration in step 5, not
    here — the maker must keep reading them for the held-out eight until the reader fallback is
    retired.
2g. **Tests.** scProfile: `tests/test_plot_declarations.py` (report.py names it) and
    `test_declaration.py` gain: an entry with `items` and no `at_most` is refused; a `kind`
    outside the registry is refused; `native.declared_from` gives the same `account()` verdict
    for cellchat from plan entries as from `native_plots` (measured after step 3); **the
    acceptance baseline**: `tests/baselines/cellchat_figure_plan.json` = the rows of
    `planner.figure_plan(cellchat, units=18, contrasts=6, cohort=1)` expanded per panel stem
    (brace members separated), written from the declaration *before* step 3 and asserted equal
    *after*. Harness: `plan` action parses (agent-surface test), `--migrate` output round-trips
    through `planner.figure_families` on a fixture plugin, `formals` reaches the R detail on the
    `cluster` package.

**Gate:** both suites green; the baseline file committed; `figure_plan` for every one of the
nine kernels byte-identical before and after (the fallback path must not move anything); `sch
dev rules` 4 held. Commit scProfile through the gate, then the harness.

## Step 3 — migrate cellchat's declaration (a worksheet answer, pasted)

```
python3 -m sch.cli dev convert plan --migrate --root <scProfile> --point kernel --name cellchat
```

Paste the printed block into `kernels/cellchat.py`: it REPLACES `native_plots`, `report.figures`,
`report.figure_axis`, `report.figure_position`. Every `by: tool` entry must have `args` and
`legend` transcribed from its site — check each against the site by reading, not trusting; the
sites with a computed guard (`if (!is.na(pw))`, `head(paths, 6)`) become `items`/`when`. Raise
`version` (the reuse key) in the same edit.

**Gate:** `scprofile validate cellchat` 0 errors; the baseline test from 2g passes — **the
expanded plan is identical**; `sch dev convert status --name cellchat` build complete with the
new `plan` stage done; `capacity --promised` on the sealed run (reads only, workstation copy of
`report.json` is enough) reports 0 declared-and-never-drawn; both suites green; rules 4 held.
Commit through the gate. **No R has changed yet; no run is needed.**

*Amendment, 2026-09-12, after step 3 — what the paste found.* Six things, each a check seen
to fail first, none of them in the R:

1. **The worksheet dropped two of the 46 sites without a word.** `_families` required
   `figures/` on every file name in a prose `use:`, so the second name of an "X.png and
   Y.png" sentence was never a family and its site (18 files per run) had nothing to attach
   to; and a site no legacy field names at all — the log-scale companion drawn under an `if`
   beside its sibling — was silently not printed. The worksheet now prints every site the scan
   reads, counts the ones no legacy field names in its header, and reads a site's own `by =`
   as the provenance (the argument whose value is in the stage's `drawn_by` vocabulary; the
   site record carries its named arguments because `call` is cut at 400 characters).
2. **The validator asked the plugin's own R sites for a `question`, a `shows` and a
   `source`** — twelve errors on fields the reporter never reads for such a panel. There are
   three kinds of entry on one list, and `declare.drawn_by_companion` tells them apart once:
   an upstream call, the plugin's own R site (it carries `expr`/`args`/`file`/`items`/`when`/
   `device`), and a panel the host's emit path writes (it carries none). The third owes the
   three fields and is the only one a vector copy exists for; the planner had promised eleven
   vector files for the four interaction families that no run has ever written.
3. **The accounting's id matcher did not know one-underscore files.** `paste0("…_", pat)`
   writes `<id>_<item>.png`; `native.names_file` matches `<id>`, `<id>__…` and, for a per-item
   entry, `<id>_…`, and `undrawn` reads through it.
4. **The placement debt read only the maps.** A migrated plugin carries none, so every family
   came back unplaced and unaxised while saying in its own entry exactly where it went;
   `placement_debt` folds each entry's own word into the map as an exact key — the rule the
   target's one reader applies — and `entry_keys` names `axis` and `position`.
5. **The baseline moved on one position and nothing else.** The pre-migration fingerprint
   placed the heatmap brace family by its STEM, which misses the `…heatmap_` rule by one
   underscore and fell to the appendix; the reporter, matching file names, placed those 36
   files at contrast, and so does the plan per member. Files 897, vector 0, total 897 were
   identical; re-recorded once with the reason in the test's docstring.
6. **`sch dev rules` read the plan as copied mechanism**: two entries share nine key lines, and
   fifty-seven `{`/`},` pairs are a 9-line block repeated fifty-three times. A quoted key and
   its value, and a line of nothing but brackets, are a declaration, not a statement.

Also: `test_plot_declarations` had stopped checking cellchat the moment `native_plots` left —
it parsed that literal out of the source and skipped a plugin without one, green. It reads
every embedded script through `native.declared_from` now, with the prefix each script declares.
Four host comments named plugin figure ids and were caught by the portability check the moment
the plan listed every id.

## Step 4 — generate the sites; the host launches R; delete the hand-written sites

4a. **`scaffold.py`** — `render_plan(spec)` returns R text: `.draw_unit/.draw_contrast/
    .draw_cohort` from the entries (`by: tool` and `by: plugin` entries whose `fn` is an R
    function; skip `by: plugin` entries whose `fn` is a Python function — those are the host's
    emit path). Literal calls, one per entry; `for (.item in .items(<items>))` where `items`;
    `if (<when>)` where `when`; `w/h/res` where given; `.legend(id, item = .item)`; `by` from
    the entry. `R_DRAW` gains `.facts`, `.fact(...)`, `.legend(id, ...)` (template fill from
    the plan's legends, embedded as a named R list the generator writes), `.items(x)` (drops NA
    and ""), and `.draw_one` appends the record row to `figures/figures.tsv`. `_one_file`
    writes `R_DRAW + render_plan(spec)`. Deterministic: same declaration → same bytes.
4b. **`plugin.py`** — `Context.rscript(body, args=(), *, name)` and the same on
    `CompareContext` (extend `tests/test_the_two_contexts_agree.py`): writes
    `figure_context.tsv` (move `_write_figure_context` here, unchanged), writes the script as
    companion + body, runs `Rscript` with the plugin's environment and the run's thread bounds,
    keeps the full log beside the unit (move `_log_r` here, unchanged), and after return reads
    `figures/figures.tsv`, appending each row to `self._figures` as `{id, path, caption,
    drawn_by, native_function, measured: False}`. **`manifest._figure`** carries
    `native_function` and `measured` (add the test its own comment asks for: every key
    `emit_figure` writes is one `_figure` carries). **`report.py`** `_native_unit_panels` /
    `_native_panels` skip any file whose run-relative path is already a manifest record — one
    render, never two. `tests/loop_stations.py` station 6b: a record with `measured: False`
    counts as unmeasured (it already counts from disk; make the two agree and say which).
4c. **cellchat** — through the maker only: regenerate the companion (`scaffold --force`); in
    `_R_RUN`, `_R_COMPARE`, `_R_COHORT` delete the hand-written `npng`/`ndev` sites and put
    `.draw_unit()` / `.draw_contrast()` / `.draw_cohort()` at the point the first site stood,
    after the variables the entries name exist; add `.fact(...)` calls for every placeholder the
    legends use; delete `_draw_r`, `_write_figure_context`, `_log_r`, `_RS`, `_R_INVENTORY`,
    `plot_inventory`, `_split_inventory`, `check_plot_accounting` and the selftest's call to it;
    replace the three `subprocess.run([rscript, script…])` launches with `ctx.rscript(...)`.
    This is the one step where method-adjacent lines in the plugin are deleted by hand: they
    are the glue the host now owns and the sites the companion now generates, and
    `sch dev rules` (`maker_output`) and `generated_by` are what prove that nothing general was
    left behind.
4d. **Local gates**, before any cluster time: both suites green; `scprofile check --deep` green;
    `sch dev convert status --name cellchat` → `plan` done, companion *generated*;
    `sch dev rules` 4 held; the baseline from 2g still identical; the R companion parses
    (`Rscript -e 'parse("kernels/cellchat.draw.R")'` on the workstation — R is installed here).
4e. **The reproduction.** Push both. On the cluster, submit through
    `tools/scProfile-cconly-jobs/submit_legends.sh` with predictions in the job header:
    945 PNG + 24 PDF; 90 of 90 numeric tables byte-identical to 710085 excluding
    `cellchat_net_embedding.csv`; `chord_cell` `[8,8,8,8,8,8]`; `capacity --against` the
    reference 0 regressions; `promised` 0 gaps; every panel's manifest record present (new);
    `figures.tsv` present in every unit and contrast; station 6b's unmeasured count equals the
    number of R records. Then `sch dev convert status --run <new run>` (step 1's job) — the
    six run-side stages answer the same as on 710085.

**Gate:** sealed, every prediction graded in the seal, identical where predicted identical.
**If one file differs, the plan changed a figure it was not asked to: find the entry, fix the
generator or the entry, resubmit. Do not accept a "close enough".** Commit through the gate.

*Amendment, 2026-09-12, after 4a-4d — what generating the sites found, and one deferral.*

1. **Eleven of the 46 transcribed calls did not parse as R.** The extractor's one-line form of
   a site's expression joins the lines of a brace block with a space, and `{ f(x) g() }` is
   not R. A site record now carries the expression with its lines (`raw`); the worksheet
   carries a brace block that way; `plan --rscript <R>` parses every entry's call in one
   interpreter start and prints `LACKS  does not parse as R` under the entry, so the first
   parser a transcribed call meets is the maker's.
2. **Three device sizes were expressions and were dropped**: `w = .bw`, `w = max(1500, 340 *
   length(objs))`. Read as an integer or nothing, the entries lost their width and a generated
   site would have drawn at the script's default. Sizes are read from the site's named
   arguments, an integer as an integer and anything else as the expression, which the draw
   evaluates where the site did.
3. **A 47th site.** `paste0("compareInteractions_", ms)` and `paste0("compareInteractions_",
   ms, "_per1k")` in one loop shared a literal head and were one id; the second was silently
   dropped, and it was found by the one `npng(` left after the other 46 were replaced. The
   id is every top-level literal piece of the expression; the loop variable is the one
   non-literal piece.
4. **The interpreter is not a site.** The companion defines `.draw` and it delegates to the
   device path, which is what a draw wrapper looks like, so a rerun of the migration read
   `.draw("nativecmp_x")` as a site, doubled the prefix, and rewrote 46 migrated calls.
   `.draw`/`.draw_all` are never sites; the rerun's damage was repaired by hand and
   `test_plot_declarations` (which now reads `.draw` sites through the one reader) is what
   caught the ids that exist nowhere.
5. **The interpreter's form** is the amended one: `.plan[[id]]` as R data with every
   expression embedded as `quote(...)`, `.draw(id, item, env = parent.frame())`,
   `.draw_all(axis, env)`, `.fill` for legend templates (`{...}` are R expressions evaluated in
   the caller's frame; a failed placeholder renders as `?` and is logged), `.items` drops NA
   and "". Everything is evaluated in the CALLER's frame - including assignments a site's block
   makes, which one site relied on (`assign(..., globalenv())`). `ctx.rscript(body, args, name)`
   and `ctx.write_figure_context()` live on the shared mixin, both contexts carry
   `r_companion`, and `_entry` reads the companion beside the plugin. The comments six sites
   carried inside their expressions moved above their plan entries.
6. **Four tests read the old form and now read the new one.** `test_plot_declarations` and
   `test_legends_are_written` read a `.draw("<id>")` site's function and legend from the plan
   entry it names; `test_r_argv_alignment` counts the arguments of `ctx.rscript(_R_X, [...])`
   (no interpreter, no script path to subtract); `subject.r_as_run` prepends the companion to
   a script the host launches; `test_discovery_is_not_membership` moved to the level where the
   distinction lives now - `native.account(inventory, declared, every=None)` counts a declared,
   exported function the inventory's rule missed as used, reports only one absent from the
   namespace as stale, and without `every` says it cannot tell which. **Follow-up for step 5:**
   the maker's R probe reads every export and tags the matched ones; carrying the full list on
   `Inventory` and passing it as `every` closes the loop on the maker's side.
7. **Deferred to a step 4f, after the reproduction: the manifest half of 4b.** Recording every
   R-drawn panel in the manifest (`native_function`, `measured: False`), the reporter skipping
   files that are already records, and 6b counting `measured: False` change the reporter's
   render path - the kernel page groups manifest figures by `shows`, and an R panel there has
   none - and cannot be proven by the file-and-table gate of 4e. It is its own increment with
   its own predictions. `captions.tsv` is still what the reporter reads for R panels, exactly
   as before, so 4e's gate is unchanged.

**Local gates as run:** both suites green; `scprofile check --deep` 35 green; validate 0 errors;
the plan is the same plan (897 files, 58 families over 57 baseline stems - the 47th site's
family split two and two); `status` build 8 of 8, companion generated; rules 4 held; `plan
--rscript` 0 that do not parse; the companion and each of the four embedded scripts parse under
R 4.6.1 with the companion in front; the interpreter's own check drew, guarded, iterated and
captioned under R on a fixture plan. `version` 0.27.0 -> 0.28.0.

## Step 5 — retire what the plan makes redundant

*harness*: delete `sch/dev/extract/draw_sites.py`; in `convert.py` delete
`measure_draw_sites`, `draw_debt`, `draw_summary`, `_draw_lines`, `draw_worksheet`, the
`DRAWS_KEY`/`PLACES_KEY` handling, `_families`, `placement_debt`'s guard half, `_r_beside`,
`placement_worksheet`; keep `generated_drift`/`companion_paths`. Delete the tests that tested
them (`test_a_plotting_function_is_found_by_what_it_does.py` keeps the extractor halves; the
draw-site tests in `test_convert.py` go). `overfit.checks_of` loses the two sub-instruments.
`docs/DEVELOPING.md` §8 table: remove `each_draw_site_describes`, `places_every`,
`positions`/`axes`, `axis_field`, `enforced_by`; add the `plan` stage paragraph. Skill: a
section "The figure plan" — the entry, the three commands, "never edit a draw site".
*scProfile*: remove `places_every`/`axis_field`/`enforced_by`/`each_draw_site_describes` from
`DEVPOINTS.yaml`; `planner._prefix_map` stays until the last held-out plugin converts (say so in
its comment with the date); `onefile.py` template shows the entry shape; `docs/PLUGIN_DESIGN.md`
and `docs/MAINTAINING_PLUGINS.md` document it.

**Gate:** both suites green; `sch dev convert overfit` reports fewer corpus-1 instruments (the
ceiling-guard row is gone); rules 4 held; `wc -l` of `sch/dev` and of `kernels/cellchat.py`
recorded in the commit message against the numbers in this record (7,918 and 5,414).

*Amendment, 2026-09-12, before step 5 runs.* Two of the deletions listed above conflict with
the standing rule that the maker keeps reading the eight held-out plugins: `_families` and the
placement maps' half of `placement_debt` are what their `places_every` rule and prefix maps are
read by. They stay until the last held-out plugin is on the plan; what goes in step 5 is what
served hand-written R sites alone - the draw-site extractor, the draws debt and worksheet, the
ceiling-guard half (no plugin here has a hand-written site left, and the eight embed no R). A
hand-written site written against the rules is caught by scProfile's `test_plot_declarations`,
which requires every `.draw`/`npng`/`ndev` site to name an entry of the plan. The account
worksheet's plan form was done early (it was a live defect for the migrated plugin). Follow-up
still open from step 4: `Inventory` carrying every export and `native.account(every=...)`.

## Step 6 — `kind` binds the rules (ADR-0015's P4)

`standard.py`: for each entry with a `kind`, check the caption against the kind's rules where a
rule has a mechanical form — R3 (a cut names what it removed: the legend states a fraction or a
count), R10 (the panel names its unit: the host stamp is present). `figure.audit` gains nothing
(collisions are kind-independent). Report per kind on the page's standard line. cellchat's
entries get their `kind` in step 3 already; this step only makes the host read it.

**Gate:** `check --deep` green; the standard's own `selfcheck()` gains one mutation per new
criterion (a page that must fail it).

## Step 7 — the evidence

7a. enrichment's test phase: one PBS job that builds its environment, runs the fixture through
    the plugin, then `status --run` — the six run-side stages on a plugin the maker never ran.
    If it cannot run, remove `tests/smoke/plugins/enrichment.py` — unrun code is not test
    material.
7b. The third blind conversion, `docs/blind/0003-<tool>.md`, predictions first, the agent rooted
    in the clean room, on a tool whose figures the plan must carry. The cost line to beat:
    0 draw sites written by hand, and fewer maker defects than 0002's four.

**Gate:** records written; the memory file updated.

## What must not be done while executing this

- No second reader "for now". The fallback is the existing prose path or nothing.
- No `args` parser. If a step wants to understand R, it is the wrong step.
- No plan file beside the plugin, no plan editor, no knob system beside `config`.
- No hand-edit of a held-out kernel, whatever the migration would make easier.
- No cluster run without its predictions in the job header; no "rebuild part of a run".

## Status

| step | status | commit(s) | note |
|---|---|---|---|
| 0 record | done | harness (this commit) | |
| 1 spine on a sealed run | **authored, not submitted** | harness: `jobs/status_on_run.pbs` (jobcheck clean) | the cluster was unreachable from the workstation on 2026-09-12 (`ssh` timed out twice); submit when it answers, then grade S1-S8 in the seal |
| 2 schema, reader, validator, migrate worksheet | done | harness: this commit; scProfile: the commit after 043a60c | found on the way: the draw-site scan had been blind to cellchat's R sites since the companion move (wrappers read from the companion now); foreign wrapper spans hid a script's first sites; `DRAWN_BY` had two definitions; the record itself carried workstation paths |
| 3 cellchat declaration migrated | done | harness: this commit; scProfile: the commit after d8cb913 | the baseline held on files, vector copies and total, and moved on one position - see the amendment under step 3; `capacity --promised` on the sealed run is asked by the step 1 job (cluster unreachable again on 2026-09-12) |
| 4 generated sites, `ctx.rscript`, sites deleted | **4a-4d done locally; 4e not run** | harness: 582ff44, b366be4, 51c02e0 and this commit; scProfile: the four commits after 44a5541 | the companion carries the plan and its interpreter; every one of cellchat's 47 sites is `.draw(id)`; the host launches R; the plugin's R glue is gone; the manifest half of 4b is deferred to 4f (see the amendment); the reproduction waits for the cluster, unreachable all day on 2026-09-12 |
| 5 retire the extractor, maps, prose, glue | not started; one item done early | harness: the commit after ff60907 | `sch dev convert account` printed a `native_plots` block for a plugin that has none: `declared_of` reads the plan's `fn`s and skips, and the worksheet speaks the plan form (`"skips": {`, a USED function is an entry). The rest waits for 4e - and see the amendment: `_families` and the placement maps stay until the eight migrate |
| 6 `kind` binds rules | not started | | |
| 7 evidence: enrichment test phase, blind 0003 | not started | | |
