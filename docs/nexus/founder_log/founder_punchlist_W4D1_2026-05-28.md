# Founder W4D1 行动清单 — 2026-05-28(开工日)

**Date target**: W4D1 = 2026-05-28(下周一)早 09:00 开始
**Prerequisites**: 全部已就位(协议 / 隐私 / DM 模板 / concierge 脚本 / Doubao key / 工程产品)
**Total time budget**: 5h(对齐 capacity audit §7 PM 推 weekly load 5h/w)
**Goal**: W4D7 收盘前 ≥ 1 个真实 creator 跑完 first-run + 给 3 个反馈点

---

## ⚡ 心法

- **不需要做完所有动作** — 选 §1 + §2 + §3 即可。其他 §4-§6 是可选 boost
- **不要再做 W3 没做完的事** — 那些已迁到 W4 内,不必负罪感
- **每个 ☑️ 后 commit 一下** — 让 probe 看见进度,PM session 才能跟踪
- 卡住任何一步 → 留空 + 写一句"为什么卡" → PM 下次能帮你调整

---

## 1. 09:00-10:00 · 决策签字(2 件)

### 1.1 在 PM_phase0_crisis_2026-05-22.md §5 末尾追加(若不同意 PM 代签 A+C)

打开 `docs/nexus/founder_log/PM_phase0_crisis_2026-05-22.md`,如果你**同意** PM 代签的 A+C(Phase 1 内测立刻起 + P0-A 转公测前阻塞 + 仅 P0-C 5 条委外),**不用动**。

如果你**不同意**,在 §5 末尾追加一行:

```
**FOUNDER OVERRIDE @ 2026-05-28**: <你想选的路径,例如 B(extend Phase 1)/ C(全部外包)/ 自定>
ETA: <你的新 ETA>
```

→ commit:`git commit -m "founder: phase0_crisis §5 override to <X>"`

### 1.2 在 PM_founder_capacity_audit_2026-05-22.md §6 写决策

打开 `docs/nexus/founder_log/PM_founder_capacity_audit_2026-05-22.md`,在 §6 写一行(必填):

```
(a) Stay the course · 每周可投 _____ h · ETA W4D7 出 _____
```
**或**
```
(b) Shrink scope · 每周可投 5h · ETA W4D7 出 1 个真实 creator first-run + 3 反馈点(PM 推荐)
```
**或**
```
(c) Outsource · 预算 ¥_____ · ETA W4D3 起 outsource_log 落 founder_log/
```
**或**
```
(d) Pause + reset · 2026-06-21 出新计划 · engineering 同期继续 W4 路线
```

→ commit:`git commit -m "founder: capacity_audit §6 选 (X)"`

---

## 2. 10:00-12:00 · 招募启动(W4D1 必做)

### 2.1 选 5 位真实候选 creator(35 min)

打开你常用的小红书 / 抖音 / 飞瓜 / 新榜 → 按 niche 找 5 位候选(不必一次找完;首选 1-2 个 niche)。

每个候选**必须满足** `recruitment.md §"选人 4 条标准"`:

1. 30-40 岁女性(看头像 / 朋友圈)
2. 粉丝 1k-50k(太大不缺工具,太小没素材)
3. 最近 7 天 ≥ 1 条更新(活跃)
4. 内容 niche 明确(辅食 / 育儿 / 厨房 之一,**不混**)

把 5 个名单贴到 `docs/nexus/founder_log/candidate_list_W4_2026-05-28.md`(新建文件,格式自由,有 @用户名 + niche + 一条作品 URL 就够)。

### 2.2 给 5 位候选发 DM(40 min,每人 8 min)

用 `docs/nexus/founder_log/recruitment.md §"DM 文案模板"`(已按 3 niche 拆好)。

**纪律**:
- 每条 DM 必须**改 2 个字段**:[名字] + [具体作品标题]
- **不要群发** — 5 条都点点改改发,15 min 不可能完成,这是设计
- 每条 DM 引用她**真实看过的** 1 条作品细节(例如 "你那条 #七夕辅食 我注意到结尾镜头的转场")

每条 DM 发出后,append `recruitment.md §"DM batch · W3 (target 25)"`:

```
- DM 2026-05-28 小红书 @<用户名> niche=baomam_fushi 状态=已发
```

(改 `· W3 (target 25)` 标题为 `· W4 (target 35)`,便于 PM 后续 grep)

### 2.3 commit

```bash
git add docs/nexus/founder_log/candidate_list_W4_2026-05-28.md docs/nexus/founder_log/recruitment.md
git commit -m "founder: W4D1 candidate list + 5 DMs sent"
```

→ `bash scripts/check_progress.sh` 应显示 `Recruit dms=5`,这是 founder lane 4 周以来第一次非 0 数字。**这一步比所有工程价值都大**。

---

## 3. 14:00-15:00 · 小红书 seed 发布(W4D1 必做)

