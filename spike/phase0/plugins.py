"""Toy plugins for the Phase 0 spike. Five, so the stack is five deep.

Each is the smallest thing that exercises one property:

  mask_umi     contributes a MASK — the reversible removal the whole thesis rests on
  mask_genes   a second mask, so masks must compose rather than overwrite
  qc_metrics   contributes COLUMNS derived from the observations
  score        reads a column, so unmounting what it read must invalidate it
  embed        contributes an EMBEDDING, the expensive kind of contribution

`READS` is how a plugin declares what it consumes. It is the whole of dependency resolution in
this spike, and the thing invalidation is computed from — the kernel never asks a plugin whether
it is still valid.
"""
from __future__ import annotations


class mask_umi:
    NAME = "mask_umi"
    READS = set()

    @staticmethod
    def run(view, min_umi=350):
        import numpy as np
        tot = np.asarray(view.obs.X.sum(axis=1)).ravel()
        yield "mask", "min_umi", tot >= min_umi


class mask_genes:
    NAME = "mask_genes"
    READS = {"mask"}

    @staticmethod
    def run(view, min_genes=200):
        import numpy as np
        X = view.obs.X
        ngene = np.asarray((X > 0).sum(axis=1)).ravel()
        yield "mask", "min_genes", ngene >= min_genes


class qc_metrics:
    NAME = "qc_metrics"
    READS = {"mask"}

    @staticmethod
    def run(view):
        import numpy as np
        X = view.obs.X
        yield "column", "total_counts", np.asarray(X.sum(axis=1)).ravel().astype("float32")
        yield "column", "n_genes", np.asarray((X > 0).sum(axis=1)).ravel().astype("float32")


class score:
    NAME = "score"
    READS = {"column"}

    @staticmethod
    def run(view):
        import numpy as np
        tc = view.columns.get("total_counts")
        if tc is None:
            raise RuntimeError("score reads column/total_counts, which is not present")
        ng = view.columns["n_genes"]
        yield "column", "complexity", (ng / np.maximum(tc, 1)).astype("float32")


class embed:
    NAME = "embed"
    READS = {"mask", "column"}

    @staticmethod
    def run(view, k=20, seed=0):
        """A truncated SVD over the kept observations, padded back to full length.

        Padded with NaN, never 0 (single-cell profile §6): a masked observation has no embedding,
        and a zero would sort, average and plot as though it did.
        """
        import numpy as np
        from scipy.sparse.linalg import svds
        X = view.obs.X[view.keep].astype("float32")
        rng = np.random.default_rng(seed)
        v0 = rng.normal(size=min(X.shape))
        U, S, _ = svds(X, k=k, v0=v0)
        full = np.full((view.obs.n, k), np.nan, dtype="float32")
        full[view.keep] = (U * S)[:, ::-1]
        yield "embedding", "X_svd", full


ORDER = [mask_umi, mask_genes, qc_metrics, score, embed]
