"""The figure plan under a layout: budgets per axis, what to keep first, and the trim (ADR-0024).

945 FIGURES A RUN WAS THE FLOOR OF A PLAN WITH NO BUDGET: 58 entries, each drawn for every unit,
contrast and the cohort. The layout is one declaration in the tool's DEVPOINTS - the axes a run
has, a budget per axis in FILES per occurrence of the axis, which kinds a reader needs first on
each axis, whose drawing comes first (the upstream's own before the plugin's) and which position
goes first when something must go. `check` holds a plan to it; `trim` decides what stays; `apply`
writes the decision into the plugin's own file, by span, so that a plugin is never hand-edited to
be made smaller.

The plan's field names are the tool's (`entry_keys` on the plan stage); nothing here knows that
a ceiling is spelled `at_most`.
"""
import ast
import re
from pathlib import Path

#: Legacy axis names and what they mean under a layout: `unit` is a sample and a group at once;
#: `cohort` entries whose kind the interaction axis keeps are interaction entries.
UNIT_AXES = ("sample", "group")
DEFAULT_LAYOUT = {"prefer": ["tool", "plugin"],
                  "drop_first": ["appendix", "conclusion", "contrast", "overview"]}


def _k(keys, what, default):
    return str((keys or {}).get(what) or default)


def _entries(spec, keys=None):
    """The plan's plates. An entry the format marks as a side effect - a file the tool writes
    while the method calls it, `generated: False` in one format - is an accounting entry and
    not a plate: neither counted against a budget nor dropped by the trim."""
    rep = (spec or {}).get("report") or {}
    side = _k(keys, "side_effect", "")
    return [e for e in (rep.get("figures") or []) if isinstance(e, dict) and e.get("id")
            and not (side and e.get(side) is False)]


def host_files(layout):
    """{axis: files} the host's own kept panels take on each axis, per occurrence.

    The layout names every kind the host draws with its axis (`host`), and which of them a
    reader is handed (`host_keep`); a kind not kept is not drawn, and the plugin carries the
    decision as the list `host_list` names. `files` is per occurrence of the axis (a kind that
    draws two matrices per contrast says 2), one where unsaid.
    """
    host = (layout or {}).get("host") or {}
    keep = [k for k in ((layout or {}).get("host_keep") or []) if k in host]
    out = {}
    for k in keep:
        ax = str((host[k] or {}).get("axis") or "cohort")
        out[ax] = out.get(ax, 0) + max(1, int((host[k] or {}).get("files") or 1))
    return out


def host_kept(layout):
    """The host kinds a reader is handed, in the layout's order - what the plugin will carry."""
    host = (layout or {}).get("host") or {}
    return [k for k in ((layout or {}).get("host_keep") or []) if k in host]


def _files(e, bound):
    try:
        return max(1, int(e.get(bound) or 1))
    except (TypeError, ValueError):
        return 1


def axes_of(e, layout, keys):
    """The layout axes an entry counts against, from its declared axis and kind."""
    ax = str(e.get(_k(keys, "axis", "axis")) or "unit")
    axes = (layout or {}).get("axes") or {}
    if ax == "unit":
        return [a for a in UNIT_AXES if a in axes] or ["unit"]
    if ax == "cohort" and "interaction" in axes:
        kinds = (axes["interaction"] or {}).get("keep") or []
        if str(e.get("kind") or "") in kinds:
            return ["interaction"]
    return [ax]


def check(spec, layout, keys=None):
    """{ok, counts, budgets, over: [axis], entries: {axis: [(id, files)]}} for a plan."""
    keys = keys or {}
    bound = _k(keys, "bound", "at_most")
    axes = (layout or {}).get("axes") or {}
    host = host_files(layout)
    counts, per = {a: host.get(a, 0) for a in axes}, {a: [] for a in axes}
    for e in _entries(spec, keys):
        for a in axes_of(e, layout, keys):
            if a in counts:
                counts[a] += _files(e, bound)
                per[a].append((str(e["id"]), _files(e, bound)))
    budgets = {a: int((axes[a] or {}).get("budget") or 0) for a in axes}
    over = [a for a in axes if counts[a] > budgets[a]]
    # THE HOST'S LIST, CARRIED BY THE PLUGIN: what the layout keeps is what the plugin must
    # declare, or the host draws every kind it owns and the count above is not the run's.
    hlist = _k(keys, "host_list", "") or str((layout or {}).get("host_list") or "")
    wanted = host_kept(layout) if (layout or {}).get("host") else None
    declared = None
    if hlist and wanted is not None:
        node = spec or {}
        for part in hlist.split("."):
            node = node.get(part) if isinstance(node, dict) else None
        declared = list(node) if isinstance(node, (list, tuple)) else None
    list_ok = wanted is None or declared == wanted
    return {"ok": not over and list_ok, "counts": counts, "budgets": budgets, "over": over,
            "entries": per, "host": {a: n for a, n in host.items() if a in axes},
            "host_list": ({"declared": declared, "wanted": wanted, "at": hlist}
                          if wanted is not None else {})}


