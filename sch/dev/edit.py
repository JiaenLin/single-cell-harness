"""The maker edits a plugin's declaration by span (harness ADR-0026).

A COLD AUTHOR EDITED A 5,454-LINE FILE BY HAND FOR 71 MINUTES. An id rename touched four sites,
the ceiling that mattered was 250 lines from its entry, and the only instrument was a text
editor and the file's own comments. The declaration is a pure literal, so the exact source span
of any value is known from `ast`, and replacing that span alone leaves everything else - the
comment trail three authors left, the code, the other declarations - byte for byte. The sites
the maker knows, it follows: the protocol's `.draw("<id>")` lines, the profile list the R guard
reads, the evidence routes (`plan:<id>`), the skips. A site in hand-written code it cannot
follow is REPORTED with its line, never guessed at - and a site only a human can follow is the
finding the round is after.

Every write round-trips through `ast` before it lands: the file must parse and the literal must
still evaluate, or the edit is refused and the file is untouched. `dry=True` returns the diff and
writes nothing. The version is raised once per call, the maker's own minor bump (the layout's
rule), unless the author states one.

Offsets are BYTES: `ast` reports `col_offset` in UTF-8 bytes, and a legend with a non-ASCII
character moved every replacement after it when this worked on characters.
"""
from __future__ import annotations

import ast
import difflib
import re
from pathlib import Path


class Raw:
    """A value given as source text rather than as a Python object: `Raw("c(1, 2)")` lands
    verbatim, so a caller can write a literal exactly as the author would."""

    def __init__(self, text: str):
        self.text = str(text)


def _src_of(value, like: bytes = b"") -> str:
    """The source of a value; a string keeps the quote style of the span it replaces (`like`)
    when it can, so an edited line looks like the lines around it."""
    if isinstance(value, Raw):
        return value.text
    if isinstance(value, str) and like[:1] == b'"' and '"' not in value and "\\" not in value \
            and "\n" not in value:
        return '"' + value + '"'
    return repr(value)


# ------------------------------------------------------------------------------- the literal
def _plugin_node(tree):
    node = next((n for n in tree.body if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == "PLUGIN" for t in n.targets)), None)
    if node is None or not isinstance(node.value, ast.Dict):
        raise ValueError("no `PLUGIN = {...}` dict in the file")
    return node.value


def _get(dnode, key):
    """(key_node, value_node) of `key` in a Dict node, or (None, None)."""
    for k, v in zip(dnode.keys, dnode.values):
        if isinstance(k, ast.Constant) and k.value == key:
            return k, v
    return None, None


_SEG = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)|\[([^\]]+)\]")


def segments(path: str) -> list:
    """`report.figures[native_x].at_most` -> ['report', 'figures', ('id', 'native_x'), 'at_most'];
    `produces[2]` -> ['produces', ('index', 2)]."""
    out, pos = [], 0
    for m in _SEG.finditer(path):
        if m.start() != pos and path[pos:m.start()] != ".":
            raise ValueError(f"cannot read the path {path!r} at {path[pos:]!r}")
        pos = m.end()
        if m.group(1):
            out.append(m.group(1))
        else:
            sel = m.group(2).strip()
            out.append(("index", int(sel)) if sel.lstrip("-").isdigit() else ("id", sel.strip("'\"")))
    if pos != len(path):
        raise ValueError(f"cannot read the path {path!r} at {path[pos:]!r}")
    return out


def resolve(plug, path: str):
    """(parent_node, key_or_index, key_node, value_node) for a path into the literal; the
    key/value nodes are None when the last segment names a key the parent lacks."""
    segs = segments(path)
    node, parent, key, knode = plug, None, None, None
    for i, seg in enumerate(segs):
        parent = node
        if isinstance(seg, tuple):
            if not isinstance(node, ast.List):
                raise ValueError(f"{path}: `{_show(segs[:i])}` is not a list")
            if seg[0] == "index":
                idx = seg[1] if seg[1] >= 0 else len(node.elts) + seg[1]
                if not 0 <= idx < len(node.elts):
                    raise ValueError(f"{path}: no element {seg[1]} in `{_show(segs[:i])}`")
                key, knode, node = idx, None, node.elts[idx]
                continue
            want = seg[1]
            hit = next((e for e in node.elts if isinstance(e, ast.Dict)
                        and isinstance(_get(e, "id")[1], ast.Constant)
                        and _get(e, "id")[1].value == want), None)
            if hit is None:
                raise ValueError(f"{path}: no entry with id {want!r} in `{_show(segs[:i])}`; "
                                 f"the ids are " + ", ".join(
                                     str(_get(e, "id")[1].value) for e in node.elts
                                     if isinstance(e, ast.Dict) and _get(e, "id")[1] is not None))
            key, knode, node = want, None, hit
            continue
        if not isinstance(node, ast.Dict):
            raise ValueError(f"{path}: `{_show(segs[:i])}` is not a mapping")
        knode, vnode = _get(node, seg)
        if vnode is None:
            if i == len(segs) - 1:
                return node, seg, None, None
            raise ValueError(f"{path}: no key {seg!r} in `{_show(segs[:i]) or 'PLUGIN'}`")
        key, node = seg, vnode
    return parent, key, knode, node


