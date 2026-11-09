#!/usr/bin/env python3
"""The python extractor reads a package's classes and submodules, not only its top level (autodev
W019, GAP-C39).

FOUND BY THE BLIND CONVERSION OF de (scProfile docs/MIGRATIONS.md, autodev W013): `inventory` exited
2 with "no extractor could look at pydeseq2". pydeseq2 exports nothing at its top level; it draws
with METHODS of its two classes (`DeseqDataSet.plot_dispersions`, `DeseqStats.plot_MA`) and with
functions in a SUBMODULE (`utils.make_MA_plot`, and `utils.make_scatter`, the helper behind
`plot_dispersions`). The extractor looked at the top level alone, so the inventory stage and the plan
stayed part-way on an admission nobody could pay.

The package below has pydeseq2's shape: an empty top level apart from one re-exported class, two
classes in two submodules - one inheriting from another package, whose methods are not this
package's plots - a function in a third that writes its figure file, a private module, a test
module, and a submodule that will not import. Exactly the plotting functions this package defines
are found, each once, by its shortest public name; nothing inherited, private or merely imported.

Run: PYTHONPATH=. python3 tests/test_the_python_extractor_reads_classes_and_submodules.py
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sch.dev.extract import python_package as PP                           # noqa: E402

FILES = {
    "otherpkg/__init__.py": "",
    "otherpkg/base.py": """\
        class Holder:
            def plot_everything(self, ax=None):
                return ax


        def external_plot(ax=None):
            return ax
        """,
    "fakeplot/__init__.py": """\
        from .ds import Stats
        """,
    "fakeplot/dds.py": """\
        from otherpkg.base import Holder


        class DataSet(Holder):
            def fit(self):
                return self

            def plot_dispersions(self, log=True, save_path=None):
                return log

            def _plot_private(self):
                return None

            @staticmethod
            def scatter_static(ax=None):
                return ax
        """,
    "fakeplot/ds.py": """\
        class Stats:
            def summary(self):
                return None

            def plot_MA(self, log=True, save_path=None):
                return log
        """,
    "fakeplot/utils.py": """\
        from otherpkg.base import external_plot


        def make_ma_plot(results, save_path=None):
            fig = results
            if save_path:
                fig.savefig(save_path)


        def helper(x):
            return x
        """,
    "fakeplot/_private.py": """\
        def plot_hidden(ax=None):
            return ax
        """,
    "fakeplot/tests/__init__.py": "",
    "fakeplot/tests/test_x.py": """\
        def plot_test(ax=None):
            return ax
        """,
    "fakeplot/broken.py": """\
        raise ImportError("an optional dependency this machine has not got")
        """,
}


class ThePythonExtractorReadsClassesAndSubmodules(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.d = Path(tempfile.mkdtemp(prefix="sch-c39-"))
        for rel, text in FILES.items():
            p = cls.d / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(textwrap.dedent(text), encoding="utf-8")
        old = os.environ.get("PYTHONPATH")
        os.environ["PYTHONPATH"] = str(cls.d) + (os.pathsep + old if old else "")
        try:
            cls.inv = PP.inventory("fakeplot", python=sys.executable)
        finally:
            if old is None:
                os.environ.pop("PYTHONPATH", None)
            else:
                os.environ["PYTHONPATH"] = old

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.d, ignore_errors=True)

    def test_the_plotting_methods_and_the_submodule_function_are_found(self):
        self.assertTrue(self.inv.complete, self.inv.why_not)
        self.assertEqual(self.inv.names, ["Stats.plot_MA", "dds.DataSet.plot_dispersions",
                                          "dds.DataSet.scatter_static", "utils.make_ma_plot"],
                         self.inv.how)

    def test_each_says_which_rule_found_it(self):
        d = self.inv.detail
        self.assertEqual(d["dds.DataSet.plot_dispersions"]["found_by"], "name")
        self.assertEqual(d["utils.make_ma_plot"]["found_by"], "saves")
        self.assertIn("signature", d["dds.DataSet.scatter_static"]["found_by"])
        self.assertIn("log=True", d["Stats.plot_MA"]["signature"])

    def test_nothing_inherited_private_tested_or_merely_imported_is_reported(self):
        joined = " ".join(self.inv.names)
        for absent in ("plot_everything", "external_plot", "_plot_private", "plot_hidden",
                       "plot_test", "fit", "summary", "helper", "ds.Stats.plot_MA"):
            self.assertNotIn(absent, self.inv.names)
        self.assertNotIn("plot_everything", joined)

    def test_what_was_read_is_said_including_what_would_not_import(self):
        self.assertIn("public class(es)", self.inv.how)
        self.assertIn("submodule(s)", self.inv.how)
        self.assertIn("broken (ImportError)", self.inv.how)


if __name__ == "__main__":
    unittest.main()
