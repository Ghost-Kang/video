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
export UV_CACHE_DIR="${UV_CACHE_DIR:-$REPO_ROOT/.codex-tmp/uv-cache}"
mkdir -p "$UV_CACHE_DIR"

# ---------- Phase 0 closure ----------
real_fixtures=$(find backend/src/agent/cascade/fixtures/real_v1 -name "*.json" 2>/dev/null | wc -l | tr -d ' ')
test_count=$(cd backend 2>/dev/null && uv run pytest tests/test_cascade_contract.py tests/test_topic_intelligence.py --collect-only -q 2>/dev/null | awk '/::test_/ { n++ } END { print n + 0 }' || echo 0)
test_count=${test_count:-0}
test_skipped=$(cd backend 2>/dev/null && uv run pytest tests/test_cascade_contract.py tests/test_topic_intelligence.py 2>&1 | grep -oE '[0-9]+ skipped' | head -1 | grep -oE '[0-9]+' || true)
test_skipped=${test_skipped:-0}
# compliance: count actual checked top-level items (`- [x] **Done**`) across all
# compliance_done_*.md files. Probe flips to 1 only when ≥5 of the 5 mandated
# items are ticked. File existence alone (template stub) does NOT count as done —
# this was a real false-positive on W3D0 (file present, 0/5 ticked, probe said 1).
compliance_done=0
for f in docs/nexus/founder_log/compliance_done_*.md; do
  [ -e "$f" ] || continue
  ticks=$(grep -c '^- \[x\] \*\*Done\*\*' "$f" 2>/dev/null || true)
  ticks=${ticks:-0}
  [ "$ticks" -ge 5 ] && compliance_done=1
done
# algo_filing: file presence alone is not enough — must contain a real 受理回执号
# (digits, not the `<FILL e.g. 京网信备...` placeholder). Detect by matching a
# "受理回执号" line that includes ≥3 consecutive digits AND has no <FILL marker
# on the same line.
algo_filing=0
for f in docs/nexus/founder_log/algo_filing_*.md; do
  [ -e "$f" ] || continue
  if grep -E '受理回执号' "$f" 2>/dev/null | grep -vE '<FILL' | grep -qE '[0-9]{3,}'; then
    algo_filing=1
  fi
done
# prereg: file present AND no <FILL> placeholders remaining in committed text.
# (line 57 — the founder action checklist — uses `<FILL` literally as docs about
# the workflow; exclude that one descriptive line.)
prereg=0
for f in docs/nexus/founder_log/pre_registration_*.md; do
  [ -e "$f" ] || continue
  unfilled=$(grep -v 'Replace each `<FILL' "$f" 2>/dev/null | grep -cE '<FILL' || true)
  unfilled=${unfilled:-0}
  [ "$unfilled" -eq 0 ] && prereg=1
done

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

# ---------- PM W2 — ticket status (probes added per PM_W2_allocation.md §7) ----------
# P2-1 double-emit fix: Codex adds a concurrency test in test_analysis_service.py
p2_1=$(status_probe "backend/tests/test_analysis_service.py" "test_concurrent_same_url|test_double_emit|once_per_analysis_id")
# P2-2 S7/S8 upstream wiring: analysis_service.py raises S7/S8 from real upstream
p2_2=$(status_probe "backend/src/agent/cascade/analysis_service.py" "S7_UPSTREAM_TIMEOUT|S8_UPSTREAM_REFUSED")
# P2-4 LLM mode real-URL signoff: presence of the qualitative signoff file is the bar
if ls docs/nexus/founder_log/p2-4_qualitative_signoff_*.md >/dev/null 2>&1; then
  p2_4="done"
elif [ -f scripts/p2-4_run_real_urls.py ]; then
  p2_4="partial"
else
  p2_4="open"
fi
# P2-5 anchor sidebar polish: reuse pill text + sort toggle text both present
p2_5_card=$(status_probe "frontend/src/components/anchors/AnchorCard.tsx" "已用|reuse_count > 0")
p2_5_sidebar=$(status_probe "frontend/src/components/anchors/AnchorSidebar.tsx" "按使用次数|按时间|AnchorSort")
if [ "$p2_5_card" = "done" ] && [ "$p2_5_sidebar" = "done" ]; then
  p2_5="done"
elif [ "$p2_5_card" != "open" ] || [ "$p2_5_sidebar" != "open" ]; then
  p2_5="partial"
else
  p2_5="open"
fi

# ---------- W3 ticket probes (Claude already-done + Codex new + frontend Claude) ----------
# P3-3 admin creator view: backend list_creators + frontend page
p3_3_back=$(status_probe "backend/src/agent/cascade/storage.py" "async def list_creators")
p3_3_front=$(status_probe "frontend/src/pages/AdminCreators.tsx" "AdminCreators")
if [ "$p3_3_back" = "done" ] && [ "$p3_3_front" = "done" ]; then
  p3_3="done"
elif [ "$p3_3_back" != "open" ] || [ "$p3_3_front" != "open" ]; then
  p3_3="partial"
else
  p3_3="open"
