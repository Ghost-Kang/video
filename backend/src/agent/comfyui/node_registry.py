"""Pro 节点类型注册表 —— 单一真相源(前后端共用一份 schema)。

这里定义 Pro 画布 MVP 的 5 类节点(plan §3.1),每类节点声明:
  - 端口(input data ports 走连线 / output ports)+ Pro 级端口类型(MVP 弱校验,P2 强类型)
  - 静态参数(非连线 input,带默认值与类型)
  - 对应的 self-host ComfyUI class_type(Generate 是宏,编译期展开成 KSampler+VAEDecode 等)
  - provider 归属(any / selfhosted / runninghub)—— 合规闸:RunningHub-only 节点在
    SelfHosted 模式不出现在面板,反之亦然
  - billable —— 是否花钱(成本估算 / 成本闸只数 billable 节点)

`registry_json()` 把注册表导出成可序列化结构,供前端从中派生节点面板 UI(避免前后端 schema 漂移)。

> 设计取舍:Pro 级端口类型只用 image / text / model 三种(降低用户连线心智);ComfyUI 内部的
> MODEL/CLIP/VAE/CONDITIONING/LATENT 类型桥接全部由 compiler 在编译期负责,用户不感知。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class PortType:
    """Pro 级端口类型(MVP 弱校验用)。ComfyUI 原生类型由 compiler 内部桥接,不在此暴露。"""

    IMAGE = "image"
    TEXT = "text"
    MODEL = "model"
    ANY = "any"


# provider 归属常量
PROVIDER_ANY = "any"
PROVIDER_SELFHOSTED = "selfhosted"
PROVIDER_RUNNINGHUB = "runninghub"


@dataclass(frozen=True)
class Port:
    """一个数据端口。required 仅对 input 有意义(output 恒为产出)。"""

    name: str
    type: str
    required: bool = True


@dataclass(frozen=True)
class ParamSpec:
    """一个静态参数(非连线输入)。type ∈ {'str','int','float'};choices 非空时为枚举。"""

    name: str
    type: str
    default: Any
    label: str = ""
    choices: tuple[str, ...] = ()
    minimum: float | None = None
    maximum: float | None = None


@dataclass(frozen=True)
class NodeType:
    """一类 Pro 节点的完整声明。"""

    key: str
    label: str
    category: str  # 面板分组:input / prompt / model / generate / output
    comfy_class: str  # self-host ComfyUI class_type(Generate 是宏:见 compiler)
    inputs: tuple[Port, ...] = ()
    outputs: tuple[Port, ...] = ()
    params: tuple[ParamSpec, ...] = ()
    providers: tuple[str, ...] = (PROVIDER_ANY,)
    billable: bool = False

    def input(self, name: str) -> Port | None:
        for p in self.inputs:
            if p.name == name:
                return p
        return None

    def output(self, name: str) -> Port | None:
        for p in self.outputs:
            if p.name == name:
                return p
        return None

    def param(self, name: str) -> ParamSpec | None:
        for p in self.params:
            if p.name == name:
                return p
        return None


# ── 默认值(可经 Model 节点参数覆盖) ─────────────────────────────────────────────
DEFAULT_CKPT = "sd_xl_base_1.0.safetensors"
DEFAULT_SAMPLER = "euler"
DEFAULT_SCHEDULER = "normal"
DEFAULT_STEPS = 20
DEFAULT_CFG = 7.0
DEFAULT_DENOISE = 1.0
DEFAULT_WIDTH = 1024
DEFAULT_HEIGHT = 1024


# ── 5 类 MVP 节点(plan §3.1) ───────────────────────────────────────────────────
NODE_TYPES: dict[str, NodeType] = {
    "Model": NodeType(
        key="Model",
        label="模型",
        category="model",
        comfy_class="CheckpointLoaderSimple",
        outputs=(Port("model", PortType.MODEL),),
        params=(
            ParamSpec("ckpt_name", "str", DEFAULT_CKPT, label="检查点模型"),
        ),
    ),
    "Prompt": NodeType(
        key="Prompt",
        label="提示词",
        category="prompt",
        comfy_class="CLIPTextEncode",
        outputs=(Port("text", PortType.TEXT),),
        params=(
            ParamSpec("text", "str", "", label="文本"),
            ParamSpec("role", "str", "positive", label="角色", choices=("positive", "negative")),
        ),
    ),
    "LoadImage": NodeType(
        key="LoadImage",
        label="加载图片",
        category="input",
        comfy_class="LoadImage",
        outputs=(Port("image", PortType.IMAGE),),
        params=(
            ParamSpec("image_url", "str", "", label="图片地址"),
        ),
    ),
    # Anchor = 锚点级联的图形化:从 anchors 表取 character/scene 复用图,跨镜共享一份。
    # 编译同 LoadImage(从 URL 载图),但携带 anchor_id 以便回写 reuse_count(护城河 metric)。
    "Anchor": NodeType(
        key="Anchor",
        label="锚点",
        category="input",
        comfy_class="LoadImage",
        outputs=(Port("image", PortType.IMAGE),),
        params=(
            ParamSpec("anchor_id", "str", "", label="锚点ID"),
            ParamSpec("image_url", "str", "", label="图片地址"),
            ParamSpec("label", "str", "", label="名称"),
            ParamSpec("kind", "str", "character", label="类型", choices=("character", "scene")),
        ),
    ),
    "Generate": NodeType(
        key="Generate",
        label="生成图像",
        category="generate",
        comfy_class="__GENERATE__",  # 宏:compiler 展开成 (VAEEncode?)+EmptyLatentImage?+KSampler+VAEDecode
        inputs=(
            Port("model", PortType.MODEL, required=True),
            Port("positive", PortType.TEXT, required=True),
            Port("negative", PortType.TEXT, required=False),
            Port("image", PortType.IMAGE, required=False),  # 传图 = 图生图(denoise<1)
        ),
        outputs=(Port("image", PortType.IMAGE),),
        params=(
            ParamSpec("seed", "int", 0, label="随机种子", minimum=0),
            ParamSpec("steps", "int", DEFAULT_STEPS, label="步数", minimum=1, maximum=150),
            ParamSpec("cfg", "float", DEFAULT_CFG, label="CFG", minimum=0.0, maximum=30.0),
            ParamSpec("sampler_name", "str", DEFAULT_SAMPLER, label="采样器"),
            ParamSpec("scheduler", "str", DEFAULT_SCHEDULER, label="调度器"),
            ParamSpec("denoise", "float", DEFAULT_DENOISE, label="重绘幅度", minimum=0.0, maximum=1.0),
            ParamSpec("width", "int", DEFAULT_WIDTH, label="宽", minimum=64, maximum=4096),
            ParamSpec("height", "int", DEFAULT_HEIGHT, label="高", minimum=64, maximum=4096),
        ),
        billable=True,
    ),
    "Preview": NodeType(
        key="Preview",
        label="预览",
        category="output",
        comfy_class="SaveImage",
        inputs=(Port("image", PortType.IMAGE, required=True),),
    ),
}


def get_node_type(key: str) -> NodeType | None:
    """按 key 取节点类型声明;未知返回 None。"""
    return NODE_TYPES.get(key)


def is_billable(key: str) -> bool:
    """该节点类型是否计费(成本估算/成本闸只数 billable 节点)。"""
    nt = NODE_TYPES.get(key)
    return bool(nt and nt.billable)


def node_available_for_provider(key: str, provider: str) -> bool:
    """该节点类型在指定 provider 下是否可用(合规面板过滤)。"""
    nt = NODE_TYPES.get(key)
    if not nt:
        return False
    return PROVIDER_ANY in nt.providers or (provider or "").lower() in nt.providers


def _param_json(p: ParamSpec) -> dict[str, Any]:
    out: dict[str, Any] = {"name": p.name, "type": p.type, "default": p.default, "label": p.label}
    if p.choices:
        out["choices"] = list(p.choices)
    if p.minimum is not None:
        out["min"] = p.minimum
    if p.maximum is not None:
        out["max"] = p.maximum
    return out


def registry_json() -> dict[str, Any]:
    """可序列化的注册表导出 —— 前端从中派生节点面板 UI(单一真相源,防 schema 漂移)。"""
    return {
        "version": 1,
        "port_types": [PortType.IMAGE, PortType.TEXT, PortType.MODEL, PortType.ANY],
        "nodes": [
            {
                "key": nt.key,
                "label": nt.label,
                "category": nt.category,
                "providers": list(nt.providers),
                "billable": nt.billable,
                "inputs": [{"name": p.name, "type": p.type, "required": p.required} for p in nt.inputs],
                "outputs": [{"name": p.name, "type": p.type} for p in nt.outputs],
                "params": [_param_json(p) for p in nt.params],
            }
            for nt in NODE_TYPES.values()
        ],
    }
