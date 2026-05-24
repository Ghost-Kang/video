# PM-ack kit — W4D1 (2026-05-28 Mon) 启动日预制

**Purpose**: founder W4D1 早盘 3 个 ping 命中后,PM(下一个 session)≤60 秒响应的预制脚本。任何 PM session 进来读本文件 + `founder_punchlist_W4D1_2026-05-28.md` 即可立即 dispatch,不必现场重设计 prompt。
**Source of truth**: `founder_punchlist_W4D1_2026-05-28.md §2-§4`(本 kit 是把 punchlist 的 invocation 部分提前烘焙)
**Dry-run 基线**: `dm_dryrun_W3D4_2026-05-24.md` 已验证 Xiaohongshu Specialist 单 invoke 89s,质量达 W4D1 直接发布门槛

---

## 1. Founder ping A — DM batch(预计 W4D1 09:30-09:35)

### Founder 触发原文(punchlist §2.2)

> PM,这是今天 5 个 baomam_fushi 名单,改 DM 文案。剩 <X> 个名额。
> ```
> @<用户名> | <作品 URL> | <1 句作品细节>
> @<用户名> | <作品 URL> | <1 句作品细节>
> ... 共 5 行
> ```

### PM 立即响应(≤30s)

> 收到。invoke Xiaohongshu Specialist,剩 <X> 名额参数化进文案,3 min 给你 5 条 DM。dry-run 基线已验过,review 1-2 条即可发。

### PM 立即 Agent invoke(同一 turn)

`Agent(subagent_type="Xiaohongshu Specialist", description="W4D1 DM batch baomam_fushi", prompt=<下方 prompt>)`

**Prompt 模板**(把 `<X>` + 5 个 candidate 行 + 今日日期插入):

```
你是 Xiaohongshu Specialist。给 Cascade Phase 1 招募的 5 个真实小红书宝妈辅食 niche creator 写 DM 文案,
要求与 2026-05-24 W3D4 dry-run 一致的质量基线(产物 `dm_dryrun_W3D4_2026-05-24.md` 已 founder review 通过)。

5 个真实 candidate(founder 今晨亲手 sourcing,非 MOCK):
<5 行 @用户名 | 作品 URL | 1 句作品细节>

剩余名额:<X>(必须在每条 DM 末尾真实出现,不要写"还剩几个名额"这种模糊语)
今日日期:2026-05-28

每条 DM 严格遵循:
1. 开头直接引述该作品的 1 个**具体动作/细节**(从 candidate 行的"作品细节"扩,不准空泛"很喜欢你的内容")
2. 一句话点破"为什么这个细节比其他号好"(差异化定位,展示你看懂了)
3. 自然过渡到 Cascade 价值主张:6 周一对一免费陪跑、把别人爆的选题拆成她自己的版本、不是搬运
4. 名额 + CTA:"剩 <X> 个名额,这周方便 30 分钟聊一聊吗?"
5. 字数 170-200 字,口语化、平等口吻、不要"亲""宝"开头

输出格式:5 条 DM 各自标号,每条带 candidate @用户名 标题 + DM 正文。
禁用词扫一遍(母婴 niche 合规底线):不出现"治疗""根治""药效""医生推荐""第一""最好",
不暗示与药品/医疗器械替代关系。任何禁用词替换为同义合规说法。
```

### PM 写回(founder review 后 / 同步发布后)

- `recruitment.md` append 5 行 `- DM | <用户名> | <date> | sent | <剩余名额>`
- commit message:`founder: W4D1 DM batch sent — <X> candidates via Xiaohongshu Specialist`

---

## 2. Founder ping B — seed 帖(预计 W4D1 09:30-09:45)

### Founder 触发原文(punchlist §3)

> PM,启 Content-Seed-Agent 起 baomam_fushi seed 帖 9 图 brief + caption

### PM 立即响应(≤30s)

> 收到。并行 invoke Xiaohongshu Specialist + Content Creator,5 min 给你 caption(500 字内,禁用词扫过)+ 9 图拍摄 brief,落 `founder_log/xhs_post_2026-05-28.md`。你拍封面 1 张,5 min 内发出。

### PM 并行 Agent invoke(同一 turn,2 个 agents 并行)

**Agent 1** `Xiaohongshu Specialist`:

```
你是 Xiaohongshu Specialist。为 Cascade Phase 1 母婴辅食 niche 招募写小红书 seed 帖文案。
目标:吸引 30-40 岁宝妈辅食 creator 看到→DM 私聊"我也想入选"。
不是直发广告,是真实问句帖:"我个人在 1v1 陪跑 10 位辅食创作者,本周还剩 <X> 个名额,你符合不?"

要求:
- 标题 ≤ 20 字,带"宝妈辅食""陪跑""免费"任意 2 个关键词
- 正文 ≤ 500 字,口语化、平等口吻
- 自然交代选人标准:30-40 岁女性、粉丝 1k-50k、近 7 天有更新、niche 纯辅食(改写 recruitment.md §"选人 4 条标准")
- 价值主张:6 周一对一陪跑、把别人爆的选题拆成你自己的版本、不收费、本周剩 <X> 个名额
- 结尾 CTA:"觉得自己符合的私我",留出 founder 在评论区互动的余地
- 禁用词:不出现"治疗""根治""药效""医生推荐""第一""最好",不暗示药品/医疗器械
- 不带个人微信号、不带二维码(平台规则 + 后续 W5 私域引流另启)

输出格式:
## 标题
<≤ 20 字>
## 正文
<≤ 500 字>
## 话题 tag
<3-5 个,带 #>
```

