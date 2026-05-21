#!/usr/bin/env bash
# Cascade Phase 1 progress check — single source of truth for "is it done yet?"
#
# Output: 5 named structured lines to stdout. NO opinions. NO colors. Parseable.
# Exit code: 0 always (intended for cron / /loop consumption; never alarm).
#
# Usage:
#   bash scripts/check_progress.sh                    # human-readable
#   bash scripts/check_progress.sh --json             # one JSON object per line
#
# Consumed by:
#   docs/nexus/PM_W1_allocation.md §7  (PM check cadence)
#   Future /loop or /schedule invocations (Claude PM session reads this output)

set -u
cd "$(dirname "$0")/.."

REPO_ROOT="$(pwd)"
JSON=0
[ "${1:-}" = "--json" ] && JSON=1

# ---------- Phase 0 closure ----------
real_fixtures=$(find backend/src/agent/cascade/fixtures/real_v1 -name "*.json" 2>/dev/null | wc -l | tr -d ' ')
test_count=$(cd backend 2>/dev/null && uv run pytest tests/test_cascade_contract.py tests/test_topic_intelligence.py --collect-only -q 2>/dev/null | grep -E "test " | wc -l | tr -d ' ' || echo 0)
test_skipped=$(cd backend 2>/dev/null && uv run pytest tests/test_cascade_contract.py tests/test_topic_intelligence.py 2>&1 | grep -oE '[0-9]+ skipped' | head -1 | grep -oE '[0-9]+' || echo "?")
compliance_done=$(ls docs/nexus/founder_log/compliance_done_*.md 2>/dev/null | wc -l | tr -d ' ')
algo_filing=$(ls docs/nexus/founder_log/algo_filing_*.md 2>/dev/null | wc -l | tr -d ' ')
prereg=$(ls docs/nexus/founder_log/pre_registration_*.md 2>/dev/null | wc -l | tr -d ' ')

phase0_closed="NO"
if [ "$real_fixtures" -ge 20 ] && [ "$test_skipped" = "0" ] && [ "$compliance_done" -ge 1 ] && [ "$algo_filing" -ge 1 ] && [ "$prereg" -ge 1 ]; then
  phase0_closed="YES"
fi

# ---------- PM W1 — handoff briefs ----------
brief_count=$(find docs/nexus/handoff -name "*.md" 2>/dev/null | wc -l | tr -d ' ')

# ---------- PM W1 — ticket status (presence of expected output) ----------
# status_probe checks BOTH file existence AND a required symbol — defeats "empty
# file = done" false positives. probe_signature is a grep pattern that MUST match
# (function def, export, route registration, etc.).
status_probe() {
  local file="$1"
  local sig="$2"
  if [ -e "$file" ] && grep -qE "$sig" "$file" 2>/dev/null; then
    echo "done"
  elif [ -e "$file" ]; then
    echo "partial"
  else
    echo "open"
  fi
}

p1_2=$(status_probe "backend/src/agent/cascade/analysis_service.py" "request_shallow_analysis|async def request_shallow")
p1_1=$(status_probe "frontend/src/pages/Landing.tsx" "export +(default +)?function Landing|挑一张开始")
p1_3_prompts=$(status_probe "backend/src/agent/prompts/rewrite_baomam_fushi.md" "rewritten_script|赛道")
p1_3_chain=$(status_probe "backend/src/agent/cascade/rewrite_service.py" "request_rewrite|async def request_rewrite")
p1_4=$(status_probe "frontend/src/components/cards/PublishPackCard.tsx" "PublishPackCard|export")
p1_6_back=$(status_probe "backend/src/agent/cascade/anchors.py" "reuse_count|async def list_anchors|class Anchor")
p1_6_sb=$(status_probe "frontend/src/components/anchors/AnchorSidebar.tsx" "AnchorSidebar")
p1_7=$(status_probe "frontend/src/lib/buildPublishPack.ts" "buildPublishPack|export function")
p1_8=$(status_probe "frontend/src/components/feedback/FailureBanner.tsx" "FailureBanner")
p1_9=$(status_probe "backend/src/agent/cascade/cost_guard.py" "cost_guard|async def cost_guard|run_cap")

# Count engineering tickets done (excludes prompts which is Claude's own)
eng_done=0
for t in "$p1_2" "$p1_1" "$p1_3_chain" "$p1_4" "$p1_6_back" "$p1_6_sb" "$p1_7" "$p1_8" "$p1_9"; do
  [ "$t" = "done" ] && eng_done=$((eng_done + 1))
done

# ---------- Recruitment + marketing (read from founder log if exists) ----------
recruit_log="docs/nexus/founder_log/recruitment.md"
if [ -e "$recruit_log" ]; then
  # grep -c outputs the count AND exits non-zero on zero matches, so the old
  # `|| echo 0` fallback appended a second "0" line. Use `|| true` to drop the
  # non-zero exit; grep's own stdout is already the count we want.
  dms=$(grep -ic '^- DM' "$recruit_log" 2>/dev/null || true)
  calls=$(grep -ic '^- CALL' "$recruit_log" 2>/dev/null || true)
  commits=$(grep -ic '^- COMMIT' "$recruit_log" 2>/dev/null || true)
  dms=${dms:-0}
  calls=${calls:-0}
  commits=${commits:-0}
else
  dms=0
  calls=0
  commits=0
fi