def _rank(e, axis, layout, keys):
    keep = list(((layout.get("axes") or {}).get(axis) or {}).get("keep") or [])
    prefer = list(layout.get("prefer") or DEFAULT_LAYOUT["prefer"])
    drop = list(layout.get("drop_first") or DEFAULT_LAYOUT["drop_first"])
    kind, by = str(e.get("kind") or ""), str(e.get("drawn_by") or "tool")
    pos = str(e.get(_k(keys, "position", "position")) or "")
    return (keep.index(kind) if kind in keep else len(keep),
            prefer.index(by) if by in prefer else len(prefer),
            (len(drop) - 1 - drop.index(pos)) if pos in drop else 0)


def trim(spec, layout, keys=None):
    """{kept: [entry], dropped: [{id, axis, axes, why}]} - the plan held to the layout.

    WHAT STAYS, IN PASSES: on each axis, the first pass takes one file from one entry of each
    kind the layout keeps, in its order - so five per group are five different views, not five
    circles - the upstream's own drawing before the plugin's within a kind, the position the
    layout drops last before the rest, then the plan's own order; the second pass takes a second
    entry of each kind, and so on while the budget lasts. Only then does a per-item family grow
    past one file, up to its own ceiling, while files remain. An entry on both unit axes keeps
    `unit` when both keep it, one axis when one does, and goes when neither does.
    """
    keys = keys or {}
    bound, axis_key = _k(keys, "bound", "at_most"), _k(keys, "axis", "axis")
    axes = (layout or {}).get("axes") or {}
    decided = {}        # id -> {axis: files kept}
    dropped = []
    entries = _entries(spec, keys)
    host = host_files(layout)
    for a in axes:
        # THE HOST'S OWN PANELS TAKE THEIR FILES FIRST: the budget is the reader's, whoever drew
        # the file, and the host's kinds are what the layout kept on purpose.
        budget = int((axes[a] or {}).get("budget") or 0) - host.get(a, 0)
        cands = [(i, e) for i, e in enumerate(entries) if a in axes_of(e, layout, keys)]
        cands.sort(key=lambda ie: (_rank(ie[1], a, layout, keys), ie[0]))
        # THE PASS OF EACH CANDIDATE: its rank among the entries of its own kind.
        seen = {}
        ordered = []
        for i, e in cands:
            kind = str(e.get("kind") or "")
            ordered.append((seen.get(kind, 0), _rank(e, a, layout, keys), i, e))
            seen[kind] = seen.get(kind, 0) + 1
        ordered.sort(key=lambda t: (t[0], t[1], t[2]))
        left = budget
        took = {}
        for _p, _r, _i, e in ordered:
            if left >= 1:
                took[str(e["id"])] = 1
                left -= 1
            else:
                dropped.append({"id": str(e["id"]), "axis": a,
                                "why": f"over_budget: {a} keeps {budget} file(s), one of each kind "
                                       f"the layout names first ({', '.join(axes[a].get('keep') or []) or 'none named'})"})
        # THE FAMILIES GROW LAST, in the same order, up to their own ceiling.
        for _p, _r, _i, e in ordered:
            fid = str(e["id"])
            if fid not in took or left <= 0:
                continue
            want = _files(e, bound)
            extra = min(want - took[fid], left)
            if extra > 0:
                took[fid] += extra
                left -= extra
        for fid, n in took.items():
            decided.setdefault(fid, {})[a] = n
    kept, gone = [], []
    side = _k(keys, "side_effect", "")
    for e in [x for x in (((spec or {}).get("report") or {}).get("figures") or [])
              if isinstance(x, dict) and x.get("id")]:
        if side and e.get(side) is False:
            kept.append(dict(e))          # an accounting entry: kept as it is, on no axis
            continue
        d = decided.get(str(e["id"]))
        if not d:
            gone.append(str(e["id"]))
            continue
        e2 = dict(e)
        on = sorted(d)
        if set(on) == set(UNIT_AXES):
            e2[axis_key] = "unit"
        elif len(on) == 1:
            e2[axis_key] = on[0]
        n = min(d.values())
        if n != _files(e, bound):
            e2[bound] = n
        elif e.get(bound) is None:
            e2.pop(bound, None)
        kept.append(e2)
    # ONE RECORD PER DROPPED ENTRY, the first axis that dropped it named, every axis listed.
    by_id = {}
    for x in dropped:
        if x["id"] in gone:
            rec = by_id.setdefault(x["id"], dict(x, axes=[]))
            rec["axes"].append(x["axis"])
    return {"kept": kept, "dropped": list(by_id.values())}


