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
import shutil
import subprocess
import sys
import time
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
            # W049 fix 1: THE COLUMNS scQC's OWN PLANNER READS (engine/graph.py main_stage, which builds each
            # supplied library's provenance from its row and hands it to plan_ambient) - not a list beside it
            plan = [n for n in ast.walk(ast.parse((real / "engine" / "graph.py").read_text()))
                    if isinstance(n, ast.FunctionDef) and n.name == "main_stage"]
            self.assertEqual(len(plan), 1, "scQC's planner (engine/graph.py main_stage) moved: follow it")

            def got(node):                       # each `<row>.get("<column>")` under `node`
                return [x.args[0].value for x in ast.walk(node) if isinstance(x, ast.Call) and getattr(
                    x.func, "attr", "") == "get" and x.args and isinstance(x.args[0], ast.Constant)
                    and isinstance(x.args[0].value, str)]
            prov = [n for n in ast.walk(plan[0]) if isinstance(n, ast.Dict) and {"tool", "version"} <= {
                getattr(k, "value", None) for k in n.keys}]
            self.assertEqual(len(prov), 1, "the supplied library's provenance, as scQC's planner builds it")
            up = m["upstream_columns"]["ambient"]
            read = {k.value: got(v) for k, v in zip(prov[0].keys, prov[0].values) if isinstance(k, ast.Constant)}
            self.assertEqual((read["tool"], read["version"]), ([up["tool"]], [up["version"]]), read)
            self.assertLessEqual({x for v in read.values() for x in v}, {up["tool"], up["version"], *up["performed"]})
            self.assertLessEqual({up["tool"], up["version"], *up["performed"], *up["declined"]}, set(got(plan[0])),
                                 "every upstream column the adapter declares is one scQC's planner reads")
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


def git(d, *a) -> str:
    return subprocess.run(["git", "-C", str(d), *a], capture_output=True, text=True, check=True).stdout.strip()


def commit(d, msg) -> str:
    git(d, "add", "-A")
    git(d, "-c", "user.email=t", "-c", "user.name=t", "commit", "-qm", msg)
    return git(d, "rev-parse", "HEAD")


