#!/usr/bin/env python3
"""The layout charges the host's own panels to the plugins the host draws them for, as each declares
them; and a plugin that runs once over the cohort gets its own budget (autodev W019, GAP-C40).

FOUND BY THE BLIND CONVERSION OF de (scProfile docs/MIGRATIONS.md, autodev W013). The host draws its
own panels - the design grid, the census, the per-unit totals, the interaction - from a plugin's
per-unit network, so only for a plugin that has one. The layout charged them to EVERY plugin and
demanded every plugin's `report.host_panels` equal its list. de has no network and runs once over
the cohort: its six plates sat against a cohort budget of three that the host's three panels had
already spent, so the plan was over budget by construction and the trim would have deleted all six.

Which plugins earn the host's panels is the tool's to say (`host_for`, a field of a plugin's own
declaration). A plugin the host draws for carries the kinds its pages show, any of the host's kinds.
And the cohort axis is a per-unit plugin's summary; a plugin that runs once over the cohort (the
plan stage's `per_unit` field, empty) is held to the layout's `pooled` budget where one is declared.
Without the declarations the layout behaves as before - the other half of this file says so.

Run: PYTHONPATH=. python3 tests/test_the_host_is_charged_where_it_draws.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sch.dev import layout as L                                                  # noqa: E402

HOST = {"across_design": {"axis": "cohort"}, "unit_presence": {"axis": "cohort"},
        "unit_totals": {"axis": "cohort"}, "diff_matrix": {"axis": "contrast", "files": 2},
        "interaction": {"axis": "interaction"}, "circle": {"axis": "group"}}
BASE_LAYOUT = {
    "axes": {"sample": {"budget": 2, "keep": ["circle"]},
             "group": {"budget": 5, "keep": ["circle"]},
             "contrast": {"budget": 10, "keep": ["diff_matrix", "other"]},
             "interaction": {"budget": 20, "keep": ["interaction"]},
             "cohort": {"budget": 3, "keep": ["unit_presence", "unit_totals", "coverage"]}},
    "prefer": ["tool", "plugin"],
    "drop_first": ["appendix", "conclusion", "contrast", "overview"],
    "host": HOST,
    "host_keep": ["across_design", "unit_presence", "unit_totals", "interaction"],
    "host_list": "report.host_panels",
}
LAYOUT = dict(BASE_LAYOUT, host_for="report.unit_network", pooled={"budget": 9, "keep": []})
KEYS = {"upstream": "fn", "bound": "at_most", "axis": "axis", "position": "position",
        "skips": "report.skips", "per_unit": "per_unit"}

# de's shape: four checks and two answers, every one drawn once over the whole cohort.
POOLED = textwrap.dedent('''\
    PLUGIN = {
        "name": "pooled",
        "version": "0.3.0",
        "report": {
            "figures": [
                {"id": "F1_replicates", "drawn_by": "plugin", "axis": "cohort", "position": "overview"},
                {"id": "F2_dispersion", "drawn_by": "plugin", "axis": "cohort", "position": "overview"},
                {"id": "F3_calibration", "drawn_by": "plugin", "axis": "cohort", "position": "overview"},
                {"id": "F4_untested", "drawn_by": "plugin", "axis": "cohort", "position": "overview"},
                {"id": "F5_ma", "drawn_by": "plugin", "axis": "cohort", "position": "contrast"},
                {"id": "F6_hits", "drawn_by": "plugin", "axis": "cohort", "position": "contrast"},
            ],
            "skips": {},
        },
    }
    ''')


def spec_of(text):
    ns = {}
    exec(text, ns)                                                           # noqa: S102
    return ns["PLUGIN"]


def network(host_panels=None):
    spec = {"name": "net", "per_unit": "sample",
            "report": {"unit_network": {"table": "t.csv", "source": "s", "target": "t",
                                        "weight": "w"},
                       "figures": [{"id": "native_circle", "kind": "circle", "drawn_by": "tool",
                                    "fn": "f", "axis": "unit", "position": "contrast"}]}}
    if host_panels is not None:
        spec["report"]["host_panels"] = list(host_panels)
    return spec


class TheHostIsChargedWhereItDraws(unittest.TestCase):

    def test_a_plugin_without_the_field_carries_none_of_the_hosts_files_and_owes_no_list(self):
        rep = L.check(spec_of(POOLED), dict(LAYOUT, pooled=None), KEYS)
        self.assertEqual(rep["host"], {}, rep)
        self.assertFalse(rep["host_list"]["earns"])
        self.assertFalse(rep["host_list"]["owes"])
        self.assertEqual(rep["counts"]["cohort"], 6)        # its own six, none of the host's
        self.assertIn("draws none of its own panels", L.format_report("pooled", rep))

    def test_a_pooled_plugin_is_held_to_its_own_budget_and_the_trim_keeps_its_plates(self):
        rep = L.check(spec_of(POOLED), LAYOUT, KEYS)
        self.assertTrue(rep["pooled"])
        self.assertEqual(rep["budgets"]["cohort"], 9)
        self.assertTrue(rep["ok"], rep)
        self.assertEqual(L.trim(spec_of(POOLED), LAYOUT, KEYS)["dropped"], [])

    def test_without_a_pooled_budget_its_own_cohort_budget_is_not_shared_with_the_host(self):
        plan = L.trim(spec_of(POOLED), dict(LAYOUT, pooled=None), KEYS)
        self.assertEqual(len(plan["kept"]), 3, plan)        # three of six, not none of six

    def test_a_network_plugin_is_charged_the_kinds_it_declares(self):
        rep = L.check(network(["across_design"]), LAYOUT, KEYS)
        self.assertTrue(rep["host_list"]["earns"])
        self.assertEqual(rep["host"], {"cohort": 1}, rep)
        self.assertTrue(rep["ok"], rep)                     # a subset is not a debt
        rep = L.check(network(), LAYOUT, KEYS)               # no list: the host draws every kind
        self.assertFalse(rep["ok"])
        self.assertTrue(rep["host_list"]["owes"])
        self.assertEqual(rep["host"].get("cohort"), 3)       # charged as the layout keeps them

    def test_a_kind_the_host_does_not_draw_is_still_owed_and_apply_refuses_it(self):
        spec = network(["across_design", "made_up_kind"])
        rep = L.check(spec, LAYOUT, KEYS)
        self.assertFalse(rep["ok"])
        self.assertEqual(rep["host_list"]["unknown"], ["made_up_kind"])
        self.assertIn("made_up_kind", L.format_report("net", rep))
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "net.py"
            text = "PLUGIN = " + repr(spec) + "\n"
            f.write_text(text, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "made_up_kind"):
                L.apply(f, LAYOUT, KEYS)
            self.assertEqual(f.read_text(encoding="utf-8"), text)       # nothing written

    def test_apply_writes_no_host_list_for_a_plugin_the_host_draws_nothing_for(self):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "pooled.py"
            f.write_text(POOLED.replace('"version": "0.3.0",', '"version": "0.3.0",'), encoding="utf-8")
            lay = dict(LAYOUT, pooled={"budget": 4, "keep": []})   # four of six fit
            L.apply(f, lay, dict(KEYS, version="version"))
            after = L.read_spec(f)
            self.assertNotIn("host_panels", after["report"])
            self.assertEqual(len(after["report"]["figures"]), 4)
            self.assertTrue(L.check(after, lay, KEYS)["ok"])


class WithoutTheDeclarationsTheLayoutIsAsBefore(unittest.TestCase):
    """The tool decides; until it says, every plugin is charged and nothing is pooled."""

    def test_every_plugin_is_charged_and_owes_the_list(self):
        rep = L.check(spec_of(POOLED), BASE_LAYOUT, KEYS)
        self.assertEqual(rep["host"].get("cohort"), 3)
        self.assertTrue(rep["host_list"]["owes"])
        self.assertFalse(rep["pooled"])
        rep = L.check(spec_of(POOLED), dict(LAYOUT, pooled={"budget": 9}), dict(KEYS, per_unit=""))
        self.assertFalse(rep["pooled"])                     # no per-unit field named: not pooled


class ThroughTheRealCli(unittest.TestCase):

    def test_sch_dev_convert_layout_reads_the_declarations(self):
        d = Path(tempfile.mkdtemp(prefix="sch-c40-"))
        try:
            (d / "kernels").mkdir()
            (d / "kernels" / "pooled.py").write_text(POOLED, encoding="utf-8")
            (d / "DEVPOINTS.yaml").write_text(textwrap.dedent("""\
                tool: quarry
                devpoints: 1
                points:
                  kernel:
                    what: a kernel
                    lives: kernels
                    must_declare: []
                    proves: it is read
                    cannot_prove: that it is right
                    convert:
                      placeholder: TODO
                      upstream: wraps.tool
                      stages:
                        - name: plan
                          phase: build
                          fills: [report.figures]
                          entry_keys: {upstream: fn, bound: at_most, axis: axis, position: position, skips: report.skips, per_unit: per_unit}
                        - name: layout
                          phase: build
                          fills: [report.figures]
                          under_layout: true
                          axes:
                            cohort: {budget: 3, keep: [unit_presence, unit_totals]}
                          host:
                            across_design: {axis: cohort}
                            unit_presence: {axis: cohort}
                            unit_totals: {axis: cohort}
                          host_keep: [across_design, unit_presence, unit_totals]
                          host_list: report.host_panels
                          host_for: report.unit_network
                          pooled: {budget: 9, keep: []}
                """), encoding="utf-8")
            env = dict(os.environ, PYTHONPATH=str(ROOT))
            p = subprocess.run([sys.executable, "-m", "sch", "dev", "convert", "layout", "--root",
                                str(d), "--point", "kernel", "--name", "pooled"],
                               capture_output=True, text=True, env=env, cwd=str(ROOT), timeout=120)
            out = p.stdout + p.stderr
            self.assertEqual(p.returncode, 0, out)
            self.assertIn("6 file(s) per occurrence against a budget of 9", out)
            self.assertIn("draws none of its own panels", out)
        finally:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
