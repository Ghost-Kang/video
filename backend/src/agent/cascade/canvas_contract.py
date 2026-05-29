"""Canvas wire contract shared by backend canvas storage and frontend types."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


NodeType = Literal["script", "image", "video", "composite"]
NodeStatus = Literal["reviewing", "confirmed"]
AssetStatus = Literal["idle", "generating", "done", "failed", "timeout"]
GenerationStatus = Literal["idle", "pending", "submitted", "polling", "done", "failed"]


class CanvasNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    type: NodeType
    title: str
    description: str
    status: str
    node_status: NodeStatus
    asset_status: AssetStatus
    result: dict[str, Any] | None = None
    subtype: str | None = None
    shot_no: str | None = None
    image_gen_provider: str | None = None
    feedback: str | None = None
    generation_status: GenerationStatus = "idle"
    generation_task_id: str | None = None
    generation_error: str | None = None
    generation_attempt_count: int = 0
    generation_lease_until: str | None = None
    generation_next_retry_at: str | None = None
    user_id: str
    thread_id: str
    x: float | None = None
    y: float | None = None


class CanvasEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    source: str
    target: str
    position: int = 0


class CanvasState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nodes: dict[str, CanvasNode]
    edges: list[CanvasEdge]
