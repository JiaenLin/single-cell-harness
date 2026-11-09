"""The pin is checked before a part is read, and its refusals say what to do (autodev W029, GAP-C60).

Three residuals of harness W010, measured by its third verifier (scratch verify_W010c/,
probe_e2.py):
  - `Stack()` READ THE PARTS BEFORE THE PIN WAS CHECKED. Opening a stack with a plugin mounted
    restores its contributions, and that read every library's identities through h5py. A library
    corrupted in place, with its size and mtime restored, made `sch stack`, `plan`, `unmount
    --dry-run` and `materialise` raise h5py's own OSError ("bad heap index") - a traceback that
    names no file - instead of the A1 error naming the library;
  - A HARD LINK moves a file's ctime and nothing else, and the pin compares ctime: a stack whose
    library was hard-linked (a `cp -al` tree is hard links) is refused for good, and nothing said
    why or what to do;
  - THE `chmod a-w` REMEDY for a library made writable after `init` did not say that the chmod
    leaves the stack refused - it moved the ctime too - so a new `init` is needed.
"""
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from helpers import HAVE_H5PY, PROTO_HEAD, delivery, write_plugin
from sch.cli import main
from sch.kernel import Stack


def cli(*argv):
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


@unittest.skipUnless(HAVE_H5PY, "h5py is not available in this interpreter")
class ThePinIsCheckedBeforeAPartIsRead(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sch-pinread-"))
        self.sheet = delivery(self.tmp / "deliv", "v1")
        self.part = self.tmp / "deliv" / "v1" / "libs" / "L2.h5ad"
        self.stack = self.tmp / "stack"
        rc, out = cli("init", str(self.stack), "--profile", "single-cell/1.0", "--observations",
                      str(self.sheet), "--parts", "ambient_h5", "--key", "sample=sample",
                      "--context", "assay=snrna")
        self.assertEqual(rc, 0, out)
        self.plugins = self.tmp / "plugins"
        write_plugin(self.plugins, "good", {"profile": "single-cell/1.0",
                                            "provides": ["mask/floor"]}, GOOD)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def corrupt_in_place(self):
        """The owner's rewrite the pin exists for: one byte flipped inside the library's HDF5
        heap, at the same size, with its mode and mtime put back."""
        st0 = os.stat(self.part)
        self.part.chmod(0o644)
        data = bytearray(self.part.read_bytes())
        data[-1] ^= 0xFF
        with open(self.part, "r+b") as fh:
            fh.write(bytes(data))
        self.part.chmod(0o444)
        os.utime(self.part, ns=(st0.st_atime_ns, st0.st_mtime_ns))
        st1 = os.stat(self.part)
        self.assertEqual((st1.st_size, st1.st_mtime_ns), (st0.st_size, st0.st_mtime_ns))

    def test_a_library_corrupted_in_place_is_named_by_a1_before_h5py_reads_it(self):
        rc, out = cli("mount", "--stack", str(self.stack), str(self.plugins / "good"))
        self.assertEqual(out.get("status"), "mounted", out)
        self.corrupt_in_place()
        for argv in (["stack"], ["plan", str(self.plugins / "good"), "--name", "again"],
                     ["unmount", "good", "--dry-run"], ["materialise"]):
            with self.subTest(argv[0]):
                rc, out = cli(argv[0], "--stack", str(self.stack), *argv[1:])
                self.assertEqual(rc, 2, out)                   # an error said, not a traceback
                reason = out.get("reason") or ""
                self.assertIn("A1", reason)
                self.assertIn(str(self.part.resolve()), reason)

    def test_a_hard_link_is_a_ctime_change_the_refusal_explains(self):
        os.link(self.part, self.tmp / "a_hard_link.h5ad")          # changes no byte of it
        rc, out = cli("materialise", "--stack", str(self.stack))
        self.assertEqual(rc, 2, out)
        reason = out.get("reason") or ""
        self.assertIn("ctime", reason)
        self.assertIn("hard link", reason)
        self.assertIn("initialise a new stack over the same files", reason)
        rc, out = cli("plan", "--stack", str(self.stack), str(self.plugins / "good"))
        self.assertEqual(rc, 2, out)
        self.assertIn("initialise a new stack over the same files", out.get("fix") or "")

    def test_the_chmod_remedy_says_a_new_init_must_follow_and_still_runs_in_a_shell(self):
        self.part.chmod(0o644)                         # writable after init: ctime moved
        rc, out = cli("mount", "--stack", str(self.stack), str(self.plugins / "good"))
        self.assertEqual(out.get("status"), "refused", out)
        fix = out.get("fix") or ""
        self.assertIn("chmod a-w", fix)
        self.assertIn("initialise a new stack", fix)
        sh = subprocess.run(["sh", "-c", fix], capture_output=True, text=True)
        self.assertEqual(sh.returncode, 0, sh.stderr)
        self.assertFalse(os.access(self.part, os.W_OK))
        # read-only again, the stack is still refused - by A1, with the same remedy - as it said
        rc, out = cli("mount", "--stack", str(self.stack), str(self.plugins / "good"))
        self.assertEqual(out.get("status"), "refused", out)
        self.assertIn("ctime", out.get("reason") or "")
        # and a new init over the very same files mounts
        rc, out = cli("init", str(self.tmp / "stack2"), "--profile", "single-cell/1.0",
                      "--observations", str(self.sheet), "--parts", "ambient_h5",
                      "--key", "sample=sample", "--context", "assay=snrna")
        self.assertEqual(rc, 0, out)
        rc, out = cli("mount", "--stack", str(self.tmp / "stack2"), str(self.plugins / "good"))
        self.assertEqual(out.get("status"), "mounted", out)

    def test_opening_a_stack_whose_library_changed_says_which(self):
        rc, out = cli("mount", "--stack", str(self.stack), str(self.plugins / "good"))
        self.assertEqual(out.get("status"), "mounted", out)
        self.corrupt_in_place()
        from sch.services.dataset import DatasetError
        with self.assertRaises(DatasetError) as caught:
            Stack.open(self.stack)
        self.assertIn(str(self.part.resolve()), str(caught.exception))


if __name__ == "__main__":
    unittest.main()
