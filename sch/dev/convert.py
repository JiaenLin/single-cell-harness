"""Turning somebody else's tool into a plugin, and picking that job up where it was left.

A HALF-BUILT PLUGIN AND A RAW TOOL ARE THE SAME INPUT AT DIFFERENT POINTS ON ONE LINE. Converting
a repository is resuming from zero. That is not a convenience: it is the reason resume works at
all, because it makes resume the ONLY mode and there is no second code path that only runs the
first time and is therefore never exercised.

THE STATE IS THE PLUGIN FILE. Nothing is remembered between invocations - no lock file, no journal,
no `.convert-state.json` to go stale against the thing it describes. What remains to be done is
computed from the declaration every time, by asking which fields still carry the scaffold's
placeholder. A conversion interrupted by a lost connection, a different machine, or four months is
resumed by reading the file.

WHAT THIS MODULE DOES NOT KNOW. It names no tool, no field and no plugin format. Which stage fills
which field is declared by the repository being converted into, in its own `DEVPOINTS.yaml`, for
the same reason `sch dev` reads everything else from there: this suite serves five repositories and
a stage list written here would be one repository's shape imposed on the other four.

WHY THE STAGES SPLIT WHERE THEY DO. Every stage is either something a machine can extract from the
tool's own source, or something only a person or an agent can answer - and never both. The
mechanical ones are commands that run in seconds and can be re-run. The judgement ones are asked
ONCE, with the evidence already gathered, which is the whole efficiency argument: the expensive
participant should be answering "should this wrapper be using scvelo's 34th plotting function",
not finding out that scvelo has 34.
"""
from __future__ import annotations

import ast
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from . import points as pts

#: Where a point declares its conversion, inside its entry in DEVPOINTS.yaml.
KEY = "convert"
#: What a stage entry must carry.
STAGE_REQUIRED = ("name", "fills")
#: What a stage declares when its work is not finished while a panel goes out undescribed.
#:
#: DELIBERATELY NOT `each_item_declares`, AND THIS IS THE SECOND ATTEMPT. `item_gaps` walks a
#: stage's `fills` and stops at the FIRST field whose value is a list; `report.figures` is a
#: non-empty list in all nine of the plugins this was built against, so anything hung behind it
#: was unreachable and a design that put draw sites there reported nothing, forever, in silence.
#:
#: The deeper reason it does not belong there: `each_item_declares` rules on entries of a
#: DECLARED list, and a draw site is not declared anywhere. It is MEASURED FROM SOURCE - the line
#: in the plugin where a panel is produced - which is a different kind of fact with a different
#: failure mode. A declared list can be empty because the author has not written it; a measured
#: one can be empty because nobody looked, and only the second needs `complete=False`.
DRAWS_KEY = "each_draw_site_describes"

#: A stage that rules on WHICH of a plugin's figures a result is written from, and on how many of
#: each family it may draw. Both are properties of the declaration, so this is a build stage.
PLACES_KEY = "places_every"
#: A stage may ask whether this plugin USES anything its declaration does not name,
#: and whether the field this repository calls its reuse key has kept up with the code.
#: Both were commands with no stage, so nothing gated on either.
LOAN_KEY = "every_requirement_declared"
VERSION_KEY = "version_is_current"


class ConvertError(Exception):
    """The declaration cannot be read, or does not say enough to convert anything."""


def _dotted(spec, path):
    """`wraps.tool` out of a nested declaration, or None. Never raises on a missing branch."""
    cur = spec
    for part in str(path).split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def plan(doc, point_name):
    """(placeholder, upstream_path, [stage]) as the target repository declares them."""
    pt = pts.point(doc, point_name)
    conv = pt.get(KEY)
    if not isinstance(conv, dict):
        raise ConvertError(
            f"point {point_name!r} declares no `{KEY}:` block, so there is nothing to convert "
            f"INTO. A conversion needs to know which stage fills which field of this format, and "
            f"only this repository knows that.")
    stages = conv.get("stages") or []
    if not stages:
        raise ConvertError(f"point {point_name!r} declares `{KEY}:` with no stages")
    for i, st in enumerate(stages):
        missing = [k for k in STAGE_REQUIRED if k not in st]
        if missing:
            raise ConvertError(f"point {point_name!r}: stage {i} declares no {missing}")
        # A STAGE FILLS FIELDS OR RUNS A COMMAND, and may do both; one that does neither is a
        # name. `fills: []` is legitimate for a stage that VERIFIES a run - the loop's stations
        # declared as test-phase stages fill nothing and answer from what a run left behind.
        if not st.get("fills") and not st.get("command"):
            raise ConvertError(f"point {point_name!r}: stage {st.get('name', i)!r} fills no "
                               f"field and runs no command, so it can never be done or not")
    return conv.get("placeholder", "TODO"), conv.get("upstream", ""), list(stages)


def unfilled(spec, fields, placeholder):
    """Which of these declared fields are absent or still carry the placeholder.

    ABSENT AND PLACEHOLDER ARE THE SAME ANSWER HERE and different everywhere else. To a reader of
    the finished plugin they differ - a missing `report` block is a WARN and a `report` full of
    TODO is an ERROR. To a conversion they are one thing: not done yet.
    """
    out = []
    for f in fields:
        v = _dotted(spec, f)
        if v is None:
            out.append(f)
        elif placeholder and placeholder in _flatten(v):
            out.append(f)
    return out