# Event-table reads (if SQLite db exists)
events_db="backend/data/messages.db"
runs_count=0
returns_count=0
if [ -e "$events_db" ]; then
  runs_count=$(sqlite3 "$events_db" "SELECT COUNT(DISTINCT user_id) FROM events WHERE event_name='publish_pack_copied'" 2>/dev/null || echo 0)
  returns_count=$(sqlite3 "$events_db" "SELECT COUNT(*) FROM (SELECT user_id, COUNT(*) c FROM events WHERE event_name='run_started' GROUP BY user_id HAVING c >= 2)" 2>/dev/null || echo 0)
fi

# Marketing assets posted (founder log)
seed_posted="NO"
ls docs/nexus/founder_log/seed_post_url_*.md >/dev/null 2>&1 && seed_posted="YES"
xhs_posts=$(ls docs/nexus/founder_log/xhs_post_*.md 2>/dev/null | wc -l | tr -d ' ')
douyin_posts=$(ls docs/nexus/founder_log/douyin_post_*.md 2>/dev/null | wc -l | tr -d ' ')
wechat_oa=$(ls docs/nexus/founder_log/wechat_oa_*.md 2>/dev/null | wc -l | tr -d ' ')
jike_thread=$(ls docs/nexus/founder_log/jike_thread_*.md 2>/dev/null | wc -l | tr -d ' ')

# ---------- Risk signals ----------
blockers=$(ls docs/nexus/founder_log/blockers*.md 2>/dev/null | wc -l | tr -d ' ')
quotes=$(grep -c '^> ' docs/nexus/founder_log/W*.md 2>/dev/null | awk -F: '{s+=$2} END {print s+0}')

cost_p95="?"
if [ -e "$events_db" ]; then
  # rough P95 by ordering desc and picking index ceil(0.05 * N) — SQLite has no quantile fn
  cost_p95=$(sqlite3 "$events_db" "SELECT printf('%.2f', json_extract(payload_json, '\$.cost_cny')) FROM events WHERE event_name='generation_cost' ORDER BY json_extract(payload_json, '\$.cost_cny') DESC LIMIT 1" 2>/dev/null || echo "?")
fi

# ---------- Output ----------
ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

if [ "$JSON" = "1" ]; then
  printf '{"ts":"%s","scope":"phase0","closed":"%s","fixtures":%d,"tests":%s,"skipped":%s,"compliance":%d,"algo_filing":%d,"prereg":%d}\n' \
    "$ts" "$phase0_closed" "$real_fixtures" "$test_count" "$test_skipped" "$compliance_done" "$algo_filing" "$prereg"
  printf '{"ts":"%s","scope":"pm_w1","briefs":%d,"eng_done":%d,"P1_2":"%s","P1_1":"%s","P1_3_prompts":"%s","P1_3_chain":"%s","P1_4":"%s","P1_6_back":"%s","P1_6_sb":"%s","P1_7":"%s","P1_8":"%s","P1_9":"%s"}\n' \
    "$ts" "$brief_count" "$eng_done" "$p1_2" "$p1_1" "$p1_3_prompts" "$p1_3_chain" "$p1_4" "$p1_6_back" "$p1_6_sb" "$p1_7" "$p1_8" "$p1_9"
  printf '{"ts":"%s","scope":"recruit","dms":%d,"calls":%d,"commits":%d,"runs":%d,"returns":%d}\n' \
    "$ts" "$dms" "$calls" "$commits" "$runs_count" "$returns_count"
  printf '{"ts":"%s","scope":"marketing","seed":"%s","xhs":%d,"douyin":%d,"wechat":%d,"jike":%d}\n' \
    "$ts" "$seed_posted" "$xhs_posts" "$douyin_posts" "$wechat_oa" "$jike_thread"
  printf '{"ts":"%s","scope":"risk","blockers":%d,"quotes":%d,"cost_top":"%s"}\n' \
    "$ts" "$blockers" "$quotes" "$cost_p95"
else
  printf 'Phase0   closed=%s  fixtures=%d  tests=%s  skipped=%s  compliance=%d  algo_filing=%d  prereg=%d\n' \
    "$phase0_closed" "$real_fixtures" "$test_count" "$test_skipped" "$compliance_done" "$algo_filing" "$prereg"
  printf 'PM_W1    briefs=%d  eng_done=%d/9  P1-2=%s  P1-1=%s  P1-3pr=%s  P1-3ch=%s  P1-4=%s  P1-6bk=%s  P1-6sb=%s  P1-7=%s  P1-8=%s  P1-9=%s\n' \
    "$brief_count" "$eng_done" "$p1_2" "$p1_1" "$p1_3_prompts" "$p1_3_chain" "$p1_4" "$p1_6_back" "$p1_6_sb" "$p1_7" "$p1_8" "$p1_9"
  printf 'Recruit  dms=%d  calls=%d  commits=%d  runs=%d  returns=%d\n' \
    "$dms" "$calls" "$commits" "$runs_count" "$returns_count"
  printf 'Marketing seed=%s  xhs=%d/10  douyin=%d/5  wechat=%d/1  jike=%d/1\n' \
    "$seed_posted" "$xhs_posts" "$douyin_posts" "$wechat_oa" "$jike_thread"
  printf 'Risk     blockers=%d  quotes=%d  cost_top=¥%s\n' \
    "$blockers" "$quotes" "$cost_p95"
fi

exit 0
