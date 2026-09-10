"""The conversion pipeline: reading a foreign codebase, and resuming a half-built plugin.

WHAT THIS IS FOR. Eight of scProfile's nine plugins owe an accounting of the figures their wrapped
tool already draws. Not because the work was skipped - because the only inventory extractor this
family had was four lines of R inside `kernels/cellchat.py`, hardcoded to one package's naming
convention and reachable by nothing else. `scprofile/native.py`, the half that CONSUMES an
inventory, has been domain-free and shipped the whole time.
"""
from __future__ import annotations

import ast
import contextlib
import inspect
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from sch.dev import convert as C
from sch.dev import extract
from sch.dev import points as P
from sch.dev.extract import draw_sites as DS

ROOT = Path(__file__).resolve().parents[1]

DECL = """
tool: demo
devpoints: 1
tests:
  command: ["{python}", "-c", "print(1)"]
points:
  widget:
    what: a widget
    lives: widgets
    proves: it runs
    cannot_prove: that it is right
    convert:
      placeholder: "TODO"
      upstream: wraps.tool
      stages:
        - {name: contract, fills: [inject]}
        - {name: inventory, fills: [native_plots], why: what the tool already draws}
        - {name: judgement, kind: judgement, fills: [summary, cannot_show]}
"""


def _literals(path):
    """Every string CONSTANT in a module, docstrings excluded, joined.

    A ratchet on "this suite names no repository's vocabulary" has to read the code and not the
    prose. `r_namespace.py` explains CellChat in its header and must go on being able to; what it
    may not do is put one repository's field or wrapper name into a literal the code compares
    against. Comments are not constants at all, so `ast` already excludes them.
    """
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    docs = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", None) or []
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                docs.add(id(body[0].value))
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docs:
            out.append(node.value)
    return "\n".join(out)


@contextlib.contextmanager
def _fake_package(pl):
    """A throwaway importable package, so extraction is tested without depending on a site.

    Yields an interpreter that can import `fakepkg`: the real `sys.executable` with the temporary
    directory on its PYTHONPATH, which the extractor's subprocess inherits.
    """
    d = Path(tempfile.mkdtemp())
    pkg = d / "fakepkg"
    pkg.mkdir()
    if pl:
        (pkg / "__init__.py").write_text("from . import pl\n")
        (pkg / "pl.py").write_text("def umap(x=None): pass\ndef dotplot(x=None): pass\n"
                                   "def _hidden(): pass\n")
    else:
        (pkg / "__init__.py").write_text("def plot_thing(x=None): pass\n"
                                         "def compute_thing(x=None): pass\n")
    prev = os.environ.get("PYTHONPATH")
    os.environ["PYTHONPATH"] = os.pathsep.join([str(d)] + ([prev] if prev else []))
    try:
        yield sys.executable
    finally:
        if prev is None:
            os.environ.pop("PYTHONPATH", None)
        else:
            os.environ["PYTHONPATH"] = prev
        shutil.rmtree(d, ignore_errors=True)


class Extractors(unittest.TestCase):
    def test_the_built_ins_load(self):
        """STRICT, because the first version of the loader returned an empty dict.

        `python_package.py` does `from . import Inventory`; loaded by file path it had no package
        context, the relative import raised, and `discover()` swallowed it - so "there are no
        extractors" and "neither extractor would load" were the same answer.
        """
        got = extract.discover(strict=True)
        self.assertIn("python_package", got)
        self.assertIn("r_namespace", got)
        self.assertIn("draw_sites", got)
        self.assertIn("shared_env", got)
        # THE KINDS ARE LISTED RATHER THAN COUNTED, so adding one is a deliberate edit here.
        # `draw_sites` reads the PLUGIN and the first two read the upstream it wraps, which is
        # why it declares a third kind rather than pretending to be one of theirs. `shared_env`
        # declares a fourth for the same reason and it is the sharpest case: it reads neither the
        # plugin's source alone nor an upstream package, but the ENVIRONMENT a plugin resolves
        # into - which exists only in the repository's own resolver and in no file either of the
        # other kinds can open.
        self.assertEqual({m.EXTRACT["reads"] for m in got.values()},
                         {"python-package", "r-package", "plugin-source", "plugin-environment"})

    def test_every_extractor_declares_what_it_reads(self):
        for name, mod in extract.discover(strict=True).items():
            for key in extract.REQUIRED:
                self.assertTrue(str(mod.EXTRACT.get(key) or "").strip(), f"{name}: no {key}")

    def test_a_package_that_is_not_there_is_not_an_empty_inventory(self):
        """THE DISTINCTION THE WHOLE MECHANISM RESTS ON. An accounting of zero plots, filed
        because the package could not be imported, is a wrapper certified as having nothing to
        account for."""
        from sch.dev.extract import python_package as PP
        inv = PP.inventory("nosuchpackage_zzz")
        self.assertFalse(inv.complete)
        self.assertFalse(bool(inv))
        self.assertEqual(inv.names, [])
        self.assertIn("nosuchpackage_zzz", inv.why_not)

    def test_a_real_package_is_inventoried_and_says_how(self):
        """AGAINST A PACKAGE THIS TEST WRITES, not one that happens to be installed.

        This asked for `matplotlib.pyplot` and passed on the workstation and failed on the cluster,
        because the extractor spawns the interpreter it is GIVEN - correctly, since a wrapped tool
        pins versions the harness does not have - and the default is bare `python3`, which is not
        the interpreter running the suite and had no matplotlib. A test of the extraction should
        not also be a test of what somebody installed.
        """
        from sch.dev.extract import python_package as PP
        with _fake_package(pl=True) as py:
            inv = PP.inventory("fakepkg", python=py)
        self.assertTrue(inv.complete, inv.why_not)
        self.assertIn("pl.umap", inv.names)
        self.assertIn("plotting submodule", inv.how,
                      "an inventory nobody can argue with is one nobody reads")

    def test_a_package_with_no_plotting_submodule_falls_back_to_names_and_says_so(self):
        """THE HEURISTIC PATH, marked as one. cellchat's R extractor is this shape and the
        difference between the two answers is what a maintainer needs to weigh them."""
        from sch.dev.extract import python_package as PP
        with _fake_package(pl=False) as py:
            inv = PP.inventory("fakepkg", python=py)
        self.assertTrue(inv.complete, inv.why_not)
        self.assertIn("plot_thing", inv.names)
        self.assertIn("HEURISTIC", inv.how)

    @unittest.skipUnless(shutil.which("Rscript") or shutil.which("R"), "no R here")
    def test_the_r_extractor_finds_r_plots(self):
        """CELLCHAT'S FOUR LINES, OUT OF CELLCHAT. `stats` is used because it ships with R, so
        this asserts the mechanism rather than the presence of somebody's bioinformatics stack."""
        from sch.dev.extract import r_namespace as RN
        inv = RN.inventory("stats")
        self.assertTrue(inv.complete, inv.why_not)
        self.assertIn("plot.ts", inv.names)

    @unittest.skipUnless(shutil.which("Rscript") or shutil.which("R"), "no R here")
    def test_the_r_pattern_is_an_argument_and_not_a_law(self):
        """A pattern that finds everything and one that finds nothing must give different answers,
        or the pattern is not being used."""
        from sch.dev.extract import r_namespace as RN
        none = RN.inventory("stats", pattern="^zzz_no_such_prefix")
        self.assertTrue(none.complete, "an unmatched pattern is not a failure to look")
        self.assertEqual(none.names, [])


class Stages(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / "widgets").mkdir()
        (self.d / "DEVPOINTS.yaml").write_text(DECL)
        self.doc = P.load(self.d)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_a_point_with_no_convert_block_says_so(self):
        (self.d / "DEVPOINTS.yaml").write_text(
            DECL.split("    convert:")[0])
        with self.assertRaises(C.ConvertError) as cm:
            C.plan(P.load(self.d), "widget")
        self.assertIn("convert", str(cm.exception))

    def test_status_is_computed_from_the_declaration_not_remembered(self):
        """NO JOURNAL, NO LOCK FILE. The plugin file is the state, so a conversion picked up on
        another machine four months later reads the same answer."""
        half = {"inject": {"required": ["counts"]}, "summary": "TODO — what it gives you"}
        rows = C.status(half, self.doc, "widget")
        by = {r["stage"]: r for r in rows}
        self.assertTrue(by["contract"]["done"])
        self.assertFalse(by["inventory"]["done"])
        self.assertFalse(by["judgement"]["done"])
        self.assertEqual(C.next_stage(half, self.doc, "widget")["stage"], "inventory")

    def test_a_placeholder_counts_as_unfilled_however_deep(self):
        deep = {"inject": {"required": ["TODO"]}}
        self.assertEqual(C.unfilled(deep, ["inject"], "TODO"), ["inject"])

    def test_declaring_nothing_and_declaring_it_is_empty_are_different(self):
        """`references: {}` is a maintainer saying they looked; absent is nobody having looked.
        The same distinction the extractors draw, one layer up."""
        self.assertEqual(C.unfilled({}, ["native_plots"], "TODO"), ["native_plots"])
        self.assertEqual(C.unfilled({"native_plots": {}}, ["native_plots"], "TODO"), [])

    def test_a_finished_declaration_has_nothing_left(self):
        done = {"inject": {"required": ["counts"]}, "native_plots": {"pl.x": {"where": "f.png"}},
                "summary": "what it gives you", "cannot_show": ["not a causal claim"]}
        self.assertIsNone(C.next_stage(done, self.doc, "widget"))
        self.assertTrue(all(r["done"] for r in C.status(done, self.doc, "widget")))

    def test_judgement_stages_are_marked_as_such(self):
        """A conversion that stopped listing what only a person can answer would look finished
        while the plugin still could not say what its result must not be read as."""
        rows = {r["stage"]: r for r in C.status({}, self.doc, "widget")}
        self.assertEqual(rows["judgement"]["kind"], "judgement")
        self.assertEqual(rows["inventory"]["kind"], "mechanical")

    def test_the_upstream_field_is_read_from_the_declaration(self):
        _ph, up, _st = C.plan(self.doc, "widget")
        self.assertEqual(up, "wraps.tool")
        self.assertEqual(C._dotted({"wraps": {"tool": "scvelo"}}, up), "scvelo")
        self.assertIsNone(C._dotted({"wraps": {}}, up))


class Command(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / "widgets").mkdir()
        (self.d / "DEVPOINTS.yaml").write_text(DECL)
        (self.d / "widgets" / "half.py").write_text(
            'PLUGIN = {"wraps": {"tool": "nosuchpackage_zzz"}, "inject": {"required": ["x"]}}\n'
            'def run(ctx):\n    raise NotImplementedError\n')

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _run(self, *args):
        return subprocess.run([sys.executable, "-m", "sch", "dev", "convert", *args,
                               "--root", str(self.d), "--point", "widget"],
                              capture_output=True, text=True, cwd=ROOT)

    def test_status_reads_a_plugin_that_does_not_import(self):
        """PARSED, NOT IMPORTED. A half-built plugin is exactly the kind that will not import -
        its run() raises and its dependencies are not installed - which is the state a conversion
        exists to get it out of."""
        p = self._run("status")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("half", p.stdout)
        self.assertIn("what is left, in order", p.stdout)
        self.assertIn("inventory", p.stdout)

    def test_an_inventory_nobody_could_take_fails_rather_than_recording_zero(self):
        p = self._run("inventory")
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertIn("NO EXTRACTOR COULD LOOK", p.stdout)