def _flatten(value):
    """Every string anywhere inside a value, joined. For asking "is the marker still in there"."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(_flatten(k) + " " + _flatten(v) for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return " ".join(_flatten(v) for v in value)
    return ""


def item_gaps(spec, stage):
    """Which entries of a list-valued field do not yet declare what the stage says every one must.

    WHY A STAGE NEEDS THIS AT ALL. `unfilled` asks whether a FIELD is there. For most stages that
    is the whole question. For a stage that rules on a LIST - one entry per figure, per plot, per
    resource - the field is there from the moment the first entry is written, and the stage then
    reports done with every entry after the first still undecided. That is the same defect
    `outstanding_if` was added for, in the one shape `outstanding_if` cannot see: the plugin is
    not admitting anything is left, because nothing in it knows that anything is left.

    NO FIELD NAME LIVES HERE. The stage names its own list through `fills`, the keys through
    `each_item_declares`, and the permitted values as that key's list. `id` and `name` are read
    only to LABEL a row in the worksheet, and a row with neither is labelled by position.
    """
    want = stage.get("each_item_declares") or {}
    if not want:
        return {}
    items, where = None, ""
    for f in stage.get("fills") or ():
        v = _dotted(spec, f)
        if isinstance(v, (list, tuple)):
            items, where = list(v), f
            break
    if items is None:
        return {}
    gaps = []
    for i, it in enumerate(items):
        d = it if isinstance(it, dict) else {}
        who = str(d.get("id") or d.get("name") or f"entry {i + 1}")
        bad = []
        for key, allowed in want.items():
            v = d.get(key)
            allowed = [str(x) for x in (allowed or [])]
            if v in (None, "", [], {}):
                bad.append(f"no {key}")
            elif allowed and str(v) not in allowed:
                bad.append(f"{key}={v!r}, expected one of {', '.join(allowed)}")
        if bad:
            gaps.append((who, bad))
    return {"field": where, "total": len(items), "gaps": gaps, "want": want}


# -----------------------------------------------------------------------------------------------
# THE HALF OF A STAGE THAT IS MEASURED FROM SOURCE RATHER THAN READ FROM A DECLARATION.
#
# WHY THIS EXISTS AT ALL, MEASURED. On a sealed run: 711 panels, 69 with a written legend and 642
# without. Every check this suite had counted that gap on the FAR side - in the run's output - and
# a count of undescribed PNGs is a number nobody can act on: it names a directory, not the lines
# that must change. The 642 panels come out of 35 call sites in one file, every one of which
# already has a legend parameter sitting on the wrapper it calls, unused.
#
# So a conversion is not finished while a plugin's own source still produces a panel at a site
# that offers a legend and passes none.
# -----------------------------------------------------------------------------------------------

def _convert_specs_for_ladder(doc, point_name, only=""):
    """[(name, declaration)] for the artefacts at a point. Parsed, never imported.

    THE SAME READER THE CLI USES, exported so the ladder does not grow a second one. A half-built
    plugin is exactly the kind that does not import - its `run()` raises and its dependencies are
    not installed - which is the state a conversion exists to get it out of.
    """
    pt = pts.point(doc, point_name)
    d = Path(str(doc.get("_root") or ".")) / str(pt.get("lives") or ".")
    out = []
    for f in sorted(d.glob("*.py")):
        if f.stem.startswith("_") or (only and f.stem != only):
            continue
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "PLUGIN":
                try:
                    out.append((f.stem, ast.literal_eval(node.value)))
                except ValueError:
                    pass
    return out


def artefact(doc, point_name, name):
    """The file this point says one artefact lives in, or None. Never raises on a missing tree."""
    try:
        pt = pts.point(doc, point_name)
    except Exception:                                                     # noqa: BLE001
        return None
    root = Path(str(doc.get("_root") or "."))
    lives = root / str(pt.get("lives") or ".")
    target = lives / f"{name}.py" if lives.is_dir() else lives
    return target if target.is_file() else None


def measure_draw_sites(doc, point_name, name, source=None):
    """Where this plugin produces a panel, and whether each site offers a legend.

    THE ANSWER IS THE EXTRACTOR'S, INCLUDING WHEN IT IS "I COULD NOT LOOK". Nothing here turns a
    failure to read the plugin into an empty list of draw sites - which is what would let a stage
    that cannot see the source report itself finished.

    THE HOST'S EMIT PATH IS NOT NAMED HERE. `doc['tool']` is what the repository calls its own
    package, in its own DEVPOINTS.yaml; the extractor measures the emit path out of that package.
    A point may override it with `draws_through:` when the measurement cannot see it, and the
    inventory's `how` says which of the two answered.
    """
    from .extract import Inventory, draw_sites as DS
    if not name:
        return Inventory("", [], "", complete=False,
                         why_not="this status was asked without naming a plugin, so no source "
                                 "was read and no draw site was looked at. Pass --name.")
    path = artefact(doc, point_name, name)
    if source is None:
        if path is None:
            return Inventory(name, [], "", complete=False,
                             why_not=f"no artefact for {name!r} under the directory this point "
                                     f"declares, so its draw sites could not be read.")
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as e:
            return Inventory(name, [], "", complete=False,
                             why_not=f"{path}: {type(e).__name__}: {e}")
    root = Path(str(doc.get("_root") or "."))
    declared = []
    try:
        conv = pts.point(doc, point_name).get(KEY) or {}
        declared = list(conv.get("draws_through") or [])
    except Exception:                                                     # noqa: BLE001
        pass
    emits = DS.host_emits(root, doc.get("tool") or "", declared)
    where = str(path.relative_to(root)) if path else f"{name}.py"
    return DS.draw_sites(name, source, where, emits, also=_r_beside(doc, point_name, name))


def draw_debt(inv):
    """What one plugin's draw sites owe. `{looked, why_not, total, silent, unknown, described}`.

    THREE ANSWERS AND NOT TWO. A site is DESCRIBED, SILENT, or UNKNOWN - the last being a site
    whose wrapper has no discoverable legend slot, which is a fact about the wrapper and not a
    debt of the call. Folding unknown into silent would invent 47 gaps out of a wrapper that
    requires its legend and therefore has none.

    AND `broken`, WHICH IS NOT ONE OF THE THREE. A described site can still hold a legend the
    language will not run, and it counts as described everywhere above here - correctly, because
    the sentence IS there. Measured: one legend carrying `paste0(..., name_a,, ...)` at a site
    only the compare phase reaches. R parses it, the plugin imports, the environment installs,
    the selftest passes, eighteen units draw all their panels, and then every arm-pair comparison
    dies and six declared plots are never drawn. It is a separate key because it is a separate
    question: not "was this panel described" but "will this file run".
    """
    from .extract import draw_sites as DS
    if inv is None:
        return {"looked": False, "why_not": "nobody looked", "total": 0,
                "silent": [], "unknown": [], "described": 0, "how": "", "broken": [],
                "broken_read": ""}
    if not getattr(inv, "complete", False):
        return {"looked": False, "why_not": getattr(inv, "why_not", ""), "total": 0,
                "silent": [], "unknown": [], "described": 0, "how": "", "broken": [],
                "broken_read": ""}
    sites = DS.sites_of(inv)
    sil, unk = DS.silent(inv), DS.unknown(inv)
    return {"looked": True, "why_not": "", "total": len(sites), "silent": sil, "unknown": unk,
            "described": len(sites) - len(sil) - len(unk), "how": getattr(inv, "how", ""),
            "broken": list(getattr(inv, "defects", [])),
            "broken_read": getattr(inv, "defects_read", "")}


def draw_summary(debt):
    """The one sentence a status line carries, or "" when there is nothing outstanding."""
    if not debt.get("looked"):
        return (f"the draw sites of this plugin were NOT looked at, so whether its panels go out "
                f"described is unknown: {debt.get('why_not', '')}")
    parts = []
    if debt.get("broken"):
        parts.append(f"{len(debt['broken'])} call(s) the language will not run - "
                     + ", ".join(f"line {n}" for n, _ in debt["broken"][:3]))
    if debt["silent"]:
        parts.append(f"{len(debt['silent'])} of {debt['total']} draw sites write no legend")
    if debt["unknown"]:
        parts.append(f"{len(debt['unknown'])} draw at a wrapper with no legend parameter to pass")
    return "; ".join(parts)


def status(spec, doc, point_name, name="", source=None, python="", run=""):
    """[{stage, kind, done, missing, why}] in declared order. The whole resume mechanism.

    `name` IS OPTIONAL AND ITS ABSENCE IS AN ANSWER. A stage that rules on draw sites needs the
    plugin's source, and a caller that names no plugin has not supplied one - so such a stage
    reports "not looked at" rather than done. A status that quietly skipped the half it could not
    measure would be the same defect this module has fixed in four other places.

    `run` IS HOW THE TEST PHASE IS ANSWERED. A stage that declares a `command:` is RUN against
    the run directory, and its exit code is its verdict - the loop's own stations, declared as
    stages, are answered by the loop's own script. Without `run` a command stage is judged by the
    presence of what it fills, as before, and the command is printed as the way to answer it.
    """
    placeholder, _up, stages = plan(doc, point_name)
    out = []
    drawn_inv = None
    if any(st.get(DRAWS_KEY) for st in stages):
        drawn_inv = measure_draw_sites(doc, point_name, name, source)
    for st in stages:
        missing = unfilled(spec, list(st["fills"]), placeholder)
        # A FIELD THAT IS PRESENT IS NOT ALWAYS A STAGE THAT IS FINISHED. velocity's `native_plots`
        # holds two of scvelo's twenty and its `wraps.plots_unreviewed` says the other eighteen are
        # unruled - and this reported the stage as done, because the field was there and carried no
        # placeholder. The plugin was telling the truth in one field and the status was reading the
        # other. A point declares which field, if any, means the work is still outstanding.
        partial = ""
        if not missing and st.get("outstanding_if"):
            said = _dotted(spec, st["outstanding_if"])
            if said:
                partial = str(said)
        # AND THE SAME QUESTION ASKED OF EVERY ENTRY. `outstanding_if` needs the plugin to admit
        # what is left; this needs nothing but the entries themselves, which is what makes it
        # work on a plugin that has never been told the stage exists.
        # HOW A PARTIAL STAGE IS FINISHED, or that nothing says. `outstanding_if` gave the
        # maker a way to report a stage as started-and-owing, and no way to report how the debt
        # is paid - so a wrapper part-way through printed what it owed, forever, and the reader
        # was left to work out that no command in this suite can produce what the accounting
        # demands. Measured: `superseded_by_design` must name a DEFECT, a defect needs the
        # upstream's panel rendered beside the plugin's, and no stage renders one. Two plugins
        # sat at PARTIAL for that reason with nothing saying so.
        #
        # A dead end that announces itself is a task. A silent one is a plugin nobody finishes.
        finished_by = str(st.get("finished_by") or "")
        ig = item_gaps(spec, st) if not missing and not partial else {}
        if ig and ig["gaps"]:
            # THE REASON TRAVELS WITH THE NAME. Listing the entries alone said "F1 does not
            # declare drawn_by" about an entry that declares it as `yes` - a different problem
            # with a different fix, described as the one it is not.
            shown = ", ".join(f"{w} ({'; '.join(r)})" for w, r in ig["gaps"][:3])
            partial = (f"{len(ig['gaps'])} of {ig['total']} entries in `{ig['field']}` have not "
                       f"been ruled on: " + shown
                       + (f", and {len(ig['gaps']) - 3} more" if len(ig["gaps"]) > 3 else ""))
        # AND THE HALF THAT IS NOT DECLARED ANYWHERE. `unfilled` asks whether a field is there,
        # `item_gaps` asks whether every entry of it has been ruled on, and both of them read the
        # plugin's DECLARATION. Neither can see a panel that is produced and never described,
        # because a draw site is a line of code and not an entry in a list.
        #
        # ITS OWN KEY IN THE ROW, NOT `partial`. `partial` is one sentence that the report clips
        # at 150 characters, and this debt is 35 named lines - the whole value of it is that a
        # reader can open them. Folded into `partial` it would print as "35 of 47 draw sit…".
        draws = {}
        if st.get(DRAWS_KEY):
            draws = draw_debt(drawn_inv)
        owes_draws = bool(draws) and (not draws["looked"] or draws["silent"] or draws["unknown"]
                                      or draws.get("broken"))
        # AND A PLACEMENT STAGE IS NOT DONE WHILE A FAMILY IS UNPLACED, UNAXISED, UNBOUNDED, OR
        # ITS CEILING UNREAD. The worksheet named all six unguarded wrappers and `status` still
        # reported build 7 of 7 complete - a debt reported and gated on by nothing, which is the
        # defect `finished_by` exists to prevent, one level up from where it was found before.
        owes_place = False
        places = {}
        if st.get(PLACES_KEY):
            places = placement_debt(spec, st, source_text=_source_of(doc, point_name, name),
                                    also_r=_r_beside(doc, point_name, name),
                                    generated=generated_drift(st, doc, point_name, name))
            owes_place = bool(places["unplaced"] or places["unbounded"] or places["wrong"]
                              or places["unaxised"] or places.get("unguarded")
                              or places.get("ungenerated"))
        # AND THE TWO DEBTS THAT WERE COMMANDS WITH NO STAGE: a package this plugin uses and does
        # not declare, and a reuse key that stood still while the code moved. Both are computed
        # only when the point's declaration asks a stage to carry them.
        loan = loan_debt(st, doc, point_name, name, python=python)
        vers = version_debt(st, spec, doc, point_name, name)
        owes_loan = bool(loan.get("owes"))
        owes_vers = bool(vers.get("owes"))
        # A COMMAND STAGE IS ANSWERED BY RUNNING IT, when there is a run to run it against. Until
        # this, `measure` and `promised` were judged by whether the field they fill was PRESENT -
        # a run-side check read as a declaration check - and the four run-side stations of the
        # loop had no way in at all: the loop said BLOCKED at 6b while this printed the test
        # phase as 2 of 2 complete about the same run.
        ran = run_stage(st, doc, name, run) if (run and st.get("command")) else {}
        owes_run = bool(ran.get("owes"))
        # A STAGE THAT VERIFIES A RUN AND WAS GIVEN NONE IS UNASKED, NOT DONE. `fills: []` means
        # nothing is missing, and "nothing missing" read as complete - so a status with no run
        # printed the run-side stages as finished about a run nobody named. Unasked is its own
        # state: not done, and the command that would answer it is what is printed.
        #
        # WHETHER OR NOT THE STAGE ALSO FILLS A FIELD. The first version exempted a command stage
        # with `fills` and judged it by presence when no run was named - so `promised` read
        # `done` on a plugin nothing had ever run, because `native_plots` was present. That is
        # the inventory stage's question answered twice and the promised stage's answered never;
        # a cold agent's status showed it (docs/blind/0002-gseapy.md, "test: 1 of 6 complete"
        # about a plugin that had never run). A command is the stage's question; without a run
        # it is unasked, and what it fills being present says only that somebody wrote it down.
        unasked = bool(st.get("command")) and not run
        out.append({"stage": st["name"],
                    "partial": partial,
                    "loan": loan,
                    "version": vers,
                    "ran": ran,
                    "unasked": unasked,
                    "kind": st.get("kind", "mechanical"),
                    # BUILD OR TEST, and the split is the point. A BUILD stage reads source - the
                    # plugin's own code, or the wrapped tool's signatures and namespace - and
                    # touches no data at all, so it CANNOT be overfitted to a cohort. A TEST stage
                    # needs something to run on, and that is where a fixture or an existing
                    # dataset belongs.
                    #
                    # Keeping them apart is what stops the build reaching for a real cohort
                    # because that is where the data happens to be. A plugin whose build is
                    # complete is finished as a piece of code; whether it is CORRECT is the test
                    # stage's question and a different one.
                    "phase": st.get("phase", "build"),
                    "finished_by": finished_by,
                    "fills": list(st["fills"]),
                    "draws": draws,
                    # THE DEBT ITSELF, NOT ONLY WHETHER THERE IS ONE. `owes_place` is the gate;
                    # this is what the gate read, and `sch dev convert overfit` needs it to tell
                    # a stage that PASSED from one that had nothing to look at. The ceiling-guard
                    # half of this stage can only look at a plugin that draws in a second
                    # language, and in the family it was written for that is one plugin of nine.
                    "places": places,
                    "done": (not missing and not partial and not owes_draws and not owes_place
                             and not owes_loan and not owes_vers and not owes_run
                             and not unasked),
                    "missing": missing,
                    "why": st.get("why", "")})
    return out


#: THE LOAN SURVEY RESOLVES THE WHOLE FAMILY, so it is computed once per process and not once
#: per plugin. `status` is asked of every artefact at a point by `overfit` and by the family
#: status, and nine resolves of the same landscape is the same answer nine times.
_LOANS: dict = {}


def loan_debt(st, doc, point_name, name, python=""):
    """{owes, loaded, says} - does this plugin USE a package its own declaration never asks for?

    A LENT PACKAGE IS EXPOSURE; A LOADED ONE IS A DEFECT. A seven-member environment lends its
    members a hundred names each and almost none is ever touched, so a stage that owed on a LOAN
    would be red on every member of every shared environment at once. What is owed on is a name
    the plugin's own source LOADS and its own declaration does not ask for - the plugin works
    today, inside the group, and loses it the day it is deployed alone.

    MEASURED, AND IT COST AN END-TO-END RUN: a plugin spent its whole life in a seven-member
    environment and depended on two packages it declared neither of. Its selftest passed, because
    neither is imported at module scope. Unplugged, two drawing paths died - 54 panels of 711 -
    forty minutes into a cohort run.

    THE ANSWER IS THE SURVEY'S, INCLUDING "I COULD NOT LOOK". A resolver that cannot be reached
    gives `owes=False, says=<why>` and the stage reports that it could not be established, which
    is not the same as a plugin that declares everything.
    """
    if not st.get(LOAN_KEY) or not name:
        return {}
    from .extract import shared_env as _SE
    root = str(doc.get("_root") or ".")
    key = (root, point_name, python or "python3")
    if key not in _LOANS:
        try:
            _LOANS[key] = _SE.survey(doc, point_name, root, python=python or "python3")
        except Exception as e:                                            # noqa: BLE001
            _LOANS[key] = e
    got = _LOANS[key]
    if isinstance(got, Exception):
        return {"owes": False, "loaded": [], "complete": False,
                "says": f"the loan survey could not run: {type(got).__name__}: {got}"}
    mine = next((l for l in got if l.plugin == name), None)
    if mine is None or not mine.complete:
        return {"owes": False, "loaded": [], "complete": False,
                "says": (mine.why_not if mine is not None else
                         f"{name!r} is not in this repository's own catalogue")}
    loaded = [r for r in mine.rows if r.get("loaded")]
    return {"owes": bool(loaded), "loaded": loaded, "complete": True,
            "says": (f"{len(loaded)} package(s) this plugin LOADS are lent by "
                     f"{mine.environment} and declared by nothing it owns: "
                     + ", ".join(sorted({r['entry'] for r in loaded}))
                     if loaded else
                     (f"nothing lent by {mine.environment} is loaded here"
                      if not mine.alone else
                      f"alone in {mine.environment}: nothing is lent, so nothing can be lost"))}


def version_debt(st, spec, doc, point_name, name):
    """{owes, says} - has the field this repository calls its reuse key kept up with the code?

    A DECLARED VERSION IS A CLAIM ABOUT CODE AND NOTHING GATED ON IT. The command existed and was
    a command: `sch dev convert freshness` asks git whether the field moved when the file did.
    Nothing ran it, so a plugin could be rewritten, committed and reported `build complete` with
    its reuse key standing still - and this suite did exactly that, in the commit that moved a
    plugin's drawing protocol into a generated file. The audit found it afterwards. As a stage it
    is found before.

    STALE IS THE ONLY DEBT. `CANNOT SAY` - an uncommitted change, a computed value, no history -
    is reported and does not owe, because it is a fact about the checkout and not about the
    plugin.
    """
    if not st.get(VERSION_KEY) or not name:
        return {}
    from . import freshness as _FR
    try:
        f = _FR.check(spec, doc, point_name, name)
    except Exception as e:                                                # noqa: BLE001
        return {"owes": False, "says": f"freshness could not be established: {e}"}
    if not f.complete:
        return {"owes": False, "verdict": f.verdict,
                "says": f"{f.verdict}, and that is an answer and not a pass: {f.why_not}"}
    since = ", ".join(c.get("short", "?") for c in f.commits_since[:4])
    return {"owes": f.verdict == _FR.STALE, "verdict": f.verdict,
            "says": (f"`{f.field}` = {f.declared!r}, set by "
                     f"{(f.set_by or {}).get('short', '?')}, and "
                     f"{len(f.commits_since)} commit(s) have touched this artefact since"
                     + (f": {since}" if since else "")
                     if f.verdict == _FR.STALE else
                     f"`{f.field}` = {f.declared!r} is {f.verdict}")}


def coverage(doc, point_name):
    """{field: [stage]} for what a point REQUIRES, and [] for a field no stage fills.

    `status` ANSWERS "ARE THE STAGES DONE" AND NOT "IS THE DECLARATION COVERED", and the two look
    identical from a green report. Measured on the repository this was written for: seventeen keys
    in `must_declare`, nine of them filled by a stage, and `build: 7 of 7 complete` printed over
    the other EIGHT - fields a conversion is required to carry that no stage ever mentions. Two of
    them are the ones this suite has already paid for:

      `requires` - the environment. `sch dev convert borrowed` answers it from declarations alone,
      and a plugin that borrows an undeclared package from a shared environment passes every stage
      and dies the day it is deployed alone. That cost an end-to-end run.

      `version` - the reuse key. `sch dev convert freshness` asks git whether it moved when the
      code did, and a stale one makes every reusing run serve last week's products and seal clean.

    Both were COMMANDS and neither was a stage, so nothing gated on either. A field with a command
    and no stage is help you have to know exists.

    AN UNOWNED FIELD IS NOT AUTOMATICALLY A DEFECT. `wraps.tool` is the conversion's INPUT - the
    upstream it is driven by - and cannot be an output of it. What is a defect is not saying so:
    this reports the coverage and the reader rules on it.

    FOUR STATES, NOT TWO, and the fourth is red. "Filled by no stage" was one line covering an
    input, three keys the validator refuses, and two keys nothing anywhere checks - and the two
    were the numbers a node is packed on. The point now says, in `truth:`, how each unowned key's
    truth is established; a key with no stage and no entry is `nobody`, which is the answer this
    used to give for all six while printing none of them red.

      by: stage      a conversion stage fills it; `stages` names them
          input      the conversion's input, never its output
          validator  the repository's own validator refuses it when wrong
          measured   read back from a run by a named command
          nobody     required, present-checked, and true by nobody's account

    `says` carries a disagreement: a `truth:` entry for a key a stage ALSO fills is two answers
    to one question and is reported, not silently resolved.
    """
    pt = pts.point(doc, point_name)
    try:
        _ph, _up, stages = plan(doc, point_name)
    except ConvertError:
        stages = []
    fills = {}
    for st in stages:
        for f in st["fills"]:
            fills.setdefault(str(f).split(".")[0], []).append(st["name"])
    truth = {str(k): str(v) for k, v in (pt.get("truth") or {}).items()}
    out = {}
    for k in (pt.get("must_declare") or []):
        k = str(k)
        if not pts._KEYISH.match(k):
            continue                       # a sentence for a person, not a field
        st_k = list(fills.get(k, ()))
        declared = truth.get(k, "")
        says = ""
        if st_k:
            by = "stage"
            if declared:
                says = (f"`{k}` is filled by the {', '.join(st_k)} stage and `truth:` also says "
                        f"{declared} - two answers to one question; drop one")
        elif declared in pts.TRUTH:
            by = declared
        else:
            by = "nobody"
        out[k] = {"by": by, "stages": st_k, "says": says}
    return out


def coverage_report(cov, point_name):
    """One line when every key has a stage; otherwise the four states, and `nobody` in red."""
    if not cov:
        return ""
    by = {}
    for k, v in cov.items():
        by.setdefault(v["by"], []).append(k)
    n_stage = len(by.get("stage", ()))
    if n_stage == len(cov):
        return f"every one of the {len(cov)} key(s) this point requires is filled by a stage"
    L = [f"{n_stage} of {len(cov)} key(s) this point requires are filled by a CONVERSION STAGE."]
    if by.get("input"):
        L.append(f"  input to the conversion, never its output:  {', '.join(sorted(by['input']))}")
    if by.get("validator"):
        L.append(f"  refused by the repository's own validator:  "
                 f"{', '.join(sorted(by['validator']))}")
    if by.get("measured"):
        L.append(f"  measured from a run by a named command:      "
                 f"{', '.join(sorted(by['measured']))}")
    if by.get("nobody"):
        L.append(f"  CHECKED BY NOBODY:                          {', '.join(sorted(by['nobody']))}")
        L.append(f"    required, present-checked, and true by nobody's account. A number nothing "
                 f"checks is a number the host trusts forever. Give each a stage in")
        L.append(f"    `convert.stages`, a validator, or a measuring command - and say which "
                 f"under `truth:` in the point - or it stays red here.")
    for k, v in sorted(cov.items()):
        if v.get("says"):
            L.append(f"  {v['says']}")
    return "\n".join(L)


def next_stage(spec, doc, point_name, name=""):
    """The first stage not done, or None. Order is the declaration's, and it is the dependency.

    A LIST IS A DEPENDENCY GRAPH WHEN THE ORDER IS MEANT. `account` cannot run before `inventory`,
    and `judgement` is asked last because every earlier stage is evidence for it. Declaring that as
    an ordered list rather than as edges is enough here and says so: if a conversion ever needs two
    stages that genuinely do not depend on each other to run at once, this is where that shows up.
    """
    for row in status(spec, doc, point_name, name):
        if not row["done"]:
            return row
    return None


def inventory(tool, python=None, rscript=None):
    """Ask every extractor that can look. [(extractor name, Inventory)].

    ALL OF THEM, NOT THE RIGHT ONE. The declaration does not say whether a wrapped tool is a Python
    package or an R one - `wraps.tool` is a name - and inferring it from `requires.r` would be a
    guess that is wrong for the first plugin that wraps a Python package and also needs R. Each
    extractor fails fast when it cannot look, and says which of those two happened, so trying them
    all costs a second and produces a better answer than a guess: the ones that could not look say
    so by name.
    """
    from . import extract
    got = []
    for name, mod in sorted(extract.discover().items()):
        kind = mod.EXTRACT.get("reads")
        try:
            if kind == "python-package":
                inv = mod.inventory(tool, python=python or "python3")
            elif kind == "r-package":
                inv = mod.inventory(tool, rscript=rscript)
            else:
                continue
        except Exception as e:                                            # noqa: BLE001
            from .extract import Inventory
            inv = Inventory(tool, [], "", complete=False,
                            why_not=f"{type(e).__name__}: {e}")
        got.append((name, inv))
    return got


def _draw_lines(row, limit=40):
    """The draw-site half of one status row, as lines. Empty when the stage owes nothing there.

    THE SITES ARE NAMED AND NOT COUNTED - UP TO `limit` OF THEM, AND THEN SAID TO BE MORE. The
    whole difference between this and the check it replaces is that a count of 642 undescribed
    panels names a directory and 35 named lines name the work, so truncating the list back down
    to three hands the reader the count again.

    IT IS A CAP AND NOT A PROMISE, and the prose used to say otherwise. Past `limit` the row says
    how many it did not name, and that one line is all that stands between a shorter cap and
    sites leaving the report with no trace - so the two constants are tested against each other
    WITH a truncation, which is the only state in which they can disagree.
    """
    d = row.get("draws") or {}
    if not d:
        return []
    if not d.get("looked"):
        return [f"       COULD NOT LOOK at this plugin's draw sites, so whether its panels go "
                f"out described is unknown -",
                f"       {d.get('why_not', '')}",
                f"       An answer of zero silent draw sites from here would be a fact about "
                f"this checkout, not about the plugin."]
    if not (d.get("silent") or d.get("unknown")):
        return []
    L = []
    if d.get("silent"):
        L.append(f"       {len(d['silent'])} of {d['total']} draw sites write no legend "
                 f"({d['described']} do). Each is a panel the page will describe by its "
                 f"filename:")
        for s in d["silent"][:limit]:
            panel = _clip(s.get("panel") or "(unnamed)", 46)
            call = (s.get("calls") or [""])[0] or _clip(s.get("draws", ""), 40)
            L.append(f"         {s['file']}:{s['line']:<6} {s['wrapper']}({panel})"
                     + (f"   -> {call}" if call else ""))
        if len(d["silent"]) > limit:
            L.append(f"         ... and {len(d['silent']) - limit} more")
    if d.get("unknown"):
        L.append(f"       {len(d['unknown'])} site(s) draw through a wrapper with no legend "
                 f"parameter at all, so no call could pass one:")
        for s in d["unknown"][:6]:
            L.append(f"         {s['file']}:{s['line']:<6} {s['wrapper']} defined at "
                     f"{s.get('wrapper_at', '?')}")
    return L


def format_status(rows, name, point_name, doc=None, root=".", python="", run=""):
    """The line-per-stage a person reads to know where a conversion stands.

    REPORTED IN TWO HALVES, because they are two different claims. "The build is complete" says
    this plugin is finished as a piece of code and was written without any data in front of it -
    which is the only way to know it was not shaped around one cohort. "The tests pass" says it
    behaves, and needs something to run on.

    AND WHICH SIDE OF THE ROUND'S RULES THIS PLUGIN IS ON, first, before any debt is listed. A
    status that prints "35 silent draw sites, fix them" about an artefact the round holds out is
    an instruction to spend the family's only evidence that the maker generalises; the rule that
    forbids it lived in a declaration nobody reads while working, and the routing loop that
    follows from it lived in one session's memory. The banner is the routing loop's first branch,
    printed where the work is driven from.
    """
    L = []
    L += _side_of_the_rules(doc, name)
    for phase, headline in (("build", "BUILD - reads source only, so it cannot be fitted to a "
                                      "cohort"),
                            ("test", (f"TEST - answered by running each stage's command against "
                                      f"{run}" if run else
                                      "TEST - needs something to run on: the fixture, or a "
                                      "dataset you already have; pass --run RUNDIR and each "
                                      "stage's command is run for you"))):
        group = [r for r in rows if r.get("phase", "build") == phase]
        if not group:
            continue
        done = sum(1 for r in group if r["done"])
        L.append(f"{name}  ({point_name})  {phase}: {done} of {len(group)} complete    {headline}")
        for r in group:
            mark = ("done" if r["done"]
                    else "RUN?" if r.get("unasked")
                    else "PART" if r.get("partial") or r.get("draws", {}).get("silent")
                    else "ASK " if r["kind"] == "judgement" else "todo")
            L.append(f"  {mark} {r['stage']:12s} {', '.join(r['fills'])}")
            d = r.get("draws") or {}
            L += _draw_lines(r)
            if r.get("unasked"):
                L.append(f"       not asked: this stage verifies a run, and none was named. "
                         f"Pass --run RUNDIR")
            # WHAT A COMMAND STAGE SAID WHEN IT WAS RUN. The argv, so the reader can run it
            # again; the verdict, so the mark above is explained; the tail, because the
            # command's own last lines are the reason and this module does not know their
            # vocabulary.
            if r.get("ran"):
                ran = r["ran"]
                L.append(f"       ran:  {' '.join(ran['argv'])}")
                L.append(f"       {'answered' if not ran['owes'] else 'OWES'}  (exit {ran['rc']})")
                # WHOLE, NOT CLIPPED. The count a prediction was about sat past the 160th
                # character of a station's one line; a tail line is the command's own answer.
                for line in ran["says"][-5:]:
                    L.append(f"         {line}")
            if r.get("partial"):
                L.append(f"       started, and the plugin says so: {r['partial'][:150]}")
            if r.get("partial") or d.get("silent") or d.get("unknown"):
                # AND WHAT WOULD FINISH IT, or that this repository declares nothing that
                # would. The second case is the one worth printing: a stage whose remaining
                # work no command in the suite can do is a gap in the SUITE, and it was
                # invisible - the maker printed the debt and stopped, every time, forever.
                #
                # THE DRAW-SITE DEBT GOES THROUGH THE SAME GATE, because it is the same
                # failure: 35 sites reported as owing a legend, and nothing anywhere saying
                # what pays them, is a report an agent reads and cannot act on.
                if r.get("finished_by"):
                    L.append(f"       to finish it:  {r['finished_by']}")
                else:
                    L.append(f"       NOTHING DECLARES HOW TO FINISH THIS. `{r['stage']}` can "
                             f"report what is outstanding and this point names no stage or "
                             f"command that closes it,")
                    L.append(f"       so the plugin stays part-way through no matter who reads "
                             f"it. That is a gap in the suite, not in the plugin. Declare "
                             f"`finished_by:` on the stage")
                    L.append(f"       once something can do the work.")
            elif not r["done"]:
                if r.get("loan", {}).get("owes"):
                    L.append(f"       {r['loan']['says']}")
                    for row in r["loan"]["loaded"][:6]:
                        L.append(f"         LOADED  {row['entry']}  at {row['written_in']}"
                                 f":{row.get('at', '?')}  ({row.get('times', 1)} site(s))")
                if r.get("version", {}).get("owes"):
                    L.append(f"       {r['version']['says']}")
                if r["missing"]:
                    L.append(f"       unfilled: {', '.join(r['missing'])}")
                if r["why"]:
                    L.append(f"       {r['why']}")
        L.append("")
    # WHAT THE STAGES COVER, WHICH IS A DIFFERENT QUESTION FROM WHETHER THEY ARE DONE. A complete
    # build over a declaration eight of whose required keys no stage mentions is a complete build
    # and an incomplete conversion, and only one of those two facts was ever printed.
    if doc:
        cov_ = coverage(doc, point_name)
        cov = coverage_report(cov_, point_name)
        # PRINTED WHENEVER A KEY IS NOT A STAGE'S, and not only when one is nobody's: the four
        # states are the reader's evidence that the split was decided rather than assumed.
        if cov and any(v["by"] != "stage" for v in cov_.values()):
            L.append("  " + cov.replace("\n", "\n  "))
            L.append("")
    todo = [r for r in rows if not r["done"]]
    if not todo:
        L.append("  nothing left to convert")
        return "\n".join(L)
    L.append("  what is left, in order:")
    for r in todo:
        # `doc` IS OPTIONAL AND MUST BE. A caller that only wants the summary should not have to
        # hand over the declaration; without it the stages are still named and only the commands
        # are missing, which is a smaller loss than a TypeError.
        cmd = advance_command(r, doc, point_name, root, name, python, run) if doc else ""
        if cmd:
            L.append(f"    {r['stage']:12s} {cmd}")
        else:
            L.append(f"    {r['stage']:12s} nothing runs this - it is what only you can answer: "
                     f"{', '.join(r['missing'])}")
    return "\n".join(L)


def _side_of_the_rules(doc, name):
    """Lines saying whether `name` is held out or is the round's maker output, or [] with no rules.

    Read from the same `rules:` block `sch dev rules` checks, so the status and the check cannot
    name different artefacts. A repository declaring no rules gets no banner: inventing one would
    be this tool deciding how somebody else's round works.
    """
    if not doc or not name:
        return []
    from . import rules as _RL
    rules = _RL.declared(doc)
    if not rules:
        return []
    held = [str(x) for x in ((rules.get("held_out") or {}).get("names") or [])]
    out = [str(x) for x in ((rules.get("end_to_end") or {}).get("names") or [])]
    if name in held:
        return [f"  HELD OUT: {name} is one of this round's held-out artefacts. Every debt below "
                f"is a RESULT to record, never a fix to make -",
                f"  a repair fits the maker to it and spends the family's only evidence that the "
                f"maker generalises. `sch dev rules` checks it.", ""]
    if name in out:
        return [f"  MAKER OUTPUT: {name} is what this round converts. A debt below is paid by "
                f"changing the maker and regenerating, or by answering",
                f"  the worksheet the stage names - never by hand-editing the artefact. "
                f"Duplicated mechanism is the tell, and `sch dev rules` measures it.", ""]
    return []


def _clip(text, n):
    """Truncated so the reader can see it was truncated. A silent cut reads as the whole thing."""
    t = " ".join(str(text or "").split())
    return t if len(t) <= n else t[:n - 1] + "…"


def ruling_context(spec, doc, point_name, width=96):
    """The plugin's OWN half of a ruling, printed beside the upstream's surface.

    WHAT THIS FIXES, MEASURED ON ONE CONVERSION. The worksheet showed twelve of the wrapped
    tool's plotting functions with their signatures and docstrings - genuinely good evidence -
    and nothing about the plugin. But `superseded_by_design` has to NAME the panel that
    supersedes, and `not_applicable` has to say why, and on that conversion eight of the twelve
    rulings turned on a single line in the plugin's own `cannot_show` saying it has no spatial
    information. All of it was in the declaration this tool had already parsed, and whoever was
    ruling had to go and find it.

    The expensive participant should be deciding, not gathering. This is the gathering.

    WHICH FIELDS, ASKED OF THE REPOSITORY. `ruling_context:` in the point's convert block lists
    them; nothing here knows what a panel or a limit is called in any format.
    """
    import textwrap
    conv = pts.point(doc, point_name).get(KEY) or {}
    fields = list(conv.get("ruling_context") or ())
    if not fields:
        return ""
    out = []
    for f in fields:
        v = _dotted(spec, f)
        if not v:
            continue
        out.append(f"#   {f}:")
        if isinstance(v, (list, tuple)):
            for item in v:
                if isinstance(item, dict):
                    # an id and whatever it says it is for, without knowing either key's name
                    label = str(item.get("id") or item.get("name") or "")
                    why = next((str(item[k]) for k in ("question", "shows", "what")
                                if item.get(k)), "")
                    line = f"{label} - {why}" if label and why else (label or why or str(item))
                else:
                    line = str(item)
                out += textwrap.wrap(" ".join(line.split()), width=width,
                                     initial_indent="#     - ", subsequent_indent="#       ")
        elif isinstance(v, dict):
            for k in sorted(v):
                out.append(f"#     - {k}")
        else:
            out += textwrap.wrap(" ".join(str(v).split()), width=width,
                                 initial_indent="#     - ", subsequent_indent="#       ")
    if not out:
        return ""
    return ("#\n"
            "# WHAT THIS PLUGIN ALREADY SAYS. A `superseded_by_design` ruling has to name the\n"
            "# panel that supersedes, and a `not_applicable` one has to say why - both are here.\n"
            + "\n".join(out) + "\n#")


def declared_of(spec, doc, point_name):
    """(declared, form): what this plugin has decided about its upstream's plots, in one shape.

    ON THE PLAN (harness ADR-0016) a USED function is the `fn` of an entry in the list the plan
    stage fills, and its files are the entries' ids; a SKIPPED one is a line in the skips the
    stage names (`entry_keys.skips`). Before the plan it was one field read by the first
    `places_every` rule - prose per function. Both are returned as {fn: {"use"} | {"skip"...}},
    so the accounting worksheet reads one shape, and `form` says which the plugin is on: the
    plan, or the older field's name.
    """
    st = plan_stage(doc, point_name)
    if st is not None:
        keys = {str(k): str(v) for k, v in (st.get(ENTRY_KEYS) or {}).items()}
        fn_key, skips_key = keys.get("upstream", "fn"), keys.get("skips", "report.skips")
        _field, entries = _entries(spec, st)
        planned = [e for e in entries if str(e.get(fn_key) or "").strip()]
        if planned:
            out = {}
            for e in planned:
                if str(e.get("drawn_by") or "tool") != "tool":
                    continue
                fn = str(e[fn_key]).strip()
                rec = out.setdefault(fn, {"use": "", "ids": []})
                fid = str(e.get("id") or "").strip()
                if fid and fid not in rec["ids"]:
                    rec["ids"].append(fid)
            for fn, rec in out.items():
                rec["use"] = ", ".join(f"figures/{i}.png" for i in rec["ids"])
            skips = _dotted(spec, skips_key) or {}
            for fn, d in (skips.items() if isinstance(skips, dict) else []):
                out[str(fn)] = dict(d) if isinstance(d, dict) else {"skip": str(d)}
            return out, "plan"
        rules = st.get(PLACES_KEY) or []
        for r in rules:
            if str(r.get("named_by") or "") == "use" and r.get("field"):
                v = _dotted(spec, str(r["field"]))
                return (dict(v) if isinstance(v, dict) else {}), str(r["field"])
    v = spec.get("native_plots") if isinstance(spec, dict) else None
    return (dict(v) if isinstance(v, dict) else {}), "native_plots"


def worksheet(tool, inv, declared, source="", placeholder="TODO", width=96, form="native_plots",
              skips_key="report.skips"):
    """A paste-ready accounting block with the evidence for each decision beside it.

    PRINTED TO PASTE, NOT WRITTEN INTO THE FILE. This tool already has that idiom - every run fits
    both memory terms "and prints them ready to paste" - and it is right here for a reason beyond
    consistency: inserting a nested dict into Python source means an AST round-trip that loses the
    comments a plugin is mostly made of, or a regex over somebody's declaration.

    A NAME IS THE ONE THING THE DECIDER ALREADY HAS. The first version listed thirty-five of them
    and left somebody to open thirty-five documentation pages and read five thousand lines of
    plugin. Both answers are already available: what the function draws is in the package, and
    whether this wrapper calls it is in the wrapper. Each entry now carries the upstream signature
    and summary line, and the call site with the string literals on it - which for cellchat is
    `npng("heatmap_count", netVisual_heatmap(cc, ...))`, the output's own name.

    NOTHING IS DECIDED HERE. Every undecided entry stays a placeholder however strong the evidence,
    so a half-filled worksheet pasted into a plugin does not validate. A wrong `use` reads as a
    decision and is worse than an absent one.

    What is already decided is carried through unchanged, so this is re-runnable after a version
    bump and the answer is then the diff.
    """
    detail = getattr(inv, "detail", None) or {}
    names = list(getattr(inv, "names", inv) or [])
    calls = callsites(source, names) if source else {}
    decided = dict(declared or {})
    known = [n for n in names if n in decided]
    new = [n for n in names if n not in decided]
    stale = [n for n in decided if n not in names]

    L = [f'    # {len(names)} function(s) exported by {tool}. '
         f'{len(known)} already decided, {len(new)} to rule on; '
         f'{sum(1 for n in new if n in calls)} of those are called by this plugin.']
    if form == "plan":
        # THE PLAN FORM (harness ADR-0016): a USED function is an entry in the figure plan and
        # is only NAMED here; a SKIPPED one is a line in the skips. Printing a `native_plots`
        # block to paste, for a plugin that has no such field, was the maker speaking a form
        # the plugin had left.
        used = [n for n in known if (decided[n] or {}).get("use")]
        for n in used:
            L.append(f'    # used     {n}  ->  {decided[n]["use"]}   (an entry in the plan; '
                     f'`sch dev convert plan` prints it)')
        L.append(f'    "{skips_key.split(".")[-1]}": {{')
        for n in known:
            if not (decided[n] or {}).get("use"):
                L.append(f'        {n!r}: {decided[n]!r},')
        if new:
            L += ['        # ---- NOT YET RULED ON. Each is either USED - then it is an ENTRY in',
                  '        # `report.figures` (drawn_by: tool, fn, axis, position, args/expr, legend)',
                  '        # and not a line here - or SKIPPED for one of exactly three reasons:',
                  '        #   {"skip": "not_applicable",       "evidence": "..."}',
                  '        #   {"skip": "superseded_by_design", "panel": "...", "defect": "..."}',
                  '        #   {"skip": "duplicate_of",         "same_as": "..."}',
                  '        # "reimplemented", "not considered" and "dependency missing" are rejected by',
                  '        # name; see scprofile/native.py.']
    else:
        L.append('    "native_plots": {')
        for n in known:
            L.append(f'        {n!r}: {decided[n]!r},')
    if new:
        L += ['        # ---- NOT YET RULED ON. Each is either USED - say where its output lands -',
              '        # or SKIPPED for one of exactly three reasons, with what that reason supplies:',
              '        #   {"use": "figures/x.png"}',
              '        #   {"skip": "not_applicable",       "evidence": "..."}',
              '        #   {"skip": "superseded_by_design", "panel": "...", "defect": "..."}',
              '        #   {"skip": "duplicate_of",         "same_as": "..."}',
              '        # "reimplemented", "not considered" and "dependency missing" are rejected by',
              '        # name; see scprofile/native.py.']
        for n in new:
            d = detail.get(n) or {}
            sig = d.get("signature") or ""
            summary = d.get("summary") or ""
            # THE SUMMARY GETS ITS OWN LINE. Both on one, truncated together, meant decoupler's
            # signatures - which carry full type annotations and a return type - pushed the
            # docstring line off the end, losing the single most useful thing on the row.
            L.append(f"        # {n}{_clip(sig, 104)}")
            if summary:
                L.append(f"        #   {_clip(summary, 104)}")
            if d.get("deprecated"):
                L.append("        #   DEPRECATED upstream. Using it ties this plugin to something "
                         "its author is removing.")
            c = calls.get(n)
            if c:
                where = "in a COMMENT at" if c["in_comment"] else "called at"
                L.append(f'        #   {where} line {c["line"]}: {c["text"]}')
                if c["literals"]:
                    L.append(f'        #   strings on that line: '
                             f'{", ".join(repr(x) for x in c["literals"])}')
                if form == "plan":
                    L.append(f'        {n!r}: {{"skip": "{placeholder} — it is called: make it '
                             f'an entry in report.figures, or say which skip applies"}},')
                else:
                    L.append(f'        {n!r}: {{"use": "{placeholder} — confirm where this lands"}},')
            else:
                L.append("        #   not called anywhere in this plugin.")
                if form == "plan":
                    L.append(f'        {n!r}: {{"skip": "{placeholder} — use it (an entry in '
                             f'report.figures), or which skip applies?"}},')
                else:
                    L.append(f'        {n!r}: {{"use": "{placeholder} — use it, or which skip '
                             f'applies?"}},')
    L.append("    },")
    if stale:
        L.append(f"    # DECLARED AND NO LONGER EXPORTED by {tool}: {sorted(stale)}")
        L.append("    # Either the upstream dropped them or the inventory pattern stopped")
        L.append("    # matching. Both are worth knowing; neither is fixed by deleting the line.")
    return "\n".join(L)


def callsites(source, names, window=3):
    """{name: {line, text, context, literals, in_comment}} for every inventory name the code calls.

    THE ACCOUNTING IS MOSTLY ALREADY WRITTEN, IN THE PLUGIN. Thirty-two of cellchat's thirty-five
    entries say where a function's output lands, and the plugin is what put it there - so asking a
    maintainer to supply that is asking them to re-derive what the file in front of them states.

    EVIDENCE, NOT A GUESS AT THE ANSWER. The first version tried to name the output by looking for
    the nearest path literal, and found one for 1 of 32 - because the outputs are not path
    literals. cellchat's line reads `npng("heatmap_count", netVisual_heatmap(cc, ...))`: the name
    is the first argument of the plugin's own saving wrapper, and the declared use is
    `figures/native_heatmap_{count,weight}.png`, assembled by a convention this module must not
    learn. Encoding `npng` here would be one plugin's habit compiled into a suite that serves five
    repositories.

    So this reports the call, the lines around it, and the string literals on it. Everything a
    reader needs to write the entry is then in front of them, and nothing has been decided for
    them - a wrong `use` reads as a decision, which is worse than an absent one.

    A MATCH IN A COMMENT IS STILL WORTH REPORTING and is marked as one. `rankNet`'s only mention is
    the comment "return.data, nothing drawn", which is precisely the evidence the entry needs; a
    scan that hid it would have thrown away the answer. Non-comment matches are preferred.
    """
    lines = source.splitlines()
    out = {}
    for name in names:
        tail = str(name).split(".")[-1]
        if not tail:
            continue
        # AS MUCH OF THE DOTTED NAME AS THE INVENTORY GIVES. Matching the tail alone reported
        # scvelo's `pl.paga` as called at `scv.tl.paga(...)` - a different submodule - and
        # `pl.plot` at `ctx.plot()` and `pl.scatter` at `ax.scatter(...)`, neither of them scvelo
        # at all. Three of seven "called" were wrong, presented as evidence, and each would have
        # sent somebody to write a `use` entry for a function this plugin never calls.
        #
        # `(?<!\w)` and not `(?<![\w.])` on the front: excluding a preceding dot rejected
        # `sc.pl.umap(adata)`, which is how every scanpy plot is called, so it found nothing in
        # the eight Python plugins. A word character still excludes `foo_umap(`.
        want = ".".join(str(name).split(".")[-2:]) if "." in str(name) else tail
        rx = re.compile(r"(?<!\w)" + re.escape(want).replace(r"\.", r"\.") + r"\s*\(")
        best = None
        for i, line in enumerate(lines):
            if not rx.search(line):
                continue
            comment = line.lstrip().startswith("#")
            if best is None or (best["in_comment"] and not comment):
                best = {"line": i + 1, "text": line.strip()[:120],
                        "context": [l.rstrip()[:120] for l in lines[i + 1:i + 1 + window]],
                        "literals": [x for x in re.findall(r"[\"\']([^\"\'\n]{2,80})[\"\']", line)
                                     if not x.isspace()][:4],
                        "in_comment": comment}
            if best and not best["in_comment"]:
                break
        if best:
            out[name] = best
    return out


def run_stage(st, doc, name, run, timeout=1800):
    """Run a command stage against `run`. {argv, rc, owes, says} - `says` is the output's tail.

    THE EXIT CODE IS THE VERDICT AND THE TAIL IS THE REASON. The maker knows nothing about what
    the command prints - a loop station's prose, a capacity fit, a ledger count - so it keeps the
    last lines for the reader and rules on nothing but zero or not. `{python}` is the HOST's
    interpreter: these are the repository's own tools whatever language its plugins draw in.

    A COMMAND THAT CANNOT RUN OWES, AND SAYS WHY. Nothing here can turn "could not run" into a
    pass, which is the same rule every other reader in this module keeps.
    """
    argv = fill(list(st.get("command") or []), {"python": sys.executable, "run": str(run),
                                                "root": str(doc.get("_root") or "."),
                                                "name": name or ""})
    try:
        p = subprocess.run(argv, cwd=str(doc.get("_root") or "."), capture_output=True,
                           text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as e:
        return {"argv": argv, "rc": None, "owes": True, "says": [f"could not run: {e}"]}
    lines = [l.rstrip() for l in ((p.stdout or "") + "\n" + (p.stderr or "")).splitlines()
             if l.strip()]
    return {"argv": argv, "rc": p.returncode, "owes": p.returncode != 0, "says": lines[-8:]}


def stage_command(doc, point_name, stage_name):
    """The argv a stage declares, or []. Stages that are a command say so; the rest are not."""
    _ph, _up, stages = plan(doc, point_name)
    for st in stages:
        if st["name"] == stage_name:
            return list(st.get("command") or [])
    return []


def fill(argv, values):
    """`{python}` and `{run}` substituted by name. EXPLICIT, never `str.format`.

    A declaration is somebody else's text and may contain a brace for its own reasons; `format`
    would raise on it, or worse, substitute something. The same rule the ladder already follows.
    """
    out = []
    for tok in argv:
        s = str(tok)
        for k, v in values.items():
            s = s.replace("{" + k + "}", str(v))
        out.append(s)
    return out


# -----------------------------------------------------------------------------------------------
# SCANS READ THE PLUGIN. EXTRACTORS READ THE UPSTREAM. Keeping the two apart is what stops this
# module learning one package's habits: everything below parses the wrapper, which this family
# wrote and can therefore rely on being Python.
# -----------------------------------------------------------------------------------------------


def _aliases(tree, tool):
    """{local name: dotted upstream path} for every way this file names the wrapped tool.

    THE IMPORTS ARE INSIDE THE FUNCTIONS, deliberately - `scprofile/plugin.py` requires it, because
    module scope runs in the HOST's interpreter, which has none of the plugin's pins. So this walks
    the whole tree rather than the module body, and a grep for `^import` finds almost nothing.
    """
    root = str(tool).split(".")[0]
    out = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for al in node.names:
                if al.name == root or al.name.startswith(root + "."):
                    out[al.asname or al.name.split(".")[0]] = al.name
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod == root or mod.startswith(root + "."):
                for al in node.names:
                    out[al.asname or al.name] = f"{mod}.{al.name}"
    return out


def _dotted_name(node):
    """`sc.tl.score_genes` out of an ast attribute chain, or ""."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return ""
    parts.append(node.id)
    return ".".join(reversed(parts))


