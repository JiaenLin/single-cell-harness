"""`sch catalogue` lists every plugin the family has, through the real CLI (W016, GAP-005).

The finding this answers: an agent asked a question could not list the methods it might answer it
with. scProfile has no list command, and the harness's kernel sees only `plugin.yml` directories,
so scProfile's nine plugins were invisible to the agent surface. Every test here runs
`python -m sch catalogue`, on the harness's own plugins and on a synthetic scProfile-shaped
checkout built in a temporary directory.
"""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from catalogue_fixture import (ROOT, catalogue_json, checkout, harness_plugin, plugin_source, rows,
                               sch, spec)


class TheCatalogueListsEveryPluginTheFamilyHas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="sch-catalogue-"))
        cls.co = checkout(cls.tmp / "checkout", {
            "alpha": plugin_source(spec(
                summary="whether alpha answers the question",
                wraps={"tool": "toola", "version": "1.0.0", "cite": "Someone et al., 2020"},
                config={"min_size": {"type": "int", "default": 3, "help": "the smallest group kept"}},
                cannot_show=["alpha cannot show a cause"])),
            "beta": plugin_source(spec(summary="what beta measures",
                                       wraps={"tool": "toolb", "unreviewed": "nobody looked yet"})),
            "gamma": plugin_source(spec(summary="what gamma orders")),
        }, files={"kernels/alpha.signatures.json": "{}"})
        cls.site = cls.tmp / "site"
        harness_plugin(cls.site, "alpha", summary="a site plugin sharing a name with a scProfile one")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_every_harness_plugin_is_listed_once(self):
        rc, doc = catalogue_json()
        self.assertEqual(rc, 0, doc.get("errors"))
        shipped = sorted(str(p.parent.relative_to(ROOT)) for p in (ROOT / "plugins").rglob("plugin.yml"))
        listed = sorted(r["path"] for r in doc["plugins"] if r["source"] == "harness")
        self.assertEqual(listed, shipped, "every shipped plugin.yml, and nothing else, is a row")
        ids = [r["id"] for r in doc["plugins"]]
        self.assertEqual(len(ids), len(set(ids)), "an id names one plugin")
        self.assertEqual({r["format"] for r in doc["plugins"]}, {"directory"})
        # A LISTING THAT DID NOT READ scProfile SAYS SO, so it never reads as the whole family.
        sp = [s for s in doc["sources"] if s["name"] == "scprofile"]
        self.assertEqual(len(sp), 1)
        self.assertFalse(sp[0]["read"])
        self.assertIn("--scprofile", sp[0]["why"])

    def test_a_scprofile_checkout_named_by_the_flag_is_read(self):
        rc, doc = catalogue_json("--scprofile", str(self.co))
        self.assertEqual(rc, 0, doc.get("errors"))
        got = rows(doc)
        self.assertEqual(sorted(got), ["scprofile:alpha", "scprofile:beta", "scprofile:gamma"])
        a = got["scprofile:alpha"]
        self.assertEqual(a["path"], "kernels/alpha.py")
        self.assertEqual(a["question"]["summary"], "whether alpha answers the question")
        self.assertEqual(a["inputs"]["requires"], ["counts", "label"])
        self.assertEqual(a["outputs"]["produces"], ["tables/out.csv"])
        self.assertEqual(a["provenance"]["upstream"], "toola")
        self.assertEqual(a["cannot_show"], ["alpha cannot show a cause"])
        src = [s for s in doc["sources"] if s["name"] == "scprofile"][0]
        self.assertTrue(src["read"])
        self.assertEqual((src["plugins"], src["errors"]), (3, 0))
        self.assertEqual(Path(src["root"]), self.co.resolve())

    def test_the_text_view_names_every_plugin_and_the_counts(self):
        p = sch("catalogue", "--scprofile", str(self.co))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        for ident in ("scprofile:alpha", "scprofile:beta", "scprofile:gamma",
                      "harness:single-cell/mask_floor"):
            self.assertIn(ident, p.stdout)
        n = len(list((ROOT / "plugins").rglob("plugin.yml"))) + 3
        self.assertIn(f"{n} plugin(s) from 2 source(s); 0 file(s) could not be read", p.stdout)

    def test_show_gives_one_plugin_whole_by_id_or_unique_tail(self):
        rc, doc = catalogue_json("show", "scprofile:alpha", "--scprofile", str(self.co))
        self.assertEqual(rc, 0, doc)
        row = doc["plugin"]
        self.assertEqual(row["id"], "scprofile:alpha")
        self.assertEqual(row["details"]["parameters"]["min_size"]["default"], 3)
        rc, tail = catalogue_json("show", "gamma", "--scprofile", str(self.co))
        self.assertEqual((rc, tail["plugin"]["id"]), (0, "scprofile:gamma"))
        p = sch("catalogue", "show", "scprofile:alpha", "--scprofile", str(self.co))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("alpha cannot show a cause", p.stdout)
        self.assertIn("min_size", p.stdout)

    def test_show_refuses_an_ambiguous_or_unknown_id_by_name(self):
        # `alpha` is a harness site plugin AND a scProfile plugin: a bare name is ambiguous.
        rc, doc = catalogue_json("show", "alpha", "--scprofile", str(self.co), plugins=str(self.site))
        self.assertEqual(rc, 2)
        self.assertEqual(doc["status"], "refused")
        self.assertIn("harness:table/alpha", doc["reason"])
        self.assertIn("scprofile:alpha", doc["reason"])
        rc, doc = catalogue_json("show", "scprofile:alpha", "--scprofile", str(self.co),
                                 plugins=str(self.site))
        self.assertEqual((rc, doc["plugin"]["id"]), (0, "scprofile:alpha"))
        rc, doc = catalogue_json("show", "no_such_plugin")
        self.assertEqual(rc, 2)
        self.assertIn("no plugin 'no_such_plugin'", doc["reason"])
        self.assertIn("--scprofile", doc["reason"], "it says which source was not read")

    def test_a_missing_or_wrong_checkout_is_refused_by_name(self):
        nowhere = self.tmp / "nowhere"
        rc, doc = catalogue_json("--scprofile", str(nowhere))
        self.assertEqual(rc, 2)
        self.assertIn(str(nowhere), doc["reason"])
        empty = self.tmp / "not_a_checkout"
        empty.mkdir(exist_ok=True)
        rc, doc = catalogue_json("--scprofile", str(empty))
        self.assertEqual(rc, 2)
        self.assertIn("kernels/", doc["reason"])

    def test_json_is_accepted_before_and_after_the_subcommand(self):
        before = sch("--json", "catalogue", "--scprofile", str(self.co))
        after = sch("catalogue", "--scprofile", str(self.co), "--json")
        self.assertEqual((before.returncode, after.returncode), (0, 0), before.stderr + after.stderr)
        self.assertEqual(json.loads(before.stdout), json.loads(after.stdout))


if __name__ == "__main__":
    unittest.main()
