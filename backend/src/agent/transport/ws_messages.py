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

from typing import Annotated, Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

# Reuse the canonical niche literal — single source of truth lives in the Cascade
# rewrite service. Importing here keeps WS schema and rewrite prompts in lockstep.
from agent.cascade.rewrite_service import Niche


# ---------- inbound ----------


class _Base(BaseModel):
    """共用 config:严格 extra,catch 客户端 typo。"""

    model_config = ConfigDict(extra="forbid")


class AuthMsg(_Base):
    type: Literal["auth"]
    user_id: str = Field(min_length=1)
    # 内测准入码;production 部署时 backend 校验 in `config.INVITE_CODES`。
    # Optional 因为 dev (INVITE_CODES 空) 不强制;backend gate 决定是否拒。
    invite_code: str | None = None


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
    # Creator's chosen niche; routes the Director to the matching `rewrite_<niche>.md`
    # flavor and lets it skip the "which niche?" question. Optional → legacy clients
    # without onboarding still work; unknown values are rejected by the Literal.
    selected_niche: Optional[Niche] = None


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


class AnalysisReturnedEvent(_Base):
    """Pushed by `cascade_analyze` tool after upstream analysis succeeds.

    Carries the full `CascadeAnalysisContract.model_dump()` so the frontend
    CardStack can render ScriptCard/ShotCard immediately without an extra
    HTTP round-trip.
    """

    type: Literal["analysis_returned"]
    thread_id: str
    analysis: dict[str, Any]


class RewriteReturnedEvent(_Base):
    """Pushed by `cascade_rewrite` tool after niche rewrite succeeds.

    Carries `RewriteResult.model_dump()` plus the originating analysis_id so
    the frontend can correlate the rewrite back to its source analysis card.
    """

    type: Literal["rewrite_returned"]
    thread_id: str
    analysis_id: str
    rewrite: dict[str, Any]


class ShotFirstFrameReturnedEvent(_Base):
    """Pushed by `cascade_generate_first_frame` after a per-shot image succeeds.

    Frontend matches `shot_index` against `shots[].scene_index` and patches in
    `image_url` so the matching ShotCard re-renders without a full payload
    refresh.
    """

    type: Literal["shot_first_frame_returned"]
    thread_id: str
    rewrite_id: str
    shot_index: int
    image_url: str


class AnalysisAnswerReturnedEvent(_Base):
    """Pushed by `cascade_ask` after a free-form Q&A LLM call succeeds.

    Carries the analysis_id + the user's question + the bounded (~300 char)
    answer so the frontend chat panel can render a styled bubble (or, in
    Phase 1, just chat-relay it via the Director's reply).
    """

    type: Literal["analysis_answer_returned"]
    thread_id: str
    analysis_id: str
    question: str
    answer: str


class AnalysisFailedEvent(_Base):
    """W5D3 — structured failure push (replaces fragile chat-message heuristic).

    Whenever the agent runner / cascade tool catches a HardFailure or unhandled
    exception in the analysis path, push this frame so the frontend can flip
    ChatPanel into `failed` state directly. `payload` mirrors FailurePayload
    in frontend/src/types/cascade.ts (code / hint / actions / request_id).
    """

    type: Literal["analysis_failed"]
    thread_id: str
    code: str  # FailureCode str value, e.g. "S4_SCENES_LEN_OUT_OF_RANGE"
    hint: str  # human-readable Chinese, ≤200 chars
    actions: list[str] = Field(default_factory=list)  # RecoveryAction enum values
    request_id: str = ""
    stage: str = "analysis"  # "analysis" | "rewrite" | "first_frame" | "ask"


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
        AnalysisReturnedEvent,
        RewriteReturnedEvent,
        ShotFirstFrameReturnedEvent,
        AnalysisAnswerReturnedEvent,
        AnalysisFailedEvent,
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
