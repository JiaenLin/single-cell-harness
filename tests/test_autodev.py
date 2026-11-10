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
    "decisions.tsv": ["stamp", "decision_id", "action", "reversible", "outward", "rules_searched",
                      "decides", "verdict", "decided_by", "where_recorded"],
    "scores.tsv": ["stamp", "pass", "test_id", "score", "numerator", "denominator", "evidence"],
}
USER_ONLY = ("promotion", "sign convention", "threshold the data cannot decide", "core rule or goal",
             "budget or token mode", "permission", "collaborator or vendor", "account")
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


class ThePreDeciderGate(unittest.TestCase):
    """autodev/PRE_DECIDER.md v2 (2026-11-10): a question reaches the PI only through the form."""

    def test_every_decision_row_is_well_formed_and_every_ask_names_a_user_only_clause(self):
        for i, row in enumerate(rows("decisions.tsv")[1:], start=2):
            rec = dict(zip(HEADERS["decisions.tsv"], row))
            self.assertRegex(rec["decision_id"], r"^D-\d{3}$", f"decisions.tsv line {i}")
            self.assertIn(rec["reversible"], {"yes", "no"}, f"decisions.tsv line {i}")
            self.assertIn(rec["outward"], {"yes", "no"}, f"decisions.tsv line {i}")
            self.assertIn(rec["verdict"], {"ACT", "DECLINE", "ASK"}, f"decisions.tsv line {i}")
            if rec["verdict"] == "ASK":
                self.assertTrue(any(c in rec["decided_by"] for c in USER_ONLY),
                                f"{rec['decision_id']} asks the PI without a user-only clause")

    def test_every_question_in_state_cites_an_ask_row(self):
        state = (ROOT / "autodev" / "STATE.md").read_text(encoding="utf-8")
        section = state.split("## Decisions needed from the PI", 1)[1].split("\n## ", 1)[0]
        asks = {dict(zip(HEADERS["decisions.tsv"], r))["decision_id"]
                for r in rows("decisions.tsv")[1:] if r[7] == "ASK"}
        for line in section.splitlines():
            if re.match(r"^\d+\. ", line):
                cited = re.findall(r"\bD-\d{3}\b", line)
                self.assertTrue(cited, f"a question without a decisions.tsv row: {line[:80]}")
                for d in cited:
                    self.assertIn(d, asks, f"{d} is cited as a question but is not an ASK row")

    def test_no_ask_repeats_a_catalogue_class(self):
        doc = (ROOT / "autodev" / "PRE_DECIDER.md").read_text(encoding="utf-8")
        catalogue = doc.split("## 4.", 1)[1].split("## 5.", 1)[0]
        classes = {m.strip().lower() for m in re.findall(r"^\| ([^|]+) \|", catalogue, flags=re.M)}
        classes -= {"class of question", "---"}
        for r in rows("decisions.tsv")[1:]:
            rec = dict(zip(HEADERS["decisions.tsv"], r))
            if rec["verdict"] == "ASK":
                self.assertNotIn(rec["action"].strip().lower(), classes,
                                 f"{rec['decision_id']} asks a question the catalogue answers")


class TheScoresAreMeasured(unittest.TestCase):
    """GOALS.md layer 3 scored (2026-11-10): a score is a numerator over a denominator, in [0, 1]."""

    def test_scores_rows(self):
        tests = set(layer3_tests())
        for i, row in enumerate(rows("scores.tsv")[1:], start=2):
            rec = dict(zip(HEADERS["scores.tsv"], row))
            self.assertIn(rec["test_id"], tests, f"scores.tsv line {i}")
            num, den, score = float(rec["numerator"]), float(rec["denominator"]), float(rec["score"])
            self.assertGreater(den, 0, f"scores.tsv line {i}")
            self.assertTrue(0 <= score <= 1, f"scores.tsv line {i}")
            self.assertAlmostEqual(score, min(1.0, num / den), places=3, msg=f"scores.tsv line {i}")
            self.assertTrue(rec["evidence"].strip(), f"scores.tsv line {i}: no evidence")


class TheHarnessPackageIsWhole(unittest.TestCase):
    """autodev/ is rebuilt from the repository alone (RULES tier IV, 2026-11-10): what a new session needs is here."""

    def test_every_layer3_test_has_a_score_formula(self):
        scored = goals_text().split("## Layer 3, scored", 1)[1].split("\n## ", 1)[0]
        formulas = re.findall(r"^\| (A\d\.\d) \|", scored, flags=re.M)
        self.assertEqual(formulas, layer3_tests(), "the scored table is not the layer-3 list in order")

    def test_the_tools_exist_and_the_shell_ones_parse(self):
        import subprocess
        tools = ROOT / "autodev" / "tools"
        for name in ("usage.py", "pbs_mirror.sh", "monitor_verdicts.sh", "bootstrap.sh"):
            self.assertTrue((tools / name).is_file(), name)
            if name.endswith(".sh"):
                rc = subprocess.run(["bash", "-n", str(tools / name)], capture_output=True)
                self.assertEqual(rc.returncode, 0, f"{name}: {rc.stderr.decode()[:200]}")

    def test_the_method_files_carry_their_sections(self):
        readme = (ROOT / "autodev" / "README.md").read_text(encoding="utf-8")
        for name in ("LOOP TICK", "BLOCKER SWEEP", "PERIODIC CHECK"):
            self.assertIn(f"| {name} |", readme, f"README's reminders table lacks {name}")
        self.assertIn("## The machinery", readme)
        briefs = (ROOT / "autodev" / "BRIEFS.md").read_text(encoding="utf-8")
        self.assertIn("## 0. The block every brief carries", briefs)
        pre = (ROOT / "autodev" / "PRE_DECIDER.md").read_text(encoding="utf-8")
        for sec in ("## 1.", "## 2.", "## 3.", "## 4.", "## 5."):
            self.assertIn(sec, pre, f"PRE_DECIDER.md lacks {sec}")
        rules = (ROOT / "autodev" / "RULES.md").read_text(encoding="utf-8")
        self.assertIn("## Added 2026-11-10 by the PI's", rules)


if __name__ == "__main__":
    unittest.main()
