#!/usr/bin/env python3
"""Numbers a wave removed that are still in the tree (the coordinator's preflight, 2026-11-11).

    python3 -I setup/autodev/survivors.py <clone> <base> [<head>] [--min-digits 3] [--max 400] [--near] [--words]

Three waves that removed a cohort's values failed verification the same way (W035 twice, W048): the builder removed
each value where a term list or a named line pointed at it, and the same value stayed in a sibling doc, further down
the same file, in a runtime message, or written with a comma or another noun. Every verifier found it with one grep:
take every number on the diff's REMOVED lines and look for it at the head. This is that grep, so a builder runs it
before hand-back and the coordinator before spending a verifier.

It prints `file:line: text` for every line at <head> that holds a number the diff removed, then one last line
`SURVIVORS <lines> lines, <numbers> of <removed> removed numbers, in <files> files`. It judges nothing: a survivor may
be a default, a version or a date. The reader says what each is. Exit status is always 0.

Two more passes, each from a verifier's finding the digit grep could not see (W048's re-check, 2026-11-11):
`--near` lists numbers the diff ADDED that equal a removed number at two significant figures without being it (a
measured value rounded and relabelled "synthetic"); `--words` lists lines at <head> that write a count in words next to
a noun a cohort is counted in ("ten libraries", "the other nine", "thirteen REVIEWs", "eighteen minutes").
"""
import argparse
import re
import subprocess
import sys

NUM = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?(?![\w])")


def git(clone, *args):
    return subprocess.run(["git", "-C", clone, *args], capture_output=True, text=True, errors="replace").stdout


def norm(tok):
    return tok.replace(",", "").rstrip(".")


WORDS = ("two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen "
         "nineteen twenty thirty forty fifty sixty seventy eighty ninety hundred thousand dozen").split()
NOUNS = ("librar sample cohort cluster nuclei nucleus cell droplet barcode gene minute hour second job task run file "
         "review refus flag donor replicate batch fence valley").split()
WORD_NEAR = re.compile(r"\b(?:the other |all |nearly |about |a few )?(?:" + "|".join(WORDS) + r")(?:[- ](?:" + "|".join(WORDS) + r"))?\b[^.;\n]{0,24}?\b(?:"
                       + "|".join(NOUNS) + r")\w*", re.I)


def sig2(tok):
    try:
        v = float(tok)
    except ValueError:
        return None
    return None if v == 0 else float(f"{v:.1e}")


def wanted(tok, min_digits):
    digits = re.sub(r"\D", "", tok)
    return len(digits) >= min_digits and not re.fullmatch(r"(19|20)\d\d", tok)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clone")
    ap.add_argument("base")
    ap.add_argument("head", nargs="?", default="HEAD")
    ap.add_argument("--min-digits", type=int, default=3)
    ap.add_argument("--max", type=int, default=400)
    ap.add_argument("--near", action="store_true", help="added numbers equal to a removed one at 2 significant figures")
    ap.add_argument("--words", action="store_true", help="counts written in words next to a noun a cohort is counted in")
    a = ap.parse_args()

    if a.words:
        n_lines = 0
        for name in git(a.clone, "ls-tree", "-r", "--name-only", a.head).splitlines():
            text = git(a.clone, "show", f"{a.head}:{name}")
            if "\0" in text[:4096]:
                continue
            for n, line in enumerate(text.splitlines(), 1):
                m = WORD_NEAR.search(line)
                if m:
                    n_lines += 1
                    if n_lines <= a.max:
                        print(f"{name}:{n}: [{m.group(0)[:40]}] {line.strip()[:160]}")
        print(f"WORDS {n_lines} lines hold a count in words beside a counted noun (read each: a cohort's, or the method's)")
        return

    removed, added = set(), set()
    for line in git(a.clone, "diff", "-U0", a.base, a.head).splitlines():
        if line.startswith("---") or line.startswith("+++"):
            continue
        if line.startswith("-"):
            removed |= {norm(t) for t in NUM.findall(line[1:]) if wanted(norm(t), a.min_digits)}
        elif line.startswith("+"):
            added |= {norm(t) for t in NUM.findall(line[1:]) if wanted(norm(t), a.min_digits)}
    gone = removed - added  # a number the diff also adds was moved or kept on purpose, not removed
    if a.near:
        by = {}
        for g in gone:
            s = sig2(g)
            if s is not None and len(re.sub(r"\D", "", g)) >= 3:
                by.setdefault(s, set()).add(g)
        near = sorted((x, sorted(by[sig2(x)])) for x in (added - removed) if sig2(x) in by)
        for x, src in near[: a.max]:
            print(f"added {x}  ~  removed {' '.join(src)}")
        print(f"NEAR {len(near)} added numbers equal a removed one at 2 significant figures (a rounded copy is still the measurement)")
        return
    if not gone:
        print(f"SURVIVORS 0 lines, 0 of 0 removed numbers, in 0 files")
        return

    hits, found, files = [], set(), set()
    for name in git(a.clone, "ls-tree", "-r", "--name-only", a.head).splitlines():
        text = git(a.clone, "show", f"{a.head}:{name}")
        if "\0" in text[:4096]:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            here = {norm(t) for t in NUM.findall(line)} & gone
            if here:
                hits.append((name, n, sorted(here), line.strip()))
                found |= here
                files.add(name)
    for name, n, nums, line in hits[: a.max]:
        print(f"{name}:{n}: [{' '.join(nums)}] {line[:170]}")
    if len(hits) > a.max:
        print(f"... {len(hits) - a.max} more lines (raise --max)")
    print(f"SURVIVORS {len(hits)} lines, {len(found)} of {len(gone)} removed numbers, in {len(files)} files")


if __name__ == "__main__":
    sys.exit(main())
