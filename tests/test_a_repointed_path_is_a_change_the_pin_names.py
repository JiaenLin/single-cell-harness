"""A path re-pointed after `init` is a change the pin names (autodev W029, GAP-C57).

THE PIN WAS KEYED TO WHAT THE DECLARED PATH RESOLVED TO AT INIT, and never resolved it again. A
stack declared over `deliv/latest/sheet.tsv`, with `latest -> v1`, pinned v1's files; when
`latest` was re-pointed at v2 - an upstream rerun does exactly that, and so does a person - every
pinned file was still unchanged, so `changed()` said nothing, while every command read v2:
  - with a warm view cache, `materialise` died on D6, which names no file;
  - with a cold one it ANSWERED: 41 observations where the stack was pinned on 36, under the pinned
    digest, and a probe counted them;
  - a plugin that re-pointed the link and died left the same state behind it, unnoticed;
  - a one-file stack declared through a file symlink behaved the same way.
Measured by the third verifier of harness W010 (scratch verify_W010c/, probe_swap.py). The path is
now resolved again at every check, and a file read but not pinned is an A1 error naming it.
"""
import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from helpers import HAVE_H5PY, PROTO_HEAD, delivery, repoint, write_plugin
from sch.cli import main
from sch.kernel import Stack
from sch.plugin.test import table_fixture
from sch.services.dataset import DatasetError


def cli(*argv):
    """(exit, parsed --json output). An exception escaping the command is a failure of the test,
    said as one, not a traceback that hides which command raised it."""
    buf, err = io.StringIO(), io.StringIO()
    try:
        with redirect_stdout(buf), redirect_stderr(err):
            rc = main(["--json", *argv])
    except Exception as e:                                  # noqa: BLE001
        return f"EXC {type(e).__name__}: {e}", {}
    try:
        return rc, json.loads(buf.getvalue())
    except ValueError:
        return rc, {"unparsed": buf.getvalue()}


GOOD = PROTO_HEAD + """
import csv
idc = run.inp["identity"]["column"]
ids = [r[idc] for r in csv.DictReader(open(run.data))]
run.mask("floor", {i: not i.endswith("00011-1") for i in ids}, reason="a test floor", id_field=idc)
sys.exit(run.finish(headline="masked"))
"""

COUNT = PROTO_HEAD + """
import csv
run.answer(observations_seen=sum(1 for _ in csv.DictReader(open(run.data))))
sys.exit(run.finish(headline="counted"))
"""


