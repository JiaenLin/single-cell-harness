#!/usr/bin/env python3
"""The figure plan carries the call, and the maker prints it, checks it and migrates to it.

Harness ADR-0016. A stage declaring `entry_keys` is the plan stage: the list it fills is one
entry per figure family - who draws it, over which axis, the function, its items, its ceiling,
where it sits, how it is described - and the target repository generates its draw sites from it.

THREE THINGS ARE FIXED HERE, none of them a field name of any repository:

  `plan_worksheet` prints one row per entry, what each lacks under it, and the upstream
  function's parameters beside its name when an inventory is given.

  `migrate_worksheet` builds the paste-ready plan for a plugin still on the older form - ids
  parsed out of prose, ceilings per function, two prefix maps - from those fields and from its
  hand-written draw sites, read one last time. Every field it could not read is the
  placeholder; a legend written at the site from runtime values is a placeholder with the
  expression beside it, because a template is a decision.

  A plugin whose protocol lives in a generated companion beside it has its sites read with the
  companion's wrappers. Read from the Python alone, such a plugin reported no draw sites at all,
  and the stage that reads them printed done - a plugin with 47 sites, silently, for two days.
"""
from __future__ import annotations

import ast
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sch.dev import convert as CV                                          # noqa: E402
from sch.dev import points as P                                            # noqa: E402
from sch.dev.extract import Inventory                                      # noqa: E402

DEVPOINTS = """\
tool: quarry
devpoints: 1
tests:
  command: ["true"]
fixture:
  command: [["true"]]
  products: []
baseline_dir: b
points:
  seam:
    what: one seam
    lives: seams
    must_declare: [api]
    example: alpha
    proves: it is read
    cannot_prove: that it is right
    convert:
      placeholder: TODO
      upstream: wraps.tool
      stages:
        - name: plan
          phase: build
          fills: [report.figures]
          entry_keys:
            upstream: fn
            items: items
            bound: at_most
            call: args
            expression: expr
            skips: report.skips
          each_item_declares:
            drawn_by: [tool, plugin]
            axis: [unit, contrast, cohort]
            position: [overview, contrast, conclusion, appendix]
            legend: []
          places_every:
            - {field: native_plots, named_by: use, per_item: "<", bound: at_most}
            - {field: report.figures, named_by: id}
          axis_field: report.figure_axis
          positions: [overview, contrast, conclusion, appendix]
          axes: [unit, contrast, cohort]
          why: the plan
"""

# A plugin on the OLDER form: prose ids, a ceiling dict per function, two prefix maps, and an
# embedded R script that defines its own draw wrapper and draws three panels through it.
LEGACY = '''PLUGIN = {
    "api": 1,
    "wraps": {"tool": "quarrytool"},
    "native_plots": {
        "quarry_heat": {"at_most": {"native_heat": 2}, "profile": True,
                        "use": "figures/native_heat_{count,weight}.png per unit"},
        "quarry_chord": {"at_most": 6,
                         "use": "figures/nativecmp_chord__<pathway>.png per arm pair"},
        "quarry_palette": {"skip": "not_applicable", "evidence": "returns colours; draws nothing"},
        # THE DIRECTORY IS WRITTEN ONCE AND THE FILES FOLLOW IT, in English
        "quarry_ring": {"use": "figures/native_ring_count.png and native_ring_weight.png"},
    },
    "report": {
        "figures": [
            {"id": "F1_coverage", "drawn_by": "plugin", "shows": "diagnostic", "required": True,
             "question": "did the database match?", "source": "figures/F1_coverage.csv"},
        ],
        "figure_axis": {"native_": "unit", "nativecmp_": "contrast"},
        "figure_position": {"native_": "appendix", "nativecmp_": "contrast", "F1_": "appendix"},
    },
}

_R_RUN = r"""
.figures(prefix = "native_", what = "native plot")
npng <- function(id, expr, legend = "") {
  png(paste0(id, ".png")); print(expr); dev.off()
}
npng("heat_count", quarry_heat(cc, measure = "count", color = "Blues"),
     legend = "Counts between every ordered pair of populations.")
npng("heat_weight", quarry_heat(cc, measure = "weight"),
     legend = paste0("Weights for ", n, " populations."))
npng("ring_count", {
  quarry_ring(cc, measure = "count")
  stamp()
}, legend = "Rings by count.")
npng("ring_weight", quarry_ring(cc, measure = "weight"), w = .bw, h = 1200,
     legend = "Rings by weight.")
"""

_R_COMPARE = r"""
.figures(prefix = "nativecmp_", what = "native compare")
npng <- function(id, expr, legend = "") {
  png(paste0(id, ".png")); print(expr); dev.off()
}
for (p in shared) npng(paste0("chord__", p), quarry_chord(merged, signaling = p))
if (nrow(pos) >= 3) npng(paste0("orphan_log__", safe), quarry_orphan(pos, title = paste0(
    "Does the response depend on the stratum? ", "One point per pathway; the dashed line is no ",
    "interaction - the same fold change in both strata. Above it the response is larger in the ",
    "first stratum, below it in the second, which is the control. Every value is the method's ",
    "own per-pathway contribution and no test is claimed for a difference of two differences; ",
    "the multiplicative scale ranks pathways differently from the additive one beside it.")),
    by = "plugin", legend = "The same question on the log scale.")
"""
'''


