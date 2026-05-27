"""Runtime context for agent tools — survives across `await` boundaries.

LangGraph's `astream` runs tools inside the same asyncio task that called
`run_agent`. `contextvars.ContextVar` is the right primitive to bridge "this
WS turn" → "tool call deep inside the graph" without polluting the LangGraph
config schema or threading wsstate as kwargs through every tool.

Contract:
    1. `run_agent` MUST call `set_run_ctx(...)` at the start of every WS turn,
       before invoking the graph. The values it stores are valid only for the
       duration of that turn — never read RUN_CTX outside a `run_agent` frame.
    2. Tools (`cascade_analyze`, `cascade_rewrite`, anything that needs to push
       WS frames out-of-band) read via `get_run_ctx()`. Missing keys → tool
       should fall back to returning data without WS push, not crash.
    3. ContextVars propagate across `await` automatically (see PEP 567), so the
       value set in `run_agent` is visible to every tool descendant of that
       call frame.
    4. Do NOT mutate the dict returned by `get_run_ctx()` — treat it as
       read-only. If you need to extend, call `set_run_ctx(...)` with a fresh
       dict (it returns a Token you can `reset()` if needed).

Why a single dict instead of one ContextVar per field: keeps the public surface
to two functions (`set_run_ctx` / `get_run_ctx`) and lets us add fields (e.g.
`run_id` for telemetry) without touching every tool.
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any, TypedDict


class RunCtx(TypedDict, total=False):
    """Per-WS-turn runtime context. All keys optional — tools degrade gracefully."""

    user_id: str
    thread_id: str
    ws: Any  # duck-typed websocket; FakeWebSocket works in tests
    run_id: str | None


RUN_CTX: ContextVar[RunCtx] = ContextVar("openrhtv_run_ctx", default={})


def set_run_ctx(ctx: RunCtx):
    """Install a fresh run context. Returns the Token in case caller wants reset()."""
    return RUN_CTX.set(ctx)


def get_run_ctx() -> RunCtx:
    """Read current run context. Returns empty dict if no turn is active."""
    return RUN_CTX.get()
