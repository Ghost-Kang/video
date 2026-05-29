"""HTTP route table — 之前 `_handle_http` 里 200 行 if/elif 改成显式路由。

每个 handler 签名:`async def handler(qs: dict, body: dict, **path_params) -> tuple[int, dict, str]`
返回 (status, response_body, reason)。reason 默认 "OK"。

路由匹配:
- EXACT_ROUTES: (method, path) tuple → handler
- PARAM_ROUTES: prefix + suffix 匹配,提取 id 作 path_param

错误统一在 dispatcher 处理:
- HardFailure → 503(upstream refused)/ 422(其他)
- LookupError → 404
- 其他 Exception → 500
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable
from urllib.parse import parse_qs, urlparse

from pydantic import ValidationError

from agent import config
from agent.cascade import cost_guard
from agent.cascade.analysis_service import request_shallow_analysis
from agent.cascade.anchors import create_anchor, list_anchors, list_reuses, reuse_anchor
from agent.cascade.event_names import EventName
from agent.cascade.events import emit
from agent.cascade.failures import HardFailure
from agent.cascade.persistence.db import _connect
from agent.cascade.rewrite_service import error_payload, request_rewrite
from agent.cascade.storage import list_creators, list_events


# Slowloris guard for the hand-rolled HTTP server: cap how long we wait for a
# client to finish sending headers/body. nginx fronts us in prod (it buffers +
# times out), but defense-in-depth — a direct/local client must not be able to
# pin an asyncio task forever on a half-open socket.
HTTP_READ_TIMEOUT_S = 15.0


# ---------- response helper ----------


def _http_response(status: int, body: dict, reason: str = "OK") -> bytes:
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    return (
        f"HTTP/1.1 {status} {reason}\r\n"
        "Content-Type: application/json; charset=utf-8\r\n"
        f"Content-Length: {len(payload)}\r\n"
        "Connection: close\r\n"
        "\r\n"
    ).encode("ascii") + payload


# ---------- handlers ----------


HandlerFn = Callable[..., Awaitable[tuple[int, dict, str]]]


async def handle_cost_status(qs: dict, body: dict) -> tuple[int, dict, str]:
    user_id = qs.get("user_id", [None])[0]
    if not user_id:
        return 400, {"error": "user_id required"}, "Bad Request"
    payload = await cost_guard.cost_status(user_id, qs.get("run_id", ["default"])[0])
    return 200, payload, "OK"


async def handle_creators(qs: dict, body: dict) -> tuple[int, dict, str]:
    creators = await list_creators()
    return 200, {"creators": creators}, "OK"


async def handle_events_get(qs: dict, body: dict) -> tuple[int, dict, str]:
    try:
        limit = int(qs.get("limit", ["200"])[0])
        offset = int(qs.get("offset", ["0"])[0])
    except ValueError:
        return 400, {"error": "limit/offset must be integers"}, "Bad Request"
    event_name = qs.get("type", [None])[0]
    user_id_q = qs.get("user_id", [None])[0]
    since_ts = qs.get("since_ts", [None])[0]
    try:
        payload = await list_events(
            limit=limit,
            offset=offset,
            event_name=event_name,
            user_id=user_id_q,
            since_ts=since_ts,
        )
    except ValueError as exc:
        return 400, {"error": str(exc)}, "Bad Request"
    return 200, payload, "OK"


async def handle_events_post(qs: dict, body: dict) -> tuple[int, dict, str]:
    event_name = body.get("event_name")
    if not event_name or not isinstance(event_name, str):
        return 400, {"error": "event_name required (string)"}, "Bad Request"
    try:
        await emit(
            event_name,
            user_id=str(body.get("user_id") or "default"),
            run_id=body.get("run_id"),
            payload=body.get("payload") or {},
        )
    except ValueError as exc:
        return 400, {"error": f"invalid event: {exc}"}, "Bad Request"
    return 200, {"ok": True}, "OK"


async def handle_anchors_get(qs: dict, body: dict) -> tuple[int, dict, str]:
    user_id = qs.get("user_id", ["default"])[0]
    kind = qs.get("kind", [None])[0]
    try:
        anchors = await list_anchors(user_id=user_id, kind=kind)
    except ValueError as exc:
        return 400, {"error": str(exc)}, "Bad Request"
    return 200, {"anchors": [a.model_dump(mode="json") for a in anchors]}, "OK"


async def handle_anchors_post(qs: dict, body: dict) -> tuple[int, dict, str]:
    try:
        anchor = await create_anchor(
            user_id=str(body.get("user_id") or "default"),
            kind=str(body.get("kind") or ""),
            label=str(body.get("label") or ""),
            image_url=str(body.get("image_url") or ""),
            source_run_id=body.get("source_run_id"),
            source_shot_index=body.get("source_shot_index"),
        )
    except (ValidationError, ValueError) as exc:
        return 400, {"error": str(exc)}, "Bad Request"
    return 200, anchor.model_dump(mode="json"), "OK"


async def handle_anchor_reuses(qs: dict, body: dict, anchor_id: str) -> tuple[int, dict, str]:
    user_id = qs.get("user_id", ["default"])[0]
    try:
        payload = await list_reuses(anchor_id=anchor_id, user_id=user_id)
    except LookupError as exc:
        return 404, {"error": str(exc)}, "Not Found"
    except PermissionError as exc:
        return 403, {"error": str(exc)}, "Forbidden"
    return 200, payload, "OK"


async def handle_anchor_reuse_post(qs: dict, body: dict, anchor_id: str) -> tuple[int, dict, str]:
    try:
        anchor = await reuse_anchor(
            anchor_id=anchor_id,
            user_id=str(body.get("user_id") or "default"),
            reused_in_run_id=str(body.get("reused_in_run_id") or ""),
            reused_in_shot_index=body.get("reused_in_shot_index"),
        )
    except LookupError as exc:
        return 404, {"error": str(exc)}, "Not Found"
    except PermissionError as exc:
        return 403, {"error": str(exc)}, "Forbidden"
    return 200, anchor.model_dump(mode="json"), "OK"


async def handle_rewrite(qs: dict, body: dict) -> tuple[int, dict, str]:
    user_id = str(body.get("user_id") or "default")
    run_id = str(body.get("run_id") or "default")
    await cost_guard.cost_guard(user_id, run_id, cost_guard.PREDICT_REWRITE_CNY)
    _t0 = time.monotonic()
    result = await request_rewrite(
        analysis_id=str(body.get("analysis_id") or ""),
        niche=body.get("niche"),
        user_id=user_id,
        run_id=run_id,
    )
    _latency_ms = int((time.monotonic() - _t0) * 1000)
    await emit(
        EventName.GENERATION_COST,
        user_id=user_id,
        run_id=run_id,
        payload={
            "run_id": run_id,
            "call_kind": "rewrite",
            "provider": "local",
            "model": result.model,
            "cost_fen": int(round(result.cost_cny * 100)),
            "latency_ms": _latency_ms,
            "tokens_in": None,
            "tokens_out": None,
            "outcome": "done",
        },
    )
    return 200, result.model_dump(mode="json"), "OK"


async def handle_analysis_shallow(qs: dict, body: dict) -> tuple[int, dict, str]:
    source_url = str(body.get("source_url") or "").strip()
    if not source_url:
        return 400, {"error": "source_url_required"}, "Bad Request"
    user_id = str(body.get("user_id") or "default")
    run_id = str(body.get("run_id") or "default")
    await cost_guard.cost_guard(user_id, run_id, cost_guard.PREDICT_ANALYSIS_CNY)
    _t0 = time.monotonic()
    contract = await request_shallow_analysis(source_url, user_id=user_id, run_id=run_id)
    _latency_ms = int((time.monotonic() - _t0) * 1000)
    await emit(
        EventName.GENERATION_COST,
        user_id=user_id,
        run_id=run_id,
        payload={
            "run_id": run_id,
            "call_kind": "analysis",
            "provider": "fixture",
            "model": contract.model,
            "cost_fen": int(round(contract.cost_cny * 100)),
            "latency_ms": _latency_ms,
            "tokens_in": None,
            "tokens_out": None,
            "outcome": "done",
        },
    )
    return 200, contract.model_dump(mode="json"), "OK"


_SERVER_START_TIME = time.monotonic()


async def handle_health_summary(qs: dict, body: dict) -> tuple[int, dict, str]:
    """W5D2-D — single endpoint for /admin/health dashboard. Combines:
    - server stats (CPU/mem/disk/uptime) from stdlib (no psutil dep)
    - events 5min aggregate
    - upstream success rate over 1h (analysis + rewrite)
    - last 10 failure_emitted events
    """
    import shutil

    # server stats — stdlib only (avoid psutil add to deps)
    try:
        cpu_percent = _cpu_percent_proc()
    except Exception:
        cpu_percent = 0.0
    try:
        mem_total_mb, mem_used_mb = _meminfo_proc()
    except Exception:
        mem_total_mb, mem_used_mb = (0, 0)
    try:
        du = shutil.disk_usage("/")
        disk_total_gb = round(du.total / 1024 / 1024 / 1024, 2)
        disk_used_gb = round(du.used / 1024 / 1024 / 1024, 2)
    except Exception:
        disk_total_gb, disk_used_gb = (0.0, 0.0)
    uptime = int(time.monotonic() - _SERVER_START_TIME)

    # events_5min aggregate
    five_min_ago = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    try:
        events_5min, upstream, recent_failures = await _health_event_stats(
            five_min_ago=five_min_ago,
            one_hour_ago=one_hour_ago,
        )
    except Exception:
        # health endpoint must not crash; return what we have
        events_5min = {"total": 0, "by_type": {}}
        upstream = {
            EventName.ANALYSIS_RETURNED.value: None,
            EventName.SCRIPT_REWRITTEN.value: None,
        }
        recent_failures = []

    return 200, {
        "server": {
            "cpu_percent": cpu_percent,
            "mem_used_mb": mem_used_mb,
            "mem_total_mb": mem_total_mb,
            "disk_used_gb": disk_used_gb,
            "disk_total_gb": disk_total_gb,
            "uptime_seconds": uptime,
        },
        "events_5min": events_5min,
        "upstream_success_rate": upstream,
        "recent_failures": recent_failures,
    }, "OK"


async def _health_event_stats(
    *,
    five_min_ago: str,
    one_hour_ago: str,
) -> tuple[dict, dict[str, float | None], list[dict]]:
    db = await _connect()
    try:
        grouped = await db.execute_fetchall(
            """SELECT event_name, COUNT(*)
               FROM events
               WHERE created_at > ?
               GROUP BY event_name""",
            (five_min_ago,),
        )
        by_type = {str(name): int(count or 0) for name, count in grouped}
        events_5min = {"total": sum(by_type.values()), "by_type": by_type}

        counts = dict(
            await db.execute_fetchall(
                """SELECT event_name, COUNT(*)
                   FROM events
                   WHERE created_at > ?
                     AND event_name IN (?, ?)
                   GROUP BY event_name""",
                (
                    one_hour_ago,
                    EventName.ANALYSIS_RETURNED.value,
                    EventName.SCRIPT_REWRITTEN.value,
                ),
            )
        )
        failure_rows = await db.execute_fetchall(
            """SELECT payload_json
               FROM events
               WHERE created_at > ? AND event_name = ?""",
            (one_hour_ago, EventName.FAILURE_EMITTED.value),
        )
        analysis_fail = 0
        rewrite_fail = 0
        for (payload_json,) in failure_rows:
            try:
                payload = json.loads(payload_json) if payload_json else {}
            except json.JSONDecodeError:
                continue
            if payload.get("stage") == "analysis":
                analysis_fail += 1
            elif payload.get("stage") == "rewrite":
                rewrite_fail += 1

        analysis_done = int(counts.get(EventName.ANALYSIS_RETURNED.value, 0) or 0)
        rewrite_done = int(counts.get(EventName.SCRIPT_REWRITTEN.value, 0) or 0)
        upstream: dict[str, float | None] = {
            EventName.ANALYSIS_RETURNED.value: None,
            EventName.SCRIPT_REWRITTEN.value: None,
        }
        if analysis_done + analysis_fail > 0:
            upstream[EventName.ANALYSIS_RETURNED.value] = round(
                analysis_done / (analysis_done + analysis_fail), 3
            )
        if rewrite_done + rewrite_fail > 0:
            upstream[EventName.SCRIPT_REWRITTEN.value] = round(
                rewrite_done / (rewrite_done + rewrite_fail), 3
            )

        rows = await db.execute_fetchall(
            """SELECT id, event_name, user_id, run_id, payload_json, created_at
               FROM events
               WHERE event_name = ?
               ORDER BY created_at DESC, id DESC
               LIMIT 10""",
            (EventName.FAILURE_EMITTED.value,),
        )
    finally:
        await db.close()

    recent_failures = []
    for row_id, name, uid, rid, payload_json, created_at in rows:
        try:
            payload = json.loads(payload_json) if payload_json else {}
        except json.JSONDecodeError:
            payload = {"_raw": payload_json}
        recent_failures.append({
            "id": int(row_id),
            "ts": created_at,
            "event_name": name,
            "user_id": uid,
            "run_id": rid,
            "payload": payload,
        })
    return events_5min, upstream, recent_failures


def _cpu_percent_proc() -> float:
    """Coarse CPU usage without psutil.

    Linux reads /proc/stat. Dev machines without /proc fall back to loadavg
    scaled by CPU count so the health contract still returns a number.
    """
    try:
        with open("/proc/stat", "r") as f:
            line = f.readline()
        parts = [int(x) for x in line.split()[1:]]
        if len(parts) < 4:
            return 0.0
        idle = parts[3]
        total = sum(parts)
        if total == 0:
            return 0.0
        return round(100.0 * (total - idle) / total, 2)
    except FileNotFoundError:
        load_1m = os.getloadavg()[0] if hasattr(os, "getloadavg") else 0.0
        cpus = os.cpu_count() or 1
        return round(min(100.0, max(0.0, 100.0 * load_1m / cpus)), 2)


def _meminfo_proc() -> tuple[int, int]:
    """Returns (total_mb, used_mb) without psutil."""
    try:
        with open("/proc/meminfo", "r") as f:
            info = {}
            for line in f:
                k, _, v = line.partition(":")
                info[k.strip()] = v.strip()
        total_kb = int(info["MemTotal"].split()[0])
        avail_kb = int(info.get("MemAvailable", info.get("MemFree", "0 kB")).split()[0])
        total_mb = total_kb // 1024
        used_mb = (total_kb - avail_kb) // 1024
        return total_mb, used_mb
    except FileNotFoundError:
        if hasattr(os, "sysconf"):
            page_size = os.sysconf("SC_PAGE_SIZE")
            phys_pages = os.sysconf("SC_PHYS_PAGES")
            total_mb = int(page_size * phys_pages / 1024 / 1024)
            return total_mb, total_mb
        return 0, 0


async def handle_health_live(qs: dict, body: dict) -> tuple[int, dict, str]:
    """Lightweight liveness probe (OPEN, no auth). Used by the container
    healthcheck. Distinct from /api/health/summary, which is admin-gated and
    does real DB aggregation. Must stay cheap and unauthenticated so the
    Docker healthcheck doesn't need a token and doesn't write a data-endpoint
    access-log line every 30s."""
    return 200, {"ok": True, "uptime_seconds": int(time.monotonic() - _SERVER_START_TIME)}, "OK"


async def handle_invite_verify(qs: dict, body: dict) -> tuple[int, dict, str]:
    """W5D4 — pre-flight invite-code check for the invite gate (OPEN, no auth).

    The gate used to accept any input and only let the WS auth reject a bad code
    afterward — which (before the 4003 loop-breaker) trapped users like the one
    who entered 'ee' in a connect→4003→reconnect death loop. Now the gate calls
    this first and only advances on `valid: true`, so a wrong code is blocked at
    the door with a clear message. When INVITE_CODES is empty (dev/test) the gate
    is disabled, so any code is valid — matching the WS auth behavior.
    """
    code = (qs.get("code", [""])[0] or "").strip()
    if not config.INVITE_CODES:
        return 200, {"valid": True, "gate": "open"}, "OK"
    valid = code in config.INVITE_CODES
    return 200, {"valid": valid, "gate": "cohort"}, "OK"


async def handle_public_stats(qs: dict, body: dict) -> tuple[int, dict, str]:
    """Aggregate-only public counters for the landing page (OPEN, no auth).

    Replaces the landing page pulling 500 raw events to the browser (which
    leaked source URLs / user_ids to every anonymous visitor). Returns only
    two integers, computed server-side via COUNT(DISTINCT)."""
    try:
        db = await _connect()
        try:
            rows = await db.execute_fetchall(
                "SELECT COUNT(DISTINCT run_id), COUNT(DISTINCT user_id) FROM events"
            )
        finally:
            await db.close()
        runs = int(rows[0][0] or 0) if rows else 0
        creators = int(rows[0][1] or 0) if rows else 0
    except Exception:
        runs, creators = 0, 0
    return 200, {"runs": runs, "creators": creators}, "OK"


async def handle_client_error(qs: dict, body: dict) -> tuple[int, dict, str]:
    """W5D2 — frontend Sentry-lite. Browser JS errors POST here; we strip
    PII (truncate UA/stack/message), emit a `client_error` event into the
    same events.db pipeline /admin/events reads. No auth: anonymous cohort
    creators must be able to report errors before invite/login resolves.
    Rate limiting is handled implicitly by the frontend dedup (1 min)."""
    kind = str(body.get("kind") or "unknown")[:40]
    message = str(body.get("message") or "")[:500]
    if not message:
        return 400, {"error": "message required"}, "Bad Request"
    # Truncate everything aggressively — events.db row is best kept < 8KB
    payload = {
        "kind": kind,
        "message": message,
        "stack": str(body.get("stack") or "")[:4000],
        "filename": str(body.get("filename") or "")[:200],
        "lineno": body.get("lineno") if isinstance(body.get("lineno"), int) else None,
        "colno": body.get("colno") if isinstance(body.get("colno"), int) else None,
        "url": str(body.get("url") or "")[:500],
        "ua": str(body.get("ua") or "")[:200],
        "thread_id": str(body.get("thread_id") or "")[:80] or None,
    }
    try:
        await emit(
            EventName.CLIENT_ERROR,
            user_id=str(body.get("user_id") or "anonymous")[:80],
            run_id=None,
            payload=payload,
        )
    except ValueError as exc:
        return 400, {"error": f"invalid event: {exc}"}, "Bad Request"
    return 200, {"ok": True}, "OK"


# ---------- routing ----------


EXACT_ROUTES: dict[tuple[str, str], HandlerFn] = {
    ("GET", "/api/cost/status"): handle_cost_status,
    ("GET", "/api/creators"): handle_creators,
    ("GET", "/api/events"): handle_events_get,
    ("POST", "/api/events"): handle_events_post,
    ("GET", "/api/anchors"): handle_anchors_get,
    ("POST", "/api/anchors"): handle_anchors_post,
    ("POST", "/api/rewrite"): handle_rewrite,
    ("POST", "/api/analysis/shallow"): handle_analysis_shallow,
    ("POST", "/api/client_error"): handle_client_error,
    ("GET", "/api/health"): handle_health_live,
    ("GET", "/api/health/summary"): handle_health_summary,
    ("GET", "/api/stats/public"): handle_public_stats,
    ("GET", "/api/invite/verify"): handle_invite_verify,
}

# (method, prefix, suffix, param_name, handler) — 路径里的可变段会作为 path_param 传入。
PARAM_ROUTES: list[tuple[str, str, str, str, HandlerFn]] = [
    ("GET", "/api/anchors/", "/reuses", "anchor_id", handle_anchor_reuses),
    ("POST", "/api/anchors/", "/reuse", "anchor_id", handle_anchor_reuse_post),
]


# ---------- auth ----------
#
# Three tiers. Default (anything not listed) = COHORT.
#   OPEN   — no auth. Liveness, public stats, anonymous client error reports.
#   ADMIN  — cross-user reads; require X-Admin-Token == config.ADMIN_TOKEN.
#   COHORT — creator actions (spends money / reads own data); require a valid
#            X-Invite-Code, but only enforced when INVITE_CODES is configured
#            (mirrors the WS gate: dev/test with empty INVITE_CODES stays open).
OPEN_ROUTES: frozenset[tuple[str, str]] = frozenset({
    ("POST", "/api/client_error"),
    ("GET", "/api/health"),
    ("GET", "/api/stats/public"),
    ("GET", "/api/invite/verify"),  # pre-flight gate check; must be reachable pre-auth
})
ADMIN_ROUTES: frozenset[tuple[str, str]] = frozenset({
    ("GET", "/api/events"),
    ("GET", "/api/creators"),
    ("GET", "/api/health/summary"),
})


def _check_auth(method: str, path: str, headers: dict[str, str]) -> tuple[int, dict, str] | None:
    """Return an error response tuple if the request is unauthorized, else None.

    `headers` keys are already lowercased by the dispatcher.
    """
    key = (method, path)
    if key in OPEN_ROUTES:
        return None
    if key in ADMIN_ROUTES:
        if not config.ADMIN_TOKEN:
            # No token configured: open in dev, fail-closed in prod so admin
            # data is never silently world-readable on a real deploy.
            if config.IS_PROD_LIKE:
                return 403, {"error": "admin_not_configured"}, "Forbidden"
            return None
        if headers.get("x-admin-token", "") == config.ADMIN_TOKEN:
            return None
        return 401, {"error": "admin_token_required"}, "Unauthorized"
    # COHORT (default)
    if not config.INVITE_CODES:
        return None  # dev/test: gate disabled
    if headers.get("x-invite-code", "") in config.INVITE_CODES:
        return None
    return 401, {"error": "invite_code_required"}, "Unauthorized"


def _match(method: str, path: str) -> tuple[HandlerFn | None, dict]:
    handler = EXACT_ROUTES.get((method, path))
    if handler is not None:
        return handler, {}
    for m, prefix, suffix, name, handler in PARAM_ROUTES:
        if m == method and path.startswith(prefix) and path.endswith(suffix) and len(path) > len(prefix) + len(suffix):
            param = path[len(prefix):-len(suffix)]
            return handler, {name: param}
    return None, {}


# ---------- dispatcher ----------


async def handle_http(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        # Slowloris guard: cap total time spent reading the request. A client
        # that opens a socket and dribbles bytes can otherwise pin this task
        # forever (readuntil/readexactly have no timeout of their own).
        header_bytes = await asyncio.wait_for(
            reader.readuntil(b"\r\n\r\n"), timeout=HTTP_READ_TIMEOUT_S
        )
        header_text = header_bytes.decode("iso-8859-1")
        first_line, *header_lines = header_text.split("\r\n")
        method, path, _ = first_line.split(" ", 2)
        headers: dict[str, str] = {}
        for line in header_lines:
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip().lower()] = v.strip()
        content_length = int(headers.get("content-length", "0") or "0")
        body_bytes = (
            await asyncio.wait_for(reader.readexactly(content_length), timeout=HTTP_READ_TIMEOUT_S)
            if content_length
            else b"{}"
        )

        # P1 fix: malformed JSON body 返 400 而非 500
        try:
            body = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            writer.write(_http_response(400, {"error": f"malformed_json: {exc}"}, "Bad Request"))
            await writer.drain()
            return
        if not isinstance(body, dict):
            writer.write(_http_response(400, {"error": "body must be a JSON object"}, "Bad Request"))
            await writer.drain()
            return

        parsed = urlparse(path)
        route_path = parsed.path
        qs = parse_qs(parsed.query)

        handler, path_params = _match(method, route_path)
        if handler is None:
            writer.write(_http_response(404, {"error": "not_found"}, "Not Found"))
            await writer.drain()
            return

        auth_error = _check_auth(method, route_path, headers)
        if auth_error is not None:
            a_status, a_body, a_reason = auth_error
            writer.write(_http_response(a_status, a_body, a_reason))
            await writer.drain()
            return

        status, response_body, reason = await handler(qs, body, **path_params)
        writer.write(_http_response(status, response_body, reason))
        await writer.drain()

    except (asyncio.TimeoutError, asyncio.IncompleteReadError, asyncio.LimitOverrunError):
        # Slow/oversized/broken request — close quietly without a full response.
        pass
    except HardFailure as exc:
        status = 503 if exc.code.value == "S8_UPSTREAM_REFUSED" else 422
        writer.write(_http_response(status, error_payload(exc), "Unprocessable Entity"))
        await writer.drain()
    except LookupError as exc:
        writer.write(_http_response(404, error_payload(exc), "Not Found"))
        await writer.drain()
    except Exception as exc:
        writer.write(_http_response(500, {"error": str(exc)}, "Internal Server Error"))
        await writer.drain()
    finally:
        writer.close()
        await writer.wait_closed()
