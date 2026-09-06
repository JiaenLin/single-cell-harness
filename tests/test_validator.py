"""Every validator rule is proved by regression: a deliberately broken plugin per rule."""
import shutil
import tempfile
import unittest
from pathlib import Path

from helpers import write_plugin, PROTO_HEAD, ROOT
from sch.plugin.validate import validate
from sch import yamlish

GOOD_RUN = PROTO_HEAD + "run.finish()\n"


def rules(problems):
    return sorted({p["rule"] for p in problems if p["level"] == "error"})


class TestValidator(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sch-val-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def good(self, name="good", **over):
        return write_plugin(self.tmp, name, over, GOOD_RUN)

    def test_a_valid_plugin_passes_and_shipped_plugins_pass(self):
        self.assertEqual(rules(validate(self.good())), [])
        for pf in (ROOT / "plugins").rglob("plugin.yml"):
            self.assertEqual(rules(validate(pf.parent)), [], str(pf.parent))

    def test_rule_1_contract_and_profile(self):
        self.assertIn(1, rules(validate(self.good(contract="2.0"))))
        self.assertIn(1, rules(validate(self.good("p2", profile="spatial/1.0"))))

    def test_rule_2_required_fields_and_cannot_show(self):
        self.assertIn(2, rules(validate(self.good(cannot_show=[]))))
        d = self.good("nosees")
        m = yamlish.load(d / "plugin.yml"); m.pop("sees"); yamlish.dump(m, d / "plugin.yml")
        self.assertIn(2, rules(validate(d)))
        self.assertIn(2, rules(validate(self.good("todo", summary="TODO later"))))

    def test_rule_3_checkpoint_needs_rebuild_from(self):
        self.assertIn(3, rules(validate(self.good(layer="checkpoint", reversible=False))))
        self.assertIn(3, rules(validate(self.good("l2", layer="sideways"))))

    def test_rule_4_grammar_and_vocabulary(self):
        self.assertIn(4, rules(validate(self.good(provides=["obs/thing"]))))       # slot not in profile
        self.assertIn(4, rules(validate(self.good("g2", needs=["nonsense"]))))

    def test_rule_5_entry_exists(self):
        d = self.good(); (d / "run.py").unlink()
        self.assertIn(5, rules(validate(d)))

    def test_rule_6_and_7_lock_and_selftest(self):
        self.assertIn(6, rules(validate(self.good(needs_env=True))))
        d = self.good("ranges", needs_env=True)
        (d / "lock.yml").write_text("name: x\ndependencies:\n  - python=3.11\n  - pip:\n    - numpy>=1.26\n")
        (d / "selftest.py").write_text("print('ok')\n")
        self.assertIn(7, rules(validate(d)))
        (d / "lock.yml").write_text("name: x\ndependencies:\n  - python=3.11\n  - pip:\n    - numpy==1.26.4\n")
        self.assertNotIn(7, rules(validate(d)))

    def test_rule_8_wraps(self):
        self.assertIn(8, rules(validate(self.good(wraps={"tool": "x", "version": "1"}))))

    def test_rule_9_references_checksums(self):
        d = self.good()
        (d / "references.yml").write_text("references:\n  db:\n    url: http://x\n")
        self.assertIn(9, rules(validate(d)))

    def test_rule_10_reversible_vs_layer(self):
        self.assertIn(10, rules(validate(self.good(layer="checkpoint", reversible=True,
                                                   rebuild_from={"inputs": ["observations/raw"]}))))

    def test_rule_11_no_hard_coded_identifier(self):
        self.assertIn(11, rules(validate(self.good(needs=["column/score"]))))
        d = self.good("src")
        (d / "run.py").write_text(PROTO_HEAD + 'x = rows["score"] if False else 0\nrun.finish()\n')
        self.assertIn(11, rules(validate(d)))

    def test_rule_12_state_version(self):
        d = self.good(provides=["column/x"])
        m = yamlish.load(d / "plugin.yml"); m.pop("state_version"); yamlish.dump(m, d / "plugin.yml")
        self.assertIn(12, rules(validate(d)))

    def test_rule_13_gate_escape_and_verdicts(self):
        self.assertIn(13, rules(validate(self.good("g", **{"class": "gate", "measures_with": "differential",
                                                          "verdict": ["PASS", "APPROVED"], "escape": "--x"}))))
        self.assertIn(13, rules(validate(self.good("g2", **{"class": "gate", "measures_with": "differential",
                                                           "verdict": ["PASS", "REFUSE"]}))))    # no escape

    def test_rule_14_invariant_or_reason(self):
        d = self.good()
        m = yamlish.load(d / "plugin.yml"); m.pop("no_runtime_invariant"); yamlish.dump(m, d / "plugin.yml")
        self.assertIn(14, rules(validate(d)))
        self.assertIn(14, rules(validate(self.good("weak", no_runtime_invariant="not needed"))))
        d = self.good("empty")
        m = yamlish.load(d / "plugin.yml"); m.pop("no_runtime_invariant"); m["invariant"] = "invariant.py"
        yamlish.dump(m, d / "plugin.yml"); (d / "invariant.py").write_text("pass\n")
        self.assertIn(14, rules(validate(d)))

    def test_rule_15_readme_sections(self):
        d = self.good()
        (d / "README.md").write_text("# x\n\n## What it does\nsomething useful for a reader who wants to mount it\n\n"
                                     "## Report surface\nthe numbers a reader could quote, with their limits stated\n\n"
                                     "## Cost\nlow to run and low to unmount, nothing depends on it\n\n## Known limitations\n\n")
        self.assertIn(15, rules(validate(d)))


if __name__ == "__main__":
    unittest.main()
