"""Shared fixtures for the kernel tests. Everything synthetic; nothing names a project."""
import os
import shutil
import sys
import tempfile
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sch.kernel import Stack  # noqa: E402
from sch.plugin.test import table_fixture  # noqa: E402

PLUGINS = ROOT / "plugins"


def fresh_stack(n=200, plugin_paths=None):
    tmp = Path(tempfile.mkdtemp(prefix="sch-test-"))
    rows, design = table_fixture(tmp, n=n)
    st = Stack.init(tmp / "stack", "table/1.0", str(rows), str(design),
                    keys={"value": "score", "group": "arm", "unit": "unit"},
                    plugin_paths=[str(p) for p in (plugin_paths or [])])
    return st, tmp


def write_plugin(root: Path, name: str, manifest: dict, run_py: str, extra: dict = None) -> Path:
    """A throwaway plugin directory. `manifest` is merged over a valid method manifest."""
    from sch import yamlish
    base = {"contract": "1.0", "profile": "table/1.0", "name": name, "version": "0.0.1",
            "summary": "a test plugin", "when_to_use": "in tests", "class": "method",
            "layer": "stack", "reversible": True, "state_version": 1, "inject": ["dataset"],
            "needs": [], "provides": [], "sees": [], "language": "python", "entry": "run.py",
            "needs_env": False,
            "no_runtime_invariant": "the output is a pure transformation of the declared input and nothing observable changes between calls",
            "cannot_show": ["a test plugin shows nothing"]}
    base.update(manifest)
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    yamlish.dump(base, d / "plugin.yml")
    (d / "run.py").write_text(textwrap.dedent(run_py))
    (d / "README.md").write_text("# t\n\n## What it does\nA test plugin that exists to exercise one rule of the kernel and nothing else.\n\n"
                                 "## Report surface\nWhatever numbers the test records; none of them are quotable outside the test.\n\n"
                                 "## Cost\nMilliseconds to run, nothing to unmount beyond its own contribution.\n\n"
                                 "## Known limitations\nIt is a test fixture and has never been run on real data of any kind.\n")
    for fname, content in (extra or {}).items():
        (d / fname).write_text(textwrap.dedent(content))
    return d


PROTO_HEAD = '''
import importlib.util, os, sys, json
spec = importlib.util.spec_from_file_location("protocol", os.environ["SCH_PROTOCOL"])
protocol = importlib.util.module_from_spec(spec); spec.loader.exec_module(protocol)
run = protocol.Run.from_argv()
'''


def cleanup(tmp):
    shutil.rmtree(tmp, ignore_errors=True)
