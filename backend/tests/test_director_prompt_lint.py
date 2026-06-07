"""director.md prompt-lint(审计 2026-06-06 M8/L1)。

prompt 即代码:director.md 指挥 Director 调工具。曾漂移成调 `compose_canvas()`(从不存在的
幻影工具)和 `execute_node`(存在但不在 Director 工具集 —— 那是用户在画布点击触发的 WS 工具)。
模型可能照着 prompt 去调一个不存在/调不到的工具,白白浪费一轮。这里锁死:prompt 里出现的
工具调用必须都是 Director 真正注册的工具。
"""

from __future__ import annotations

import re
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src" / "agent"
DIRECTOR_MD = _SRC / "prompts" / "director.md"
MAIN_PY = _SRC / "main.py"

# Director 在 main.py create_deep_agent(tools=[...]) 注册的工具 + deepagents 内置工具。
# 改 main.py 的工具集时同步这里(test_director_tools_in_sync_with_main 会粗校验主要工具)。
DIRECTOR_TOOLS = {
    "create_canvas_node",
    "update_canvas_node",
    "delete_canvas_node",
    "get_canvas_state",
    "cascade_analyze",
    "cascade_rewrite",
    "cascade_generate_first_frame",
    "cascade_generate_shot_video",
    "cascade_compose_film",
    "cascade_ask",
    # deepagents 内置(planning / subagent 委托)
    "write_todos",
    "task",
}

# 存在但 Director 调不到的工具(WS handler / 后端层,由用户在画布点击触发),以及从不存在的
# 幻影工具。director.md 不该把这些当作 Director 可调的工具来指挥。
NON_DIRECTOR_TOOLS = {
    "execute_node",
    "approve_node",
    "reject_node",
    "enqueue_generation",
    "regenerate_node",
    "restore_node_version",
    "cancel_node_generation",
    "create_canvas_edge",
    "delete_canvas_edge",
    "reorder_edge",
    "recover_generation_tasks",
    "schedule_generation_retry",
    "update_generation_state",
    "compose_canvas",  # 幻影工具(全仓不存在)
}


def _director_text() -> str:
    return DIRECTOR_MD.read_text(encoding="utf-8")


def test_director_prompt_only_calls_registered_tools():
    """director.md 里所有 `name(` 形式的工具调用都必须是 Director 真正注册的工具。"""
    text = _director_text()
    called = set(re.findall(r"`([a-z_][a-z0-9_]*)\s*\(", text))
    unknown = called - DIRECTOR_TOOLS
    assert not unknown, f"director.md 引用了 Director 没有的工具调用: {sorted(unknown)}"


def test_director_prompt_does_not_reference_non_director_tools():
    """Director 不该被指示去调 WS/后端层工具或幻影工具(execute_node / compose_canvas 等)。"""
    text = _director_text()
    leaked = {t for t in NON_DIRECTOR_TOOLS if re.search(rf"`{t}\b", text)}
    assert not leaked, f"director.md 提到了 Director 调不到的工具: {sorted(leaked)}"


def test_director_tools_in_sync_with_main():
    """护栏:DIRECTOR_TOOLS allowlist 不能漂移 —— main.py 注册块里的核心工具必须都在其中。"""
    main_src = MAIN_PY.read_text(encoding="utf-8")
    block = main_src.split("tools=[", 1)[1].split("]", 1)[0]
    registered = set(re.findall(r"\b([a-z_][a-z0-9_]*)\b", block))
    core = {"create_canvas_node", "update_canvas_node", "delete_canvas_node",
            "get_canvas_state", "cascade_analyze", "cascade_rewrite"}
    missing_from_main = core - registered
    assert not missing_from_main, f"main.py 注册块缺核心工具: {sorted(missing_from_main)}"
    # main.py 注册块里出现的工具都应在 allowlist(否则 allowlist 落后于 main)
    block_tools = registered & (
        {t for t in registered if t.startswith("cascade_") or t.startswith("create_canvas")
         or t.startswith("update_canvas") or t.startswith("delete_canvas") or t == "get_canvas_state"}
    )
    drift = block_tools - DIRECTOR_TOOLS
    assert not drift, f"main.py 注册了 allowlist 没有的工具,请同步 DIRECTOR_TOOLS: {sorted(drift)}"
