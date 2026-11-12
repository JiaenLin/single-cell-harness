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


if __name__ == "__main__":
    unittest.main()
