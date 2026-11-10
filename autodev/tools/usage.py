#!/usr/bin/env python3
"""Measure the loop's token burn from Claude Code transcripts (RULES tier IV, the budget, 2026-11-10).

usage: python3 -I autodev/tools/usage.py [--since YYYY-MM-DD] PATH_OR_GLOB ...

Each path is a session transcript (.jsonl) or a background task output (tasks/*.output). The per-day
table sums the API usage fields of every assistant message: cache_read (the context re-read on each
call), cache_write, output (what the model wrote) and the number of calls. Agent launches are counted
from Agent tool uses. Nothing here is estimated: a path that holds no usage fields contributes zero.
The caller names the paths; this file names none (a home path in the repo is a site leak).
"""
import argparse
import collections
import glob
import json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="", help="count days >= this ISO date")
    ap.add_argument("paths", nargs="+")
    a = ap.parse_args()
    paths = [p for pat in a.paths for p in glob.glob(pat)]
    day = collections.defaultdict(collections.Counter)
    launches = collections.Counter()
    for p in paths:
        try:
            fh = open(p, "rb")
        except OSError:
            continue
        with fh:
            for line in fh:
                if b'"usage"' not in line and b'"name":"Agent"' not in line and b'"name": "Agent"' not in line:
                    continue
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                m = d.get("message") or {}
                if not isinstance(m, dict):
                    continue
                ts = (d.get("timestamp") or "")[:10]
                if a.since and ts < a.since:
                    continue
                u = m.get("usage")
                if u:
                    c = day[ts]
                    c["calls"] += 1
                    c["cache_read"] += u.get("cache_read_input_tokens", 0)
                    c["cache_write"] += u.get("cache_creation_input_tokens", 0)
                    c["output"] += u.get("output_tokens", 0)
                for b in m.get("content") or []:
                    if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") == "Agent":
                        launches[ts] += 1
    total = collections.Counter()
    print("day         calls  cache_read(M)  cache_write(M)  output(M)  launches")
    for ts in sorted(day):
        c = day[ts]
        total.update(c)
        print(f"{ts}  {c['calls']:6}  {c['cache_read']/1e6:13.1f}  {c['cache_write']/1e6:14.1f}"
              f"  {c['output']/1e6:9.2f}  {launches[ts]:8}")
    print(f"TOTAL       {total['calls']:6}  {total['cache_read']/1e6:13.1f}  {total['cache_write']/1e6:14.1f}"
          f"  {total['output']/1e6:9.2f}  {sum(launches.values()):8}   files={len(paths)}")


if __name__ == "__main__":
    main()