def upstream_calls(source, tool):
    """{upstream dotted path: {line, passes:[kwarg names], text}} for calls into the wrapped tool.

    WHICH FUNCTIONS THIS WRAPPER ACTUALLY DRIVES, which is the set whose defaults matter. A tool
    exports hundreds; a plugin calls a handful, and it is that handful whose parameters are being
    inherited silently. `passes` is what the call names explicitly - everything else in the
    signature is a default nobody has looked at.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}
    al = _aliases(tree, tool)
    if not al:
        return {}
    out = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _dotted_name(node.func)
        if not name:
            continue
        head, _, rest = name.partition(".")
        if head not in al:
            continue
        full = al[head] + ("." + rest if rest else "")
        got = out.setdefault(full, {"line": node.lineno, "passes": set(), "calls": 0,
                                    "splat": False})
        got["calls"] += 1
        for kw in node.keywords:
            if kw.arg:
                got["passes"].add(kw.arg)
            else:
                # `f(**opts)` HIDES EVERY KEYWORD IT PASSES. Not the case in any shipped plugin,
                # but "passes: nothing by name" would otherwise be reported for a call that in
                # fact names all of them - the same blind spot the contract scan has for a
                # computed emit name, and knowable at the same moment.
                got["splat"] = True
    for v in out.values():
        v["passes"] = sorted(v["passes"])
    return out


def _satisfies(installed, pin):
    """Crudely: does this version sit inside this pin? Only used to decide whether to WARN."""
    m = re.findall(r"(>=|<=|==|<|>)\s*([0-9][0-9.]*)", str(pin))
    if not m:
        return True
    def parts(v):
        return tuple(int(x) for x in re.findall(r"\d+", v)[:3])
    got = parts(installed)
    for op, ver in m:
        want = parts(ver)
        n = min(len(got), len(want)) or 1
        a, b = got[:n], want[:n]
        if op == ">=" and not a >= b: return False
        if op == ">" and not a > b: return False
        if op == "<=" and not a <= b: return False
        if op == "<" and not a < b: return False
        if op == "==" and a != b: return False
    return True


def defaults_worksheet(tool, calls, params, declared, placeholder="TODO", pins=None):
    """What the wrapper is inheriting from the tool without saying so.

    `config` MEANS "THE TOOL'S OWN DEFAULTS, DECLARED RATHER THAN INHERITED", and the failure it
    exists to stop is silent: `predict_terminal_states()` was called bare, so the single number
    deciding which macrostates the fate probabilities are probabilities OF appeared nowhere a
    reader could see it. Nothing in the plugin was wrong; nothing said what it had chosen.

    Three groups, because they need three different decisions:
      PASSED      the call names it. Already a decision, and only worth declaring in `config` if a
                  user should be able to change it.
      INHERITED   the call does not name it and the tool has a default. THIS IS THE GROUP THE
                  STAGE IS FOR - each is a choice made by somebody else, invisible in the report.
      REQUIRED    no default upstream, so the call must supply it. Not a config question.

    Nothing is decided here either. An inherited default is not automatically a `config` key: most
    are noise and a handful decide the answer, and only a person who understands the method can
    say which. What the machine can do is stop them being invisible.
    """
    decided = set((declared or {}).keys())
    L = [f"    # {tool}: what this wrapper inherits without declaring it.",
         '    "config": {']
    for path in sorted(calls):
        info = params.get(path) or {}
        if not info.get("found"):
            # A MISSING ATTRIBUTE IS USUALLY THE WRONG INTERPRETER, AND THE TOOL KNOWS IT. Asked
            # with a python holding decoupler 2.2.0 about a plugin pinned to >=1.8,<1.9, this said
            # only "module has no attribute run_ulm" - true, useless, and it reads as a broken
            # plugin. The version is in hand and the pin is in the declaration; saying both turns
            # a puzzle into the answer.
            L.append(f"        # {path}: could not read its signature - {info.get('why_not', '')}")
            inst, want = info.get("installed", ""), (pins or {}).get(path.split(".")[0], "")
            if inst or want:
                L.append(f"        #      this interpreter has {inst or 'an unknown version'}"
                         + (f"; the plugin pins {want}" if want else ""))
                if inst and want and not _satisfies(inst, want):
                    L.append("        #      THOSE DISAGREE. Ask with the interpreter this plugin "
                             "runs in - `scprofile install <name> --prefix DIR` builds it - "
                             "because a signature from another version is one it will never see.")
            continue
        passed = set(calls[path].get("passes") or ())
        inherited = [q for q in info["params"]
                     if not q["required"] and q["name"] not in passed and q["name"] != "self"]
        required = [q["name"] for q in info["params"] if q["required"]]
        L.append(f"        # ---- {path}  (called at line {calls[path]['line']})")
        if info.get("summary"):
            L.append(f"        #      {_clip(info['summary'], 100)}")
        L.append(f"        #      passes: {sorted(passed) or 'nothing by name'}")
        if calls[path].get("splat"):
            L.append("        #      AND `**kwargs`, so this scan cannot see every keyword it "
                     "passes; the inherited list below may be too long.")
        if required:
            L.append(f"        #      required by the signature: {required}")
        if not inherited:
            L.append("        #      inherits nothing - every optional parameter is named.")
            continue
        L.append(f"        #      INHERITED SILENTLY ({len(inherited)}): each is a default chosen "
                 f"by {tool}, not by this plugin.")
        for q in inherited:
            # A CONFIG KEY OF THE SAME NAME IS NOT THE SAME PARAMETER, and saying "already in
            # config" for one implied it was handled. velocity declares `min_confidence` default
            # 0.5 - its OWN threshold for a figure gate - and calls `scv.tl.latent_time(A)` bare,
            # which inherits scvelo's `min_confidence` of 0.75. Two values, one name, both live in
            # the same plugin, and a reader of the config would reasonably think they were one.
            if q["name"] in decided:
                mine = (declared or {}).get(q["name"]) or {}
                mine_d = mine.get("default", "?") if isinstance(mine, dict) else "?"
                mark = (f'NAME COLLISION: this plugin declares `{q["name"]}` (default {mine_d!r}) '
                        f'and does NOT pass it here, so {tool} uses {q["default"]}')
            else:
                mark = f'{placeholder} — declare it, or leave it and say nothing?'
            L.append(f'        #        {q["name"]:24s} = {q["default"]:<22s} {mark}')
    L.append("    },")
    return "\n".join(L)


#: Names that mean "this fetches something the user did not supply". Deliberately broad: a false
#: positive costs a glance at a line number, and a missed reference is one the plan cannot warn
#: about and the report cannot name.
_FETCHY = re.compile(r"^(get|fetch|load|download|read)_|^(get|fetch|download)$", re.I)
_URL = re.compile(r"https?://[^\s\"\'<>)]+")


def _literal_items(node):
    """The strings a module-level assignment holds, seeing through a trailing `.split()`.

    THE FIRST VERSION MISSED THE ONLY REAL FINDING. cellcycle's gene sets are written
    `S_GENES = <triple-quoted block>.split()`, which is a Call and not a literal, so
    `ast.literal_eval` raised and the 97 symbols this plugin scores every cell against were
    invisible - while a docstring assigned to a variable came back as a 29-entry data set.
    """
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
            and node.func.attr == "split":
        node = node.func.value
    try:
        value = ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError):
        return []
    if isinstance(value, str):
        return [t for t in value.split() if t]
    if isinstance(value, (list, tuple, set, frozenset)):
        return [t for t in value if isinstance(t, str)]
    return []


#: A symbol, not a word. `origin (29 entries, e.g. on, the, single)` was a docstring split on
#: whitespace and reported as a data set; requiring most entries to look like identifiers rather
#: than prose is what tells 97 gene symbols from a paragraph.
_SYMBOL = re.compile(r"^[A-Z0-9][A-Z0-9._:-]{1,}$")


def references_in(source, tool="", min_items=20, symbol_share=0.7):
    """[{kind, what, line, why}] for everything this plugin consults that is not the user's object.

    THREE SHAPES, and the third is the one that hides. A URL is obvious. A call named
    `get_progeny` is nearly obvious. A gene list pasted into the file is not obvious at all -
    cellcycle carries 97 symbols from Tirosh et al. 2016, declares `references: None`, and the
    report therefore cannot say where its phase calls came from. Its own comment says HUMAN
    symbols, which is the case the format warns about: a prior published for one organism returns
    a small plausible table for the wrong one rather than failing.

    A LITERAL IS A `bundled` REFERENCE. It ships with the plugin and is pinned by the plugin's
    version, which is what that tier means; being spelled in Python rather than downloaded changes
    who stores it, not whether it decides the answer.

    URLS IN PROSE ARE NOT REFERENCES. Every plugin records its upstream's homepage and docs in its
    own declaration, and reporting those made each plugin look like it had two undeclared fetches.
    Only URLs in executable code count - a URL something actually goes to.
    """
    out = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return out
    docs = {id(n) for n in ast.walk(tree)
            if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            and getattr(n, "body", None) and isinstance(n.body[0], ast.Expr)
            and isinstance(n.body[0].value, ast.Constant)
            for n in [n.body[0].value]}
    declared = {id(n) for a in tree.body
                if isinstance(a, ast.Assign) and getattr(a.targets[0], "id", "") == "PLUGIN"
                for n in ast.walk(a)}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        if id(node) in docs or id(node) in declared:
            continue
        for u in _URL.findall(node.value):
            out.append({"kind": "fetch", "what": u, "line": getattr(node, "lineno", 0),
                        "why": "a URL in executable code. Declare it with a checksum, or say "
                               "which tier it is."})
    if tool:
        for path, info in sorted(upstream_calls(source, tool).items()):
            if _FETCHY.match(path.rsplit(".", 1)[-1]):
                out.append({"kind": "runtime?", "what": path, "line": info["line"],
                            "why": "named like something that fetches. If it reaches the network "
                                   "at run time the COMPUTE NODE needs a route, and a node "
                                   "without one fails after the queue slot is spent."})
    for node in tree.body:
        if not isinstance(node, ast.Assign) or not isinstance(node.targets[0], ast.Name):
            continue
        items = _literal_items(node.value)
        if len(items) < min_items:
            continue
        share = sum(1 for t in items if _SYMBOL.match(t)) / len(items)
        if share < symbol_share:
            continue
        out.append({"kind": "bundled",
                    "what": f"{node.targets[0].id} ({len(items)} entries, e.g. "
                            f"{', '.join(items[:3])})",
                    "line": node.lineno,
                    "why": "a data set written into the plugin. It ships with this file and is "
                           "pinned by its version - that is what `bundled` means - and the report "
                           "cannot name it while it is undeclared."})
    return out


def contract_in(source):
    """{produces:[...], reads:[...]} inferred from what the plugin emits and asks `ctx` for."""
    produces, reads = [], set()
    #: Emissions whose name is COMPUTED, so this scan cannot say what they are called. velocity
    #: emits inside `for col in ...: ctx.emit_obs(col, ...)` and as an f-string, which is why a
    #: scan of it finds 3 tables where the declaration has 9. THAT DIFFERENCE IS NOT EVIDENCE THE
    #: DECLARATION IS WRONG, and presenting the found set as if it were a replacement would have
    #: deleted six correct entries.
    dynamic = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {"produces": [], "report.figures": [], "reads": [], "dynamic": []}
    # FIGURES ARE NOT `produces` AND MUST NOT BE OFFERED AS IF THEY WERE. They are declared in
    # `report.figures`, each with the question it settles; listing them here sent a reader to add
    # five entries to the wrong field. Grouped by where each one is declared.
    EMIT = {"emit_obs": ("produces", "obs[{}]"), "emit_obsm": ("produces", "obsm[{}]"),
            "emit_layer": ("produces", "layers[{}]"), "emit_table": ("produces", "tables/{}"),
            "emit_figure": ("report.figures", "{}")}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            fn = node.func.attr
            if fn in EMIT and node.args:
                where, shape = EMIT[fn]
                arg = node.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    produces.append((where, shape.format(arg.value)))
                else:
                    dynamic.append((fn, node.lineno, ast.unparse(arg)[:60]
                                    if hasattr(ast, "unparse") else "<computed>"))
        if isinstance(node, ast.Attribute) and _dotted_name(node).startswith("ctx."):
            reads.add(_dotted_name(node).split(".", 2)[1])
        if isinstance(node, ast.Subscript) and _dotted_name(node.value) == "ctx.keys" \
                and isinstance(node.slice, ast.Constant):
            reads.add(f"keys[{node.slice.value}]")
    out = {"produces": [], "report.figures": [], "reads": sorted(reads), "dynamic": dynamic}
    for where, what in sorted(set(produces)):
        out[where].append(what)
    return out


def _families(spec, rules):
    """[(figure id, field it came from, is it drawn once per data item)] from a declaration.

    THE FIELDS AND HOW TO READ THEM COME FROM THE REPOSITORY'S OWN DECLARATION, never from here.
    One repository names its upstream plots in `native_plots` with the filenames written into a
    prose `use:`; another will name them somewhere else in some other shape. A rule says which
    field to read and whether the id is a key, a value at a path, or a filename inside text.
    """
    out = []
    for rule in rules or []:
        field = str(rule.get("field") or "")
        if not field:
            continue
        node = spec or {}
        for part in field.split("."):
            node = (node or {}).get(part) if isinstance(node, dict) else None
        if not node:
            continue
        named_by = str(rule.get("named_by") or "")
        per_item_mark = str(rule.get("per_item") or "")
        bound = str(rule.get("bound") or "")
        entries = node.items() if isinstance(node, dict) else enumerate(node)
        for key, rec in entries:
            rec = rec if isinstance(rec, dict) else {}
            if rec.get("skip"):
                continue
            text = str(rec.get(named_by) or "") if named_by else str(key)
            if named_by == "id" or not named_by:
                ids = [text] if text else []
            else:
                # THE FILENAMES INSIDE THE TEXT, including a brace family written as one token.
                # THE DIRECTORY IS WRITTEN ONCE AND THE FILES FOLLOW IT, in English: "figures/
                # native_circle_count.png and native_circle_weight.png". Requiring `figures/` on
                # every name found the first and missed the second, and the migration worksheet
                # built from this left a family of eighteen files out of the plan without a
                # word. The extension is what makes a token a figure; a `.csv` is not one.
                ids = []
                for m in re.finditer(r"(?:figures/)?([A-Za-z0-9_{},<>-]+?)\.(?:png|pdf|svg)",
                                     text):
                    ids.append(m.group(1))
            for fid in ids:
                per = bool(per_item_mark) and per_item_mark in fid
                # THE STEM STOPS AT THE FIRST THING THAT VARIES, whichever way this format
                # writes it: `__<unit>`, a `{count,weight}` brace family, or a bare `<pattern>`
                # in the middle of the name. Missing the third reported
                # `nativecmp_signalingRole_heatmap_<pattern>` as a family of its own, so a rule
                # placing `nativecmp_signalingRole_heatmap` would never have matched it.
                stem = re.split(r"__|\{|<", fid)[0].rstrip("_")
                # A CEILING PER FAMILY, NOT PER ENTRY. `netVisual_aggregate` names both
                # `native_aggregate_circle__<pathway>` (one per unit) and
                # `nativecmp_aggregate_circle__<pathway>` (six per contrast) in one `use:`, and a
                # single number bounded both - so the per-unit family was declared at 6 where it
                # draws 1, and a plan computed from the declaration over-counted it by 90. A
                # scalar still means "all the families in this entry", which is right when there
                # is one.
                cap = rec.get(bound) if bound else None
                if isinstance(cap, dict):
                    cap = cap.get(stem, cap.get(fid))
                out.append((stem, field, per, bound, cap))
    seen, uniq = set(), []
    for row in out:
        if row[0] in seen:
            continue
        seen.add(row[0])
        uniq.append(row)
    return uniq


def generated_drift(st, doc, point_name, name, python=""):
    """[{file, verdict, note}] - does each generated companion still match what generates it?

    DEMANDED, CHECKED, AND GENERATED ARE THREE DIFFERENT CLAIMS. A stage can require that a
    plugin's drawing code refuses past its declared ceilings; it can find the code that does; and
    neither of those says the code is the maker's OUTPUT rather than a hand-written file that
    satisfies the check. The difference matters because the whole reason to generate mechanism is
    that one definition serves every plugin - and a hand-written look-alike is one definition
    again the moment somebody edits it.

    So this RUNS the generator into a scratch directory and compares, byte for byte.

    THE GENERATOR RUNS IN THE HOST'S INTERPRETER, not the plugin's. It is the repository's own
    tool and it is the same tool whatever the plugin is written in; `{python}` here is this
    process, and a plugin's pinned environment - which may not have the host installed at all -
    is the wrong place to ask for it.

    An absent declaration is an absent question: a repository that generates nothing gets no rows
    and no verdict, exactly as it did before this existed.
    """
    cfg = st.get("generated_by") or {}
    argv = cfg.get("command")
    if not argv or not name:
        return []
    target = artefact(doc, point_name, name)
    if target is None:
        return [{"file": "", "verdict": "cannot say",
                 "note": f"no {point_name} named {name!r} to compare against"}]
    root = str(doc.get("_root") or ".")
    with tempfile.TemporaryDirectory(prefix="sch-generated-") as tmp:
        cmd = fill(list(argv), {"python": sys.executable, "name": name, "root": root, "out": tmp})
        try:
            r = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=300)
        except (OSError, subprocess.SubprocessError) as e:                # noqa: BLE001
            return [{"file": "", "verdict": "cannot say",
                     "note": f"{' '.join(cmd)} could not run: {e}"}]
        if r.returncode != 0:
            return [{"file": "", "verdict": "cannot say",
                     "note": f"{' '.join(cmd)} exited {r.returncode}: "
                             f"{(r.stderr or r.stdout).strip().splitlines()[-1:] or ['']}"[2:-2]}]
        made = sorted(p for p in Path(tmp).rglob("*") if p.is_file())
        if not made:
            return [{"file": "", "verdict": "none",
                     "note": f"{' '.join(cmd)} wrote nothing, so this {point_name} has no "
                             f"generated companion to drift from"}]
        out = []
        for g in made:
            beside = Path(target).parent / g.name
            if not beside.is_file():
                out.append({"file": g.name, "verdict": "MISSING",
                            "note": f"the generator writes {g.name} and it is not beside this "
                                    f"{point_name}"})
            elif beside.read_bytes() != g.read_bytes():
                out.append({"file": g.name, "verdict": "DRIFTED",
                            "note": f"{g.name} beside this {point_name} is not what the "
                                    f"generator writes - it has been edited in place, so the "
                                    f"next regeneration silently reverts it"})
            else:
                out.append({"file": g.name, "verdict": "generated", "note": ""})
        return out


def generated_report(rows):
    """A sentence for `generated_drift`, including when there was nothing to ask about."""
    if not rows:
        return ""
    bad = [r for r in rows if r["verdict"] in ("MISSING", "DRIFTED")]
    mute = [r for r in rows if r["verdict"] in ("cannot say", "none")]
    if mute:
        return "; ".join(r["note"] for r in mute)
    if not bad:
        return (f"{len(rows)} generated companion(s) match what generates them, byte for byte: "
                + ", ".join(r["file"] for r in rows))
    return "; ".join(f"{r['verdict']} {r['file']}: {r['note']}" for r in bad)


def placement_debt(spec, st, source_text="", also_r=(), generated=()):
    """What a plugin still owes on WHERE its figures go, HOW MANY of each, and whether the code
    that draws them reads the ceiling."""
    rules = st.get(PLACES_KEY) or []
    placed = {str(k): str(v) for k, v in
              (((spec or {}).get("report") or {}).get("figure_position") or {}).items()}
    ok_positions = [str(x) for x in (st.get("positions") or [])]
    # WHAT A FAMILY MULTIPLIES OVER, read the same way a position is: a prefix map the plugin
    # owns, longest match wins. Without it a ceiling is a number with no units - "at most 6" of
    # what, per run or per unit or per contrast? - and no count can be computed from the
    # declaration before anything is scheduled, which is the whole point of having one.
    axis_field = str(st.get("axis_field") or "")
    axes = [str(x) for x in (st.get("axes") or [])]
    amap = {}
    if axis_field:
        node = spec or {}
        for part in axis_field.split("."):
            node = (node or {}).get(part) if isinstance(node, dict) else None
        amap = {str(k): str(v) for k, v in (node or {}).items()}
    # THE ENTRY'S OWN WORD, THEN THE PREFIX MAP (harness ADR-0016) - the rule the target's one
    # reader applies. A plan entry that says where it goes and what it multiplies over is folded
    # into the map as an exact key; longest prefix wins, so it beats any broader rule. Without
    # this a migrated plugin, carrying no map at all, came back owing every one of its 57
    # families twice - each entry saying in its own words exactly what it was asked for - and
    # the stage the migration exists to finish read `todo` forever.
    ek = {str(k): str(v) for k, v in (st.get(ENTRY_KEYS) or {}).items()}
    _f, own = _entries(spec, st)
    for e in own:
        fid = str(e.get("id") or "").strip()
        if not fid:
            continue
        if e.get(ek.get("position", "position")) is not None:
            placed.setdefault(fid, str(e[ek.get("position", "position")]))
        if axis_field and e.get(ek.get("axis", "axis")) is not None:
            amap.setdefault(fid, str(e[ek.get("axis", "axis")]))
    keys = sorted(placed, key=len, reverse=True)
    akeys = sorted(amap, key=len, reverse=True)

    # AND WHETHER THE DRAWING CODE READS THE CEILING AT ALL. A declaration the code ignores is a
    # comment: one plugin declared 49 ceilings, enforced none of them, and the whole build phase
    # reported finished. Deleting a declaration turns this stage red at once; until now, deleting
    # the code that honours it turned nothing red.
    guards, guard_says = [], ""
    enf = st.get("enforced_by") or {}
    if enf.get("token") and source_text:
        from .extract import draw_sites as _DS
        guards = _DS.ceiling_guards(source_text, str(enf["token"]),
                                    str(enf.get("returns") or "return"), also=also_r)
        guard_says = _DS.guard_report(guards, str(enf["token"]))

    fams = _families(spec or {}, rules)
    unplaced, unbounded, wrong, unaxised = [], [], [], []
    for stem, field, per, bound, value in fams:
        if axis_field:
            hit_a = next((k for k in akeys if stem.startswith(k)), "")
            if not hit_a:
                unaxised.append((stem, axis_field))
            elif axes and amap[hit_a] not in axes:
                wrong.append((stem, amap[hit_a]))
        hit = next((k for k in keys if stem.startswith(k)), "")
        if not hit:
            unplaced.append((stem, field))
        elif ok_positions and placed[hit] not in ok_positions:
            wrong.append((stem, placed[hit]))
        # A FAMILY DRAWN ONCE PER DATA ITEM HAS NO SIZE UNTIL A COHORT ARRIVES, which is exactly
        # why the bound belongs in the declaration and not in the run. Measured: one contrast
        # drew 62 panels of one family over the populations two arms shared, and 72 of another
        # over pathways; on a cohort with forty populations the same loop draws 240.
        if per and not value:
            unbounded.append((stem, field, bound))
    return {"looked": bool(rules), "families": fams, "unplaced": unplaced,
            "unbounded": unbounded, "wrong": wrong, "positions": ok_positions,
            "unaxised": unaxised, "axes": axes, "axis_field": axis_field,
            # ONLY WHEN A CEILING IS DECLARED. A plugin that bounds nothing owes no guard, and
            # reporting one would be a demand nobody could act on.
            "unguarded": ([g for g in guards if not g["guarded"]]
                          if any(v for _s, _f, _p, _b, v in fams) else []),
            # EVERY WRAPPER THE CHECK FOUND, not only the ones that failed. An empty list here
            # and an empty `unguarded` mean opposite things - nothing to look at, and nothing
            # wrong - and only the first of them is a corpus of zero.
            "guards": guards,
            "enforces": bool(enf.get("token")),
            "guard_says": guard_says,
            # AND WHETHER THE CODE THAT HONOURS THE CEILING IS THE MAKER'S OUTPUT. Computed at
            # the call site because it RUNS a command, and `placement_debt` is called from a
            # status that must stay cheap enough to run on every edit.
            "generated": list(generated),
            "ungenerated": [g for g in generated if g["verdict"] in ("MISSING", "DRIFTED")],
            "generated_says": generated_report(generated)}


def _companions(path, suffix):
    """Files carrying `suffix` that belong to THIS artefact, by name. Never a shared sibling.

    A COMPANION IS NAMED FOR ITS PLUGIN OR IT IS SOMEBODY ELSE'S. Two shapes count, and only
    two: a file inside a directory named for the artefact (`kernels/cellchat/draw.R`), and a
    sibling whose name is the artefact's own stem and then a separator
    (`kernels/cellchat.draw.R`, or `kernels/cellchat.R`).

    THE SEPARATOR IS LOAD-BEARING. Written as a bare prefix this borrowed one stem further along
    the alphabet: `alphabet.draw.R` answered for `alpha`, because `alpha` is a prefix of
    `alphabet`. The suite caught it on the first run of the rule it was written for.

    THE FIRST VERSION GLOBBED THE WHOLE DIRECTORY and it is the borrowing defect this repository
    already keeps a test for, one point over. Nine one-file plugins live in one `kernels/`, so a
    single `kernels/draw.R` written by whichever of them was scaffolded first would have answered
    the ceiling-guard requirement for ALL NINE - including the eight that never read it. The
    check would then be green for a plugin that is unbounded, and go red the day that plugin was
    deployed alone, which is exactly when nobody is looking at this stage any more.
    """
    out = []
    for f in companion_paths(path, suffix):
        try:
            out.append((f.read_text(encoding="utf-8", errors="replace"), f.name))
        except OSError:
            continue
    return out


def companion_paths(path, suffix=""):
    """[Path] for the files that belong to THIS artefact by name. Reads no content.

    Separate from `_companions` because the RULE checker needs the names and not the text: a
    generated companion of the artefact a round is converting is in that round's scope by the
    same definition the artefact is, and reading every one of them to find that out would make
    a path question depend on a file being readable.
    """
    p = Path(path)
    stem = p.stem
    beside = sorted(set(p.parent.glob(f"{stem}.*{suffix}")) | set(p.parent.glob(f"{stem}{suffix}")))
    return sorted(p.parent.glob(f"{stem}/*" + suffix)) + [f for f in beside if f != p]


def _r_beside(doc, point_name, name):
    """[(text, filename)] for R kept in a file next to the plugin rather than inside it.

    The scaffolded form is one draw wrapper prepended to every embedded script, so the wrapper is
    defined once. A check that read only the Python would not see it.
    """
    path = artefact(doc, point_name, name) if name else None
    if path is None:
        return []
    try:
        return _companions(path, ".R")
    except OSError:
        return []


def _source_of(doc, point_name, name):
    """The plugin's own source, or "" - the same artefact `measure_draw_sites` reads."""
    path = artefact(doc, point_name, name) if name else None
    try:
        return path.read_text(encoding="utf-8") if path else ""
    except OSError:
        return ""


