"""`sch conform` — what a child tool must expose before an adapter is written, checked.

Two modes. `sch conform <repo>` reads a tool's repository statically; `sch conform --run <dir>`
reads a finished run directory. Both print a checklist naming the fix for every failure, so an
agent working inside a child knows what to change and can prove it changed.

Nothing here names a project, a cohort, a site or a host. Site-specific forbidden terms come
from a file OUTSIDE the repository (`--terms`, `$SCH_SITE_TERMS`, or `$SCH_SITE/forbidden_terms.txt`)
so that the guard itself never spells what it guards against. A list that is named and missing,
or that holds no term, is refused rather than read as empty (W024).

S1 reads every file git lists, by content; binary files are skipped and counted. A repository
declares its records and the words it legitimately holds in `LEAK_SCOPE.txt`, one reasoned entry
per line. `sch conform terms build COHORT --out FILE` generates a cohort's list from its own
records (`terms.py`); the list lives with the cohort, never in a repository.
"""
from .checks import (conform_repo, conform_run, conform_against, run_record, format_checks,  # noqa: F401
                     leak_scan, load_scope, TermListError, Term, SCOPE_FILE)
