# Phase 2 发布目标 · 差距分析(2026-06-01)

**作者**: PM(Claude)· **方法**: 对照 [`phase2_master_plan_2026-05-31.md`](phase2_master_plan_2026-05-31.md) build order + 今天 13 个 commit + 逐项读码核验(非记忆)
**关联**: [`phase2_kickoff_synthesis_2026-05-31.md`](phase2_kickoff_synthesis_2026-05-31.md) · [`../PHASED_PLAN.md`](../PHASED_PLAN.md) §5.3 Gate

---

## 0. TL;DR

Phase 2 = **改写-发布闭环**(端到端 分析→改写→生成→发布)+ 达到 PHASED_PLAN §5.3 的 30 人 Beta Gate。

**今天完成的是「地基 + 一条腿」**:P0-a 工程债全清、改写「解封就绪」、鉴权堵刷钱、ARK 超时修、落地页案例自动化上线。但**闭环的后三段(改写真上线 / 生成 / 发布)还没打通** —— 当前线上用户能跑的仍只是「分析」单环。

**离「可发布」(完整闭环 demo-able)还差 4 个硬动作**,其中 2 个卡在 founder(质量门拍板 + 凭证轮换),2 个是工程(生成 leg 落地 + 发布收尾)。**关键路径串行 ~2-3 个 cycle。**

---

## 1. 已完成(今天,13 commits)

| 项 | 状态 | commit |
|----|------|--------|
| P0-a 工程债 B2/B4/B5/B7(缓存守卫/canvas.db路径/失败标lifecycle/遥测修真) | ✅ 上线 | ad67fdd |
| 6 决策代码(B6境内provider/D5长度/D3通用prompt/D2灰度flag/B3生成cost_guard/B8安全) | ✅ 上线 | ca01a3b |
| 鉴权A 每用户独立邀请码(堵 cost-cap 刷钱) | ✅ 上线 | 1a4e04b |
| D6 改写质量 prompt 3 轮调优(占位符泄漏→0,confidence 真实化) | ✅ 代码上线 | 25a5306 |
| ARK 超时 120→165s(内容丰富视频不再卡死) | ✅ 上线 | 60432d9 |
| 拆解进度卡顿修(inter-stage creep) | ✅ 上线 | 77bfa2f |
| 落地页案例自动化(数据驱动 + top-10 排名 + 用户跑完自动上) | ✅ 上线 | 5555095 |

**今天本质交付**:把 master plan 的 **P0-a 全部 + P0-b/P1 的前置代码** 做完并上线;额外完成了一条 founder 临时插入的「案例自动化」需求(不在原 build order,但消除了运营手工债)。

---

## 2. 离「可发布闭环」还差什么(按 build order)

> 核查口径:直接读码,非记忆。

### 🔴 P0-b 改写真解封 —— **代码就绪,但没翻开关**(闭环第一段缺失)
核验当前线上状态:
- `rewriteAccess.ts` 默认 `false`(灰度 flag 已建,但没开)
- `CASCADE_REWRITE_UPSTREAM` 默认仍 `fixture`(rewrite.py:74)
- `REWRITE_PIPELINE_REVISION = 1`(未 bump)

**= 改写功能用户摸不到,闭环停在「分析」。** 解封要三件事联动 + 先过质量门:
1. **[founder] 改写质量门拍板**(D6)—— 在 worksheet 勾「✅我会发」标 3-5 条锚点 → 定 rubric 阈值。**这是最强阻塞**:不拍板,后面全卡。
2. [工程] 真 URL 评测集跑 eval,过 §4.1 七项门(机械≥85% / realism≥3.8 / kept_formula≥70% / ad_risk=0 / 人工≥70% / llm显著优于fixture / 缓存守卫已落地✓)
3. [工程] 翻三开关:后端 `CASCADE_REWRITE_UPSTREAM=llm` + 前端 flag 开(灰度 cohort)+ bump revision 到 2
4. [前端] RewriteCard + 在途态接回 CardStack(rewrite_returned 帧已 wired,需渲染)

### 🟡 P1 生成 leg(草稿图)—— **cost_guard 已接线,但 leg 没打通**(闭环第二段)
核验:`ws_handlers.py:296` 生成 cost_guard **已接线**(B3 今天做了)✅。但还缺:
- **C3 镜头桥接(必新建)**:`build_shot_prompts` 把分析/改写 → canvas image-node。**依赖 P0-b 改写解封**(主用 `rewriteShots[].visual`,无改写则回退源片描述,语义弱)
- **草稿图四态状态机 UI**(IDLE/PENDING/POLLING/DONE/FAILED + reconnect 重建,复用 run_lifecycle)
- **provider 合规已落地**(B6 默认切境内 apimart)✅ —— 不再阻塞

