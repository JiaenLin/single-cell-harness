"""A cohort arrives as libraries, never as one file (harness W010, GAP-001).

The kernel took ONE observation file, and no cohort is one: a single-cell experiment is N
libraries, and the profile has always said a barcode is unique only within `{sample}` while the
kernel had no way to say it. A stack may now declare its observations as a PARTS MANIFEST - one
row per library, the scope column being the stack's `{sample}` key, a declared column naming the
file that holds that library's droplets - and for a QC stage that manifest is the tool's own
samplesheet, as delivered.

What must hold, each asserted against the files rather than the kernel's account of them:
  - an identity is `<sample>|<barcode>`, so the same barcode in two libraries is two observations;
  - the digest covers the manifest AND every part, so a write to a library is a write the A1
    companion sees;
  - a manifest that cannot define an observation set is refused at `init`, with the fix, before
    anything is written.
"""
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from helpers import HAVE_H5PY, PROTO_HEAD, library_cohort, write_part, write_plugin
from sch.cli import main
from sch.kernel import Stack
from sch.services.dataset import DatasetError
from sch.services.invariant import InvariantFailure


def cli(*argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(list(argv))
    return rc, buf.getvalue()


@unittest.skipUnless(HAVE_H5PY, "h5py is not available in this interpreter")
class ACohortArrivesAsLibraries(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sch-parts-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def init(self, sheet, *extra, stack="stack"):
        return cli("init", str(self.tmp / stack), "--profile", "single-cell/1.0",
                   "--observations", str(sheet), "--parts", "ambient_h5",
                   "--key", "sample=sample", *extra)

    def test_an_identity_is_a_barcode_within_its_sample(self):
        for delimiter, name in (("\t", "tab"), (",", "comma")):
            with self.subTest(delimiter=name):
                sheet, _, _ = library_cohort(self.tmp / name, libraries=4, droplets=30,
                                             delimiter=delimiter)
                rc, out = self.init(sheet, stack=f"stack_{name}")
                self.assertEqual(rc, 0, out)
                st = Stack.open(self.tmp / f"stack_{name}")
                ids = st.dataset.ids
                # the SAME thirty barcodes in four libraries are 120 observations, not 30
                self.assertEqual(len(ids), 120)
                self.assertEqual(len(set(ids)), 120)
                self.assertIn("L1|BC00000-1", ids)
                self.assertIn("L4|BC00000-1", ids)
                self.assertIn("observations/raw", st.dataset.observation_capabilities())
                self.assertIn("column/sample", st.dataset.observation_capabilities())
                view, _ = st.materialise()
                self.assertEqual(view.path.name, "view.csv")
                self.assertEqual((view.n, view.n_total), (120, 120))
                rows = view.path.read_text().splitlines()
                self.assertEqual(rows[0].split(",")[:3], ["barcode", "sample", "keep"])
                self.assertEqual(rows[1].split(",")[:2], ["L1|BC00000-1", "L1"])
                st.close()

    def test_the_digest_covers_every_part_and_a1_sees_a_write_to_one(self):
        sheet, _, _ = library_cohort(self.tmp, libraries=3, droplets=20)
        self.assertEqual(self.init(sheet)[0], 0)
        st = Stack.open(self.tmp / "stack")
        before = st.dataset.digest()
        part = self.tmp / "objects" / "L2_ambient.h5ad"
        part.chmod(0o644)
        with open(part, "ab") as fh:              # a write that came from outside any plugin
            fh.write(b"\0")
        part.chmod(0o444)
        with self.assertRaises(InvariantFailure):
            st.inv.a1_no_undeclared_write(st.dataset)
        st.close()
        st2 = Stack.open(self.tmp / "stack")
        with self.assertRaises(DatasetError) as caught:   # never a new baseline, silently
            st2.dataset.digest()
        self.assertIn("L2_ambient.h5ad", str(caught.exception))
        st2.close()

    def test_no_plugin_runs_while_an_observation_file_is_writable(self):
        """ARCHITECTURE E2: a plugin cannot mutate the dataset except through a declared
        contribution, enforced by what it is HANDED, not by inspection. A parts stack hands a
        plugin the libraries themselves (they are read in place), so a mount refuses while any of
        them - or the manifest - is writable by the running user, naming the files and the fix.
        Read-only, a plugin that tries to write one fails and the observations are untouched.
        verifier W010 F3: before this, only the after-the-fact digest (A1) stood in the way."""
        sheet, _, _ = library_cohort(self.tmp, libraries=3, droplets=20)
        self.assertEqual(self.init(sheet)[0], 0)
        write_plugin(self.tmp / "plugins", "scribbler",
                     {"profile": "single-cell/1.0", "needs": [], "provides": []},
                     PROTO_HEAD + """
import csv
obs = run.inp["observations"]
lines = [l for l in open(obs["path"]).read().splitlines() if not l.startswith("#")]
first = next(csv.DictReader(lines, delimiter="\\t"))
with open(first[obs["parts"]], "ab") as fh:
    fh.write(b"\\0")
sys.exit(run.finish(headline="wrote to a library"))
""")
        parts = sorted((self.tmp / "objects").glob("*.h5ad"))
        bytes_before = [p.read_bytes() for p in parts]
        parts[1].chmod(0o644)                     # one library left writable
        st = Stack.open(self.tmp / "stack")
        r = st.mount(str(self.tmp / "plugins" / "scribbler"))
        self.assertEqual(r.status, "refused", r.reason)
        self.assertIn(parts[1].name, r.reason)
        self.assertIn("chmod a-w", r.fix)
        self.assertFalse((st.dir / "plugins" / "scribbler").exists(), "the plugin ran")
        st.close()
        parts[1].chmod(0o444)
        self.assertEqual(self.init(sheet, stack="stack_ro")[0], 0)
        st = Stack.open(self.tmp / "stack_ro")
        r = st.mount(str(self.tmp / "plugins" / "scribbler"))
        self.assertEqual(r.status, "died", r.reason)   # its write was refused by the filesystem
        self.assertEqual([p.read_bytes() for p in parts], bytes_before)
        st.inv.a1_no_undeclared_write(st.dataset)
        st.close()

    def test_a_library_changed_by_a_plugin_that_then_dies_is_named_never_rebaselined(self):
        """verifier W010b E2. Read-only files still leave two routes: rename a new file over a
        part through its writable directory, or chmod a part as its owner and write it. A plugin
        that does either and then DIES skipped A1 (which ran only on a completed mount), and the
        next command re-baselined the digest and mounted on the replaced library. Each file is now
        fingerprinted (dev, inode, size, mtime_ns, ctime_ns) at init and re-checked after every
        plugin run, whatever its outcome; a change is an error naming the file, for good."""
        routes = {
            "rename over": """
import shutil
tmp = part + ".new"
shutil.copyfile(part, tmp)
with open(tmp, "ab") as fh:
    fh.write(b"\\0")
os.rename(tmp, part)
sys.exit(3)
""",
            "chmod as owner": """
os.chmod(part, 0o644)
with open(part, "ab") as fh:
    fh.write(b"\\0")
os.chmod(part, 0o444)
sys.exit(3)
""",
        }
        for why, body in routes.items():
            with self.subTest(why):
                d = self.tmp / why.replace(" ", "_")
                sheet, _, _ = library_cohort(d, libraries=2, droplets=10)
                self.assertEqual(self.init(sheet, stack=f"{d.name}_stack")[0], 0)
                write_plugin(d / "plugins", "replacer",
                             {"profile": "single-cell/1.0", "needs": [], "provides": []},
                             PROTO_HEAD + """
import csv
obs = run.inp["observations"]
lines = [l for l in open(obs["path"]).read().splitlines() if not l.startswith("#")]
part = next(csv.DictReader(lines, delimiter="\\t"))[obs["parts"]]
""" + body)
                st = Stack.open(self.tmp / f"{d.name}_stack")
                r = st.mount(str(d / "plugins" / "replacer"))
                st.close()
                self.assertEqual(r.status, "refused", r.reason)    # not "died", and not forgotten
                self.assertIn("A1", r.reason)
                self.assertIn("L1_ambient.h5ad", r.reason)
                rc, out = cli("--json", "materialise", "--stack", str(self.tmp / f"{d.name}_stack"))
                self.assertNotEqual(rc, 0, out)
                self.assertIn("L1_ambient.h5ad", out)

    def test_the_printed_remedy_is_one_a_shell_can_run(self):
        """verifier W010b D3: the `chmod a-w` named in a refusal is shell-quoted, so it works on a
        path with a space - from the mount's refusal and from any other plugin run's."""
        d = self.tmp / "my data"
        sheet, _, _ = library_cohort(d, libraries=2, droplets=10)
        self.assertEqual(self.init(sheet)[0], 0)
        part = d / "objects" / "L2_ambient.h5ad"
        part.chmod(0o644)
        st = Stack.open(self.tmp / "stack")
        r = st.mount("qc@scqc")
        self.assertEqual(r.status, "refused", r.reason)
        sh = subprocess.run(["sh", "-c", r.fix], capture_output=True, text=True)
        self.assertEqual(sh.returncode, 0, sh.stderr)
        self.assertFalse(os.access(part, os.W_OK))
        part.chmod(0o644)
        with self.assertRaises(DatasetError) as caught:
            st.ask("differential", subject={"masks": {}})
        fix = str(caught.exception).split("Delivered data are immutable: ", 1)[1]
        sh = subprocess.run(["sh", "-c", fix], capture_output=True, text=True)
        self.assertEqual(sh.returncode, 0, sh.stderr)
        self.assertFalse(os.access(part, os.W_OK))
        st.close()

    def test_a_library_someone_else_owns_is_given_a_remedy_that_can_work(self):
        """chmod by anyone but a file's owner fails with EPERM, so for such a file the refusal
        names its owner, or a read-only copy, and offers no chmod that cannot run."""
        from unittest import mock
        sheet, _, _ = library_cohort(self.tmp, libraries=2, droplets=10)
        self.assertEqual(self.init(sheet)[0], 0)
        part = self.tmp / "objects" / "L2_ambient.h5ad"
        part.chmod(0o644)
        st = Stack.open(self.tmp / "stack")
        with mock.patch("os.geteuid", return_value=os.geteuid() + 1):   # as another user sees it
            r = st.mount("qc@scqc")
        st.close()
        self.assertEqual(r.status, "refused", r.reason)
        self.assertIn("owned by", r.fix)
        self.assertIn("read-only copy", r.fix)
        self.assertNotIn(f"chmod a-w {part}", r.fix)

    def test_a_plugin_on_one_observation_file_is_handed_only_the_read_only_view(self):
        """The observations' own path is handed out only where a plugin must read parts in place.
        On one file, a plugin gets the read-only view, as before W010."""
        rows = self.tmp / "rows.csv"
        rows.write_text("id,score\nR1,1\nR2,2\n")
        st = Stack.init(self.tmp / "table", "table/1.0", str(rows), keys={"value": "score"})
        write_plugin(self.tmp / "plugins", "looks", {}, PROTO_HEAD + "sys.exit(run.finish())\n")
        r = st.mount(str(self.tmp / "plugins" / "looks"))
        self.assertEqual(r.status, "mounted", r.reason)
        inp = json.loads((st.dir / "plugins" / "looks" / "in.json").read_text())
        self.assertIsNone(inp["observations"])
        self.assertNotIn(str(rows.resolve()), json.dumps(inp))
        st.close()

    def test_a_manifest_that_cannot_define_observations_is_refused_at_init(self):
        sheet, _, _ = library_cohort(self.tmp / "good", libraries=2, droplets=10)
        text = sheet.read_text()
        lines = text.splitlines()
        part = lines[2].split("\t")[5]
        cases = {
            "the same sample twice": text.replace("\tL2\t", "\tL1\t").replace("\nL2\t", "\nL1\t"),
            "a part that does not exist": text.replace(part, part + ".gone"),
            "a sample carrying the joiner": text.replace("\nL2\t", "\nL|2\t"),
            "no parts column": text.replace("ambient_h5", "matrix_h5"),
            "a part no reader exists for": text.replace(part, str(self.tmp / "good")),
        }
        for why, body in cases.items():
            with self.subTest(why):
                bad = self.tmp / f"bad_{len(why)}.tsv"
                bad.write_text(body)
                stack = f"stack_{len(why)}"
                rc, out = self.init(bad, stack=stack)
                self.assertEqual(rc, 2, out)
                self.assertFalse((self.tmp / stack / "stack.yml").exists(),
                                 "a refused init wrote a stack")
        with self.subTest("no scope key"):
            rc, out = cli("init", str(self.tmp / "stack_nokey"), "--profile", "single-cell/1.0",
                          "--observations", str(sheet), "--parts", "ambient_h5")
            self.assertEqual(rc, 2, out)
            self.assertIn("--key sample=", out)
        with self.subTest("a profile with no identity scope"):
            rows = self.tmp / "rows.csv"
            rows.write_text("id,score\nR1,1\n")
            rc, out = cli("init", str(self.tmp / "stack_table"), "--profile", "table/1.0",
                          "--observations", str(rows), "--parts", "score")
            self.assertEqual(rc, 2, out)

    def test_a_single_file_stack_is_unchanged(self):
        """The manifest is opt-in: a stack declaring one observation file reads it as before."""
        part = write_part(self.tmp / "one.h5ad", ["A", "B", "C"])
        st = Stack.init(self.tmp / "single", "single-cell/1.0", str(part), keys={"sample": "s"})
        self.assertEqual(st.dataset.ids, ["A", "B", "C"])
        self.assertNotIn("observation_parts", json.loads(json.dumps(st.decl)))
        st.close()


if __name__ == "__main__":
    unittest.main()
