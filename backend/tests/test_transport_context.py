"""transport/context.py unit tests.

WSCtx dataclass + send_json + canvas_data — 全是 W4D3 Claude-A 拆出来的小 helper,
但 send_json 是所有 outbound 帧的单点写入,canvas_data 喂给前端 every canvas_updated
事件,值得直接 unit 保护。
"""

from __future__ import annotations

import asyncio
import json
import uuid

import pytest

from agent.pool import AgentPool
from agent.tools import canvas as canvas_tools
from agent.transport.context import WSCtx, canvas_data, send_json


class FakeWS:
    """async send + 收集 payload — 不起真 WS。"""

    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send(self, data: str) -> None:
        self.sent.append(data)


def _unique_thread() -> str:
    return f"ctx-test-{uuid.uuid4().hex[:8]}"


# ---------- WSCtx dataclass ----------


class TestWSCtx:
    def test_holds_user_ws_pool(self):
        ws = FakeWS()
        pool = AgentPool(max_size=1)
        ctx = WSCtx(user_id="u1", ws=ws, pool=pool)
        assert ctx.user_id == "u1"
        assert ctx.ws is ws
        assert ctx.pool is pool

    def test_dataclass_equality(self):
        ws = FakeWS()
        pool = AgentPool(max_size=1)
        a = WSCtx(user_id="u1", ws=ws, pool=pool)
        b = WSCtx(user_id="u1", ws=ws, pool=pool)
        assert a == b


# ---------- send_json ----------


class TestSendJson:
    def test_writes_json_frame(self):
        ws = FakeWS()
        asyncio.run(send_json(ws, type="session_list", sessions=[]))
        assert len(ws.sent) == 1
        decoded = json.loads(ws.sent[0])
        assert decoded == {"type": "session_list", "sessions": []}

    def test_preserves_chinese_characters(self):
        """ensure_ascii=False — 中文 title 不应被 \\uxxxx escape。"""
        ws = FakeWS()
        asyncio.run(send_json(ws, type="error", code="invalid_command", message="请求格式不对"))
        # 直接看字符串里有没有汉字,避免 escape 走 \\u4e00 这种
        assert "请求格式不对" in ws.sent[0]
        # 再 round-trip 一次确认 JSON 还是 well-formed
        decoded = json.loads(ws.sent[0])
        assert decoded["message"] == "请求格式不对"

    def test_multiple_kwargs(self):
        ws = FakeWS()
        asyncio.run(send_json(
            ws,
            type="canvas_updated",
            thread_id="t1",
            canvas={"nodes": {}, "edges": []},
        ))
        decoded = json.loads(ws.sent[0])
        assert decoded["type"] == "canvas_updated"
        assert decoded["thread_id"] == "t1"
        assert decoded["canvas"]["nodes"] == {}

    def test_empty_kwargs(self):
        ws = FakeWS()
        asyncio.run(send_json(ws))
        assert json.loads(ws.sent[0]) == {}


# ---------- canvas_data ----------


class TestCanvasData:
    def test_empty_thread_returns_none(self):
        # 全新 thread,无节点 → None
        tid = _unique_thread()
        result = canvas_data(tid)
        assert result is None

    def test_with_nodes_returns_nodes_and_edges(self):
        """create_canvas_node + 读取 canvas_data 验证 round-trip。"""
        tid = _unique_thread()
        canvas_tools.set_thread_id(tid)
        canvas_tools.create_canvas_node("script", "测试", "描述")

        result = canvas_data(tid)
        assert result is not None
        assert "nodes" in result
        assert "edges" in result
        assert len(result["nodes"]) == 1

    def test_sets_context_var_side_effect(self):
        """canvas_data 内部会 set_thread_id — 验证 side effect。"""
        tid = _unique_thread()
        canvas_data(tid)
        # 内部已经 set;再调一次 _load_all_nodes 应该用同 thread_id
        assert canvas_tools._current_thread_id.get() == tid


# ---------- W5D3 P0-3 — per-WS send lock ----------


class TestSendJsonLock:
    def test_concurrent_sends_are_serialized(self):
        """W5D3 P0-3: send_json must serialize concurrent writes per connection.

        Without the lock, two `await ws.send(...)` calls scheduled on different
        asyncio tasks could interleave bytes in the underlying socket buffer.
        We model this by recording start+end of each send and asserting they
        don't overlap.
        """
        import asyncio
        from agent.transport.context import send_json

        events: list[tuple[str, int]] = []

        class TimedWS:
            def __init__(self) -> None:
                self.counter = 0

            async def send(self, data: str) -> None:
                self.counter += 1
                my_id = self.counter
                events.append(("start", my_id))
                await asyncio.sleep(0.01)  # simulate slow socket write
                events.append(("end", my_id))

        async def _run():
            ws = TimedWS()
            await asyncio.gather(
                send_json(ws, type="a", thread_id="t"),
                send_json(ws, type="b", thread_id="t"),
                send_json(ws, type="c", thread_id="t"),
            )
            return ws

        asyncio.run(_run())

        # Each (start, n) must be immediately followed by (end, n) — no interleaving.
        for i in range(0, len(events), 2):
            assert events[i][0] == "start", f"events[{i}] = {events[i]}"
            assert events[i + 1][0] == "end", f"events[{i+1}] = {events[i+1]}"
            assert events[i][1] == events[i + 1][1], "send not atomic"
