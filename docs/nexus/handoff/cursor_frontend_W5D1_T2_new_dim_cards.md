# Cursor handoff — W5D1-T2: 新维度卡片 + ChatPanel 自由提问入口

**Owner**: Cursor
**Source**: [W5D1 cycle index](_index_W5D1.md)
**优先级**: 🟡 中(UI 增量,不阻塞核心流)
**Effort**: M (4-6h)
**Dependencies**: T3 (Codex) 的 `wsStore` `analysis_answer_returned` case 必须先合(契约接口已定,可并行编码)

---

## 0. 你做什么

后端 cycle 已经给 `viral_analysis` 加了 `audio` + `production` 两个结构化子块,顶层加 `full_transcript`,还新增了 `cascade_ask` tool 供「用户对 analysis 自由提问」。

前端需要把这 4 个新能力**渲染出来**:

1. **AudioCard** — 渲染 `analysis.viral_analysis.audio.{bgm, voice_pace, sound_effects}`
2. **TranscriptCard** — 渲染 `analysis.full_transcript`(collapsible,默认折叠;长文本)
3. **ProductionCard** — 渲染 `analysis.viral_analysis.production.{cost_tier, estimated_hours, replaceable_anchors[]}`
4. **ChatPanel 自由提问入口** — chip 形式触发 `[ask: <用户输入>]` 前缀的 user_message

3 个卡片整合到 CardStack 渲染序列中,放在 ScriptCard 后、ShotCard 前,作为「为什么这条会火」的延展。

---

## 1. 目标文件

| 文件 | 操作 |
|---|---|
| `frontend/src/components/cards/AudioCard.tsx`(新) | 渲染音频 3 维 |
| `frontend/src/components/cards/TranscriptCard.tsx`(新) | collapsible 完整逐字脚本 |
| `frontend/src/components/cards/ProductionCard.tsx`(新) | 拍摄成本 + 可替换元素 |
| `frontend/src/components/CardStack.tsx` | 把 3 个新卡按序插入 |
| `frontend/src/components/ChatPanel.tsx` | 加「问点别的」chip,onClick 弹一个 inline mini textbox,输 question 后 send `[ask: <question>]` |
| `frontend/src/lib/cardCopy.ts` | 加全部新文案(下方清单) |
| 各卡片 `__tests__` 目录新增对应 .test.tsx | 每个卡 ≥ 2 测试(render + FORBIDDEN_TERMS) |

---

## 2. AudioCard 设计

```tsx
<section className={CARD_CLASS} data-testid="audio-card">
  <h2 ...>音频拆解</h2>
  <ul border-l-2 ...>
    <li>
      <span 🟧 chip>BGM</span>
      <p>{audio.bgm}</p>
    </li>
    <li>
      <span 🟧 chip>口播 / 语速</span>
      <p>{audio.voice_pace}</p>
    </li>
    <li>
      <span 🟧 chip>音效</span>
      <p>{audio.sound_effects}</p>
    </li>
  </ul>
</section>
```

样式跟 ScriptCard 的 bullet 风格保持一致(border-l-2 + 陶土橙 label)。

---

## 3. TranscriptCard 设计

- 默认折叠,标题旁一个「展开 ▼」按钮
- 折叠态: 显示前 60 字符 + `…`
- 展开态: `<pre>` 滚动框,max-h-80,whitespace-pre-wrap
- 右上角一个「复制」按钮,clipboard 写整段 transcript + toast 「已复制完整台词」
- 如果 `analysis.full_transcript` 为空 → 整张卡不渲染(`if (!transcript) return null`)

---

## 4. ProductionCard 设计

```tsx
<section ...>
  <h2>拍这条要花多少</h2>
  <div className="flex gap-2 mb-3">
    <span chip>{cost_tier === 'solo_phone' ? '一个人 + 手机' : cost_tier === 'small_team' ? '小团队' : '重后期'}</span>
    <span chip>{estimated_hours}h</span>
  </div>
  {replaceable_anchors.length > 0 && (
    <>
      <h3>能换成你自己的</h3>
      <ul>{anchors.map(a => <li>{a}</li>)}</ul>
    </>
  )}
</section>
```

---

## 5. ChatPanel 自由提问入口

输入框上方 chip 行(在 `chat_quick_continue / hook / oral` 旁):

```
[继续下一步] [开头再抓] [更口语] [💡 问点别的]
```

点「问点别的」→ chip 区下方滑出一个 mini textarea(2 行)+ 「发问」按钮。
点「发问」→ `onSend("[ask: " + input + "]")` → mini textarea 关闭。

Tip 文案: 「比如:这条 BGM 给人什么感觉? / 这种节奏适合我做吗?」

---

## 6. 新 cardCopy 键(全部加这里)

```ts
audio_header: "音频拆解",
audio_bgm_label: "BGM",
audio_pace_label: "口播 / 语速",
audio_sfx_label: "音效",

transcript_header: "完整原片台词",
transcript_expand: "展开",
transcript_collapse: "收起",
transcript_copy: "复制",
transcript_copied: "已复制完整台词",

production_header: "拍这条要花多少",
production_cost_solo: "一个人 + 手机",
production_cost_team: "小团队",
production_cost_heavy: "重后期",
production_hours_suffix: "h",
production_replaceable_header: "能换成你自己的",

ask_chip_label: "问点别的",
ask_placeholder: "比如:这条 BGM 给人什么感觉?",
ask_submit: "发问",
ask_hint: "针对刚才的分析提任何问题",
```

**所有新文案过 FORBIDDEN_TERMS audit**(节点 / 锚点 / AI / Agent / 平台 / 工具 / 画布 / DAG)。

---

## 7. CardStack 渲染插入位置

```
1. ScriptCard (含「为什么火」)
2. AudioCard (新)
3. ProductionCard (新)
4. TranscriptCard (新, 折叠)
5. h2「源视频每一幕」+ ShotCard[] (T1 Claude 改)
6. NicheCTA (script === "" 时)
7. h2「改完的版本」+ script body (script !== "" 时)
8. h2「改写后的镜头」+ RewriteShotCard[] (T1 Claude 加)
9. PublishPackCard (仅 script !== "")
```

---

## 8. 验收

- vitest: 现有 119 → ≥ 125(每卡片 2 测试 = 6 个新,自由提问 chip 加 1)
- tsc 干净
- FORBIDDEN_TERMS 测试覆盖新文案
- 手动: 贴 URL → 看到 4 个新 UI 出现(audio / production / transcript / 问点别的 chip)

---

## 9. 边界

- 不动 ScriptCard 已有结构(它已经在 T1 + 之前 cycle 改好了)
- 不动 backend / prompt / contract
- 不动 ShotCard / PublishPackCard
- 不引入 framer-motion / 任何新 deps,纯 Tailwind + CSS 动效

---

## 10. 提交规范

commit: `feat(frontend): Cursor-W5D1-T2 audio/production/transcript cards + ask chip`
