#!/bin/bash
# The writing run (harness ADR-0017 step 5), in two invocations on a login node, seconds each:
#   --prepare REF      make the writing run's directory beside REF and print incoming/, the
#                      path the agent sends the written layer to (rsync from the replay)
#   --seal RUNDIR      validate the job and submit it: the replay is rebuilt from REF, the
#                      written layer laid over it, the maker asked, the run sealed
# Authored on the workstation and pushed (rule H1). Never qsub the job directly.
set -euo pipefail
HOME_=/data/wangyb/home/jiaen.lin
PROJ="$HOME_/projects/SAMBO"
TOOL="${TOOL:-$HOME_/tools/scProfile-cconly}"
HARNESS="$HOME_/tools/single-cell-harness"
PLUGIN="${PLUGIN:-cellchat}"
mode="${1:?--prepare REF | --seal RUNDIR}"
case "$mode" in
  --prepare)
    REF="${2:?--prepare needs the sealed run}"
    [ -f "$REF/SEALED.txt" ] || { echo "the run is not sealed: $REF"; exit 3; }
    COMMIT="$(cat "$TOOL/HEAD.txt" 2>/dev/null || echo unknown)"
    [ "$COMMIT" != "unknown" ] || { echo "no HEAD.txt in $TOOL"; exit 3; }
    STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
    RUNKEY="${STAMP}__scprofile-${COMMIT}__04_profile__written"
    RUNDIR="$PROJ/runs/scprofile/04_profile/$RUNKEY"
    mkdir "$RUNDIR" || { echo "run key collision: $RUNDIR"; exit 4; }
    mkdir "$RUNDIR/logs" "$RUNDIR/incoming"
    echo "$RUNKEY" > "$RUNDIR/RUNKEY.txt"
    echo "$REF" > "$RUNDIR/REF.txt"
    echo "$RUNDIR"
    echo "$RUNDIR/incoming"
    ;;
  --seal)
    RUNDIR="${2:?--seal needs the writing run directory}"
    REF="$(cat "$RUNDIR/REF.txt")"
    [ -d "$RUNDIR/incoming" ] || { echo "no incoming/ under $RUNDIR"; exit 3; }
    n=$(find "$RUNDIR/incoming" -type f | wc -l | tr -d " ")
    [ "$n" -gt 0 ] || { echo "incoming/ is empty: nothing was sent back"; exit 3; }
    "$HOME_/tools/hpc-site/validate.sh" "$HARNESS/jobs/writing_seal.pbs"
    JOB=$(qsub -o "$RUNDIR/logs/" -e "$RUNDIR/logs/" \
         -v RUNDIR="$RUNDIR",REF="$REF",HARNESS="$HARNESS",TOOL="$TOOL",PLUGIN="$PLUGIN" \
         "$HARNESS/jobs/writing_seal.pbs")
    echo "$JOB" > "$RUNDIR/JOBID.txt"
    echo "$JOB"; echo "$RUNDIR"
    ;;
  *) echo "usage: $0 --prepare REF | --seal RUNDIR"; exit 2;;
esac