fi
# P3-4 PR template
[ -f .github/PULL_REQUEST_TEMPLATE.md ] && p3_4="done" || p3_4="open"
# P3-5 anchor analytics page
p3_5=$(status_probe "frontend/src/pages/AnchorAnalytics.tsx" "AnchorAnalytics")
# P3-6 anchor reuses endpoint (Codex)
p3_6=$(status_probe "backend/src/agent/cascade/anchors.py" "list_reuses|async def list_reuses")
# P3-7 Toprador hardening (Codex) — circuit_breaker module + analysis_service
# uses it. Match by symbols actually present (before_call / record_failure).
p3_7=$(status_probe "backend/src/agent/cascade/circuit_breaker.py" "before_call|record_failure|FAILURE_THRESHOLD")
# P3-8 Reality Checker remaining hazards — closure marker file is done
# state; triage marker file is partial; brief STUB alone is open.
if ls docs/nexus/founder_log/p3-8_closed_*.md >/dev/null 2>&1; then
  p3_8="done"
elif ls docs/nexus/founder_log/p3-8_triage_*.md >/dev/null 2>&1; then
  p3_8="partial"  # founder triaged but Codex hasn't finished closure
elif [ -f docs/nexus/handoff/codex_backend_P3-8.md ]; then
  p3_8="open"  # STUB only — awaiting founder triage
else
  p3_8="open"
fi

# Count W3 engineering tickets done (P3-3..P3-8 minus P3-1/P3-2 which are blocked on API key)
w3_eng_done=0
for t in "$p3_3" "$p3_4" "$p3_5" "$p3_6" "$p3_7" "$p3_8"; do
  [ "$t" = "done" ] && w3_eng_done=$((w3_eng_done + 1))
done
# P2-6 eval harness: runner.py existence + CLI script
p2_6_runner=$(status_probe "backend/src/agent/cascade/eval/runner.py" "run_eval|class EvalReport|def run_eval")
if [ "$p2_6_runner" = "done" ] && [ -f scripts/p2-6_eval.py ]; then
  p2_6="done"
elif [ "$p2_6_runner" = "done" ] || [ -f scripts/p2-6_eval.py ]; then
  p2_6="partial"
else
  p2_6="open"
fi

# Count W2 engineering tickets done
w2_eng_done=0
for t in "$p2_1" "$p2_2" "$p2_4" "$p2_5" "$p2_6"; do
  [ "$t" = "done" ] && w2_eng_done=$((w2_eng_done + 1))
done

# ---------- W4 ticket probes ----------
p4_1="open"
for f in docs/nexus/founder_log/p2-6_baseline_*.json; do
  [ -e "$f" ] || continue
  if grep -q '"mode": "llm"' "$f" 2>/dev/null && grep -q '"overall_judge_realism_avg": [1-9]' "$f" 2>/dev/null; then
    p4_1="done"
  fi
done
p4_2_back=$(status_probe "backend/src/agent/cascade/storage.py" "async def list_events")
p4_2_front=$(status_probe "frontend/src/pages/AdminEvents.tsx" "AdminEvents")
if [ "$p4_2_back" = "done" ] && [ "$p4_2_front" = "done" ]; then
  p4_2="done"
elif [ "$p4_2_back" != "open" ] || [ "$p4_2_front" != "open" ]; then
  p4_2="partial"
else
  p4_2="open"
fi
p4_3=$(status_probe "backend/src/agent/cascade/events.py" "cascade_retry|cascade_circuit_open|cascade_cache_hit|cascade_cache_miss")
p4_4=$(status_probe "backend/src/agent/cascade/storage.py" "idx_events_thread_ts|idx_events_type_ts")
p4_5_front=$(status_probe "frontend/src/pages/AdminCost.tsx" "AdminCost|成本看板")
p4_5_hook=$(status_probe "frontend/src/hooks/useGenerationCost.ts" "useGenerationCost|generation_cost")
if [ "$p4_5_front" = "done" ] && [ "$p4_5_hook" = "done" ]; then
  p4_5="done"
elif [ "$p4_5_front" != "open" ] || [ "$p4_5_hook" != "open" ]; then
  p4_5="partial"
else
  p4_5="open"
fi
p4_6_storage=$(status_probe "backend/src/agent/cascade/storage.py" "save_toprador_cache|load_toprador_cache|cleanup_expired_toprador_cache")
if [ "$p4_6_storage" = "done" ] && [ -f backend/tests/test_toprador_cache_persistence.py ]; then
  p4_6="done"
elif [ "$p4_6_storage" != "open" ] || [ -f backend/tests/test_toprador_cache_persistence.py ]; then
  p4_6="partial"
else
  p4_6="open"
fi
p4_7_storage=$(status_probe "backend/src/agent/cascade/storage.py" "async def retention_sweep")
if [ "$p4_7_storage" = "done" ] && [ -f scripts/retention_sweep.py ]; then
  p4_7="done"
elif [ "$p4_7_storage" != "open" ] || [ -f scripts/retention_sweep.py ]; then
  p4_7="partial"
else
  p4_7="open"
