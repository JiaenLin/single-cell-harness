#!/usr/bin/env python3
"""The program's ledgers are only as good as their join to the goals.

autodev/ (ADR-0028) records the development toward GOALS.md in five append-only TSVs. A ledger
that names a goal id GOALS.md does not have, or an audit row whose columns are not GOALS.md's
layer-3 tests, records progress toward a goal nobody set. Rule 5 of autodev/RULES.md bans a wave
that moves no goal, and that ban only holds if the goal ids it names are real.

WHAT IS ASSERTED HERE.

  EVERY LEDGER IS RECTANGULAR. Each TSV has its declared header, and every row has exactly as many
  fields as the header. A tab inside a free-text cell would silently shift every later column.

  THE AUDIT'S COLUMNS ARE THE GOALS' TESTS. audits.tsv carries one column per layer-3 test, in
  GOALS.md's order. A test added to GOALS.md without a column, or a column whose test was removed,
  fails here.

  EVERY GOAL ID NAMED IS A GOAL ID THAT EXISTS. This covers the gap rows and the wave rows, and a
  wave's gap ids must be gaps that were opened.
"""
import csv
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "autodev" / "ledger"

HEADERS = {
    "gaps.tsv": ["stamp", "pass", "gap_id", "status", "goal_ids", "repo", "size", "gap",
                 "evidence", "depends_on", "blocked_by", "first_move"],
    "waves.tsv": ["stamp", "wave_id", "lane", "repo", "branch", "goal_ids", "gap_ids",
                  "acceptance_check", "prediction", "status", "commits", "pbs_ids", "outcome",
                  "note"],
    "blockers.tsv": ["stamp", "blocker_id", "blocks", "class", "symptom", "root_cause",
                     "evidence", "action", "owner", "status"],
    "housekeeping.tsv": ["stamp", "pass", "kind", "target", "action", "reason"],
}
GAP_STATUS = {"open", "in_wave", "closed", "deferred", "lean"}
WAVE_STATUS = {"registered", "building", "gating", "verifying", "merged", "done", "held", "failed"}


def goals_text():
    return (ROOT / "GOALS.md").read_text(encoding="utf-8")


def goal_ids():
    """Layer-1 (G1..G7), layer-2 (QC.1 ...) and layer-3 (A1.1 ...) ids, as bolded in GOALS.md."""
    return set(re.findall(r"\*\*(G\d|(?:QC|ANNO|INT|PROF|HARN|PLAT)\.\d+|A\d\.\d)\b",
                          goals_text()))


def layer3_tests():
    """The layer-3 test ids, in GOALS.md order."""
    layer3 = goals_text().split("## Layer 3", 1)[1]
    return re.findall(r"^\| \*\*(A\d\.\d)\b", layer3, flags=re.M)


def rows(name):
    with open(LEDGER / name, encoding="utf-8", newline="") as fh:
        return list(csv.reader(fh, delimiter="\t"))


def split_ids(cell):
    return [x for x in re.split(r"[,\s]+", cell.strip()) if x and x != "-"]


class TheLedgersJoinTheGoals(unittest.TestCase):

    def test_goals_md_declares_its_ids(self):
        ids = goal_ids()
        for expected in ("G1", "G7", "QC.1", "HARN.4", "A1.1", "A7.1"):
            self.assertIn(expected, ids)
        self.assertEqual(len(layer3_tests()), len(set(layer3_tests())), "a layer-3 id repeats")

    def test_every_ledger_is_rectangular_with_its_header(self):
        for name, header in HEADERS.items():
            table = rows(name)
            self.assertEqual(table[0], header, name)
            for i, row in enumerate(table[1:], start=2):
                self.assertEqual(len(row), len(header), f"{name} line {i}: {len(row)} fields")

    def test_the_audit_columns_are_the_layer3_tests_in_order(self):
        table = rows("audits.tsv")
        header = table[0]
        self.assertEqual(header[:4], ["stamp", "pass", "kind", "verdict"])
        self.assertEqual(header[-1], "report")
        self.assertEqual(header[4:-1], layer3_tests())
        grades = {"PASS", "PARTIAL", "FAIL", "UNKNOWN", "DEFERRED", "-"}
        for i, row in enumerate(table[1:], start=2):
            self.assertEqual(len(row), len(header), f"audits.tsv line {i}")
            self.assertIn(row[3], {"HAPPY", "NOT HAPPY"}, f"audits.tsv line {i}")
            for cell in row[4:-1]:
                self.assertIn(cell, grades, f"audits.tsv line {i}: {cell!r}")

    def test_every_goal_id_named_exists(self):
        ids = goal_ids()
        gaps = rows("gaps.tsv")[1:]
        for row in gaps:
            rec = dict(zip(HEADERS["gaps.tsv"], row))
            self.assertIn(rec["status"], GAP_STATUS, rec["gap_id"])
            for gid in split_ids(rec["goal_ids"]):
                self.assertIn(gid, ids, f"{rec['gap_id']} names {gid}")
        opened = {dict(zip(HEADERS["gaps.tsv"], r))["gap_id"] for r in gaps}
        for row in rows("waves.tsv")[1:]:
            rec = dict(zip(HEADERS["waves.tsv"], row))
            self.assertIn(rec["status"], WAVE_STATUS, rec["wave_id"])
            self.assertTrue(split_ids(rec["goal_ids"]), f"{rec['wave_id']} moves no goal (rule 5)")
            for gid in split_ids(rec["goal_ids"]):
                self.assertIn(gid, ids, f"{rec['wave_id']} names {gid}")
            for gap in split_ids(rec["gap_ids"]):
                self.assertIn(gap, opened, f"{rec['wave_id']} names unopened {gap}")


if __name__ == "__main__":
    unittest.main()