def placement_worksheet(spec, doc, point_name, stage_name, name="", width=96):
    """One row per figure family this plugin has not said where it goes, or how many it draws."""
    import textwrap
    _ph, _up, stages = plan(doc, point_name)
    st = next((x for x in stages if x["name"] == stage_name), None)
    if st is None:
        raise ConvertError(f"no stage named {stage_name!r} in point {point_name!r}")
    if not st.get(PLACES_KEY):
        raise ConvertError(
            f"stage {stage_name!r} declares no `{PLACES_KEY}:`, so this repository has not said "
            f"which declarations name a figure family. This worksheet is for a stage that has.")
    d = placement_debt(spec, st, source_text=_source_of(doc, point_name, name),
                       also_r=_r_beside(doc, point_name, name),
                       generated=generated_drift(st, doc, point_name, name))
    fams = d["families"]
    L = [f"{stage_name}: {len(fams)} figure family(ies) declared by {name or 'this plugin'}. "
         f"{len(fams) - len(d['unplaced'])} placed, {len(d['unplaced'])} not; "
         f"{len(fams) - len(d['unaxised'] and d['unaxised'] or [])if False else len(fams) - len(d['unaxised'])}"
         f" say what they multiply over, {len(d['unaxised'])} do not; "
         f"{len(d['unbounded'])} drawn per data item with no bound."]
    L += textwrap.wrap(
        "A POSITION IS NOT A RANKING. It says where in a result a figure is read - and "
        "`appendix` says a result is not written from it at all, which keeps it out of the "
        "paper's numbering and out of what the writing step waits on. It is still drawn, still "
        "placed on the pages, still reviewable.", width=width, initial_indent="  ",
        subsequent_indent="  ")
    L += textwrap.wrap(
        "A BOUND IS THE MOST FILES THIS FAMILY WRITES PER OCCURRENCE OF ITS AXIS - not the most "
        "items it iterates. A family drawing each of six pathways once per arm writes twelve "
        "files per contrast, and declaring six under-counts it by half. The number has to mean "
        "files or nothing can be multiplied by it.",
        width=width, initial_indent="  ", subsequent_indent="  ")
    L.append("")
    if d.get("generated_says"):
        L += textwrap.wrap(f"generated: {d['generated_says']}", width=width,
                           initial_indent="  ", subsequent_indent="    ")
        L.append("")
    if d.get("guard_says"):
        L += textwrap.wrap(f"ceiling guards: {d['guard_says']}", width=width,
                           initial_indent="  ", subsequent_indent="    ")
        L.append("")
    for g in d.get("unguarded", []):
        L.append(f"  READS NO CEILING  {g['wrapper']}  at line {g['line']}")
        L.append(f"            this plugin declares ceilings and this wrapper draws without "
                 f"consulting one.")
        L.append(f"            Add an early exit at the top of the body, before the panel is "
                 f"computed:")
        L.append(f"                if (<the family is full>) return(invisible(NULL))")
        L.append("            A declaration the drawing code does not read is a comment.")
        L.append("")
    if d.get("ungenerated"):
        for g in d["ungenerated"]:
            L.append(f"  GENERATE  {g['file']}")
            L.append(f"            {g['note']}")
            L.append(f"            Regenerate it - the stage declares the command under "
                     f"`generated_by` - and put the change in the GENERATOR.")
            L.append("")
    # EVERY DEBT OF THIS STAGE, NOT THE THREE IT STARTED WITH. The closing sentence read
    # "Every declared figure family is placed, says what it multiplies over, and is bounded"
    # while the generated companion sat DELETED four lines above it, because the condition had
    # not grown with the stage. A summary that is true of part of a check reads as a pass.
    if not (d["unplaced"] or d["unbounded"] or d["wrong"] or d["unaxised"]
            or d.get("unguarded") or d.get("ungenerated")):
        L.append("  Every declared figure family is placed, says what it multiplies over, and "
                 "is bounded.")
        return "\n".join(L)
    if not (d["unplaced"] or d["unbounded"] or d["wrong"] or d["unaxised"]):
        return "\n".join(L)
    for stem, field in d["unplaced"]:
        L.append(f"  PLACE     {stem}")
        L.append(f"            declared in {field}; add a `report.figure_position` rule - "
                 f"one of {', '.join(d['positions']) or 'the positions this stage declares'}")
    for stem, pos in d["wrong"]:
        L.append(f"  NOT A POSITION  {stem} is placed {pos!r}, which this stage does not declare")
    for stem, field in d["unaxised"]:
        L.append(f"  AXIS      {stem}")
        L.append(f"            add a `{field}` prefix rule - one of "
                 f"{', '.join(d['axes']) or 'the axes this stage declares'}. A ceiling with no "
                 f"axis is a number with no units, and no count can be computed from it")
    for stem, field, bound in d["unbounded"]:
        L.append(f"  BOUND     {stem}")
        L.append(f"            declared in {field} as one panel per data item and with no "
                 f"`{bound}:` - add it, and cap the loop that draws it")
    L.append("")
    return "\n".join(L)


