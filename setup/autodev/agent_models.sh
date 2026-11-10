#!/usr/bin/env bash
# Which model and effort each background agent is running on (2026-11-10).
#   bash setup/autodev/agent_models.sh TASKS_DIR [AGENT_ID ...]
# TASKS_DIR is the coordinating session's tasks folder (the Agent tool's output files). For each
# agent output (all of them, or the ids given), count the models and efforts of its last 40
# messages, read from the transcript's own fields; any model but opus or any effort but max flags it. A development agent must show
# claude-opus-5-5 and max (RULES tier II, 2026-11-10). Measured the same day: an agent resumed by
# SendMessage runs on the model the coordinating session has AT RESUME TIME, so two builders
# resumed while the session ran another model ran on it. Nothing here is estimated.
set -u
T=${1:?TASKS_DIR}; shift
if [ $# -gt 0 ]; then files=(); for a in "$@"; do files+=("$T/$a.output"); done
else files=("$T"/*.output); fi
bad=0
for f in "${files[@]}"; do
  [ -f "$f" ] || continue
  tailb=$(tail -c 300000 "$f")
  # the LAST 40 messages, counted: one stray line (a stop, a resume notice) must not decide it
  models=$(printf '%s' "$tailb" | grep -o '"model":"claude-[a-z0-9-]*"' | tail -40 | cut -d'"' -f4 | sort | uniq -c | awk '{printf "%s x%s ", $2, $1}')
  efforts=$(printf '%s' "$tailb" | grep -o '"effort":"[a-z]*"' | tail -40 | cut -d'"' -f4 | sort | uniq -c | awk '{printf "%s x%s ", $2, $1}')
  [ -z "$models" ] && continue
  flag=ok
  case "$models" in *claude-opus-5-5*) ;; *) flag=NOT-OPUS-MAX ;; esac
  printf '%s' "$models" | tr ' ' '\n' | grep -q '^claude-' && [ "$(printf '%s' "$models" | grep -o 'claude-[a-z0-9-]*' | grep -vc '^claude-opus-5-5$')" != 0 ] && flag=NOT-OPUS-MAX
  [ -n "$efforts" ] && [ "$(printf '%s' "$efforts" | grep -o '^[a-z]* \|[a-z]* x' | grep -vc '^max x')" != 0 ] && flag=NOT-OPUS-MAX
  [ "$flag" = ok ] || bad=$((bad + 1))
  printf '%-20s %-13s %-40s %s\n' "$(basename "$f" .output)" "$flag" "$models" "$efforts"
done
[ "$bad" = 0 ]