打开 `docs/nexus/founder_log/seed_post_url_2026-05-22.md`。

**最小路径(30 min)**:
1. 拍 / P 1 张封面图(你家厨房 + 手机屏一张爆款截图脸打码 + 准备食材的砧板)
2. 把 caption(下方"📋 Caption 文案速查")复制粘贴到小红书
3. 上传 1 张封面 → 发布
4. **复制小红书帖 URL**(从浏览器或 app 分享按钮拿)
5. 把 URL 贴到 `seed_post_url_2026-05-22.md` 顶部:

```
seed_url: https://www.xiaohongshu.com/discovery/item/<...>
posted_at: 2026-05-28 14:30 Asia/Shanghai
platform: 小红书
```

→ commit:`git commit -m "founder: seed post published"`

→ `bash scripts/check_progress.sh` 应显示 `Marketing seed=YES`。

**禁用词自查**(发布前过 1 分钟):caption 中不能有 ❌ AI / 智能 / 神器 / pipeline / DAG / 节点 / 锚点 / 复刻 / 营养师 / 必爆。当前 caption 干净,如果你改写过过一遍。

---

## 4. 15:00-15:30 · 评估工具 first-look(可选,建议做)

打开 `http://localhost:5173/admin/cost` 看一眼 — 本周 cost 是 0(还没真实 user)。

打开 `http://localhost:5173/admin/events` — 应该能看到你 W3D2 同意协议时的 1 条 `consent_accepted` event。

这两个看板就是你后续观察 creator 的窗口,**今天先认个脸**。

---

## 5. 15:30-16:00 · P0-T 合约测试 ✅ 已 Claude 跑过

PM 在 W3D3 已替你跑过(`backend/tests/test_cascade_contract.py`):
- **41 passed,1 skipped**(skipped 是 `test_phase0_gate_field_completeness_real` — 因为 real_v1 fixture 只有 15/20)
- 这 1 个 skip **不阻塞 Phase 1 内测**,只是等你或外包审稿人补 5 条真实标注后会自动转 PASS

**不需要 W4D1 做**;放在 W4D2-D3 补 5 条 fixture 时一起处理。

---

## 6. (可选)P0-C 5 条委外标注 — W4D2-D3 处理

**今天先列候选**:
- 选 1 位你认识的、做内容 / 写文案 / 视频运营行业熟人(微信问问)
- 让他/她按 `docs/nexus/founder_log/p0-c_real_fixture_labeling_sop.md` 标 5 条新真实 URL
- 预算 ¥200-500 一次性(对方 1-2h 工作量)
- 完成后在 `founder_log/p0-c_outsource_log_2026-05-28.md`(新建)写:对方姓名 + 5 条 URL + 预算实际 + 完成时间

**今天不必启动这件**;只在 §2 DM 名单做完后剩了时间再问。

---

## 7. 17:00 · 收尾 commit + 给 PM 一个信号

```bash
bash scripts/check_progress.sh > /tmp/today_status.txt
cat /tmp/today_status.txt
git add docs/nexus/founder_log/
git commit -m "founder: W4D1 收盘"
```

如果 `Recruit dms=5` + `Marketing seed=YES` 同时出现 → **founder lane 4 周以来第一次正向破冰**,PM 下次 session 会显著调整 W4-W6 路径。

**不必报告 PM**;下次 PM session 会自己从 git log + probe 看到。

---

## 8. 卡住怎么办

任何 §1-§3 卡住:

1. **写一行卡点**到 `founder_log/W4D1_blocker_2026-05-28.md`(新建),格式:

```
卡在: <哪一步>
原因: <一句话>
影响: <我今天还能 / 不能继续到哪里>
```

2. commit 这个文件
3. 继续做下一项(不要追求 §1-§3 全 ✅)

PM 下次 session 看到 blocker 文件会优先处理。

---

## 9. 心理预期管理

- 5 条 DM **不一定有回复** — 平均 24-72h,只有 1-2 条会回。3-5 天后才会有第一个 discovery call。这是正常,**不是失败**。
- Seed 帖**第一天大概率没 1k 阅读** — 第 1 篇就为了"开账号" + 后续 DM 可指过去的"主页"。**不必焦虑数据**。
- 哪怕 §1-§3 全没做完,**只要今晚 17:00 之前发出 1 条 DM + 1 条 seed**,就比 W1/W2/W3 任何一周都好。

---

## 10. 此 punchlist 来源

- §1 from `PM_phase0_crisis_2026-05-22.md §5` + `PM_founder_capacity_audit_2026-05-22.md §6`
- §2 from `recruitment.md §"DM 文案模板"` + `02_growth_plan.md §1.3` + `concierge_onboarding_script_2026-05-23.md §1`
- §3 from `seed_post_url_2026-05-22.md` Caption 文案速查
- §5 from `PM_W4_allocation.md §9` + PM 在 W3D3 已跑测试
- §6 from `PM_phase0_crisis §3` Option C 子集
