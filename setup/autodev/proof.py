#!/usr/bin/env python3
"""Is a wave's proof table there, and is every judge shown a right and a wrong input? (RULES item 22, 2026-11-12.)

    python3 -I setup/autodev/proof.py <wave file>

A wave file's PROOF TABLE is the markdown table under the last heading whose text holds "proof table" (any case).
Its columns, in order: the judge | a RIGHT input and what the judge printed | a WRONG input and what it printed |
who made the inputs. The script judges nothing about the content: it counts rows and names every row whose judge,
RIGHT, WRONG or maker cell is empty, a dash or a placeholder. It prints one line per incomplete row, then
`PROOF: <n> rows, <k> incomplete`, and exits 1 when the section is missing, the table has no row, or k is not 0.
The coordinator runs it before any verifier is launched; a verifier starts from the WRONG rows.

It exists because of the direction review of 2026-11-12: 13 of 52 blocking reasons in two days were a judge never
shown both a right and a wrong input (a check script tried only on an empty run; a prediction with no arithmetic; a
field a deployed app reads with one fixed sentence), and the one fix round that handed back such a table passed its
re-check on the verifier's own states.
"""
import re
import sys

EMPTY = re.compile(r"^(?:|-+|\?+|tbd|todo|n/?a|\.\.\.|…)$", re.I)


def table_after_heading(text):
    """The rows (lists of cells) of the first table under the LAST heading that names the proof table, or None."""
    lines = text.splitlines()
    starts = [i for i, l in enumerate(lines) if re.match(r"^\s{0,3}(#{1,6}\s+|\*\*).*proof table", l, flags=re.I)]
    if not starts:
        return None
    rows = []
    for line in lines[starts[-1] + 1:]:
        if re.match(r"^\s{0,3}#{1,6}\s", line) and not rows:
            continue
        if re.match(r"^\s{0,3}#{1,6}\s", line):
            break
        if line.lstrip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c) and any(cells):
                continue
            rows.append(cells)
        elif rows and line.strip():
            break
    return rows[1:] if rows else []   # the first row is the header


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__.split("\n\n")[1])
    text = open(sys.argv[1], encoding="utf-8").read()
    rows = table_after_heading(text)
    if rows is None:
        print("PROOF: no proof table (a heading that says 'Proof table', then a table of four columns)")
        return 1
    incomplete = 0
    for n, cells in enumerate(rows, 1):
        cells = (cells + ["", "", "", ""])[:4]
        missing = [name for name, cell in zip(("judge", "RIGHT", "WRONG", "who made the inputs"), cells) if EMPTY.match(cell)]
        if missing:
            incomplete += 1
            print(f"row {n} ({cells[0][:60] or 'no judge'}): empty {', '.join(missing)}")
    print(f"PROOF: {len(rows)} rows, {incomplete} incomplete")
    return 1 if (incomplete or not rows) else 0


if __name__ == "__main__":
    sys.exit(main())
