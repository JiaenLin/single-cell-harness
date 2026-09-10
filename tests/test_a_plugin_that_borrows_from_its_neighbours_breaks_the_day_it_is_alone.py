#!/usr/bin/env python3
"""A plugin that borrows from its neighbours breaks the day it is alone, and nothing said so.

THE DEFECT THIS PREVENTS, AND IT COST AN END-TO-END RUN. A plugin in one of the repositories this
suite serves had spent its whole life inside a SEVEN-MEMBER environment. Unplug the other eight
plugins and the resolver correctly gives it an environment of its own - the group's name hashes
the union of its members' requirements, so a group of one is a different directory - and two of
its drawing paths died in it:

    native plot geneExpression FAILED: there is no package called 'Seurat'
    net embedding FAILED: Cannot find UMAP ... (umap-learn)

54 panels of 711, three draw sites across 18 units, and the plugin's SELFTEST STILL PASSED: a
selftest proves the plugin's imports resolve, and neither package is imported at module scope -
they are reached only when a particular panel is drawn. The plugin had met the error before and
misread it as the wrong interpreter rather than a missing declaration, which inside a shared
environment is an honest mistake, because both of those look exactly like "it works here".

The question is answerable with NO RUN AND NO ENVIRONMENT BUILT: resolve the plugin alone, resolve
it with its family, and subtract. `sch/dev/extract/shared_env.py` does that through the
repository's own resolver, reached through the repository's own declaration.

WHAT THIS FILE RATCHETS, AND WHY EACH ONE IS HERE RATHER THAN HOPED FOR.

  THE SUBTRACTION ITSELF, in both directions, because a check that reported the union rather than
  the difference would call every member of a seven-member environment a borrower of everything.

  THAT A LOAN IS NOT AN ALARM. A seven-member environment lends its members over a hundred names
  each and almost none of them is ever touched. The rows a person reads are the narrowed ones, and
  a version of this that printed "110 undeclared dependencies" would be a false-alarm generator on
  every plugin in the family at once.

  THAT A NAME IS SEARCHED ONLY IN THE TEXT ITS SPELLING BELONGS TO. MEASURED: searched across the
  whole plugin file, the channel entries `r-matrix`, `r-shape`, `r-base` and `r-cluster` matched
  the English words `matrix`, `shape`, `base` and `cluster` in seven plugins' Python comments - a
  false alarm on seven of nine plugins from one unscoped regex.

  THAT LOADED AND MENTIONED ARE DIFFERENT ANSWERS. One of them is a dependency; the other is a
  sentence. Folding them together loses the whole point of narrowing.

  THAT A ONE-MEMBER GROUP IS A POSITIVE ANSWER AND NOT A SILENCE, the way `complete=False` is a
  first-class answer everywhere else in this family.

  THAT IT CANNOT WRITE, and that no repository's vocabulary is in the module.

THE FIXTURE IS WRITTEN OUT AND POINTS AT NO REAL REPOSITORY, deliberately - and its vocabulary is
chosen to share no word with any repository this suite serves, so a maker that had quietly learnt
one repository's field names could not pass here.
"""
from __future__ import annotations

import inspect
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sch.dev import points as P                                           # noqa: E402
from sch.dev.extract import shared_env as SE                              # noqa: E402

# ------------------------------------------------------------------------------- the fixture
#: A repository whose resolver, catalogue, member list and requirement fields are all called
#: something no repository in this family calls them. If a word of this appears in `sch/`, the
#: maker has learnt a repository instead of reading one.
CATALOGUE = '''
class Item:
    def __init__(self, label, family, needs):
        self.label, self.family, self.needs = label, family, needs


def all_of_them():
    return {i.label: i for i in (
        Item("alpha", "A", {"wheels": {"numsy": ">=1"}}),
        Item("beta", "A", {"wheels": {"tabler": ">=1"},
                           "channelled": ["lang-plotters"],
                           "other_language": ["owner/Charty@abc123"]}),
        Item("gamma", "B", {"wheels": {"solo": ">=1"}}),
        Item("delta", "C", {}),
    )}
'''

