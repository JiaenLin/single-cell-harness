#!/usr/bin/env python3
"""Runs the whole path on a synthetic object: build, sum, mask. Asserts shapes and finiteness only."""
import numpy as np
import anndata as ad
import scipy.sparse as sp

rng = np.random.default_rng(0)
X = sp.random(300, 50, density=0.2, random_state=0, format="csr")
X.data = np.round(X.data * 10) + 1
a = ad.AnnData(X=X)
a.layers["counts"] = X.copy()
a.obs_names = [f"B{i:04d}" for i in range(300)]
tot = np.asarray(a.layers["counts"].sum(axis=1)).ravel()
assert tot.shape == (300,) and np.isfinite(tot).all()
keep = tot >= np.median(tot)
assert keep.sum() > 0 and (~keep).sum() > 0
print("selftest ok", int(keep.sum()), "kept of", len(keep))
