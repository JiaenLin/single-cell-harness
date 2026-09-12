#!/bin/bash
# The enrichment test phase (harness ADR-0016 step 7a). Builds the run key, refuses a tree
# carrying more than one kernel, submits. Authored on the workstation and pushed (rule H1);
# runs on a login node in seconds.
set -euo pipefail
HOME_=/data/wangyb/home/jiaen.lin
PROJ="$HOME_/projects/SAMBO"
TOOL="${TOOL:-$HOME_/tools/scProfile-smoke}"
HARNESS="$HOME_/tools/single-cell-harness"
COMMIT="$(cat "$TOOL/HEAD.txt" 2>/dev/null || echo unknown)"
[ "$COMMIT" != "unknown" ] || { echo "no HEAD.txt in $TOOL"; exit 3; }
n=$(find "$TOOL/kernels" -maxdepth 1 -name "*.py" -not -name "_*" | wc -l | tr -d " ")
[ "$n" = "1" ] || { echo "this tree carries $n kernels; the enrichment-only run needs exactly 1"; exit 3; }
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
RUNKEY="${STAMP}__scprofile-${COMMIT}__04_profile__enrichment-test"
RUNDIR="$PROJ/runs/scprofile/04_profile/$RUNKEY"
mkdir "$RUNDIR" || { echo "run key collision: $RUNDIR"; exit 4; }
mkdir "$RUNDIR/logs"
echo "$RUNKEY" > "$RUNDIR/RUNKEY.txt"
JOB=$(qsub -o "$RUNDIR/logs/" -e "$RUNDIR/logs/" \
     -v RUNDIR="$RUNDIR",RUNKEY="$RUNKEY",TOOL="$TOOL",HARNESS="$HARNESS" \
     "$HARNESS/jobs/enrichment_test_phase.pbs")
echo "$JOB" > "$RUNDIR/JOBID.txt"
echo "$JOB"; echo "$RUNDIR"
