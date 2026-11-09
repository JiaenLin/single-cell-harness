"""The dev ladder reads every status a command writes, not only STATUS.json (W024, GAP-C38).

WHAT WAS WRONG. A tool of several commands writes one status per command, `STATUS.<cmd>.json`
beside `SEALED.<cmd>.txt` - the status contract allows it and `sch conform --run` already reads
it. The ladder's fixture tier and `agree` opened `STATUS.json` alone. On a tool that writes
`STATUS.annotate.json`, a command that exited 0 having written `partial` passed the fixture tier,
and the tier said "no STATUS.json - the status contract is not being written by this command"
about a command that was writing it.
"""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from sch.dev import ladder as L
from sch.dev import points as P

DECL = """
tool: demo
devpoints: 1
points:
  widget:
    what: a thing
    lives: pkg
    register:
      - {file: pkg/reg.py, table: WIDGETS}
    must_declare: [state_version]
    proves: it runs
    cannot_prove: that it is right
"""


def writes(statuses: dict, products=()) -> list:
    """A fixture command that writes these per-command statuses (and products) into {out}."""
    body = ("import json, sys, pathlib; out = pathlib.Path(sys.argv[1]); "
            f"[(out / k).write_text(json.dumps(v)) for k, v in {statuses!r}.items()]; "
            f"[(out / p).write_text('x') for p in {list(products)!r}]")
    return ["python3", "-c", body, "{out}"]


class TheLadderReadsEveryStatusACommandWrites(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix="sch-status-"))
        (self.d / "pkg").mkdir()
        (self.d / "pkg" / "reg.py").write_text("WIDGETS = {'alpha': 1}\n")
        (self.d / "DEVPOINTS.yaml").write_text(DECL)
        (self.d / "fx").mkdir()
        for shape in ("a", "b"):
            (self.d / "fx" / f"fixture_{shape}.h5ad").write_text("not really an object")
            (self.d / "fx" / f"design_{shape}.csv").write_text("x\n1\n")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _tier(self, spec, shape="a"):
        doc = P.load(self.d)
        doc["fixture"] = spec
        res = []
        L._fixture_tier(doc, "widget", "alpha", shape, self.d / "fx", res, f"fixture_{shape}")
        return res[0]

    def test_a_per_command_status_that_is_not_ok_fails_the_tier(self):
        r = self._tier({"command": writes({"STATUS.annotate.json":
                                           {"status": "partial", "headline": "stopped at depth 2"}})})
        self.assertFalse(r["ok"], r["evidence"])
        self.assertTrue(any("STATUS.annotate.json" in e and "partial" in e for e in r["evidence"]),
                        r["evidence"])

    def test_an_ok_per_command_status_is_quoted_and_not_reported_missing(self):
        r = self._tier({"command": writes({"STATUS.annotate.json": {"status": "ok", "headline": "done"}},
                                          products=["labels.csv"]),
                        "products": ["labels.csv"]})
        self.assertTrue(r["ok"], r["evidence"])
        self.assertTrue(any(e.startswith("STATUS.annotate.json: ok") for e in r["evidence"]), r["evidence"])
        self.assertFalse(any("no STATUS.json" in e for e in r["evidence"]), r["evidence"])

    def test_every_status_is_read_and_one_that_is_not_ok_is_enough(self):
        r = self._tier({"command": writes({"STATUS.json": {"status": "ok"},
                                           "STATUS.report.json": {"status": "died"}})})
        self.assertFalse(r["ok"], r["evidence"])
        self.assertTrue(any(e.startswith("STATUS.report.json: died") for e in r["evidence"]), r["evidence"])

    def test_a_refusal_written_per_command_is_accepted_and_agree_reads_it(self):
        spec = {"command": writes({"STATUS.plan.json": {"status": "refused", "headline": "confounded"}}),
                "accepts_refusal": True, "refusal_says": "confounded"}
        results = [self._tier(spec, "a"), self._tier(spec, "b")]
        self.assertTrue(all(r["ok"] for r in results), [r["evidence"] for r in results])
        doc = P.load(self.d)
        doc["fixture"] = spec
        L.t_agree(doc, "widget", "alpha", self.d / "fx", results)
        agree = results[-1]
        self.assertEqual(agree["tier"], "agree")
        self.assertTrue(agree["skipped"])
        self.assertTrue(any("declared refusal" in e for e in agree["evidence"]), agree["evidence"])


if __name__ == "__main__":
    unittest.main()
