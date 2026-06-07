"""Pro 高级子画布 · ComfyUI(litegraph)执行后端集成包。

在现有「低门槛 Agent 模式」之外,增量引入一条「Pro 高级子画布」轨:用户在 tldraw 画布上
拖拽连线出一张**通用可执行计算图**,编译成 ComfyUI prompt(自建境内实例)或 RunningHub
payload(境外托管,opt-in),经现有异步队列 + cost_guard + 熔断执行。

模块:
    node_registry  —— Pro 节点类型 ↔ ComfyUI class_type + 端口 + provider 归属(单一真相源,前后端共用)
    compiler       —— tldraw 图 JSON → ComfyUI prompt / RunningHub payload + 校验 + 成本估算
    provider       —— ComfyUIProvider ABC + SelfHosted / RunningHub / Fixture + get_comfyui_provider()
    seed_builder   —— 爆点分析 → 种子可执行图(deterministic,不改可直接 Run)

灰度开关 config.PRO_CANVAS_ENABLED(默认 OFF);跨境 RunningHub 受 STRICT_CROSS_BORDER_REJECT
默认拦截。详见 docs/PRO_CANVAS_TLDRAW_COMFYUI_PLAN.md。
"""

from __future__ import annotations

from agent.comfyui.compiler import (
    CompileError,
    compile_graph,
    estimate_graph_cost,
    validate_graph,
)
from agent.comfyui.node_registry import (
    NODE_TYPES,
    PortType,
    get_node_type,
    registry_json,
)
from agent.comfyui.provider import (
    ComfyUIProvider,
    FixtureComfyUIProvider,
    RunningHubComfyUIProvider,
    SelfHostedComfyUIProvider,
    comfyui_provider_blocked,
    get_comfyui_provider,
)

__all__ = [
    "CompileError",
    "compile_graph",
    "estimate_graph_cost",
    "validate_graph",
    "NODE_TYPES",
    "PortType",
    "get_node_type",
    "registry_json",
    "ComfyUIProvider",
    "FixtureComfyUIProvider",
    "RunningHubComfyUIProvider",
    "SelfHostedComfyUIProvider",
    "comfyui_provider_blocked",
    "get_comfyui_provider",
]
