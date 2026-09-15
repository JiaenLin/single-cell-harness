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
