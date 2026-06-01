# Phase 2 总计划（Master Plan）— 改写-发布 闭环产品化

**创建**: 2026-05-31
**作者**: PM（Alex, Opus 4.8）
**状态**: ✅ Founder 已拍板 6 项决策(2026-06-01,见 §6 + synthesis §3);P0-a 工程债可立即开工
**性质**: 把四份 Phase 2 设计产出（架构 / 改写质量 / 闭环 UX / 用户访谈）编排为**可执行、带 Gate、带 owner、带回退点**的单一权威路线图。所有现状断言均已对真实代码 Read/Grep 核验（行号引用见正文）。

**权威基线（继承，不重写）**:
- 阶段门 + Gate: [`../PHASED_PLAN.md`](../PHASED_PLAN.md)（§5 = Phase2 官方定义；§5.3 = Phase2 Gate；§7 = H1-H8 假设）
- Phase 1 复盘 + 8 铁律 + 交接: [`phase1_retro_handoff_2026-05-31.md`](phase1_retro_handoff_2026-05-31.md)
- 视觉规范: [`warm_tech_design_system_2026-05-31.md`](warm_tech_design_system_2026-05-31.md)（SoT = `frontend/src/index.css`）

**Phase 2 设计四件套（本计划编排对象）**:
- 架构: [`architecture_phase1_phase2_design_2026-05-31.md`](architecture_phase1_phase2_design_2026-05-31.md)（CreationRun 聚合根 + C1-C4 handoff 契约 + JobProgress 投影 + M0-M5 迁移顺序）
- 改写质量: [`rewrite_quality_standard_2026-05-31.md`](rewrite_quality_standard_2026-05-31.md)（五维 rubric + 9 硬检查 + 批次解封门 + 解封 checklist）
- 闭环 UX: [`phase2_loop_ux_design_2026-05-31.md`](phase2_loop_ux_design_2026-05-31.md)（单结果页四幕渐进披露 + 失败矩阵 + S0-S5 实现顺序）
- 用户访谈: [`phase2_user_interview_guide_2026-05-31.md`](phase2_user_interview_guide_2026-05-31.md)（并行验证轨 + interview_logged/consent_accepted 落 events 表）

---

## 0. TL;DR（给 Founder 的一段话）

Phase 2 的主线由 founder 本次定调为 **「改写-发布 闭环」**：端到端 **爆点分析 → 改写 → 生成 → 发布**。这与 `PHASED_PLAN.md` §5 的官方 Phase 2「30 人 Beta 产品化」**本质对齐但有侧重差异**——官方 §5.1 把 11 项必做按工程能力排序（视频链路 P2-1 居首），founder 定调把**改写解封作为第一张多米诺**（恢复 §4.1 原 Phase 1 完整闭环，而非新方向）。本计划取两者交集：**先解封改写（恢复闭环价值），再补生成草稿图与发布收尾，最后接视频（P2-1）**，每一步独立可发可测、过 Gate 才进下一步。

三件 P0（founder 点 5 已明确纳入 Phase 2）：① **解封改写**（必须先过质量 agent 的解封门，不是直接翻开关）；② **正式修 DB 路径**（cascade.db 已修，但发现第二个库 canvas.db 仍是巧合正确，慢生成队列全在此库——隐患未收口）；③ **prod 凭证轮换**（4 项待轮换，列为上线 Gate 项）。

用户访谈轨（INTV 指南）与建设轨**并行**（founder 点 1），为 Phase 1 Gate 收口与 H3 改写质量验收提供真实用户证据。

---

## 1. 定位锚定：founder 定调 vs PHASED_PLAN §5 官方 Phase 2

### 1.1 founder 本次定调（主线）

> **Phase 2 = 改写-发布 闭环。端到端：爆点分析 → 改写 → 生成 → 发布。**

