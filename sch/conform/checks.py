from __future__ import annotations

import json
import os
import re
from pathlib import Path

TEXT_EXT = {".py", ".R", ".r", ".sh", ".pbs", ".md", ".yml", ".yaml", ".toml", ".cfg", ".txt",
            ".json", ".csv", ".tsv", ".cff", ".ipynb"}
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", "env", "dist", "build",
             ".mpl", "_data", ".egg-info"}

# Shapes of site leakage, not names: a home directory path, a login-node hostname, a scheduler
# job id, an e-mail address, a scratch directory dated like the site convention.
GENERIC_PATTERNS = [
    (r"(?<![\w/])/(?:Users|home)/[A-Za-z][\w.-]*", "a user home path"),
    (r"/data/[A-Za-z][\w.-]*/home/", "a site home path"),
    (r"\blogin-\d{2}-\d{2}\b", "a login-node hostname"),
    (r"\bhn-\d{2}-\d{2}\b", "a scheduler head-node name"),
    (r"\b\d{6}\.hn-\d{2}-\d{2}\b", "a scheduler job id"),
    (r"[\w.+-]+@[\w-]+\.(?:edu|com|org|sg|ac\.uk)\b", "an e-mail address"),
    (r"scratch/\d{8}__", "a dated scratch directory"),
]

RUNKEY = re.compile(r"^[0-9]{8}T[0-9]{4,6}Z__[a-z][a-z0-9]*-[0-9a-f]{7,40}__[0-9]{2}_[a-z0-9_]+(__[a-z0-9-]+)?$")


def _load_terms(terms_file) -> list:
    cands = [terms_file, os.environ.get("SCH_SITE_TERMS"),
             (Path(os.environ["SCH_SITE"]) / "forbidden_terms.txt") if os.environ.get("SCH_SITE") else None]
    for c in cands:
        if c and Path(c).exists():
            return [l.strip() for l in Path(c).read_text().splitlines() if l.strip() and not l.startswith("#")]
    return []


def _text_files(root: Path):
    for p in root.rglob("*"):
        if any(part in SKIP_DIRS or part.endswith(".egg-info") for part in p.relative_to(root).parts):
            continue
        if p.is_file() and (p.suffix in TEXT_EXT or p.name in ("VERSION", "HEAD.txt")):
            yield p


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _is_guard(p: Path) -> bool:
    n = p.name.lower()
    return ("portab" in n or "leak" in n) and n.startswith("test")


def _pkg_files(root: Path):
    """Package source: python/R files outside tests/, docs/, setup/, jobs/."""
    for p in _text_files(root):
        rel = p.relative_to(root).parts
        if p.suffix in (".py", ".R", ".r") and not any(x in ("tests", "test", "docs", "setup", "jobs", "scripts") for x in rel[:-1]):
            yield p


def _check(checks, cid, ok, evidence, fix, level="error"):
    checks.append({"id": cid, "ok": bool(ok), "level": level if not ok else "ok",
                   "evidence": evidence, "fix": fix})


