# 0002 — gseapy, by a cold agent, on the workstation

**Date** 2026-09-12
**Tool** [gseapy](https://github.com/zqfang/GSEApy) 1.3.1 — gene-set enrichment; Python; no
kernel in the family wraps it, and its plotting convention is one the maker has never met: the
module is `gseapy.plot` (the extractor looks for `pl`, `plotting`, `plots`), three of its six
plotting functions are named by suffix (`gseaplot`, `ringplot`) rather than prefix, and those
three write their own file (`ofname=`) and take no axes.
**Agent** Claude Sonnet, cold: a clean-room copy of scProfile at `HEAD`, the harness on
`PYTHONPATH`, the plugin-maker skill, a workstation venv holding gseapy as the tool's interpreter,
and nothing else. The agent may read the tool's documentation. It may not edit the harness or the
real scProfile checkout; if the maker is wrong it records that and works around it in the plugin.
**Venue** the workstation, build phase only. No cluster job, no cohort (the round's rule 4: end to
end is cellchat). The test phase — a run of the plugin on the fixture — is a second step, if the
build phase earns it.
**Where the work lands** the clean room is a copy under the session scratchpad and is not a home;
the plugin the agent produces is captured into scProfile's `tests/smoke/plugins/` as test
material beside `silhouette.py`, the agent's report and the measurements into this file.

## Predictions, written before the agent starts

- **B1** Scaffold → `status` reads every build stage owing and every test stage `RUN?`. Zero
  decisions.
- **B2** The inventory in the tool's own interpreter finds **3 of 6**: `barplot`, `dotplot`,
  `heatmap` — the three that take `ax=`. `gseaplot`, `gseaplot2` and `ringplot` are missed:
  suffix names, no axes, they write their own file. **Measured before the agent ran** (the maker
  pointed at the venv from cellchat's declaration, with `--tool gseapy`): exactly that, "3 of 3
  were reached by the signature rule". This is maker defect #1, priced 3 of 6, and it is NOT
  fixed before the run — the run is to find out whether the workflow surfaces it.
- **B3** The agent does not notice the three missing functions on its own. The skill tells it to
  read the tool's documentation for `upstream.docs` and to account for every function the
  inventory lists; it does not tell it to compare the inventory with the documented plotting
  surface. If it does notice, the skill was sufficient and this prediction fails in the right
  direction.
- **B4** Zero edits under `sch/` and zero under the real scProfile checkout. Measured by `git
  status` in both after the agent stops.
- **B5** The build phase reaches done in the clean room by the agent alone, including the
  judgement stage — the agent is the person here. The test phase stays `RUN?` and the agent
  reports it as unasked rather than done. **B5b** `memory_gb_base` / `memory_gb_per_100k` are
  left undeclared, not invented: the template says measure once and declare, and the validator
  says a rate alone is worse than nothing.
- **B6** `scprofile validate enrichment` exits 0 in the clean room. `sch dev check --point kernel
  --name enrichment` there: declaration ok, fixture tiers ok (`plan` refuses "not ready in this
  installation", which the declaration accepts), the `rules` tier **could not run** — the clean
  room has no git, so the two history rules cannot be asked — and the ladder exits 3, not 0 and
  not 2.
- **B7** `sch dev convert overfit` over ten artefacts: `heatmap` and `barplot`, today attributed
  to cellchat, become conventions shared by two members and drop out; `dotplot` appears as a
  literal fitted to the new member (it is in `_NAMEY`). Fitted literals go from 12 to between 10
  and 12, and `dotplot` is named against `enrichment`.
- **B8** At least one workflow defect that is not the extractor's: a place where the status, a
  worksheet or the skill left the agent without the next command, measured from the agent's own
  report of where it was unsure.

## Cost, filled in after

| | |
|---|---|
| maker defects found | |
| decisions that needed a person | |
| commands run | |
| job submissions | 0 (build phase, workstation) |
| edits outside the clean room | |

## Results

*(written after the run; nothing above this line changes)*
