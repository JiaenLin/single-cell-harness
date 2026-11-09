"""A plugin the catalogue cannot read is an error naming the file, never a silent drop (W016).

The class this guards against has been met twice in this family. scProfile's host reads a syntax
error or a non-literal `PLUGIN` as an empty declaration, and lists the plugin as `planned` with
nothing declared. The harness's own leak scan once read a named word list that did not exist as
"no words" (GAP-101). In both cases the reader could not tell "nothing there" from "could not
look". And a catalogue that imported a plugin to list it would need that plugin's environment,
and would run its code.
"""
from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from catalogue_fixture import (catalogue_json, checkout, harness_plugin, plugin_source, rows, sch,
                               spec)

#: Each is a shape a host would read as nothing, and each must come back as an error naming it.
UNREADABLE = {
    "syntax": "PLUGIN = {'summary': 'never closed'\n",
    "nothing": "def run(ctx):\n    pass\n",
    "computed": "PLUGIN = dict(summary='built at import time')\n",
    "annotated": "PLUGIN: dict = {'summary': 'annotated'}\n",
    "twice": "PLUGIN = {'summary': 'first'}\nPLUGIN = {'summary': 'second'}\n",
    "listed": "PLUGIN = ['summary', 'not a mapping']\n",
    "mutated": "PLUGIN = {'summary': 'as written'}\nPLUGIN['summary'] = 'as run'\n",
}


class TheCatalogueNeverDropsAPluginItCannotRead(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="sch-catalogue-"))
        plugins = dict(UNREADABLE)
        plugins["fine"] = plugin_source(spec(summary="a plugin that reads"))
        plugins["_private"] = "this is not Python, and a leading underscore is not a plugin\n"
        cls.co = checkout(cls.tmp / "checkout", plugins, files={
            "kernels/fine.draw.R": "# a companion, not a plugin\n",
            "kernels/old/kernel.yml": "summary: [never closed\n",
            "kernels/older/kernel.yml": "summary: an old-shape plugin that reads\n"
                                        "cannot_show:\n  - nothing\n"})

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_each_unreadable_one_file_plugin_is_an_error_naming_the_file(self):
        rc, doc = catalogue_json("--scprofile", str(self.co))
        self.assertEqual(rc, 2, "an unreadable plugin fails the listing")
        errors = {e["path"]: e["error"] for e in doc["errors"]}
        for name in UNREADABLE:
            path = f"kernels/{name}.py"
            self.assertIn(path, errors, f"{name}: dropped without a word")
            self.assertTrue(errors[path].startswith(path), errors[path])
        self.assertIn("kernels/old/kernel.yml", errors)
        self.assertIn("scprofile:fine", rows(doc), "the readable plugins are still listed")
        self.assertIn("scprofile:older", rows(doc))
        p = sch("catalogue", "--scprofile", str(self.co))
        self.assertEqual(p.returncode, 2)
        self.assertIn("UNREADABLE", p.stdout)
        for name in UNREADABLE:
            self.assertIn(f"kernels/{name}.py", p.stdout)

    def test_a_broken_manifest_is_an_error_naming_the_file(self):
        site = self.tmp / "site"
        bad = harness_plugin(site, "badyaml")
        (bad / "plugin.yml").write_text("name: [never closed\nsummary: x\n")
        noname = harness_plugin(site, "noname")
        (noname / "plugin.yml").write_text("profile: table/1.0\nsummary: a plugin with no name\n")
        harness_plugin(site, "good", summary="a site plugin that reads")
        rc, doc = catalogue_json(plugins=str(site))
        self.assertEqual(rc, 2)
        errors = {e["path"]: e["error"] for e in doc["errors"]}
        for d in (bad, noname):
            f = str((d / "plugin.yml").resolve())
            self.assertIn(f, errors, sorted(errors))
            self.assertIn(f, errors[f])
        self.assertIn("harness:table/good", rows(doc, "harness"))

    def test_rows_and_errors_account_for_every_candidate_file(self):
        rc, doc = catalogue_json("--scprofile", str(self.co))
        k = self.co / "kernels"
        candidates = ({f"kernels/{p.name}" for p in k.glob("*.py") if not p.name.startswith("_")}
                      | {f"kernels/{d.name}/kernel.yml" for d in k.iterdir() if (d / "kernel.yml").is_file()})
        listed = {r["path"] for r in doc["plugins"] if r["source"] == "scprofile"}
        listed = {p if p.endswith(".py") else f"{p}/kernel.yml" for p in listed}
        failed = {e["path"] for e in doc["errors"] if e["source"] == "scprofile"}
        self.assertEqual(listed | failed, candidates, "every candidate is a row or an error")
        self.assertFalse(listed & failed)
        self.assertNotIn("kernels/fine.draw.R", listed | failed)
        self.assertIn("kernels/fine.draw.R", rows(doc)["scprofile:fine"]["companions"])

    def test_reading_never_imports_or_executes_a_plugin(self):
        sentinel = self.tmp / "EXECUTED"
        body = (f"import os\nopen({str(sentinel)!r}, 'w').write('a plugin ran')\n"
                "import a_package_this_machine_does_not_have\n"
                "raise SystemExit(7)\n")
        src = body + plugin_source(spec(summary="read, never run"))
        vocab = (f"open({str(sentinel)!r}, 'w').write('the vocabulary ran')\n"
                 "CAPABILITIES = {'counts': {'resolve': 'data', 'why': 'integer counts'}}\n")
        co = checkout(self.tmp / "inert", {"inert": src}, vocabulary=vocab)
        rc, doc = catalogue_json("--scprofile", str(co))
        self.assertEqual(rc, 0, doc.get("errors"))
        self.assertEqual(rows(doc)["scprofile:inert"]["question"]["summary"], "read, never run")
        self.assertIn("scprofile", doc["vocabulary"])
        self.assertFalse(sentinel.exists(), "the catalogue executed a file it should only have read")


if __name__ == "__main__":
    unittest.main()