def _show(segs) -> str:
    out = ""
    for s in segs:
        out += (f"[{s[1]}]" if isinstance(s, tuple) else ("." if out else "") + s)
    return out


# ------------------------------------------------------------------------------- the spans
class _Src:
    """The file as bytes with a line table, so an `ast` position becomes an offset."""

    def __init__(self, text: str):
        self.b = text.encode("utf-8")
        self.starts = [0]
        for i, ch in enumerate(self.b):
            if ch == 0x0A:
                self.starts.append(i + 1)

    def off(self, lineno, col) -> int:
        return self.starts[lineno - 1] + col

    def span(self, node):
        return self.off(node.lineno, node.col_offset), self.off(node.end_lineno, node.end_col_offset)

    def line_bounds(self, lineno):
        a = self.starts[lineno - 1]
        b = self.starts[lineno] if lineno < len(self.starts) else len(self.b)
        return a, b

    def replace(self, a, b, new: str) -> str:
        return (self.b[:a] + new.encode("utf-8") + self.b[b:]).decode("utf-8")

    def text(self) -> str:
        return self.b.decode("utf-8")


def _parse(text: str):
    tree = ast.parse(text)
    return tree, _plugin_node(tree)


def _indent_of(src: _Src, lineno) -> str:
    a, b = src.line_bounds(lineno)
    line = src.b[a:b].decode("utf-8")
    return line[:len(line) - len(line.lstrip())]


def _own_line(src: _Src, node) -> bool:
    """Whether the node's first line holds nothing before it but indentation."""
    a, _ = src.line_bounds(node.lineno)
    return src.b[a:src.off(node.lineno, node.col_offset)].strip() == b""


# ------------------------------------------------------------------------------- operations
_SITES = []        # the draw sites an add or duplicate wrote, with their context, per edit() call


def op_set(text: str, path: str, value) -> str:
    tree, plug = _parse(text)
    parent, key, knode, vnode = resolve(plug, path)
    src = _Src(text)
    if vnode is not None:
        a, b = src.span(vnode)
        return src.replace(a, b, _src_of(value, like=src.b[a:a + 1]))
    # A KEY THE MAPPING LACKS: after its first key, on its own line when the keys have their own
    # lines (the layout's own rule for the ceiling), inline otherwise.
    if not parent.keys:
        raise ValueError(f"{path}: `{key}` cannot be added to an empty mapping by span")
    k0, v0 = parent.keys[0], parent.values[0]
    multi = _own_line(src, k0) and (len(parent.keys) < 2 or parent.keys[1].lineno != k0.lineno)
    # the entry's `id` first, when it has one: the layout inserts the ceiling after it
    kid, vid = _get(parent, "id")
    anchor = vid if vid is not None else v0
    if multi:
        _, end = src.line_bounds(anchor.end_lineno)
        ins = f"{_indent_of(src, anchor.lineno)}{key!r}: {_src_of(value)},\n"
        return src.replace(end, end, ins)
    _, b = src.span(anchor)
    return src.replace(b, b, f", {key!r}: {_src_of(value)}")


def op_delete(text: str, path: str) -> str:
    tree, plug = _parse(text)
    parent, key, knode, vnode = resolve(plug, path)
    if vnode is None:
        raise ValueError(f"{path}: nothing to delete, the key is absent")
    src = _Src(text)
    if knode is None:                       # a list element
        a, b = src.span(vnode)
    else:
        a, _ = src.span(knode)
        _, b = src.span(vnode)
    return _cut(src, a, b)