class Worksheet(unittest.TestCase):
    """The inventory turned into decisions, with the evidence for each one beside it.

    A NAME IS THE ONE THING THE DECIDER ALREADY HAS. The first version of this printed thirty-five
    of them and left somebody to open thirty-five documentation pages and read five thousand lines
    of plugin. Both answers are already available - what a function draws is in the package, and
    whether this wrapper calls it is in the wrapper.
    """

    def _inv(self, names, detail=None):
        from sch.dev.extract import Inventory
        return Inventory("t", names, "how", detail=detail or {})

    def test_every_exported_function_appears(self):
        w = C.worksheet("scanpy", self._inv(["pl.umap", "pl.dotplot"]), {})
        self.assertIn("'pl.umap'", w)
        self.assertIn("'pl.dotplot'", w)

    def test_the_upstream_signature_and_summary_travel_with_it(self):
        w = C.worksheet("t", self._inv(["pl.umap"], {
            "pl.umap": {"signature": "(adata, color=None)",
                        "summary": "Scatter plot in UMAP basis."}}), {})
        self.assertIn("(adata, color=None)", w)
        self.assertIn("Scatter plot in UMAP basis.", w)

    def test_a_deprecated_function_says_so(self):
        w = C.worksheet("t", self._inv(["pl.old"], {"pl.old": {"deprecated": True}}), {})
        self.assertIn("DEPRECATED", w)

    def test_a_function_the_plugin_calls_carries_its_call_site(self):
        """32 of cellchat's 35 are located this way, and 21 carry the output's own name as a
        string literal on the call line."""
        src = 'x = 1\nnpng("heatmap_count", netVisual_heatmap(cc, measure = "count"))\n'
        w = C.worksheet("t", self._inv(["netVisual_heatmap"]), {}, src)
        self.assertIn("called at line 2", w)
        self.assertIn("'heatmap_count'", w)
        self.assertIn("confirm where this lands", w)

    def test_a_function_the_plugin_never_calls_says_that_instead(self):
        w = C.worksheet("t", self._inv(["pl.unused"]), {}, "x = 1\n")
        self.assertIn("not called anywhere", w)
        self.assertIn("which skip applies", w)

    def test_nothing_is_decided_however_strong_the_evidence(self):
        """A wrong `use` reads as a decision and is worse than an absent one."""
        src = 'npng("stem", thing(cc))\n'
        w = C.worksheet("t", self._inv(["thing"]), {}, src)
        self.assertIn("TODO", w.split("'thing'", 1)[1][:120])

    def test_what_is_already_decided_is_carried_through_unchanged(self):
        w = C.worksheet("t", self._inv(["a", "b"]), {"a": {"use": "figures/a.png"}})
        self.assertIn("'a': {'use': 'figures/a.png'}", w)
        self.assertNotIn("TODO", w.split("'b'", 1)[0])

    def test_the_three_valid_skips_are_offered_and_the_rejected_ones_named(self):
        w = C.worksheet("t", self._inv(["a"]), {})
        for reason in ("not_applicable", "superseded_by_design", "duplicate_of"):
            self.assertIn(reason, w)
        self.assertIn("reimplemented", w)

    def test_a_declaration_the_upstream_no_longer_exports_is_reported(self):
        w = C.worksheet("t", self._inv(["a"]), {"gone": {"use": "x"}})
        self.assertIn("NO LONGER EXPORTED", w)
        self.assertIn("gone", w)

    def test_it_counts_what_is_left_and_how_much_is_already_evidenced(self):
        w = C.worksheet("t", self._inv(["a", "b", "c"]), {"a": {"use": "x"}}, "b(1)\n")
        self.assertIn("3 function(s)", w)
        self.assertIn("1 already decided, 2 to rule on", w)
        self.assertIn("1 of those are called by this plugin", w)


class CallSites(unittest.TestCase):
    def test_a_match_in_a_comment_is_reported_and_marked(self):
        """`rankNet`'s only mention in cellchat is the comment "return.data, nothing drawn" -
        precisely the evidence its entry needs. A scan that hid it would throw the answer away."""
        got = C.callsites("# ranked flow, rankNet(return.data, nothing drawn)\n", ["rankNet"])
        self.assertTrue(got["rankNet"]["in_comment"])

    def test_a_real_call_is_preferred_over_a_comment(self):
        src = "# see thing(x)\nthing(cc)\n"
        self.assertFalse(C.callsites(src, ["thing"])["thing"]["in_comment"])

    def test_a_dotted_name_matches_on_its_tail(self):
        self.assertIn("pl.umap", C.callsites("sc.pl.umap(adata)\n", ["pl.umap"]))

    def test_a_name_that_is_never_called_is_absent_not_empty(self):
        self.assertEqual(C.callsites("x = 1\n", ["nope"]), {})


class ActionsAreReachable(unittest.TestCase):
    """EVERY ACTION MUST BE ABLE TO RUN. `account` was unreachable for a commit: the inventory
    block above it had no `if` and returned unconditionally, so `convert account` printed an
    inventory and said nothing about it. Dead code behind a return says nothing when it happens,
    which is the same shape as a test defined below the runner that collects it."""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / "widgets").mkdir()
        (self.d / "DEVPOINTS.yaml").write_text(DECL)
        (self.d / "widgets" / "half.py").write_text(
            'PLUGIN = {"wraps": {"tool": "fakepkg"}, "inject": {"required": ["x"]}}\n')

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _run(self, action, python=None):
        argv = [sys.executable, "-m", "sch", "dev", "convert", action,
                "--root", str(self.d), "--point", "widget"]
        if python:
            argv += ["--python", python]
        return subprocess.run(argv, capture_output=True, text=True, cwd=ROOT)

    def test_each_action_produces_its_own_output(self):
        with _fake_package(pl=True) as py:
            seen = {a: self._run(a, py).stdout for a in ("status", "inventory", "account")}
        self.assertIn("build:", seen["status"])
        self.assertIn("function(s)", seen["inventory"])
        self.assertIn('"native_plots"', seen["account"],
                      "account printed something that is not a worksheet")
        self.assertNotEqual(seen["inventory"], seen["account"])