class TheRunsRecordIsItsStagesSeals(M._Base):
    """W049 fix 1, the reason the driver batch's verification failed (ATTACKS 13, 21, 32): what a run's record
    says a stage was given is what that stage's own seal says - on every resume and at the run's seal."""

    def waiting(self, c, out):
        req = request(c)
        rc, rec = self.drive(req, out, *ANSWERS, "--by", "a tester")
        self.assertEqual((rc, rec["status"], rec["stage"]), (3, "waiting", "04_prof"), rec)
        return req

    def test_an_answer_to_a_sealed_stage_is_refused_before_anything_runs_and_the_seal_says_it_agrees(self):
        c, out = cohort(self.tmp / "c", "a"), self.tmp / "run"
        req = self.waiting(c, out)               # the verifier's late.py: 02_anno sealed, 04_prof waiting
        before, n = (out / "decisions.json").read_bytes(), len(self.calls())
        rc, rec = self.drive(req, out, *ctrl(c)[:2], "--answer", "anno.no_exclude=true", "--by", "a tester")
        self.assertEqual((rc, rec["status"]), (2, "refused"), rec)          # was: 0, sealed, the escape recorded
        self.assertIn("--answer anno.no_exclude: 02_anno is sealed, and its tool ran without this answer",
                      rec["reason"])
        self.assertIn("start a new --out", rec["reason"])
        self.assertEqual((len(self.calls()), (out / "decisions.json").read_bytes()), (n, before), "nothing ran")
        rc, text = cli("run", "--request", str(req), "--out", str(out), *ctrl(c))
        self.assertEqual(rc, 0, text)
        self.assertIn("  agreed: the run's decisions, who answered them and the params each tool was handed are "
                      "each stage's own seal (4 stages, 3 answers)", text)
        top = json.loads((out / "SEALED.json").read_text())
        for s in top["sealed"]:
            seal = json.loads((out / s / "SEALED.json").read_text())
            self.assertEqual({k: top["decisions"].get(k) for k in seal["decisions"]}, seal["decisions"], s)
        self.assertNotIn("anno.no_exclude", top["decisions"])

    def test_a_recorded_answer_given_again_by_another_name_is_refused(self):
        c = cohort(self.tmp / "c", "a")
        req = self.waiting(c, self.tmp / "by")   # whose name is recorded for an answer given earlier?
        rc, rec = self.drive(req, self.tmp / "by", "--answer", "qc.mode=apply", *ctrl(c)[:2], "--by", "someone else")
        self.assertEqual((rc, rec["status"]), (2, "refused"), rec)          # was: sealed, the first name kept
        self.assertIn('qc.mode is recorded "apply" by a tester, and given again by someone else', rec["reason"])

    def test_one_decision_answered_twice_in_one_command_is_refused_as_such(self):
        c = cohort(self.tmp / "c", "a")          # was: refused as "already answered", a record that is not
        rc, rec = self.drive(request(c), self.tmp / "twice", "--answer", "qc.mode=apply", "--answer",
                             "qc.mode=draft", "--answer", "qc.decisions=null", "--by", "a tester")
        self.assertEqual((rc, rec["status"]), (2, "refused"), rec)
        self.assertIn('--answer qc.mode is given twice in one command ("apply" and "draft")', rec["reason"])

    def test_an_answer_removed_with_its_record_rewritten_is_refused_by_the_sealed_stages_own_record(self):
        c = cohort(self.tmp / "c", "a")
        out = self.tmp / "removed"               # the record and its hash rewritten together (ATTACKS 13)
        req = self.waiting(c, out)
        d = json.loads((out / "decisions.json").read_text())
        del d["qc.mode"]
        (out / "decisions.json").write_text(json.dumps(d, indent=1) + "\n")
        led = json.loads((out / "INPUTS.json").read_text())
        led["decisions_sha256"] = M.sha(out / "decisions.json")
        (out / "INPUTS.json").write_text(json.dumps(led, indent=1) + "\n")
        n = len(self.calls())
        rc, rec = self.drive(req, out, *ctrl(c))
        self.assertEqual((rc, rec["status"]), (2, "refused"), rec)          # was: sealed without it
        self.assertIn("the run's record and 01_qc's seal disagree: qc.mode: not given in the run's record, "
                      "\"apply\" by a tester in 01_qc's seal", rec["reason"])
        self.assertEqual(len(self.calls()), n, "refused before 04_prof ran")

    def test_the_runs_seal_refuses_a_record_its_stages_seals_do_not_hold(self):
        from unittest import mock
        import sch.drive as D
        c, out = cohort(self.tmp / "c", "a"), self.tmp / "run"
        req = self.waiting(c, out)
        with mock.patch.object(D, "_late", lambda *a, **k: None, create=True):   # (i) taken away: (ii) alone
            rc, rec = self.drive(req, out, *ctrl(c)[:2], "--answer", "anno.no_exclude=true", "--by", "a tester")
        self.assertEqual((rc, rec["status"], rec.get("stage")), (2, "failed", "02_anno"), rec)
        self.assertIn("the run is not sealed: its record and 02_anno's seal disagree: anno.no_exclude: true by a "
                      "tester in the run's record, not given in 02_anno's seal", rec["reason"])
        self.assertFalse((out / "SEALED.json").exists())

    def test_a_name_of_characters_that_print_as_nothing_is_no_name(self):
        c = cohort(self.tmp / "c", "a")
        req = request(c)
        rc, rec = self.drive(req, self.tmp / "r", *ANSWERS, "--by", "​")
        self.assertEqual((rc, rec["status"]), (2, "refused"), rec)          # was: accepted, recorded by U+200B
        self.assertIn("is no name", rec["reason"])
        self.assertEqual(self.calls(), [])
        for by in ("​‍", "ㅤ", "﻿", "⁠", "­", " ‌ "):
            rc, text = cli("plan", "--request", str(req), *ANSWERS, "--by", by)
            self.assertEqual(rc, 2, (by, text))
        for by in ("a tester", "李雷", "José", "O'Brien", "PI-1"):   # a name that prints is one
            rc, text = cli("plan", "--request", str(req), *ANSWERS, "--by", by)
            self.assertEqual(rc, 0, (by, text))

    def test_a_link_to_a_large_directory_gives_up_that_link_alone(self):
        from unittest import mock
        import sch.drive as D
        c = cohort(self.tmp / "c", "a")
        big, named = self.tmp / "big", self.tmp / "named"
        big.mkdir()
        named.mkdir()
        for i in range(5):
            (big / f"f{i}.txt").write_text(f"{i}\n")
        (named / "own.txt").write_text("own\n")
        os.symlink(big, named / "big")
        st = stages(c)
        st[3]["params"]["run"]["prefix"] = str(named)
        r = D.load(request(c, stages=st))
        with mock.patch.object(D, "TREE_LIMIT", 3):
            s = D.run_inputs(r, {})
            self.assertTrue(s.get("04_prof.run.prefix/own.txt", {}).get("sha256"), "its own files are compared")
            self.assertIn("this link alone", s["04_prof.run.prefix/big"]["unpinned"])
            before = D.flat(s)
            (named / "own.txt").write_text("edited\n")
            d = [k for k, _a, _b in D.differ(before, D.flat(D.run_inputs(r, {})))]
        self.assertEqual(d, ["04_prof.run.prefix/own.txt"])