这**不是新方向**，而是**恢复** `PHASED_PLAN.md` §4.1 定义的原 Phase 1 唯一闭环：
`粘 URL → 看懂为什么火 → 选赛道 → 改写脚本 → 3-5 草稿图 → 复用锚点 → 导出发布包`。
当前线上只跑到「看懂为什么火」（分析单环），改写后半段被 `REWRITE_ENABLED=false`（`frontend/src/App.tsx:157`，已核验）+ 后端 `CASCADE_REWRITE_UPSTREAM` 默认 `fixture`（`backend/src/agent/cascade/rewrite.py:70`，已核验）双重暂挂。

### 1.2 与官方 PHASED_PLAN §5 的对齐 / 差异

| 维度 | PHASED_PLAN §5 官方 | founder 本次定调 | 本计划处置 |
|---|---|---|---|
| 主线 | 30 人 Beta 产品化（能稳定支撑 30 人重复用并收费） | 改写-发布闭环（端到端） | **两者交集**：闭环是 Beta 能留存的前提；先闭环再规模 |
| 第一优先 | P2-1 完整视频生成链路（Kling+Seedance） | 改写解封（恢复闭环第一张多米诺） | **采纳 founder**：改写解封为 P0；视频 P2-1 降到 P3（闭环跑通后） |
| 生成范围 | P2-1 单镜头视频（不做 60s 合成） | 先 image-grounded 草稿图 | **先草稿图（P1）**，视频 P2-1 留扩展位（同一状态机） |
| 发布 | （§4.1 闭环终点，§5 未单列） | 发布 leg 收尾 | **P2** 复用 `buildPublishPack`，堵三个洞 |
| 配额付费 | P2-5 freemium ¥0 / Pro ¥39 | （未单提，依赖成本核算） | **P2-P3** 随生成 leg 落地 cost_guard 后接 |
| 埋点 | P2-10 25 事件 | （隐含，Gate 需证据） | **贯穿全程**，每幕点亮=漏斗节点 |
| Beta 招募 | P2-11 30 人 | （并行访谈轨先行） | 访谈轨先验需求，再扩 Beta |
| 视频/锚点三视图/topics/TTS/字幕/BGM | P2-1/2/3/6/7/8/9 | 未提 | **延后**到闭环过内部 gate 后，按 INTV 真实需求排（§5.2 仍不做清单不变） |

**差异结论**：founder 定调把**「先证闭环价值」**置于**「先堆 Beta 产品化功能」**之前——这与 `PHASED_PLAN.md` §4.4 / §7 的证据驱动原则一致（H3「改写质量足以让用户继续」在改写暂挂期无法验证）。本计划据此把 build order 排成 **改写解封（P0）→ 草稿图（P1）→ 发布收尾（P2）→ 视频/配额付费/埋点收口（P3）**。

### 1.3 绝不重做的事（防下游踩坑，retro §2.2 已点名）

- ❌ 不要把结果页改成「抓人/留人/带人」三幕 act-nav，不要做 3+1 维度精简——那是 W4 提案，已被 2026-05-30 toprador 对齐**反转覆盖**。现行 = **toprador 全量维度 + 三级视觉层级 + 脚本抽屉**（CardStack 顺序已稳定）。
- ❌ 不要在 `contract/revision.py` bump revision——**该路径不存在**。真实常量在 `backend/src/agent/cascade/contract.py:28`（`ANALYSIS_PIPELINE_REVISION = 3`，已核验）。
- ❌ 不要据「暖橙=宝妈」做 niche 假设——niche 已于 `929cb21` 清理，定位收窄为「任意短视频/抖音」。
- ❌ 不要引 framer-motion / 迁 SSE / 换 websockets / 为 30 人引 Redis/Postgres（三份 review 一致结论）。

---

## 2. Build Order（每步独立可发可测，带验收）

每个 step 对齐架构文档的 M 阶段（迁移顺序）与 UX 文档的 S 阶段（实现顺序）。**每步独立可发布、独立可验收、过验收才进下一步。**