class StageCommands(unittest.TestCase):
    """A stage that is a command declares it, the way `tests` and `fixture` already do.

    THE HARNESS MUST NOT LEARN WHAT A RUN DIRECTORY LOOKS LIKE. Memory is fitted from what a real
    run cost, the shape of that record is the child tool's, and a measure stage implemented here
    would be scProfile's report.json format compiled into a suite that serves five repositories.
    """

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / "widgets").mkdir()
        (self.d / "DEVPOINTS.yaml").write_text(DECL.replace(
            "        - {name: inventory, fills: [native_plots], why: what the tool already draws}",
            "        - {name: inventory, fills: [native_plots], why: what the tool already draws}\n"
            '        - {name: measure, fills: [mem], command: ["{python}", "-c", "print(1)", "{run}"]}'))
        self.doc = P.load(self.d)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_a_stage_with_a_command_declares_it_and_others_do_not(self):
        self.assertEqual(C.stage_command(self.doc, "widget", "measure")[:3],
                         ["{python}", "-c", "print(1)"])
        self.assertEqual(C.stage_command(self.doc, "widget", "inventory"), [])

    def test_placeholders_are_substituted_by_name_not_by_format(self):
        """EXPLICIT SUBSTITUTION. A declaration is somebody else's text and may hold a brace for
        its own reasons; `str.format` would raise on it or, worse, substitute something."""
        got = C.fill(["{python}", "-x", "{run}", "a{b}c"], {"python": "P", "run": "R"})
        self.assertEqual(got, ["P", "-x", "R", "a{b}c"])

    def test_measure_refuses_without_a_run_rather_than_inventing_one(self):
        p = subprocess.run([sys.executable, "-m", "sch", "dev", "convert", "measure",
                            "--root", str(self.d), "--point", "widget"],
                           capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(p.returncode, 3, p.stdout + p.stderr)
        self.assertIn("--run", p.stderr)

    def test_a_stage_declaring_no_command_says_so_rather_than_guessing(self):
        (self.d / "DEVPOINTS.yaml").write_text(DECL)
        p = subprocess.run([sys.executable, "-m", "sch", "dev", "convert", "measure",
                            "--root", str(self.d), "--point", "widget", "--run", str(self.d)],
                           capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(p.returncode, 3, p.stdout + p.stderr)
        self.assertIn("no command", p.stderr)


class JobScriptsKeepTheirExitCodes(unittest.TestCase):
    """A validation job that can report success while a check failed is not a validation job.

    PBS 708048 sealed `exit=0` with the harness's own unit tier failing. Every summary line in it
    said "1 failing" and the seal said nothing. The cause was one line: the check's exit was
    captured into `echo "  exit $?"` and discarded, so it never reached the trap that decides which
    seal to write.

    THIS FAMILY HAS LOST AN EXIT CODE BEFORE, through `| tee` without `pipefail`, and it is written
    down in docs/CHILD_CONFORMANCE.md. Two different mechanisms, one defect: a command whose status
    is displayed rather than kept.
    """

    JOBS = sorted((ROOT / "jobs").glob("*.pbs")) if (ROOT / "jobs").is_dir() else []

    def test_there_are_job_scripts_to_check(self):
        self.assertTrue(self.JOBS, "no jobs/*.pbs found, so this suite proves nothing")

    def test_no_job_displays_an_exit_code_without_keeping_it(self):
        """`echo "... $?"` is the shape: it READS the status, which resets it, and stores nothing.

        Assigning it first - `rc=$?; echo "  exit $rc"` - keeps it available to test.
        """
        # ONE DEFINITION, in sch/dev/jobcheck.py, so this suite and `sch dev jobcheck` cannot
        # disagree. They used to be the same rule written twice - and the command did not exist,
        # so the rule guarded only the jobs kept in this repository while a job written anywhere
        # else reproduced the defect unwatched.
        from sch.dev import jobcheck as _JC
        bad = [f"{f.name}:{h}" for f in self.JOBS
               for rid, _why, hits in _JC.problems(f) if rid in ("exit-displayed",
                                                                 "status-not-kept")
               for h in hits]
        self.assertEqual(bad, [], "an exit code displayed and not kept:\n  " + "\n  ".join(bad))

    def test_a_pipeline_that_matters_sets_pipefail(self):
        """`cmd | tee log` exits with tee's status, so a failing cmd reads as success. Named in
        docs/CHILD_CONFORMANCE.md after it happened."""
        for f in self.JOBS:
            text = f.read_text(encoding="utf-8")
            if re.search(r"^\s*[^#\n]*\|\s*tee\b", text, re.M):
                self.assertIn("pipefail", text,
                              f"{f.name} pipes into tee without setting pipefail")

    def test_every_job_writes_one_seal_or_the_other(self):
        for f in self.JOBS:
            text = f.read_text(encoding="utf-8")
            self.assertIn("SEALED.txt", text, f"{f.name} writes no seal")
            self.assertIn("FAILED.txt", text, f"{f.name} can only succeed")


class SealsDistinguishFailedFromNotRun(unittest.TestCase):
    """Exit 2 and exit 3 are different answers and a job must not fold them together.

    `sch dev check` exits 2 when a tier FAILED and 3 when one COULD NOT RUN. The distinction was
    built into the ladder deliberately - "an exit code that is always the same is not read" - and
    the first attempt at making a failing tier seal FAILED flattened it, so PBS 708051 sealed
    FAILED with every tier reporting 0 failing. scQC has no baseline and never will, so that seal
    would have been FAILED for ever, which teaches everyone to ignore it: the same defect pointing
    the other way.
    """

    JOBS = sorted((ROOT / "jobs").glob("*.pbs")) if (ROOT / "jobs").is_dir() else []

    def test_a_job_that_reads_a_check_exit_code_tells_three_from_two(self):
        for f in self.JOBS:
            text = f.read_text(encoding="utf-8")
            if "dev check" not in text:
                continue
            self.assertIn("INCOMPLETE_CHECKS", text,
                          f"{f.name} runs `sch dev check` and records only pass or fail, so a "
                          f"tier that could not run reads as one that failed")
            self.assertRegex(text, r"3\)\s*INCOMPLETE_CHECKS",
                             f"{f.name} does not route exit 3 to the incomplete list")

    def test_the_seal_says_what_was_not_checked(self):
        for f in self.JOBS:
            text = f.read_text(encoding="utf-8")
            if "INCOMPLETE_CHECKS" not in text:
                continue
            self.assertIn("incomplete_checks=", text,
                          f"{f.name} tracks incomplete checks and never writes them into the seal")


class UpstreamCalls(unittest.TestCase):
    """Which functions of the wrapped tool this plugin actually drives.

    THE IMPORTS ARE INSIDE THE FUNCTIONS, because `scprofile/plugin.py` requires it - module scope
    runs in the HOST's interpreter, which has none of the plugin's pins. A grep for `^import`
    finds almost nothing, so this is parsed.
    """

    SRC = ("def run(ctx):\n"
           "    import scanpy as sc\n"
           "    sc.tl.score_genes_cell_cycle(a, s_genes=S, n_bins=25)\n"
           "    sc.pl.umap(a)\n"
           "    other.thing(1)\n")

    def test_it_follows_the_alias(self):
        got = C.upstream_calls(self.SRC, "scanpy")
        self.assertIn("scanpy.tl.score_genes_cell_cycle", got)
        self.assertIn("scanpy.pl.umap", got)

    def test_it_records_what_the_call_names_explicitly(self):
        got = C.upstream_calls(self.SRC, "scanpy")
        self.assertEqual(got["scanpy.tl.score_genes_cell_cycle"]["passes"], ["n_bins", "s_genes"])

    def test_calls_into_anything_else_are_not_the_wrapped_tool(self):
        self.assertNotIn("other.thing", C.upstream_calls(self.SRC, "scanpy"))

    def test_a_plugin_that_never_imports_the_tool_yields_nothing(self):
        self.assertEqual(C.upstream_calls("def run(ctx):\n    pass\n", "scanpy"), {})


class Defaults(unittest.TestCase):
    def test_the_worksheet_separates_passed_from_inherited(self):
        """`config` means the tool's own defaults DECLARED rather than inherited, and the failure
        is silent - cellrank's terminal-state method was passed bare, so the number deciding what
        the fate probabilities are probabilities OF appeared nowhere a reader could see."""
        w = C.defaults_worksheet(
            "fk", {"fk.score": {"line": 9, "passes": ["s_genes"]}},
            {"fk.score": {"found": True, "summary": "Score.", "params": [
                {"name": "adata", "default": "", "required": True, "annotation": ""},
                {"name": "s_genes", "default": "None", "required": False, "annotation": ""},
                {"name": "n_bins", "default": "25", "required": False, "annotation": ""}]}},
            {})
        self.assertIn("passes: ['s_genes']", w)
        self.assertIn("INHERITED SILENTLY (1)", w)
        self.assertIn("n_bins", w.split("INHERITED SILENTLY", 1)[1])
        self.assertNotIn("s_genes", w.split("INHERITED SILENTLY", 1)[1])

    def test_a_signature_that_could_not_be_read_says_so(self):
        w = C.defaults_worksheet("fk", {"fk.x": {"line": 1, "passes": []}},
                                 {"fk.x": {"found": False, "why_not": "no such attribute"}}, {})
        self.assertIn("could not read its signature", w)

    def test_a_call_naming_every_optional_parameter_inherits_nothing(self):
        w = C.defaults_worksheet(
            "fk", {"fk.x": {"line": 1, "passes": ["a"]}},
            {"fk.x": {"found": True, "params": [
                {"name": "a", "default": "1", "required": False, "annotation": ""}]}}, {})
        self.assertIn("inherits nothing", w)


class References(unittest.TestCase):
    def test_a_gene_list_written_into_the_plugin_is_a_bundled_reference(self):
        """THE ONE THE FIRST VERSION MISSED. cellcycle's sets are `<block>.split()`, a Call and not
        a literal, so `literal_eval` raised and 97 symbols scored against every cell were
        invisible."""
        src = 'S_GENES = """%s""".split()\n' % " ".join(f"GENE{i}" for i in range(30))
        got = C.references_in(src)
        self.assertEqual([r["kind"] for r in got], ["bundled"])
        self.assertIn("30 entries", got[0]["what"])

    def test_prose_is_not_a_data_set(self):
        """`origin (29 entries, e.g. on, the, single)` was a docstring split on whitespace."""
        src = 'NOTE = """%s""".split()\n' % " ".join(["the", "quick", "brown", "fox"] * 8)
        self.assertEqual(C.references_in(src), [])

    def test_a_url_in_prose_is_not_a_reference(self):
        """Every plugin records its upstream's homepage, and reporting those made each one look
        like it had two undeclared fetches."""
        src = '"""See https://example.com/docs for the method."""\nPLUGIN = {"wraps": {"homepage": "https://example.com"}}\n'
        self.assertEqual(C.references_in(src), [])

    def test_a_url_in_executable_code_is_one(self):
        src = 'def run(ctx):\n    url = "https://example.com/data.csv"\n'
        self.assertEqual([r["kind"] for r in C.references_in(src)], ["fetch"])

    def test_a_call_named_like_a_fetch_is_flagged(self):
        src = "def run(ctx):\n    import decoupler as dc\n    net = dc.get_collectri(organism='human')\n"
        got = C.references_in(src, "decoupler")
        self.assertIn("runtime?", [r["kind"] for r in got])


class Contract(unittest.TestCase):
    def test_figures_are_not_produces(self):
        """They are declared in `report.figures`, each with the question it settles. Listing them
        under `produces` sent a reader to add five entries to the wrong field."""
        src = ('def run(ctx):\n    ctx.emit_obs("score", x)\n    ctx.emit_figure("F1_thing", y)\n'
               '    ctx.emit_table("t", z)\n')
        got = C.contract_in(src)
        self.assertEqual(got["produces"], ["obs[score]", "tables/t"])
        self.assertEqual(got["report.figures"], ["F1_thing"])

    def test_what_the_plugin_asks_ctx_for_is_reported(self):
        src = 'def run(ctx):\n    a = ctx.organism\n    b = ctx.keys["label"]\n'
        reads = C.contract_in(src)["reads"]
        self.assertIn("organism", reads)
        self.assertIn("keys[label]", reads)


class VersionMismatchIsDiagnosed(unittest.TestCase):
    """A missing attribute is usually the wrong interpreter, and the tool has what it needs to say so.

    Asked with a python holding decoupler 2.2.0 about a plugin pinned to `>=1.8,<1.9`, the first
    version said only "module 'decoupler' has no attribute 'run_ulm'" - true, useless, and it reads
    as a broken plugin. `run_ulm` moved to `dc.mt.*` in 2.x. The installed version is in hand and
    the pin is in the declaration.
    """

    def test_a_pin_and_an_installed_version_that_disagree_are_named(self):
        w = C.defaults_worksheet(
            "decoupler", {"decoupler.run_ulm": {"line": 1, "passes": []}},
            {"decoupler.run_ulm": {"found": False, "why_not": "no attribute", "installed": "2.2.0"}},
            {}, pins={"decoupler": ">=1.8,<1.9"})
        self.assertIn("2.2.0", w)
        self.assertIn(">=1.8,<1.9", w)
        self.assertIn("THOSE DISAGREE", w)

    def test_a_version_inside_the_pin_is_not_blamed(self):
        w = C.defaults_worksheet(
            "decoupler", {"decoupler.x": {"line": 1, "passes": []}},
            {"decoupler.x": {"found": False, "why_not": "no attribute", "installed": "1.8.3"}},
            {}, pins={"decoupler": ">=1.8,<1.9"})
        self.assertNotIn("THOSE DISAGREE", w)

    def test_the_comparison_is_only_used_to_warn(self):
        for inst, pin, ok in (("2.2.0", ">=1.8,<1.9", False), ("1.8.3", ">=1.8,<1.9", True),
                              ("1.9.0", ">=1.8,<1.9", False), ("3.6.1", ">=3.6,<4", True),
                              ("1.0", "some prose", True)):
            self.assertEqual(C._satisfies(inst, pin), ok, f"{inst} vs {pin}")


class TheContractScanAdmitsWhatItCannotSee(unittest.TestCase):
    """A found set presented as a replacement would delete correct entries.

    velocity emits inside `for col in ...: ctx.emit_obs(col, ...)` and as an f-string, so a scan
    finds 3 of its 9 `produces` and 7 of its 9 figures. Printing the found set as the answer would
    have removed six correct declarations - and the six it cannot see are precisely the ones whose
    names are computed, which is knowable and now said.
    """

    DYN = ('def run(ctx):\n'
           '    ctx.emit_obs("fixed", a)\n'
           '    for col in cols:\n'
           '        ctx.emit_obs(col, a)\n'
           '    ctx.emit_obsm(f"velocity_{basis}", b)\n')

    def test_a_computed_name_is_recorded_not_dropped(self):
        got = C.contract_in(self.DYN)
        self.assertEqual(got["produces"], ["obs[fixed]"])
        self.assertEqual(len(got["dynamic"]), 2)
        self.assertEqual({d[0] for d in got["dynamic"]}, {"emit_obs", "emit_obsm"})

    def test_each_blind_spot_carries_its_line(self):
        for _fn, line, _expr in C.contract_in(self.DYN)["dynamic"]:
            self.assertTrue(line > 0)

    def test_a_plugin_emitting_only_literals_has_no_blind_spots(self):
        got = C.contract_in('def run(ctx):\n    ctx.emit_obs("a", x)\n')
        self.assertEqual(got["dynamic"], [])
        self.assertEqual(got["produces"], ["obs[a]"])


class NameCollisionsAreNotHandledParameters(unittest.TestCase):
    """A config key of the same name is not the same parameter, and saying so implied it was.

    velocity declares `min_confidence` with default 0.5 - its OWN threshold, for a figure gate -
    and calls `scv.tl.latent_time(A)` bare, so scvelo uses its own `min_confidence` of 0.75. Two
    values, one name, both live in that plugin, and a reader of the config would reasonably think
    they were one thing. "already in config" said the opposite of what is true.
    """

    def _w(self, declared):
        return C.defaults_worksheet(
            "scvelo", {"scvelo.tl.latent_time": {"line": 1, "passes": [], "splat": False}},
            {"scvelo.tl.latent_time": {"found": True, "params": [
                {"name": "min_confidence", "default": "0.75", "required": False,
                 "annotation": ""}]}},
            declared)

    def test_a_same_named_config_key_that_is_not_passed_is_a_collision(self):
        w = self._w({"min_confidence": {"type": "float", "default": 0.5}})
        self.assertIn("NAME COLLISION", w)
        self.assertIn("0.5", w)
        self.assertIn("0.75", w)
        self.assertNotIn("already in config", w)

    def test_with_no_such_config_key_it_is_simply_undeclared(self):
        w = self._w({})
        self.assertNotIn("NAME COLLISION", w)
        self.assertIn("declare it, or leave it", w)


class SplatHidesKeywords(unittest.TestCase):
    """`f(**opts)` passes keywords this scan cannot name, so "passes nothing" would be wrong."""

    def test_a_splat_call_is_recorded(self):
        got = C.upstream_calls(
            "def run(ctx):\n    import scvelo as scv\n    scv.tl.velocity(A, **opts)\n", "scvelo")
        self.assertTrue(got["scvelo.tl.velocity"]["splat"])

    def test_the_worksheet_says_the_inherited_list_may_be_too_long(self):
        w = C.defaults_worksheet(
            "scvelo", {"scvelo.tl.velocity": {"line": 1, "passes": [], "splat": True}},
            {"scvelo.tl.velocity": {"found": True, "params": [
                {"name": "mode", "default": "'stochastic'", "required": False, "annotation": ""}]}},
            {})
        self.assertIn("**kwargs", w)
        self.assertIn("may be too long", w)

    def test_a_plain_call_makes_no_such_claim(self):
        got = C.upstream_calls(
            "def run(ctx):\n    import scvelo as scv\n    scv.tl.velocity(A, mode='x')\n", "scvelo")
        self.assertFalse(got["scvelo.tl.velocity"]["splat"])


class TheDefaultPathWorks(unittest.TestCase):
    """`--point` OMITTED IS THE PATH SOMEBODY TYPES FIRST, and it crashed.

    `point = a.point or next(iter(P.points(doc)))` - `points.py` exports `point`, singular, so
    every `sch dev convert` without --point died on AttributeError. Every test and every example
    I wrote passed --point, so the default was never executed by anything. A cold agent hit it on
    its first command.
    """

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / "widgets").mkdir()
        (self.d / "DEVPOINTS.yaml").write_text(DECL)
        (self.d / "widgets" / "half.py").write_text('PLUGIN = {"inject": {"required": ["x"]}}\n')

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _run(self, *args, root=None):
        return subprocess.run([sys.executable, "-m", "sch", "dev", "convert", *args,
                               "--root", str(root or self.d)],
                              capture_output=True, text=True, cwd=ROOT)

    def test_status_runs_without_being_told_the_point(self):
        p = self._run()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("build:", p.stdout)

    def test_a_repository_declaring_nothing_says_so_rather_than_tracing_back(self):
        empty = Path(tempfile.mkdtemp())
        try:
            p = self._run(root=empty)
            self.assertEqual(p.returncode, 3, p.stdout + p.stderr)
            self.assertIn("DEVPOINTS", p.stderr)
            self.assertNotIn("Traceback", p.stderr)
        finally:
            shutil.rmtree(empty, ignore_errors=True)


class ReferencesAcknowledgesWhatIsDeclared(unittest.TestCase):
    """It printed the same "declare {}" line before and after somebody declared {}.

    The already-declared line was only reached when the extractor had candidates, so a maintainer
    who had just done the work was told to do it again and reasonably concluded the edit had not
    taken. Reported by a cold agent who hit exactly that.
    """

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / "widgets").mkdir()
        (self.d / "DEVPOINTS.yaml").write_text(DECL)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _say(self, plugin_src):
        (self.d / "widgets" / "w.py").write_text(plugin_src)
        p = subprocess.run([sys.executable, "-m", "sch", "dev", "convert", "references",
                            "--root", str(self.d), "--point", "widget"],
                           capture_output=True, text=True, cwd=ROOT)
        return p.stdout

    def test_an_explicit_empty_is_acknowledged(self):
        out = self._say('PLUGIN = {"references": {}}\n')
        self.assertIn("somebody looked", out)
        self.assertNotIn("absent says nobody did", out)

    def test_absent_is_still_asked_for(self):
        out = self._say('PLUGIN = {}\n')
        self.assertIn("absent says nobody did", out)

    def test_declared_references_this_scan_cannot_see_are_not_contradicted(self):
        out = self._say('PLUGIN = {"references": {"db": {"tier": "fetch"}}}\n')
        self.assertIn("already declared", out)
        self.assertIn("not contradicted", out)


class ADottedNameMatchesItsSubmodule(unittest.TestCase):
    """Matching the tail alone reported three scvelo plots as called when none was.

    `pl.paga` matched `scv.tl.paga(...)` - a different submodule - `pl.plot` matched `ctx.plot()`
    and `pl.scatter` matched `ax.scatter(...)`, neither of them scvelo. Three of seven "called"
    were wrong and each would have sent somebody to write a `use` entry for a function the plugin
    never calls. The whole point of the worksheet is that its evidence can be trusted at a glance.
    """

    SRC = ("scv.tl.paga(A, groups=k)\n"
           "F, plt = ctx.figure, ctx.plot()\n"
           "ax.scatter(x, y)\n"
           "scv.pl.velocity_embedding_stream(A)\n")

    def test_a_different_submodule_is_not_a_match(self):
        self.assertEqual(C.callsites(self.SRC, ["pl.paga"]), {})

    def test_a_same_named_method_on_something_else_is_not_a_match(self):
        self.assertEqual(C.callsites(self.SRC, ["pl.plot"]), {})
        self.assertEqual(C.callsites(self.SRC, ["pl.scatter"]), {})

    def test_the_real_call_still_matches_through_an_alias(self):
        got = C.callsites(self.SRC, ["pl.velocity_embedding_stream"])
        self.assertEqual(got["pl.velocity_embedding_stream"]["line"], 4)

    def test_an_undotted_name_still_matches_on_itself(self):
        got = C.callsites("netVisual_circle(cc)\n", ["netVisual_circle"])
        self.assertIn("netVisual_circle", got)

    def test_and_is_not_matched_inside_a_longer_identifier(self):
        self.assertEqual(C.callsites("my_netVisual_circle(cc)\n", ["netVisual_circle"]), {})


