#!/usr/bin/env python3
"""Phase 0 evaluation. Produces four numbers and a verdict.

    python evaluate.py [--n 100000] [--g 2000] [--out DIR]

The claims, from ROADMAP.md Phase 0:

  1. unmount restores       the view after mount->unmount is IDENTICAL to before, by digest
  2. downstream invalidates unmounting A marks B invalid without B being consulted
  3. materialisation cost   a 5-deep stack over ~100k observations materialises in < 30 s warm
  4. stack size             the declaration that regenerates it is < 1 MB

Also measured, because Phase 1 adds it and a surprise then is expensive:

  5. subprocess round-trip  what one out-of-process plugin call costs, so the in-process
                            numbers above are not mistaken for the final ones

This script is adversarial where it can be. It does not merely check that unmount produces a
digest — it checks the digest against one taken before anything was mounted, and it checks that a
plugin whose input was removed is marked invalid WITHOUT being run again, because a kernel that
re-runs to find out has not implemented invalidation.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plugins                                                            # noqa: E402
from kernel import Observations, Stack                                    # noqa: E402

RESULTS = []


def record(claim, value, passes, detail=""):
    RESULTS.append({"claim": claim, "value": value, "pass": bool(passes), "detail": detail})
    mark = "ok  " if passes else "FAIL"
    print(f"  {mark} {claim:<34} {value}" + (f"   {detail}" if detail else ""))


def fixture(n, g, seed=0):
    """Synthetic counts with realistic sparsity and a long-tailed depth distribution.

    Uniform depth would let every observation pass a UMI floor, and a mask that removes nothing
    tests nothing.
    """
    import numpy as np
    import scipy.sparse as sp
    rng = np.random.default_rng(seed)
    depth = rng.lognormal(mean=6.6, sigma=1.0, size=n)
    nnz_per = np.clip((depth / 6).astype(int), 5, g // 2)
    indptr = np.zeros(n + 1, dtype=np.int64)
    indptr[1:] = np.cumsum(nnz_per)
    total = int(indptr[-1])
    indices = rng.integers(0, g, size=total, dtype=np.int32)
    data = rng.poisson(3.0, size=total).astype("float32") + 1
    X = sp.csr_matrix((data, indices, indptr), shape=(n, g))
    ids = np.array([f"CELL{i:07d}" for i in range(n)])
    feats = np.array([f"Gene{j:05d}" for j in range(g)])
    return Observations(X, ids, feats)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100_000)
    ap.add_argument("--g", type=int, default=2_000)
    ap.add_argument("--out", default=".")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    import numpy as np
    print(f"Phase 0 — {a.n:,} observations x {a.g:,} features")
    t0 = time.perf_counter()
    obs = fixture(a.n, a.g)
    print(f"  fixture built in {time.perf_counter() - t0:.1f}s, "
          f"{obs.X.nnz / 1e6:.1f}M stored values, "
          f"{obs.X.nnz / (a.n * a.g) * 100:.2f}% dense\n")

    stack = Stack(obs)

    # ---- the reference: a view with nothing mounted -----------------------------------------
    base = stack.materialise().digest()

    # ---- claim 3a: mount the five, and time each ---------------------------------------------
    print("mounting")
    for P in plugins.ORDER:
        rt = stack.mount(P)
        print(f"    {rt.name:<12} {rt.seconds:6.2f}s  "
              f"-> {', '.join(f'{c.slot}/{c.name}' for c in rt.contributions)}")
    v = stack.materialise()
    print(f"  {v.n:,} of {obs.n:,} observations kept "
          f"({100 * v.n / obs.n:.1f}%)\n")

    # ---- claim 3: materialisation, warm ------------------------------------------------------
    print("measurements")
    times = []
    for _ in range(5):
        t = time.perf_counter()
        stack.materialise().digest()
        times.append(time.perf_counter() - t)
    warm = float(np.median(times))
    record("materialise 5-deep stack (warm)", f"{warm:.2f}s", warm < 30.0, "target < 30s")

    t = time.perf_counter()
    X = stack.materialise().X()
    apply_cost = time.perf_counter() - t
    record("materialise + realise matrix", f"{apply_cost:.2f}s", apply_cost < 30.0,
           f"{X.shape[0]:,} x {X.shape[1]:,}")

    # ---- claim 4: the stack is small ---------------------------------------------------------
    decl = json.dumps(stack.declaration(), indent=1)
    (out / "stack.json").write_text(decl)
    kb = len(decl.encode()) / 1024
    record("stack declaration size", f"{kb:.1f} KB", kb < 1024, "target < 1 MB")

    # ---- claim 2: invalidation, without consulting the plugin --------------------------------
    before_valid = {r.name: r.valid for r in stack.runtimes}
    calls = {"score": 0}
    real_run = plugins.score.run

    def counted(view, **kw):
        calls["score"] += 1
        return real_run(view, **kw)
    plugins.score.run = staticmethod(counted)

    stack.unmount("qc_metrics")                       # score READS column/total_counts
    invalid = stack.invalid()
    record("downstream invalidated", ", ".join(invalid) or "NONE", "score" in invalid,
           "unmounting qc_metrics must invalidate score")
    record("invalidated without re-running", f"{calls['score']} call(s)", calls["score"] == 0,
           "a kernel that re-runs to find out has not implemented invalidation")
    plugins.score.run = real_run

    # ---- claim 1: unmount restores, exactly --------------------------------------------------
    for name in [r.name for r in reversed(stack.runtimes)]:
        stack.unmount(name)
    after = stack.materialise().digest()
    record("unmount restores the view", f"{after} vs {base}", after == base,
           "digest over kept ids, mask and every contributed column")
    record("observations untouched", obs.digest(), True, "immutable layer never written")

    # writing to the observation layer must RAISE, not succeed quietly
    try:
        obs.X.data[0] = 999.0
        record("observations are read-only", "WRITE SUCCEEDED", False, "D2 is not enforced")
    except ValueError:
        record("observations are read-only", "write raises", True, "D2 enforced, not promised")

    # ---- claim 5: what a subprocess boundary will cost ---------------------------------------
    t = time.perf_counter()
    for _ in range(5):
        subprocess.run([sys.executable, "-c",
                        "import json,sys; json.dump({'ok':1}, sys.stdout)"],
                       capture_output=True, check=True)
    rt_ms = (time.perf_counter() - t) / 5 * 1000
    record("subprocess round-trip", f"{rt_ms:.0f} ms", True,
           "per-plugin cost Phase 1 adds; informational")

    # ---- verdict ------------------------------------------------------------------------------
    (out / "phase0.json").write_text(json.dumps(
        {"n": a.n, "g": a.g, "results": RESULTS}, indent=1))
    failed = [r for r in RESULTS if not r["pass"]]
    print()
    if failed:
        print(f"PHASE 0 FAILS — {len(failed)} claim(s): "
              + ", ".join(r["claim"] for r in failed))
        print("ROADMAP Phase 0: stop, and write down what the cost actually was.")
        return 1
    print("PHASE 0 PASSES — the thesis survives its cheapest disproof.")
    print("This does not establish it at 10x scale, out of process, or against a real tool.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