def items_worksheet(spec, doc, point_name, stage_name, width=96):
    """The worksheet for any stage that rules on every entry of a list, not just on the field.

    WHAT IT DOES NOT CHECK, AND WHY THAT IS THE RIGHT LINE. For legends this rules on the
    PROVENANCE - a fact about the figure that is true before the run and is therefore a build
    stage's business. It does not check that a sentence was written, because the sentence is
    written where the figure is DRAWN, out of numbers that do not exist until something runs: how
    many pairs there were before the cap, which populations were dropped, what n is. A build
    stage that demanded the sentence would be asking for one that could only be a guess, and a
    guessed legend is worse than an absent one - it is believed. The sentence is proved at test
    time, by reading back what the run wrote beside its figures.
    """
    _ph, _up, stages = plan(doc, point_name)
    st = next((x for x in stages if x["name"] == stage_name), None)
    if st is None:
        raise ConvertError(f"no stage named {stage_name!r} in point {point_name!r}")
    if not st.get("each_item_declares"):
        raise ConvertError(
            f"stage {stage_name!r} declares no `each_item_declares:`, so there is nothing to rule "
            f"on entry by entry. This worksheet is for a stage whose field is a LIST and whose "
            f"work is one decision per item.")
    ig = item_gaps(spec, st) or {}
    lines = [f"{stage_name}: {ig.get('total', 0)} entries in `{ig.get('field', '?')}`, "
             f"{len(ig.get('gaps', ()))} still to rule on"]
    for k, allowed in (st.get("each_item_declares") or {}).items():
        lines.append(f"  every entry must declare  {k}: "
                     + (" | ".join(str(x) for x in allowed) if allowed else "<any non-empty>"))
    why = " ".join(str(st.get("why", "")).split())
    if why:
        import textwrap
        lines += textwrap.wrap(why, width=width, initial_indent="  ", subsequent_indent="  ")
    lines.append("")
    items = _dotted(spec, ig.get("field") or "") or []
    bad = dict(ig.get("gaps") or ())
    for i, it in enumerate(items):
        d = it if isinstance(it, dict) else {}
        who = str(d.get("id") or d.get("name") or f"entry {i + 1}")
        mark = "TO RULE" if who in bad else "     ok"
        lines.append(f"  {mark}  {who}")
        # THE PLUGIN'S OWN WORDS ARE THE PROMPT. Whoever fills this in needs to know what the
        # panel is FOR, and the plugin already says so; making them go and look it up is how a
        # worksheet gets filled in by pattern rather than by reading.
        for key in ("question", "shows", "what"):
            if d.get(key):
                import textwrap
                lines += textwrap.wrap(f"{key}: {d[key]}", width=width,
                                       initial_indent="           ", subsequent_indent="           ")
                break
        for reason in bad.get(who, ()):
            lines.append(f"           -> {reason}")
    return "\n".join(lines)


