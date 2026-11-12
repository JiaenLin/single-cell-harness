"""A RUN DEPENDS ON EXACTLY WHAT IS DECLARED FOR IT (harness autodev W056, wave A of the design read D6).

The files a driven run depends on are the files DECLARED for it - by the request's schema, the site's and each stage
adapter's `files:` (`sch/drive.py` declared(), the one place) - and every other string is text: never resolved, looked
up, opened, pinned or refused for how it looks. THE ONE TEST walks every shipped stage adapter with a hostile text in
every param it forwards that is not declared, in every undeclared samplesheet column and in a text answer, a file of
each text's name planted beside the request and the sheet: the roles of the walk (`run_inputs`) equal the roles of the
declaration, and both equal the roles the adapters' `files:` name, read here from their plugin.yml. A path nested two
files deep through declared readers is followed, pinned and held at a resume.
"""
import ast
import json
import os
import shutil
import unittest
from pathlib import Path

import sch.drive as D
import test_one_request_every_stage as M
from sch import yamlish
from test_one_request_every_stage import cli, cohort, request, stages

ROOT = Path(__file__).resolve().parent.parent
FAMILY = ROOT / "plugins" / "single-cell"
#: Texts a guess took for paths: a label holding slashes, a drawn tree line holding a fraction, a key written like a
#: relative path, an absolute path, a word naming a file beside its document, a home path, a comma list of them.
HOSTILE = ["Immune/Myeloid/Dendritic cell", "│   └── Lymphoid  ■ SEALED   886   8/10",
           "species_x/ref_9", "/etc/hosts", "planted.tsv", "~/.zshrc", "planted.tsv,species_x/ref_9"]
#: The command a flat flag list sits under, in a stage's params.
UNDER = {"int@scintegrate": "integrate", "prof@scprofile": "run"}


