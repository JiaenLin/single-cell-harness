"""A cohort's word list is GENERATED from its own records (W024, GAP-008).

WHAT WAS WRONG. Each cohort's `docs/forbidden_terms.txt` was written by hand once and never grew:
sample names, site strings and four comma-grouped counts. No factor level, no small count, no
"N of M", no margin. A tool's test fixture could carry the first cohort's age and diet levels, and
the scQC and scAnno fixtures did; a docstring could carry the first cohort's measured counts, and
W011's builder and verifier found 59 of them by hand - all invisible to the list.

WHAT `sch conform terms build COHORT --out FILE` DOES. It reads the cohort's sheets and records
and writes a list in which every term sits under the line it came from. It reads the cohort and
never writes to it: the list holds the cohort's strings by design, so it lives outside every
repository, and the coordinator installs it after review.

The cohort below is invented, and so is every word and number in it.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import ROOT
from sch.conform import conform_repo

ENV = ("SCH_SITE_TERMS", "SCH_SITE", "SCH_SITE_SHAPES", "SCH_FORBIDDEN_TERMS")

DESIGN = """sample,age,batch,chemistry,diet,dose
QxA1,elderfold,A,KIT-V2,lardmash,1.5
QxA2,elderfold,B,KIT-V2,lardmash,2.0
QxB1,sprigling,A,KIT-V3,kibbleon,1.5
QxB2,sprigling,B,KIT-V3,kibbleon,2.0
"""
SHEET = ("# a comment line the reader skips\n"
         "sample\tspecies\tassay\tmatrix\tgenotype\tstrain\tdbr\n"
         "QxA1\tmus_zz\tsnrna\t/data/x/QxA1/raw\tQz\tVxa\t0.051\n"
         "QxA2\tmus_zz\tsnrna\t/data/x/QxA2/raw\tQz\tVxa\t0.063\n"
         "QxB1\tmus_zz\tsnrna\t/data/x/QxB1/raw\tQy\tVxb\t0.058\n"
         "QxB2\tmus_zz\tsnrna\t/data/x/QxB2/raw\tQy\tVxb\t0.071\n")
RUNLOG = """# Stage 01 run log
kept 7,481 of 58,213 nuclei after QC; 2,000 HVGs were chosen.
29 nuclei carried the flag; held 637 for review.
observed in 13 of 77 animals, and 1 of 3 runs.
mito share 41.7% (thresholds 5.0% and 2.5%).
best AUC 0.7319 and gap 0.83; ratio 318.27x; python 3.12.13.
settings, not measurements: 100.0 and 25.00; scale 1.4826 x MAD; 0.1% floor; top-20 markers; <300 reads.
job 123457 read the matrix, and a 50 gene signature is a set, not a count.
Removed 2026-08-06: the stale run. kept 2025-01-31 as the cut.
PBS 4567890 sealed the rerun; queue `blipq` held it for an hour.
"""


def term_lines(text):
    """[(term line, the comment line above it)] for every term the list holds."""
    lines = text.splitlines()
    return [(l, lines[i - 1] if i else "") for i, l in enumerate(lines)
            if l.strip() and not l.lstrip().startswith("#")]


class ACohortWordListIsGeneratedFromItsRecords(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="sch-terms-build-"))
        c = cls.cohort = cls.tmp / "Qox_cohort"
        for rel, text in {
            "docs/forbidden_terms.txt": "# the hand list\nqoxcohort\nQx_ARM\n",
            "stages/04_profile/design.csv": DESIGN,
            "stages/01_qc/samplesheet.tsv": SHEET,
            "stages/01_qc/RUNLOG.md": RUNLOG,
            "stages/02_x/DECISIONS.md": "D1: kept 9,163 droplets.\n",
            "stages/02_x/PROTOCOL.md": "expected 4,417 cells per library.\n",
            "stages/02_x/NOTES.md": "8,888 is in a file that is not a record.\n",
            "results/02_x/PROMOTED.md": "promoted with 6,029 labels.\n",
            "README.md": "# the cohort\nthe doublet share reached 66.9% in one library.\n",
            "docs/PORTABILITY.md": "a ceiling of 71.45% on the worst library.\n",
            "docs/site_shapes.txt": "\\bzz-\\d{2}\\b :: a zz login node :: zz-\n",
            "stages/01_qc/jobs/qc.pbs": "#!/bin/bash\n#PBS -q zappq\n#PBS -l walltime=01:00:00\n",
        }.items():
            p = c / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
        cls.stems = cls.tmp / "stems.txt"
        cls.stems.write_text("# hand-kept stems of the first study\n"
                             "# a stem of the study's tissue\nword:fibrozor*\n"
                             "not: a phrase about shapes :: a description of a leak's shape, "
                             "not a string\n")
        cls.carry = cls.tmp / "carry.txt"
        cls.carry.write_text("# handed back by an earlier wave\nheld 637\n58,?213\n"
                             "zz unseen phrase\nqoxcohort\na phrase about shapes\n")
        from sch.conform.terms import build
        cls.out = cls.tmp / "out" / "terms.txt"
        cls.shapes = cls.tmp / "out" / "shapes.txt"
        cls.summary = build(c, cls.out, stems=[cls.stems], carry=[cls.carry], shapes_out=cls.shapes)
        cls.text = cls.out.read_text()
        cls.terms = [t for t, _ in term_lines(cls.text)]
        cls.above = dict(term_lines(cls.text))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_the_hand_list_is_carried_first_and_verbatim(self):
        self.assertEqual(self.terms[:2], ["qoxcohort", "Qx_ARM"])
        self.assertEqual(self.terms.count("qoxcohort"), 1, "a carried term is listed once")

    def test_samples_and_levels_come_from_the_sheets_and_axes_do_not(self):
        for t in ("word:QxA1", "word:QxA2", "word:QxB1", "word:QxB2", "word:elderfold",
                  "word:sprigling", "word:lardmash", "word:kibbleon", "exact:Qz", "exact:Qy",
                  "word:Vxa", "word:Vxb"):
            self.assertIn(t, self.terms)
        for absent in ("KIT-V2", "KIT-V3", "mus_zz", "snrna", "/data/x", "1.5", "0.051"):
            self.assertFalse(any(absent in t for t in self.terms), absent)

    def test_a_one_character_level_is_dropped_and_the_drop_is_written_down(self):
        self.assertFalse(any(t.split(":", 1)[-1] in ("A", "B") for t in self.terms))
        self.assertTrue(re.search(r"^#.*'A'.*batch", self.text, re.M), "the drop is not said")

    def test_the_records_numbers_follow_the_rules(self):
        for t in ("word:7,481", "word:58,213", "word:58213", "word:9,163", "word:4,417",
                  "word:6,029", "word:7,481 of 58,213", "word:13 of 77", "word:29 nuclei",
                  "word:held 637", "word:77 animals", "word:41.7%", "word:AUC 0.7319",
                  "word:gap 0.83", "word:0.7319", "word:318.27"):
            self.assertIn(t, self.terms)
        for t in ("word:2,000", "word:2000", "word:7481", "word:1 of 3", "word:5.0%", "word:2.5%",
                  "word:3.12", "word:12.13", "word:8,888", "word:213 nuclei", "word:0.83"):
            self.assertNotIn(t, self.terms)

    def test_a_level_of_three_characters_or_more_matches_in_any_case(self):
        """The verifier found a three-letter diet level in lowercase in two tools' fixtures, unmatched by a level
        written in capitals (W024 fix-up). From three characters a recased copy is the leak's
        shape, so the level matches in any case; a two-character level keeps its own case,
        because in another case it is overwhelmingly an identifier (`wt`, gzip's "wt" mode)."""
        self.assertIn("word:Vxa", self.terms)
        self.assertIn("exact:Qz", self.terms)
        saved = {k: os.environ.pop(k, None) for k in ENV}
        tool = self.tmp / "tool_case"
        try:
            (tool / "tests").mkdir(parents=True)
            (tool / "tests" / "test_rows.py").write_text("ROWS = [{'strain': 'vxa'}]\nqz = 1\n")
            s1 = [c for c in conform_repo(tool, terms_file=str(self.out)) if c["id"].startswith("S1 ")][0]
            found = [e for e in s1["evidence"] if " site term " in e]
            self.assertEqual([e.split(" site term ")[0] for e in found], ["tests/test_rows.py:1"], found)
        finally:
            for k, v in saved.items():
                if v is not None:
                    os.environ[k] = v

    def test_the_cohorts_readme_and_docs_are_read(self):
        """The first cohort's README and a portability note in its docs carried measured percentages the
        records did not, and the list missed them (W024 fix-up)."""
        self.assertIn("word:66.9%", self.terms)
        self.assertIn("word:71.45%", self.terms)
        self.assertIn("README.md:2", self.above["word:66.9%"])

    def test_a_date_is_not_a_count(self):
        """`Removed 2026` was listed from `Removed 2026-08-06` (W024 fix-up)."""
        self.assertFalse(any("2026" in t or "2025" in t for t in self.terms), self.terms)

    def test_queues_and_bare_job_ids_are_generated_as_site_shapes(self):
        """A queue the cohort's jobs name, and a job id written bare as its records write it,
        are the site's shapes rather than words; they go to a shapes list, beside the site's own
        shapes carried verbatim (W024 fix-up)."""
        text = self.shapes.read_text()
        self.assertIn(r"\bzz-\d{2}\b :: a zz login node :: zz-", text)
        self.assertIn(r"\bPBS \d{7}\b", text)
        self.assertRegex(text, r"(?m)^\S*blipq\S* :: ")
        self.assertRegex(text, r"(?m)^\S*zappq\S* :: ")
        saved = {k: os.environ.pop(k, None) for k in ENV}
        tool = self.tmp / "tool_shapes"
        try:
            (tool / "jobs").mkdir(parents=True)
            (tool / "jobs" / "run.pbs").write_text("#PBS -q zappq\n# rerun of PBS 1234567\nqsub -q other\n")
            s1 = [c for c in conform_repo(tool, shapes_file=str(self.shapes)) if c["id"].startswith("S1 ")][0]
            lines = sorted({e.split(" ")[0] for e in s1["evidence"] if e.startswith("jobs/")})
            self.assertEqual(lines, ["jobs/run.pbs:1", "jobs/run.pbs:2"], s1["evidence"])
        finally:
            for k, v in saved.items():
                if v is not None:
                    os.environ[k] = v

    def test_a_setting_or_a_constant_is_not_taken_for_a_measurement(self):
        """Measured on the eight repositories (W024): a round decimal, a statistical constant, a
        one-digit percentage, a top-N and a threshold after `<` were listed and found in tools
        that legitimately hold them - `100.0 *` in every percentage, MAD's 1.4826, top-20. And a
        live record wrote a job id before the verb "read": a count of ten or more is plural."""
        for t in ("word:100.0", "word:25.00", "word:1.4826", "word:0.1%", "word:20 markers",
                  "word:300 reads", "word:123457 read", "word:50 gene"):
            self.assertNotIn(t, self.terms)

    def test_every_term_carries_its_source_line(self):
        for t, above in self.above.items():
            self.assertRegex(above, r"^# \[[a-z]+\] \S+:\d+", f"{t} has no source line above it")
        self.assertIn("stages/04_profile/design.csv:2", self.above["word:elderfold"])
        self.assertIn("stages/01_qc/RUNLOG.md:2", self.above["word:7,481"])

    def test_a_handed_back_term_names_its_list_and_where_the_cohort_says_it(self):
        self.assertIn("word:zz unseen phrase", self.terms)
        self.assertIn("carry.txt:4", self.above["word:zz unseen phrase"])
        self.assertIn("not in the cohort's text", self.above["word:zz unseen phrase"])
        self.assertIn("carry.txt:2", self.above["word:held 637"])          # also generated: one line
        self.assertEqual(self.terms.count("word:held 637"), 1)
        self.assertFalse(any("58,?213" in t for t in self.terms), "a pattern is not a term")
        self.assertTrue(re.search(r"^#.*58,\?213.*pattern", self.text, re.M))

    def test_a_handed_back_line_the_stems_call_no_term_is_said_not_listed(self):
        """A person decides that a handed-back line describes a leak rather than spelling one;
        the decision lives in the hand-kept stems file, and the list says it."""
        self.assertFalse(any("a phrase about shapes" in t for t in self.terms))
        self.assertTrue(re.search(r"^# not listed: a phrase about shapes \(carry\.txt:6\): "
                                  r"a description of a leak's shape", self.text, re.M), self.text[-600:])

    def test_the_stems_are_carried_with_their_reason(self):
        self.assertIn("word:fibrozor*", self.terms)
        self.assertIn("stems.txt:3", self.above["word:fibrozor*"])
        self.assertIn("a stem of the study's tissue", self.above["word:fibrozor*"])

    def test_a_record_that_is_not_one_of_the_named_kinds_is_not_read(self):
        self.assertFalse(any("8,888" in t for t in self.terms))

    def test_it_refuses_to_write_into_the_cohort(self):
        from sch.conform.terms import build
        for inside in (self.cohort / "docs" / "forbidden_terms.txt", self.cohort / "list.txt"):
            with self.assertRaises(ValueError):
                build(self.cohort, inside)
        self.assertEqual((self.cohort / "docs" / "forbidden_terms.txt").read_text(),
                         "# the hand list\nqoxcohort\nQx_ARM\n")

    def test_a_generated_list_is_never_read_back_as_the_hand_list(self):
        """Installed over the hand list, a generated list would be carried verbatim by the next
        build, and no term could ever leave it. It is installed beside the hand list."""
        from sch.conform.terms import build
        twin = self.tmp / "twin"
        shutil.copytree(self.cohort, twin)
        shutil.copy(self.out, twin / "docs" / "forbidden_terms.txt")
        with self.assertRaises(ValueError) as e:
            build(twin, self.tmp / "twin_out.txt")
        self.assertIn("beside", str(e.exception))

    def test_the_same_records_give_the_same_list(self):
        from sch.conform.terms import build
        again = self.tmp / "again.txt"
        build(self.cohort, again, stems=[self.stems], carry=[self.carry])
        strip = lambda s: [l for l in s.splitlines() if not l.startswith("# generated ")]
        self.assertEqual(strip(again.read_text()), strip(self.text))

    def test_s1_finds_a_generated_level_planted_in_a_tool_and_nothing_it_should_not(self):
        saved = {k: os.environ.pop(k, None) for k in ENV}
        tool = self.tmp / "tool"
        try:
            (tool / "tests").mkdir(parents=True)
            (tool / "tests" / "test_design.py").write_text(
                "ROWS = [{'sample': 's1', 'age': 'elderfold'}]\n")
            (tool / "docs").mkdir()
            (tool / "docs" / "notes.md").write_text(
                "the averaged scores of an elderfolded leaf; 17,481 rows; a qz variable\n")
            s1 = [c for c in conform_repo(tool, terms_file=str(self.out)) if c["id"].startswith("S1 ")][0]
            self.assertFalse(s1["ok"])
            found = [e for e in s1["evidence"] if " site term " in e]
            self.assertEqual([e.split(":")[0] for e in found], ["tests/test_design.py"], found)
        finally:
            for k, v in saved.items():
                if v is not None:
                    os.environ[k] = v

    def test_the_command_line_builds_it_and_requires_an_out(self):
        env = {k: v for k, v in os.environ.items() if k not in ENV}
        env["PYTHONPATH"] = str(ROOT)
        out = self.tmp / "cli" / "terms.txt"
        r = subprocess.run([sys.executable, "-m", "sch", "conform", "terms", "build", str(self.cohort),
                            "--out", str(out), "--stems", str(self.stems), "--carry", str(self.carry)],
                           capture_output=True, text=True, cwd=str(ROOT), env=env)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        self.assertTrue(out.is_file())
        self.assertIn(str(out), r.stdout)
        r = subprocess.run([sys.executable, "-m", "sch", "conform", "terms", "build", str(self.cohort)],
                           capture_output=True, text=True, cwd=str(ROOT), env=env)
        self.assertEqual(r.returncode, 2)
        self.assertIn("--out", r.stderr)


if __name__ == "__main__":
    unittest.main()