def conform_repo(repo, terms_file=None) -> list:
    root = Path(repo).resolve()
    checks: list = []
    terms = _load_terms(terms_file)
    # S1 leak guard, generic shapes + site terms
    hits, guard_hits = [], []
    pats = [(re.compile(p), why) for p, why in GENERIC_PATTERNS]
    tpats = [(re.compile(re.escape(t), re.I), f"site term {t!r}") for t in terms]
    for p in _text_files(root):
        text = _read(p)
        for i, line in enumerate(text.splitlines(), 1):
            for rx, why in pats + tpats:
                if why == "an e-mail address" and p.name in ("CITATION.cff", "pyproject.toml"):
                    continue                     # attribution, not leakage
                if rx.search(line):
                    (guard_hits if _is_guard(p) else hits).append(f"{p.relative_to(root)}:{i} {why}")
    _check(checks, "S1 no site or cohort identifiers anywhere in the repository", not hits,
           hits[:25] + ([f"... {len(hits) - 25} more"] if len(hits) > 25 else []),
           "remove or generalise; keep site strings in a file outside the repo and point --terms at it")
    if guard_hits:
        _check(checks, "S1b the leak guard does not spell the site", False, guard_hits[:10],
               "load forbidden terms from an untracked file or environment variable", level="warn")
    _check(checks, "S1c site terms were supplied to this scan", bool(terms),
           f"{len(terms)} term(s)" if terms else "none: only generic shapes were scanned",
           "pass --terms FILE or set SCH_SITE_TERMS; without it S1 proves less", level="warn")
    # S2 a leak-guard test exists and scans the whole tree
    guards = [p for p in _text_files(root) if _is_guard(p)]
    whole = []
    for g in guards:
        t = _read(g)
        whole.append(all(k in t for k in ("tests", "setup")) or "rglob" in t or "git ls-files" in t)
    _check(checks, "S2 a leak-guard test exists", bool(guards), [str(g.relative_to(root)) for g in guards],
           "add tests/test_portability.py: a regex ratchet over every text file for cohort names, site paths, counts")
    if guards:
        _check(checks, "S2b the leak guard scans tests/, setup/, jobs/ and docs/, not only the package",
               any(whole), [str(g.relative_to(root)) for g in guards],
               "walk the whole tree (git ls-files) and exempt only the guard itself", level="warn")
    # S3 --out required; no writes to cwd or $HOME in package code
    out_default, cwd_writes = [], []
    for p in _pkg_files(root):
        t = _read(p)
        for i, line in enumerate(t.splitlines(), 1):
            if re.search(r"add_argument\(\s*[\"']--out(?:-dir)?[\"']", line) and "default=" in line and "required" not in line:
                out_default.append(f"{p.relative_to(root)}:{i}")
            if re.search(r"Path\(\s*[\"']\.[\"']\s*\)|os\.getcwd\(\)|expanduser\(\s*[\"']~", line) and re.search(r"write|open\(|mkdir|to_csv|savefig|/\s*[\"']", line):
                cwd_writes.append(f"{p.relative_to(root)}:{i}")
    _check(checks, "S3 --out has no default (a tool never chooses where a project's output lands)",
           not out_default, out_default, "make --out required; refuse rather than default")
    _check(checks, "S3b package code does not write relative to cwd or $HOME", not cwd_writes, cwd_writes,
           "route every write through the declared --out", level="warn")
    # S4 compute placement
    login = []
    for p in _text_files(root):
        if p.suffix in (".pbs", ".sh") or "setup" in p.parts or "jobs" in p.parts:
            t = _read(p)
            for i, line in enumerate(t.splitlines(), 1):
                s = line.strip()
                if s.startswith("#"):
                    continue
                if re.search(r"\bnohup\b|--executor\s+local|\s&\s*$", s):
                    login.append(f"{p.relative_to(root)}:{i} {s[:60]}")
    _check(checks, "S4 no job or setup script runs compute outside the scheduler", not login, login,
           "every tool invocation goes through qsub; remove nohup, trailing &, --executor local")
    exec_default = []
    for p in _pkg_files(root):
        t = _read(p)
        for i, line in enumerate(t.splitlines(), 1):
            if re.search(r"--executor", line) and re.search(r"default\s*=\s*[\"']local", line):
                exec_default.append(f"{p.relative_to(root)}:{i}")
    _check(checks, "S4b --executor does not default to local without refusing on a login node", not exec_default,
           exec_default, "refuse when a scheduler is on PATH and no job environment is set, unless --allow-local", level="warn")
    # S5 PBS scripts in the tool repo
    pbs = [p for p in _text_files(root) if p.suffix == ".pbs"]
    for p in pbs:
        t = _read(p)
        probs = []
        if "set -euo pipefail" not in t and "set -eu" not in t:
            if "set -uo pipefail" in t and re.search(r"trap\s+\w+\s+EXIT", t):
                pass                              # continues past failures on purpose, and seals
            else:
                probs.append("no set -euo pipefail")
        if not re.search(r"walltime=", t):
            probs.append("no walltime")
        if re.search(r"^[^#\n]*(?<![\w./-])git\s+(?:rev-parse|log|status|pull|fetch|checkout|describe|clone|diff|show)\b", t, re.M):
            probs.append("invokes git (compute nodes have none)")
        if not re.search(r"SEALED\.txt|FAILED\.txt", t):
            probs.append("no seal trap")
        elif not re.search(r"trap\s+\w+\s+EXIT", t):
            probs.append("seal not in an EXIT trap")
        if re.search(r"^#PBS -q\s+\S+", t, re.M):
            probs.append("hard-codes a queue name (site-specific in a portable tool)")
        if re.search(r"^#PBS -o\s+\$HOME|^#PBS -o\s+~", t, re.M):
            probs.append("-o resolves to $HOME")
        if re.search(r"/tmp/", t):
            probs.append("uses /tmp (node-local)")
        _check(checks, f"S5 job script {p.relative_to(root)} follows the site contract", not probs, probs,
               "copy the site template; set -euo pipefail; walltime; seal in an EXIT trap checking products; "
               "queue and -o from the caller", level="warn" if probs and all("queue" in x for x in probs) else "error")
    if not pbs:
        _check(checks, "S5 job scripts", True, "none in the tool repository (jobs belong to the project)", "")
    # S6 version agreement
    versions = {}
    vf = root / "VERSION"
    if vf.exists():
        versions["VERSION"] = vf.read_text().strip()
    for name in ("CITATION.cff",):
        f = root / name
        if f.exists():
            m = re.search(r"^version:\s*[\"']?([\w.]+)", _read(f), re.M)
            if m:
                versions[name] = m.group(1)
    for f in root.rglob("__init__.py"):
        if any(x in SKIP_DIRS for x in f.parts):
            continue
        m = re.search(r"__version__\s*=\s*[\"']([\w.]+)", _read(f))
        if m:
            versions[str(f.relative_to(root))] = m.group(1)
    for f in root.rglob("pyproject.toml"):
        m = re.search(r"^version\s*=\s*[\"']([\w.]+)", _read(f), re.M)
        if m:
            versions["pyproject.toml"] = m.group(1)
    distinct = set(versions.values())
    _check(checks, "S6 every version string agrees", len(distinct) <= 1, versions,
           "one source of truth (VERSION) read by the rest, and a test that asserts it")
    # S7–S10 interface declarations in package code
    pkg_text = "\n".join(_read(p) for p in _pkg_files(root))
    _check(checks, "S7 the tool writes a machine-readable run status (ok | partial | refused | died)",
           bool(re.search(r"STATUS\.json|run\.json|RUN_CARD\.json|\"status\"\s*:\s*\"(ok|partial|refused)", pkg_text)),
           "", "write <out>/STATUS.json first as partial and last as ok/refused; a crash leaves partial")
    _check(checks, "S8 the tool seals its own run (RUNNING → SEALED | FAILED, products listed)",
           bool(re.search(r"SEALED\.(?:txt|\{|\w+\.txt)|FAILED\.(?:txt|\{|\w+\.txt)", pkg_text)), "",
           "write RUNNING.txt at start and SEALED.txt/FAILED.txt at exit from the tool, not only the job script")
    _check(checks, "S9 the tool records its own commit at runtime (without a git binary)",
           bool(re.search(r"\.git/HEAD|packed-refs|HEAD\.txt|rev-parse", pkg_text)), "",
           "read .git/HEAD by file into the status/report JSON; compute nodes have no git")
    _check(checks, "S10 the tool declares sees and cannot_show", "cannot_show" in pkg_text and re.search(r"\bsees\b", pkg_text) is not None,
           {"cannot_show": "cannot_show" in pkg_text, "sees": re.search(r"\bsees\b", pkg_text) is not None},
           "one declaration block per tool/method: sees (labels|design|heldout), cannot_show (non-empty), state_version")
    _check(checks, "S10b the tool declares state_version (the numbers, versioned)", "state_version" in pkg_text, "",
           "declare an integer state_version and bump it whenever the same inputs would give different numbers")
    # S11 column-name sniffing
    sniff = []
    for p in _pkg_files(root):
        t = _read(p)
        for i, line in enumerate(t.splitlines(), 1):
            if re.search(r"for\s+\w+\s+in\s*\(\s*[\"'][A-Za-z_]+[\"']\s*,\s*[\"']", line) or re.search(r"CANDIDATES\s*=\s*[\[(]", line):
                sniff.append(f"{p.relative_to(root)}:{i} {line.strip()[:70]}")
    _check(checks, "S11 keys are declared, not sniffed from column names", not sniff, sniff,
           "resolve keys from a declaration (in.json keys / --label-key); hints may suggest, never decide", level="warn")
    # S12 escapes recorded as ask/decision pairs
    _check(checks, "S12 escapes are recorded as ask/decision pairs with who and why",
           bool(re.search(r"escape|override", pkg_text)) and bool(re.search(r"\"by\"|'by'|decided_by|approved_by", pkg_text)),
           "", "every --allow / --no-* that lifts a refusal writes {ask:{gate, number, refusal}, decision:{by, why, when}}",
           level="warn")
    return checks


