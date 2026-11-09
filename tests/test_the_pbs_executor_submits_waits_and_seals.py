"""The `pbs` executor: the run directory before qsub, the seal by the job, and no site literal.

It was refused as "not shipped before ROADMAP Phase 9" (sch/services/executor.py, before W010) and
ADR-0029 withdrew that phase stop. These tests drive it through `sch mount` with a stand-in qsub,
qstat and qdel (tests/fixtures/fake_pbs.py), because nothing here may touch a cluster:

  - every plugin run is a job whose script carries the DECLARED queue, select and walltime, and
    nothing the declaration did not give;
  - the job seals its own directory (SEALED.txt / FAILED.txt with the exit and the job id), and the
    executor reads the exit from that seal - an outcome nobody recorded is not a zero;
  - a declaration missing a resource is refused before anything is submitted;
  - a full queue is waited for, not failed (scQC's lesson, ADR-0027 Q11);
  - a stop is a qdel CONFIRMED by qstat, and one that cannot be confirmed fails E5.
"""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from helpers import FIXTURES, PROTO_HEAD, write_plugin
from sch import yamlish
from sch.cli import main
from sch.kernel import Stack
from sch.plugin.test import table_fixture
from sch.services.executor import make_executor
from sch.services.invariant import InvariantFailure, InvariantService
from sch.services.provenance import Provenance


