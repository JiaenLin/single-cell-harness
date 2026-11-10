#!/usr/bin/env bash
# One Monitor event per new verdict or held file the PBS mirror writes (2026-11-10).
#   Monitor: bash setup/autodev/monitor_verdicts.sh OUTDIR
OUT=${1:?OUTDIR}; SEEN="$OUT/.seen"; touch "$SEEN"
while true; do
  for f in "$OUT"/*.verdict "$OUT"/*.held; do
    [ -e "$f" ] || continue
    b=$(basename "$f")
    grep -qx "$b" "$SEEN" && continue
    echo "$b: $(head -1 "$f") | $(grep -m1 'VERDICT\|MISS\|exit=' "$f" 2>/dev/null)"
    echo "$b" >> "$SEEN"
  done
  sleep 60
done