### 🟡 P2 发布 leg 收尾 —— **未动**(闭环第三段)
核验 `buildPublishPack.ts`:仍 `baomam_fushi` 硬编码标签 + 兜底(line 9/16/22),仍只 `stripHookCode` **不 `scrubUiForbidden`**(禁词可漏到剪贴板)。要堵 4 个洞:
- 镜头图空壳(接 P1 草稿图 url)/ niche 硬编码去除 / 标题辅食兜底去除 / 复制前 scrub 禁词
- PublishPackCard 接回 CardStack(当前死代码)+ 分字段复制

### 🔴 P0-c prod 凭证轮换 —— **未做,上线硬 Gate**(横切)
4 项凭证(SSH key/root 口令/CF token/admin token)memory 明文已脱敏,但**真密钥未轮换**。**[founder] 需 SSH/console 执行**(runbook 在 [[reference_prod_server]])。任意正式 Beta 上线前的硬 Gate。

### ⚪ P3(视频 P2-1 / 配额付费 P2-5 / 25 事件埋点 P2-10)—— 闭环跑通后才启动
- 视频复用 P1 四态状态机(留扩展位)
- 配额付费(freemium ¥0 / Pro ¥39)随生成 cost_guard 落地后接 —— **免费额度数字待 founder 定**
- 埋点:`publish_pack_copied` 等贯穿全程,P3 对齐 25 事件

### ⚪ 并行轨 — 用户访谈(INTV)+ Phase 1 Gate 收口
- 访谈指南就绪(`phase2_user_interview_guide`),**未启动**:从邀请码 cohort 招 12 人,回灌「足够好的改写」词表给质量门
- Phase 1 Gate 8 指标(≥10试用/≥5完成/≥3回访…)未量化达成 —— 与建设并行陪跑

---

## 3. 两个「可发布」定义 —— 你要哪个?

「发布目标」有两档,工作量差一个数量级:

| | A. 闭环 demo-able(内部/灰度可跑通) | B. PHASED_PLAN §5.3 官方 Gate(可进 Phase 3) |
|---|---|---|
| 含义 | 端到端 分析→改写→生成草稿图→发布包 一条命令跑通 | 30 注册 / D1完成≥40% / 14天留存≥25% / 7天人均≥3条 / ≥5付费 / 单条<¥15 / 锚点复用≥60% |
| 还需 | P0-b 解封 + P1 生成 + P2 发布 + P0-c 凭证 | A + 视频/付费/埋点 + 真实 30 人 Beta 运营 + 留存数据 |
| 估时 | ~2-3 cycle(串行,卡 founder 质量门) | + 数周 Beta 运营 + 数据收集 |

**建议**:先冲 **A(闭环 demo-able)** —— 这是「Phase 2 能不能发布」的真实门槛(没有闭环,谈不上 Beta 留存)。B 是 A 跑通 + 真实用户运营后的自然结果。

---

## 4. 到「A. 闭环 demo-able」的关键路径(串行)

```
[founder] D6 质量门拍板(标锚点+定阈值)  ← 最强阻塞,先做
   └─> 改写 eval 过 §4.1 七项门
        └─> P0-b 翻三开关 + bump revision(改写真上线,灰度)
             └─> P1 C3 镜头桥接 + 草稿图四态 UI(生成草稿图)
                  └─> P2 发布收尾(堵 4 洞 + PublishPackCard 接回)
                       └─> 闭环 demo-able ✅
[founder] P0-c 凭证轮换 ═══ 横切,正式灰度前任意时点做
[并行] INTV 访谈 ═══ 回灌改写验收词表(可与 eval 并行)
```

**4 个硬动作**(2 卡 founder / 2 工程):
1. 🔴 **[founder] 改写质量门拍板**(D6 标锚点)— 解封整条链的总开关
2. 🟢 **[工程] P0-b 解封 + P1 生成 + P2 发布**(过门后串行,我可全做 + 真浏览器验证 + 部署)
3. 🔴 **[founder] P0-c 凭证轮换**(SSH,正式灰度前)
4. ⚪ **[并行] INTV 访谈启动**(可现在就开,不阻塞工程)

---

## 5. 我的建议:下一步做什么

**给 founder 的请求(解锁关键路径)**:
- **跑一次 D6 质量门标注**(~20min):`uv run python scripts/d6_generate_rewrite_samples.py --mode llm` 已在 prod 可跑;读 worksheet 勾「✅我会发」+ 定 rubric 阈值。这一步不做,改写解封整条链全卡。

**我能立即推进的(不等 founder)**:
- P2 发布收尾的**纯工程部分**(去 niche 硬编码 + 加 scrub + PublishPackCard 接回)—— 不依赖改写解封,可先做好等接
- eval 框架就绪性自检(真 URL 评测集能否跑通 generic 路径)
- INTV 访谈轨的运营脚手架(招募名单 + 7 阶段脚本就绪化)

**不建议现在做**:P3(视频/付费/埋点)—— 闭环未通前做这些是过早投入(PHASED_PLAN §7 反模式)。

---

*本文为差距分析,非新计划。build order / Gate / 风险登记以 master plan 为准;本文只回答「还差什么、谁来做、什么顺序」。*
