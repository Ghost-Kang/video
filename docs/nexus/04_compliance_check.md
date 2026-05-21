# Cascade Phase 0/1 China Compliance Audit

**Document Status**: v1 — Phase 0 audit, NEXUS sprint output
**Date**: 2026-05-19
**Auditor role**: Legal Compliance Checker (non-lawyer; this is a defensive readiness review, **not legal advice**)
**Scope**: Cascade Phase 0 deliverables (contract + adapter) + Phase 1 plan (≤10 hand-picked Chinese creators)
**Reads**: `PRODUCT_VISION.md`, `PHASED_PLAN.md §4`, `TOPRADOR_SCHEMA.md §7`, `MVP_SCOPE.md §10`, `backend/src/agent/cascade/{adapter.py,contract.py}`

---

## Verdict: **CONDITIONAL — SAFE FOR 10-USER CONCIERGE TRIAL** if 5 light items are done before first invite. **NOT SAFE FOR PUBLIC LAUNCH** without separate Phase-2 compliance workstream.

The 10-user trial is on defensible ground because (a) it is non-public, invite-only, no payment, no public-facing "service"; (b) data persisted is narrowly scoped (URLs + text + cost), no biometric/identity data, no 实名认证; (c) the doubao multimodal LLM keeps deep-analysis data 境内. The single biggest gap is **absence of a 用户协议 + 隐私政策** — fixable in <1 day with a templated 中文 notice + click-through. The single biggest **deferred** risk is **算法备案 + 生成式 AI 备案** — required well before any public/free-tier launch, not for 10-user concierge trial (实务做法 view; see §3).

---

## Compliance matrix

| 法规 / 框架 | 适用 | 当前状态 | 10-user 风险 | 100-user (public) 风险 | 行动 |
|---|---|---|---|---|---|
| **个人信息保护法 (PIPL)** (2021) | 是 — 收集 URL、改写、偏好 = 个人信息 | 无 隐私政策, 无 知情同意 | **中** — 私下试用＋告知后可控 | **高** — 公开必须有 隐私政策 + 同意流 + 个人权利接口 | Phase 1 加 1 页 隐私通知 + 试用知情同意 |
| **PIPL §28 敏感个人信息** | 否（10-user 不涉及） | n/a | 低 | 中 — 若 scene `subject="宝宝"` 触发未成年 → 升敏感 | Phase 1 PII strip 已有；P2 加未成年关键词标记 |
| **数据安全法 (DSL)** (2021) | 是（分类分级义务） | 未做分类 | 低 — 数据量小 | 中 — 公开后需做分类登记 | Phase 2 做数据分类清单 |
| **网络安全法 (CSL)** (2017) | 部分（非"关键信息基础设施"） | 无 ICP，无等保 | 低 | **中** — 公网服务需 ICP 备案 + 等保 2.0 二级 | Phase 2 公测前办 ICP |
| **生成式人工智能服务管理暂行办法** (2023年7月15日施行) | 是（文本＋图像生成均覆盖） | 未备案 | **中-低** — 10-user 内测＋未对公众提供，**实务做法**认为可豁免 | **高** — 公测即 "向公众提供"，必须 算法备案 + 安全评估 | Phase 2 启动备案，**不在 Phase 1**（备案周期 1-3 月） |
| **互联网信息服务算法推荐管理规定** (2022) | 适用性边缘（改写 prompt 含算法但非推荐算法） | 未备案 | 低 | **中** — 实务做法看是否被网信办认定为"具有舆论属性或社会动员能力"，公测可能触发 | Phase 2 法律咨询后定 |
| **信息网络传播权 / 著作权法** | 是 — 第三方视频被分析 | 24h 不存原始视频 (MVP §10) | **中** — 分析 JSON 是衍生作品的灰区；学习用＋小范围实务上低风险 | **高** — 公开商业化"复刻爆款"易引发平台投诉 + 民事索赔 | Phase 1 用户协议明确"借鉴公式、非复制" + 不公开分析 JSON |
| **抖音/小红书 用户协议 + robots** | 是 — 抓取/分析他人公开内容 | 平台 ToS 通常禁止"商业化复用" | **中** — 试用期不公开 OK | **高** — 公测要么取得授权要么承担投诉风险 | Phase 2 法律 + BD 介入 |
| **未成年人保护法** (2020 修订) + 未成年人网络保护条例 (2024) | 中等 — 母婴/育儿赛道源视频可能含未成年人 | 无 subject 字段过滤 | **低-中** — 我们不发布，只分析 | **中-高** — 公测生成的成品若含未成年人形象＝高风险 | Phase 1 加 subject 关键词审计 (1h)；Phase 2 加儿童肖像生成拦截 |
| **数据出境安全评估办法** (2023) + **个人信息出境标准合同办法** (2023) | **是** — Apimart / Google Gemini 走境外 | adapter 已有 W9 跨境标记，但仅是 source URL 检查 | **中** — 用户输入 URL/文本送到 Gemini = 数据出境，10 用户量级**实务做法**通常不触发监管阈值（10w 自然人门槛远超），但仍是 PIPL §38 项下行为 | **高** — 公开服务一旦累计 PI 出境≥10w 自然人或被举报，需补办标准合同 / 评估 | Phase 1 给境内默认 + 知情同意覆盖；Phase 2 切换为境内 image gen 或办标准合同 |
| **ICP 备案 (工信部)** | 公网域名 = 是 | 假设域名已备 / 未备未知 | **中** — 若已上公网无 ICP，开站日起违规 | 高 | 上公网前确认；不上公网（内网 + 邀请码）可绕开 |
| **增值电信业务许可证 (EDI/ICP)** | 经营性互联网信息服务 = 是（一旦收费） | n/a，Phase 1 不收费 | 低 | **中-高** — 收费即需 ICP经营许可证 | Phase 2 申请（周期 60-90 天） |
| **网信办 算法备案** | 是 — 改写 prompt 是算法 | 未备案 | 低 — 不公开 | **高** — 公测前未备案 = 责令限期改正 + 罚款 | Phase 2 启动（与生成式 AI 备案合并申报） |
| **应急响应 / 内容审核 (举报渠道、关键词过滤)** | 是 — 凡能生成内容的服务 | 无 内容安全过滤 | 中 — 10 用户已知身份 | **高** — 公测必须有违规内容拦截 + 用户举报通道 | Phase 2 接 阿里云 / 腾讯云 内容安全 API |

