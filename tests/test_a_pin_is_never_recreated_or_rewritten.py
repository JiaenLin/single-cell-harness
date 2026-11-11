"""A pin is never re-created, and never rewritten (autodev W029, GAP-C58).

A MISSING PIN WAS RE-CREATED SILENTLY. `digest()` pinned whatever it found when there was no pin -
a rule meant for stacks initialised before pins existed - so a plugin that deleted
`observations.pin.json`, replaced a library with one carrying the SAME barcodes and other bytes,
and died, left the next command to pin the replaced library as the delivery, and the next mount
went through (the third verifier of harness W010, probe_swap.py S4). Rewriting the pin over the
replaced library did the same with one more step.

`init` records the pin as an `observations/pinned` event, with its digest. While events.jsonl
holds one, a pin that is missing, or is not the one recorded, is an A1 error - after the plugin
that did it, in the same command, and in every command after. Only a stack with no pin and no such
event (initialised before pins existed) is pinned on its first read, and that is recorded too.
"""
import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from helpers import HAVE_H5PY, PROTO_HEAD, delivery, write_plugin
from sch.cli import main
from sch.kernel import Stack
from sch.services.dataset import DatasetError

PIN, PINNED = "observations.pin.json", "observations/pinned"    # as written since harness W010b


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

#: Replace library L2 with one carrying the SAME barcodes and other bytes - the h5py write the
#: verifier's probe made - as a plugin can through the library's writable directory.
REPLACE = PROTO_HEAD + """
import h5py
obs = run.inp["observations"]
stack = os.path.dirname(os.path.dirname(os.path.dirname(run.inp["out_dir"])))
part = os.path.join(os.path.dirname(obs["path"]), "libs", "L2.h5ad")
tmp = part + ".tmp"
with h5py.File(tmp, "w") as f:
    o = f.create_group("obs"); o.attrs["_index"] = "_index"
    o.create_dataset("_index", data=[("BC%05d-1" % j).encode() for j in range(12)])
    f.create_dataset("TAMPERED", data=[42])
os.chmod(tmp, 0o444); os.replace(tmp, part)
"""


