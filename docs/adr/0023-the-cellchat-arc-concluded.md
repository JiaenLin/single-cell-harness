# ADR-0023: the cellchat arc concluded - the short list, then the account before the eight

**Date** 2026-09-14. **Follows** ADR-0022 (what is worth fixing). **Status** in progress; the table at
the end is filled as each step lands. Opened after its first two steps had landed under its name,
which is recorded here rather than rewritten.

## Context

ADR-0022 closed with a short list: the harness's commit gate, one rerun to measure the process
count so `cores` reads answered, the three kinds the eye found on the plates that never render
the same twice, and then the eight held-out plugins. The instruction: go ahead, and conclude
properly before the eight.

## Decisions

1. **The harness gets the tool's commit gate**, the same shape: a versioned pre-commit hook that
   runs the suite and conform, installed per clone, with a conform check that says whether the
   clone has it.
2. **The three kinds are answered where they belong.** The host's role-shift panel states in its
   caption where arrows may cross, and a host panel can be stated against the caption the page
   prints under it, the same stated path the plugin's entries have. The two tool kinds go to a
   cold author: the differential role scatter was never passed the run's colour map (an edit);
   the scatter pair's placement is the upstream's own (a disclosure).
3. **One rerun** measures the process count, redraws the corrected scatter, carries the caption,
   and is sealed with its writing run, so that the maker can read the whole test phase answered
   on one run before the eight begin.
4. **The conclusion is a document, not a paragraph**: what the cellchat arc proved, what it did
   not, the numbers, the rules that held, and the plan for the eight, written so that the round
   that migrates them starts from it.

## Predictions

- **G1** conform reports the gate red on a clone without it and green on this one; the hook
  refuses a commit while the suite is red.
- **K1** after the rerun and a fresh look on the plates that render differently, the audit reads
  no open finding on the scan set, the role-shift finding stated by the host.
- **P1** the rerun records a process count per instance and the maker reads `cores` answered
  at the declared 2.
- **W1** the writing seal holds, and the maker reads test 8 of 8 on the writing run.

## Status

| step | state | where | what |
|---|---|---|---|
| 1 the commit gate | done | harness 7699531 | `setup/githooks/pre-commit` runs the suite and conform; `git config core.hooksPath setup/githooks` installs it; conform G1 reports it; the gate refused its own commit's first attempt on a doc-surface test (G1 held) |
| 2 the three kinds | done | scProfile f46ea44 (a host panel stated against the page's caption), 0213ebf (the role-shift caption), defeff8 (cellchat 0.34.0: the colour map passed, the scatter pair disclosed); the suite guard for one-kernel trees beside them | |
| 3 the rerun | done | harness d380cc6 (jobs/rerun_0010.pbs), PBS 711346 on compute1016, run key 20260914T083704Z__scprofile-defeff8__04_profile__rerun | SEALED in 37 minutes, 18 of 18, 945 figures; every instance recorded its process count (2 to 6) and the maker reads `cores` answered at the declared 2, sustained 1.18, peak 1.33 (P1 held) |
| 4 the fresh look, the host's stated answer, the seal | done | the run's copy under blind5/; writing run 20260914T092235Z__scprofile-defeff8__04_profile__written prepared | 122 looks carried; the host recorded its stated answer on the role-shift panel against the page's caption; a looker on the 17 plates that render differently; the previous run's written layer laid over: 6 standing, 5 stale, 4 unreviewed for a reviewer |
| 5 the conclusion | done | docs/THE_CELLCHAT_ARC.md | G1 and P1 held; K1 failed on the letter: after the looker on the 17 plates and the host's stated answer the audit reads one finding on one kind, a caption whose count does not match its bars, found by this run's fresh look - the next author's; W1 held on the seal (writing run 20260914T092235Z__scprofile-defeff8__04_profile__written, PBS 711365, 3 of 3) and not on the letter: the maker reads test 7 of 8, audited owing on that one finding. Two more defects met and fixed test-first: the portability suite on a one-kernel tree (twice more), and the agenda's defend task printing the claim command where a round was owed |

## Closed, 2026-09-14

The short list is done. The harness has the tool's commit gate and refused its own first commit
with it. The three kinds are answered where they belong: the colour map the differential scatter
was never passed is passed, and a fresh look confirmed the two plates agree; the scatter pair's
placement is disclosed; the role-shift panel's caption states where its arrows cross and the host
recorded the disclosure against it, the stated path now reaching host panels. One rerun measured
the process count and the maker reads `cores` answered at 2. Its writing seal held 3 of 3, and
fifteen claims stand on it.

The number: 36, 25, 16, 1, 6, 2, and now 1 - a caption whose count does not match its bars, found
by the fresh look on a plate that renders differently every run. That is the floor the arc ends
on, and it is the plugin author's, one kind long. The maker reads test 7 of 8 on the last run, the
one stage owing on that one finding.

The account for the round that migrates the eight is `docs/THE_CELLCHAT_ARC.md`. The eight begin
from it, one at a time, through the maker, the first the one most unlike cellchat.

