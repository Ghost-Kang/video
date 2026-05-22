"""Small in-memory circuit breaker for upstream analysis calls."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from agent.cascade.failures import FailureCode, HardFailure


FAILURE_THRESHOLD = 5
WINDOW_S = 60.0
COOLDOWN_S = 30.0


@dataclass
class _State:
    failures: list[float] = field(default_factory=list)
    opened_at: float | None = None


_BREAKERS: dict[str, _State] = {}


def reset(name: str | None = None) -> None:
    if name is None:
        _BREAKERS.clear()
    else:
        _BREAKERS.pop(name, None)


def before_call(name: str) -> None:
    state = _BREAKERS.setdefault(name, _State())
    if state.opened_at is None:
        return
    now = time.monotonic()
    if now - state.opened_at < COOLDOWN_S:
        raise HardFailure(FailureCode.S8_UPSTREAM_REFUSED, "circuit_open")
    # Half-open: allow exactly one probe. A success closes; a failure re-opens.
    state.opened_at = None
    state.failures = []


def record_success(name: str) -> None:
    _BREAKERS[name] = _State()


def record_failure(name: str) -> None:
    state = _BREAKERS.setdefault(name, _State())
    now = time.monotonic()
    state.failures = [ts for ts in state.failures if now - ts <= WINDOW_S]
    state.failures.append(now)
    if len(state.failures) >= FAILURE_THRESHOLD:
        state.opened_at = now
