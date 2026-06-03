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
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from agent.llm_factory import get_chat_model
from agent.tools import canvas as canvas_tools
from agent.tools.canvas import (
    create_canvas_node,
    delete_canvas_node,
    execute_node,
    get_canvas_state,
    update_canvas_node,
)
from agent.tools.cascade import (
    cascade_analyze,
    cascade_ask,
    cascade_compose_film,
    cascade_generate_first_frame,
    cascade_generate_shot_video,
    cascade_rewrite,
)

_prompts_dir = Path(__file__).resolve().parent / "prompts"
_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def build_interrupt_on() -> dict | None:
    """审核闸门配置:受管控的生成工具 → LangGraph 原生 interrupt(approve/edit/reject)。

    读 `config.CANVAS_INTERRUPT_GATE`(默认 OFF) + `INTERRUPT_GATE_TOOLS`。返回 None
    表示不挂闸门(deepagents 不加 HumanInTheLoopMiddleware,行为与今天完全一致)。
    单独成函数,方便 pool / 测试按需构造带闸门的 agent,不依赖进程环境变量。

    `respond` 决策(替工具回话、跳过执行)对生成工具无意义,故只放 approve/edit/reject。
    """
    from agent.config import CANVAS_INTERRUPT_GATE, INTERRUPT_GATE_TOOLS

    if not CANVAS_INTERRUPT_GATE or not INTERRUPT_GATE_TOOLS:
        return None
    return {
        name: {"allowed_decisions": ["approve", "edit", "reject"]}
        for name in INTERRUPT_GATE_TOOLS
    }


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


def create_director_agent(checkpointer=None, interrupt_on: dict | None = "default"):
    """创建导演 agent，单 agent 承担全部创作角色。

    `interrupt_on`:None=不挂闸门;dict=显式闸门配置(测试用);默认哨兵 "default"
    =从 config 读(`build_interrupt_on()`),让生产走开关、测试可显式覆盖而不碰环境变量。
    """
    if interrupt_on == "default":
        interrupt_on = build_interrupt_on()
    model = get_chat_model()
    system_prompt = (_prompts_dir / "director.md").read_text(encoding="utf-8")
    canvas_prompt = (_prompts_dir / "canvas-manager.md").read_text(encoding="utf-8")

    return create_deep_agent(
        model=model,
        system_prompt=system_prompt,
        tools=[
            create_canvas_node,
            update_canvas_node,
            delete_canvas_node,
            cascade_analyze,
            cascade_rewrite,
            cascade_generate_first_frame,
            cascade_generate_shot_video,
            cascade_compose_film,
            cascade_ask,
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
        interrupt_on=interrupt_on,
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
