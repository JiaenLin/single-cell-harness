"""The single-cell profile on a synthetic object. Skips where anndata is absent; runs on the cluster."""
import csv
import shutil
import tempfile
import unittest
from pathlib import Path

from helpers import ROOT
from sch.kernel import Stack

try:
    import anndata as ad
    import numpy as np
    import scipy.sparse as sp
    HAVE = True
except ImportError:
    HAVE = False


def make_object(dest: Path, n=300, g=80, seed=0):
    rng = np.random.default_rng(seed)
    X = sp.random(n, g, density=0.25, random_state=seed, format="csr")
    X.data = np.round(X.data * 20) + 1
    a = ad.AnnData(X=X.astype("float32"))
    a.layers["counts"] = X.astype("float32")
    samples = [f"S{i % 6}" for i in range(n)]
    a.obs_names = [f"{s}_B{i:04d}" for i, s in enumerate(samples)]
    a.obs["sample"] = samples
    a.obs["cell_type"] = [("A", "B", "C")[i % 3] for i in range(n)]
    a.write_h5ad(dest / "object.h5ad")
    with open(dest / "design.csv", "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["sample", "arm"])
        for i in range(6):
            w.writerow([f"S{i}", "control" if i % 2 == 0 else "treated"])
    return dest / "object.h5ad", dest / "design.csv"


@unittest.skipUnless(HAVE, "anndata / numpy / scipy not available in this interpreter")
class TestSingleCellProfile(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sch-sc-"))
        self.obj, self.design = make_object(self.tmp)
        self.st = Stack.init(self.tmp / "stack", "single-cell/1.0", str(self.obj), str(self.design),
                             keys={"label": "cell_type", "sample": "sample", "batch": "sample", "counts": "counts"})

    def tearDown(self):
        self.st.close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_identity_inventory_and_materialisation(self):
        self.assertEqual(len(self.st.dataset.ids), 300)
        caps = self.st.dataset.observation_capabilities()
        self.assertIn("column/cell_type", caps)
        self.assertIn("matrix/counts", caps)
        view, d = self.st.materialise()
        self.assertTrue(view.path.name.endswith(".h5ad"))
        self.assertEqual(view.n, 300)

    def test_mask_plugin_mounts_gates_and_unmounts_by_digest(self):
        st = self.st
        base = st.materialise()[0].digest()
        p = st.plan("mask_floor", {"min": 60})
        self.assertTrue(p["admitted"], p)
        self.assertEqual(p["gates"], ["differential_check"])
        r = st.mount("mask_floor", {"min": 60})
        self.assertTrue(r.ok, r.reason + " " + r.fix)
        self.assertEqual(r.gates[0]["gate"], "differential_check")
        self.assertIn(r.gates[0]["verdict"], ("PASS", "REVIEW"))
        v = st.materialise()[0]
        self.assertLess(v.n, 300)
        self.assertIn("count_floor", v.masks())
        # the h5ad view carries every observation with its mask column when unfiltered
        full, _ = st.materialise(filtered=False)
        a = ad.read_h5ad(full.path)
        self.assertEqual(a.n_obs, 300)
        self.assertIn("mask__count_floor", a.obs)
        self.assertEqual(int((~a.obs["mask__count_floor"]).sum()), 300 - v.n)
        rep = st.report()
        self.assertIn("mask_floor/n_removed", rep["numbers"])
        st.unmount("mask_floor")
        self.assertEqual(st.materialise()[0].digest(), base)

    def test_the_gate_refuses_an_arm_selective_removal_with_the_number(self):
        st = self.st
        # a floor that removes only the control arm: put control samples' counts low
        a = ad.read_h5ad(self.obj)
        ctrl = a.obs["sample"].isin(["S0", "S2", "S4"]).values
        M = a.layers["counts"].tolil()
        for i in np.where(ctrl)[0]:
            M[i, :] = M[i, :] * 0.05
        a.layers["counts"] = M.tocsr()
        a.write_h5ad(self.obj)
        st.dataset._digest = None
        (st.dir / "observations.sha256").unlink(missing_ok=True)
        r = st.mount("mask_floor", {"min": 30})
        self.assertEqual(r.status, "refused", r.reason)
        self.assertEqual(r.gates[0]["verdict"], "REFUSE")
        self.assertIsNotNone(r.gates[0]["number"])
        ans = st.ask("differential", subject={"masks": {"count_floor": str(st.dir / "plugins" / "mask_floor" / "out" / "masks" / "count_floor.csv")}})
        self.assertEqual(ans["answer"]["max_ratio"], r.gates[0]["number"])


if __name__ == "__main__":
    unittest.main()
