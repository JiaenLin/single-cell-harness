# Root design review: the run section of Lab's converter (W017)
**Asked** 2026-11-12 under RULES 20, after five fix-ups failed verification and a sixth was briefed. **Read-only:** nothing was
changed, committed or run. **Finding: the design is the cause.** Recommendation: replace the generic walk with a closed reader of
six named fields, keep one part of the sixth fix-up, and narrow what the docs promise.

## A. What it is for
GOALS A6.2: Studio shows the run that produced the object, as recorded, never inferred. The section has one reader, a card.
Studio's `run.ts` puts six fields first under exactly these names (`tool`, `version`, `commit`, `stage`, `run_key`, `job`) and prints
every other top-level field as folded JSON text. Its Methods paragraph uses only the paths of the records carried. Nothing in
Studio reads below a record's first level. What the family's writers put in `uns` (read from each writer's code; not measured):

| writer and key | what it holds | of the six |
|---|---|---|
| scIntegrate, `uns/scintegrate/provenance` | 32 fields: strings, numbers, lists of strings, dicts to depth 3 | tool, version, commit, job |
| scQC, `uns/scqc` (schema `scqc/provenance@1`) | about 18 scalars, depth 1; a contract that scAnno reads | tool, version, commit, run_key |
| scAnno, `uns/<column>_provenance` | 8 to 11 fields with label counts: where a label column came from, not which run | none |
| scProfile, `uns/scprofile` | contract, input, kernels to depth 3 | none; the section's rule does not find it |
| the harness, `uns/harness_run` (GAP-P20) | decided as one JSON string | nothing writes it yet |

Every writer coerces to plain types before writing (`_plain`, `_uns_safe`): no structured array, no reference, no link, no deep
nesting. The committed fixture's record, modelled on scIntegrate's, is 394 bytes at depth 3. scIntegrate's `emit.build` makes a new
object and writes only its own entry, so the final object carries one record the section finds. No writer records `stage` on its
normal path and only scQC records `run_key`: what A6.2 still lacks is on the writers' side (GAP-P20), whatever the reader does.
**The smallest thing that serves the purpose:** per record, up to six short strings read by name; today, four from one group.

## B. Why each round failed
| round | what it added | what broke it |
|---|---|---|
| first build | any entry named provenance, converted to JSON | a structured array crashed the conversion; no bound on size |
| fix-up 1 | conversion value by value; budgets in characters | compact JSON measured, the file is indented UTF-8; 800 levels took 93 s; records uncounted once full |
| fix-up 2 | bytes as written, recomputed; depth 16; `leftOut` | hard links make a few groups into exponentially many paths |
| fix-up 3 | identity by address; 10,000 nodes a record | many records linked to one large group each read it again |
| fix-up 4 | one walk, `seen` shared; 50,000 nodes a section | a record never written "owned" an object, and later records lost it |
| fix-up 5 | `seen` per record again; identity tagged with the link's file name | the tag collides for two files of one name; an external link read another file as the object's own; `__proto__` lost |

Two patterns. Each fix added a mechanism (a measure, a bound, an identity, a dedupe), and the next failure sat either inside the
mechanism just added (fix-ups 1, 4, 5) or in the next HDF5 feature nobody had bounded (depth, hard links, shared links, external
links, key names). And fix-ups 4 and 5 undo each other: on a graph, "bounded cost" and "no record lost" pull against each other,
and no dedupe rule gives both. As far as the writers' code shows, none of these defects needs an input a family tool produces.

**The cause, as one sentence a builder could have had on day one:** the section was specified by where to look and a promise to
copy whatever is there, without loss and without ever stopping, and never by what a run record is; so its input became all of HDF5
(a graph with links, types JSON cannot hold, names that are code in JavaScript, other files) while its only reader needs six strings.

"Attack the family" (ATTACKS 21) is the right rule, and against an open contract it has no end: every README sentence about the
walk is a claim to break. Read from the code and not run, more are waiting: a record that is the string `(not copied: ...)` is shown
by Studio as "named, not copied"; NaN and the string "NaN" are one value after the copy, under "as recorded"; the budgets count
nodes, not bytes, so many records linked to one long string read it once each. And one cost no verifier raised, because it is the
design working: scIntegrate's record holds `argv` and `input`, the producing machine's paths, and they go into a shareable bundle.

## C. The designs
**1. The generic walk, hardened further (the sixth fix-up as briefed).** Removes the last three failures, each by a new mechanism
(a link resolver on every lookup, null-prototype records), and nothing by construction: the stopped work adds 272 lines to a section
of about 480. Gives up nothing on paper; it still misses scProfile's record and shows scAnno's column records as runs. Costs no
format or Studio change, one more re-check and, by this history, another. Still possible: the three above and the next feature.

**2. A closed reader (recommended).** Discovery stays (entries named provenance, the schema rule, `uns/harness_run`), capped at 64
records and counted past that. From each record the converter asks for six names and keeps a value only if it is a scalar string of
256 characters or fewer. The output object is built from the converter's own literal keys. A record with none of the six is not
written as a record; a note names it.
- Removes by construction: depth and node budgets (at most 64 x 6 reads); hard-link graphs, cycles, shared groups and identity
  (nothing is walked, so nothing is reached twice); the indented-bytes measure and the fill order (the section is a few kilobytes
  at most); structured arrays, float16 and references (not a short string: said, not shown); `__proto__` and integer-like keys (no
  key comes from the file); the sentinel in band; the paths in `argv`. Not the external link: that is the open's (section E).
- Gives up every field outside the six: scIntegrate's other 28 of 32 (arguments, package versions, method settings, seed, design);
  about 14 fields of scQC's flag declaration (they stay in the object); scAnno's column records whole; of scProfile nothing.
- Costs. Lab: about 450 lines out and 80 in; about 45 of 508 checks and two fixtures (`uns-records`, `uns-unreadable`) pin the walk
  and are retired or restated; the committed fixture's digest changes, in `meta.json`'s `run` and notes and `collection.json`'s size
  and hash only. Format: `{searched, records: [{path, record}]}` kept, `record` a flat object. Studio: no reader change (a flat
  object is its "copied" kind; bundles the live Lab already wrote still open), one sentence of card copy. Writers: none.
- Still possible: a file can claim any tool and commit (true of every design: recorded, never vouched for). A very long string
  under one of the six names is read once before it is refused, so the first oversize value ends the section's reading.

**3. One JSON string per tool, copied as text to a size and never walked.** Removes what design 2 removes and keeps a whole record
up to the cap. Gives up every object already written, since no tool writes such a string; `uns/scqc` cannot become one, because
scAnno reads its fields and digest as a contract. Costs four writers, or one (the harness at seal time: GAP-P20 as decided), and
Studio parsing the text. Still possible: the text is opaque to Lab, so paths travel; deep JSON is Studio's to refuse.
**4. No section, a sidecar file handed to the converter.** Removes all HDF5 reading; gives up the self-contained object (0001b, B2).

## D. Recommendation: redesign as the closed reader (design 2), and promise less
1. **One file, at the open, for the whole converter.** Keep from the sixth fix-up only its seal: while the input is open, HDF5 can
   open no other file. Proof: `c_ext_other` gives one bundle whatever the other file holds; ordinary soft links still read.
2. **Replace `plain` and the fill logic of `readRun` with the closed reader.** Same bundle shape, so Studio's reader is untouched.
3. **The docs, in these words:** "The lab carries the run's identity, not the run's record. From each record it finds it reads six
   fields by name (`tool`, `version`, `commit`, `stage`, `run_key`, `job`) and keeps each one stored as a string of 256 characters
   or fewer, unchanged and under its own name. Nothing else in a record is read: its other fields are counted and stay in the
   object. An absent field is not shown; a longer one, or one that is not a string, is said so."
4. **Studio, in its next wave, copy only:** the card says it shows the run's identity fields.
5. **GAP-P20, as design 3 inside the same rule.** The harness writes `uns/harness_run`, one JSON string listing the stages with the
   six fields; Lab reads the text to 65,536 bytes, parses it once inside a `try`, and takes the six names from at most 32 stages.
   This is where `stage` and `run_key` come from; no work on the reader produces them.
6. **One verification of the new contract.** Its attack list is short: a link, a long value, a wrong type, many records, a name.

**The sixth fix-up: reduce it; do not build it as briefed.** Its seal stays (step 1; uncommitted and untested as it stands). Its
link resolver and null-prototype records are not built: the closed reader leaves them nothing to protect. To the builder:
- HDF5 may open only the input, in the command and in the worker; what fails for that reason is named once, by entry.
- The run section reads six named scalar strings from each record it finds, at most 64 records: no walk, no budgets.
- Rewrite the README section in the words above, retire the walk's tests and fixtures, and predict the new digest.

## E. The same cause elsewhere in the converter
- **The open-ended walk: nowhere else.** `obs`, `var`, `X`, `layers` and `obsm` are read by name, one level down, into sized arrays.
- **The link out of the file: everywhere.** Every lookup in the scan follows an external link, so another file's matrix, column or
  embedding can enter a bundle as the object's own, as a run record did. Step 1 closes all of them; a fix in the run section, one.
- **A name from the file used as a JavaScript key: one place found.** `replicatesPerCondition` in `scan.ts` keys a plain object by
  the condition's levels; a level named `__proto__` would drop out of the replicate counts. Read, not run: a gap to register.

## What was not read or run
No probe was re-run and no code executed: the failures listed as waiting in B, the level-name defect in E and the seal's effect are
readings of the code. The writers' record sizes come from their code, not from an object. Not read: Lab's `build.ts`, `rds.ts` and
worker beyond an outline; Studio's two run-card tests; the first four verifiers' own notes (only the wave file's account of them).