class BuildAndTestAreSeparate(unittest.TestCase):
    """A build stage reads source and cannot be fitted to a cohort; a test stage needs data.

    Written down because the pull is real. The memory measurement needs a run, the real cohort is
    where the data is, and reaching for it during a BUILD is how a plugin ends up shaped around one
    dataset - which is the thing the two-shape fixture exists to prevent.
    """

    DECL2 = DECL.replace(
        "        - {name: contract, fills: [inject]}",
        "        - {name: contract, phase: build, fills: [inject]}\n"
        "        - {name: measure, phase: test, fills: [mem]}")

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / "widgets").mkdir()
        (self.d / "DEVPOINTS.yaml").write_text(self.DECL2)
        self.doc = P.load(self.d)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_each_stage_carries_its_phase(self):
        got = {r["stage"]: r["phase"] for r in C.status({}, self.doc, "widget")}
        self.assertEqual(got["contract"], "build")
        self.assertEqual(got["measure"], "test")

    def test_a_stage_with_no_phase_declared_is_a_build_stage(self):
        """The safe default: a stage nobody classified must not silently be allowed data."""
        got = {r["stage"]: r["phase"] for r in C.status({}, self.doc, "widget")}
        self.assertEqual(got["inventory"], "build")

    def test_the_two_are_counted_and_reported_apart(self):
        out = C.format_status(C.status({"inject": {"a": 1}}, self.doc, "widget"), "w", "widget")
        self.assertIn("build: 1 of", out)
        self.assertIn("test: 0 of 1", out)
        self.assertIn("cannot be fitted to a cohort", out)


class AFilledFieldIsNotAlwaysAFinishedStage(unittest.TestCase):
    """velocity's `native_plots` holds 2 of scvelo's 20 and its admission says so.

    The status read the field's presence and reported the stage done, while the plugin was saying
    in another field that eighteen remain. A point declares which field means outstanding.
    """

    DECL3 = DECL.replace(
        "        - {name: inventory, fills: [native_plots], why: what the tool already draws}",
        "        - {name: inventory, fills: [native_plots], outstanding_if: wraps.unreviewed}")

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / "widgets").mkdir()
        (self.d / "DEVPOINTS.yaml").write_text(self.DECL3)
        self.doc = P.load(self.d)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _row(self, spec):
        return {r["stage"]: r for r in C.status(spec, self.doc, "widget")}["inventory"]

    def test_filled_with_an_outstanding_admission_is_partial(self):
        r = self._row({"native_plots": {"a": {"use": "x"}},
                       "wraps": {"unreviewed": "18 of 20 remain"}})
        self.assertFalse(r["done"])
        self.assertEqual(r["partial"], "18 of 20 remain")

    def test_filled_with_no_admission_is_done(self):
        r = self._row({"native_plots": {"a": {"use": "x"}}})
        self.assertTrue(r["done"])
        self.assertFalse(r["partial"])

    def test_empty_is_neither_done_nor_partial(self):
        r = self._row({})
        self.assertFalse(r["done"])
        self.assertFalse(r["partial"])

    def test_the_report_distinguishes_partial_from_todo(self):
        out = C.format_status(C.status({"native_plots": {"a": 1},
                                        "wraps": {"unreviewed": "18 remain"}},
                                       self.doc, "widget"), "w", "widget")
        self.assertIn("PART inventory", out)
        self.assertIn("the plugin says so", out)


class JobScriptsParse(unittest.TestCase):
    """`bash -n` on every job, because a shell quoting trap is invisible to reading.

    `VPY="${VPY:?pass -v VPY=<the interpreter velocity's environment resolved to>}"` - the
    apostrophe inside a `${VAR:?message}` expansion opens a quote context that is never closed, and
    the error bash reports points at the END of the file, sixty lines from the cause. Every line in
    the file has balanced quotes; the construct spans them.
    """

    JOBS = sorted((ROOT / "jobs").glob("*.pbs")) if (ROOT / "jobs").is_dir() else []

    def test_every_job_script_is_valid_shell(self):
        bad = []
        for f in self.JOBS:
            p = subprocess.run(["bash", "-n", str(f)], capture_output=True, text=True)
            if p.returncode != 0:
                bad.append(f"{f.name}: {p.stderr.strip().splitlines()[0] if p.stderr else '?'}")
        self.assertEqual(bad, [], "job scripts that do not parse:\n  " + "\n  ".join(bad))

    def test_the_check_fires_on_the_trap_that_caused_it(self):
        import tempfile as _t
        with _t.NamedTemporaryFile("w", suffix=".pbs", delete=False) as fh:
            fh.write('X="${X:?the tool\'s own thing}"\necho done\n')
            name = fh.name
        try:
            p = subprocess.run(["bash", "-n", name], capture_output=True, text=True)
            self.assertNotEqual(p.returncode, 0,
                                "an apostrophe inside ${VAR:?...} no longer breaks bash, so this "
                                "check is testing nothing")
        finally:
            pathlib_unlink = Path(name)
            pathlib_unlink.unlink(missing_ok=True)


class TheDriverWalksTheBuild(unittest.TestCase):
    """`sch dev convert build` runs the build phase in order and stops where a person is needed.

    `status` named the next stage and not the command; naming the command still left an agent to
    run six of them by hand and know which need the plugin's own interpreter. NEVER the test
    phase - that needs data and is a different question.
    """

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / "widgets").mkdir()
        (self.d / "DEVPOINTS.yaml").write_text(DECL.replace(
            "        - {name: contract, fills: [inject]}",
            "        - {name: contract, phase: build, fills: [inject]}\n"
            "        - {name: measure, phase: test, fills: [mem]}"))
        (self.d / "widgets" / "w.py").write_text(
            'PLUGIN = {"inject": {"required": ["x"]}, "wraps": {"tool": "fakepkg"}}\n')

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _build(self):
        return subprocess.run([sys.executable, "-m", "sch", "dev", "convert", "build",
                               "--root", str(self.d), "--point", "widget"],
                              capture_output=True, text=True, cwd=ROOT)

    def test_it_reports_the_build_and_never_the_test_phase(self):
        out = self._build().stdout
        self.assertIn("build is", out)
        self.assertNotIn("measure", out.split("STOP")[0])

    def test_it_stops_where_only_a_person_can_go_on(self):
        out = self._build().stdout
        self.assertIn("STOP at", out)

    def test_a_sub_stage_can_find_the_harness(self):
        """It ran each stage with cwd set to the TARGET repository, so `-m sch` was not importable
        and every stage died on "No module named sch" - reported as the stage failing."""
        self.assertNotIn("No module named sch", self._build().stdout + self._build().stderr)

    def test_the_header_comes_before_the_output_it_heads(self):
        """The parent's prints are buffered and the child's are not, so a stage's output arrived
        ABOVE the line saying which stage it was."""
        out = self._build().stdout
        if "--- references" in out and "consulted" in out:
            self.assertLess(out.index("--- references"), out.index("consulted"))


class RulingOnEveryEntry(unittest.TestCase):
    """A stage whose field is a LIST is not finished when the list exists.

    THE DEFECT THIS EXISTS FOR. `unfilled` asks whether a field is there, which is the whole
    question for `config` or `summary` and the wrong question for `report.figures`. The list is
    there from the moment the first figure is declared, so a stage that ruled on it reported done
    with fifty-five of fifty-six panels never looked at. Unlike `outstanding_if`, this needs no
    admission from the plugin - which is what makes it work on a plugin that has never been told
    the stage exists, and every plugin in the family was one.
    """

    DECL = DECL.replace(
        "        - {name: judgement, kind: judgement, fills: [summary, cannot_show]}",
        "        - name: legends\n"
        "          fills: [report.figures]\n"
        "          each_item_declares:\n"
        "            drawn_by: [tool, plugin]\n"
        "          why: who drew each panel\n"
        "        - {name: judgement, kind: judgement, fills: [summary, cannot_show]}")

    def setUp(self):
        from sch import yamlish
        self.doc = yamlish.loads(self.DECL)

    def _row(self, spec):
        return next(r for r in C.status(spec, self.doc, "widget") if r["stage"] == "legends")

    def test_a_list_that_exists_is_not_a_stage_that_is_done(self):
        spec = {"report": {"figures": [{"id": "F1", "drawn_by": "plugin"}, {"id": "F2"}]}}
        row = self._row(spec)
        self.assertFalse(row["done"])
        self.assertIn("1 of 2", row["partial"])
        self.assertIn("F2 (no drawn_by)", row["partial"])

    def test_every_entry_ruled_is_done(self):
        spec = {"report": {"figures": [{"id": "F1", "drawn_by": "plugin"},
                                       {"id": "F2", "drawn_by": "tool"}]}}
        self.assertTrue(self._row(spec)["done"])

    def test_a_value_outside_the_declared_set_is_not_a_ruling(self):
        """`drawn_by: yes` is a filled field and an unanswered question."""
        spec = {"report": {"figures": [{"id": "F1", "drawn_by": "yes"}]}}
        row = self._row(spec)
        self.assertFalse(row["done"])
        self.assertIn("expected one of tool, plugin", row["partial"])

    def test_an_absent_field_is_still_the_missing_answer_not_the_item_answer(self):
        """With no `report` at all the stage is TODO, not PARTIAL: there is nothing to rule on."""
        row = self._row({})
        self.assertFalse(row["done"])
        self.assertEqual(row["missing"], ["report.figures"])
        self.assertEqual(row["partial"], "")

    def test_the_harness_knows_none_of_these_names(self):
        """`report.figures`, `drawn_by`, `tool` and `plugin` all arrive from the declaration.

        Asserted on the two functions that do the work rather than on the module, because the
        module is not clean: see the test below.
        """
        import inspect
        src = inspect.getsource(C.item_gaps) + inspect.getsource(C.items_worksheet)
        for word in ("report.figures", "drawn_by", "plugin", "tool"):
            self.assertNotIn(f'"{word}"', src, f"{word!r} is one repository's vocabulary")

    def test_the_one_place_the_module_does_name_a_field_is_still_the_one_place(self):
        """A RATCHET OVER A KNOWN DEVIATION, not an endorsement of it. The module's own docstring
        says it "names no tool, no field and no plugin format", and `contract_in` names
        `report.figures` anyway - it buckets a scanned produce-call under scProfile's field name.
        That predates this stage and is a real leak of one format into the shared tool; the fix
        is for the point to declare the bucket, and it is not this change. What must not happen
        meanwhile is the leak spreading, so the count is pinned."""
        import inspect
        src = (ROOT / "sch" / "dev" / "convert.py").read_text()
        here = inspect.getsource(C.contract_in)
        self.assertEqual(src.count('"report.figures"'), here.count('"report.figures"'),
                         "a format's field name has spread beyond `contract_in`")

    def test_the_worksheet_names_the_plugins_own_question_beside_each_row(self):
        spec = {"report": {"figures": [{"id": "F1", "question": "does the field hold?"}]}}
        sheet = C.items_worksheet(spec, self.doc, "widget", "legends")
        self.assertIn("TO RULE  F1", sheet)
        self.assertIn("does the field hold?", sheet)
        self.assertIn("tool | plugin", sheet)

    def test_a_stage_that_rules_on_nothing_refuses_the_worksheet(self):
        with self.assertRaises(C.ConvertError):
            C.items_worksheet({}, self.doc, "widget", "contract")

    def test_the_stage_advances_like_any_other(self):
        self.assertIn("legends", C.ADVANCES)
        row = self._row({})
        cmd = C.advance_command(row, self.doc, "widget", ".", "w")
        self.assertIn("convert legends", cmd)


class EveryActionLoadsTheDeclarationsItReads(unittest.TestCase):
    """`legends` was added to the parser's choices and not to the list of actions that load the
    plugins, so the loop ran zero times and the command printed nothing and exited 0. A second
    place to register an action is a place to forget one; the list is now the exceptions."""

    def test_a_new_action_cannot_silently_read_no_plugins(self):
        src = (ROOT / "sch" / "cli.py").read_text()
        self.assertIn('if a.action not in ("measure",):', src)

    def test_legends_prints_something_for_a_real_repository(self):
        out = subprocess.run([sys.executable, "-m", "sch", "dev", "convert", "legends",
                              "--root", str(ROOT), "--point", "kernel"],
                             cwd=str(ROOT), capture_output=True, text=True)
        self.assertNotEqual(out.stdout.strip() + out.stderr.strip(), "",
                            "an action that reads declarations printed nothing at all")




