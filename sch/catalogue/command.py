"""`sch catalogue [list|show] [ID] [--scprofile CHECKOUT] [--json]`: what an agent reads to choose.

    sch catalogue --scprofile CHECKOUT --json      every plugin, one row each, for an agent
    sch catalogue show ID --scprofile CHECKOUT     one plugin whole: parameters, figures, limits

EXIT CODES, as every `sch` command (sch/cli.py). 2 always means something is wrong, and the
output names it.
- The listing exits 0 when every candidate file was read. It exits 2 when one could not be, and
  names each such file.
- `show` exits 0 when its id names exactly one plugin that was read, even if other files could not
  be: one broken plugin must not stop an agent reading another. The JSON names those files under
  `errors`, and the text gives their count. It exits 2 when the id names nothing, listing the
  unreadable files as possible matches, or when it names more than one plugin.
- Either exits 2 for a checkout that is not one.
"""
from __future__ import annotations

import json

from . import CatalogueError, NOT_DECLARED, build, find, public


def run(a) -> int:
    try:
        cat = build(scprofile=a.scprofile)
    except CatalogueError as e:
        return _refuse(a, str(e))
    if a.action == "show":
        return _show(a, cat)
    if a.id:
        return _refuse(a, f"`sch catalogue list` takes no id; one plugin is `sch catalogue show {a.id}`")
    return _list(a, cat)


def _refuse(a, reason) -> int:
    if a.json:
        print(json.dumps({"status": "refused", "reason": reason}, indent=1))
    else:
        print(f"  refused: {reason}")
    return 2


def _clip(text, n) -> str:
    """Truncated so the reader can see it was truncated (the convention of sch/dev/convert.py)."""
    t = " ".join(str(text or "").split())
    return t if len(t) <= n else t[:n - 1] + "…"


def _pin(prov) -> str:
    up = prov["upstream"]
    if up == NOT_DECLARED:
        return "-"
    v = prov["version"]
    return f"{up} {v[:12]}" if v != NOT_DECLARED else f"{up} (no pin)"


def _sources(cat) -> list:
    lines = []
    for s in cat["sources"]:
        if not s.get("read"):
            lines.append(f"  {s['name']:<10} not read: {s['why']}")
            continue
        at = f" at {s['commit'][:7]}" if s.get("commit") else ""
        lines.append(f"  {s['name']:<10} {s['plugins']:>3} plugin(s), {s['errors']} unreadable, "
                     f"from {', '.join(s['searched'])}{at}")
        lines += [f"             warning: {w}" for w in s.get("warnings", [])]
    return lines


def _list(a, cat) -> int:
    rows = cat["plugins"]
    if a.json:
        print(json.dumps({"catalogue": cat["catalogue"], "sources": cat["sources"],
                          "plugins": [public(r) for r in rows], "errors": cat["errors"],
                          "vocabulary": cat["vocabulary"]}, indent=1, sort_keys=True))
        return 2 if cat["errors"] else 0
    read = [s for s in cat["sources"] if s.get("read")]
    out = [f"  {len(rows)} plugin(s) from {len(read)} source(s); {len(cat['errors'])} file(s) could "
           f"not be read", *_sources(cat), ""]
    w = max([len(r["id"]) for r in rows] + [2])
    out.append(f"  {'ID':<{w}}  {'FORMAT':<10} {'UPSTREAM':<24} {'COHORT RUN':<10} ANSWERS")
    for r in rows:
        shadow = f"  (shadowed by {r['shadowed_by']})" if r.get("shadowed_by") else ""
        out.append(f"  {r['id']:<{w}}  {r['format']:<10} {_clip(_pin(r['provenance']), 24):<24} "
                   f"{r['ran_on_cohort']:<10} {_clip(r['question']['summary'], 72)}{shadow}")
    if cat["errors"]:
        out += ["", "  UNREADABLE - each is a plugin this listing does not contain:"]
        out += [f"    {e['source']}: {e['error']}" for e in cat["errors"]]
    out += ["", "  one plugin whole: sch catalogue show ID; every field: sch catalogue --json"]
    print("\n".join(out))
    return 2 if cat["errors"] else 0


