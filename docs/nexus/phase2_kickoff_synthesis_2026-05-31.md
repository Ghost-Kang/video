# Phase 2 启动 · 设计总览 + 对抗验证结论(SYNTHESIS / 入口)

**创建**: 2026-05-31
**负责**: PM(编排 + 综合,Opus 4.8 · ultracode 多 agent workflow)
**性质**: Phase 2 启动包的**单一入口**。把架构 / 改写质量 / 闭环 UX / 用户访谈 / 总计划 五份设计 + 18-agent 对抗验证结论 收敛成一页可决策视图。
**怎么用**: Founder 先读本文 §0 + §3(待拍板)+ §2(P0 硬阻断);深入某 leg 再点对应文档。

---

## 0. TL;DR

按你的 6 点指令,以 ultracode 多 agent workflow(18 agents / ~1.6M tokens / 375 tool calls)完成 Phase 2 启动设计:**6 个 leg 先读真码取证 → 5 份设计文档(架构agent + 质量agent 等点名到位)→ 7 个 skeptic 对抗验证**。

- **定位锚定(你的点 4)**:Phase 2 = **改写-发布闭环**(端到端 分析→改写→生成→发布)。验证确认这**不是新方向,而是恢复** `PHASED_PLAN.md` §4.1 原 Phase 1 完整闭环——当前线上只跑到「看懂为什么火」,后半段被双重暂挂。
- **解封改写(你的点 2)**:质量 agent 已定可度量验收标准(五维 rubric + 9 项硬检查 + 批次解封门)。**但解封不是翻开关那么简单**——验证挖出「三联动缺一即假解封」+「改写缓存零版本守卫」两个真硬阻断。
- **整体架构(你的点 3)**:Backend Architect 设计了 Phase1+2 统一架构(CreationRun 聚合根 + leg 间 handoff 契约 + 慢生成任务沿用 Phase1 通讯加固 + M0-M5 迁移顺序)。验证判 **SOUND**,但揪出 6 个 code-verified 硬阻断。
- **DB 修 + 凭证轮换(你的点 5)**:已纳入 Phase 2 P0。验证发现 **cascade.db 已修,但第二个库 canvas.db 仍是「巧合正确」,慢生成队列全在此库** —— 这是比原以为更大的隐患。
- **并行访谈(你的点 1)**:访谈指南就绪,与建设轨并行,每问可回灌 Phase 1 Gate / H 假设。

**一句话**:设计扎实、全部 grounded;落地前有 **8 个 P0 硬阻断**(全部 code-verified 到 file:line);**6 类决策 founder 已于 2026-06-01 拍板**(见 §3),开工无阻塞。

---

## 1. 设计五件套(产物清单)

| 文档 | agent | 覆盖你的点 | 验证结论 |
|---|---|---|---|
| [architecture_phase1_phase2_design](architecture_phase1_phase2_design_2026-05-31.md)(476行) | Backend Architect | ③ 整体架构 + ⑤ DB/凭证 | **SOUND**(6 mustfix) |
| [rewrite_quality_standard](rewrite_quality_standard_2026-05-31.md)(296行) | Model QA Specialist | ② 改写质量标准 | **NEEDS-WORK**(6 mustfix) |
| [phase2_loop_ux_design](phase2_loop_ux_design_2026-05-31.md)(314行) | Product Manager | ④ 闭环 UX | **SOUND**(4 实现 Gate) |
| [phase2_user_interview_guide](phase2_user_interview_guide_2026-05-31.md)(229行) | Feedback Synthesizer | ① 并行访谈 | **NEEDS-WORK**(3 mustfix) |
| [phase2_master_plan](phase2_master_plan_2026-05-31.md)(269行) | Product Manager | 编排全部 + build order + 4-owner | **NEEDS-WORK**(6 mustfix) |

> NEEDS-WORK ≠ 设计错,而是 skeptic 要求把若干断言补成可执行 checklist / 补现存隐患的明确修法 —— 已在各文档 mustfix 列清。架构与 UX 判 SOUND。

---

## 2. P0 硬阻断(落地前必修,全部 code-verified)

