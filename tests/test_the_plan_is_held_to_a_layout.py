"""The figure plan is held to a layout the maker declares, and the maker trims it (ADR-0024).

945 figures a run from 58 entries was the cellchat arc's floor: every entry drawn for every
unit, contrast and the cohort, with no budget anywhere. The layout is one declaration in the
tool's DEVPOINTS - axes, a budget per axis, what to keep first, what to drop first - and
`sch dev convert layout` holds a plugin's plan to it: it refuses a plan over budget, naming the
axis and the entries, and `--apply` trims the plan in the plugin's own file, so that nobody
hand-edits a plugin to make it smaller.

Run: PYTHONPATH=. python3 tests/test_the_plan_is_held_to_a_layout.py
"""
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sch.dev import layout as L                                                  # noqa: E402

LAYOUT = {
    "axes": {
        "sample": {"budget": 2, "keep": ["unit_presence", "circle"]},
        "group": {"budget": 3, "keep": ["circle", "matrix", "role_scatter"]},
        "contrast": {"budget": 3, "keep": ["diff_matrix", "flow_compare", "chord"]},
        "interaction": {"budget": 2, "keep": ["interaction"]},
        "cohort": {"budget": 1, "keep": ["unit_totals"]},
    },
    "prefer": ["tool", "plugin"],
    "drop_first": ["appendix", "conclusion", "contrast", "overview"],
}
KEYS = {"upstream": "fn", "bound": "at_most", "axis": "axis", "position": "position",
        "skips": "report.skips"}

PLUGIN = textwrap.dedent('''\
    PLUGIN = {
        "name": "demo",
        "report": {
            "figures": [
                {'id': 'native_circle', 'kind': 'circle', 'drawn_by': 'tool', 'fn': 'drawCircle',
                 'axis': 'unit', 'position': 'contrast', 'legend': 'a circle'},
                {'id': 'native_matrix', 'kind': 'matrix', 'drawn_by': 'tool', 'fn': 'drawMatrix',
                 'axis': 'unit', 'position': 'contrast', 'legend': 'a matrix'},
                {'id': 'native_roles', 'kind': 'role_scatter', 'drawn_by': 'tool', 'fn': 'drawRoles',
                 'axis': 'unit', 'position': 'contrast', 'legend': 'roles'},
                {'id': 'native_patterns', 'kind': 'patterns', 'drawn_by': 'tool', 'fn': 'drawPatterns',
                 'axis': 'unit', 'position': 'appendix', 'at_most': 2,
                 'items': 'c("in", "out")', 'legend': 'patterns'},
                {'id': 'F2_presence', 'kind': 'unit_presence', 'drawn_by': 'plugin',
                 'axis': 'unit', 'position': 'appendix', 'legend': 'who is present'},
                {'id': 'F5_dotplot', 'kind': 'other', 'drawn_by': 'plugin',
                 'axis': 'unit', 'position': 'appendix', 'legend': 'a dotplot'},
                {'id': 'nativecmp_diff', 'kind': 'diff_matrix', 'drawn_by': 'tool', 'fn': 'drawDiff',
                 'axis': 'contrast', 'position': 'contrast', 'at_most': 1, 'legend': 'the difference'},
                {'id': 'nativecmp_chord', 'kind': 'chord', 'drawn_by': 'tool', 'fn': 'drawChord',
                 'axis': 'contrast', 'position': 'appendix', 'at_most': 8, 'legend': 'chords'},
                {'id': 'nativecmp_rank', 'kind': 'flow_compare', 'drawn_by': 'tool', 'fn': 'drawRank',
                 'axis': 'contrast', 'position': 'contrast', 'at_most': 1, 'legend': 'ranks'},
                {'id': 'nativecmp_bubble', 'kind': 'other', 'drawn_by': 'tool', 'fn': 'drawBubble',
                 'axis': 'contrast', 'position': 'contrast', 'legend': 'bubbles'},
                {'id': 'nativecmp_flow', 'kind': 'interaction', 'drawn_by': 'plugin',
                 'axis': 'cohort', 'position': 'conclusion', 'at_most': 2, 'legend': 'flow'},
                {'id': 'nativecmp_lr', 'kind': 'interaction', 'drawn_by': 'plugin',
                 'axis': 'cohort', 'position': 'conclusion', 'at_most': 2, 'legend': 'lr'},
                {'id': 'nativecmp_totals', 'kind': 'unit_totals', 'drawn_by': 'tool', 'fn': 'drawTotals',
                 'axis': 'cohort', 'position': 'overview', 'at_most': 2, 'items': 'c("a", "b")',
                 'legend': 'totals'},
            ],
            "skips": {
                'drawSpatial': {'skip': 'not_applicable', 'evidence': 'no coordinates'},
            },
        },
    }


    def run(ctx):
        pass
    ''')