### P0 — 还债 + 解封改写（恢复闭环价值）

**P0 包含三条并行子轨，全部是 founder 点 5 明确纳入 Phase 2 的项：**

#### P0-a 还工程债（架构 M0，解封前置）
对齐架构 M0。这些是「不修则解封即翻车 / 慢生成即裸奔」的前置债：
| 项 | 修法 | 验收 |
|---|---|---|
| **DB 路径第二库 canvas.db 未收口** | `backend/src/agent/tools/canvas_persistence/db.py:17` 用 `parent`×5 无容器检测（已核验，当前巧合正确，慢生成队列全在此库）。抽 `resolve_data_dir` 复用 cascade.db 的 `Path("/app/src").exists()` 检测，容器内路径不变=零迁移 | 容器内 canvas.db 解析到 `/app/data` 卷；本地解析到 repo/backend/data；重启后队列不丢（真容器验证，铁律⑤） |
| **工具级失败漏标 lifecycle** | cascade.py 4 处 HardFailure 只推 `analysis_failed` 帧、不调 `run_state.mark_failed`，run_agent 反而 mark_done（已核验）。在 `_push_failure_frame` 补 `mark_failed` | 工具失败后 `run_lifecycle` 记 failed；重连 replay 能拿到 failure + recovery_path_id |
| **成本遥测失真** | `http_router.py:217` analysis cost 事件硬编码 `provider='fixture'`（已核验）。改为真实上游名（doubao_direct） | events 表 GENERATION_COST 归因正确，成本 dashboard 不误判 |
| **改写缓存无版本守卫** | 新增 `REWRITE_PIPELINE_REVISION`（铁律①的 `ANALYSIS_PIPELINE_REVISION` 只守 analysis 永久缓存，对 rewrites 24h 缓存**完全无效**——已核验）。rewrites_repo 缓存键加该列 | 切 llm 后旧 fixture 结果不再被 24h 缓存命中 |

#### P0-b 解封改写（架构 M1+M2，过质量 agent 标准 gate）
**解封 = 三件事联动，漏一处=假解封**（已核验三处状态）：
1. 后端 `.env` / docker-compose 加 `CASCADE_REWRITE_UPSTREAM=llm`（当前所有部署文件都没设，默认 fixture）；
2. 前端 `frontend/src/App.tsx:157` `REWRITE_ENABLED=false → true` 并**重建部署**（当前是源码硬常量，非运行时开关——**建议顺手改成 env/远程 flag** 便于灰度，见 ❓5）；
3. **bump `ANALYSIS_PIPELINE_REVISION`**（铁律①，`contract.py:28`，现=3→4）。

**但翻开关前必须先过改写质量 agent 的解封门**（见 §4.1 P0 内部 Gate），即 `rewrite_quality_standard_2026-05-31.md` 定义的：
- G0 eval 框架改造（补后端 hook-code 泄漏检查、放开 niche 强制项）+ rewrite 缓存守卫先落地（P0-a 已含）；
- 批次解封门：机械通过率≥85% / judge realism≥3.8 / kept_formula=yes≥70% / ad_risk=0 / 人工 signoff≥70% / **且 --mode llm 显著优于 --mode fixture**；
- 真 URL + doubao 实跑验收（铁律⑤）。

#### P0-c prod 凭证轮换（上线 Gate 项，founder 点 2）
4 项待轮换（memory `reference_prod_server` + architecture_review §Follow-ups）：① SSH 私钥（`~/.ssh/cascade_prod`）；② root 口令；③ Cloudflare API token（cloudflared.service）；④ `CASCADE_ADMIN_TOKEN`（曾出现在 transcript）。**列为 Phase 2 任意上线动作前的硬 Gate 核实项。**

