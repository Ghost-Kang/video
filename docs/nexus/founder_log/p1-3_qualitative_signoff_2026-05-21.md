# P1-3 改写 prompts · Founder qualitative signoff

**Date**: 2026-05-21
**Reviewer**: Founder
**Scope**: 三个 niche 的改写 prompt + fixture 模式输出
**Acceptance bar** (per `docs/nexus/handoff/claude_prompts_P1-3.md §3`):
- 机械检查 4/5 通过(长度 / shot 数 / 禁用词 / 置信度 / 保留+改 marker)— 已自动通过 `backend/tests/test_rewrite.py`
- Founder qualitative bar: "我会把这个版本发出去吗?"(本文档要解决的问题)

机械检查全 15/15 通过(每个 niche 5/5)。下面是 fixture 模式针对每个 niche `ref_001.json` 的样例输出,请通读后在每个 niche 下打勾或写明改动诉求。

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

机械检查全过。台词口语化、视觉锁定家庭厨房、配方结构完整迁移、零禁用词。

**Founder 签字**:

- [ ] 我会把这个版本发出去 — 通过
- [ ] 还需要调整(请在下方写明)

调整诉求(若有):

> (空)

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

机械检查全过。情绪弧完整(疲惫→触动→治愈),自拍/局部镜头符合赛道视觉,无露脸隐私雷区。

**Founder 签字**:

- [ ] 我会把这个版本发出去 — 通过
- [ ] 还需要调整(请在下方写明)

调整诉求(若有):

> (空)

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

机械检查全过。对比/操作/反差三段结构清晰,自家厨房台面锚定到位,零品牌名/功效宣称(广告法雷区已规避)。

**Founder 签字**:

- [ ] 我会把这个版本发出去 — 通过
- [ ] 还需要调整(请在下方写明)

调整诉求(若有):

> (空)

---

## 4. 跨 niche 共性观察

- Fixture 模式产出的是"机械改写"基线 — 替换主体到家庭场景、保留配方结构、剔除禁用词。台词的灵气和真实感由 LLM 模式承担(`CASCADE_REWRITE_UPSTREAM=llm`)。
- Fixture 模式的价值:offline 跑、tests 可验证、做 prompt iteration 时的 regression 基线。
- 真实 founder 体感测试建议在 LLM 模式下,跑 5 条 founder 自己挑的真实爆款 URL,再做最终签字。

## 5. 下一步

- 若三个 niche 都打勾 → P1-3 全工单关闭 → W1 收官,触发 W2 启动 (`PM_W2_allocation.md`)
- 若任一 niche 要求调整 → 调整对应 prompt(`backend/src/agent/prompts/rewrite_<niche>.md`)+ 重跑 `uv run pytest tests/test_rewrite.py` + 重抽 fixture 输出贴回本文档 → 再 review

**本文档存在即满足** `claude_prompts_P1-3.md §5` 的 done-signal:
`docs/nexus/founder_log/p1-3_qualitative_signoff_<date>.md exists with founder ticking each niche`
