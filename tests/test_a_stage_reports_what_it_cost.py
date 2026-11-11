"""What a stage cost, as the scheduler measured it, and where its job runs (harness W042, GAP-C91).

GOALS A3.4 asks for cells, wall time and peak memory per stage. Before W042 the pbs executor read the
scheduler only for the job's state and exit, so no record held a stage's peak memory. Now:
  - each run's facts carry `cost`: the scheduler's `resources_used` (wall time, peak memory) once the
    job has ended, or `from: null` with the reason when the scheduler said nothing after the end;
    under the local executor, the clock and "peak memory not measured", never a filled-in figure;
  - each run is a `run/cost` event, and the stage's report gives `cost`: its cells, the summed wall
    time and the largest peak, each with the events it came from, and every unmeasured run by name;
  - a run's size is declared as `ncpus`, `mem`, `walltime` and written in the scheduler's words, and
    its queue is the FIRST of the site's declared queues whose ceilings hold it; a size no queue
    holds is refused before any qsub.
Driven through `sch mount` with the stand-in scheduler (tests/fixtures/fake_pbs.py); nothing here
touches a cluster.
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

from helpers import FIXTURES
from sch import yamlish
from sch.cli import main
from sch.kernel import Stack
from sch.plugin.test import table_fixture
from sch.services.executor import sized

USED = {"walltime": "00:01:05", "mem": "2048kb", "ncpus": "1", "cput": "00:00:30"}
QUEUES = [{"queue": "q_small", "walltime": "01:00:00", "ncpus": 2, "mem": "4gb"},
          {"queue": "q_big", "walltime": "48:00:00", "ncpus": 24, "mem": "90gb"}]


def cli(*argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(list(argv))
    return rc, buf.getvalue()


class _Pbs(unittest.TestCase):
    ENV = ("FAKE_PBS_STATE", "FAKE_PBS_MODE", "FAKE_PBS_USED", "FAKE_PBS_HISTORY")

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sch-cost-"))
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
        self._env = {k: os.environ.get(k) for k in self.ENV}
        for k in self.ENV:
            os.environ.pop(k, None)
        os.environ["FAKE_PBS_STATE"] = str(self.state)
        os.environ["FAKE_PBS_USED"] = json.dumps(USED)

    def tearDown(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.tmp, ignore_errors=True)

    def declare(self, executor="pbs", **over):
        decl = yamlish.load(self.stack / "stack.yml")
        decl["executor"] = executor
        cfg = {"queue": "q_default", "select": "1:ncpus=1:mem=1gb", "walltime": "00:10:00",
               "commands": dict(self.commands), "poll_s": 0.01, "stop_grace_s": 0.2,
               "queue_full_first_wait_s": 0.01, "seal_visibility_s": 0.2, **over}
        decl["pbs"] = {k: v for k, v in cfg.items() if v is not None}
        yamlish.dump(decl, self.stack / "stack.yml")

    def mount(self, *extra):
        rc, out = cli("--json", "mount", "--stack", str(self.stack), "filter_threshold", "--param", "min=5",
                      *extra)
        return rc, json.loads(out)

    def report(self) -> dict:
        rc, out = cli("--json", "report", "--stack", str(self.stack))
        self.assertEqual(rc, 0, out)
        return json.loads((self.stack / "report" / "report.json").read_text())

    def qsubs(self) -> int:
        if not self.state.exists():
            return 0
        return len([c for c in json.loads(self.state.read_text())["calls"] if c[0] == "qsub"])


class EachRunCarriesWhatTheSchedulerMeasured(_Pbs):
    def test_every_run_records_the_schedulers_wall_time_and_peak_memory_and_the_report_sums_them(self):
        self.declare()
        rc, r = self.mount()
        self.assertEqual((rc, r["status"]), (0, "mounted"), r)
        facts = json.loads((self.stack.resolve() / "plugins" / "filter_threshold" / "facts.json").read_text())
        self.assertEqual(facts["cost"]["from"], "scheduler")
        self.assertEqual((facts["cost"]["wall_s"], facts["cost"]["peak_mem_kb"], facts["cost"]["cput_s"]),
                         (65, 2048, 30))
        self.assertEqual(facts["cost"]["resources_used"], USED, "the scheduler's words, verbatim")
        self.assertEqual(facts["cost"]["job"], facts["job"])
        rep = self.report()
        cost = rep["cost"]
        runs = cost["runs"]
        self.assertGreaterEqual(len(runs), 2, "the method and its companion at least, each a job")
        self.assertEqual({x["from"] for x in runs}, {"scheduler"})
        self.assertEqual(cost["wall_s"]["value"], 65 * len(runs))
        self.assertEqual(cost["peak_mem_kb"]["value"], 2048)
        self.assertEqual(cost["unmeasured"], [])
        # every figure names the events it came from, and they are the run/cost events
        events = {e["seq"]: e for e in json.loads(cli("--json", "events", "--stack", str(self.stack))[1])}
        self.assertEqual(sorted(cost["wall_s"]["events"]), sorted(x["event"] for x in runs))
        self.assertTrue(all(events[x["event"]]["kind"] == "run/cost" for x in runs))
        self.assertEqual(events[cost["cells"]["event"]]["kind"], "cost/cells")
        ids = Stack(self.stack).dataset.ids
        self.assertEqual(cost["cells"]["value"], len(ids() if callable(ids) else ids))

    def test_a_job_the_scheduler_no_longer_knows_is_unmeasured_and_said_never_filled_in(self):
        self.declare()
        os.environ["FAKE_PBS_HISTORY"] = "0"          # the server forgets an ended job at once
        rc, r = self.mount()
        self.assertEqual((rc, r["status"]), (0, "mounted"), r)
        cost = self.report()["cost"]
        self.assertIsNone(cost["peak_mem_kb"])
        self.assertIsNone(cost["wall_s"])
        self.assertTrue(cost["unmeasured"])
        for u in cost["unmeasured"]:
            self.assertEqual(u["missing"], ["wall_s", "peak_mem_kb"])
            self.assertIn("said nothing", u["why"])

    def test_a_scheduler_that_reports_no_usage_is_said_and_the_local_executor_measures_its_clock_only(self):
        self.declare()
        os.environ["FAKE_PBS_USED"] = "none"
        rc, r = self.mount()
        self.assertEqual((rc, r["status"]), (0, "mounted"), r)
        u = self.report()["cost"]["unmeasured"]
        self.assertTrue(u and all("carried no resources_used" in x["why"] for x in u), u)
        # the local executor: its own clock, and peak memory named as not measured
        shutil.rmtree(self.stack)
        rows, design = self.tmp / "rows.csv", self.tmp / "design.csv"
        Stack.init(self.stack, "table/1.0", str(rows), str(design),
                   keys={"value": "score", "group": "arm", "unit": "unit"}).close()
        rc, r = self.mount()
        self.assertEqual((rc, r["status"]), (0, "mounted"), r)
        cost = self.report()["cost"]
        self.assertEqual(cost["measured_by"], ["local"])
        self.assertGreater(cost["wall_s"]["value"], 0)
        self.assertIsNone(cost["peak_mem_kb"])
        self.assertTrue(all(x["missing"] == ["peak_mem_kb"] and "measures none" in x["why"]
                            for x in cost["unmeasured"]))


class TheQueueIsChosenFromTheSize(_Pbs):
    def test_a_size_is_written_in_the_schedulers_words_and_takes_the_first_queue_that_holds_it(self):
        self.declare(queues=QUEUES, plugins={"filter_threshold": {"ncpus": 4, "mem": "8gb",
                                                                  "walltime": "02:00:00"}})
        rc, r = self.mount()
        self.assertEqual((rc, r["status"]), (0, "mounted"), r)
        script = (self.stack.resolve() / "plugins" / "filter_threshold" / "pbs" / "job.pbs").read_text()
        self.assertIn("#PBS -q q_big\n", script, "4 cpus and 2 h are over q_small's ceilings")
        self.assertIn("#PBS -l select=1:ncpus=4:mem=8gb\n", script)
        self.assertIn("#PBS -l walltime=02:00:00\n", script)
        # the companion is not the stage's run: the site's default size, and the first queue that holds it
        comp = [p for p in (self.stack.resolve() / "plugins" / "filter_threshold").rglob("job.pbs")
                if p.parent.parent.name != "filter_threshold"]
        for p in comp:
            self.assertIn("#PBS -q q_small\n", p.read_text())
            self.assertIn("#PBS -l select=1:ncpus=1:mem=1gb\n", p.read_text())

    def test_a_size_no_declared_queue_holds_is_refused_before_any_qsub(self):
        self.declare(queues=QUEUES, plugins={"filter_threshold": {"ncpus": 64, "mem": "500gb",
                                                                  "walltime": "100:00:00"}})
        rc, r = self.mount()
        self.assertNotEqual(r["status"], "mounted", r)
        self.assertIn("no declared queue holds", json.dumps(r))
        self.assertEqual(self.qsubs(), 0, "refused before any qsub")

    def test_the_rule_itself(self):
        self.assertEqual(sized({"queue": "a", "select": "2:ncpus=8:mem=10gb"})["select"], "2:ncpus=8:mem=10gb")
        got = sized({"queue": "a", "select": "1:ncpus=1:mem=1gb", "queues": QUEUES, "ncpus": 2, "mem": "3gb",
                     "walltime": "00:30:00"}, {"ncpus": 2, "mem": "3gb"})
        self.assertEqual((got["queue"], got["select"]), ("q_small", "1:ncpus=2:mem=3gb"))
        # 16 cpus in two chunks of 8 is 16 cpus: over q_small, held by q_big
        got = sized({"select": "2:ncpus=8:mem=1gb", "walltime": "00:10:00", "queues": QUEUES})
        self.assertEqual(got["queue"], "q_big")
        # a queue named at the most specific layer is that layer's word, not chosen
        self.assertEqual(sized({"queue": "mine", "queues": QUEUES, "select": "1:ncpus=99"},
                               {"queue": "mine"})["queue"], "mine")


if __name__ == "__main__":
    unittest.main()
