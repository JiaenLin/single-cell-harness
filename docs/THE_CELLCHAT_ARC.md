# The cellchat arc, concluded - what nine ADRs proved before the eight plugins

*Written 2026-09-14 for the round that migrates the eight held-out plugins. It states what the
harness and the tool can now do, what was proved and by what evidence, what was not, the numbers,
the rules that held, and where the next round starts. ADR-0015 to ADR-0023 are the record; this
is the account.*

## The claim, and the evidence for it

**The plugin maker is the deliverable, and a plugin is its output.** From ADR-0015 on, one plugin
(cellchat, a wrapper over CellChat in R) was built and rebuilt only through the maker's stages:
the plan carries the call (ADR-0016), the run drives its own writing (ADR-0017), the audit repairs
what it can and the run measures what it uses (ADR-0018), and the loop from author to sealed
writing run closes with no person in it (ADR-0019). Five cold authors edited the plugin's file in
clean rooms with no git and no way to ask, and every one of their answers was pasted, gated and
committed by the maker's own commands. Nobody hand-edited the plugin. The eight other plugins
were never touched, so they remain the evidence that the maker generalises.

**The loop runs end to end on cold agents.** Four turns (ADR-0019 to ADR-0022): author, rerun
through an emitted job on the scheduler, two lookers on a split the tool prints, the audit's
worksheet, a writer, a reviewer, a render, a writing seal on the cluster. Every dispatcher command
was one a status, a worksheet, a refusal or an ADR printed. Every turn sealed. Every defect met
was fixed test-first in the layer that exists, the same day: 17 in the first turn, 8, 2, 8, and
then the short list's own.

**The audit converges to an honest floor.** Kinds surviving a fresh look: 36, 25, 16, then 1 by
disclosure, then 6 found anew on the seventeen plates the upstream draws with a random start, then
2 after the fifth answer, then 1 on the final run. The number stopped falling on its own when
what was left was the upstream's own drawing; the stated answer (ADR-0022) closes those by
disclosure in the legend, checked mechanically, and the worksheet keeps the eye's later words
where the disclosure understates. What remains each run is what the eye finds anew on plates
that never render the same twice, and that has a looker's cost, not an author's.

**The written result stands on its figures.** The composed ratio claims cite the plate whose
caption states their totals (ADR-0021); a writer's claims are bound to figure hashes; a round
records what it saw, and staleness is a figure changed since the latest record that saw it
(ADR-0022). On the last reviewed run every claim stood.

**The maker reads the whole test phase on one run but one stage.** On the final run: memory, cores, cost, promised, looked at, written and delivered answered; audited owing on the one finding above.

**The run measures what it uses.** Memory, wall and CPU per instance, a cores model and a cost
band per plugin, and the declarations written by the tool's own command from the run: memory
(ADR-0018), cost (ADR-0020), cores (ADR-0022), with the burst held against the tree's process
count (this ADR). The plugin caps its threads to the share it is given: a peak of 2.4 on a share of
4, where it once burst to 62.

## What was not proved

- **That the maker generalises.** One plugin, five authors, all cellchat. The eight held-out
  plugins are the only evidence, and it is unspent.
- **That the audit reaches zero.** It reaches the floor of nondeterministic rendering plus the
  data's own crossings, both stated rather than cured.
- **That a written result is right.** The loop proves a claim is defended against its figures by a
  second agent; it does not judge the science, and the reviewer's reasoning is checked only for
  length.

## The numbers of the last turn

| what | value |
|---|---|
| runs sealed on the cluster in the arc | 11 reruns and 6 writing runs, every one through a validated job |
| cellchat version | 0.28.0 to 0.34.0, six pasted answers |
| kinds surviving a fresh look | 36 → 25 → 16 → 1 (disclosure) → 6 (nondeterministic plates) → 2 → 1 (the final run: one caption's count against its bars) |
| claims on the last reviewed run | 15, all standing (final run `20260914T083704Z__scprofile-defeff8__04_profile__rerun`, writing run PBS 711365 sealed 3 of 3) |
| cores | declared 2 by the tool; on the final run sustained 1.18, peak 1.33 on a share of 2, process counts 2 to 6, answered |
| defects of the mechanism fixed test-first across the arc | 17 + 8 + 2 + 8 + 4 (ADR-0019 to ADR-0023) |
| rules of the round | 4 held, 0 broken at every commit; 0 fitted literals; held-out plugins untouched |

## The rules that held, and should hold for the eight

1. A plugin is maker output; a human or an agent edits it only by pasting a cold author's answer
   that the gates accepted. The vocabulary check against the cohort is part of the paste.
2. The eight are held out until their own migration; touching one for any other reason spends the
   evidence.
3. The mechanism is fixed where it exists, never beside; every fix has a check that failed first.
4. Every tool invocation on the cluster goes through a validated job from a submitter; run
   directories are made by the submitter; retired trees go to the archive.
5. Predictions are committed before the change and graded as they fall; a failed prediction is a
   finding.
6. Commit only when green: both repositories now have a gate that refuses otherwise.

## Where the eight start

Each of the eight migrates one at a time through the maker, exactly as cellchat did: the maker's
status names the stage, the worksheet names the finding, the stated answer names the upstream's
own. The first plugin to migrate should be the one most unlike cellchat - a Python plugin with no
R, no compare phase - because that is where the maker's assumptions are least tested. Expect the
first migration to find defects of the mechanism at the rate cellchat's first turn did, and the
later ones at the rate of its last.
