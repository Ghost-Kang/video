# P1-3 改写 prompts · Founder qualitative signoff

**Date**: 2026-05-21
**Reviewer**: Founder
**Scope**: 三个 niche 的改写 prompt + fixture 模式输出
**Acceptance bar** (per `docs/nexus/handoff/claude_prompts_P1-3.md §3`):
- 机械检查 4/5 通过(长度 / shot 数 / 禁用词 / 置信度 / 保留+改 marker)— 已自动通过 `backend/tests/test_rewrite.py`
- Founder qualitative bar: "我会把这个版本发出去吗?"(本文档要解决的问题)

机械检查全 15/15 通过(每个 niche 5/5)。下面是 fixture 模式针对每个 niche `ref_001.json` 的样例输出 founder 通读后的签字与调整诉求。

> **重要前置**: 本签字是**对 fixture baseline 的签字**,不是对最终 creator 发布版本的签字。Fixture 是 regression 兜底,真实 founder bar 在 LLM 模式 + P2-4 真爆款 URL 池下检验。下方"调整诉求"全部针对 **LLM 模式 prompt**,fixture 不需要返工。

---

## 1. 宝妈辅食 (baomam_fushi)

源 contract: `backend/src/agent/cascade/fixtures/rewrite_smoke/baomam_fushi/ref_001.json`
源 hook: "开场 1.2 秒:宝宝撇头拒食 + 妈妈无奈表情"
源 formula: "悬念开场(拒食痛点) + 3 步解决(换花样) + 反差结尾(主动吃)"

改写输出 (`script_markdown`):

```
### 改写脚本
<!-- 保留:悬念开场(拒食痛点) + 3 步解决(换花样) + 反差结尾(主动吃) | 改:换成宝妈辅食视角和家庭场景 -->
1. 你家宝宝是不是也这样,怎么喂都不吃?
   画面:暖色家庭厨房,暖色俯拍,餐椅特写,橙色胡萝卜泥
2. 试试换成苹果,颜色更亮宝宝更感兴趣
   画面:暖色家庭厨房,暖色俯拍砧板,红苹果块
3. 蒸 8 分钟,又软又香
   画面:暖色家庭厨房,侧拍蒸锅,蒸汽中红苹果
4. 看,张嘴了!这一勺下去我眼泪都要出来
   画面:暖色家庭厨房,中景,妈妈手持勺子,宝宝张嘴接住
```

**Founder 签字**:

- [x] **我会把这个版本发出去 — 通过 (fixture baseline 级)**
- [ ] 还需要调整(请在下方写明)

**调整诉求 (落到 LLM 模式 prompt,不阻塞 fixture)**:

> **F-1-a [P1] 钩子模式与 P2-4 主流模板严重脱节**
> - 当前 shot 1 "你家宝宝是不是也这样" 是泛化疑问句,**未使用** P2-4 已验证的 H1(月龄)/H2(一周不重样)/H3(结果承诺) 任一主流钩子。
> - 真实爆款基准: @阿倩 "来看看 12 月龄宝宝一周辅食不重样" (4640赞/5791收藏) — 月龄+不重样是辅食 niche 的标配开场。
> - **要求**: LLM 模式 prompt 必须强制在 shot 1 注入 H1(月龄) + H2(数字清单/不重样) 至少一个,缺一个就 reject。

> **F-1-b [P0 信任崩塌雷区] 食材替换营养逻辑断裂**
> - "胡萝卜泥 → 苹果" 是蔬菜换水果,不是同营养类目内换花样。这种在辅食赛道的评论区会被宝妈直接怼,信任损耗比触发禁用词还严重。
> - **要求**: 在 niche prompt 加营养类目约束 — "替代食材必须与原食材同营养类目(蛋白/蔬菜/水果/主食),禁止跨类替换"。机械可校验,加进 `test_rewrite.py`。

> **F-1-c [P2] 调性混搭弱化定位**
> - 开场"工具型钩子"(怎么喂都不吃?) + 结尾"我眼泪都要出来"情绪型钩子,定调摇摆。
> - 真爆款要么纯工具流(阿倩) 要么纯情绪流(@当妈以后),混搭让笔记定位模糊,影响算法分发。
> - **要求**: LLM prompt 在 shot 1 决定调性后,后续 shot 必须同调性一致。

---

## 2. 育儿日常 (yuer_richang)

源 contract: `backend/src/agent/cascade/fixtures/rewrite_smoke/yuer_richang/ref_001.json`
源 hook: "开场 1 秒:妈妈在凌晨 3 点的卧室,娃又醒了"
源 formula: "深夜场景痛点 + 孩子一句话 + 妈妈独白治愈"

改写输出 (`script_markdown`):

