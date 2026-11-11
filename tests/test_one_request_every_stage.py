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


def stages(c: dict) -> list:
    """Each stage's tool flags, verbatim, by the tool's own names."""
    return [
        {"plugin": "qc@scqc", "params": {"scqc": str(FIXTURES / "fake_scqc.py"),
                                         "registry": str(c["dir"] / "registry.tsv"), "executor": "local",
                                         "allow_local": True, "dbr": 0.06, "seed": 0}},
        {"plugin": "anno@scanno", "params": {
            "scanno": str(FIXTURES / "fake_scanno.py"), "cluster": {"resolutions": "0.5,1.0", "seed": 0},
            "annotate": {"cluster_key": ["leiden_0p5", "leiden_1p0"], "tree": "/refs/tree.json",
                         "species": "species_x", "tissue": "tissue_x"},
            "embed": {"label_obs": ["scanno_cell_type=cell_type"], "seed": 0}}},
        {"plugin": "int@scintegrate", "params": {
            "scintegrate": str(FIXTURES / "fake_scintegrate"),
            "integrate": {"batch_key": "sample", "label_key": "cell_type", "design": str(c["design"]),
                          "design_sample_col": c["roles"]["sample"], "methods": "none,harmony",
                          "seed": 0, "n_cores": 1}}},
        {"plugin": "prof@scprofile", "params": {
            "scprofile": str(FIXTURES / "fake_scprofile"),
            "run": {"kernel": "de,abundance", "label_key": "cell_type", "sample_key": "sample",
                    "batch_key": "sample", "embedding": "X_harmony", "no_cache": True,
                    "prefix": "/declared/prefix", "timeout": 600}}},
    ]


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
        reps, died = self.check_equal_by_hand(c, out, 3)
        if rc == 0:
            self.assertIsNone(died)
        else:
            # scQC writes `sample` into its objects whatever the cohort calls it, and scProfile joins
            # the design on its --sample-key: stage 4 fails, through the driver and by hand alike
            self.assertEqual((rc, rec["status"], rec["stage"]), (2, "failed", "04_prof"), rec)
            self.assertIn("--out", rec["resume"])
            self.assertIsNotNone(died)
            self.assertEqual(died["status"], rec["reason"].split(" ")[1].rstrip(":"))


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


if __name__ == "__main__":
    unittest.main()
