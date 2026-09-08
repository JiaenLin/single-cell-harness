"""The conversion pipeline: reading a foreign codebase, and resuming a half-built plugin.

WHAT THIS IS FOR. Eight of scProfile's nine plugins owe an accounting of the figures their wrapped
tool already draws. Not because the work was skipped - because the only inventory extractor this
family had was four lines of R inside `kernels/cellchat.py`, hardcoded to one package's naming
convention and reachable by nothing else. `scprofile/native.py`, the half that CONSUMES an
inventory, has been domain-free and shipped the whole time.
"""
from __future__ import annotations

import json
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
        from sch.dev.extract import python_package as PP
        inv = PP.inventory("matplotlib.pyplot")
        self.assertTrue(inv.complete, inv.why_not)
        self.assertIn("plot", inv.names)
        self.assertTrue(inv.how, "an inventory nobody can argue with is one nobody reads")

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
        self.assertIn("next: inventory", p.stdout)

    def test_an_inventory_nobody_could_take_fails_rather_than_recording_zero(self):
        p = self._run("inventory")
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertIn("NO EXTRACTOR COULD LOOK", p.stdout)


class Worksheet(unittest.TestCase):
    """The inventory turned into a decision a maintainer can make without looking anything up."""

    def test_every_exported_function_appears(self):
        w = C.worksheet("scanpy", ["pl.umap", "pl.dotplot"], {}, "TODO")
        self.assertIn("'pl.umap'", w)
        self.assertIn("'pl.dotplot'", w)

    def test_what_is_already_decided_is_carried_through_unchanged(self):
        """RE-RUNNABLE AFTER A VERSION BUMP, and the answer is the diff. A worksheet that reset
        every decision would be a worksheet nobody runs twice."""
        w = C.worksheet("t", ["a", "b"], {"a": {"use": "figures/a.png"}}, "TODO")
        self.assertIn("'a': {'use': 'figures/a.png'}", w)
        self.assertIn("TODO", w.split("'b'", 1)[1][:80])
        self.assertNotIn("TODO", w.split("'b'", 1)[0])

    def test_an_undecided_entry_is_a_placeholder_so_it_cannot_pass_as_finished(self):
        w = C.worksheet("t", ["a"], {}, "TODO")
        self.assertIn("TODO", w)

    def test_the_three_valid_skips_are_offered_and_the_rejected_ones_named(self):
        """The vocabulary is `scprofile/native.py`'s and this must not invent a fourth reason."""
        w = C.worksheet("t", ["a"], {}, "TODO")
        for reason in ("not_applicable", "superseded_by_design", "duplicate_of"):
            self.assertIn(reason, w)
        self.assertIn("reimplemented", w)

    def test_a_declaration_the_upstream_no_longer_exports_is_reported(self):
        """Both causes matter - the tool dropped it, or the inventory pattern stopped matching -
        and neither is fixed by deleting the line."""
        w = C.worksheet("t", ["a"], {"gone": {"use": "x"}}, "TODO")
        self.assertIn("NO LONGER EXPORTED", w)
        self.assertIn("gone", w)

    def test_it_counts_what_is_left(self):
        w = C.worksheet("t", ["a", "b", "c"], {"a": {"use": "x"}}, "TODO")
        self.assertIn("3 function(s)", w)
        self.assertIn("1 already decided, 2 to rule on", w)


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
            'PLUGIN = {"wraps": {"tool": "matplotlib.pyplot"}, "inject": {"required": ["x"]}}\n')

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _run(self, action):
        return subprocess.run([sys.executable, "-m", "sch", "dev", "convert", action,
                               "--root", str(self.d), "--point", "widget"],
                              capture_output=True, text=True, cwd=ROOT)

    def test_each_action_produces_its_own_output(self):
        seen = {a: self._run(a).stdout for a in ("status", "inventory", "account")}
        self.assertIn("stage(s) complete", seen["status"])
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