**P0 整体验收（可发布判据）**: 改写解封后真 URL 端到端跑通「分析→自动改写→你的版本卡」；rubric 抽检≥70；零禁词漏到 UI；DB 重启不丢队列；4 项凭证确认已轮换。

---

### P1 — 生成 leg（先 image-grounded 草稿图）

对齐架构 M3 + UX S2。**先草稿图，不做视频**（视频是 P3 的 P2-1）。
| 项 | 内容 | 关键约束 |
|---|---|---|
| C3 镜头桥接（**P2 必新建**） | `build_shot_prompts`：分析/改写 → canvas image-node。镜头 prompt 主用改写 `rewriteShots[].visual`，回退 `analysis.scenes[].visual_content` | 依赖 P0-b 改写解封（无改写则回退源片描述，语义弱） |
| 生成 cost_guard（**硬 Gate**） | 现 `cost_guard.py` 只覆盖分析侧 token（已核验，PREDICT_* 全是分析/transcribe/ask，**无 image/video**）。enqueue 前置 cost_guard + 按张/按秒预测 + retry×3 重复扣费防护 | 生成 leg 当前零成本护栏，30 人 Beta 会真金白银裸奔 |
| 草稿图四态状态机 | UX S2：IDLE/PENDING/POLLING/DONE/FAILED 卡级状态机；reconnect 从 JobProgress 投影重建（防卡95%同构）；单镜失败降级到文字不连累全卡；只出 3-5 关键镜头控成本 | 复用 W5D4 P0-B run_lifecycle + P0-C pendingByThread（不可删） |
| provider 合规 | 默认 `IMAGE_GEN_PROVIDER=google`（Gemini 跨境，已核验默认值漂移）——**阻塞项**，见 ❓1 | 铁律⑦：改写已隔离境内，生成图不能裸奔 |

**P1 验收**: 真 URL 端到端出 3-5 张 image-grounded 草稿图；断线重连进度从权威态重建不丢；cost_guard 在 enqueue 前生效（超额拒绝有 banner）；provider 合规决策已落地。

---

### P2 — 发布 leg 收尾（拿去发）

对齐架构 M4 + UX S3。复用 `frontend/src/lib/buildPublishPack.ts`（纯函数 + 7 单测已绿），堵三个洞：
| 洞 | 现状（已核验） | 修法 |
|---|---|---|
| 镜头图空壳 | `PublishPackCard` 恒传空 `shotImages` → 发布包永远「镜头 1: 待补充」 | 接 P1 生成草稿图 S3 url；缺图优雅降级（best-effort，clip 范式） |
| niche 硬编码 | `buildPublishPack.ts` 仍硬编码辅食/育儿/厨房标签 + tagline，但 `929cb21` 已砍 niche，运行时 niche 恒 null → 默认套辅食标签 | 标签从分析 `theme`/`target_audience` 经 scrub 后生成 + 用户可编辑 |
| 标题辅食兜底 | `buildPublishPack.ts:80-81` 硬回退辅食句 | 去 niche 化通用空态 |
| **禁词漏到剪贴板** | `buildPublishPack` 只 `stripHookCode`，不 `scrubUiForbidden`（已核验） | 复制前对拼入 script/标题跑 `scrubUiForbidden` |

UX：整段复制 + 分字段复制（抖音发布表单是分字段的）；PublishPackCard 接回 CardStack（当前不渲染=死代码）。

**P2 验收**: 发布包含真镜头图（缺图降级不塞坏链）；零 niche 残留；零禁词漏到剪贴板；分字段复制可用；`publish_pack_copied` 事件落 events 表。

---

### P3 — 视频（P2-1）+ 配额付费（P2-5）+ 埋点收口（P2-10）

闭环跑通且过内部 gate 后启动。视频复用 P1 同一任务无关四态状态机（留扩展位）；配额付费随生成 cost_guard 落地后接 freemium/Pro；25 事件埋点贯穿全程，P3 收口对齐 P2-10。**视频/TTS/字幕/BGM/topics 雷达按 INTV 真实需求排序**（§5.2 仍不做清单不变）。