@unittest.skipUnless(HAVE_H5PY, "h5py is not available in this interpreter")
class ARepointedPathIsAChangeThePinNames(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sch-repoint-"))
        self.deliv = self.tmp / "deliv"
        delivery(self.deliv, "v1")                            # 3 libraries x 12 = 36
        delivery(self.deliv, "v2", extra={0: [f"NEW{j:04d}-1" for j in range(5)]})   # 41
        os.symlink("v1", self.deliv / "latest")
        self.stack = self.tmp / "stack"
        rc, out = cli("init", str(self.stack), "--profile", "single-cell/1.0", "--observations",
                      str(self.deliv / "latest" / "sheet.tsv"), "--parts", "ambient_h5",
                      "--key", "sample=sample", "--context", "assay=snrna")
        self.assertEqual(rc, 0, out)
        self.v2 = str((self.deliv / "v2" / "sheet.tsv").resolve())
        self.plugins = self.tmp / "plugins"
        write_plugin(self.plugins, "good", {"profile": "single-cell/1.0",
                                            "provides": ["mask/floor"]}, GOOD)
        write_plugin(self.plugins, "counter", {"profile": "single-cell/1.0", "class": "probe"},
                     COUNT)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def assertNamed(self, rc, out):
        """Refused, by A1, naming the file the path now resolves to."""
        self.assertEqual(rc, 2, out)
        reason = out.get("reason") or ""
        self.assertIn("A1", reason)
        self.assertIn(self.v2, reason)
        self.assertNotIn("D6", reason)

    def test_changed_names_the_file_the_path_now_resolves_to(self):
        st = Stack.open(self.stack)               # nothing mounted, so opening reads nothing
        self.assertEqual(st.dataset.changed(), [])
        st.close()
        repoint(self.deliv / "latest", "v2")
        st = Stack.open(self.stack)
        found = st.dataset.changed()
        st.close()
        self.assertTrue(any(self.v2 in line and "not pinned" in line for line in found), found)

    def test_a_warm_view_is_refused_by_a1_naming_the_file_not_by_d6(self):
        rc, out = cli("materialise", "--stack", str(self.stack))
        self.assertEqual((rc, out.get("total")), (0, 36), out)
        repoint(self.deliv / "latest", "v2")
        self.assertNamed(*cli("materialise", "--stack", str(self.stack)))
        rc, out = cli("mount", "--stack", str(self.stack), str(self.plugins / "good"))
        self.assertEqual(out.get("status"), "refused", out)
        self.assertIn(self.v2, out.get("reason") or "")

    def test_a_cold_view_and_a_probe_are_refused_and_never_answer_on_the_new_files(self):
        repoint(self.deliv / "latest", "v2")
        self.assertNamed(*cli("materialise", "--stack", str(self.stack)))
        rc, out = cli("ask", "--stack", str(self.stack), str(self.plugins / "counter"))
        self.assertEqual(rc, 2, out)
        self.assertNotIn("observations_seen", json.dumps(out))
        self.assertIn(self.v2, out.get("reason") or "")

    def test_a_plugin_that_repoints_the_path_and_dies_is_named_after_it_runs(self):
        write_plugin(self.plugins, "repointer", {"profile": "single-cell/1.0"}, PROTO_HEAD + f"""
link = {str(self.deliv / "latest")!r}
os.symlink("v2", link + ".new"); os.replace(link + ".new", link)
os._exit(1)
""")
        rc, out = cli("mount", "--stack", str(self.stack), str(self.plugins / "repointer"))
        self.assertEqual(out.get("status"), "refused", out)        # A1, not a forgotten death
        self.assertIn("A1", out.get("reason") or "")
        self.assertIn(self.v2, out.get("reason") or "")
        self.assertNamed(*cli("materialise", "--stack", str(self.stack)))

    def test_pointed_back_the_stack_reads_what_it_was_pinned_on(self):
        repoint(self.deliv / "latest", "v2")
        self.assertNamed(*cli("materialise", "--stack", str(self.stack)))
        repoint(self.deliv / "latest", "v1")
        rc, out = cli("materialise", "--stack", str(self.stack))
        self.assertEqual((rc, out.get("total")), (0, 36), out)


class AOneFileStackThroughASymlinkIsHeldTheSameWay(unittest.TestCase):
    def test_a_repointed_file_symlink_is_named(self):
        tmp = Path(tempfile.mkdtemp(prefix="sch-repoint1-"))
        try:
            rows, design = table_fixture(tmp, n=40)
            v1, v2 = tmp / "rows_v1.csv", tmp / "rows_v2.csv"
            shutil.copyfile(rows, v1)
            lines = Path(rows).read_text().splitlines()
            v2.write_text("\n".join(lines + ["R9999" + lines[-1][lines[-1].index(","):]]) + "\n")
            os.symlink(v1.name, tmp / "rows_link.csv")
            Stack.init(tmp / "stack", "table/1.0", str(tmp / "rows_link.csv"), str(design),
                       keys={"value": "score", "group": "arm", "unit": "unit"}).close()
            rc, out = cli("materialise", "--stack", str(tmp / "stack"))
            self.assertEqual((rc, out.get("total")), (0, 40), out)
            repoint(tmp / "rows_link.csv", v2.name)
            rc, out = cli("materialise", "--stack", str(tmp / "stack"))
            self.assertEqual(rc, 2, out)
            self.assertIn("A1", out.get("reason") or "")
            self.assertIn(str(v2.resolve()), out.get("reason") or "")
            with self.assertRaises(DatasetError):
                Stack.open(tmp / "stack").materialise()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
