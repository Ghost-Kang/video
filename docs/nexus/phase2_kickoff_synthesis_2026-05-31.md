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

> 这 8 条是对抗验证从真码挖出的「不修则解封翻车 / 慢生成裸奔 / 数据失真」级别阻断。**它们是 Phase 2 能否安全启动的真实门槛。**

| # | 硬阻断 | 证据(file:line) | 修在哪一步 |
|---|--------|----------------|-----------|
| **B1** | **解封三联动,缺一即假解封** | `App.tsx:157` REWRITE_ENABLED=false(源码硬常量,需重建) + `rewrite.py:70` CASCADE_REWRITE_UPSTREAM 默认 fixture(部署文件全没设) + `contract.py:28` revision=3 需 bump | P0-b |
| **B2** | **改写缓存零版本守卫** —— 切 llm 后 24h 内必命中旧 fixture 套娃(精确重蹈分析缓存坑) | `rewrites_repo.py:47-64` 缓存键无 pipeline 列;全仓 `REWRITE_PIPELINE_REVISION` grep=0;铁律① 的 ANALYSIS_PIPELINE_REVISION 对 rewrites 表**完全无效** | P0-a(解封前置) |
| **B3** | **生成 leg 零成本护栏裸奔** —— 任意用户 ×retry3 ×重启重入队 = 真金白银失控 | `workers/` + `tools/generation.py`/`video_generation.py` grep cost_guard=0;`cost_guard.py:36` PREDICT_SHOT_IMAGE_CNY=1.5 **从不被调用**,无 video 按秒预测 | P1(生成上线前) |
| **B4** | **canvas.db 第二库无容器检测** —— 慢生成队列全在此库,挪文件/改 Dockerfile 即回 off-by-one,重启丢队列(Google 内存 task 重入队=重复扣费) | `canvas_persistence/db.py:17` parent×5 纯相对路径,与 cascade.db `db_path()` 的 `/app/src` 检测策略不一致(巧合正确) | P0-a |
| **B5** | **工具级失败漏标 lifecycle** —— 工具失败记成 done,重连 replay 拿不到 failure,违反「失败有下一步100%」 | `cascade.py:224/304/409/577` 四处 except HardFailure 只 `_push_failure_frame` 不 `mark_failed`;`agent_runner.py:127` 随后 mark_done | P0-a |
| **B6** | **生成图默认跨境 Gemini** —— 改写已隔离境内,生成图默认 google 处理 30 人真实用户数据,PIPL §38 张力 | `config.py:27` IMAGE_GEN_PROVIDER 默认 `google` | **待 founder 拍板**(P1 前) |
| **B7** | **成本遥测 provider 失真** —— Beta 期成本/上游 dashboard 误判(数字好看≠真相,铁律⑤同类) | `http_router.py:217` analysis cost 事件硬编码 `provider="fixture"`,实际 doubao_direct | P0-a |
| **B8** | **凭证未轮换 + 安全小洞** —— 4 项凭证待轮换;另:invite_code 拒绝时打印原始码(`ws_server.py:72`)、admin token 非常量时间比较(`http_router.py:570` 用 `==`)、cost_guard user_id/run_id 须服务端派生(否则换字段绕 cap 刷钱) | memory `reference_prod_server` + 上述行 | P0-c(上线 Gate) |

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

## 5. memory & 后续

- 设计基线已记 memory `project_phase2_kickoff`。
- 工作树:本次新增 6 份 nexus 文档(含本文),warm_tech 文档有 1 处改动 —— **均未提交**,等你过目。
- 下一步等你 §3 拍板后,P0-a 工程债(B2/B4/B5/B7)不依赖任何决策、可立即开工;P0-b/P1 的 provider 与灰度需你先定。

---

*本文是 Phase 2 启动入口。各 leg 细节见五件套;现状断言全部 Read/Grep 核验到 file:line,对抗验证结论见各文档 mustfix。*
