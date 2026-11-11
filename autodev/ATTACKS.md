# Attacks that worked

Every line here is a way a verifier broke a wave in this program, with the wave it broke. A builder runs each one that
applies against its own change BEFORE hand-back, and says in the hand-back which it ran and what happened (BRIEFS
section 0, SELF-ATTACK). A verifier that breaks a wave a new way adds a line to the inbox at the end; the coordinator
moves it up. Keep it one screen: a line that has not caught anything in 20 waves is dropped.

The PI, 2026-11-11, after the comparison with ScientistTwo: failures are input for the next builder, not only rows in a
ledger. Of the 9 new waves verified that day, 5 failed first verification, on causes that repeat.

| # | the defect | the attack | broke |
|---|---|---|---|
| 1 | A stand-in laxer than the real tool: the fixture passes where the tool refuses | Make every stand-in refuse what its tool refuses; run the real tool on the path at least once and say exactly what ran real | W042 (the library column) |
| 2 | A ban or a check matched on one exact string | Spell around it: a version suffix, case, whitespace, another field that carries the same fact. Prefer a list of what is allowed | W041 (the remover's name) |
| 3 | An escape that lifts an invariant | For each accept, override or force: list everything it can lift. A check that cannot fire on a correct run has no escape | W043 (accept by name) |
| 4 | A rule fitted until one cohort comes out right; thresholds as bare literals | Write down what you expect on at least ten other inputs BEFORE changing the rule, then score it. Every threshold is a named, recorded parameter | W044 (the tree rule) |
| 5 | A record that keeps what was removed | After removing a string, grep the records, design files and history the tool writes, not only the source | W035 (twice) |
| 6 | A value spliced raw into a file | Treat every option as hostile: quotes, newlines, a second key, non-ASCII digits. Check the file as written, not the input | W035 (`--as-version`) |
| 7 | A clean status with no result | Make each component refuse or produce nothing, then read the run's status, report and exit code | GAP-C96 (exit 0, no table) |
| 8 | An input not pinned across steps | Change each named file between two steps, between generation and run, and between a seal and a resume | W041, W042 |
| 9 | A decision that is the user's, never asked | Compare what the adapter asks with what the tool itself declares as the user's; drift is a test, not a review | W041 |
| 10 | A new refusal that blocks true cases | For each new refusal, find a correct input it wrongly refuses (a published number, a method rule, a fixture sentence) | W035 (the sample rule) |
| 11 | A test that does not fail on the base, or fails for another reason | Copy the new tests onto the base commit and read WHY each fails | several, 2026-11-09 |
| 12 | A verdict line that can read success on a miss, or a miss that looks like a crash | Force each failure the job predicts against and read the one line the coordinator will read | W043's jobs |
| 13 | A consistency check that tampering preserves | Tamper while keeping every count and hash the check looks at | W043 (same count, wrong cells) |
| 14 | Evidence carried to a commit whose executed files changed; a hash printed and never compared | Diff the files the job executes between the gated commit and the merging one; find who compares each printed hash | W011, W021, W042 |
| 15 | A doc sentence the change made false | Grep the docs, help text and docstrings for every claim about the behaviour you changed | most waves |
| 16 | A leak moved, not removed; a cohort's measured number no term list holds | Scan untruncated, records included; read comments for counts, sizes and times that came from one cohort's run | W035, GAP-C100 |
| 17 | A refusal that comes after the expensive work | Give the last stage a bad size, flag or file and count how much ran before the refusal | W042 (sizes), W041 (owned flags) |
| 18 | A silent pick among candidates | Give it two candidates, or none, where it expects one: it must refuse by name | W041 (`hands_on`), GAP-C103 |
| 19 | A fix round that only patches the design that failed | In a wave that has to FIND something: bring one fresh candidate to the fix round and score both on the same expectations | W044 (one tree rule, patched); carried from VCC's list |
| 20 | A winner reported as if it were the only thing tried | Say how many candidates the result was chosen from, and keep every one in the pool with its result | carried from VCC's list |
| 21 | A fix that closes the one case shown and leaves the door it was in | After a fix, attack the family: the same fact through another field, another file, another route; the same check at another moment (start, seal, resume, generation) | the driver's fix round 1 (four of six fixes) |
| 22 | A check that trusts the history it reads | Rewrite what the check reads back (`git replace` on the commits a record names; an edited cache; a moved ref) and see whether it still passes | W035 (a record check that honours replace refs; found in the last re-check) |
| 23 | A graded line that is true by construction, or a line that missed demoted to a record | For each graded line, name a tool output that would fail it; a line that missed stays graded, as a bound written before the run | W044 fix 1 (the job's walk lines) |
| 24 | A score taken on a capped output; a laxer result for less evidence | Grade the rule's verdict, not the truncated list (read what the cap cut); order inputs by how much evidence they hold and check the tool never gets laxer as evidence drops | W044 fix 1 (3 hidden by the cap; a no-health release drafted unchecked) |
| 25 | A user-given name the output format forbids, accepted at input and refused only at the write, after the expensive work | Give each name that becomes a key in a written file one the format reserves or forbids (a slash, a reserved column name) and count what ran before the failure | W046 (the design's key and factors) |

## Inbox (a verifier appends here; one line each: the defect, the attack, the wave)

