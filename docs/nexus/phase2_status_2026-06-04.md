# Phase 2 状态对账 — 2026-06-04

**作者**: Claude(phase2「按顺序做 8 件事」step 8)
**性质**: 把 [`phase2_master_plan_2026-05-31.md`](phase2_master_plan_2026-05-31.md) 的计划项 + canvas 统筹 P2 对账到**今天的真实状态**(均经代码 / PR / prod / 浏览器真机核验)。master plan 本体不改写,以本文为「现在到哪了」单一参照。

## prod 实况(HEAD `ea3e12b`)
- `REWRITE_ENABLED=1`、`CASCADE_REWRITE_MIN_CONFIDENCE=0.5`、`CANVAS_INTERRUPT_GATE=1`、`CASCADE_REWRITE_UPSTREAM=llm`(`/opt/cascade/.env`)。
- 闭环 `分析→改写→生成→发布` 全建齐 + 部署 + **浏览器真机端到端验证通过**(邀请码 `cascade`)。

## 计划对账

| 计划项 | 状态 | 证据 |
|---|---|---|
| **P0-a 还债** canvas.db 收口 | ✅ | `resolve_data_dir` 已复用(canvas_persistence/db.py) |
| P0-a 成本遥测真 provider | ✅ | http_router 不再硬编码 'fixture' |
| P0-a 改写缓存版本守卫 | ✅ | `REWRITE_PIPELINE_REVISION`(现 =3) |
| P0-a 工具失败 mark_failed | ✅ | `_push_failure_frame` 写 `ctx["tool_failure"]` → run_agent mark_failed(优先于 review) |
| **P0-b 解封改写** | ✅ **本会话上线** | confidence 闸 + kill-switch + D6 质量门 5/5;[[project_rewrite_unseal_live]] |
| **P0-c 凭证轮换** | 🔴 **未做(founder-only)** | 4 项泄漏凭证;master plan 列为上线硬 Gate,至今未关 |
| **P1 草稿图 + cost_guard** | ✅ | 生成 leg 部署;`cost_guard` 在 enqueue 前拦(cascade.py:464/685/921) |
| **P2 发布收尾** | ✅ **本会话补全** | PR#3(真镜头图 + niche 去硬编码 + 禁词 scrub)+ 分字段复制(标题/话题/脚本)部署 |
| **P3 视频链路** | ✅ | 图生视频 + 合成,prod 真跑通 |
| P3 配额付费 | 🟡 核算完,实现待定 | 成本核算见 [`phase2_pricing_cost_analysis_2026-06-04.md`](phase2_pricing_cost_analysis_2026-06-04.md);quota/credit 系统未建(❓7 待 founder 定数字) |
| P3 埋点收口 | 🟡 漏斗洞已堵 | 6 个前端遥测事件曾全被 /api/events 400 拒(浏览器验证抓出),已补 allowlist + emit 兜底;25 事件全量收口仍部分 |
| **Canvas interrupt 闸门** | ✅ **本会话启用** | `build_interrupt_on()` LIVE,拦 3 个烧钱工具;[[project_canvas_p2_interrupt_gate]] |
| Canvas time-travel | ✅ 部署 | PR#1 合并;needs_regen / 版本对比 / 回滚 |
| Canvas bridge / 锚点级联 / 逐镜取消 / write_todos | ✅ 部署 | PR#2;[[project_canvas_unified_direction]] |
| **INTV 用户访谈轨** | 🟡 开跑包就绪,未启动 | [`phase2_interview_run_packet_2026-06-04.md`](phase2_interview_run_packet_2026-06-04.md)(招募 DM + runsheet + 落点模板,已验 200);需 founder 招真人 |
| **真验证(浏览器)** | ✅ **本会话解锁** | Playwright 直打 prod 可用(「挂着」是陈旧判断);闭环真机验证通过 |
| **Phase 2 官方 Gate**(30人 Beta / 留存 / 付费) | ⬜ 未开始 | 闭环既已可用,这是下一大块:招募 + 量漏斗 |

## 本会话新增/修复(2026-06-04)
- 改写解封上线(五关+强点关 prompt rev3 + confidence 闸 + kill-switch + 源解析修复 → D6 5/5)。
- 浏览器真机验证解锁 + 全闭环端到端验证。
- 🐛 修:6 个前端遥测事件被 /api/events 400 拒(等待漏斗丢数据)。
- 发布包分字段复制。
- 工程债 P0-a 全部核实已闭。
- 配额付费成本核算 + INTV 开跑包。

## 仍欠(优先级)
1. 🔴 **P0-c 凭证轮换**(founder-only,Beta 扩量硬线)。
2. **per-run 成本 cap 退化**(run_id 恒 None,只剩 ¥30/天/用户生效)—— 配额付费前修(见 pricing 核算洞察 3)。
3. **Phase 2 官方 Gate = 跑 Beta**:招 30 人 + INTV 回灌 + 量留存/转化/成本 + ≥5 人付费。
4. 配额付费实现(待 ❓7 数字)、25 事件全量收口。

> 证据驱动(retro 铁律):闭环建好≠验证够好。下一步重心 = INTV 真实用户 + Beta 漏斗,而非继续堆功能。
