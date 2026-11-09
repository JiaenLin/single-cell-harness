"""A catalogue row says what the declaration says, or `not declared`; it never fills a gap (W016).

Four things an agent chooses a method by, and each has a way to be filled in silently.
- **The assay** (rule 2: single cells are not single nuclei). A row states the assays a plugin
  declares, verbatim, or `not declared`; it never assumes one. Where the code reads the run's assay,
  the lines are evidence beside the answer, not an answer.
- **The upstream version** (A4.3). A range is what a plugin was written against, not what it runs.
- **The DOI** (A4.3). Only the field counts, never a guess from the free-text citation.
- **Whether it ran on a cohort.** `recorded` from the tool's own record, or `unknown`, never `no`.

The design needs are read from the tool's own capability vocabulary, never from a list here.
"""
from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from catalogue_fixture import (catalogue_json, checkout, harness_plugin, plugin_source, rows, spec)

READS_ASSAY = '''
def guard(g):
    # the assay matters here, and this comment must not count
    if not g.assay:
        return "declare it"
    note = "assay"
    return getattr(g, "assay", None)
'''

SHA = "0123456789abcdef0123456789abcdef01234567"


class ACatalogueRowSaysOnlyWhatIsDeclared(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="sch-catalogue-"))
        cls.reads_src = plugin_source(spec(), READS_ASSAY)
        cls.co = checkout(cls.tmp / "checkout", {
            "alpha": plugin_source(spec()),
            "reads": cls.reads_src,
            "nuclei": plugin_source(spec(assays=["snrna"])),
            "both": plugin_source(spec(assays=["scrna", "snrna"])),
            "badstring": plugin_source(spec(assays="scrna")),
            "badempty": plugin_source(spec(assays=[])),
            "badmember": plugin_source(spec(assays=["scrna", 3])),
            # provenance
            "pinwraps": plugin_source(spec(wraps={"tool": "toola", "version": "1.2.3",
                                                  "doi": "10.1234/abcd.5678"})),
            "pinpkg": plugin_source(spec(wraps={"tool": "tool_b"},
                                         requires={"packages": {"Tool-B": "==2.0.1"}})),
            "pinremote": plugin_source(spec(wraps={"tool": "ToolC", "doi": ["10.1/x", "10.2/y"]},
                                            requires={"r": ["Other==1.0", f"someone/ToolC@{SHA}"]})),
            "range": plugin_source(spec(wraps={"tool": "toold"},
                                        requires={"packages": {"toold": ">=1.0,<2"}})),
            "wildcard": plugin_source(spec(wraps={"tool": "toolw"},
                                           requires={"packages": {"toolw": "==1.*"}})),
            "branch": plugin_source(spec(wraps={"tool": "toole", "cite": "doi:10.9999/in.the.text"},
                                         requires={"r": ["someone/toole@main"]})),
            "wrapsrange": plugin_source(spec(wraps={"tool": "toolf", "version": ">=1.0"})),
            "nowraps": plugin_source(spec()),
            "baddoi": plugin_source(spec(wraps={"tool": "toolg", "doi": 1234})),
            # design, read from the tool's vocabulary
            "designed": plugin_source(spec(inject={"required": ["counts", "design"],
                                                   "optional": ["contrast", "ordering", "mystery"]},
                                           design_aware=True)),
            # the directory contract's kernel fields, as ADR-0030 adds them to the one-file layout
            "kernelish": plugin_source(spec(**{"class": "probe", "layer": "stack", "reversible": True,
                                               "gates": {"a_gate": "required"},
                                               "no_runtime_invariant": "a pure read of its input",
                                               "services": ["dataset"], "sourceable": ["spliced"],
                                               "measures_with": "a_probe", "verdict": ["PASS", "REFUSE"],
                                               "escape": "--allow", "rebuild_from": {"inputs": ["x"]}})),
            "fetches": plugin_source(spec(needs={"layers": ["spliced"]}, can_source_layers=True)),
        })
        cls.site = cls.tmp / "site"
        harness_plugin(cls.site, "dirassay", profile="single-cell/1.0", needs='["matrix/{counts}"]')
        with open(cls.site / "dirassay" / "plugin.yml", "a") as f:
            f.write("assays: [scrna]\nwraps:\n  tool: toolh\n")
        harness_plugin(cls.site, "dirlock", extra={"lock.yml": (
            "name: t\ndependencies:\n  - python=3.12\n  - pip\n  - pip: [toolh==3.1.4, other==1.0]\n")})
        with open(cls.site / "dirlock" / "plugin.yml", "a") as f:
            f.write("wraps:\n  tool: toolh\n")
        harness_plugin(cls.site, "dirconda", extra={"lock.yml": (
            "name: t\ndependencies:\n  - toolh=3.1\n")})
        with open(cls.site / "dirconda" / "plugin.yml", "a") as f:
            f.write("wraps:\n  tool: toolh\n")
        cls.rc, cls.doc = catalogue_json("--scprofile", str(cls.co), plugins=str(cls.site))
        cls.rows = rows(cls.doc)
        cls.site_rows = rows(cls.doc, "harness")
        cls.errors = {e["path"]: e["error"] for e in cls.doc["errors"]}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_an_undeclared_assay_is_not_declared_even_when_the_code_reads_one(self):
        r = self.rows["scprofile:reads"]
        self.assertEqual(r["inputs"]["assays"], "not declared")
        lines = [i for i, line in enumerate(self.reads_src.splitlines(), 1)
                 if "g.assay" in line or '"assay", None' in line]
        self.assertEqual(len(lines), 2)
        self.assertEqual(r["inputs"]["assay_read_at"], [f"kernels/reads.py:{i}" for i in lines],
                         "the code's reads are evidence; the comment and the plain string are not")
        self.assertEqual(self.rows["scprofile:alpha"]["inputs"]["assays"], "not declared")
        self.assertEqual(self.rows["scprofile:alpha"]["inputs"]["assay_read_at"], [])
        for row in self.doc["plugins"]:
            if row["inputs"]["assays"] != "not declared":
                self.assertIsInstance(row["inputs"]["assays"], list, row["id"])

    def test_a_declared_assay_set_is_reported_verbatim(self):
        self.assertEqual(self.rows["scprofile:nuclei"]["inputs"]["assays"], ["snrna"])
        self.assertEqual(self.rows["scprofile:both"]["inputs"]["assays"], ["scrna", "snrna"])
        self.assertEqual(self.site_rows["harness:single-cell/dirassay"]["inputs"]["assays"], ["scrna"])

    def test_a_malformed_assay_declaration_is_an_error(self):
        self.assertEqual(self.rc, 2)
        for name in ("badstring", "badempty", "badmember"):
            path = f"kernels/{name}.py"
            self.assertIn(path, self.errors)
            self.assertIn("assays", self.errors[path])
            self.assertNotIn(f"scprofile:{name}", self.rows)

    def test_an_exact_pin_is_found_where_it_is_declared(self):
        def pin(rid, rows=None):
            p = (rows or self.rows)[rid]["provenance"]
            return p["version"], p["version_from"]
        self.assertEqual(pin("scprofile:pinwraps"), ("1.2.3", "wraps.version"))
        self.assertEqual(pin("scprofile:pinpkg"), ("2.0.1", "requires.packages.Tool-B"))
        self.assertEqual(pin("scprofile:pinremote"), (SHA, "requires.r"))
        self.assertEqual(pin("harness:table/dirlock", self.site_rows), ("3.1.4", "lock.yml"))

    def test_a_range_or_a_branch_is_not_an_exact_pin(self):
        for rid, declared in (("scprofile:range", ">=1.0,<2"), ("scprofile:wildcard", "==1.*"),
                              ("scprofile:branch", "someone/toole@main"),
                              ("scprofile:wrapsrange", ">=1.0")):
            p = self.rows[rid]["provenance"]
            self.assertEqual(p["version"], "not declared", rid)
            self.assertIn(declared, p["version_declared_as"], rid)
        self.assertEqual(self.site_rows["harness:table/dirconda"]["provenance"]["version"], "not declared",
                         "a conda `=` is a prefix match, not a pin")
        none = self.rows["scprofile:nowraps"]["provenance"]
        self.assertEqual((none["upstream"], none["version"], none["doi"]),
                         ("not declared", "not declared", "not declared"))

    def test_a_doi_is_reported_only_from_its_field(self):
        self.assertEqual(self.rows["scprofile:pinwraps"]["provenance"]["doi"], "10.1234/abcd.5678")
        self.assertEqual(self.rows["scprofile:pinremote"]["provenance"]["doi"], ["10.1/x", "10.2/y"])
        self.assertEqual(self.rows["scprofile:branch"]["provenance"]["doi"], "not declared",
                         "a DOI inside the citation's prose is not a declaration")
        self.assertIn("kernels/baddoi.py", self.errors)
        self.assertIn("wraps.doi", self.errors["kernels/baddoi.py"])

    def test_design_needs_are_read_from_the_tool_vocabulary_never_guessed(self):
        i = self.rows["scprofile:designed"]["inputs"]
        self.assertEqual(i["design"]["required"], ["design"])
        self.assertEqual(i["design"]["optional"], ["contrast"])
        self.assertIs(i["design"]["per_arm"], True)
        self.assertIs(i["design"]["shown"], True)
        self.assertEqual(i["from_plugins"], ["ordering"])
        self.assertEqual(i["not_in_vocabulary"], ["mystery"])
        self.assertEqual(self.doc["vocabulary"]["scprofile"]["design"]["resolve"], "design")
        # NO VOCABULARY, NO GUESS: the same plugin in a checkout that does not state one.
        co = checkout(self.tmp / "novocab", {"designed": plugin_source(spec(
            inject={"required": ["counts", "design"], "optional": ["contrast"]}))}, vocabulary=None)
        rc, doc = catalogue_json("--scprofile", str(co))
        self.assertEqual(rc, 0, doc.get("errors"))
        i = rows(doc)["scprofile:designed"]["inputs"]
        self.assertEqual((i["design"]["required"], i["from_plugins"], i["design"]["shown"]),
                         ("unknown", "unknown", "unknown"))
        src = [s for s in doc["sources"] if s["name"] == "scprofile"][0]
        self.assertTrue(any("scprofile/declare.py" in w for w in src["warnings"]), src["warnings"])

    def test_the_kernel_fields_the_format_adds_are_read_from_one_file_too(self):
        rc, doc = catalogue_json("show", "scprofile:kernelish", "--scprofile", str(self.co))
        self.assertEqual(rc, 0, doc)
        d, i = doc["plugin"]["details"], doc["plugin"]["inputs"]
        self.assertEqual((d["class"], d["layer"], d["reversible"]), ("probe", "stack", True))
        self.assertEqual(d["gates"], {"a_gate": "required"})
        self.assertEqual(d["invariant"], {"none": "a pure read of its input"})
        self.assertEqual((d["measures_with"], d["verdict"], d["escape"], d["rebuild_from"]),
                         ("a_probe", ["PASS", "REFUSE"], "--allow", {"inputs": ["x"]}))
        self.assertEqual((i["services"], i["sourceable"]), (["dataset"], ["spliced"]))
        self.assertEqual(self.rows["scprofile:alpha"]["inputs"]["services"], "not declared")
        self.assertEqual(self.rows["scprofile:fetches"]["inputs"]["sourceable"], ["spliced"])
        self.assertEqual(self.rows["scprofile:alpha"]["inputs"]["sourceable"], [])

    def test_a_cohort_run_is_recorded_or_unknown_never_no(self):
        alpha = self.rows["scprofile:alpha"]
        self.assertEqual(alpha["ran_on_cohort"], "recorded")
        self.assertIn("rules.end_to_end", alpha["ran_on_cohort_record"])
        self.assertEqual({r["ran_on_cohort"] for rid, r in self.rows.items() if rid != "scprofile:alpha"},
                         {"unknown"})
        self.assertEqual({r["ran_on_cohort"] for r in self.doc["plugins"]} - {"recorded", "unknown"}, set())
        co = checkout(self.tmp / "norecords", {"alpha": plugin_source(spec())}, devpoints=None)
        rc, doc = catalogue_json("--scprofile", str(co))
        self.assertEqual(rows(doc)["scprofile:alpha"]["ran_on_cohort"], "unknown")


if __name__ == "__main__":
    unittest.main()
