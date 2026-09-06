import unittest
from helpers import ROOT  # noqa: F401
from sch import yamlish


class TestYamlish(unittest.TestCase):
    def test_roundtrip_manifest_shapes(self):
        text = '''
contract: "1.0"
name: velocity
version: 0.1.0
when_to_use: >
  spans two
  lines
class: method
executor: {cost: high, gpu: optional}
needs:   [matrix/spliced, "column/{label}"]
provides:
  - column/velocity_confidence
  - "embedding/velocity_*"
wraps:
  tool: scvelo
  version: "0.3.4"
capabilities:
  "capability:embedding": embedding/*
list_of_maps:
  - name: a
    v: 1
  - name: b
    v: 2
empty: []
flag: true
none: null
num: 3.5
# a comment
cannot_show:
  - Velocity is a DIRECTION, not a rate.
'''
        d = yamlish.loads(text)
        self.assertEqual(d["contract"], "1.0")
        self.assertEqual(d["when_to_use"], "spans two lines")
        self.assertEqual(d["executor"], {"cost": "high", "gpu": "optional"})
        self.assertEqual(d["needs"], ["matrix/spliced", "column/{label}"])
        self.assertEqual(d["provides"][1], "embedding/velocity_*")
        self.assertEqual(d["wraps"]["version"], "0.3.4")
        self.assertEqual(d["capabilities"]["capability:embedding"], "embedding/*")
        self.assertEqual(d["list_of_maps"][1], {"name": "b", "v": 2})
        self.assertEqual(d["empty"], [])
        self.assertIs(d["flag"], True)
        self.assertIsNone(d["none"])
        self.assertEqual(d["num"], 3.5)
        again = yamlish.loads(yamlish.dumps(d))
        self.assertEqual(again, d)

    def test_errors_name_the_line(self):
        with self.assertRaises(yamlish.YamlError) as cm:
            yamlish.loads("a: 1\n\tb: 2\n")
        self.assertIn("line 2", str(cm.exception))
        with self.assertRaises(yamlish.YamlError):
            yamlish.loads("a: [1, 2\n")
        with self.assertRaises(yamlish.YamlError):
            yamlish.loads("a: 1\na: 2\n")


if __name__ == "__main__":
    unittest.main()
