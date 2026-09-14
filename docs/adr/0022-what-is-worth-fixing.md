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
| 1 the stated answer | | | |
| 2 cores by the tool; the ADR-0016 debts | | | |
| 3 dead mechanism removed | | | |
| 4 the author's pass on the sixteen | | | |
| 5 the rerun and the seal | | | |
| 6 the record | | | |
