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
| maker defects found | **4** real (extractor 3 of 5; `promised` read done with nothing run; the declaration tier demanded a measured key; `figure_axis` unknown to scProfile's checker), 1 the agent inferred and the maker does not actually do, 1 correct refusal the agent read as a defect |
| decisions that needed a person | 12 by the agent's count, of which 10 are method decisions a plugin author must make and 2 are the workflow's to absorb (figure axis/position defaults; `duplicate_of` versus "the default is use it") |
| commands run | ~35 maker/host CLI invocations; ~140 tool calls in all |
| job submissions | 0 (build phase, workstation) |
| edits outside the clean room | **0** — `git status` clean in both repositories |
| agent | Claude Sonnet, 505k tokens, 50 minutes, 155 tool uses |

## Results

*(written after the run; nothing above this line changes)*

The agent reached **build 9 of 9** in the clean room alone, `validate` 0 errors, and reported
the test phase as unasked. It wrote a 922-line plugin with a real `run(ctx)` — per-population
signal-to-noise ranking, `gseapy.prerank` against a library resolved through
`gseapy.get_library`, four declared figures with legends at every emit site, six upstream plots
accounted (four used, two `duplicate_of`), a `selftest` that plants a gene set and recovers it
(NES +1.52, run by the agent under a hand-built `FakeCtx` in the venv), and a `refuse` on fewer
than two populations. It found four upstream defects in gseapy 1.3.1 and recorded them in the
plugin's `upstream.gotchas`. It edited nothing outside the clean room.

| | held? | what was measured |
|---|---|---|
| **B1** scaffold owes everything | **partly** | 8 of 9 build stages owed, not 9: `freshness` read done because the clean room has no git and CANNOT SAY is not a debt — correct by its own rule, wrong in my prediction. And `promised` read **done** with nothing run, because it fills a field that was present. That second one is a maker defect, not a prediction error: see below. |
| **B2** inventory 3 of 6 | **held, list wrong** | 3 found, exactly as measured beforehand. My list of the missed three was wrong in one member: `ringplot` is not exported from `gseapy` and its 1.3.1 body is a no-op that draws nothing — the agent measured that; `enrichment_map` returns two tables for an external layout and draws nothing either. The tool's drawing surface is **5**, and the maker found **3 of 5**. |
| **B3** the agent does not notice | **failed, in the right direction** | The agent read `gseapy/__init__.py` and `plot.py` in the venv, found all six exports, accounted for every one, and reported the extractor gap as its first maker defect. The inventory line says "a HEURISTIC, because this package has no pl/plotting submodule", and the agent acted on that word. The skill was sufficient for this agent; whether it is sufficient for a weaker one is not measured. |
| **B4** zero edits outside | **held** | |
| **B5** build 9 of 9 alone; test phase unasked | **held** | `memory_gb_*` left undeclared: "honesty over a green ladder", the agent's words. |
| **B6** validate 0; ladder exit 3 with rules unaskable | **failed twice** | `validate` exited 0 (3 warnings). The ladder exited **2**: the `declaration` tier FAILED on `memory_gb_per_100k` — a key the scaffold's own template says to measure from a run and never invent — and stopped the ladder, so every other tier could not run without `--keep-going`. Second, the fixture tiers **skipped** on the workstation (no anndata in the host interpreter), which I should have predicted. The `rules` tier failed rather than could-not-run: `end_to_end` reported the complement of the held-out set as `cellchat, enrichment` — a **correct refusal** of a tenth kernel the round's declaration does not admit, and the reason the plugin lands as test material. |
| **B7** overfit over ten | **held** | 12 → **9** fitted literals (`heatmap`, `barplot`, `scatter` became conventions shared by two members); `dotplot` reported against `enrichment` from `_NAMEY`. |
| **B8** a workflow defect that is not the extractor's | **held, three** | (i) the declaration tier versus a measured key, above; (ii) scProfile's validator warned "`report` carries unknown key(s) figure_axis" about the key the maker's placement stage had just demanded — `figure_axis` was `figure_position`'s sibling, one edit behind, read by the planner through `report.get` rather than the accessor the drift guard scans; (iii) the agent had to read `scprofile/planner.py` and `compose.py` to learn that an undeclared axis defaults to `unit` and an undeclared position to `contrast` — the placement worksheet prints the allowed values and not the defaults, because the defaults are the host's and the maker cannot know them. |

**What the agent reported as a defect and is not.** It wrote that re-running `account` "would
report" its three source-verified entries as "stale or misspelt". It did not run it; the
worksheet's actual line reads *"either the upstream dropped them or the inventory pattern
stopped matching. Both are worth knowing; neither is fixed by deleting the line"* — already
hedged. Recorded because an agent's inference about a message it never saw is a different kind
of finding from a message it quoted.

**What the round changes because of this run**, each routed by the rules:

- *maker* — the extractor gained a third rule: a function whose body writes a figure file
  (`savefig(`) draws its own figure. Measured before adding it on the three packages the venue
  held: gseapy +2 (exactly `gseaplot`, `gseaplot2`), pandas.plotting +0, matplotlib.pyplot +1
  and that one is `savefig` itself. gseapy now reads **5 of 5**.
- *maker* — a command stage with no run is UNASKED whether or not it also fills a field.
  `promised` had been the inventory stage's question answered twice and its own answered never.
  cellchat's own status now reads `test: 0 of 6` without a run, which is the truth.
- *maker* — the declaration tier no longer demands a key a test-phase stage fills; it prints
  "not declared yet: filled by the `measure` stage from a run". The ladder on the agent's plugin
  now reaches every tier, with `rules` the only failure and that one correct.
- *host, in place* — `figure_axis` is in `declare.REPORT_KEYS`, and the planner reads both
  placement maps through `report_get`, so the guard that scans consumers can see the next
  sibling.
- *test material* — the plugin and its SPEC land in scProfile at `tests/smoke/plugins/`, beside
  `silhouette.py`, unmodified: what the agent produced is the evidence. Not a tenth shipped
  method; the round's `end_to_end` does not admit it and was right to refuse.
- *not fixed, recorded* — the plugin's `selftest` passes `organism="human"` to `prerank` on a
  synthetic gene-set dict where gseapy ignores it; `run` uses `ctx.organism`. The leak tier
  would have flagged the literal, and the leak tier skipped because the venue supplied no word
  list. The plugin is test material and stays as produced.

**Venue defects, for the next record.** The agent's session inherited the harness's git context,
which showed it the *title* of the commit carrying these predictions; it chose not to open it
and said so. Root the next agent in the clean room. The fixture and leak tiers cannot run on
this workstation (no anndata; no site word list), so the ladder's answer here is four tiers of
eight. The test phase — the four loop stations and `measure`/`promised` on a real run of this
plugin — needs an environment build and a fixture run on the cluster, and is a separate step.