---

## Top 5 must-do before 10-user trial (ranked, time-budgeted, ≤2 days total)

> 这 5 项**不增加 > 2 天**，是 Phase 1 启动前的最小合规闸门。

1. **【0.5 day】写一页中文 用户协议 + 隐私政策（试用版）+ 邀请页 click-through 同意**
   - 内容要点：(a) 试用性质 / 不公开 / 无费用；(b) 收集 URL、改写文本、偏好，目的=改善产品＋个性化分析；(c) 数据存于境内 SQLite；(d) 用户随时可发邮件要求删除；(e) **明确：图像生成调用 Gemini = 境外，用户知情同意发送 prompt + 输入文本到境外**；(f) 借鉴爆款公式、非复制原视频；(g) 用户保证有权使用所粘贴的 URL。
   - 法律依据：PIPL §13（知情同意）, §17（告知义务）, §38（出境告知＋单独同意）, §39。
   - **不需要律师**：用 飞书 / GitHub 公开模板即可，标注 "v0 试用版，公测前重写"。

2. **【0.25 day】给 `_strip_pii` 增加 IP 地址与作者昵称字段过滤**
   - 当前 `_KNOWN_PII_KEYS = {author_uid, author_handle, author_avatar_url, uid}` ✅ 已经够好。
   - 补一项：`author_nickname`, `author_name`, `ip_address`, `user_ip`（防御性）。
   - 单测覆盖。
   - 法律依据：PIPL §4（个人信息定义包含 IP）, 实务上 ICP 备案场景下 IP 是必须 strip 的 PI。

