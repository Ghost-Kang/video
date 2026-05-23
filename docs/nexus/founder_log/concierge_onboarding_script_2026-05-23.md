# Concierge onboarding 完整脚本 — first-call + first-run

**Date**: 2026-05-23 W3D3 by Claude as PM validation prep
**Status**: ready · founder copy-paste 直接用
**Purpose**: 桥接 DM 已回复 → discovery call → 真实 creator 第一次跑通改写流水线之间的全部交互。Founder 不需要 from scratch。
**Per `PM_risk_audit_2026-05-23.md §3.3`**: 工程线 idle 时把 Claude 时间投在这种 founder-lane 桥接物料,比再 ship 一个工程票更有价值。
**Related**: `recruitment.md`(DM 模板)· `05_launch_package.md §5`(Phase 1 招募手册)· `02_growth_plan.md §1.3`(选人标准)

---

## 0. 时间轴(从 DM 发出到第一次反馈,理想 ≤ 7 天)

```
T+0d (今天)   founder 发 DM
T+1d-3d       creator 回复"愿意聊"
T+3d-5d       Discovery call (30 min)
T+5d-7d       Creator 第一次跑改写(first run)
T+7d-10d      Founder 收第一次反馈 — Phase 1 真正 unblock
```

每一步都有可能 churn(creator 不回 / 答应了不来 / 跑一半放弃);**concierge 模式 = founder 1-on-1 推着走,不依赖自动化**。

---

## 1. DM 回复后 — booking discovery call(收到回复 3h 内)

### 1.1 情况判断

读 creator 第一条回复,分 3 类:

**A. 直接答应** ("好啊,什么时候?")
→ 走 §1.2 booking 模板

**B. 谨慎好奇** ("是免费的吗?" / "这是什么?" / "你们公司是?")
→ 走 §1.3 信任回应模板

**C. 婉拒** ("最近没空" / "不需要")
→ 走 §1.4 礼貌退出 + 保留通道

### 1.2 booking 模板(回应 A)

> 太好了。我想请你 30 分钟聊一下,不是产品演示 — 我主要想听你目前每周怎么选题、卡在哪、什么帮你最有用。
>
> 我可以这周四 / 五的下午,或者下周一上午。微信视频 / 飞书都可以。你方便哪个时段?
>
> (聊完如果你觉得对路,我请你免费试用 6 周;觉得不对路也没关系 — 30 分钟当帮我做用户调研,我请你吃一杯星巴克。)

**关键设计**:
- "不是产品演示" — 降警惕,creator 经常以为是销售 call
- "我主要想听你目前…卡在哪" — 把焦点放在 creator 自己,显得不像 pitch
- "30 分钟当用户调研,我请杯咖啡" — 即使不试用也有回报,降拒绝率

### 1.3 信任回应模板(回应 B)

> [其中是问"什么产品" / "什么公司":]
>
> 是我自己做的,还没正式上线。叫 Cascade — 简单说就是帮短视频创作者把别人的爆款拆开看清"为什么火",再帮你换成你自己人设的版本。我本来是给自己用,后来发现身边几位做内容的朋友也想要,就想正式做出来。
>
> 现在 10 个名额闭测,全免费,我个人陪你做第一条。你不需要做决定,先聊 30 分钟看一下你目前的工作流,我看能不能帮上忙。
>
> [其中是问"免费多久":]
>
> 6 周全免费。6 周后我会问你愿不愿意继续用、值多少钱 — 这是用户调研的一部分,不是隐藏收费。
>
> [其中是问"为什么找我":]
>
> 我刷到你的 [作品标题] 后,觉得你的内容是我们目标用户画像 — [一句具体观察,例如 "你的辅食内容有很扎实的食材逻辑,但用爆款拆解的方法可以让你更省时间"]。所以专门找你。

**关键设计**:
- "我自己做的" + "本来是给自己用" — 个人色彩降警惕
- 主动揭"6 周后会问值多少钱" — 反向坦诚,反而降不信任
- "为什么找我" 答里必须有 **一句具体作品观察** — 区别于群发,这是 trust trigger

### 1.4 礼貌退出 + 保留通道(回应 C)

> 完全理解。如果之后你那边有空闲、或者觉得想看一下,随时回我这条消息,1 天内回。
>
> 顺便:如果你身边有同行 [niche] 朋友可能感兴趣,引荐一下我也很感激 — 同样 10 人闭测,免费 6 周。

**关键设计**:
- 不解释 / 不说服 — creator 已经表明态度,继续 push 会反向降分
- "1 天内回" — 留通道但不勉强
- 引荐请求 — 转化率低但成本 0,值得问一次

