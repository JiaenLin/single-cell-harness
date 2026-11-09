#!/usr/bin/env python3
"""`plan --migrate` derives an entry's axis from the plugin, or asks; it never writes `unit` from
nothing (autodev W019, GAP-C42).

FOUND BY THE BLIND CONVERSION OF de (scProfile docs/MIGRATIONS.md, autodev W013): `--migrate`
printed each of de's six figures with `axis: unit` - a plugin that runs ONCE over the whole cohort,
whose plates would then have been counted per sample and per group, and placed on pages that do not
exist for it. The default was the shape of the one plugin the maker was built on.

Whether a plugin runs once per unit is a field of its own declaration, and only the target
repository knows its name: the plan stage may name it (`entry_keys.per_unit`). Set, an entry the
legacy axis map does not place is `unit`; empty, `cohort`. Not named, the maker asks - the
placeholder, counted among what a person still owes. The legacy map, where it places an entry, still
decides: it is the plugin's own statement.

Run: PYTHONPATH=. python3 tests/test_migrate_never_guesses_an_axis.py
"""
from __future__ import annotations

import ast
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sch.dev import convert as CV                                          # noqa: E402
from sch.dev import points as P                                            # noqa: E402

DEVPOINTS = """\
tool: quarry
devpoints: 1
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
            skips: report.skips
{per_unit}
          each_item_declares:
            drawn_by: [tool, plugin]
            axis: [unit, contrast, cohort]
            position: [overview, contrast, conclusion, appendix]
            legend: []
          places_every:
            - {{field: native_plots, named_by: use, per_item: "<", bound: at_most}}
            - {{field: report.figures, named_by: id}}
          axis_field: report.figure_axis
          positions: [overview, contrast, conclusion, appendix]
          axes: [unit, contrast, cohort]
          why: the plan
"""

# A plugin as de was before its migration: its own figures, none with an axis, no prefix map that
# reaches them, and one the map does reach.
def plugin(runs_per_unit: bool) -> str:
    return (
        'PLUGIN = {\n'
        '    "api": 1,\n'
        '    "wraps": {"tool": "quarrytool"},\n'
        + ('    "per_unit": "sample",\n' if runs_per_unit else "")
        + '    "native_plots": {\n'
        '        "quarry_heat": {"use": "figures/native_heat.png per unit"},\n'
        '    },\n'
        '    "report": {\n'
        '        "figures": [\n'
        '            {"id": "F1_replicates", "drawn_by": "plugin", "legend": "Replicates."},\n'
        '            {"id": "F5_ma", "drawn_by": "plugin", "legend": "An MA plot."},\n'
        '            {"id": "X1_summary", "drawn_by": "plugin", "legend": "A summary."},\n'
        '        ],\n'
        '        "figure_axis": {"X1_": "contrast"},\n'
        '    },\n'
        '}\n')


def _repo(per_unit_key: str, runs_per_unit: bool):
    d = Path(tempfile.mkdtemp(prefix="sch-c42-"))
    (d / "seams").mkdir()
    (d / "seams" / "alpha.py").write_text(plugin(runs_per_unit), encoding="utf-8")
    line = f"            per_unit: {per_unit_key}" if per_unit_key else ""
    (d / "DEVPOINTS.yaml").write_text(DEVPOINTS.format(per_unit=line), encoding="utf-8")
    return d


def _migrated(d):
    doc = P.load(d)
    spec = dict(CV._convert_specs_for_ladder(doc, "seam"))["alpha"]
    text = CV.migrate_worksheet(spec, doc, "seam", "alpha")
    body = "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("#"))
    plan = ast.literal_eval("{" + body + "}")
    return text, {e["id"]: e for e in plan["figures"]}


class MigrateNeverGuessesAnAxis(unittest.TestCase):

    def tearDown(self):
        shutil.rmtree(getattr(self, "d", ""), ignore_errors=True)

    def test_a_plugin_that_runs_once_over_the_cohort_gets_cohort(self):
        self.d = _repo("per_unit", runs_per_unit=False)
        text, by_id = _migrated(self.d)
        for fid in ("F1_replicates", "F5_ma", "native_heat"):
            self.assertEqual(by_id[fid]["axis"], "cohort", (fid, text))
        self.assertIn("once over the whole cohort", text)

    def test_a_plugin_that_runs_per_unit_gets_unit(self):
        self.d = _repo("per_unit", runs_per_unit=True)
        _text, by_id = _migrated(self.d)
        for fid in ("F1_replicates", "F5_ma", "native_heat"):
            self.assertEqual(by_id[fid]["axis"], "unit", fid)

    def test_the_legacy_map_still_places_what_it_reaches(self):
        for per_unit in (True, False):
            self.d = _repo("per_unit", runs_per_unit=per_unit)
            _text, by_id = _migrated(self.d)
            self.assertEqual(by_id["X1_summary"]["axis"], "contrast")
            shutil.rmtree(self.d, ignore_errors=True)

    def test_without_the_declaration_the_axis_is_asked_and_counted(self):
        self.d = _repo("", runs_per_unit=False)
        text, by_id = _migrated(self.d)
        for fid in ("F1_replicates", "F5_ma", "native_heat"):
            self.assertTrue(by_id[fid]["axis"].startswith("TODO - unit or cohort"), by_id[fid])
        self.assertNotIn("'axis': 'unit'", text)
        head = text.splitlines()[0]
        n = int(head.split(" field(s) left for a person")[0].rsplit(", ", 1)[1])
        self.assertGreaterEqual(n, 3, head)            # the three asked axes are counted

    def test_through_the_real_cli(self):
        self.d = _repo("per_unit", runs_per_unit=False)
        env = dict(os.environ, PYTHONPATH=str(ROOT))
        p = subprocess.run([sys.executable, "-m", "sch", "dev", "convert", "plan", "--migrate",
                            "--root", str(self.d), "--point", "seam", "--name", "alpha"],
                           capture_output=True, text=True, env=env, cwd=str(ROOT), timeout=120)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("'axis': 'cohort'", p.stdout)
        self.assertNotIn("'axis': 'unit'", p.stdout)


if __name__ == "__main__":
    unittest.main()
