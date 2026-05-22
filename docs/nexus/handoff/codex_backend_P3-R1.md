# Codex handoff — P3-R1 compliance batch (PII + cross-border block + minor audit)

**Owner**: Codex session
**Source of truth**: `docs/nexus/04_compliance_check.md §"Top 5 must-do before 10-user trial"` 第 2, 3, 4 项
**Status**: ready to execute (no founder triage gate — 3 well-scoped engineering tasks)
**Time budget**: 1 day (3 tasks × ~0.25-0.5 day each, all in one PR)
**Why batched**: all three are Phase 0 compliance gate items, share the same review surface (`adapter.py` + `failures.py` + contract tests), and Codex can ship a single coherent PR rather than three small ones.

---

## 0. Why this ticket exists

`founder_log/compliance_done_2026-05-21.md` lists 5 items. #2/#3/#4 are engineering (no legal署名 needed); #1/#5 are pure-docs and founder-only. PM is fan-out routing the 3 engineering items to Codex so founder can spend the same window writing the legal docs + filing 算法备案.

When this PR merges, founder ticks the corresponding boxes in `compliance_done_2026-05-21.md` and Phase 0 `compliance` flag becomes真实 closed (not just file-existence闭环 — the probe will count `[x]` ticks after the W3D0 probe fix).

---

## 1. Sub-ticket A — `_strip_pii` 加 IP + author_name 字段(0.25 day)

### What
Extend `_KNOWN_PII_KEYS` in `backend/src/agent/cascade/adapter.py:45-49`.

Currently includes: `author_uid, author_handle, author_avatar_url, uid, author_id, author_nickname, user_phone` (last 3 added Stage 4).

**Add**: `author_name`, `ip_address`, `user_ip`.