> 这 8 条是对抗验证从真码挖出的「不修则解封翻车 / 慢生成裸奔 / 数据失真」级别阻断。
> **进度(2026-06-01)**:B2/B4/B5/B7 已修(commit ad67fdd P0-a)。本轮再修 B6/B8(安全小洞部分)+ 落地 D1/D3/D5/D2 全部代码,生成 cost_guard(B3)已接线。剩余:B1 解封 flip(需质量门)+ B8 凭证轮换(P0-c,需 founder)+ cost_guard 身份派生缺口(B8-3,需鉴权改造)。

| # | 硬阻断 | 证据(file:line) | 状态 |
|---|--------|----------------|-----------|
| **B1** | **解封三联动,缺一即假解封** | `App.tsx` REWRITE_ENABLED + `rewrite.py:70` CASCADE_REWRITE_UPSTREAM=fixture + `contract.py` revision | ⏳ 解封就绪(D2 flag 已可运行时控,仍默认关);flip 待质量门 |
| **B2** | **改写缓存零版本守卫** | `rewrites_repo.py` 缓存键无 pipeline 列 | ✅ 修复(REWRITE_PIPELINE_REVISION=1,commit ad67fdd) |
| **B3** | **生成 leg 零成本护栏裸奔** | `workers/`+`generation.py` 无 cost_guard | ✅ 接线(enqueue 前置 cost_guard + 视频按秒预测,handle_execute_node) |
| **B4** | **canvas.db 第二库无容器检测** | `canvas_persistence/db.py` parent×5 无检测 | ✅ 修复(resolve_data_dir,commit ad67fdd) |
| **B5** | **工具级失败漏标 lifecycle** | `cascade.py` HardFailure 不 mark_failed | ✅ 修复(RUN_CTX.tool_failure,commit ad67fdd) |
| **B6** | **生成图默认跨境 Gemini** | `config.py` IMAGE_GEN_PROVIDER 默认 google | ✅ 修复(默认切 apimart + execute_node 第二处漂移修;D1 双轨) |
| **B7** | **成本遥测 provider 失真** | `http_router.py` 硬编码 fixture | ✅ 修复(active_upstream,commit ad67fdd) |
| **B8** | **凭证未轮换 + 安全小洞** | invite码明文/admin token `==`/cost_guard 身份 | 🔶 安全小洞已修(invite码脱敏 sha256[:8] + admin token compare_digest);凭证轮换=P0-c 待 founder;身份派生缺口已注释+§6 follow-up |

**还有几条 cosmetic / 非阻断**(不卡启动,顺手修):事件数 23→21(`event_names.py` 实 21 个);run_started 生产从不 emit(只在 tests,访谈轨 Gate 计数会漏计);boto3 同步上传是否已 to_thread(`s3_upload.py:29` + `video_pipeline.py:55` 需 grep 确认);改写长度上限三处不一致(prompt:24 / checks.py:41 / 还有 rewrite.py:215-218 fixture 兜底)。

---

## 3. Founder 决策(2026-06-01 已拍板,后续 phase 直接继承)

> 这 6 项原为待拍板,founder 已定。**后续不要再问,以下为准。**

| # | 决策项 | Founder 拍板 | 对开工的影响 |
|---|--------|-------------|-------------|
| D1 | 生成图 provider 合规(B6) | **双轨:境内 Apimart 默认 + 跨境 Gemini 可选** | `config.py:27` 默认改境内 Apimart;Gemini 降级为显式可选(带跨境同意)。P1 先把默认值切境内即可解锁开工;可选轨工程量大,排到 P1 后段/P3 |
| D2 | 改写解封节奏 | **先灰度一周,再全量** | 前端 `App.tsx:157` `REWRITE_ENABLED` 必须从源码硬常量改成**按 cohort 的运行时 flag**(列入 P0-b);先开 rewrite-beta cohort 邀请码,跑一周达标再全量 |
| D3 | 去 niche 后改写形态 | **单一通用代笔 prompt + 用户填一句话主题** | 合并 baomam/yuer/jiating 三套为一个通用 prompt;**第②幕需加「一句话主题/赛道」输入框**喂改写;eval 去掉 per-niche 强制项;bump `REWRITE_PIPELINE_REVISION` |
| D4 | Phase 1 Gate 是否硬卡 P2 | **不硬卡,能力建设 + 陪跑并行** | 建设轨与访谈轨并行;接受「改写未上线期访谈只验『完成一次分析』非完整闭环首条」的偏差,解封后再正式收口完整闭环 Gate |
| D5 | 改写脚本长度上限 | **80–220 字** | 同步改 4 处:`rewrite_*.md:24`(现 80-400)+ `checks.py:41`(现 80-600)+ `rewrite.py:215-218` fixture 兜底 + brief 措辞 |
| D6 | 改写「质量达标」谁拍板 | **Founder 人工锚点 + rubric 辅助** | Founder 对 3-5 条改写样例标「这就是我会发的口吻」作 judge 校准锚点(需真 URL+doubao 先跑出样例);之后自动 rubric+阈值跑批量。**这是 P0-b 解封门的人类输入,需 founder ~20min** |

