# P0-A 算法备案 申报 prep packet

**Date opened**: 2026-05-21
**Owner**: Founder
**Spec source**: `docs/nexus/04_compliance_check.md §"Top 5 must-do before 100-user public launch"` 第 1 项
**Status**: B + C 章节 100% PM 填好(2026-05-22 Claude 更新对齐 Doubao境内 + 法律文档落地);A 章节 4 项扫描件 founder-only;Step 2 实名提交 founder-only。Pending founder 提交(等 受理回执 号)。

---

## 申报口径与豁免说明

10 人内测 + 邀请制可 **实务豁免**(网信办无明确公众门槛定义),但建议**在 Phase 1 期间就启动备案流程**作为合规前置,公测前必须完成。
本文件作为 founder 提交时的材料 packet + 备案号回收点。

---

## 申报渠道

- **主管单位**:中央网信办 + 当地网信办
- **入口**:https://beian.mps.gov.cn(公安网备)+ 网信办区级 / 市级 算法备案系统
- **同时申报**:深度合成服务备案(常和算法备案合并申报)
- **预计周期**:30-90 天审批,但**受理回执 24-72 小时**内出

---

## 申报材料(逐项准备)

### A. 主体材料

- [ ] 营业执照副本扫描件: <FILL path>
- [ ] 法人身份证扫描件: <FILL path>
- [ ] 域名 ICP 备案号: <FILL 如 京ICP备XXX号>
- [ ] 服务器境内托管证明: <FILL e.g. 阿里云/腾讯云控制台截图>

### B. 算法说明书(PM 已预填,founder review + 改署名)

**算法名称**: OpenRHTV 视频改写算法 v1
**算法主体**: OpenRHTV 项目组(以开源/个人项目署名;运营主体:王旭康,身份证号 <FILL 法人身份证号>,地址 <FILL 法人地址>)
**类型**: 生成式人工智能服务(文本)+ 合成类算法(图像生成为可选)

**算法基本原理**:

> 本算法接收用户输入的短视频公开 URL,通过上游分析服务(Toprador,**境内**)提取视频的镜头序列与传播分析数据(viral_analysis: hook / pacing / climax / emotional_arc / replicable_formula 等 8 个维度;scenes: 3-12 个镜头的 dialogue + visual_content)。系统按用户所选 niche(宝妈辅食 / 育儿日常 / 家庭厨房)调用**字节跳动 Doubao(豆包)模型 — 中国境内服务**,通过火山方舟 ARK 接口对内容进行**风格化改写**,保留原视频的可复制结构(replicable_formula 钩子模式 H1-H9),替换为创作者本人的人设、场景、台词。改写产物包含:script_markdown(脚本)、shots(3-5 个镜头,含 dialogue + visual)。
>
> **图像生成为可选**:用户在产品内主动点击"生图"按钮且经二次同意确认后,图像生成请求通过 Apimart 聚合接口处理(可能涉及境外模型,如 OpenAI gpt-image);**用户可选择全程不生图,核心改写功能不依赖境外接口**。
>
> 系统**不自动复制原视频画面或音频**,仅借鉴公开传播规律(钩子模式)。所有改写文本经禁用词过滤(广告法雷区)、营养类目一致性校验、菜名锚点校验、跨境平台 URL 拒绝、未成年人关键词审计。

**应用场景**: 短视频创作者辅助工具。仅限邀请制内测,不对公众开放。

**目标人群**: 18 岁以上中文短视频创作者(母婴 / 厨房 / 育儿 niche)。

**数据来源**:

| 数据 | 来源 | 存储 |
|---|---|---|
| 用户输入 URL | 用户主动粘贴 | 境内 SQLite |
| 视频分析数据 | 上游 Toprador 境内 API | 境内 SQLite(`analyses` 表) |
| 用户偏好 | 用户在产品内选择 niche | 境内 SQLite |
| 改写输出 | **Doubao(豆包)境内模型** 生成(经火山方舟 ARK,境内接口) | 境内 SQLite(`rewrites` 表) |
| 图像生成(可选) | 用户主动触发 + 二次同意后,经 Apimart 聚合(可能涉境外) | 境内 SQLite(`images` 表;原图链接 + 元数据) |
| 训练数据 | **不训练** — 仅 inference;无模型 fine-tuning;不使用用户数据训练任何模型 | n/a |

**数据出境说明**:

