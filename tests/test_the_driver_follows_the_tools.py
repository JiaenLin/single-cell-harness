"""The driver's residue after its last re-check (harness autodev W049, GAP-C110, GAP-C111).

What must hold, each through `sch` and asserted against the world (the tools' argv, the records):
  - every route by which a path reaches a tool is in the run's one set or refused, at every moment:
    an ANSWER's file (scQC's thresholds, `--answer qc.decisions=FILE`) at the start, at each stage's
    start and seal, on a resume, in `sch plan --expect` and in a generated job's pins; a file under a
    linked directory; a path a named document holds; the site layer; the harness and each tool's
    checkout; a relative answer, a blank `--by` and a size or an answer on two lines are refused;
  - what may have run upstream of an assay is what the first stage's tool accepts there (its adapter's
    `upstream_accepts:`, drift-tested against the tool), rule 2 over it (the profile's), whatever
    stage the request starts at; a word named like a folder beside the request is a word.
The tools are the suite's stand-ins; the drift test reads the real scQC where SCH_REAL_TOOLS names it.
"""
import importlib.util
import json
import os
import sys
import unittest
from pathlib import Path

import test_one_request_every_stage as M
from helpers import FIXTURES
from sch import yamlish
from test_one_request_every_stage import ANSWERS, CONTROL, PROVENANCE, cli, cohort, request, scrna, stages

ROOT = Path(__file__).resolve().parent.parent


def ctrl(c):
    return ["--answer", CONTROL.format(c=c["roles"]["condition"]), "--by", "a tester"]


def thresholds(d: Path, v) -> Path:
    f = d / "thresholds" / "decisions.yml"
    f.parent.mkdir(exist_ok=True)
    f.write_text(f"umi_floor: {{value: {v}, class: DERIVED, approved_by: the PI}}\n")
    return f


def sheet(c, rename=None, cols=None):
    f = c["dir"] / "samplesheet.tsv"
    f.chmod(0o644)
    rows = [ln.split("\t") for ln in f.read_text().splitlines()]
    if rename:
        rows[0][rows[0].index(rename[0])] = rename[1]
    for k, v in (cols or {}).items():
        rows[0].append(k)
        for r in rows[1:]:
            r.append(v)
    f.write_text("\n".join("\t".join(r) for r in rows) + "\n")
    f.chmod(0o444)