# A plugin ON THE PLAN ALONE: every entry says where it goes and what it multiplies over, and
# the two prefix maps are gone.
PLANNED = '''PLUGIN = {
    "api": 1,
    "wraps": {"tool": "quarrytool"},
    "report": {
        "figures": [
            {"id": "native_heat_count", "drawn_by": "tool", "fn": "quarry_heat", "axis": "unit",
             "position": "appendix", "args": 'cc, measure = "count"', "legend": "Counts."},
            {"id": "nativecmp_chord", "drawn_by": "tool", "fn": "quarry_chord", "axis": "contrast",
             "position": "contrast", "items": "shared", "at_most": 6,
             "file": 'paste0("chord__", p)', "args": "merged, signaling = p",
             "legend": "The {p} pathway."},
        ],
        "skips": {"quarry_palette": {"skip": "not_applicable",
                                     "evidence": "returns colours; draws nothing"}},
    },
}
'''


def _repo(plugin_text):
    d = Path(tempfile.mkdtemp(prefix="sch-plan-"))
    (d / "seams").mkdir()
    (d / "seams" / "alpha.py").write_text(plugin_text, encoding="utf-8")
    (d / "DEVPOINTS.yaml").write_text(DEVPOINTS, encoding="utf-8")
    return d


def _spec(d):
    return dict(CV._convert_specs_for_ladder(P.load(d), "seam"))["alpha"]


