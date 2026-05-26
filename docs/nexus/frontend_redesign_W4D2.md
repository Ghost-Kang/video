# Cascade 前端重设计 brief — W4D2 (2026-05-26)

**Trigger**: founder 2026-05-26 W4D2 "界面太丑且体验不好"
**PM dispatch**: `UX Researcher` (audit + IA + happy path) + `UI Designer` (视觉 tokens + 组件 mockup) 并行
**Synthesis owner**: PM (Claude)
**Implementation owner**: Frontend Developer (待 founder 选 phase 后调)
**Cross-link**: `frontend/src/pages/Landing.tsx`, `frontend/src/components/{Header,Sidebar,ChatPanel,Canvas,CardStack}.tsx`

---

## 0. Core insight(合并两 agent)

**问题不是"丑",是 mental-model mismatch**。工程师的心智(thread / session / canvas / node / pipeline / tool_call)直接漏到 UI 上。3 个最重证据:

1. Header 常驻"策划书 → image → video → composite"工程流水线文字 (`Header.tsx:56`)
2. ProToggle 默认所有人可见,误点进 Canvas 看到节点 + MiniMap + 连线 (`App.tsx:317-319`)
3. `UrlFallback.onSubmit` 把 URL 直接丢弃没传给 chat 路由 (`Landing.tsx:26`)— **这是真 P0 bug,不只是 UX**

视觉层"丑" = SaaS 内部工具感(`bg-stone-50` 冷灰 + `border-stone-200` 死灰边 + Header 内联 `#18181b` 纯黑)。修复方向 = 燕麦奶 + 落日橘 + 手写感(小红书 lifestyle,非 Linear / TikTok)。

---

## 1. Top 7 修复(按 impact/effort)

| # | 修复 | 影响 | 工时 | 来源 |
|---|---|---|---|---|
| 1 | **修 `UrlFallback.onSubmit` URL 透传 bug** — 现在 URL 粘了被丢,跳 chat 是空状态 | P0,直接砍掉一条核心流程 | 15 min | UX 报告 #11 |
| 2 | **Landing 视觉换暖色系** — `bg-stone-50` → `bg-gradient-to-b from-orange-50 via-amber-50/60 to-white` + `rounded-2xl` 全统一 | P0,3 秒第一印象 | 1 h | UI tokens §1 |
| 3 | **Landing 主标题换价值承诺** — "挑一张开始" → "粘一条爆款,30 秒拆给你 → 照着拍就行" | P0,挑完得到啥要写出来 | 5 min | UX 报告 #3 |
| 4 | **HotCard 升级** — 加 🔥 floating badge + 🥕 niche chip + "168 位妈妈正在做" 社证 + 暖橘 hover | P0,3 张灰占位 → lifestyle 卡片 | 1 h | UI mockup #2 |
| 5 | **Loading 状态做"小红书加载感"** — emoji bounce + 进度 checklist + 暖文案"还要 15 秒先喝口水 ☕" | P0,5-30s LLM 等待期是用户跑路高峰 | 1 h | UI mockup #3 |
| 6 | **Header 去 pipeline 化** — 删 "策划书 → image → video → composite" 标语 + ProToggle 改 admin 白名单 | P0,首屏第二眼看到的工程师文字 | 30 min | UX 报告 #1 #4 |
| 7 | **ChatPanel `thinking[]` 隐藏 tool 名** — 不展开 `script_writer(...)` monospace,只显中文进度词 | P1,产出过程不能破功 | 30 min | UX 报告 #7 |

**前 7 项合计 ≈ 4.5 h**,做完首屏 + URL 入口 + 等待态 + Header 完全改观。

---

## 2. 3 个落地 phase

### Phase A — 立即见效(2 h)· **推荐先做**

**目标**:刷新浏览器立刻看到换皮 + 修一个 P0 bug。Founder 30 min 内能晒图。

包含 #1 + #2 + #3 + #4 + #6(Header 部分)中的视觉部分:
- `UrlFallback.onSubmit` URL 透传修复
- Landing 渐变暖背景 + 主标题改文案 + 副标题加引导
- HotCard 加 badge + chip + 社证 + 暖橘 hover
- Header 删 pipeline 标语(简单字符串删除)

**不动**:Chat 页 / Canvas / ProToggle / 移动端布局

