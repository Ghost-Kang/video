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
from typing import Awaitable, Callable
from urllib.parse import parse_qs, urlparse

from pydantic import ValidationError

from agent.cascade import cost_guard
from agent.cascade.analysis_service import request_shallow_analysis
from agent.cascade.anchors import create_anchor, list_anchors, list_reuses, reuse_anchor
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
        "generation_cost",
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
        "generation_cost",
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