GROUPER = '''
import hashlib


class Env:
    """One environment and everybody in it. Members share when they name the same family."""

    def __init__(self, members):
        self.sharers = sorted(m.label for m in members)
        self.wheels, self.channelled, self.other_language = {}, [], []
        for m in members:
            self.wheels.update(m.needs.get("wheels") or {})
            for c in m.needs.get("channelled") or []:
                if c not in self.channelled:
                    self.channelled.append(c)
            for c in m.needs.get("other_language") or []:
                if c not in self.other_language:
                    self.other_language.append(c)

    @property
    def tag(self):
        key = repr((sorted(self.wheels.items()), sorted(self.channelled),
                    sorted(self.other_language)))
        return "env-" + hashlib.sha256(key.encode()).hexdigest()[:8]


def into_envs(items):
    fams = {}
    for it in items:
        if not it.needs:
            continue
        fams.setdefault(it.family, []).append(it)
    return [Env(ms) for _f, ms in sorted(fams.items())]
'''

DECL = '''
tool: demopkg
devpoints: 1
tests:
  command: ["{python}", "-c", "print(1)"]
points:
  widget:
    what: a widget
    lives: widgets
    proves: it runs
    cannot_prove: that it is right
    convert:
      placeholder: "TODO"
      upstream: wraps.tool
      stages:
        - {name: contract, fills: [inject]}
      environment:
        catalogue: catalogue.all_of_them
        plugin_named: label
        groups: grouper.into_envs
        environment_named: tag
        shared_by: sharers
        holds:
          - field: wheels
            what: wheel packages
            spelled:
              - {as: "^(.+)$", written_in: host}
          - field: channelled
            what: channel packages
            spelled:
              - {as: "^(.+)$", written_in: host}
              - {as: "^lang-(.+)$", written_in: embedded}
          - field: other_language
            what: other-language packages
            spelled:
              - {as: "^(?:.*/)?([^/@=]+)", written_in: embedded}
'''

#: THE PLUGIN THAT NAMES THREE LENT NAMES IN THREE DIFFERENT PLACES, which is what makes the
#: language scoping testable at all. `tabler` is a host name in its Python. `Charty` is an
#: other-language name and is written in the embedded script, where such a name belongs.
#: `plotters` is ALSO an other-language name and is written ONLY in the Python - so it must not
#: be a row, and that is the ratchet against the unscoped scan that matched English words.
ALPHA = '''
PLUGIN = {"api": 1}

# We considered plotters for this and did not use it. tabler is what the neighbour reaches for,
# and solo is a name out of an environment this widget never touches.

_SCRIPT = r"""
draw <- function(name, expr, legend = "") {
  # Charty would draw this one, if anything here reached for it
  png(name)
  print(expr)
  dev.off()
}
"""


def run(ctx):
    return 1
'''

#: The plugin that IMPORTS what its neighbour declares. `numsy` is alpha's, not beta's, and beta
#: will lose it the day alpha is unplugged.
BETA = '''
PLUGIN = {"api": 1}

import numsy


def run(ctx):
    return numsy
'''

GAMMA = '''
PLUGIN = {"api": 1}


def run(ctx):
    return 1
'''

DELTA = '''
PLUGIN = {"api": 1}


def run(ctx):
    return 1
'''


class Repo:
    """A throwaway repository with a resolver of its own."""

    def __init__(self, decl=DECL, catalogue=CATALOGUE, grouper=GROUPER, plugins=None):
        self.d = Path(tempfile.mkdtemp())
        pkg = self.d / "demopkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "catalogue.py").write_text(catalogue)
        (pkg / "grouper.py").write_text(grouper)
        (self.d / "widgets").mkdir()
        for name, src in (plugins or {"alpha": ALPHA, "beta": BETA,
                                      "gamma": GAMMA, "delta": DELTA}).items():
            (self.d / "widgets" / f"{name}.py").write_text(src)
        (self.d / "DEVPOINTS.yaml").write_text(decl)

    def survey(self, **kw):
        return SE.survey(P.load(self.d), "widget", str(self.d), **kw)

    def one(self, name, **kw):
        return {x.plugin: x for x in self.survey(**kw)}[name]

    def close(self):
        shutil.rmtree(self.d, ignore_errors=True)


