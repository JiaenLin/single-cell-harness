"""The maker edits a plugin's declaration by span, one verb per change, and the prose around
the change survives (harness ADR-0026, step 2).

A COLD AUTHOR EDITED A 5,454-LINE FILE BY HAND FOR 71 MINUTES: an id rename touched four
sites, the ceiling that mattered was 250 lines from its entry, and the only instrument was a
text editor. The declaration is a pure literal, so the maker can find the exact source span of
any value and replace that span alone - the comment trail stays byte for byte - and follow the
sites it knows: the protocol's `.draw("<id>")` lines, the profile list, the evidence routes,
the skips. A site it cannot follow is reported, not guessed at. Every write round-trips through
`ast` before it lands; a value that would not parse is refused with the file untouched.

Run: PYTHONPATH=. python3 tests/test_the_maker_edits_a_plugin.py
"""
import ast
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sch.dev import edit as E                                                    # noqa: E402

KEYS = {"upstream": "fn", "bound": "at_most", "axis": "axis", "position": "position",
        "skips": "report.skips", "routes": "report.provides_evidence", "version": "version",
        "profile_list": "_PROFILE_PLOTS", "side_effect": "generated"}

PLUGIN = textwrap.dedent('''\
    """A demo plugin of a dose-by-time design."""
    PLUGIN = {
        "name": "demo",
        "version": "1.4.0",
        "config": {
            # HOW MANY PERMUTATIONS. A comment the author left, and must keep.
            "nboot": {"default": 100, "help": "permutations"},
            "trim": {"default": 0.1},
        },
        "produces": ["tables/edges.csv", "[optional] objects/demo.rds"],
        "report": {
            "host_panels": ["across_design", "unit_totals"],
            "subject": "signalling",
            "provides_evidence": {"who_changed": ["native:drawDiff", "plan:nativecmp_diff"]},
            "figures": [
                {
                    'id': 'native_circle',
                    'kind': 'circle',
                    'drawn_by': 'tool',
                    'fn': 'drawCircle',
                    # THE AXIS. Kept on both unit axes on purpose - a comment inside an entry.
                    'axis': 'unit',
                    'position': 'contrast',
                    'legend': 'A circle of the populations; edge width is the summed strength.',
                },
                {'id': 'native_matrix', 'kind': 'matrix', 'drawn_by': 'tool', 'fn': 'drawMatrix',
                 'axis': 'group', 'position': 'contrast', 'at_most': 1,
                 'args': 'x, measure = "count"', 'legend': 'a matrix'},
                {'id': 'nativecmp_diff', 'kind': 'diff_matrix', 'drawn_by': 'tool', 'fn': 'drawDiff',
                 'axis': 'contrast', 'position': 'contrast', 'at_most': 1,
                 'legend': ('The difference between the two arms, '
                            'red where the second arm is larger.')},
                {'id': 'F2_presence', 'kind': 'unit_presence', 'drawn_by': 'plugin',
                 'axis': 'sample', 'position': 'appendix', 'legend': 'who is present'},
            ],
            "skips": {
                'drawSpatial': {'skip': 'not_applicable', 'evidence': 'no coordinates'},
                'drawBubble': {'skip': 'over_budget', 'axis': 'contrast', 'budget': 3},
            },
        },
    }

    _PROFILE_PLOTS = ('circle', 'matrix')

    R_PROTOCOL = """
    .draw("native_circle")
    .draw("native_matrix")
    .draw("nativecmp_diff")
    """


    def run(ctx):
        C = ctx.config
        n = C["nboot"]
        return n, "native_circle"
    ''')


def spec_of(text):
    tree = ast.parse(text)
    node = next(n for n in tree.body if isinstance(n, ast.Assign) and n.targets[0].id == "PLUGIN")
    return ast.literal_eval(node.value)


def comments_of(text):
    return [l for l in text.splitlines() if l.strip().startswith("#")]


