# 0001 — cellchat, from the tool's own namespace

**Date** 2026-09-10
**Job** `jobs/blind_convert.pbs`, PBS 710088, sealed
**Agent** none — the maker driven by the job script; the finished plugin hidden and compared

The first blind test was not a conversion by a cold agent: it hid the finished plugin, scaffolded
from nothing, pointed the maker at CellChat in the plugin's own environment, and asked whether
the accounting the plugin ships could have come from the maker rather than from somebody reading
CellChat's manual. Four predictions, in the job script.

**Result** 4 of 4 held: B3 **36 of 36** upstream plots the plugin accounts for are in the blind
inventory. An earlier run (710086) gave 31 of 37 and named six — `rankNet`, `rankSimilarity`,
`compareInteractions`, `identifyCommunicationPatterns`, `netClustering`, `interaction_lr` — of
which five were reached by replacing the name rule with a behaviour rule (a function whose body
calls one of R's own plotting entry points draws, whatever it is called) and the sixth is
`drawn_by: plugin` and correctly not in the tool's namespace.

**Cost** three maker defects found in ten minutes: the scaffold crashed for every kernel in the
repository; a second hand-kept copy of the action list; a companion glob that answered for all
nine plugins. Two cluster submissions.

**What it could not measure** — and the reason 0002 exists: the tool was the one the maker was
built on, so every instrument had been fitted to its conventions already. It proves the maker can
*read* a finished plugin. It says nothing about *making* one.
