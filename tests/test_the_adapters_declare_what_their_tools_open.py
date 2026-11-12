"""THE ADAPTERS DECLARE WHAT THEIR TOOLS OPEN (harness autodev W056, wave B of the design read D6).

Wave A made the files a driven run depends on exactly the files DECLARED for it (each stage adapter's `files:`). A
declaration can be wrong: a tool opens a file its adapter does not declare, or an adapter declares what its tool never
opens. Here the other side is read from the TOOL:

- each stand-in (tests/fixtures) declares in its `describe` the files each command opens (`files`: its flags by
  dest, and for scQC the samplesheet's columns), as its tool would, and REFUSES a call whose declared file is absent,
  so no test can pass a stand-in a file the declaration would not have caught (ATTACKS 1);
- THE DRIFT TEST compares each family adapter's `files:` and `owned:` with what its tool says it opens: always with
  the stand-in's `describe` and the flags its parser types a path; and with SCH_REAL_TOOLS naming the four checkouts
  (read as text by `ast`, no environment), with the flags each tool's own argument parser types `type=Path` for the
  commands its adapter calls and, for scQC, whose parser types none, the samplesheet columns its planner reads
  (engine/graph.py) and lists as its own (engine/steps.py NOT_FACTORS). A file flag the adapter forwards and neither
  declares nor owns FAILS; a declared param the tool does not know FAILS; a column the tool reads that is neither
  declared nor decided TEXT below FAILS; a declared column it never reads FAILS. Each difference names the flag and
  both sides.

What no flag and no declared column names (an environment variable, a default, a key inside an inline JSON value,
a file derived from a named one, a child process's reads) is seen by nothing here: the design read's stated limit.
"""
from __future__ import annotations

import ast
import copy
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from sch import yamlish

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
FAMILY = ROOT / "plugins" / "single-cell"
#: Each family adapter: its tool, and the command its flat params go to (anno@scanno's FLAGS name their commands).
ADAPTERS = {"qc@scqc": ("scQC", "run"), "anno@scanno": ("scAnno", None), "int@scintegrate": ("scIntegrate", "integrate"),
            "prof@scprofile": ("scProfile", "run")}
#: Each real tool's parser, under SCH_REAL_TOOLS/<tool>.
PARSERS = {"scQC": "scqc_cli.py", "scAnno": "scanno/cli.py", "scIntegrate": "scintegrate/cli.py",
           "scProfile": "scprofile/cli.py"}
#: THE COLUMNS scQC READS THAT ARE TEXT, each decided by the tool's line that reads it (wave B, at 8106f50): a column
#: its planner reads that is neither here nor in qc@scqc's `observations` reader fails the drift test, by name.
TEXT_COLUMNS = {"scQC": {
    "sample": "the library's name (engine/graph.py:49)", "assay": "a word (engine/graph.py:103)",
    "platform": "a word (modules/00_ingest/ingest.py:118)", "species": "a word (modules/00_ingest/ingest.py:116)",
    "reference": "a registry key, looked up (modules/00_ingest/ingest.py:131-132); on the align route also the "
                 "aligner's folder (engine/steps.py:1135, :1142), undeclared there: a stated limit",
    "fastq_r2": "listed (engine/steps.py:93) and read nowhere", "expected_genes": "a number (engine/graph.py:54)",
    "dbr": "a number (engine/graph.py:381)", "dbr_sd": "a number (engine/graph.py:382)",
    "mt_prefix": "a gene-name prefix (engine/graph.py:460)", "ribo_pattern": "a pattern (engine/graph.py:461)",
    "nf_antisense": "a boolean (engine/graph.py:471)",
    **{f"ambient_{k}": f"a supplied correction's provenance, recorded (engine/graph.py:{n})"
       for k, n in (("tool", 137), ("version", 138), ("params", 139), ("produced_by", 140))},
    "ambient_skip_reason": "recorded (engine/graph.py:167)", "ambient_skip_approved_by": "recorded (engine/graph.py:168)",
}}
#: Each stand-in: how its `describe` is called, and its parser's source.
STAND_INS = {
    "scQC": ([str(FIXTURES / "fake_scqc.py")], None, FIXTURES / "fake_scqc.py"),
    "scAnno": ([str(FIXTURES / "fake_scanno.py")], None, FIXTURES / "fake_scanno.py"),
    "scIntegrate": (["-m", "scintegrate.cli"], FIXTURES / "fake_scintegrate",
                    FIXTURES / "fake_scintegrate" / "scintegrate" / "cli.py"),
    "scProfile": (["-m", "scprofile.cli"], FIXTURES / "fake_scprofile",
                  FIXTURES / "fake_scprofile" / "scprofile" / "cli.py"),
}


