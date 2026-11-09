"""The format column is the maker's verdict, read from the maker's declaration (W016, ADR-0030).

ADR-0030 adopts the maker's layout as the Universal Plugin Format. A one-file plugin reads `maker`
only when two things hold, and both come from the maker. First, no field that the maker's
declaration marks outstanding (`outstanding_if`) is set. Second, the record that only the maker
writes (`<name>.signatures.json`) sits beside the plugin. Without the maker's declaration there is
no verdict: the plugin reads `one-file`, never `maker`. The fixture's marker is not scProfile's
spelling, so a pass here shows that the marker was read, not known in advance.
"""
from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from catalogue_fixture import catalogue_json, checkout, plugin_source, rows, spec


class TheFormatColumnFollowsTheMaker(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="sch-catalogue-"))
        cls.plugins = {
            "alpha": plugin_source(spec()),
            "beta": plugin_source(spec(wraps={"tool": "toolb", "unreviewed": "nobody looked yet"})),
            "gamma": plugin_source(spec()),
            # scProfile's own spelling of the marker, which THIS declaration does not name.
            "delta": plugin_source(spec(wraps={"tool": "toold", "plots_unreviewed": "not looked"})),
        }
        cls.files = {
            "kernels/alpha.signatures.json": "{}",
            "kernels/alpha.draw.R": "# generated\n",
            "kernels/alpha.extra.py": "# a companion in Python is still a companion\n",
            "kernels/_helper.py": "HELPER = True\n",
            "kernels/beta.signatures.json": "{}",
            "kernels/delta.signatures.json": "{}",
            "kernels/old/kernel.yml": ("summary: the six-file shape\nneeds_layers:\n  - spliced\n"
                                       "cannot_show:\n  - nothing\n"),
            "kernels/old/run.py": "print('never run')\n",
        }
        cls.co = checkout(cls.tmp / "checkout", cls.plugins, files=cls.files)
        cls.rc, cls.doc = catalogue_json("--scprofile", str(cls.co))
        cls.rows = rows(cls.doc)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_the_maker_outstanding_marker_keeps_a_plugin_one_file(self):
        beta = self.rows["scprofile:beta"]
        self.assertEqual(beta["format"], "one-file")
        self.assertTrue(any("wraps.unreviewed" in e for e in beta["format_evidence"]), beta["format_evidence"])

    def test_no_marker_and_the_maker_record_is_the_maker_layout(self):
        self.assertEqual(self.rc, 0, self.doc.get("errors"))
        self.assertEqual(self.rows["scprofile:alpha"]["format"], "maker")
        gamma = self.rows["scprofile:gamma"]
        self.assertEqual(gamma["format"], "one-file")
        self.assertTrue(any("gamma.signatures.json" in e for e in gamma["format_evidence"]))
        self.assertEqual(self.rows["scprofile:delta"]["format"], "maker",
                         "a field the maker's declaration does not mark is not a marker")

    def test_without_the_maker_declaration_the_status_is_unknown_not_maker(self):
        co = checkout(self.tmp / "nodevpoints", self.plugins, files=self.files, devpoints=None)
        rc, doc = catalogue_json("--scprofile", str(co))
        self.assertEqual(rc, 0, doc.get("errors"))
        alpha = rows(doc)["scprofile:alpha"]
        self.assertEqual(alpha["format"], "one-file")
        self.assertTrue(any("unknown" in e for e in alpha["format_evidence"]), alpha["format_evidence"])
        self.assertNotIn("maker", {r["format"] for r in rows(doc).values()})
        src = [s for s in doc["sources"] if s["name"] == "scprofile"][0]
        self.assertTrue(any("DEVPOINTS.yaml" in w for w in src["warnings"]), src["warnings"])

    def test_a_companion_is_never_a_plugin(self):
        self.assertEqual(sorted(self.rows), ["scprofile:alpha", "scprofile:beta", "scprofile:delta",
                                             "scprofile:gamma", "scprofile:old"])
        self.assertEqual(self.doc["errors"], [])
        self.assertEqual(self.rows["scprofile:alpha"]["companions"],
                         ["kernels/alpha.draw.R", "kernels/alpha.extra.py", "kernels/alpha.signatures.json"])

    def test_legacy_layouts_are_named(self):
        old = self.rows["scprofile:old"]
        self.assertEqual(old["format"], "kernel-yml")
        self.assertEqual(old["inputs"]["layers"], [{"layer": "spliced", "from": "needs.layers"}])
        self.assertEqual(old["inputs"]["requires"], ["spliced"])
        self.assertEqual(old["path"], "kernels/old")
        rc, doc = catalogue_json()
        self.assertEqual({r["format"] for r in doc["plugins"]}, {"directory"})


if __name__ == "__main__":
    unittest.main()
