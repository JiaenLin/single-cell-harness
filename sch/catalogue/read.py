"""Reading a plugin without running it: every layout the family has, by parsing, never by import.

A CATALOGUE THAT IMPORTS A PLUGIN TO LIST IT CANNOT LIST THE FAMILY. A one-file plugin pinned to
numpy 1.23 is listable by a host running numpy 2 only because its declaration is a LITERAL, read
from the syntax tree (scProfile's `FileKernel` reads it the same way). Nothing here executes a line
of a plugin, imports a tool, or needs a tool's environment: `ast`, the harness's `yamlish`, and
files read as text.

UNREADABLE IS AN ERROR THAT NAMES THE FILE, NEVER AN EMPTY DECLARATION. scProfile's host turns a
syntax error or a non-literal `PLUGIN` into a kernel with `spec = {}` and status `planned`
(`scprofile/kernels.py`, `FileKernel.__init__`) - a plugin listed with nothing declared, which a
reader takes for a plugin that declares nothing. The same class as a named word list that silently
loads no words (GAP-101). Here each such file raises `Unreadable` carrying its path, and the
catalogue reports it beside the plugins it could read.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

from .. import yamlish


class Unreadable(Exception):
    """A plugin, or a declaration it depends on, that could not be read. Names the file."""

    def __init__(self, path, why):
        super().__init__(f"{path}: {why}")
        self.path = Path(path)
        self.why = why


def _source(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise Unreadable(path, f"cannot be read: {type(e).__name__}: {e}") from None


def _tree(path: Path, text: str):
    try:
        return ast.parse(text, filename=str(path))
    except SyntaxError as e:
        raise Unreadable(path, f"is not valid Python (line {e.lineno}): {e.msg}") from None


def _named(target, name) -> bool:
    return isinstance(target, ast.Name) and target.id == name


def _mutates(node, name) -> bool:
    """A module-level statement that changes `name` after it was assigned: `X[k] = v`, `X.a = v`,
    `X |= {...}`, `del X[k]`, `X.update(...)`. The literal a static reader sees is then not the
    declaration the plugin runs with."""
    def base(t):
        while isinstance(t, (ast.Subscript, ast.Attribute)):
            t = t.value
        return t
    if isinstance(node, ast.Assign):
        return any(not _named(t, name) and _named(base(t), name) for t in node.targets)
    if isinstance(node, ast.AugAssign):
        return _named(base(node.target), name)
    if isinstance(node, ast.Delete):
        return any(_named(base(t), name) for t in node.targets)
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
        f = node.value.func
        return isinstance(f, ast.Attribute) and _named(base(f.value), name)
    return False


def module_literal(path, name: str, *, what: str = "declaration"):
    """(value, line) of a module-level `name = <literal>`, read without importing the file.

    Every shape a host would silently read as nothing is refused here, by name: no assignment, an
    annotated one (`name: dict = {...}` is an `AnnAssign`, which `FileKernel` does not look at), two
    assignments (which one is meant is a guess), a value that is not a literal, and a literal that
    is changed after it is written.
    """
    p = Path(path)
    tree = _tree(p, _source(p))
    found = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(_named(t, name) for t in node.targets):
            found.append(node)
        elif isinstance(node, ast.AnnAssign) and _named(node.target, name):
            raise Unreadable(p, f"line {node.lineno}: `{name}` is assigned with a type annotation; "
                                f"a host reads `{name} = ...` only, so it would see no {what}")
    if not found:
        raise Unreadable(p, f"has no module-level `{name} = ...`; a host would list it with an "
                            f"empty {what}")
    if len(found) > 1:
        lines = ", ".join(str(n.lineno) for n in found)
        raise Unreadable(p, f"assigns `{name}` {len(found)} times (lines {lines}); which one is the "
                            f"{what} is a guess this catalogue does not make")
    node = found[0]
    later = [n.lineno for n in tree.body if n.lineno > node.lineno and _mutates(n, name)]
    if later:
        raise Unreadable(p, f"changes `{name}` after it is written (line {later[0]}); the literal "
                            f"a static reader sees is then not the {what} the plugin runs with")
    try:
        value = ast.literal_eval(node.value)
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError) as e:
        raise Unreadable(p, f"line {node.lineno}: `{name}` is not a literal ({e}); a {what} must be "
                            f"readable without running the file") from None
    return value, node.lineno


def plugin_literal(path):
    """(spec, line) of a one-file plugin's `PLUGIN` dict. Raises `Unreadable` naming the file."""
    spec, line = module_literal(path, "PLUGIN")
    if not isinstance(spec, dict):
        raise Unreadable(path, f"line {line}: `PLUGIN` is a {type(spec).__name__}, not a mapping")
    return spec, line


