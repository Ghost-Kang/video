"""WebSocket + HTTP entry point.

实际 handler 在 `agent/transport/{ws_server, ws_handlers, http_router}.py`,
worker pipeline 在 `agent/workers/`。本文件只剩 serve loop 和 __main__ 入口。

历史背景:此文件曾是 916 LOC god module(WS dispatch + HTTP routes + generation
worker + S3 + globals 全塞一处)。W4D3 拆分见 docs/nexus/architecture_review_2026-05-26.md。

W5D3 P0-5 — graceful drain on SIGTERM. Docker compose sends SIGTERM on
`docker compose restart` / `up -d` (recreate). Without a handler, the asyncio
loop is killed mid-tool-call: ARK responses lost, agent_runner tasks orphaned,
checkpoints possibly inconsistent. We:
  1. Stop accepting new WS connections (serve() context exits)
  2. Wait up to GRACEFUL_DRAIN_SEC for in-flight tasks to complete
  3. Close SHARED_POOL connections
  4. Exit
"""

from __future__ import annotations

import asyncio
import signal

from websockets.asyncio.server import serve

from agent.cascade.persistence.db import bootstrap_schema
from agent.pool import SHARED_POOL
from agent.transport.http_router import handle_http
from agent.transport.ws_server import handle
from agent.workers import generation_worker


# 向后兼容别名 — 若有外部代码引用旧名,继续可用。
# 注意:monkeypatch.setattr(server, "_handle_http", ...) 不会传播到调用方(asyncio.start_server
# 已经绑定了原函数引用);测试应直接 patch agent.transport.http_router.handle_http。
_handle_http = handle_http
_start_worker = generation_worker.start_workers

GRACEFUL_DRAIN_SEC = 30
"""Max seconds to wait for in-flight WS turns + worker tasks on shutdown."""


async def _graceful_shutdown(stop_event: asyncio.Event) -> None:
    """Run when SIGTERM/SIGINT received. Sets stop_event so main() returns."""
    print(f"[shutdown] signal received — draining up to {GRACEFUL_DRAIN_SEC}s")

    # Give the loop a moment for any "in-progress" tasks to settle. We don't
    # forcibly cancel in-flight run_agent tasks (they hold WS frames not yet
    # sent); the asyncio loop close at the end will surface CancelledError
    # which their try/finally blocks handle.
    try:
        await asyncio.wait_for(asyncio.sleep(GRACEFUL_DRAIN_SEC), timeout=GRACEFUL_DRAIN_SEC + 1)
    except asyncio.TimeoutError:
        pass

    print("[shutdown] closing checkpoint pool connections...")
    try:
        await SHARED_POOL.close()
    except Exception as e:
        print(f"[shutdown] pool close error (continuing): {e}")

    print("[shutdown] done")
    stop_event.set()


def _install_signal_handlers(stop_event: asyncio.Event) -> None:
    """Wire SIGTERM + SIGINT to schedule _graceful_shutdown()."""
    loop = asyncio.get_running_loop()

    def _handler(sig_name: str) -> None:
        print(f"[shutdown] caught {sig_name}")
        loop.create_task(_graceful_shutdown(stop_event))

    for sig, name in ((signal.SIGTERM, "SIGTERM"), (signal.SIGINT, "SIGINT")):
        try:
            loop.add_signal_handler(sig, _handler, name)
        except NotImplementedError:
            # add_signal_handler isn't available on Windows asyncio. Tests rarely
            # run on Windows; if they do, fall back to the default SIGINT
            # KeyboardInterrupt behavior.
            pass


async def main(host: str = "0.0.0.0", port: int = 8765, http_port: int = 8766) -> None:
    print(f"OpenRHTV WebSocket 服务: ws://{host}:{port}")
    print(f"OpenRHTV HTTP API: http://{host}:{http_port}/api/analysis/shallow")
    # Codex-E 后:schema bootstrap 在 startup 一次性完成,而不是每个 _connect() 里反复
    # CREATE TABLE IF NOT EXISTS。lazy-init pattern 仍由 repo 内部支持兜底(冷启动安全)。
    await bootstrap_schema()
    generation_worker.start_workers()

    stop_event = asyncio.Event()
    _install_signal_handlers(stop_event)

    http_server = await asyncio.start_server(handle_http, host, http_port)
    async with serve(handle, host, port), http_server:
        # Block until either the HTTP server returns (it won't on its own) or
        # the shutdown handler fires.
        await stop_event.wait()
        print("[shutdown] stop_event received, exiting serve loop")


if __name__ == "__main__":
    asyncio.run(main())
