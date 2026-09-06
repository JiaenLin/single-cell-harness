"""Plugin-side tooling: the validator, the plugin test, the scaffold, and the protocol helper.

`protocol.py` is the one file a plugin may copy or import from the host. It is stdlib-only and
imports nothing else from `sch`, so a plugin pinned to an old interpreter still reads it.
"""