---

## 2. Discovery call 脚本(30 分钟,1 对 1)

> **⚠️ Shrink-mode 路径**(默认,per `PM_founder_capacity_audit §6` PM 代签 (b)+(c)):
> **跳过本节**。改用 §1 DM 模板里追问 + 文字 Q&A 自助调研。下面这 5 个倾听问题(§2.4)用 DM 文字版逐个问,creator 文字回答 → founder 把回答 append 到 `recruitment.md` 对应 creator 行下。
>
> **保留本节的情况**:creator **主动**说"想视频聊一下" / "电话方便吗"时,才约 30 min call;此时按本 §2 全文走。
>
> 理由:founder weekly load 5h/w 不支持 N×30min 视频 call 节奏;DM 文字 Q&A 在 Phase 1 shrink-scope 体量(3 人 cohort)下信息密度足够。本质性反馈仍在 §3 first-run together(1 小时,保留)。

### 2.1 准备(call 前 10 min,founder 一定要做)

- [ ] 重新过一遍 creator 最近 3 条作品 — 记下 hook 是什么、有没有用 H1-H9 中的某个
- [ ] 看一眼 creator 的粉丝数 / 平均互动数 / 发布频率 — 判断她处在 "刚起步" / "瓶颈期" / "稳定输出"
- [ ] 准备 1 张白纸 + 笔(用纸记 > 用电脑;不分心 + creator 看到会觉得你认真)
- [ ] 关掉其他 app 通知

### 2.2 开场(2 min)

> 嗨 [名字],今天 30 分钟,我大概分这样:前 5 分钟我快速说我是谁、为什么做这个,然后 20 分钟主要听你 — 你现在的工作流、哪里最难、最近一周哪条让你最骄傲哪条让你最郁闷。最后 5 分钟我说一下我能怎么帮你,你不需要现场做决定。
>
> 这中间我会**用纸记**,不录音可以吗?

**关键设计**:
- 时间分配预告 — 让 creator 知道大头在她
- "不录音可以吗" — 给信任感,顺便 creator 大概率说 "录音也行" → founder 还是用纸,纸更让人放松

### 2.3 Founder 自介(5 min)

简版,**不要超过 5 分钟**:

> 我是 [名字],之前 [一句相关背景,例如 "做了 X 年内容/产品/AI 工程"]。
>
> 做 Cascade 是因为我自己也做过短视频 — 你应该懂那种刷到一条 5 万赞、想抄但又怕被骂搬运、想原创但又怕选题不对的纠结。我做了一个东西帮自己解决:把别人爆款的"为什么火"拆开,然后帮你换成你自己人设的版本。
>
> 现在 10 个人闭测,所有人我都个人陪着跑 — 第一条视频我陪你一起做,你看效果再决定要不要继续。

### 2.4 倾听问题(18 min,核心)

**5 个问题,按顺序问,问完一个等 creator 回答完再问下一个**(不要打断):

1. **现状基线** (3 min)
   > 你现在一周发几条?每条大概花多久?

2. **选题痛点** (4 min)
   > 你怎么决定下一条拍什么?
   >
   > [后续 prompt 如果她答得太短:]
   > 比如最近一周你拍了 X 条,你能讲一下其中最难定的那条是怎么定下来的吗?

3. **改写痛点** (4 min)
   > 假如你刷到一条爆款,你想"哇这个我也能拍",从看到爆款到你真的发出自己的版本,中间一般几步?哪一步最卡你?

4. **价值统计陈述检验** (4 min)
   > 假如有这么个工具,你刷到一条爆款 → 它告诉你"它为什么火,有哪些可复用元素" → 然后帮你改成你自己人设版本 → 你自己看哪里要改哪里保留,改完直接拿去发。这个对你来说**会不会**让你每周多发 1-2 条?
   >
   > (听 creator 回答的具体程度 — 越具体例如 "我现在 3 条,如果到 5 条…" 越是真实价值;说"嗯应该会"等模糊回答记为 weak signal)

5. **付费意愿测试** (3 min)
   > 假如这个工具 6 周免费试用之后,觉得对你有用想继续用,**你愿意付 39 元 / 月**继续用吗?(不是逼你答应,我想知道你心里的真实 number。)
   >
   > [Listen for: "39 我觉得 OK" 强信号 / "可能要看效果" 弱信号 / "免费我才用" 反信号]

### 2.5 演示(5 min,可选)

如果 creator 在 §2.4 表现出兴趣信号 ≥ 3 个,founder 用屏幕共享演示 30s:

