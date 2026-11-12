"""A layer is what its mount recorded (harness W052 fix 1; ATTACKS 21, 22, 26).

A reopened stack rebuilt each runtime from the plugin.yml its mount named, as that file is NOW, and
folded, keyed and showed the view under the declared numbers. So a layer computed at state_version 1
was served as 2 once the plugin's checkout moved (a pull, a checkout, an edit), and nothing refused
it: `sch materialise` exited 0 with the old digest, `sch stack` said 2, and a new materialised key
for 2 held the old layer. Here the plugin.yml is rewritten between a mount and the next command, as a
move does, and every command that reads the layer refuses by name (the plugin, both numbers, what
to do), `sch stack` and `sch doctor --runtime` show the difference, and `sch unmount` stays the way
out. A stack nobody changed, one whose plugin.yml changed only in a doc field, and one copied to
another folder are served as before (ATTACKS 10).
"""
import io
import json
import os
import re
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from helpers import FIXTURES, HAVE_H5PY, PLUGINS, PROTO_HEAD, fresh_stack, library_cohort, write_plugin
from sch.cli import main

COLUMN = PROTO_HEAD + '''
idc = run.inp.get("identity", {}).get("column", "id")
rows = run.read_csv(run.data)
run.column("NAME", {r[idc]: str(len(r[idc]) + LEN) for r in rows}, id_field=idc)
run.finish("NAME written")
'''


