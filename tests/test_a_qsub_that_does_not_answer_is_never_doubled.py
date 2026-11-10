"""A qsub that does not answer is asked about, never doubled (autodev W029, GAP-C59).

qsub had no timeout (sch/services/executor.py `_submit`), so a qsub that hung held the harness
for as long as it hung; and a qsub that gave up - a client that lost the server after the server
had queued the job - came back as a refusal, while its job ran with nothing watching it. Retrying
it blind would run the plugin twice into one run directory.

Now qsub has a timeout, and before anything is submitted again the scheduler is asked BY JOB NAME
for the jobs of this submission, each confirmed by the token its script declares
(`#PBS -v SCH_SUBMISSION=...`, read from `qstat -x -f`, whose long values PBS wraps onto tab-led
lines) - and, after a look that finds nothing, by the seal the job wrote in the run, since a
server that keeps no history lists no job that has ended. Found, that job is the run's; absent,
the job is submitted again; and when the scheduler cannot say, nothing is submitted again - the
run is refused, naming the job - and the executor keeps the submission, so the command's disposer
asks once more and fails E5 if it still cannot. Driven through `sch mount` with the stand-in
scheduler (tests/fixtures/fake_pbs.py), whose qsub can queue a job and then hang, run it to its
end and then hang, or hang having queued nothing, and whose server may keep no history.
"""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from helpers import FIXTURES
from sch import yamlish
from sch.cli import main
from sch.kernel import Stack
from sch.plugin.test import table_fixture

USER = os.environ.get("USER") or os.environ.get("LOGNAME") or "u"
NAME = "sch_filter_thre"                      # the job name of plugin filter_threshold


def cli(*argv):
    buf, err = io.StringIO(), io.StringIO()
    with redirect_stdout(buf), redirect_stderr(err):
        rc = main(list(argv))
    try:
        return rc, json.loads(buf.getvalue()), err.getvalue()
    except ValueError:
        return rc, {"unparsed": buf.getvalue()}, err.getvalue()


