"""A cohort to develop against that is not the cohort you will be judged on.

WHY THIS EXISTS. Every tool in this family was developed against one real cohort, and a tool
developed against one cohort learns that cohort. It learns that the sample column is called
`sample`, that there are ten libraries, that the arms are two, that a cell type called
`Cardiomyocyte` exists. None of that is true of the next dataset, and none of it fails a test,
because the only dataset the tests have is the one the assumptions came from. Overfitting here is
not a mistake somebody makes - it is the default outcome of having one dataset.

THE MECHANISM: TWO SHAPES OF THE SAME COHORT. Shape `a` and shape `b` hold the SAME numbers -
identical counts, identical embedding, identical assignment of cells to samples and types - under
DIFFERENT names. `sample` becomes `library_id`, `condition` becomes `arm`, `cell_type` becomes
`celltype_final`, the counts layer becomes `raw_counts`. Anything that reads a role by resolving
it gives the same answer on both. Anything that reads a role by knowing its name gives an answer
on one and fails on the other. That turns overfitting from something a reviewer notices into
something a test reports, which is the only form of it that survives a deadline.

WHAT IT IS NOT. It is synthetic, so no number it produces means anything biological, and no
result on it may be quoted. It cannot tell you a method is good, only that a method runs, keeps
its contract, and does not depend on names it was never promised. The biology is proved on the
real cohort, by reproduction, and nothing here substitutes for that.

THE HAZARDS ARE THE POINT. A clean synthetic cohort proves almost nothing, because clean input is
not what breaks code. Sixteen structural hazards are built in and named in `HAZARDS.json`, each
one drawn from a defect this family has actually had or a trap the format actually sets: a sample
too small to fit, a cell type in one arm only, NaN in a numeric column, a category no cell has, a
barcode that repeats across samples, an empty cell, an empty gene, a gene with no variance, a
gene symbol that collides with a column name, sample names where one is a prefix of another, a
label containing a space and a slash, an object column holding None, a design row for a sample
with no cells, a singleton population, mitochondrial genes, and a numeric covariate that is
constant within one arm.

Deterministic: same seed, same bytes, verified by digest.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

SHAPES = ("a", "b")

# One role, two names. The roles are what a tool is promised; the names are what it must not
# assume. Anything a tool may legitimately hard-code - `X_pca` is a scanpy convention, not a
# property of a cohort - is deliberately the SAME in both shapes, so a failure here is always a
# real portability defect and never a purist objection.
ROLES = {
    "sample":    {"a": "sample",      "b": "library_id"},
    "condition": {"a": "condition",   "b": "arm"},
    "batch":     {"a": "batch",       "b": "chip"},
    "cell_type": {"a": "cell_type",   "b": "celltype_final"},
    "subject":   {"a": "subject",     "b": "donor_id"},
    "covariate": {"a": "age_weeks",   "b": "age_at_collection"},
    # ONLY IN THE CROSSED FIXTURE. Absent by default, so `_rename` simply finds nothing to
    # rename and the one-factor object is byte-identical to what every baseline was recorded on.
    #
    # `crossed_only` SAYS SO IN THE DECLARATION, and it is here because the fact was known to
    # `_rename` and to nobody else. `jobs/dev_suite.pbs` asserts that each shape carries every
    # role it declares, walked this dict, and demanded `timepoint` of a fixture that says two
    # lines up it does not have one - so the full ladder job failed at step 0, before running a
    # single tier, from the commit that added this role. A property one function knows and no
    # reader can ask for is a property that goes stale the first time somebody else needs it.
    "stratum":   {"a": "timepoint",   "b": "visit", "crossed_only": True},
    "counts":    {"a": "counts",      "b": "raw_counts"},
}

def roles(crossed=False):
    """{role: {a, b}} for the shape actually being written. Not every role is in every shape."""
    return {r: n for r, n in ROLES.items() if crossed or not n.get("crossed_only")}


HAZARDS = {
    "tiny_sample":            "one sample carries 7 cells - too few for a per-sample fit",
    "arm_exclusive_type":     "a population present in one arm only - no paired comparison exists",
    "singleton_type":         "a population of exactly one cell",
    "nan_in_numeric_obs":     "NaN in a numeric obs column, where zero would be a different claim",
    "unused_category":        "a categorical carrying a category no cell has",
    "duplicate_barcodes":     "the same barcode string in two samples; obs_names disambiguate, the column does not",
    "empty_cell":             "a cell with zero counts in every gene",
    "empty_gene":             "a gene detected in no cell",
    "constant_gene":          "a gene with the same non-zero count in every non-empty cell - no variance\n                               to scale by, once the empty cell has been dropped as any pipeline drops it",
    "gene_named_like_obs":    "a gene symbol equal to an obs column name",
    "prefix_sample_names":    "sample S1 and sample S10 - one name is a prefix of the other",
    "awkward_label":          "a label containing a space and a slash",
    "mixed_object_obs":       "an object column holding strings and None together",
    "design_row_without_cells": "a design row for a sample that contributed no cells",
    "mito_genes":             "MT- prefixed genes, so a mitochondrial fraction is computable",
    "constant_covariate_in_arm": "a numeric covariate with no spread inside one arm",
}

#: Present only when the second factor is asked for. The 2x2 is not itself a hazard - it is the
#: design - but these two are, and both are reachable only once a design has strata.
CROSSED_HAZARDS = {
    "tiny_sample_inside_a_design_cell":
        "the 7-cell sample sits in one cell of the 2x2, so one stratum's simple effect rests on\n"
        "                               one usable sample while the marginal over it looks fully powered",
    "subject_nested_in_a_design_cell":
        "each subject contributes to one cell only - the shape that makes a subject term and a\n"
        "                               design term inseparable, and the reason a marginal is not a within-subject claim",
}

# Real symbols, so a tool that looks anything up finds something; the rest are synthetic. A
# marker-driven tool will not annotate this cohort correctly, and it is not asked to.
REAL_GENES = ["ACTB", "GAPDH", "PTPRC", "EPCAM", "COL1A1", "PECAM1", "MKI67", "RPS4X", "RPL13",
              "MT-CO1", "MT-CO2", "MT-ND1", "MT-ND4", "MT-ATP6"]
TYPES = ["Type_alpha", "Type_beta", "Type_gamma", "Type delta / epsilon", "Type_zeta", "Type_eta"]


def _rng(seed):
    import numpy as np
    return np.random.default_rng(seed)


def build(seed: int = 20260906, n_cells: int = 2000, n_genes: int = 520,
          crossed: bool = False):
    """The numbers, once. Both shapes are this, renamed - so a difference between the shapes can
    only ever be the tool's, never the fixture's.

    `crossed` ADDS A SECOND DESIGN FACTOR, and is off by default for the same reason `splice` is:
    the digest is a contract and every recorded baseline rests on it.

    WHY IT HAS TO EXIST. With one factor the richest thing this cohort can express is a main
    effect. An interaction - one factor's effect compared against the same effect at the other
    factor's control level - is not a harder version of that; it is a different branch of the
    code, with its own sign convention, its own reading order, and its own unit. Four defects in
    this family lived in that branch: an interaction subtracted the wrong way round and stayed
    self-consistent so no cross-check saw it; marginals were emitted before the strata they
    average, which is precisely the order that hides an interaction; a marginal arm was a
    question the design enumerated and an object no tool could be handed; and a composed section
    called five small movers the leading ones. Not one of them is REACHABLE on a one-factor
    cohort, so a plugin could pass every tier here and meet all four on the first real study.

    EIGHT SAMPLES, TWO IN EVERY CELL. Six cannot do it: a 2x2 out of six is 2/1 somewhere, and a
    cell holding one sample has no spread, so the simple effect it is half of is undefined and
    the interaction silently degrades to a main effect. Two per cell is the smallest design in
    which every term the reading order distinguishes actually exists.
    """
    import numpy as np
    import pandas as pd

    rng = _rng(seed)
    if crossed:
        # S1 is still a prefix of S10-S13. Batch is fully crossed with BOTH factors - one chip
        # in every cell of the 2x2 - because a batch confounded with the design would make every
        # conclusion here unattributable, which is a different lesson taught by a different
        # fixture. Subject stays nested, and is declared as a hazard for that reason.
        samples = ["S1", "S2", "S3", "S4", "S10", "S11", "S12", "S13"]   # prefix_sample_names
        arm_of = {"S1": "ctrl", "S2": "ctrl", "S3": "ctrl", "S4": "ctrl",
                  "S10": "treated", "S11": "treated", "S12": "treated", "S13": "treated"}
        strat_of = {"S1": "baseline", "S2": "baseline", "S3": "followup", "S4": "followup",
                    "S10": "baseline", "S11": "baseline", "S12": "followup", "S13": "followup"}
        chip_of = {"S1": "chipA", "S2": "chipB", "S3": "chipA", "S4": "chipB",
                   "S10": "chipA", "S11": "chipB", "S12": "chipA", "S13": "chipB"}
    else:
        samples = ["S1", "S2", "S3", "S10", "S11", "S12"]      # prefix_sample_names
        arm_of = {"S1": "ctrl", "S2": "ctrl", "S3": "ctrl", "S10": "treated", "S11": "treated", "S12": "treated"}
        strat_of = {}
        chip_of = {"S1": "chipA", "S2": "chipA", "S3": "chipB", "S10": "chipB", "S11": "chipA", "S12": "chipB"}
    subj_of = {s: f"D{i//2 + 1}" for i, s in enumerate(samples)}

    # The LAST sample gets 7 cells (tiny_sample); the rest split what is left, unevenly. Named
    # positionally rather than as "S12", so the crossed design does not quietly lose the hazard
    # by adding a sample after it.
    n_tiny = 7
    w = rng.dirichlet(np.ones(len(samples) - 1) * 4.0)
    counts_per = list((w * (n_cells - n_tiny)).astype(int))
    counts_per[0] += (n_cells - n_tiny) - sum(counts_per)
    per_sample = dict(zip(samples[:-1], counts_per)) | {samples[-1]: n_tiny}

    sample_col = np.concatenate([np.repeat(s, k) for s, k in per_sample.items()])
    n = len(sample_col)

    # Populations. Type_zeta is treated-only (arm_exclusive_type); Type_eta gets one cell
    # (singleton_type). Everything else is drawn from a shared prior so the arms are comparable.
    p = np.array([0.34, 0.26, 0.20, 0.14, 0.06])
    ctype = np.empty(n, dtype=object)
    for i, s in enumerate(sample_col):
        if arm_of[s] == "treated":
            ctype[i] = rng.choice(TYPES[:5], p=p)
        else:
            q = p[:4] / p[:4].sum()
            ctype[i] = rng.choice(TYPES[:4], p=q)
    ctype[int(rng.integers(0, n))] = TYPES[5]

    # Counts: gamma-poisson, one library-size factor per cell, one mean per gene.
    gene_mu = rng.gamma(1.4, 1.0, size=n_genes) + 0.05
    lib = rng.gamma(6.0, 1 / 6.0, size=n)
    lam = np.outer(lib, gene_mu)
    # A population signature, so the embedding is not noise and a clustering step has something
    # to find. Its magnitude is arbitrary and means nothing.
    # CLIPPED TO THE OBJECT THAT EXISTS. Twenty markers per type needs 20 x len(TYPES) genes, and
    # `n_genes` is a documented parameter: `build(n_genes=60)` indexed column 60 of a 60-column
    # array and raised. Six tests of this module's own suite call it that way and had errored
    # since the commit that wrote this line - invisibly, because they SKIP on a workstation with
    # no anndata and only run where the full ladder runs, which is a machine nobody was reading.
    #
    # THE WIDTH IS NOT DERIVED FROM `n_genes`, deliberately. Making the block scale would change
    # the default object and every baseline recorded against it; clipping changes nothing at the
    # default, where 120 markers fit inside 520 genes with room to spare.
    for k, t in enumerate(TYPES):
        idx = np.flatnonzero(ctype == t)
        lo, hi = k * 20, min(k * 20 + 20, n_genes)
        if len(idx) and lo < hi:
            lam[np.ix_(idx, np.arange(lo, hi))] *= 3.5
    X = rng.poisson(lam).astype("float32")

    genes = REAL_GENES + [f"GENE{i:04d}" for i in range(n_genes - len(REAL_GENES))]
    genes[len(REAL_GENES)] = "condition"          # gene_named_like_obs
    # ORDER MATTERS AND THE TWO HAZARDS COLLIDE. An all-zero cell makes every gene non-constant,
    # so `constant_gene` is constant over the cells that have any counts at all - which is the
    # realistic form of the trap anyway: the variance is zero only after QC drops the empty cell,
    # which is exactly when a scaling step reaches it.
    X[0, :] = 0.0                                 # empty_cell
    X[:, -1] = 0.0                                # empty_gene
    X[1:, -2] = 4.0                               # constant_gene, among the non-empty

    barcode = np.array([f"{'ACGT'[i % 4]}{i:07d}-1" for i in range(n)], dtype=object)
    barcode[n - 1] = barcode[0]                   # duplicate_barcodes

    covar = rng.normal(52.0, 6.0, size=n).round(1)
    covar[np.array([arm_of[s] == "treated" for s in sample_col])] = 60.0   # constant_covariate_in_arm
    qc = rng.normal(0.05, 0.02, size=n).round(4)
    qc[rng.choice(n, size=max(3, n // 400), replace=False)] = np.nan       # nan_in_numeric_obs

    note = np.array([None if i % 97 == 0 else f"note{i % 5}" for i in range(n)], dtype=object)

    obs = pd.DataFrame({
        "barcode": barcode,
        "_role_sample": pd.Categorical(sample_col, categories=samples + ["S99"]),  # unused_category
        "_role_condition": pd.Categorical([arm_of[s] for s in sample_col]),
        "_role_batch": pd.Categorical([chip_of[s] for s in sample_col]),
        "_role_subject": pd.Categorical([subj_of[s] for s in sample_col]),
        "_role_cell_type": pd.Categorical(ctype.astype(str)),                      # awkward_label
        "_role_covariate": covar,
        "pct_counts_mt_like": qc,
        "free_note": note,                                                          # mixed_object_obs
    })
    if strat_of:
        # PLACED AFTER condition, NOT BESIDE batch. A reader scanning the columns should see the
        # two design factors adjacent; a second factor filed among the nuisance columns is how a
        # crossed term gets treated as one.
        obs.insert(list(obs.columns).index("_role_condition") + 1, "_role_stratum",
                   pd.Categorical([strat_of[s] for s in sample_col]))
    obs.index = pd.Index([f"{s}_{b}" for s, b in zip(sample_col, barcode)], name=None)
    if not obs.index.is_unique:                   # the duplicate pair shares a sample only by chance
        obs.index = pd.Index([f"{x}_{i}" if d else x for i, (x, d) in
                              enumerate(zip(obs.index, obs.index.duplicated(keep="first")))])

    # THE COVARIATE IS SPELLED OUT, not generated, because `constant_covariate_in_arm` is a
    # hazard and a formula would smooth it away. `treated` is 60.0 throughout in both designs.
    covar_of = {"S1": 51.0, "S2": 53.0, "S3": 49.0, "S4": 47.0,
                "S10": 60.0, "S11": 60.0, "S12": 60.0, "S13": 60.0}
    design = pd.DataFrame({
        "_role_sample": samples + ["S98"],                     # design_row_without_cells
        "_role_condition": [arm_of[s] for s in samples] + ["ctrl"],
        "_role_batch": [chip_of[s] for s in samples] + ["chipA"],
        "_role_subject": [subj_of[s] for s in samples] + ["D9"],
        "_role_covariate": [covar_of[s] for s in samples] + [55.0],
    })
    if strat_of:
        design.insert(list(design.columns).index("_role_condition") + 1, "_role_stratum",
                      [strat_of[s] for s in samples] + ["baseline"])
    return {"X": X, "obs": obs, "genes": genes, "design": design, "seed": seed,
            "crossed": bool(strat_of)}


def _rename(frame, shape):
    return frame.rename(columns={f"_role_{r}": names[shape] for r, names in ROLES.items()})


def matching(out, shape, seed, n_cells, n_genes, splice, crossed):
    """The record already on disk if it was written from exactly these arguments, else None.

    EXISTS-AND-MATCHES, THE SAME RULE THE ENVIRONMENT INSTALLER USES. This cohort is a pure
    function of (seed, cells, genes, splice, crossed) - that is what "deterministic: same seed,
    same bytes" means - so writing it a second time produces the files that are already there.
    Two sizes with splice layers, which is what a memory measurement needs, was rebuilt on every
    submission of a job whose expensive part it is not.

    KEYED ON THE ARGUMENTS, NOT ON THE DIGEST, because the digest is computed FROM the built
    cohort: verifying it would cost the build it is meant to avoid. The digest still goes into
    the record and still fails loudly if the generator ever stops being deterministic.
    """
    rec_path = Path(out) / f"FIXTURE_{shape}.json"
    if not rec_path.is_file():
        return None
    try:
        rec = json.loads(rec_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not (Path(rec.get("observations", "")).is_file()
            and Path(rec.get("design", "")).is_file()):
        return None                      # the record outlived what it describes
    want = {"seed": int(seed), "cells": int(n_cells), "genes": int(n_genes),
            "splice": bool(splice), "crossed": bool(crossed)}
    got = {k: rec.get(k) for k in want}
    return rec if got == want else None


def write(out, shape: str = "a", seed: int = 20260906, n_cells: int = 2000, n_genes: int = 520,
          core=None, splice: bool = False, crossed: bool = False, force: bool = False) -> dict:
    """Write one shape. `core` lets both shapes share one build, which is what makes them the
    same cohort rather than two cohorts that resemble each other.

    `splice` ADDS SPLICED AND UNSPLICED LAYERS, and is off by default on purpose. A plugin whose
    entire input is those two layers - RNA velocity is the case - could not be run against this
    fixture at all, so its fixture tier only ever exercised `plan`, and the one thing that would
    have measured its memory or rendered its panels beside the upstream's was missing. The
    alternative was a velocity-shaped object written somewhere else, which is one plugin's cohort
    and the thing the two-shape fixture exists to prevent.

    DEFAULT OFF BECAUSE THE DIGEST IS A CONTRACT. Every recorded baseline and the two-shape
    equality both rest on the written object; adding layers unconditionally would move the digest
    and invalidate all of them for the benefit of one plugin. Asked for, the layers are added and
    the digest of the CORE is unchanged - `digest()` reads the core, not the file.
    """
    import anndata as ad
    import numpy as np
    import pandas as pd

    if shape not in SHAPES:
        raise ValueError(f"shape must be one of {SHAPES}, not {shape!r}")
    if not force:
        have = matching(out, shape, seed, n_cells, n_genes, splice, crossed)
        if have is not None:
            return dict(have, reused=True)
    c = core or build(seed=seed, n_cells=n_cells, n_genes=n_genes, crossed=crossed)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)

    obs = _rename(c["obs"].copy(), shape)
    var = pd.DataFrame(index=pd.Index(c["genes"], name=None))
    var["mt"] = [g.startswith("MT-") for g in c["genes"]]
    A = ad.AnnData(X=c["X"].copy(), obs=obs, var=var)
    A.layers[ROLES["counts"][shape]] = c["X"].copy()
    if splice:
        # A FIXED SPLIT OF THE SAME COUNTS, not a second random draw. The unspliced fraction has
        # to VARY BETWEEN CELLS or every diagnostic that asks "is there enough unspliced signal"
        # sees one number and cannot fail; it is drawn from the cell's own index so both shapes
        # get identical values, which is what keeps the two-shape comparison meaningful.
        #
        # NOT A MODEL OF SPLICING. Nothing fitted on this means anything about kinetics - the
        # object says `quotable: False` and this is why. What it supports is the code path: that a
        # plugin reading these layers runs, draws, and can be measured.
        frac = 0.10 + 0.30 * ((np.arange(c["X"].shape[0]) % 17) / 16.0)
        un = np.rint(c["X"] * frac[:, None]).astype(c["X"].dtype)
        A.layers["unspliced"] = un
        A.layers["spliced"] = (c["X"] - un).astype(c["X"].dtype)

    # A PCA-like embedding computed from the counts, so it is consistent with them; the key is
    # `X_pca` in BOTH shapes, because that name is a convention and not a cohort's choice.
    Z = np.log1p(c["X"])
    Z = Z - Z.mean(axis=0, keepdims=True)
    A.obsm["X_pca"] = np.ascontiguousarray(
        (Z @ np.linalg.svd(Z, full_matrices=False)[2][:20].T).astype("float32"))
    A.uns["sch_dev_fixture"] = {"shape": shape, "seed": c["seed"], "synthetic": True,
                                "quotable": False}

    h5 = out / f"fixture_{shape}.h5ad"
    A.write_h5ad(h5)
    dsn = out / f"design_{shape}.csv"
    _rename(c["design"].copy(), shape).to_csv(dsn, index=False)

    # THE ROLES ARE WHAT THIS OBJECT ACTUALLY CARRIES. Listing `stratum` on a one-factor
    # fixture would promise a column that is not there, and a resolver believing it would report
    # the absence as the tool's fault.
    #
    # READ FROM THE DECLARATION, NOT SPELLED AGAIN. This condition named `stratum` by hand, so
    # the fact that a role can be crossed-only lived in two places and a third reader - the job
    # that runs the whole ladder - had neither and asserted the opposite.
    _crossed = bool(c.get("crossed"))
    roles = {r: names[shape] for r, names in globals()["roles"](_crossed).items()}
    rec = {"shape": shape, "seed": c["seed"], "cells": int(A.n_obs), "genes": int(A.n_vars),
           # RECORDED BECAUSE THE REUSE CHECK READS IT. Without `splice` on the record, a run
           # that asked for the layers would match a record written without them and be handed
           # an object missing the only thing it needs.
           "splice": bool(splice),
           "roles": roles,
           "factors": [roles["condition"]] + ([roles["stratum"]] if _crossed else []),
           "crossed": _crossed,
           "observations": str(h5), "design": str(dsn),
           "digest": digest(c),
           "hazards": dict(HAZARDS, **(CROSSED_HAZARDS if _crossed else {})),
           "synthetic": True, "quotable": False,
           "cannot_prove": ["that any number here is biologically meaningful",
                            "that a method is better than another method",
                            "that the tool works on the real cohort - only a reproduction shows that"]}
    (out / f"FIXTURE_{shape}.json").write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8")
    return rec


def write_both(out, seed: int = 20260906, n_cells: int = 2000, n_genes: int = 520,
               splice: bool = False, crossed: bool = False, force: bool = False) -> list:
    # THE CORE IS BUILT ONCE, OR NOT AT ALL. Checking both shapes first is the difference between
    # skipping the write and skipping the WORK: the two shapes are one cohort renamed, so if
    # neither needs writing there is nothing to draw, and building it to discover that is the
    # redundancy this check exists to remove.
    if not force:
        have = [matching(out, s, seed, n_cells, n_genes, splice, crossed) for s in SHAPES]
        if all(h is not None for h in have):
            return [dict(h, reused=True) for h in have]
    core = build(seed=seed, n_cells=n_cells, n_genes=n_genes, crossed=crossed)
    return [write(out, shape=s, core=core, splice=splice, force=force) for s in SHAPES]


def digest(core) -> str:
    """Of the numbers only - not of the names. Both shapes carry the SAME digest, and that is the
    invariant the two-shape trick rests on: if they ever differ, the fixture is at fault and no
    conclusion drawn from a shape comparison is worth anything."""
    h = hashlib.sha256()
    h.update(core["X"].tobytes())
    h.update("|".join(core["genes"]).encode())
    # APPENDED, NEVER INSERTED. A second design factor is part of what this cohort IS, so a
    # crossed fixture must not share a digest with the one-factor one - but adding the column to
    # the middle of this tuple would move the DEFAULT digest too, and every baseline with it.
    for col in ("_role_sample", "_role_cell_type", "_role_condition", "_role_stratum"):
        if col in core["obs"]:
            h.update("|".join(map(str, core["obs"][col])).encode())
    return h.hexdigest()[:16]
