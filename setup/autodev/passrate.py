#!/usr/bin/env python3
"""How often a wave passes its first verification (RULES 2026-11-11, item 15: the measure of the attacks list).

  python3 -I setup/autodev/passrate.py [--since YYYY-MM-DD]

Reads autodev/ledger/waves.tsv. A wave's first verdict is its first row whose outcome starts with a verifier's verdict
("verifier ...: PASS" or "...: FAIL"; a fix round's re-check is not a first verdict). With --since, only waves whose build
began on or after that day are counted. Prints, per day, the waves first verified and how many passed, then the total. Nothing is estimated: a wave with no verdict row is not counted.
"""
import collections
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
VERDICT = re.compile(r"^(?:verifier|verification|its check)\b[^:]{0,60}:\s*(PASS|FAIL|READY)")  # widened 2026-11-12: three outcomes began otherwise


def first_verdicts(path, since="0000"):
    """With --since, only waves whose BUILD began on or after that day count: an older wave verified late is not new."""
    seen, out, built = set(), [], {}
    for line in path.read_text(encoding="utf-8").splitlines()[1:]:
        cells = line.split("\t")
        if len(cells) != 14:
            continue
        if cells[9] == "building":
            built.setdefault(cells[1], cells[0][:10])
        if cells[1] in seen:
            continue
        m = VERDICT.match(cells[12])
        if m:
            seen.add(cells[1])
            if built.get(cells[1], "0000") >= since:
                out.append((cells[0][:10], cells[1], "PASS" if m.group(1) == "READY" else m.group(1)))
    return out


def main():
    since = sys.argv[sys.argv.index("--since") + 1] if "--since" in sys.argv else "0000"
    rows = first_verdicts(ROOT / "autodev" / "ledger" / "waves.tsv", since)
    days = collections.defaultdict(list)
    for day, wave, verdict in rows:
        days[day].append((wave, verdict))
    for day in sorted(days):
        got = days[day]
        passed = [w for w, v in got if v == "PASS"]
        failed = [w for w, v in got if v == "FAIL"]
        print(f"{day}  first verified {len(got):2d}  passed {len(passed):2d}  failed {len(failed):2d}  ({' '.join(failed) or '-'})")
    total = len(rows)
    ok = sum(1 for _, _, v in rows if v == "PASS")
    print(f"TOTAL       first verified {total:2d}  passed {ok:2d}  ({100 * ok / total:.0f} %)" if total else "TOTAL       no first verdict in the ledger")


if __name__ == "__main__":
    main()