def draw_worksheet(doc, point_name, stage_name, name, source=None, width=96, inv=None):
    """The half of a legends worksheet that is measured from the plugin's source.

    WHAT A WORKSHEET IS FOR, AND WHAT THIS ONE HAS TO CARRY. `items_worksheet` above rules on a
    DECLARED list and its rows are labelled by the plugin's own ids, so a person filling it in
    already knows what each row is. A draw site has no id and no declaration: it is a line of
    code, and the only reason somebody can write a true sentence about it is that the line says
    what is being plotted. So each row carries the panel name AS WRITTEN - a literal or the
    `paste0(...)` that makes one name per pathway - the plotting call underneath it, and the file
    and line to open.

    IT WRITES NOTHING AND DECIDES NOTHING, for the same reason `worksheet` does not: this can see
    that a legend is absent and cannot see what the panel shows. A sentence generated from a
    function name would be a label in the place a description goes, which is the exact defect the
    host's caption module was written to remove - and a wrong legend is believed where an absent
    one is noticed.

    THE EDIT IS SHOWN, NOT MADE. Each row prints the argument to add and where to add it, because
    the fix is one keyword argument at a call site whose wrapper already has the parameter.
    """
    import textwrap
    _ph, _up, stages = plan(doc, point_name)
    st = next((x for x in stages if x["name"] == stage_name), None)
    if st is None:
        raise ConvertError(f"no stage named {stage_name!r} in point {point_name!r}")
    if not st.get(DRAWS_KEY):
        raise ConvertError(
            f"stage {stage_name!r} does not declare `{DRAWS_KEY}:`, so this repository has not "
            f"said that a panel produced without a legend is unfinished work. This worksheet is "
            f"for a stage that has.")
    if inv is None:
        inv = measure_draw_sites(doc, point_name, name, source)
    d = draw_debt(inv)
    if not d["looked"]:
        return "\n".join([
            f"{stage_name}: COULD NOT LOOK at {name}'s draw sites.",
            f"  {d['why_not']}",
            "  An empty worksheet here would read as a plugin whose every panel is described.",
        ])
    L = [f"{stage_name}: {d['total']} draw site(s) in {name}. {d['described']} pass a legend, "
         f"{len(d['silent'])} do not"
         + (f", {len(d['unknown'])} draw through a wrapper that has no legend parameter"
            if d["unknown"] else "") + "."]
    L += textwrap.wrap(f"how they were found: {d['how']}", width=width,
                       initial_indent="  ", subsequent_indent="    ")
    L += textwrap.wrap(
        "A legend is written HERE, at the draw site, because here is where the numbers that "
        "describe the panel still exist - the n, the cap that was applied, the populations that "
        "were dropped. Written anywhere else it can only be a guess, and a guessed legend is "
        "worse than an absent one: the page prints it in the space a description goes, and a "
        "reader believes it.", width=width, initial_indent="  ", subsequent_indent="  ")
    # WHAT THE THIRD COLUMN IS, SAID ON THE PAGE THAT PRINTS IT. It is a filtered list of the
    # names called in the expression, not a measurement of which of them draws - a plotting call
    # assigned to a variable on the line above is not in the expression at all. Measured on the
    # plugin this was built against, 2 of 35 rows name the wrong function. The file, the line and
    # the count do not come from it.
    L += textwrap.wrap(
        "`names called` is what the drawn expression calls, with helpers and language "
        "scaffolding filtered out BY A LIST - a guess at which of them draws the panel and not a "
        "measurement of it, wrong on a small minority of rows, and no part of the count or the "
        "line number. Open the line.",
        width=width, initial_indent="  ", subsequent_indent="  ")
    L.append("")
    # FIRST, AND ABOVE THE MISSING ONES. A legend that is absent costs a reader a sentence; a
    # legend the language cannot run costs the run every panel downstream of it. This is printed
    # before the worksheet proper because it is not worksheet work - nothing here is waiting on a
    # sentence anybody has to think of.
    if d.get("broken_read"):
        L += textwrap.wrap(f"calls read for a missing argument: {d['broken_read']}",
                           width=width, initial_indent="  ", subsequent_indent="    ")
        L.append("")
    for line, text in d.get("broken", []):
        L.append(f"  WILL NOT RUN  {name}:{line}")
        L += textwrap.wrap(_clip(text, 400), width=width,
                           initial_indent="                ", subsequent_indent="                ")
        L.append("                an argument slot in this call holds nothing. R PARSES IT: the "
                 "file imports,")
        L.append("                the environment installs and the selftest passes, and the call "
                 "fails the moment")
        L.append("                it is evaluated with \"argument is missing, with no default\". "
                 "Fix the call.")
        L.append("")
    if not d["silent"] and not d["unknown"]:
        if not d.get("broken"):
            L.append("  Every draw site in this plugin passes a legend. Nothing to fill in.")
        return "\n".join(L)
    for s in d["silent"]:
        L.append(f"  TO WRITE  {s['file']}:{s['line']}")
        L.append(f"            panel name as written:  {_clip(s.get('panel') or '?', width - 36)}")
        if s.get("calls"):
            L.append(f"            {'names called:':<24}{', '.join(s['calls'])}")
        # WHAT TO SHOW IS NOT THE SAME IN THE TWO LANGUAGES. Where the wrapper is handed the
        # plotting expression, that expression IS the panel and it is what a reader needs. Where
        # the wrapper is handed a finished figure object, the expression is the variable's name
        # and says nothing - so the whole call is shown, and the line number is what takes the
        # reader to the drawing above it.
        shown = s.get("draws") if s.get("lang") == "R" else s.get("call")
        if shown:
            L += textwrap.wrap(_clip(shown, 600), width=width,
                               initial_indent="            call:   ",
                               subsequent_indent="                    ")
        L.append(f"            add:                    {s['legend_param']} = \"...\"   "
                 f"(the wrapper is {s['wrapper']}, defined at {s.get('wrapper_at', '?')})")
        L.append("")
    for s in d["unknown"]:
        L.append(f"  NO SLOT   {s['file']}:{s['line']}  {s['wrapper']}({_clip(s.get('panel'), 40)})")
        L.append(f"            {s['wrapper']} is defined at {s.get('wrapper_at', '?')} and no "
                 f"parameter of it defaults to the empty string,")
        L.append("            so no call to it can pass a legend. The wrapper is what has to "
                 "change, not these call sites.")
        L.append("")
    return "\n".join(L)