class EveryRouteIsInTheSet(M._Base):
    def test_an_answered_file_is_in_the_set_at_the_start_on_a_resume_and_in_the_plans_check(self):
        c, dec = cohort(self.tmp / "c", "a"), thresholds(self.tmp, 500)
        req, out = request(c), self.tmp / "run"
        ans = ["--answer", "qc.mode=apply", "--answer", f"qc.decisions={dec}", "--by", "a tester"]
        rc, rec = self.drive(req, out, *ans)
        self.assertEqual((rc, rec.get("stage")), (3, "04_prof"), rec)
        self.assertEqual(json.loads((out / "INPUTS.json").read_text())["files"]["answer[qc.decisions]"]["path"],
                         str(dec))
        self.assertIn("answer[qc.decisions]", json.loads((out / "01_qc" / "SEALED.json").read_text())["inputs"])
        qc = [a for k, a in self.calls() if k == "FAKE_SCQC_LOG" and "--decisions" in a]
        self.assertEqual(qc[0][qc[0].index("--decisions") + 1], str(dec), "the tool read that file")
        thresholds(self.tmp, 5000)               # the re-checker's atk_b: edited after stage 1 sealed
        rc, rec = self.drive(req, out, *ctrl(c))
        self.assertEqual((rc, rec["status"]), (2, "refused"), rec)
        self.assertIn("answer[qc.decisions]", rec["reason"])
        thresholds(self.tmp, 500)
        from sch.drive import answers_of, load, run_inputs
        given, _new = answers_of(load(req), [x for x in ans[:-2] if x != "--answer"], "a tester")
        pins = self.tmp / "PINS.json"
        pins.write_text(json.dumps({"files": run_inputs(load(req), given)}))
        rc, text = cli("plan", "--request", str(req), *ans, "--expect", str(pins))
        self.assertEqual(rc, 0, text)
        thresholds(self.tmp, 50)                 # edited after the job's pins (atk_b, 3)
        rc, text = cli("plan", "--request", str(req), *ans, "--expect", str(pins))
        self.assertEqual(rc, 2, text)
        self.assertIn("differs: answer[qc.decisions]", text)
        rc, rec = self.drive(req, out, *ctrl(c))
        self.assertIn("answer[qc.decisions]", rec.get("reason", ""), rec)
        thresholds(self.tmp, 500)
        rc, rec = self.drive(req, out, *ctrl(c))
        self.assertEqual((rc, rec["status"]), (0, "sealed"), rec)

    def test_an_answer_given_at_a_resume_enters_the_record_and_a_relative_or_blank_one_is_refused(self):
        c, dec = cohort(self.tmp / "c", "a"), thresholds(self.tmp, 500)
        req, out = request(c), self.tmp / "run"
        rc, rec = self.drive(req, out)
        self.assertEqual((rc, rec.get("stage")), (3, "01_qc"), rec)
        (c["dir"] / "thr.yml").write_text("umi_floor: {value: 1}\n")
        for bad, said in [(["--answer", "qc.decisions=thr.yml", "--by", "a tester"], "is a relative path"),
                          (["--answer", "qc.mode=apply", "--by", " "], "a blank is no name"),
                          (["--answer", "qc.mode=apply", "--by", "a\ntester"], "one line of printable text"),
                          (["--answer", "qc.decisions=/x\n/y", "--by", "a tester"], "one line of printable text")]:
            with self.subTest(bad=bad):
                rc, rec = self.drive(req, out, *bad)
                self.assertEqual((rc, rec["status"]), (2, "refused"), rec)
                self.assertIn(said, rec["reason"])
                rc, text = cli("plan", "--request", str(req), *bad)
                self.assertEqual(rc, 2, text)
        rc, rec = self.drive(req, out, "--answer", "qc.mode=apply", "--answer", f"qc.decisions={dec}", "--by", "the PI")
        self.assertEqual((rc, rec.get("stage")), (3, "04_prof"), rec)
        self.assertIn("answer[qc.decisions]", json.loads((out / "INPUTS.json").read_text())["files"])
        thresholds(self.tmp, 7)
        rc, rec = self.drive(req, out, *ctrl(c))
        self.assertIn("answer[qc.decisions]", rec.get("reason", ""), rec)
        self.assertEqual(json.loads((out / "decisions.json").read_text())["qc.mode"]["by"], "the PI")

    def test_a_linked_directory_a_document_the_harness_and_each_tools_checkout_are_in_the_set(self):
        c = cohort(self.tmp / "c", "a")
        refs, real = self.tmp / "refs", self.tmp / "elsewhere" / "sub"
        refs.mkdir()
        real.mkdir(parents=True)
        (real / "ref.tsv").write_text("a\t1\n")
        (refs / "linked").symlink_to(real)       # the re-checker's atk_b2: a linked subdirectory
        (refs / "loop").symlink_to(refs)
        named = self.tmp / "genome" / "ref.fa"
        named.parent.mkdir()
        named.write_text(">x\nACGT\n")
        reg = self.tmp / "registry.tsv"          # a path inside a named document (scQC's registry)
        reg.write_text(f"species\tbuild\tpath\nspecies_x\tref_1\t{named}\n")
        st = stages(c)
        st[3]["params"]["run"]["references"] = str(refs)
        st[0]["params"]["registry"] = str(reg)
        req, out = request(c, stages=st), self.tmp / "run"
        rc, rec = self.drive(req, out, *ANSWERS, "--by", "a tester")
        self.assertEqual((rc, rec.get("stage")), (3, "04_prof"), rec)
        files = json.loads((out / "INPUTS.json").read_text())["files"]
        self.assertEqual(files["04_prof.run.references/loop"].get("loop"), os.path.realpath(refs))
        for role in ("04_prof.run.references/linked/ref.tsv", "01_qc.registry>[1.2]", "harness",
                     "01_qc.scqc@checkout", "02_anno.scanno@checkout"):
            self.assertIn(role, files)
        for f, role in [(real / "ref.tsv", "04_prof.run.references/linked/ref.tsv"), (named, "01_qc.registry>[1.2]")]:
            was = f.read_text()
            f.write_text("changed\n")
            rc, rec = self.drive(req, out, *ctrl(c))
            self.assertEqual((rc, rec["status"]), (2, "refused"), rec)
            self.assertIn(role, rec["reason"])
            f.write_text(was)
        rc, rec = self.drive(req, out, *ctrl(c))
        self.assertEqual((rc, rec["status"]), (0, "sealed"), rec)

    def test_a_word_named_like_a_folder_beside_the_request_is_a_word(self):
        c = cohort(self.tmp / "c", "a")
        (c["dir"] / "harmony").mkdir()           # the re-checker's atk_w: methods none,harmony
        (c["dir"] / "de").mkdir()
        rc, text = cli("plan", "--request", str(request(c)))
        self.assertEqual(rc, 0, text)
        (c["dir"] / "tree.json").write_text("{}\n")
        st = stages(c)
        st[1]["params"]["annotate"]["tree"] = "tree.json"
        rc, text = cli("plan", "--request", str(request(c, name="rel.yml", stages=st)))
        self.assertEqual(rc, 2, text)
        self.assertIn("a relative path", text)

    def test_a_size_on_two_lines_is_refused_before_any_tool(self):
        c = cohort(self.tmp / "c", "a")
        rc, text = cli("plan", "--request", str(request(c, resources={"qc": {"ncpus": "4\n"}})))
        self.assertEqual(rc, 2, text)
        self.assertIn("one line of printable text", text)