3. **【0.25 day】为 W9_CROSS_BORDER_SOURCE 加一个 hard block 开关（Phase 1 默认拒绝 YouTube/TikTok）**
   - 当前 adapter 只 emit warning。建议 Phase 1 增加 `STRICT_CROSS_BORDER_REJECT = True` 配置项 → HardFailure。
   - 原因：拒绝 YouTube/TikTok URL 输入可以彻底回避"分析境外平台内容＝出境＋著作权双重风险"。**这是 10-user 期间最干净的姿态**。
   - 法律依据：实务做法 — 不接境外 URL 就不存在 出境的"个人信息"由用户主动引入；DMCA 之类跨境著作权风险也避开。

4. **【0.5 day】给所有 scene `subject` 字段加未成年人关键词 audit + 日志告警**
   - 关键词：`宝宝 / 小孩 / 婴儿 / 幼儿 / child / baby / kid / 小朋友`
   - 触发后：在 warnings 加 `W_MINOR_SUBJECT_DETECTED`（INFO 级），写入审计日志，**不阻断 Phase 1**（仅观察用）。
   - 用途：等到 Phase 2 做未成年人保护拦截时已有数据。
   - 法律依据：未成年人保护法 §73, 未成年人网络保护条例 (2024) §27 (生成内容涉未成年需审核)。

5. **【0.5 day】用户协议中明确"24h 删除"+ 数据导出/删除联系渠道**
   - 加一行：`用户可发邮件 to <founder@email> 请求 (a) 导出全部数据；(b) 删除账号 + 所有 run。15 天内响应。`
   - 法律依据：PIPL §44-§47（个人查阅、复制、转移、删除权）。
   - **实现层**：试用期手动处理即可（10 个人 × 邮件兜底）。不需要 自动化 API（Phase 2 再做）。

**合计 = 2 人天。在 Phase 1 buffer 内（PHASED_PLAN §4.2 给了 25% buffer = 5 天）。**

---

## Top 5 must-do before 100-user public launch (Phase 2/3 工作量，不挤进 Phase 1)

> 这些都是公测前必须做的、各项需要 5-30 天，**严禁挤进 Phase 1**。

1. **【5-10 天 + 30-90 天等待】生成式 AI 服务备案 + 算法备案（两件事可一同申报）**
   - 主管：网信办 + 文旅 + 公安。
   - 材料：算法说明书、安全自评估报告、训练数据来源说明、内容安全机制、关键词过滤库、举报机制。
   - **关键时点**：必须在向不特定公众提供服务前完成。10 人内测＋邀请制可豁免（**实务做法**，无明确 条文 定义"公众"门槛；建议法律意见书背书）。
   - Phase 2 的第一周就要启动。

2. **【3-5 天 + 等待】ICP 备案（如未办）+ ICP 经营许可证（如要收费）**
   - 工信部备案：30 个工作日内审批，需阿里云 / 腾讯云协助。
   - 经营许可证：60-90 天，需公司注册资本≥100w（实务）、3 名社保员工等门槛 → **不一定 Phase 2 当月能拿到**，建议在收费前 3 个月启动。

3. **【7-15 天】内容安全过滤链路接入（阿里云 / 腾讯云 内容安全 API）**
   - 拦截：(a) 涉政、涉黄、涉暴 文本；(b) 未成年人肖像生成；(c) 名人 / 公众人物 生成；(d) 涉敏感 LOGO / 品牌。
   - 强制：所有 image gen 输入 prompt + 输出图像走一次过滤。
   - 法律依据：生成式 AI 暂行办法 §4(1)(4), §9-§10。

4. **【5-10 天】数据出境合规：要么换境内 image gen，要么走 标准合同条款 (SCC)**
   - 选项 A（推荐）：image gen 切换到 阿里 通义万相 / 字节 即梦 / 腾讯 混元（境内）→ 彻底取消"用户输入文本送境外"。
   - 选项 B：保留 Gemini，但 (a) 单独同意流；(b) 与 Google 签 标准合同（实务上对自然人主体 Google 是合规接收方，但仍需备案 标准合同 to 网信办，备案时长 10w 自然人门槛以下可豁免评估、走 标准合同 备案路径）。
   - 法律依据：PIPL §38-§39, 个人信息出境标准合同办法 (2023)。