```
### 改写脚本
<!-- 保留:深夜场景痛点 + 孩子一句话 + 妈妈独白治愈 | 改:换成育儿日常视角和家庭场景 -->
1. 他又醒了,这是今晚第三次
   画面:家里温暖灯光,夜灯昏黄,卧室广角
2. 我快撑不住了
   画面:家里温暖灯光,妈妈手轻拍娃后背特写
3. 他说了句'妈妈在',然后就睡了
   画面:家里温暖灯光,娃睡颜侧面
4. 原来他也在确认我在
   画面:家里温暖灯光,妈妈侧脸特写
```

**Founder 签字**:

- [x] **我会把这个版本发出去 — 通过 (fixture baseline 级)**
- [ ] 还需要调整(请在下方写明)

**调整诉求 (落到 LLM 模式 prompt)**:

> **F-2-a [P2] 这条质量明显高于辅食条,作为"好样本"标杆**
> - 情绪弧完整: 疲惫 → 崩溃边缘 → 真实细节钩 → 治愈金句
> - "他说了句'妈妈在'然后就睡了" 是真实细节钩,对齐 @当妈以后 (7610100974662207717) 的语言风格
> - 金句"原来他也在确认我在" 有截图传播力 → 小红书封面可直接用
> - **要求**: 把这条 fixture 输出作为 `prompts/rewrite_yuer_richang.md` 的 in-context exemplar,LLM 模式向这条对齐。

> **F-2-b [P1] 视觉锚点单一化(跨 niche 共性问题,见 §4-A)**
> - 4 个 shot 全部"家里温暖灯光" — fixture 可接受,LLM 必须给每 shot 不同视觉元素
> - **要求**: LLM prompt 强制每 shot ≥2 个差异化视觉元素(光/物件/景别),否则 reject

> **F-2-c [P2] 缺钩子前置承诺**
> - 当前是纯叙事流,没给观众"看完得到什么"的暗示
> - 育儿情绪型爆款的强 hook 是"妈妈们都懂"式共鸣承诺前置
> - **要求**: LLM 模式可选(非强制)在 shot 1 前加 1 句锚点,如"凌晨 3 点的妈妈们都在干什么"

---

## 3. 家庭厨房 (jiating_chufang)

源 contract: `backend/src/agent/cascade/fixtures/rewrite_smoke/jiating_chufang/ref_001.json`
源 hook: "开场 1.2 秒:餐厅 88 元的菜,在家做花了 12"
源 formula: "餐厅 vs 家庭对比 + 3 步操作 + 成品反差"

改写输出 (`script_markdown`):

```
### 改写脚本
<!-- 保留:餐厅 vs 家庭对比 + 3 步操作 + 成品反差 | 改:换成家庭厨房视角和家庭场景 -->
1. 餐厅卖 88,我猜成本不到 15
   画面:自家厨房台面,手机屏幕照特写
2. 牛肉切片,生抽糖淀粉抓匀
   画面:自家厨房台面,俯拍砧板,牛肉特写
3. 热锅冷油,30 秒变色
   画面:自家厨房台面,侧拍炒锅,火光特写
4. 出锅撒葱花,这卖相
   画面:自家厨房台面,成品装盘俯拍
```

**Founder 签字**:

- [x] **我会把这个版本发出去 — 通过 (fixture baseline 级)**
- [ ] 还需要调整(请在下方写明)

**调整诉求 (落到 LLM 模式 prompt)**:

> **F-3-a [P1] hook→action 衔接断层,缺菜名锚点**
> - shot 1 给出价差,shot 2 直接切牛肉 — 观众还没反应过来要做什么菜
> - 对比 @王刚 "厨师长教你做一道家常菜:'家常豆腐'" — 菜名必须在 shot 1 落地
> - **要求**: LLM prompt 强制 shot 1 必须含 [菜名] 占位符,例如 "教你做'家常滑牛肉',餐厅 88 我做 12"

> **F-3-b [P1] 缺评论区二次梗钩 (family kitchen 爆款长尾的关键)**
> - @王刚"家常豆腐"持续被翻出 7 年,核心是评论区在玩"宽油是什么油"这个梗
> - 当前改写"热锅冷油,30 秒变色"是技术陈述,无玩梗钩
> - **要求**: LLM prompt 显式约束 — 每条改写必须埋 ≥1 个"违反直觉的小技术点/反常识细节"作为评论区话题种子(例:为什么牛肉要逆纹切 / 为什么油温要 6 成而不是 7 成)
> - 这条诉求催生了一个新钩子模式 **H9: 评论区二次梗钩**,定义见 `p2-4_hooks_taxonomy.md`