(`author_nickname` already present — compliance checklist #2 listed it as new but it's done. Tick the box without code change for that one.)

### Files
| Path | Change |
|---|---|
| `backend/src/agent/cascade/adapter.py:45-49` | append 3 keys to `_KNOWN_PII_KEYS` frozenset |
| `backend/tests/test_cascade_contract.py` | add 1 test `test_strip_pii_ip_and_author_name` — feeds payload containing `ip_address` + `user_ip` + `author_name` → asserts they're stripped + `W10_AUTHOR_PII_STRIPPED` warnings emitted |

### Done-signal
- `grep -E '"ip_address"|"user_ip"|"author_name"' backend/src/agent/cascade/adapter.py` → 3 matches in `_KNOWN_PII_KEYS`
- `uv run pytest backend/tests/test_cascade_contract.py::test_strip_pii_ip_and_author_name -v` passes
- Existing PII tests still pass (no regression on `author_uid` etc.)

### Legal anchor
PIPL §4(个人信息定义包含 IP); ICP 备案场景下 IP 是必须 strip 的 PI. See `04_compliance_check.md §"Top 5" 第 2 项`.

---

## 2. Sub-ticket B — W9 cross-border hard block 开关(0.25 day)

### What
Today `adapter.py:177-185` emits a `W9_CROSS_BORDER_SOURCE` warning for YouTube/TikTok/Instagram URLs but does NOT block. Add a config toggle that, when on, converts this to a **HardFailure** — Phase 1 默认 ON to彻底回避境外平台分析的双重风险(数据出境 + 跨境著作权).

### Files
| Path | Change |
|---|---|
| `backend/src/agent/config.py` | add `STRICT_CROSS_BORDER_REJECT: bool = os.getenv("STRICT_CROSS_BORDER_REJECT", "1") == "1"` (default ON for Phase 1) |
| `backend/src/agent/cascade/failures.py:17` (FailureCode enum) | add `S9_CROSS_BORDER_BLOCKED = "S9_CROSS_BORDER_BLOCKED"` — **new code, not overloaded onto S8**. S8 means "upstream refused"; this is "we refused locally" — semantically distinct, easier to grep |
| `backend/src/agent/cascade/failures.py` (RECOVERY_HINTS dict) | add 人话 hint: `"这条链接来自境外平台,Phase 1 试用期只支持境内平台(抖音/小红书/快手/B站)。换一条境内链接吧。"` |
| `backend/src/agent/cascade/adapter.py:175-185` | After the host match: if `config.STRICT_CROSS_BORDER_REJECT` is True, `raise HardFailure(FailureCode.S9_CROSS_BORDER_BLOCKED, f"cross-border platform blocked: {host}")`. Else fall through to existing warning emit (current behavior) |
| `backend/tests/test_cascade_contract.py` | add `test_cross_border_hard_block_default_on` (default config → S9 raised on YouTube URL) + `test_cross_border_warning_when_disabled` (env override → warning emitted, no raise) |

### Done-signal
- `grep -n "STRICT_CROSS_BORDER_REJECT" backend/src/agent/config.py` matches
- `grep -n "S9_CROSS_BORDER_BLOCKED" backend/src/agent/cascade/failures.py backend/src/agent/cascade/adapter.py` matches in both
- `uv run pytest backend/tests/test_cascade_contract.py -k cross_border -v` 2/2 passes
- `STRICT_CROSS_BORDER_REJECT=0 uv run pytest backend/tests/test_cascade_contract.py -k cross_border -v` still passes (toggle works both ways)

### Choice flagged for review
The original compliance brief proposed `raise HardFailure(S8_UPSTREAM_REFUSED, "cross_border_blocked")`. I'm proposing a **new code S9 instead** because:
1. S8 means "upstream系统 refused" — overloading it for "我们本地 refused" muddies grep / metrics / RECOVERY_HINTS specificity
2. S9 lets the UI show a 人话 hint that's actually about cross-border (not "系统繁忙")
3. One new enum value is cheaper than the cognitive overhead of an overloaded code

If founder/PM prefer overloading S8 to avoid expanding the enum, downgrade this sub-ticket to "use S8 with detail string"; everything else stays.

### Legal anchor
PIPL §38-§39 (出境告知 + 单独同意); 不接境外 URL 就不存在用户主动引入的出境 PI. `04_compliance_check.md §"Top 5" 第 3 项`.

---

## 3. Sub-ticket C — 未成年人关键词 audit + 日志告警(0.5 day)

### What
Inspect each scene's `dialogue` + `visual_content` (and optionally `subject` if present) for未成年人 keywords. Emit **soft warning** `W14_MINOR_SUBJECT_DETECTED` — INFO severity, **does NOT block** Phase 1 — purely observational so we have data for Phase 2 hard拦截.

### Keyword list (founder, 点头确认前请说一声)
- 中文: `宝宝`, `小孩`, `婴儿`, `幼儿`, `小朋友`, `儿童`, `小宝`
- 英文 (lowercase compare): `baby`, `kid`, `child`, `children`, `infant`, `toddler`

(Founder may add / remove — if you make changes, update this brief + tick checklist #4 only after the keyword list ships.)

### Files
| Path | Change |
|---|---|
| `backend/src/agent/cascade/failures.py:57-72` (WarningCode enum) | add `W14_MINOR_SUBJECT_DETECTED = "W14_MINOR_SUBJECT_DETECTED"` |
| `backend/src/agent/cascade/failures.py` (RECOVERY_HINTS) | add 人话 (INFO 级,UI 一般不展示但留着备用): `"系统注意到这条视频涉及未成年人。Phase 1 仅记录、不拦截。"` |
| `backend/src/agent/cascade/minor_audit.py` (**new file**) | module-level `MINOR_KEYWORDS: frozenset[str]` + `def detect_minor_subjects(scenes: list[Scene]) -> list[str]` returning offending scene indices (1-based to match scene `no`) |
| `backend/src/agent/cascade/adapter.py` (`_normalize_scenes` tail or in `normalize_analysis_result` after `_normalize_scenes` returns) | call `detect_minor_subjects` on parsed scenes; for each hit append a `Warning_(W14, field=f"scenes[{i}]", message="minor subject keyword detected", severity=Severity.INFO)` |
| `backend/src/agent/cascade/storage.py` (audit log) | extend `analysis_returned` event payload — if any W14 warnings present, include `minor_audit: {hit_count: N, scene_indices: [...]}` for offline review. Founder reads via SQLite directly during Phase 1 |
| `backend/tests/test_cascade_contract.py` | `test_minor_audit_keyword_hit` (scene with `dialogue` 含"宝宝" → W14 emitted, no HardFailure) + `test_minor_audit_no_false_positive` (scene with "宝藏" — substring overlap — does NOT trigger) |

### Implementation note on the false-positive test
`宝宝` ⊂ `宝藏` — naive `in` check trips this. Use **word-boundary matching for English** (regex `\b(baby|kid|...)\b`) and **exact-substring for Chinese** with a manual deny-list of known overlaps (e.g. don't fire on `宝藏`, `小巷`, `儿童相见不相识` — last one is poetic context that probably shouldn't even appear, but the deny-list pattern is the right shape).

If founder wants ultra-conservative (zero false negatives) → drop the deny-list, accept some false positives in W14 since it's INFO-only audit data; humans review the audit log anyway. Document the choice in module docstring.

### Done-signal
- `backend/src/agent/cascade/minor_audit.py` exists with `MINOR_KEYWORDS` + `detect_minor_subjects`
- `grep -n "W14_MINOR_SUBJECT_DETECTED" backend/src/agent/cascade/failures.py backend/src/agent/cascade/adapter.py` matches in both
- `uv run pytest backend/tests/test_cascade_contract.py -k minor -v` both cases pass
- Manually `sqlite3 backend/data/messages.db "SELECT json_extract(payload_json,'\$.minor_audit') FROM events WHERE event_name='analysis_returned' AND json_extract(payload_json,'\$.minor_audit') IS NOT NULL LIMIT 5"` returns non-null rows when test-触发 (founder verifies after PR merges and 1 real run with未成年人 content)

### Legal anchor
未成年人保护法 §73; 未成年人网络保护条例 (2024) §27. `04_compliance_check.md §"Top 5" 第 4 项`.

---

## 4. Single-PR shape (recommended)

One branch, one PR, three commits (or one squash — Codex preference):

```
git checkout -b codex/p3-r1-compliance-batch
# commit A: PII keys (~5 line diff + 1 test)
# commit B: cross-border hard block (~30 line diff + 2 tests + new FailureCode + RECOVERY_HINTS)
# commit C: minor audit (~80 line diff + new module + 2 tests + W14 + storage event hook)
```

PR title: `feat(compliance): P3-R1 batch — PII keys + cross-border block + minor audit`

PR description should link to this brief + cite `04_compliance_check.md §"Top 5"` items 2/3/4.

---

## 5. Done-signal for entire P3-R1 (PM probe)

PM will add a probe to `scripts/check_progress.sh`:

```bash
p3_r1_pii=$(grep -c '"ip_address"\|"user_ip"\|"author_name"' backend/src/agent/cascade/adapter.py 2>/dev/null || echo 0)
p3_r1_cross=$(grep -c "S9_CROSS_BORDER_BLOCKED" backend/src/agent/cascade/failures.py 2>/dev/null || echo 0)
p3_r1_minor=$([ -f backend/src/agent/cascade/minor_audit.py ] && echo 1 || echo 0)
# all 3 must be ≥1 for P3-R1=done
```

---

## 6. NOT in this ticket

- Phase 2 hard拦截 of未成年人 content (P3-R1 is INFO-only audit; blocking is Phase 2)
- 阿里云/腾讯云内容安全 API 集成 (Phase 2, separate ticket)
- Auto-extending `MINOR_KEYWORDS` based on ML — manual list only
- UI surface for W14 — events table is sufficient for Phase 1 audit
- Compliance items #1 (用户协议) + #5 (删除条款) — founder-only, not Codex work

---

## 7. PM notes

- Pre-condition: none. All three sub-tickets are well-scoped, no blocking deps
- 4-owner allocation: while Codex works on this, founder writes #1 + #5 docs (parallel,~2h) and PM updates `check_progress.sh` compliance probe to count `[x]` ticks rather than file existence
- Expected close: W3D1 EOD (~24h from brief creation 2026-05-21)
- If Codex hits an unexpected design issue, write a `handoff/codex_backend_P3-R1_blocked.md` and ping founder/PM before defaulting to a workaround

**Carry the [[pm-4-owner-allocation-rule]]** — this brief is the §3.2 Codex row for W3 W3D0+ extension.
