# Claude handoff — W5D3-T1: 真实分析进度 WS event

**Owner**: Claude (next cycle)
**Source**: [W5D3 cycle index](_index_W5D3.md)
**优先级**: 🟡 中 (UX 锦上添花, 不阻塞 Founder 当前流程)
**Effort**: M (3-4h)
**Dependencies**: 无

---

## 0. 你做什么

当前 `AnalysisProgress.tsx` 显示的进度条**是前端估算的**:0 → 80% 线性递增 60s, 等 `analysis_returned` 才 snap 100%。问题:
- WS 断连 / backend 慢时, 进度条卡 95% 没真实信号
- "约 N 秒" 倒计时跟真实 backend 进度脱节

UX Architect agent 自己 flag 过这是 implicit risk:
> 进度条目前是前端估算 (60s 内 0→80%，等 `analysis_returned` snap 100%)。WS 中途断了 + reconnect 时进度会卡在 95% 直到 backend 真完成。

修法: backend 在 cascade_analyze 内部各阶段 emit `analysis_progress` WS event, 前端订阅取代 fake percent。

---

## 1. Backend 实现 (主体)

### 1.1 新 outbound event

`backend/src/agent/transport/ws_messages.py`:

```py
class AnalysisProgressEvent(_Base):
    """W5D3 — push from cascade_analyze at stage boundaries so the frontend
    progress bar can snap to real percent instead of estimating from elapsed
    seconds."""

    type: Literal["analysis_progress"]
    thread_id: str
    stage: Literal["resolve_url", "mediakit_storyline", "ark_overlay", "transcribe", "done"]
    percent: int = Field(..., ge=0, le=100)
    eta_seconds: int = Field(..., ge=0, le=300)  # 估算剩余 (backend 知道平均时长)
    detail: str = Field("", max_length=120)  # 中文一句 e.g. "拉抖音 CDN 直链"
```

加到 WSOutbound union。

### 1.2 backend emit 点

`backend/src/agent/cascade/analysis_service.py` `_call_doubao_direct` (或 `_call_mediakit`) 各阶段加 emit:

```py
async def _emit_progress(stage: str, percent: int, eta: int, detail: str):
    ctx = get_run_ctx()  # 从 ContextVar 拿 ws + thread_id
    if ctx and ctx.get("ws"):
        try:
            await send_json(
                ctx["ws"],
                type="analysis_progress",
                thread_id=ctx["thread_id"],
                stage=stage, percent=percent, eta_seconds=eta, detail=detail,
            )
        except Exception:
            pass

# 在 _call_doubao_direct 内部:
await _emit_progress("resolve_url", 5, 55, "拉抖音 CDN 直链")
direct_url, metadata = await resolve_to_direct_media(source_url)

await _emit_progress("ark_overlay", 15, 50, "送豆包视觉模型")
result = await doubao_direct_client.analyze_video_direct(...)

await _emit_progress("transcribe", 85, 8, "提取台词")
transcript = await transcribe_client.fetch_transcript(...)

await _emit_progress("done", 100, 0, "整理完成")
```

参考 `backend/src/agent/cascade/cascade/cascade_analyze tool` 已经用过的 `runtime_ctx.get_run_ctx()` pattern。

### 1.3 backend tests

`backend/tests/transport/test_analysis_progress_event.py`:
- AnalysisProgressEvent parse 4 个 stage value + invalid stage 拒绝
- percent / eta_seconds 边界值
- 加到现有 WSOutbound 联合测试 (test_ws_messages.py)

`backend/tests/test_cascade_tool.py` 扩 cascade_analyze happy path:
- mock send_json,assert 至少 emit 3 次 analysis_progress (各 stage)
- stage 顺序: resolve_url → ark_overlay → transcribe → done

---

## 2. Frontend 接入

### 2.1 wsStore.ts 加 case

```ts
case "analysis_progress":
  set({
    progressStage: event.stage,
    progressPercent: event.percent,
    progressEta: event.eta_seconds,
    progressDetail: event.detail,
  });
  break;
```

wsStore state 加 4 个 field (initial null/0)。

### 2.2 AnalysisProgress.tsx 取 store, 不再自己 setInterval 估算

```tsx
const stage = useWSStore(s => s.progressStage);
const percent = useWSStore(s => s.progressPercent);
const eta = useWSStore(s => s.progressEta);
const detail = useWSStore(s => s.progressDetail);

// 老的 elapsed 估算保留作 fallback: 若 backend 没 emit (旧 client / mediakit mode),
// fall back to time-based ramp.
const displayPercent = percent > 0 ? percent : fallbackTimeEstimate();
const displayEta = eta > 0 ? eta : fallbackEtaEstimate();
```

`progressDetail` (例如 "拉抖音 CDN 直链") 在 stage list 旁显示，比单纯 stage 名更直观。

### 2.3 ws.ts 加 AnalysisProgressEvent 到 WSEvent union

跑 `scripts/sync-ws-types.sh` 自动 codegen。

### 2.4 Frontend tests

- `chat/__tests__/AnalysisProgress.realProgress.test.tsx`: 模拟 wsStore 推 stage="ark_overlay" + percent=50, assert 渲染 50% 不是估算
- Fallback: 没收到 analysis_progress event 时还是按 time-based 估算 (老行为)

---

## 3. 边界 / 禁区

- **不动 frontend ChatPanel.tsx** — AnalysisProgress 是独立组件, 改它就够
- **不动 backend agent_runner.py 异常处理** — Risk 1 已经在那里
- **不动 cascade_rewrite / cascade_ask** — 它们短跑没必要 emit progress
- **保留 fake-percent fallback** — 旧客户端 / cascade_upstream=mediakit 路径还会用

---

## 4. 验收 checklist

- [ ] backend pytest ≥510 (baseline 507 + 3 progress event tests)
- [ ] frontend vitest ≥172 (baseline 170 + 2 realProgress tests)
- [ ] tsc clean
- [ ] e2e (founder 自测 douyin URL): 进度从 0% → 5% (resolve) → 15% → 50% (ark) → 85% (transcribe) → 100%, 不再线性递增
- [ ] backend logs 含 4 个 [progress] emit 行
- [ ] frontend /admin/health 看到新事件流 analysis_progress (可选, 不强求 events.db 落盘)

---

## 5. 提交规范

3 个 commit:

```
feat(backend): W5D3-T1 analysis_progress WS event from cascade_analyze stages
feat(frontend): W5D3-T1 AnalysisProgress consumes real progress events
docs(handoff): mark Claude W5D3-T1 ✅
```

Push `gk/main`。

---

**Owner sign-off**: Claude (next cycle)
**Estimated**: 3-4h