class TheJobsCheckerRunsBeforeItIsSubmitted(unittest.TestCase):
    """A prediction is only as good as the thing grading it, and nothing was grading that.

    THREE TIMES IN ONE JOB. The SAMBO writing job carries its predictions as an embedded Python
    checker, and three separate defects in that checker reached the cluster: it counted only one
    of the two places a legend can live and reported 558 undescribed panels against 378 saying
    so; it searched for one module's phrasing of the aliasing caveat and called two pages that
    carry it silent; and it used a name that the section below it defined, which is fine until
    the file is read top to bottom, which is how it runs. Each cost a submission, and the first
    two produced confident FAIL lines about the tool that were about the checker.

    A wrong answer about a tool looks exactly like a right one. So the checker is extracted and
    RUN here, against a tiny synthetic tree shaped like a run, and every prediction has to
    evaluate. This does not check that the predictions are TRUE - only the cohort can say that -
    it checks that asking them does not raise.
    """

    JOB = ROOT / "jobs" / "writing_sambo.pbs"

    def _checker(self):
        lines = self.JOB.read_text().split("\n")
        i = next(n for n, l in enumerate(lines) if "PYCHK" in l and "<<" in l)
        j = next(n for n, l in enumerate(lines) if l.strip() == "PYCHK")
        return "\n".join(lines[i + 1:j])

    def test_the_job_and_its_checker_parse(self):
        import ast
        self.assertEqual(subprocess.run(["bash", "-n", str(self.JOB)]).returncode, 0)
        ast.parse(self._checker())

    def test_every_prediction_evaluates_on_a_tree_shaped_like_a_run(self):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        (d / "report").mkdir()
        figs = d / "kernels" / "k" / "u" / "figures"
        figs.mkdir(parents=True)
        (d / "report" / "p.html").write_text(
            "<h2>x</h2> nativecmp_a.png: NO LEGEND WAS WRITTEN for this panel. "
            "In this design <b>f1</b> varies together with machine across all samples. "
            "interactions from lo to hi")
        (figs / "nativecmp_a.png").write_bytes(b"x")
        (d / "kernels" / "k" / "WRITING_BRIEF.md").write_text("`f1` is aliased with `machine`")
        des = {}
        for i, (a, b) in enumerate([(a, b) for a in ("lo", "hi") for b in ("base", "alt")
                                    for _ in (0, 1)]):
            des[f"s{i}"] = {"f1": a, "f2": b, "machine": "m1" if a == "lo" else "m2"}
        (d / "report.json").write_text(json.dumps(
            {"design": des, "controls": {"f1": "lo", "f2": "base"},
             "kernels": {"k": {"figures": []}}}))

        tool = os.environ.get("SCH_TEST_TOOL", "")
        env = dict(os.environ, PANELS="1", LEGENDS="0", TOOL=tool)
        r = subprocess.run([sys.executable, "-", str(d)], input=self._checker(),
                           text=True, capture_output=True, env=env)
        if "cannot import the enumerator" in r.stdout:
            self.skipTest("the plugin format's own package is not importable here")
        self.assertNotIn("Traceback", r.stderr, f"the checker raised:\n{r.stderr[-600:]}")
        for tag in ("P0", "P1", "P2", "P3", "P4", "P5", "P6"):
            self.assertIn(f"  {tag}  ", r.stdout, f"{tag} did not evaluate:\n{r.stdout}")




class JobsDoNotDieOnAGrepThatFindsNothing(unittest.TestCase):
    """`set -euo pipefail` plus an unguarded command substitution is a silent early exit.

    THE DEFECT. A job's summary line was built with `line=$(grep -m1 ... | sed ...)`. Under
    `set -euo pipefail` a substitution whose pipeline fails takes the shell with it, and `grep`
    fails when it finds nothing - which is exactly the case that line existed to detect. So the
    first plugin whose tool could not be looked at ENDED THE JOB, after one line of output, with
    a seal that said `problems=3` and a summary file that was empty. The version before it had
    `|| echo 0` and the rewrite dropped the guard along with the command it was attached to.

    The rule is narrow on purpose: only `grep`, and only inside a substitution, because `awk`
    and `sed` return 0 on no match and are not the hazard.
    """

    JOBS = sorted((ROOT / "jobs").glob("*.pbs"))

    def test_every_job_uses_the_strict_shell(self):
        """The rule below only matters because they do."""
        for j in self.JOBS:
            self.assertIn("set -euo pipefail", j.read_text(), f"{j.name} is not strict")

    def test_no_apostrophe_inside_a_required_variable_message(self):
        """`${VAR:?the tool's own thing}` does not parse, and lies about where.

        Bash treats the apostrophe as opening a quote, so the error it reports names the END OF
        THE FILE rather than the line that caused it - once, sixty lines away from the mistake.
        This project has been bitten twice: `${VPY:?...velocity's environment...}` and then
        `${RSCRIPT:?...the environment's own Rscript...}`, months apart, by the same hand.
        """
        bad = []
        for j in self.JOBS:
            for n, line in enumerate(j.read_text().splitlines(), 1):
                for m in re.finditer(r"\$\{[A-Za-z_][A-Za-z0-9_]*:\?([^}]*)\}", line):
                    if "'" in m.group(1):
                        bad.append(f"{j.name}:{n}: {line.strip()[:88]}")
        self.assertEqual(bad, [], "an apostrophe in a `${VAR:?...}` message stops the job "
                                  "parsing, and the error points somewhere else:\n  "
                                  + "\n  ".join(bad))

    def test_no_grep_in_a_substitution_is_left_unguarded(self):
        bad = []
        for j in self.JOBS:
            text = j.read_text()
            # join continuations so a substitution split over two lines is seen whole
            joined = re.sub(r"\\\n\s*", " ", text)
            for m in re.finditer(r"\$\((?:[^()]|\([^()]*\))*\)", joined):
                frag = m.group(0)
                if re.search(r"\bgrep\b", frag) and "|| true" not in frag \
                        and "|| echo" not in frag:
                    line = joined[:m.start()].count("\n") + 1
                    bad.append(f"{j.name}:~{line}: {' '.join(frag.split())[:88]}")
        self.assertEqual(bad, [], "a grep that finds nothing will end these jobs:\n  "
                                  + "\n  ".join(bad))




class AnExtractorThatFailsSaysWhatFailed(unittest.TestCase):
    """`produced no answer: ` with nothing after the colon is not a diagnosis.

    MET ON A REAL MACHINE. The R extractor was pointed at an environment with CellChat and 219
    other R packages installed in it, and Rscript came back with both streams empty. The message
    interpolated `stderr or stdout`, so it rendered as the prefix and nothing - the least
    informative output possible for the one failure that most needs explaining. An R that writes
    an error and an R that cannot start at all are different problems, and the exit status is
    what separates them.
    """

    def _inv(self, script):
        from sch.dev.extract import r_namespace as RN
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        exe = d / "Rscript"
        exe.write_text(script)
        exe.chmod(0o755)
        return RN.inventory("SomePkg", rscript=str(exe))

    def test_a_silent_failure_names_the_exit_status_and_says_it_was_silent(self):
        inv = self._inv("#!/bin/sh\nexit 127\n")
        self.assertFalse(inv.complete)
        self.assertIn("exit 127", inv.why_not)
        self.assertIn("both stdout and stderr were empty", inv.why_not)

    def test_an_error_on_stderr_is_still_reported_verbatim(self):
        inv = self._inv("#!/bin/sh\necho 'cannot open shared object' >&2\nexit 1\n")
        self.assertFalse(inv.complete)
        self.assertIn("cannot open shared object", inv.why_not)

    def test_a_missing_namespace_is_its_own_answer_and_not_a_silent_one(self):
        """Distinct from both: R started, and said the package is not there."""
        inv = self._inv("#!/bin/sh\nprintf SCH_NO_NAMESPACE\n")
        self.assertFalse(inv.complete)
        self.assertIn("cannot load the namespace", inv.why_not)
        # it may well warn that an empty inventory would be misread - what it must not do is
        # report the SILENT failure, which is a different diagnosis
        self.assertNotIn("both stdout and stderr were empty", inv.why_not)
        self.assertNotIn("produced no answer", inv.why_not)

    def test_a_working_probe_still_returns_the_names(self):
        inv = self._inv("#!/bin/sh\nprintf 'SCH_OK\\nnetVisual_a\\nplotB\\n'\n")
        self.assertTrue(inv.complete)
        self.assertEqual(list(inv.names), ["netVisual_a", "plotB"])




class OnePluginAtATime(unittest.TestCase):
    """The held-out rule, enforced by the suite rather than trusted to whoever is converting.

    WHY IT IS A RULE AND NOT A HABIT. The actions that fill a declaration all put the wrapped
    tool's own surface in front of you. Run across a family at once they show every answer
    before any of them has been decided - and every change made to the MAKER afterwards is
    fitted to all of them at once, with nothing held back to show it generalises. The next
    unseen tool is then the first real test, and there is no evidence left to predict it.

    Measured, on this repository: nine plugins were inventoried in one submission, which made
    every extractor fix after it a fix against a corpus already read. The loop that does not do
    that is convert one, finish it, have a person check it, improve the maker from what that one
    taught, then start the next - where the next one is the test.

    `status` is deliberately exempt. It reads declarations and shows nobody an upstream, so it is
    the command that answers "where is everything" without spending the held-out set.
    """

    FILLS = ("inventory", "account", "defaults", "references", "contract", "legends", "build")

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.d, True)
        (self.d / "DEVPOINTS.yaml").write_text(DECL)
        (self.d / "widgets").mkdir()
        for nm in ("alpha", "beta"):
            (self.d / "widgets" / f"{nm}.py").write_text(
                'PLUGIN = {"wraps": {"tool": "json"}, "inject": "x"}\n')

    def _run(self, *args):
        return subprocess.run([sys.executable, "-m", "sch", "dev", "convert", *args,
                               "--root", str(self.d), "--point", "widget"],
                              cwd=str(ROOT), capture_output=True, text=True)

    def test_every_filling_action_refuses_a_whole_family(self):
        for action in self.FILLS:
            r = self._run(action)
            self.assertEqual(r.returncode, 3,
                             f"`convert {action}` without --name did not refuse: {r.stdout[:200]}")
            self.assertIn("name ONE with --name", r.stderr, action)
            self.assertIn("alpha, beta", r.stderr, f"{action} does not say which ones")

    def test_the_refusal_says_why_rather_than_just_no(self):
        r = self._run("account")
        for phrase in ("held back", "generalises", "the next one is the test"):
            self.assertIn(phrase.lower(), r.stderr.lower(), f"the refusal does not say {phrase!r}")

    def test_it_points_at_the_command_that_is_safe_to_run_across_everything(self):
        self.assertIn("convert status", self._run("account").stderr)

    def test_a_point_holding_one_artefact_is_not_refused(self):
        """No held-out set exists to spend, so the friction buys nothing. The first version of
        this rule refused it anyway and took seven of this suite's own tests with it."""
        (self.d / "widgets" / "beta.py").unlink()
        r = self._run("legends")
        self.assertNotEqual(r.returncode, 3, r.stderr[:300])

    def test_status_reads_the_whole_family_and_is_not_refused(self):
        r = self._run("status")
        self.assertEqual(r.returncode, 0, r.stderr[:300])
        for nm in ("alpha", "beta"):
            self.assertIn(nm, r.stdout)

    def test_naming_one_is_allowed(self):
        r = self._run("legends", "--name", "alpha")
        self.assertNotEqual(r.returncode, 3, r.stderr[:300])

    def test_build_is_covered_because_it_runs_the_others(self):
        """The widest door of all - it walks the build phase and executes every mechanical
        stage in it, so leaving it out would have left one open behind a closed one."""
        self.assertIn("build", self.FILLS)
        self.assertEqual(self._run("build").returncode, 3)




class TheWorksheetShowsBothHalvesOfARuling(unittest.TestCase):
    """A ruling needs the plugin's own panels and limits, not only the tool's surface.

    MEASURED ON ONE CONVERSION. liana's worksheet listed twelve of the wrapped tool's plotting
    functions with signatures and docstrings - good evidence, and only half of it. Eight of the
    twelve rulings turned on a single line of the plugin's own `cannot_show` saying the method
    has no spatial information, and `superseded_by_design` cannot be written at all without the
    id of the panel that supersedes. All of it was in the declaration this tool had already
    parsed, and whoever was ruling had to go and find it.

    WHICH FIELDS IS THE REPOSITORY'S TO SAY. `ruling_context:` names them; nothing here knows
    what a panel or a limit is called in any format.
    """

    DECL = DECL.replace('      upstream: wraps.tool',
                        '      upstream: wraps.tool\n'
                        '      ruling_context: [report.figures, cannot_show]')

    def setUp(self):
        from sch import yamlish
        self.doc = yamlish.loads(self.DECL)
        self.spec = {"report": {"figures": [
                         {"id": "F1", "question": "does the field hold?"},
                         {"id": "F2", "shows": "diagnostic"}]},
                     "cannot_show": ["it has no spatial information",
                                     "a rank is within this dataset"]}

    def test_it_names_the_panels_a_superseded_ruling_would_have_to_cite(self):
        out = C.ruling_context(self.spec, self.doc, "widget")
        self.assertIn("F1", out)
        self.assertIn("does the field hold?", out)
        self.assertIn("F2", out)

    def test_it_carries_the_limits_that_decide_a_not_applicable(self):
        self.assertIn("no spatial information", C.ruling_context(self.spec, self.doc, "widget"))

    def test_every_line_is_a_comment_so_the_block_can_be_pasted(self):
        for line in C.ruling_context(self.spec, self.doc, "widget").splitlines():
            self.assertTrue(line.startswith("#"), f"{line!r} would not survive a paste")

    def test_a_point_declaring_no_context_gets_none(self):
        from sch import yamlish
        plain = yamlish.loads(DECL)
        self.assertEqual(C.ruling_context(self.spec, plain, "widget"), "")

    def test_a_plugin_with_nothing_to_say_yet_produces_nothing(self):
        self.assertEqual(C.ruling_context({}, self.doc, "widget"), "")

    def test_the_harness_names_neither_field(self):
        import inspect
        src = inspect.getsource(C.ruling_context)
        for word in ("report.figures", "cannot_show", "native_plots"):
            self.assertNotIn(f'"{word}"', src, f"{word!r} is one repository's vocabulary")