@unittest.skipUnless(HAVE_H5PY, "h5py is not available in this interpreter")
class APinIsNeverRecreatedOrRewritten(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sch-pin-"))
        self.sheet = delivery(self.tmp / "deliv", "v1")
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

    def events(self, stack=None):
        f = (stack or self.stack) / "events.jsonl"
        return [json.loads(ln) for ln in f.read_text().splitlines() if ln.strip()]

    def test_init_records_the_pin_it_writes(self):
        pinned = [e for e in self.events() if e["kind"] == PINNED]
        self.assertEqual(len(pinned), 1)
        pin = json.loads((self.stack / PIN).read_text())
        self.assertEqual(pinned[0]["sha256"], pin["sha256"])
        self.assertEqual(pinned[0]["files"], 4)                   # the manifest and 3 libraries

    def test_a_plugin_that_deletes_the_pin_replaces_a_library_and_dies_is_named(self):
        """The verifier's S4, through the real CLI."""
        write_plugin(self.plugins, "unpinner", {"profile": "single-cell/1.0"}, REPLACE + """
os.unlink(os.path.join(stack, "observations.pin.json"))
os._exit(1)
""")
        rc, out = cli("mount", "--stack", str(self.stack), str(self.plugins / "unpinner"))
        self.assertEqual(out.get("status"), "refused", out)     # A1 after it ran, not "died"
        self.assertIn("A1", out.get("reason") or "")
        self.assertIn(PIN, out.get("reason") or "")
        rc, out = cli("materialise", "--stack", str(self.stack))
        self.assertEqual(rc, 2, out)                            # never re-pinned on the new bytes
        self.assertIn("missing", out.get("reason") or "")
        self.assertFalse((self.stack / PIN).exists(), "a pin was re-created")
        rc, out = cli("mount", "--stack", str(self.stack), str(self.plugins / "good"))
        self.assertNotEqual(out.get("status"), "mounted", out)

    def test_a_pin_rewritten_over_a_replaced_library_is_refused(self):
        """One step further than deleting it: the pin rewritten to match the replaced library -
        its digest and every fingerprint - by a plugin that then dies."""
        write_plugin(self.plugins, "forger", {"profile": "single-cell/1.0"}, REPLACE + """
import hashlib
def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()
pin_path = os.path.join(stack, "observations.pin.json")
pin = json.load(open(pin_path))
files = sorted(pin["files"], key=lambda f: (not f.endswith(".tsv"), f))
h = hashlib.sha256()
for f in files:
    h.update(sha(f).encode()); h.update(b"\\0")
pin["sha256"] = h.hexdigest()
for f in pin["files"]:
    s = os.stat(f)
    pin["files"][f] = {"dev": s.st_dev, "inode": s.st_ino, "size": s.st_size,
                       "mtime_ns": s.st_mtime_ns, "ctime_ns": s.st_ctime_ns}
json.dump(pin, open(pin_path, "w"), indent=1, sort_keys=True)
os._exit(1)
""")
        rc, out = cli("mount", "--stack", str(self.stack), str(self.plugins / "forger"))
        self.assertEqual(out.get("status"), "refused", out)
        self.assertIn("rewritten", out.get("reason") or "")
        rc, out = cli("materialise", "--stack", str(self.stack))
        self.assertEqual(rc, 2, out)
        self.assertIn("rewritten", out.get("reason") or "")
        rc, out = cli("mount", "--stack", str(self.stack), str(self.plugins / "good"))
        self.assertNotEqual(out.get("status"), "mounted", out)

    def test_a_stack_from_before_pins_is_pinned_once_and_then_held(self):
        """The one stack that may be pinned on its first read - no pin and no event, as every
        stack initialised before pins existed - is, once, and the event is written; after that a
        deleted pin is refused like any other."""
        (self.stack / PIN).unlink()
        kept = [ln for ln in (self.stack / "events.jsonl").read_text().splitlines()
                if PINNED not in ln]
        (self.stack / "events.jsonl").write_text("\n".join(kept) + "\n")
        rc, out = cli("materialise", "--stack", str(self.stack))
        self.assertEqual((rc, out.get("total")), (0, 36), out)
        self.assertTrue((self.stack / PIN).exists())
        first = [e for e in self.events() if e["kind"] == PINNED]
        self.assertEqual(len(first), 1)
        self.assertTrue(first[0].get("on_first_read"))
        (self.stack / PIN).unlink()
        rc, out = cli("materialise", "--stack", str(self.stack))
        self.assertEqual(rc, 2, out)
        self.assertIn("missing", out.get("reason") or "")
        self.assertFalse((self.stack / PIN).exists())

    def test_a_fork_holds_the_pin_it_copies(self):
        st = Stack.open(self.stack)
        fork = st.fork(self.tmp / "fork")
        fork.close()
        st.close()
        self.assertEqual([e["sha256"] for e in self.events(self.tmp / "fork") if e["kind"] == PINNED],
                         [json.loads((self.stack / PIN).read_text())["sha256"]])
        (self.tmp / "fork" / PIN).unlink()
        with self.assertRaises(DatasetError) as caught:
            Stack.open(self.tmp / "fork").materialise()
        self.assertIn("missing", str(caught.exception))
        self.assertFalse((self.tmp / "fork" / PIN).exists())

    def test_an_untouched_stack_mounts_as_before(self):
        rc, out = cli("mount", "--stack", str(self.stack), str(self.plugins / "good"))
        self.assertEqual((rc, out.get("status")), (0, "mounted"), out)
        rc, out = cli("materialise", "--stack", str(self.stack))
        self.assertEqual((rc, out.get("kept"), out.get("total")), (0, 33, 36), out)
        self.assertEqual(len([e for e in self.events() if e["kind"] == PINNED]), 1)


if __name__ == "__main__":
    unittest.main()
