# Phase 1(6 周验证版 / 内测)复盘 & Phase 2 交接基线

**创建**: 2026-05-31
**负责**: PM(复盘 + 交接,Opus 4.8)
**状态**: 权威交接文档 —— 后续 phase 的实现以本文 §3(铁律)/ §4(视觉)/ §6(继承)为继承基线
**关联(均为真实存在文件)**:
- 阶段计划:[../PHASED_PLAN.md](../PHASED_PLAN.md)(四阶段 + Gate,2026-05-19 v1)
- 视觉规范:[warm_tech_design_system_2026-05-31.md](warm_tech_design_system_2026-05-31.md)(代码侧 SoT = `frontend/src/index.css`)
- 产品重设计:[product_redesign_breakdown_ux_2026-05-29.md](product_redesign_breakdown_ux_2026-05-29.md)
- 结果页 UX/动效:[analysis_page_ux_redesign_2026-05-31.md](analysis_page_ux_redesign_2026-05-31.md)
- 落地/入口 PM 评审:[landing_entry_pm_review_2026-05-31.md](landing_entry_pm_review_2026-05-31.md)
- 通讯加固复盘:[architecture_comms_review_2026-05-29.md](architecture_comms_review_2026-05-29.md)

> ⚠️ 注:本文如提到 `design_tokens_visual_spec.md` / `cascade_phasing_plan.md` / `toprador_alignment_design_*.md`——这些文件**不存在**。真实对应物见上方关联清单。

---

## 0. TL;DR(给 Founder 的一段话)

Phase 1(`PHASED_PLAN.md` 定义的「6 周验证版 / 火箭发动机」,内部称内测)在 2026-05-24 战略 pivot 后,用约一周(从 pivot 到 HEAD `929cb21`)把产品从「按分析师解剖学组织、改写从没接模型」校正成「按创作者决策组织、对齐 toprador 金标准、暖色科技视觉、通讯稳态」。期间发生 **2 次方向反转**(分析维度、改写策略)+ **1 次稳定性大修**(卡 95%/空白屏 5 同源 bug + 通讯加固)+ **1 套视觉语言固化**(暖色科技)。

**最重要的三件事要 Phase 2 知道**:
1. **改写护城河当前被 `REWRITE_ENABLED=false` 暂挂**(代码留)。本轮产品定位收窄为「看懂为什么火」的分析工具。`PHASED_PLAN.md` 的 Phase 1 闭环本含「改写→草稿→发布包」,**改写解封是恢复完整闭环的第一张多米诺**。
2. **Phase 1 Gate 尚未量化达成**(≥10 试用 / ≥5 完成首条 / ≥3 一周内回访,见 `PHASED_PLAN.md` §4.4)。能力已就绪,缺真实用户数据收口。
3. **沉淀了 8 条工程铁律 + 1 套暖色科技视觉**,每条都对应一次真实事故/决策,Phase 2 继承,别重新踩。

---

## 1. Phase 1 定义回顾(出处:`PHASED_PLAN.md`,真实)

| 阶段 | 名称 | 目标 | Gate(进入下一阶段) |
|------|------|------|----------------------|
| Phase 0 | Schema & Contract 稳定 | 先稳上游表示 | 深分析成功率≥80% / 字段完整≥90% / 0 静默失败 |
| **Phase 1** | **6 周验证版(内测)** | **证明「热点→改写→草稿→复用→发布包」单一闭环对真实创作者有用且会重复用** | **≥10 试用 / ≥5 完成首条 / ≥3 一周内回访 / ≥2 能一句话说出价值 / 单条<¥15 / 热点→创作≥15% / 失败有下一步 100%** |
| Phase 2 | 30 人 Beta 产品化 | 稳定支撑 30 人重复用并收费 | 30 注册 / D1 完成≥40% / 14 天留存≥25% / ≥5 付费 |
| Phase 3 | 资产复利与商业化 | 扩到 300 付费 | 见 PHASED_PLAN §6.3 |

**当前判断**:Phase 1 的「能力建设」基本完成(真 URL 跑通 + 对齐金标准 + 稳定 + 视觉固化),但 **Gate 的用户侧指标未量化达成**;且因改写暂挂,验证的是「分析」单环而非完整「分析→改写→发布」闭环。**Phase 2 启动前需 founder 决策:是先收口 Phase 1 Gate(陪跑 + 改写解封 + 埋点),还是带着已就绪能力直接推 Phase 2。**(现实是能力建设与陪跑在并行。)

---

## 2. 复盘:Phase 1 实际发生了什么

### 2.1 时间线(2026-05-24 → 05-31,HEAD `929cb21`)