class ADeadEndAnnouncesItself(unittest.TestCase):
    """A stage that reports what it owes and no way to pay it is a gap in the SUITE.

    `outstanding_if` gave the maker a way to say a stage is started-and-owing, and no way to say
    how the debt is paid. So a wrapper part-way through printed what it owed, forever, and
    nobody reading it could tell that no command in this suite can produce what the accounting
    demands.

    MEASURED, ON TWO PLUGINS. `superseded_by_design` must name a DEFECT; a defect needs the
    upstream's panel rendered beside the plugin's own; no stage renders one. liana and velocity
    both sit at PARTIAL for exactly that reason and neither said so - the maker printed the debt
    and stopped.

    A dead end that announces itself is a task. A silent one is a plugin nobody finishes.
    """

    def setUp(self):
        from sch import yamlish
        self.doc = yamlish.loads(DECL.replace(
            "        - {name: inventory, fills: [native_plots], why: what the tool already draws}",
            "        - name: inventory\n"
            "          fills: [native_plots]\n"
            "          outstanding_if: wraps.owed\n"
            "          why: what the tool already draws"))
        self.spec = {"native_plots": {"a": {"use": "x"}}, "wraps": {"owed": "two are unruled"}}

    def _rows(self):
        return C.status(self.spec, self.doc, "widget")

    def _text(self):
        return C.format_status(self._rows(), "w", "widget", doc=self.doc, root=".")

    def test_the_stage_is_partial_not_done(self):
        row = next(r for r in self._rows() if r["stage"] == "inventory")
        self.assertFalse(row["done"])
        self.assertIn("two are unruled", row["partial"])

    def test_a_partial_stage_with_no_declared_closer_says_the_suite_is_the_gap(self):
        out = self._text()
        self.assertIn("NOTHING DECLARES HOW TO FINISH THIS", out)
        self.assertIn("gap in the suite, not in the plugin", out)
        self.assertIn("finished_by", out)

    def test_where_something_can_do_the_work_it_is_named_instead(self):
        from sch import yamlish
        doc = yamlish.loads(DECL.replace(
            "        - {name: inventory, fills: [native_plots], why: what the tool already draws}",
            "        - name: inventory\n"
            "          fills: [native_plots]\n"
            "          outstanding_if: wraps.owed\n"
            "          finished_by: run the panels side by side and rule each\n"
            "          why: what the tool already draws"))
        out = C.format_status(C.status(self.spec, doc, "widget"), "w", "widget", doc=doc, root=".")
        self.assertIn("to finish it:  run the panels side by side", out)
        self.assertNotIn("NOTHING DECLARES HOW", out)

    def test_a_finished_stage_says_neither(self):
        spec = {"native_plots": {"a": {"use": "x"}}, "wraps": {}}
        out = C.format_status(C.status(spec, self.doc, "widget"), "w", "widget",
                              doc=self.doc, root=".")
        self.assertNotIn("NOTHING DECLARES HOW", out)
        self.assertNotIn("to finish it:", out)

    def test_the_harness_names_no_repository_field(self):
        import inspect
        src = inspect.getsource(C.format_status) + inspect.getsource(C.status)
        for word in ("native_plots", "wraps.owed", "superseded_by_design"):
            self.assertNotIn(f'"{word}"', src)


# -----------------------------------------------------------------------------------------------
# THE DRAW-SITE HALF. A conversion is not finished while the plugin still produces a panel and
# says nothing about it.
#
# MEASURED, AND THIS IS WHY THE CLASSES BELOW EXIST. A sealed run of this family: 711 panels, 69
# with a written legend, 642 without. The 642 come out of 35 call sites in ONE file, every one of
# them calling a wrapper that already HAS a legend parameter and passing nothing to it. Every
# check that existed counted the gap in the RUN'S OUTPUT - a number that names a directory of
# PNGs and not one line anybody can open - and no check anywhere looked at a draw site.
# -----------------------------------------------------------------------------------------------

#: A host package with TWO emit paths, reached two different ways, and a plugin that draws in
#: both languages. Written out rather than pointed at a real repository, for the reason every
#: other fixture here is: a test that reads scProfile passes or fails on scProfile's current
#: state.
#:
#: THE TWO ROUTES ARE THE POINT. One emit path is a METHOD, reached through the object a plugin
#: is handed; the other is a MODULE-LEVEL FUNCTION, reached through an import. Keyed on the
#: attribute name alone, `anything.write_panel(...)` in any plugin was a draw site - and a
#: synthetic plugin that saved a checkpoint and a table and drew nothing at all was reported as
#: two undescribed panels.
HOST = '''
class Context:
    """What a plugin is handed. Its emit path is reached through the instance."""

    def emit_figure(self, name, fig, *, caption="", source=None):
        """One of the host's two emit paths."""
        fig.savefig(name)


def write_panel(fig, out_dir, name, *, caption="", source=None):
    """The other, at module level - so a call to it comes through an import of this module."""
    fig.savefig(out_dir / name)
'''

#: EVERY R CALL IS ALONE ON ITS LINE WITH A BLANK LINE EITHER SIDE, and no two of them draw the
#: same panel. Stacked on consecutive lines, a uniform shift in the embedded-R line arithmetic
#: lands every site on another line that still holds the wrapper name - so an off-by-one that
#: made all of the reported line numbers wrong passed a test written to catch exactly that.
PLUGIN = '''
PLUGIN = {"api": 1}

_R = r"""
npng <- function(name, expr, w = 1800, h = 1500, res = 200, legend = "", by = "tool") {
  path <- file.path(figdir, paste0(name, ".png"))
  .legend(basename(path), legend, by)
  grDevices::png(path, width = w, height = h, res = res)
  print(expr)
  grDevices::dev.off()
}

helper <- function(x) { paste0("not a draw site: ", x) }

opener <- function(p) { grDevices::png(p); invisible(NULL) }

npng("silent_one", someTool_circle(cc))

npng("spoken_one", someTool_heatmap(cc), legend = "This one says what it shows and why.")

npng("prefixed", someTool_bubble(cc), leg = "Named by prefix, which R resolves.")

npng("positional", someTool_river(cc), 900, 900, 100, "Supplied without naming anything at all.")

npng(paste0("looped__", pw), someTool_aggregate(cc, signaling = pw))

kept <- npng("assigned_arrow", someTool_dot(cc))

kept2 = npng("assigned_equals", someTool_bar(cc))

npng("silent_five", someTool_violin(cc))

npng("silent_six", someTool_ridge(cc))

npng("silent_seven", someTool_tile(cc))

npng("silent_eight", someTool_rose(cc))

# npng("commented_out", someTool_nothing(cc))

message("npng(\\"in a string\\", nothing())")
"""


def run(ctx):
    ctx.emit_figure("F1", fig, caption="A described panel, five words at least.")
    ctx.emit_figure(
        "F2", fig,
        # A COMMENT LONG ENOUGH TO PUSH THE ARGUMENT OUT OF ANY WINDOW A LINE SCAN WOULD USE,
        # which is exactly the shape that made a grep report two described panels as silent.
        # Three more lines of it, so no plausible window reaches the keyword below.
        # Four.
        # Five.
        caption="Also described, and six lines below the parenthesis.")
    ctx.emit_figure("F3", fig)
    # NONE OF THE NEXT THREE IS A DRAW SITE. The host's `write_panel` is a module-level function
    # and none of these receivers is the module it lives in - they are other objects that happen
    # to have a method of the same name. The first two are the reviewer's demonstration verbatim.
    ctx.model.write_panel("checkpoint.pt")
    ctx.table.write_panel(ctx.out / "counts.parquet")
    ctx.table.write_panel(fig, ctx.out, "fits_the_signature_wrong_object")


def more(ctx, fig):
    from demopkg.plugin import write_panel
    from demopkg import plugin as hostmod
    write_panel(fig, ctx.out, "F4")
    hostmod.write_panel(fig, ctx.out, "F5", caption="Described, through the module alias.")
'''

DRAWDECL = """
tool: demopkg
devpoints: 1
points:
  widget:
    what: a widget
    lives: widgets
    proves: it runs
    cannot_prove: that it is right
    convert:
      placeholder: "TODO"
      upstream: wraps.tool
      stages:
        - {name: contract, fills: [inject]}
        - name: legends
          fills: [report.figures]
          each_item_declares:
            drawn_by: [tool, plugin]
          each_draw_site_describes: true
          finished_by: write the sentence at the call site
          why: who drew each panel
"""