**附:成本/付费**(可稍后)：freemium ¥0 / Pro ¥39 的具体免费额度待 founder + 成本核算定(P2-5)。

---

## 4. 建设节奏(master plan §2 摘要)

**Build order**(每步独立可发可测,过 Gate 才进下一步):
- **P0 还债+解封**(三并行子轨):P0-a 工程债(B2/B4/B5/B7 + 改写版本守卫)→ P0-b 解封改写(过质量门 → 三联动 B1 → bump revision)→ P0-c 凭证轮换(B8)。
- **P1 生成草稿图**(先 image-grounded,不做视频):C3 镜头桥接 + 生成 cost_guard(B3)+ 四态状态机(复用 run_lifecycle/pendingByThread)+ provider 合规(B6)。
- **P2 发布收尾**:复用 buildPublishPack,堵镜头图空壳 / niche 硬编码 / scrub 三洞。
- **P3 视频(原 P2-1)/ 配额付费 / 埋点收口**:闭环跑通后按 INTV 真实需求排。

**并行访谈轨**:与建设轨同时跑,回灌 Gate / H 假设。

**4-owner**(铁律,founder 2026-05-24 后 decision-only):首 cycle 分配见 master plan;Claude=后端债+解封工程+架构落地,Cursor/Codex=前端闭环 UX + eval 框架改造,Founder=本文 §3 五项决策 + 改写口吻人类锚点。

---

## 5. 实现进度(2026-06-01)

P0-a(commit ad67fdd)+ 本轮(6 决策解锁的全部代码)已落地、测试绿:**backend 574 passed / frontend 240 passed**。
- ✅ **已实现并测试**:B2(改写缓存守卫)/ B4(canvas.db 统一路径)/ B5(工具失败标 lifecycle)/ B7(遥测修真)/ B6+D1(生成图默认境内 apimart + execute_node 第二处漂移)/ B8 安全小洞(invite 码脱敏 + admin token compare_digest)/ B3(生成 enqueue 前置 cost_guard + 视频按秒预测)/ D5(改写长度 80–220 五处统一)/ D3(generic 通用代笔 prompt + 一句话主题,旧三套保留)/ D2(REWRITE_ENABLED 运行时可控,默认仍关)。
- ⏳ **解封就绪但未 flip**(等质量门 D6):改写仍走 fixture 路径,REWRITE_ENABLED 默认 false,CASCADE_REWRITE_UPSTREAM 默认 fixture,REWRITE_PIPELINE_REVISION 仍=1。解封时一次性 bump 到 2 并 flip 三联动(B1)。

## 6. 三项收尾进度(2026-06-01,founder 指「1 2 3 先完成」)

> 这三项性质不同:能自主做完的已做完;**本质需 founder/SSH/鉴权决策的,只能就绪化 + 写清 runbook,不能假装完成**。

### ① D6 改写质量人工锚点 —— ✅ 工具就绪,待 founder 标
- 已建样例生成器 `backend/scripts/d6_generate_rewrite_samples.py`:对一组通用主题跑 **generic 通用代笔**改写,产出可勾选 worksheet(`docs/nexus/founder_log/d6_rewrite_anchors_<date>.md`)。
- `--mode fixture`(默认,免费确定性)已验证管线通;**`--mode llm`(真 doubao 境内,有 API 成本)未自动跑** —— 烧钱 + 主题应由 founder 定,不擅自触发。
- **待 founder**:`uv run python scripts/d6_generate_rewrite_samples.py --mode llm`(或给我主题集 + 授权我跑),然后在 worksheet 勾「✅ 我会发」。被标 ✅ 的样例 = judge 校准锚点 + 解封质量门人类基线。
- 注:fixture 模式输出会暴露模板套娃局限(借用源台词,与新主题不贴)——这正是为何锚点必须用 llm 模式跑,印证了「改写解封前必须接真模型」。

