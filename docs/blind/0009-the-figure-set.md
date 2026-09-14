# 0009 — the figure set: the plan under budget, named, composed, written to

**Date** 2026-09-14. **Follows** docs/blind/0008 (the loop's third turn) and ADR-0024 (the figure
plan under budget). **What is being tested** whether the plan the maker trimmed to the layout
runs, whether the figure set the report builds from it - every plate named by its place in the
argument, laid into lettered figures with composed legends - is what a cold writer writes to in a
journal's register, and whether a cold reviewer leaves the claims standing.

**The runs** `20260914T133714Z__scprofile-0ec4852__04_profile__rerun` (PBS 711438, cellchat
0.35.0, the count half of L3, sealed FAILED on figure-side products and a side-effect file, both
the mechanism's) and `20260914T145501Z__scprofile-ffa9c5c__04_profile__rerun` (PBS 711528,
cellchat 0.36.0, SEALED in 29 minutes); the writing run
`20260914T171426Z__scprofile-d318075__04_profile__written` (PBS 711584).

**The agents** Claude Sonnet, cold, in clean rooms under the session's `blind12/`: scProfile as a
cellchat-only `git archive` copy (re-exported at each commit the round made), the harness at
HEAD, no git anywhere; the run's copy; the roles: two lookers, a writer, a reviewer. No author
this round: the plugin's only edits were the maker's verb's output (`sch dev convert layout
--apply`, twice, the second as `--as-version 0.36.0` to the author's 0.34.0 file).

## Measured before any agent starts

- the plan under the layout: 24 entries (one a side-effect accounting entry), 2 per sample, 5 per
  arm, 10 per contrast, 16 over the interaction, 3 for the cohort; `report.host_panels` naming
  the design grid, the census, the totals and the interaction; 119 plates predicted;
- the second run drew 119 plates exactly, the four marginal pools nothing, no arm a per-sample
  panel; the figure set: 119 copies under `report/figures/<axis>/<subject>/<NN>_<what>.png`,
  15 main figures and 20 supplementary, no space, pipe or drawing-side prefix in any path;
- cores peak 2.46 on 2, `over_share` false; cost high; memory at or under the declaration;
  `capacity --promised` answered; 50 of the scan set's 77 plates carried looks by content hash.

## Cost, filled in after

| | |
|---|---|
| lookers: figures handed, recorded, refusals, defects marked | 27 handed in two shards (14 and 13); 27 recorded, 0 refused, 10 marked defect (4 and 6); 417k tokens, 78 tool uses, 13 and 20 min |
| audited after the fresh look | 5 open findings on 3 kinds (TOOL 2, PLUGIN 1) after 6 closed by disclosure; two of the three kinds are the host's own defects wearing the tool's and the plugin's names - the colour map and the caption suffix - fixed test-first and answered on the ledger for the next rerun's fresh look |
| writer | brief, agenda and the maker's status read; 4 claims recorded citing 9 clean plates, 0 refused; a 1,226-word Results in the register carried in on the first `--write`, 0 refusals, 0 defects reported; wrote around four whole figures because one panel of each was flagged and the citation check keyed on the number; 201k tokens, 38 tool uses, 18 min |
| reviewer | 13 of 13 claims standing, every number checked against `rank_net_comparison.csv` and `cellchat_two_scale.csv`, 27 plates opened; 0 refusals, 0 defects; 283k tokens, 73 tool uses, 16 min |
| defects of the mechanism | 14 fixed test-first the same day: 4 found by the first run (the plugin-side axis gate, the marginal pools, the redraw's expected products, the side-effect entry), 4 by the page (the interaction heading, the contrast title, greedy chunking, the cohort's n), 2 by the lookers (the colour map's gap, the colour-map sentence on a scale-coloured plate), 3 by the writer's path (the brief's verbatim headings in the design's tags, the citation check by figure number, the composed section not rebuilt with the page), 1 by the page again (the record's colour sentence in a legend) |
| agents, tokens, wall time | 4 cold agents: 901k tokens, 189 tool uses, 67 min of agent time; two submissions of the rerun (33 and 29 min on the node) and one writing seal |

## Defects of the mechanism, as they came

1. The host's own emit path did not hold a plugin-drawn panel to its axis; every arm drew the
   per-sample census and the group axis read six against five (PBS 711438). Fixed: `Context`
   reads the plan's axis per entry (6e8b58a).
2. A marginal pool drew the whole group set. Fixed: the resolver names the pools, the run files
   them under `margin`, neither language draws for one (6e8b58a).
3. The redraw's expected products included a plate's source table and the per-sample page;
   163 missing, every table of the analysis present. Fixed in the job emitter (harness 2cacda2).
4. The trim dropped the side-effect entry for the tool's rank estimation; the call still ran and
   `capacity --promised` refused 24 files. Fixed: `generated: False` is neither counted nor
   dropped; the trim re-applied to the author's file as 0.36.0 (harness 2cacda2, ffa9c5c).
5–8. On the second run's page: the interaction heading named one pair twice; a contrast title
   without the factor bracketed; seven plates of one direction laid greedily into six and one;
   the cohort's n missing (49c8613).
9. Fourteen labels given hues 0.6 degrees apart and called distinct (two lookers): the map keeps
   a gap of eighteen degrees, measured around the circle (dc48927).
10. The colour-map sentence on every caption, false on a per-programme scatter (two lookers):
   only on a kind that colours by population (dc48927).
11. The brief's verbatim headings were `SIMPLE age | diet = chow` - the source of the
   manuscript the user called unprofessional; the register's headings now, and the panel's
   section names with them (6c5d947).
12. A composed section was not rebuilt when the page was (6c5d947).
13. The citation check keyed on the figure number and refused a clean panel for a flagged
   sibling; by panel where a panel is named (b0a8260).
14. The record's colour sentence, with its digest and "this run", printed under every panel of
   every contrast on the page: in the register on the legends, and only where true (8c30092).

## Results

| prediction | held? | what happened |
|---|---|---|
| L1 | held | the verb refused the untrimmed plan before any change (step 1) |
| L2 | held | the trim written by the verb, twice, no hand edit; every gate green |
| L3 | held | 119 plates, every path on the rule; cores 2.46 peak on 2 |
| L4 | held | composites, legends and Methods from declarations alone; four composition defects found on the run and fixed |
| L5 | held | a cold writer's Results in the standard; 13 of 13 claims standing |
| B1 | **failed** | fourteen against four; every one found by a run, a page or a cold agent, every one fixed the same day |

What the user's decision left to the mechanism and the mechanism decided differently: the host's
difference matrices were not kept. The option's letter kept them as something CellChat cannot
draw; CellChat draws them, and keeping them would have cost the tool's strength heatmap two of a
contrast's ten. `host_keep` in the tool's DEVPOINTS is the one word that restores them.

What is left for the author's next pass, recorded rather than done: `shows: result` on the
strength circle; the interaction family's item order; the role heatmap's colour floor as a
disclosure; the plan legends' capitalised emphasis. Then the eight held-out plugins.