**Done-signal**: 浏览器 http://localhost:5173/ 截图前后对比 + `UrlFallback` 提交真带 URL 到 chat 路由

### Phase B — 核心交互重排(4-6 h)

包含 #5 + #6(完整)+ #7 + 移动端 first 改造:
- Loading state 组件(emoji bounce + 进度 checklist + 安抚文案)
- ProToggle 改 admin 白名单(`shouldHideProToggle` 改按 user_id allowlist)
- ChatPanel `thinking[]` filter 掉 tool name,只留中文进度
- `<768px` 时 Sidebar + ChatPanel 默认收起,主区只显 CardStack
- ChatRoom 顶部加返回 + 当前爆款缩略(她确认拆哪条)

**Done-signal**: 手机浏览器打开能用 + 拆解 5-30s 期间不破功

### Phase C — 架构重写(1-2 天)

包含 UX Researcher §2 完整 IA 改造:
- ChatPanel 从常驻 360px 列 → 右下 FAB 抽屉(默认收起,有红点提示)
- Canvas 移到 `?debug=1` 路由,不在 Header 出现
- CardStack 成为唯一工作区
- ConsentGate 从阻塞门 → 底部非阻塞条 + 首次产出前再提示
- 卡片内嵌"换一种 / 再口语点 / 突出宝宝反应"微调按钮(替代 chat panel)

**Done-signal**: 宝妈打开 → 30 秒内看到第一份脚本卡 → 不需要 chat 也能 iterate

---

## 3. Design tokens 速查(Frontend Developer 落地用)

完整在 UI Designer 报告。核心:

```tsx
// 主背景
bg-gradient-to-b from-orange-50 via-amber-50/60 to-white

// 主品牌色
bg-orange-500 text-white  // CTA
text-orange-600           // 强调文字
bg-amber-50 text-amber-700 // niche chip / 二级 tag

// 文字
text-stone-800 // 正文最深(不用纯黑)
text-stone-500 // 副文
text-emerald-600 // 成功(checklist ✓)

// 圆角
rounded-2xl // 卡片 / 输入框 / CTA 全统一
rounded-full // chip / 头像 / 状态点

// 阴影(暖橘渲染,非灰)
shadow-[0_2px_8px_-2px_rgba(251,146,60,0.08)]   // 卡片静态
shadow-[0_8px_24px_-8px_rgba(251,146,60,0.18)]  // hover

// Hover
hover:-translate-y-0.5 + 升级 shadow + bg-orange-600
transition-all duration-200

// 字体(index.css)
body: "PingFang SC", "HarmonyOS Sans SC", "Noto Sans SC", system
.font-display: "Smiley Sans", "PingFang SC"(可选,得意黑)
```

**3 条非协商硬约束**(给 Frontend Developer):
1. 零纯黑零纯白边线(`#000` `#fff` `border-gray-300` 一律驳回)
2. emoji 是 feature 不是装饰(`🍳🥕🔥✨☕` 必须保留在 chip / 标题 / loading / 空状态)
3. Hover 必须存在且温柔(禁止 `hover:opacity-80`,必须 translate + shadow + 颜色三件套)

---

## 4. PM 推荐路径

**先 Phase A**(2 h)→ founder 看完截图决定要不要继续 Phase B → Phase C 留到 W5。

理由:
- founder 今天目标是"尽快看到产品" — Phase A 2h 投入产出最高
- Phase B 需要移动端测试设备,founder 在手机上验证 first-run 才有意义
- Phase C 架构改动大,需要先看 Phase A/B 实际效果再决定是否值得

---

## 5. 待 founder 1 行决策

选项:
- **A. 先 Phase A**(推荐,2h,看到换皮)
- **B. Phase A + B 一起**(6-8h,今晚做完)
- **C. 全部 A + B + C**(1-2 天,完整重写)
- **D. 其他/暂停**(告诉我)

决策后我立刻 dispatch **Frontend Developer** 落地,每完成 1 步刷新浏览器你看效果。

---

## Cross-link

- UX Researcher 完整报告:agent output(本文 §1 + §2 已摘核心)
- UI Designer 完整报告:agent output(本文 §3 已摘核心)
- 当前 Landing 截图:founder 提供 @ 2026-05-26 chat
- 实施 ticket 入口:待 founder 选 phase 后写 `handoff/claude_frontend_redesign_W4D2_phase<X>.md`
