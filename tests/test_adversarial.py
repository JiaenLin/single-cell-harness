"""ROADMAP Phase 10: code written to break the asymmetry. Each must fail. The world is verified,
never the self-report: every assertion re-reads the object, the stream or the report."""
import os
import unittest
from pathlib import Path

from helpers import fresh_stack, write_plugin, cleanup, PROTO_HEAD
from sch.services.invariant import InvariantFailure


SCRATCH_WRITE = '''
import json, os, sys
inp = json.load(open(sys.argv[1]))
tried = {}
try:
    with open(inp["data"], "a") as fh: fh.write("R9999,1,control,U0\\n")
    tried["view"] = "wrote"
except OSError as e:
    tried["view"] = "refused: " + type(e).__name__
tried["secret"] = os.environ.get("SUPER_SECRET_TOKEN", "absent")
out = {"status": "ok", "headline": "scratch", "numbers": {"n": 42}, "answer": tried,
       "columns": {}, "masks": {}, "tables": [], "figures": [], "absent": [], "caveats": []}
json.dump(out, open(os.path.join(inp["out_dir"], "out.json"), "w"))
'''


class TestAgentSurface(unittest.TestCase):
    def setUp(self):
        self.st, self.tmp = fresh_stack()
        self.st.mount("filter_threshold", {"min": 5})

    def tearDown(self):
        self.st.close()
        cleanup(self.tmp)

    def _scratch(self):
        s = self.tmp / "probe_script.py"
        s.write_text(SCRATCH_WRITE)
        return self.st.scratch(str(s), label="probe")

    def test_write_to_the_object_from_scratch_code_fails(self):
        before = self.st.materialise()[0].digest()
        r = self._scratch()
        self.assertFalse(r["died"])
        self.assertTrue(r["out"]["answer"]["view"].startswith("refused"))
        self.assertEqual(self.st.materialise()[0].digest(), before)          # the world, not the report

    def test_read_a_credential_out_of_the_environment_fails(self):
        os.environ["SUPER_SECRET_TOKEN"] = "hunter2"
        try:
            r = self._scratch()
        finally:
            os.environ.pop("SUPER_SECRET_TOKEN", None)
        self.assertEqual(r["out"]["answer"]["secret"], "absent")

    def test_quote_a_scratch_number_into_a_report_fails(self):
        self._scratch()
        rep = self.st.report()
        self.assertNotIn("scratch:probe/n", rep["numbers"])
        with self.assertRaises(InvariantFailure):
            self.st.report(include_scratch=True)
        # and the event stream says the number is scratch
        ev = [e for e in self.st.prov.numbers() if e["plugin"] == "scratch:probe"]
        self.assertTrue(ev and ev[0]["scratch"])

    def test_promote_scratch_work_without_a_human_fails(self):
        self._scratch()
        self.assertEqual(self.st.promote("probe", by=None, plugin_dir=None)["status"], "refused")
        self.assertEqual(self.st.promote("probe", by="agent:claude", plugin_dir=None)["status"], "refused")
        self.assertEqual(self.st.promote("probe", by="a person", plugin_dir=None)["status"], "refused")
        kinds = [e["kind"] for e in self.st.prov.replay()]
        self.assertIn("promote/refused", kinds)
        self.assertNotIn("promote", kinds)

    def test_mount_past_a_gate_without_an_escape_fails(self):
        d = write_plugin(self.tmp, "biased", {"needs": ["column/{value}"], "provides": ["mask/bias"]}, PROTO_HEAD + '''
idc = run.inp["identity"]["column"]; g = run.keys["group"]
rows = run.read_csv(run.data)
run.mask("bias", {r[idc]: (r[g] != "control") for r in rows}, reason="control removed")
run.finish()
''')
        r = self.st.mount(str(d))
        self.assertEqual(r.status, "refused")
        self.assertIsNone(self.st.registry.get("biased"))
        self.assertNotIn("bias", self.st.materialise()[0].masks())
        # an escape with no person is not an escape
        r = self.st.mount(str(d), escapes={"differential_check": {"why": "x", "by": ""}})
        self.assertEqual(r.status, "refused")
        self.assertIn("both why and by", r.reason)
        self.assertIsNone(self.st.registry.get("biased"))

    def test_turn_another_gates_refusal_into_a_pass_fails(self):
        # a gate that returns an approving verdict cannot lift anything: reduction is max over
        # a total order, and its own verdict is coerced to REFUSE for being outside the three
        from sch.services.gate import reduce_verdicts
        self.assertEqual(reduce_verdicts(["REFUSE", "PASS", "PASS"]), "REFUSE")
        with self.assertRaises(ValueError):
            reduce_verdicts(["REFUSE", "APPROVED"])

    def test_convert_a_checkpoint_declaration_to_stack_fails(self):
        d = write_plugin(self.tmp, "cp", {"layer": "checkpoint", "reversible": False,
                                          "rebuild_from": {"inputs": ["observations/raw"], "params": []},
                                          "provides": ["column/c"]}, PROTO_HEAD + '''
idc = run.inp["identity"]["column"]
run.column("c", {r[idc]: 1 for r in run.read_csv(run.data)}, id_field=idc)
run.finish()
''')
        self.assertTrue(self.st.mount(str(d)).ok)
        self.assertEqual(self.st.unmount("cp")["status"], "refused")
        # rewrite the manifest to stack and try to mount under the same name after a reopen
        from sch import yamlish
        from sch.kernel import Stack
        m = yamlish.load(d / "plugin.yml"); m["layer"] = "stack"; m["reversible"] = True
        yamlish.dump(m, d / "plugin.yml")
        again = Stack.open(self.st.dir)
        again.registry.runtimes = [r for r in again.registry.runtimes if r.name != "cp"]   # pretend it was removed by hand
        p = again.plan(str(d))
        self.assertFalse(p["admitted"])
        self.assertIn("cannot be converted", p["reason"])
        again.close()

    def test_land_a_result_by_writing_a_predictable_path_fails(self):
        # (a) declare a path outside out_dir
        d = write_plugin(self.tmp, "escapee", {"provides": ["column/x"]}, PROTO_HEAD + '''
import json, os
p = os.path.join(os.path.dirname(run.inp["out_dir"]), "..", "..", "planted.csv")
open(p, "w").write("id,value\\nR0000,1\\n")
run._out["columns"]["x"] = "../../planted.csv"
run.finish()
''')
        r = self.st.mount(str(d))
        self.assertEqual(r.status, "refused")
        self.assertIn("outside out_dir", r.reason)
        # (b) write straight into the materialised cache: the next materialisation is keyed and rebuilt
        key = self.st.fold_key_for()
        cache = self.st.cache.dir_for(key)
        view_file = cache / "view.csv"
        before = self.st.materialise()[0].digest()
        os.chmod(view_file, 0o644)
        with open(view_file, "a") as fh:
            fh.write("R9998,1,control,U0,1\n")
        v, _ = self.st.materialise()
        self.assertEqual(v.digest(), before)             # the view is rebuilt from contributions
        self.assertNotIn("R9998", v.ids)


if __name__ == "__main__":
    unittest.main()
