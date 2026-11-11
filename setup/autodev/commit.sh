#!/usr/bin/env bash
# The coordinator's records commit (2026-11-11). One at a time, and it SAYS whether it landed.
#   bash setup/autodev/commit.sh "<message>" <path> [<path> ...]
# Twice on 2026-11-11 a records commit was blocked by the suite (a site path an agent had written into a wave file) while
# the command still exited 0 because a `git log` followed it, and the coordinator reported it as landed. This prints
# exactly one last line: `COMMITTED <sha> pushed`, or `BLOCKED: <the suite's first failing line>` with exit 1.
set -u
msg=${1:?message}; shift
while pgrep -f "git commit -q -m" >/dev/null 2>&1 || pgrep -f "git merge -q --no-ff" >/dev/null 2>&1; do sleep 15; done
git add -- "$@" || { echo "BLOCKED: git add failed"; exit 1; }
out=$(git commit -q -m "$msg" 2>&1); rc=$?
if [ $rc -ne 0 ]; then
  echo "BLOCKED: $(printf '%s\n' "$out" | grep -m1 -E '^(FAIL|ERROR):|BLOCKED|nothing to commit' || printf '%s' "$out" | tail -1)"
  printf '%s\n' "$out" | grep -m3 -E "AssertionError|First extra element|^'" | cut -c1-300
  exit 1
fi
if git push -q origin HEAD 2>/dev/null; then echo "COMMITTED $(git rev-parse --short HEAD) pushed"; else echo "COMMITTED $(git rev-parse --short HEAD) NOT PUSHED"; exit 1; fi