class TheJobPinsEveryRoute(M.TheClusterPath):
    def test_W049_the_job_pins_an_answered_file_and_the_site_layer_and_refuses_flags_laid_by_the_site(self):
        dec = thresholds(self.tmp, 500)
        orig = M.answered
        M.answered = lambda c: [a.replace("qc.decisions=null", f"qc.decisions={dec}") for a in orig(c)]
        try:
            c = cohort(self.tmp / "c", "a")
            req = request(c, resources=self.SIZES)
            f, _rec = self.job(c, req)
        finally:
            M.answered = orig
        pins = f.read_text().split("SCH_PINS_END")[1]
        self.assertIn("answer[qc.decisions]", pins)
        self.assertIn("site.stack.yml", pins)
        check = [ln for ln in f.read_text().splitlines() if ln.startswith("PYTHONPATH=") and " sch plan " in ln]
        self.assertIn(f"--answer qc.decisions={dec}", check[0], "the job's check gives the run's answers")
        thresholds(self.tmp, 50000)              # the re-checker's atk_c: edited after generation
        p, _rundir = self.run_job(f, "r_dec")
        lines = p.stdout.strip().splitlines()
        self.assertEqual(lines[-1], "GATE: MISSED (1)", p.stdout[-800:])
        self.assertTrue([ln for ln in lines if "VERDICT (pins): MISSED" in ln and "answer[qc.decisions]" in ln],
                        p.stdout[-800:])
        layer = yamlish.load(self.site / "stack.yml")
        layer["plugins"] = {"prof@scprofile": {"params": {"run": {"allow": "de"}}}}
        yamlish.dump(layer, self.site / "stack.yml")
        rc, text = cli("plan", "--request", str(req))
        self.assertEqual(rc, 2, text)
        self.assertIn("declares plugins.prof@scprofile", text)