#: EVERY ACTION `sch dev convert` HAS, IN ONE PLACE. `sch/cli.py` builds the parser's `choices`
#: from this, and `advance_command` below decides from it whether a stage can be advanced by a
#: command: a stage advances by the action of the same name, when this tool has one.
#:
#: IT WAS TWO LISTS AND THAT IS THE DEFECT THIS FILE ALREADY RECORDS ONE LEVEL UP. `sch/cli.py`
#: names its `specs` set BY EXCLUSION because an inclusive one was "a second place to register an
#: action and `legends` was added to the parser and not to it". The very next list in the same
#: file was inclusive, hand-maintained and named `ADVANCES` - and `placement` and `promised` were
#: added to the parser, to DEVPOINTS and not to it. Both then reported "nothing runs this - it is
#: what only you can answer" about a MECHANICAL stage whose `finished_by` names the exact command
#: to type. Found by generating a plugin from nothing and reading what the maker said to do next.
ACTIONS = ("status", "freshness", "borrowed", "inventory", "account", "measure", "promised",
           "defaults", "references", "contract", "legends", "placement", "plan", "overfit",
           "build")


# -----------------------------------------------------------------------------------------------
# THE FIGURE PLAN (harness ADR-0016). A stage that fills a list of figure entries and declares
# `entry_keys` is a plan stage: the list carries the call - which upstream function, with which
# arguments, over which items, under which ceiling, placed where, described how - and the target
# repository generates its draw sites from it. Nothing here knows what the keys are called; the
# stage says, the way `version_field` and `axis_field` already do.
# -----------------------------------------------------------------------------------------------

#: What a plan stage declares: the maker's word for a thing -> this format's key for it.
ENTRY_KEYS = "entry_keys"
#: The plan's interpreter, as the generated companion names it (harness ADR-0016): a call to
#: either is a site already on the plan, never a hand-written one.
PLAN_INTERPRETER = (".draw", ".draw_all")


def plan_stage(doc, point_name):
    """The stage that carries the plan, or None: the one declaring `entry_keys`."""
    _ph, _up, stages = plan(doc, point_name)
    for st in stages:
        if isinstance(st.get(ENTRY_KEYS), dict):
            return st
    return None


def _entries(spec, st):
    """(field, [entries]) - the list the plan stage fills, as this plugin declares it."""
    for f in st.get("fills") or ():
        v = _dotted(spec, f)
        if isinstance(v, list):
            return str(f), [e for e in v if isinstance(e, dict)]
    return str((st.get("fills") or [""])[0]), []


def plan_worksheet(spec, doc, point_name, name="", inv=None, width=96, rscript=""):
    """Every entry of the plan, what it lacks, and the upstream function's parameters beside it.

    A TABLE, NOT A VERDICT. `status` says whether the stage is done; this shows the plan a person
    adjusts - one row per figure family - so that changing a heatmap's measure or a ceiling is a
    matter of reading a row and editing an entry. With an inventory (`--python`), each `fn` is
    followed by its signature from the package, which is what somebody writing `args` needs.
    """
    st = plan_stage(doc, point_name)
    if st is None:
        raise ConvertError(f"point {point_name!r} declares no plan stage - no stage carries "
                           f"`{ENTRY_KEYS}:`, so nothing here says what a figure entry is made of")
    keys = {str(k): str(v) for k, v in (st.get(ENTRY_KEYS) or {}).items()}
    want = st.get("each_item_declares") or {}
    field, entries = _entries(spec, st)
    gaps = item_gaps(spec, st).get("gaps") or []
    lacking = {who: list(bad) for who, bad in gaps}
    detail = (getattr(inv, "detail", None) or {}) if inv is not None else {}
    fn_key = keys.get("upstream", "fn")
    items_key = keys.get("items", "items")
    bound_key = keys.get("bound", "at_most")
    call_key = keys.get("call", "args")
    expr_key = keys.get("expression", "expr")
    # AND WHETHER EACH CALL IS R AT ALL, when R is at hand (`--rscript`). A call the plan
    # carries is pasted into a generated site verbatim; one that does not parse takes the whole
    # script down at the first figure, on the cluster.
    if rscript:
        calls = []
        for e in entries:
            fid = str(e.get("id") or e.get("name") or "?")
            expr = str(e.get(expr_key) or "").strip()
            call = str(e.get(call_key) or "").strip()
            if expr:
                calls.append((fid, expr))
            elif call and str(e.get(fn_key) or "").strip():
                calls.append((fid, f"{e[fn_key]}({call})"))
        for i, msg in sorted(_r_parse_failures([t for _f, t in calls], rscript).items()):
            lacking.setdefault(calls[i][0], []).append(f"does not parse as R: {msg}")
    cols = ["id", "drawn_by"] + [k for k in ("axis", "position") if k in want] + \
           [fn_key, items_key, bound_key, "kind", "legend"]
    L = [f"{name or 'this plugin'}: {len(entries)} entr{'y' if len(entries) == 1 else 'ies'} "
         f"in `{field}`; {len(lacking)} lack something the stage requires"]
    L.append("  " + "  ".join(f"{c:<14s}" if c != "id" else f"{c:<34s}" for c in cols))
    for e in entries:
        fid = str(e.get("id") or e.get("name") or "?")
        row = []
        for c in cols:
            v = e.get(c)
            if c == "legend":
                v = "yes" if str(v or "").strip() else "-"
            if v is None or v == "":
                v = "-"
            row.append(f"{str(v):<34.34s}" if c == "id" else f"{str(v):<14.14s}")
        L.append("  " + "  ".join(row))
        if str(e.get(fn_key) or "") and str(e.get("drawn_by") or "tool") == "tool":
            d = detail.get(str(e[fn_key])) or {}
            sig = d.get("signature") if isinstance(d, dict) else ""
            if sig:
                L.append(f"      {e[fn_key]}{_clip(sig, width - 8)}")
            elif inv is not None:
                L.append(f"      {e[fn_key]}: NOT IN THE INVENTORY - the upstream does not export "
                         f"it under this name, or the inventory's rules did not reach it")
        call = str(e.get(call_key) or "").strip()
        expr = str(e.get(expr_key) or "").strip()
        if call:
            L.append(f"      {e.get(fn_key)}({_clip(call, width - 12)})")
        elif expr:
            L.append(f"      expr: {_clip(expr, width - 12)}")
        for bad in lacking.get(fid, ()):
            L.append(f"      LACKS  {bad}")
    if inv is None:
        L.append("")
        L.append("  (pass --python <the plugin's own interpreter> to see each function's parameters)")
    return "\n".join(L)


def _r_prefix_of(rtext):
    """The `prefix = "..."` the script's protocol was configured with, or ""."""
    m = re.search(r'\.figures\s*\(.*?prefix\s*=\s*"([^"]*)"', rtext, re.S)
    return m.group(1) if m else ""


def _legacy_sites(doc, point_name, name, source):
    """{figure id: site record} from a plugin's hand-written draw sites, id = prefix + panel.

    THE LAST USE OF THE DRAW-SITE EXTRACTOR: it reads the sites so that the plan can be written
    from them once, after which there are no sites to read. A panel named by a literal is the
    id; one named `paste0("stem__", var)` is a per-item family with `var` as its items.
    """
    from .extract import draw_sites as DS
    out = {}
    blocks = list(DS.embedded_r(source))
    beside = DS.foreign(w for text, _n in _r_beside(doc, point_name, name)
                        for w in DS.r_wrappers(text))
    for rtext, base in blocks:
        prefix = _r_prefix_of(rtext)
        own = DS.r_wrappers(rtext)
        ws = own + [w for w in beside if w.name not in {x.name for x in own}]
        for site in DS._r_sites(rtext, base, "", ws):
            # A CALL TO THE PLAN'S INTERPRETER IS NOT A HAND-WRITTEN SITE. `.draw(id)` and
            # `.draw_all(axis)` are where sites used to stand (harness ADR-0016); the companion
            # defines both and they delegate to the device path, so the wrapper scan finds
            # them. Read as sites, their ids were prefixed a second time and a rerun of the
            # migration rewrote two already-migrated calls.
            if str(site.get("wrapper") or "") in PLAN_INTERPRETER:
                continue
            panel = site.get("panel") or ""
            m = re.match(r'^"([^"]+)"$', panel)
            items = ""
            if m:
                fid = prefix + m.group(1)
            else:
                # A PANEL NAMED BY paste0: the first literal is the family, the rest is what it
                # is drawn once per. A bare name is the items vector; anything else - a gsub, a
                # second key - is shown to the person, because a plan entry iterates ONE vector
                # and a site that iterates two is a decision about which one the family is.
                pm = re.match(r'^paste0\(\s*"([^"]+?)"\s*,\s*(.+)\)\s*$', panel, re.S)
                if not pm:
                    continue
                # THE ID IS EVERY LITERAL PIECE OF THE NAME, not the first: `paste0("bars_", ms)`
                # and `paste0("bars_", ms, "_per1k")` are two sites of one family, and read by
                # their head alone they were one id, so the second was silently dropped - the
                # 47th of a plugin's sites, found by the one call left after the other 46 were
                # replaced. Underscores that only separated a variable are collapsed.
                # TOP-LEVEL PIECES ONLY: a literal inside a call - the pattern of a `gsub` - is
                # not a piece of the name.
                from .extract import draw_sites as _DSn
                lits = [x.strip()[1:-1] for x in _DSn._split_args(pm.group(1).join(['"', '"'])
                                                                    + ", " + pm.group(2))
                        if re.fullmatch(r'\s*"[^"]*"\s*', x)]
                fid = prefix + re.sub(r"_+", "_", "".join(lits)).strip("_")
                # THE FILE STEM IS THE SITE'S OWN EXPRESSION, kept verbatim. `paste0("patterns_",
                # pat)`, `paste0("chord__", pw)`, `paste0("interaction_flow__", safe)` and a
                # two-key `paste0("chord_cell__", safe, "__", gsub(...))` all name files a sealed
                # run holds; the generated draw evaluates the expression in the frame it is
                # called from, so the names cannot change. A migration that normalised them
                # would not be the same plan.
                rest = pm.group(2).strip()
                # THE VARIABLE AMONG THE PIECES. `paste0("bars_", ms, "_per1k")` iterates `ms`
                # and carries a trailing literal; the pieces that are not string literals are
                # what varies, and when exactly one of them is a bare name it is the loop's
                # variable.
                from .extract import draw_sites as _DSx
                _var = [x.strip() for x in _DSx._split_args(pm.group(2))
                        if not re.fullmatch(r'\s*"[^"]*"\s*', x)]
                if len(_var) == 1:
                    rest = _var[0]
                # `items` IS THE LOOP'S VECTOR, WHEN THERE IS A LOOP. `for (p in shared)
                # npng(paste0("chord__", p), ...)` iterates `shared`: the plan names the vector
                # and `.draw_all` binds `.item`. A per-item site with no enclosing `for` - the
                # unit's top pathway, drawn once under an `if` - names no items: the method
                # calls `.draw(id, item = pw)` where the site stood, and `file` names the file.
                items = ""
                if re.match(r"^[.\w]+$", rest):
                    before = "\n".join(rtext.splitlines()[:max(0, int(site.get("line", 0)) - base)])
                    # THE VECTOR MAY CARRY PARENTHESES OF ITS OWN - `c("outgoing", "incoming")` -
                    # so the `for (` is closed by counting, not by the first `)`.
                    for fm in reversed(list(re.finditer(r"for\s*\(\s*" + re.escape(rest)
                                                        + r"\s+in\s+", before))):
                        start, depth, j = fm.end(), 1, fm.end()
                        while j < len(before) and depth:
                            depth += {"(": 1, ")": -1}.get(before[j], 0)
                            j += 1
                        if not depth:
                            items = before[start:j - 1].strip()
                            break
            out.setdefault(fid, dict(site, items=items, prefix=prefix, base=base,
                                     file=("" if m else " ".join(panel.split()))))
    return out


def _template_of(legend):
    """(template, placeholders) from a site's legend, or ("", []) when it cannot be one.

    A LEGEND IS A TEMPLATE WHOSE PLACEHOLDERS ARE R EXPRESSIONS, evaluated where the draw is
    called (ADR-0016). `paste0("The ", pw, " pathway")` becomes `"The {pw} pathway"`;
    `paste0("Does the ", fac, " response depend on ", as.character(rows$stratum_factor[1]), "?")`
    becomes the same sentence with both expressions in braces - readable, editable at the plan,
    and evaluated in the same frame the site evaluated it in. A part that itself carries a brace
    cannot be placed in one and leaves the legend a decision for a person.
    """
    leg = (legend or "").strip()
    m = re.match(r'^"((?:[^"\\]|\\.)*)"$', leg, re.S)
    if m:
        return m.group(1).replace('\\"', '"'), []
    pm = re.match(r"^paste0\((.*)\)$", leg, re.S)
    if not pm:
        return "", []
    from .extract import draw_sites as DS
    parts, holes, out = DS._split_args(pm.group(1)), [], []
    for part in parts:
        part = " ".join(part.split())
        lm = re.match(r'^"((?:[^"\\]|\\.)*)"$', part, re.S)
        if lm:
            out.append(lm.group(1).replace('\\"', '"'))
        elif part and "{" not in part and "}" not in part:
            out.append("{" + part + "}")
            holes.append(part)
        else:
            return "", []
    return "".join(out), holes