**Agent 2** `Content Creator`:

```
你是 Content Creator。为上面 Xiaohongshu Specialist 写的 seed 帖配 9 图拍摄 brief。
约束:
- founder 自己用手机拍,不用买道具,不用棚拍
- 场景 = 厨房 + 食材(已在桌面)+ 手机屏幕展示别人爆款(参考素材)
- 每张图描述:构图(1 句)+ 道具清单(列点)+ 灯光提示(自然光时段 / 角度)+ 拍摄技巧(防抖 / 距离 / 角度)
- 9 张 = 1 张封面 + 8 张正文图,封面要"眼球抓得住"

输出格式:
## 封面图
<构图 / 道具 / 灯光 / 技巧>
## 图 2-9
<编号 + 同上格式>
## Canva / 美图秀秀 模板建议
<2-3 个具体模板名 + 简单说明为什么选>
```

### PM 写回

- 两 agent 输出合并 → `docs/nexus/founder_log/xhs_post_2026-05-28.md`
- founder 30s review → 拍封面 → 发出 → URL 贴 `seed_post_url_2026-05-28.md`(覆盖任何旧 W3D2 模板)
- commit:`founder: W4D1 seed post published`
- probe 验:`bash scripts/check_progress.sh` 出 `Marketing seed=YES`

---

## 3. Founder ping C — 晚 18:00 check(预计 W4D1 18:00)

### Founder 触发原文(punchlist §8)

> (founder 自己跑 `bash scripts/check_progress.sh` 看一眼,不一定 ping PM)

### PM 主动 daily 18:00 routine(若 founder 0 回复 0 DM 反馈)

- PM 跑 `bash scripts/check_progress.sh` → 读 `Recruit dms=` 数字
- 若 dms 已涨 ≥ 5(即 §1 batch 已发出)且当日 0 收到 creator 回复:
  - PM 在 chat 主动说:"W4D1 收盘:5 DM 已发,0 回复(预期,小红书 niche 平均回复率 5-15%,5-10 条拿 1 回复)。明日 09:00 同节奏。无 founder action。"
- 若 dms = 0(即 founder Monday 早盘没真的发):
  - PM ping:"W4D1 18:00 — `Recruit dms=0`。是 sourcing 卡住,还是 review/发布卡住?给我一句话原因,我现场调对应 agent 拆 unblock。"

### Daily 18:00 routine 自动化(W4D2-W4D7 重复)

| Trigger | PM 代调 agent | 产物 |
|---|---|---|
| 收到 creator DM 回复 | `Discovery Coach` + `Feedback Synthesizer` | `dm_qa_<creator_id>.md` + `interview_logged` event |
| 当日 18:00 若 0 新回复 | `Xiaohongshu Specialist` | 给 founder 拉 5 条新 DM 候选(待明日 sourcing) |
| 任何 creator 答应 first-run | (founder 亲调)`Cascade Concierge` | 1h 陪跑材料(空表 + 3 反馈逐字) |
| 改写 → publish_pack 前 | `Healthcare Marketing Compliance` | 母婴合规审 + `compliance_audit` event |

---

## 4. Override / 紧急退路

任何 agent 产出质量差(founder review 后说"不行"):
- founder chat 说"PM,刚才 X agent 输出不行,因为 <一句>"
- PM 立即重 invoke 同 agent,把 founder 那句直接拼到 prompt 末尾作为"修正约束"
- 仍不达标 → PM 切到 `catalog.md` 找替补(例如 Xiaohongshu Specialist 退到 Content Creator + Sales Outreach 组合)

任何 founder 自己卡 ≥ 5 min:
- 不会发小红书 → PM 调 `Content Creator` 给 step-by-step 截图
- 拍封面拍不出来 → PM 调 `Content Creator` 给 5 个 phone-friendly 拍摄角度

---

## 5. 本 kit 的 commit 与维护

- W4D1 当日:不动本 kit。次日(W4D2)如果发现某段 prompt 实际表现 ≠ dry-run 预期,append `## §X 实战修正` 一节,记录改了什么、为什么
- W5D1 W4 周报后:整段重审,确认是否升级为 Phase 2 模板 OR 替换 agent

---

## 6. 来源 cross-link

- `founder_punchlist_W4D1_2026-05-28.md §2-§4`(本 kit 是其执行层的预烘焙)
- `dm_dryrun_W3D4_2026-05-24.md`(DM agent 质量基线)
- `ai_digital_employee_inventory_2026-05-23.md §1.5`(dispatch playbook)
- `concierge_onboarding_script_2026-05-23.md §3`(first-run 触发,W4D5+ 才用,本 kit 不展开)
- `recruitment.md`(候选标准 + DM 追加位置)