def stand_in(tool: str, *argv, cwd=None):
    head, path, _ = STAND_INS[tool]
    env = dict(os.environ, PYTHONPATH=str(path)) if path else dict(os.environ)
    for k in [k for k in env if k.startswith("FAKE_")]:
        env.pop(k)
    return subprocess.run([sys.executable, *head, *argv], capture_output=True, text=True, env=env, cwd=cwd)


def described(tool: str) -> dict:
    r = stand_in(tool, "describe")
    assert r.returncode == 0, (tool, r.stderr)
    return json.loads(r.stdout)["files"]


class EachStandInRefusesAnAbsentDeclaredFile(unittest.TestCase):
    """Change 1: a stand-in is no laxer than its declaration - every file its `describe` declares, absent, refuses."""

    def setUp(self):
        import tempfile
        self.tmp = Path(tempfile.mkdtemp(prefix="w056b_"))
        self.addCleanup(__import__("shutil").rmtree, self.tmp, True)

    def present(self, kind: str, name: str) -> str:
        p = self.tmp / name
        p.mkdir() if kind == "dir" else p.write_text("a declared input\n")
        return str(p)

    def calls(self, tool: str):
        """(the declared flag, a call naming every declared file present, the same call with that one absent)."""
        files = described(tool)["flags"]
        base = {"scQC": ["run", "--project", str(self.tmp / "p"), "--mode", "evidence"],
                "scAnno": None, "scIntegrate": ["integrate", "--out", str(self.tmp / "o"), "--label-key", "l",
                                                "--species", "s"],
                "scProfile": ["run", "--out", str(self.tmp / "o")]}[tool]
        for cmd, flags in files.items():
            argv = base or [cmd, "--out", str(self.tmp / "o")] + (
                ["--cluster-key", "k", "--species", "s", "--tissue", "t", "--assay", "scrna"]
                if cmd == "annotate" else [] if cmd != "rescue" else ["--label-key", "l"])
            given = {d: self.present(k, f"{cmd}.{d}") for d, k in flags.items()}
            if tool == "scQC":                   # the samplesheet: one library, its declared cells present
                cols = described(tool)["columns"]["run.samplesheet"]
                cells = {c: self.present(k, f"cell.{c}") for c, k in cols.items()}
                Path(given["samplesheet"]).write_text("sample\t" + "\t".join(cells) + "\nL1\t" +
                                                      "\t".join(cells.values()) + "\n")
            full = argv + [x for d, v in given.items() for x in (f"--{d.replace('_', '-')}", v)]
            for d in flags:
                gone = [x if x != given[d] else str(self.tmp / "absent" / Path(x).name) for x in full]
                yield f"{cmd} --{d.replace('_', '-')}", full, gone
            if tool == "scQC":
                for c in cols:
                    sheet = self.tmp / f"sheet.{c}.tsv"
                    sheet.write_text(Path(given["samplesheet"]).read_text().replace(
                        cells[c], str(self.tmp / "absent" / c)))
                    yield f"column {c}", full, [x if x != given["samplesheet"] else str(sheet) for x in full]

    def test_each_stand_in_refuses_a_call_whose_declared_file_is_absent_and_names_it(self):
        seen = {}
        for tool in STAND_INS:
            for what, full, gone in self.calls(tool):
                r = stand_in(tool, *full)
                self.assertNotIn(" is not a ", r.stderr, (tool, what, "every declared file present", r.stderr))
                self.assertNotIn("names no file", r.stderr, (tool, what, r.stderr))
                r = stand_in(tool, *gone)
                flag = what.split(" ", 1)[1]
                self.assertEqual(r.returncode, 2, (tool, what, r.stdout, r.stderr))
                self.assertIn(flag.removeprefix("column ") if what.startswith("column") else flag, r.stderr,
                              (tool, what))
                seen.setdefault(tool, []).append(what)
        self.assertEqual(sorted(seen), sorted(STAND_INS), seen)
        self.assertIn("annotate --tree", seen["scAnno"])
        self.assertIn("column matrix", seen["scQC"])
        self.assertIn("run --section", seen["scProfile"])

    def test_a_stand_ins_describe_declares_its_files_as_its_tool_would(self):
        for tool in STAND_INS:
            f = described(tool)
            self.assertTrue(f["flags"], tool)
            for cmd, flags in f["flags"].items():
                self.assertTrue(set(flags.values()) <= {"file", "dir", "path"}, (tool, cmd, flags))
        self.assertEqual(sorted(described("scQC")["columns"]), ["run.samplesheet"])