def conform_run(run_dir) -> list:
    d = Path(run_dir).resolve()
    checks: list = []
    _check(checks, "R1 the directory name is a run key <UTCSTAMP>__<tool>-<commit>__<stage>[__purpose]",
           bool(RUNKEY.match(d.name)), d.name, "let the submitting script create the directory under the run-key rule")
    # A tool of several commands may seal per command: SEALED.<cmd>.txt beside STATUS.<cmd>.json.
    seals = sorted(p.name for p in d.glob("SEALED*.txt")) + sorted(p.name for p in d.glob("FAILED*.txt"))
    seal = seals[0] if seals else None
    text = "\n".join(_read(d / n) for n in seals) if seals else ""
    _check(checks, "R2 the run is sealed (SEALED.txt or FAILED.txt)", seal is not None, seal or "unsealed",
           "the job's EXIT trap writes the seal; the tool should write one too")
    if seal:
        _check(checks, "R2b the seal records the exit status and the products", "exit=" in text and
               bool(re.search(r"missing|products|jobid|runkey", text)), text.strip().splitlines()[:6],
               "seal lines: exit=, jobid=, products or missing:, hostname, date")
    head = None
    for n in ("TOOL_HEAD.txt", "HEAD.txt"):
        if (d / n).exists():
            head = _read(d / n).strip().split()[0] if _read(d / n).strip() else ""
    m = RUNKEY.match(d.name)
    commit = None
    if m:
        commit = d.name.split("__")[1].split("-", 1)[1]
    _check(checks, "R3 the recorded commit matches the run key", bool(head) and bool(commit) and (head.startswith(commit) or commit.startswith(head)),
           {"recorded": head, "run_key": commit}, "copy the tool's HEAD into the run (TOOL_HEAD.txt) and key the directory on it")
    status = None
    per_cmd = sorted(p.name for p in d.glob("STATUS.*.json"))
    for n in ["STATUS.json", *per_cmd, "RUN_CARD.json", "run.json", "report.json", "reports/report.json", "reports/run.json"]:
        if (d / n).exists():
            try:
                j = json.loads(_read(d / n))
                status = (n, j.get("status") or j.get("verdict") or j.get("deliverable", {}).get("status") if isinstance(j, dict) else None)
                break
            except ValueError:
                continue
    _check(checks, "R4 a machine-readable status exists with a status or verdict", status is not None and status[1] is not None,
           status, "write STATUS.json {status, headline, refusal, provenance}")
    logs = d / "logs"
    _check(checks, "R5 logs live inside the run directory", logs.is_dir() and any(logs.iterdir()),
           [p.name for p in logs.iterdir()][:5] if logs.is_dir() else "no logs/",
           "point -o/-e and the driver log at <RUNDIR>/logs/")
    home = os.path.expanduser("~")
    baked = []
    for n in ["STATUS.json", *sorted(p.name for p in d.glob("STATUS.*.json")), "RUN_CARD.json", "report.json", "reports/report.json", "INPUTS.json"]:
        f = d / n
        if f.exists():
            t = _read(f)
            if "/tmp/" in t:
                baked.append(f"{n}: /tmp path")
            if home and home in t and str(d) not in t:
                baked.append(f"{n}: home path outside the run")
    _check(checks, "R6 status and report files carry no /tmp or foreign home paths", not baked, baked,
           "record paths relative to the run directory", level="warn")
    esc = []
    for f in list(d.glob("*escape*")) + list(d.glob("*override*")) + list(d.glob("**/guard_overrides.jsonl")):
        for line in _read(f).splitlines():
            try:
                j = json.loads(line)
            except ValueError:
                continue
            if not j.get("by") or not (j.get("why") or j.get("overridden_reason")):
                esc.append(f"{f.name}: {line[:80]}")
    _check(checks, "R7 every recorded escape names who and why", not esc, esc,
           "record escapes as ask/decision pairs; an escape without a person is not an escape", level="warn")
    return checks


