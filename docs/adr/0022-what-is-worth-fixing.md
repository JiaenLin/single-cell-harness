# ADR-0022: what is worth fixing - the triage of what three turns left, done in one round

**Date** 2026-09-14. **Follows** ADR-0021 (the third turn). **Status** in progress; the table at the
end is filled as each step lands.

## Context

Three turns of the loop left a list: sixteen kinds surviving a fresh look, thirteen of them the
upstream's own drawings; three debts from ADR-0016 nobody paid; a cores declaration the tool
would write lower than it stands; a review round that accepts placeholder reasoning; rounds not
gated by a figure's open finding; and the eight held-out plugins still to migrate. The
instruction for this round: decide for each whether it is worth fixing, remove from the mechanism
what is unnecessary, and fix everything that is worth it now, without another long round.

## Decisions, one per item

1. **An answer that states the upstream's own drawing closes the finding - built.** A tool kind
   whose defect is the upstream's own drawing (a legend it does not draw, labels the plugin cannot
   reach through its plan) has no exit today but a looker's fresh look, which keeps finding what
   is there. The exit is honest disclosure: the author answers `--stated`, the statement must
   appear in the plugin's own declaration for that figure (the plan entry the page captions it
   from), and the finding closes without a fresh look because the check is mechanical - the words
   are there or they are not. A redraw reopens it as it reopens every look. This extends the
   answer path that exists; no new verb, no new ledger.
2. **The cores declaration is written by the tool - done as one command.** Sustained 2 on a
   declared 4; the maker prints the apply; run it.
3. **Two of the three ADR-0016 debts are already paid and are closed as such, not rebuilt.** The
   build status runs `validate`, which refuses a per-unit plugin with no `report.unit_metrics`
   (declare.py), so a second check in the status would be the duplicate the rules forbid. The
   tool's seal on an exported tree reads the commit from the tree's own HEAD file (`commit=d91a6c2`
   on every seal of this turn). The third - the legacy family and placement maps - is the
   migration's, and stays until the eight migrate.
4. **Dead mechanism is removed.** A scan for functions no code, test, doc or job names found five (a sixth was a
   template string, not a function): four in the harness's development suite and one in the tool's planner. Each is read before it
   goes; the suites stay green.
5. **Not worth fixing, recorded:** a review round's reasoning cannot be judged by a machine beyond
   its length, and the ledger is append-only so a probe round stays visible beside the real one;
   rounds on claims that cite a flagged figure are allowed by design (the claim was registered
   before the flag) and the contract says so. Nothing changes.
6. **Not this round:** the eight held-out plugins migrate one at a time through the maker, in
   their own round, after this one closes the cellchat worksheet.

## Predictions, before any change

- **S1** a stated answer whose statement is not in the plugin's declaration is refused, naming
  the entry; with it there, the finding closes, the figure reads reviewed, the worksheet drops it,
  and a redraw reopens it - each a check that fails on the mechanism as it is.
- **S2** a cold author closes the sixteen kinds in one pass with stated answers and plan edits
  only, no drawing code; the audit on the run's copy reads no open finding on the scan set; no
  hand edit of the plugin.
- **C1** `cores` reads 2, written by the tool's declare; the build stays 8 of 8.
- **D1** six functions removed; the gate of each repository stays green; the rules of the round
  hold.
- **R1** one rerun carries the stated captions into a sealed run and its writing seal holds; the
  maker reads test 8 of 8 on it.
- **B1** at most two defects of the mechanism, each fixed test-first the same day.

## What must not be done

No hand edit of `kernels/cellchat.py` except the paste of the author's answer; nothing to the
eight held-out plugins; no fix beside the mechanism that exists; no run on a login node; no
prediction rewritten after the numbers are in.

## Status

