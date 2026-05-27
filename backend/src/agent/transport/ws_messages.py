"""WebSocket wire contract — Pydantic single source of truth.

After Claude-A 拆分,所有 WS 消息走这里的 Pydantic 模型校验。前端类型由
`make sync-ws-types` 从这些模型 codegen 出 `frontend/src/types/ws_generated.ts`。

新增消息:
1. 加 inbound model 并在 ws_handlers.HANDLERS 注册
2. 加 outbound model(可选,目前仅用于 codegen 暴露给前端)
3. `make sync-ws-types` 重新生成 TS

设计:
- 全部用 `Literal["..."]` 标识 type,实现 tagged union (discriminator="type")
- `extra="forbid"`:无人添加字段会编译/校验报错,catch drift
- thread_id 一律 required string (前端 / handler 都假设 set,避免 silent drop)
- 异常字段(legacy auth 的 user_id 等)用 min_length=1 拒绝空串
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field


# ---------- inbound ----------


class _Base(BaseModel):
    """共用 config:严格 extra,catch 客户端 typo。"""

    model_config = ConfigDict(extra="forbid")


class AuthMsg(_Base):
    type: Literal["auth"]
    user_id: str = Field(min_length=1)


class ListSessionsMsg(_Base):
    type: Literal["list_sessions"]


class DeleteSessionMsg(_Base):
    type: Literal["delete_session"]
    thread_id: str = Field(min_length=1)


class GetSessionStateMsg(_Base):
    type: Literal["get_session_state"]
    thread_id: str = Field(min_length=1)


class ReorderEdgeMsg(_Base):
    type: Literal["reorder_edge"]
    thread_id: str = Field(min_length=1)
    edge_id: str
    direction: Literal["up", "down"] = "up"


class CreateEdgeMsg(_Base):
    type: Literal["create_edge"]
    thread_id: str = Field(min_length=1)
    source: str
    target: str


class DeleteEdgeMsg(_Base):
    type: Literal["delete_edge"]
    thread_id: str = Field(min_length=1)
    edge_id: str


class UpdatePositionMsg(_Base):
    type: Literal["update_position"]
    thread_id: str = Field(min_length=1)
    node_id: str
    x: float
    y: float


class ReviewNodeMsg(_Base):
    type: Literal["review_node"]
    thread_id: str = Field(min_length=1)
    node_id: str
    action: Literal["approve", "reject"]
    feedback: str | None = None


class ExecuteNodeMsg(_Base):
    type: Literal["execute_node"]
    thread_id: str = Field(min_length=1)
    node_id: str
    node_type: Literal["script", "image", "video", "composite"]
    description: str = ""
    image_gen_provider: str | None = None
    # video 专属(可选)
    duration: int | None = None
    resolution: str | None = None
    generate_audio: bool | None = None


class UpdateNodeStatusMsg(_Base):
    type: Literal["update_node_status"]
    thread_id: str = Field(min_length=1)
    node_id: str
    node_status: Literal["reviewing", "confirmed"] = "reviewing"


class OptimizePromptMsg(_Base):
    type: Literal["optimize_prompt"]
    thread_id: str = Field(min_length=1)
    node_id: str
    prompt: str
    feedback: str


class UserMessageMsg(_Base):
    type: Literal["user_message"]
    thread_id: str = Field(min_length=1)
    content: str = Field(min_length=1)


# tagged union by `type` field — Pydantic 2 用 Field(discriminator=...)
WSInbound = Annotated[
    Union[
        AuthMsg,
        ListSessionsMsg,
        DeleteSessionMsg,
        GetSessionStateMsg,
        ReorderEdgeMsg,
        CreateEdgeMsg,
        DeleteEdgeMsg,
        UpdatePositionMsg,
        ReviewNodeMsg,
        ExecuteNodeMsg,
        UpdateNodeStatusMsg,
        OptimizePromptMsg,
        UserMessageMsg,
    ],
    Field(discriminator="type"),
]


# ---------- outbound ----------


class ErrorEvent(_Base):
    type: Literal["error"]
    code: str
    message: str
    bad_type: str | None = None  # 校验失败时回带原始 type 方便前端调试


class SessionListEvent(_Base):
    type: Literal["session_list"]
    sessions: list[dict[str, Any]]


class SessionStateEvent(_Base):
    type: Literal["session_state"]
    thread_id: str
    messages: list[dict[str, Any]]
    canvas: dict[str, Any] | None = None


class CanvasUpdatedEvent(_Base):
    type: Literal["canvas_updated"]
    thread_id: str
    canvas: dict[str, Any] | None = None


class PromptOptimizedEvent(_Base):
    type: Literal["prompt_optimized"]
    thread_id: str
    node_id: str
    optimized_prompt: str


class ProcessingEvent(_Base):
    type: Literal["processing"]
    thread_id: str


class AgentStreamEvent(_Base):
    type: Literal["agent_stream"]
    thread_id: str
    event: Literal["text", "tool_call"]
    # text 走 content;tool_call 走 name + args
    content: str | None = None
    name: str | None = None
    args: str | None = None


class AgentResponseEvent(_Base):
    type: Literal["agent_response"]
    thread_id: str
    content: str
    canvas: dict[str, Any] | None = None


WSOutbound = Annotated[
    Union[
        ErrorEvent,
        SessionListEvent,
        SessionStateEvent,
        CanvasUpdatedEvent,
        PromptOptimizedEvent,
        ProcessingEvent,
        AgentStreamEvent,
        AgentResponseEvent,
    ],
    Field(discriminator="type"),
]


# 供 ws_handlers.HANDLERS 注册时引用 — model 类引用 + handler 函数 type-pair
INBOUND_MODELS: dict[str, type[_Base]] = {
    "auth": AuthMsg,
    "list_sessions": ListSessionsMsg,
    "delete_session": DeleteSessionMsg,
    "get_session_state": GetSessionStateMsg,
    "reorder_edge": ReorderEdgeMsg,
    "create_edge": CreateEdgeMsg,
    "delete_edge": DeleteEdgeMsg,
    "update_position": UpdatePositionMsg,
    "review_node": ReviewNodeMsg,
    "execute_node": ExecuteNodeMsg,
    "update_node_status": UpdateNodeStatusMsg,
    "optimize_prompt": OptimizePromptMsg,
    "user_message": UserMessageMsg,
}