---

### 并行轨 — 用户访谈（INTV 指南，与建设轨并行，founder 点 1）

按 `phase2_user_interview_guide_2026-05-31.md` 运行：从现有邀请码 cohort 招 12 人（命中 ≥10试用/≥5完成/≥3回访）；7 阶段情境法；结论 emit `interview_logged`/`consent_accepted` 落同一 events 表（已核验 `events.py:40-41` 现成支持）。**回灌「足够好的改写」用户语言词表 + 弃稿点**给改写质量 agent 作验收输入。

---

## 3. 首个 Cycle 的 4-owner 分配表（铁律：每 cycle 不漏 owner）

**Cycle 1 = P0 还债 + 解封改写前置 + 访谈轨启动**。founder 2026-05-24 后 decision-only。

| Owner | 本 cycle 任务 | 对应 step | 交付/验收 | flag |
|---|---|---|---|---|
| **Claude** | ① canvas.db 路径收口（抽 `resolve_data_dir`，零迁移）② cascade.py 4 处 `_push_failure_frame` 补 `mark_failed` ③ http_router cost 遥测改真实 provider | P0-a | 真容器验证重启不丢队列（铁律⑤）；run_lifecycle 失败态正确 | — |
| **Cursor** | 前端：① `REWRITE_ENABLED` 改 env/远程 flag 化（为灰度铺路，见 ❓5）② RewriteCard + RewritePending 在途态接回 CardStack（rewrite_returned 帧已在 `wsStore.ts:334` wired，只需渲染）③ 跑 `npm run lint`(rules-of-hooks)+ Playwright | P0-b 前端侧 | lint 0 违规 + 真浏览器旅程（铁律②）；新 .anim-* 进 reduced-motion 名单（铁律⑧） | 依赖架构 M1 守卫先落地，否则首批看旧 fixture |
| **Codex** | 后端：① 新增 `REWRITE_PIPELINE_REVISION` + rewrites_repo 缓存键加列 ② rewrite cost 定价从 Gemini Flash 改 doubao（`rewrite.py:422`）③ eval 框架 G0 改造（补后端 hook-code 泄漏检查 + 放开 niche 强制项） | P0-a + P0-b 后端侧 + 质量 G0 | 切 llm 后旧 fixture 不命中缓存；eval 通用路径可跑 | — |
| **Founder** | **5 项 decision**（见 §6 ❓1-❓5）+ 主持改写解封质量门拍板（rubric 阈值 + 评测集 URL + 灰度策略）+ 确认 prod 4 项凭证轮换状态 | P0-b gate + P0-c | 阈值文件 signoff；凭证轮换确认；访谈轨 ≥15 真 URL 评测集就位 | **延误风险**：质量门拍板若延，P0-b 翻开关阻塞 → 建议本 cycle 内先给阈值，URL 集可滚动补 |

**主动 flag 的延误风险**：
- 改写翻开关（P0-b 联动三件事）**强依赖** Founder 质量门拍板 + Codex 缓存守卫先落地。任一未就位则改写解封阻塞——本 cycle 先把守卫 + eval 改造（Claude/Codex）跑完，Founder 拍阈值，**翻开关动作放到守卫验证通过后**，避免假解封。
- 生成图 provider 合规（❓1）阻塞 P1 开工——本 cycle 请 Founder 同步决策，不要等到 P1 才提。

---

## 4. Gate（对齐 PHASED_PLAN §5.3 + P0 内部门）

### 4.1 P0 内部 Gate — 改写解封质量门（新增，本计划定义）

翻 `REWRITE_ENABLED=true` 前必须全过（出处 `rewrite_quality_standard_2026-05-31.md`）：

