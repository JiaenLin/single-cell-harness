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
