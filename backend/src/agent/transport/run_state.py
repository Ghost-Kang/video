"""In-process run-status registry — per-thread terminal state for reconnect.

W5D4 — fixes the core "stuck at 95% forever" bug. When a WS drops mid-run
(corp-proxy keepalive timeout / idle cut), the terminal frame (`agent_response`
/ `analysis_failed`) never reaches the browser, and `get_session_state` had no
way to report "this run already finished / failed". The dock stayed in `loading`
forever.

This registry lets `agent_runner` record a thread's run lifecycle so that, on the
next `get_session_state` (the frontend sends one on every reconnect), the backend
can tell the client the run's terminal state and — on failure — the structured
FailurePayload to replay.

In-memory by design: it mirrors the existing in-process registries
(`notify._ws_registry`, `ws_handlers._THREAD_RUN_LOCKS`). After a backend restart
the map is empty, which is *correct*: a run that was in flight at restart is dead,
so `get_session_state` falls back to inferring terminal state from chat history
(an agent message after the last user message == the turn already finished).
"""

from __future__ import annotations

import time
from typing import Any, Literal, Optional, TypedDict

RunStatus = Literal["running", "done", "failed"]


class RunState(TypedDict):
    status: RunStatus
    updated_at: float
    failure: Optional[dict[str, Any]]  # FailurePayload-shaped when status == "failed"


_runs: dict[str, RunState] = {}
_MAX_RUNS = 1024


def _evict_if_needed() -> None:
    """Bound dict growth. Drop oldest *terminal* entries first; never a running one."""
    if len(_runs) < _MAX_RUNS:
        return
    terminal = sorted(
        ((k, v["updated_at"]) for k, v in _runs.items() if v["status"] != "running"),
        key=lambda kv: kv[1],
    )
    for k, _ in terminal[: max(1, len(_runs) - _MAX_RUNS + 1)]:
        _runs.pop(k, None)


def mark_running(thread_id: str) -> None:
    _evict_if_needed()
    _runs[thread_id] = {"status": "running", "updated_at": time.time(), "failure": None}


def mark_done(thread_id: str) -> None:
    _runs[thread_id] = {"status": "done", "updated_at": time.time(), "failure": None}


def mark_failed(thread_id: str, failure: dict[str, Any] | None) -> None:
    _runs[thread_id] = {"status": "failed", "updated_at": time.time(), "failure": failure}


def get(thread_id: str) -> RunState | None:
    return _runs.get(thread_id)


def clear(thread_id: str) -> None:
    _runs.pop(thread_id, None)