| 指标 | 通过线 |
|---|---:|
| 机械硬检查通过率（9 条，N≥15 真 URL） | ≥ 85% |
| LLM judge realism（境内 doubao judge，禁 gemini） | ≥ 3.8 / 5 |
| kept_formula=yes（套路保真） | ≥ 70% |
| ad_risk（广告法/品牌禁词） | = 0 |
| 人工 signoff | ≥ 70% |
| llm 模式 vs fixture 模式 | **显著优于**（否则解封无意义） |
| rewrite 缓存版本守卫已落地 | 是（P0-a） |

不通过 → 不翻开关，回 prompt/阈值调优。

### 4.2 Phase 2 官方 Gate（PHASED_PLAN §5.3，进入 Phase 3 条件）

| 指标 | 通过线 |
|---|---:|
| 30 人 Beta 注册 | ≥ 30 |
| Day 1 完成首条 | ≥ 40% |
| 14 天留存 | ≥ 25% |
| 7 天人均创作 | ≥ 3 条 |
| 单条 60s 完整成片成本 | < ¥15 |
| 锚点跨 run 复用率 | ≥ 60% Beta 用户 |
| 至少 5 人付 ¥39/月 | ≥ 5 |

不通过 → 不扩规模，回产品深度优化（§7 H1-H8）。

### 4.3 Phase 1 Gate 收口（并行陪跑，retro §5 未闭合债）

8 项用户侧指标（≥10 试用/≥5 完成/≥3 回访/≥2 一句话价值/单条<¥15/转化≥15%/失败有下一步 100%/≥2 沉淀锚点）由 INTV 轨陪跑收口。**口径偏差（❓4）**：改写未上线前，「完成首条」只能验证分析单环；解封改写后才能验证完整闭环。

---

## 5. 风险登记册 + 依赖顺序 + 回退点

### 5.1 风险登记册

| # | 风险 | 概率 | 影响 | 缓解 | 回退点 |
|---|---|---|---|---|---|
| R1 | 改写解封漏开关之一 → 表面解封仍套娃 | 中 | 高 | 三件事 checklist 钉死（§2 P0-b）；缓存守卫先行 | 翻回 `REWRITE_ENABLED=false`（前端常量/flag 一行） |
| R2 | doubao 真输出常触发 scrub/超长 → confidence≤0.4 大面积 | 中 | 中 | 解封前真跑标定阈值；低把握给可操作话术 | 调 prompt 长度/阈值；不解封 |
| R3 | 生成 leg 零成本护栏 + retry×3 + Google 重启重入队 → 重复扣费 | 高 | 高 | P1 enqueue 前置 cost_guard 定为硬 Gate | 关 execute_node 触发；降并发 Semaphore |
| R4 | canvas.db 落 ephemeral → 重启丢慢生成队列 | 中 | 高 | P0-a 收口 resolve_data_dir | CASCADE_DB_PATH env 临时兜底 |
| R5 | 生成图默认 Gemini 跨境违反 PIPL §38 | — | 高（合规） | ❓1 founder 拍板：默认切境内 Apimart 或加同意条款 | 默认 IMAGE_GEN_PROVIDER=apimart |
| R6 | 慢生成时长超 run_lifecycle 210s stale 阈值 → 误判 | 中 | 中 | JobProgress 投影独立生命周期（架构 M3） | worker 帧靠 canvas_updated 自愈 |
| R7 | 单事件循环 + 3 worker task：慢生成多 → 反压 send_to_user | 中 | 中 | worker 并发参数 env 化 + backpressure 观测 | 降 Semaphore；不拆进程（review 反对） |
| R8 | SQLite 锁竞争触 Postgres 阈值（30 人正踩线） | 低 | 中 | Beta 期观测锁竞争>1/1000 或 p95>150ms 才议迁 | 证据驱动，不预先迁 |
| R9 | prod 4 项凭证未轮换上线 | — | 高（安全） | P0-c 列为上线硬 Gate（❓2） | 阻断上线直到确认 |
| R10 | 改 prompt/维度/模型漏 bump revision → 旧缓存永久挡新维度 | 中 | 高 | 铁律①；改写侧用 REWRITE_PIPELINE_REVISION | 手动清缓存或换 user_id |
| R11 | 下游按 W4 三幕/3+1 改 UI（已被反转） | 中 | 中 | §1.3 + retro §2.2 红字警告 | 回退到 toprador 全量维度+三级层级 |
| R12 | 短链 v.douyin.com 302 不跟随 → 移动端隐形流失 | 中 | 中 | 架构 M5 补 302 跟随 | — |