def _show(a, cat) -> int:
    if not a.id:
        return _refuse(a, "`show` needs the plugin's id: sch catalogue show ID")
    hits = find(cat, a.id)
    if not hits:
        why = f"no plugin {a.id!r} in this catalogue"
        if cat["errors"]:
            why += (f"; {len(cat['errors'])} file(s) could not be read and it may be one of them: "
                    + "; ".join(e["path"] for e in cat["errors"]))
        missing = [s["name"] for s in cat["sources"] if not s.get("read")]
        if missing:
            why += f"; not read: {', '.join(missing)} (pass --scprofile CHECKOUT)"
        return _refuse(a, why)
    if len(hits) > 1:
        return _refuse(a, f"{a.id!r} names {len(hits)} plugins - {', '.join(r['id'] for r in hits)} - "
                          f"so give one of those ids")
    row = public(hits[0], details=True)
    if a.json:
        print(json.dumps({"plugin": row, "sources": cat["sources"], "errors": cat["errors"]},
                         indent=1, sort_keys=True))
        return 0
    print("\n".join(_whole(row, cat)))
    return 0


def _join(v, empty="none") -> str:
    if v == NOT_DECLARED or v is None:
        return NOT_DECLARED
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, (str, int, float)):
        return str(v)
    if isinstance(v, dict):
        return ", ".join(f"{k}: {_join(x)}" for k, x in v.items()) or empty
    items = [f"{x['layer']} ({x['from']})" if isinstance(x, dict) and "layer" in x else str(x) for x in v]
    return ", ".join(items) or empty


def _whole(r, cat) -> list:
    i, o, p, d = r["inputs"], r["outputs"], r["provenance"], r.get("details", {})
    des = i["design"]
    pin = p["version"] if p["version"] != NOT_DECLARED else (
        f"not declared (declared as {p['version_declared_as']})"
        if p["version_declared_as"] != NOT_DECLARED else NOT_DECLARED)
    L = [f"{r['id']}  ({r['format']})  {r['path']}"]
    if r.get("shadowed_by"):
        L.append(f"  shadowed by   {r['shadowed_by']}")
    L += [f"  answers       {r['question']['summary']}",
          f"  when to use   {_clip(r['question']['when_to_use'], 160)}",
          f"  format        {r['format']}: {'; '.join(r['format_evidence'])}",
          f"  version       {r['version']}",
          f"  assays        {_join(i['assays'])}",
          f"  reads assay   {_join(i['assay_read_at'], 'nowhere in its Python')}",
          f"  requires      {_join(i['requires'])}",
          f"  optional      {_join(i['optional'])}",
          f"  fetchable     {_join(i['sourceable'])}",
          f"  services      {_join(i['services'])}",
          f"  design        required: {_join(des['required'])}; optional: {_join(des['optional'])}; "
          f"per arm: {_join(des['per_arm'])}; shown the design: {_join(des['shown'])}",
          f"  layers        {_join(i['layers'])}",
          f"  from plugins  {_join(i['from_plugins'])}"]
    if i.get("not_in_vocabulary"):
        L.append(f"  not in vocab  {_join(i['not_in_vocabulary'])}")
    L += [f"  provides      {_join(o['provides'])}",
          f"  produces      {_join(o['produces'])}",
          f"  upstream      {p['upstream']}; version {pin}"
          + (f" ({p['version_from']})" if p.get("version_from") else ""),
          f"  doi           {_join(p['doi'])}",
          f"  cite          {p['cite']}",
          f"  licence       {p['license']}   {p['homepage']}",
          f"  cohort run    {r['ran_on_cohort']}"
          + (f" - {r['ran_on_cohort_record']}" if r.get("ran_on_cohort_record") else "")]
    if r["companions"]:
        L.append(f"  companions    {_join(r['companions'])}")
    params = d.get("parameters") or {}
    if params:
        L.append("  parameters")
        L += [f"    {k} ({v['type']}, default {v['default']!r})  {_clip(v['help'], 100)}"
              for k, v in params.items()]
    for k in ("class", "layer", "reversible", "per_unit", "executor", "figures"):
        if k in d and d[k] not in (NOT_DECLARED, [], {}):
            L.append(f"  {k:<13} {_join(d[k])}")
    L.append("  cannot show")
    L += [f"    - {_clip(c, 180)}" for c in r["cannot_show"]] or ["    (none declared)"]
    if cat["errors"]:
        L.append(f"  ({len(cat['errors'])} other file(s) could not be read: sch catalogue lists them)")
    return L