class TheSubtraction(unittest.TestCase):
    """Resolve alone, resolve with the family, and the difference is the loan."""

    @classmethod
    def setUpClass(cls):
        cls.repo = Repo()
        cls.rows = {x.plugin: x for x in cls.repo.survey()}

    @classmethod
    def tearDownClass(cls):
        cls.repo.close()

    def test_the_family_resolves_and_every_plugin_gets_an_answer(self):
        self.assertEqual(sorted(self.rows), ["alpha", "beta", "delta", "gamma"])
        for x in self.rows.values():
            self.assertTrue(x.complete, x.why_not)

    def test_a_sharer_is_lent_exactly_what_the_other_member_declared(self):
        """The DIFFERENCE and not the union. A check that reported what the environment holds
        would call beta a borrower of its own `tabler`, and the number it printed would be the
        same for every member of the group - which is the shape of an answer nobody can act on."""
        alpha, beta = self.rows["alpha"], self.rows["beta"]
        self.assertEqual(len(alpha.members), 2)
        self.assertEqual(alpha.members, ["alpha", "beta"])
        # alpha is lent beta's three entries, in the four spellings the declaration gives them.
        self.assertEqual(alpha.lent, 4)
        # beta is lent alpha's one, and NOT its own.
        self.assertEqual(beta.lent, 1)

    def test_the_two_environments_are_actually_different_directories(self):
        """The whole premise: a group of one is not the group it was a member of. If the two
        resolutions gave the same environment there would be nothing to subtract."""
        self.assertNotEqual(self.rows["alpha"].environment, self.rows["gamma"].environment)
        self.assertTrue(self.rows["alpha"].environment)

    def test_the_two_halves_of_the_by_field_ratio_count_the_same_thing(self):
        """FOUND BY RUNNING IT. Counting lent NAMES against declared ENTRIES printed "100 of 51"
        on five of nine plugins, because one entry can be spelled more than one way and each
        spelling is a name a plugin might write. A ratio whose halves are different units is not
        a ratio, and a reader who noticed would stop believing the rest of the block."""
        for x in self.rows.values():
            for field, (n, held, _what) in x.by_field.items():
                self.assertLessEqual(n, held, f"{x.plugin}/{field}: {n} lent of {held} held")
            self.assertEqual(sum(n for n, _h, _w in x.by_field.values()), x.lent)

    def test_the_loan_is_broken_down_by_field_and_a_field_that_lends_nothing_says_so(self):
        """A TOTAL HIDES THE ONE ANSWER THAT IS CERTAIN. Where a field lends zero, the two
        resolutions agree over that whole field - so anything that still goes missing there was
        never in anybody's declaration, which is the half of the original finding that no
        subtraction can reach."""
        beta = self.rows["beta"]
        lent_by_field = {f: n for f, (n, _held, _what) in beta.by_field.items()}
        self.assertEqual(lent_by_field["other_language"], 0)
        self.assertEqual(lent_by_field["wheels"], 1)
        out = SE.format_report([beta], "widget")
        self.assertIn("0 of the 1 other-language packages are lent", out)
        self.assertIn("nothing in this", out)


