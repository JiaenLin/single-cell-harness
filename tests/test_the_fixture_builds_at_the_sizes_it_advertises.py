#!/usr/bin/env python3
"""`build(n_genes=60)` raised, and six tests of this suite met it where nobody was reading.

WHAT HAPPENED. The fixture gives each cell type twenty marker genes, at a fixed offset:
`lam[np.ix_(idx, np.arange(k * 20, k * 20 + 20))]`. `n_genes` is a documented parameter with a
default of 520, and six types need 120 markers - so the default is fine and `build(n_genes=60)`
indexes column 60 of a 60-column array and raises `IndexError`. That line is as old as the module.

WHY IT WAS INVISIBLE FOR FOUR DAYS, WHICH IS THE PART WORTH KEEPING. The six tests that call it
that way live in `test_dev.py` and are guarded on anndata, because they go on to WRITE the object.
A workstation without anndata skips them; the cluster runs them; and the only thing that runs the
suite on the cluster is the full-ladder job, which had been failing at step 0 for a separate
reason and so never reached the tier. Three separate silences over one exception.

`build` NEEDS NO anndata - it returns arrays and frames, and only `write` needs a library to put
them in a file. So this file exercises the sizes directly and runs everywhere, which is the
difference between a defect that waits for a cluster and one that fails on the machine it is
introduced on.

AND THE DEFAULT OBJECT MUST NOT MOVE. Every recorded baseline in this family is keyed on its
digest. Deriving the marker width from `n_genes` would have fixed the crash and invalidated all of
them; clipping the block leaves the default byte-identical, and that is asserted here rather than
believed.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sch.dev import fixture as F                                           # noqa: E402

#: The digest of the default cohort, recorded before the marker block was clipped. A change here
#: is a change to every baseline in this family and must be a deliberate one.
DEFAULT_DIGEST = "d423a5817fdcb29e"


class TheFixtureBuildsAtTheSizesItAdvertises(unittest.TestCase):

    def test_the_default_object_has_not_moved(self):
        self.assertEqual(DEFAULT_DIGEST, F.digest(F.build()),
                         "the default fixture changed, so every recorded baseline in this family "
                         "is now measured against a different cohort")

    def test_it_builds_below_one_marker_block_per_type(self):
        # 6 types x 20 markers = 120 genes. Everything under that used to raise.
        need = len(F.TYPES) * 20
        for n in (len(F.REAL_GENES) + 1, 60, need - 1, need, need + 1):
            with self.subTest(n_genes=n):
                c = F.build(n_cells=120, n_genes=n)
                self.assertEqual(n, c["X"].shape[1])
                self.assertEqual(n, len(c["genes"]))

    def test_the_hazards_that_index_from_the_end_still_land(self):
        # `empty_gene` is the last column and `constant_gene` the one before it; a clip that ate
        # them would leave the fixture advertising sixteen hazards and carrying fourteen.
        c = F.build(n_cells=120, n_genes=60)
        X = c["X"]
        self.assertEqual(0.0, float(X[:, -1].sum()), "empty_gene is not empty")
        self.assertEqual(1, len(set(X[1:, -2].tolist())), "constant_gene is not constant")
        self.assertEqual(0.0, float(X[0].sum()), "empty_cell is not empty")

    def test_every_type_that_fits_still_gets_its_markers(self):
        # The clip removes markers only for types whose block starts past the end - it must not
        # quietly stop marking the ones that fit.
        c = F.build(n_cells=600, n_genes=len(F.TYPES) * 20)
        X, ctype = c["X"], c["obs"]["_role_cell_type"].astype(str).to_numpy()
        marked = 0
        for k, t in enumerate(F.TYPES):
            rows = [i for i, x in enumerate(ctype) if x == t and i > 0]
            if len(rows) < 5:
                continue
            block = X[rows][:, k * 20:(k + 1) * 20].mean()
            rest = X[rows][:, (k + 1) * 20:].mean() if (k + 1) * 20 < X.shape[1] else \
                X[rows][:, :k * 20].mean()
            if block > rest:
                marked += 1
        self.assertGreaterEqual(marked, 3,
                                "the marker blocks no longer stand out, so the fixture's cell "
                                "types are not distinguishable by expression")

    def test_build_needs_no_anndata(self):
        """THE REASON THIS FILE EXISTS. `write` needs a library to put the object in a file;
        `build` does not, and a check that shares `write`'s dependency inherits its silence.

        PARSED, NOT GREPPED. The first version searched the source text for "anndata" and matched
        the COMMENT that explains this very property - a substring standing in for a name, which
        is the error this suite has paid for more than once and paid for again here.
        """
        import ast
        import inspect
        tree = ast.parse(inspect.getsource(F.build).lstrip())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertNotIn("anndata", imported,
                         "build imports anndata, so every check of it inherits a dependency that "
                         "makes it skip on the machine it is written on")
        self.assertEqual({"numpy", "pandas"}, imported)


if __name__ == "__main__":
    unittest.main()
