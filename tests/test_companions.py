"""The companions get written to pass unless each is shown to fail on a planted violation."""
import os
import stat
import unittest
from pathlib import Path

from helpers import fresh_stack, write_plugin, cleanup, PROTO_HEAD
from sch.services.invariant import InvariantFailure
from sch.services.executor import LocalExecutor


class TestKernelCompanions(unittest.TestCase):
    def setUp(self):
        self.st, self.tmp = fresh_stack()

    def tearDown(self):
        self.st.close()
        cleanup(self.tmp)

    def test_a1_a_plugin_that_writes_to_the_observations_is_refused(self):
        obs = self.st.dataset.observations
        os.chmod(obs, stat.S_IWUSR | stat.S_IRUSR)
        d = write_plugin(self.tmp, "vandal", {}, PROTO_HEAD + '''
import os
with open(os.environ["SCH_OBS"], "a") as fh: fh.write("R9999,1,control,U0\\n")
run.finish()
''')
        os.environ["SCH_OBS"] = str(obs)
        try:
            r = self.st.mount(str(d))
        finally:
            os.environ.pop("SCH_OBS", None)
        self.assertEqual(r.status, "refused")
        self.assertIn("A1", r.reason)
        self.assertTrue(any(e["kind"] == "invariant/failed" for e in self.st.prov.replay()))

    def test_d4_count_never_decreases(self):
        with self.assertRaises(InvariantFailure):
            self.st.inv.d4_count_never_decreases(200, 199)
        self.st.inv.d4_count_never_decreases(200, 200)

    def test_d6_differing_result_under_unchanged_tuple_raises(self):
        with self.assertRaises(InvariantFailure):
            self.st.inv.d6_same_tuple_same_result("k", "abc", "abd")

    def test_e5_facts_are_independent(self):
        with self.assertRaises(InvariantFailure):
            self.st.inv.e5_disposer_quiesced({"requested": True, "stopped": False})
        self.st.inv.e5_disposer_quiesced({"requested": True, "stopped": True, "timed_out": True, "exit": 0})

    def test_e5_executor_stops_a_process_that_traps_the_signal(self):
        ex = LocalExecutor()
        script = self.tmp / "trap.py"
        script.write_text("import signal, time, sys\nsignal.signal(signal.SIGTERM, lambda *a: sys.exit(0))\n"
                          "signal.signal(signal.SIGTERM, signal.SIG_IGN)\ntime.sleep(30)\n")
        import sys
        h = ex.launch([sys.executable, str(script)], self.tmp, self.tmp / "trap.log", timeout=0.5)
        f = h.wait()
        self.assertTrue(f["timed_out"])
        self.assertTrue(f["stopped"])
        self.assertTrue(f["requested"])
        self.assertIsNotNone(f["exit"])
        facts = ex.quiesce()
        self.assertTrue(facts["stopped"])

    def test_g2_an_ask_without_a_decision_fails(self):
        self.st.prov.append("escape/ask", gate="x", mounting="y")
        with self.assertRaises(InvariantFailure):
            self.st.inv.g2_escapes_paired()

    def test_g4_a_verdict_outside_the_three_fails(self):
        self.st.prov.append("gate/result", gate="x", verdict="APPROVED", mounting="y")
        with self.assertRaises(InvariantFailure):
            self.st.inv.g4_verdicts_monotonic()

    def test_a2_and_p2_on_the_report(self):
        self.st.prov.record_number("scratch:1", "n", 5, scratch=True)
        rep = self.st.report()                      # scratch is excluded, so it renders
        self.assertNotIn("scratch:1/n", rep["numbers"])
        with self.assertRaises(InvariantFailure):
            self.st.report(include_scratch=True)    # and cannot be quoted in
        with self.assertRaises(InvariantFailure):
            self.st.inv.p2_numbers_resolve({"x/y": {"value": 1, "event": 999999}})

    def test_plugin_companion_fails_on_a_planted_regression(self):
        # filter_threshold's companion: every masked row is in the removal record. Break it.
        import shutil
        src = Path(__file__).resolve().parents[1] / "plugins" / "table" / "filter_threshold"
        broken = self.tmp / "broken" / "filter_threshold"
        shutil.copytree(src, broken)
        run = (broken / "run.py").read_text().replace('run.table("removal_record", removed,',
                                                     'run.table("removal_record", removed[:-1],')
        (broken / "run.py").write_text(run)
        (broken / "run.py").chmod(0o755)
        r = self.st.mount(str(broken), {"min": 5})
        self.assertEqual(r.status, "refused")
        self.assertIn("masked without a record", r.reason)
        self.assertTrue(any(e["kind"] == "invariant/failed" and e["owner"] == "filter_threshold"
                            for e in self.st.prov.replay()))
        # and the unbroken one holds
        r = self.st.mount(str(src), {"min": 5})
        self.assertTrue(r.ok, r.reason)

    def test_an_empty_companion_is_decoration(self):
        d = write_plugin(self.tmp, "hollow", {"invariant": "invariant.py", "no_runtime_invariant": None},
                         PROTO_HEAD + "run.finish()", extra={"invariant.py": '''
import json, sys
json.dump({"held": [], "failed": []}, open(sys.argv[2], "w"))
'''})
        r = self.st.mount(str(d))
        self.assertEqual(r.status, "refused")
        self.assertIn("decoration", r.reason)


if __name__ == "__main__":
    unittest.main()