# ---------------------------------------------------------------------------- the other side, read from the tool
def parser_flags(src: str) -> dict:
    """{command: {dest: (typed a path, line)}} for every `add_argument` of every subcommand of an argparse parser, read
    by `ast`: a subparser bound to a name, its groups, a helper called with it (`_common(g)`) and a loop over every
    subcommand (`for sp in sub.choices.values()`) or over a tuple of flag names (`for f in ("a", "b")`, a flag
    written `f` or `f"--{f}"`); `type=Path` (or `pathlib.Path`) is typed a path."""
    tree = ast.parse(src)
    defs = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.args.args}
    out: dict = {}

    def text(node, env):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.Name) and node.id in env:
            return env[node.id]
        if isinstance(node, ast.JoinedStr):
            parts = [text(v.value if isinstance(v, ast.FormattedValue) else v, env) for v in node.values]
            return None if None in parts else "".join(parts)
        return None

    def add(cmds, call, env):
        flags = [x for x in (text(a, env) for a in call.args) if x]
        kw = {k.arg: k.value for k in call.keywords if k.arg}
        dest = kw["dest"].value if isinstance(kw.get("dest"), ast.Constant) else next(
            (f for f in flags if f.startswith("--")), flags[0] if flags else "").lstrip("-").replace("-", "_")
        typed = "type" in kw and ast.unparse(kw["type"]).split(".")[-1] == "Path"
        for c in cmds:
            if dest:
                was = out.setdefault(c, {}).get(dest)
                out[c][dest] = (typed or bool(was and was[0]), call.lineno if typed or not was else was[1])

    def run(body, bound, env):
        for st in body:
            if isinstance(st, ast.FunctionDef):
                continue                         # a helper runs where it is called, with what it is called with
            if isinstance(st, ast.For):
                names = [text(e, env) for e in getattr(st.iter, "elts", None) or []]
                if isinstance(st.target, ast.Name) and ".choices" in ast.unparse(st.iter):
                    run(st.body, dict(bound, **{st.target.id: set(out)}), env)
                elif isinstance(st.target, ast.Name) and names and None not in names:
                    for x in names:
                        run(st.body, dict(bound), dict(env, **{st.target.id: x}))
                else:
                    run(st.body, dict(bound), env)
                continue
            if isinstance(st, (ast.If, ast.With, ast.Try, ast.While)):
                for part in ("body", "orelse", "finalbody"):
                    run(getattr(st, part, None) or [], bound, env)
                for h in getattr(st, "handlers", None) or []:
                    run(h.body, bound, env)
                continue
            if isinstance(st, ast.Assign) and isinstance(st.value, ast.Call):
                f, names = st.value.func, [t.id for t in st.targets if isinstance(t, ast.Name)]
                if getattr(f, "attr", "") == "add_parser" and st.value.args and isinstance(st.value.args[0],
                                                                                           ast.Constant):
                    for n in names:
                        bound[n] = {st.value.args[0].value}
                    out.setdefault(st.value.args[0].value, {})
                elif getattr(f, "attr", "") in ("add_argument_group", "add_mutually_exclusive_group") and \
                        isinstance(f.value, ast.Name) and f.value.id in bound:
                    for n in names:
                        bound[n] = set(bound[f.value.id])
            for c in ast.walk(st):
                if not isinstance(c, ast.Call):
                    continue
                if isinstance(c.func, ast.Attribute) and c.func.attr == "add_argument" and isinstance(
                        c.func.value, ast.Name) and c.func.value.id in bound:
                    add(bound[c.func.value.id], c, env)
                elif isinstance(c.func, ast.Name) and c.func.id in defs and c.args and isinstance(
                        c.args[0], ast.Name) and c.args[0].id in bound:
                    h = defs[c.func.id]
                    run(h.body, {h.args.args[0].arg: set(bound[c.args[0].id])}, {})

    for n in tree.body:
        if isinstance(n, ast.FunctionDef):
            run(n.body, {}, {})
    return out