class ADrawSiteIsFoundByWhatItDoes(unittest.TestCase):
    """Requiring a plugin to DECLARE its draw wrappers would mean editing every plugin in order
    to discover that they all need editing - which is the same reason eight of nine owed an
    accounting: the work was not skipped, there was no command that did it. So a draw wrapper is
    recognised by behaviour, in both of the languages a plugin here is written in."""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / "demopkg").mkdir()
        (self.d / "demopkg" / "__init__.py").write_text("")
        (self.d / "demopkg" / "plugin.py").write_text(HOST)
        (self.d / "widgets").mkdir()
        (self.d / "widgets" / "w.py").write_text(PLUGIN)
        (self.d / "DEVPOINTS.yaml").write_text(DRAWDECL)
        self.doc = P.load(self.d)
        self.inv = C.measure_draw_sites(self.doc, "widget", "w")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _by_panel(self):
        return {s["panel"]: s for s in DS.sites_of(self.inv)}

    def test_an_r_function_that_opens_a_device_and_closes_it_is_a_draw_wrapper(self):
        rtext = DS.embedded_r(PLUGIN)[0][0]
        self.assertEqual([w.name for w in DS.r_wrappers(rtext)], ["npng"])

    def test_a_function_that_only_pastes_a_string_is_not_one(self):
        """`helper` is defined right beside the wrapper and draws nothing. A scan keyed on "a
        function defined in the embedded R" would report every one of its calls as a panel."""
        rtext = DS.embedded_r(PLUGIN)[0][0]
        self.assertNotIn("helper", [w.name for w in DS.r_wrappers(rtext)])

    def test_a_function_that_opens_a_device_and_never_closes_it_is_not_one(self):
        """A preamble that opens a device is not a draw site, and treating it as one would file
        the whole script as one panel."""
        rtext = DS.embedded_r(PLUGIN)[0][0]
        self.assertNotIn("opener", [w.name for w in DS.r_wrappers(rtext)])

    def test_the_legend_parameter_is_read_off_the_signature(self):
        """NOT ASSUMED TO BE CALLED `legend`. It is `caption` on the Python side of the very
        repository this was built against, and neither name belongs in this suite."""
        rtext = DS.embedded_r(PLUGIN)[0][0]
        self.assertEqual(DS.r_wrappers(rtext)[0].legend, "legend")
        emits = DS.host_emits(self.d, "demopkg")
        self.assertEqual(emits.detail["emit_figure"]["legend"], "caption")

    def test_a_call_that_passes_nothing_is_silent_and_one_that_passes_something_is_not(self):
        got = self._by_panel()
        self.assertIs(got['"silent_one"']["has_legend"], False)
        self.assertIs(got['"spoken_one"']["has_legend"], True)

    def test_a_legend_named_by_prefix_is_not_reported_silent(self):
        """R matches argument names by prefix, so `leg =` fills `legend`. A scan looking only for
        the exact name would send somebody to write a legend that is already there."""
        self.assertIs(self._by_panel()['"prefixed"']["has_legend"], True)

    def test_a_legend_supplied_positionally_is_not_reported_silent(self):
        self.assertIs(self._by_panel()['"positional"']["has_legend"], True)

    def test_the_panel_name_is_reported_as_written_including_a_paste0(self):
        """35 sites produce ~642 panels because many of them are loops. A scan that could only
        report literal names would drop the sites that account for most of the debt."""
        self.assertIn('paste0("looped__", pw)', self._by_panel())

    def test_a_commented_out_call_is_not_a_draw_site(self):
        self.assertNotIn('"commented_out"', self._by_panel())

    def test_the_wrapper_name_inside_a_string_is_not_a_draw_site(self):
        self.assertNotIn('"in a string"', self._by_panel())

    def test_a_line_number_is_the_python_files_and_not_the_embedded_scripts(self):
        """"line 6 of the R" is a line number nobody can open. Checked against the file itself,
        so the arithmetic cannot drift from the thing it indexes.

        THE LINE'S CONTENT IS THIS SITE'S OWN PANEL, NOT JUST THE WRAPPER NAME. Asserting only
        that the wrapper appears there is satisfied by ANY line that calls the wrapper - and the
        embedded-R arithmetic fails as a UNIFORM SHIFT, which with the calls stacked on
        consecutive lines lands every site on another such line, the commented-out one included.
        A single `- 1` dropped from `embedded_r` made all of the reported line numbers wrong and
        this test passed. The panel name is unique per site, so a shift of any size fails."""
        lines = PLUGIN.splitlines()
        seen = 0
        for s in DS.sites_of(self.inv):
            if s["lang"] != "R":
                continue
            at = lines[s["line"] - 1]
            self.assertIn(s["wrapper"], at,
                          f"{s['panel']} reported at a line that does not hold its call")
            self.assertIn(s["panel"], at,
                          f"{s['panel']} reported at line {s['line']}, which holds {at.strip()!r}")
            seen += 1
        self.assertGreater(seen, 6, "too few R sites here to distinguish a shift from a match")

    def test_the_embedded_r_arithmetic_survives_a_literal_that_does_not_start_on_its_own_line(self):
        """The base line is derived from where the literal ENDS, so a literal that opens on the
        same line as the assignment and one that opens on the next must both land."""
        for opener in ('_R = r"""\n', '_R = r"""'):
            src = (opener + 'np <- function(n, e, legend = "") {\n'
                            '  grDevices::png(n); print(e); grDevices::dev.off()\n'
                            '}\n'
                            'np("only_one", thing())\n'
                            '"""\n')
            inv = DS.draw_sites("w", src, "w.py", None)
            site = DS.sites_of(inv)[0]
            self.assertIn('np("only_one"', src.splitlines()[site["line"] - 1])

    def test_the_python_emit_path_is_measured_and_not_named_here(self):
        """The repository says what its host package is called - `tool:` in its own
        DEVPOINTS.yaml - and the emit path is measured out of that package."""
        emits = DS.host_emits(self.d, "demopkg")
        self.assertTrue(emits.complete)
        self.assertEqual(emits.names, ["emit_figure", "write_panel"])
        src = _literals(ROOT / "sch" / "dev" / "extract" / "draw_sites.py")
        for word in ("emit_figure", "caption", "npng", "ndev", "scp_draw", "demopkg"):
            self.assertNotIn(word, src, f"{word!r} is somebody else's vocabulary")

    def test_a_multi_line_python_call_is_not_silent_because_the_argument_is_six_lines_down(self):
        """MEASURED, AND IT CHANGED THE ANSWER. A line-window scan of the nine shipped plugins
        reported two sites as passing no legend. Both pass one, six and seven lines below the
        opening parenthesis, behind a comment explaining what the legend had been getting wrong.
        A window scan invents debt in the plugins whose authors documented themselves best."""
        got = {s["panel"]: s for s in DS.sites_of(self.inv) if s["lang"] == "python"}
        self.assertIs(got["'F2'"]["has_legend"], True)
        self.assertIs(got["'F3'"]["has_legend"], False)

    def test_a_plugin_that_will_not_parse_is_not_a_plugin_with_no_draw_sites(self):
        inv = DS.draw_sites("broken", "def f(:\n", "broken.py", None)
        self.assertFalse(inv.complete)
        self.assertEqual(len(inv), 0)
        self.assertIn("will not parse", inv.why_not)

    def test_a_host_package_that_is_not_there_is_not_a_host_with_no_emit_path(self):
        inv = DS.host_emits(self.d, "nosuchpkg")
        self.assertFalse(inv.complete)
        self.assertIn("nosuchpkg", inv.why_not)


    def test_the_upstream_inventory_does_not_dispatch_to_a_plugin_source_reader(self):
        """`convert.inventory` asks every extractor that can look at an UPSTREAM PACKAGE. This
        one reads the plugin instead and takes different arguments; dispatched there it would be
        called with a package name and reported as an extractor that could not look at the
        wrapped tool - a false "could not look", which is the one answer this family protects."""
        self.assertIn(DS, extract.for_kind("plugin-source"))
        got = dict(C.inventory("nosuchpackage_xyz", python=sys.executable))
        self.assertNotIn("draw_sites", got)

    def test_the_command_prints_both_halves_of_the_stage(self):
        """The declared half rules on figures the plugin DECLARES; the measured half reads its
        source. A command that printed one of them would report a finished conversion with the
        other outstanding, which is the whole defect."""
        out = subprocess.run([sys.executable, "-m", "sch", "dev", "convert", "legends",
                              "--root", str(self.d), "--point", "widget", "--name", "w"],
                             cwd=str(ROOT), capture_output=True, text=True)
        self.assertIn("still to rule on", out.stdout)      # the DECLARED half
        self.assertIn("draw site(s) in w", out.stdout)     # the MEASURED half
        self.assertIn('"silent_one"', out.stdout)

    def test_a_wrapper_with_no_empty_default_leaves_its_sites_unknown_and_not_silent(self):
        """A wrapper whose legend is REQUIRED has no empty default to find. Reporting its calls
        as silent would manufacture a debt out of a wrapper that has no gap at all - so the third
        answer is UNKNOWN, for the same reason `complete=False` is a third answer next door."""
        src = ('_R = r"""\n'
               'draw2 <- function(p, expr, legend) {\n'
               '  grDevices::png(p); print(expr); grDevices::dev.off()\n'
               '}\n'
               'draw2("x", thing())\n'
               '"""\n')
        inv = DS.draw_sites("w2", src, "w2.py", None)
        self.assertEqual(len(DS.silent(inv)), 0)
        self.assertEqual(len(DS.unknown(inv)), 1)

    def test_two_calls_on_one_line_are_two_draw_sites(self):
        """ASSERTED ON THE SIDE OF THE OBJECT EVERY CONSUMER READS. `len(inv)` counts `names`,
        which is never de-duplicated; `sites_of`, `silent`, `unknown` and the debt all read
        `detail`, which is keyed on `file:line`. Removing the collision fix left `len(inv)` at 2
        and dropped a site out of the debt, and a test that asked the length saw nothing."""
        src = ('_R = r"""\n'
               'np <- function(n, e, legend = "") {\n'
               '  grDevices::png(n); print(e); grDevices::dev.off()\n'
               '}\n'
               'np("a", one()); np("b", two())\n'
               '"""\n')
        inv = DS.draw_sites("w3", src, "w3.py", None)
        self.assertEqual(len(DS.sites_of(inv)), 2,
                         "keyed on the line alone, the second overwrites the first")
        self.assertEqual([x["panel"] for x in DS.sites_of(inv)], ['"a"', '"b"'])
        self.assertEqual(len(DS.silent(inv)), 2)
        self.assertEqual(C.draw_debt(inv)["total"], 2)

    def test_a_draw_site_whose_result_is_assigned_is_still_a_draw_site(self):
        """AN R DEFINITION IS `name <- function(...)`, WHICH NEVER MATCHES `name(`. A guard in
        front of the call scan skipped anything preceded by `<-`, commented as "the definition,
        not a use" - it suppressed no definition anywhere, and what it did suppress was a panel
        drawn and kept in a variable. R's other assignment operator was unaffected, so one of
        the two spellings of the same site was counted and the other silently was not."""
        got = self._by_panel()
        self.assertIn('"assigned_arrow"', got, "a site whose result is kept is still a site")
        self.assertIs(got['"assigned_arrow"']["has_legend"], False)
        self.assertIs(got['"assigned_equals"']["has_legend"], False)

    def test_one_name_defined_twice_in_one_script_does_not_count_its_calls_twice(self):
        """R has no overloads: a second definition of a name replaces the first. Scanning both
        reports every call to it twice, which doubles the one number this extractor produces."""
        src = ('_R = r"""\n'
               'np <- function(n, e, legend = "") {\n'
               '  grDevices::png(n); print(e); grDevices::dev.off()\n'
               '}\n'
               'np <- function(n, e, legend = "") {\n'
               '  grDevices::pdf(n); print(e); grDevices::dev.off()\n'
               '}\n'
               'np("once", thing())\n'
               '"""\n')
        inv = DS.draw_sites("w4", src, "w4.py", None)
        self.assertEqual([x["panel"] for x in DS.sites_of(inv)], ['"once"'])

    def test_a_signature_with_two_empty_defaults_is_unknown_and_says_which_two(self):
        """WHICH ONE CARRIES THE LEGEND IS NOT SETTLED BY DECLARATION ORDER. Taking the first
        reported a DESCRIBED panel as silent - the call filled the other one - and the worksheet
        then printed the wrong argument to add. A disagreement between two DEFINITIONS is already
        reported; this is the same disagreement inside one signature and gets the same answer."""
        src = ('_R = r"""\n'
               'plate <- function(slug, expr, provenance = "", subtitle = "", w = 900) {\n'
               '  grDevices::png(slug, width = w); print(expr); grDevices::dev.off()\n'
               '}\n'
               'plate("p1", someThing(x), subtitle = "What this panel shows, and why it is here.")\n'
               '"""\n')
        inv = DS.draw_sites("w5", src, "w5.py", None)
        self.assertEqual(len(DS.silent(inv)), 0, "the call DID describe the panel")
        self.assertEqual(len(DS.unknown(inv)), 1)
        how = DS.unknown(inv)[0]["how"]
        self.assertIn("AMBIGUOUS", how)
        self.assertIn("provenance", how)
        self.assertIn("subtitle", how)
        self.assertEqual(DS.unknown(inv)[0]["legend_param"], "",
                         "naming one of them sends the reader to the wrong argument")

    def test_an_emit_path_reached_through_the_wrong_object_is_not_a_draw_site(self):
        """THE NAME ALONE IS NOT THE EMIT PATH. This host's module-level emit path is matched on
        the bare attribute name with no receiver check, so any `x.write_panel(...)` anywhere
        became a draw site - and a plugin that saves a checkpoint and a table and draws nothing
        was reported as two undescribed panels. That is debt manufactured out of a name, which
        is the failure UNKNOWN exists at the other end to avoid."""
        got = {(x["line"]) for x in DS.sites_of(self.inv) if x["lang"] == "python"}
        lines = PLUGIN.splitlines()
        for i, text in enumerate(lines, start=1):
            if "checkpoint.pt" in text or "counts.parquet" in text:
                self.assertNotIn(i, got, f"{text.strip()} is not a draw site")
        wrong = next(i for i, t in enumerate(lines, start=1)
                     if "fits_the_signature_wrong_object" in t)
        self.assertNotIn(wrong, got, "the signature fits; the object it is called on does not")

    def test_the_module_level_emit_path_is_found_when_it_is_actually_imported(self):
        """The receiver rule must not be a way of not looking. The same name, reached the way
        the host defines it - the name imported, and the module aliased - IS a draw site."""
        got = {s["line"]: s for s in DS.sites_of(self.inv) if s["lang"] == "python"}
        lines = PLUGIN.splitlines()
        bare = next(i for i, t in enumerate(lines, start=1) if t.strip().startswith("write_panel("))
        alias = next(i for i, t in enumerate(lines, start=1) if "hostmod.write_panel(" in t)
        self.assertIn(bare, got)
        self.assertIs(got[bare]["has_legend"], False)
        self.assertIn(alias, got)
        self.assertIs(got[alias]["has_legend"], True)

    def test_a_call_that_cannot_fit_the_measured_signature_is_not_that_function(self):
        """One positional argument cannot be a call to a function with three required
        parameters, whatever the attribute is called."""
        emits = DS.host_emits(self.d, "demopkg")
        src = ('PLUGIN = {"api": 1}\n'
               'from demopkg.plugin import write_panel\n'
               'def run(ctx):\n'
               '    write_panel(ctx.thing)\n')
        self.assertEqual(DS.sites_of(DS.draw_sites("w6", src, "w6.py", emits)), [])


