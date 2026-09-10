#!/usr/bin/env python3
"""An inventory that finds plots by NAME finds the plots of the package it was written for.

WHERE THIS CAME FROM, MEASURED. The only inventory extractor this family ever had was four lines
lifted out of one plugin, and the grep in it was that package's own export naming written as if it
were a general rule. A BLIND CONVERSION measured what that costs: the finished plugin hidden, the
plugin scaffolded from nothing, the maker pointed at the real namespace in the plugin's own
environment - and 31 of the 37 upstream plots the plugin accounts for came back. The six that did
not were `rankNet`, `rankSimilarity`, `compareInteractions`, `identifyCommunicationPatterns`,
`netClustering` and `interaction_lr`. Every one of them draws. Not one of them follows the
convention its own package is named after.

SO THERE IS A SECOND RULE AND IT IS ABOUT BEHAVIOUR: a function whose body calls one of R's own
plotting entry points draws, whatever it is called. That is the same principle the draw-wrapper
detector in this package already uses one directory over, and it is the only kind of rule that can
be general - a name is a convention and a convention belongs to somebody.

WHAT THIS FILE RATCHETS.

  THE TWO RULES STAY INDEPENDENT. A general list that quietly re-states the convention list is one
  rule wearing two hats. Written once and caught here: `netVisual_` was pasted into the list of
  "R's own plotting entry points", where it is exactly the fitted literal the overfit scan exists
  to find.

  THE BEHAVIOUR RULE EARNS ITS PLACE ON PACKAGES THIS MAKER WAS NOT BUILT FOR. ggplot2, lattice
  and cluster: 15, 6 and 1 exports that the name pattern cannot reach - `bannerplot`,
  `panel.violin`, `panel.cloud`, `xyplot.ts`. lattice finds NOTHING by name alone.

  A PACKAGE THAT CANNOT BE LOADED IS NOT A PACKAGE WITH NO PLOTS. That distinction is the one
  claim about a wrapper that is never true, and it is the whole reason this returns `complete`.

  EACH EXPORT SAYS WHICH RULE FOUND IT, so a reader can see when a convention has stopped being
  followed instead of trusting a merged list.
"""
from __future__ import annotations

import re
import shutil
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sch.dev.extract import r_namespace as RN                              # noqa: E402

RSCRIPT = shutil.which("Rscript") or shutil.which("R")


def has(pkg):
    if not RSCRIPT:
        return False
    return RN.inventory(pkg).complete