# ---------------------------------------------------------------------------------------------
# Are two runs comparable at all?
#
# A difference between the outputs of two runs made with DIFFERENT INPUTS is evidence about
# nothing, and it reads exactly like the most serious finding this project can make: that a
# change moved the numbers. Post-mortem 0001 is that mistake, made and caught.
#
# This reads what each run RECORDED about itself and says whether comparing them means anything.
# It cannot read what a run did not write down: a tool that records no parameters fails A1 here,
# which is the same finding S7 and S9 make about the tool.

_PARAMISH = {"seed", "k", "n_pcs", "n_latent", "w_bio", "resolution", "resolutions", "methods",
             "organism", "assay", "timeout", "min_dist", "mode", "label_key", "batch_key",
             "sample_key", "l1_key", "cluster_key", "state_version", "unit_by", "min_tier",
             "gap_min", "dbr", "dbr_sd", "light_floor", "species", "tissue"}
_PARAM_DICTS = ("keys", "controls", "params", "parameters", "settings")
_NOT_A_PARAM = {"generated", "version", "commit", "tool_commit", "seconds", "timings", "started",
                "finished", "host", "job", "jobid", "products", "argv", "python", "elapsed"}
#: Recorded, compared, but a difference here does not make two runs incomparable: a limit only
#: changes a result by FIRING, and a run whose instance was killed says so in its own status.
#: Reported as a warning rather than a failure, because a check that fires on correct behaviour
#: is a check somebody switches off — and then the checks that would have caught something go
#: with it.
_RESOURCE = {"timeout", "cores", "n_cores", "jobs", "n_jobs", "prefix", "out", "out_dir",
             "threads", "memory", "mem", "queue", "executor", "lisi_subsample"}