def spec_of(text):
    ns = {}
    exec(text, ns)                                                           # noqa: S102
    return ns["PLUGIN"]


class ThePlanIsHeldToALayout(unittest.TestCase):

    def test_the_check_counts_files_per_axis_occurrence_and_names_what_is_over(self):
        rep = L.check(spec_of(PLUGIN), LAYOUT, KEYS)
        self.assertEqual(rep["counts"]["sample"], 7, rep)      # 6 unit entries, patterns at 2
        self.assertEqual(rep["counts"]["group"], 7, rep)
        self.assertEqual(rep["counts"]["contrast"], 11, rep)   # 1 + 8 + 1 + 1
        self.assertEqual(rep["counts"]["interaction"], 4, rep)
        self.assertEqual(rep["counts"]["cohort"], 2, rep)
        self.assertEqual(sorted(rep["over"]), ["cohort", "contrast", "group", "interaction", "sample"])
        self.assertFalse(rep["ok"])

    def test_the_trim_keeps_what_the_layout_names_first_and_drops_the_rest(self):
        plan = L.trim(spec_of(PLUGIN), LAYOUT, KEYS)
        kept = {e["id"]: e for e in plan["kept"]}
        # sample: presence and circle; group: circle, matrix, roles -> circle on both axes.
        self.assertEqual(kept["native_circle"]["axis"], "unit")
        self.assertEqual(kept["F2_presence"]["axis"], "sample")
        self.assertEqual(kept["native_matrix"]["axis"], "group")
        self.assertEqual(kept["native_roles"]["axis"], "group")
        self.assertNotIn("native_patterns", kept)
        self.assertNotIn("F5_dotplot", kept)
        # contrast: diff (1) + rank (1) + chord lowered to fit the remaining 1
        self.assertEqual(kept["nativecmp_chord"]["at_most"], 1)
        self.assertNotIn("nativecmp_bubble", kept)
        # interaction: two families at 2 each against 2 -> one file of each, two views
        self.assertEqual(kept["nativecmp_flow"]["axis"], "interaction")
        self.assertEqual(kept["nativecmp_flow"]["at_most"], 1)
        self.assertEqual(kept["nativecmp_lr"]["at_most"], 1)
        # cohort: totals lowered to 1
        self.assertEqual(kept["nativecmp_totals"]["at_most"], 1)
        dropped = {d["id"]: d for d in plan["dropped"]}
        self.assertEqual(dropped["native_patterns"]["axis"], "sample")
        self.assertIn("over_budget", dropped["native_patterns"]["why"])
        # and the trimmed plan is under budget
        rep = L.check({"report": {"figures": plan["kept"]}}, LAYOUT, KEYS)
        self.assertTrue(rep["ok"], rep)

    def test_apply_rewrites_the_plugin_file_and_the_check_then_holds(self):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "demo.py"
            f.write_text(PLUGIN, encoding="utf-8")
            report = L.apply(f, LAYOUT, KEYS)
            text = f.read_text(encoding="utf-8")
            spec = spec_of(text)
            ids = [e["id"] for e in spec["report"]["figures"]]
            self.assertNotIn("native_patterns", ids)
            self.assertNotIn("nativecmp_bubble", ids)
            self.assertIn("native_circle", ids)
            # a dropped tool entry is accounted for in skips, with the reason and the budget
            self.assertEqual(spec["report"]["skips"]["drawPatterns"]["skip"], "over_budget")
            self.assertEqual(spec["report"]["skips"]["drawBubble"]["axis"], "contrast")
            # the plugin's own dropped panel is not an upstream export and takes no skip
            self.assertNotIn("F5_dotplot", spec["report"]["skips"])
            self.assertTrue(L.check(spec, LAYOUT, KEYS)["ok"])
            self.assertIn("native_patterns", report["dropped_ids"])
            # the comment trail and the untouched skip survive
            self.assertIn("drawSpatial", text)
            self.assertIn("def run(ctx)", text)

    def test_apply_also_clears_the_draw_sites_the_skips_and_the_version(self):
        """What the gate found on the first trim of cellchat: two dropped entries shared one
        upstream function and the skips carried it twice; the plugin's R protocol still called
        `.draw("<id>")` for dropped entries, so every suite that holds the draw sites to the plan
        refused; the profile marks named entries that were gone; and `version`, the reuse key,
        had not moved for an artefact that draws differently. The verb does all four."""
        text = PLUGIN.replace('    "name": "demo",', '    "name": "demo",\n    "version": "0.3.0",')
        text = text.replace("'id': 'native_circle', 'kind': 'circle'",
                            "'id': 'native_circle', 'profile': True, 'kind': 'circle'")
        text = text.replace("'id': 'native_patterns', 'kind': 'patterns'",
                            "'id': 'native_patterns', 'profile': True, 'kind': 'patterns'")
        text = text.replace("'fn': 'drawDiff'", "'fn': 'drawBubble'")
        text += "\n_PROFILE_PLOTS = ('patterns', 'roles')\n"
        text += ('\n_R = r"""\n.figures(prefix = "native_")\n.draw("native_circle")\n'
                 '.draw("native_patterns")\n  .draw("nativecmp_bubble")\n.draw("nativecmp_diff")\n'
                 'cat("done")\n"""\n')
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "demo.py"
            f.write_text(text, encoding="utf-8")
            rep = L.apply(f, LAYOUT, dict(KEYS, version="version", profile_list="_PROFILE_PLOTS"))
            out = f.read_text(encoding="utf-8")
            spec = spec_of(out)
            skips = spec["report"]["skips"]
            # drawBubble is still called by the kept nativecmp_diff, so it takes no skip;
            # drawPatterns is dropped once even though two axes dropped it
            self.assertNotIn("drawBubble", skips)
            self.assertEqual(skips["drawPatterns"]["skip"], "over_budget")
            self.assertEqual(out.count("'drawPatterns': {'skip'"), 1)
            self.assertNotIn('.draw("native_patterns")', out)
            self.assertNotIn('.draw("nativecmp_bubble")', out)
            self.assertIn('.draw("native_circle")', out)
            self.assertIn('.draw("nativecmp_diff")', out)
            self.assertEqual(spec["version"], "0.4.0")
            self.assertEqual(rep["version"], ("0.3.0", "0.4.0"))
            kept = {e["id"]: e for e in spec["report"]["figures"]}
            self.assertTrue(kept["native_circle"].get("profile"))
            self.assertTrue(kept["F2_presence"].get("profile"),
                            "a kept sample-axis entry is the profile")
            self.assertFalse(kept["native_matrix"].get("profile"))
            # the R guard's list names the tool's own plots of the profile, by stem, and not the
            # plugin's Python panel, which no R function draws
            self.assertIn("_PROFILE_PLOTS = ('circle',)", out)

    def test_a_plugin_under_budget_is_left_alone(self):
        small = {"report": {"figures": [
            {"id": "a", "kind": "circle", "drawn_by": "tool", "fn": "f", "axis": "unit",
             "position": "contrast"}]}}
        rep = L.check(small, LAYOUT, KEYS)
        self.assertTrue(rep["ok"])
        plan = L.trim(small, LAYOUT, KEYS)
        self.assertEqual(plan["dropped"], [])

    def test_the_verb_is_reachable_and_refuses_the_current_cellchat_plan(self):
        """The stage is declared in the tool's DEVPOINTS and reachable as a maker verb."""
        tool = Path.home() / "tools" / "scProfile"
        if not (tool / "DEVPOINTS.yaml").is_file():
            self.skipTest("the tool's repository is not beside this one")
        p = subprocess.run([sys.executable, "-m", "sch", "dev", "convert", "layout", "--root",
                            str(tool), "--point", "kernel", "--name", "cellchat"],
                           capture_output=True, text=True, cwd=ROOT)
        self.assertIn("budget", p.stdout + p.stderr)
        self.assertNotIn("invalid choice", p.stderr)


if __name__ == "__main__":
    unittest.main()