| 日期 | 里程碑 | 性质 |
|------|--------|------|
| 05-24 | 战略 pivot;Founder 转 decision-only | 方向 |
| 05-27~28 | W5D1-D3:doubao_direct 上游 + 维度契约 + 时长闸门 + 邀请码门 + Dockerfile/nginx/cf 隧道 + 可观测性 | 地基/部署 |
| 05-28 | Opus 4.8 架构审计 P0–P3 修复 + 国内镜像(清华/阿里)加速部署 + DB 持久化到卷 | 加固 |
| 05-29 | **稳定性大修**:卡 95%/拆解中空白/邀请码 4003 死循环——5 同源 bug + 错误边界 | 救火 |
| 05-29 | **通讯加固**:实时 ws 注册表 + 生命周期持久化 + 帧缓冲重放(commit `78bbaba`) | 架构 |
| 05-29 | **产品重设计**(`product_redesign_breakdown_ux`):诊断 6 根因 + 改写接真模型 + 三幕一屉提案 | 反转①(提案) |
| 05-30 | **反转→对齐 toprador 金标准**:爆点 10 维 + 逐幕 14 维 + doubao 升 2.0;**改写暂挂** `REWRITE_ENABLED=false` | 反转②(落定) |
| 05-30 | 分析缓存版本守卫 `ANALYSIS_PIPELINE_REVISION` + save 改 upsert(commit `4656b28`) | 铁律落地 |
| 05-31 | **结果页暖色科技重设计**:玻璃拟态 + 流光 + 数据滚动 + 重点发光(`ba7503d`/`18a444d`)→ 铺到全站(`b938bed`) | 视觉固化 |
| 05-31 | 原脚本抽屉 + 逐幕 clip 播放器 + 三级爆点卡(`3190bd5`);revision 2→3 | 体验升级 |
| 05-31 | 会话自动命名 + 清理空会话 + 批量原子删(`0e14401`/`953fef6`/`3bb46fa`) | 修复 |
| 05-31 | 入口:抖音短链/文案可解析 + 时长甜蜜点 + 真实案例预览轮播 + 撤假 ticker(`a962d95`→`929cb21`) | 体验升级 |
| 05-31 | niche 清理:删除 宝妈/育儿/家庭厨房 与「小红书」残留 | 收窄定位 |

### 2.2 两次方向反转(必须理解,否则会被重新踩)

**反转① 信息架构:20+ 卡 dump →(W4 提案)三幕一屉**
`product_redesign_breakdown`(05-29)诊断:结果页是「分析师 dump」(ConfidenceBanner + Audio/Production/Transcript + 12×ShotCard + AnchorSidebar = 20+ 块),价值(改写脚本)被埋在底部手动 CTA 后。提案改成「为什么火 3 chip / 你的版本 / 拿去发」三幕一屉。**这是提案,不是最终落地形态(被反转②部分覆盖)。**

**反转② 分析维度:11+ →(W4 提案)3+1 →(W5 落定)toprador 金标准 10+14**
W4 提案把维度精简到「抓人/留人/带人 + 套路」3+1。W5 用 toprador 做金标准对照后判定:**问题不在维度多,在结构乱/呈现差** → **反转回 toprador 全量维度**(爆点 10 维 + 逐幕 14 维 + 总结/主题),前端用**清晰网格 + 三级视觉层级**呈现,而非删维度。
**最终落地形态(以 `analysis_page_ux_redesign` 实现记录 + 代码为准)**:
- `ViralAnalysisCard` 爆点卡:**三级层级**——英雄四维(钩子/痛点需求/情绪触发/目标人群,大字+暖橙左条+绘入)→ 次级(素材利益点/主要视频元素/微创新方向)→ 辅助(BGM 风格,弱化最末)。
- `SceneAnalysisCard` 逐幕卡:14 维 + 视觉/听觉双栏 + 顶部 clip 播放器。
- `ScriptDrawer` 原视频脚本抽屉:分镜脚本 tab + 逐字稿 tab(「屉」保留下来了)。
- `AnalysisStatStrip`:镜头/时长/把握 三个关键数字玻璃卡 + 滚动计数。

> ⚠️ 给 Phase 2 的明确提示:**「三幕(抓/留/带)」是 W4 提案,已被 toprador 对齐覆盖;当前不是 act-nav 三幕,而是「toprador 维度 + 三级视觉层级 + 脚本抽屉」。** 不要按「三幕」去改 UI。

**改写策略的连带状态**:`product_redesign` P0 把改写从 fixture 接到真 doubao(境内合规);随后 toprador 对齐期 **`REWRITE_ENABLED=false` 暂挂**(代码留、关 UI),本轮定位收窄为「看懂为什么火」分析工具。**改写解封 = Phase 2 第一张多米诺(见 §6)。**

### 2.3 一次稳定性大修(架构教训)