fi
if [ -f scripts/cost_calibration.py ] && ls docs/nexus/founder_log/cost_calibration_*.md >/dev/null 2>&1; then
  p4_8="done"
elif [ -f scripts/cost_calibration.py ]; then
  p4_8="partial"
else
  p4_8="open"
fi
if ls docs/nexus/founder_log/p4-9_toprador_staging_*.md >/dev/null 2>&1; then
  p4_9="done"
elif [ -f scripts/p4-9_toprador_staging.py ]; then
  p4_9="blocked"
else
  p4_9="open"
fi
w4_eng_done=0
for t in "$p4_1" "$p4_2" "$p4_3" "$p4_4" "$p4_5" "$p4_6" "$p4_7" "$p4_8" "$p4_9"; do
  [ "$t" = "done" ] && w4_eng_done=$((w4_eng_done + 1))
done

# Phase indicator — newest active allocation doc wins.
w2_allocation_exists="NO"
[ -f docs/nexus/PM_W2_allocation.md ] && w2_allocation_exists="YES"
w3_allocation_exists="NO"
[ -f docs/nexus/PM_W3_allocation.md ] && w3_allocation_exists="YES"
w4_allocation_exists="NO"
[ -f docs/nexus/PM_W4_allocation.md ] && w4_allocation_exists="YES"
active_phase="W1"
[ "$w2_allocation_exists" = "YES" ] && active_phase="W2"
[ "$w3_allocation_exists" = "YES" ] && active_phase="W3"
[ "$w4_allocation_exists" = "YES" ] && active_phase="W4"

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
# seed_posted: file presence alone is not enough — match same pattern as
# compliance / algo_filing probes (truth-check content, not existence). The
# template line `seed_url: <FILL ...>` must be replaced by a real URL containing
# `http`. Without that, the founder has the template but hasn't actually posted.
seed_posted="NO"
for f in docs/nexus/founder_log/seed_post_url_*.md; do
  [ -e "$f" ] || continue
  if grep -E '^seed_url:' "$f" 2>/dev/null | grep -v '<FILL' | grep -q 'http'; then
    seed_posted="YES"
  fi
done
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
  printf '{"ts":"%s","scope":"pm_w2","active":"%s","w2_eng_done":%d,"P2_1":"%s","P2_2":"%s","P2_4":"%s","P2_5":"%s","P2_6":"%s"}\n' \
    "$ts" "$active_phase" "$w2_eng_done" "$p2_1" "$p2_2" "$p2_4" "$p2_5" "$p2_6"
  printf '{"ts":"%s","scope":"pm_w3","w3_eng_done":%d,"P3_3":"%s","P3_4":"%s","P3_5":"%s","P3_6":"%s","P3_7":"%s","P3_8":"%s"}\n' \
    "$ts" "$w3_eng_done" "$p3_3" "$p3_4" "$p3_5" "$p3_6" "$p3_7" "$p3_8"
  printf '{"ts":"%s","scope":"pm_w4","active":"%s","w4_eng_done":%d,"P4_1":"%s","P4_2":"%s","P4_3":"%s","P4_4":"%s","P4_5":"%s","P4_6":"%s","P4_7":"%s","P4_8":"%s","P4_9":"%s"}\n' \
    "$ts" "$active_phase" "$w4_eng_done" "$p4_1" "$p4_2" "$p4_3" "$p4_4" "$p4_5" "$p4_6" "$p4_7" "$p4_8" "$p4_9"
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
  printf 'PM_W2    active=%s  w2_eng_done=%d/5  P2-1=%s  P2-2=%s  P2-4=%s  P2-5=%s  P2-6=%s\n' \
    "$active_phase" "$w2_eng_done" "$p2_1" "$p2_2" "$p2_4" "$p2_5" "$p2_6"
  printf 'PM_W3    w3_eng_done=%d/6  P3-3=%s  P3-4=%s  P3-5=%s  P3-6=%s  P3-7=%s  P3-8=%s\n' \
    "$w3_eng_done" "$p3_3" "$p3_4" "$p3_5" "$p3_6" "$p3_7" "$p3_8"
  printf 'PM_W4    active=%s  w4_eng_done=%d/9  P4-1=%s  P4-2=%s  P4-3=%s  P4-4=%s  P4-5=%s  P4-6=%s  P4-7=%s  P4-8=%s  P4-9=%s\n' \
    "$active_phase" "$w4_eng_done" "$p4_1" "$p4_2" "$p4_3" "$p4_4" "$p4_5" "$p4_6" "$p4_7" "$p4_8" "$p4_9"
  printf 'Recruit  dms=%d  calls=%d  commits=%d  runs=%d  returns=%d\n' \
    "$dms" "$calls" "$commits" "$runs_count" "$returns_count"
  printf 'Marketing seed=%s  xhs=%d/10  douyin=%d/5  wechat=%d/1  jike=%d/1\n' \
    "$seed_posted" "$xhs_posts" "$douyin_posts" "$wechat_oa" "$jike_thread"
  printf 'Risk     blockers=%d  quotes=%d  cost_top=¥%s\n' \
    "$blockers" "$quotes" "$cost_p95"
fi

exit 0