def _flatten(prefix, value, into):
    if isinstance(value, dict):
        for k, v in value.items():
            _flatten(f"{prefix}.{k}" if prefix else str(k), v, into)
    elif isinstance(value, (list, tuple)):
        into[prefix] = ",".join(str(x) for x in value)
    elif value is not None:
        into[prefix] = str(value)


def _json(path):
    try:
        return json.loads(_read(path))
    except (ValueError, OSError):
        return None


def run_record(d) -> dict:
    """What a run says about itself, gathered from wherever it put it, with the sources named."""
    d = Path(d)
    rec = {"dir": str(d), "sources": [], "params": {}, "input": None, "commit": None,
           "state_version": None, "argv": None, "status": None, "reused": None}

    for name in ["STATUS.json"] + sorted(p.name for p in d.glob("STATUS.*.json")):
        j = _json(d / name)
        if not isinstance(j, dict):
            continue
        rec["sources"].append(name)
        rec["commit"] = rec["commit"] or j.get("commit")
        rec["state_version"] = j.get("state_version", rec["state_version"])
        rec["argv"] = rec["argv"] or j.get("argv")
        rec["status"] = rec["status"] or j.get("status")

    for name in ("report.json", "reports/report.json", "reports/payload.json"):
        j = _json(d / name)
        if not isinstance(j, dict):
            continue
        rec["sources"].append(name)
        rec["input"] = rec["input"] or j.get("input") or j.get("h5ad")
        prov_block = j.get("provenance") if isinstance(j.get("provenance"), dict) else {}
        rec["commit"] = rec["commit"] or j.get("tool_commit") or prov_block.get("commit")
        if rec["state_version"] is None:
            rec["state_version"] = j.get("state_version")
        if j.get("reused") is not None:
            rec["reused"] = j.get("reused")
        for k, v in j.items():
            if k in _NOT_A_PARAM:
                continue
            if k in _PARAM_DICTS and isinstance(v, dict):
                _flatten(k, v, rec["params"])
            elif k in _PARAMISH or k.endswith(("_key", "_layer")):
                _flatten(k, v, rec["params"])

    j = _json(d / "INPUTS.json")
    if isinstance(j, dict):
        rec["sources"].append("INPUTS.json")
        desc = j.get("described") or {}
        _flatten("parameters", desc.get("parameters") or {}, rec["params"])
        if desc.get("mode"):
            rec["params"]["mode"] = str(desc["mode"])
        code = desc.get("code") or {}
        rec["commit"] = rec["commit"] or code.get("commit")
        if desc.get("samples"):
            rec["params"]["samples"] = ",".join(str(x) for x in desc["samples"])

    prov = d / "PROVENANCE.txt"
    if prov.exists():
        rec["sources"].append("PROVENANCE.txt")
        for line in _read(prov).splitlines():
            if "=" in line and not line.startswith("PBS_"):
                k, v = line.split("=", 1)
                k = k.strip()
                if k and k not in _NOT_A_PARAM and not k.startswith("PBS_"):
                    rec["params"].setdefault("provenance." + k, v.strip())

    for n in ("TOOL_HEAD.txt", "HEAD.txt"):
        f = d / n
        if f.exists() and not rec["commit"]:
            t = _read(f).strip().split()
            rec["commit"] = t[0] if t else None
    return rec