5. **【3-5 天】用户权利接口产品化 + 数据保护负责人 (DPO) 指定**
   - 自动化 个人信息导出 (JSON 下载) + 删除账号 (含所有 run cascade 删除)。
   - 公示 联系方式（邮箱足够，无需独立部门）。
   - 法律依据：PIPL §52（处理 100w 人以上 PI 须指定 DPO，10-100 人公测期间不强制，但**实务做法**建议提早做）。

---

## Things that are OK as-is (defensible posture)

✅ **`_strip_pii` 当前覆盖 `author_uid / author_handle / author_avatar_url / uid`** — 在 contract §7 "no author UID, no author handle, no author avatar URL is required" 设计意图下，是合理的 PII minimization（PIPL §6 最小必要原则）。审计补 `author_nickname / ip_address` 即可。

✅ **24h 不存原始视频二进制** (MVP_SCOPE §10) — 对 信息网络传播权 是合理的 实务做法 抗辩点：Cascade 不在"提供"原作品（无 cache、无 transcode、无 distribution），只在做 "为创作目的的临时分析"。这与"网络爬虫＋公开数据用于研究"的判例方向一致（**注**：无明确 条文 兜底，是 实务做法 + 案例倾向，律师可能仍要求加强）。

✅ **doubao 多模态 LLM (字节境内)** — 深分析数据不出境，PIPL §38 不触发。这是 Cascade 选 doubao 而非 OpenAI 的关键合规优势，**值得在 PRODUCT_VISION 显式记录**。

✅ **schema_version + warnings[] + failures.py 的 audit trail 设计** — 在合规检查中是加分项，证明你有"可追溯的处理决策"。PIPL §55 的影响评估、§51 的安全管理义务 都会要看这种 audit log。**继续保留**。

✅ **`W9_CROSS_BORDER_SOURCE` 已经在 adapter 实现** — 表示你**主动识别了**跨境数据来源问题，不是被动忽略。从合规态度看是非常加分的（举证时律师爱看这种"明知风险并标注"的代码）。

✅ **不做 OAuth 一键发布 (MVP §1 决策 27 + PHASED_PLAN §4.3)** — 间接规避了"代发布"产生的"我们成了内容分发者"的法律定性风险。**继续不做**。

✅ **schema 设计上没有要求 author_id、author_handle** — 这是 PII minimization 的工程实现，从 GDPR/PIPL 角度都属于 "privacy by design"。继续保持。

---

## Honest open questions for founder + lawyer

> 这些问题我（合规审计员）**不能仅凭法条给确定答案**，需要中国数据保护律师 30-60 分钟咨询。建议在 Phase 1 启动后、Phase 2 之前的某个周末做一次电话咨询（费用通常 2000-5000 元）。

1. **"10 人邀请制内测" 是否构成生成式 AI 暂行办法定义的"向公众提供"？**
   - 我的判断：**实务做法**多数认为不构成（同 Cursor、Perplexity 在 中国 都未备案就开始内测的先例），但 暂行办法 §2 文字上是 "向中华人民共和国境内公众提供"，未定义"公众"门槛。律师意见决定 Phase 2 节奏。

2. **改写 prompt + storyboard 算 "推荐算法" 吗？**
   - 算法推荐管理规定 §2 列举了 5 类算法（生成合成、个性化推送、排序精选、检索过滤、调度决策）。改写脚本最接近"生成合成"，**实务做法**已纳入 算法备案 (生成式 AI 备案与算法备案是同一套接口的两个分类)。可以一并申报。

3. **抖音 / 小红书 ToS 中 "禁止抓取 / 商业化复用" 条款，对 Cascade 这种"用户主动粘贴 URL → 系统分析"是否构成违约？**
   - 我的判断：用户粘贴 = 用户自己的行为，平台合约约束的是用户而非 Cascade。但 Cascade 如果 a) 大规模代抓、b) 把分析结果公开展示，可能被认定 帮助侵权 / 不正当竞争。Phase 1 的"内测＋不公开分析 JSON"姿态相对安全。**需要律师审过用户协议条款里 "用户保证自己有权使用粘贴的链接" 这一句的可执行性。**