def _cut(src: _Src, a: int, b: int) -> str:
    """Remove bytes a..b and the comma that followed; drop the line when it is left blank."""
    m = re.match(rb"\s*,", src.b[b:])
    if m:
        b += m.end()
    else:
        pm = re.search(rb",\s*$", src.b[:a])
        if pm:
            a = pm.start()
    out = src.b[:a] + src.b[b:]
    # the line that held it, when nothing but whitespace is left of it
    la = out.rfind(b"\n", 0, a) + 1
    lb = out.find(b"\n", a)
    lb = len(out) if lb < 0 else lb + 1
    if out[la:lb].strip() == b"":
        out = out[:la] + out[lb:]
    return out.decode("utf-8")


def op_list_add(text: str, path: str, value) -> str:
    tree, plug = _parse(text)
    parent, key, knode, vnode = resolve(plug, path)
    if not isinstance(vnode, ast.List):
        raise ValueError(f"{path} is not a list")
    src = _Src(text)
    if not vnode.elts:
        a, b = src.span(vnode)
        return src.replace(a, b, f"[{_src_of(value)}]")
    last = vnode.elts[-1]
    # A NEW LINE ONLY WHEN THE BRACKET HAS ONE OF ITS OWN: a list whose `]` closes on the last
    # element's line (`"c.csv"],`) takes the new element inline, or the line after the bracket
    # would carry it and the file would not parse (found on the plugin's own `produces`).
    own_line = last.lineno != vnode.lineno and _own_line(src, last)
    closes_on_last = vnode.end_lineno == last.end_lineno
    a, b = src.span(last)
    new = _src_of(value, like=src.b[a:a + 1])
    if own_line and not closes_on_last:
        _, end = src.line_bounds(last.end_lineno)
        ins = f"{_indent_of(src, last.lineno)}{new},\n"
        return src.replace(end, end, ins)
    if own_line:
        # one element per line, the bracket on the last: the new element takes a line of its
        # own and the bracket moves down with it
        return src.replace(b, b, f",\n{_indent_of(src, last.lineno)}{new}")
    return src.replace(b, b, f", {new}")


def op_list_remove(text: str, path: str, value) -> str:
    tree, plug = _parse(text)
    parent, key, knode, vnode = resolve(plug, path)
    if not isinstance(vnode, ast.List):
        raise ValueError(f"{path} is not a list")
    hit = next((e for e in vnode.elts if isinstance(e, ast.Constant) and e.value == value), None)
    if hit is None:
        raise ValueError(f"{path}: no element {value!r}; the list holds " + ", ".join(
            repr(e.value) for e in vnode.elts if isinstance(e, ast.Constant)))
    src = _Src(text)
    a, b = src.span(hit)
    return _cut(src, a, b)


def _entry(plug, fid):
    _p, _k, _kn, figs = resolve(plug, "report.figures")
    for e in figs.elts:
        if isinstance(e, ast.Dict):
            _, v = _get(e, "id")
            if isinstance(v, ast.Constant) and v.value == fid:
                return figs, e
    raise ValueError(f"no entry with id {fid!r}")


def _stem(fid: str) -> str:
    return fid[len("native_"):] if fid.startswith("native_") else fid


def _profile_list_edit(text: str, plist: str, fn) -> str:
    """Rewrite the stems of `_PROFILE_PLOTS = (...)` with `fn(list) -> list`."""
    if not plist:
        return text
    pat = re.compile(r"(%s\s*=\s*\()([^)]*)(\))" % re.escape(plist), flags=re.S)
    m = pat.search(text)
    if not m:
        return text
    stems = [s.strip().strip("'\"") for s in m.group(2).split(",") if s.strip()]
    new = fn(list(stems))
    body = ", ".join(repr(x) for x in new) + ("," if len(new) == 1 else "")
    return text[:m.start()] + m.group(1) + body + m.group(3) + text[m.end():]


