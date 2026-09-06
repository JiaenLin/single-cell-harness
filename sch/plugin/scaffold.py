"""`sch plugin new <name> --profile P [--wraps TOOL] [--language python|r]`.

Writes a directory with every required field present and the unanswerable ones marked TODO.
A manifest containing TODO fails `sch plugin validate`: the scaffold is deliberately not
runnable until the seven questions in docs/AUTHORING.md are answered.
"""
from __future__ import annotations

from pathlib import Path

from .. import CONTRACT

MANIFEST = """contract: "{contract}"
profile: {profile}
name: {name}
version: 0.1.0
summary: TODO one line, in the terms a user of the wrapped tool would recognise
when_to_use: >
  TODO when this answers something nothing already mounted answers

class: method
layer: stack                    # TODO: a view of existing data, or genuinely new numbers? when in doubt, checkpoint
reversible: true
state_version: 1
{wraps}
inject: [dataset]
needs: []                       # TODO data capabilities, e.g. column/{{label}}
provides: []                    # TODO what it contributes; it is held to this
optional: []
sourceable: []
sees: []                        # an empty list is a positive claim

language: {language}
entry: {entry}
needs_env: false
executor: {{cost: low}}
no_runtime_invariant: TODO name the relationship this plugin owns while it runs, or write invariant.py

cannot_show:
  - TODO what the output does NOT establish, in the reader's words
"""

RUN_PY = '''#!/usr/bin/env python3
"""Entry point. Reads in.json (argv[1]), writes out.json in out_dir. Stdlib only unless locked."""
import importlib.util, os, sys

spec = importlib.util.spec_from_file_location("protocol", os.environ.get("SCH_PROTOCOL", "protocol.py"))
protocol = importlib.util.module_from_spec(spec); spec.loader.exec_module(protocol)

run = protocol.Run.from_argv()
# TODO: read run.data (the materialised view), compute, contribute:
#   run.column("name", {identity: value}); run.mask("name", {identity: keep}, reason="...")
#   run.number("key", value)  -> report-visible only through the event stream
sys.exit(run.finish(headline="TODO"))
'''

RUN_R = '''#!/usr/bin/env Rscript
# Entry point. Reads in.json (argv[1]), writes out.json in out_dir.
args <- commandArgs(trailingOnly = TRUE)
inp <- jsonlite::fromJSON(args[1])
out <- list(contract = inp$contract, plugin = inp$plugin, version = inp$plugin_version,
            status = "ok", headline = "TODO", columns = list(), masks = list(), tables = list(),
            figures = list(), answer = list(), absent = list(), caveats = list(), numbers = list())
jsonlite::write_json(out, file.path(inp$out_dir, "out.json"), auto_unbox = TRUE)
'''

README = """# {name}

## What it does
TODO the operation, in the terms a user of the wrapped tool would recognise.

## Report surface
TODO every number, table and figure a reader could quote, and the cannot_show line each travels with.

## Cost
TODO what it costs to run and what it costs to unmount: declared executor cost, and what invalidates.

## Known limitations
TODO written last and honestly. An empty section is the plugin telling a reader it has not been used in anger.
"""


def scaffold(name: str, dest, profile: str, wraps: str | None = None, language: str = "python") -> Path:
    d = Path(dest) / name
    d.mkdir(parents=True, exist_ok=False)
    entry = "run.py" if language == "python" else "run.R"
    wraps_block = ""
    if wraps:
        wraps_block = f"wraps:\n  tool: {wraps}\n  version: \"TODO\"\n  homepage: TODO\n  license: TODO\n  cite: \"TODO\"\n"
    (d / "plugin.yml").write_text(MANIFEST.format(contract=CONTRACT, profile=profile, name=name,
                                                  wraps=wraps_block, language=language, entry=entry))
    (d / entry).write_text(RUN_PY if language == "python" else RUN_R)
    (d / entry).chmod(0o755)
    (d / "README.md").write_text(README.format(name=name))
    return d
