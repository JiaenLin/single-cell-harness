# freshness

## What it does
Compares the modification time of an artifact with the newest of its inputs and answers
`stale: true` when the artifact is older.

## Report surface
A boolean and two timestamps. It travels with: *fresh means written after, not computed from.*

## Cost
A stat call per file, so effectively free. It contributes nothing and can always be re-run against any artifact in the run.

## Known limitations
Modification time is the only evidence. It cannot see a report rendered from a stale payload
written a second later, which is why the kernel keys materialisations on content, not on time.
