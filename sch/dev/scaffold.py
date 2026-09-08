"""A new extension, started from the repository's own template rather than from a memory of one.

WHAT IT WRITES AND WHAT IT REFUSES TO WRITE. It writes the artifact, a SPEC.md the author fills
in, and a test stub. It does NOT edit the registry. Text-editing a Python dict literal works
until the file is laid out differently from the way the editor guessed, and a scaffolder that
half-registers something has created a defect that looks like a typo. So it prints the edit and
`sch dev check` verifies, by parsing, that it landed. The tool that writes is not the tool that
checks, which is the only arrangement where the check is worth running.

SPEC.md IS NOT PAPERWORK. Every extension in this family carries three claims that cannot be
recovered from its code: what it SEES of the data, what it CANNOT SHOW, and what would make it
wrong. An agent that writes the code first and the claims afterwards writes claims that describe
the code. Writing them first is the cheapest available design review, and it is the difference
between a mechanism that declares its limits and one that has them.
"""
from __future__ import annotations

from pathlib import Path

from . import points as pts

SPEC = """# {point}: {name}

> Written BEFORE the code. If a line here changes while the code is being written, that is a
> finding about the design, not an edit to tidy away - say what changed and why in the PR.

## The question it answers
<one sentence a reader who is not you would recognise as their question>

## What it SEES
<the labels, design columns and held-out data it is given. A mechanism that sees the design can
 be led by it; a mechanism that sees held-out labels cannot be evaluated on them.>

## What it CANNOT SHOW
<the questions a reader will bring to its output that its output does not answer. This is the
 field readers use and authors skip.>

## What would make it wrong
<the condition under which its answer is misleading rather than merely imprecise>

## state_version
1 - <what the numbers are, so a later bump can say what changed about them>

## How it is proved
- [ ] `sch dev check --point {point} --name {name}` - contract, both fixture shapes, leak, baseline
- [ ] a pre-declared reproduction against a reference run, if this touches numbers a run has quoted
"""

TEST = '''"""What only THIS {point} must satisfy.

The GENERIC contract - that it is registered, that it declares what it must, that it runs on both
fixture shapes, that it leaks nothing, that its numbers have not moved - is checked by
`sch dev check --point {point} --name {name}` and is not repeated here. Nothing in this file
should import the harness: these repositories vendor what they share (each carries its own
`status.py` rather than importing one) so that a suite runs wherever the tool runs.

What belongs here is the claim in SPEC.{name}.md that a generic contract cannot see.
"""


def test_the_claim_in_its_spec():
    """<the one thing SPEC.{name}.md promises that no generic check can verify>"""
    raise AssertionError(
        "write this before writing the mechanism. A test added afterwards tests what the code "
        "does; a test written first tests what it was for.")
'''


def new(root, point_name: str, name: str, *, force: bool = False) -> dict:
    doc = pts.load(root)
    pt = pts.point(doc, point_name)
    base = Path(doc["_root"])
    if not name.replace("_", "").isalnum():
        raise ValueError(f"{name!r}: a name is letters, digits and underscores - it becomes a key, "
                         f"a directory and a filename")
    already = pts.existing(doc, point_name)
    if name in already and not force:
        raise ValueError(f"{doc['tool']} already registers a {point_name} called {name!r}")

    written, skipped = [], []

    def put(path: Path, text: str):
        if path.exists() and not force:
            skipped.append(str(path.relative_to(base)))
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        written.append(str(path.relative_to(base)))

    lives = Path(pt["lives"])
    target = base / (lives / f"{name}.py" if (base / lives).is_dir() else lives)
    # A TOOL THAT HAS ITS OWN SCAFFOLDER KEEPS IT. scProfile's writes a rich, commented template
    # from its own knowledge of the format; this one would have written a one-line stub beside
    # it. Both were pointed at - the declaration said "`scprofile scaffold` is the right first
    # command" while `sch dev map` printed "`sch dev new POINT NAME` starts one" - and a newcomer
    # had to guess which. Declaring `scaffold_command` removes the choice: the suite runs nothing
    # and writes no skeleton, and contributes the one thing the tool's own scaffolder does not,
    # which is the SPEC written before the code.
    own = pt.get("scaffold_command")
    if own:
        own = str(own).replace("{name}", name)
    elif pt.get("template"):
        tpl = base / pt["template"]
        if not tpl.is_file():
            raise ValueError(f"{doc['tool']} declares template {pt['template']} for {point_name}, "
                             f"and it does not exist")
        put(target, tpl.read_text(encoding="utf-8").replace("{name}", name).replace("{NAME}", name.upper()))
    elif (base / lives).is_dir():
        put(target, f'"""{name}: <one line>. Started from {pt.get("example") or "the point declaration"};\n'
                    f'see SPEC.md beside it before writing anything here."""\n')

    spec_dir = target.parent if target.suffix else base / lives
    put(spec_dir / f"SPEC.{name}.md", SPEC.format(point=point_name, name=name))
    tdir = base / "tests"
    if tdir.is_dir():
        put(tdir / f"test_{point_name}_{name}.py", TEST.format(point=point_name, name=name))

    edits = []
    for reg in pt.get("register") or []:
        where = (f"add {name!r} to {reg['table']} in {reg['file']}" if reg.get("table")
                 else f"add a line to {reg['file']} matching  "
                      + reg["pattern"].replace("{name}", name))
        edits.append(where + (f"  (beside {pt['example']!r})" if pt.get("example") else ""))
    return {"tool": doc["tool"], "point": point_name, "name": name,
            "scaffold_command": own,
            "written": written, "skipped": skipped, "register": edits,
            "must_declare": pt.get("must_declare") or [],
            "example": pt.get("example"), "proves": pt.get("proves"),
            "cannot_prove": pt.get("cannot_prove"),
            "next": ([f"this tool scaffolds its own: {own}"] if own else [])
                    + [f"fill in {Path(spec_dir).name}/SPEC.{name}.md before writing the mechanism",
                     *[f"registry: {e}" for e in edits],
                     f"then: sch dev check --point {point_name} --name {name}"]}
