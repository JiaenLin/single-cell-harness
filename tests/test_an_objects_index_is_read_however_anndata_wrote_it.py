#!/usr/bin/env python3
"""An object's shape is read from its index however anndata wrote it (autodev W029, from the W026
verifier).

The baseline fingerprints an .h5ad by its shape and keys (autodev W019), and read the number of
observations as `obs/<index>.shape[0]`. anndata 0.12 writes the index as a `string-array`
DATASET; anndata 0.13, under pandas 3, writes it as a `nullable-string-array` GROUP of `values`
and `mask`, which has no `.shape` - so every object written by 0.13 lost its structure, silently
(the reader catches everything), and the test of it raised KeyError 'structure'. That test needs
anndata and is skipped where there is none, which is how it went unseen. These write both
encodings - and a categorical index - with h5py alone, so every interpreter that has h5py runs them.

Run: PYTHONPATH=. python3 tests/test_an_objects_index_is_read_however_anndata_wrote_it.py
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sch.dev import baseline as B                                               # noqa: E402

try:
    import h5py
    import numpy as np
    HAVE_H5PY = True
except ImportError:
    HAVE_H5PY = False


def write_index(group, names, encoding):
    group.attrs["_index"] = "_index"
    data = np.array([n.encode() for n in names], dtype=object)
    if encoding == "string-array":                    # anndata <= 0.12
        ds = group.create_dataset("_index", data=data, dtype=h5py.string_dtype())
        ds.attrs["encoding-type"] = "string-array"
        return
    g = group.create_group("_index")
    if encoding == "nullable-string-array":           # anndata 0.13 under pandas 3
        g.attrs["encoding-type"] = "nullable-string-array"
        g.create_dataset("values", data=data, dtype=h5py.string_dtype())
        g.create_dataset("mask", data=np.zeros(len(names), dtype=bool))
    else:                                             # a categorical index
        g.attrs["encoding-type"] = "categorical"
        cats = sorted(set(names))
        g.create_dataset("categories", data=np.array([c.encode() for c in cats], dtype=object),
                         dtype=h5py.string_dtype())
        g.create_dataset("codes", data=np.array([cats.index(n) for n in names], dtype="int8"))


def write_object(path: Path, n_obs: int, n_vars: int, encoding: str):
    with h5py.File(path, "w") as f:
        f.create_dataset("X", data=np.zeros((n_obs, n_vars), dtype="float32"))
        write_index(f.create_group("obs"), [f"c{i}" for i in range(n_obs)], encoding)
        write_index(f.create_group("var"), [f"g{i}" for i in range(n_vars)], encoding)
        f.create_group("layers").create_dataset("counts", data=np.zeros((n_obs, n_vars)))


@unittest.skipUnless(HAVE_H5PY, "h5py is not available in this interpreter")
class AnObjectsIndexIsReadHoweverAnndataWroteIt(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix="sch-h5ad-index-"))

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_every_encoding_gives_the_shape(self):
        for encoding in ("string-array", "nullable-string-array", "categorical"):
            with self.subTest(encoding):
                p = self.d / f"{encoding}.h5ad"
                write_object(p, 10, 3, encoding)
                s = B._h5ad_structure(p)
                self.assertIsNotNone(s, encoding)
                self.assertEqual((s["n_obs"], s["n_vars"], s["X"]), (10, 3, [10, 3]))
                self.assertEqual(s["layers"], ["counts"])

    def test_a_baseline_sees_an_object_written_the_new_way_double(self):
        run = self.d / "run"
        run.mkdir()
        write_object(run / "obj.h5ad", 10, 3, "nullable-string-array")
        (run / "r.json").write_text('{"k": 1.0}')
        path = self.d / "b.json"
        ref = B.record(run, path)
        self.assertEqual(ref["products"]["obj.h5ad"]["structure"]["n_obs"], 10)
        write_object(run / "obj.h5ad", 20, 3, "nullable-string-array")
        diffs = B.check(run, path)[0]
        self.assertIn("structure", [x["what"] for x in diffs])
        self.assertIn("n_obs 10 -> 20", next(x["detail"] for x in diffs if x["what"] == "structure"))


if __name__ == "__main__":
    unittest.main()