class TheLegendsStageHoldsOpenWhileAPanelGoesOutUndescribed(unittest.TestCase):
    """A conversion that reported `legends` done with 35 silent draw sites in the file was
    telling the truth about the declaration and nothing about the plugin."""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / "demopkg").mkdir()
        (self.d / "demopkg" / "__init__.py").write_text("")
        (self.d / "demopkg" / "plugin.py").write_text(HOST)
        (self.d / "widgets").mkdir()
        (self.d / "widgets" / "w.py").write_text(PLUGIN)
        (self.d / "DEVPOINTS.yaml").write_text(DRAWDECL)
        self.doc = P.load(self.d)
        #: EVERY DECLARED ENTRY ALREADY RULED ON, so the only thing left is the measured half.
        self.spec = {"inject": {"a": 1},
                     "report": {"figures": [{"id": "F1", "drawn_by": "tool"},
                                            {"id": "F2", "drawn_by": "plugin"}]}}

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _row(self, name="w"):
        return next(r for r in C.status(self.spec, self.doc, "widget", name)
                    if r["stage"] == "legends")

    def test_a_silent_draw_site_is_not_a_finished_stage(self):
        row = self._row()
        self.assertFalse(row["done"])
        self.assertTrue(row["draws"]["silent"])

    def test_the_debt_is_not_routed_through_the_declared_list(self):
        """THE DESIGN CONSTRAINT, PAID FOR ONCE ALREADY. `item_gaps` walks a stage's `fills` and
        stops at the FIRST list-valued field, and `report.figures` is a non-empty list in all nine
        plugins - so a draw-site check hung behind it is unreachable and reports nothing, in
        silence, forever. Here every declared entry IS ruled on, `item_gaps` therefore has nothing
        to say, and the stage must still be open."""
        row = self._row()
        self.assertEqual(row["partial"], "", "the declared half is satisfied")
        self.assertFalse(row["done"], "and the measured half is not")

    def test_every_silent_site_is_named_and_not_a_leading_handful(self):
        """A count is a number nobody can act on. The whole value of this check is that a reader
        can open the lines, and truncating the list gives them the count back.

        THE FIXTURE HAS TO BE ABLE TO TELL THE DIFFERENCE. Named for this regression and given
        exactly three silent sites, this test passed with the list truncated to three: only a
        truncation to TWO failed it, so the one revert it exists to catch went straight through.
        It is the whole file:line that is looked for, because `:17` is inside `:170`."""
        out = C.format_status(C.status(self.spec, self.doc, "widget", "w"), "w", "widget")
        row = self._row()
        sil = row["draws"]["silent"]
        self.assertGreater(len(sil), 8, "too few silent sites here to see a truncation")
        for s in sil:
            self.assertIn(f"{s['file']}:{s['line']}", out)

    def test_a_truncated_list_says_how_many_it_did_not_name(self):
        """AND THAT LINE IS WHAT KEEPS A TRUNCATION FROM BEING SILENT. The cap and the "... and
        N more" line are two constants that have to agree: with the list cut to three and the
        test for more still reading the cap, thirty-two sites left the report with no trace at
        all. Checked WITH a truncation, which is the only state in which they can disagree."""
        row = self._row()
        sil = row["draws"]["silent"]
        L = C._draw_lines(row, limit=2)
        named = [x for x in sil if any(f"{x['file']}:{x['line']}" in line for line in L)]
        self.assertEqual(len(named), 2, "the cap is not the number of sites printed")
        self.assertIn(f"... and {len(sil) - 2} more", "\n".join(L))

    def test_a_stage_that_reports_this_debt_says_how_it_is_paid(self):
        out = C.format_status(C.status(self.spec, self.doc, "widget", "w"), "w", "widget")
        self.assertIn("to finish it:  write the sentence at the call site", out)

    def test_and_says_the_suite_is_the_gap_when_nothing_declares_a_closer(self):
        from sch import yamlish
        doc = yamlish.loads(DRAWDECL.replace(
            "          finished_by: write the sentence at the call site\n", ""))
        doc["_root"] = str(self.d)
        out = C.format_status(C.status(self.spec, doc, "widget", "w"), "w", "widget")
        self.assertIn("NOTHING DECLARES HOW TO FINISH THIS", out)

    def test_not_having_looked_is_not_the_same_as_nothing_to_do(self):
        """A status asked without naming a plugin has read no source. Reporting the stage done
        there would file "I did not look" as "there is nothing left"."""
        row = self._row(name="")
        self.assertFalse(row["done"])
        self.assertFalse(row["draws"]["looked"])
        out = C.format_status(C.status(self.spec, self.doc, "widget", ""), "w", "widget")
        self.assertIn("COULD NOT LOOK", out)

    def test_a_point_that_does_not_declare_this_is_unaffected(self):
        from sch import yamlish
        doc = yamlish.loads(DRAWDECL.replace("          each_draw_site_describes: true\n", ""))
        doc["_root"] = str(self.d)
        row = next(r for r in C.status(self.spec, doc, "widget", "w") if r["stage"] == "legends")
        self.assertTrue(row["done"])
        self.assertEqual(row["draws"], {})

    def test_the_worksheet_shows_the_call_and_the_argument_to_add(self):
        """A worksheet nobody can fill in from is a list of line numbers. Each row carries the
        panel name as written, what is being plotted, and the argument to add - and no sentence,
        because a legend generated from a function name is a label in the place a description
        goes and a reader believes it."""
        sheet = C.draw_worksheet(self.doc, "widget", "legends", "w")
        self.assertIn("TO WRITE", sheet)
        self.assertIn('"silent_one"', sheet)
        self.assertIn("someTool_circle", sheet)
        self.assertIn('legend = "..."', sheet)
        self.assertNotIn('"spoken_one"', sheet)

    def test_the_worksheet_refuses_a_stage_that_did_not_ask_for_it(self):
        with self.assertRaises(C.ConvertError):
            C.draw_worksheet(self.doc, "widget", "contract", "w")

    def test_the_worksheet_says_it_could_not_look_rather_than_showing_an_empty_one(self):
        sheet = C.draw_worksheet(self.doc, "widget", "legends", "nosuchwidget")
        self.assertIn("COULD NOT LOOK", sheet)
        self.assertNotIn("TO WRITE", sheet)

    def test_the_harness_names_no_wrapper_no_field_and_no_stage_of_any_repository(self):
        """The module's own docstring says it names no tool, no field and no plugin format. The
        stage is `legends` in ONE repository's declaration; the key is this suite's own."""
        for fn in (C.status, C.format_status, C._draw_lines, C.draw_worksheet,
                   C.measure_draw_sites, C.draw_debt):
            src = inspect.getsource(fn)
            for word in ("legends", "report.figures", "npng", "emit_figure", "caption",
                         "scprofile", "cellchat"):
                self.assertNotIn(f'"{word}"', src, f"{word!r} in {fn.__name__}")
                self.assertNotIn(f"'{word}'", src, f"{word!r} in {fn.__name__}")


class TheCommandsAPersonActuallyRunsCarryTheMeasuredHalf(unittest.TestCase):
    """THE MEASUREMENT WAS RATCHETED AND ITS TWO ENTRY POINTS WERE NOT.

    `status` is the first command anybody types and `build` is the one that walks the whole
    phase, and neither was run by any test: only `legends` was. So dropping the plugin's name in
    the CLI's call to `status` - degrading every plugin to "COULD NOT LOOK at this plugin's draw
    sites" - was green, and so was a `draw_summary` that returned "" for every debt, which lets
    the driver walk straight past a stage with ten undescribed panels in it and run the rest of
    the build behind it.
    """

    #: EVERY DECLARED ENTRY RULED ON, so nothing but the measured half can hold the stage open -
    #: which is what makes the driver's walk-past visible here and nowhere else.
    SPEC = {"inject": {"a": 1},
            "report": {"figures": [{"id": "F1", "drawn_by": "tool"},
                                   {"id": "F2", "drawn_by": "plugin"}]}}

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / "demopkg").mkdir()
        (self.d / "demopkg" / "__init__.py").write_text("")
        (self.d / "demopkg" / "plugin.py").write_text(HOST)
        (self.d / "widgets").mkdir()
        (self.d / "widgets" / "w.py").write_text(
            PLUGIN.replace('PLUGIN = {"api": 1}', "PLUGIN = " + repr(self.SPEC)))
        (self.d / "DEVPOINTS.yaml").write_text(DRAWDECL)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _run(self, action):
        return subprocess.run([sys.executable, "-m", "sch", "dev", "convert", action,
                               "--root", str(self.d), "--point", "widget"],
                              capture_output=True, text=True, cwd=str(ROOT))

    def _silent(self):
        doc = P.load(self.d)
        return C.draw_debt(C.measure_draw_sites(doc, "widget", "w"))["silent"]

    def test_status_through_the_cli_looks_at_the_plugins_draw_sites(self):
        """The name has to reach `status`, and only this command can tell whether it did. Without
        it the answer is honest and useless - "could not look" for every plugin, on the one
        command a person types first."""
        out = self._run("status")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertNotIn("COULD NOT LOOK", out.stdout)
        sil = self._silent()
        self.assertGreater(len(sil), 8)
        for site in sil:
            self.assertIn(f"{site['file']}:{site['line']}", out.stdout)

    def test_the_driver_stops_at_a_debt_measured_from_the_source(self):
        """`partial` is what a plugin admits about itself; this is what its source says whether it
        admits it or not. A driver that walked past it would run every later stage and report a
        build with ten undescribed panels in it as finished."""
        out = self._run("build")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("STOP at legends", out.stdout)
        self.assertIn("started, and the source says what is left", out.stdout)
        self.assertIn(f"{len(self._silent())} of ", out.stdout)
        self.assertNotIn("--- legends", out.stdout,
                         "it printed the stop and then ran the stage anyway")

    def test_the_driver_runs_nothing_after_the_stage_it_stopped_at(self):
        out = self._run("build").stdout
        after = out.split("STOP at legends")[1]
        self.assertNotIn("---", after, "a stage ran behind the stop")


SLOTS = '''
"""A plugin does not open with its R. These lines exist so the embedded literal starts at a
line number that is not zero - without them `base` is 0 and the line arithmetic below cannot
be told from no arithmetic at all."""
import os

NAME = "widget"


_R = """
npng <- function(name, expr, w = 1800, h = 1400, legend = "") {
  png(file.path(out, paste0(name, ".png")), width = w, height = h); print(expr); dev.off()
}

# THE DEFECT. R parses this; it fails only when the call is evaluated.
npng("broken", plot(m), legend = paste0("a comparison of ", name_a,, " against ", name_b))

# LEGITIMATE, and textually identical to a reader that is not counting brackets.
.cr <- .fc[startsWith(.fc$k, "colour:"), , drop = FALSE]
row <- frame[i, ]
col <- frame[, j]

# LEGITIMATE: the slot is named, not empty - `a` falls through to `b`.
label <- switch(kind, a =, b = "shared", "other")

# LEGITIMATE: a call with no arguments at all has no missing one.
now <- Sys.time()

# A STRING IS AN ARGUMENT THAT IS THERE.
cat("database:", nrow(d), "interactions,", "genes")
"""
'''


class EmptyArgumentSlots(unittest.TestCase):
    """A legend the maker placed that R can parse and cannot run.

    Found by a run, not by a check: eighteen units drew all their panels, the plugin selftested
    ok, and all six arm-pair comparisons then died on `paste0(..., name_a,, ...)` at a draw site
    only the compare phase reaches.
    """

    def test_an_empty_argument_slot_in_a_call_is_found(self):
        hits = DS.empty_argument_slots(SLOTS)
        self.assertEqual(len(hits), 1, f"expected the one defect, got {hits}")
        self.assertIn("name_a,,", hits[0][1])

    def test_an_empty_index_slot_is_not_a_defect(self):
        """`x[cond, , drop = FALSE]` is how a data frame is kept from collapsing to a vector, and
        `frame[i, ]` is a whole row. Only the delimiter that opened the list tells these from the
        defect - the regex written first reported four of them in one real plugin."""
        for legit in ("drop = FALSE", "frame[i,", "frame[,"):
            self.assertFalse([h for h in DS.empty_argument_slots(SLOTS) if legit in h[1]],
                             f"indexing reported as a missing argument: {legit}")

    def test_a_named_slot_left_valueless_is_not_an_empty_one(self):
        """`switch(kind, a =, b = "shared")` is the documented way to make a branch fall
        through. The text between the commas is `a =`, which is not nothing."""
        self.assertFalse([h for h in DS.empty_argument_slots(SLOTS) if "switch" in h[1]])

    def test_a_string_argument_is_an_argument_that_is_there(self):
        """The scan reads structure off a mask and EMPTINESS off the text. Reading both off a
        mask that blanks strings reported 742 defects in a plugin that has one."""
        self.assertFalse([h for h in DS.empty_argument_slots(SLOTS) if "database" in h[1]])

    def test_a_call_with_no_arguments_has_no_missing_one(self):
        self.assertFalse([h for h in DS.empty_argument_slots(SLOTS) if "Sys.time" in h[1]])

    def test_a_trailing_comma_before_the_bracket_is_an_empty_slot(self):
        """R has no trailing-comma grace: `paste0("a", )` is a missing argument. Python allows
        it, which is exactly why a check written against Python habits would pass this."""
        src = 'x = """\n.f <- function(a, b = "") { png(a); print(b); dev.off() }\n.f("p", legend = paste0("one", ))\n"""\n'
        hits = DS.empty_argument_slots(src)
        self.assertEqual(len(hits), 1, f"a trailing comma is a missing argument in R: {hits}")

    def test_the_line_reported_is_the_python_files_line(self):
        """A defect reported at "line 9 of the R" is a line nobody can open."""
        ln = DS.empty_argument_slots(SLOTS)[0][0]
        self.assertTrue(SLOTS.splitlines()[ln - 1].strip().startswith('npng("broken"'),
                        f"reported line {ln}, which holds {SLOTS.splitlines()[ln - 1]!r}")



if __name__ == "__main__":
    unittest.main()
