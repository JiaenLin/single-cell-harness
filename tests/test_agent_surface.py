#!/usr/bin/env python3
"""Can an agent do what the documentation tells it to do?

Every finding here started as a real one. `sch dev map --json` is the form the skill, the README
and `docs/DEVELOPING.md` all give, and it exited 2 with "unrecognized arguments" because `--json`
was declared only before the subcommand - so an agent following the documentation failed on its
first machine-readable call, and the form that worked was written down nowhere.

That is not a typo, it is a class: the documentation and the parser are two descriptions of one
interface, maintained by hand, and nothing compared them. These tests compare them.
"""
from __future__ import annotations

import json
import re
import shlex
import subprocess
import sys
import unittest
from pathlib import Path

from helpers import ROOT

# EVERY DOCUMENT AN AGENT FOLLOWS, and `plugin-maker` was not on this list. It is the skill for
# converting somebody else's tool into a plugin, so it is nearly all commands - and none of them
# was checked against the parser. It also spent months describing a six-file directory layout that
# `scprofile/plugin.py` had already replaced, which this check cannot catch but the omission is the
# same shape: a document nobody verifies drifts from the tool it documents.
DOCS = ["skills/harness-developer/SKILL.md", "skills/harness-agent/SKILL.md",
        "skills/plugin-maker/SKILL.md",
        "docs/DEVELOPING.md", "README.md", "docs/CHILD_CONFORMANCE.md"]

# A documented command is written for a reader, so it carries placeholders. These stand in for
# them; the test asks whether the SHAPE parses, not whether the paths exist.
STAND_IN = {"DIR": "/tmp/x", "REPO": "/tmp/x", "POINT": "plugin", "NAME": "n", "P": "plugin",
            "N": "n", "RUN": "/tmp/x", "RUNDIR": "/tmp/x", "REFRUN": "/tmp/x", "FILE": "/tmp/f",
            "NEW": "/tmp/x", "REF": "/tmp/x", "Q": "short", "S": "select=1:ncpus=1",
            "TEXT": "why", "PERSON": "p", "SCRIPT.py": "/tmp/s.py", "PLUGIN": "pl",
            "STACK": "/tmp/x", "NEWDIR": "/tmp/x", "K": "kind", "L": "label", "PROBE": "pr"}


def _blocks(text):
    """The fenced code blocks - where a runnable command lives. A command mentioned inline in a
    sentence is a reference to a command; a command in a block is an instruction to run one, and
    only the second has to survive being typed verbatim."""
    out, inside, buf = [], False, []
    for line in text.splitlines():
        if line.strip().startswith("```"):
            if inside:
                out.append("\n".join(buf)); buf = []
            inside = not inside
            continue
        if inside:
            buf.append(line)
    return out


def _commands():
    """Every `sch ...` command a document shows in a block, with placeholders filled in."""
    seen = {}
    for rel in DOCS:
        for block in _blocks((ROOT / rel).read_text(encoding="utf-8")):
            # Join continuation lines, collapsing the next line's indentation - otherwise it
            # becomes a run of spaces that the column split below mistakes for a separator, and
            # the command is truncated at exactly the point where its required arguments start.
            block = re.sub(r"\s*\\\s*\n\s*", " ", block)
            for raw in re.findall(r"^\s*(sch .+)$", block, re.M):
                # COLUMNS FIRST, THEN NOTATION. These blocks lay commands out as
                # `command<two or more spaces>description`; stripping `[--optional]` before the
                # split collapses the separator and swallows the description into the command.
                line = re.split(r"\s{2,}", raw.strip(), 1)[0].strip()
                line = re.sub(r"\[[^\]]*\]", " ", line)        # [--optional] is notation
                if "..." in line or "…" in line or "|" in line:
                    continue
                line = re.sub(r"<[^>]+>", lambda m: STAND_IN.get(m.group(0)[1:-1].upper(), "/tmp/x"), line)
                line = re.sub(r"\{[^}]+\}", "/tmp/x", line)
                # A documented command is written to be typed into a shell, so it is split the
                # way a shell would: `--predict 'why this run'` is one argument, not four.
                try:
                    toks = shlex.split(line, comments=True)
                except ValueError:
                    continue
                out = tuple(STAND_IN.get(t, t) for t in toks[1:])
                if not out:
                    continue
                # THE TOKENS, NOT A JOINED STRING. Re-splitting a rejoined command breaks any
                # argument that legitimately contains a space - `--predict 'why this run'` became
                # five arguments and the parser rejected a command that is perfectly valid.
                seen.setdefault(out, rel)
    return seen


class DocumentedCommandsParse(unittest.TestCase):
    def test_every_sch_command_in_the_docs_is_accepted_by_the_parser(self):
        """Not that it succeeds - that the parser recognises it. A documented command the parser
        rejects is worse than an undocumented one: it costs the agent a run to find out."""
        from sch.cli import build_parser
        bad = []
        for argv, where in sorted(_commands().items()):
            try:
                build_parser().parse_args(list(argv))
            except SystemExit:
                bad.append(f"{where}: sch {' '.join(argv)}")
        self.assertEqual(bad, [], "documented commands the parser rejects:\n  " + "\n  ".join(bad))

    def test_the_docs_show_at_least_the_whole_dev_surface(self):
        """A subcommand nobody documented is a subcommand no agent will use."""
        shown = " ".join(" ".join(a) for a in _commands())
        for sub in ("map", "new", "fixture", "check", "baseline", "job"):
            self.assertIn(f"dev {sub}", shown, f"`sch dev {sub}` appears in no document")