def planner_columns(root: Path) -> dict:
    """{column: line} - the samplesheet columns scQC's planner reads (engine/graph.py: `.get("<c>")` or `["<c>"]` of a
    row, `row`, `r` or `by_sample[...]`) and the ones it lists as its own inputs (engine/steps.py NOT_FACTORS)."""
    def row(b):
        return (isinstance(b, ast.Name) and b.id in ("row", "r")) or (
            isinstance(b, ast.Subscript) and isinstance(b.value, ast.Name) and b.value.id == "by_sample")
    seen = {}
    for n in ast.walk(ast.parse((root / "engine" / "graph.py").read_text(encoding="utf-8"))):
        c = None
        if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "get" and row(n.func.value) and n.args and \
                isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str):
            c = n.args[0].value
        elif isinstance(n, ast.Subscript) and row(n.value) and isinstance(n.slice, ast.Constant) and \
                isinstance(n.slice.value, str):
            c = n.slice.value
        if c:
            seen[c] = min(seen.get(c, n.lineno), n.lineno)
    steps = ast.parse((root / "engine" / "steps.py").read_text(encoding="utf-8"))
    nf = [n for n in ast.walk(steps) if isinstance(n, ast.Assign) and any(
        getattr(t, "id", "") == "NOT_FACTORS" for t in n.targets)]
    assert len(nf) == 1, "scQC's own list of its samplesheet inputs (engine/steps.py NOT_FACTORS) moved: follow it"
    for e in ast.walk(nf[0].value):
        if isinstance(e, ast.Constant) and isinstance(e.value, str):
            seen.setdefault(e.value, f"steps.py:{nf[0].lineno}")
    return {c: (f"engine/graph.py:{v}" if isinstance(v, int) else f"engine/{v}") for c, v in seen.items()}


#: HOW scQC 8106f50 TAKES EACH DECLARED SAMPLESHEET CELL (autodev W056 D6 fix round, ATTACKS 1), read from its planner and
#: ingest: True where every read of the column by name strips the cell, else the lines reading it as written. The
#: stand-in reads each column it opens by name the same way (always tested), and this is scQC's own code (under
#: SCH_REAL_TOOLS). The walk refuses a padded cell of any column a tool reads, so this ties the stand-in, not the walk.
SCQC_CELLS = {"matrix": "engine/graph.py:52, engine/graph.py:119", "fastq_r1": "engine/graph.py:52, engine/graph.py:112",
              "ambient_h5": True,
              "aligner_cells": True, "cellbender_barcodes": True, "cellreads_stats": True, "ambient_log": True,
              "ambient_metrics": True}


def cell_reads(files: dict, columns) -> dict:
    """{column: True, or the lines reading it as written} - how a reader takes each named samplesheet cell: a read
    (`.get("<c>")` or `["<c>"]` of `row`, `r` or `by_sample[...]`) inside the receiver of a `.strip()` is stripped
    (`str(row.get("c") or "").strip()`); any other (`Path(str(row.get("c")))`) is as written. `files`: {label: src}."""
    def row(b):
        return (isinstance(b, ast.Name) and b.id in ("row", "r")) or (
            isinstance(b, ast.Subscript) and isinstance(b.value, ast.Name) and b.value.id == "by_sample")
    got: dict = {}
    for label, src in files.items():
        tree = ast.parse(src)
        inside = {id(m) for n in ast.walk(tree) if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "strip"
                  for m in ast.walk(n.func.value)}
        for n in ast.walk(tree):
            c = None
            if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "get" and row(n.func.value) and n.args and \
                    isinstance(n.args[0], ast.Constant):
                c = n.args[0].value
            elif isinstance(n, ast.Subscript) and row(n.value) and isinstance(n.slice, ast.Constant):
                c = n.slice.value
            if c in columns:
                got.setdefault(c, [])
                if id(n) not in inside:
                    got[c].append(f"{label}:{n.lineno}")
    return {c: True if not v else ", ".join(sorted(set(v), key=lambda w: (w.split(":")[0], int(w.split(":")[1]))))
            for c, v in got.items()}