- 打开 `https://localhost:5173/`(或 staging URL)
- 粘一条 niche 内的真实 URL
- 跑分析 → 改写 → 看锚点 sidebar
- 不要完整跑完;只让 creator 看 "**它能从这条爆款拆出 hook 和分镜**" 这一步

如果 §2.4 信号弱 ≤ 1,**不演示**;直接进 §2.6。

### 2.6 收尾 + commit ask(5 min)

**如果 §2.4 信号强(≥ 3 个)**:
> 我想邀请你加入 10 人闭测。具体是这样:这周内我们约一次 1 小时的"陪跑",你拍一条真视频(从你的素材选一条最近想拍的),我现场陪你跑完整个流程。结束你给我 3 个反馈点 — 你觉得帮上了什么、没帮上什么、什么地方让你不爽。
>
> 这一条免费、产出归你 100%、发不发都可以。你愿意吗?

**如果 §2.4 信号弱**:
> 谢谢你今天的时间,真的对我帮助很大。我可能这个版本还不太对你的场景,先不浪费你时间。我用你今天讲的去打磨,有合适版本再回来找你。
>
> [然后塞 "如果你身边有同行可能感兴趣,引荐一下" — 同 §1.4]

### 2.7 Call 结束 5 min 内 founder 必做

记一个 `interview_logged` event(per `events.py` 要求):

```bash
curl -X POST http://localhost:8765/api/events \
  -H 'Content-Type: application/json' \
  -d '{
    "event_name": "interview_logged",
    "user_id": "creator_<short_id>",
    "payload": {
      "value_statement_match": true,
      "would_pay_39": true,
      "notes_url": "<飞书或 notion 笔记 URL>",
      "niche": "baomam_fushi"
    }
  }'
```

`value_statement_match` + `would_pay_39` 按 §2.4 信号填 true/false。
`notes_url` 必须填,后续 PM 要看的就这个。

也 append `recruitment.md`:

```
- CALL 2026-05-23 @creator_xxx 30min 主要痛点=选题没思路 / 评价=对工具兴趣点是"省时间不是出爆款"
```

---

## 3. First-run together 脚本(creator 答应 → 1 小时陪跑)

### 3.1 准备(call 前一天 founder 做)

- [ ] 与 creator 约好准确时间(给两个时段让她选)
- [ ] 让 creator 准备 1 条她**最近想拍但还没拍**的爆款 URL (Douyin / 小红书 都可)
- [ ] 把 backend 起好,确认 `bash scripts/check_progress.sh` 正常,Doubao key + model 可用
- [ ] 准备好 admin dashboard:打开 `/admin/cost` 看本次预估 cost(发现接近 ¥1 阈值时主动停)
- [ ] 准备 1 张表格(纸或飞书),分 5 列:**[环节] [她做了什么] [她说了什么] [她卡了多久] [她的情绪]**

### 3.2 开场(5 min)

> 今天 1 小时我会陪你跑一遍。具体是:
> - 你粘一条你想拍的爆款 URL
> - 系统帮你分析它为什么火
> - 然后帮你改成你自己的版本
> - 你看输出,我们一起判断要不要改
>
> 中间任何时刻你觉得别扭、看不懂、不顺,**马上说出来**,我用笔记录 — 这就是我今天要的反馈。
>
> 准备好的 URL 给我?

### 3.3 步骤(50 min,founder 控速)

| 阶段 | 时长 | 她做 | 你做 | 你记 |
|---|---|---|---|---|
| **粘 URL** | 2 min | 粘到 chat panel | 不干预 | 她有没有迟疑找 URL 的位置 |
| **看分析输出** | 5 min | 读 analysis_returned 结果 | 解释字段:scenes / warnings / hook_pattern_id | "她看到 hook_pattern_id=H1+H2 会问什么是 H1 吗?" |
| **选 niche** | 2 min | 在 niche dropdown 选 | 不干预 | 她有没有问"我能不能填我自己的 niche" |
| **改写** | 8 min(含 LLM 等待)| 等 + 读改写产物 | 等 LLM 调用回来;监控 cost(/admin/cost 这时候应该亮红/黄)| LLM 等待时她是 idle 还是 fidget,情绪如何 |
| **读 shots 改写产物** | 10 min | 读 script_markdown + shots[] | **关键!** 让她念出第一句 — 听她真实反应("这听起来像我吗" / "这词我不会说") | 她对每一 shot 的具体反应 |
| **看锚点 sidebar** | 5 min | 看左侧 anchor 提示 | 解释 "未来同一个角色 / 场景会复用,你的下一条更省力" | 她有没有"哦"那个表情 — 没有就说明锚点价值没传到 |
| **她改一改** | 10 min | 在 UI 里改文案 / shot | 不干预 | 哪个 shot 改得最多 = 改写质量差的地方 |
| **复制发布包** | 3 min | 点 publish pack copy | 提示 "复制后你可以直接粘抖音" | 她有没有意外 "就这样?" — 这是好信号 |
| **收尾确认** | 5 min | 决定要不要拍 / 发 | 见 §3.4 | (跨入收尾环节)|

