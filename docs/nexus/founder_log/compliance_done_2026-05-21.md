# P0-R compliance checklist — Top 5 must-do before 10-user trial

**Date opened**: 2026-05-21
**Owner**: Founder
**Spec source**: `docs/nexus/04_compliance_check.md §"Top 5 must-do before 10-user trial"`
**Status**: in progress — #1 + #5 docs done 2026-05-22 by Claude (founder review pending); #2/#3/#4 in flight by Codex per `handoff/codex_backend_P3-R1.md`

Each item is intentionally small (≤ 0.5 day). Total budget ≤ 2 days.
**Check the box AND drop evidence/path** beside each. Empty boxes block Phase 0 closure.

---

## 1. 用户协议 + 隐私政策 v0(0.5 day)

- [x] **Done** (2026-05-22 — Claude drafted, awaiting founder review)

**Evidence**:

- 文件路径: `docs/legal/user_agreement_v0.md` + `docs/legal/privacy_v0.md`
- 邀请页 click-through 同意机制: **partial** — 协议措辞已在 §11 / §10 显式定义"勾选 + 进入产品 = 接受;同意时间存入 localStorage + 服务端审计日志"。Landing 页 checkbox UI 需要 frontend 实施(**P3-R3 frontend ticket — 由 Claude 处理;DM 发出前必须 ready**)
- 法律依据已在协议中标注: PIPL §13 / §17 / §38 / §39 / §44-§49 + 民法典 §1032-1039 + 生成式 AI 暂行办法 + 未成年人保护法 等(完整列表在两份文档的"附:法律依据引用一览")

**8 项要点 checklist**(协议正文里逐项要 cover):

- [x] (a) 试用性质 / 不公开 / 无费用 — `user_agreement_v0.md §1.2`
- [x] (b) 收集 URL / 改写文本 / 偏好,目的=改善产品 + 个性化分析 — `privacy_v0.md §2 + §3`
- [x] (c) 数据存于境内 SQLite — `privacy_v0.md §4.1`
- [x] (d) 随时可发邮件要求删除 — `privacy_v0.md §7.2` + `user_agreement_v0.md §5.2`
- [x] (e) ~~图像生成调用 Gemini = 境外~~ → 已升级为:LLM 改写走 Doubao **境内不出境**(`privacy_v0.md §4.2`);图像生成走 Apimart 聚合可能涉境外,**用户主动点"生图"才触发 + 二次确认**(`privacy_v0.md §4.3`)— **P3-R2 切换 Doubao 后此条更干净**
- [x] (f) 借鉴爆款公式、非复制原视频 — `user_agreement_v0.md §2.3`
- [x] (g) 用户保证有权使用所粘贴 URL — `user_agreement_v0.md §3.1`
- [x] 标注 "v0 试用版,公测前重写" — 两份文档头部 + 末尾"v0 → 公测重写承诺"章节

---

## 2. `_strip_pii` 加 IP 地址 + 作者昵称字段(0.25 day)

- [ ] **Done**

**Implementation evidence**:

- 修改文件: `backend/src/agent/cascade/adapter.py`(`_KNOWN_PII_KEYS` 集合)
- 新增字段: `author_nickname`, `author_name`, `ip_address`, `user_ip`
- 测试覆盖: <FILL test name in `backend/tests/test_cascade_contract.py`>

**Status**: 这是工程任务,但归到 P0-R 因为它是合规闸门的一部分。**可委派 Codex** 完成,founder 只需 review + 打勾。

PM 提议:把这条 fork 成 `codex_backend_P3-R1.md` 让 Codex 处理。Founder 决定。

---

## 3. W9_CROSS_BORDER_SOURCE hard block 开关(0.25 day)

- [ ] **Done**

**Implementation evidence**:

- 配置项: `backend/src/agent/config.py` 加 `STRICT_CROSS_BORDER_REJECT: bool = True`
- 拒绝路径: adapter 在 `W9_CROSS_BORDER_SOURCE` 触发时,如开关 True,raise `HardFailure(S8_UPSTREAM_REFUSED, "cross_border_blocked")`
- 测试: <FILL test name>

**Status**: 工程任务,**可委派 Codex**(同 #2)。

---

## 4. 未成年人关键词 audit + 日志告警(0.5 day)

- [ ] **Done**

**Implementation evidence**:

- 修改文件: `backend/src/agent/cascade/adapter.py` 或新建 `cascade/minor_audit.py`
- 关键词列表: `宝宝 / 小孩 / 婴儿 / 幼儿 / child / baby / kid / 小朋友`
- 触发时: warnings 加 `W_MINOR_SUBJECT_DETECTED`(INFO 级),写审计日志,**不阻断 Phase 1**
- 测试: <FILL test name>

**Status**: 工程任务,**可委派 Codex**。Founder 只需对关键词列表点头。

---

## 5. 用户协议中明确"24h 删除" + 数据导出/删除联系渠道(0.5 day)

- [x] **Done** (2026-05-22 — covered in same协议落地)

**Evidence**(协议正文要写明):

- [x] 用户可发邮件到 `xukang.wang@gmail.com` 请求(a) 导出全部数据 / (b) 删除账号 + 所有 run — `privacy_v0.md §7.1-§7.2` + `user_agreement_v0.md §5.1-§5.2`
- [x] 15 天内响应承诺(导出查阅);**删除请求承诺 24 小时**(更严) — `privacy_v0.md §7.2`
- [x] 法律依据:PIPL §44-§47 — `privacy_v0.md §7` 标题正文显式引用

**Status**: 试用期手动处理(10 个人邮件兜底);不需要 API 自动化。

---

## Founder 行动指引

5 项中 **2 项纯文档**(#1, #5)只能 founder 写(法律署名责任),**3 项工程**(#2, #3, #4)可委派 Codex。

**最快路径(2 天内 close)**:
- W3D1 上午 1.5h:founder 写 user_agreement_v0.md + privacy_v0.md(可以抄 飞书 / GitHub 公开模板)
- W3D1 下午 0.5h:founder 看 Codex 提的 PR(#2 + #3 + #4 一个 batch),点头打勾
- W3D2 上午 0.5h:把所有 ticks 打上,commit 此文件

**完成判定**:

- `bash scripts/check_progress.sh` 显示 `compliance=1`(因为 `compliance_done_<date>.md` 存在)
- 此文件所有 `- [ ]` 变 `- [x]`
- 5 个 evidence 字段全填完