def stand_in_side(tool: str, src: str | None = None) -> dict:
    """What a stand-in says it opens: its `describe` files, plus every flag its parser types a path."""
    f = described(tool)
    flags = {c: {d: (k, "its describe") for d, k in v.items()} for c, v in f["flags"].items()}
    for c, v in parser_flags(src if src is not None else STAND_INS[tool][2].read_text()).items():
        for d, (typed, line) in v.items():
            if typed:
                flags.setdefault(c, {}).setdefault(d, ("path", f"its parser, type=Path at line {line}"))
    return {"who": f"the {tool} stand-in", "flags": flags, "known": {c: set(v) for c, v in flags.items()},
            "columns": {k: {c: (kind, "its describe") for c, kind in v.items()} for k, v in
                        (f.get("columns") or {}).items()}, "kinds": True}


def real_side(tool: str, root: Path, src: str | None = None) -> dict:
    """What a real tool says it opens: the flags its parser types `type=Path`, the flags it knows, and for scQC the
    columns its planner reads (each a path to compare, or decided TEXT_COLUMNS)."""
    rel = PARSERS[tool]
    got = parser_flags(src if src is not None else (root / tool / rel).read_text(encoding="utf-8"))
    side = {"who": tool, "flags": {c: {d: ("path", f"{rel}:{line}") for d, (t, line) in v.items() if t}
                                   for c, v in got.items()},
            "known": {c: set(v) for c, v in got.items()}, "columns": {}, "kinds": False}
    if tool == "scQC":
        side["columns"]["run.samplesheet"] = {c: ("path", w) for c, w in planner_columns(root / tool).items()}
    return side