class AQsubThatDoesNotAnswerIsNeverDoubled(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sch-qsub-"))
        rows, design = table_fixture(self.tmp)
        Stack.init(self.tmp / "stack", "table/1.0", str(rows), str(design),
                   keys={"value": "score", "group": "arm", "unit": "unit"}).close()
        self.stack = self.tmp / "stack"
        self.state = self.tmp / "pbs_state.json"
        # the kernel runs inside a job (rule 3), so the user's listing always holds one
        self.seed({"999.server": {"script": "", "state": "R", "exit": None, "user": USER,
                                  "name": "sch_kernel", "vars": {}}})
        bin_ = self.tmp / "bin"
        bin_.mkdir()
        self.commands = {}
        for c in ("qsub", "qstat", "qdel"):
            w = bin_ / c
            fake = FIXTURES / "fake_pbs.py"
            w.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{fake}" {c} "$@"\n')
            w.chmod(0o755)
            self.commands[c] = str(w)
        self._env = {k: os.environ.get(k) for k in ("FAKE_PBS_STATE", "FAKE_PBS_MODE",
                                                    "FAKE_PBS_HANG_S", "FAKE_PBS_HISTORY")}
        os.environ["FAKE_PBS_STATE"] = str(self.state)
        os.environ["FAKE_PBS_HANG_S"] = "4"
        self.declare()

    def tearDown(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.tmp, ignore_errors=True)

    def seed(self, jobs):
        s = json.loads(self.state.read_text()) if self.state.exists() else \
            {"next": 1000, "jobs": {}, "calls": []}
        s["jobs"].update(jobs)
        self.state.write_text(json.dumps(s))

    def declare(self, **over):
        cfg = {"queue": "testq", "select": "1:ncpus=1:mem=1gb", "walltime": "00:10:00",
               "commands": dict(self.commands), "poll_s": 0.01, "stop_grace_s": 0.2,
               "queue_full_first_wait_s": 0.01, "seal_visibility_s": 0.2,
               "qsub_timeout_s": 1.0, "qstat_outage_polls": 3}
        cfg.update(over)
        decl = yamlish.load(self.stack / "stack.yml")
        decl["executor"] = "pbs"
        decl["pbs"] = {k: v for k, v in cfg.items() if v is not None}
        yamlish.dump(decl, self.stack / "stack.yml")

    def scheduler(self):
        return json.loads(self.state.read_text())

    def method_qsubs(self):
        return [c for c in self.scheduler()["calls"] if c[0] == "qsub"
                and c[-1].endswith(os.path.join("filter_threshold", "pbs", "job.pbs"))]

    def method_jobs(self):
        return {j: v for j, v in self.scheduler()["jobs"].items() if v.get("name") == NAME}

    def mount(self):
        return cli("--json", "mount", "--stack", str(self.stack), "filter_threshold",
                   "--param", "min=5")

    def facts(self):
        return json.loads((self.stack / "plugins" / "filter_threshold" / "facts.json").read_text())

    def test_a_qsub_that_queued_the_job_and_then_hung_is_adopted_not_doubled(self):
        os.environ["FAKE_PBS_MODE"] = "hang:queued:1"
        rc, r, _err = self.mount()
        self.assertEqual((rc, r.get("status")), (0, "mounted"), r)
        self.assertEqual(len(self.method_qsubs()), 1, "the job was submitted twice")
        self.assertEqual(list(self.method_jobs()), ["1000.server"])
        facts = self.facts()
        self.assertEqual((facts["job"], facts["exit"]), ("1000.server", 0))
        self.assertEqual(facts["reconciled"]["found"], "1000.server")
        self.assertIn("SCH_SUBMISSION=", (self.stack / "plugins" / "filter_threshold" / "pbs" /
                                          "job.pbs").read_text())

    def test_a_qsub_that_hung_having_queued_nothing_is_submitted_once_more(self):
        os.environ["FAKE_PBS_MODE"] = "hang:lost:1"
        rc, r, _err = self.mount()
        self.assertEqual((rc, r.get("status")), (0, "mounted"), r)
        self.assertEqual(len(self.method_qsubs()), 2)
        self.assertEqual(len(self.method_jobs()), 1)
        self.assertNotIn("reconciled", self.facts())

    def test_a_job_that_ran_and_ended_where_the_server_keeps_no_history_is_found_by_its_seal(self):
        """A server with job history disabled lists only jobs that have not ended. A qsub that
        timed out after its job had already run and ended read as absent twice, and the job was
        submitted again: the plugin ran twice into one run directory. The job's own seal in the
        run names it, so it is adopted and nothing is submitted again. The qsub timeout here is
        long enough for the job to end before it expires, and shorter than the hang after it."""
        os.environ.update(FAKE_PBS_MODE="hang:ran:1", FAKE_PBS_HISTORY="0", FAKE_PBS_HANG_S="8")
        self.declare(qsub_timeout_s=5.0)
        rc, r, _err = self.mount()
        self.assertEqual((rc, r.get("status")), (0, "mounted"), r)
        self.assertEqual(len(self.method_qsubs()), 1, "the job was submitted twice")
        self.assertEqual(list(self.method_jobs()), ["1000.server"])
        facts = self.facts()
        self.assertEqual((facts["job"], facts["exit"]), ("1000.server", 0))
        self.assertEqual(facts["reconciled"]["found"], "1000.server")
        self.assertIn("seal", facts["reconciled"]["said"])

    def test_a_job_that_sealed_is_adopted_while_qstat_cannot_say(self):
        """The seal is the job's own word that it ran (harness W010b D1), so a qsub that timed
        out after its job ended needs no scheduler to be reconciled: one qsub, the job adopted,
        and its exit read from the seal."""
        os.environ.update(FAKE_PBS_MODE="hang:ran:1", FAKE_PBS_HANG_S="8")
        down = self.tmp / "bin" / "qstat_down"
        down.write_text("#!/bin/sh\necho 'qstat: cannot connect to server' >&2\nexit 1\n")
        down.chmod(0o755)
        self.declare(commands={**self.commands, "qstat": str(down)}, qsub_timeout_s=5.0)
        rc, r, _err = self.mount()
        self.assertEqual((rc, r.get("status")), (0, "mounted"), r)
        self.assertEqual(len(self.method_qsubs()), 1, "submitted again while the job had sealed")
        self.assertEqual(self.facts()["reconciled"]["found"], "1000.server")

    def test_an_earlier_job_of_the_same_name_is_never_taken_for_this_one(self):
        self.seed({"900.server": {"script": "", "state": "F", "exit": 0, "user": USER,
                                  "name": NAME, "vars": {"SCH_SUBMISSION": "0123456789ab"}}})
        os.environ["FAKE_PBS_MODE"] = "hang:lost:1"
        rc, r, _err = self.mount()
        self.assertEqual((rc, r.get("status")), (0, "mounted"), r)
        self.assertNotEqual(self.facts()["job"], "900.server")
        self.assertEqual(len(self.method_qsubs()), 2)

    def test_when_the_scheduler_cannot_say_nothing_is_submitted_again_and_e5_says_so(self):
        os.environ["FAKE_PBS_MODE"] = "hang:queued:1"
        down = self.tmp / "bin" / "qstat_down"
        down.write_text("#!/bin/sh\necho 'qstat: cannot connect to server' >&2\nexit 1\n")
        down.chmod(0o755)
        self.declare(commands={**self.commands, "qstat": str(down)})
        rc, r, err = self.mount()
        self.assertEqual(r.get("status"), "refused", r)
        reason = r.get("reason") or ""
        self.assertIn("cannot say", reason)
        self.assertIn(NAME, reason)
        self.assertIn("SCH_SUBMISSION=", reason)
        self.assertEqual(len(self.method_qsubs()), 1, "submitted again while nobody could say")
        self.assertEqual(rc, 3, err)                   # its disposer still cannot say: E5
        self.assertIn("E5", err)

    def test_a_job_the_scheduler_held_for_good_is_not_waited_for(self):
        """autodev BLK-009 (2026-11-10): after four failed attempts to run it, PBS Pro held
        W013's job (`job_state = H`, `comment = job held, too many failed attempts to run`), and
        a held job stays held until a person releases or deletes it. `wait` returns at once with
        the hold in its facts and the exit unknown - a death to the kernel - and the disposer
        qdels it, confirmed."""
        from sch.services.executor import make_executor
        os.environ["FAKE_PBS_MODE"] = "hold"
        cfg = yamlish.load(self.stack / "stack.yml")["pbs"]
        ex = make_executor("pbs", config=cfg)
        run = self.tmp / "held"
        run.mkdir()
        h = ex.launch([sys.executable, "-c", "pass"], run, run / "stderr.log")
        s = self.scheduler()
        s["jobs"][h.job].update(state="H", comment="Not Running: job held, too many failed "
                                                   "attempts to run")
        self.state.write_text(json.dumps(s))
        facts = h.wait()
        self.assertIn("too many failed attempts", facts.get("held") or "", facts)
        self.assertEqual((facts["stopped"], facts["exit"]), (False, None))
        self.assertLess(facts["seconds"], 5.0)
        q = ex.quiesce()
        self.assertEqual((q["requested"], q["stopped"]), (True, True), q)
        self.assertEqual(self.scheduler()["jobs"][h.job]["state"], "F")

    def test_a_qsub_that_answers_is_one_qsub_and_no_question(self):
        os.environ["FAKE_PBS_MODE"] = "run"
        rc, r, _err = self.mount()
        self.assertEqual((rc, r.get("status")), (0, "mounted"), r)
        self.assertEqual(len(self.method_qsubs()), 1)
        self.assertFalse([c for c in self.scheduler()["calls"] if c[0] == "qstat" and "-u" in c])
        self.assertNotIn("reconciled", self.facts())


if __name__ == "__main__":
    unittest.main()
