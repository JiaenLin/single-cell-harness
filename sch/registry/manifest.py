"""The manifest and the capability grammar (PLUGIN_FORMAT.md §2, §4).

A manifest is `plugin.yml` in a plugin directory. The kernel reads it and nothing else from the
directory directly (L3). The grammar of `needs` / `provides` is fixed here; the VOCABULARY of
slots is the profile's, and this module never assumes one.

    <slot>/<name>       a named thing in a slot the profile defines
    <slot>/*            glob
    {key}               resolved through the profile's key map at mount
    capability:<name>   an abstract capability any implementation may satisfy
    checkpoint:<name>   the output of a checkpoint plugin
    service/<name>      a service on the Context (inject only)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .. import yamlish

CLASSES = ("method", "probe", "gate", "executor", "storage", "report", "publish", "companion")
LAYERS = ("stack", "checkpoint")
VERDICTS = ("PASS", "REVIEW", "REFUSE")
STATUSES = ("ok", "partial", "refused")

_CAP = re.compile(r"^(?P<kind>capability|checkpoint|service):?/?(?P<rest>.+)$")


class ManifestError(ValueError):
    pass


@dataclass(frozen=True)
class Capability:
    kind: str            # slot | capability | checkpoint | service
    slot: str            # for kind=slot: the slot name; otherwise the capability/checkpoint name
    name: str            # for kind=slot: the item name, may be "*" or "{key}" or "{key}_suffix"
    raw: str

    def is_glob(self) -> bool:
        return self.kind == "slot" and "*" in self.name

    def keys(self) -> list[str]:
        return re.findall(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", self.name)

    def resolve(self, keymap: dict) -> "Capability":
        """Resolve `{key}` through the key map. A key with no resolution stays unresolved."""
        if self.kind != "slot" or not self.keys():
            return self
        name = self.name
        for k in self.keys():
            v = keymap.get(k)
            if v is None:
                raise ManifestError(f"{self.raw}: key {{{k}}} has no resolution in this stack")
            name = name.replace("{" + k + "}", str(v))
        return Capability("slot", self.slot, name, self.raw)

    def matches(self, other: "Capability") -> bool:
        """Does a provided capability (`self`) satisfy a needed one (`other`)?"""
        if self.kind != other.kind:
            return False
        if self.kind != "slot":
            return self.slot == other.slot
        if self.slot != other.slot:
            return False
        if "*" in self.name:
            pat = "^" + re.escape(self.name).replace("\\*", ".*") + "$"
            return re.match(pat, other.name) is not None
        if "*" in other.name:
            pat = "^" + re.escape(other.name).replace("\\*", ".*") + "$"
            return re.match(pat, self.name) is not None
        return self.name == other.name


def parse_capability(s: str) -> Capability:
    if not isinstance(s, str) or not s.strip():
        raise ManifestError(f"capability must be a non-empty string, got {s!r}")
    s = s.strip()
    m = _CAP.match(s)
    if m and m.group("kind") in ("capability", "checkpoint", "service") and s.startswith(m.group("kind")):
        return Capability(m.group("kind"), m.group("rest"), "", s)
    if "/" not in s:
        raise ManifestError(f"{s!r}: a capability is <slot>/<name>, capability:<name>, "
                            f"checkpoint:<name> or service/<name>")
    slot, name = s.split("/", 1)
    if not re.match(r"^[a-z][a-z0-9_]*$", slot):
        raise ManifestError(f"{s!r}: slot {slot!r} is not a lowercase identifier")
    if not name:
        raise ManifestError(f"{s!r}: empty name")
    return Capability("slot", slot, name, s)


REQUIRED = ("contract", "profile", "name", "version", "summary", "when_to_use", "layer",
            "reversible", "needs", "provides", "sees", "language", "entry", "needs_env",
            "cannot_show")


@dataclass
class Manifest:
    data: dict
    dir: Path | None = None
    problems: list = field(default_factory=list)

    # ------------------------------------------------------------- accessors
    @property
    def name(self) -> str:
        return str(self.data.get("name", ""))

    @property
    def version(self) -> str:
        return str(self.data.get("version", ""))

    @property
    def cls(self) -> str:
        return str(self.data.get("class", "method"))

    @property
    def layer(self) -> str:
        return str(self.data.get("layer", ""))

    @property
    def reversible(self) -> bool:
        return bool(self.data.get("reversible", False))

    @property
    def state_version(self):
        return self.data.get("state_version")

    @property
    def contract_major(self) -> int | None:
        c = str(self.data.get("contract", ""))
        m = re.match(r"^(\d+)", c)
        return int(m.group(1)) if m else None

    @property
    def profile(self) -> str:
        return str(self.data.get("profile", ""))

    def caps(self, field_name: str) -> list[Capability]:
        vals = self.data.get(field_name) or []
        if not isinstance(vals, list):
            raise ManifestError(f"{self.name}: {field_name} must be a list")
        return [parse_capability(v) for v in vals]

    @property
    def needs(self) -> list[Capability]:
        return self.caps("needs")

    @property
    def provides(self) -> list[Capability]:
        return self.caps("provides")

    @property
    def optional(self) -> list[Capability]:
        return self.caps("optional")

    @property
    def inject(self) -> list[str]:
        return [str(x) for x in (self.data.get("inject") or [])]

    @property
    def gates(self) -> dict:
        return dict(self.data.get("gates") or {})

    @property
    def contributes(self) -> bool:
        """Does this plugin contribute to the stack? Probes, gates and companions do not."""
        return self.cls in ("method",) and bool(self.data.get("provides"))

    def entry_path(self) -> Path | None:
        if not self.dir:
            return None
        return self.dir / str(self.data.get("entry", ""))

    def to_dict(self) -> dict:
        return dict(self.data)


def load_manifest(plugin_dir) -> Manifest:
    d = Path(plugin_dir)
    f = d / "plugin.yml"
    if not f.exists():
        raise ManifestError(f"{d}: no plugin.yml")
    try:
        data = yamlish.load(f)
    except yamlish.YamlError as e:
        raise ManifestError(f"{f}: {e}") from e
    if not isinstance(data, dict):
        raise ManifestError(f"{f}: manifest is not a mapping")
    return Manifest(data=data, dir=d)