### 3.4 收尾(5 min)— 3 个反馈点

> 谢谢你跑完。我现在让你说 3 个反馈点 — 你想到什么就说什么,不需要客气,我做这个就靠你今天的真话。
>
> 1. **今天哪一步让你最爽?**(value-statement 实际命中点)
> 2. **哪一步让你最别扭 / 觉得"这不对"?**(产品最大短板)
> 3. **如果今天你自己一个人,而不是我陪你 — 你会跑到哪一步停下来?**(实际 onboarding cliff)

把 3 个回答**逐字**(不要总结)写进 `founder_log/concierge_run_<date>_<creator_id>.md`。

最后:

> 我下周一会问你:这周你自己又用了几次。不期待你天天用,看真实数据。

不要承诺修复任何 bug;只承诺 "看真实数据"。

### 3.5 first-run 结束 founder 必做(当天 1h 内)

- [ ] 写 `founder_log/concierge_run_<date>_<creator_id>.md` — 5 列表格 + 3 个反馈点逐字
- [ ] 在 `recruitment.md` append `- COMMIT <date> @creator_xxx commit=<是/否> firstrun_at=<时间>`
- [ ] 在 `/admin/cost` 截图本 run 的实际 cost,贴进 `concierge_run_<...>.md` 末尾
- [ ] 给 creator 发一条 30s 内的 DM:"今天谢谢你,我把你说的 3 点记下来了。下周一聊。"

### 3.6 D+7 follow-up(1 周后 founder 必做)

发一条 DM:

> 嗨 [名字],一周过去了 — 你这周自己用了几次? 没用也直接说没用,我想看真实数据。

**收到回应后:**

- "用了 X 次 + 哪些时候" → strong;append 到 `recruitment.md` 的 COMMIT 行
- "没用,因为..." → 同样 strong(你拿到 churn 原因),写到 `concierge_run_<...>.md` 末尾
- 不回复 → 1 周后再发 1 条;再不回视为 lost,不要追到第 3 次

---

## 4. Concierge 模式的 PM-level KPI

Founder 跑完第 1 位 concierge creator 后,PM 在下次 cycle 评估:

| 指标 | weak signal | strong signal |
|---|---|---|
| Creator 完成 first-run | < 70% 真到 publish pack copy | ≥ 70% |
| 3 个反馈点中 value-hit 数 | 0-1 | ≥ 2(她说出 ≥ 2 个非客套的真实 hit) |
| would_pay_39 = true | 心里 ≤ ¥20 | ≥ ¥39 |
| D+7 主动复用次数 | 0 | ≥ 1 |
| 改写产物 founder qualitative pass | 5/10 | ≥ 7/10 |

**3+ strong signal**:Phase 1 内测正方向,可以放大到 cohort 5-10
**1-2 strong signal**:产品形态对路,但有 1-2 个关键修复点 — pivot 而非 abandon
**0 strong signal**:Phase 1 假设需要重新考虑;开 `PM_phase1_rethink_<date>.md`

---

## 5. Founder 行动栏(本 doc 完成后立即可执行)

- [ ] **W4D1**: 启动 5 条 DM(用 `recruitment.md §"DM 文案模板"`)
- [ ] **W4D2-D3**: 第一条回复出现 → 用本 doc §1 booking,目标本周三或周四做第一个 discovery call
- [ ] **W4D3-D5**: 第一个 discovery call(本 doc §2,30 min)
- [ ] **W4D4-D7**: 第一个 first-run together(本 doc §3,1 小时)
- [ ] **W5D1**: PM 看完成情况,写 `PM_W5_allocation.md` 或 `PM_phase1_rethink_<date>.md`

---

## 6. 此 doc 生命周期

- 写于 2026-05-23 W3D3 by PM (Claude)
- 第一次有 creator 跑完 first-run 后,founder 在 §0 后加一节 "实际跑通笔记 — 哪些和脚本对的上 / 哪些走偏"
- W4 末 PM 在本 doc 末加 §7 "concierge 模式真实效果回顾",决定是否 scale 到 cohort 5-10
