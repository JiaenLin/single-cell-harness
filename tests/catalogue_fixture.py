"""A synthetic scProfile-shaped checkout for the catalogue's tests, and the real CLI to read it.

Everything here is invented: the tools, the fields' values, the vocabulary. The maker's marker is
deliberately NOT scProfile's word (`wraps.unreviewed`, where scProfile says
`wraps.plots_unreviewed`), so a test passing on this checkout proves the catalogue read the
marker from the declaration rather than knowing it. Imported as a sibling module, never as
`tests.<module>` (GAP-C23).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

VOCABULARY = '''
"""A capability vocabulary, as a literal, the way the tool states its own."""
CAPABILITIES = {
    "counts": {"resolve": "data", "why": "integer counts"},
    "lognorm": {"resolve": "data", "why": "log-normalised values"},
    "label": {"resolve": "data", "why": "a grouping column"},
    "sample": {"resolve": "data", "why": "the unit of replication"},
    "spliced": {"resolve": "data", "why": "spliced counts"},
    "design": {"resolve": "design", "why": "a design table"},
    "contrast": {"resolve": "design", "why": "a testable factor"},
    "ordering": {"resolve": "derived", "why": "an ordering another plugin provides"},
}
'''

DEVPOINTS = '''tool: toolkit
devpoints: 1
points:
  kernel:
    what: one method, hosted
    lives: kernels
    proves: it is declared
    cannot_prove: that it is right
    convert:
      stages:
        - name: inventory
          phase: build
          fills: [report.figures]
          outstanding_if: wraps.unreviewed
rules:
  end_to_end:
    names: [alpha]
'''

HARNESS_PLUGIN = '''contract: "1.0"
profile: {profile}
name: {name}
version: 0.0.1
summary: {summary}
when_to_use: in a test
layer: stack
reversible: true
needs: {needs}
provides: []
sees: []
cannot_show:
  - a test plugin shows nothing
'''


def plugin_source(spec: dict, body: str = "") -> str:
    """A one-file plugin: the PLUGIN literal on line 1, a run(ctx), then `body`."""
    return f"PLUGIN = {spec!r}\n\n\ndef run(ctx):\n    pass\n" + textwrap.dedent(body)


def spec(**over) -> dict:
    """A complete-enough declaration; `over` replaces or adds keys."""
    base = {"api": 1, "version": "0.1.0", "summary": "a test method", "when_to_use": "in a test",
            "inject": {"required": ["counts", "label"], "optional": []},
            "provides": [], "produces": ["tables/out.csv"],
            "cannot_show": ["a test plugin shows nothing"]}
    base.update(over)
    return base


def checkout(root: Path, plugins: dict, files: dict = None, devpoints=DEVPOINTS,
             vocabulary=VOCABULARY) -> Path:
    """A scProfile-shaped checkout at `root`: kernels/<name>.py for each plugin source."""
    root = Path(root)
    (root / "kernels").mkdir(parents=True, exist_ok=True)
    for name, src in plugins.items():
        (root / "kernels" / f"{name}.py").write_text(src, encoding="utf-8")
    if devpoints is not None:
        (root / "DEVPOINTS.yaml").write_text(devpoints, encoding="utf-8")
    if vocabulary is not None:
        (root / "scprofile").mkdir(exist_ok=True)
        (root / "scprofile" / "declare.py").write_text(vocabulary, encoding="utf-8")
    for rel, text in (files or {}).items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    return root


def harness_plugin(where: Path, name: str, profile="table/1.0", summary="a site plugin",
                   needs="[]", extra: dict = None) -> Path:
    d = Path(where) / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "plugin.yml").write_text(HARNESS_PLUGIN.format(profile=profile, name=name,
                                                        summary=summary, needs=needs))
    for fname, text in (extra or {}).items():
        (d / fname).write_text(text)
    return d


def sch(*args, plugins: str = "") -> subprocess.CompletedProcess:
    """`python -m sch ...` from the repository, the way an agent runs it. `$SCH_PLUGINS` is set
    by the test, never inherited, so a site directory on the machine cannot change an answer."""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env["SCH_PLUGINS"] = plugins
    return subprocess.run([sys.executable, "-m", "sch", *args], cwd=str(ROOT), env=env,
                          capture_output=True, text=True, timeout=120)


def catalogue_json(*args, plugins: str = ""):
    """(exit code, parsed JSON) of `sch catalogue ... --json`. A non-JSON answer fails loudly."""
    p = sch("catalogue", *args, "--json", plugins=plugins)
    try:
        return p.returncode, json.loads(p.stdout)
    except ValueError:
        raise AssertionError(f"`sch catalogue {' '.join(args)} --json` printed no JSON "
                             f"(exit {p.returncode}):\n{p.stdout}\n{p.stderr}") from None


def rows(doc, source="scprofile") -> dict:
    return {r["id"]: r for r in doc["plugins"] if r["source"] == source}
