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
        missing = [k for k in STAGE_REQUIRED if not st.get(k)]
        if missing:
            raise ConvertError(f"point {point_name!r}: stage {i} declares no {missing}")
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
    return DS.draw_sites(name, source, where, emits)


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


def status(spec, doc, point_name, name="", source=None):
    """[{stage, kind, done, missing, why}] in declared order. The whole resume mechanism.

    `name` IS OPTIONAL AND ITS ABSENCE IS AN ANSWER. A stage that rules on draw sites needs the
    plugin's source, and a caller that names no plugin has not supplied one - so such a stage
    reports "not looked at" rather than done. A status that quietly skipped the half it could not
    measure would be the same defect this module has fixed in four other places.
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
        out.append({"stage": st["name"],
                    "partial": partial,
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
                    "done": not missing and not partial and not owes_draws,
                    "missing": missing,
                    "why": st.get("why", "")})
    return out


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
    """
    L = []
    for phase, headline in (("build", "BUILD - reads source only, so it cannot be fitted to a "
                                      "cohort"),
                            ("test", "TEST - needs something to run on: the fixture, or a "
                                     "dataset you already have")):
        group = [r for r in rows if r.get("phase", "build") == phase]
        if not group:
            continue
        done = sum(1 for r in group if r["done"])
        L.append(f"{name}  ({point_name})  {phase}: {done} of {len(group)} complete    {headline}")
        for r in group:
            mark = ("done" if r["done"]
                    else "PART" if r.get("partial") or r.get("draws", {}).get("silent")
                    else "ASK " if r["kind"] == "judgement" else "todo")
            L.append(f"  {mark} {r['stage']:12s} {', '.join(r['fills'])}")
            d = r.get("draws") or {}
            L += _draw_lines(r)
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
                if r["missing"]:
                    L.append(f"       unfilled: {', '.join(r['missing'])}")
                if r["why"]:
                    L.append(f"       {r['why']}")
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


def worksheet(tool, inv, declared, source="", placeholder="TODO", width=96):
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
         f'{sum(1 for n in new if n in calls)} of those are called by this plugin.',
         '    "native_plots": {']
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
                L.append(f'        {n!r}: {{"use": "{placeholder} — confirm where this lands"}},')
            else:
                L.append("        #   not called anywhere in this plugin.")
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


#: The convert actions that advance a stage of the same name. `judgement` has none and never will.
ADVANCES = ("contract", "defaults", "references", "inventory", "legends", "measure")


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
    if stage in ADVANCES:
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
