"""WS handler 单元测试 — 覆盖 server.handle() 的 auth / list / get_state / delete /
unknown / malformed / rename(回归)路径。

P1 fix verify(QA W4D2):
  - malformed JSON 不再 close 1011,而是回 type=error code=malformed_json + 保活
P2 fix verify:
  - list_sessions 无 thread_id 仍回 session_list(不被 thread_id 检查吞掉)
  - delete_session 之后会 push 新的 session_list 作为 ACK
回归:
  - rename_session 已删,发送应 silently dropped + 连接存活

测试用直接 await `handle(fake_ws)` + FakeWebSocket 收发,
不起真实 server,不依赖 LLM/工具调用。
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from agent import server
from agent.transport import notify
from agent.workers import generation_worker


class FakeWebSocket:
    """模拟 websockets.ServerConnection,够喂给 server.handle()。

    - 用 incoming list 模拟 client 推过来的消息(handle 里 `async for raw in ws`)
    - send(data) 把字符串 capture 到 self.sent
    - close(code, reason) 标记 self.closed = (code, reason)
    """

    def __init__(self, incoming: list[str | bytes]):
        self._incoming = list(incoming)
        self._idx = 0
        self.sent: list[dict] = []
        self.closed: tuple[int, str] | None = None

    def __aiter__(self):
        return self

    async def __anext__(self):
        # close 之后停止 iterate
        if self.closed is not None:
            raise StopAsyncIteration
        if self._idx >= len(self._incoming):
            raise StopAsyncIteration
        item = self._incoming[self._idx]
        self._idx += 1
        return item

    async def send(self, data: str):
        # capture 成 dict 方便 assert
        try:
            self.sent.append(json.loads(data))
        except json.JSONDecodeError:
            self.sent.append({"_raw": data})

    async def close(self, code: int = 1000, reason: str = ""):
        self.closed = (code, reason)


# ---------- fixtures ----------


@pytest.fixture
def isolated_ws(monkeypatch, tmp_path):
    """每个 test 用独立 tmp DB + 干净 _ws_registry + 不启动 background worker。

    注:W4D3 重构后,_ws_registry 移到 agent.transport.notify;_start_worker 移到
    agent.workers.generation_worker.start_workers。tests 直接 patch 那两个 module。
    """
    db_path = tmp_path / "messages.db"

    # store.py 用 module-level _DB_PATH 常量,需要直接改它
    from agent import store

    monkeypatch.setattr(store, "_DB_PATH", db_path)
    monkeypatch.setattr(store, "_DB_DIR", tmp_path)

    # cascade 持久化 DB(analyses/rewrites/session_results/shot_assets/...)也要隔离,
    # 否则跨 test 污染:别的 test 写的 pointer/shot_asset 会被本 test 的 _replay_results
    # 读出来,多推帧。db_path() 优先读 CASCADE_DB_PATH。
    monkeypatch.setenv("CASCADE_DB_PATH", str(tmp_path / "cascade.db"))

    # _ws_registry 是 module global dict,需要隔离避免 test 互相污染
    monkeypatch.setattr(notify, "_ws_registry", {})

    # start_workers 启动 background tasks,test 里不需要
    monkeypatch.setattr(generation_worker, "start_workers", lambda: None)

    yield


def _run(coro):
    """通用 asyncio.run wrapper(避免每个 test 重写)。"""
    return asyncio.run(coro)


# ---------- 测试 ----------


def test_auth_happy_path_sends_session_list(isolated_ws):
    """auth 成功 → 应自动收到 session_list 帧;session_list 已 send 本身就证明 auth 走通了。

    (handle finally 会 pop user_id from _ws_registry,所以 post-handle 时 registry 已清。)
    """
    ws = FakeWebSocket([json.dumps({"type": "auth", "user_id": "u1"})])
    _run(server.handle(ws))

    assert ws.closed is None, "auth 成功不应 close"
    assert len(ws.sent) == 1
    assert ws.sent[0]["type"] == "session_list"
    assert "sessions" in ws.sent[0]


def test_auth_registers_user_during_call(isolated_ws):
    """单独测 auth 写 _ws_registry — 在 send 回调里 capture registry snapshot。"""
    captured: dict = {}

    class HookedWS(FakeWebSocket):
        async def send(self, data):
            captured["registry_keys"] = list(notify._ws_registry.keys())
            await super().send(data)

    ws = HookedWS([json.dumps({"type": "auth", "user_id": "u1"})])
    _run(server.handle(ws))

    assert captured.get("registry_keys") == ["u1"]
    # handle 退出后会清理
    assert "u1" not in notify._ws_registry


def test_auth_missing_user_id_closes_4001(isolated_ws):
    """auth 缺 user_id → close(4001, 'user_id required')。"""
    ws = FakeWebSocket([json.dumps({"type": "auth", "user_id": ""})])
    _run(server.handle(ws))

    assert ws.closed == (4001, "user_id required")
    assert ws.sent == []


def test_unauth_message_closes_4001(isolated_ws):
    """没 auth 直接发非-auth 消息 → close(4001, '未认证')。"""
    ws = FakeWebSocket([json.dumps({"type": "list_sessions", "thread_id": "t1"})])
    _run(server.handle(ws))

    assert ws.closed == (4001, "未认证")
    assert ws.sent == []


def test_malformed_json_sends_error_frame_keeps_conn(isolated_ws):
    """P1 fix verify:malformed JSON 不再 close 1011,而是回 error 帧 + 保活。

    auth 成功后再发坏 JSON,然后发 list_sessions 应仍能正常收到 session_list。
    """
    ws = FakeWebSocket([
        json.dumps({"type": "auth", "user_id": "u1"}),  # 1. auth ok → session_list
        "{not valid json",                                # 2. malformed → error 帧
        json.dumps({"type": "list_sessions"}),            # 3. 仍能正常工作 → session_list
    ])
    _run(server.handle(ws))

    # 不应有 close
    assert ws.closed is None, "malformed JSON 应保活,不应 close 1011"
    # 应有 3 个 send: session_list (auth) + error + session_list (list_sessions)
    assert len(ws.sent) == 3
    assert ws.sent[0]["type"] == "session_list"
    assert ws.sent[1]["type"] == "error"
    assert ws.sent[1]["code"] == "malformed_json"
    assert ws.sent[2]["type"] == "session_list"


def test_non_dict_json_silently_dropped(isolated_ws):
    """JSON 解出来不是 dict(如数字、字符串、数组)→ 静默 drop,不崩,不回包。"""
    ws = FakeWebSocket([
        json.dumps({"type": "auth", "user_id": "u1"}),
        json.dumps(42),         # 数字
        json.dumps([1, 2, 3]),  # 数组
        json.dumps({"type": "list_sessions"}),
    ])
    _run(server.handle(ws))

    assert ws.closed is None
    # auth 回 session_list + list_sessions 回 session_list = 2 个 send,非 dict 不回
    assert len(ws.sent) == 2
    assert all(m["type"] == "session_list" for m in ws.sent)


def test_list_sessions_without_thread_id_returns_session_list(isolated_ws):
    """P2 fix verify:list_sessions 没 thread_id 应正常回 session_list
    (不应被 `if not thread_id: continue` 静默 drop)。"""
    ws = FakeWebSocket([
        json.dumps({"type": "auth", "user_id": "u1"}),
        json.dumps({"type": "list_sessions"}),  # 无 thread_id
    ])
    _run(server.handle(ws))

    assert ws.closed is None
    assert len(ws.sent) == 2
    assert ws.sent[0]["type"] == "session_list"  # auth 自动下发
    assert ws.sent[1]["type"] == "session_list"  # list_sessions 显式请求


def test_get_session_state_returns_messages_and_canvas(isolated_ws):
    """get_session_state → 收到 session_state{messages, canvas, thread_id}。"""
    ws = FakeWebSocket([
        json.dumps({"type": "auth", "user_id": "u1"}),
        json.dumps({"type": "get_session_state", "thread_id": "t1"}),
    ])
    _run(server.handle(ws))

    assert ws.closed is None
    assert len(ws.sent) == 2
    state = ws.sent[1]
    assert state["type"] == "session_state"
    assert state["thread_id"] == "t1"
    assert state["messages"] == []  # 新 session 应该空
    # canvas 可能为 None(新 session 无节点),不强 assert 内容,只 assert 字段存在
    assert "canvas" in state


def test_get_session_state_replays_analysis_and_rewrite(isolated_ws, monkeypatch):
    """W5D4: a finished thread with stored results re-pushes analysis_returned +
    rewrite_returned after session_state, so a reload renders the cards."""
    from agent.transport import ws_handlers

    class _FakeContract:
        analysis_id = "ana_test123"

        def model_dump(self, mode="json"):
            return {"analysis_id": self.analysis_id, "scenes": []}

    async def _fake_pointers(user_id, thread_id):
        assert thread_id == "t1"
        return "ana_test123", "rw_test456"

    async def _fake_load_analysis(analysis_id):
        assert analysis_id == "ana_test123"
        return _FakeContract()

    async def _fake_load_rewrite(rewrite_id):
        assert rewrite_id == "rw_test456"
        return json.dumps({"rewrite_id": rewrite_id, "analysis_id": "ana_test123", "shots": []})

    monkeypatch.setattr(ws_handlers.cascade_storage, "load_pointers", _fake_pointers)
    monkeypatch.setattr(ws_handlers.cascade_storage, "load_analysis", _fake_load_analysis)
    monkeypatch.setattr(ws_handlers.cascade_storage, "load_rewrite_by_id", _fake_load_rewrite)

    ws = FakeWebSocket([
        json.dumps({"type": "auth", "user_id": "u1"}),
        json.dumps({"type": "get_session_state", "thread_id": "t1"}),
    ])
    _run(server.handle(ws))

    # auth→session_list, then session_state + analysis_returned + rewrite_returned
    types = [m.get("type") for m in ws.sent]
    assert types == ["session_list", "session_state", "analysis_returned", "rewrite_returned"]
    assert ws.sent[2]["analysis"]["analysis_id"] == "ana_test123"
    assert ws.sent[3]["analysis_id"] == "ana_test123"
    assert ws.sent[3]["rewrite"]["rewrite_id"] == "rw_test456"


def test_get_session_state_no_results_no_replay(isolated_ws, monkeypatch):
    """W5D4: a thread with no stored results sends only session_state (no replay)."""
    from agent.transport import ws_handlers

    async def _no_pointers(user_id, thread_id):
        return None, None

    monkeypatch.setattr(ws_handlers.cascade_storage, "load_pointers", _no_pointers)

    ws = FakeWebSocket([
        json.dumps({"type": "auth", "user_id": "u1"}),
        json.dumps({"type": "get_session_state", "thread_id": "t1"}),
    ])
    _run(server.handle(ws))

    types = [m.get("type") for m in ws.sent]
    assert types == ["session_list", "session_state"]


def test_delete_session_sends_session_list_ack(isolated_ws):
    """P2 fix verify:delete_session 之后应 push 新的 session_list 作为 ACK,
    且被删除的 session 不再出现在列表中。"""
    from agent.store import ensure_session_exists

    ensure_session_exists("u1", "t-keep")
    ensure_session_exists("u1", "t-delete")

    ws = FakeWebSocket([
        json.dumps({"type": "auth", "user_id": "u1"}),
        json.dumps({"type": "delete_session", "thread_id": "t-delete"}),
    ])
    _run(server.handle(ws))

    assert ws.closed is None
    # 期待 2 个 send:auth 后的 session_list(含 2 个 session)+ delete 后的 ACK session_list(含 1 个)
    assert len(ws.sent) == 2
    assert ws.sent[0]["type"] == "session_list"
    assert ws.sent[1]["type"] == "session_list"

    # ACK 的 session_list 不应包含 t-delete
    ack_thread_ids = {s["thread_id"] for s in ws.sent[1]["sessions"]}
    assert "t-delete" not in ack_thread_ids
    assert "t-keep" in ack_thread_ids


def test_delete_sessions_bulk_acks_once(isolated_ws):
    """delete_sessions 批量软删:一条命令 → 一条 session_list ACK(非 N 条),
    所有被删的都不在列表里,保留项还在。"""
    from agent.store import ensure_session_exists

    for t in ("t-keep", "t-del1", "t-del2", "t-del3"):
        ensure_session_exists("u1", t)

    ws = FakeWebSocket([
        json.dumps({"type": "auth", "user_id": "u1"}),
        json.dumps({"type": "delete_sessions", "thread_ids": ["t-del1", "t-del2", "t-del3"]}),
    ])
    _run(server.handle(ws))

    assert ws.closed is None
    # auth 后的 session_list + 批量删后的「一条」ACK —— 不是 3 条。
    assert len(ws.sent) == 2
    assert ws.sent[1]["type"] == "session_list"
    ack_ids = {s["thread_id"] for s in ws.sent[1]["sessions"]}
    assert ack_ids.isdisjoint({"t-del1", "t-del2", "t-del3"})
    assert "t-keep" in ack_ids


def test_unknown_msg_type_silently_dropped(isolated_ws):
    """未知 msg_type → 静默 drop,连接存活,后续消息仍能正常处理。"""
    ws = FakeWebSocket([
        json.dumps({"type": "auth", "user_id": "u1"}),
        json.dumps({"type": "this_does_not_exist", "thread_id": "t1"}),
        json.dumps({"type": "list_sessions"}),
    ])
    _run(server.handle(ws))

    assert ws.closed is None
    # auth → session_list,unknown 不回,list_sessions → session_list = 2 个
    assert len(ws.sent) == 2
    assert all(m["type"] == "session_list" for m in ws.sent)


def test_rename_session_regression_silently_dropped(isolated_ws):
    """回归:rename_session 已删,发送 → 静默 drop + 连接存活 + 后续消息正常。

    这是 commit 92f40ec 删 rename_session 的回归测试。
    """
    ws = FakeWebSocket([
        json.dumps({"type": "auth", "user_id": "u1"}),
        json.dumps({"type": "rename_session", "thread_id": "t1", "name": "新名"}),
        json.dumps({"type": "list_sessions"}),
    ])
    _run(server.handle(ws))

    assert ws.closed is None
    assert len(ws.sent) == 2
    assert all(m["type"] == "session_list" for m in ws.sent)


def test_invite_reject_does_not_log_plaintext_code(isolated_ws, monkeypatch, capsys):
    """B8 regression: a rejected invite code must never appear in plaintext logs.

    The reject path logs only a sha256[:8] fingerprint + length, so the raw
    secret can't be harvested from log access. We assert the secret string is
    absent from stdout and that the fingerprint is present instead.
    """
    import hashlib

    from agent import config

    secret = "S3CRET-INVITE-XYZ"
    monkeypatch.setattr(config, "INVITE_CODES", frozenset({"GOOD-CODE"}))

    ws = FakeWebSocket([
        json.dumps({"type": "auth", "user_id": "u1", "invite_code": secret}),
    ])
    _run(server.handle(ws))

    # Rejected with the invite-code close code, nothing sent back.
    assert ws.closed == (4003, "invite code required")
    assert ws.sent == []

    out = capsys.readouterr().out
    # The raw secret must NOT leak to logs.
    assert secret not in out
    # A non-reversible fingerprint must be present so attempts stay correlatable.
    expected_fp = hashlib.sha256(secret.encode("utf-8")).hexdigest()[:8]
    assert expected_fp in out


def test_invite_accept_still_works_after_redaction(isolated_ws, monkeypatch):
    """B8 regression: redacting the log must not change the gate decision —
    a valid code still authenticates and gets a session_list."""
    from agent import config

    monkeypatch.setattr(config, "INVITE_CODES", frozenset({"GOOD-CODE"}))

    ws = FakeWebSocket([
        json.dumps({"type": "auth", "user_id": "u1", "invite_code": "GOOD-CODE"}),
    ])
    _run(server.handle(ws))

    assert ws.closed is None
    assert len(ws.sent) == 1
    assert ws.sent[0]["type"] == "session_list"