class Migrate(unittest.TestCase):
    def setUp(self):
        self.d = _repo(LEGACY)
        self.doc = P.load(self.d)
        self.spec = _spec(self.d)
        self.text = CV.migrate_worksheet(self.spec, self.doc, "seam", "alpha",
                                         source=(self.d / "seams" / "alpha.py").read_text())
        body = self.text.split("\n", 2)[2]          # drop the two comment lines
        self.plan = ast.literal_eval("{" + body + "}")
        self.by_id = {e["id"]: e for e in self.plan["figures"]}

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_a_brace_family_becomes_one_entry_per_member_with_a_ceiling_of_one(self):
        self.assertIn("native_heat_count", self.by_id)
        self.assertIn("native_heat_weight", self.by_id)
        self.assertEqual(self.by_id["native_heat_count"]["at_most"], 1)
        self.assertEqual(self.by_id["native_heat_count"]["fn"], "quarry_heat")
        self.assertEqual(self.by_id["native_heat_count"]["drawn_by"], "tool")
        self.assertTrue(self.by_id["native_heat_count"]["profile"])

    def test_the_axis_and_position_come_from_the_prefix_maps(self):
        self.assertEqual(self.by_id["native_heat_count"]["axis"], "unit")
        self.assertEqual(self.by_id["native_heat_count"]["position"], "appendix")
        self.assertEqual(self.by_id["nativecmp_chord"]["axis"], "contrast")
        self.assertEqual(self.by_id["nativecmp_chord"]["position"], "contrast")

    def test_the_call_is_read_from_the_site(self):
        self.assertEqual(self.by_id["native_heat_count"]["args"],
                         'cc, measure = "count", color = "Blues"')
        self.assertEqual(self.by_id["native_heat_weight"]["args"], 'cc, measure = "weight"')

    def test_a_literal_legend_is_the_template_and_a_paste0_of_names_becomes_one(self):
        self.assertEqual(self.by_id["native_heat_count"]["legend"],
                         "Counts between every ordered pair of populations.")
        # `paste0("Weights for ", n, " populations.")` is a template with one fact the method
        # must record; a legend built with a CALL inside would stay a decision for a person.
        self.assertEqual(self.by_id["native_heat_weight"]["legend"], "Weights for {n} populations.")
        self.assertNotIn("facts", self.by_id["native_heat_weight"])

    def test_a_per_item_site_names_its_items_vector_and_keeps_its_ceiling(self):
        e = self.by_id["nativecmp_chord"]
        self.assertEqual(e["items"], "shared")
        self.assertEqual(e["file"], 'paste0("chord__", p)',
                         "the file stem is the site's own expression, kept verbatim")
        self.assertEqual(e["at_most"], 6)
        self.assertEqual(e["args"], "merged, signaling = p")
        self.assertTrue(e["legend"].startswith("TODO"))

    def test_the_existing_entry_is_carried_with_its_axis_and_position_made_explicit(self):
        e = self.by_id["F1_coverage"]
        self.assertEqual(e["drawn_by"], "plugin")
        self.assertEqual(e["question"], "did the database match?")
        self.assertEqual(e["axis"], "unit")
        self.assertEqual(e["position"], "appendix")
        self.assertTrue(e["legend"].startswith("TODO"))

    def test_the_skips_are_carried_verbatim(self):
        self.assertEqual(self.plan["skips"]["quarry_palette"]["skip"], "not_applicable")

    def test_the_worksheet_counts_what_a_person_still_owes(self):
        head = self.text.splitlines()[0]
        self.assertIn("6 draw site(s) read", head)
        self.assertIn("1 named by no legacy field", head)
        self.assertIn("left for a person", head)
        self.assertGreaterEqual(self.text.count("TODO"), 3)

    def test_a_second_file_named_after_an_and_is_read(self):
        # "figures/native_ring_count.png and native_ring_weight.png": the directory written once,
        # the second name bare. The reader that placed these families found the first and missed
        # the second, so a family of eighteen files left the plan without a word.
        self.assertIn("native_ring_weight", self.by_id)
        e = self.by_id["native_ring_weight"]
        self.assertEqual(e["fn"], "quarry_ring")
        self.assertEqual(e["args"], 'cc, measure = "weight"')
        self.assertEqual(e["legend"], "Rings by weight.")

    def test_a_device_size_that_is_an_expression_is_carried_as_one(self):
        # `w = .bw`, `w = max(1500, 340 * length(objs))`: a width computed by the method. Read
        # as "an integer or nothing", three of one plugin's sites lost their width and the
        # generated site would have drawn them at the script's default - a change to a figure
        # nobody asked for, invisible to every count.
        e = self.by_id["native_ring_weight"]
        self.assertEqual(e["w"], ".bw")
        self.assertEqual(e["h"], 1200)

    def test_a_brace_block_keeps_its_statement_boundaries(self):
        # `{ f(x) g() }` on one line is not R. The block is carried with its lines, indented
        # one space, so the generated site is the site that was read.
        e = self.by_id["native_ring_count"]
        self.assertNotIn("args", e)
        self.assertEqual(e["expr"], '{\n quarry_ring(cc, measure = "count")\n stamp()\n }')

    def test_a_site_no_legacy_field_names_is_printed_and_never_dropped(self):
        # A draw site is a figure a run draws. One that no prose names is not a site to lose:
        # after the migration the sites are generated from the plan, and an entry that is not
        # there is a panel that stops existing - silently, because nothing counted it.
        self.assertIn("nativecmp_orphan_log", self.by_id)
        e = self.by_id["nativecmp_orphan_log"]
        self.assertEqual(e["drawn_by"], "plugin", "the site's own `by =` is the provenance")
        self.assertEqual(e["file"], 'paste0("orphan_log__", safe)')
        self.assertEqual(e["fn"], "quarry_orphan")
        self.assertTrue(e["args"].startswith("pos, title = paste0("), e["args"])
        self.assertEqual(e["axis"], "contrast")
        self.assertEqual(e["position"], "contrast")
        self.assertEqual(e["legend"], "The same question on the log scale.")
        self.assertTrue(str(e["at_most"]).startswith("TODO"), e["at_most"])

    def test_nothing_is_decided_that_was_not_read(self):
        # the count of TODOs is the count of decisions; every one names what it is for
        for e in self.plan["figures"]:
            for v in e.values():
                if isinstance(v, str) and v.startswith("TODO"):
                    self.assertIn(" - ", v, v)


