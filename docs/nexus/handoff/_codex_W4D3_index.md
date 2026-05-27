# Codex W4D3 cycle 任务 index

**Cycle**: 2026-05-26 W4D3
**Owner**: Codex
**Source**: `docs/nexus/architecture_review_2026-05-26.md` (PM 分派段)
**Total**: 5 个 task

---

## 任务清单

| Task | 标题 | 文件 | 优先级 | Effort | 阻塞 |
|---|---|---|---|---|---|
| **C** | P1-2 `App.tsx` 拆 store | [codex_frontend_P1-2_C.md](codex_frontend_P1-2_C.md) | 🔴 最高 | M | 无 |
| **D** | P0-2 前端 WS 类型镜像 | [codex_frontend_P0-2_D.md](codex_frontend_P0-2_D.md) | 🟡 中 | S | **等 Claude-B** |
| **E** | P1-1 `cascade/storage.py` 拆 | [codex_backend_P1-1_E.md](codex_backend_P1-1_E.md) | 🔴 高 | M | 无 |
| **F** | P2-2 Canvas node 跨端 contract | [codex_fullstack_P2-2_F.md](codex_fullstack_P2-2_F.md) | 🟡 中 | S | 无 |
| **G** | P3-1 事件名 → StrEnum | [codex_backend_P3-1_G.md](codex_backend_P3-1_G.md) | 🟢 低 | S | 建议 E 之后做 |

---

## 推荐执行顺序

```
Day 1:  C 启动(M)  + E 启动(M)  并行
Day 2:  C 收尾     + E 收尾      + F (S)
Day 3:  G          + D (等 Claude-B 完成)
```

**最早交付**:E.Step1 + F 可在半天内出 commit。C 是最大块,优先级最高。

---

## Founder 决策(已定)

- **Decision-1**: WS 类型镜像 **B = codegen**(影响 D)
- **Decision-2**: worker **立刻拆**(已在 Claude-A 完成,不影响 Codex)
- **Decision-3**: 5 task **全做**,不砍 G

---

## 完成后

每个 task 完成请在 `docs/nexus/architecture_review_2026-05-26.md` 的 PM 分派段
对应 Codex-X 后面打 ✅ + commit hash。

如遇阻塞,在本 index 文件加注释,标红色 ⚠️ + 一句话说明。

---

## 不要碰(Architect 红线)

- `backend/src/agent/cascade/contract.py` (ACL 核心)
- `backend/src/agent/cascade/failures.py` (HardFailure envelope)
- `backend/src/agent/cascade/events.py` 单写路径(只换 ALLOWED_EVENTS 构建方式,不改验证逻辑)
- `frontend/src/components/NodeDetail.tsx`(P2-1 don't-refactor)
- Backend Claude 已动的文件:`transport/`, `workers/`,以及 `tools/canvas.py` 的 claim/recover