def yaml_mapping(path):
    """A YAML file the harness's `yamlish` can read, as a mapping, or `Unreadable` naming it."""
    p = Path(path)
    try:
        data = yamlish.load(p)
    except (OSError, UnicodeDecodeError) as e:
        raise Unreadable(p, f"cannot be read: {type(e).__name__}: {e}") from None
    except yamlish.YamlError as e:
        raise Unreadable(p, f"is not readable YAML: {e}") from None
    if not isinstance(data, dict):
        raise Unreadable(p, "is not a mapping at the top level")
    return data


def assay_reads(paths, root) -> list:
    """`file:line` for every place these Python sources read the run's assay.

    EVIDENCE, NEVER A DEFAULT. A plugin whose code branches on the assay and whose declaration
    names none is the shape rule 2 exists for ("no silent default assay"), and the catalogue can
    show it without deciding anything. Read from the syntax tree, so a comment or a docstring
    mentioning the word never counts: an attribute named `assay` (`ctx.assay`, `g.assay`),
    `getattr(x, "assay", ...)`, a key `"assay"` taken by subscript or `.get`. Python only.
    """
    out = set()
    for p in paths:
        p = Path(p)
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        except (OSError, UnicodeDecodeError, SyntaxError):
            continue                      # the plugin's own reader has already said why
        rel = _rel(p, root)

        def key(n):
            return isinstance(n, ast.Constant) and n.value == "assay"
        for n in ast.walk(tree):
            if isinstance(n, ast.Attribute) and n.attr == "assay":
                out.add((rel, n.lineno))
            elif isinstance(n, ast.Subscript) and key(n.slice):
                out.add((rel, n.lineno))
            elif isinstance(n, ast.Call) and n.args:
                f = n.func
                name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
                if name == "getattr" and len(n.args) >= 2 and key(n.args[1]):
                    out.add((rel, n.lineno))
                elif name == "get" and key(n.args[0]):
                    out.add((rel, n.lineno))
    return [f"{f}:{ln}" for f, ln in sorted(out)]


def _rel(p: Path, root) -> str:
    try:
        return str(Path(p).resolve().relative_to(Path(root).resolve()))
    except ValueError:
        return str(p)


_HEX = re.compile(r"^[0-9a-f]{7,64}$")


def head_of(root):
    """The commit a checkout is at, read from `.git` by file (no git binary), or None."""
    g = Path(root) / ".git"
    try:
        if g.is_file():                           # a linked worktree: `gitdir: <path>`
            txt = g.read_text(encoding="utf-8").strip()
            if not txt.startswith("gitdir:"):
                return None
            g = (Path(root) / txt.split(":", 1)[1].strip()).resolve()
        head = (g / "HEAD").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if _HEX.match(head):
        return head
    if not head.startswith("ref:"):
        return None
    ref = head.split(":", 1)[1].strip()
    dirs = [g]
    common = g / "commondir"
    if common.is_file():
        try:
            dirs.append((g / common.read_text(encoding="utf-8").strip()).resolve())
        except OSError:
            pass
    for d in dirs:
        f = d / ref
        if f.is_file():
            sha = f.read_text(encoding="utf-8").strip()
            if _HEX.match(sha):
                return sha
        packed = d / "packed-refs"
        if packed.is_file():
            for line in packed.read_text(encoding="utf-8").splitlines():
                parts = line.split()
                if len(parts) == 2 and parts[1] == ref and _HEX.match(parts[0]):
                    return parts[0]
    return None