TABLE = [  # the wave's table (W049.md), the rows a correct request names and the rule-2 cases
    ("T2", "snrna", ("cellranger-arc", "2.0.2"), ("CellBender", "0.3.0"), "supplied", "plans"),
    ("T4", "snrna", ("cellranger", "8.0.1"), ("SoupX", "1.6.2"), "supplied", "plans"),
    ("T8", "scrna", ("STAR", "2.7.10a"), ("none", None), "raw", "plans"),
    ("T10", "scrna", ("dnbc4tools", "2.1.3"), ("none", None), "raw", "plans"),
    ("T14", "snrna", ("cellranger", "7.1.0"), ("CellBender", "0.3.0"), "anno", "plans"),
    ("S2", "scrna", ("cellranger", "7.1.0"), ("SoupX", "1.6.2"), "supplied", "asks"),
    ("S3", "scrna", ("cellranger", "7.1.0"), ("Cell-Bender v0.3", "0.3.0"), "supplied", "asks"),
    ("S6", "scrna", ("cellranger", "7.1.0"), ("none", None), "anno+cb", "refused"),
    ("S8", "scrna", ("cellranger count + CellBender", None), ("none", None), "raw", "asks"),
    ("S10", "scrna", ("cellranger", "7.1.0"), ("CellBender", "0.3.0"), "anno", "asks"),
]


