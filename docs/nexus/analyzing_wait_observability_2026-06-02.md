# 分析等待态：观测口径 + P2-3 工程债结论

**日期**：2026-06-02
**关联 commit**：`feat/analyzing-wait-redesign`（AnalyzingHero 沉浸骨架 + 进度上移 + 承诺松绑 + 等待埋点）
**关联 memory**：`project_analyzing_wait_redesign`
**状态**：前端已实现+本地验证，**prod 待部署**

本文落两件事：① 这轮埋点上线后怎么在 `/admin/events` 量化「改得对不对」；② 产品方案里 P2-3「后端真实逐幕进度」的可行性结论（**investigate 后推翻原假设**）。

---

## 一、P2-3「后端按已完成幕数推真实进度」—— 结论：架构不支持，不排期

### 代码事实（investigate before guess）

分析 pipeline 的进度阶段（`backend/src/agent/cascade/analysis_service.py`）：

| 阶段 | percent | 说明 | 是否逐幕 |
|---|---|---|---|
| `resolve_url` | 5% | 拉抖音 CDN 直链 | — |
| `ark_overlay` | 15% → 85% | **`analyze_video_direct` 单次 ARK 豆包视觉调用** | ❌ 黑盒一次返回 |
| `transcribe` | 92% | 整理时间线 + 字幕对齐 | — |
| `clip` | 95% | `extract_scene_clips` 逐幕剪辑片段 | ✅ 但很快 |
| `done` | 100% | 完成 | — |

关键：`analysis_service.py:500` 注释明确 **"Single-shot ARK Doubao vision call → contract-shaped payload"**。15%→85% 这 **70% 的跨度就是那一个慢调用**（占整个分析的大部分耗时），豆包视觉模型一次吃整个视频、一次性吐出全部 scenes + 10 维爆点 + 逐幕维度。**中间没有「已完成第 N/M 幕」这种可上报的状态** —— 模型是黑盒。

前端 `AnalysisProgress` 在这 70% 跨度里做的「creep 爬坡」本质是**演**出来的进度感，这是已知且刻意的设计（用户要的是确定感，不是审计精度）。

### 为什么不该硬做 P2-3

产品 agent 的 P2-3 假设「分析是逐幕的、能报 N/M」。代码证明这是 **single-shot**，假设不成立。要做出「真实逐幕进度」，唯一路径是把单次 ARK 调用拆成**按时间窗口分段多次调用**，代价：

- 调用次数 ↑ → 成本 ↑（每次 ARK vision 都要钱，见 `cost_guard`）
- 串行分段 → 总延迟 ↑（与「让等待更短」的目标相反）
- toprador 对齐的 10 维爆点 / 主题 / 总结**需要全局视角**，分段会丢失跨幕的整体判断 → 分析质量倒退

**不划算，不排期。** 标记为「已评估 → 架构不支持」。

### 已落地的替代（前端侧，已规避打脸风险）

- AnalyzingHero 的逐幕扫描动效 + 「逐幕扫描中」用的是**过程性表达**，没有声称「已拆完第 2 幕」这类可被证伪的精确断言 → 不制造新的「打脸」点。✅ 已在本次实现里规避。
- 倒计时归零后跟阶段名 + 安抚文案，不空转 00:00。✅ 已做。

### 唯一值得的小增量（可选，低优先级）

`clip` 阶段（95%，`extract_scene_clips` 逐幕循环）**可以**推真实 `current/total` 进度。但：clip 用 ffmpeg `-c copy` 很快、且只占 95→100 的 5% 跨度，**体感增益极小**。建议**不做**，除非将来 clip 阶段变慢。

---

## 二、埋点观测口径（上线后在 `/admin/events` 看什么）

本轮埋了 6 个事件（`trackEvent` fire-and-forget，复用现有 `/api/events` + events 表，无需新接口）：

| event_name | 触发时机 | 关键 payload |
|---|---|---|
| `analysis_wait_started` | 发起一次分析（发 URL） | `has_case`（是否从案例卡进来） |
| `analysis_wait_completed` | analysis 到达（成功收尾） | `elapsed_ms`, `analysis_id` |
| `analysis_wait_abandoned` | 分析中切走/隐藏页面 | `reason`(hidden\|switch_session), `elapsed_ms` |
| `analysis_wait_timeout` | 前端 300s 兜底超时 | `elapsed_ms` |
| `pin_escape_shown` | 95% 卡 >90s 弹软提示 | `elapsed_sec` |
| `pin_escape_action` | 软提示点了按钮 | `action`(wait\|switch), `elapsed_sec` |

### 北极星 + 计算公式

> **北极星：案例点击 → 看到完整分析的完成率**

| 指标 | 公式 | 目标 |
|---|---|---|
| **等待完成率** | `completed / (completed + abandoned + timeout)` | 越高越好 |
| **中途跳出率** | `abandoned / started` | 较现状显著下降（先定向降 1/3） |
| **超时触达率** | `timeout / started` | 维持 <10%（基线见 `project_analysis_robustness_diag_fixed` 33%→7%） |
| **中位等待时长** | `median(elapsed_ms)`，按 completed / abandoned 分桶 | abandoned 的中位时长 ↑ = 用户更愿意多等 |
| **软提示后继续等占比** | `count(action=wait) / pin_escape_shown` | wait 占比 ↑（话术反转 + 按钮语序是否生效） |
| **案例 vs 陌生链接** | 按 `has_case` 分桶看上面所有指标 | 验证「带封面进来」是否真的提升完成率 |

### 怎么查

- `/admin/events` 页支持按 `type`(event_name) 过滤、按 `user_id` / `since_ts` 筛（见 `lib/eventsApi.listEvents`）。
- 上线后先看 `analysis_wait_started` 是否有量（确认埋点通了），再算上面公式。
- **对照口径**：部署日为界，对比改版前后（改版前没有这些事件，所以跳出率是从 0 基线建立，重点看趋势与 has_case 分桶差异）。

---

## 三、部署 checklist（交给 founder / 部署时）

- [ ] 合并 `feat/analyzing-wait-redesign` → 构建前端 → 部署 prod
- [ ] 部署后**真旅程验证**（铁律 `feedback_deploy_validation`）：真机点案例 → 确认主画面是 AnalyzingHero（非旧说明卡）→ 等到结果或超时
- [ ] 确认 `/admin/events` 收到 `analysis_wait_started`（埋点鉴权过：events POST 走 invite-code gate，内测用户都有）
- [ ] 决策记录：承诺文案「30 秒→1 分钟」已采纳（founder 2026-06-02 拍板：信任本金 > 获客冲击）
- [ ] P2-3 不排期（本文结论）；若将来 ARK 改分段再议
