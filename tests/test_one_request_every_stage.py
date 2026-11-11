"""One request, every stage: the stage driver (harness W041, ROUTE R03, GAP-001's driver part).

Until this wave each stage of a cohort went through the harness by its own hand-written job. A
request now names the libraries, the design, what the dataset is, what happened upstream, and each
stage's tool flags; `sch run --request` runs the four stages as four stacks, each reading what the
stage before it handed on from that stage's own record, and seals the run. What must hold, each
asserted against the world (the tools' argv, the files, the records), never the driver's account:
  - a request that cannot be run is refused before any tool starts: no assay, a third spelling of
    one, `organism` beside `species`, CellBender upstream of single cells, a user's decision set
    as a plain parameter;
  - the plan names every stage and every decision a tool declares as the user's, and runs nothing;
  - the run stops before a stage whose decision is unanswered, by name, and resumes from the answer,
    recorded with who gave it; a sealed stage is never run again; a failed one says where and how;
  - the chained run equals the same four stages mounted by hand in the same order: the driver adds
    nothing and hides nothing. Shape b's role names reach the tools; where the tools' own
    conventions do not carry them (scQC writes `sample`), the failure is the tool's, and identical.
The tools are the suite's stand-ins (`fixtures/fake_*`), which honour each tool's flags and status
contract and compute nothing.
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

from helpers import FIXTURES, HAVE_H5PY, write_part
from sch import yamlish
from sch.cli import main
from sch.kernel import Stack

LOGS = ("FAKE_SCQC_LOG", "FAKE_SCANNO_LOG", "FAKE_SCINTEGRATE_LOG", "FAKE_SCPROFILE_LOG")
MODES = ("FAKE_SCQC_MODE", "FAKE_SCANNO_MODE", "FAKE_SCINTEGRATE_MODE", "FAKE_SCPROFILE_MODE")
ROLES = {"a": {"sample": "sample", "condition": "condition"},
         "b": {"sample": "library_id", "condition": "arm"}}
ANSWERS = ["--answer", "qc.mode=apply", "--answer", "qc.decisions=null"]
CONTROL = "prof.control=[\"{c}=control\"]"


def cli(*argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(list(argv))
    return rc, buf.getvalue()


def cohort(dest: Path, shape: str, libraries: int = 4, droplets: int = 40) -> dict:
    """A cohort as a samplesheet of libraries (scQC's: `sample`, `assay`, `ambient_h5`) whose scope
    and design columns carry the shape's role names. Read-only, as delivered."""
    r = ROLES[shape]
    dest.mkdir(parents=True)
    head = ["sample"] + ([r["sample"]] if r["sample"] != "sample" else []) + ["assay", "ambient_h5", r["condition"]]
    rows = ["\t".join(head)]
    for i in range(libraries):
        lib = f"L{i + 1}"
        part = write_part(dest / "libs" / f"{lib}.h5ad", [f"BC{j:05d}-1" for j in range(droplets)])
        arm = "control" if i % 2 == 0 else "treated"
        rows.append("\t".join([lib] + ([lib] if r["sample"] != "sample" else []) + ["snrna", str(part), arm]))
    (dest / "samplesheet.tsv").write_text("\n".join(rows) + "\n")
    (dest / "design.csv").write_text(f"{r['sample']},{r['condition']}\n" + "".join(
        f"L{i + 1},{'control' if i % 2 == 0 else 'treated'}\n" for i in range(libraries)))
    (dest / "registry.tsv").write_text("species\tbuild\tpath\nspecies_x\tref_1\treferences/species_x/ref_1\n")
    for f in [dest / "samplesheet.tsv", dest / "design.csv"] + sorted((dest / "libs").glob("*.h5ad")):
        f.chmod(0o444)
    return {"dir": dest, "roles": r, "design": dest / "design.csv"}


def stages(c: dict, lib: bool = True) -> list:
    """Each stage's tool flags, verbatim, by the tool's own names. `lib`: the library column written
    into each tool's own flag by hand, as the driver writes keys.sample there (W042); without it,
    the request leaves them to the driver."""
    out = [
        {"plugin": "qc@scqc", "params": {"scqc": str(FIXTURES / "fake_scqc.py"),
                                         "registry": str(c["dir"] / "registry.tsv"), "executor": "local",
                                         "allow_local": True, "dbr": 0.06, "seed": 0}},
        {"plugin": "anno@scanno", "params": {
            "scanno": str(FIXTURES / "fake_scanno.py"), "cluster": {"resolutions": "0.5,1.0", "seed": 0},
            "annotate": {"cluster_key": ["leiden_0p5", "leiden_1p0"], "tree": "/refs/tree.json",
                         "species": "species_x", "tissue": "tissue_x"},
            "embed": {"label_obs": ["scanno_cell_type=cell_type"], "seed": 0,
                      "sample_key": c["roles"]["sample"]}}},
        {"plugin": "int@scintegrate", "params": {
            "scintegrate": str(FIXTURES / "fake_scintegrate"),
            "integrate": {"batch_key": "sample", "label_key": "cell_type", "design": str(c["design"]),
                          "design_sample_col": c["roles"]["sample"], "methods": "none,harmony",
                          "seed": 0, "n_cores": 1}}},
        {"plugin": "prof@scprofile", "params": {
            "scprofile": str(FIXTURES / "fake_scprofile"),
            "run": {"kernel": "de,abundance", "label_key": "cell_type", "sample_key": c["roles"]["sample"],
                    "batch_key": "sample", "embedding": "X_harmony", "no_cache": True,
                    "prefix": "/declared/prefix", "timeout": 600}}},
    ]
    if not lib:
        del out[1]["params"]["embed"]["sample_key"]
        del out[2]["params"]["integrate"]["design_sample_col"]
        del out[3]["params"]["run"]["sample_key"]
    return out


def request(c: dict, name="request.yml", **over) -> Path:
    r = c["roles"]
    doc = {"request": 1, "observations": "samplesheet.tsv", "parts": "ambient_h5",
           "keys": {"sample": r["sample"], "condition": r["condition"]}, "design": "design.csv",
           "context": {"assay": "snrna", "species": "species_x", "tissue": "tissue_x"},
           "upstream": {"alignment": {"tool": "aligner_x", "version": "1"},
                        "ambient": {"tool": "remover_x", "ran": True}},
           "stages": stages(c)}
    for k, v in over.items():
        if v is None:
            doc.pop(k, None)
        else:
            doc[k] = v
    p = c["dir"] / name
    yamlish.dump(doc, p)
    return p


@unittest.skipUnless(HAVE_H5PY, "h5py is not available in this interpreter")
class _Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sch-drive-"))
        self._env = {k: os.environ.get(k) for k in LOGS + MODES}
        for k in MODES:
            os.environ.pop(k, None)
        for k in LOGS:
            os.environ[k] = str(self.tmp / f"{k.lower()}.jsonl")

    def tearDown(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        for p in self.tmp.rglob("*"):
            try:
                p.chmod(0o755 if p.is_dir() else 0o644)
            except OSError:
                pass
        shutil.rmtree(self.tmp, ignore_errors=True)

    def calls(self) -> list:
        out = []
        for k in LOGS:
            f = Path(os.environ[k])
            if f.exists():
                out += [(k, json.loads(x)["argv"]) for x in f.read_text().splitlines()]
        return out

    def drive(self, req, out, *extra):
        rc, text = cli("--json", "run", "--request", str(req), "--out", str(out), *extra)
        return rc, json.loads(text)


class TheRequestIsRefusedBeforeAnyTool(_Base):
    def test_a_request_that_cannot_run_is_refused_by_name_and_no_tool_starts(self):
        c = cohort(self.tmp / "c", "a")
        bad_stages = stages(c)
        bad_stages[3]["params"]["run"]["control"] = ["condition=control"]
        no_embed = stages(c)
        del no_embed[1]["params"]["embed"]
        cases = [({"context": {"species": "species_x"}}, "declares no assay"),
                 ({"context": {"assay": "sn", "species": "species_x"}}, "scrna, snrna"),
                 ({"context": {"assay": "nucleus", "species": "species_x"}}, "scrna, snrna"),
                 ({"context": {"assay": "snrna", "organism": "x"}}, "declared once as `species`"),
                 ({"context": {"assay": "scrna"}, "upstream": {"alignment": {"tool": "aligner_x"},
                                                               "ambient": {"tool": "CellBender"}}}, "rule 2"),
                 ({"upstream": {"alignment": {"tool": "aligner_x"}}}, "declares no ambient"),
                 ({"stages": bad_stages}, "prof.control"),
                 ({"stages": stages(c)[2:]}, "the first stage must read libraries"),
                 ({"stages": no_embed}, "hands on joint when its params declare 'embed'"),
                 ({"samplesheet": "x"}, "not a request field")]
        for i, (over, said) in enumerate(cases):
            with self.subTest(said=said):
                req = request(c, name=f"r{i}.yml", **over)
                out = self.tmp / f"run{i}"
                rc, rec = self.drive(req, out)
                self.assertEqual((rc, rec["status"]), (2, "refused"), rec)
                self.assertIn(said, rec["reason"])
                rc, text = cli("plan", "--request", str(req))
                self.assertEqual(rc, 2, text)
                self.assertFalse(out.exists(), "a refused request writes nothing")
        self.assertEqual(self.calls(), [], "no tool started")

    def test_nuclei_after_cellbender_are_planned_and_the_upstream_is_said(self):
        c = cohort(self.tmp / "c", "a")
        req = request(c, upstream={"alignment": {"tool": "aligner_x"}, "ambient": {"tool": "CellBender"}})
        rc, text = cli("plan", "--request", str(req))
        self.assertEqual(rc, 0, text)
        self.assertIn("ambient: CellBender", text)


class ThePlan(_Base):
    def test_the_plan_names_every_stage_and_every_users_decision_and_runs_nothing(self):
        c = cohort(self.tmp / "c", "a")
        rc, text = cli("--json", "plan", "--request", str(request(c)))
        self.assertEqual(rc, 0, text)
        p = json.loads(text)
        self.assertEqual([s["stage"] for s in p["stages"]], ["01_qc", "02_anno", "03_int", "04_prof"])
        self.assertEqual([d["name"] for s in p["stages"] for d in s["decisions"]],
                         ["qc.mode", "qc.decisions", "prof.control"])
        self.assertEqual([(s["reads"], s["hands_on"]) for s in p["stages"]],
                         [("libraries", ["libraries", "joint"]), ("libraries", ["libraries", "joint"]),
                          ("joint", ["joint"]), ("joint", ["joint"])])
        rc, text = cli("plan", "--request", str(request(c)))
        self.assertIn("UNANSWERED", text)
        self.assertEqual(self.calls(), [])


class OneRequestEveryStage(_Base):
    def by_hand(self, c, root, control):
        """The same four stages, mounted by hand with the kernel's own verbs, in the same order."""
        root.mkdir()
        handed, reps = None, []
        for s, ans in zip(stages(c), [{"mode": "apply", "decisions": None}, {}, {}, {"run.control": control}]):
            short = s["plugin"].split("@")[0]
            sd = root / {"qc": "01_qc", "anno": "02_anno", "int": "03_int", "prof": "04_prof"}[short]
            params = json.loads(json.dumps(s["params"]))
            for k, v in ans.items():
                head, _, rest = k.partition(".")
                (params.setdefault(head, {}).__setitem__(rest, v) if rest else params.__setitem__(head, v))
            keys = [f"sample={c['roles']['sample']}", f"condition={c['roles']['condition']}"]
            if handed is None:
                obs, parts = c["dir"] / "samplesheet.tsv", "ambient_h5"
            else:
                sd.mkdir()
                obs, parts = sd / "observations.tsv", "h5ad"
                if short == "anno":
                    rows = [f"{c['roles']['sample']}\th5ad"] + [f"{k}\t{v}" for k, v in handed["libraries"].items()]
                else:
                    rows = ["part\th5ad", f"{Path(handed['joint']).name.split('.')[0]}\t{handed['joint']}"]
                    keys[0] = "sample=part"
                obs.write_text("\n".join(rows) + "\n")
                obs.chmod(0o444)
            argv = ["init", str(sd), "--profile", "single-cell/1.0", "--observations", str(obs), "--parts", parts,
                    "--design", str(c["design"]), "--context", "assay=snrna", "--context", "species=species_x",
                    "--context", "tissue=tissue_x"]
            for k in keys:
                argv += ["--key", k]
            rc, text = cli(*argv)
            self.assertEqual(rc, 0, text)
            margv = ["--json", "mount", "--stack", str(sd), s["plugin"]]
            for k, v in params.items():
                margv += ["--param", f"{k}={json.dumps(v)}"]
            rc, text = cli(*margv)
            if rc != 0:
                return reps, json.loads(text)
            out = sd / "plugins" / s["plugin"].replace("@", "_") / "out"
            got = json.loads((out / "out.json").read_text())["answer"]["hands_on"]
            handed = {"libraries": {k: str(out / v) for k, v in got["libraries"].items()},
                      "joint": str(out / got["joint"]) if got["joint"] else None}
            for p in out.rglob("*"):                 # a deliverable is read-only: the kernel's own rule
                if p.is_file():
                    p.chmod(0o444)
            reps.append(sd)
        return reps, None

    def layer(self, sd, plugin):
        st = Stack(sd)
        try:
            return {c.capability(): (Path(c.path).read_bytes() if c.path and Path(c.path).is_file() else None)
                    for c in st.dataset.contributions_of(plugin) if c.slot != "object"}
        finally:
            st.close()

    def check_equal_by_hand(self, c, out, upto):
        driver_calls = self.calls()
        for k in LOGS:
            Path(os.environ[k]).unlink(missing_ok=True)
        hand = (self.tmp / "hand").resolve()
        reps, died = self.by_hand(c, hand, [f"{c['roles']['condition']}=control"])
        hand_calls = self.calls()
        sub = lambda calls: [(k, [x.replace(str(hand), "<RUN>") for x in a]) for k, a in calls]  # noqa: E731
        self.assertEqual([(k, [x.replace(str(out.resolve()), "<RUN>") for x in a]) for k, a in driver_calls],
                         sub(hand_calls), "every tool call, flag for flag, once the run directory is named")
        for sd in reps[:upto]:
            plugin = {"01_qc": "qc@scqc", "02_anno": "anno@scanno", "03_int": "int@scintegrate",
                      "04_prof": "prof@scprofile"}[sd.name]
            with self.subTest(stage=sd.name):
                self.assertEqual(self.layer(out / sd.name, plugin), self.layer(sd, plugin))
                self.assertTrue(self.layer(sd, plugin) or plugin == "prof@scprofile")
        return reps, died

    def test_shape_a_stops_at_each_users_decision_resumes_seals_and_equals_the_stages_by_hand(self):
        c = cohort(self.tmp / "c", "a")
        req, out = request(c), self.tmp / "run"
        rc, rec = self.drive(req, out)
        self.assertEqual((rc, rec["status"], rec["stage"]), (3, "waiting", "01_qc"))
        self.assertEqual([d["name"] for d in rec["waiting_for"]], ["qc.mode", "qc.decisions"])
        self.assertEqual(self.calls(), [], "stopped before any tool")
        rc, rec = self.drive(req, out, *ANSWERS, "--by", "a tester")
        self.assertEqual((rc, rec["status"], rec["stage"]), (3, "waiting", "04_prof"), rec)
        self.assertEqual(rec["sealed"], ["01_qc", "02_anno", "03_int"])
        rc, rec = self.drive(req, out, "--answer", CONTROL.format(c="condition"), "--by", "a tester")
        self.assertEqual((rc, rec["status"]), (0, "sealed"), rec)
        self.assertEqual(rec["sealed"], ["01_qc", "02_anno", "03_int", "04_prof"])
        self.assertTrue((out / "SEALED.json").is_file())
        for s in rec["sealed"]:
            self.assertTrue((out / s / "report" / "report.json").is_file(), s)
            self.assertTrue((out / s / "SEALED.json").is_file(), s)
        # recorded where the stage's own record is, with who decided
        rc, text = cli("--json", "events", "--stack", str(out / "01_qc"), "--kind", "decision")
        ev = json.loads(text)
        self.assertEqual([(e["name"], e["value"], e["by"]) for e in ev],
                         [("qc.mode", "apply", "a tester"), ("qc.decisions", None, "a tester")])
        rc, text = cli("--json", "events", "--stack", str(out / "04_prof"), "--kind", "upstream")
        self.assertEqual(json.loads(text)[0]["ambient"], {"tool": "remover_x", "ran": True})
        # each stage read the stage before it from that stage's record, never a promoted path
        sheet = (out / "02_anno" / "observations.tsv").read_text()
        self.assertIn(str(out.resolve() / "01_qc" / "plugins" / "qc_scqc" / "out"), sheet)
        self.assertIn("cohort_per_sample/L1.filtered.h5ad", sheet)
        self.assertIn("02_anno/plugins/anno_scanno/out/scanno/joint/joint.h5ad",
                      (out / "03_int" / "observations.tsv").read_text())
        # the plan's words reached each tool in its own: snrna -> scProfile's `nucleus`
        prof = [a for k, a in self.calls() if k == "FAKE_SCPROFILE_LOG" and a[0] == "run"][0]
        self.assertEqual(prof[prof.index("--assay") + 1], "nucleus")
        self.assertNotIn("--organism", prof, "species_x has no word in scProfile: undeclared, and said")
        self.check_equal_by_hand(c, out, 4)

    def test_shape_b_carries_its_role_names_and_where_a_tool_does_not_the_failure_is_the_tools(self):
        c = cohort(self.tmp / "c", "b")
        req, out = request(c), self.tmp / "run"
        rc, rec = self.drive(req, out, *ANSWERS, "--answer", CONTROL.format(c="arm"), "--by", "a tester")
        sheet = (out / "02_anno" / "observations.tsv").read_text()
        self.assertTrue(sheet.startswith("library_id\th5ad\n"), sheet)
        # W042 (GAP-C92): the library column is one fact - scAnno's embed writes keys.sample into the
        # joint object, and scIntegrate and scProfile take it by that name - so shape b seals
        self.assertEqual((rc, rec["status"]), (0, "sealed"), rec)
        reps, died = self.check_equal_by_hand(c, out, 4)
        self.assertIsNone(died)


class AFailedStageSaysWhereAndResumes(_Base):
    def test_a_stage_that_dies_is_named_kept_and_resumed_without_running_a_sealed_stage_again(self):
        c = cohort(self.tmp / "c", "a")
        req, out = request(c), self.tmp / "run"
        os.environ["FAKE_SCINTEGRATE_MODE"] = "fail"
        rc, rec = self.drive(req, out, *ANSWERS, "--answer", CONTROL.format(c="condition"), "--by", "a tester")
        self.assertEqual((rc, rec["status"], rec["stage"]), (2, "failed", "03_int"), rec)
        self.assertEqual(rec["sealed"], ["01_qc", "02_anno"])
        self.assertEqual(rec["resume"], f"sch run --request {req.resolve()} --out {out.resolve()}")
        self.assertEqual(json.loads((out / "DRIVE.json").read_text())["stage"], "03_int")
        before = [k for k, _a in self.calls()]
        os.environ.pop("FAKE_SCINTEGRATE_MODE")
        rc, rec = self.drive(req, out)
        self.assertEqual((rc, rec["status"]), (0, "sealed"), rec)
        after = [k for k, _a in self.calls()][len(before):]
        self.assertNotIn("FAKE_SCQC_LOG", after, "a sealed stage is never run again")
        self.assertNotIn("FAKE_SCANNO_LOG", after)
        self.assertTrue((out / "03_int.failed-1").is_dir(), "the failed attempt stays as its record")

    def test_a_recorded_decision_is_not_rewritten_and_another_request_is_another_run(self):
        c = cohort(self.tmp / "c", "a")
        req, out = request(c), self.tmp / "run"
        rc, rec = self.drive(req, out, "--answer", "qc.mode=evidence", "--by", "a tester")
        self.assertEqual(rc, 3)
        rc, rec = self.drive(req, out, "--answer", "qc.mode=apply", "--by", "someone else")
        self.assertEqual((rc, rec["status"]), (2, "refused"))
        self.assertIn("not rewritten", rec["reason"])
        rc, rec = self.drive(req, out, "--answer", "qc.nothing=1", "--by", "a tester")
        self.assertIn("no stage declares", rec["reason"])
        rc, rec = self.drive(request(c, name="other.yml", context={"assay": "snrna", "species": "s2"}), out)
        self.assertIn("another request", rec["reason"])



ANSWERED = ANSWERS + ["--answer", CONTROL.format(c="{c}"), "--by", "a tester"]


def answered(c):
    return [a.replace("{c}", c["roles"]["condition"]) for a in ANSWERED]


class OneLibraryColumn(_Base):
    """W042, GAP-C92: the request's keys.sample is written into every tool that takes the library."""

    def test_the_driver_writes_keys_sample_into_every_stage_and_shape_b_seals(self):
        c = cohort(self.tmp / "c", "b")
        req, out = request(c, stages=stages(c, lib=False)), self.tmp / "run"
        rc, rec = self.drive(req, out, *answered(c))
        self.assertEqual((rc, rec["status"]), (0, "sealed"), rec)
        calls = self.calls()
        embed = [a for k, a in calls if k == "FAKE_SCANNO_LOG" and a[0] == "embed"][0]
        self.assertEqual(embed[embed.index("--sample-key") + 1], "library_id")
        prof = [a for k, a in calls if k == "FAKE_SCPROFILE_LOG" and a[0] == "run"][0]
        self.assertEqual(prof[prof.index("--sample-key") + 1], "library_id")
        integ = [a for k, a in calls if k == "FAKE_SCINTEGRATE_LOG" and "library_id" in a]
        self.assertEqual(len(integ), 1, [a for k, a in calls if k == "FAKE_SCINTEGRATE_LOG"])
        rc, text = cli("plan", "--request", str(req))
        self.assertIn("the library column: keys.sample=library_id -> run.sample_key", text)

    def test_a_stage_that_names_another_library_column_is_refused_before_any_tool(self):
        c = cohort(self.tmp / "c", "b")
        st = stages(c, lib=False)
        st[3]["params"]["run"]["sample_key"] = "sample"           # scQC's word, not the cohort's
        rc, rec = self.drive(request(c, stages=st), self.tmp / "run", *answered(c))
        self.assertEqual((rc, rec["status"]), (2, "refused"), rec)
        self.assertIn("keys.sample = 'library_id'", rec["reason"])
        self.assertEqual(self.calls(), [], "no tool started")


class TheClusterPath(_Base):
    """W042, ROUTE R03 run 2: every stage a job on the scheduler (the stand-in), sized by the request,
    queued by the site file; and the job that runs a request, generated."""
    QUEUES = [{"queue": "q_small", "walltime": "01:00:00", "ncpus": 2, "mem": "4gb"},
              {"queue": "q_big", "walltime": "48:00:00", "ncpus": 24, "mem": "90gb"}]
    USED = {"walltime": "00:00:07", "mem": "4096kb", "ncpus": "1"}

    def setUp(self):
        super().setUp()
        self._pbs_env = {k: os.environ.get(k) for k in ("FAKE_PBS_STATE", "FAKE_PBS_USED", "SCH_SITE")}
        bin_ = self.tmp / "bin"
        bin_.mkdir()
        commands = {}
        for c in ("qsub", "qstat", "qdel"):
            w = bin_ / c
            w.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{FIXTURES / "fake_pbs.py"}" {c} "$@"\n')
            w.chmod(0o755)
            commands[c] = str(w)
        self.site = self.tmp / "site"
        self.site.mkdir()
        yamlish.dump({"executor": "pbs", "pbs": {
            "queue": "q_small", "queues": self.QUEUES, "select": "1:ncpus=1:mem=1gb", "walltime": "00:10:00",
            "commands": commands, "poll_s": 0.01, "stop_grace_s": 0.2, "seal_visibility_s": 0.2}},
            self.site / "stack.yml")
        os.environ["FAKE_PBS_STATE"] = str(self.tmp / "pbs_state.json")
        os.environ["FAKE_PBS_USED"] = json.dumps(self.USED)
        os.environ["SCH_SITE"] = str(self.site)

    def tearDown(self):
        for k, v in self._pbs_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        super().tearDown()

    SIZES = {"drive": {"ncpus": 1, "mem": "2gb", "walltime": "04:00:00"},
             "qc": {"ncpus": 4, "mem": "8gb", "walltime": "02:00:00"},
             "prof": {"ncpus": 2, "mem": "2gb", "walltime": "00:30:00"}}

    def test_every_stage_is_a_job_sized_by_the_request_queued_by_the_site_and_reports_its_cost(self):
        c = cohort(self.tmp / "c", "a")
        req, out = request(c, resources=self.SIZES), self.tmp / "run"
        rc, rec = self.drive(req, out, *answered(c))
        self.assertEqual((rc, rec["status"]), (0, "sealed"), rec)
        want = {"01_qc": ("q_big", "1:ncpus=4:mem=8gb", "02:00:00"),
                "02_anno": ("q_small", "1:ncpus=1:mem=1gb", "00:10:00"),
                "03_int": ("q_small", "1:ncpus=1:mem=1gb", "00:10:00"),
                "04_prof": ("q_small", "1:ncpus=2:mem=2gb", "00:30:00")}
        plugin = {"01_qc": "qc_scqc", "02_anno": "anno_scanno", "03_int": "int_scintegrate",
                  "04_prof": "prof_scprofile"}
        for sd, (queue, select, wall) in want.items():
            with self.subTest(stage=sd):
                script = (out / sd / "plugins" / plugin[sd] / "pbs" / "job.pbs").read_text()
                self.assertIn(f"#PBS -q {queue}\n", script)
                self.assertIn(f"#PBS -l select={select}\n", script)
                self.assertIn(f"#PBS -l walltime={wall}\n", script)
                cost = json.loads((out / sd / "report" / "report.json").read_text())["cost"]
                self.assertEqual(cost["measured_by"], ["scheduler"])
                self.assertEqual(cost["peak_mem_kb"]["value"], 4096)
                self.assertEqual(cost["wall_s"]["value"], 7 * len(cost["runs"]))
                self.assertGreater(cost["cells"]["value"], 0)
        rc, text = cli("plan", "--request", str(req))
        self.assertIn("size: mem=8gb, ncpus=4, walltime=02:00:00", text)

    def test_a_queue_in_the_request_or_a_size_no_queue_holds_is_refused(self):
        c = cohort(self.tmp / "c", "a")
        rc, rec = self.drive(request(c, name="q.yml", resources={"qc": {"queue": "q_big"}}), self.tmp / "r1")
        self.assertEqual((rc, rec["status"]), (2, "refused"), rec)
        self.assertIn("a queue is the site's", rec["reason"])
        big = {"qc": {"ncpus": 64, "mem": "500gb", "walltime": "100:00:00"}}
        rc, rec = self.drive(request(c, name="big.yml", resources=big), self.tmp / "r2", *answered(c))
        self.assertEqual((rc, rec["status"], rec["stage"]), (2, "failed", "01_qc"), rec)
        self.assertIn("no declared queue holds", rec["reason"])
        self.assertEqual(self.calls(), [], "no tool started")

    def job(self, c, req, check_ok=True):
        """The job generated for `req`, in a stage's jobs/ directory, with its site's job.yml."""
        import subprocess
        harness = self.tmp / "harness"
        if not harness.exists():
            harness.mkdir()
            (harness / "sch").symlink_to(Path(__file__).resolve().parent.parent / "sch")
            head = subprocess.run(["git", "-C", str(Path(__file__).resolve().parent.parent), "rev-parse",
                                   "HEAD"], capture_output=True, text=True).stdout.strip()
            (harness / "HEAD.txt").write_text(head + "\n")
        # this interpreter may keep its packages in the user's site, which a job hides by default
        yamlish.dump({"harness": str(harness), "python": sys.executable, "runs": "../../runs/sch",
                      "setup": ["unset PYTHONNOUSERSITE"]}, self.site / "job.yml")
        jobs = c["dir"] / "00_driver" / "jobs"
        pred, chk = c["dir"] / "00_driver" / "PREDICTION.txt", c["dir"] / "00_driver" / "checks.sh"
        jobs.mkdir(parents=True, exist_ok=True)
        pred.write_text("(1) the chained run seals, four stages from one request.\n")
        want = 4 if check_ok else 5              # a check that cannot hold, to see the GATE miss
        chk.write_text("#!/bin/bash\nn=$(ls \"$1\"/0*/report/report.json | wc -l | tr -d ' ')\n"
                       f"if [ \"$n\" -eq {want} ]; then echo \"VERDICT (four reports): AS PREDICTED - $n\"\n"
                       "else echo \"VERDICT (four reports): MISSED - $n\"; fi\n")
        f = jobs / ("drive.pbs" if check_ok else "drive_missed.pbs")
        rc, text = cli("--json", "run", "--request", str(req), "--job", str(f), "--predict", str(pred),
                       "--check", str(chk), "--purpose", "w042", *answered(c))
        self.assertEqual(rc, 0, text)
        return f, json.loads(text)

    def run_job(self, f, name):
        import subprocess
        rundir = self.tmp / name
        (rundir / "logs").mkdir(parents=True)
        p = subprocess.run(["bash", str(f)], cwd=str(self.tmp), capture_output=True, text=True,
                           env=dict(os.environ, RUNDIR=str(rundir), PBS_O_WORKDIR=str(f.parent),
                                    HARNESSHEAD="test"))
        return p, rundir

    def test_the_job_is_generated_from_the_request_and_its_body_runs_it_to_the_gate(self):
        import subprocess
        c = cohort(self.tmp / "c", "a")
        req = request(c, resources=self.SIZES)
        f, rec = self.job(c, req)
        text = f.read_text()
        self.assertEqual(subprocess.run(["bash", "-n", str(f)]).returncode, 0)
        rc, jc = cli("dev", "jobcheck", str(f))
        self.assertEqual(rc, 0, jc)
        self.assertIn("#PBS -q q_big\n", text, "the driver's 4 h is over q_small's 1 h")
        self.assertIn("#PBS -l select=1:ncpus=1:mem=2gb\n", text)
        head = text.split("# SUBMIT-BEGIN")[0]
        self.assertIn("(1) the chained run seals", head, "the prediction is in the header, before the run")
        recipe = text.split("# SUBMIT-BEGIN\n")[1].split("# SUBMIT-END")[0]
        self.assertTrue(all(ln.startswith("#   ") for ln in recipe.splitlines()), recipe)
        self.assertIn("qsub -o \"$RUNDIR/logs/\"", recipe)
        self.assertIn('mkdir "$RUNDIR" "$RUNDIR/logs"', recipe)
        self.assertNotIn(str(self.tmp), text.split("# SUBMIT-END")[1].replace(str(self.site), "")
                         .replace(sys.executable, "").replace(str(self.tmp / "harness"), ""),
                         "the body names the cohort's files relative to the job, nowhere else")
        p, rundir = self.run_job(f, "rundir")
        self.assertEqual(p.returncode, 0, p.stdout[-3000:] + p.stderr[-2000:])
        self.assertEqual(p.stdout.strip().splitlines()[-1], "GATE: AS PREDICTED")
        seal = (rundir / "SEALED.txt").read_text()
        self.assertIn("VERDICT (drive): SEALED - 4 stages from one request", seal)
        self.assertIn("VERDICT (four reports): AS PREDICTED - 4", seal)
        for sd in ("01_qc", "02_anno", "03_int", "04_prof"):
            cost = json.loads((rundir / sd / "report" / "report.json").read_text())["cost"]
            self.assertEqual(cost["measured_by"], ["scheduler"], sd)
        # a job is generated where it is authored: a samplesheet only the cluster has is named, not
        # opened there, and `sch plan` (which runs where the files are) still refuses it
        absent = request(c, name="absent.yml", observations="only_on_the_cluster.tsv")
        rc, text = cli("--json", "run", "--request", str(absent), "--job", str(f.parent / "absent.pbs"))
        self.assertEqual(rc, 0, text)
        self.assertEqual(cli("plan", "--request", str(absent))[0], 2)
        f2, _ = self.job(c, req, check_ok=False)
        p, rundir = self.run_job(f2, "rundir2")
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(p.stdout.strip().splitlines()[-1], "GATE: MISSED (1)")
        self.assertTrue((rundir / "FAILED.txt").is_file())

if __name__ == "__main__":
    unittest.main()