class APlottingFunctionIsFoundByWhatItDoes(unittest.TestCase):

    def test_the_general_list_does_not_restate_the_convention(self):
        # Every alternative in the name pattern, as a plain prefix.
        alts = re.findall(r"[A-Za-z_][A-Za-z0-9_.]*", RN.DEFAULT_PATTERN.split("(", 1)[-1])
        tool_shaped = [a for a in alts if len(a) > 4]     # `plot`, `gg`, `vis` are R's, not a tool's
        for prim in RN._PRIMITIVES:
            for a in tool_shaped:
                self.assertFalse(prim.startswith(a),
                                 f"{prim!r} is in the list of R's OWN plotting entry points and "
                                 f"begins with {a!r}, which is one wrapped package's naming "
                                 f"convention - the two rules have stopped being independent")

    def test_every_entry_is_a_call_shape_and_not_a_prefix(self):
        for prim in RN._PRIMITIVES:
            self.assertFalse(prim.endswith("_"),
                             f"{prim!r} is a prefix, not a function name: the body rule matches a "
                             f"CALL, so a prefix here silently matches nothing")

    @unittest.skipUnless(RSCRIPT, "no Rscript on this machine, so no namespace can be read")
    def test_a_namespace_that_cannot_be_loaded_is_not_a_package_with_no_plots(self):
        inv = RN.inventory("thisPackageDoesNotExistAnywhere")
        self.assertFalse(inv.complete)
        self.assertEqual([], inv.names)
        self.assertIn("cannot load the namespace", inv.why_not)

    @unittest.skipUnless(RSCRIPT and has("lattice"),
                         "lattice is not installed here, so the generality claim is not checked")
    def test_behaviour_reaches_what_the_convention_cannot_on_another_package(self):
        inv = RN.inventory("lattice")
        self.assertTrue(inv.complete)
        by_body_only = [k for k, v in inv.detail.items() if v == "body"]
        self.assertTrue(by_body_only,
                        "the body rule found nothing in lattice that the name pattern missed, so "
                        "it is not earning its place on a package this maker was not built for")
        self.assertIn("body rule", inv.how)

    @unittest.skipUnless(RSCRIPT and has("lattice"), "lattice is not installed here")
    def test_each_export_says_which_rule_found_it(self):
        inv = RN.inventory("lattice")
        self.assertEqual(sorted(inv.names), sorted(inv.detail))
        self.assertTrue(set(inv.detail.values()) <= {"name", "body", "both"}, inv.detail)

    @unittest.skipUnless(RSCRIPT and has("cluster"), "cluster is not installed here")
    def test_a_package_with_one_plot_and_no_convention_is_still_read(self):
        inv = RN.inventory("cluster")
        self.assertTrue(inv.complete)
        self.assertIn("bannerplot", inv.names,
                      "a plotting export whose name follows no convention at all was missed")

    # ---- and the same question one language over ----------------------------------------

    def test_python_is_asked_by_signature_and_not_only_by_name(self):
        """A callable that takes an axes or a figure draws on it.

        THE PREFIX LIST IS THE UNION OF FIVE PACKAGES' CONVENTIONS, which is the shape that stops
        working on the sixth - exactly what the blind conversion measured in R. Measured here on
        pandas.plotting, which has no `pl` submodule: the NAME rule finds one of its thirteen
        plotting functions. `radviz`, `andrews_curves`, `parallel_coordinates` and nine more are
        reached only by the signature.
        """
        from sch.dev.extract import python_package as PP
        inv = PP.inventory("pandas.plotting")
        if not inv.complete:
            self.skipTest(f"pandas is not installed here: {inv.why_not[:60]}")
        by_sig = sorted(k for k, v in inv.detail.items() if v.get("found_by") == "signature")
        self.assertIn("radviz", by_sig,
                      "a plotting function following no naming convention was missed")
        self.assertIn("parallel_coordinates", by_sig)
        self.assertGreater(len(by_sig), 5,
                           "the signature rule is not earning its place on a package whose "
                           "names do not follow the list")
        self.assertNotIn("register_matplotlib_converters", inv.names,
                         "a converter registration was reported as a plotting function")

    def test_which_axis_is_not_an_axis_to_draw_on(self):
        """`axis=` in matplotlib means WHICH axis - a string, not an object to draw on.

        Including it added five of pyplot's helpers and no plotting function anywhere.
        """
        from sch.dev.extract import python_package as PP
        self.assertNotIn("axis", PP._AXIS_PARAMS)
        self.assertIn("ax", PP._AXIS_PARAMS)

    def test_the_python_probe_is_valid_python(self):
        """IT IS SOURCE IN A STRING, and a bad edit to it fails at the far end of a subprocess.

        Measured: a replacement left an unterminated string literal in the middle of the probe,
        and the only symptom was every inventory returning "produced no answer" - a message about
        the interpreter, for a defect in this file.
        """
        from sch.dev.extract import python_package as PP
        body = (PP._PROBE.replace("__NAMEY__", repr(list(PP._NAMEY)))
                .replace("__DRAWS__", repr(list(PP._AXIS_PARAMS))))
        compile(body, "<probe>", "exec")

    @unittest.skipUnless(RSCRIPT, "no Rscript on this machine")
    def test_the_probe_survives_being_handed_to_r(self):
        # THE BACKSLASHES ARE THE POINT. The probe's lookbehind reached R with one backslash
        # instead of two when it was passed through `-e`, and R refused the entire script with
        # "unrecognized escape in character string" - a script that runs correctly from a file.
        # TWO BACKSLASHES, because this is R SOURCE: R's parser turns `"\\w"` into `\w` before
        # the regex engine ever sees it. One backslash here is the bug this guards against.
        self.assertIn(r"(?<![\\w.])", RN._PROBE)
        inv = RN.inventory("stats")
        self.assertTrue(inv.complete or "cannot load" in inv.why_not,
                        f"the probe did not run: {inv.why_not}")


if __name__ == "__main__":
    unittest.main()
