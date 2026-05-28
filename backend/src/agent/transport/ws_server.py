"""WS accept loop + auth gate + dispatch。

`handle(websocket)` 是入口:
1. 第一帧必须是 auth → 设置 user_id + register + 启动 workers + 自动下发 session_list
2. 后续帧按 msg.type 查 HANDLERS dict 分派
3. malformed JSON 不 close,回 error 帧保活(P1 fix)
4. non-dict / 未知 type 静默 drop
5. 未 auth 发其他消息 → close(4001)
"""

from __future__ import annotations

import json

from pydantic import ValidationError
from websockets.exceptions import ConnectionClosedOK

from agent import config, store  # 通过 module 访问,方便 test monkeypatch
from agent.pool import AgentPool
from agent.tools import canvas as canvas_tools
from agent.transport import notify
from agent.transport.context import WSCtx, send_json
from agent.transport.ws_handlers import HANDLERS
from agent.transport.ws_messages import AuthMsg
from agent.workers import generation_worker  # module 访问同理


POOL_SIZE = 5


async def handle(websocket) -> None:
    pool = AgentPool(max_size=POOL_SIZE)
    user_id: str | None = None
    ctx: WSCtx | None = None
    print("[连接] 新连接,等待 auth...")

    try:
        async for raw in websocket:
            # P1 fix: malformed JSON 不再 crash 1011,回 error 帧保活。
            try:
                msg = json.loads(raw)
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                print(f"[MSG] malformed JSON dropped: {exc}")
                try:
                    await send_json(websocket, type="error", code="malformed_json", message=str(exc))
                except Exception:
                    pass
                continue

            if not isinstance(msg, dict):
                print(f"[MSG] non-dict payload dropped: {type(msg).__name__}")
                continue

            msg_type = msg.get("type")
            print(f"[MSG] type={msg_type} thread={msg.get('thread_id', '?')} user={user_id or '(未认证)'}")

            # 首条必须是 auth
            if msg_type == "auth":
                try:
                    auth = AuthMsg.model_validate(msg)
                except ValidationError:
                    # 空 user_id / missing user_id / 多余字段 — 关闭(test 期望 4001)
                    await websocket.close(4001, "user_id required")
                    return
                # 内测准入码 gate — 仅在 INVITE_CODES 非空时强制 (production)。
                # Dev/test 默认空集 = 任何 user 可接入,保留原行为。
                if config.INVITE_CODES and auth.invite_code not in config.INVITE_CODES:
                    print(f"[连接] 拒 user={auth.user_id} 无效 invite_code={auth.invite_code!r}")
                    await websocket.close(4003, "invite code required")
                    return
                user_id = auth.user_id
                canvas_tools.set_user_id(user_id)
                notify.register(user_id, websocket)
                generation_worker.start_workers()
                ctx = WSCtx(user_id=user_id, ws=websocket, pool=pool)
                print(f"[连接] user={user_id} pool 上限 {POOL_SIZE}")
                # auth 后自动下发会话列表
                sessions = store.list_sessions(user_id)
                await send_json(websocket, type="session_list", sessions=sessions)
                continue

            if not user_id or ctx is None:
                await websocket.close(4001, "未认证")
                return

            entry = HANDLERS.get(msg_type or "")
            if entry is None:
                # 未知 type silently drop(rename_session 回归测试覆盖此路径)
                continue
            model_cls, handler = entry
            try:
                typed_msg = model_cls.model_validate(msg)
            except ValidationError as exc:
                # 已知 type 但字段不合规 — 之前会 silent drop;现在回结构化 error 帧。
                print(f"[MSG] invalid_command type={msg_type}: {exc}")
                try:
                    await send_json(
                        websocket,
                        type="error",
                        code="invalid_command",
                        bad_type=msg_type,
                        message=str(exc),
                    )
                except Exception:
                    pass
                continue
            await handler(ctx, typed_msg)

    except ConnectionClosedOK:
        pass
    finally:
        if user_id:
            notify.unregister(user_id)
        print("[断开] WS 连接已关闭")
