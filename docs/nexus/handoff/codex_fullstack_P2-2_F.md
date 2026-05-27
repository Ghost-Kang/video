# Codex handoff — Task F (P2-2 Canvas node 跨端 contract)

**Owner**: Codex
**Source**: `docs/nexus/architecture_review_2026-05-26.md` P2-2
**优先级**: 中(独立,可与 C/E 并行)
**Effort**: S (半天)
**Dependencies**: 无(Decision-1 决定走 codegen,但 canvas contract 比 WS 简单,优先沿用 cascade.ts 的手镜像模式;codegen 可后跟进)

---

## 0. 你做什么

Cascade contract 已经在 BE/FE 镜像(`backend/src/agent/cascade/contract.py` ↔
`frontend/src/types/cascade.ts`),但 **canvas node 是唯一没共享的 contract**:
- 后端 node schema:`backend/src/agent/tools/canvas.py:47-63`(SQLite 列)+ `:96-109`(`_row_to_node`)
- 前端 node 类型:`frontend/src/types/index.ts:16-30`(手写 `CanvasNode`)

字段已经 drift:后端发 `feedback / generation_status / generation_task_id /
generation_error`,前端 type 没建模。每加一个字段都是 4 文件改动,无编译保护。

你要定义共享 Pydantic 模型 + 镜像到 TS,把所有字段对齐。

---

## 1. 目标文件

| 文件 | 操作 |
|---|---|
| `backend/src/agent/cascade/canvas_contract.py` | 新建 — Pydantic `CanvasNode` / `CanvasEdge` / `CanvasState` |
| `backend/src/agent/tools/canvas.py` | 修改 — `_row_to_node` 返回 `CanvasNode.model_dump(mode="json")` 或返回 model 本身 |
| `frontend/src/types/canvas.ts` | 新建 — 镜像 |
| `frontend/src/types/index.ts` | 修改 — `export type { CanvasNode, CanvasEdge } from "./canvas"`,删除旧手写 |

---

## 2. Pydantic 模型(必须字段)

参考 `canvas.py:47-63` 的 SQLite schema + `:96-109` 的 `_row_to_node`,完整字段:

```python
# backend/src/agent/cascade/canvas_contract.py
from typing import Literal, Optional
from pydantic import BaseModel, Field

NodeType = Literal["script", "image", "video", "composite"]
NodeStatus = Literal["draft", "ready", "generating", "reviewing", "approved", "rejected"]
AssetStatus = Literal["draft", "queued", "generating", "done", "failed"]
GenerationStatus = Literal["", "pending", "submitted", "polling", "done", "failed"]


class CanvasNode(BaseModel):
    id: str
    user_id: str
    thread_id: str
    type: NodeType
    subtype: Optional[str] = None
    description: str = ""
    x: float = 0.0
    y: float = 0.0
    node_status: NodeStatus = "draft"
    asset_status: AssetStatus = "draft"
    image_gen_provider: Optional[str] = None
    feedback: Optional[str] = None              # ← 前端缺
    generation_status: GenerationStatus = ""    # ← 前端缺
    generation_task_id: Optional[str] = None    # ← 前端缺
    generation_error: Optional[str] = None      # ← 前端缺
    result: Optional[dict] = None
    created_at: str
    updated_at: str


class CanvasEdge(BaseModel):
    id: str
    source: str
    target: str
    order_index: int = 0


class CanvasState(BaseModel):
    nodes: dict[str, CanvasNode]
    edges: list[CanvasEdge]
```

**关键**:把字段名 / 类型与 `_row_to_node` 的 dict key 100% 对齐。看 `canvas.py:96-109`
和 SQLite CREATE TABLE 列定义,逐一对应。

---

## 3. TypeScript 镜像

```ts
// frontend/src/types/canvas.ts
export type NodeType = "script" | "image" | "video" | "composite";
export type NodeStatus = "draft" | "ready" | "generating" | "reviewing" | "approved" | "rejected";
export type AssetStatus = "draft" | "queued" | "generating" | "done" | "failed";
export type GenerationStatus = "" | "pending" | "submitted" | "polling" | "done" | "failed";

export interface CanvasNode {
  id: string;
  user_id: string;
  thread_id: string;
  type: NodeType;
  subtype: string | null;
  description: string;
  x: number;
  y: number;
  node_status: NodeStatus;
  asset_status: AssetStatus;
  image_gen_provider: string | null;
  feedback: string | null;
  generation_status: GenerationStatus;
  generation_task_id: string | null;
  generation_error: string | null;
  result: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface CanvasEdge {
  id: string;
  source: string;
  target: string;
  order_index: number;
}

export interface CanvasState {
  nodes: Record<string, CanvasNode>;
  edges: CanvasEdge[];
}
```

`frontend/src/types/index.ts` 里旧的 `CanvasNode` 删掉,加:
```ts
export type { CanvasNode, CanvasEdge, CanvasState, NodeType, NodeStatus, AssetStatus, GenerationStatus } from "./canvas";
```

---

## 4. 后端接入

`canvas.py:96-109` `_row_to_node`:

**最小侵入版**(推荐先做):返回的 dict 不变,但加一个 `_row_to_node_model` 函数返
Pydantic 实例供新代码用,旧 dict 保留兼容。

**完整版**(可下 cycle):`_row_to_node` 直接返 `CanvasNode.model_dump(mode="json")`。
逐步替换 dict 访问为 model attribute 访问。

Codex-F **只做最小侵入版**:
- `canvas_contract.py` 全新建,Pydantic + TS 都到位
- `_row_to_node` 加 validation:在函数末尾 `CanvasNode.model_validate(node).model_dump(mode="json")` 走一遍,确保后端返回的 dict 一定符合 schema(catch 类型 drift)
- 前端 type 替换完毕

这样后端 wire format 不变,前端 type 收紧,以后字段 drift 在 backend test 时 Pydantic 直接报错。

---

## 5. 验收

**必过**:
1. `backend/src/agent/cascade/canvas_contract.py` 存在,Pydantic 完整
2. `frontend/src/types/canvas.ts` 存在,与 Pydantic 字段一一对应
3. `frontend/src/types/index.ts` 旧 `CanvasNode` 删除,改 re-export
4. `npm run build` 通过(tsc 严格类型检查)— 这一步会 catch 所有现在用 `feedback` 等
   字段但前端没声明的地方,可能需要补 NodeDetail.tsx / Canvas.tsx 的类型 hint
5. backend pytest 通过(`_row_to_node` 加 validation 后,如有 drift 会 fail)
6. Playwright 12 个 smoke 全绿

**手测**:
- `/chat/:threadId` 内拖拽节点 → x/y 写入正确(没有类型 drift)
- 节点 reject 操作 → feedback 字段写入并显示

---

## 6. 不要碰

- `backend/src/agent/tools/canvas.py` 的具体 SQL / 业务函数(approve_node, execute_node 等)— 只动 `_row_to_node` 加 validation
- `tools/canvas.py` 的 SQLite schema(改 schema 要 migration,不在 scope)
- `frontend/src/types/cascade.ts`(那是 Toprador analysis contract,不是 canvas)

---

## 7. 提交规范

- 单 commit:`refactor(fullstack): Codex-F canvas contract 跨端共享 + 字段对齐`
