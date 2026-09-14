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
        text = text.replace("'id': 'native_roles', 'kind': 'role_scatter'",
                            "'id': 'native_roles', 'profile': True, 'kind': 'role_scatter'")
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
            # an entry kept on the group axis alone loses the mark and leaves the list
            self.assertFalse(kept["native_roles"].get("profile"))

    def test_a_side_effect_entry_is_neither_counted_nor_dropped(self):
        """`generated: False` marks a file the tool writes as a side effect of a call the method
        makes - an accounting entry, not a plate. The first trim of cellchat dropped one (its
        NMF rank estimation), the call still ran, and `capacity --promised` refused the run on
        24 files accounted for by nothing (PBS 711438)."""
        keys = dict(KEYS, side_effect="generated")
        spec = spec_of(PLUGIN)
        spec["report"]["figures"].append(
            {"id": "estimation", "kind": "other", "drawn_by": "tool", "fn": "cluster",
             "axis": "unit", "position": "appendix", "at_most": 2, "generated": False})
        rep = L.check(spec, LAYOUT, keys)
        self.assertEqual(rep["counts"]["sample"], 7, rep)       # unchanged by the side effect
        plan = L.trim(spec, LAYOUT, keys)
        self.assertIn("estimation", {e["id"] for e in plan["kept"]})
        self.assertNotIn("estimation", {d["id"] for d in plan["dropped"]})
        # and without the key it is a plate like any other, as before
        rep2 = L.check(spec, LAYOUT, KEYS)
        self.assertEqual(rep2["counts"]["sample"], 9, rep2)
        # applied, it is neither marked as the profile nor listed among the profile's plots
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "demo.py"
            entry = ("            {'id': 'estimation', 'kind': 'other', 'drawn_by': 'tool', "
                     "'fn': 'cluster',\n             'axis': 'unit', 'position': 'appendix', "
                     "'at_most': 2, 'generated': False},\n")
            close = '        ],\n        "skips": {'
            self.assertIn(close, PLUGIN)
            f.write_text(PLUGIN.replace(close, entry + close) + "\n_PROFILE_PLOTS = ('circle',)\n",
                         encoding="utf-8")
            L.apply(f, LAYOUT, dict(keys, profile_list="_PROFILE_PLOTS"))
            text = f.read_text()
            after = L.read_spec(f)
            est = next(e for e in after["report"]["figures"] if e["id"] == "estimation")
            self.assertFalse(est.get("profile"), est)
            self.assertNotIn("estimation", text.split("_PROFILE_PLOTS")[-1])

    def test_the_hosts_panels_count_inside_the_budgets_and_the_list_is_written(self):
        """The host draws panels of its own beside the plan's - three per contrast, seven per
        arm, the cohort's census and totals, the interaction, the design grid: 84 files on a
        2x2 cohort - and the reader's budget is per axis whoever drew the file. The layout
        names the host's kinds and their axis (`host`), which of them a reader is handed
        (`host_keep`), and where the plugin carries the decision (`host_list`)."""
        lay = dict(LAYOUT, axes=dict(LAYOUT["axes"], cohort={"budget": 3, "keep": ["unit_totals"]}),
                   host={
            "across_design": {"axis": "cohort"}, "unit_presence": {"axis": "cohort"},
            "unit_totals": {"axis": "cohort"}, "diff_matrix": {"axis": "contrast", "files": 2},
            "flow_compare": {"axis": "contrast"}, "role_shift": {"axis": "contrast"},
            "interaction": {"axis": "interaction"}, "circle": {"axis": "group"},
            "chord": {"axis": "group"}},
            host_keep=["across_design", "unit_presence", "diff_matrix", "interaction"],
            host_list="report.host_panels")
        rep = L.check(spec_of(PLUGIN), lay, KEYS)
        self.assertFalse(rep["ok"])
        self.assertEqual(rep["host_list"]["wanted"],
                         ["across_design", "unit_presence", "diff_matrix", "interaction"])
        self.assertIsNone(rep["host_list"]["declared"])
        self.assertIn("host_panels", L.format_report("demo", rep))
        self.assertEqual(rep["host"]["contrast"], 2, rep)          # the two difference matrices
        self.assertEqual(rep["host"]["cohort"], 2, rep)            # the grid and the census
        self.assertEqual(rep["host"]["interaction"], 1, rep)
        self.assertEqual(rep["host"].get("group", 0), 0, rep)      # the arm kinds are not kept
        self.assertEqual(rep["counts"]["contrast"], 11 + 2, rep)   # plan files plus the host's
        plan = L.trim(spec_of(PLUGIN), lay, KEYS)
        kept = {e["id"]: e for e in plan["kept"]}
        # contrast: 3 - 2 for the host leaves 1: the first kind the layout names
        self.assertIn("nativecmp_diff", kept)
        self.assertNotIn("nativecmp_rank", kept)
        self.assertNotIn("nativecmp_chord", kept)
        # interaction: 2 - 1 for the host leaves 1 file
        self.assertEqual(sum(e.get("at_most", 1) for e in plan["kept"]
                             if e.get("axis") == "interaction"), 1)
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "demo.py"
            f.write_text(PLUGIN, encoding="utf-8")
            L.apply(f, lay, KEYS)
            after = L.read_spec(f)
            self.assertEqual(after["report"]["host_panels"],
                             ["across_design", "unit_presence", "diff_matrix", "interaction"])
            rep = L.check(after, lay, KEYS)
            self.assertTrue(rep["ok"], rep)
            # applied twice, the list is written once
            L.apply(f, lay, KEYS)
            self.assertEqual(f.read_text().count("host_panels"), 1)
            # a plan under budget that lacks the list still owes the layout
            small = {"report": {"figures": [
                {"id": "a", "kind": "circle", "drawn_by": "tool", "fn": "f", "axis": "unit",
                 "position": "contrast"}]}}
            self.assertFalse(L.check(small, lay, KEYS)["ok"])
            small["report"]["host_panels"] = ["across_design", "unit_presence", "diff_matrix",
                                              "interaction"]
            self.assertTrue(L.check(small, lay, KEYS)["ok"])
        text = L.format_report("demo", rep)
        self.assertIn("host", text)

    def test_apply_takes_the_version_the_author_states(self):
        keys = dict(KEYS, version="version")
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "demo.py"
            f.write_text(PLUGIN.replace('"name": "demo",', '"name": "demo",\n    "version": "0.34.0",'),
                         encoding="utf-8")
            got = L.apply(f, LAYOUT, keys, as_version="0.36.0")
            self.assertEqual(got["version"], ("0.34.0", "0.36.0"))
            self.assertIn('"version": "0.36.0"', f.read_text())

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