class JsonWorksInBothPositions(unittest.TestCase):
    """`--json` is global, so it must be accepted before or after the subcommand - and mean the
    same thing in both. The subparser's default would otherwise overwrite the parent's value and
    silently turn JSON back off."""

    def _out(self, argv):
        r = subprocess.run([sys.executable, "-m", "sch", *argv], cwd=str(ROOT),
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, f"sch {' '.join(argv)} exited {r.returncode}: {r.stderr[-300:]}")
        return r.stdout

    def test_dev_map(self):
        before = self._out(["--json", "dev", "map"])
        after = self._out(["dev", "map", "--json"])
        self.assertEqual(json.loads(before), json.loads(after))
        self.assertEqual(json.loads(before)["tool"], "sch")

    def test_conform(self):
        self.assertEqual(self._out(["--json", "conform", "."]), self._out(["conform", ".", "--json"]))

    def test_the_flag_after_the_subcommand_actually_turns_json_on(self):
        """The failure this guards against is silent: a subparser default of False overwriting a
        True set before the subcommand, so the flag is accepted and does nothing."""
        self.assertIn('"tool"', self._out(["dev", "map", "--json"]))


class MapIsEnoughToActOn(unittest.TestCase):
    """An agent reads `sch dev map --json` and must be able to form the next command from it
    without guessing. Anything it has to guess is a place it will guess wrong."""

    def setUp(self):
        r = subprocess.run([sys.executable, "-m", "sch", "dev", "map", "--json"],
                           cwd=str(ROOT), capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr[-400:])
        self.doc = json.loads(r.stdout)

    def test_it_names_the_tool_and_where_the_declaration_lives(self):
        self.assertIn("tool", self.doc)
        self.assertTrue(Path(self.doc["path"]).is_file())

    def test_every_point_says_what_it_proves_and_what_it_cannot(self):
        for name, pt in self.doc["points"].items():
            for field in ("what", "lives", "proves", "cannot_prove"):
                self.assertTrue(pt.get(field), f"{name} has no {field}")

    def test_every_point_reports_what_is_already_registered(self):
        for name, pt in self.doc["points"].items():
            self.assertIn("registered", pt, f"{name} does not say what already exists")


if __name__ == "__main__":
    unittest.main()


def _path_exists(parser, toks):
    """Does this sequence of words name a real subcommand path?"""
    import argparse as _a
    for t in toks:
        subs = [x for x in parser._actions if isinstance(x, _a._SubParsersAction)]
        if not subs:
            return False
        if t not in subs[0].choices:
            return False
        parser = subs[0].choices[t]
    return True


class ErrorsNameCommandsThatExist(unittest.TestCase):
    """An error message that tells an agent to run something is an instruction, and an
    instruction to run a command that does not exist costs a round trip to discover.

    `sch dev map` without a declaration said "`sch dev map --init` writes a first one". There was
    no --init. The flag exists now, but the class of defect is what matters: a message and a
    parser are two descriptions of one interface, and only one of them is executable.
    """

    def test_every_sch_command_in_a_message_parses(self):
        """AND IN EVERY DOCUMENT AN AGENT FOLLOWS, not only in the source.

        This scanned `sch/**/*.py` alone, so the messages the tool prints were checked and the
        SKILLS were not - and a skill is nearly all commands, written for an agent that will run
        them verbatim. `skills/plugin-maker/SKILL.md` had never had a single one checked.
        """
        from sch.cli import build_parser
        bad = []
        paths = sorted((ROOT / "sch").rglob("*.py")) + [ROOT / d for d in DOCS]
        for path in paths:
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            for cmd in re.findall(r"`sch ([a-z][^`\n]*)`", text):
                cmd = re.sub(r"<[^>]*>", "X", cmd)
                cmd = re.sub(r"\{[^}]*\}", "X", cmd)
                cmd = re.sub(r"\b(FILE|DIR|RUNDIR|REFRUN|NAME|POINT|REPO|NEW|REF|Q|S|TEXT|PATH)\b",
                             "X", cmd)
                if "..." in cmd or "|" in cmd:
                    continue
                try:
                    toks = shlex.split(cmd)
                except ValueError:
                    continue                      # unbalanced quotes in prose, not a command
                if not any(t.startswith("-") or t == "X" for t in toks):
                    # A bare `sch dev new` in a sentence is a reference to a command, not an
                    # instruction to run one. What must be right is that the SUBCOMMAND PATH
                    # exists - a message naming `sch dev sprocket` would be just as wrong.
                    self.assertTrue(_path_exists(build_parser(), toks),
                                    f"{path.relative_to(ROOT)}: `sch {cmd}` is not a subcommand")
                    continue
                try:
                    build_parser().parse_args(toks)
                except SystemExit:
                    bad.append(f"{path.relative_to(ROOT)}: sch {cmd}")
        self.assertEqual(bad, [], "messages naming commands the parser rejects:\n  " + "\n  ".join(bad))


class ExitCodesSeparateFailedFromCouldNotRun(unittest.TestCase):
    """0 passed, 2 failed, 3 nothing could be run. The third is the one that was missing: a check
    whose every tier skipped exited 0, which an agent reads as proof."""

    def _code(self, argv, **env):
        import os
        return subprocess.run([sys.executable, "-m", "sch", *argv], cwd=str(ROOT),
                              capture_output=True, text=True,
                              env={**os.environ, **env}).returncode

    def test_green_is_zero(self):
        self.assertEqual(self._code(["dev", "check", "--only", "contract"]), 0)

    def test_a_failing_tier_is_two(self):
        self.assertEqual(self._code(["conform", "/tmp"]), 2)

    def test_no_declaration_is_three_not_two(self):
        self.assertEqual(self._code(["dev", "map", "--root", "/tmp"]), 3)

    def test_every_tier_skipped_is_three_not_zero(self):
        """The failure this guards against is a green that proved nothing."""
        self.assertEqual(self._code(["dev", "check", "--only", "baseline"]), 3)
