"""A YAML subset reader and writer, stdlib only.

The kernel reads manifests and stack declarations. Requiring PyYAML for that would make the one
file every plugin must have depend on a library the host may not carry (C4: the boundary is
plain data both sides are certain to read). The subset is what a manifest needs and no more:

    mappings by indentation · `- ` lists · inline `[a, b]` and `{k: v}` · quoted and bare
    scalars · int / float / bool / null · `>` folded and `|` literal block scalars · comments.

Anything outside the subset raises `YamlError` with the line number, rather than guessing.
"""
from __future__ import annotations

import json
import re


class YamlError(ValueError):
    pass


_SCALAR_INT = re.compile(r"^-?\d+$")
_SCALAR_FLOAT = re.compile(r"^-?(\d+\.\d*|\.\d+|\d+)([eE][-+]?\d+)?$")


def _scalar(tok: str, ln: int):
    t = tok.strip()
    if t == "" or t in ("null", "~"):
        return None
    if t in ("true", "True"):
        return True
    if t in ("false", "False"):
        return False
    if t[0] in "\"'":
        if len(t) < 2 or t[-1] != t[0]:
            raise YamlError(f"line {ln}: unterminated quoted string")
        body = t[1:-1]
        return json.loads('"' + body.replace('"', '\\"') + '"') if t[0] == "'" else json.loads(t)
    if t[0] == "[":
        return _inline_list(t, ln)
    if t[0] == "{":
        return _inline_map(t, ln)
    if _SCALAR_INT.match(t):
        return int(t)
    if _SCALAR_FLOAT.match(t):
        return float(t)
    return t


def _split_inline(body: str, ln: int) -> list[str]:
    out, depth, cur, q = [], 0, [], None
    for ch in body:
        if q:
            cur.append(ch)
            if ch == q:
                q = None
            continue
        if ch in "\"'":
            q = ch
            cur.append(ch)
        elif ch in "[{":
            depth += 1
            cur.append(ch)
        elif ch in "]}":
            depth -= 1
            cur.append(ch)
        elif ch == "," and depth == 0:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    if q or depth:
        raise YamlError(f"line {ln}: unbalanced inline collection")
    tail = "".join(cur)
    if tail.strip():
        out.append(tail)
    return out


def _inline_list(t: str, ln: int):
    if not t.endswith("]"):
        raise YamlError(f"line {ln}: inline list not closed")
    return [_scalar(x, ln) for x in _split_inline(t[1:-1], ln)]


def _inline_map(t: str, ln: int):
    if not t.endswith("}"):
        raise YamlError(f"line {ln}: inline map not closed")
    out = {}
    for item in _split_inline(t[1:-1], ln):
        if ":" not in item:
            raise YamlError(f"line {ln}: inline map entry without ':'")
        k, v = item.split(":", 1)
        out[k.strip().strip("\"'")] = _scalar(v, ln)
    return out


def _strip_comment(line: str) -> str:
    q = None
    for i, ch in enumerate(line):
        if q:
            if ch == q:
                q = None
        elif ch in "\"'":
            q = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            return line[:i].rstrip()
    return line.rstrip()


def loads(text: str):
    lines = []
    for i, raw in enumerate(text.splitlines(), 1):
        if "\t" in raw[: len(raw) - len(raw.lstrip())]:
            raise YamlError(f"line {i}: tabs are not indentation")
        s = _strip_comment(raw)
        if s.strip():
            lines.append((i, len(s) - len(s.lstrip()), s.strip(), raw))
    if not lines:
        return None
    val, idx = _parse_block(lines, 0, lines[0][1])
    if idx != len(lines):
        raise YamlError(f"line {lines[idx][0]}: unexpected content")
    return val


def _block_scalar(lines, idx, indent, style):
    parts, i = [], idx
    while i < len(lines) and lines[i][1] > indent:
        parts.append(lines[i][3].strip())
        i += 1
    text = ("\n" if style == "|" else " ").join(parts)
    return text, i


def _parse_block(lines, idx, indent):
    ln, ind, s, _ = lines[idx]
    if s.startswith("- "):
        return _parse_list(lines, idx, ind)
    if s == "-":
        return _parse_list(lines, idx, ind)
    return _parse_map(lines, idx, ind)


