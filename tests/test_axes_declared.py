"""The cohort axes, declared once and checked against the data (harness ADR-0027, step 2).

The second cohort found three tools that took an axis without checking it: an assay defaulted to
the first cohort's, a species string used only as a filter, an organism "taken as declared". Each
would have run a human cohort as the first cohort's mouse and said nothing. The stack now declares
its axes once (`profile_context`, names from the profile's `axes:`); the `axes` probe reads the
species off the gene identifiers; the `axes_declared` gate refuses a contradiction.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import ROOT

GATE = ROOT / "plugins" / "single-cell" / "gate_axes_declared" / "run.py"
PROTOCOL = ROOT / "sch" / "plugin" / "protocol.py"


def gate(answer):
    """Run the gate's own entry point on a probe answer, through the real protocol."""
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "out"
        out.mkdir()
        (Path(td) / "in.json").write_text(json.dumps({"contract": "1.0", "out_dir": str(out),
                                                      "probe_answer": answer, "params": {}}))
        r = subprocess.run([sys.executable, str(GATE), str(Path(td) / "in.json")],
                           env=dict(os.environ, SCH_PROTOCOL=str(PROTOCOL)),
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        return json.loads((out / "out.json").read_text())["answer"]


def probe(declared, measured=None, reads_as=None, expected=None):
    return {"declared": declared,
            "species": {"measured": measured, "basis": f"identifiers say {measured}" if measured else "none"},
            "convention": {"reads_as": reads_as, "expected_for_declared": expected}}


class TheGate(unittest.TestCase):
    def test_a_species_the_identifiers_contradict_is_refused_with_both_values(self):
        a = gate(probe({"species": "mus_musculus", "assay": "scrna"}, measured="homo_sapiens"))
        self.assertEqual(a["verdict"], "REFUSE")
        self.assertIn("mus_musculus", a["reason"])
        self.assertIn("homo_sapiens", a["reason"])

    def test_agreement_passes(self):
        a = gate(probe({"species": "homo_sapiens", "assay": "scrna"}, measured="homo_sapiens"))
        self.assertEqual(a["verdict"], "PASS")

    def test_measurable_and_undeclared_is_a_review_that_names_the_declaration(self):
        a = gate(probe({"assay": "scrna"}, measured="homo_sapiens"))
        self.assertEqual(a["verdict"], "REVIEW")
        self.assertIn("--context species=homo_sapiens", a["reason"])

    def test_a_convention_mismatch_is_a_review_never_a_refusal(self):
        a = gate(probe({"species": "mus_musculus", "assay": "snrna"}, reads_as="upper", expected="title"))
        self.assertEqual(a["verdict"], "REVIEW")

    def test_an_undeclared_assay_is_asked_for_and_never_guessed(self):
        a = gate(probe({"species": "homo_sapiens"}, measured="homo_sapiens"))
        self.assertEqual(a["verdict"], "REVIEW")
        self.assertIn("assay", a["reason"])
        # and a REFUSE on the species does not hide it
        a = gate(probe({"species": "mus_musculus"}, measured="homo_sapiens"))
        self.assertEqual(a["verdict"], "REFUSE")
        self.assertEqual(sorted(f["verdict"] for f in a["findings"]), ["REFUSE", "REVIEW"])


try:
    import anndata as ad
    import numpy as np
    import pandas as pd
    import scipy.sparse as sp
    HAVE = True
except ImportError:
    HAVE = False


@unittest.skipUnless(HAVE, "anndata / numpy / scipy not available in this interpreter")
class TheProbeOnAnObject(unittest.TestCase):
    def setUp(self):
        from sch.kernel import Stack
        self.Stack = Stack
        self.tmp = Path(tempfile.mkdtemp(prefix="sch-axes-"))
        rng = np.random.default_rng(0)
        g = 60
        X = sp.random(120, g, density=0.3, random_state=0, format="csr")
        X.data = np.round(X.data * 20) + 1
        a = ad.AnnData(X=X.astype("float32"))
        a.layers["counts"] = a.X.copy()
        a.obs_names = [f"S{i % 4}_B{i:04d}" for i in range(120)]
        a.obs["sample"] = [f"S{i % 4}" for i in range(120)]
        a.obs["cell_type"] = [("A", "B")[i % 2] for i in range(120)]
        symbols = ["MT-CO1", "MT-ND1", "ACTB", "GAPDH"] + [f"GENE{i:03d}" for i in range(g - 4)]
        a.var_names = symbols
        a.var["gene_ids"] = [f"ENSG{100000 + i:011d}" for i in range(g)]
        self.obj = self.tmp / "object.h5ad"
        a.write_h5ad(self.obj)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _stack(self, name, context):
        return self.Stack.init(self.tmp / name, "single-cell/1.0", str(self.obj),
                               keys={"label": "cell_type", "sample": "sample", "counts": "counts"},
                               context=context)

    def test_the_identifiers_say_human_whatever_the_stack_declared(self):
        st = self._stack("mouse", {"species": "mus_musculus", "assay": "scrna"})
        try:
            ans = st.ask("axes")["answer"]
        finally:
            st.close()
        self.assertEqual(ans["declared"], {"species": "mus_musculus", "assay": "scrna"})
        self.assertEqual(ans["species"]["measured"], "homo_sapiens")
        self.assertEqual(ans["convention"]["reads_as"], "upper")
        self.assertEqual(ans["convention"]["mitochondrial"]["MT-"], 2)
        self.assertEqual(gate(ans)["verdict"], "REFUSE")

    def test_a_name_that_is_not_an_axis_is_refused_at_init(self):
        from sch.stack import StackError
        with self.assertRaises(StackError) as cm:
            self._stack("typo", {"specis": "homo_sapiens"})
        self.assertIn("species", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
