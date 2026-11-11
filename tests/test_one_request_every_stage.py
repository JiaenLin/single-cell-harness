"""One request, every stage: the stage driver (harness W041, ROUTE R03, GAP-001's driver part).

Until this wave each stage of a cohort went through the harness by its own hand-written job. A
request now names the libraries, the design, what the dataset is, what happened upstream, and each
stage's tool flags; `sch run --request` runs the four stages as four stacks, each reading what the
stage before it handed on from that stage's own record, and seals the run. What must hold, each
asserted against the world (the tools' argv, the files, the records), never the driver's account:
  - a request that cannot be run is refused before any tool starts: no assay, a third spelling of
    one, `organism` beside `species`, a remover the profile does not list upstream of single cells
    (one it asks about stops the run at the user's decision, W042 fix 2), a user's decision set as
    a plain parameter;
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


def cohort(dest: Path, shape: str, libraries: int = 4, droplets: int = 40, assay: str = "snrna",
           extra=None) -> dict:
    """A cohort as a samplesheet of libraries (scQC's: `sample`, `assay`, `ambient_h5`) whose scope
    and design columns carry the shape's role names. Read-only, as delivered. `extra`: more of scQC's
    columns, {column: value or a function of the library}."""
    r = ROLES[shape]
    extra = dict(extra or {})
    dest.mkdir(parents=True)
    head = ["sample"] + ([r["sample"]] if r["sample"] != "sample" else []) + ["assay", "ambient_h5", r["condition"]] \
        + list(extra)
    rows = ["\t".join(head)]
    for i in range(libraries):
        lib = f"L{i + 1}"
        part = write_part(dest / "libs" / f"{lib}.h5ad", [f"BC{j:05d}-1" for j in range(droplets)])
        arm = "control" if i % 2 == 0 else "treated"
        rows.append("\t".join([lib] + ([lib] if r["sample"] != "sample" else []) + [assay, str(part), arm]
                               + [str(v(lib) if callable(v) else v) for v in extra.values()]))
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
           "upstream": {"alignment": {"tool": "cellranger", "version": "7.1.0"},
                        "ambient": {"tool": "cellbender", "version": "0.3.0"}},
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
                 ({"context": {"assay": "scrna"}, "upstream": {"alignment": {"tool": "cellranger"},
                                                               "ambient": {"tool": "remover_x"}}}, "rule 2"),
                 ({"upstream": {"alignment": {"tool": "cellranger"}}}, "declares no ambient"),
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
        req = request(c, upstream={"alignment": {"tool": "cellranger"}, "ambient": {"tool": "CellBender"}})
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
                         ["qc.mode", "qc.decisions", "anno.no_exclude", "anno.background_from_clusters",
                          "anno.gap_min", "anno.tissue_fallback", "anno.marker_species", "int.drop_labels",
                          "prof.control", "prof.allow", "prof.force", "prof.no_validate"])
        self.assertEqual([d["name"] for s in p["stages"] for d in s["decisions"] if d["unanswered"] == "stop"],
                         ["qc.mode", "qc.decisions", "prof.control"], "an escape does not stop the run (W042 fix 1)")
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
        self.assertEqual(json.loads(text)[0]["ambient"], {"tool": "cellbender", "version": "0.3.0"})
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
        # W042 fix 1 (E): scIntegrate keeps its batch, label and colour columns and the design's
        # factors, never the design's key (scintegrate/cli.py:489-503), so with the batch key `sample`
        # the cohort's `library_id` does not reach stage 4, and scProfile refuses the --sample-key
        # its object lacks - through the driver and by hand alike: the tools' failure, quoted
        self.assertEqual((rc, rec["status"], rec["stage"]), (2, "failed", "04_prof"), rec)
        self.assertIn("--sample-key 'library_id' is not present", rec["reason"])
        reps, died = self.check_equal_by_hand(c, out, 3)
        self.assertEqual(died["status"], "refused", died)
        self.assertIn("--sample-key 'library_id' is not present", died["reason"])


    def test_a_request_without_the_library_flags_equals_the_stages_by_hand_with_them(self):
        # W042 fix 1 (observation 7): the driver writes keys.sample where each tool takes it, and
        # that run is the by-hand one with those flags, flag for flag
        c = cohort(self.tmp / "c", "a")
        req, out = request(c, stages=stages(c, lib=False)), self.tmp / "run"
        rc, rec = self.drive(req, out, *answered(c))
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
        rc, rec = self.drive(request(c, name="other.yml", upstream={"alignment": {"tool": "starsolo"},
                                                                    "ambient": {"tool": "cellbender"}}), out)
        self.assertIn("another request", rec["reason"])



ANSWERED = ANSWERS + ["--answer", CONTROL.format(c="{c}"), "--by", "a tester"]


def answered(c):
    return [a.replace("{c}", c["roles"]["condition"]) for a in ANSWERED]


class OneLibraryColumn(_Base):
    """W042, GAP-C92: the request's keys.sample is written into every tool that takes the library."""

    def test_the_driver_writes_keys_sample_into_every_stage_and_where_a_tool_drops_it_the_tool_says(self):
        # W042 fix 1 (E): the flags reach every tool; the column does not reach stage 4, because
        # scIntegrate keeps the design's factors and never its key (scintegrate/cli.py:489-503), and
        # the strict stand-in refuses as the real scProfile does
        c = cohort(self.tmp / "c", "b")
        req, out = request(c, stages=stages(c, lib=False)), self.tmp / "run"
        rc, rec = self.drive(req, out, *answered(c))
        self.assertEqual((rc, rec["status"], rec["stage"]), (2, "failed", "04_prof"), rec)
        self.assertIn("--sample-key 'library_id' is not present", rec["reason"])
        calls = self.calls()
        embed = [a for k, a in calls if k == "FAKE_SCANNO_LOG" and a[0] == "embed"][0]
        self.assertEqual(embed[embed.index("--sample-key") + 1], "library_id")
        prof = [a for k, a in calls if k == "FAKE_SCPROFILE_LOG" and a[0] == "run"][0]
        self.assertEqual(prof[prof.index("--sample-key") + 1], "library_id")
        integ = [a for k, a in calls if k == "FAKE_SCINTEGRATE_LOG" and a[0] == "integrate"][0]
        self.assertEqual(integ[integ.index("--design-sample-col") + 1], "library_id")
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
        # W042 fix 1 (observation 1): a size no queue holds is refused before stage 1, at any stage
        for who in ("qc", "prof"):
            big = {who: {"ncpus": 64, "mem": "500gb", "walltime": "100:00:00"}}
            rc, rec = self.drive(request(c, name=f"big_{who}.yml", resources=big), self.tmp / f"r_{who}",
                                 *answered(c))
            self.assertEqual((rc, rec["status"]), (2, "refused"), rec)
            self.assertIn(f"resources ({'01_qc' if who == 'qc' else '04_prof'})", rec["reason"])
            self.assertIn("no declared queue holds", rec["reason"])
            self.assertFalse((self.tmp / f"r_{who}").exists())
        self.assertEqual(self.calls(), [], "no tool started")

    def job(self, c, req, check_ok=True, name=None):
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
        f = jobs / (name or ("drive.pbs" if check_ok else "drive_missed.pbs"))
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

    # ---- W042 fix 1: C (the job pins what it was generated for) and F (a size keeps the site's words)
    def test_C_the_job_runs_only_the_request_and_check_it_was_generated_for(self):
        c = cohort(self.tmp / "c", "a")
        req = request(c, resources=self.SIZES)
        f, _rec = self.job(c, req)
        self.assertIn(f'check_pin request "$REQUEST" {sha(req)}', f.read_text())
        req.write_text(req.read_text() + "# edited after the job was generated\n")
        p, rundir = self.run_job(f, "edited")
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(p.stdout.strip().splitlines()[-1], "GATE: MISSED (1)")
        self.assertIn("VERDICT (pins): MISSED - the request", (rundir / "FAILED.txt").read_text())
        self.assertFalse((rundir / "01_qc").exists(), "nothing ran")
        f2, _rec = self.job(c, req, name="drive2.pbs")   # generated again, as another job
        chk = c["dir"] / "00_driver" / "checks.sh"
        chk.write_text(chk.read_text() + "echo 'VERDICT (added): AS PREDICTED'\n")
        p, rundir = self.run_job(f2, "edited_check")
        self.assertIn("VERDICT (pins): MISSED - the check", (rundir / "FAILED.txt").read_text())
        self.assertFalse((rundir / "01_qc").exists(), "nothing ran")

    def test_F_a_size_the_request_does_not_state_keeps_the_sites_value(self):
        c = cohort(self.tmp / "c", "a")
        req, out = request(c, resources={"qc": {"ncpus": 4}}), self.tmp / "run"
        rc, rec = self.drive(req, out, *answered(c))
        self.assertEqual((rc, rec["status"]), (0, "sealed"), rec)
        script = (out / "01_qc" / "plugins" / "qc_scqc" / "pbs" / "job.pbs").read_text()
        self.assertIn("#PBS -l select=1:ncpus=4:mem=1gb\n", script, "the site's 1gb, kept")
        self.assertIn("#PBS -q q_big\n", script, "4 cpus are over q_small's 2")


    # ---- W042 fix 2: C (the job pins B's whole set; never generated over) and F (every size word)
    def test_C2_the_job_pins_every_file_the_run_reads_and_is_never_generated_over(self):
        c = cohort(self.tmp / "c", "a")
        req = request(c, resources=self.SIZES)
        f, _rec = self.job(c, req)
        before = f.read_text()
        self.assertIn("files the run reads, pinned as generated", before)
        self.assertIn('--expect "$RUNDIR/PINS.json"', before)
        rc, text = cli("--json", "run", "--request", str(req), "--job", str(f), *answered(c))
        self.assertEqual(rc, 2, text)
        self.assertIn("a job is there already", json.loads(text)["reason"])
        self.assertEqual(f.read_text(), before, "the job and its prediction are untouched")
        d, was = c["design"], c["design"].read_text()
        d.chmod(0o644)
        d.write_text(was.replace("control", "@").replace("treated", "control").replace("@", "treated"))
        p, rundir = self.run_job(f, "swapped")
        self.assertEqual(p.stdout.strip().splitlines()[-1], "GATE: MISSED (1)", p.stdout[-1500:])
        self.assertIn("VERDICT (pins): MISSED", (rundir / "FAILED.txt").read_text())
        self.assertIn("differs: design", (rundir / "FAILED.txt").read_text())
        self.assertFalse((rundir / "01_qc").exists(), "nothing ran")
        d.write_text(was)
        p, rundir = self.run_job(f, "as_generated")
        self.assertEqual(p.stdout.strip().splitlines()[-1], "GATE: AS PREDICTED", p.stdout[-2500:] + p.stderr[-800:])
        absent = request(c, name="absent.yml", observations="only_on_the_cluster.tsv")
        rc, text = cli("--json", "run", "--request", str(absent), "--job", str(f.parent / "absent.pbs"))
        self.assertEqual(rc, 0, text)
        self.assertIn("#     on the cluster only: observations ", (f.parent / "absent.pbs").read_text())

    def test_F2_every_size_word_is_laid_over_the_sites_and_a_bad_size_is_refused_before_any_tool(self):
        c = cohort(self.tmp / "c", "a")
        req, out = request(c, resources={"qc": {"select": "1:ncpus=4"}}), self.tmp / "run"
        rc, rec = self.drive(req, out, *answered(c))
        self.assertEqual((rc, rec["status"]), (0, "sealed"), rec)
        script = (out / "01_qc" / "plugins" / "qc_scqc" / "pbs" / "job.pbs").read_text()
        self.assertIn("#PBS -l select=1:ncpus=4:mem=1gb\n", script, "a request's select keeps the site's 1gb")
        bad = [{"ncpus": 0}, {"ncpus": -2}, {"mem": 8}, {"mem": "0gb"}, {"walltime": 0}, {"walltime": "00:00:00"},
               {"select": "1:ncpus=4:mem=8"}]
        for i, size in enumerate(bad):
            for site in (True, False):
                with self.subTest(size=size, site=site):
                    if not site:
                        os.environ.pop("SCH_SITE")
                    n = len(self.calls())
                    rc, rec = self.drive(request(c, name=f"b{i}.yml", resources={"prof": size}),
                                         self.tmp / f"rb{i}{site}", *answered(c))
                    os.environ["SCH_SITE"] = str(self.site)
                    self.assertEqual((rc, rec["status"]), (2, "refused"), rec)
                    self.assertIn("resources.prof", rec["reason"])
                    self.assertEqual(len(self.calls()), n, "refused before any tool")

    def test_C3_a_samplesheet_only_on_the_cluster_is_checked_there_with_its_cells(self):
        c = cohort(self.tmp / "c", "a")
        there = c["dir"] / "only_on_the_cluster.tsv"
        f, _rec = self.job(c, request(c, name="absent.yml", observations=there.name, resources=self.SIZES))
        self.assertIn("#     on the cluster only: observations ", f.read_text())
        shutil.copy2(c["dir"] / "samplesheet.tsv", there)   # where the job runs, the sheet and its cells are
        p, rundir = self.run_job(f, "sheet_there")
        self.assertEqual(p.stdout.strip().splitlines()[-1], "GATE: AS PREDICTED", p.stdout[-2500:] + p.stderr[-800:])
        self.assertIn("only here: observations.", (rundir / "PINS.txt").read_text())

    def test_F3_a_size_word_is_the_schedulers_word_and_nothing_else(self):
        c = cohort(self.tmp / "c", "a")
        bad = [{"select": "1:ncpus=4:host=a\n#PBS -q other"}, {"select": "1:ncpus=4:mem=8gb #x"},
               {"select": "0:ncpus=4"}, {"select": "1:ncpus=4:place='excl'"}, {"select": "1:NCPUS=4"},
               {"walltime": "１:００:００"}]
        for i, size in enumerate(bad):
            with self.subTest(size=size):
                n = len(self.calls())
                rc, rec = self.drive(request(c, name=f"w{i}.yml", resources={"prof": size}), self.tmp / f"rw{i}",
                                     *answered(c))
                self.assertEqual((rc, rec["status"]), (2, "refused"), rec)
                self.assertIn("resources.prof", rec["reason"])
                self.assertEqual(len(self.calls()), n, "refused before any tool")


def sha(path) -> str:
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def scrna(**over):
    return {"assay": "scrna", "species": "species_x", "tissue": "tissue_x", **over}


class TheDriverHoldsItsRules(_Base):
    """W042 fix 1: the verifier's reasons A, B, D and its observations, each through `sch`."""

    def test_B_a_resume_on_a_changed_file_the_request_names_is_refused_by_name(self):
        c = cohort(self.tmp / "c", "a")
        req, out = request(c), self.tmp / "run"
        rc, rec = self.drive(req, out, *ANSWERS, "--by", "a tester")
        self.assertEqual((rc, rec["stage"]), (3, "04_prof"), rec)
        for s in ("01_qc", "02_anno", "03_int"):
            inputs = json.loads((out / s / "SEALED.json").read_text())["inputs"]
            self.assertEqual(inputs["design"], sha(c["design"]), s)
            self.assertEqual(inputs["observations.ambient_h5[L1]"], sha(c["dir"] / "libs" / "L1.h5ad"), s)
        design, was = c["design"], c["design"].read_text()
        design.chmod(0o644)                      # the arms swapped after stages 1 to 3 sealed
        design.write_text(was.replace("control", "@").replace("treated", "control").replace("@", "treated"))
        before = len(self.calls())
        rc, rec = self.drive(req, out, "--answer", CONTROL.format(c="condition"), "--by", "a tester")
        self.assertEqual((rc, rec["status"]), (2, "refused"), rec)
        self.assertIn(f"design {design.resolve()}", rec["reason"])
        self.assertIn("start a new --out", rec["reason"])
        self.assertEqual(len(self.calls()), before, "stage 4 did not run")
        self.assertFalse((out / "04_prof").exists())
        design.write_text(was)                   # restored as it was: the run goes on
        rc, rec = self.drive(req, out, "--answer", CONTROL.format(c="condition"), "--by", "a tester")
        self.assertEqual((rc, rec["status"]), (0, "sealed"), rec)

    def test_a_recorded_decision_is_not_changed_by_editing_decisions_json(self):
        c = cohort(self.tmp / "c", "a")
        req, out = request(c), self.tmp / "run"
        os.environ["FAKE_SCPROFILE_MODE"] = "fail"
        rc, rec = self.drive(req, out, *answered(c))
        self.assertEqual((rc, rec["stage"]), (2, "04_prof"), rec)
        os.environ.pop("FAKE_SCPROFILE_MODE")
        d = out / "decisions.json"
        doc = json.loads(d.read_text())
        doc["prof.control"]["value"] = ["condition=treated"]
        d.write_text(json.dumps(doc, indent=1) + "\n")
        rc, rec = self.drive(req, out)
        self.assertEqual((rc, rec["status"]), (2, "refused"), rec)
        self.assertIn("decisions.json was changed outside `sch run`", rec["reason"])

    def test_D_each_adapters_decisions_are_the_escapes_its_tool_declares(self):
        import subprocess
        plugins = Path(__file__).resolve().parent.parent / "plugins" / "single-cell"
        py = [sys.executable]
        tools = {"qc@scqc": (py + [str(FIXTURES / "fake_scqc.py"), "describe"], None),
                 "anno@scanno": (py + [str(FIXTURES / "fake_scanno.py"), "describe"], None),
                 "int@scintegrate": (py + ["-m", "scintegrate.cli", "describe"], FIXTURES / "fake_scintegrate")}
        for plugin, (argv, path) in tools.items():
            with self.subTest(plugin=plugin):
                env = dict(os.environ, **({"PYTHONPATH": str(path)} if path else {}))
                said = json.loads(subprocess.run(argv, capture_output=True, text=True, env=env).stdout)
                declared = {str(e.get("flag") or e.get("what")) for e in said.get("escapes") or []}
                m = yamlish.load(plugins / plugin / "plugin.yml")
                asked = {d["escape"] for d in m.get("decisions") or [] if d.get("escape")}
                not_asked = set(m.get("escapes_not_asked") or {})
                self.assertTrue(declared, "the stand-in carries its tool's escapes")
                self.assertEqual(declared, asked | not_asked, "an adapter's decisions are its tool's escapes")
                self.assertFalse(asked & not_asked)
        # scProfile has no `describe`: its manifest lists its escapes by hand, each a flag its parser declares
        m = yamlish.load(plugins / "prof@scprofile" / "plugin.yml")
        self.assertEqual([d.get("escape") for d in m["decisions"]], [None, "--allow", "--force", "--no-validate"])
        self.assertIn("LISTED BY HAND", (plugins / "prof@scprofile" / "plugin.yml").read_text())

    def test_D_an_escape_is_never_a_plain_param_answered_it_is_passed_and_recorded_with_who(self):
        c = cohort(self.tmp / "c", "a")
        for i, (k, cmd, flag, v) in enumerate([(1, "annotate", "no_exclude", True), (2, "integrate", "drop_labels", "x")]):
            st = stages(c)
            st[k]["params"][cmd][flag] = v
            rc, rec = self.drive(request(c, name=f"p{i}.yml", stages=st), self.tmp / f"rp{i}", *answered(c))
            self.assertEqual((rc, rec["status"]), (2, "refused"), rec)
            self.assertIn(f"--answer {st[k]['plugin'].split('@')[0]}.{flag}=VALUE --by WHO", rec["reason"])
        rc, text = cli("plan", "--request", str(request(c)))
        self.assertIn("the user's: anno.gap_min (annotate.gap_min, scAnno's escape --gap-min)", text)
        self.assertIn("not passed (scAnno's default) unless answered", text)
        self.assertIn("the user's: int.drop_labels (integrate.drop_labels, scIntegrate's escape", text)
        out = self.tmp / "run"
        rc, rec = self.drive(request(c), out, *answered(c), "--answer", "anno.gap_min=0.2")
        self.assertEqual((rc, rec["status"]), (0, "sealed"), rec)
        ann = [a for k, a in self.calls() if k == "FAKE_SCANNO_LOG" and a[0] == "annotate"]
        self.assertTrue(ann and all(a[a.index("--gap-min") + 1] == "0.2" for a in ann), ann)
        self.assertFalse([a for k, a in self.calls() if "--drop-labels" in a or "--no-exclude" in a])
        rc, text = cli("--json", "events", "--stack", str(out / "02_anno"), "--kind", "decision")
        ev = {e["name"]: (e["kind"], e["value"], e["by"]) for e in json.loads(text)}
        self.assertEqual(ev["anno.gap_min"], ("decision/answered", 0.2, "a tester"))
        self.assertEqual(ev["anno.no_exclude"], ("decision/unanswered", None, None))

    def test_D_a_tool_declaring_an_escape_its_adapter_does_not_ask_is_refused_at_its_stage(self):
        c = cohort(self.tmp / "c", "a")
        req, out = request(c), self.tmp / "run"
        os.environ["FAKE_SCANNO_MODE"] = "escape_drift"
        rc, rec = self.drive(req, out, *answered(c))
        self.assertEqual((rc, rec["status"], rec["stage"]), (2, "failed", "02_anno"), rec)
        self.assertIn("declares the escape(s) --drift", rec["reason"])
        self.assertIn("anno.no_exclude", [e["name"] for e in rec["escapes"]])
        os.environ.pop("FAKE_SCANNO_MODE")
        os.environ["FAKE_SCINTEGRATE_MODE"] = "escape_drift"
        rc, rec = self.drive(req, out)
        self.assertEqual((rc, rec["status"], rec["stage"]), (2, "failed", "03_int"), rec)
        self.assertIn("declares the escape(s) a stand-in's new escape", rec["reason"])

    def test_a_fact_stated_twice_must_agree_and_a_word_is_its_letters(self):
        c = cohort(self.tmp / "c", "a")
        st = stages(c)
        st[1]["params"]["annotate"]["species"] = "species_y"
        rc, rec = self.drive(request(c, name="sp.yml", stages=st), self.tmp / "r1")
        self.assertEqual((rc, rec["status"]), (2, "refused"), rec)
        self.assertIn("annotate.species is 'species_y', but the request's context declares species 'species_x'",
                      rec["reason"])
        st[1]["params"]["annotate"]["species"] = "Species_X"
        self.assertEqual(cli("plan", "--request", str(request(c, name="sp2.yml", stages=st)))[0], 0)
        req = request(c, name="ws.yml", context={"assay": " snrna ", "species": "species_x", "tissue": "tissue_x"})
        rc, text = cli("--json", "plan", "--request", str(req))
        self.assertEqual((rc, json.loads(text)["context"]["assay"]), (0, "snrna"))
        self.assertEqual(self.calls(), [])

    def test_two_candidates_are_refused_by_name_and_a_shape_not_handed_on_fails_its_stage(self):
        c = cohort(self.tmp / "c", "a")
        os.environ["FAKE_SCQC_MODE"] = "two_prefixes"
        rc, rec = self.drive(request(c), self.tmp / "r1", *answered(c))
        self.assertEqual((rc, rec["status"], rec["stage"]), (2, "failed", "01_qc"), rec)
        self.assertIn("kept objects for library", rec["reason"])
        os.environ["FAKE_SCQC_MODE"] = "no_joint"
        st = stages(c)
        out = self.tmp / "r2"
        rc, rec = self.drive(request(c, name="nj.yml", stages=[st[0], st[2], st[3]]), out, *answered(c))
        self.assertEqual((rc, rec["status"], rec["stage"]), (2, "failed", "02_int"), rec)
        self.assertIn("handed on none", rec["reason"])
        self.assertEqual(json.loads((out / "DRIVE.json").read_text())["status"], "failed")


SWAP = lambda t: t.replace("control", "@").replace("treated", "control").replace("@", "treated")  # noqa: E731
CTRL = ["--answer", CONTROL.format(c="condition"), "--by", "a tester"]


class TheDriverHoldsItsRulesRound2(_Base):
    """W042 fix 2: each break of the re-check closed by its principle, each through `sch`."""

    def sheet(self, c, rename=None, cols=None):
        f = c["dir"] / "samplesheet.tsv"
        f.chmod(0o644)
        rows = [ln.split("\t") for ln in f.read_text().splitlines()]
        if rename:
            rows[0][rows[0].index(rename[0])] = rename[1]
        for name, fn in (cols or {}).items():
            rows[0].append(name)
            for r in rows[1:]:
                r.append(str(fn(r[0])))
        f.write_text("\n".join("\t".join(r) for r in rows) + "\n")
        f.chmod(0o444)

    def plan(self, req):
        rc, text = cli("--json", "plan", "--request", str(req))
        return rc, json.loads(text).get("reason") or ""

    def set_design(self, c, text):
        c["design"].chmod(0o644)
        c["design"].write_text(text)

    # ---- B: one set, recomputed and compared everywhere
    def test_B2_the_set_is_every_file_the_run_reads_and_a_relative_param_is_refused(self):
        c = cohort(self.tmp / "c", "a")
        refs = c["dir"] / "refdir" / "sub"
        refs.mkdir(parents=True)
        (refs / "ref.tsv").write_text("a\t1\n")
        for i in range(1, 5):
            (c["dir"] / f"raw{i}.h5").write_text("raw v1\n")
        self.sheet(c, cols={"raw_h5": lambda lib: c["dir"] / f"raw{lib[1:]}.h5"})
        st = stages(c)
        st[3]["params"]["run"]["references"] = str(refs.parent)
        req, out = request(c, stages=st), self.tmp / "run"
        rc, rec = self.drive(req, out, *ANSWERS, "--by", "a tester")
        self.assertEqual((rc, rec.get("stage")), (3, "04_prof"), rec)
        files = json.loads((out / "INPUTS.json").read_text())["files"]
        for role in ("04_prof.run.references/sub/ref.tsv", "observations.raw_h5[L1]", "02_anno.scanno"):
            self.assertIn(role, files)
        self.assertFalse([k for k in files if "__pycache__" in k or k.endswith(".pyc")])
        for f, role in [(refs / "ref.tsv", "04_prof.run.references/sub/ref.tsv"),
                        (c["dir"] / "raw1.h5", "observations.raw_h5[L1]")]:
            was = f.read_text()
            f.write_text("changed\n")
            rc, rec = self.drive(req, out, *CTRL)
            self.assertEqual((rc, rec["status"]), (2, "refused"), rec)
            self.assertIn(role, rec["reason"])
            f.write_text(was)
        (refs / "new.tsv").write_text("added\n")
        rc, rec = self.drive(req, out, *CTRL)
        self.assertIn("04_prof.run.references/sub/new.tsv", rec.get("reason", ""), rec)
        (refs / "new.tsv").unlink()
        rc, rec = self.drive(req, out, *CTRL)
        self.assertEqual((rc, rec["status"]), (0, "sealed"), rec)
        (c["dir"] / "tree.json").write_text('{"v": 1}\n')
        st = stages(c)
        st[1]["params"]["annotate"]["tree"] = "tree.json"
        rc, why = self.plan(request(c, name="rel.yml", stages=st))
        self.assertEqual(rc, 2, why)
        self.assertIn("annotate.tree is 'tree.json', a relative path", why)

    def test_B3_a_sealed_stage_is_trusted_only_on_the_runs_record(self):
        c = cohort(self.tmp / "c", "a")
        req, out = request(c), self.tmp / "run"
        rc, rec = self.drive(req, out, *ANSWERS, "--by", "a tester")
        self.assertEqual((rc, rec.get("stage")), (3, "04_prof"), rec)
        was = c["design"].read_text()
        keep = {f: f.read_bytes() for f in (out / "INPUTS.json", out / "request.json")}

        def restore():
            self.set_design(c, was)
            for f, b in keep.items():
                f.write_bytes(b)
        self.set_design(c, SWAP(was))            # the record edited to the swapped design (the re-check's B4)
        doc = json.loads(keep[out / "INPUTS.json"])
        for k in ("design", "03_int.integrate.design"):
            doc["files"][k]["sha256"] = sha(c["design"])
        (out / "INPUTS.json").write_text(json.dumps(doc))
        rc, rec = self.drive(req, out, *CTRL)
        self.assertEqual((rc, rec["status"]), (2, "refused"), rec)
        self.assertIn("was sealed on other files", rec["reason"])
        restore()
        for f in keep:                           # the record removed (B5): never a fresh start
            f.unlink()
        rc, rec = self.drive(req, out, *CTRL)
        self.assertEqual((rc, rec["status"]), (2, "refused"), rec)
        self.assertIn("a missing record is not a fresh start", rec["reason"])
        restore()
        for n, names in enumerate([("01_qc", "02_anno", "03_int"),
                                   ("01_qc", "02_anno", "03_int", "INPUTS.json", "request.json", "decisions.json")]):
            new = self.tmp / f"copy{n}"          # sealed stages copied into another run directory
            new.mkdir()
            for x in names:
                (shutil.copytree if (out / x).is_dir() else shutil.copy2)(out / x, new / x)
            rc, rec = self.drive(req, new, *CTRL)
            self.assertEqual((rc, rec["status"]), (2, "refused"), rec)
            self.assertIn("start a new --out", rec["reason"])
        seal = out / "02_anno" / "SEALED.json"
        b = seal.read_bytes()
        seal.write_text(b.decode().replace('"numbers"', '"numbers" ', 1))
        rc, rec = self.drive(req, out, *CTRL)
        self.assertIn("02_anno's seal is not one this run recorded", rec.get("reason", ""), rec)
        seal.write_bytes(b)
        joint = Path(json.loads(b)["hands_on"]["joint"])
        jb = joint.read_bytes()
        joint.chmod(0o644)
        joint.write_bytes(jb + b"\0")
        rc, rec = self.drive(req, out, *CTRL)
        self.assertIn("02_anno handed on", rec.get("reason", ""), rec)
        joint.write_bytes(jb)
        rc, rec = self.drive(req, out, *CTRL)
        self.assertEqual((rc, rec["status"]), (0, "sealed"), rec)

    def test_B4_the_set_is_recomputed_at_each_stages_start_and_at_its_seal(self):
        import sch.drive as D
        c = cohort(self.tmp / "c", "a")
        req, out = request(c), self.tmp / "run"
        was = c["design"].read_text()
        real = Stack.run_declared

        def during(st, *a, **k):                 # swapped while stage 3's tool runs, and left so
            r = real(st, *a, **k)
            if Path(st.dir).name == "03_int":
                self.set_design(c, SWAP(was))
            return r
        Stack.run_declared = during
        try:
            rc, rec = self.drive(req, out, *answered(c))
        finally:
            Stack.run_declared = real
        self.assertEqual((rc, rec["status"], rec.get("stage")), (2, "failed", "03_int"), rec)
        self.assertIn("changed while 03_int ran", rec["reason"])
        self.assertIn("design", rec["reason"])
        self.assertFalse((out / "03_int" / "SEALED.json").exists())
        self.set_design(c, was)
        real_stage = D._stage

        def around(p, sd, *a, **k):              # the re-check's B6: swapped before a stage, back after it
            if p["stage"] == "04_prof":
                self.set_design(c, SWAP(was))
            try:
                return real_stage(p, sd, *a, **k)
            finally:
                self.set_design(c, was)
        D._stage = around
        try:
            rc, rec = self.drive(req, out)
        finally:
            D._stage = real_stage
        self.assertEqual((rc, rec["status"], rec.get("stage")), (2, "failed", "04_prof"), rec)
        self.assertIn("before 04_prof started", rec["reason"])
        rc, rec = self.drive(req, out)
        self.assertEqual((rc, rec["status"]), (0, "sealed"), rec)
        for s in ("01_qc", "02_anno", "03_int", "04_prof"):
            self.assertEqual(json.loads((out / s / "SEALED.json").read_text())["inputs"]["design"], sha(c["design"]))

    # ---- A: rule 2 read from every place a step is declared, and the places agree
    def test_B5_a_seal_the_ledger_names_is_never_missing_and_the_seals_are_in_order(self):
        c = cohort(self.tmp / "c", "a")
        req, out = request(c), self.tmp / "run"
        rc, rec = self.drive(req, out, *ANSWERS, "--by", "a tester")
        self.assertEqual((rc, rec.get("stage")), (3, "04_prof"), rec)
        (out / "02_anno" / "SEALED.json").unlink()   # a middle stage's seal removed: 02 would run again
        n = len(self.calls())                        # beneath 03, sealed on what 02 handed on before
        rc, rec = self.drive(req, out, *CTRL)
        self.assertEqual((rc, rec["status"]), (2, "refused"), rec)
        self.assertIn("names 02_anno's seal", rec["reason"])
        led = json.loads((out / "INPUTS.json").read_text())
        del led["seals"]["02_anno"]                  # and the ledger edited to agree
        (out / "INPUTS.json").write_text(json.dumps(led))
        rc, rec = self.drive(req, out, *CTRL)
        self.assertEqual((rc, rec["status"]), (2, "refused"), rec)
        self.assertIn("03_int is sealed and 02_anno, before it, is not", rec["reason"])
        self.assertEqual(len(self.calls()), n, "nothing ran again")

    def test_B6_a_path_out_of_its_tools_directory_is_refused_and_an_adapter_not_shipped_is_pinned(self):
        c = cohort(self.tmp / "c", "a")
        for v, refused in (("../../../../../c/design.csv", True), ("x/../../design.csv", True),
                           ("~nobody/design.csv", True), ("made_by_the_run/x.tsv", False), ("~ condition", False)):
            st = stages(c)
            st[3]["params"]["run"]["references"] = v
            rc, reason = self.plan(request(c, name="rel.yml", stages=st))
            with self.subTest(value=v):
                self.assertEqual(rc, 2 if refused else 0, reason)
                if refused:
                    self.assertIn("out of its tool's working directory", reason)
        plug = self.tmp / "adapters" / "qc@scqc"     # the first stage's adapter named by a path
        shutil.copytree(Path(__file__).resolve().parent.parent / "plugins" / "single-cell" / "qc@scqc", plug,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        st = stages(c)
        st[0]["plugin"] = str(plug)
        req, out = request(c, name="bypath.yml", stages=st), self.tmp / "run"
        rc, rec = self.drive(req, out, *ANSWERS, "--by", "a tester")
        self.assertEqual((rc, rec.get("stage")), (3, "04_prof"), rec)
        files = json.loads((out / "INPUTS.json").read_text())["files"]
        self.assertIn("01_qc.plugin/run.py", files)
        self.assertFalse([k for k in files if k.startswith("02_anno.plugin")], "a shipped adapter is the harness's")
        with open(plug / "run.py", "a") as fh:      # its code edited after its stage sealed
            fh.write("# edited\n")
        rc, rec = self.drive(req, out, *CTRL)
        self.assertEqual((rc, rec["status"]), (2, "refused"), rec)
        self.assertIn("01_qc.plugin/run.py", rec["reason"])

    def test_A2_rule_2_reads_every_key_of_every_step_and_the_shipped_profile_only(self):
        c = cohort(self.tmp / "c", "a", assay="scrna")
        self.sheet(c, rename=("ambient_h5", "matrix"))   # the aligner's call, not a denoised object
        cr = {"tool": "cellranger", "version": "7.1.0"}

        def req(name, amb, aln=cr, **over):
            return request(c, name=name, parts="matrix", context=scrna(),
                           upstream={"alignment": aln, "ambient": amb}, **over)
        refused = [({"tool": "none", "version": "CellBender 0.3.0"}, cr, "is 'CellBender 0.3.0', not a release number"),
                   ({"tool": "none", "version": "0.3.0"}, cr, "a step nothing performed has no version"),
                   ({"tool": "none", "ran": True, "command": "cellbender remove-background"}, cr,
                    "command, ran is not a step field"),
                   ({"tool": ["none"]}, cr, "it is one tool's name"),
                   ({"tool": "none; cellbender ran"}, cr, "upstream.allowed.scrna.ambient: none"),
                   ({"tool": "none\u200b"}, cr, "upstream.allowed.scrna.ambient: none"),
                   ({"tool": "remover_x"}, cr, "upstream.allowed.scrna.ambient: none"),
                   ({"tool": "none"}, {"tool": "cellranger count + cellbender remove-background"},
                    "upstream.allowed.scrna.alignment"),
                   ({"tool": "none"}, {"tool": "cellranger", "version": "7.1.0-cellbender"}, "not a release number")]
        for i, (amb, aln, said) in enumerate(refused):
            with self.subTest(said=said, amb=amb):
                rc, why = self.plan(req(f"r{i}.yml", amb, aln))
                self.assertEqual(rc, 2, why)
                self.assertIn(said, why)
        for i, (amb, aln) in enumerate([({"tool": "NONE "}, cr), ({"tool": "none"}, {"tool": "Cell Ranger", "version": "v7.1.0"})]):
            self.assertEqual(self.plan(req(f"ok{i}.yml", amb, aln)), (0, ""))
        st = stages(c)                           # the family never runs the remover on cells: no decision
        st[0]["params"]["cellbender"] = "/path/to/cellbender"
        rc, why = self.plan(req("cb.yml", {"tool": "none"}, stages=st))
        self.assertEqual(rc, 2, why)
        self.assertIn("params set cellbender, with which its tool performs ambient itself", why)
        plug = self.tmp / "plugins" / "qc@scqc"  # a plugin by path whose profile has the rule removed
        shutil.copytree(Path(__file__).resolve().parent.parent / "plugins" / "single-cell" / "qc@scqc", plug)
        prof = self.tmp / "loose.yml"
        text = (Path(__file__).resolve().parent.parent / "sch" / "profile" / "single-cell.yml").read_text()
        prof.write_text(text.replace("ambient: [none]", "ambient: [none, cellbender]"))
        m = plug / "plugin.yml"
        m.write_text(m.read_text().replace("profile: single-cell/1.0", f"profile: {prof}"))
        st = stages(c)
        st[0]["plugin"] = str(plug)
        rc, why = self.plan(req("byp.yml", {"tool": "cellbender"}, stages=st))
        self.assertEqual(rc, 2, why)
        self.assertIn("only from a profile this harness ships", why)
        sn = cohort(self.tmp / "sn", "a")        # nuclei list what may run too: nothing by silence
        rc, why = self.plan(request(sn, name="sn.yml", upstream={"alignment": cr, "ambient": {"tool": "remover_x"}}))
        self.assertEqual(rc, 2, why)
        self.assertIn("upstream.allowed.snrna.ambient: none, cellbender", why)
        self.sheet(c, cols={"ambient_tool": lambda lib: "CellBender", "ambient_version": lambda lib: "0.3.0"})
        rc, why = self.plan(req("a7.yml", {"tool": "none"}))   # the re-check's A7: the samplesheet says it
        self.assertEqual(rc, 2, why)
        self.assertIn("the samplesheet's row L1 says ambient_tool='CellBender'", why)
        self.sheet(sn, cols={"ambient_tool": lambda lib: "CellBender", "ambient_version": lambda lib: "0.3.2"})
        rc, why = self.plan(request(sn, name="sn2.yml", upstream={"alignment": cr, "ambient": {"tool": "cellbender",
                                                                                               "version": "0.3.0"}}))
        self.assertEqual(rc, 2, why)
        self.assertIn("ambient_version='0.3.2'", why)
        self.assertEqual(self.calls(), [])

    def test_A3_single_cells_denoised_elsewhere_stop_the_run_at_the_users_decision(self):
        c = cohort(self.tmp / "c", "a", assay="scrna", extra={"ambient_tool": "CellBender", "ambient_version": "0.3.0"})
        req = request(c, context=scrna(), upstream={"alignment": {"tool": "cellranger", "version": "7.1.0"},
                                                     "ambient": {"tool": "CellBender", "version": "0.3.0"}})
        rc, text = cli("plan", "--request", str(req))
        self.assertEqual(rc, 0, text)
        self.assertIn("the user's: upstream.ambient", text)
        self.assertIn("UNANSWERED - nothing runs (accept | decline)", text)
        out = self.tmp / "run"
        rc, rec = self.drive(req, out, *answered(c))
        self.assertEqual((rc, rec["status"], rec["stage"]), (3, "waiting", "01_qc"), rec)
        self.assertEqual([d["name"] for d in rec["waiting_for"]], ["upstream.ambient"])
        rc, rec = self.drive(req, out, "--answer", "upstream.ambient=maybe", "--by", "a tester")
        self.assertIn("upstream.ambient is answered accept or decline", rec["reason"])
        rc, rec = self.drive(req, out, "--answer", "upstream.ambient=decline", "--by", "the PI")
        self.assertEqual((rc, rec["status"]), (2, "refused"), rec)
        self.assertIn("declined, nothing runs", rec["reason"])
        self.assertEqual(self.calls(), [], "unanswered or declined, nothing runs")
        out2 = self.tmp / "run2"
        rc, rec = self.drive(req, out2, *answered(c), "--answer", "upstream.ambient=accept")
        self.assertEqual((rc, rec["status"]), (0, "sealed"), rec)
        self.assertEqual(json.loads((out2 / "decisions.json").read_text())["upstream.ambient"]["by"], "a tester")
        rc, text = cli("--json", "events", "--stack", str(out2 / "01_qc"), "--kind", "decision")
        self.assertIn(("upstream.ambient", "decision/answered", "accept", "a tester"),
                      [(e["name"], e["kind"], e.get("value"), e.get("by")) for e in json.loads(text)])

    # ---- D: every escape a tool declares is asked, under any spelling
    def test_D2_scprofiles_escapes_are_asked_and_no_escape_passes_under_another_spelling(self):
        c = cohort(self.tmp / "c", "a")
        for i, (k, cmd, over) in enumerate([(3, "run", {"allow": "de,abundance"}), (3, "run", {"force": True}),
                                            (3, "run", {"no-validate": True}), (3, "run", {"Force": True}),
                                            (1, "annotate", {"no-exclude": True})]):
            st = stages(c)
            st[k]["params"][cmd].update(over)
            with self.subTest(over=over):
                rc, why = self.plan(request(c, name=f"e{i}.yml", stages=st))
                self.assertEqual(rc, 2, why)
                self.assertIn("--answer", why)
        out = self.tmp / "run"
        rc, rec = self.drive(request(c), out, *answered(c), "--answer", "prof.allow=de")
        self.assertEqual((rc, rec["status"]), (0, "sealed"), rec)
        prof = [a for k, a in self.calls() if k == "FAKE_SCPROFILE_LOG" and "--h5ad" in a]
        self.assertTrue(prof and all(a[a.index("--allow") + 1] == "de" for a in prof), prof)
        self.assertFalse([a for a in prof if "--force" in a or "--no-validate" in a])
        rc, text = cli("--json", "events", "--stack", str(out / "04_prof"), "--kind", "decision")
        ev = {e["name"]: (e["kind"], e["value"], e["by"]) for e in json.loads(text)}
        self.assertEqual(ev["prof.allow"], ("decision/answered", "de", "a tester"))
        self.assertEqual(ev["prof.force"], ("decision/unanswered", None, None))

    @unittest.skipUnless(os.environ.get("SCH_REAL_TOOLS"), "SCH_REAL_TOOLS names no checkouts of the real tools")
    def test_D3_the_manifests_are_the_real_tools_escapes_when_their_checkouts_are_here(self):
        import subprocess
        root = Path(os.environ["SCH_REAL_TOOLS"])
        plugins = Path(__file__).resolve().parent.parent / "plugins" / "single-cell"
        py = [os.environ.get("SCH_REAL_PY", sys.executable)]
        compared = []
        for plugin, name, argv in [("qc@scqc", "scQC", py + ["scqc_cli.py", "describe"]),
                                   ("anno@scanno", "scAnno", py + ["bin/scanno", "describe"]),
                                   ("int@scintegrate", "scIntegrate", py + ["-m", "scintegrate.cli", "describe"])]:
            d = root / name
            if not d.is_dir():
                continue
            r = subprocess.run(argv, cwd=str(d), capture_output=True, text=True, env=dict(os.environ, PYTHONPATH=str(d)))
            said = json.loads(r.stdout)
            declared = {str(e.get("flag") or e.get("what")) for e in said.get("escapes") or []}
            m = yamlish.load(plugins / plugin / "plugin.yml")
            asked = {x["escape"] for x in m.get("decisions") or [] if x.get("escape")}
            self.assertEqual(declared, asked | set(m.get("escapes_not_asked") or {}), f"{name} at {d}")
            compared.append(name)
        if (root / "scProfile").is_dir():        # no describe: each listed escape is a flag of its `run`
            src = (root / "scProfile" / "scprofile" / "cli.py").read_text()
            m = yamlish.load(plugins / "prof@scprofile" / "plugin.yml")
            listed = [x["escape"] for x in m["decisions"] if x.get("escape")]
            for x in listed:
                self.assertIn(f'r.add_argument("{x}"', src, x)
            # the guard's escape scProfile names itself (kernels.py guard_verdict: "the escape is one flag away")
            self.assertIn('f"--allow {kernel.name}"', (root / "scProfile" / "scprofile" / "kernels.py").read_text())
            self.assertIn("--allow", listed, "scProfile's own escape is asked")
            compared.append("scProfile")
        self.assertTrue(compared, f"no tool checkout under {root}")

    # ---- the observation: a flag an adapter owns is refused when the plan is made
    def test_an_owned_flag_is_refused_when_the_plan_is_made_and_the_manifests_copy_run_py(self):
        import ast
        c = cohort(self.tmp / "c", "a")
        for i, (k, cmd, flag) in enumerate([(0, None, "samplesheet"), (1, "annotate", "out_h5ad"),
                                            (2, "integrate", "out"), (3, "run", "design")]):
            st = stages(c)
            (st[k]["params"][cmd] if cmd else st[k]["params"])[flag] = "/somewhere"
            with self.subTest(flag=flag):
                rc, why = self.plan(request(c, name=f"o{i}.yml", stages=st))
                self.assertEqual(rc, 2, why)
                self.assertIn("sets itself from the stack (its `owned:`)", why)
        plugins = Path(__file__).resolve().parent.parent / "plugins" / "single-cell"
        for plugin, cmd in [("qc@scqc", None), ("anno@scanno", None), ("int@scintegrate", "integrate"),
                            ("prof@scprofile", "run")]:
            def keys(n):                         # the names OWNED declares, not the reasons beside them
                if isinstance(n, ast.Dict):
                    return {k.value: keys(v) for k, v in zip(n.keys, n.values)}
                return {e.value: None for e in n.elts} if isinstance(n, (ast.Tuple, ast.List)) else None
            tree = ast.parse((plugins / plugin / "run.py").read_text())
            owned = [keys(n.value) for n in tree.body if isinstance(n, ast.Assign)
                     and any(getattr(t, "id", "") == "OWNED" for t in n.targets)][0]
            want = ({f"{c_}.{f}" for c_, fl in owned.items() for f in fl} if plugin == "anno@scanno" else
                    {f"{cmd}.{f}" for f in owned} if cmd else set(owned))
            self.assertEqual(set(yamlish.load(plugins / plugin / "plugin.yml")["owned"]), want, plugin)


if __name__ == "__main__":
    unittest.main()