class TheMakerEditsAPlugin(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.f = Path(self.td.name) / "demo.py"
        self.f.write_text(PLUGIN, encoding="utf-8")

    def tearDown(self):
        self.td.cleanup()

    def text(self):
        return self.f.read_text(encoding="utf-8")

    # ---- set
    def test_set_rewrites_one_value_by_span_and_keeps_every_comment(self):
        rep = E.edit(self.f, [("set", "report.figures[native_matrix].at_most", 3)], KEYS)
        spec = spec_of(self.text())
        self.assertEqual(spec["report"]["figures"][1]["at_most"], 3)
        self.assertEqual(comments_of(self.text()), comments_of(PLUGIN))
        self.assertEqual(spec["version"], "1.5.0")
        self.assertEqual(rep["version"], ("1.4.0", "1.5.0"))

    def test_set_adds_a_key_an_entry_lacks_after_its_id(self):
        E.edit(self.f, [("set", "report.figures[native_circle].at_most", 2)], KEYS)
        spec = spec_of(self.text())
        self.assertEqual(spec["report"]["figures"][0]["at_most"], 2)
        self.assertIn("# THE AXIS.", self.text())

    def test_set_reaches_a_nested_default_a_report_key_and_a_top_key(self):
        E.edit(self.f, [("set", "config.nboot.default", 50),
                        ("set", "report.subject", "intercellular signalling"),
                        ("set", "cores", 4)], KEYS)
        spec = spec_of(self.text())
        self.assertEqual(spec["config"]["nboot"]["default"], 50)
        self.assertEqual(spec["report"]["subject"], "intercellular signalling")
        self.assertEqual(spec["cores"], 4)
        self.assertIn("# HOW MANY PERMUTATIONS.", self.text())

    def test_a_legend_spanning_lines_is_replaced_whole(self):
        E.edit(self.f, [("set", "report.figures[nativecmp_diff].legend", "One sentence.")], KEYS)
        spec = spec_of(self.text())
        self.assertEqual(spec["report"]["figures"][2]["legend"], "One sentence.")
        self.assertNotIn("red where the second arm", self.text())

    # ---- delete
    def test_delete_removes_a_key_and_nothing_else(self):
        E.edit(self.f, [("delete", "report.figures[native_matrix].args")], KEYS)
        spec = spec_of(self.text())
        self.assertNotIn("args", spec["report"]["figures"][1])
        self.assertEqual(spec["report"]["figures"][1]["at_most"], 1)
        E.edit(self.f, [("delete", "report.host_panels")], KEYS)
        self.assertNotIn("host_panels", spec_of(self.text())["report"])

    # ---- lists
    def test_list_add_and_remove_on_host_panels_and_produces(self):
        E.edit(self.f, [("list_add", "report.host_panels", "interaction"),
                        ("list_remove", "produces", "tables/edges.csv")], KEYS)
        spec = spec_of(self.text())
        self.assertEqual(spec["report"]["host_panels"], ["across_design", "unit_totals", "interaction"])
        self.assertEqual(spec["produces"], ["[optional] objects/demo.rds"])

    def test_list_add_on_a_list_whose_bracket_closes_on_the_last_line(self):
        # the plugin's own `produces`: one element per line, the bracket on the last one
        text = self.text().replace(
            '"produces": ["tables/edges.csv", "[optional] objects/demo.rds"],',
            '"produces": ["tables/edges.csv",\n                 "[optional] objects/demo.rds"],')
        self.f.write_text(text, encoding="utf-8")
        E.edit(self.f, [("list_remove", "produces", "[optional] objects/demo.rds"),
                        ("list_add", "produces", "tables/z.csv")], KEYS)
        self.assertEqual(spec_of(self.text())["produces"], ["tables/edges.csv", "tables/z.csv"])
        E.edit(self.f, [("list_add", "produces", "tables/y.csv")], KEYS)
        self.assertEqual(spec_of(self.text())["produces"][-1], "tables/y.csv")

    # ---- rename
    def test_rename_follows_the_literal_the_routes_the_draw_site_and_the_profile_list(self):
        rep = E.edit(self.f, [("rename", "native_circle", "native_ring")], KEYS)
        text = self.text()
        spec = spec_of(text)
        self.assertEqual(spec["report"]["figures"][0]["id"], "native_ring")
        self.assertIn('.draw("native_ring")', text)
        self.assertNotIn('.draw("native_circle")', text)
        self.assertIn("_PROFILE_PLOTS = ('ring', 'matrix')", text)
        # the site in code it cannot follow is reported, by line, not rewritten
        self.assertTrue(rep["sites_not_followed"], rep)
        self.assertIn('return n, "native_circle"', text)
        rep = E.edit(self.f, [("rename", "nativecmp_diff", "nativecmp_delta")], KEYS)
        spec = spec_of(self.text())
        self.assertIn("plan:nativecmp_delta", spec["report"]["provides_evidence"]["who_changed"])
        self.assertEqual(rep["sites_not_followed"], [])

    # ---- remove / add / duplicate / swap
    def test_remove_takes_the_draw_site_and_the_profile_stem_and_needs_a_skip_for_a_lone_fn(self):
        with self.assertRaises(ValueError) as e:
            E.edit(self.f, [("remove", "native_matrix")], KEYS)
        self.assertIn("drawMatrix", str(e.exception))
        self.assertEqual(self.text(), PLUGIN)                      # nothing written
        E.edit(self.f, [("remove", "native_matrix", {"skip": "not_applicable",
                                                      "evidence": "the author's decision"})], KEYS)
        text = self.text()
        spec = spec_of(text)
        self.assertNotIn("native_matrix", [e["id"] for e in spec["report"]["figures"]])
        self.assertNotIn('.draw("native_matrix")', text)
        self.assertIn("_PROFILE_PLOTS = ('circle',)", text)
        self.assertEqual(spec["report"]["skips"]["drawMatrix"]["skip"], "not_applicable")

    def test_add_lifts_the_skip_and_appends_an_entry_the_plan_can_count(self):
        E.edit(self.f, [("add", {"id": "nativecmp_bubble", "kind": "other", "drawn_by": "tool",
                                 "fn": "drawBubble", "axis": "contrast", "position": "contrast",
                                 "at_most": 1, "legend": "bubbles"})], KEYS)
        text = self.text()
        spec = spec_of(text)
        self.assertEqual(spec["report"]["figures"][-1]["id"], "nativecmp_bubble")
        self.assertNotIn("drawBubble", spec["report"]["skips"])
        self.assertIn('.draw("nativecmp_bubble")', text)

    def test_duplicate_and_swap(self):
        E.edit(self.f, [("duplicate", "native_matrix", "native_matrix_twin")], KEYS)
        spec = spec_of(self.text())
        ids = [e["id"] for e in spec["report"]["figures"]]
        self.assertEqual(ids[1:3], ["native_matrix", "native_matrix_twin"])
        self.assertEqual(spec["report"]["figures"][2]["fn"], "drawMatrix")
        E.edit(self.f, [("swap", "native_circle", "F2_presence")], KEYS)
        ids = [e["id"] for e in spec_of(self.text())["report"]["figures"]]
        self.assertEqual(ids[0], "F2_presence")
        self.assertEqual(ids[-1], "native_circle")
        self.assertIn("# THE AXIS.", self.text())

    # ---- config key rename follows the code's own reads
    def test_rename_key_follows_the_literal_and_the_config_reads_in_code(self):
        rep = E.edit(self.f, [("rename_key", "config.nboot", "permutations")], KEYS)
        text = self.text()
        self.assertEqual(spec_of(text)["config"]["permutations"]["default"], 100)
        self.assertIn('C["permutations"]', text)
        self.assertEqual(rep["sites_followed"], 1)

    # ---- refusals and the dry run
    def test_a_value_that_breaks_the_literal_is_refused_and_nothing_is_written(self):
        with self.assertRaises(ValueError):
            E.edit(self.f, [("set", "report.figures[native_circle].at_most", E.Raw("1 +"))], KEYS)
        self.assertEqual(self.text(), PLUGIN)
        with self.assertRaises(ValueError) as e:
            E.edit(self.f, [("set", "report.figures[no_such].at_most", 1)], KEYS)
        self.assertIn("no_such", str(e.exception))

    def test_a_dry_run_prints_the_diff_and_writes_nothing(self):
        rep = E.edit(self.f, [("set", "report.figures[native_matrix].at_most", 3)], KEYS, dry=True)
        self.assertEqual(self.text(), PLUGIN)
        self.assertIn("-             'axis': 'group', 'position': 'contrast', 'at_most': 1,", rep["diff"])
        self.assertIn("+             'axis': 'group', 'position': 'contrast', 'at_most': 3,", rep["diff"])

    def test_the_version_is_bumped_once_per_edit_or_stated(self):
        E.edit(self.f, [("set", "cores", 4), ("set", "report.subject", "x")], KEYS)
        self.assertEqual(spec_of(self.text())["version"], "1.5.0")
        E.edit(self.f, [("set", "cores", 2)], KEYS, as_version="2.0.0")
        self.assertEqual(spec_of(self.text())["version"], "2.0.0")



DECL = """
tool: demo
devpoints: 1
tests:
  command: ["{python}", "-c", "print(1)"]
run:
  forecast: ["{python}", "forecast.py", "{run}", "{name}"]
points:
  kernel:
    what: a kernel
    lives: kernels
    proves: it runs
    cannot_prove: that it is right
    convert:
      placeholder: "TODO"
      upstream: wraps.tool
      stages:
        - {name: contract, fills: [inject]}
        - name: plan
          fills: [report.figures]
          entry_keys: {upstream: fn, bound: at_most, axis: axis, position: position, skips: report.skips, routes: report.provides_evidence, side_effect: generated}
          after_edit:
            - ["{python}", "-c", "import sys; print('scaffolded {name}')"]
        - name: audited
          phase: test
          fills: []
          command: ["{python}", "-c", "print('audited')"]
          worksheet: ["{python}", "worksheet.py", "{run}"]
        - name: layout
          fills: [report.figures]
          under_layout: true
          axes:
            sample: {budget: 2, keep: [unit_presence, circle]}
            group: {budget: 3, keep: [circle, matrix]}
            contrast: {budget: 3, keep: [diff_matrix]}
            interaction: {budget: 2, keep: [interaction]}
            cohort: {budget: 1, keep: [unit_totals]}
          prefer: [tool, plugin]
          drop_first: [appendix, conclusion, contrast, overview]
          profile_list: _PROFILE_PLOTS
        - {name: judgement, kind: judgement, fills: [summary, cannot_show]}
"""


class TheVerbIsReachable(unittest.TestCase):
    """`sch dev edit` on a repository: the ops in the order typed, the followers the tool
    declares, the state after, and a refusal that writes nothing."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        (self.root / "DEVPOINTS.yaml").write_text(DECL, encoding="utf-8")
        (self.root / "kernels").mkdir()
        self.f = self.root / "kernels" / "demo.py"
        self.f.write_text(PLUGIN, encoding="utf-8")
        # the audited stage's worksheet, standing in: what the real one prints after a legend
        # rewrite, read on a run with the declaration in this tree
        (self.root / "worksheet.py").write_text(
            "import sys\n"
            "print('# THE WORKSHEET on ' + sys.argv[1] + ': 2 open finding(s) on 1 kind(s)')\n"
            "print('# STATED, AND THE LEGEND NO LONGER SAYS IT: 1 kind(s)')\n"
            "print('   - native_circle: \"the summed strength\"')\n", encoding="utf-8")
        # the tool's forecast, standing in: what `run.forecast` prints about the cache
        (self.root / "forecast.py").write_text(
            "import sys\nprint('  CACHE FORECAST for ' + sys.argv[2] + ': HIT - the span is that of the run')\n",
            encoding="utf-8")

    def tearDown(self):
        self.td.cleanup()

    def sch(self, *args):
        import subprocess
        return subprocess.run([sys.executable, "-m", "sch", "dev", "edit", "--root", str(self.root),
                               "--point", "kernel", "--name", "demo", *args],
                              capture_output=True, text=True, cwd=ROOT)

    def test_a_dry_run_prints_the_diff_and_the_file_stands(self):
        p = self.sch("--set", "report.figures[native_matrix].at_most=3", "--dry")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("+             'axis': 'group', 'position': 'contrast', 'at_most': 3,", p.stdout)
        self.assertEqual(self.f.read_text(encoding="utf-8"), PLUGIN)

    def test_an_edit_lands_reports_the_state_after_and_runs_the_followers(self):
        p = self.sch("--set", "report.figures[native_matrix].at_most=3",
                     "--legend", "native_circle", "One ring.", "--python", sys.executable)
        self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
        spec = spec_of(self.f.read_text(encoding="utf-8"))
        self.assertEqual(spec["report"]["figures"][1]["at_most"], 3)
        self.assertEqual(spec["report"]["figures"][0]["legend"], "One ring.")
        self.assertIn("version 1.4.0 -> 1.5.0", p.stdout)
        self.assertIn("budget", p.stdout)                       # the layout's count after
        self.assertIn("the plan: 4 -> 4 entr(ies), changed", p.stdout)
        self.assertIn("scaffolded demo", p.stdout)               # the follower ran

    def test_without_the_interpreter_the_followers_are_printed_as_the_next_step(self):
        p = self.sch("--set", "cores=4")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("next:", p.stdout)
        self.assertIn("unchanged", p.stdout)                     # the plan did not change

    def test_with_a_run_the_verb_reads_the_disclosures_a_legend_edit_unbinds(self):
        run = self.root / "run"
        run.mkdir()
        p = self.sch("--legend", "native_circle", "One ring.", "--run", str(run))
        self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
        self.assertIn("2 open finding(s)", p.stdout)
        self.assertIn("NO LONGER SAYS IT", p.stdout)
        self.assertIn("native_circle", p.stdout.split("NO LONGER")[1])
        self.assertIn("CACHE FORECAST for demo: HIT", p.stdout)

    def test_a_rename_reports_the_site_it_could_not_follow(self):
        p = self.sch("--rename", "native_circle", "native_ring")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("NOT FOLLOWED", p.stdout)
        self.assertIn('return n, "native_circle"', p.stdout)

    def test_a_refusal_names_the_reason_and_writes_nothing(self):
        p = self.sch("--remove", "native_matrix")
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("drawMatrix", p.stderr)
        self.assertEqual(self.f.read_text(encoding="utf-8"), PLUGIN)
        p = self.sch("--remove", "native_matrix", "--skip",
                     "{'skip': 'not_applicable', 'evidence': 'decided'}")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertNotIn("native_matrix", self.f.read_text(encoding="utf-8").split("_PROFILE")[0])

    def test_the_order_typed_is_the_order_applied(self):
        p = self.sch("--duplicate", "native_matrix", "native_matrix_twin",
                     "--set", "report.figures[native_matrix_twin].at_most=2")
        self.assertEqual(p.returncode, 0, p.stderr)
        spec = spec_of(self.f.read_text(encoding="utf-8"))
        twin = next(e for e in spec["report"]["figures"] if e["id"] == "native_matrix_twin")
        self.assertEqual(twin["at_most"], 2)


if __name__ == "__main__":
    unittest.main()
