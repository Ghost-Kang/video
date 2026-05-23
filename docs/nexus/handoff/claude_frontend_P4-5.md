# Claude handoff — P4-5 generation_cost admin 仪表盘

**Owner**: Claude session (frontend + small backend aggregation)
**Source of truth**: P3-3 admin layout、P4-2 admin events 端点、`backend/src/agent/cascade/storage.py:sum_generation_cost`、`backend/src/agent/cascade/events.py` `generation_cost` event schema
**Status**: DRAFT · no upstream blocker(可直起)
**Time budget**: 1 day
**Allocation**: `PM_W4_allocation.md §3.1`(W3D3 新加,补 P4-1 blocked-on-key idle)

---

## 0. 背景

Phase 1 内测进入 concierge 阶段后,每个 creator 跑 1 次会触发 1+ `generation_cost` event(call_kind ∈ {analysis, rewrite, shot, audio, video}),`cost_fen` 累积。

Founder + PM 需要一眼看到:
- 今日总成本 / 本周总成本 / 累计
- 按 creator 拆解 — 哪个用户成本最高 / 是否有 runaway
- 按 call_kind 拆解 — analysis / rewrite / shot 各占多少
- 与 `cost_guard` PREDICT 值对比 — 实际 vs 预算

P4-5 在 `/admin/cost` 落这个看板,**80% 用前端聚合 P4-2 已有的 `/api/events?type=generation_cost` 输出**,20% 后端补一个轻聚合端点。

---

## 1. Done-signal

- `/admin/cost` 路由可访问(在 main.tsx 注册,与 /admin/creators + /admin/events 同级)
- 页面展示:
  - **顶部 KPI 行**:今日 ¥X / 本周 ¥X / 累计 ¥X(以 `cost_fen` / 100 显示)
  - **by user 排行表**:Top 10,列 user_id + 总 cost_cny + 调用次数 + 平均/次
  - **by call_kind 饼图或柱状**:analysis / rewrite / shot / audio / video 各占比
  - **每日 trend 折线**:最近 14 天 daily total
  - **runaway alert**:任一 user 今日 cost_cny > 5 时高亮 amber;> 10 高亮 red
- 后端可选补 `/api/cost/aggregate?since=2026-05-20`(若纯前端聚合性能慢)
- 3 个 vitest 用例:聚合算 / runaway 判定 / trend 数据点
- `pnpm tsc --noEmit` 0 错;`pnpm vitest run` 全绿

---

## 2. 实现指引

### 2.1 默认路径(前端聚合)

1. 调 `/api/events?type=generation_cost&limit=1000`(P4-2 端点已存在);若 has_more 翻页拉满到累计 ≥ 14 天数据
2. 前端聚合:
   - 按 `payload.cost_fen / 100` 求和(本日/本周/累计)
   - 按 `user_id` group → 排序
   - 按 `payload.call_kind` group → 饼图数据
   - 按 `ts` 切日 → trend 折线
3. runaway 判定:nested loop over events,per-user 累积 today's cost > 5 / 10 阈值

### 2.2 后端 fallback(若前端聚合 > 500ms)

加 `/api/cost/aggregate` 在 `server.py` `_handle_http`:
- qs 参数:`since` (ISO 8601), `until` (可选)
- 复用 `storage.sum_generation_cost(...)` 但扩展为返回 by-user / by-kind / by-day buckets
- 返回 `{kpis: {today, week, all_time}, by_user: [...], by_kind: {...}, by_day: [...]}`

**先走默认路径**,只有前端聚合实测慢才走 fallback。理由:Phase 1 内测 ~30 个 events/day × 7 day × 5 weeks ≤ 1000 行,纯前端聚合应 < 50ms。

### 2.3 复用现有组件

- 折线/饼图复用 `AnchorAnalytics.tsx` 已有 chart 套件(grep `frontend/src/pages/AnchorAnalytics.tsx` 看用了什么库)
- 表格复用 `AdminCreators.tsx` 的样式 token(tailwind `rounded-2xl bg-white border border-stone-200`)

---

## 3. 边界(不在此票)

- **不做** 实时推送 / SSE
- **不做** 历史数据 export(CSV/JSON download)— Phase 1 用 founder 直接看页面就够
- **不做** alert 通知(邮件/微信)— 仅页面高亮
- **不做** budget 设置 UI(目前 `cost_guard` 在 config.py 硬编码;P5/P6 才上 UI 配置)
- **不做** RBAC — 与 P3-3 / P4-2 同口径,assume admin-only,reverse-proxy 拦截

---

## 4. Upstream dep

- ✅ P4-2 `/api/events` 端点
- ✅ 现有 `generation_cost` event schema (`events.py` `_REQUIRED_FIELDS["generation_cost"]`)
- ✅ `cost_guard` PREDICT 常量(`backend/src/agent/cascade/cost_guard.py`)

无 blocker,W4D1-2 起跑。

---

## 5. 失败兜底

- 若 1000 events 聚合慢 → 走 §2.2 backend aggregate 端点
- 若 events 表里 `generation_cost` 数据稀疏(Phase 1 早期)→ 页面优雅展示 "尚无成本数据" 而不是空表
- runaway 阈值需要 founder 调整 → 暂时硬编码在 `AdminCost.tsx` const,后续 §"不在此票" 升级为 config

---

## 6. Output 清单(W4D2 末)

- `frontend/src/pages/AdminCost.tsx`(新文件)
- `frontend/src/hooks/useGenerationCost.ts`(新文件,聚合逻辑独立可测)
- `frontend/src/hooks/__tests__/useGenerationCost.test.ts`(3 cases)
- `frontend/src/main.tsx`(注册路由)
- (可选)`backend/src/agent/server.py` + `backend/src/agent/cascade/storage.py` 加 `/api/cost/aggregate`
- commit:`feat(P4-5): admin generation_cost dashboard — /admin/cost`

---

## 7. 决策权(W4D1 founder 开工前可调整)

- 是否扩展 KPI 行加 "本月 ¥X"?(默认不加,Phase 1 内测才 6 周不到 1 月)
- runaway 阈值 ¥5 today / ¥10 ever 是否对齐 founder 心理预期?
- 折线 14 天 vs 30 天 vs 全部?(默认 14 天)

founder 若无意见,Claude 按默认推进。
