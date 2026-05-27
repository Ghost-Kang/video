# Claude handoff — W5D1-T1: ShotCard 数据源 bug + cascadeMapper 重构

**Owner**: Claude
**Source**: [W5D1 cycle index](_index_W5D1.md)
**优先级**: 🔴 高(bug 体感最强,founder 已亲眼看到)
**Effort**: S (2-3h)
**Dependencies**: 无

---

## 0. 你做什么

founder 截图反馈: **「ShotCard 应该是拆的每一幕的视频」**。

现在的 bug:
- `wsStore.ts` 收到 `rewrite_returned` 时调 `setShots(mapRewriteShotsToScenes(rewrite.shots))`
- **这把源视频的 scenes 给覆盖了**
- 用户分析完 + 改写完看「镜头草稿」,是改写后的虚构镜头,不是原视频每一幕

正确的语义:
- `analysis.scenes` = 源视频每一幕(永远显示在「镜头草稿」)
- `rewrite.shots` = 改写后的镜头(显示在「改完的版本」下方,新区域)
- 两套数据 **共存**,不互相覆盖

---

## 1. 目标文件

| 文件 | 操作 |
|---|---|
| `frontend/src/store/canvasStore.ts` | 加 `rewriteShots: RewriteShot[]` 顶层 state + setter,跟 `shots` 分开 |
| `frontend/src/store/wsStore.ts` | `analysis_returned` → `setShots(analysis.scenes)`;`rewrite_returned` → 只 `setScript` + `setRewriteShots`,**不动 `setShots`** |
| `frontend/src/lib/cascadeMapper.ts` | 保留(供 rewrite 渲染用) |
| `frontend/src/components/CardStack.tsx` | 调整渲染:「镜头草稿」遍历 `analysis.scenes`(改名 `源视频每一幕`),改写镜头(如果有)单独一段 |
| `frontend/src/components/cards/ShotCard.tsx` | 接收 `Scene`(已经是,不动) — 不接 RewriteShot 转的 |
| `frontend/src/components/cards/RewriteShotCard.tsx`(新) | 渲染改写后的 RewriteShot,样式区别于源 ShotCard(更"草稿"感) |
| `frontend/src/lib/cardCopy.ts` | 加 `source_shots_header: "源视频每一幕"` + `rewrite_shots_header: "改写后的镜头"` |

---

## 2. canvasStore 改造细则

```ts
// 之前
shots: Scene[];
setShots: (shots: Scene[]) => void;

// 之后
shots: Scene[];           // 源视频每一幕(从 analysis.scenes)
rewriteShots: RewriteShot[];  // 改写后的镜头(从 rewrite.shots)
setShots: (shots: Scene[]) => void;
setRewriteShots: (shots: RewriteShot[]) => void;
```

`clear()` 同步加 `rewriteShots: []`。

`RewriteShot` type 已经在 `cascadeMapper.ts` 定义,export 出来即可。

---

## 3. wsStore 改造细则

```ts
case "analysis_returned": {
  const { setAnalysis, setShots } = useCanvasStore.getState();
  setAnalysis(event.analysis);
  setShots(event.analysis.scenes ?? []);  // ← 关键:这里就把源视频每一幕填上
  break;
}
case "rewrite_returned": {
  const { setScript, setRewriteShots } = useCanvasStore.getState();
  setScript(event.rewrite.script_markdown);
  setRewriteShots(event.rewrite.shots);  // ← 不再调 setShots
  break;
}
```

---

## 4. CardStack 渲染顺序

```
1. ScriptCard (含 audio/production sub-blocks — Cursor 在 T2 做)
2. 「源视频每一幕」h2 + ShotCard[] (遍历 shots = analysis.scenes)
3. 「改写后的镜头」h2 + RewriteShotCard[] (遍历 rewriteShots, 仅当非空)
4. PublishPackCard (仅当有 rewrite 才显示)
```

---

## 5. 验收

- vitest 全 green(`npm test -- --run` 119 → 121 左右,新增 2 个测试)
- `npx tsc --noEmit` clean
- 手动验:
  1. 起 backend + 前端
  2. 贴抖音 URL,先看到「源视频每一幕」N 个 ShotCard 含真实 timestamp + dialogue
  3. 点 niche chip 触发 rewrite
  4. rewrite 完成后**源 ShotCard 不变**,下方出现「改写后的镜头」区
  5. 切换 session / 新会话 → 一切清空

---

## 6. 边界

- **不动** ShotCard 本体 UI(它就是给 Scene 用的,不变)
- **不动**「生成首帧」按钮逻辑(那个继续工作)
- **不动**任何 prompt 文件或后端代码
- 不引入 framer-motion / 新 deps

---

## 7. 提交规范

commit: `fix(frontend): Claude-W5D1-T1 ShotCard data source — bind analysis.scenes, decouple rewrite shots`
