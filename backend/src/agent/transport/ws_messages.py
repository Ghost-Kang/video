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


class DeleteSessionsMsg(_Base):
    # Bulk soft-delete (e.g. 历史「清理空会话」). One command → one transaction →
    # one session_list push, avoiding the N-round-trip race that let mid-state
    # session_list events re-add deleted sessions on the client.
    type: Literal["delete_sessions"]
    thread_ids: list[str] = Field(min_length=1)


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


class RegenerateNodeMsg(_Base):
    """time-travel 回溯(P2 slice-2)— 重生一个节点:旧产物快照存版本 → 清 + 入队重生
    → 下游标脏。worker 按边读父节点最新 result 作参考,所以下游自动反映新上游。
    needs_regen / 重生进度经现有 canvas_updated 快照回前端,无需新 outbound 帧。"""

    type: Literal["regenerate_node"]
    thread_id: str = Field(min_length=1)
    node_id: str


class ListNodeVersionsMsg(_Base):
    """time-travel 回溯(P2 slice-2b)— 拉取一个节点的产物版本快照(append-only 旧版)。
    回 `node_versions_returned`。只读,不改画布、不入队。前端 NodeVersionHistory 用它
    渲染历史 + 「当前 vs 选中旧版」对比。"""

    type: Literal["list_node_versions"]
    thread_id: str = Field(min_length=1)
    node_id: str


class ReviewDecisionMsg(_Base):
    """P2 审核闸门 — 用户对 `review_required` 的决策(approve/edit/reject)。

    `decisions` 与 review_required.reviews **同序、同数量**(HumanInTheLoopMiddleware
    硬要求 len(decisions)==被拦工具数)。每个 decision 形如:
      {"type": "approve"} |
      {"type": "edit", "edited_action": {"name": str, "args": {...}}} |
      {"type": "reject", "message"?: str}
    结构由后端 middleware 校验,这里只保证非空 + 字典列表。"""

    type: Literal["review_decision"]
    thread_id: str = Field(min_length=1)
    decisions: list[dict[str, Any]] = Field(min_length=1)
    # 绑定本次决策属于哪一轮 review(对应 review_required.interrupt_id)。空=不绑定
    # (legacy)。resume_agent 用它挡掉「对已结闸门的陈旧/重复决策被套用到下一个级联
    # 闸门」(review #3)。
    interrupt_id: str = ""


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
        RegenerateNodeMsg,
        ListNodeVersionsMsg,
        ReviewDecisionMsg,
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
    # W5D4 — run lifecycle for reconnect resume:
    # "running" | "done" | "failed" | "idle" | "awaiting_review" (P2). Lets the
    # client stop an orphaned 95% spinner when the terminal WS frame was lost to a
    # mid-run disconnect; awaiting_review additionally triggers a review_required
    # replay (handle_get_session_state) so a reconnect re-shows the approval card.
    run_status: str = "idle"
    # Present (FailurePayload-shaped: code/hint/actions/request_id) when
    # run_status == "failed", so the client can replay the failure UI.
    failure: dict[str, Any] | None = None


class CanvasUpdatedEvent(_Base):
    type: Literal["canvas_updated"]
    thread_id: str
    canvas: dict[str, Any] | None = None


class NodeVersionsReturnedEvent(_Base):
    """time-travel 回溯(P2 slice-2b)— 某节点的产物版本快照列表(versions_repo.list_versions),
    按 version_seq 升序。回应 `list_node_versions`。每项形如:
      {version_seq, description, result, asset_status, reason, created_at}。
    前端 NodeVersionHistory 渲染历史 + 「当前(节点 live result)vs 选中旧版」对比。"""

    type: Literal["node_versions_returned"]
    thread_id: str
    node_id: str
    versions: list[dict[str, Any]]


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
    """Pushed by `cascade_generate_first_frame` per-shot — success OR failure.

    Frontend matches `shot_index` against the rewrite shot and patches in either
    `image_url` (success → render image) or `error` (failure → flip that shot to a
    friendly "失败/重试" state INSTANTLY, instead of waiting on the frontend timeout).
    Per-shot so a single draft-image failure never nukes the whole result page.
    """

    type: Literal["shot_first_frame_returned"]
    thread_id: str
    rewrite_id: str
    shot_index: int
    image_url: str = ""             # success → url; failure → ""
    error: Optional[str] = None     # failure → user-friendly message; success → None