class TheNarrowing(unittest.TestCase):
    """Which lent names the plugin's own source writes down, and how strong that evidence is."""

    @classmethod
    def setUpClass(cls):
        cls.repo = Repo()
        cls.rows = {x.plugin: x for x in cls.repo.survey()}

    @classmethod
    def tearDownClass(cls):
        cls.repo.close()

    def _named(self, plugin):
        return {r["name"]: r for r in self.rows[plugin].named(SE.LENT)}

    def test_a_lent_name_written_in_the_plugins_own_source_is_a_row(self):
        self.assertIn("tabler", self._named("alpha"))

    def test_an_other_language_name_is_found_inside_the_embedded_script(self):
        """`Charty` is written where such a name belongs - inside the script of another language
        embedded in the plugin - which is where both of the packages that died were written."""
        got = self._named("alpha")
        self.assertIn("Charty", got)
        self.assertEqual(got["Charty"]["written_in"], SE.EMBEDDED)

    def test_the_line_reported_is_a_line_of_the_plugin_file_and_not_of_the_script(self):
        """A draw site reported at "line 3 of the script" is a line number nobody can open."""
        row = self._named("alpha")["Charty"]
        text = (self.repo.d / "widgets" / "alpha.py").read_text().splitlines()
        self.assertIn("Charty", text[row["at"] - 1])

    def test_an_other_language_name_written_only_in_the_host_text_is_NOT_a_row(self):
        """THE RATCHET THE FALSE ALARM PAID FOR. `plotters` is lent to alpha and alpha's Python
        comment says the word - but the declaration says that spelling is written in the embedded
        script, and alpha's script does not say it. Unscoped, this is the scan that turned
        `r-matrix`, `r-shape`, `r-base` and `r-cluster` into rows on seven plugins whose prose
        says matrix, shape, base and cluster in English."""
        self.assertNotIn("plotters", self._named("alpha"))
        self.assertIn("plotters", (self.repo.d / "widgets" / "alpha.py").read_text())

    def test_loaded_and_mentioned_are_different_answers(self):
        """One of them is a dependency and the other is a sentence."""
        self.assertTrue(self._named("beta")["numsy"]["loaded"])
        self.assertFalse(self._named("alpha")["tabler"]["loaded"])
        out = SE.format_report(list(self.rows.values()), "widget")
        self.assertIn("LOADED", out)
        self.assertIn("mentioned", out)

    def test_an_import_written_in_a_comment_is_not_an_import(self):
        """PARSED, NOT GREPPED. The whole value of the LOADED column is that it cannot be earned
        by a comment - and a scan that could be would report a plugin discussing a dependency as
        depending on it."""
        repo = Repo(plugins={"alpha": ALPHA, "beta": BETA.replace("import numsy",
                                                                  "# import numsy"),
                             "gamma": GAMMA, "delta": DELTA})
        try:
            got = {r["name"]: r for r in repo.one("beta").named(SE.LENT)}
            self.assertIn("numsy", got)
            self.assertFalse(got["numsy"]["loaded"])
        finally:
            repo.close()

    def test_a_lent_name_nobody_writes_down_is_counted_and_never_itemised(self):
        """A LENT PACKAGE IS NOT A DEFECT. The row list is the narrowed part; the rest is a
        number with a sentence saying what it does not mean."""
        alpha = self.rows["alpha"]
        self.assertLess(len(alpha.named(SE.LENT)), alpha.lent)
        out = SE.format_report([alpha], "widget")
        self.assertIn("AVAILABLE AND NEVER NAMED", out)
        self.assertIn("exposure, not debt", out)
        self.assertNotIn("lang-plotters", out)

    def test_the_report_never_calls_a_loan_a_defect(self):
        out = SE.format_report(list(self.rows.values()), "widget")
        for word in ("undeclared dependenc", "FAIL", "ERROR", "must declare"):
            self.assertNotIn(word, out, f"{word!r} turns exposure into an alarm")
        self.assertIn("A LENT NAME IS NOT A DEFECT", out)

    def test_the_answer_says_it_is_a_lower_bound(self):
        """The loan is a difference of DIRECT declarations. A built environment also holds every
        transitive dependency of them, and one of the two packages that died was exactly that -
        so an answer that did not say this would be read as complete."""
        out = SE.format_report(list(self.rows.values()), "widget")
        self.assertIn("LOWER BOUND", out)

    def test_the_shown_line_is_the_code_and_not_the_comment_about_it(self):
        """MEASURED on the plugin this was built for: the first mention of the package that
        killed five panels is a comment recounting the error, forty lines above the call that
        reaches for it. A row that showed the comment sent a reader to the paragraph about the
        problem instead of the line with the problem in it."""
        src = ALPHA.replace("# We considered plotters",
                            "# tabler is discussed here first\n# We considered plotters")
        src = src.replace("def run(ctx):\n    return 1",
                          "def run(ctx):\n    return tabler.go()")
        repo = Repo(plugins={"alpha": src, "beta": BETA, "gamma": GAMMA, "delta": DELTA})
        try:
            row = {r["name"]: r for r in repo.one("alpha").named(SE.LENT)}["tabler"]
            self.assertIn("tabler.go()", row["line"])
            self.assertGreater(row["times"], 1)
        finally:
            repo.close()


