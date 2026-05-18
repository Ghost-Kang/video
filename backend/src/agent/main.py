"""OpenRHTV Director Agent

单 agent + DeepAgents，导演独立负责全流程创作。
画布通过 CompositeBackend 持久化到本地文件系统。

用法:
    uv run python -m agent.main          # 多轮对话
    uv run python -m agent.main --single  # 单轮测试
"""

import asyncio
import aiosqlite
import sys
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from agent import config
from agent.tools import canvas as canvas_tools
from agent.tools.canvas import (
    create_canvas_node,
    delete_canvas_node,
    execute_node,
    get_canvas_state,
    update_canvas_node,
)

_prompts_dir = Path(__file__).resolve().parent / "prompts"
_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def _make_backend() -> CompositeBackend:
    return CompositeBackend(
        default=StateBackend(),
        routes={
            "/canvas/": FilesystemBackend(
                root_dir=str(_DATA_DIR),
                virtual_mode=True,
            ),
        },
    )


def create_director_agent(checkpointer=None):
    """创建导演 agent，单 agent 承担全部创作角色。"""
    model = ChatGoogleGenerativeAI(model=config.LLM_MODEL)
    system_prompt = (_prompts_dir / "director.md").read_text(encoding="utf-8")
    canvas_prompt = (_prompts_dir / "canvas-manager.md").read_text(encoding="utf-8")

    return create_deep_agent(
        model=model,
        system_prompt=system_prompt,
        tools=[
            create_canvas_node,
            update_canvas_node,
            delete_canvas_node,
        ],
        subagents=[
            {
                "name": "canvas-manager",
                "description": "画布拓扑专家。查看画布现状，根据节点类型和层级规则确定父子连线关系，返回正确的 parent_id。",
                "system_prompt": canvas_prompt,
                "model": model,
                "tools": [get_canvas_state],
            },
        ],
        backend=_make_backend(),
        name="director",
        checkpointer=checkpointer,
    )


async def run_chat_loop():
    """多轮对话循环，AsyncSqliteSaver 持久化上下文。"""
    async with aiosqlite.connect(str(_DATA_DIR / "checkpoints.db")) as conn:
        checkpointer = AsyncSqliteSaver(conn)
        await checkpointer.setup()
        agent = create_director_agent(checkpointer=checkpointer)
        config_ = {"configurable": {"thread_id": "demo-1"}}
        canvas_tools.set_thread_id("demo-1")

        print("=" * 50)
        print("OpenRHTV 导演 - 多轮对话")
        print("输入 quit 退出")
        print("=" * 50)

        while True:
            try:
                user_input = input("\n你: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n退出")
                break

            if user_input.lower() in ("quit", "exit", "q"):
                break
            if not user_input:
                continue

            result = agent.invoke(
                {"messages": [{"role": "user", "content": user_input}]},
                config=config_,
            )
            last_msg = result["messages"][-1]
            print(f"\n导演: {last_msg.content}")


if __name__ == "__main__":
    if "--single" in sys.argv:
        agent = create_director_agent()
        result = agent.invoke({
            "messages": [{"role": "user", "content": "你好，我想创作一支30秒的科幻短片"}]
        })
        print(result["messages"][-1].content)
    else:
        asyncio.run(run_chat_loop())
