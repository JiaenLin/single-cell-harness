#!/usr/bin/env python3
"""What each agent run cost, by wave and role (RULES, 2026-11-11: the efficiency is measured, not estimated).

  python3 -I setup/autodev/costs.py <TASKS_DIR> <the session's transcript .jsonl> [--since YYYY-MM-DD]

One row per agent run (its start, wave, role, calls, output, context read and written, largest context), a table by
role, and the coordinator's own calls by day. A run's role and wave are read from its brief's first lines. The fields
are the transcripts' own usage fields; a path with none contributes nothing. The caller names the paths.
"""
import glob, json, re, sys, collections, os
T = sys.argv[1]; MAIN = sys.argv[2]
SINCE = sys.argv[sys.argv.index("--since") + 1] if "--since" in sys.argv else "0000"
def scan(path):
    seen = {}; first = None; t0 = t1 = None
    for line in open(path, errors="replace"):
        try: o = json.loads(line)
        except Exception: continue
        if not isinstance(o, dict): continue
        ts = o.get("timestamp")
        if ts: t0 = t0 or ts; t1 = ts
        m = o.get("message") or {}
        if o.get("type") == "user" and first is None:
            c = m.get("content")
            if isinstance(c, list): c = " ".join(b.get("text", "") for b in c if isinstance(b, dict))
            first = (c or "")[:400]
        u = m.get("usage")
        if o.get("type") == "assistant" and u and m.get("id"):
            seen[m["id"]] = (u.get("output_tokens", 0), u.get("cache_read_input_tokens", 0), u.get("cache_creation_input_tokens", 0), u.get("input_tokens", 0), ts)
    return seen, first or "", t0, t1
rows = []
for f in sorted(glob.glob(T + "/*.output")):
    seen, first, t0, t1 = scan(f)
    if not seen: continue
    out = sum(v[0] for v in seen.values()); cr = sum(v[1] for v in seen.values()); cw = sum(v[2] for v in seen.values())
    ctx = max(v[1] + v[2] + v[3] for v in seen.values())
    w = re.search(r"wave[s]? (W\d+\w?)", first) or re.search(r"(W\d{3}\w?)", first)
    role = "builder" if "builder" in first[:200] else "verifier" if "verif" in first[:300].lower() else "auditor" if "audit" in first[:300].lower() else "blocker" if "blocker" in first[:300].lower() else "housekeeping" if "housekeep" in first[:300].lower() else "other"
    rows.append((t0 or "", w.group(1) if w else "-", role, len(seen), out, cr, cw, ctx, os.path.basename(f)[:8]))
rows.sort()
print("start            wave  role      calls  out(k)  cread(M) cwrite(M) maxctx(k)")
agg = collections.defaultdict(lambda: [0, 0, 0, 0, 0])
for r in rows:
    if r[0][:10] >= SINCE:
        print(f"{r[0][5:16]:16} {r[1]:5} {r[2]:9} {r[3]:5} {r[4]/1e3:7.0f} {r[5]/1e6:8.1f} {r[6]/1e6:8.1f} {r[7]/1e3:8.0f}")
        a = agg[r[2]]; a[0] += 1; a[1] += r[3]; a[2] += r[4]; a[3] += r[5]; a[4] += r[6]
print("\nBY ROLE: n agents, calls, out(M), cread(M), cwrite(M), out/agent(k), cread/agent(M), calls/agent")
for k, a in sorted(agg.items()):
    print(f"{k:12} {a[0]:3} {a[1]:6} {a[2]/1e6:6.2f} {a[3]/1e6:8.1f} {a[4]/1e6:6.1f} {a[2]/a[0]/1e3:7.0f} {a[3]/a[0]/1e6:7.1f} {a[1]/a[0]:6.0f}")
seen, _, _, _ = scan(MAIN)
byday = collections.defaultdict(lambda: [0, 0, 0, 0])
for o, cr, cw, i, ts in seen.values():
    d = (ts or "")[:10]; b = byday[d]; b[0] += 1; b[1] += o; b[2] += cr; b[3] += cw
print("\nCOORDINATOR (main transcript) by day: calls, out(M), cread(M), cwrite(M), avg ctx(k)")
for d, b in sorted(byday.items()):
    print(f"{d} {b[0]:5} {b[1]/1e6:6.2f} {b[2]/1e6:8.1f} {b[3]/1e6:6.1f} {(b[2]+b[3])/max(b[0],1)/1e3:7.0f}")
