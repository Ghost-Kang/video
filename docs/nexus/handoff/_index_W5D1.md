# Cycle W5D1 — 分析维度扩展前端落地 (2026-05-27)

## 背景

W4D5 收尾后 founder 体验真实抖音 URL,发现:
1. 分析维度不够(缺音频 / 完整脚本 / 拍摄可复刻)
2. **ShotCard 显示错** — 应该是源视频每一幕,实际被 rewrite_shots 覆盖
3. Landing 缺时长性价比提示
4. 用户想能"自由提问" analysis,缺 chat 入口

后端 cycle 已完成(see backend agent report): contract 加 `viral_analysis.audio` / `production` / 顶层 `full_transcript`; prompt overlay 扩展; transcribe_client 新建; `cascade_ask` tool 注册; analysis_service 加 180s/5s duration guard; `douyin_share_resolver.duration_s`。pytest **489 passed**。

WS schema 已 codegen,`ws_generated.ts` 新增 `AnalysisAnswerReturnedEvent` 等。**前端尚未消费**。

---

## 三家分工

| Owner | Task | 文件 | 优先级 | Effort | 依赖 |
|---|---|---|---|---|---|
| **Claude** | T1 修 ShotCard 数据源 bug + cascadeMapper 重构 | [claude_frontend_W5D1_T1_shotcard_data_source.md](claude_frontend_W5D1_T1_shotcard_data_source.md) | 🔴 高 (bug 体感最强) | S (2-3h) | 无 |
| **Cursor** | T2 新建 3 个维度卡片 + ChatPanel 自由提问入口 | [cursor_frontend_W5D1_T2_new_dim_cards.md](cursor_frontend_W5D1_T2_new_dim_cards.md) | 🟡 中 (UI 增量) | M (4-6h) | T3 的 wsStore wire(可并行,接口已 freeze) |
| **Codex** | T3 wsStore + canvasStore + Landing 时长提示 + cardCopy | [codex_frontend_W5D1_T3_ws_glue_duration.md](codex_frontend_W5D1_T3_ws_glue_duration.md) | 🔴 高 (T2 阻塞) | S (1.5h) | 无 |
| **Founder** | 决策点 ↓ | (本文档) | — | — | — |

## Founder 决策点

1. **transcribe endpoint guess 是否要 verify**(backend agent risk a)
   - 选择: 现在 verify (founder 拿真 MediaKit doc 对一下) / 先看真实跑 + W17 warning 频次再说
2. **W15/W16 (audio/production fallback)频次警戒线** 跌穿后是否要分拆 prompt 成 2 次 LLM 调用
   - 选择: 设阈值 / 等真实数据
3. **「自由提问」入口在 ChatPanel 哪个位置**
   - 选择: 输入框上方 chip / quick reply 按钮区 / 长按消息出菜单

---

## 验收(三家完工后)

founder 在 incognito 浏览器贴 `https://www.douyin.com/video/7643415855329561897`(人民日报钓鱼侠救溺水视频),期望看到:

- ✅ Landing 输入框下方提示 「建议 ≤ 3 分钟」
- ✅ 跳 chat 后 ShotCard 区显示**源视频的真实每一幕**(timestamp + visual + dialogue),不是改写后的
- ✅ ScriptCard 含「为什么这条会火」8 维 + audio 子卡 + production 子卡
- ✅ 新独立卡片「完整原片台词」 collapsible
- ✅ ChatPanel 底部有「自由提问」入口
- ✅ 输 `这条 BGM 给人什么感觉?` → Director 调 `cascade_ask` → answer 原文回 chat
- ✅ /admin/events 实时看到事件流: `analysis_returned` → `analysis_answer_returned`

---

## 注意

- 此 cycle **不动后端代码**(后端已 freeze + 489 测试 green)
- WS 协议契约见 `frontend/src/types/ws_generated.ts`(codegen 产物,不要手编)
- 不违反 `FORBIDDEN_TERMS`(节点 / 锚点 / AI / Agent / 平台 / 工具 / 画布 / DAG)
- 前端 baseline: vitest **119 passed**,tsc clean。完工后必须仍 green。
