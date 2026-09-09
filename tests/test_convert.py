"""The conversion pipeline: reading a foreign codebase, and resuming a half-built plugin.

WHAT THIS IS FOR. Eight of scProfile's nine plugins owe an accounting of the figures their wrapped
tool already draws. Not because the work was skipped - because the only inventory extractor this
family had was four lines of R inside `kernels/cellchat.py`, hardcoded to one package's naming
convention and reachable by nothing else. `scprofile/native.py`, the half that CONSUMES an
inventory, has been domain-free and shipped the whole time.
"""
from __future__ import annotations

import contextlib
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
        self.assertEqual({m.EXTRACT["reads"] for m in got.values()},
                         {"python-package", "r-package"})

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
        bad = []
        for f in self.JOBS:
            for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                s = line.strip()
                if s.startswith("#"):
                    continue
                if re.search(r'^echo\s+.*\$\?', s):
                    bad.append(f"{f.name}:{i}: {s}")
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
