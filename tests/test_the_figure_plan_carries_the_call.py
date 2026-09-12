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
"""

_R_COMPARE = r"""
.figures(prefix = "nativecmp_", what = "native compare")
npng <- function(id, expr, legend = "") {
  png(paste0(id, ".png")); print(expr); dev.off()
}
for (p in shared) npng(paste0("chord__", p), quarry_chord(merged, signaling = p))
"""
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

    def test_a_literal_legend_is_the_template_and_a_computed_one_is_a_decision(self):
        self.assertEqual(self.by_id["native_heat_count"]["legend"],
                         "Counts between every ordered pair of populations.")
        self.assertTrue(self.by_id["native_heat_weight"]["legend"].startswith("TODO"))
        self.assertIn("paste0(", self.by_id["native_heat_weight"]["legend"])

    def test_a_per_item_site_names_its_items_vector_and_keeps_its_ceiling(self):
        e = self.by_id["nativecmp_chord"]
        self.assertEqual(e["items"], "shared")
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
        self.assertIn("3 draw site(s) read", head)
        self.assertIn("left for a person", head)
        self.assertGreaterEqual(self.text.count("TODO"), 3)

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

    def test_a_point_without_a_plan_stage_says_so(self):
        doc = P.load(self.d)
        for st in doc["points"]["seam"]["convert"]["stages"]:
            st.pop("entry_keys", None)
        with self.assertRaises(CV.ConvertError) as cm:
            CV.plan_worksheet(self.spec, doc, "seam", "alpha")
        self.assertIn("entry_keys", str(cm.exception))


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