class PlanTable(unittest.TestCase):
    def setUp(self):
        self.d = _repo(LEGACY)
        self.doc = P.load(self.d)
        self.spec = _spec(self.d)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_the_table_names_what_each_entry_lacks(self):
        text = CV.plan_worksheet(self.spec, self.doc, "seam", "alpha")
        self.assertIn("F1_coverage", text)
        self.assertIn("LACKS  no axis", text)
        self.assertIn("LACKS  no legend", text)
        self.assertIn("pass --python", text)

    def test_the_upstream_signature_is_printed_beside_fn(self):
        spec = dict(self.spec)
        spec["report"] = dict(spec["report"], figures=[
            {"id": "native_heat_count", "drawn_by": "tool", "fn": "quarry_heat", "axis": "unit",
             "position": "appendix", "legend": "Counts.", "args": 'cc, measure = "count"'}])
        inv = Inventory("quarrytool", ["quarry_heat"], "measured",
                        detail={"quarry_heat": {"signature": "(cc, measure = 'count', ...)",
                                                "found_by": "signature", "summary": ""}})
        text = CV.plan_worksheet(spec, self.doc, "seam", "alpha", inv=inv)
        self.assertIn("quarry_heat(cc, measure = 'count', ...)", text)
        self.assertIn('quarry_heat(cc, measure = "count")', text)
        self.assertNotIn("LACKS", text)

    @unittest.skipUnless(shutil.which("Rscript"), "no R on this machine")
    def test_a_call_r_cannot_parse_is_a_lack_when_r_is_at_hand(self):
        spec = dict(self.spec)
        spec["report"] = dict(spec["report"], figures=[
            {"id": "native_broken", "drawn_by": "tool", "fn": "quarry_heat", "axis": "unit",
             "position": "appendix", "legend": "L", "expr": "{ quarry_heat(cc) stamp() }"},
            {"id": "native_fine", "drawn_by": "tool", "fn": "quarry_heat", "axis": "unit",
             "position": "appendix", "legend": "L", "args": 'cc, measure = "count"'}])
        text = CV.plan_worksheet(spec, self.doc, "seam", "alpha", rscript=shutil.which("Rscript"))
        self.assertEqual(text.count("LACKS  does not parse as R"), 1, text)
        self.assertIn("1 lack something", text.splitlines()[0])
        self.assertLess(text.index("native_broken"), text.index("does not parse"))

    def test_a_point_without_a_plan_stage_says_so(self):
        doc = P.load(self.d)
        for st in doc["points"]["seam"]["convert"]["stages"]:
            st.pop("entry_keys", None)
        with self.assertRaises(CV.ConvertError) as cm:
            CV.plan_worksheet(self.spec, doc, "seam", "alpha")
        self.assertIn("entry_keys", str(cm.exception))


class ThePlanIsPlacedByItsOwnWord(unittest.TestCase):
    """The entry's own word, then the prefix map - the rule the target's one reader applies.

    A migrated plugin carries no map, and the placement debt read only the maps: every one of
    its 57 families came back unplaced and unaxised, each of them saying in its own entry
    exactly where it went, and the stage the migration exists to finish read `todo` forever.
    """

    def setUp(self):
        self.d = _repo(PLANNED)
        self.doc = P.load(self.d)
        self.spec = _spec(self.d)
        self.st = CV.plan_stage(self.doc, "seam")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_a_plugin_on_the_plan_alone_owes_no_placement(self):
        debt = CV.placement_debt(self.spec, self.st)
        self.assertEqual(debt["unplaced"], [])
        self.assertEqual(debt["unaxised"], [])
        self.assertEqual(debt["wrong"], [])
        self.assertEqual(sorted(f[0] for f in debt["families"]),
                         ["native_heat_count", "nativecmp_chord"])

    def test_and_the_plan_stage_reads_done(self):
        rows = CV.status(self.spec, self.doc, "seam", "alpha",
                         source=(self.d / "seams" / "alpha.py").read_text())
        row = next(r for r in rows if r["stage"] == "plan")
        self.assertTrue(row["done"], {k: v for k, v in row.items() if k != "why"})

    def test_a_value_outside_the_vocabulary_is_still_wrong(self):
        spec = dict(self.spec)
        figs = [dict(e) for e in spec["report"]["figures"]]
        figs[0]["position"] = "margin"
        spec["report"] = dict(spec["report"], figures=figs)
        debt = CV.placement_debt(spec, self.st)
        self.assertEqual(debt["wrong"], [("native_heat_count", "margin")])


class TheCompanionsWrappersReachTheScan(unittest.TestCase):
    """A plugin whose draw wrappers were generated into a file beside it defines none in its
    embedded scripts. The scan must read the companion's, or the plugin draws nothing."""

    def test_sites_are_found_through_the_companion(self):
        text = LEGACY.replace(
            'npng <- function(id, expr, legend = "") {\n  png(paste0(id, ".png")); print(expr); dev.off()\n}\n',
            "")
        # the embedded scripts must still be recognised as R: keep one function definition
        text = text.replace('.figures(prefix = "native_", what = "native plot")',
                            '.figures(prefix = "native_", what = "native plot")\n'
                            '.ttl <- function(x) x')
        d = _repo(text)
        try:
            (d / "seams" / "alpha.draw.R").write_text(
                'npng <- function(id, expr, legend = "") {\n'
                '  png(paste0(id, ".png")); print(expr); dev.off()\n}\n', encoding="utf-8")
            doc = P.load(d)
            src = (d / "seams" / "alpha.py").read_text()
            found = CV._legacy_sites(doc, "seam", "alpha", src)
            self.assertIn("native_heat_count", found)
            inv = CV.measure_draw_sites(doc, "seam", "alpha", src)
            self.assertTrue(inv.complete)
            self.assertGreaterEqual(len(inv.names), 2,
                                    "the companion's wrapper did not reach the site scan")
        finally:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
