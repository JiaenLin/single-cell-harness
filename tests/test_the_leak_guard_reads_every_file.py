"""S1 reads every file in the repository by its content, not by its extension (W024, GAP-C46).

WHAT WAS WRONG. S1 walked the tree and read a file only when its suffix was in a list of the
family's own languages: Python, R, shell, YAML, Markdown and their kin. Studio, Lab and the Service
are TypeScript, JavaScript and HTML, so `sch conform` passed all three on their READMEs alone; and
a script with no suffix at all - a git hook, a launcher - was never read anywhere. Mirroring every
tracked file to .txt found five hits on the Service that the guard had passed.

WHAT IT DOES NOW. It reads every file git lists (tracked, and new files git does not ignore), or
the whole tree where there is no git, and decides from the first bytes whether a file is text. A
binary file is skipped and counted. Nothing here names a cohort: the terms are invented, and the
file is its own fixture.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import ROOT
from sch.conform import conform_repo

TERM = "zorblax"
ENV = ("SCH_SITE_TERMS", "SCH_SITE", "SCH_SITE_SHAPES", "SCH_FORBIDDEN_TERMS")
LOCATING = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_PREFIX")


def s1(checks, prefix="S1 "):
    return [c for c in checks if c["id"].startswith(prefix)][0]


class TheLeakGuardReadsEveryFile(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sch-every-file-"))
        self.repo = self.tmp / "tool"
        self.repo.mkdir()
        self.terms = self.tmp / "terms.txt"
        self.terms.write_text(f"# invented\n{TERM}\n")
        self._saved = {k: os.environ.pop(k, None) for k in ENV}

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        for k, v in self._saved.items():
            if v is not None:
                os.environ[k] = v

    def _put(self, rel, content):
        p = self.repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            p.write_bytes(content)
        else:
            p.write_text(content)
        return p

    def test_a_listed_term_is_found_in_every_kind_of_text_file(self):
        """The base read the .sh alone; every other file here was invisible to it."""
        planted = {
            "web/src/lib/request.ts": f"export const VENDOR = '{TERM}'\n",
            "web/src/view.tsx": f"export const V = () => <p>{TERM}</p>\n",
            "scripts/probe.mjs": f"const who = '{TERM}'\n",
            "docs/page.html": f"<p>delivered by {TERM}</p>\n",
            "web/style.css": f".x::after {{ content: '{TERM}' }}\n",
            "jobs/run.sh": f"#!/bin/bash\necho {TERM}\n",
            "bin/launch": f"#!/bin/bash\n# no suffix: a hook or a launcher\necho {TERM}\n",
            "Makefile": f"all:\n\techo {TERM}\n",
        }
        for rel, text in planted.items():
            self._put(rel, text)
        got = s1(conform_repo(self.repo, terms_file=str(self.terms)))
        self.assertFalse(got["ok"])
        for rel in planted:
            self.assertTrue(any(e.startswith(f"{rel}:") for e in got["evidence"]),
                            f"{rel} was not read: {got['evidence']}")

    def test_a_binary_file_is_skipped_and_counted_not_read(self):
        """Decided by the first bytes: a NUL, or bytes that are not UTF-8. The term's own bytes
        inside a binary file are not text anybody wrote."""
        self._put("assets/logo.png", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + TERM.encode() + b"\x00")
        self._put("data/blob.dat", b"caf\xe9 " + TERM.encode() + b"\n")        # Latin-1, not UTF-8
        self._put("src/app.ts", "export const x = 1\n")
        got = s1(conform_repo(self.repo, terms_file=str(self.terms)))
        self.assertTrue(got["ok"], got["evidence"])
        summary = " ".join(got["evidence"])
        self.assertIn("1 file(s) read by content", summary)
        self.assertIn("2 binary", summary)

    def test_a_character_cut_at_the_sniffing_boundary_is_still_text(self):
        """The first 8 KiB can end inside a multi-byte character; that file is text."""
        body = ("a" * 8191 + "é " + TERM + "\n").encode("utf-8")      # é straddles byte 8192
        self._put("notes/long.txt", body)
        got = s1(conform_repo(self.repo, terms_file=str(self.terms)))
        self.assertFalse(got["ok"], got["evidence"])
        self.assertTrue(any(e.startswith("notes/long.txt:") for e in got["evidence"]))

    @unittest.skipUnless(shutil.which("git"), "no git binary here - a compute node has none")
    def test_where_git_lists_the_tree_an_ignored_file_is_not_read_and_a_new_one_is(self):
        env = {k: v for k, v in os.environ.items() if k not in LOCATING}
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True, env=env)
        self._put(".gitignore", "out/\n")
        self._put("out/scratch.txt", f"{TERM}\n")           # ignored: a build product, not source
        self._put("src/kept.py", "X = 1\n")
        subprocess.run(["git", "-C", str(self.repo), "add", "."], check=True, env=env)
        self._put("src/new.ts", f"const y = '{TERM}'\n")    # not yet added, and not ignored
        got = s1(conform_repo(self.repo, terms_file=str(self.terms)))
        self.assertFalse(got["ok"])
        self.assertTrue(any(e.startswith("src/new.ts:") for e in got["evidence"]), got["evidence"])
        self.assertFalse(any(e.startswith("out/") for e in got["evidence"]), got["evidence"])


class EveryKindOfTermIsFoundTheSameWayFastOrSlow(unittest.TestCase):
    """The list's four forms, each planted where it must and must not match, scanned with the
    prefilter and without it. The prefilter for a whole-word term asks whether the file holds
    every word of the term as a word; this is the measurement that it never says no to a match."""

    LIST = "\n".join([
        "# invented terms, one of each form",
        "quuxplain",                 # anywhere, any case (the original form)
        "word:elderfold",            # a whole word, any case
        "word:7,481",                # a number, not inside a longer number
        "word:13 of 77",             # a phrase; any run of spaces between its words
        "exact:Qz",                  # a whole word in this case only
        "word:fibrozor*",            # a word that begins so
    ]) + "\n"

    MUST = {
        "a.py": "X = 'aQUUXPLAINb'\n",
        "b.md": "an Elderfold arm\n",
        "c.ts": "const n = '7,481 droplets'\n",
        "d.txt": "seen in 13  of\t77 runs\n",
        "e.R": "levels <- c('Qz')\n",
        "f.html": "<td>Fibrozorcytes</td>\n",
    }
    MUST_NOT = {
        "g.py": "averaged = 'elderfolded'  # not the word\n",
        "h.md": "17,481 and 7,4810 and 7,481.5 are other numbers\n",
        "i.txt": "113 of 77 and 13 of 770\n",
        "j.py": "qz = 1  # another case\n",
        "k.md": "prefibrozor is not a word that begins so\n",
    }

    def _scan(self, root, terms, slow):
        code = ("import json,sys;from sch.conform import conform_repo;"
                "c=[x for x in conform_repo(sys.argv[1], sys.argv[2]) if x['id'].startswith('S1 ')];"
                "print(json.dumps(c, sort_keys=True))")
        env = {k: v for k, v in os.environ.items() if k not in ENV and k != "SCH_CONFORM_NO_PREFILTER"}
        env["PYTHONPATH"] = str(ROOT)
        if slow:
            env["SCH_CONFORM_NO_PREFILTER"] = "1"
        r = subprocess.run([sys.executable, "-c", code, str(root), str(terms)], capture_output=True,
                           text=True, cwd=str(ROOT), env=env)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        return json.loads(r.stdout)[0]

    def test_each_form_matches_where_it_must_and_nowhere_else_on_both_paths(self):
        d = Path(tempfile.mkdtemp(prefix="sch-forms-"))
        try:
            (d / "tool").mkdir()
            for name, text in {**self.MUST, **self.MUST_NOT}.items():
                (d / "tool" / name).write_text(text)
            (d / "terms.txt").write_text(self.LIST)
            fast = self._scan(d / "tool", d / "terms.txt", slow=False)
            slow = self._scan(d / "tool", d / "terms.txt", slow=True)
            self.assertEqual(fast, slow)
            hit = {e.split(":")[0] for e in fast["evidence"] if ":" in e and "read by content" not in e}
            self.assertEqual(hit, set(self.MUST), fast["evidence"])
        finally:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