def cli(*argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(list(argv))
    return rc, buf.getvalue()


def declare(plugin_dir: Path, **fields):
    """Rewrite plugin.yml's top-level `key: value` lines in place, as a pull or a checkout does."""
    y = plugin_dir / "plugin.yml"
    text = y.read_text()
    for k, v in fields.items():
        # the plugin's own `version` only; every `state_version` line (a wraps block repeats it)
        pat = rf"(?m)^(\s*){k}:.*$" if k == "state_version" else rf"(?m)^(){k}:.*$"
        text, n = re.subn(pat, rf"\g<1>{k}: {v}", text)
        assert n >= 1, (k, y)
    y.write_text(text)


class _Kernel(unittest.TestCase):
    """Three throwaway layers on the table profile, each writing a column of its own."""

    def setUp(self):
        st, self.tmp = fresh_stack(n=40)
        self.stack = st.dir
        st.close()
        self.plugins = {}
        for i, name in enumerate(("bottom", "middle", "top")):
            self.plugins[name] = write_plugin(
                self.tmp / "plugins", name, {"provides": [f"column/{name}_len"]},
                COLUMN.replace("NAME", f"{name}_len").replace("LEN", str(i)))
            self.mount(name)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def mount(self, name, rc=0):
        got, out = cli("--json", "mount", "--stack", str(self.stack), str(self.plugins[name]))
        self.assertEqual(got, rc, out)
        return json.loads(out)

    def run_json(self, *argv):
        rc, out = cli("--json", *argv)
        return rc, json.loads(out)

    def keys(self):
        return sorted(p.name for p in (self.stack / "materialised").iterdir())


class AReopenedStackServesOnlyWhatItsMountsRecorded(_Kernel):
    def test_a_mount_two_layers_down_rewritten_is_refused_by_every_command_that_reads_it(self):
        rc, served = self.run_json("materialise", "--stack", str(self.stack))
        self.assertEqual(rc, 0, served)
        keys = self.keys()
        declare(self.plugins["bottom"], state_version=2)
        # the view, by name: the plugin, both numbers, and the way out
        rc, r = self.run_json("materialise", "--stack", str(self.stack))
        self.assertEqual(rc, 2, f"a layer computed at state_version 1 was served under 2: {r}")
        self.assertEqual(r["status"], "refused")
        self.assertEqual(r["plugins"], ["bottom"])
        self.assertIn("bottom was mounted at version 0.0.1 state_version 1", r["reason"])
        self.assertIn("now declares version 0.0.1 state_version 2", r["reason"])
        self.assertIn("sch unmount bottom, then mount it again", r["fix"])
        self.assertEqual(self.keys(), keys, "a new materialised key was written for the other numbers")
        # a mount above it, before anything runs
        self.plugins["fourth"] = write_plugin(self.tmp / "plugins", "fourth", {"provides": ["column/fourth_len"]},
                                              COLUMN.replace("NAME", "fourth_len").replace("LEN", "9"))
        m = self.mount("fourth", rc=2)
        self.assertEqual(m["status"], "refused")
        self.assertIn("bottom was mounted at version 0.0.1 state_version 1", m["reason"])
        self.assertFalse((self.stack / "plugins" / "fourth").exists(), "the mount above it ran")
        # a scratch run and a report read the layer too
        script = self.tmp / "peek.py"
        script.write_text(PROTO_HEAD + "run.finish('peeked')\n")
        self.assertEqual(self.run_json("scratch", "--stack", str(self.stack), str(script))[0], 2)
        self.assertEqual(self.run_json("report", "--stack", str(self.stack))[0], 2)
        # `sch stack` shows what was recorded, and the difference; `sch doctor --runtime` names it
        rc, s = self.run_json("stack", "--stack", str(self.stack))
        self.assertEqual(rc, 2, s)
        bottom = s["plugins"][0]
        self.assertEqual((bottom["name"], bottom["state_version"], bottom["state"]), ("bottom", 1, "mounted"))
        self.assertEqual(bottom["mismatch"]["declared"]["state_version"], 2)
        self.assertFalse(s["served"])
        self.assertNotIn("mismatch", s["plugins"][1])
        rc, d = self.run_json("doctor", "--runtime", str(self.stack))
        self.assertEqual(rc, 2)
        self.assertIn("bottom (mounted) was mounted at version 0.0.1 state_version 1",
                      " ".join(f["message"] for f in d if not f["ok"]))
        # a save by another command does not launder the record: still 1 after a refused mount
        state = json.loads((self.stack / "state.json").read_text())
        self.assertEqual(state["runtimes"][0]["state_version"], 1)
        # the way out
        rc, u = self.run_json("unmount", "--stack", str(self.stack), "bottom")
        self.assertEqual(rc, 0, u)
        self.assertEqual(self.run_json("materialise", "--stack", str(self.stack))[0], 0)
        self.mount("bottom")
        rc, s = self.run_json("stack", "--stack", str(self.stack))
        self.assertEqual(rc, 0, s)
        self.assertEqual([(p["name"], p["state_version"]) for p in s["plugins"]],
                         [("middle", 1), ("top", 1), ("bottom", 2)])

    def test_each_field_a_mount_records_is_compared_the_version_and_the_layer_kind(self):
        declare(self.plugins["middle"], version="0.0.2")
        rc, r = self.run_json("materialise", "--stack", str(self.stack))
        self.assertEqual(rc, 2, r)
        self.assertIn("middle was mounted at version 0.0.1", r["reason"])
        self.assertIn("now declares version 0.0.2", r["reason"])
        declare(self.plugins["middle"], version="0.0.1")
        self.assertEqual(self.run_json("materialise", "--stack", str(self.stack))[0], 0)
        declare(self.plugins["top"], layer="checkpoint")
        rc, r = self.run_json("materialise", "--stack", str(self.stack))
        self.assertEqual(rc, 2, r)
        self.assertIn("state.json layer 'stack', plugin.yml 'checkpoint'", r["reason"])
        # recorded as a stack layer, it is unmounted as one: the way out is not closed by the new kind
        self.assertEqual(self.run_json("unmount", "--stack", str(self.stack), "top")[0], 0)

    def test_a_non_integer_state_version_is_a_difference_and_is_not_admitted(self):
        declare(self.plugins["top"], state_version="1.0")
        rc, r = self.run_json("materialise", "--stack", str(self.stack))
        self.assertEqual(rc, 2, r)
        self.assertIn("state_version 1.0", r["reason"])
        self.plugins["fifth"] = write_plugin(self.tmp / "plugins", "fifth", {"state_version": 2.0},
                                             PROTO_HEAD + "run.finish()")
        rc, p = self.run_json("plan", "--stack", str(self.stack), str(self.plugins["fifth"]))
        self.assertEqual(rc, 2)
        self.assertIn("declares state_version 2.0, which is not an integer", p["reason"])

    def test_a_record_edited_to_match_is_still_refused_while_another_record_says_otherwise(self):
        declare(self.plugins["bottom"], state_version=2)
        sj = self.stack / "state.json"
        state = json.loads(sj.read_text())
        state["runtimes"][0]["state_version"] = 2
        sj.write_text(json.dumps(state))
        rc, r = self.run_json("materialise", "--stack", str(self.stack))
        self.assertEqual(rc, 2, r)
        self.assertIn("in.json state_version 1, plugin.yml 2", r["reason"])


class ACorrectStackIsServedAsBefore(_Kernel):
    """ATTACKS 10: the refusal must not block a stack whose layers are what their plugins declare."""

    def test_never_changed_a_doc_field_changed_and_copied_to_another_folder(self):
        rc, first = self.run_json("materialise", "--stack", str(self.stack))
        self.assertEqual(rc, 0, first)
        rc, again = self.run_json("materialise", "--stack", str(self.stack))
        self.assertEqual((rc, again["digest"], again["cache"]["hits"]), (0, first["digest"], 1))
        y = self.plugins["middle"] / "plugin.yml"
        y.write_text(y.read_text().replace("summary: a test plugin", "summary: a test plugin, reworded")
                     + "# a comment added by a pull\n")
        rc, doc = self.run_json("materialise", "--stack", str(self.stack))
        self.assertEqual((rc, doc.get("digest")), (0, first["digest"]), doc)
        copy = self.tmp / "elsewhere" / "stack"
        shutil.copytree(self.stack, copy, symlinks=True)
        rc, moved = self.run_json("materialise", "--stack", str(copy))
        self.assertEqual((rc, moved.get("digest")), (0, first["digest"]), moved)
        rc, s = self.run_json("stack", "--stack", str(copy))
        self.assertEqual(rc, 0, s)
        self.assertFalse(any("mismatch" in p for p in s["plugins"]))
        rc, d = self.run_json("doctor", "--runtime", str(self.stack))
        self.assertIn({"rule": "D6", "ok": True, "message": "every mount is the identity its plugin.yml declares"}, d)


def _copy_adapter(tmp: Path, name: str) -> Path:
    dest = tmp / "adapters" / name
    shutil.copytree(PLUGINS / "single-cell" / name, dest, ignore=shutil.ignore_patterns("__pycache__"))
    return dest


@unittest.skipUnless(HAVE_H5PY, "h5py is not available in this interpreter")
class TheVerifiersReproductionThroughTheAdapters(unittest.TestCase):
    """V-W052's case: a stack mounted under the adapter and its stand-in at state_version 1, the same
    checkout then moved to 2 (here: the adapter's plugin.yml and constant rewritten in place)."""

    ENV = ("FAKE_SCINTEGRATE_LOG", "FAKE_SCINTEGRATE_MODE", "FAKE_SCINTEGRATE_STATE_VERSION",
           "FAKE_SCINTEGRATE_STATUS_STATE_VERSION", "FAKE_SCINTEGRATE_PROV_STATE_VERSION",
           "FAKE_SCQC_LOG", "FAKE_SCQC_MODE", "FAKE_SCQC_STATE_VERSION")

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sch-recorded-"))
        self._env = {k: os.environ.get(k) for k in self.ENV}
        for k in self.ENV:
            os.environ.pop(k, None)

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

    def test_scintegrate_mounted_at_1_and_moved_to_2_is_refused_by_name(self):
        import test_the_harness_runs_scintegrate as T
        adapter = _copy_adapter(self.tmp, "int@scintegrate")
        declare(adapter, state_version=1)
        run_py = adapter / "run.py"
        run_py.write_text(run_py.read_text().replace("\nSTATE_VERSION = 2\n", "\nSTATE_VERSION = 1\n"))
        manifest, design, _part = T.joint(self.tmp / "cohort")
        stack = self.tmp / "stack"
        rc, out = cli("init", str(stack), "--profile", "single-cell/1.0", "--observations", str(manifest),
                      "--parts", "h5ad", "--key", "sample=part", "--context", "assay=scrna",
                      "--context", "species=homo_sapiens")
        self.assertEqual(rc, 0, out)
        os.environ["FAKE_SCINTEGRATE_STATE_VERSION"] = "1"
        mount = ["--json", "mount", "--stack", str(stack), str(adapter), "--param", f"scintegrate={T.FAKE}",
                 "--param", f"integrate={json.dumps(T.block(design))}"]
        rc, out = cli(*mount)
        self.assertEqual(rc, 0, out)
        rc, under_1 = cli("--json", "materialise", "--stack", str(stack))
        self.assertEqual(rc, 0, under_1)
        keys = sorted(p.name for p in (stack / "materialised").iterdir())
        # the checkout moves: the declaration and the adapter's constant both say 2 now
        declare(adapter, state_version=2)
        run_py.write_text(run_py.read_text().replace("\nSTATE_VERSION = 1\n", "\nSTATE_VERSION = 2\n"))
        rc, out = cli("--json", "materialise", "--stack", str(stack))
        r = json.loads(out)
        self.assertEqual(rc, 2, f"the state_version 1 layer was served under 2: {r}")
        self.assertIn("int@scintegrate was mounted at version", r["reason"])
        self.assertIn("state_version 1 and its plugin.yml", r["reason"])
        self.assertIn("state_version 2 (", r["reason"])
        self.assertIn("sch unmount int@scintegrate, then mount it again", r["fix"])
        self.assertEqual(sorted(p.name for p in (stack / "materialised").iterdir()), keys)
        rc, out = cli("--json", "stack", "--stack", str(stack))
        p = json.loads(out)["plugins"][0]
        self.assertEqual((rc, p["state_version"], p["mismatch"]["declared"]["state_version"]), (2, 1, 2))
        # the way out: unmount, mount again under the tool at 2
        self.assertEqual(cli("--json", "unmount", "--stack", str(stack), "int@scintegrate")[0], 0)
        os.environ["FAKE_SCINTEGRATE_STATE_VERSION"] = "2"
        rc, out = cli(*mount)
        self.assertEqual(rc, 0, out)
        rc, out = cli("--json", "stack", "--stack", str(stack))
        self.assertEqual((rc, json.loads(out)["plugins"][0]["state_version"]), (0, 2), out)

    def test_another_adapter_scqc_moved_under_its_mount_is_refused_by_name(self):
        adapter = _copy_adapter(self.tmp, "qc@scqc")
        sheet, registry, design = library_cohort(self.tmp, libraries=2, droplets=60)
        stack = self.tmp / "stack"
        rc, out = cli("init", str(stack), "--profile", "single-cell/1.0", "--observations", str(sheet),
                      "--parts", "ambient_h5", "--key", "sample=sample", "--design", str(design),
                      "--context", "assay=snrna")
        self.assertEqual(rc, 0, out)
        os.environ["FAKE_SCQC_LOG"] = str(self.tmp / "calls.jsonl")
        rc, out = cli("--json", "mount", "--stack", str(stack), str(adapter),
                      "--param", f"scqc={FIXTURES / 'fake_scqc.py'}", "--param", f"registry={registry}",
                      "--param", "executor=local", "--param", "allow_local=true",
                      "--param", "dbr=0.06", "--param", "seed=0")
        self.assertEqual(rc, 0, out)
        self.assertEqual(cli("--json", "materialise", "--stack", str(stack))[0], 0)
        declare(adapter, state_version=2)
        rc, out = cli("--json", "materialise", "--stack", str(stack))
        r = json.loads(out)
        self.assertEqual(rc, 2, f"the scqc layer was served under numbers it was not computed at: {r}")
        self.assertIn("qc@scqc was mounted at version", r["reason"])
        self.assertIn("state_version 1 and its plugin.yml", r["reason"])
        self.assertIn("sch unmount qc@scqc, then mount it again", r["fix"])


if __name__ == "__main__":
    unittest.main()
