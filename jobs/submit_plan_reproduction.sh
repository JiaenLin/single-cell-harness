#!/bin/bash
# The plan reproduction (harness ADR-0016 step 4e), cellchat only. Never qsub the job directly:
# the run key is built here, and a tree carrying more than one kernel is refused.
# Authored on the workstation and pushed (rule H1). Runs on a login node in seconds: mkdir, qsub.
set -euo pipefail
HOME_=/data/wangyb/home/jiaen.lin
PROJ="$HOME_/projects/SAMBO"
TOOL="$HOME_/tools/scProfile-cconly"
HARNESS="$HOME_/tools/single-cell-harness"
REF="${REF:-$PROJ/runs/scprofile/04_profile/20260910T130619Z__scprofile-9211f81__04_profile__legends}"

COMMIT="$(cat "$TOOL/HEAD.txt" 2>/dev/null || echo unknown)"
[ "$COMMIT" != "unknown" ] || { echo "no HEAD.txt in $TOOL"; exit 3; }
n=$(find "$TOOL/kernels" -maxdepth 1 -name "*.py" -not -name "_*" | wc -l | tr -d " ")
[ "$n" = "1" ] || { echo "this tree carries $n kernels; the cellchat-only run needs exactly 1"; exit 3; }
[ -d "$REF" ] || { echo "reference run not found: $REF"; exit 3; }
[ -f "$REF/SEALED.txt" ] || { echo "the reference is not sealed: $REF"; exit 3; }

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
RUNKEY="${STAMP}__scprofile-${COMMIT}__04_profile__plan"
RUNDIR="$PROJ/runs/scprofile/04_profile/$RUNKEY"
mkdir -p "$PROJ/runs/scprofile/04_profile"
mkdir "$RUNDIR" || { echo "run key collision: $RUNDIR"; exit 4; }
mkdir "$RUNDIR/logs"
echo "$RUNKEY" > "$RUNDIR/RUNKEY.txt"

JOB=$(qsub -o "$RUNDIR/logs/" -e "$RUNDIR/logs/" \
     -v RUNDIR="$RUNDIR",RUNKEY="$RUNKEY",REF="$REF",HARNESS="$HARNESS" \
     "$HARNESS/jobs/plan_reproduction.pbs")
echo "$JOB" > "$RUNDIR/JOBID.txt"
echo "$JOB"
echo "$RUNDIR"
