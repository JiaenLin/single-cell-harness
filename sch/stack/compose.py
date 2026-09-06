"""Overlay composition of stack declarations.

ONE function. `sch stack --dump` and a real mount both call `compose`, so a dump cannot drift
from what mounts (ROADMAP Phase 1, "composition"). Layers are applied in order; a later layer's
scalar replaces, its mapping merges key-by-key, and its `plugins` mapping merges by plugin name
with per-plugin params merged. `null` in a later layer removes the key.
"""
from __future__ import annotations

import os
from pathlib import Path

from .. import yamlish


class StackError(ValueError):
    pass


def _merge(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        out = dict(a)
        for k, v in b.items():
            if v is None:
                out.pop(k, None)
            elif k in out:
                out[k] = _merge(out[k], v)
            else:
                out[k] = v
        return out
    return b


def compose(layers: list) -> dict:
    """`layers`: list of (label, dict). Returns the composed declaration with a `composed_from`."""
    result: dict = {}
    labels = []
    for label, data in layers:
        if data is None:
            continue
        if not isinstance(data, dict):
            raise StackError(f"layer {label}: not a mapping")
        result = _merge(result, data)
        labels.append(label)
    result["composed_from"] = labels
    return result


def load_layers(stack_dir, run_overrides: dict | None = None) -> list:
    """Site (`$SCH_SITE/stack.yml`), then project (`<stack>/stack.yml`), then run overrides."""
    layers = []
    site = os.environ.get("SCH_SITE")
    if site and (Path(site) / "stack.yml").exists():
        layers.append(("site", yamlish.load(Path(site) / "stack.yml")))
    proj = Path(stack_dir) / "stack.yml"
    if proj.exists():
        layers.append(("project", yamlish.load(proj)))
    if run_overrides:
        layers.append(("run", run_overrides))
    return layers


def set_path(data: dict, dotted: str, value):
    """`keys.label=cell_type` style override into a nested dict."""
    parts = dotted.split(".")
    cur = data
    for p in parts[:-1]:
        cur = cur.setdefault(p, {})
    cur[parts[-1]] = value
    return data
