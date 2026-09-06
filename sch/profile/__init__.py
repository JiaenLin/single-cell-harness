"""Profiles bind the generic contract to a domain (PLUGIN_FORMAT.md §14).

A profile is a YAML file naming: what an observation is, the slot vocabulary and its on-disk
form, the key map, the identity rule, sentinels, checkpoint kinds, the missing value, the
capability aliases, required declarations, and the domain terms `sch doctor` forbids in the core.

Two ship with the kernel: `table` — rows in a CSV, no biology, the L2 test — and
`single-cell`. A stack declares one; a kernel asked to mount a plugin under an unknown profile
refuses rather than guessing at its vocabulary.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .. import yamlish

HERE = Path(__file__).resolve().parent


class ProfileError(ValueError):
    pass


@dataclass
class Profile:
    data: dict
    path: Path

    @property
    def id(self) -> str:
        return str(self.data["profile"])

    @property
    def family(self) -> str:
        return self.id.split("/")[0]

    @property
    def major(self) -> int:
        m = re.search(r"/(\d+)", self.id)
        return int(m.group(1)) if m else 0

    @property
    def slots(self) -> dict:
        return dict(self.data.get("slots") or {})

    @property
    def keys(self) -> list[str]:
        return list(self.data.get("keys") or [])

    @property
    def sentinels(self) -> list[str]:
        return list(self.data.get("sentinels") or [])

    @property
    def identity(self) -> dict:
        return dict(self.data.get("identity") or {})

    @property
    def checkpoint_kinds(self) -> list[str]:
        return list(self.data.get("checkpoint_kinds") or [])

    @property
    def capabilities(self) -> dict:
        return dict(self.data.get("capabilities") or {})

    @property
    def reserved_identifiers(self) -> list[str]:
        return list(self.data.get("reserved_identifiers") or [])

    @property
    def domain_terms(self) -> list[str]:
        return list(self.data.get("domain_terms") or [])

    @property
    def required(self) -> dict:
        return dict(self.data.get("required") or {})

    @property
    def materialiser(self) -> str:
        return str(self.data.get("materialiser", self.family))

    @property
    def missing(self):
        return self.data.get("missing")

    def accepts(self, declared: str) -> bool:
        """A plugin declares `profile: family/major`; only the family and MAJOR are compared (X1)."""
        m = re.match(r"^([a-z0-9-]+)/(\d+)", str(declared))
        return bool(m) and m.group(1) == self.family and int(m.group(2)) == self.major

    def slot_dir(self, slot: str) -> str:
        s = self.slots.get(slot) or {}
        return str(s.get("dir", slot + "s"))


def load_profile(name_or_path) -> Profile:
    p = Path(str(name_or_path))
    if not p.exists():
        cand = HERE / (str(name_or_path).split("/")[0] + ".yml")
        if not cand.exists():
            raise ProfileError(f"unknown profile {name_or_path!r}; known: "
                               f"{sorted(x.stem for x in HERE.glob('*.yml'))}")
        p = cand
    data = yamlish.load(p)
    if not isinstance(data, dict) or "profile" not in data:
        raise ProfileError(f"{p}: not a profile")
    prof = Profile(data, p)
    if isinstance(name_or_path, str) and "/" in name_or_path and not Path(name_or_path).exists():
        if not prof.accepts(name_or_path):
            raise ProfileError(f"profile {name_or_path!r} is not served by {prof.id}")
    return prof


def known_profiles() -> list[str]:
    return sorted(x.stem for x in HERE.glob("*.yml"))
