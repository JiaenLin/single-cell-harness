import unittest
from helpers import ROOT  # noqa: F401
from sch.core import Context, Service, InjectError, DisposeError


class TestContext(unittest.TestCase):
    def test_inject_is_declared_not_discovered(self):
        ctx = Context()
        ctx.provide("dataset", Service())
        self.assertEqual(list(ctx.inject(["dataset"])), ["dataset"])
        with self.assertRaises(InjectError):
            ctx.inject(["dataset", "executor"])

    def test_disposers_run_in_exactly_reverse_order(self):
        ctx = Context()
        order = []
        for i in range(5):
            ctx.effect(f"e{i}", (lambda i=i: order.append(i)))
        ctx.dispose()
        self.assertEqual(order, [4, 3, 2, 1, 0])

    def test_fork_sees_parent_and_owns_its_effects(self):
        ctx = Context()
        ctx.provide("dataset", Service())
        f = ctx.fork("child")
        self.assertTrue(f.has("dataset"))
        gone = []
        f.effect("x", lambda: gone.append("x"))
        ctx.effect("y", lambda: gone.append("y"))
        f.dispose()
        self.assertEqual(gone, ["x"])
        ctx.dispose()
        self.assertEqual(gone, ["x", "y"])

    def test_e5_a_disposer_that_cannot_confirm_termination_fails_the_dispose(self):
        ctx = Context()
        ctx.effect("job", lambda: {"requested": True, "stopped": False, "timed_out": True, "exit": None})
        with self.assertRaises(DisposeError):
            ctx.dispose()
        ctx2 = Context()
        ctx2.effect("job", lambda: {"requested": True, "stopped": True, "timed_out": True, "exit": 0})
        facts = ctx2.dispose()
        # timed_out AND exit 0 are reported independently — a trapped signal is not a clean run
        self.assertTrue(facts[0]["timed_out"] and facts[0]["exit"] == 0 and facts[0]["stopped"])

    def test_bus_broadcast_and_waterfall(self):
        ctx = Context()
        ctx.on("x", lambda v: v + 1)
        ctx.on("x", lambda v: v + 2)
        self.assertEqual(ctx.emit("x", 1), [2, 3])
        ctx.on("g", lambda v: None)
        ctx.on("g", lambda v: "REFUSE")
        ctx.on("g", lambda v: "PASS")
        self.assertEqual(ctx.bail("g", 0), "REFUSE")

    def test_c4_serialises_names_only(self):
        ctx = Context()
        ctx.provide("dataset", Service())
        self.assertIn('"services": ["dataset"]', ctx.to_json())


if __name__ == "__main__":
    unittest.main()
