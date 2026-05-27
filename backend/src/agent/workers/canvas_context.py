"""Worker 任务的 canvas_tools 上下文设置。

每个 task 处理前必须调一次,确保 canvas_tools ContextVar 指向正确的 user/thread。
后续 Claude-A2 会替换为显式参数,届时这个 helper 退役。
"""

from __future__ import annotations

from agent.tools import canvas as canvas_tools


def setup_canvas_context(node: dict) -> None:
    """从 node dict 读 user_id/thread_id,写入 ContextVar。"""
    canvas_tools.set_user_id(node["user_id"])
    canvas_tools.set_thread_id(node["thread_id"])
