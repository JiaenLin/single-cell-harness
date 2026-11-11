#!/usr/bin/env bash
# The autodev PBS mirror (RULES tier IV, "watching by machinery", 2026-11-10).
#
#   bash setup/autodev/pbs_mirror.sh OUTDIR [POLL_SECONDS=300]
#
# Reads OUTDIR/watch.tsv (lines: jobid<TAB>rundir<TAB>wave; '#' comments). Every poll makes ONE ssh
# call to the cluster (login-node reads only: qstat, cat, grep, ls) and writes:
#   OUTDIR/poll.txt        the last poll (qstat, then each watched job's seal lines)
#   OUTDIR/<id>.verdict    written ONCE when the run reaches ANY terminal state: SEALED (SEALED.txt),
#                          FAILED (FAILED.txt) or GONE (left the queue with neither; qstat -x's exit status);
#                          with the VERDICT, RECORD, MISS, PREDICT and exit= lines of SEALED/FAILED.txt and logs/*.OU
#   OUTDIR/<id>.held       written ONCE when qstat shows the job in state H
#   OUTDIR/mirror.log      one line per poll
# The coordinator reads the verdict files (monitor_verdicts.sh turns them into Monitor events). The
# mirror never submits, deletes or modifies anything. The host alias is $PBS_HOST (default hpc); the
# queue is read for the remote account's own user, so the script names no user.
set -u
OUT=${1:?OUTDIR}; POLL=${2:-300}; HOST=${PBS_HOST:-hpc}
mkdir -p "$OUT"; touch "$OUT/watch.tsv"
while true; do
  stamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  watch=$(grep -v '^#' "$OUT/watch.tsv" | awk -F'\t' 'NF>=2{print $1" "$2}')
  ssh -o BatchMode=yes -o ConnectTimeout=30 "$HOST" 'bash -s' <<EOF > "$OUT/poll.tmp" 2>/dev/null
echo "== QSTAT"; qstat -u \$(whoami) 2>/dev/null | tail -n +6
while read -r job dir; do
  [ -z "\$job" ] && continue
  echo "== JOB \$job"
  # EVERY TERMINAL STATE, not only the happy one (2026-11-10: a run that wrote FAILED.txt stayed silent)
  if [ -f "\$dir/SEALED.txt" ]; then echo "SEALED"
  elif [ -f "\$dir/FAILED.txt" ]; then echo "FAILED"
  elif ! qstat "\$job" >/dev/null 2>&1; then echo "GONE"; qstat -x -f "\$job" 2>/dev/null | grep -E "Exit_status|job_state|comment" | sed 's/^ *//'
  fi
  grep -h "VERDICT\|RECORD\|MISS\|PREDICT\|GATE:\|exit=" "\$dir/SEALED.txt" "\$dir/FAILED.txt" "\$dir"/logs/*.OU 2>/dev/null | sort -u
done <<WL
$watch
WL
EOF
  rc=$?
  if [ "$rc" -ne 0 ]; then echo "$stamp ssh rc=$rc" >> "$OUT/mirror.log"; sleep "$POLL"; continue; fi
  mv "$OUT/poll.tmp" "$OUT/poll.txt"; echo "$stamp ok" >> "$OUT/mirror.log"
  while IFS=$'\t' read -r job dir wave tools jobfile; do   # 4th column: the tool commits the job uses; 5th: its job file (gate.py)
    [ -z "$job" ] && continue
    id=${job%%.*}
    block() { awk -v j="$job" '$0=="== JOB "j{f=1;next} /^== /{f=0} f' "$OUT/poll.txt"; }
    state=$(block | grep -m1 -E '^(SEALED|FAILED|GONE)$')
    if [ ! -f "$OUT/$id.verdict" ] && [ -n "$state" ]; then
      { echo "job=$job wave=$wave state=$state rundir=$dir seen=$stamp"; block | grep -vE '^(SEALED|FAILED|GONE)$'; } > "$OUT/$id.verdict"
    fi
    if [ ! -f "$OUT/$id.held" ] && grep -E "^$id\." "$OUT/poll.txt" | awk '$10=="H"' | grep -q .; then
      echo "job=$job wave=$wave state=H seen=$stamp" > "$OUT/$id.held"
    fi
  done < <(grep -v '^#' "$OUT/watch.tsv")
  sleep "$POLL"
done
