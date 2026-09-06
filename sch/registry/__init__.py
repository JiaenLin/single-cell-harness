"""L2 — the registry. A manifest becomes a Runtime; the registry owns lifecycle and the fold.

Depends on `sch.core` only (L1). Knows no domain term (L2): what a slot is called on disk, what
identity means, what may be masked — all of it arrives through the Profile the stack declares.
"""
from .manifest import Manifest, ManifestError, Capability, parse_capability  # noqa: F401
from .runtime import Registry, Runtime, MountResult, RegistryError  # noqa: F401
from .fold import fold_key, FoldCache  # noqa: F401