class TheOtherDirection(unittest.TestCase):
    """A name this plugin reaches for that NOTHING in its own environment asks for."""

    @classmethod
    def setUpClass(cls):
        cls.repo = Repo()
        cls.rows = {x.plugin: x for x in cls.repo.survey()}

    @classmethod
    def tearDownClass(cls):
        cls.repo.close()

    def test_a_name_declared_only_by_another_environment_is_reported_as_a_stray(self):
        """NOT A LOAN - nothing here is lending it. If it is present at all it is present as
        somebody's transitive dependency, which is a worse footing than a loan: a loan at least
        has a declaration behind it that a person can read. This is where the surviving half of
        the original finding lands."""
        stray = {r["name"]: r for r in self.rows["alpha"].named(SE.STRAY)}
        self.assertIn("solo", stray)
        self.assertEqual(stray["solo"]["by"], ["gamma"])

    def test_a_stray_is_not_reported_when_this_environment_provides_the_name_some_other_way(self):
        """The same bare name reached through a different field is still the name being reached
        for. Reported anyway, it sends a reader to declare something they already have."""
        for x in self.rows.values():
            for r in x.named(SE.STRAY):
                held = {n for n, _w in SE.provided(
                    SE.resolve(str(self.repo.d), "demopkg",
                               SE.declared(P.load(self.repo.d), "widget")).of(x.plugin)["contents"]
                    if x.members else {},
                    (SE.declared(P.load(self.repo.d), "widget").get(SE.HOLDS) or []))}
                self.assertNotIn(r["name"], held)

    def test_the_candidate_name_always_comes_from_a_declaration_and_never_from_the_source(self):
        """THE GUARD AGAINST THE FALSE ALARM. This reads a plugin's text only to answer yes or no
        about a name the repository already wrote down. Harvesting package-shaped tokens out of
        an embedded script instead was measured at 116 candidates on one plugin, of which the
        great majority were English words beginning a comment."""
        declared = set()
        land = SE.resolve(str(self.repo.d), "demopkg", SE.declared(P.load(self.repo.d), "widget"))
        holds = SE.declared(P.load(self.repo.d), "widget").get(SE.HOLDS) or []
        for env in land.environments:
            declared |= {n for n, _w in SE.provided(env["contents"], holds)}
        for x in self.rows.values():
            for r in x.rows:
                self.assertIn(r["name"], declared, f"{r['name']!r} was invented from source")


class ThePositiveAnswers(unittest.TestCase):
    """A one-member group lends nothing, and that has to READ as an answer."""

    @classmethod
    def setUpClass(cls):
        cls.repo = Repo()
        cls.rows = {x.plugin: x for x in cls.repo.survey()}

    @classmethod
    def tearDownClass(cls):
        cls.repo.close()

    def test_a_one_member_group_lends_nothing_and_is_told_so(self):
        gamma = self.rows["gamma"]
        self.assertTrue(gamma.complete)
        self.assertTrue(gamma.alone)
        self.assertEqual(gamma.lent, 0)
        self.assertEqual(gamma.rows, [])
        out = SE.format_report([gamma], "widget")
        self.assertIn("ALONE by declaration", out)
        self.assertIn("NOTHING IS LENT", out)
        self.assertIn("not a silence", out)

    def test_a_plugin_needing_no_environment_is_an_answer_and_not_a_gap(self):
        delta = self.rows["delta"]
        self.assertTrue(delta.complete)
        self.assertTrue(delta.needs_none)
        self.assertIn("needs no environment at all", SE.format_report([delta], "widget"))