### 5.2 依赖顺序（DAG）

```
P0-a（还债：canvas.db / mark_failed / cost遥测 / REWRITE守卫）
  └─> P0-b（改写解封：守卫先落地 → 质量门 → 三开关联动 + bump revision）
        ├─> P1（生成草稿图：C3 桥接依赖改写 shots[].visual；cost_guard 依赖 P0-a 真实 cost）
        │     └─> P2（发布收尾：标题/脚本来源=改写；镜头图=P1 S3 url）
        │           └─> P3（视频 P2-1 / 配额付费 P2-5 / 埋点收口 P2-10）
        └─ 并行：INTV 访谈轨（回灌改写验收词表）
P0-c（prod 凭证轮换）═══> 任意上线动作前的硬 Gate（横切所有 step）
❓1 provider 合规决策 ═══> 阻塞 P1 开工
```

关键依赖（架构文档确认）：
- M2 改写解封依赖 M1 `REWRITE_PIPELINE_REVISION` 守卫先落地（否则首批用户看旧 fixture 套娃）。
- M3 生成桥接（C3）依赖 M2 改写解封（无改写回退 `analysis.scenes[].visual_content`）。
- M3 cost_guard 依赖 M0 修复成本遥测（用真实 cost 而非预测累加）。
- M4 发布依赖 M2（标题/脚本数据源）+ M3（镜头图 S3 url）。
- 所有前端步骤依赖铁律②（rules-of-hooks lint + Playwright）+ 铁律⑧（reduced-motion 名单）。

### 5.3 回退点原则

每个 step 独立可发布 = 每个 step 有独立回退：改写一行 flag 翻回；生成关 execute_node 触发 + 降并发；发布卡不渲染（回到当前死代码态）；视频留扩展位灰置。**best-effort（装饰层）失败降级，硬阻断（核心价值缺失/花钱前）必给 banner**——以 clip 范式划界（架构失败矩阵）。

### 5.4 8 铁律 honor 对照

| # | 铁律 | 本计划落点 |
|---|---|---|
| ① | 改 prompt/维度/模型 bump `ANALYSIS_PIPELINE_REVISION`（=3，`contract.py:28`） | P0-b 解封 bump 3→4；改写侧另加 `REWRITE_PIPELINE_REVISION`（铁律①对 rewrites 缓存无效，已核验） |
| ② | 改 UI 跑 lint + 真浏览器 | Cursor 每 step 跑；Playwright 真旅程 |
| ③ | 批量删会话用原子 delete_sessions | 不动会话路径，继承现状 |
| ④ | 实时通讯永不发启动捕获的 ws | 慢生成复用 send_to_user 实时注册表（已落地，不破坏） |
| ⑤ | 容器健康≠功能可用，真 URL 验证 | 每 step 验收=真 URL doubao 实跑 |
| ⑥ | 改 mirror/依赖重 lock | 若动依赖（如 cost 库）重 lock |
| ⑦ | doubao 境内合规，禁 gemini 跑改写，全名带后缀 | 改写已境内；生成图 provider 待 ❓1 拍板 |
| ⑧ | 不引 framer-motion，新动效进 reduced-motion 名单 | 复用 index.css keyframe 层 |

---

