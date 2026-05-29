"""LangGraph agent 调度 — 把 user message 喂给 deepagent,流式回推。

ws_handlers 里 `user_message` handler 调度此函数;`optimize_prompt` 单独走 LLM
直调,绕开主 agent 流程。
"""

from __future__ import annotations

import asyncio
from typing import Optional

from langchain_core.messages import AIMessageChunk, ToolMessage
from websockets.exceptions import ConnectionClosed, ConnectionClosedOK

from agent.cascade.rewrite_service import Niche
from agent.llm_factory import get_chat_model
from agent.pool import AgentPool
from agent.store import save_message
from agent.tools import canvas as canvas_tools
from agent.transport import notify, run_state
from agent.transport.context import canvas_data
from agent.transport.runtime_ctx import RUN_CTX, set_run_ctx

# W5D4 — hard ceiling on a single Director turn (seconds). A hung upstream model
# call otherwise leaves the run task — and the thread run-state — pending forever
# (the "stuck at 95%" root cause). asyncio.timeout raises TimeoutError on expiry,
# which the handler below classifies as S7_UPSTREAM_TIMEOUT.
RUN_TURN_TIMEOUT_S = 180


def extract_text(content) -> str:
    """从 LangChain message content 中抽出纯文本(string 或 part list)。"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
        return "\n".join(parts)
    return str(content)


async def run_agent(
    user_id: str,
    pool: AgentPool,
    thread_id: str,
    user_content: str,
    ws,
    selected_niche: Optional[Niche] = None,
) -> None:
    """后台执行 agent。出错时推 analysis_failed + canvas_updated 而非 raw exception。

    `selected_niche` 来自前端 onboarding 选择;非 None 时,我们在 user content
    最前面注入一行 `[selected_niche: <id>]` 标记,Director prompt 已经知道如何
    解析这个标记并跳过 "你想选哪个赛道?" 的追问。保留原文给画布消息历史,
    所以 store 里仍存原始 user_content,标记只进 agent stream。
    """
    # W5D3 — defensive ContextVar cleanup. PEP 567 + asyncio.create_task each
    # snapshot the parent Context, so two concurrent run_agent tasks already
    # see isolated RUN_CTX values without this reset. The reset is hygiene
    # (avoids holding the ws reference for one extra GC cycle), not concurrency
    # safety. We capture the token before try so it's in scope for finally.
    _ctx_token = set_run_ctx({
        "user_id": user_id,
        "thread_id": thread_id,
        "ws": ws,
        "run_id": None,
    })
    reply = ""
    failed = False  # W5D3 CR-P1: explicit flag replaces magic-string sentinel.
    await run_state.mark_running(user_id, thread_id)  # W5D4 P0-B — persisted lifecycle
    try:
        # agent 的 tool call 通过 ContextVar 读写正确的用户/会话数据
        canvas_tools.set_user_id(user_id)
        canvas_tools.set_thread_id(thread_id)
        await asyncio.to_thread(save_message, user_id, thread_id, "user", user_content)
        entry = await pool.get(user_id, thread_id)

        # 注入 niche 标记 — 不污染存储,只在喂给 LLM 的 turn 加 prefix。
        agent_input_content = (
            f"[selected_niche: {selected_niche}]\n\n{user_content}"
            if selected_niche
            else user_content
        )

        full_reply = ""
        # W5D4 — bound the whole streamed turn. If the upstream model stalls,
        # asyncio.timeout fires TimeoutError instead of hanging this task (and
        # the thread's run-state) indefinitely; the except below classifies it
        # as S7_UPSTREAM_TIMEOUT and pushes a recoverable failure.
        async with asyncio.timeout(RUN_TURN_TIMEOUT_S):
            async for chunk in entry["agent"].astream(
                {"messages": [{"role": "user", "content": agent_input_content}]},
                config=entry["config"],
                stream_mode="messages",
                version="v2",
            ):
                msg, meta = chunk["data"]

                if isinstance(msg, AIMessageChunk) and msg.tool_calls:
                    for tc in msg.tool_calls:
                        await notify.send_to_user(
                            user_id,
                            {
                                "type": "agent_stream",
                                "thread_id": thread_id,
                                "event": "tool_call",
                                "name": tc.get("name", ""),
                                "args": str(tc.get("args", {})),
                            },
                            fallback_ws=ws,
                        )

                elif isinstance(msg, AIMessageChunk) and msg.content and not isinstance(msg, ToolMessage):
                    token = extract_text(msg.content)
                    if token and not full_reply.endswith(token):
                        full_reply += token
                        await notify.send_to_user(
                            user_id,
                            {"type": "agent_stream", "thread_id": thread_id, "event": "text", "content": token},
                            fallback_ws=ws,
                        )

        reply = full_reply or "（未生成回复）"
        await asyncio.to_thread(save_message, user_id, thread_id, "agent", reply)
        await run_state.mark_done(thread_id)  # W5D4 — terminal success, reconnect-visible
    except Exception as e:
        # W5D3 — don't leak raw exception string into the WS push, AND don't
        # persist it verbatim into the chat history. The persisted line is
        # sanitized so a future session_state replay shows a friendly hint
        # instead of an internal stack trace fragment.
        failed = True
        print(f"[错误] thread={thread_id} {e}")
        import traceback as _tb
        from agent.cascade.event_names import EventName as _EN
        from agent.cascade.events import emit as _emit
        from agent.cascade.failures import HardFailure as _HF, FailureCode as _FC, RECOVERY_HINTS as _HINTS, RECOVERY_ACTIONS as _ACTIONS

        # Compute the sanitized user-facing hint from the failure taxonomy.
        if isinstance(e, _HF):
            code_val = e.code.value
            hint_val = e.hint
            actions_val = e.actions
            request_id_val = e.request_id
        else:
            if type(e).__name__ == "TimeoutError" or "timeout" in str(e).lower():
                code_val = _FC.S7_UPSTREAM_TIMEOUT.value
            elif isinstance(e, (ConnectionError, OSError)) or "refus" in str(e).lower() or "rate" in str(e).lower():
                code_val = _FC.S8_UPSTREAM_REFUSED.value
            else:
                # Unexpected internal error (programming bug / unclassified) —
                # don't mislabel our own bug as "upstream refused". Full
                # traceback is captured in the uncaught_exception event below.
                code_val = _FC.S11_INTERNAL_ERROR.value
            hint_val = _HINTS.get(code_val, "处理出错,请重试或换一条链接。")
            actions_val = _ACTIONS.get(code_val, ["REPORT"])
            request_id_val = ""

        # W5D4 — record terminal failure so a reconnecting client (via
        # get_session_state) can replay it. The live analysis_failed frame
        # pushed below often never lands — the WS that died is usually what
        # triggered this failure in the first place.
        await run_state.mark_failed(thread_id, {
            "code": code_val,
            "hint": hint_val or "处理出错,请重试",
            "actions": actions_val,
            "request_id": request_id_val,
        })

        # Persist sanitized hint (raw traceback still lands in events.db below).
        await asyncio.to_thread(
            save_message, user_id, thread_id, "agent", hint_val or "处理出错,请重试"
        )

        # W5D2 observability — persist the full traceback to events.db so
        # /admin/events can surface it. Best-effort; observability errors
        # never swallow the real error.
        try:
            await _emit(
                _EN.UNCAUGHT_EXCEPTION,
                user_id=user_id,
                run_id=None,
                payload={
                    "site": "agent_runner.run_agent",
                    "exc_type": type(e).__name__,
                    "message": str(e)[:500],
                    "traceback": _tb.format_exc()[:4000],
                    "thread_id": thread_id,
                },
            )
        except Exception:
            pass

        # Push structured analysis_failed WS frame so frontend ChatPanel flips
        # into `failed` state directly. W5D4 P0-A — via live registry so a
        # reconnect during the failing run still receives it.
        try:
            await notify.send_to_user(
                user_id,
                {
                    "type": "analysis_failed",
                    "thread_id": thread_id,
                    "code": code_val,
                    "hint": hint_val,
                    "actions": actions_val,
                    "request_id": request_id_val,
                    "stage": "analysis",
                },
                fallback_ws=ws,
            )
        except (ConnectionClosed, ConnectionClosedOK, RuntimeError, OSError):
            pass
    finally:
        # Defensive cleanup (see top-of-function note about ContextVar semantics).
        try:
            RUN_CTX.reset(_ctx_token)
        except (ValueError, LookupError):
            pass

    # W5D3 CR-P1 — explicit failed flag replaces the magic-string sentinel.
    # When the agent failed, frontend already got `analysis_failed`; we still
    # push canvas snapshot to keep canvas/anchor state consistent, then return
    # without sending `agent_response` (which would carry the failure hint
    # again and confuse the chat history).
    # Canvas snapshot is synchronous sqlite3 — read it off the event loop.
    snapshot = await asyncio.to_thread(canvas_data, thread_id)
    if failed:
        try:
            await notify.send_to_user(
                user_id,
                {"type": "canvas_updated", "thread_id": thread_id, "canvas": snapshot},
                fallback_ws=ws,
            )
        except (ConnectionClosed, ConnectionClosedOK, RuntimeError, OSError):
            pass
    else:
        try:
            await notify.send_to_user(
                user_id,
                {"type": "agent_response", "thread_id": thread_id, "content": reply, "canvas": snapshot},
                fallback_ws=ws,
            )
        except (ConnectionClosed, ConnectionClosedOK, RuntimeError, OSError):
            pass


async def optimize_prompt(node_id: str, prompt: str, feedback: str) -> str:
    """LLM 优化图片 prompt,不经过主 agent 流程。同步写回 node.description。"""
    model = get_chat_model()
    system = "你是一位专业的 AI 绘画提示词优化师。根据用户的反馈优化提示词，只返回优化后的提示词，不要加任何解释或前缀。"
    user = f"当前提示词：\n{prompt}\n\n用户反馈：\n{feedback}\n\n请输出优化后的提示词："
    # await ainvoke — `.invoke()` is a blocking network call; on the asyncio
    # event loop it would stall ALL websocket/HTTP handling for the duration.
    result = await model.ainvoke(
        [{"role": "system", "content": system}, {"role": "user", "content": user}]
    )
    optimized = result.content if hasattr(result, "content") else str(result)

    # Canvas DAO is synchronous sqlite3 — offload so the load/upsert doesn't
    # block the event loop either.
    def _persist() -> None:
        node = canvas_tools._load_node(node_id)
        if node:
            node["description"] = optimized
            canvas_tools._upsert_node(node)
            print(f"[润色] 已更新节点 description node={node_id}")

    await asyncio.to_thread(_persist)
    return optimized
