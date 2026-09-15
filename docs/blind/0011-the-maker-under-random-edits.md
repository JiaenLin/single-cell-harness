# 0011 — the maker under random edits: the runs that check the maker, and a cold maintainer's replay

**Date** 2026-09-15. **Follows** docs/blind/0010 (the last turn on cellchat) and ADR-0026 (the
maker under random edits). **What is being tested** whether the maker reads a plugin's state
truly and cheaply: 42 random and targeted edits of `cellchat` through the maker's verb (steps 3
and 4, recorded in the ADR), five mutant runs on the cluster that say whether the run agrees
with what the maker said locally (step 5), and one cold maintainer given six fresh edits and the
maker's own documents, timed (step 6).

**The runs** the control `20260915T084449Z__scprofile-dc9bb46__04_profile__rerun` (PBS 711884)
and the mutants A `20260915T102223Z__scprofile-7d8b5dd` (PBS 712280), B
`20260915T102227Z__scprofile-a00ea49` (712289), C `20260915T102230Z__scprofile-490d0bb`, F
`20260915T102233Z__scprofile-161afbe`, G `20260915T102236Z__scprofile-1b24b79`, all
`__04_profile__rerun`, each on its own cellchat-only tree (`~/tools/scProfile-cconly-<class>`),
each with its predictions in the job's header (`jobs/rerun_0017.pbs` to `0021`).

**The agent** one Claude Sonnet, cold, in a clean room under the session's `blind14/`: the
harness at HEAD, scProfile as a cellchat-only `git archive` copy at main (0.41.0), no git, no
pristine twin (removed by the user's decision), the run copy of 0.39.0 for anything read
against a run; the maker's documents as its only instruction (`skills/plugin-maker/SKILL.md`,
`docs/MAINTAINING_PLUGINS.md`); six edits drawn with seed 20260916, one per class.

## Measured before the agent starts

- the verb, its followers and the readings of steps 1-4 in place (harness 21233dc, scProfile
  ea700a4 at the room's export; the K-m, K-n, K-o fixes landed after it);
- the room reads build 9 of 9 and `validate` clean.

## The cold maintainer's replay (step 6)

| | |
|---|---|
| the six edits (seed 20260916) | a side-effect entry's ceiling 2 -> 1; the report's subject; an entry added from the skips (`netVisual_embeddingPairwiseZoomIn`, the call decided from the recorded signature); a ceiling of 0; an entry's `axis` deleted; a code change the maintainer makes by hand - the coverage panel writing one extra file - then the maker read without a run |
| commands, seconds | ONE maker command per edit, 8-9 s each, for the five declaration edits; the refusal of the ceiling of 0 immediate; the code edit read by four static commands in 1.7 min |
| hand edits of the declaration | none for 1-5; the code edit to a function body only; the tree restored after each edit and diffed against a copy: byte for byte |
| refusals | one earned - `at_most=0`, the validator's, left standing; four not earned - the vocabulary guard's five family checks failed on the one-kernel tree before any edit (K-q, fixed) |
| what the maker said, judged true | the plan's delta and the layout's count after every edit exact to the file (150 = 164 - 14; 170 = 164 + 6; 17 = 19 - 2), the skip lifted on the add, PART on the deleted axis, the four static commands on the code edit each saying what it cannot read |
| defects of the verb it found | the added entry's draw site appended after the textually last `.draw(` - inside an unrelated if/else - with nothing printed about where (K-r, fixed: with its axis, at the top level, and SITE WRITTEN printed); a dict literal with an R call inside is two levels of shell quoting (`--add @FILE`, done); the layout block read "ok" on the line above the validator's refusal of the same value (the state after now follows the followers) |
| tokens, tool uses, minutes | 217k tokens, 79 tool uses, 18 min 10 s wall clock from the first `date` to the last |

Its own words on what was slow: quoting the `--add` literal; telling an earned refusal from a
pre-existing one by exit code alone; not seeing the site the verb wrote into hand-authored R.
All three are closed above.

## The runs (step 5), in one table

| run | node time | reused | the maker's word held? |
|---|---|---|---|
| control | 12 min 9 s (was 31) | 18 of 18 | S1 held; `measure` owes under reuse (2.9 GB fitted, 2.4 declared) |
| A | 12 min 1 s | 18 of 18 | the count heatmaps' size yes; an entry's `axis` moved nothing at run time (K-o); a ceiling of 2 on a single-file entry counted six plates no run holds (K-m) |
| B | 11 min 21 s | 18 of 18 | the rename, the title and the new `declared` stage exact; the renamed side-effect entry promised a file the tool never writes under that name (K-p) |
| C | 12 min 28 s | 18 of 18 | 128 plates to the plate; the added entry never drew - its site inside another entry's else-branch (K-r) and its call naming an unbound `pop` (K-n) |
| F, first cut | 11 min 35 s to failure | 0 of 18 | every unit re-inferred as forecast, then `NameError: Path` - the campaign's own patch, and nothing local had read the plugin's Python (K-s) |
| G, first cut | 14 s | - | `scprofile run` refused the unknown writing template at its door - a control the prediction had not credited |
| F, second cut | 11 min 52 s | 18 of 18 | the 18 extra files accounted for by nothing, the strength heatmaps redrawn from count and only the eye to see it; the forecast said MISS and the first cut had already written the store |
| G, second cut | 19 min 46 s | 0 of 18 | cost and measure owe after the run as predicted; the store had been overwritten by F's first cut and this run wrote it back; the `when` literal bit nothing |

## Defects of the mechanism, as they came

Twenty-eight fixed test-first the same day, listed in the ADR's step 3, 4, 5 and 6 rows: the
cache flag inherited from the audit reference, the serial compare phase, the double report, the
serial suite default; three of the verb's own; the eleven the kill pass turned red (K-a to K-l);
K-m to K-p and K-s from the runs, K-q and K-r from the cold maintainer, and the emitter running
the reference's tree for a tree of another name. Two recorded open: a fitted literal has no
static gate (the fixture run is it), and the maker cannot say which script holds a draw site.

## After the round: the open items closed (2026-09-15/16)

The user read the six open items and their impact and had them all closed, housekeeping
included, then one more run for review. The record is the ADR's "open items, closed" section;
the finding under it: the fixture gate that "was the gate" for a fitted literal had never
existed for this repository - the kernel point's tiers planned and refused "not ready in this
installation" on every ladder, cluster included, and had a plugin run, the fixture's neutral gene
names would have given a ligand-receptor database nothing to match. Three jobs for one: PBS
712312 ran cellchat on the synthetic cohort for the first time and read two things about itself
(twenty units for nine; a shape passed without running), 712313's gate refused the cohort and
said two true things and one untrue (a promise on an axis a one-factor design never launches;
a plan not told the roles, accepted on the installation's words), 712314 sealed in 14 min 9 s
with both shapes run end to end, 18 of 18 objects reused under the store's new key, the same
122 plates, and every machine stage done. Eleven more mechanism defects fixed test-first
(scProfile 11b0240 to f7e5a0d, harness f7e7c5e to 4f33e56); the plugin written only by the
tool's verbs (`--declare`, `--legend`): cellchat 0.42.0.

## Results

S1 held; V1 held; K1 held on the count and failed on the letter; R1 failed on the letter (three
of six runs held every prediction, each miss a state the maker had misread); C1 held on the
measure and failed on the letter (four refusals were the suite's own); B1 failed (28 against
15). The plugin is back to what it was plus three declared things the maker reads, every one of
them the verb's write. The eight held-out plugins are ADR-0027.
