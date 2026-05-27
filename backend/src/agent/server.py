"""WebSocket + HTTP entry point.

实际 handler 在 `agent/transport/{ws_server, ws_handlers, http_router}.py`,
worker pipeline 在 `agent/workers/`。本文件只剩 serve loop 和 __main__ 入口。

历史背景:此文件曾是 916 LOC god module(WS dispatch + HTTP routes + generation
worker + S3 + globals 全塞一处)。W4D3 拆分见 docs/nexus/architecture_review_2026-05-26.md。
"""

from __future__ import annotations

import asyncio

from websockets.asyncio.server import serve

from agent.cascade.persistence.db import bootstrap_schema
from agent.transport.http_router import handle_http
from agent.transport.ws_server import handle
from agent.workers import generation_worker


# 向后兼容别名 — 若有外部代码引用旧名,继续可用。
# 注意:monkeypatch.setattr(server, "_handle_http", ...) 不会传播到调用方(asyncio.start_server
# 已经绑定了原函数引用);测试应直接 patch agent.transport.http_router.handle_http。
_handle_http = handle_http
_start_worker = generation_worker.start_workers


async def main(host: str = "0.0.0.0", port: int = 8765, http_port: int = 8766) -> None:
    print(f"OpenRHTV WebSocket 服务: ws://{host}:{port}")
    print(f"OpenRHTV HTTP API: http://{host}:{http_port}/api/analysis/shallow")
    # Codex-E 后:schema bootstrap 在 startup 一次性完成,而不是每个 _connect() 里反复
    # CREATE TABLE IF NOT EXISTS。lazy-init pattern 仍由 repo 内部支持兜底(冷启动安全)。
    await bootstrap_schema()
    generation_worker.start_workers()
    http_server = await asyncio.start_server(handle_http, host, http_port)
    async with serve(handle, host, port), http_server:
        await asyncio.gather(
            http_server.serve_forever(),
            asyncio.get_running_loop().create_future(),
        )


if __name__ == "__main__":
    asyncio.run(main())
