"""LangGraph agent 调度 — 把 user message 喂给 deepagent,流式回推。

ws_handlers 里 `user_message` handler 调度此函数;`optimize_prompt` 单独走 LLM
直调,绕开主 agent 流程。
"""

from __future__ import annotations

from typing import Optional

from langchain_core.messages import AIMessageChunk, ToolMessage
from websockets.exceptions import ConnectionClosedOK

from agent.cascade.rewrite_service import Niche
from agent.llm_factory import get_chat_model
from agent.pool import AgentPool
from agent.store import save_message
from agent.tools import canvas as canvas_tools
from agent.transport.context import canvas_data, send_json
from agent.transport.runtime_ctx import set_run_ctx


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
    """后台执行 agent。出错也会回 agent_response 帧避免前端 hang。

    `selected_niche` 来自前端 onboarding 选择;非 None 时,我们在 user content
    最前面注入一行 `[selected_niche: <id>]` 标记,Director prompt 已经知道如何
    解析这个标记并跳过 "你想选哪个赛道?" 的追问。保留原文给画布消息历史,
    所以 store 里仍存原始 user_content,标记只进 agent stream。
    """
    try:
        # agent 的 tool call 通过 ContextVar 读写正确的用户/会话数据
        canvas_tools.set_user_id(user_id)
        canvas_tools.set_thread_id(thread_id)
        # Cascade tools (cascade_analyze / cascade_rewrite) 也通过 ContextVar 读
        # ws/user_id/thread_id —— 见 transport/runtime_ctx.py 的 contract 注释。
        set_run_ctx({
            "user_id": user_id,
            "thread_id": thread_id,
            "ws": ws,
            "run_id": None,
        })
        save_message(user_id, thread_id, "user", user_content)
        entry = await pool.get(thread_id)

        # 注入 niche 标记 — 不污染存储,只在喂给 LLM 的 turn 加 prefix。
        agent_input_content = (
            f"[selected_niche: {selected_niche}]\n\n{user_content}"
            if selected_niche
            else user_content
        )

        full_reply = ""
        async for chunk in entry["agent"].astream(
            {"messages": [{"role": "user", "content": agent_input_content}]},
            config=entry["config"],
            stream_mode="messages",
            version="v2",
        ):
            msg, meta = chunk["data"]

            if isinstance(msg, AIMessageChunk) and msg.tool_calls:
                for tc in msg.tool_calls:
                    await send_json(
                        ws,
                        type="agent_stream",
                        thread_id=thread_id,
                        event="tool_call",
                        name=tc.get("name", ""),
                        args=str(tc.get("args", {})),
                    )

            elif isinstance(msg, AIMessageChunk) and msg.content and not isinstance(msg, ToolMessage):
                token = extract_text(msg.content)
                if token and not full_reply.endswith(token):
                    full_reply += token
                    await send_json(ws, type="agent_stream", thread_id=thread_id, event="text", content=token)

        reply = full_reply or "（未生成回复）"
        save_message(user_id, thread_id, "agent", reply)
    except Exception as e:
        reply = f"处理出错: {e}"
        save_message(user_id, thread_id, "agent", reply)
        print(f"[错误] thread={thread_id} {e}")

    try:
        await send_json(
            ws,
            type="agent_response",
            thread_id=thread_id,
            content=reply,
            canvas=canvas_data(thread_id),
        )
    except (ConnectionClosedOK, Exception):
        pass


async def optimize_prompt(node_id: str, prompt: str, feedback: str) -> str:
    """LLM 优化图片 prompt,不经过主 agent 流程。同步写回 node.description。"""
    model = get_chat_model()
    system = "你是一位专业的 AI 绘画提示词优化师。根据用户的反馈优化提示词，只返回优化后的提示词，不要加任何解释或前缀。"
    user = f"当前提示词：\n{prompt}\n\n用户反馈：\n{feedback}\n\n请输出优化后的提示词："
    result = model.invoke([{"role": "system", "content": system}, {"role": "user", "content": user}])
    optimized = result.content if hasattr(result, "content") else str(result)

    node = canvas_tools._load_node(node_id)
    if node:
        node["description"] = optimized
        canvas_tools._upsert_node(node)
        print(f"[润色] 已更新节点 description node={node_id}")

    return optimized
