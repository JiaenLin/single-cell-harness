"""The materialisation fold, keyed by declared semantics (D6, ADR-0010).

A cached materialisation is valid only for the exact tuple

    (observations digest, ordered stack of (plugin, version, state_version, params), profile)

Anything else is a miss, never a partial hit. The fold itself is the profile's job — how a mask
and a column become a file is domain — and the key is the kernel's, because it is the thing that
must never be approximated.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def fold_key(observations_digest: str, entries: list, profile: str) -> str:
    """`entries` is an ordered list of (plugin, version, state_version, params)."""
    canon = {
        "observations": observations_digest,
        "stack": [[str(p), str(v), int(sv) if sv is not None else None,
                   json.dumps(params, sort_keys=True, default=str)] for p, v, sv, params in entries],
        "profile": profile,
    }
    return hashlib.sha256(json.dumps(canon, sort_keys=True).encode()).hexdigest()[:20]


class FoldCache:
    """Exact-tuple cache of materialisations. A miss is a miss; nothing is reused partially."""

    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.hits = 0
        self.misses = 0

    def dir_for(self, key: str) -> Path:
        return self.root / key

    def lookup(self, key: str) -> Path | None:
        d = self.dir_for(key)
        marker = d / "key.json"
        if marker.exists():
            try:
                if json.loads(marker.read_text())["key"] == key:
                    self.hits += 1
                    return d
            except (ValueError, KeyError):
                pass
        self.misses += 1
        return None

    def commit(self, key: str, meta: dict) -> Path:
        d = self.dir_for(key)
        d.mkdir(parents=True, exist_ok=True)
        (d / "key.json").write_text(json.dumps({"key": key, **meta}, indent=1, sort_keys=True))
        return d

    def clear(self):
        import shutil
        if self.root.exists():
            shutil.rmtree(self.root)
        self.root.mkdir(parents=True, exist_ok=True)
