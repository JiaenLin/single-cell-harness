"""L3 — services attached to the Context.

    dataset      the immutable observations, the contributions, materialisation (the fold's body)
    executor     where an entry point physically runs, and how it is stopped (E5)
    provenance   the append-only, replayable event stream (P1)
    probe        read-only questions with bounded answers
    gate         refusals: monotonic (G4), measured with a probe (G3), escapes as pairs (G2)
    invariant    the companions: kernel-owned and plugin-owned runtime checks (ADR-0008)
    report       report-visible ⟺ replayable (P2)

Services may import `sch.core` and `sch.registry.manifest`/`fold` (L1, L2) and each other.
The domain reaches them only through a Profile object; the h5ad materialiser is the single place
that knows a file format, and it is selected by the profile's `materialiser` field.
"""
