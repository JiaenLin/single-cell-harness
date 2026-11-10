#!/usr/bin/env bash
# The autodev PBS mirror (RULES tier IV, "watching by machinery", 2026-11-10).
#
#   bash setup/autodev/pbs_mirror.sh OUTDIR [POLL_SECONDS=300]
#
# Reads OUTDIR/watch.tsv (lines: jobid<TAB>rundir<TAB>wave; '#' comments). Every poll makes ONE ssh
# call to the cluster (login-node reads only: qstat, cat, grep, ls) and writes:
#   OUTDIR/poll.txt        the last poll (qstat, then each watched job's seal lines)
#   OUTDIR/<id>.verdict    written ONCE when the run's SEALED.txt exists: the job's VERDICT, RECORD,
#                          MISS, PREDICT and exit= lines from SEALED.txt and logs/*.OU
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
  if [ -f "\$dir/SEALED.txt" ]; then
    echo "SEALED"
    grep -h "VERDICT\|RECORD\|MISS\|PREDICT\|exit=" "\$dir/SEALED.txt" "\$dir"/logs/*.OU 2>/dev/null | sort -u
  fi
done <<WL
$watch
WL
EOF
  rc=$?
  if [ "$rc" -ne 0 ]; then echo "$stamp ssh rc=$rc" >> "$OUT/mirror.log"; sleep "$POLL"; continue; fi
  mv "$OUT/poll.tmp" "$OUT/poll.txt"; echo "$stamp ok" >> "$OUT/mirror.log"
  while IFS=$'\t' read -r job dir wave; do
    [ -z "$job" ] && continue
    id=${job%%.*}
    block() { awk -v j="$job" '$0=="== JOB "j{f=1;next} /^== /{f=0} f' "$OUT/poll.txt"; }
    if [ ! -f "$OUT/$id.verdict" ] && block | grep -q '^SEALED$'; then
      { echo "job=$job wave=$wave rundir=$dir sealed_seen=$stamp"; block | grep -v '^SEALED$'; } > "$OUT/$id.verdict"
    fi
    if [ ! -f "$OUT/$id.held" ] && grep -E "^$id\." "$OUT/poll.txt" | awk '$10=="H"' | grep -q .; then
      echo "job=$job wave=$wave state=H seen=$stamp" > "$OUT/$id.held"
    fi
  done < <(grep -v '^#' "$OUT/watch.tsv")
  sleep "$POLL"
done