def op_rename(text: str, old: str, new: str, keys: dict) -> tuple:
    """(text, sites_not_followed): the id in the literal, the routes, the draw sites and the
    profile list follow; a remaining whole-word occurrence in the file is reported by line."""
    tree, plug = _parse(text)
    _figs, e = _entry(plug, old)
    # A SIDE-EFFECT ENTRY'S ID IS THE FILE STEM THE TOOL WRITES (harness ADR-0026, run B): the
    # tool names those files itself, so a renamed id promises a file nobody writes and leaves
    # the tool's own files accounted for by nothing.
    side = keys.get("side_effect", "generated")
    _k, gen = _get(e, side)
    if isinstance(gen, ast.Constant) and gen.value is False:
        raise ValueError(f"{old!r} declares `{side}: False`: its files are written by the tool "
                         f"under the tool's own name, and the id is that name. Renaming it "
                         f"promises a file nothing writes; leave the id as the tool spells it.")
    src = _Src(text)
    edits = []
    for node in ast.walk(plug):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            a0, _b0 = src.span(node)
            if node.value == old:
                edits.append((src.span(node), _src_of(new, like=src.b[a0:a0 + 1])))
            elif node.value == f"plan:{old}":
                edits.append((src.span(node), _src_of(f"plan:{new}", like=src.b[a0:a0 + 1])))
    out = src.b
    for (a, b), rep in sorted(edits, key=lambda t: -t[0][0]):
        out = out[:a] + rep.encode("utf-8") + out[b:]
    text = out.decode("utf-8")
    text = re.sub(r"""\.draw\((["'])%s\1\)""" % re.escape(old), f'.draw("{new}")', text)
    text = _profile_list_edit(text, keys.get("profile_list", ""),
                              lambda st: [_stem(new) if s == _stem(old) else s for s in st])
    left = []
    pat = re.compile(r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])" % re.escape(old))
    for i, line in enumerate(text.splitlines(), 1):
        if pat.search(line) and not line.lstrip().startswith("#"):
            left.append((i, line.strip()))
    return text, left


def _fn_of(e):
    _, v = _get(e, "fn")
    return v.value if isinstance(v, ast.Constant) else None


def _drawn_by_tool(e):
    _, v = _get(e, "drawn_by")
    return not isinstance(v, ast.Constant) or v.value == "tool"


def _lone_fn(figs, e) -> str | None:
    """The upstream function this entry alone draws, or None."""
    fn = _fn_of(e)
    if not fn or not _drawn_by_tool(e):
        return None
    for other in figs.elts:
        if other is not e and isinstance(other, ast.Dict) and _fn_of(other) == fn \
                and _drawn_by_tool(other):
            return None
    return fn


def op_remove(text: str, fid: str, keys: dict, skip: dict | None = None) -> str:
    tree, plug = _parse(text)
    figs, e = _entry(plug, fid)
    lone = _lone_fn(figs, e)
    if lone and not skip:
        raise ValueError(f"removing {fid!r} leaves {lone!r} an upstream function no entry draws; "
                         f"say why in `report.skips` - give the ruling as skip={{'skip': "
                         f"<reason>, ...}} (the vocabulary is the tool's `native.VALID`)")
    src = _Src(text)
    a, _ = src.line_bounds(e.lineno)
    _, b = src.line_bounds(e.end_lineno)
    text = src.replace(a, b, "")
    if lone and skip:
        text = op_set(text, f"report.skips.{lone}", dict(skip))
    text = re.sub(r"""^[ \t]*\.draw\((["'])%s\1\)[ \t]*\n""" % re.escape(fid), "", text, flags=re.M)
    text = _profile_list_edit(text, keys.get("profile_list", ""),
                              lambda st: [s for s in st if s != _stem(fid)])
    return text


def _entry_block(entry: dict, indent: str) -> str:
    inner = indent + "    "
    lines = [f"{indent}{{\n"]
    for k, v in entry.items():
        lines.append(f"{inner}{k!r}: {_src_of(v)},\n")
    lines.append(f"{indent}}},\n")
    return "".join(lines)