## 6. 开放问题（Founder 已于 2026-06-01 拍板）

> **以下决策为准,后续不再问。** 决策摘要见 [`phase2_kickoff_synthesis_2026-05-31.md`](phase2_kickoff_synthesis_2026-05-31.md) §3。

| # | 拍板 | 落地动作 |
|---|------|---------|
| ❓1 → **D1** | **双轨:境内 Apimart 默认 + 跨境 Gemini 可选** | `config.py:27` 默认切 apimart;Gemini 降为显式可选(带跨境同意条款),可选轨工程量大排 P1 后段/P3 |
| ❓2 → **D-凭证** | 4 项凭证轮换 = 上线硬 Gate(P0-c),上线前核实 | 不变 |
| ❓3+❓5 → **D2** | **先 rewrite-beta cohort 灰度一周,达标再全量** | `REWRITE_ENABLED` 本 cycle 改成按 cohort 运行时 flag(P0-b 必含) |
| ❓4 → **D4** | **不硬卡,能力建设 + 陪跑并行**;接受改写未上线期访谈只验分析单环 | 解封后再正式收口完整闭环 Gate |
| ❓6 → **D5** | **长度上限 80–220 字** | 同步改 4 处:`rewrite_*.md:24` + `checks.py:41` + `rewrite.py:215-218` fixture 兜底 + brief |
| 新 → **D3** | **去 niche:单一通用代笔 prompt + 用户填一句话主题** | 合并三套 niche prompt;第②幕加主题输入框;eval 去 per-niche;bump REWRITE_PIPELINE_REVISION |
| 新 → **D6** | **质量达标 = Founder 人工锚点(标 3-5 条「我会发的口吻」)+ rubric 辅助** | P0-b 解封门的人类输入,需 founder ~20min;先跑出真 URL 样例供标注 |

**历史待决项原文(留痕)**:

| # | 问题 | 阻塞 |
|---|---|---|
| ❓1 | 生成图默认 `IMAGE_GEN_PROVIDER=google`（Gemini 跨境，PIPL §38）：30 人 Beta 真实用户数据，默认切境内 Apimart，还是明确接受跨境+加同意条款？ | 阻塞 P1 开工（ShotPrompt provider 默认值） |
| ❓2 | prod 4 项凭证（SSH 私钥/root 口令/CF token/CASCADE_ADMIN_TOKEN）是否已轮换完成？建议作为 Phase 2 上线硬 Gate 核实。 | 阻塞任意上线动作 |
| ❓3 | 改写解封质量验收基线由谁拍板阈值？先 cohort 灰度（部分邀请码可见）还是达标全量？ | 阻塞 P0-b 翻开关 |
| ❓4 | Phase 1 Gate 用户侧 8 指标未量化达成——是否硬卡 Phase 2 启动，还是能力建设+陪跑并行？（现实是并行）改写未上线时「完成首条」只能验证分析单环，这道口径偏差是否接受？ | 影响 Gate 收口口径 |
| ❓5 | `REWRITE_ENABLED` 改为 env/远程 flag 化（当前是 `App.tsx:157` 源码硬常量）以支持灰度——是否本 cycle 一并做？ | 影响灰度策略可行性 |
| ❓6 | 改写长度上限到底 220/400/600？brief、prompt（rewrite_*.md:24=400）、硬检查（checks.py:41=600）三处不一致，拍板后须同步改三处。 | 阻塞改写 eval 通过线 |
| ❓7 | freemium ¥0 / Pro ¥39 具体免费额度数字（待成本核算）。 | 阻塞 P3 配额付费 |

---

*本文为 Phase 2 总计划（master plan），编排四份设计产出为带 Gate/owner/回退点的路线图。所有现状断言经 Read/Grep/Bash 对真实代码核验。继承 `phase1_retro_handoff_2026-05-31.md` 的 8 铁律 + 视觉规范 + 结果页结构基线，不重写。*