def _plugin_nodes(src):
    tree = ast.parse(src)
    plug = next((n for n in tree.body if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == "PLUGIN" for t in n.targets)), None)
    if plug is None or not isinstance(plug.value, ast.Dict):
        raise ValueError("no `PLUGIN = {...}` dict in the file")

    def get(dnode, key):
        for k, v in zip(dnode.keys, dnode.values):
            if isinstance(k, ast.Constant) and k.value == key:
                return v
        return None
    rep = get(plug.value, "report")
    figs = get(rep, "figures") if isinstance(rep, ast.Dict) else None
    skips = get(rep, "skips") if isinstance(rep, ast.Dict) else None
    if not isinstance(figs, ast.List):
        raise ValueError("no `report.figures` list in the PLUGIN dict")
    return plug.value, figs, skips


def read_spec(path):
    """The PLUGIN dict of a one-file plugin, read as a literal - never imported."""
    src = Path(path).read_text(encoding="utf-8")
    plug, _figs, _skips = _plugin_nodes(src)
    return ast.literal_eval(plug)


def apply(path, layout, keys=None, as_version=None):
    """Trim the plan in the plugin's own file to the layout. Returns what changed.

    `as_version` is the version the author states for the trimmed plugin; without it the minor
    is raised by one, which is the maker's own bump and collides with nothing only while the
    file's version is the newest in the repository's history.

    BY SPAN, NOT BY REGENERATION: every entry is a dict literal with its own lines, so a dropped
    entry's lines go, a kept entry's axis and ceiling are rewritten on their own lines, and
    everything else in the file - the comment trail three authors left, the code, the other
    declarations - stays byte for byte. A dropped entry the upstream draws is accounted for in
    the skips with the reason and the budget; the plugin's own dropped panel is no upstream
    export and takes no skip.
    """
    keys = keys or {}
    bound, axis_key = _k(keys, "bound", "at_most"), _k(keys, "axis", "axis")
    fn_key = _k(keys, "upstream", "fn")
    p = Path(path)
    src = p.read_text(encoding="utf-8")
    plug, figs, skips = _plugin_nodes(src)
    spec = ast.literal_eval(plug)
    plan = trim(spec, layout, keys)
    kept = {e["id"]: e for e in plan["kept"]}
    lines = src.splitlines(keepends=True)
    edits = []          # (start_line, end_line, replacement_lines)  1-based inclusive
    dropped_ids, dropped_fns = [], []
    for node in figs.elts:
        if not isinstance(node, ast.Dict):
            continue
        e = ast.literal_eval(node)
        fid = str(e.get("id") or "")
        a, b = node.lineno, node.end_lineno
        if fid not in kept:
            dropped_ids.append(fid)
            fn = str(e.get(fn_key) or "")
            if fn and str(e.get("drawn_by") or "tool") == "tool":
                dropped_fns.append((fn, next((d for d in plan["dropped"] if d["id"] == fid), {})))
            edits.append((a, b, []))
            continue
        new = kept[fid]
        block = lines[a - 1:b]
        # THE AXIS, ON ITS OWN LINE
        if new.get(axis_key) != e.get(axis_key):
            pat = re.compile(r"""(['"]%s['"]\s*:\s*)(['"][a-z]+['"])""" % re.escape(axis_key))
            block = [pat.sub(lambda m: m.group(1) + repr(str(new[axis_key])), l, count=1)
                     if pat.search(l) else l for l in block]
        # THE CEILING, ON ITS OWN LINE, OR INSERTED AFTER THE ID
        if new.get(bound) is not None and new.get(bound) != e.get(bound):
            pat = re.compile(r"""(['"]%s['"]\s*:\s*)(\d+)""" % re.escape(bound))
            if any(pat.search(l) for l in block):
                block = [pat.sub(lambda m: m.group(1) + str(int(new[bound])), l, count=1)
                         if pat.search(l) else l for l in block]
            else:
                idp = re.compile(r"""^(\s*)['"]id['"]\s*:""")
                out = []
                for l in block:
                    out.append(l)
                    m = idp.match(l)
                    if m and not any(pat.search(x) for x in out):
                        out.append(f"{m.group(1)}'{bound}': {int(new[bound])},   # held to the layout\n")
                block = out
        if block != lines[a - 1:b]:
            edits.append((a, b, block))
        # THE PROFILE MARK: the sample axis is the per-unit profile under a layout, so a kept
        # entry on it carries `profile: True` and a kept entry off it does not.
        side_key = _k(keys, "side_effect", "")
        want_profile = (str(new.get(axis_key) or "") in ("sample", "unit")
                        and not (side_key and e.get(side_key) is False))
        has_profile = bool(e.get("profile"))
        if want_profile and not has_profile:
            idp = re.compile(r"""(['"]id['"]\s*:\s*['"][^'"]+['"]\s*,)""")
            block = [idp.sub(lambda m: m.group(1) + " 'profile': True,", l, count=1)
                     if idp.search(l) else l for l in block]
        elif has_profile and not want_profile:
            pp = re.compile(r"""\s*['"]profile['"]\s*:\s*True\s*,?""")
            block = [pp.sub("", l, count=1) if pp.search(l) else l for l in block]
            block = [l for l in block if l.strip()]
        if block != lines[a - 1:b]:
            edits = [x for x in edits if x[0] != a] + [(a, b, block)]
    # THE SKIPS: the dropped upstream functions no kept entry still calls, each once
    still = {str(e.get(fn_key) or "") for e in plan["kept"]}
    skip_lines, seen_fn = [], set()
    for fn, d in dropped_fns:
        if fn in still or fn in seen_fn or fn in ((spec.get("report") or {}).get("skips") or {}):
            continue
        seen_fn.add(fn)
        skip_lines.append((fn, d))
    if skip_lines:
        if skips is None or not isinstance(skips, ast.Dict):
            raise ValueError("the plan drops upstream entries and the file has no `report.skips` "
                             "dict to account for them in; declare `skips: {}` first")
        a = skips.lineno
        indent = re.match(r"^(\s*)", lines[a]).group(1) if a < len(lines) else "            "
        if skips.end_lineno == skips.lineno:
            indent = "            "
        ins = [f"{indent}{fn!r}: {{'skip': 'over_budget', 'axis': {d.get('axis')!r}, "
               f"'budget': {int((((layout.get('axes') or {}).get(d.get('axis')) or {}).get('budget') or 0))}}},   # held to the layout\n"
               for fn, d in skip_lines]
        edits.append((a, a, [lines[a - 1]] + ins))
    # THE HOST'S PANELS THE PAGES CARRY, as the list the format names, on its own line inside
    # the report block - written once, rewritten in place when it is already there.
    hlist = _k(keys, "host_list", "") or str((layout or {}).get("host_list") or "")
    if hlist and (layout or {}).get("host"):
        field = hlist.split(".")[-1]
        rep_node = next((v for k, v in zip(plug.keys, plug.values)
                         if isinstance(k, ast.Constant) and k.value == "report"), None)
        kept_kinds = host_kept(layout)
        line = (f"            {field!r}: [{', '.join(repr(k) for k in kept_kinds)}],"
                f"   # held to the layout: the host's own panels these pages carry\n")
        hpat = re.compile(r"""^\s*['"]%s['"]\s*:""" % re.escape(field))
        have = [i for i in range(rep_node.lineno, rep_node.end_lineno + 1)
                if hpat.match(lines[i - 1])] if rep_node is not None else []
        if have:
            edits.append((have[0], have[0], [line]))
        elif rep_node is not None:
            a = rep_node.lineno
            edits.append((a, a, [lines[a - 1], line]))
    # APPLY FROM THE BOTTOM, so line numbers stay true
    for a, b, repl in sorted(edits, key=lambda t: -t[0]):
        lines[a - 1:b] = repl
    out = "".join(lines)
    # THE DRAW SITES: a protocol line that still calls a dropped entry by id goes with it. The
    # companion would skip it and say so, and every suite that holds the sites to the plan
    # would refuse; the plan is the one source.
    site = re.compile(r"""^\s*\.draw\((['"])(%s)\1\)\s*$""" % "|".join(re.escape(i) for i in dropped_ids)) \
        if dropped_ids else None
    if site:
        out = "".join(l for l in out.splitlines(keepends=True) if not site.match(l))
    # THE PLUGIN'S OWN PROFILE LIST, where the format has one: the R guard's list of plot stems
    # is rewritten to the kept profile, so the two halves of the profile declaration agree.
    plist = _k(keys, "profile_list", "")
    if plist:
        _side = _k(keys, "side_effect", "")
        prof = [str(e["id"]) for e in plan["kept"]
                if str(e.get(axis_key) or "") in ("sample", "unit")
                and str(e.get("drawn_by") or "tool") == "tool"
                and not (_side and e.get(_side) is False)]
        stems = [i[len("native_"):] if i.startswith("native_") else i for i in prof]
        pat = re.compile(r"(%s\s*=\s*\()([^)]*)(\))" % re.escape(plist), flags=re.S)
        if pat.search(out):
            out = pat.sub(lambda m: m.group(1) + ", ".join(repr(x) for x in stems)
                          + ("," if len(stems) == 1 else "") + m.group(3), out, count=1)
    # THE VERSION, THE REUSE KEY: an artefact that draws differently is a new version, and the
    # freshness stage asks for it in the same commit.
    vkey = _k(keys, "version", "")
    version = None
    if vkey:
        vpat = re.compile(r"""(["']%s["']\s*:\s*["'])(\d+)\.(\d+)\.(\d+)(["'])""" % re.escape(vkey))
        m = vpat.search(out)
        if m:
            old_v = f"{m.group(2)}.{m.group(3)}.{m.group(4)}"
            new_v = str(as_version) if as_version else f"{m.group(2)}.{int(m.group(3)) + 1}.0"
            out = vpat.sub(lambda mm: mm.group(1) + new_v + mm.group(5), out, count=1)
            version = (old_v, new_v)
    ast.parse(out)
    _pl, _f, _s = _plugin_nodes(out)
    after = ast.literal_eval(_pl)
    rep = check(after, layout, keys)
    if not rep["ok"]:
        raise ValueError(f"the trimmed plan still reads over budget on {rep['over']}; nothing written")
    p.write_text(out, encoding="utf-8")
    return {"dropped_ids": dropped_ids, "skips_added": [fn for fn, _ in skip_lines],
            "kept": len(plan["kept"]), "check": rep, "version": version}