class AJobStatesTheToolsItExpects(M.TheClusterPath):
    """W049 fix 1, the gap blocking the cohort gate (ATTACKS 33): a job states which commit of each tool it
    expects (`--tool`), and its pins check the checkout WHERE IT RUNS against that, never against the
    checkout of the machine it was generated on; a checkout absent where it is named is recorded absent."""

    def origin(self):
        """scQC's stand-in as a checkout of its own: v0 (older code), v1, and a docs-only commit after it."""
        o = self.tmp / "origin" / "scQC"
        o.mkdir(parents=True)
        (o / "fake_scqc.py").write_text((FIXTURES / "fake_scqc.py").read_text() + "# an older version\n")
        git(o, "init", "-q")
        v0 = commit(o, "v0")
        shutil.copy(FIXTURES / "fake_scqc.py", o / "fake_scqc.py")
        v1 = commit(o, "v1")
        (o / "NOTES.md").write_text("docs only\n")
        return o, v0, v1, commit(o, "v2: docs only")

    def at(self, c, tool):
        req = request(c, resources=self.SIZES)
        doc = yamlish.load(req)
        doc["stages"][0]["params"]["scqc"] = str(tool / "fake_scqc.py")
        os.chmod(req, 0o644)
        yamlish.dump(doc, req)
        return req

    def check(self, f, req, c):
        """The job's own pins check, as its body runs it: `sch plan --request ... <answers> --expect PINS`."""
        pins = self.tmp / f"{f.stem}.PINS.json"
        pins.write_text(f.read_text().split("<<'SCH_PINS_END'\n")[1].split("\nSCH_PINS_END")[0])
        return cli("plan", "--request", str(req), *M.answered(c), "--expect", str(pins))

    def test_a_job_made_where_a_tool_is_absent_checks_it_where_it_runs(self):
        c = cohort(self.tmp / "c", "a")
        o, _v0, _v1, _v2 = self.origin()
        tool = self.tmp / "tools" / "scQC"       # absent where the job is generated
        req = self.at(c, tool)
        f, _ = self.job(c, req)
        git(self.tmp, "clone", "-q", str(o), str(tool))       # the checkout where the job runs
        rc, text = self.check(f, req, c)
        self.assertEqual(rc, 0, text)            # was: differs, 01_qc.scqc@checkout not named when generated
        self.assertIn("  only here: 01_qc.scqc@checkout", text)
        self.assertIn("#   tool      scQC (01_qc): absent here and not stated (--tool)", f.read_text())

    def test_a_job_states_the_commit_it_expects_and_checks_the_checkout_where_it_runs_against_it(self):
        c = cohort(self.tmp / "c", "a")
        o, v0, v1, v2 = self.origin()
        tool = self.tmp / "tools" / "scQC"
        req = self.at(c, tool)
        absent, _ = self.job(c, req, name="absent.pbs", extra=("--tool", f"scQC={v1}"))
        git(self.tmp, "clone", "-q", str(o), str(tool))
        git(tool, "checkout", "-q", "--detach", v0)           # here: older code than the commit stated
        other, _ = self.job(c, req, name="other.pbs", extra=("--tool", f"scQC={v1}"))
        self.assertIn(f"#   tool      scQC (01_qc): expects {v1}, clean (--tool", other.read_text())
        git(tool, "checkout", "-q", "--detach", v1)           # where the job runs: at the commit it states
        for f in (absent, other):
            rc, text = self.check(f, req, c)
            self.assertEqual(rc, 0, text)
            self.assertIn(f"  tool: scQC at {v1}, clean, as this job states (01_qc.scqc@checkout ", text)
        p, rundir = self.run_job(absent, "r_held")
        self.assertEqual(p.stdout.strip().splitlines()[-1], "GATE: AS PREDICTED", p.stdout[-1500:])
        self.assertIn(f"  tool: scQC at {v1}, clean, as this job states", p.stdout)
        self.assertIn("VERDICT (drive): SEALED - 4 stages", p.stdout)
        self.assertIn("  agreed: the run's decisions", (rundir / "DRIVE.log").read_text())

        def missed(here):                        # anything else where it runs: MISSED, naming the tool
            rc, text = self.check(other, req, c)
            self.assertEqual(rc, 2, text)
            self.assertIn("  differs: 01_qc.scqc@checkout ", text)
            self.assertIn(f"(scQC: this job expects {v1}, clean; here {here})", text)
        git(tool, "checkout", "-q", "--detach", v2)
        missed(f"at {v2}, clean")
        git(tool, "checkout", "-q", "--detach", v1)
        (tool / "fake_scqc.py").write_text((tool / "fake_scqc.py").read_text() + "# edited\n")
        missed(f"at {v1}, with tracked changes")
        git(tool, "update-index", "--assume-unchanged", "fake_scqc.py")     # ATTACKS 22: git told not to look
        missed(f"at {v1}, with tracked changes")
        git(tool, "update-index", "--no-assume-unchanged", "fake_scqc.py")
        git(tool, "checkout", "-q", "--", "fake_scqc.py")               # ATTACKS 22: a stat cache trusted
        git(tool, "config", "core.trustctime", "false")                  # less by the checkout's own config,
        git(tool, "config", "core.checkStat", "minimal")                 # and an edit keeping size and mtime
        time.sleep(1.1)
        git(tool, "update-index", "--refresh")
        f = tool / "fake_scqc.py"
        st, text = f.stat(), f.read_text()
        f.write_text(text.replace("import", "imporT", 1))
        os.utime(f, ns=(st.st_atime_ns, st.st_mtime_ns))
        self.assertEqual(git(tool, "status", "--porcelain"), "", "git itself is told to see nothing")
        missed(f"at {v1}, with tracked changes")
        f.write_text(text + "# edited\n")
        git(tool, "replace", v1, commit(tool, "v3: edited"))              # ATTACKS 22: v1 read as another
        git(tool, "checkout", "-q", "--detach", v1)
        missed(f"at {v1}, with tracked changes")

    def test_a_tool_no_stage_runs_a_commit_that_is_not_one_or_one_tool_twice_is_refused(self):
        c = cohort(self.tmp / "c", "a")
        req = request(c, resources=self.SIZES)
        f, _ = self.job(c, req)
        h = "a" * 40
        for bad, why in ((["--tool", f"scqc={h}"], "no stage of this request runs a tool named 'scqc'"),
                         (["--tool", f"scQC={h[:12]}"], "40 hexadecimal digits"),
                         (["--tool", f"scQC={h.upper()}"], "40 hexadecimal digits"),
                         (["--tool", f"scQC={h} "], "40 hexadecimal digits"),
                         (["--tool", "scQC=main"], "40 hexadecimal digits"),
                         (["--tool", f"scQC={h}", "--tool", f"scQC={'b' * 40}"], "given twice")):
            g = f.parent / "bad.pbs"
            rc, text = cli("--json", "run", "--request", str(req), "--job", str(g), *M.answered(c), *bad)
            self.assertEqual(rc, 2, text)
            self.assertIn(why, json.loads(text)["reason"])
            self.assertFalse(g.exists())
        with self.assertRaises(SystemExit):
            cli("run", "--request", str(req), "--out", str(self.tmp / "r"), "--tool", f"scQC={h}")


def load_tests(loader, tests, pattern):
    """Only this module's own tests: TheJobPinsEveryRoute inherits the cluster path's set-up, not its tests."""
    suite = unittest.TestSuite()
    for cls in (EveryRouteIsInTheSet, TheJobPinsEveryRoute, WhatRunsUpstreamIsTheToolsAndRule2IsOverIt,
                TheRunsRecordIsItsStagesSeals, AJobStatesTheToolsItExpects):
        suite.addTests(cls(n) for n in loader.getTestCaseNames(cls) if n in cls.__dict__)
    return suite


if __name__ == "__main__":
    sys.exit(unittest.main())