- **文本改写主链路 — 全境内不出境**:用户粘贴的 URL、上游分析数据、改写产物在文本环节**全程在中国境内传输与处理**,经 Doubao 境内模型(火山方舟 ARK)生成。**不触发 PIPL §38**。
- **图像生成可选路径 — 用户主动触发 + 二次同意**:仅当用户在产品内主动点击"生图"按钮并经弹窗二次确认后,请求才会经 Apimart 聚合接口发出,Apimart 可能聚合境外模型(如 OpenAI gpt-image)。此操作:
  - **用户事先在邀请页 click-through 同意书 + 二次点击同意**两道确认;符合 PIPL §39 单独同意要求
  - 出境数据**不包含**用户姓名、身份证、IP、设备指纹等直接标识(已经 `_strip_pii` 剥离)
  - 用户可全程拒绝,核心改写功能不受影响
- **fallback 提供方 Gemini**:系统保留 LLM_PROVIDER=gemini 作为 A/B 对比工具与回滚路径,但 Phase 1 **默认 LLM_PROVIDER=doubao**(配置项写入 `.env`),所有 10-人内测用户实际只触达 Doubao 境内服务。如未来切换或新增境外 LLM 主链路,我们将事先通过邮件取得用户单独同意。

### C. 安全自评估报告(PM 已草拟,founder 完善)

**核心风险点 + 缓解措施**:

1. **生成虚假信息风险**: prompt 显式约束"不复制原视频角色 / 不杜撰人物" + 改写产物均为创作者第一人称视角,founder 在 P1-3 fixture signoff 已确认调性。改写产物经 LLM 评审(`backend/src/agent/cascade/eval/judge.py`)进行 kept_formula / realism / ad_risk 三维度审计。
2. **侵权风险**: 用户协议条款 §3.1 显式要求用户保证有权使用所粘贴 URL(见 `docs/legal/user_agreement_v0.md §3`);系统仅借鉴公开传播规律(钩子 H1-H9),非画面复制。
3. **未成年人保护**: 接收侧加未成年人关键词检测(中文 7 项 + 英文 7 项,见 `backend/src/agent/cascade/minor_audit.py`),触发后产生 `W14_MINOR_SUBJECT_DETECTED` 警告并写入审计日志(INFO 级,Phase 1 不阻断);Phase 2 接入阿里云内容安全 API 升级为拦截。
4. **数据出境合规**: 文本改写主链路通过 Doubao 境内模型完成,**不触发 PIPL §38**。可选图像生成依赖用户主动触发 + 二次同意,符合 PIPL §39 单独同意要求。10-人内测自然人数量远低于 10-100w 标准合同门槛;Phase 2 公测前如仍涉境外接口,将启动标准合同备案路径。
5. **内容安全过滤**: 改写产物经禁用词列表过滤(无 AI / 智能 / 神器 / 营养师 / 米其林 / 权威 / 功效宣称等);广告法雷区已避开。
6. **跨境平台拦截**: `STRICT_CROSS_BORDER_REJECT=1` 默认开启,境外平台 URL(YouTube / TikTok / Instagram / youtu.be 等)在 adapter 入口直接 `S9_CROSS_BORDER_BLOCKED` 拒绝,从源头消除"分析境外平台公开内容"导致的跨境数据 + 著作权双重风险。
7. **PII 剥离**: 所有上游可能返回的作者 UID / 头像 URL / 昵称 / IP / 电话等字段在 adapter 落库前由 `_strip_pii` 自动剥离(`backend/src/agent/cascade/adapter.py:_KNOWN_PII_KEYS`)。
8. **用户权利**: 完整的查阅 / 复制 / 删除 / 更正 / 撤回同意 / 转移 权利在 `docs/legal/privacy_v0.md §7` 落地,删除请求承诺 24 小时响应,查阅请求承诺 15 天响应。

**内容安全机制**:

- 关键词过滤库:`backend/src/agent/cascade/rewrite.py FORBIDDEN_TERMS`
- 钩子模式正则约束:`backend/src/agent/cascade/hook_taxonomy.py`
- 营养类目一致性:`hook_taxonomy.nutrient_category_consistency`(辅食 niche 专属)
- 菜名锚点强制:`hook_taxonomy.dish_anchor_present`(家庭厨房 niche 专属)
- 反面钩子拒绝:`hook_taxonomy.negative_hook_absence`(每 niche 不同的反面 H)
- 跨境平台 hard block:`backend/src/agent/cascade/adapter.py` + `S9_CROSS_BORDER_BLOCKED` FailureCode
- 未成年人审计:`backend/src/agent/cascade/minor_audit.py` + `W14_MINOR_SUBJECT_DETECTED` WarningCode
- 全部经 `backend/tests/test_rewrite.py` 23 个 case + `test_rewrite_llm.py` 14 个 case + `test_cascade_contract.py` 跨境与未成年人 4 个 case 覆盖

