#!/usr/bin/env python3
"""`sch dev edit` writes what it adds the way the file around it is written (autodev W019,
GAP-C43).

FOUND BY THE BLIND CONVERSION OF de (scProfile docs/MIGRATIONS.md, autodev W013). de's figure plan
went in through this verb, and every legend, position and axis it added landed on its entry's first
line, after the id: six lines of 400 to 660 characters in a file whose other lines stay under 100.
The verb exists so that nobody edits a plugin by hand; what it writes is then read by people, and
has to look like what a person wrote - a new key on its own line, indented like its neighbours,
and a long string as adjacent literals inside the file's own margin.

THE ENTRY BELOW IS de's OWN SHAPE at its blind record: several keys on the first line, one key a
line after it, a string already wrapped, the brace closing on the last value. Every value written
here must read back exactly; nothing else in the file may move.

Run: PYTHONPATH=. python3 tests/test_an_inserted_key_is_wrapped_like_its_file.py
"""
from __future__ import annotations

import ast
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sch.dev import edit as E                                                    # noqa: E402

KEYS = {"upstream": "fn", "bound": "at_most", "axis": "axis", "position": "position",
        "skips": "report.skips", "version": "version"}

PLUGIN = textwrap.dedent('''\
    PLUGIN = {
        "name": "pooled",
        "version": "0.2.0",
        "cannot_show": [
            "A gene absent from the object was not tested, and its absence is not evidence of no "
            "change.",
            "PSEUDOBULK CANNOT SEE A CHANGE CONFINED TO A SUBPOPULATION of a labelled type.",
        ],
        "report": {
            "figures": [
                # THE CHECKS FIRST. A comment the author left, and must keep.
                {"id": "F1_replicates", "drawn_by": "plugin", "shows": "diagnostic", "required": True,
                 "question": "how many cells and how many counts went into each pseudobulk sample, "
                             "and is that balanced across the levels being compared?",
                 "source": "figures/F1_replicates.csv"},
                {"id": "F5_ma", "drawn_by": "plugin", "shows": "result", "required": True,
                 "question": "which genes change?",
                 "source": "tables/de_by_population.csv"},
            ],
            "skips": {
                'plot_counts': {'skip': 'not_applicable', 'evidence': 'no counts'},
            },
        },
    }


    def run(ctx):
        return ctx
    ''')

# de's own legend for F1, as W013's plan wrote it
LEGEND = ("Cells and counts summed into each pseudobulk sample, per population and level of the "
          "first contrasted factor, so an imbalance between the levels compared is visible before "
          "any result; a grey point is a population whose units fell below min_cells and formed "
          "no sample.")


def margin_of(text):
    """The file's right margin as the verb reads it: the 95th percentile of its non-blank line
    lengths, never under 79. Computed here as well, so the base is held to the same number."""
    lens = sorted(len(ln) for ln in text.splitlines() if ln.strip())
    return max(79, lens[min(len(lens) - 1, int(0.95 * len(lens)))])


MARGIN = margin_of(PLUGIN)


def spec_of(text):
    tree = ast.parse(text)
    node = next(n for n in tree.body if isinstance(n, ast.Assign) and n.targets[0].id == "PLUGIN")
    return ast.literal_eval(node.value)


def entry(spec, fid):
    return next(e for e in spec["report"]["figures"] if e["id"] == fid)


