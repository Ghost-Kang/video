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

from agent.cascade import cost_guard
from agent.cascade.analysis_service import request_shallow_analysis
from agent.cascade.anchors import create_anchor, list_anchors, list_reuses, reuse_anchor
from agent.cascade.event_names import EventName
from agent.cascade.events import emit
from agent.cascade.failures import HardFailure
from agent.cascade.rewrite_service import error_payload, request_rewrite
from agent.cascade.storage import list_creators, list_events


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
    result = await request_rewrite(
        analysis_id=str(body.get("analysis_id") or ""),
        niche=body.get("niche"),
        user_id=user_id,
        run_id=run_id,
    )
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
            "latency_ms": 0,
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
    contract = await request_shallow_analysis(source_url, user_id=user_id, run_id=run_id)
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
            "latency_ms": 0,
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
    recent_failures: list[dict] = []
    by_type: dict[str, int] = {}
    total_5min = 0
    upstream: dict[str, float | None] = {
        EventName.ANALYSIS_RETURNED.value: None,
        EventName.SCRIPT_REWRITTEN.value: None,
    }

    try:
        # 5min events grouped by event_name
        five = await list_events(limit=500, since_ts=five_min_ago)
        for e in five.get("events", []):
            by_type[e["event_name"]] = by_type.get(e["event_name"], 0) + 1
            total_5min += 1

        # 1h upstream success rate
        hour = await list_events(limit=1000, since_ts=one_hour_ago)
        an_done = sum(1 for e in hour.get("events", []) if e["event_name"] == EventName.ANALYSIS_RETURNED.value)
        an_fail = sum(
            1 for e in hour.get("events", [])
            if e["event_name"] == EventName.FAILURE_EMITTED.value
            and isinstance(e.get("payload"), dict)
            and e["payload"].get("stage") == "analysis"
        )
        if an_done + an_fail > 0:
            upstream[EventName.ANALYSIS_RETURNED.value] = round(an_done / (an_done + an_fail), 3)
        rw_done = sum(1 for e in hour.get("events", []) if e["event_name"] == EventName.SCRIPT_REWRITTEN.value)
        rw_fail = sum(
            1 for e in hour.get("events", [])
            if e["event_name"] == EventName.FAILURE_EMITTED.value
            and isinstance(e.get("payload"), dict)
            and e["payload"].get("stage") == "rewrite"
        )
        if rw_done + rw_fail > 0:
            upstream[EventName.SCRIPT_REWRITTEN.value] = round(rw_done / (rw_done + rw_fail), 3)

        # recent 10 failures
        fails = await list_events(limit=10, event_name=EventName.FAILURE_EMITTED.value)
        recent_failures = fails.get("events", [])[:10]
    except Exception:
        pass  # health endpoint must not crash — return what we have

    return 200, {
        "server": {
            "cpu_percent": cpu_percent,
            "mem_used_mb": mem_used_mb,
            "mem_total_mb": mem_total_mb,
            "disk_used_gb": disk_used_gb,
            "disk_total_gb": disk_total_gb,
            "uptime_seconds": uptime,
        },
        "events_5min": {"total": total_5min, "by_type": by_type},
        "upstream_success_rate": upstream,
        "recent_failures": recent_failures,
    }, "OK"


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
    ("GET", "/api/health/summary"): handle_health_summary,
}

# (method, prefix, suffix, param_name, handler) — 路径里的可变段会作为 path_param 传入。
PARAM_ROUTES: list[tuple[str, str, str, str, HandlerFn]] = [
    ("GET", "/api/anchors/", "/reuses", "anchor_id", handle_anchor_reuses),
    ("POST", "/api/anchors/", "/reuse", "anchor_id", handle_anchor_reuse_post),
]


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
        header_bytes = await reader.readuntil(b"\r\n\r\n")
        header_text = header_bytes.decode("iso-8859-1")
        first_line, *header_lines = header_text.split("\r\n")
        method, path, _ = first_line.split(" ", 2)
        headers: dict[str, str] = {}
        for line in header_lines:
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip().lower()] = v.strip()
        content_length = int(headers.get("content-length", "0") or "0")
        body_bytes = await reader.readexactly(content_length) if content_length else b"{}"

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

        status, response_body, reason = await handler(qs, body, **path_params)
        writer.write(_http_response(status, response_body, reason))
        await writer.drain()

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
