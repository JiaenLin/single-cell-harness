"""The L2 test: the whole kernel on a profile with no biology in it (ROADMAP Phase 1)."""
import itertools
import json
import unittest
from pathlib import Path

from helpers import fresh_stack, write_plugin, cleanup, PROTO_HEAD, PLUGINS, ROOT
from sch.services.gate import reduce_verdicts


class TestKernelOnTableProfile(unittest.TestCase):
    def setUp(self):
        self.st, self.tmp = fresh_stack()

    def tearDown(self):
        self.st.close()
        cleanup(self.tmp)

    def test_mount_unmount_restores_by_digest_and_invalidates_without_consulting(self):
        st = self.st
        base = st.materialise()[0].digest()
        r = st.mount("filter_threshold", {"min": 5})
        self.assertTrue(r.ok, r.reason)
        self.assertEqual([g["verdict"] for g in r.gates], ["PASS"])
        r2 = st.mount("score")
        self.assertTrue(r2.ok, r2.reason)
        self.assertIn("filter_threshold", st.registry.get("score").reads_from)
        v = st.materialise()[0]
        self.assertLess(v.n, v.n_total)
        self.assertIn("rank_fraction", v.columns())
        # dry run names the cost before it is paid
        plan = st.unmount("filter_threshold", dry_run=True)
        self.assertEqual(plan["status"], "planned")
        self.assertGreater(plan["would_restore"], 0)
        self.assertEqual(plan["would_invalidate"], [{"name": "score", "state": "invalid"}])
        self.assertEqual(st.registry.get("score").state, "mounted")
        # real unmount: score is invalidated without being re-run
        runs_before = len([e for e in st.prov.replay() if e["kind"] == "mount"])
        st.unmount("filter_threshold")
        self.assertEqual(st.registry.get("score").state, "invalid")
        self.assertEqual(len([e for e in st.prov.replay() if e["kind"] == "mount"]), runs_before)
        st.unmount("score")
        self.assertEqual(st.materialise()[0].digest(), base)

    def test_refuses_at_plan_time_with_the_fix_named(self):
        st = self.st
        p = st.plan("score")
        self.assertTrue(p["admitted"])
        st2 = st  # a need that nothing provides
        d = write_plugin(self.tmp, "needy", {"needs": ["embedding/latent"]}, PROTO_HEAD + "run.finish()")
        p = st2.plan(str(d))
        self.assertFalse(p["admitted"])
        self.assertIn("mount something that provides embedding/latent", p["missing"][0]["fix"])
        r = st2.mount(str(d))
        self.assertEqual(r.status, "refused")
        self.assertEqual([e["kind"] for e in st2.prov.replay()][-1], "mount/refused")

    def test_unknown_key_refuses_before_compute(self):
        d = write_plugin(self.tmp, "keyed", {"needs": ["column/{nokey}"]}, PROTO_HEAD + "run.finish()")
        p = self.st.plan(str(d))
        self.assertFalse(p["admitted"])
        self.assertIn("declare the key", p["missing"][0]["fix"])

    def test_checkpoint_cannot_be_unmounted_and_shields_invalidation(self):
        st = self.st
        self.assertTrue(st.mount("score").ok)
        cp = write_plugin(self.tmp, "cp", {"layer": "checkpoint", "reversible": False, "needs": ["column/rank_fraction"],
                                           "rebuild_from": {"inputs": ["column/rank_fraction"], "params": []},
                                           "provides": ["column/regenerated"]}, PROTO_HEAD + '''
idc = run.inp["identity"]["column"]
run.column("regenerated", {r[idc]: 1 for r in run.read_csv(run.data)}, id_field=idc)
run.finish()
''')
        self.assertTrue(st.mount(str(cp)).ok)
        d = write_plugin(self.tmp, "reader", {"needs": ["column/regenerated"], "provides": ["column/twice"]},
                         PROTO_HEAD + '''
idc = run.inp["identity"]["column"]
rows = run.read_csv(run.data)
run.column("twice", {r[idc]: 2 for r in rows}, id_field=idc)
run.finish()
''')
        self.assertTrue(st.mount(str(d)).ok)
        r = st.unmount("cp")
        self.assertEqual(r["status"], "refused")
        # unmounting score reaches the checkpoint, which is marked for REBUILD and shields reader
        plan = st.unmount("score", dry_run=True)
        self.assertEqual(plan["would_invalidate"], [{"name": "cp", "state": "rebuild"}])
        self.assertEqual(st.registry.get("reader").reads_from, ["cp"])

    def test_d6_cache_hits_only_on_the_exact_tuple(self):
        st = self.st
        st.mount("filter_threshold", {"min": 5})
        k1 = st.fold_key_for()
        st.materialise(); st.materialise()
        self.assertGreaterEqual(st.cache.hits, 1)
        st.unmount("filter_threshold")
        st.mount("filter_threshold", {"min": 6})
        self.assertNotEqual(k1, st.fold_key_for())
        st.unmount("filter_threshold")
        st.mount("filter_threshold", {"min": 5})
        self.assertEqual(k1, st.fold_key_for())

    def test_state_version_alone_invalidates_the_cache(self):
        d = write_plugin(self.tmp, "sv", {"provides": ["column/c"]}, PROTO_HEAD + '''
idc = run.inp["identity"]["column"]
run.column("c", {r[idc]: 1 for r in run.read_csv(run.data)}, id_field=idc)
run.finish()
''')
        self.st.mount(str(d))
        k1 = self.st.fold_key_for()
        self.st.unmount("sv")
        d2 = write_plugin(self.tmp, "sv", {"provides": ["column/c"], "state_version": 2}, PROTO_HEAD + '''
idc = run.inp["identity"]["column"]
run.column("c", {r[idc]: 1 for r in run.read_csv(run.data)}, id_field=idc)
run.finish()
''')
        self.st.mount(str(d2))
        self.assertNotEqual(k1, self.st.fold_key_for())

    def test_died_empty_and_entries_are_three_different_facts(self):
        dead = write_plugin(self.tmp, "dead", {}, "import sys; sys.exit(3)")
        empty = write_plugin(self.tmp, "empty", {}, PROTO_HEAD + "run.finish(headline='found nothing')")
        r = self.st.mount(str(dead))
        self.assertEqual(r.status, "died")
        self.assertEqual(r.facts["exit"], 3)
        r = self.st.mount(str(empty))
        self.assertTrue(r.ok)          # a result, not a death
        self.assertEqual(r.headline, "found nothing")

    def test_undeclared_output_is_recorded_and_not_merged(self):
        d = write_plugin(self.tmp, "sneaky", {"provides": ["column/declared"]}, PROTO_HEAD + '''
idc = run.inp["identity"]["column"]
rows = run.read_csv(run.data)
run.column("declared", {r[idc]: 1 for r in rows}, id_field=idc)
run.column("smuggled", {r[idc]: 9 for r in rows}, id_field=idc)
run.finish()
''')
        r = self.st.mount(str(d))
        self.assertTrue(r.ok)
        self.assertEqual(r.undeclared, ["column/smuggled"])
        self.assertNotIn("smuggled", self.st.materialise()[0].columns())
        self.assertTrue(any(e["kind"] == "plugin/undeclared_output" for e in self.st.prov.replay()))

    def test_merge_by_identity_refuses_foreign_and_short_masks(self):
        d = write_plugin(self.tmp, "posn", {"provides": ["mask/m"]}, PROTO_HEAD + '''
rows = run.read_csv(run.data)
run.mask("m", {("X" + r["id"]): True for r in rows}, reason="r")
run.finish()
''')
        r = self.st.mount(str(d))
        self.assertEqual(r.status, "refused")
        self.assertIn("not observations", r.reason)
        d = write_plugin(self.tmp, "short", {"provides": ["mask/m"]}, PROTO_HEAD + '''
rows = run.read_csv(run.data)
run.mask("m", {r["id"]: True for r in rows[:10]}, reason="r")
run.finish()
''')
        r = self.st.mount(str(d))
        self.assertEqual(r.status, "refused")
        self.assertIn("covers 10 of", r.reason)

    def test_a_refusal_is_a_result_with_the_number(self):
        st = self.st
        # arm-selective removal: control rows only -> ratio infinite -> REFUSE
        d = write_plugin(self.tmp, "biased", {"needs": ["column/{value}"], "provides": ["mask/bias"]}, PROTO_HEAD + '''
idc = run.inp["identity"]["column"]; g = run.keys["group"]
rows = run.read_csv(run.data)
run.mask("bias", {r[idc]: (r[g] != "control") for r in rows}, reason="control arm removed")
run.finish()
''')
        r = st.mount(str(d))
        self.assertEqual(r.status, "refused")
        self.assertEqual(r.gates[0]["verdict"], "REFUSE")
        ev = [e for e in st.prov.replay() if e["kind"] == "gate/result"][-1]
        self.assertEqual(ev["verdict"], "REFUSE")
        self.assertIsNotNone(ev["number"])
        self.assertIsNone(st.registry.get("biased"))
        # with a recorded escape: mounted, and the pair is in the stream
        r = st.mount(str(d), escapes={"differential_check": {"why": "test of the escape path", "by": "a person"}})
        self.assertTrue(r.ok, r.reason)
        kinds = [e["kind"] for e in st.prov.replay()]
        self.assertIn("escape/ask", kinds)
        self.assertIn("escape/decision", kinds)
        st.inv.g2_escapes_paired()

    def test_gate_verdict_is_the_same_under_every_permutation(self):
        for perm in itertools.permutations(["PASS", "REVIEW", "REFUSE", "PASS"]):
            self.assertEqual(reduce_verdicts(perm), "REFUSE")
        for perm in itertools.permutations(["PASS", "REVIEW", "PASS"]):
            self.assertEqual(reduce_verdicts(perm), "REVIEW")
        with self.assertRaises(ValueError):
            reduce_verdicts(["APPROVED"])

    def test_probe_and_gate_share_one_number(self):
        st = self.st
        d = write_plugin(self.tmp, "mild", {"needs": ["column/{value}"], "provides": ["mask/mild"]}, PROTO_HEAD + '''
idc = run.inp["identity"]["column"]; g = run.keys["group"]
rows = run.read_csv(run.data)
keep = {}
for n, r in enumerate(rows):
    keep[r[idc]] = not (r[g] == "control" and n % 4 == 0)   # 25% of control, 0% treated
run.mask("mild", keep, reason="q")
run.finish()
''')
        r = st.mount(str(d), escapes={"differential_check": {"why": "measure", "by": "p"}})
        self.assertTrue(r.ok, r.reason)
        gate_number = r.gates[0]["number"]
        probe = st.ask("differential", subject={"masks": {"mild": str(st.dir / "plugins" / "mild" / "out" / "masks" / "mild.csv")}}, upto="mild")
        self.assertEqual(probe["answer"]["max_ratio"], gate_number)

    def test_report_numbers_resolve_to_events(self):
        st = self.st
        st.mount("filter_threshold", {"min": 5})
        rep = st.report()
        self.assertIn("filter_threshold/n_removed", rep["numbers"])
        ev = st.prov.find(rep["numbers"]["filter_threshold/n_removed"]["event"])
        self.assertEqual(ev["kind"], "number")

    def test_stack_dump_and_mount_use_the_same_composition(self):
        from sch.stack import compose
        layers = [("site", {"keys": {"value": "a"}, "plugins": {"p": {"params": {"x": 1}}}}),
                  ("project", {"keys": {"group": "b"}, "plugins": {"p": {"params": {"y": 2}}}})]
        c = compose(layers)
        self.assertEqual(c["keys"], {"value": "a", "group": "b"})
        self.assertEqual(c["plugins"]["p"]["params"], {"x": 1, "y": 2})
        self.assertEqual(c["composed_from"], ["site", "project"])

    def test_fork_and_reopen(self):
        st = self.st
        st.mount("filter_threshold", {"min": 5})
        st.mount("score")
        f = st.fork(self.tmp / "no-filter", without=["filter_threshold"])
        res = f.run_declared()
        self.assertEqual([r.name for r in res], ["score"])
        self.assertTrue(res[0].ok)
        self.assertEqual(f.materialise()[0].n, f.materialise()[0].n_total)
        f.close()
        from sch.kernel import Stack
        again = Stack.open(st.dir)
        self.assertEqual(again.registry.order(), ["filter_threshold", "score"])
        self.assertEqual(again.materialise()[0].digest(), st.materialise()[0].digest())
        again.close()


if __name__ == "__main__":
    unittest.main()