class AnInsertedKeyIsWrappedLikeItsFile(unittest.TestCase):

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.f = Path(self.td.name) / "pooled.py"
        self.f.write_text(PLUGIN, encoding="utf-8")
        self.margin = MARGIN

    def tearDown(self):
        self.td.cleanup()

    def edit(self, ops):
        E.edit(self.f, ops, KEYS)
        return self.f.read_text(encoding="utf-8")

    def assert_inside_the_margin(self, text):
        long = [ln for ln in text.splitlines() if len(ln) > self.margin and ln not in PLUGIN]
        self.assertEqual(long, [], f"lines past the file's margin of {self.margin}")

    def test_the_margin_is_the_files_own(self):
        self.assertEqual(E._margin(PLUGIN), MARGIN)
        self.assertGreaterEqual(MARGIN, 79)
        self.assertLessEqual(MARGIN, max(len(ln) for ln in PLUGIN.splitlines()))

    def test_the_plan_w013_wrote_lands_like_the_entry_it_is_written_into(self):
        out = self.edit([("set", "report.figures[F1_replicates].legend", LEGEND),
                         ("set", "report.figures[F1_replicates].position", "overview"),
                         ("set", "report.figures[F1_replicates].axis", "cohort")])
        e = entry(spec_of(out), "F1_replicates")
        self.assertEqual((e["legend"], e["position"], e["axis"]), (LEGEND, "overview", "cohort"))
        self.assert_inside_the_margin(out)
        # each on its own line, indented like the keys that have their own lines, in the
        # entry's quote style
        for k in ("legend", "position", "axis"):
            line = next(ln for ln in out.splitlines() if ln.lstrip().startswith(f'"{k}"'))
            self.assertEqual(len(line) - len(line.lstrip()), 13, line)
        self.assertIn("# THE CHECKS FIRST.", out)
        self.assertEqual(entry(spec_of(out), "F5_ma"), entry(spec_of(PLUGIN), "F5_ma"))

    def test_an_added_entry_and_a_sentence_added_to_a_list_are_wrapped_too(self):
        out = self.edit([("add", {"id": "F7_new", "drawn_by": "plugin", "axis": "cohort",
                                  "position": "overview", "legend": LEGEND}),
                         ("list_add", "cannot_show", LEGEND)])
        spec = spec_of(out)
        self.assertEqual(entry(spec, "F7_new")["legend"], LEGEND)
        self.assertEqual(spec["cannot_show"][-1], LEGEND)
        self.assert_inside_the_margin(out)

    def test_a_long_value_replaced_in_place_is_wrapped_from_where_it_starts(self):
        out = self.edit([("set", "report.figures[F5_ma].question", LEGEND)])
        self.assertEqual(entry(spec_of(out), "F5_ma")["question"], LEGEND)
        self.assert_inside_the_margin(out)

    def test_a_one_line_mapping_stays_one_line_while_it_fits_and_wraps_when_it_does_not(self):
        out = self.edit([("set", "report.skips.plot_counts.n", 2)])
        self.assertEqual(spec_of(out)["report"]["skips"]["plot_counts"]["n"], 2)
        self.assertEqual(len(out.splitlines()), len(PLUGIN.splitlines()))
        self.assertIn("{'skip': 'not_applicable', 'n': 2, 'evidence': 'no counts'}", out)
        out = self.edit([("set", "report.skips.plot_counts.why", LEGEND)])
        self.assertEqual(spec_of(out)["report"]["skips"]["plot_counts"]["why"], LEGEND)
        self.assert_inside_the_margin(out)

    def test_a_string_with_both_quotes_and_a_backslash_reads_back_exactly(self):
        odd = ("It's the \"control\" level - a path like C:\\data\\x - " * 4).strip()
        out = self.edit([("set", "report.figures[F1_replicates].legend", odd)])
        self.assertEqual(entry(spec_of(out), "F1_replicates")["legend"], odd)
        self.assert_inside_the_margin(out)


class ThroughTheRealCli(unittest.TestCase):

    def test_sch_dev_edit_writes_a_legend_inside_the_margin(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "kernels").mkdir()
            (d / "kernels" / "pooled.py").write_text(PLUGIN, encoding="utf-8")
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
                          entry_keys: {upstream: fn, bound: at_most, axis: axis, position: position, skips: report.skips}
                """), encoding="utf-8")
            env = dict(os.environ, PYTHONPATH=str(ROOT))
            p = subprocess.run([sys.executable, "-m", "sch", "dev", "edit", "--root", str(d),
                                "--point", "kernel", "--name", "pooled",
                                "--legend", "F1_replicates", LEGEND],
                               capture_output=True, text=True, env=env, cwd=str(ROOT), timeout=120)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            out = (d / "kernels" / "pooled.py").read_text(encoding="utf-8")
            self.assertEqual(entry(spec_of(out), "F1_replicates")["legend"], LEGEND)
            self.assertEqual([ln for ln in out.splitlines() if len(ln) > MARGIN and ln not in PLUGIN],
                             [])


if __name__ == "__main__":
    unittest.main()