def op_add(text: str, entry: dict, keys: dict) -> str:
    fid = str(entry.get("id") or "")
    if not fid:
        raise ValueError("an entry needs an `id`")
    tree, plug = _parse(text)
    _p, _k, _kn, figs = resolve(plug, "report.figures")
    for e in figs.elts:
        if isinstance(e, ast.Dict):
            _, v = _get(e, "id")
            if isinstance(v, ast.Constant) and v.value == fid:
                raise ValueError(f"an entry with id {fid!r} exists; duplicate it under a new id, "
                                 f"or set its keys")
    src = _Src(text)
    if figs.elts:
        last = figs.elts[-1]
        indent = _indent_of(src, last.lineno)
        _, end = src.line_bounds(last.end_lineno)
        text = src.replace(end, end, _entry_block(entry, indent))
    else:
        a, b = src.span(figs)
        text = src.replace(a, b, "[\n" + _entry_block(entry, "    ") + "]")
    fn = entry.get("fn")
    skips_path = keys.get("skips", "report.skips")
    if fn:
        try:
            _t, _plug2 = _parse(text)
            _pp, _kk, _kn2, _sk = resolve(_plug2, f"{skips_path}.{fn}")
            if _sk is not None:
                text = op_delete(text, f"{skips_path}.{fn}")
        except ValueError:
            pass
    # THE DRAW SITE, WITH ITS OWN KIND OF AXIS, AT THE TOP LEVEL (harness ADR-0026, K-r): a
    # site appended after the textually last `.draw(` landed inside an unrelated if/else of
    # another entry, and nothing said where. The new line goes after the last UNINDENTED site
    # whose entry is drawn on the same kind of axis - the compare script's sites for a
    # contrast or interaction entry, the per-unit script's for a unit, sample or group entry -
    # and the lines around it are reported.
    axis_key = keys.get("axis", "axis")
    _t2, _plug3 = _parse(text)
    _p3, _k3, _kn3, figs3 = resolve(_plug3, "report.figures")
    axis_of = {}
    for e3 in figs3.elts:
        if isinstance(e3, ast.Dict):
            _, idv = _get(e3, "id")
            _, axv = _get(e3, axis_key)
            if isinstance(idv, ast.Constant) and isinstance(axv, ast.Constant):
                axis_of[str(idv.value)] = str(axv.value)
    unit_axes = ("unit", "sample", "group")
    mine = str(entry.get(axis_key) or "unit")
    same_kind = (lambda ax: (ax in unit_axes) == (mine in unit_axes))
    sites = list(re.finditer(r"""^\.draw\((["'])([^"']+)\1\)[ \t]*\n""", text, flags=re.M))
    fitting = [m for m in sites if same_kind(axis_of.get(m.group(2), "unit"))] or sites
    if fitting:
        m = fitting[-1]
        text = text[:m.end()] + f'.draw("{fid}")\n' + text[m.end():]
        at = text[:m.end()].count("\n") + 1
        ctx_lines = text.splitlines()[max(0, at - 2):at + 2]
        _SITES.append(f"line {at}: " + " | ".join(ctx_lines))
    if str(entry.get(keys.get("axis", "axis")) or "") in ("sample", "unit") \
            and str(entry.get("drawn_by") or "tool") == "tool":
        text = _profile_list_edit(text, keys.get("profile_list", ""),
                                  lambda st: st + ([_stem(fid)] if _stem(fid) not in st else []))
    return text


def op_duplicate(text: str, fid: str, new_id: str, keys: dict) -> str:
    tree, plug = _parse(text)
    figs, e = _entry(plug, fid)
    src = _Src(text)
    a, _ = src.line_bounds(e.lineno)
    _, b = src.line_bounds(e.end_lineno)
    block = src.b[a:b].decode("utf-8")
    _, idv = _get(e, "id")
    ia, ib = src.span(idv)
    block = block[:ia - a] + repr(new_id) + block[ib - a:]
    text = src.replace(b, b, block)
    text, n_ = re.subn(r"""^([ \t]*)\.draw\((["'])%s\2\)([ \t]*\n)""" % re.escape(fid),
                       lambda m: m.group(0) + f'{m.group(1)}.draw("{new_id}"){m.group(3)}', text,
                       count=1, flags=re.M)
    if n_:
        at = text.index(f'.draw("{new_id}")')
        ln = text[:at].count("\n") + 1
        _SITES.append(f"line {ln}: " + " | ".join(text.splitlines()[max(0, ln - 2):ln + 1]))
    _, ax = _get(e, keys.get("axis", "axis"))
    if isinstance(ax, ast.Constant) and ax.value in ("sample", "unit") and _drawn_by_tool(e):
        text = _profile_list_edit(text, keys.get("profile_list", ""),
                                  lambda st: st + [_stem(new_id)])
    return text


def op_swap(text: str, a_id: str, b_id: str) -> str:
    tree, plug = _parse(text)
    figs, ea = _entry(plug, a_id)
    _f, eb = _entry(plug, b_id)
    src = _Src(text)
    (a1, _), (_, a2) = src.line_bounds(ea.lineno), src.line_bounds(ea.end_lineno)
    (b1, _), (_, b2) = src.line_bounds(eb.lineno), src.line_bounds(eb.end_lineno)
    if a1 > b1:
        (a1, a2), (b1, b2) = (b1, b2), (a1, a2)
    out = src.b[:a1] + src.b[b1:b2] + src.b[a2:b1] + src.b[a1:a2] + src.b[b2:]
    return out.decode("utf-8")


