"""`sch conform` — what a child tool must expose before an adapter is written, checked.

Two modes. `sch conform <repo>` reads a tool's repository statically; `sch conform --run <dir>`
reads a finished run directory. Both print a checklist naming the fix for every failure, so an
agent working inside a child knows what to change and can prove it changed.

Nothing here names a project, a cohort, a site or a host. Site-specific forbidden terms come
from a file OUTSIDE the repository (`--terms`, `$SCH_SITE_TERMS`, or `$SCH_SITE/forbidden_terms.txt`)
so that the guard itself never spells what it guards against.
"""
from .checks import conform_repo, conform_run, format_checks  # noqa: F401