class ShotVideoReturnedEvent(_Base):
    """Pushed by the `cascade_generate_shot_video` background poll — per-shot,
    success OR failure. Frontend matches `shot_index` and patches in `video_url`
    (success → render `<video>`) or `error` (failure → 失败/重试). Per-shot so one
    clip failing never nukes the result page. Video gen takes minutes, so this
    arrives long after the submit turn (pushed via the live registry)."""

    type: Literal["shot_video_returned"]
    thread_id: str
    rewrite_id: str
    shot_index: int
    video_url: str = ""             # success → /media url; failure → ""
    error: Optional[str] = None     # failure → user-friendly message; success → None


class FilmReturnedEvent(_Base):
    """Pushed by the `cascade_compose_film` background task when the per-shot clips
    are concatenated into one film. `film_url` = /media/<rewrite_id>/film.mp4."""

    type: Literal["film_returned"]
    thread_id: str
    rewrite_id: str
    film_url: str = ""
    error: Optional[str] = None


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


class AnalysisProgressEvent(_Base):
    """W5D3-T1 — push from _call_doubao_direct at stage boundaries so the
    frontend AnalysisProgress can snap to real percent instead of estimating
    from elapsed seconds. 4 stages cover the doubao_direct path:
    resolve_url (5%) → ark_overlay (15→85%) → transcribe (90%) → done (100%).
    Frontend falls back to time-based ramp when no events arrive (mediakit
    path or older clients)."""

    type: Literal["analysis_progress"]
    thread_id: str
    stage: str  # "resolve_url" | "ark_overlay" | "transcribe" | "done"
    percent: int = Field(..., ge=0, le=100)
    eta_seconds: int = Field(..., ge=0, le=300)
    detail: str = Field("", max_length=120)


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


class ReviewRequiredEvent(_Base):
    """P2 审核闸门 — Director **自主**调生成工具触发 LangGraph interrupt,graph 暂停,
    推此帧让前端弹审核卡。`reviews` 每项一条被拦的工具调用(同序),前端按 allowed_decisions
    给按钮,用户决策回 `review_decision`(decisions 与 reviews 同序同数)。

    `reviews[i]` = {tool: str, label: str(中文友好), args: dict(待执行参数),
                    allowed_decisions: list[str]}。
    显式点「生成」(CardStack [generate_*] 标记)不会触发此帧 —— 后端自动批准。"""

    type: Literal["review_required"]
    thread_id: str
    reviews: list[dict[str, Any]]
    summary: str = ""
    # LangGraph interrupt id,绑定本轮 review;前端在 review_decision 回带。
    interrupt_id: str = ""


WSOutbound = Annotated[
    Union[
        ErrorEvent,
        ReviewRequiredEvent,
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
        ShotVideoReturnedEvent,
        FilmReturnedEvent,
        AnalysisAnswerReturnedEvent,
        AnalysisFailedEvent,
        AnalysisProgressEvent,
    ],
    Field(discriminator="type"),
]


# 供 ws_handlers.HANDLERS 注册时引用 — model 类引用 + handler 函数 type-pair
INBOUND_MODELS: dict[str, type[_Base]] = {
    "auth": AuthMsg,
    "list_sessions": ListSessionsMsg,
    "delete_session": DeleteSessionMsg,
    "delete_sessions": DeleteSessionsMsg,
    "get_session_state": GetSessionStateMsg,
    "reorder_edge": ReorderEdgeMsg,
    "create_edge": CreateEdgeMsg,
    "delete_edge": DeleteEdgeMsg,
    "update_position": UpdatePositionMsg,
    "review_node": ReviewNodeMsg,
    "execute_node": ExecuteNodeMsg,
    "update_node_status": UpdateNodeStatusMsg,
    "optimize_prompt": OptimizePromptMsg,
    "regenerate_node": RegenerateNodeMsg,
    "list_node_versions": ListNodeVersionsMsg,
    "review_decision": ReviewDecisionMsg,
    "user_message": UserMessageMsg,
}