def forwarded(adapter: str, m: dict) -> set:
    """Every param the adapter passes its tool, as the request writes it (run.py FORWARDED or FLAGS, and REQUIRED)."""
    tool, flat = ADAPTERS[adapter]
    got = set()
    for node in ast.parse((FAMILY / adapter / "run.py").read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and {getattr(t, "id", "") for t in node.targets} & {
                "FORWARDED", "FLAGS", "REQUIRED"}:
            v = ast.literal_eval(node.value)
            got |= {f"{c}.{f}" for c, fs in v.items() for f in fs} if isinstance(v, dict) else {
                f if adapter == "qc@scqc" else f"{flat}.{f}" for f in v}
    return got


def differences(adapter: str, m: dict, side: dict) -> list:
    """Each difference between an adapter's declaration (`files:`, `owned:`) and what its tool says it opens, one line
    each, naming the flag (or column) and both sides."""
    tool, flat = ADAPTERS[adapter]
    files, owned = m.get("files") or {}, {str(x) for x in m.get("owned") or []}
    fwd = forwarded(adapter, m)
    calls = sorted({p.split(".", 1)[0] for p in fwd if "." in p}) if flat is None else [flat]

    def key(cmd, dest):
        return dest if adapter == "qc@scqc" else f"{cmd}.{dest}"

    def where(param):
        return (flat, param) if adapter == "qc@scqc" else tuple(param.split(".", 1))
    out = []
    for cmd in calls:
        for dest, (kind, at) in sorted(side["flags"].get(cmd, {}).items()):
            k = key(cmd, dest)
            if k not in files and k not in owned and k in fwd:
                out.append(f"{adapter}: {cmd} --{dest.replace('_', '-')}: {side['who']} opens it ({kind}, {at}); "
                           f"the adapter forwards it as {k} and declares nothing")
    for param, e in sorted(files.items()):
        if param == "observations" or e.get("kind") == "checkout":
            continue
        cmd, dest = where(param)
        flag = f"--{dest.replace('_', '-')}"
        if dest not in side["known"].get(cmd, set()):
            out.append(f"{adapter}: files.{param}: declared ({e.get('kind')}); {side['who']}'s {cmd} "
                       + (f"does not say it opens {flag}" if side["kinds"] else f"has no {flag}"))
        elif side["kinds"] and e.get("kind") != side["flags"][cmd][dest][0]:
            out.append(f"{adapter}: files.{param}: declared a {e.get('kind')}; {side['who']} opens a "
                       f"{side['flags'][cmd][dest][0]}")
    sheet = ((files.get("observations") or {}).get("names") or {})
    at, each = set(sheet.get("at") or []), (sheet.get("each") or {}).get("kind")
    cols = side["columns"].get(f"{calls[0]}.samplesheet") if adapter == "qc@scqc" else None
    if cols is not None:
        text = TEXT_COLUMNS.get(tool, {}) if not side["kinds"] else {}
        for c in sorted(at - set(cols)):
            out.append(f"{adapter}: observations column {c}: declared; {side['who']} never reads it")
        for c in sorted(set(cols) - at - set(text)):
            out.append(f"{adapter}: observations column {c}: {side['who']} reads it ({cols[c][1]}); the adapter "
                       f"declares nothing and it is not decided text (TEXT_COLUMNS)")
        for c in sorted(at & set(text)):
            out.append(f"{adapter}: observations column {c}: declared, and decided text ({text[c]})")
        if side["kinds"]:
            out += [f"{adapter}: observations column {c}: declared a {each}; {side['who']} opens a {cols[c][0]}"
                    for c in sorted(at & set(cols)) if cols[c][0] != each]
    return out


def manifests() -> dict:
    return {a: yamlish.load(FAMILY / a / "plugin.yml") for a in ADAPTERS}


REAL = Path(os.environ.get("SCH_REAL_TOOLS") or "/nonexistent")


class TheDriftTest(unittest.TestCase):
    """Change 2: each adapter's declaration against what its tool says it opens, both ways, each difference named."""

    def sides(self):
        yield "the stand-ins", {t: stand_in_side(t) for t in STAND_INS}
        if all((REAL / t / PARSERS[t]).is_file() for t in PARSERS):
            yield "the real tools", {t: real_side(t, REAL) for t in PARSERS}

    def test_the_parser_reader_sees_every_flag_each_adapter_forwards(self):
        """The reader is checked against the adapters: every flag an adapter forwards is one its tool's parser
        has, so a parser the reader cannot follow fails here, not silently."""
        ms = manifests()
        for name, sides in self.sides():
            for a, m in ms.items():
                tool, flat = ADAPTERS[a]
                side = sides[tool] if name == "the real tools" else {"known": {c: set(v) for c, v in parser_flags(
                    STAND_INS[tool][2].read_text()).items()}}
                miss = sorted(p for p in forwarded(a, m) if
                              (p.split(".", 1)[1] if "." in p else p) not in side["known"].get(
                                  p.split(".", 1)[0] if "." in p else flat, set())
                              and p not in {str(x) for x in (m.get("files") or {}) if m["files"][x].get("kind") ==
                                            "checkout"})
                self.assertEqual(miss, [], f"{name}: {a} forwards flags its tool's parser, as read, has not")

    def test_each_adapter_declares_exactly_what_its_tool_says_it_opens(self):
        ms = manifests()
        for name, sides in self.sides():
            for a, m in ms.items():
                self.assertEqual(differences(a, m, sides[ADAPTERS[a][0]]), [], f"{a} against {name}")

    def test_a_wrong_declaration_is_named_with_both_sides(self):
        ms = manifests()
        for name, sides in self.sides():
            for a, m in ms.items():
                side = sides[ADAPTERS[a][0]]
                files, flat = m["files"], ADAPTERS[a][1]
                own = [p for p, e in files.items() if p != "observations" and e.get("kind") != "checkout"]
                typed = [p for p in own if (p if a == "qc@scqc" else p.split(".", 1)[1]) in side["flags"].get(
                    flat or p.split(".", 1)[0], {})]
                if not typed:                    # real scQC: its parser types no flag, so a removed entry is
                    self.assertEqual((name, a), ("the real tools", "qc@scqc"))   # unseen (its gap)
                    for p in own:
                        wrong = copy.deepcopy(m)
                        del wrong["files"][p]
                        self.assertEqual(differences(a, wrong, side), [], (a, p))
                gone = (typed or own)[0]
                wrong = copy.deepcopy(m)
                del wrong["files"][gone]          # an entry removed: the flag forwarded and undeclared
                got = differences(a, wrong, side)
                flag = "--" + gone.rsplit(".", 1)[-1].replace("_", "-")
                if typed:
                    self.assertEqual(len(got), 1, (name, a, got))
                    self.assertIn(f" {flag}: ", got[0], (name, a, got))
                    self.assertIn("declares nothing", got[0])
                wrong = copy.deepcopy(m)          # a param the tool does not know, declared
                unknown = ("" if a == "qc@scqc" else gone.split(".", 1)[0] + ".") + "no_such_input"
                wrong["files"][unknown] = {"kind": "file"}
                got = differences(a, wrong, side)
                self.assertEqual(len(got), 1, (name, a, got))
                self.assertIn(f"files.{unknown}: declared (file)", got[0])
            m = ms["qc@scqc"]                    # the samplesheet's columns, both ways
            side = sides["scQC"]
            wrong = copy.deepcopy(m)
            wrong["files"]["observations"]["names"]["at"].remove("cellreads_stats")
            got = differences("qc@scqc", wrong, side)
            self.assertEqual(len(got), 1, (name, got))
            self.assertIn("observations column cellreads_stats: ", got[0])
            self.assertIn("declares nothing", got[0])
            wrong["files"]["observations"]["names"]["at"] += ["cellreads_stats", "matrix_h5"]
            got = differences("qc@scqc", wrong, side)
            self.assertEqual(got, ["qc@scqc: observations column matrix_h5: declared; " + side["who"] +
                                   " never reads it"], name)

    def test_a_flag_typed_a_path_in_a_stand_in_and_forwarded_undeclared_turns_it_red(self):
        src = STAND_INS["scAnno"][2].read_text()
        typed = src.replace('s.add_argument("--gene-key")', 's.add_argument("--gene-key", type=Path)', 1)
        self.assertNotEqual(src, typed)
        got = differences("anno@scanno", manifests()["anno@scanno"], stand_in_side("scAnno", typed))
        self.assertEqual(len(got), 1, got)
        self.assertIn("anno@scanno: annotate --gene-key: the scAnno stand-in opens it (path, its parser, type=Path",
                      got[0])

    def test_the_stand_in_takes_each_declared_cell_as_scqc_does_padded_or_not(self):
        """ATTACKS 1 (autodev W056 D6 fix round): the scQC stand-in died on a padded `ambient_h5` cell that scQC strips,
        which hid a padded cell the walk pinned as an absent file. Each declared column the stand-in reads by name is
        read as scQC reads it: stripped, or as written (SCQC_CELLS); and SCQC_CELLS is scQC's own code."""
        cols = [c for c in manifests()["qc@scqc"]["files"]["observations"]["names"]["at"]]
        self.assertEqual(sorted(SCQC_CELLS), sorted(cols), "a declared column whose cell reading is not decided")
        mine = cell_reads({"fake_scqc.py": STAND_INS["scQC"][2].read_text()}, cols)
        self.assertTrue(mine, "the stand-in reads no declared column by name: nothing compared")
        want = {c: (True if SCQC_CELLS[c] is True else "as written") for c in mine}
        self.assertEqual({c: (True if v is True else "as written") for c, v in mine.items()}, want,
                         f"the stand-in takes a declared cell otherwise than scQC: {mine} against {SCQC_CELLS}")
        old = STAND_INS["scQC"][2].read_text().replace('str(r.get("ambient_h5") or "").strip()', 'r.get("ambient_h5")')
        self.assertEqual(cell_reads({"fake_scqc.py": old}, cols).get("ambient_h5", True) is True, False,
                         "the reader does not see a cell read as written")
        if (REAL / "scQC" / "engine" / "graph.py").is_file():
            real = cell_reads({"engine/graph.py": (REAL / "scQC" / "engine" / "graph.py").read_text(),
                               "ingest.py": (REAL / "scQC" / "modules" / "00_ingest" / "ingest.py").read_text()}, cols)
            self.assertEqual({c: real.get(c, True) for c in cols}, SCQC_CELLS, "scQC takes a declared cell otherwise")

    def test_each_text_column_is_one_scqc_reads_and_none_is_declared(self):
        if not (REAL / "scQC" / "engine" / "graph.py").is_file():
            self.skipTest("SCH_REAL_TOOLS names no scQC checkout")
        cols = planner_columns(REAL / "scQC")
        self.assertEqual(sorted(set(TEXT_COLUMNS["scQC"]) - set(cols)), [], "a decided column scQC no longer reads")


if __name__ == "__main__":
    unittest.main()