class ItDegradesHonestly(unittest.TestCase):
    """`complete=False` and a sentence, never an empty answer that reads as a clean one."""

    def test_a_point_that_declares_no_resolver_cannot_say_and_names_the_key_to_add(self):
        repo = Repo(decl=DECL[:DECL.index("      environment:")])
        try:
            rows = repo.survey()
            self.assertEqual(len(rows), 1)
            self.assertFalse(rows[0].complete)
            self.assertIn(SE.KEY, rows[0].why_not)
            self.assertIn("cannot be asked", rows[0].why_not)
            self.assertIn("CANNOT SAY", SE.format_report(rows, "widget"))
        finally:
            repo.close()

    def test_a_resolver_that_cannot_be_reached_is_a_cannot_say_and_not_an_empty_landscape(self):
        """"This repository shares nothing" is the finding a reader would act on, and it is the
        one thing a resolver that would not import cannot establish."""
        repo = Repo(grouper="raise ImportError('no resolver on this checkout')\n")
        try:
            rows = repo.survey()
            self.assertTrue(all(not x.complete for x in rows))
            self.assertIn("could not be reached", rows[0].why_not)
        finally:
            repo.close()

    def test_an_interpreter_that_will_not_start_is_a_cannot_say_and_not_an_empty_landscape(self):
        """FOUND BY MUTATION, and it was the one uncaught survivor. The probe failing INSIDE the
        repository was covered; the probe never starting was not, and an empty landscape there
        reads as "this repository has no shared environments" - the same found-nothing-standing-
        in-for-did-not-look defect this family has now fixed in five other places."""
        repo = Repo()
        try:
            rows = repo.survey(python="no-such-interpreter-anywhere")
            self.assertTrue(rows)
            self.assertTrue(all(not x.complete for x in rows))
            self.assertIn("could not run", rows[0].why_not)
            self.assertIn("no-such-interpreter-anywhere", rows[0].why_not)
        finally:
            repo.close()

    def test_a_catalogue_that_raises_is_named_rather_than_swallowed(self):
        repo = Repo(catalogue="def all_of_them():\n    raise RuntimeError('half a checkout')\n")
        try:
            rows = repo.survey()
            self.assertTrue(all(not x.complete for x in rows))
            self.assertIn("half a checkout", rows[0].why_not)
        finally:
            repo.close()

    def test_a_catalogue_whose_items_do_not_carry_the_declared_name_says_which_key_is_wrong(self):
        repo = Repo(decl=DECL.replace("plugin_named: label", "plugin_named: nosuchattr"))
        try:
            rows = repo.survey()
            self.assertTrue(all(not x.complete for x in rows))
            self.assertIn("nosuchattr", rows[0].why_not)
        finally:
            repo.close()

    def test_a_plugin_whose_source_cannot_be_read_keeps_its_loan_and_loses_only_the_narrowing(self):
        """TWO DIFFERENT FINDINGS. What the environment lends is established from declarations
        and does not need the source at all; whether the plugin reaches for any of it does. A
        version that dropped the whole row would throw away the half it had."""
        repo = Repo()
        try:
            os.remove(repo.d / "widgets" / "alpha.py")
            alpha = repo.one("alpha")
            self.assertTrue(alpha.complete)
            self.assertEqual(alpha.lent, 4)
            self.assertFalse(alpha.narrowed)
            self.assertIn("no artefact", alpha.why_not_narrowed)
            out = SE.format_report([alpha], "widget")
            self.assertIn("could NOT be narrowed", out)
            self.assertIn("unknown, not zero", out)
        finally:
            repo.close()

    def test_a_plugin_whose_source_will_not_parse_still_reports_what_is_written_in_it(self):
        """A file that is not valid Python has no imports this can read - so nothing is LOADED -
        but the text is still text and a name written in it is still written in it."""
        repo = Repo(plugins={"alpha": ALPHA + "\ndef (:\n", "beta": BETA,
                             "gamma": GAMMA, "delta": DELTA})
        try:
            alpha = repo.one("alpha")
            self.assertTrue(alpha.narrowed)
            self.assertIn("tabler", {r["name"] for r in alpha.named(SE.LENT)})
            self.assertTrue(all(not r["loaded"] for r in alpha.named(SE.LENT)))
        finally:
            repo.close()


def _constants(path):
    """Every string CONSTANT in a module, docstrings excluded, joined.

    Lifted from `test_convert.py`, which states the reason: a ratchet on "this suite names no
    repository's vocabulary" has to read the code and not the prose.
    """
    import ast
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    docs = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", None) or []
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                docs.add(id(body[0].value))
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docs:
            out.append(node.value)
    return out