def cli(*argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(list(argv))
    return rc, buf.getvalue()


class ThePbsExecutor(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sch-pbs-"))
        rows, design = table_fixture(self.tmp)
        Stack.init(self.tmp / "stack", "table/1.0", str(rows), str(design),
                   keys={"value": "score", "group": "arm", "unit": "unit"}).close()
        self.stack = self.tmp / "stack"
        self.state = self.tmp / "pbs_state.json"
        bin_ = self.tmp / "bin"
        bin_.mkdir()
        self.commands = {}
        for c in ("qsub", "qstat", "qdel"):
            w = bin_ / c
            w.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{FIXTURES / "fake_pbs.py"}" {c} "$@"\n')
            w.chmod(0o755)
            self.commands[c] = str(w)
        self._env = {k: os.environ.get(k) for k in ("FAKE_PBS_STATE", "FAKE_PBS_MODE")}
        os.environ["FAKE_PBS_STATE"] = str(self.state)
        os.environ.pop("FAKE_PBS_MODE", None)
        self.declare()

    def tearDown(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.tmp, ignore_errors=True)

    def config(self, **over):
        cfg = {"queue": "testq", "select": "1:ncpus=1:mem=1gb", "walltime": "00:10:00",
               "commands": dict(self.commands), "poll_s": 0.01, "stop_grace_s": 0.2,
               "queue_full_first_wait_s": 0.01, "seal_visibility_s": 0.2}
        cfg.update(over)
        return {k: v for k, v in cfg.items() if v is not None}

    def declare(self, **over):
        decl = yamlish.load(self.stack / "stack.yml")
        decl["executor"] = "pbs"
        decl["pbs"] = self.config(**over)
        yamlish.dump(decl, self.stack / "stack.yml")

    def calls(self, kind=None) -> list:
        if not self.state.exists():
            return []
        calls = json.loads(self.state.read_text())["calls"]
        return [c for c in calls if kind is None or c[0] == kind]

    def mount(self, plugin="filter_threshold", *extra):
        rc, out = cli("--json", "mount", "--stack", str(self.stack), plugin, *extra)
        return rc, json.loads(out)

    # ------------------------------------------------------------------------ the round trip
    def test_a_mount_is_jobs_that_carry_the_declaration_and_seal_themselves(self):
        rc, r = self.mount("filter_threshold", "--param", "min=5")
        self.assertEqual((rc, r["status"]), (0, "mounted"), r)
        run = self.stack.resolve() / "plugins" / "filter_threshold"
        script = (run / "pbs" / "job.pbs").read_text()
        self.assertIn("#PBS -q testq\n", script)
        self.assertIn("#PBS -l select=1:ncpus=1:mem=1gb\n", script)
        self.assertIn("#PBS -l walltime=00:10:00\n", script)
        self.assertIn(f"#PBS -o {run / 'pbs'}/\n", script)
        self.assertIn("set -euo pipefail", script)
        # the job sealed its own run, and the executor took the exit from that seal
        seal = (run / "pbs" / "SEALED.txt").read_text()
        self.assertIn("exit=0\n", seal)
        self.assertIn("jobid=1000.server\n", seal)
        facts = json.loads((run / "facts.json").read_text())
        self.assertEqual((facts["job"], facts["exit"], facts["executor"]), ("1000.server", 0, "pbs"))
        # every plugin run went to the scheduler - the method, its gate's probe, the gate and the
        # companion - each with the declared queue and nothing else
        qsubs = self.calls("qsub")
        self.assertGreaterEqual(len(qsubs), 4, qsubs)
        for c in qsubs:
            text = Path(c[-1]).read_text()
            self.assertEqual([x for x in text.splitlines() if x.startswith("#PBS -q")], ["#PBS -q testq"])
            self.assertTrue((Path(c[-1]).parent / "SEALED.txt").exists(), c)

    def test_a_failing_entry_point_is_sealed_failed_and_the_mount_died(self):
        write_plugin(self.tmp / "plugins", "falls_over", {}, PROTO_HEAD + "sys.exit(3)\n")
        rc, r = self.mount(str(self.tmp / "plugins" / "falls_over"))
        self.assertEqual((rc, r["status"]), (2, "died"), r)
        run = self.stack / "plugins" / "falls_over"
        self.assertIn("exit=3\n", (run / "pbs" / "FAILED.txt").read_text())
        self.assertIn("missing=", (run / "pbs" / "FAILED.txt").read_text())
        self.assertFalse((run / "pbs" / "SEALED.txt").exists())
        self.assertEqual(json.loads((run / "facts.json").read_text())["exit"], 3)

    def test_a_declaration_missing_a_resource_is_refused_before_anything_is_submitted(self):
        for missing in ("queue", "select", "walltime"):
            with self.subTest(missing):
                self.declare(**{missing: None})
                rc, r = self.mount("filter_threshold", "--param", "min=5")
                self.assertEqual((rc, r["status"]), (2, "refused"), r)
                self.assertIn(f"pbs.{missing}", r["reason"])
                self.assertEqual(self.calls("qsub"), [])

    def test_the_queue_may_come_from_the_site_layer_and_never_from_the_harness(self):
        site = self.tmp / "site"
        site.mkdir()
        yamlish.dump({"pbs": {"queue": "sitequeue"}}, site / "stack.yml")
        self.declare(queue=None)
        old = os.environ.get("SCH_SITE")
        os.environ["SCH_SITE"] = str(site)
        try:
            rc, r = self.mount("filter_threshold", "--param", "min=5")
        finally:
            if old is None:
                os.environ.pop("SCH_SITE", None)
            else:
                os.environ["SCH_SITE"] = old
        self.assertEqual((rc, r["status"]), (0, "mounted"), r)
        self.assertIn("#PBS -q sitequeue\n",
                      (self.stack / "plugins" / "filter_threshold" / "pbs" / "job.pbs").read_text())

    def test_a_full_queue_is_waited_for_not_failed(self):
        os.environ["FAKE_PBS_MODE"] = "full:1"
        rc, r = self.mount("filter_threshold", "--param", "min=5")
        self.assertEqual((rc, r["status"]), (0, "mounted"), r)
        self.assertGreaterEqual(len(self.calls("qsub")), 2)

    def test_an_outcome_nobody_recorded_is_not_a_success(self):
        os.environ["FAKE_PBS_MODE"] = "lost"
        rc, r = self.mount("filter_threshold", "--param", "min=5")
        self.assertEqual((rc, r["status"]), (2, "died"), r)
        facts = json.loads((self.stack / "plugins" / "filter_threshold" / "facts.json").read_text())
        self.assertIsNone(facts["exit"])

    def test_a_job_killed_by_the_scheduler_seals_failed_not_sealed(self):
        """The job's own script, under real bash and a real signal: the scheduler's TERM at
        walltime must leave FAILED.txt with a nonzero exit, never a green seal."""
        import signal
        import subprocess
        import time
        from sch.services.executor import PbsExecutor
        run = self.tmp / "killed"
        (run / "pbs").mkdir(parents=True)
        started = run / "started"
        ex = PbsExecutor(config=self.config())
        script = run / "pbs" / "job.pbs"
        script.write_text(ex._script(
            [sys.executable, "-c", f"open({str(started)!r}, 'w').close(); import time; time.sleep(30)"],
            run, run / "stderr.log", {}, False, "killed", [run / "out" / "out.json"],
            ex.settings("killed"), run / "pbs"))
        proc = subprocess.Popen(["bash", str(script)], start_new_session=True)
        deadline = time.monotonic() + 20
        while not started.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        os.killpg(proc.pid, signal.SIGTERM)          # PBS signals the job's whole session
        proc.wait(timeout=20)
        seal = (run / "pbs" / "FAILED.txt").read_text()
        self.assertIn("exit=143\n", seal)
        self.assertFalse((run / "pbs" / "SEALED.txt").exists())

    # ------------------------------------------------------------------------ E5
    def test_a_stop_is_a_qdel_confirmed_and_an_unconfirmable_one_fails_e5(self):
        work = self.tmp / "work"
        for mode, stopped in (("hold", True), ("undeletable", False)):
            with self.subTest(mode):
                os.environ["FAKE_PBS_MODE"] = mode
                ex = make_executor("pbs", config=self.config())
                run = work / mode
                run.mkdir(parents=True)
                h = ex.launch([sys.executable, "-c", "pass"], run, run / "stderr.log")
                self.assertTrue(h.running())
                facts = ex.quiesce()
                self.assertTrue(facts["requested"])
                self.assertEqual(facts["stopped"], stopped, facts)
                self.assertTrue(any(c[0] == "qdel" for c in self.calls()))
                inv = InvariantService(Provenance(self.tmp / f"events_{mode}.jsonl"), None)
                if stopped:
                    inv.e5_disposer_quiesced(facts)
                else:
                    with self.assertRaises(InvariantFailure):
                        inv.e5_disposer_quiesced(facts)

    def test_a_timeout_is_a_qdel_and_three_independent_facts(self):
        os.environ["FAKE_PBS_MODE"] = "hold"
        rc, r = self.mount("filter_threshold", "--param", "min=5", "--param", "timeout=0.05")
        self.assertEqual((rc, r["status"]), (2, "died"), r)
        facts = json.loads((self.stack / "plugins" / "filter_threshold" / "facts.json").read_text())
        self.assertEqual((facts["timed_out"], facts["requested"], facts["stopped"]), (True, True, True))
        self.assertEqual(facts["exit"], 271)
        self.assertTrue(self.calls("qdel"))


if __name__ == "__main__":
    unittest.main()
