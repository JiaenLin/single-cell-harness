#!/usr/bin/env python3
"""The leak guard: no site, host, project or cohort identifier anywhere in this repository.

WHY THE HARNESS NEEDS ITS OWN. Each of the four tools got one of these in September 2026 and the
harness did not, on the unexamined assumption that a kernel with no biology in it has nothing to
leak. That is wrong twice over. The harness carries job scripts, a spike, a profile, and a
development suite whose fixture and examples are the easiest place in the family for a real
cohort's vocabulary to settle - and it is the repository that CHECKS the others, so a leak here
would be a leak inside the instrument.

It is written the same way as the children's, deliberately: two kinds of pattern, SHAPES spelled
out here because they are shapes rather than names, and TERMS supplied from outside the
repository through $SCH_FORBIDDEN_TERMS so this guard never spells the cohort it guards against.
Without that file the scan proves less, and it says so rather than passing quietly.

This file exempts only itself. Stdlib only, so it runs anywhere the tool does.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_EXT = {".py", ".R", ".r", ".sh", ".pbs", ".md", ".yml", ".yaml", ".toml", ".cfg", ".txt",
            ".json", ".csv", ".tsv", ".cff", ".template", ".in"}
SKIP_DIRS = {".git", "__pycache__", ".egg-info", ".pytest_cache", "baselines"}
SHAPES = [
    (r"(?<![\w/])/(?:Users|home)/[A-Za-z][\w.-]*", "a user home path"),
    (r"/data/[A-Za-z][\w.-]*/home/", "a site home path"),
    (r"\blogin-\d{2}-\d{2}\b", "a login-node hostname"),
    (r"\bhn-\d{2}-\d{2}\b", "a scheduler head-node name"),
    (r"\bcompute\d{3,5}\b", "a compute-node hostname"),
    (r"\b\d{6}\.hn-\d{2}-\d{2}\b", "a scheduler job id"),
    (r"[\w.+-]+@[\w-]+\.(?:edu|com|org|sg|ac\.uk)\b", "an e-mail address"),
    (r"scratch/\d{8}__", "a dated scratch directory"),
]
# Attribution is not leakage: an address in the citation file names who to cite. A postmortem and
# a known-issues entry name the machines a measurement was taken on, and a measurement that does
# not say where it was taken is not a measurement - the harmony finding of 2026-09-06 is exactly
# that. Both are records of this project, not defaults a future dataset would inherit.
ATTRIBUTION = {"CITATION.cff", "pyproject.toml"}
RECORDS = ("docs/postmortem/", "KNOWN_ISSUES.md", "docs/CHILD_CONFORMANCE.md")


def files():
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT)
        if any(part in SKIP_DIRS or part.endswith(".egg-info") for part in rel.parts):
            continue
        if p.is_file() and (p.suffix in TEXT_EXT or p.name in ("VERSION", "HEAD.txt")) \
                and p.resolve() != Path(__file__).resolve():
            yield p


def terms() -> list:
    f = os.environ.get("SCH_FORBIDDEN_TERMS")
    if not f or not Path(f).exists():
        return []
    return [l.strip() for l in Path(f).read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.startswith("#")]


def scan() -> tuple:
    pats = [(re.compile(p), why) for p, why in SHAPES]
    site = terms()
    pats += [(re.compile(re.escape(t), re.I), f"site term {t!r}") for t in site]
    hits, n = [], 0
    for p in files():
        n += 1
        rel = str(p.relative_to(ROOT))
        record = any(rel.startswith(r) or rel.endswith(r) for r in RECORDS)
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            for rx, why in pats:
                if why == "an e-mail address" and p.name in ATTRIBUTION:
                    continue
                if record and why in ("a compute-node hostname", "a scheduler job id",
                                      "a scheduler head-node name"):
                    continue
                if rx.search(line):
                    hits.append(f"{rel}:{i}: {why}: {line.strip()[:90]}")
    return hits, n, site


def main() -> int:
    hits, n, site = scan()
    where = os.environ.get("SCH_FORBIDDEN_TERMS")
    print(f"scanned {n} files; {len(site)} site term(s) "
          + (f"from {where}" if site else "(none supplied: set SCH_FORBIDDEN_TERMS to prove more)"))
    for h in hits:
        print("  LEAK " + h)
    if hits:
        print(f"FAIL: {len(hits)} leak(s). A portable kernel carries no site or cohort "
              f"identifier; move it to the project or generalise it.")
        return 1
    print("PASS: no site or cohort identifier in the tree")
    return 0


# Discoverable by `unittest discover`, which is how the cluster suite runs.
try:
    import unittest

    class LeakGuard(unittest.TestCase):
        def test_no_site_or_cohort_identifier(self):
            hits, _, _ = scan()
            self.assertEqual(hits, [], "\n".join(hits))
except ImportError:      # pragma: no cover
    pass

if __name__ == "__main__":
    sys.exit(main())