class TheRatchets(unittest.TestCase):
    SRC = (ROOT / "sch" / "dev" / "extract" / "shared_env.py").read_text(encoding="utf-8")
    CONSTANTS = _constants(ROOT / "sch" / "dev" / "extract" / "shared_env.py")

    def test_nothing_in_the_module_can_write(self):
        """REPORT, NEVER WRITE - `sch/dev/points.py` states the policy and the whole value of
        this check is that it names a missing declaration and leaves the declaring to the author.
        A maker that picked a version constraint would be asserting on the author's behalf about
        an environment it has never built."""
        for forbidden in ("write_text(", ".write(", "os.remove", "shutil.", "unlink("):
            self.assertNotIn(forbidden, self.SRC, f"{forbidden!r} writes, and this only reports")

    def test_the_harness_names_no_repositorys_vocabulary(self):
        """Not the resolver, not the grouping call, not the fields a requirement is made of, not
        the attribute that lists who shares an environment, and not the plugin or the packages
        that paid for this check. All of it arrives through DEVPOINTS.yaml, which is where
        `sch dev` reads everything else about a repository.

        THE CODE AND NOT THE PROSE, which is the same distinction `test_convert.py` draws and for
        the same reason: `r_namespace.py` explains one repository's R package in its header and
        must go on being able to. A docstring recounting the two error messages that paid for
        this file is evidence; a literal the code COMPARES AGAINST is a repository learnt by
        heart. Only the second is forbidden, and `ast` excludes comments already."""
        # A WHOLE LITERAL, because that is what a comparison is made of. `r` is a field of one
        # repository's requirement and also a letter; the question a ratchet can answer is
        # whether this module ever holds it AS A VALUE.
        for word in ("requires", "packages", "conda", "r", "resolve", "kernels", "kernel",
                     "group_by_compatibility", "members", "scprofile", "cellchat", "Seurat",
                     "umap-learn", "PLUGIN", "native_plots", "wheels", "channelled",
                     "sharers", "label", "tag"):
            self.assertNotIn(word, self.CONSTANTS, f"{word!r} is somebody's vocabulary")
        # And the distinctive ones nowhere inside one either - a name long enough to be
        # unmistakable cannot arrive here by coincidence, and could otherwise hide in a message.
        for word in ("scprofile", "cellchat", "Seurat", "umap-learn", "group_by_compatibility",
                     "native_plots"):
            for value in self.CONSTANTS:
                self.assertNotIn(word, value, f"{word!r} is somebody's vocabulary")

    def test_not_even_the_probe_it_sends_into_the_repository_names_one(self):
        """THE ONE PLACE A NAME COULD HIDE AND STILL WORK. The probe is a string, so it is not
        read as code by anything that scans this module - and it is the only part that runs
        inside the repository, where a hard-coded attribute name would silently work on the one
        repository it was written for and fail everywhere else."""
        for word in ("scprofile", "cellchat", "kernels", "resolve", "members", "packages",
                     "conda", "sharers", "wheels", "label", "tag"):
            self.assertNotIn(f'"{word}"', SE._PROBE, f"{word!r} is baked into the probe")
            self.assertNotIn(f"'{word}'", SE._PROBE, f"{word!r} is baked into the probe")

    def test_it_declares_itself_to_the_extractor_directory(self):
        from sch.dev import extract
        got = extract.discover(strict=True)
        self.assertIn("shared_env", got)
        self.assertEqual(got["shared_env"].EXTRACT["reads"], "plugin-environment")

    def test_the_probe_runs_the_repositorys_code_in_its_own_interpreter(self):
        """NEVER IN THIS ONE. `python_package` states the reason and it is sharper here: this is
        asked about every plugin of a family in a row, so a repository's import side effects
        would land in the maker nine times."""
        self.assertIn("subprocess.run", inspect.getsource(SE.resolve))


class TheCommandAPersonActuallyRuns(unittest.TestCase):
    """THE ENTRY POINT WAS THE THING THAT WENT UNRUN LAST TIME. A measurement nobody can invoke
    is a measurement that silently stops working."""

    @classmethod
    def setUpClass(cls):
        cls.repo = Repo()

    @classmethod
    def tearDownClass(cls):
        cls.repo.close()

    def _run(self, *extra):
        return subprocess.run([sys.executable, "-m", "sch", "dev", "convert", "borrowed",
                               "--root", str(self.repo.d), "--point", "widget", *extra],
                              capture_output=True, text=True, cwd=str(ROOT))

    def test_it_runs_over_the_whole_family_and_prints_every_plugin(self):
        out = self._run()
        self.assertEqual(out.returncode, 0, out.stderr)
        for name in ("alpha", "beta", "gamma", "delta"):
            self.assertIn(name, out.stdout)
        self.assertIn("LOADED", out.stdout)
        self.assertIn("NOTHING IS LENT", out.stdout)

    def test_a_repository_that_cannot_be_resolved_exits_cannot_run_and_not_ok(self):
        """A job that greps the exit code must not read "no resolver" as "nothing is borrowed"."""
        repo = Repo(grouper="raise ImportError('gone')\n")
        try:
            out = subprocess.run([sys.executable, "-m", "sch", "dev", "convert", "borrowed",
                                  "--root", str(repo.d), "--point", "widget"],
                                 capture_output=True, text=True, cwd=str(ROOT))
            self.assertEqual(out.returncode, 3, out.stdout)
        finally:
            repo.close()


if __name__ == "__main__":
    unittest.main()
