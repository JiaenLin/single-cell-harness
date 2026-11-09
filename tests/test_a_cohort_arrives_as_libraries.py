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
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from helpers import HAVE_H5PY, PROTO_HEAD, library_cohort, write_part, write_plugin
from sch.cli import main
from sch.kernel import Stack


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

    def test_the_digest_covers_every_part_and_a_write_to_one_fails_a1(self):
        sheet, _, _ = library_cohort(self.tmp, libraries=3, droplets=20)
        self.assertEqual(self.init(sheet)[0], 0)
        st = Stack.open(self.tmp / "stack")
        before = st.dataset.digest()
        # A plugin that writes to a library: it can find the parts (reads are open, A1), and the
        # write is caught by the digest over every part, not only over the manifest.
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
        r = st.mount(str(self.tmp / "plugins" / "scribbler"))
        self.assertEqual(r.status, "refused", r.reason)
        self.assertIn("A1", r.reason)
        st.close()
        st2 = Stack.open(self.tmp / "stack")
        self.assertNotEqual(st2.dataset.digest(), before)
        st2.close()

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