### ② prod 4 项凭证轮换 —— 🔶 代码就绪 + 泄露已从 memory 脱敏,轮换本身需 founder/SSH
- **代码侧已就绪**:`CASCADE_ADMIN_TOKEN` 走 `os.getenv`(config.py:101),B8 已改常量时间比较 —— 换值即生效,无需改码。
- **泄露面已收敛**:`reference_prod_server` memory 里的 root 口令 / CF token / SSH 指纹明文已**脱敏删除**(2026-06-01),并补了轮换 runbook。**注意:脱敏 memory ≠ 撤销泄露**,真正消除暴露必须轮换 prod 上的 secret 本身。
- **待 founder(不可自动化——irreversible prod ops + 需 SSH/console/CF dashboard)**:① 重生 SSH keypair 换 prod authorized_keys;② 经 console 改 root 口令;③ CF dashboard 撤销+新建 token 更新 cloudflared.service;④ prod .env 换 `CASCADE_ADMIN_TOKEN` + 重启 backend。runbook 见 memory `reference_prod_server`。

### ③ cost_guard 身份派生缺口(B8-3)—— 🔶 已锚定 + 出设计,真修需鉴权决策
- **核实真相(比原判断更严重)**:不只 HTTP 入口——**WS 入口的 `user_id` 也来自客户端**(`ws_server.py` 取 `auth.user_id`,仅靠*共享* invite_code 把门,无 per-user 身份)。即全系统**没有任何服务端签发的 per-user 身份**;cost cap 的 user/run key 全是客户端自报,过 cohort 门者可轮换字段绕 `CASCADE_RUN/USER_DAY_CAP` 刷钱。
- 故修正先前说法:B3 的 WS 路径用 `ctx.user_id`,比 HTTP per-message 取 body 稍好(连接时定、不可逐请求轮换),但**底层身份仍是客户端自称的**,非真正可信。
- **代码已加 KNOWN 注释**锚定(http_router 两处)。**真修 = 引入 per-user 鉴权(server 签发 token/session)**,这是一次鉴权架构改造,**需 founder 先定模型**(每用户独立邀请码?注册登录?签发短期 token?),不是「小洞」补丁能解决,也不该我擅自塞进鉴权流。设计选项见 §6.1。

#### 6.1 B8-3 鉴权模型选项(待 founder 选,供解封灰度前定)
| 选项 | 做法 | 代价 | 适合 |
|------|------|------|------|
| A 每用户独立邀请码 | INVITE_CODES 从「共享集合」改「码→user_id 映射」,user_id 由码反查(非客户端传) | 小改:ws_server + http _check_auth 查映射;邀请码发放要一人一码 | 内测/小灰度最省,直接堵刷钱 |
| B 服务端签发短期 token | 邀请码换一次性登录 → 签发 HMAC/JWT 短 token,后续请求带 token,user_id 从 token 解 | 中:加签发端点 + 校验中间件 + 前端存 token | Beta 规模、可控会话 |
| C 完整注册登录 | 账号体系 + 密码/OAuth | 大 | Phase 3 商业化才值得 |
> 推荐 **A**(内测期最小改动即可让 cost cap 可信),Beta 扩量再上 B。无论哪个,都应在**解封灰度前**落地——否则改写/生成接真模型 = 真金白银裸奔在客户端自报身份上。

### [cosmetic] 预存在债(非本轮引入,顺手记)
`App.tsx` 一处 `no-unused-expressions` eslint error(三元当语句,line ~202);事件数文档写 23 实为 21;run_started 生产从不 emit。

---

*本文是 Phase 2 启动入口。各 leg 细节见五件套;现状断言全部 Read/Grep 核验到 file:line,对抗验证结论见各文档 mustfix。*