**用户协议与隐私政策**: 已落地 `docs/legal/user_agreement_v0.md`(11 节 + 法律附)+ `docs/legal/privacy_v0.md`(12 节 + 法律附),Phase 1 内测期间(2026-05-22 至 2026-07-02)适用;通过邀请页 click-through 取得用户同意(技术实现 `ConsentGate` 组件 + `consent_accepted` 事件审计日志)。

**举报机制**: 邀请页公示 founder 邮箱 **`xukang.wang@gmail.com`**;15 天内响应承诺(导出/查阅类);删除请求 24 小时内完成;数据泄漏 72 小时内通知用户。

**禁用词与负面 keyword 列表**: 见 `docs/nexus/02_brand_guardrails.md` term table + `backend/src/agent/cascade/rewrite.py FORBIDDEN_TERMS`。

---

## 提交流程(founder 执行)

### Step 1(W3D1 上午,~30min)

- 整理 A 章节扫描件 + 准备好 B 章节产品截图
- 复核 B/C 章节(签名前最后一遍)

### Step 2(W3D2 上午,~1.5h,**只能 founder 实名进系统**)

1. 浏览器开 北京 网信办 算法备案入口(具体 URL: <FILL 进系统后回填>)
2. 法人实名认证(数字证书 / 法人扫脸)
3. 上传 A / B / C 三章节材料
4. 点击 "提交申报"
5. 拿 **受理回执号**(应该 24-72h 内出邮件 / 站内信)

### Step 3(回执到手后,回填本文件)

- [ ] 已实名提交申报(日期: <FILL>)
- 受理回执号: `<FILL e.g. 京网信备2026000XXX号>`
- 受理日期: <FILL YYYY-MM-DD>
- 审批预计完成日期: <FILL 通常 30-90 天>

---

## 完成判定

- `bash scripts/check_progress.sh` → `Phase0 algo_filing=1`(因为 `algo_filing_<date>.md` 存在)
- 本文件包含真实的受理回执号(非占位)

**重要**: 受理回执号拿到 = `algo_filing` 计 1,**不需要等审批完成**。审批中阶段可以正常运行 Phase 1。

---

## PM 注

**2026-05-22 W3D1 update (post-legal-docs + post-Doubao decision)**:

- **B 章节** 算法说明书已 100% 重写对齐 Doubao 境内主链路 + 图像生成可选独立同意。仅留法人身份证号 / 地址两个空格(founder 填)
- **C 章节** 安全自评估已扩为 8 项风险点(原 5 项 + 跨境拦截 + PII 剥离 + 用户权利),全部对齐已落地代码与法律文档
- **A 章节**仍是 founder-only 物理材料(扫描件 + 截图 + ICP 号),~30min 收集
- **Step 2 实名提交**仍只能 founder 在网信办系统操作

**Founder 还需要做的 4 件事**(2026-05-22 W3D1 上午):

1. **A 章节扫描件**(~30min):营业执照 / 身份证 / 服务器境内托管证明截图 — 截图放 `founder_log/algo_filing_attachments/` 子目录或本地文件路径填进去
2. **A 章节 ICP 备案号**:如已备案,填备案号;如未备案,在 A 章节加一行说明"Phase 1 内测期间不上公网商业服务;Phase 2 公测前完成 ICP 备案后补充"。10 人内测 + 邀请制可暂用此说法
3. **B 章节空格**:法人身份证号 + 法人地址(隐私信息,只在 algo filing 提交时使用,不进 git)— **强烈建议:不要把身份证号 commit 进 git;用占位符在 git 版本里,提交备案前临时填,提交后清空**
4. **Step 2 实名提交**(W3D2 上午,~1.5h):打开 https://beian.mps.gov.cn 或北京网信办算法备案入口 → 法人扫脸 → 上传 ABC → 拿受理回执号 → 回填本文件 Step 3

**实务豁免提示**: 10-人内测 + 邀请制可主张实务豁免(网信办无明确公众门槛定义),但**仍建议在 Phase 1 期间就启动备案**作为 Phase 2 公测的合规前置。受理回执号通常 24-72h 内出,有了受理回执号 = `algo_filing` 真闭环,即可正常运行 Phase 1。

**身份证号安全提示**: 法人身份证号属于 PIPL §28 敏感个人信息。**不要 commit 进 git**。建议:
- git 跟踪的版本里 B 章节身份证号保留 `<FILL 法人身份证号>` 占位符
- 提交备案时:在本地另起一个私有副本(`.local.md` 后缀,加 `.gitignore`),临时填上身份证号 → 上传备案系统 → 上传完毕后删除该本地副本
- 此操作不影响 algo_filing probe(probe 检测受理回执号,不检测身份证号)