> **F-3-c [P1] 成品镜头不种草化**
> - 当前"成品装盘俯拍"是纪录片镜头,真爆款最后一帧必须是**满屏怼脸特写 + 蒸汽/油光/光泽**
> - **要求**: LLM prompt 在最后一个 shot 的画面描述里强制要求"近景斜 45° + 至少 1 个食欲触发元素(蒸汽/油光/拉丝/汤汁)"

> **F-3-d [P1] 视觉锚点单一化(同 F-2-b)**

---

## 4. 跨 niche 共性观察 (founder 补充)

原文档观察我同意。补 3 条**跨工单架构反馈**,需要 W2 在 P2-4 设计时一并处理:

**Founder 反馈 A [视觉锚点单一化是 fixture-mode regression test 的盲区]**
- Fixture 输出"暖色家庭厨房"/"家里温暖灯光"反复出现,regression test 仍然全过 → 说明 `test_rewrite.py` 的 invariant 是 weak invariant
- **行动项**: P2-4 加机械检查项 #6 — `visual_diversity_score`: 同一脚本内 shot 间视觉描述的 token 重合率 ≤ 50%。可写在 `backend/tests/test_rewrite.py` 里。

**Founder 反馈 B [P1-3 prompt 与 P2-4 钩子模式不连通]**
- 三个 niche 的 fixture 改写都没用上 P2-4 已经验证的 8 个钩子模式 (H1-H8)
- 这是跨工单的设计漏洞: P1-3 prompt 在真空里写,P2-4 钩子库独立产出,LLM 模式跑起来两边没对齐
- **行动项**: P2-4 entry 的第一步,把 `docs/nexus/founder_log/p2-4_hooks_taxonomy.md` (H1-H9 定义) 作为强制 input,塞进 `prompts/rewrite_<niche>.md` 的 system prompt 末尾。每 niche 还要列出 priority map:
  - baomam_fushi: **H1, H2, H3** (主流) + H8 (情绪型对照)
  - yuer_richang: **H8, H7, H4** (主流) + H6 (场景化)
  - jiating_chufang: **H4, H5, H7, H9** (主流) + H3 (收藏诱导)

**Founder 反馈 C [P1-3 → P2-4 接力点已对齐]**
- 原文档"真实 founder 体感测试建议在 LLM 模式下,跑 5 条 founder 自己挑的真实爆款 URL" — 同意,这正是 P2-4 在做的事
- P2-4 的 URL 池已建好(`docs/nexus/founder_log/real_urls_for_p2-4.md` v3.0): 9 抖音 + 6 小红书,主流模板 ROI 100%
- **接力 invariant**: 本文档签字即触发 W1 收官,W2 启动 P2-4 跑通这 15 条 + H1-H9 钩子注入后,做第二轮 founder qualitative signoff (那次是对 LLM 模式的签字,是真 founder bar)

---

## 5. 最终签字与下一步

**Niche 通过状态**:
- ✅ baomam_fushi: fixture baseline 通过 (3 个 LLM 模式调整诉求 F-1-a/b/c 落到 P2-4)
- ✅ yuer_richang: fixture baseline 通过 + 标为 LLM exemplar (调整诉求 F-2-a/b/c)
- ✅ jiating_chufang: fixture baseline 通过 (4 个调整诉求 F-3-a/b/c/d,催生新钩子 H9)

**W1 收官触发条件已满足**:
- ✅ 机械检查全 15/15 通过
- ✅ Founder qualitative 3/3 签字 (fixture baseline 级)
- ✅ 调整诉求全部归口到 P2-4,无阻塞 W1 的返工项

**下一步 (W2 启动清单)**:
1. ⏭️ PM 关闭 P1-3 全工单,触发 `PM_W2_allocation.md`
2. ⏭️ P2-4 启动时,先吸收本文档 §1-3 的调整诉求 (F-1-a/b/c, F-2-a/b/c, F-3-a/b/c/d)
3. ⏭️ P2-4 entry 任务追加: 把 `p2-4_hooks_taxonomy.md` (H1-H9) 注入 `prompts/rewrite_<niche>.md`,生成 v2 prompt
4. ⏭️ P2-6 eval harness 启动前,加机械检查项 #6 `visual_diversity_score` (来自 §4-A) + 检查项 #7 `nutrient_category_consistency` (来自 F-1-b)
5. ⏭️ 用 `real_urls_for_p2-4.md` v3.0 的 9 抖音 + 6 小红书在 LLM 模式跑通 → 触发第二轮 founder signoff (LLM 级真 founder bar)

**Acceptance bar reached** ✅

> 本文档存在即满足 `claude_prompts_P1-3.md §5` 的 done-signal:
> `docs/nexus/founder_log/p1-3_qualitative_signoff_<date>.md exists with founder ticking each niche`

— Founder signed **2026-05-21**