def conform_against(new_dir, ref_dir) -> list:
    """Whether comparing these two runs means anything. Post-mortem 0001."""
    checks: list = []
    a, b = run_record(new_dir), run_record(ref_dir)

    _check(checks, "A1 both runs recorded what they were given", bool(a["params"]) and bool(b["params"]),
           {"new": a["sources"] or "nothing readable", "ref": b["sources"] or "nothing readable",
            "new_params": len(a["params"]), "ref_params": len(b["params"])},
           "a run that records no parameters cannot be reproduced or compared; see S7 and S9")

    shared = sorted(set(a["params"]) & set(b["params"]))
    differ = {k: {"new": a["params"][k], "ref": b["params"][k]} for k in shared
              if a["params"][k] != b["params"][k]}
    resource = {k: v for k, v in differ.items() if k.split(".")[-1] in _RESOURCE}
    result = {k: v for k, v in differ.items() if k not in resource}
    only_new = sorted(set(a["params"]) - set(b["params"]))
    only_ref = sorted(set(b["params"]) - set(a["params"]))
    _check(checks, "A2 every parameter both runs recorded agrees", not result,
           [f"{k}: new={v['new']!r} ref={v['ref']!r}" for k, v in list(result.items())[:12]],
           "take the reproduction's parameters from the reference run's own record, not from a "
           "script that happens to run the same tool")
    _check(checks, "A2c the resource limits differ", not resource,
           [f"{k}: new={v['new']!r} ref={v['ref']!r}" for k, v in list(resource.items())[:8]],
           "a limit changes a result only by FIRING, and a run whose instance was killed says so "
           "in its own status; named here so it is not mistaken for a parameter", level="warn")
    _check(checks, "A2b each run recorded parameters the other did not", not (only_new or only_ref),
           {"only in new": only_new[:8], "only in ref": only_ref[:8]},
           "not necessarily a difference in what ran; it is a difference in what was written down",
           level="warn")

    same_input = (a["input"] or "") == (b["input"] or "") if (a["input"] or b["input"]) else None
    _check(checks, "A3 both runs read the same input", bool(same_input),
           {"new": a["input"], "ref": b["input"]},
           "a comparison across two inputs is a comparison of the inputs" if same_input is False
           else "neither run recorded the input it read; record it (S7)")

    # ABSENCE IS NOT DISAGREEMENT. A reference run made before the tool declared `state_version`
    # recorded none, and reading `None` as "different" fails a comparison that is perfectly
    # sound — the shape of check that gets switched off, taking the useful ones with it.
    sv_new, sv_ref = a["state_version"], b["state_version"]
    if sv_new is None or sv_ref is None:
        _check(checks, "A4 the numbers were not DECLARED to move (same state_version)", False,
               {"new": sv_new, "ref": sv_ref},
               "one run predates the declaration, so this cannot be checked; the older run's "
               "numbers are governed by its commit alone", level="warn")
    else:
        _check(checks, "A4 the numbers were not DECLARED to move (same state_version)",
               sv_new == sv_ref, {"new": sv_new, "ref": sv_ref},
               "a bumped state_version is the tool saying the numbers change for the same inputs; "
               "demanding identity is then the wrong test, and the right one is to explain the move")

    _check(checks, "A5 the two runs are of DIFFERENT code", (a["commit"] or "?") != (b["commit"] or "!"),
           {"new": (a["commit"] or "")[:12], "ref": (b["commit"] or "")[:12]},
           "comparing a run against itself proves nothing about a change", level="warn")

    adopted = [n for n, r in (("new", a), ("ref", b)) if r["reused"]]
    _check(checks, "A6 neither run adopted a result instead of computing it", not adopted,
           {n: (a if n == "new" else b)["reused"] for n in adopted},
           "an adopted instance is the earlier run's own output; comparing it to that run "
           "compares nothing. Re-run with reuse off")
    return checks


def format_checks(checks: list) -> str:
    lines = []
    for c in checks:
        mark = "ok  " if c["ok"] else ("WARN" if c["level"] == "warn" else "FAIL")
        lines.append(f"  {mark} {c['id']}")
        if not c["ok"]:
            ev = c["evidence"]
            if isinstance(ev, list):
                for e in ev[:12]:
                    lines.append(f"         {e}")
            elif ev:
                lines.append(f"         {ev}")
            if c["fix"]:
                lines.append(f"         fix: {c['fix']}")
    n_err = sum(1 for c in checks if not c["ok"] and c["level"] == "error")
    n_warn = sum(1 for c in checks if not c["ok"] and c["level"] == "warn")
    lines.append(f"{len(checks)} checks: {n_err} failing, {n_warn} warning(s)")
    return "\n".join(lines)