class WhatRunsUpstreamIsTheToolsAndRule2IsOverIt(M._Base):
    def test_the_table_of_real_requests(self):
        for rid, assay, aln, amb, how, want in TABLE:
            extra = {**PROVENANCE, "ambient_tool": amb[0], "ambient_version": amb[1]} if how == "supplied" else None
            c = cohort(self.tmp / rid, "a", assay=assay, extra=extra)
            st, parts = stages(c), "ambient_h5"
            if how == "raw":
                sheet(c, rename=("ambient_h5", "matrix"))
                parts = "matrix"
            if how.startswith("anno"):
                sheet(c, rename=("ambient_h5", "h5ad"))
                parts, st = "h5ad", st[1:]
                if how == "anno+cb":
                    sheet(c, cols={"ambient_tool": "CellBender"})
            up = {"alignment": {"tool": aln[0], **({"version": aln[1]} if aln[1] else {})},
                  "ambient": {"tool": amb[0], **({"version": amb[1]} if amb[1] else {})}}
            req = request(c, parts=parts, upstream=up, stages=st, **({"context": scrna()} if assay == "scrna" else {}))
            rc, text = cli("plan", "--request", str(req))
            got = "refused" if rc == 2 else "asks" if "the user's: upstream.ambient" in text else "plans"
            with self.subTest(row=rid):
                self.assertEqual(got, want, text[-400:])
        self.assertEqual(self.calls(), [])

    def test_every_first_stage_declares_what_its_tool_accepts_upstream(self):
        prof = yamlish.load(ROOT / "sch" / "profile" / "single-cell.yml")
        steps = prof["upstream"]["steps"]
        self.assertFalse({"allowed", "ask", "never"} & set(prof["upstream"]), "no hand list in the profile")
        for f in sorted((ROOT / "plugins" / "single-cell").glob("*/plugin.yml")):
            m = yamlish.load(f)
            if m.get("reads") != "libraries":
                continue
            for assay in m["assays"]:
                for step in steps:
                    v = m["upstream_accepts"][assay][step]
                    self.assertTrue(v == "any" or isinstance(v, list), (f.parent.name, assay, step, v))
            if not m.get("upstream_columns"):    # a tool that reads no upstream column cannot read a name
                self.assertEqual({v for a in m["upstream_accepts"].values() for v in a.values()}, {"any"}, f)

    def test_the_stand_in_refuses_a_supplied_library_without_its_provenance_as_scqc_does(self):
        c = cohort(self.tmp / "c", "a", extra={"ambient_tool": "CellBender", "ambient_version": "0.3.0"})
        rc, rec = self.drive(request(c), self.tmp / "run", *ANSWERS, "--by", "a tester")
        self.assertEqual((rc, rec["status"], rec["stage"]), (2, "failed", "01_qc"), rec)
        self.assertIn("a SUPPLIED ambient correction is missing params, produced_by", rec["reason"])

    def test_the_manifest_is_the_tools_policy_the_stand_in_and_the_real_scqc(self):
        m = yamlish.load(ROOT / "plugins" / "single-cell" / "qc@scqc" / "plugin.yml")
        entries = m["runs_upstream"]["ambient"]
        self.assertTrue(all(isinstance(e, dict) and "assays" in e for e in entries),
                        f"each param its tool performs a step with names the assays its own policy runs it on: {entries}")
        cb = [e for e in entries if e["param"] == "cellbender"][0]
        spec = importlib.util.spec_from_file_location("fake_scqc_w049", FIXTURES / "fake_scqc.py")
        fake = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fake)
        tools = [("the stand-in", fake.SUPPLIED_REQUIRED, fake.CELLBENDER_RUNS, None, None)]
        real = Path(os.environ.get("SCH_REAL_TOOLS") or "/nonexistent") / "scQC"
        if real.is_dir():                        # the real tool's own code (autodev W049's drift test)
            spec = importlib.util.spec_from_file_location("scqc_ambient_w049", real / "modules" / "01_ambient" / "ambient.py")
            amb = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = amb         # its dataclasses look their module up by name
            spec.loader.exec_module(amb)
            import ast
            tree = ast.parse((real / "engine" / "steps.py").read_text())
            cols = [n for n in ast.walk(tree) if isinstance(n, ast.Assign) and any(
                getattr(t, "id", "") == "NOT_FACTORS" for t in n.targets)][0]
            cols = {e.value for e in ast.walk(cols.value) if isinstance(e, ast.Constant) and isinstance(e.value, str)}
            tools.append(("scQC", amb.SUPPLIED_REQUIRED, amb.CELLBENDER_RUNS, amb, cols))
        for who, required, runs, amb, cols in tools:
            with self.subTest(tool=who):
                self.assertEqual(sorted(cb["assays"]), sorted(a for a, v in runs.items() if v))
                self.assertEqual(set(m["upstream_accepts"]), set(runs))
                self.assertEqual(tuple(required), tuple(fake.SUPPLIED_REQUIRED), "the stand-in is as strict")
                if amb is None:
                    continue
                self.assertEqual(set(amb.ASSAYS), set(m["upstream_accepts"]))
                for assay in amb.ASSAYS:         # any remover's name, supplied with its provenance
                    for name in ("SoupX", "DecontX", "CellBender", "remover_x"):
                        prov = {"tool": name, "version": "1.0", "params": "p", "produced_by": "x"}
                        self.assertEqual(amb.plan_ambient("s", assay, supplied=prov).state, "SUPPLIED")
                        self.assertEqual(m["upstream_accepts"][assay]["ambient"], "any")
                    with self.assertRaises(Exception):
                        amb.plan_ambient("s", assay, supplied={"tool": "SoupX", "version": "1"})
                # no column of scQC's samplesheet names an aligner: it accepts any (alignment: any)
                named = sorted(x for x in cols if x.endswith("_tool"))
                self.assertEqual(named, [m["upstream_columns"]["ambient"]["tool"]], named)
                self.assertEqual({m["upstream_accepts"][a]["alignment"] for a in amb.ASSAYS}, {"any"})


def load_tests(loader, tests, pattern):
    """Only this module's own tests: TheJobPinsEveryRoute inherits the cluster path's set-up, not its tests."""
    suite = unittest.TestSuite()
    for cls in (EveryRouteIsInTheSet, TheJobPinsEveryRoute, WhatRunsUpstreamIsTheToolsAndRule2IsOverIt):
        suite.addTests(cls(n) for n in loader.getTestCaseNames(cls) if n in cls.__dict__)
    return suite


if __name__ == "__main__":
    sys.exit(unittest.main())