| step | state | where | what |
|---|---|---|---|
| 0 record | done | this commit | |
| 1 the stated answer | done | scProfile 71b2d3d | `review --answer ... --stated`: refused until the sentence is in the plan entry's legend in the plugin's file; then the finding closes without a fresh look, the figure reads reviewed, the worksheet drops the kind, a redraw reopens it; nine checks test-first; the worksheet prints it as the third way. S1 held. (The cores declaration of step 2 rode in this commit: it was staged when the gate blocked its own commit on the then-red suite, and the stated commit picked it up - one commit carrying two changes, recorded rather than rewritten) |
| 2 cores by the tool; the ADR-0016 debts | done | scProfile 71b2d3d (the `cores` line) | `capacity --cores --declare cellchat` wrote `"cores": 2` from the run's sustained 1.13; validate 0/0, build 8 of 8 (C1 held). ADR-0016's debts: the build status runs `validate`, which refuses a per-unit plugin without `report.unit_metrics` - closed as covered; the seal reads the tree's HEAD file (`commit=d91a6c2` on every seal of ADR-0021) - closed as done; the legacy family and placement maps stay until the eight migrate |
| 3 dead mechanism removed | done | harness b6ceb57; scProfile 1ee0147 | five functions no code, test, doc or job names: plan_of_work, code_only, for_kind, set_path (harness), gap_text (tool); the job checks the scan also listed are registered by a decorator and a sixth was a template string, both kept; suites, conform and the round's rules green (D1 held) |
| 4 the author's pass on the sixteen | done; one finding left, the host's | scProfile 1cbb5ae (author room at 1ee0147); the run's ledger carries 28 stated records | the cold author closed the fifteen kinds that are its own in one pass - 28 stated records, eleven legends carrying the disclosure, no drawing code, no refusal, 0.32.0 to 0.33.0; the audit on the run's copy reads 1 open finding on 1 kind: the host's role-shift panel, the data's crossing arrows, carried on identical bytes. S2 held for the fifteen and fails on the letter for the one the mechanism has no stated path for (a host panel has no plan entry); the author found the check reading the whole entry, tightened to the legend (scProfile 5575126) |
| 5 the rerun and the seal | done | writing run 20260914T075751Z__scprofile-6f2493d__04_profile__written, PBS 711341 SEALED 3 of 3 | harness 38c7589 (jobs/rerun_0009.pbs), PBS 711309 on compute1016, run key 20260914T055758Z__scprofile-1cbb5ae__04_profile__rerun; PBS 711296 was system-held on compute1017 after 21 failed starts beside a job holding 600 GB there, deleted, its empty directory retired to the archive. PBS 711309 SEALED on compute1016 in 35 minutes, 18 of 18, 945 figures. What the carried run found, all three fixed test-first in scProfile 5cac2f6 (one commit, the files staged together): the carry kept the FIRST sibling's record per image, so eighteen figures a later looker had settled came back as needing a look; seventeen plates of the scan set render differently on every run, so a stated answer bound to bytes reopened on six with nothing changed but the pixels - a stated answer now carries by plan entry while the legend holds the words; and at the declared share of 2 a tree of three processes each honouring it summed to a one-second peak of 5.9, which the burst rule read as threads uncapped - the sampler now counts the tree and the threshold is the share times that count (the old rule where no count was recorded, so this run still reads cores owing). A fourth, of the fix itself: the by-entry carry read the plugin's declaration once per figure and the worksheet took two minutes on 945; once per kind now, three seconds (scProfile, the commit after 5cac2f6). After one looker on the ten redrawn plates the audit reads 6 findings on 3 kinds: the host's carried one, a colour-map mismatch on the difference scatter, and four on the scatter pair, which was never stated - the next author's. A reviewer re-defended the seven claims whose cited plates were redrawn and found two more defects, five and six of this round (scProfile 0f97bf7): staleness was read from the hashes the claim record carried, so no round could clear it and `next` printed the same remedy before and after; and a written layer laid over a run put an older claim record below a newer one for the same id, where file order made it win. A round now records the figures as it saw them, the most recent record that saw them is the reference, and the latest claim record by time decides. B1 (at most two defects) failed: six, each fixed test-first the same day | R1 on the job: the stated legends carried into a sealed run, every figure byte-identical, the looks and stated answers carrying |
| 6 the record | done | this table and the closing below | S1, C1, D1 held; S2 held for the fifteen kinds that are the plugin's and fails for the one the mechanism has no stated path for; R1 held on the seal and not on the letter (test 6 of 8, cores by the old rule and audited on six findings); B1 failed at eight |

## Closed, 2026-09-14

Everything the triage called worth fixing is fixed, the two ADR-0016 debts already paid are closed
as such, five dead functions are gone, and the round found eight defects on the way, every one
fixed test-first the same day: the carry kept the first sibling's look per image instead of the
latest; a stated answer bound to bytes reopened on plates that render differently every run; the
burst rule read a tree of three capped processes as threads uncapped; the by-entry carry read the
declaration once per figure; a round could not clear staleness and file order decided between two
claim records for one id; a stated disclosure counted as a look; a killed job sealed SEALED. Two
of those were of this round's own fixes, which is what the loop is for.

**What held.** The stated answer exists and works as designed: a cold author closed the fifteen
kinds that were the plugin's in one pass with 28 disclosures, no drawing code, no refusal, and
the audit read one finding, the host's carried one (S1, S2 for the fifteen). The cores
declaration was written by the tool at 2 (C1). The mechanism is five functions lighter and green
on both repositories (D1). A rerun carried the stated legends into a sealed run, 945 figures, 18
of 18, and its writing seal held all three predictions (S1 of the seal, R1 in the half that is
the seal's).

**What did not.** R1's other half: the maker reads test 6 of 8 on the carried run, because the
burst rule's process count is measured only by a run made after the fix, and because the eye,
on the seventeen plates that render differently every run, found six things on three kinds - a
colour-map mismatch between two upstream scatters, four crowded label pairs on the scatter
pair, and the host's crossing arrows. B1 failed at eight against two. And two commits landed on
the harness while its suite was red: the harness has no commit gate of its own, which the tool
has had since ADR-0015; that gate is the one mechanism this round found missing and did not add.

**The number.** 36, 25, 16, then 1 by disclosure, then 6 after the eye on the plates that never
render the same twice. The audit converges to what the eye finds anew each run on those
seventeen, which is the honest floor for a plugin over an upstream that draws with a random
start; the disclosure closes what the plugin cannot draw differently, the worksheet keeps the
eye's later words, and the next author's list is three kinds long.

**Next, in order, none of it a long round:** the harness's commit gate; one rerun to measure the
process count and read `cores` answered; the three kinds; then the eight held-out plugins, one at
a time through the maker.