卡 95% / 拆解中空白 / 邀请码 4003 死循环 —— **5 个同源 bug**,共同雷区:**消息/帧发往「启动时捕获的 ws / currentThreadId」**(过期闭包快照)。架构师复盘判「加固不重构」,落地(commit `78bbaba`,详见 `architecture_comms_review_2026-05-29.md`):
- run 帧走**实时注册表**,`send_to_user` 不再发死 ws;
- `run_lifecycle` 表**持久化生命周期** + boot reconcile;
- wsStore 帧**按 thread 缓冲 + 切换重放**(不再静默丢);
- 删前端 content-regex 失败误判。

---

## 3. 沉淀的工程铁律(Phase 2 必须继承,违反 = 重新踩坑)

> 每条对应一次真实事故/决策。

1. **改 prompt / 维度 / 模型 → 必须 bump `ANALYSIS_PIPELINE_REVISION`**(现为 **3**)。分析永久缓存(无 TTL),旧 schema 缓存会永久挡新维度;save 已改 upsert。
2. **改 UI → 必须 `npm run lint`(rules-of-hooks 0 违规)+ Playwright 真浏览器旅程**。jsdom 测不到「hook 在 early-return 之后」;prod 会被错误边界吞成空白页(React #310,commit `3cb8136`/`dd10c21`)。
3. **批量删会话 → 用原子 `delete_sessions` 一条命令**。否则删到一半的 `session_list` union 把已删的加回来。历史列表 = localStorage ∪ backend,删除要双删。
4. **实时通讯 → 永不发往「启动时捕获的 ws / currentThreadId」**。run 帧走实时注册表;生命周期走持久化表 + boot reconcile;前端帧按 thread 缓冲 + 切换重放。
5. **「容器健康 ≠ 功能可用」**。声称「上线」前必须真浏览器 + 真 URL 跑完整旅程。
6. **改 mirror / 依赖 URL → 必须重新 lock**(`uv sync --frozen` 忽略 env/CLI,URL 硬编码在 lock,用 `[[tool.uv.index]]` 重锁)。
7. **doubao 保持境内合规 provider(PIPL §38 红线,禁止 gemini 跑改写)**;模型用全名带日期后缀(`doubao-seed-2-0-pro-260215`,无后缀 ARK 返 404)。
8. **不引 framer-motion**;动效复用 `index.css` keyframe 层 + `useInView`/`useCountUp`,**新动效必须追加进 `prefers-reduced-motion` 名单**(`index.css` ~571 行)。

---

## 4. 视觉风格固化(本次复盘重点)

Phase 1 末把视觉收敛成 **「暖色科技(warm-tech)」** 一套自洽语言。完整规范见 **[warm_tech_design_system_2026-05-31.md](warm_tech_design_system_2026-05-31.md)**(已同步扩充为权威规范);代码侧 SoT = `frontend/src/index.css`(Tailwind v4 `@theme` + ~40 keyframes + `@layer components` utilities)。

**一句话定位(产品级)**:把别人的爆款讲清楚「为什么火」,让普通创作者一眼 GET、想动手——工具要有专业感 + 活感 + 数据感,但**高级克制**。

**已固化的视觉支柱(Phase 2 继承,不要另起炉灶)**:

| 支柱 | 规则 |
|------|------|
| 技术栈 | **Tailwind v4** `@import "tailwindcss"` + `@theme` 令牌;深色用 `@custom-variant dark`(`html.dark`) |
| 基调 | **暖纸基底(light-first)** `--color-paper #faf8f3` + 暖墨字 `--color-ink #1c1917`;**深色变体**(`html.dark` → `#0c0a09`) |
| 品牌 | **陶土暖橙 → 落日橘**:`--color-clay #7c2d12` / `--color-clay-soft #c2410c` / `#ea580c` / 金 `#f59e0b`;暖不冷 |
| 暖色科技层 | `.glass`(玻璃拟态)· `.tech-topline`(顶部流光描边 `hueFlow`)· `.tech-grid`(暖色网格)· `.glow-warm`/`.hover-glow`(暖光晕)· `.num-tech`(等宽数据字)· `.text-shimmer-clay`(流光渐变文字) |
| 入场/强调动效 | `.anim-tech-in`(科技揭示)· `.anim-sheen`(光扫)· `.anim-glow-pulse`(一次性发光脉冲,吸睛)· `.anim-draw-line-y`(左条绘入)· stagger 用 inline `animationDelay` |
| 数据感 | 关键数字用 `.num-tech` + `useCountUp` 滚动(reduced/无 IO 时直接终值,测试&可访问性安全) |
| 结果页 | `AnalysisStatStrip`(镜头/时长/把握玻璃卡)+ `ViralAnalysisCard`(三级层级)+ `SceneAnalysisCard`(逐幕+clip)+ `ScriptDrawer`(脚本抽屉) |
| 入口 | 时长**甜蜜点** chip(`.anim-sweet-band`/`.anim-sweet-ripple` 呼吸+涟漪)+ CTA 呼吸/光晕(`.anim-cta-breathe`/`.anim-cta-glow`)+ 真实案例预览轮播 |
| 性能 | **glass/blur 只用在少量重点卡**;长列表(逐幕可能 12 张)用实色卡避免 backdrop-blur 开销 |

**视觉铁律**:① 新组件优先复用 index.css 既有 token/utility;② 暖橙做品牌主调,不要引冷色霓虹;③ 动效服务「引导注意 / 数据感」,**高级克制不晃眼**,只在关键维度/数字处强调;④ **任何新 `.anim-*` 必须进 reduced-motion 名单**;⑤ 玻璃/blur 节制使用,长列表用实色。

> 注:`warm_tech_design_system` 旧文有「贴合宝妈/育儿」字样——**该 niche 已于 `929cb21` 清理,定位收窄为「任意短视频/抖音」**;暖橙保留为品牌色,但「暖=贴合宝妈」的理由已过时,Phase 2 勿据此做 niche 假设。

---

## 5. 技术债 / 已知风险(带入 Phase 2)

| 项 | 现状 | 风险 | 处置建议 |
|----|------|------|---------|
| **改写暂挂** | `REWRITE_ENABLED=false`,代码留,已接 doubao | 完整闭环(分析→改写→发布)未对用户开放 | Phase 2 P0,质量验收后解封 |
| **DB 路径 off-by-one** | `persistence/db.py` 解析到易失层,靠 `CASCADE_DB_PATH` env 兜底 | 配置漂移会丢数据 | 正式修解析逻辑,别长期靠 env |
| **prod 凭证泄露** | 见 memory `reference_prod_server` | 安全 | 尽快轮换 |
| **clip best-effort** | doubao_direct ffmpeg `-c copy`,失败跳过该幕不阻断 | 部分 clip 可能缺失 | 监控生成成功率 |
| **入口短链 P1** | `v.douyin.com` 302 跟随为「必做未完」(见 landing PM 评审 §5) | 手机 App 链接当场不可用 = 移动端最大隐形流失 | Phase 2 早期补 |
| **Phase 1 Gate 数据** | 用户侧指标未量化 | 阶段门未闭合 | 陪跑 + 埋点收口 |

---

## 6. Phase 2 输入与继承

**Phase 2 目标(`PHASED_PLAN.md` §5)**:从「能跑通」到「稳定支撑 30 人重复用并收费」;含完整视频生成链路、单 Tab `/topics`、配额+基础付费(freemium/¥39 Pro)、25 事件埋点、30 人 Beta 招募。Gate:30 注册 / D1 完成≥40% / 14 天留存≥25% / ≥5 付费。

**第一张多米诺 —— 改写解封(恢复完整闭环)**:
1. 定改写质量验收标准(对照源片套路是否保留、是否像创作者口吻、是否全境内合规);
2. 真 URL 端到端跑改写,人工 + 自动评估;
3. 达标后 `REWRITE_ENABLED=true`,**bump `ANALYSIS_PIPELINE_REVISION`(铁律①)**;
4. 前端把改写产物 + 发布包接回结果页(W4 提案的「你的版本 / 拿去发」可复用,但呈现走暖色科技 + 当前卡结构)。

**继承基线(不要推翻)**:
- 视觉 = §4 + `warm_tech_design_system_2026-05-31.md`
- 工程铁律 = §3(8 条)
- 结果页结构 = toprador 维度 + 三级层级 + 脚本抽屉(**非**抓/留/带三幕)
- 鉴权 = 两层 invite-code + admin-token(见 memory `http_auth_model`)
- 上游分析 = doubao_direct + toprador 金标准维度

**Phase 2 应新建/扩展**:改写解封 UI;视频生成链路(P2-1);埋点 + 转化漏斗(P2-10);配额/付费(P2-5);短链 302 跟随补齐。

---

## 7. 未决项 / 待 Founder 决策

1. **Phase 1 Gate 是否硬卡 Phase 2 启动**,还是能力建设 + 陪跑并行推进?(当前现实是并行。)
2. **改写解封时机与质量金标准**:谁定验收基线?先灰度(部分邀请码可见)还是达标全量?
3. **定位**:本轮已收窄为「看懂为什么火」分析工具——Phase 2 是否要把完整「改写→发布」闭环重新作为主线(关系到 Phase 1 Gate 中 H3「改写质量」假设能否验证)?
4. **DB 路径正式修 / prod 凭证轮换** 的优先级排期。

---

*本文为 Phase 1→2 交接基线。后续 phase 文档应继承本文 §3(铁律)、§4(视觉)、§6(基线)并增量,而非重写。所有引用文件名均已对真实仓库校验。*