def _sizes_into(e, site):
    """The device size a site asks for - `w`, `h`, `res` - into the entry, as the site wrote it.

    AN INTEGER STAYS AN INTEGER AND AN EXPRESSION STAYS AN EXPRESSION. `w = .bw` and
    `w = max(1500, 340 * length(objs))` are widths the method computes; read as "an integer or
    nothing", three sites lost theirs and the generated site would have drawn them at the
    script's default. The generated draw evaluates a string where the site evaluated the
    expression, so the width is the width the run had.
    """
    named = (site or {}).get("named") or {}
    for wh in ("w", "h", "res"):
        v = str(named.get(wh) or "").strip()
        if not v:
            continue
        e[wh] = int(v) if re.fullmatch(r"\d+", v) else v


def _site_text(site):
    """A site's drawn expression as the plan should carry it: one line for a call, the line
    structure kept for a brace block, where a newline is a statement boundary."""
    raw = str((site or {}).get("raw") or "")
    if raw.startswith("{"):
        return raw
    return str((site or {}).get("draws") or "")


def _r_parse_failures(texts, rscript):
    """{index: message} for the call texts R cannot parse. One interpreter start for all of them.

    THE MAKER CANNOT PARSE R AND DOES NOT PRETEND TO: it asks R, when told where R is. Without
    this the first parser a transcribed expression met was the run's, on the cluster, three
    steps after the worksheet that wrote it.
    """
    import shutil as _sh
    import subprocess as _sp
    import tempfile as _tf
    if not texts or not rscript:
        return {}
    d = Path(_tf.mkdtemp(prefix="sch-parse-"))
    try:
        files = []
        for i, t in enumerate(texts):
            f = d / f"{i}.R"
            f.write_text(str(t) + "\n", encoding="utf-8")
            files.append(str(f))
        prog = ('for (f in commandArgs(trailingOnly = TRUE)) {'
                ' m <- tryCatch({ parse(text = readLines(f, warn = FALSE)); "" },'
                ' error = function(e) conditionMessage(e));'
                ' cat(basename(f), "\\t", gsub("[[:space:]]+", " ", m), "\\n", sep = "") }')
        try:
            p = _sp.run([rscript, "-e", prog] + files, capture_output=True, text=True,
                        timeout=300)
        except (OSError, _sp.SubprocessError) as e:
            return {i: f"R could not be run: {e}" for i in range(len(texts))}
        out = {}
        for line in (p.stdout or "").splitlines():
            f, _t, msg = line.partition("\t")
            if _t and msg.strip() and f.endswith(".R"):
                out[int(f[:-2])] = msg.strip()
        return out
    finally:
        _sh.rmtree(d, ignore_errors=True)


def _by_of(site, vocab=("tool", "plugin")):
    """The provenance a draw site states itself, or "".

    THE ARGUMENT THAT NAMES A PROVENANCE IS THE ONE WHOSE VALUE IS A PROVENANCE: no parameter
    name is assumed, because the wrapper is the plugin's and the vocabulary is the stage's
    (`each_item_declares.drawn_by`). A literal outside the vocabulary names nothing.
    """
    for _k, v in ((site or {}).get("named") or {}).items():
        m = re.fullmatch(r'"([^"]*)"', str(v).strip())
        if m and m.group(1) in vocab:
            return m.group(1)
    return ""


def _call_of(draws, fn):
    """(args, expr): the arguments inside `fn(...)` when the expression IS that call, else the
    whole expression as `expr`. Balanced parentheses, read with the extractor's own mask."""
    from .extract import draw_sites as DS
    text = draws or ""
    if fn:
        m = re.match(r"^\s*(?:[.\w]+::)?" + re.escape(fn) + r"\s*\(", text)
        if m:
            op = m.end() - 1
            cl = DS._closing(DS._mask(text), op)
            if cl == len(text) - 1:
                return text[op + 1:cl].strip(), ""
    return "", text.strip()


def migrate_worksheet(spec, doc, point_name, name="", source="", width=96):
    """A paste-ready plan for a plugin still on the prose-and-prefix-map form.

    BUILT FROM WHAT THE PLUGIN ALREADY SAYS, in four places: the families the legacy rules name
    (`places_every`, ids parsed out of prose - the same parser the old placement stage used),
    their ceilings, the two prefix maps, the existing entries - and the hand-written draw sites,
    read one last time, for the call, the items, the device and the legend. Nothing is decided:
    every field that could not be read is the placeholder, and a legend that was built at the
    site out of runtime values is printed as a TODO with the expression beside it, because a
    template is a decision.

    PRINTED, NEVER WRITTEN. The person pastes it in place of the legacy fields, then `status`,
    `validate` and the plan's own baseline test say whether it is the same plan.
    """
    st = plan_stage(doc, point_name)
    if st is None:
        raise ConvertError(f"point {point_name!r} declares no plan stage")
    ph, _up, _stages = plan(doc, point_name)
    keys = {str(k): str(v) for k, v in (st.get(ENTRY_KEYS) or {}).items()}
    fn_key, items_key = keys.get("upstream", "fn"), keys.get("items", "items")
    bound_key, call_key = keys.get("bound", "at_most"), keys.get("call", "args")
    expr_key, skips_key = keys.get("expression", "expr"), keys.get("skips", "report.skips")
    rules = st.get(PLACES_KEY) or []
    field, existing = _entries(spec, st)
    axis_field = str(st.get("axis_field") or "")
    axis_map = {str(k): str(v) for k, v in (_dotted(spec, axis_field) or {}).items()} \
        if axis_field else {}
    pos_map = {str(k): str(v) for k, v in (_dotted(spec, field.rsplit(".", 1)[0]
                                                    + ".figure_position") or {}).items()}

    def longest(m, fid, default):
        for k in sorted(m, key=len, reverse=True):
            if fid.startswith(k):
                return m[k]
        return default

    sites = _legacy_sites(doc, point_name, name, source) if source else {}
    vocab = tuple(str(x) for x in ((st.get("each_item_declares") or {}).get("drawn_by") or ())) \
        or ("tool", "plugin")
    entries, todo = [], 0
    # 1. the families the legacy rules name, one entry per member of a brace family
    for stem, rfield, per_item, bound, cap in _families(spec, rules):
        node = _dotted(spec, rfield) or {}
        if not isinstance(node, dict):
            continue                       # entries by id are carried through below, as they are
        # which upstream function named this stem, and what that record says
        fn, rec = "", {}
        for k, r in (node.items() if isinstance(node, dict) else []):
            if stem in str((r or {}).get("use") or ""):
                fn, rec = str(k), (r or {})
                break
        members = [stem]
        for r_ in re.findall(r"figures/([A-Za-z0-9_{},<>-]+?)\.png", str(rec.get("use") or "")):
            if r_.split("{")[0].rstrip("_") == stem and "{" in r_:
                head_, rest = r_.split("{", 1)
                opts = rest.split("}", 1)[0]
                members = [head_ + o.strip() for o in opts.split(",") if o.strip()]
                break
        # A BRACE FAMILY DRAWN BY ONE LOOP IS ONE ENTRY. `native_patterns_{outgoing,incoming}`
        # is two files and one site - `for (pat in c(...)) ndev(paste0("patterns_", pat), ...)`
        # - so the plan says one family, its items and a ceiling of two, and the generated loop
        # names the files exactly as the site did.
        n_members = len(members)
        if len(members) > 1 and stem in sites and sites[stem].get("items"):
            members = [stem]
        for fid in members:
            site = sites.get(fid) or {}
            # THE SITE'S OWN `by =` IS THE PROVENANCE, when it says one: it is what the run
            # wrote into captions.tsv. The prose record's word is second; "tool" is last.
            e = {"id": fid, "drawn_by": _by_of(site, vocab) or str(rec.get("drawn_by") or "tool")}
            if fn:
                e[fn_key] = fn
            e["axis"] = longest(axis_map, fid, "unit")
            e["position"] = longest(pos_map, fid, "contrast")
            if site.get("items"):
                e[items_key] = site["items"]
            elif per_item and not site.get("file"):
                e[items_key] = f"{ph} - the R name of the vector this is drawn once per item of"
                todo += 1
            if per_item or site.get("items") or site.get("file"):
                e[bound_key] = int(cap) if cap else f"{ph} - files per {e['axis']}"
                if not cap:
                    todo += 1
            elif len(members) > 1 or cap:
                e[bound_key] = 1 if len(members) > 1 else int(cap)
            # THE PROFILE FLAG IS THE UNIT'S. In the older form it sat on the FUNCTION, and the
            # reader applied it to files in a unit's own directory; copied onto every family
            # the function names, six contrast families were marked profile and kept off the
            # arm pages - thirteen plates fewer on one reproduction.
            if rec.get("profile") and e["axis"] == "unit":
                e["profile"] = True
            if site:
                if len(members) == 1 and site.get("items") and stem == fid and not per_item:
                    e[items_key] = site["items"]
                    e[bound_key] = int(cap) if cap else n_members
                if site.get("file"):
                    e["file"] = site["file"]
                args, expr = _call_of(_site_text(site), fn)
                if args:
                    e[call_key] = args
                elif expr:
                    e[expr_key] = expr
                if site.get("wrapper") and site["wrapper"] != "npng":
                    e["device"] = site["wrapper"]
                _sizes_into(e, site)
                leg = str(site.get("legend") or "").strip()
                tpl, _holes = _template_of(leg)
                if tpl:
                    e["legend"] = tpl
                elif leg:
                    e["legend"] = f"{ph} - a template for: {leg[:200]}"
                    todo += 1
                else:
                    e["legend"] = f"{ph} - what this panel shows, as a template"
                    todo += 1
            else:
                e["legend"] = f"{ph} - what this panel shows, as a template"
                e[call_key] = f"{ph} - the arguments this plugin passes {fn or 'the function'}"
                todo += 2
            entries.append(e)
    # 1b. A DRAW SITE NO LEGACY FIELD NAMES IS PRINTED, NEVER DROPPED. A site is a figure the
    # run draws; after the migration the sites are generated from the plan, so an entry that is
    # not here is a panel that stops existing. Two of a plugin's forty-six were named by no
    # prose - the second file of an "X.png and Y.png" sentence, and the log-scale companion
    # drawn under an `if` beside its sibling - and the first worksheet lost both, silently.
    # Read from the site: the call, the file, the device, the legend, the site's own `by =`.
    # Decided by nobody: the ceiling, and the provenance when the site does not say it.
    seen = {e["id"] for e in entries}
    unnamed = 0
    for fid, site in sites.items():
        if fid in seen:
            continue
        unnamed += 1
        head = re.match(r"^\s*(?:[.\w]+::)?([.\w]+)\s*\(", site.get("draws") or "")
        fn = head.group(1) if head else ""
        e = {"id": fid, "drawn_by": _by_of(site, vocab)
             or f"{ph} - {' or '.join(vocab)}: no legacy field names this site"}
        if not _by_of(site, vocab):
            todo += 1
        if fn:
            args, _expr = _call_of(_site_text(site), fn)
            if not args and _expr:
                fn = ""
        if fn:
            e[fn_key] = fn
        e["axis"] = longest(axis_map, fid, "unit")
        e["position"] = longest(pos_map, fid, "contrast")
        if site.get("items"):
            e[items_key] = site["items"]
        if site.get("items") or site.get("file"):
            e[bound_key] = f"{ph} - files per {e['axis']}"
            todo += 1
        if site.get("file"):
            e["file"] = site["file"]
        args, expr = _call_of(_site_text(site), fn)
        if args:
            e[call_key] = args
        elif expr:
            e[expr_key] = expr
        if site.get("wrapper") and site["wrapper"] != "npng":
            e["device"] = site["wrapper"]
        _sizes_into(e, site)
        leg = str(site.get("legend") or "").strip()
        tpl, _holes = _template_of(leg)
        if tpl:
            e["legend"] = tpl
        elif leg:
            e["legend"] = f"{ph} - a template for: {leg[:200]}"
            todo += 1
        else:
            e["legend"] = f"{ph} - what this panel shows, as a template"
            todo += 1
        entries.append(e)
        seen.add(fid)
    # 2. the existing entries, carried through with their axis and position made explicit
    for e in existing:
        fid = str(e.get("id") or "")
        if not fid or fid in seen:
            continue
        e2 = dict(e)
        e2.setdefault("drawn_by", "plugin")
        e2.setdefault("axis", longest(axis_map, fid, "unit"))
        e2.setdefault("position", longest(pos_map, fid, "contrast"))
        if not str(e2.get("legend") or "").strip():
            e2["legend"] = f"{ph} - what this panel shows, as a template; the caption passed at emit still wins"
            todo += 1
        entries.append(e2)
    # 3. the skips
    skips = {}
    for rfield in {r.get("field") for r in rules if r.get("field")}:
        node = _dotted(spec, str(rfield)) or {}
        for k, r in (node.items() if isinstance(node, dict) else []):
            if isinstance(r, dict) and r.get("skip"):
                skips[str(k)] = {kk: vv for kk, vv in r.items()}
    L = [f"    # THE FIGURE PLAN for {name or 'this plugin'}: {len(entries)} entries from "
         f"{len(rules)} legacy field(s), {len(sites)} draw site(s) read, {unnamed} named by no "
         f"legacy field, {todo} field(s) left for a person.",
         f"    # Paste in place of {', '.join(sorted({str(r.get('field')) for r in rules if r.get('field')}))}, "
         f"`{axis_field or 'the axis map'}` and `figure_position`. A `{ph}` does not validate.",
         f'    "{field.split(".")[-1]}": [']
    for e in entries:
        L.append("        {")
        for k, v in e.items():
            L.append(f"            {k!r}: {v!r},")
        L.append("        },")
    L.append("    ],")
    L.append(f'    "{skips_key.split(".")[-1]}": {{')
    for k, v in sorted(skips.items()):
        L.append(f"        {k!r}: {v!r},")
    L.append("    },")
    return "\n".join(L)


def advance_command(row, doc, point_name, root, name, python="", run=""):
    """The literal command that moves this stage on, or "" when only a person can.

    `next: inventory` TOLD AN AGENT WHERE IT WAS AND NOT WHAT TO DO. Knowing that
    `sch dev convert account --python <the plugin's own interpreter>` is the thing requires already
    knowing the tool, which is exactly what somebody arriving at a half-built plugin does not have.
    A status that names the stage and withholds the command is a status you need a guide beside.
    """
    stage = row["stage"]
    declared = stage_command(doc, point_name, stage)
    if declared:
        return " ".join(fill(declared, {"python": python or "python3", "run": run or "<RUNDIR>",
                                        "root": root, "name": name}))
    if stage in ACTIONS:
        # `inventory` IS SEEN WITH ONE ACTION AND DECIDED WITH ANOTHER. `inventory` lists what the
        # tool exports; `account` turns that into the worksheet with the evidence attached, which
        # is the one somebody actually works from.
        action = "account" if stage == "inventory" else stage
        cmd = f"sch dev convert {action} --root {root} --point {point_name} --name {name}"
        if stage in ("inventory", "defaults"):
            cmd += f" --python {python or '<the interpreter this plugin runs in>'}"
        return cmd
    return ""


def plan_of_work(rows, doc, point_name, root, name, python="", run=""):
    """[(stage, command|'', what a person must decide)] for every stage not yet done, in order."""
    out = []
    for r in rows:
        if r["done"]:
            continue
        out.append((r, advance_command(r, doc, point_name, root, name, python, run),
                    r["kind"] == "judgement"))
    return out