def forwarded(adapter: Path) -> list:
    """Every param an adapter's run.py forwards to its tool (FORWARDED, or FLAGS), as the request writes it."""
    for node in ast.parse((adapter / "run.py").read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and {getattr(t, "id", "") for t in node.targets} & {"FORWARDED", "FLAGS"}:
            v = ast.literal_eval(node.value)
            if isinstance(v, dict):
                return [f"{c}.{f}" for c, fs in v.items() for f in fs]
            under = UNDER.get(adapter.name)
            return [f"{under}.{f}" if under else f for f in v]
    raise AssertionError(f"{adapter}: no FORWARDED or FLAGS")


def put(params: dict, path: str, v):
    head, _, rest = path.partition(".")
    if rest:
        params.setdefault(head, {})[rest] = v
    else:
        params[head] = v


class TheSetIsWhatIsDeclared(M._Base):
    def test_the_walk_holds_exactly_the_declared_roles_under_hostile_texts_in_every_other_field(self):
        c = cohort(self.tmp / "c", "a")
        for t in HOSTILE[:3] + ["planted.tsv"]:  # a file of each text's name beside the request and the sheet
            (c["dir"] / t).parent.mkdir(parents=True, exist_ok=True)
            (c["dir"] / t).write_text("planted beside the request\n")
        real = self.tmp / "real"
        real.mkdir()
        st, want = stages(c), {"harness", "request", "observations", "design"}
        for s in st:
            a = FAMILY / s["plugin"]
            m = yamlish.load(a / "plugin.yml")
            files = m["files"]
            skip = {str(x) for x in m.get("owned") or []} | {str(d["param"]) for d in m.get("decisions") or []} | {
                str(x) for k in ("library_key", "replicate_key")
                for x in ([m.get(k)] if isinstance(m.get(k), str) else m.get(k) or [])} | {
                str(x) for x in (m.get("context_params") or {}).values()} | {
                str(e["param"]) for es in (m.get("runs_upstream") or {}).values() for e in es}
            texts = [f for f in forwarded(a) if f not in skip | set(files)]
            self.assertTrue(texts, s["plugin"])
            for n, f in enumerate(texts):        # every text flag a hostile text
                put(s["params"], f, HOSTILE[n % len(HOSTILE)])
            short = s["plugin"].split("@")[0]
            stage = f"{st.index(s) + 1:02d}_{short}"
            for param, e in files.items():
                if param == "observations" or param in skip:   # a decision's param is an answer, never a param
                    continue
                if e["kind"] == "checkout":      # the stand-in already named there
                    want |= {f"{stage}.{param}", f"{stage}.{param}@checkout"}
                    continue
                f = real / f"{short}.{param}"
                f.mkdir() if e["kind"] == "dir" else f.write_text("a declared input\n")
                put(s["params"], param, str(f))
                want.add(f"{stage}.{param}")
        cols = {"label": HOSTILE[0], "tree_line": HOSTILE[1], "reference": HOSTILE[2], "bam": HOSTILE[3],
                "word": HOSTILE[4]}
        mine = yamlish.load(FAMILY / "qc@scqc" / "plugin.yml")["files"]["observations"]["names"]["at"]
        barcodes = real / "barcodes.csv"
        barcodes.write_text("BC00001-1\n")
        cols["cellbender_barcodes"] = str(barcodes)
        rows = (c["dir"] / "samplesheet.tsv").read_text().splitlines()
        libs = [r.split("\t")[0] for r in rows[1:]]
        f = c["dir"] / "samplesheet.tsv"         # read-only as delivered: rewritten as the suite's helper does
        f.chmod(0o644)
        f.write_text("\n".join([rows[0] + "\t" + "\t".join(cols)] + [r + "\t" + "\t".join(cols.values())
                                                                      for r in rows[1:]]) + "\n")
        f.chmod(0o444)
        want |= {f"observations.{col}[{lib}]" for col in ("ambient_h5", "cellbender_barcodes") for lib in libs}
        self.assertIn("cellbender_barcodes", mine)
        dec = real / "decisions.yml"
        dec.write_text("umi_floor: {value: 500}\n")
        answers = {"qc.mode": {"value": HOSTILE[0], "by": "t"}, "qc.decisions": {"value": str(dec), "by": "t"},
                   "prof.control": {"value": [HOSTILE[2], HOSTILE[3]], "by": "t"}}
        want.add("answer[qc.decisions]")
        r = D.load(request(c, stages=st))
        decl = D.declared(r, answers)
        roles = {d["role"] for d in decl if d["check"] != "named"}
        walk = D.run_inputs(r, answers)
        under = {k for k in walk if k not in roles and not any(k.startswith(x + "/") for x in roles)}
        self.assertEqual(under, set(), "a role no declaration names")
        self.assertEqual({k for k in walk if k in roles}, roles, "the walk is the declaration")
        self.assertEqual(roles, want, "the declaration is what the adapters' files: and the request's schema name")
        planted = {str((c["dir"] / t).resolve()) for t in HOSTILE[:3] + ["planted.tsv"]} | {"/etc/hosts"}
        self.assertEqual([k for k, v in walk.items() if os.path.realpath(v.get("path", "")) in planted], [],
                         "no text became a file")
        rc, text = cli("plan", "--request", str(c["dir"] / "request.yml"))
        self.assertEqual(rc, 0, text)

    def test_a_true_path_two_files_deep_is_followed_pinned_and_held_at_a_resume(self):
        """A declared sheet column names a list whose declared column names a file: that file is pinned, its role
        names both columns; edited after stage 1 sealed, the resume is refused naming it. A misspelt column reads 0 of
        n where the plan's check prints it."""
        c = cohort(self.tmp / "c", "a")
        adapter = self.tmp / "qc_nested"
        shutil.copytree(FAMILY / "qc@scqc", adapter, ignore=shutil.ignore_patterns("__pycache__"))
        y = adapter / "plugin.yml"
        t = y.read_text()
        i, j = t.index("  observations:\n"), t.index("ambient_metrics]}\n") + len("ambient_metrics]}\n")
        y.write_text(t[:i] + """  observations:
    names: {format: table, relative_to: none, at: [lists],
            each: {kind: file, names: {format: table, at: [path, pathh], relative_to: file, each: {kind: file}}}}
""" + t[j:])
        deep = self.tmp / "deep" / "inner.tsv"
        deep.parent.mkdir()
        deep.write_text("the file two files deep\n")
        lst = self.tmp / "deep" / "list.tsv"
        lst.write_text("path\tnote\ninner.tsv\tImmune/Myeloid 1/10\n")
        f = c["dir"] / "samplesheet.tsv"
        rows = f.read_text().splitlines()
        f.chmod(0o644)
        f.write_text("\n".join([rows[0] + "\tlists"] + [r + f"\t{lst}" for r in rows[1:]]) + "\n")
        f.chmod(0o444)
        st = stages(c)
        st[0]["plugin"] = str(adapter)
        req, out = request(c, stages=st), self.tmp / "run"
        r = D.load(req)
        walk = D.run_inputs(r, {})
        self.assertEqual(walk["observations.lists[L1]>path[1]"]["path"], str(deep))
        self.assertEqual([k for k in walk if "note" in k], [], "an undeclared column of the list is text")
        rc, rec = self.drive(req, out, *M.ANSWERS, "--by", "a tester")
        self.assertEqual((rc, rec.get("stage")), (3, "04_prof"), rec)
        self.assertTrue((out / "01_qc" / "SEALED.json").is_file())
        deep.write_text("edited after stage 1 sealed\n")
        n = len(self.calls())
        rc, rec = self.drive(req, out, "--answer", M.CONTROL.format(c=c["roles"]["condition"]), "--by", "a tester")
        self.assertEqual((rc, rec["status"]), (2, "refused"), rec)
        self.assertIn("observations.lists[L1]>path[1]", rec["reason"])
        self.assertEqual(len(self.calls()), n, "no tool ran after the edit")
        lines = D._said_declared(r, {}, walk)
        self.assertIn("  read: observations.lists[L1] pathh: 0 of 1 rows name a file (qc@scqc files.observations)", lines)

    def test_a_declaration_and_a_declared_value_are_refused_by_name(self):
        c = cohort(self.tmp / "c", "a")
        adapter = self.tmp / "qc_decl"
        shutil.copytree(FAMILY / "qc@scqc", adapter, ignore=shutil.ignore_patterns("__pycache__"))
        y, orig = adapter / "plugin.yml", (adapter / "plugin.yml").read_text()
        for bad, said in ((orig.replace("files:\n", "files_was:\n", 1), "declares no files:"),
                          (orig.replace("registry: {kind: file}", "registry: {kind: file, chek: present}"),
                           "chek is not a word of a files: entry"),
                          (orig.replace("registry: {kind: file}", "registry: {kind: fiel}"), "kind 'fiel'"),
                          (orig.replace("registry: {kind: file}", "project: {kind: file}"), "sets itself (its owned:)")):
            y.write_text(bad)
            st = stages(c)
            st[0]["plugin"] = str(adapter)
            rc, text = cli("plan", "--request", str(request(c, name="d.yml", stages=st)))
            self.assertEqual(rc, 2, text)
            self.assertIn(said, text)
        y.write_text(orig)
        for param, v, said in (("registry", "registry.tsv", "a relative path"), ("registry", 7, "which is not text"),
                               ("rscript", "../bin/Rscript", "out of its tool's working directory")):
            st = stages(c)
            st[0]["params"][param] = v
            rc, text = cli("plan", "--request", str(request(c, name="v.yml", stages=st)))
            self.assertEqual(rc, 2, text)
            self.assertIn(said, text)
        f = c["dir"] / "samplesheet.tsv"        # a relative cell of a column its tool opens from its own directory
        rows = f.read_text().splitlines()
        f.chmod(0o644)
        f.write_text("\n".join([rows[0] + "\tcellbender_barcodes"] + [r + "\tbarcodes/x.csv" for r in rows[1:]]) + "\n")
        f.chmod(0o444)
        rc, text = cli("plan", "--request", str(request(c, name="cell.yml")))
        self.assertEqual(rc, 2, text)
        self.assertIn("cellbender_barcodes[L1]", text)
        self.assertIn("a relative path", text)

    def test_a_comma_is_one_path_unless_the_entry_declares_a_list(self):
        c = cohort(self.tmp / "c", "a")
        a, b = self.tmp / "one,two.tsv", self.tmp / "two.tsv"
        a.write_text("x\n")
        b.write_text("y\n")
        st = stages(c)
        st[0]["params"]["registry"] = str(a)
        r = D.load(request(c, stages=st))
        self.assertEqual([k for k in D.run_inputs(r, {}) if k.startswith("01_qc.registry")], ["01_qc.registry"])
        st = stages(c)
        st[3]["params"]["run"]["search"] = f"{self.tmp},{self.tmp / 'c'}"
        r = D.load(request(c, name="l.yml", stages=st))
        self.assertEqual(sorted(k for k in D.run_inputs(r, {}) if k.startswith("04_prof.run.search")),
                         ["04_prof.run.search#0", "04_prof.run.search#1"])


class AJobSaysWhatItRuns(M.TheClusterPath):
    """The re-check's F2 (autodev W056 wave A): a job generated with no stated commit for a tool whose checkout has a
    tracked change printed that the checkout was clean, ran and sealed. Decided by the design's rule for `checkout`
    (its commit and its tracked changes, pinned): it runs that change, and its header, its recipe's lines and the
    job's own PINS lines each say so and name the digest; a sentence that says clean is true."""

    # Wave C, change 5: a declared input absent where a job is generated was written in its header as the path it
    # resolved to THERE - the generating machine's cloud folder and its account's name (5 lines of the first cohort's
    # subset job, 1 of its full job). Now each is written as the request, its samplesheet or its document gives it, and
    # the file a relative one is read beside; a path that is only where the job was generated is not written.
    MARKER = "W056MARKERFOLDER"

    def generate(self, home: Path, c: dict, req: Path, name: str) -> str:
        was = os.environ.get("HOME")
        os.environ["HOME"] = str(home)           # the generating machine's home holds the marked folder
        try:
            f, _out = self.job(c, req, name=name, extra=("--where", "~/the/jobs/there"))
        finally:
            if was is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = was
        return f.read_text()

    def test_C5_a_job_generated_in_a_marked_folder_holds_no_word_of_it_and_says_each_input_as_given(self):
        home = self.tmp / "home"
        c = cohort(home / self.MARKER / "c", "a")
        st = stages(c)
        st[1]["params"]["annotate"]["tree"] = "/nonexistent-w056c/refs/tree.json"   # absolute, absent here
        st[3]["params"]["run"]["prefix"] = "~/w056c-prefix"                          # the home's, absent here
        rows = (c["dir"] / "samplesheet.tsv").read_text().splitlines()
        head = rows[0].split("\t")
        lib = rows[1].split("\t")[0]
        # the request's own parts column, read beside the sheet: one cell relative and absent here, the others as written
        cells = ["libs/absent_part.h5ad"] + [r.split("\t")[head.index("ambient_h5")] for r in rows[2:]]
        (c["dir"] / "sheet_relative.tsv").write_text("\n".join([rows[0] + "\tparts_here"] + [
            r + "\t" + x for r, x in zip(rows[1:], cells)]) + "\n")
        req = request(c, stages=st, observations="sheet_relative.tsv", design="absent_design.csv", parts="parts_here")
        text = self.generate(home, c, req, "marked.pbs")
        self.assertEqual([ln for ln in text.splitlines() if self.MARKER in ln], [], "a line naming the marked folder")
        for line in ("design absent_design.csv (beside the request)",
                     f"observations.parts_here[{lib}] libs/absent_part.h5ad (beside the samplesheet)",
                     "02_anno.annotate.tree /nonexistent-w056c/refs/tree.json", "04_prof.run.prefix ~/w056c-prefix"):
            self.assertIn(f"#     on the cluster only: {line}\n", text)
        req = request(c, name="request_sheet_there.yml", stages=st, observations="sheet_on_the_cluster.tsv")
        text = self.generate(home, c, req, "marked_sheet_there.pbs")       # the samplesheet itself on the cluster only
        self.assertEqual([ln for ln in text.splitlines() if self.MARKER in ln], [], "a line naming the marked folder")
        self.assertIn("#     on the cluster only: observations sheet_on_the_cluster.tsv (beside the request)\n", text)

    def test_F2_a_tracked_change_with_no_stated_commit_is_said_with_its_digest_and_clean_only_when_clean(self):
        from test_the_driver_follows_the_tools import commit, git
        c = cohort(self.tmp / "c", "a")
        o = self.tmp / "tools" / "stand-ins"     # the four stand-ins as one checkout of their own
        shutil.copytree(M.FIXTURES, o, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        (o / ".gitignore").write_text("__pycache__/\n*.pyc\n")
        git(o, "init", "-q")
        v1 = commit(o, "v1")
        req = request(c, resources=self.SIZES)
        doc = yamlish.load(req)
        for st, (k, rel) in zip(doc["stages"], (("scqc", "fake_scqc.py"), ("scanno", "fake_scanno.py"),
                                                ("scintegrate", "fake_scintegrate"), ("scprofile", "fake_scprofile"))):
            st["params"][k] = str(o / rel)
        os.chmod(req, 0o644)
        yamlish.dump(doc, req)
        for name in ("clean", "tracked"):
            if name == "tracked":                # WRONG in one respect: a tracked change when generated, no --tool
                (o / "fake_scqc.py").write_text((o / "fake_scqc.py").read_text() + "# a tracked change\n")
            digest = D._git_state(o)["tracked_changes"]
            f, _ = self.job(c, req, name=f"{name}.pbs")
            text = f.read_text()
            head = text.split("# SUBMIT-BEGIN")[0]
            p, rd = self.run_job(f, name)
            self.assertIsNotNone(rd, p.stdout[-800:] + p.stderr[-800:])
            self.assertEqual(p.stdout.strip().splitlines()[-1], "GATE: AS PREDICTED", p.stdout[-1500:])
            pins = (rd / "PINS.txt").read_text()
            rec = [ln.split("\t") for ln in (rd / "CHECKOUTS.tsv").read_text().splitlines()]
            row = next(x for x in rec if x[:2] == ["checkout", "01_qc.scqc@checkout"])
            if name == "clean":
                self.assertEqual(digest, D.CLEAN)
                self.assertIn("ck_made && echo CHECKOUTS-CLEAN", text)
                self.assertNotIn("TRACKED:", text)
                self.assertIn(f"scQC (01_qc): as it is here, at {v1}, clean (no --tool", head)
                self.assertIn("its commit and its work tree, clean, are the submit recipe's record", pins)
                self.assertEqual(row[4], "clean")
            else:
                self.assertNotEqual(digest, D.CLEAN)
                self.assertNotIn("CHECKOUTS-CLEAN", text)
                self.assertIn("ck_made && echo CHECKOUTS-WITH-TRACKED-CHANGES", text)
                self.assertIn(f"TRACKED: 01_qc.scqc@checkout at {v1}, with tracked changes {digest}", text)
                self.assertIn(f"scQC (01_qc): as it is here, at {v1}, with tracked changes {digest} (no --tool", head)
                self.assertIn(f"01_qc.scqc@checkout {o.resolve()} (the site declares no commit file, and this job runs "
                              f"no git where it runs: its commit and its work tree, with tracked changes {digest}, are "
                              f"the submit recipe's record)", pins)
                self.assertEqual(row[4], digest)
                self.assertNotIn(", clean", head.split("scQC (01_qc):")[1].split("\n")[0])


if __name__ == "__main__":
    unittest.main()