4. **scene[].dialogue 存储 = 复制对白文字 = 是否侵犯 著作权？**
   - 对白文字属于 原视频作者著作权。我们做的是"短引用＋分析目的"，**实务做法** 在 著作权法 §24 "为介绍、评论某一作品 ... 适当引用" 框架下可主张合理使用，但**这是抗辩，不是豁免**。律师建议：(a) 限定 dialogue 最大长度（已 ≤2000 char，OK）；(b) 限定不公开展示给非粘贴用户；(c) 不基于 dialogue 单独产生商业价值（we sell 改写后的新脚本，不是原 dialogue）。

5. **未成年人形象的"分析" vs "生成" 的法律差异？**
   - 母婴/育儿赛道源视频会有 宝宝出镜。我们：(a) 分析阶段 = 看图片识别"主体是婴儿" → 实务上不算 "处理未成年人个人信息"（无 identification），但 (b) 如果用户生成的新视频里包含 与原视频相似的婴儿形象 → 进入 未成年人网络保护条例 §27 监管范围。**Phase 2 必须拦截 image gen 输出包含真实未成年人形象的 prompt**。

6. **创作者粘贴的 URL 本身是否构成"个人信息"？**
   - 我的判断：单独 URL 不算；但 URL + 时间戳 + 用户 ID 组合 → 形成"用户偏好画像"，是 PIPL §73(4) 自动化决策范畴的画像。Phase 1 数据量小可以不严抠；Phase 2 公开必须 (a) 提供画像关闭选项；(b) 提供画像逻辑说明。

---

## 单一最大风险标记 (Single Biggest Risk Flag)

> ⚠️ **生成式 AI 服务管理暂行办法 (2023) 项下的"算法 + 安全评估"备案**。
>
> 这是 Cascade 公测的**硬合规闸门**，无法用产品技巧绕开。备案周期 1-3 个月，且 2024-2025 网信办的实务尺度在收紧（多家 大模型公司被点名整改）。
>
> **不做**就公开 = 直接面临**责令暂停服务 + 处 10w-100w 罚款 + 创始人个人记录** 三连。
>
> **必须在 Phase 2 第一周启动**（即 Phase 1 Gate 通过的当日就开始准备材料），不是 Phase 3 末才想起来。
>
> Phase 1 因为不公开，**实务做法**认为可豁免；这个判断必须有律师书面意见，不能仅凭我（非律师 AI）的判断兜底。

---

## 给创始人的 5 句话总结

1. **Phase 1 (10-user trial) 干净安全，只需 2 人天合规活：1 页隐私通知 + adapter 加 3 项过滤 + 邮件兜底导出删除。**
2. **不接 YouTube/TikTok URL = Phase 1 最干净姿态**，硬拦不解释。
3. **doubao 境内、Gemini 境外是合规上最大的资产负债表分裂** — Phase 2 要么换境内 image gen，要么走 PIPL 标准合同。
4. **"24h 不存原视频" + "schema 主动不存作者 PII"** 是 Cascade 的两个合规护城河，**继续保持并在用户协议里写出来作为信任凭证**。
5. **算法/生成式 AI 备案不要拖**——Phase 1 Gate 一过即启动，**不要等到 Phase 2 中期发现已经被 30 个用户用上了再去补**，那时停服整改成本远高于 Phase 1 末就开始走流程。

---

## Document control

| 字段 | 值 |
|---|---|
| 法规截止日 | 2026-05-19（本文档生效日） |
| 假设变更触发重审 | (a) Phase 1 用户数 > 10；(b) 收费上线；(c) 域名公开 ICP 备案；(d) 接 OAuth；(e) 引入未成年人专属赛道；(f) image gen 切回 / 加 境外 provider |
| 下次重审 | Phase 1 Gate 评审日 + 1 周内 |
| 律师咨询建议时点 | Phase 1 W4 末 (10 用户已经在用、Phase 2 计划成型时) |
| 本文档**不是**法律意见 | 是合规自检清单。律师意见在 Phase 2 启动前补 |

---

*Authored by Legal Compliance Checker (NEXUS sprint, Phase 0). 本文档基于公开法规与 2024-2025 实务做法整理；具体执行前请咨询中国数据保护 / 互联网业务律师。*