def op_rename_key(text: str, path: str, new: str) -> tuple:
    """(text, sites_followed): the key in the literal, and - for a config key - the reads in
    code of the form C["k"], config["k"], ctx.config["k"]."""
    tree, plug = _parse(text)
    parent, key, knode, vnode = resolve(plug, path)
    if knode is None:
        raise ValueError(f"{path}: no such key")
    src = _Src(text)
    a, b = src.span(knode)
    text = src.replace(a, b, _src_of(new, like=src.b[a:a + 1]))
    followed = 0
    if segments(path)[0] == "config":
        pat = re.compile(r"""((?:\bC|\bconfig|\.config)\[)(["'])%s\2(\])""" % re.escape(str(key)))
        text, followed = pat.subn(lambda m: f"{m.group(1)}{m.group(2)}{new}{m.group(2)}{m.group(3)}", text)
    return text, followed


def bump_version(text: str, vkey: str, as_version=None) -> tuple:
    if not vkey:
        return text, None
    vpat = re.compile(r"""(["']%s["']\s*:\s*["'])(\d+)\.(\d+)\.(\d+)(["'])""" % re.escape(vkey))
    m = vpat.search(text)
    if not m:
        return text, None
    old = f"{m.group(2)}.{m.group(3)}.{m.group(4)}"
    new = str(as_version) if as_version else f"{m.group(2)}.{int(m.group(3)) + 1}.0"
    return vpat.sub(lambda mm: mm.group(1) + new + mm.group(5), text, count=1), (old, new)


# ------------------------------------------------------------------------------- the verb
OPS = ("set", "delete", "list_add", "list_remove", "rename", "remove", "add", "duplicate",
       "swap", "rename_key")


def apply_ops(text: str, ops: list, keys: dict) -> tuple:
    """(text, report) after every op, in order; each op re-reads the spans from the text the
    previous one left."""
    rep = {"sites_not_followed": [], "sites_followed": 0, "ops": [], "sites_written": []}
    del _SITES[:]
    for op in ops:
        name, args = op[0], list(op[1:])
        if name == "set":
            text = op_set(text, args[0], args[1])
        elif name == "delete":
            text = op_delete(text, args[0])
        elif name == "list_add":
            text = op_list_add(text, args[0], args[1])
        elif name == "list_remove":
            text = op_list_remove(text, args[0], args[1])
        elif name == "rename":
            text, left = op_rename(text, args[0], args[1], keys)
            rep["sites_not_followed"] += left
        elif name == "remove":
            text = op_remove(text, args[0], keys, skip=args[1] if len(args) > 1 else None)
        elif name == "add":
            text = op_add(text, args[0], keys)
        elif name == "duplicate":
            text = op_duplicate(text, args[0], args[1], keys)
        elif name == "swap":
            text = op_swap(text, args[0], args[1])
        elif name == "rename_key":
            text, n = op_rename_key(text, args[0], args[1])
            rep["sites_followed"] += n
        else:
            raise ValueError(f"unknown edit {name!r}; the edits are " + ", ".join(OPS))
        rep["ops"].append(name)
    rep["sites_written"] = list(_SITES)
    return text, rep


def edit(path, ops: list, keys: dict, as_version=None, dry: bool = False) -> dict:
    """Apply `ops` to the plugin file at `path`; write only when the result parses and the
    literal evaluates. Returns the report: version, sites, diff."""
    p = Path(path)
    before = p.read_text(encoding="utf-8")
    text, rep = apply_ops(before, ops, keys)
    text, version = bump_version(text, keys.get("version", ""), as_version=as_version)
    try:
        tree, plug = _parse(text)
        ast.literal_eval(plug)
    except (SyntaxError, ValueError) as e:
        raise ValueError(f"the edit would leave the file unreadable ({e}); nothing written")
    rep["version"] = version
    rep["diff"] = "".join(difflib.unified_diff(
        before.splitlines(keepends=True), text.splitlines(keepends=True),
        fromfile=str(p), tofile=str(p) + " (edited)", n=1))
    rep["changed"] = text != before
    if not dry and text != before:
        p.write_text(text, encoding="utf-8")
    return rep