def _parse_list(lines, idx, indent):
    out, i = [], idx
    while i < len(lines) and lines[i][1] == indent and (lines[i][2].startswith("- ") or lines[i][2] == "-"):
        ln, _, s, raw = lines[i]
        rest = s[1:].strip()
        if rest == "":
            if i + 1 < len(lines) and lines[i + 1][1] > indent:
                val, i = _parse_block(lines, i + 1, lines[i + 1][1])
            else:
                val, i = None, i + 1
            out.append(val)
            continue
        if _looks_like_key(rest):
            # a mapping starting on the dash line: "- key: v\n  key2: v2"
            child_indent = indent + 2
            synthetic = (ln, child_indent, rest, raw)
            sub = [synthetic]
            j = i + 1
            while j < len(lines) and lines[j][1] > indent:
                sub.append(lines[j])
                j += 1
            val, k = _parse_map(sub, 0, child_indent)
            if k != len(sub):
                raise YamlError(f"line {sub[k][0]}: unexpected content in list item")
            out.append(val)
            i = j
            continue
        out.append(_scalar(rest, ln))
        i += 1
    return out, i


def _looks_like_key(s: str) -> bool:
    if s[0] in "[{":
        return False
    m = re.match(r"^(\"(?:[^\"\\]|\\.)*\"|'[^']*'|[^:#]+?):(\s|$)", s)
    return bool(m)


def _parse_map(lines, idx, indent):
    out, i = {}, idx
    while i < len(lines) and lines[i][1] == indent:
        ln, _, s, raw = lines[i]
        if s.startswith("- "):
            break
        m = re.match(r"^(\"(?:[^\"\\]|\\.)*\"|'[^']*'|[^:]+?):(\s+(.*))?$", s)
        if not m:
            raise YamlError(f"line {ln}: expected 'key: value', got {s!r}")
        key = m.group(1).strip().strip("\"'")
        rest = (m.group(3) or "").strip()
        if key in out:
            raise YamlError(f"line {ln}: duplicate key {key!r}")
        if rest in (">", "|"):
            val, i = _block_scalar(lines, i + 1, indent, rest)
        elif rest == "":
            if i + 1 < len(lines) and lines[i + 1][1] > indent:
                val, i = _parse_block(lines, i + 1, lines[i + 1][1])
            elif i + 1 < len(lines) and lines[i + 1][1] == indent and lines[i + 1][2].startswith("- "):
                val, i = _parse_list(lines, i + 1, indent)
            else:
                val, i = None, i + 1
        else:
            val, i = _scalar(rest, ln), i + 1
        out[key] = val
    return out, i


def load(path):
    with open(path, encoding="utf-8") as fh:
        return loads(fh.read())


# ------------------------------------------------------------------------------------ writer
def dumps(obj, indent=0) -> str:
    pad = " " * indent
    if isinstance(obj, dict):
        if not obj:
            return pad + "{}\n"
        out = []
        for k, v in obj.items():
            key = json.dumps(k) if re.search(r"[:#\[\]{}\"'\s]", str(k)) else str(k)
            if isinstance(v, (dict, list)) and v:
                out.append(f"{pad}{key}:\n{dumps(v, indent + 2)}")
            else:
                out.append(f"{pad}{key}: {_emit_scalar(v)}\n")
        return "".join(out)
    if isinstance(obj, list):
        if not obj:
            return pad + "[]\n"
        out = []
        for v in obj:
            if isinstance(v, dict) and v:
                body = dumps(v, indent + 2)
                first, _, rest = body.partition("\n")
                out.append(f"{pad}- {first.strip()}\n" + (rest if rest.strip() else ""))
            elif isinstance(v, list):
                out.append(f"{pad}- {_emit_scalar(v)}\n")
            else:
                out.append(f"{pad}- {_emit_scalar(v)}\n")
        return "".join(out)
    return pad + _emit_scalar(obj) + "\n"


def _emit_scalar(v) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, (list, dict)):
        return json.dumps(v)
    s = str(v)
    if s == "" or re.search(r"[:#\[\]{}\n\"']|^[-?&*!|>%@`]", s) or s.strip() != s \
            or s in ("true", "false", "null", "~") or _SCALAR_FLOAT.match(s):
        return json.dumps(s)
    return s


def dump(obj, path):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(dumps(obj))