def format_report(name, rep, plan=None, root="", point="", apply_hint=True):
    L = [f"{name}: the figure plan against the layout"]
    for a in rep["counts"]:
        mark = "OVER" if a in rep["over"] else "ok  "
        h = (rep.get("host") or {}).get(a, 0)
        L.append(f"  {mark} {a:12s} {rep['counts'][a]:4d} file(s) per occurrence against a "
                 f"budget of {rep['budgets'][a]}"
                 + (f"  ({h} of them the host's own panels)" if h else ""))
    hl = rep.get("host_list") or {}
    if hl:
        if hl.get("declared") == hl.get("wanted"):
            L.append(f"  ok   the host's own panels these pages carry, as `{hl['at']}` declares: "
                     f"{', '.join(hl['wanted']) or 'none'}")
        else:
            L.append(f"  OWES `{hl['at']}`: the layout keeps {', '.join(hl['wanted']) or 'none'} "
                     f"of the host's own panels and the plugin declares "
                     f"{', '.join(hl['declared']) if hl.get('declared') is not None else 'nothing'}"
                     f" - without it the host draws every kind it owns")
    if plan:
        L.append(f"  the trim keeps {len(plan['kept'])} entr(ies) and drops "
                 f"{len({d['id'] for d in plan['dropped']})}:")
        for d in plan["dropped"]:
            L.append(f"    - {d['id']}  [{d['axis']}]  {d['why']}")
    if rep["over"] and apply_hint:
        L.append(f"  apply it:  sch dev convert layout --root {root} --point {point} --name {name} "
                 f"--apply")
    return "\n".join(L)
