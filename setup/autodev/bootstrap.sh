#!/usr/bin/env bash
# The autodev bootstrap (2026-11-10): what a coordinating session runs first.
#   bash setup/autodev/bootstrap.sh check   what is running, what is missing, what is waiting
#   bash setup/autodev/bootstrap.sh print   the exact start lines for the missing pieces
# Paths are computed from this file, so the script names no home path (tests/test_portability.py).
set -u
H=$(cd "$(dirname "$0")/../.." && pwd); M="$H/autodev/.machinery"; P="$M/pbs"
mkdir -p "$P"; touch "$P/watch.tsv"
case "${1:-check}" in
check)
  echo "harness: $H @ $(git -C "$H" rev-parse --short HEAD) ($(git -C "$H" status --porcelain | wc -l | tr -d ' ') changed files)"
  if pgrep -f "pbs_mirror.sh $P" >/dev/null 2>&1; then
    echo "mirror: RUNNING (last poll: $(tail -1 "$P/mirror.log" 2>/dev/null))"
  else
    echo "mirror: MISSING -> run in the background: bash setup/autodev/pbs_mirror.sh $P 300"
  fi
  echo "watch list: $(grep -vc '^#' "$P/watch.tsv" 2>/dev/null) job(s); verdict/held files: $(ls "$P"/*.verdict "$P"/*.held 2>/dev/null | wc -l | tr -d ' ')"
  echo "Monitor: arm in the session: bash setup/autodev/monitor_verdicts.sh $P (30 min; re-arm at expiry)"
  echo "reminders: CronList must show LOOP TICK (7 */3), BLOCKER SWEEP (41 */3), PERIODIC CHECK (23 */6); prompts in autodev/README.md"
  echo "open waves (last status):"
  awk -F'\t' 'NR>1{s[$2]=$10} END{for (w in s) if (s[w]!="merged" && s[w]!="done" && s[w]!="failed") print "  " w ": " s[w]}' "$H/autodev/ledger/waves.tsv" | sort
  echo "questions for the PI in STATE: $(sed -n '/^## Decisions needed/,/^## /p' "$H/autodev/STATE.md" | grep -c '^[0-9][0-9]*\. ')"
  echo "token mode: $(grep -o 'Token mode = [A-Z]*' "$H/autodev/RULES.md" | head -1)"
  echo "agents: bash setup/autodev/agent_models.sh <the session's tasks folder>  (every development agent must read claude-opus-5-5 / max)"
  ;;
print)
  cat <<EOT
# In the coordinating session, from $H:
bash setup/autodev/pbs_mirror.sh $P 300              # Bash, run_in_background
bash setup/autodev/monitor_verdicts.sh $P            # the Monitor tool, 30 min, re-arm at expiry
# CronCreate the three prompts of autodev/README.md with <HARNESS>=$H and <MACHINERY>=$P
python3 -I setup/autodev/usage.py --since \$(date -u +%F) <transcript.jsonl> '<tasks>/*.output'   # the budget meter
# Development agents: Agent tool with model "opus" and effort "max" (RULES tier II, 2026-11-10); briefs: autodev/BRIEFS.md
# Never resume an agent (SendMessage) while this session runs another model: it resumes on the session's model.
bash setup/autodev/agent_models.sh <tasks folder>        # each running agent's model and effort
EOT
  ;;
*) echo "usage: bootstrap.sh check|print"; exit 2 ;;
esac
