#!/bin/bash
# The rerun of the loop (harness ADR-0019 step 6): submits a job that `sch dev job` emitted.
# Never qsub the job directly: the run directory and its logs/ are made here, bare, the tree is
# checked against the commit the job expects, and the site's validator runs first (rule H1).
# Authored on the workstation and pushed. Runs on a login node in seconds: mkdir, validate, qsub.
#   submit_rerun.sh jobs/<emitted>.pbs
set -euo pipefail
HOME_=/data/wangyb/home/jiaen.lin
JOB="${1:?the emitted job, e.g. jobs/rerun_0006.pbs}"
[ -f "$JOB" ] || { echo "no such job: $JOB"; exit 3; }
RUNDIR="$(awk -F'"' '/^RUNDIR=/{print $2; exit}' "$JOB")"
TOOLDIR="$(awk -F'"' '/^TOOLDIR=/{print $2; exit}' "$JOB")"
EXPECT="$(awk -F'"' '/^EXPECT_COMMIT=/{print $2; exit}' "$JOB")"
QUEUE="$(awk '/^#PBS -q /{print $3; exit}' "$JOB")"
[ -n "$RUNDIR" ] && [ -n "$TOOLDIR" ] && [ -n "$EXPECT" ] && [ -n "$QUEUE" ] \
  || { echo "the job does not carry RUNDIR, TOOLDIR, EXPECT_COMMIT and a queue; was it emitted by sch dev job?"; exit 3; }
ACTUAL="$(cat "$TOOLDIR/HEAD.txt" 2>/dev/null || echo unknown)"
[ "$ACTUAL" = "$EXPECT" ] || { echo "the tree at $TOOLDIR is at $ACTUAL; the job expects $EXPECT"; exit 3; }
n=$(find "$TOOLDIR/kernels" -maxdepth 1 -name "*.py" -not -name "_*" | wc -l | tr -d " ")
[ "$n" = "1" ] || { echo "this tree carries $n kernels; the cellchat-only run needs exactly 1"; exit 3; }
mkdir "$RUNDIR" || { echo "run key collision: $RUNDIR"; exit 4; }
mkdir "$RUNDIR/logs"
basename "$RUNDIR" > "$RUNDIR/RUNKEY.txt"

# EVERY JOB IS VALIDATED BEFORE IT IS SUBMITTED (rule H1): the site's own checker, on the cluster.
"$HOME_/tools/hpc-site/validate.sh" "$JOB"
# THE SUBMISSION IS THE ONE THE EMITTER PRINTED: qsub -q <queue> -o <rundir>/logs/pbs.log <job>
JOBID=$(qsub -q "$QUEUE" -o "$RUNDIR/logs/pbs.log" "$JOB")
echo "$JOBID" > "$RUNDIR/JOBID.txt"
echo "$JOBID"
echo "$RUNDIR"
