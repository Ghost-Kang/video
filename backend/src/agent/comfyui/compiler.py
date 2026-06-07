"""tldraw 计算图 JSON → 执行后端格式 编译器 + 校验 + 成本估算。

输入 graph JSON(前后端共用,seed_builder 也产出这个形状):
    {
      "version": 1,
      "workflowId": "<runninghub only,可选>",
      "nodes": [
        {"id": "model_1", "type": "Model",  "params": {"ckpt_name": "..."}},
        {"id": "pos_1",   "type": "Prompt", "params": {"text": "一只猫", "role": "positive"}},
        {"id": "neg_1",   "type": "Prompt", "params": {"text": "模糊", "role": "negative"}},
        {"id": "load_1",  "type": "LoadImage", "params": {"image_url": "https://..."}},
        {"id": "gen_1",   "type": "Generate", "params": {"seed": 0, "steps": 20, ...},
                          "cached": false, "cached_url": null},
        {"id": "prev_1",  "type": "Preview", "params": {}}
      ],
      "edges": [
        {"id":"e1","source":"model_1","sourceHandle":"model","target":"gen_1","targetHandle":"model"},
        {"id":"e2","source":"pos_1","sourceHandle":"text","target":"gen_1","targetHandle":"positive"},
        ...
      ]
    }

输出:
    - target="selfhosted":ComfyUI **prompt(API format)** —— {"<comfyId>": {"class_type":..,"inputs":{..}}}
      连线 = inputs 引用上游输出 ["<srcComfyId>", <outputIndex>](与 litegraph 语义一致)。
      Generate 是宏:编译期展开成 CheckpointLoaderSimple + CLIPTextEncode×2 +
      (EmptyLatentImage | VAEEncode) + KSampler + VAEDecode,Preview→SaveImage。
    - target="runninghub":{workflowId, nodeInfoList:[{nodeId, fieldName, fieldValue}]}(Advanced API)。

> 校验(plan §8「图编译正确性」头号风险):未知节点 / 重复 id / 悬空连线 / 端口类型不兼容 /
> 单值输入被多连 / 成环 / 缺必填输入 / 无输出 —— 全部在 validate_graph() 抛 CompileError(带机器码)。
> 配套编译单测(test_pro_compiler.py)锁结构正确性。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agent.comfyui.node_registry import (
    NODE_TYPES,
    PortType,
    get_node_type,
)

TARGET_SELFHOSTED = "selfhosted"
TARGET_RUNNINGHUB = "runninghub"


class CompileError(Exception):
    """图非法 / 编译失败。code 是面向前端的机器码,message 是中文人话。"""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


# ── 内部:索引 + 连线 ───────────────────────────────────────────────────────────


@dataclass
class _SourceRef:
    node_id: str
    handle: str


@dataclass
class _Graph:
    nodes: dict[str, dict]
    order: list[str]  # 原始声明顺序(稳定输出)
    # (target_id, target_handle) -> _SourceRef
    incoming: dict[tuple[str, str], _SourceRef]


def _coerce(value: Any, ptype: str, default: Any) -> Any:
    """按 ParamSpec.type 做温和强转;失败回落 default。"""
    if value is None:
        return default
    try:
        if ptype == "int":
            return int(value)
        if ptype == "float":
            return float(value)
        return str(value)
    except (TypeError, ValueError):
        return default


def _resolved_params(node: dict) -> dict[str, Any]:
    """节点参数填默认 + 类型强转 + 范围钳制(以 registry 声明为准)。

    钳制(review 修复):registry 声明的 min/max 此前只用于前端 UI,服务端从不强制 —— 客户端
    可传 steps=100000 / width=99999 编出一张结构合法但吃爆 GPU 的图,而 ¥1.5/张的预测不随步数
    缩放、成本闸拦不住。这里对 int/float 参数按 ParamSpec.minimum/maximum 钳到合法区间。"""
    nt = NODE_TYPES[node["type"]]
    raw = node.get("params") or {}
    out: dict[str, Any] = {}
    for spec in nt.params:
        val = _coerce(raw.get(spec.name), spec.type, spec.default)
        if spec.type in ("int", "float") and isinstance(val, (int, float)) and not isinstance(val, bool):
            if spec.minimum is not None and val < spec.minimum:
                val = spec.minimum
            if spec.maximum is not None and val > spec.maximum:
                val = spec.maximum
            if spec.type == "int":
                val = int(val)
        out[spec.name] = val
    return out


def _ports_compatible(src_type: str, dst_type: str) -> bool:
    return src_type == dst_type or PortType.ANY in (src_type, dst_type)


def validate_graph(graph: dict) -> _Graph:
    """结构 + 端口 + 环 + 必填 校验。通过则返回内部索引;否则抛 CompileError。"""
    if not isinstance(graph, dict):
        raise CompileError("bad_graph", "图不是对象")
    nodes_raw = graph.get("nodes")
    edges_raw = graph.get("edges") or []
    if not isinstance(nodes_raw, list) or not nodes_raw:
        raise CompileError("empty_graph", "图为空(没有节点)")
    if not isinstance(edges_raw, list):
        raise CompileError("bad_graph", "edges 不是数组")

    # 1) 节点:唯一 id + 已知类型
    nodes: dict[str, dict] = {}
    order: list[str] = []
    for n in nodes_raw:
        if not isinstance(n, dict):
            raise CompileError("bad_node", "节点不是对象")
        nid = n.get("id")
        ntype = n.get("type")
        if not isinstance(nid, str) or not nid:
            raise CompileError("bad_node", "节点缺少合法 id")
        if nid in nodes:
            raise CompileError("duplicate_node_id", f"节点 id 重复:{nid}")
        if ntype not in NODE_TYPES:
            raise CompileError("unknown_node_type", f"未知节点类型:{ntype}")
        nodes[nid] = n
        order.append(nid)

    # 2) 连线:端点存在 + 句柄合法 + 端口类型兼容 + 单值输入不被多连
    incoming: dict[tuple[str, str], _SourceRef] = {}
    adjacency: dict[str, list[str]] = {nid: [] for nid in nodes}
    for e in edges_raw:
        if not isinstance(e, dict):
            raise CompileError("bad_edge", "连线不是对象")
        src = e.get("source")
        dst = e.get("target")
        s_handle = e.get("sourceHandle")
        d_handle = e.get("targetHandle")
        if src not in nodes or dst not in nodes:
            raise CompileError("bad_edge", f"连线端点不存在:{src} → {dst}")
        if not isinstance(s_handle, str) or not isinstance(d_handle, str):
            raise CompileError("bad_edge", "连线缺少 sourceHandle/targetHandle")
        s_nt = NODE_TYPES[nodes[src]["type"]]
        d_nt = NODE_TYPES[nodes[dst]["type"]]
        out_port = s_nt.output(s_handle)
        in_port = d_nt.input(d_handle)
        if out_port is None:
            raise CompileError("bad_edge", f"{nodes[src]['type']} 没有输出端口 {s_handle}")
        if in_port is None:
            raise CompileError("bad_edge", f"{nodes[dst]['type']} 没有输入端口 {d_handle}")
        if not _ports_compatible(out_port.type, in_port.type):
            raise CompileError(
                "port_type_mismatch",
                f"端口类型不兼容:{out_port.type} → {in_port.type}({src}.{s_handle} → {dst}.{d_handle})",
            )
        key = (dst, d_handle)
        if key in incoming and not in_port.multi:
            raise CompileError("multi_input", f"输入端口被多次连接:{dst}.{d_handle}")
        incoming[key] = _SourceRef(node_id=src, handle=s_handle)  # multi 端口由 domestic 执行器扫边收齐
        adjacency[src].append(dst)

    # 3) 必填输入齐全
    for nid, node in nodes.items():
        nt = NODE_TYPES[node["type"]]
        for port in nt.inputs:
            if port.required and (nid, port.name) not in incoming:
                raise CompileError(
                    "missing_required_input",
                    f"{nt.label}({nid})缺少必填输入:{port.name}",
                )

    # 4) 环检测(Kahn 拓扑)
    indeg: dict[str, int] = {nid: 0 for nid in nodes}
    for src, outs in adjacency.items():
        for dst in outs:
            indeg[dst] += 1
    queue = [nid for nid, d in indeg.items() if d == 0]
    seen = 0
    while queue:
        cur = queue.pop()
        seen += 1
        for dst in adjacency[cur]:
            indeg[dst] -= 1
            if indeg[dst] == 0:
                queue.append(dst)
    if seen != len(nodes):
        raise CompileError("cycle", "图中存在环(计算图必须是 DAG)")

    # 5) 至少一个输出(Preview)—— 否则跑了也看不到结果
    if not any(nodes[nid]["type"] == "Preview" for nid in nodes):
        raise CompileError("no_output", "图缺少输出节点(Preview)")

    return _Graph(nodes=nodes, order=order, incoming=incoming)


# ── 编译:self-host ComfyUI prompt ───────────────────────────────────────────────


class _ComfyEmitter:
    """把校验过的 Pro 图展开成 ComfyUI prompt(API format)。"""

    def __init__(self, g: _Graph):
        self.g = g
        self.prompt: dict[str, dict] = {}

    def _src(self, target_id: str, handle: str) -> _SourceRef | None:
        return self.g.incoming.get((target_id, handle))

    def _ckpt(self, model_pro_id: str) -> str:
        """确保 CheckpointLoaderSimple 已发射,返回其 comfy id(输出 0=MODEL,1=CLIP,2=VAE)。"""
        cid = f"ckpt_{model_pro_id}"
        if cid not in self.prompt:
            p = _resolved_params(self.g.nodes[model_pro_id])
            self.prompt[cid] = {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": p["ckpt_name"]},
            }
        return cid

    def _clip_encode(self, prompt_pro_id: str, ckpt_cid: str) -> list:
        """对某 Prompt 节点 + 某 checkpoint 发射 CLIPTextEncode,返回 [cid, 0]。按 (prompt,ckpt) 去重。"""
        cid = f"clip_{prompt_pro_id}__{ckpt_cid}"
        if cid not in self.prompt:
            p = _resolved_params(self.g.nodes[prompt_pro_id])
            self.prompt[cid] = {
                "class_type": "CLIPTextEncode",
                "inputs": {"clip": [ckpt_cid, 1], "text": p["text"]},
            }
        return [cid, 0]

    def _empty_neg(self, gen_id: str, ckpt_cid: str) -> list:
        cid = f"clip_neg_empty_{gen_id}"
        if cid not in self.prompt:
            self.prompt[cid] = {
                "class_type": "CLIPTextEncode",
                "inputs": {"clip": [ckpt_cid, 1], "text": ""},
            }
        return [cid, 0]

    def _is_cached(self, pro_id: str) -> bool:
        """Generate 节点是否命中缓存(已生成产物)→ 不重渲染,直接用 cached_url。"""
        n = self.g.nodes[pro_id]
        return n["type"] == "Generate" and bool(n.get("cached") and n.get("cached_url"))

    def _cached_ref(self, pro_id: str) -> list:
        """缓存命中的 Generate → 发射一个 LoadImage(cached_url),返回其 image 输出 [cid, 0]。"""
        cid = f"cached_{pro_id}"
        if cid not in self.prompt:
            self.prompt[cid] = {
                "class_type": "LoadImage",
                "inputs": {"image": self.g.nodes[pro_id].get("cached_url") or ""},
            }
        return [cid, 0]

    def _image_ref(self, pro_id: str) -> list:
        """某 Pro 节点的 image 输出 → ComfyUI [cid, idx]。"""
        ntype = self.g.nodes[pro_id]["type"]
        if ntype in ("LoadImage", "Anchor"):
            cid = f"load_{pro_id}"
            if cid not in self.prompt:
                p = _resolved_params(self.g.nodes[pro_id])
                self.prompt[cid] = {
                    "class_type": "LoadImage",
                    # 注:原生 LoadImage 读 input 目录文件名;从 URL 载图需自定义节点
                    # (LoadImageFromUrl 等)。这里把 url/filename 放进 image,SelfHosted
                    # 实例需配 URL-capable loader(plan §8 节点版本 pin)。fixture 路径不关心。
                    "inputs": {"image": p.get("image_url") or ""},
                }
            return [cid, 0]
        if ntype == "Generate":
            # 缓存命中(review 修复):成本路径已把 cached 节点算 ¥0(estimate 跳过),执行路径
            # 必须一致 —— 不再发射 KSampler 重渲染,而是从 cached_url 载图,下游引用它。
            # 否则 cached 镜照样在 GPU/按次计费 provider 上重跑,花的钱对成本闸不可见(#1 头号金钱风险类)。
            if self._is_cached(pro_id):
                return self._cached_ref(pro_id)
            return [f"vae_decode_{pro_id}", 0]
        if ntype == "Upscale":
            return self._emit_upscale(pro_id)
        raise CompileError("port_type_mismatch", f"{ntype} 不产出 image,无法作图像源")

    def _emit_upscale(self, pro_id: str) -> list:
        """放大(ImageScaleBy,免费插值)。按需发射,递归解析其 image 输入。"""
        cid = f"upscale_{pro_id}"
        if cid not in self.prompt:
            src = self._src(pro_id, "image")  # validate 保证必填存在
            p = _resolved_params(self.g.nodes[pro_id])
            self.prompt[cid] = {
                "class_type": "ImageScaleBy",
                "inputs": {
                    "image": self._image_ref(src.node_id),
                    "upscale_method": p["upscale_method"],
                    "scale_by": p["scale_by"],
                },
            }
        return [cid, 0]

    def _video_ref(self, pro_id: str) -> list:
        """Video 节点的 video 输出(帧批)。Video 在 build() 的 Video 循环里发射,这里返回其解码 ref。"""
        if self.g.nodes[pro_id]["type"] != "Video":
            # Compose 等非 Video 的 video 产出在 ComfyUI 不支持(合成走境内 ffmpeg)。
            raise CompileError("comfyui_unsupported", "合成成片(Compose)仅支持境内执行后端")
        return [f"svd_decode_{pro_id}", 0]

    def _emit_video(self, vid_id: str) -> None:
        """图生视频(i2v)→ ComfyUI SVD 子图。注:依赖 SelfHosted 实例装有 SVD 节点+检查点
        (video_ckpt),按部署 pin(plan §8);结构(image 接好 + 参数 + 输出被引用)被单测锁。"""
        p = _resolved_params(self.g.nodes[vid_id])
        img_src = self._src(vid_id, "image")  # validate 保证必填
        img = self._image_ref(img_src.node_id)
        ckpt = f"svd_ckpt_{vid_id}"
        self.prompt[ckpt] = {
            "class_type": "ImageOnlyCheckpointLoader",
            "inputs": {"ckpt_name": p["video_ckpt"]},
        }
        cond = f"svd_cond_{vid_id}"
        frames = max(1, int(p["duration"]) * int(p["fps"]))
        self.prompt[cond] = {
            "class_type": "SVD_img2vid_Conditioning",
            "inputs": {
                "clip_vision": [ckpt, 1],
                "init_image": img,
                "vae": [ckpt, 2],
                "width": 1024,
                "height": 576,
                "video_frames": frames,
                "motion_bucket_id": p["motion"],
                "fps": p["fps"],
                "augmentation_level": 0.0,
            },
        }
        ks = f"svd_sampler_{vid_id}"
        self.prompt[ks] = {
            "class_type": "KSampler",
            "inputs": {
                "model": [ckpt, 0],
                "positive": [cond, 0],
                "negative": [cond, 1],
                "latent_image": [cond, 2],
                "seed": 0,
                "steps": 20,
                "cfg": 2.5,
                "sampler_name": "euler",
                "scheduler": "karras",
                "denoise": 1.0,
            },
        }
        self.prompt[f"svd_decode_{vid_id}"] = {
            "class_type": "VAEDecode",
            "inputs": {"samples": [ks, 0], "vae": [ckpt, 2]},
        }

    def _output_type(self, pro_id: str, handle: str) -> str | None:
        nt = NODE_TYPES[self.g.nodes[pro_id]["type"]]
        port = nt.output(handle)
        return port.type if port else None

    def _emit_generate(self, gen_id: str) -> None:
        params = _resolved_params(self.g.nodes[gen_id])
        model_src = self._src(gen_id, "model")
        pos_src = self._src(gen_id, "positive")
        # ComfyUI 必须有 checkpoint(model 在 registry 是可选 —— 境内 Seedream 不需要;故在此 ComfyUI
        # 编译点强制,而非通用 validate)。positive 由 validate 保证存在。
        if model_src is None:
            raise CompileError("missing_required_input", f"生成图像({gen_id})连 ComfyUI 需要 Model 输入")
        ckpt = self._ckpt(model_src.node_id)
        pos_ref = self._clip_encode(pos_src.node_id, ckpt)
        neg_src = self._src(gen_id, "negative")
        neg_ref = self._clip_encode(neg_src.node_id, ckpt) if neg_src else self._empty_neg(gen_id, ckpt)

        img_src = self._src(gen_id, "image")
        if img_src:  # 图生图
            venc = f"vae_encode_{gen_id}"
            self.prompt[venc] = {
                "class_type": "VAEEncode",
                "inputs": {"pixels": self._image_ref(img_src.node_id), "vae": [ckpt, 2]},
            }
            latent = [venc, 0]
        else:  # 文生图
            lat = f"latent_{gen_id}"
            self.prompt[lat] = {
                "class_type": "EmptyLatentImage",
                "inputs": {"width": params["width"], "height": params["height"], "batch_size": 1},
            }
            latent = [lat, 0]

        ks = f"ksampler_{gen_id}"
        self.prompt[ks] = {
            "class_type": "KSampler",
            "inputs": {
                "model": [ckpt, 0],
                "positive": pos_ref,
                "negative": neg_ref,
                "latent_image": latent,
                "seed": params["seed"],
                "steps": params["steps"],
                "cfg": params["cfg"],
                "sampler_name": params["sampler_name"],
                "scheduler": params["scheduler"],
                "denoise": params["denoise"],
            },
        }
        self.prompt[f"vae_decode_{gen_id}"] = {
            "class_type": "VAEDecode",
            "inputs": {"samples": [ks, 0], "vae": [ckpt, 2]},
        }

    def _emit_preview(self, prev_id: str) -> None:
        img_src = self._src(prev_id, "image")  # validate 保证必填
        # 上游产出 video → 存视频(SaveAnimatedWEBP);否则存图(SaveImage)。Preview 输入是 ANY。
        if self._output_type(img_src.node_id, img_src.handle) == PortType.VIDEO:
            p = _resolved_params(self.g.nodes[img_src.node_id])
            self.prompt[f"save_{prev_id}"] = {
                "class_type": "SaveAnimatedWEBP",
                "inputs": {
                    "images": self._video_ref(img_src.node_id),
                    "fps": float(p.get("fps", 8)),
                    "lossless": False,
                    "quality": 90,
                    "method": "default",
                    "filename_prefix": "rhtv_pro",
                },
            }
        else:
            self.prompt[f"save_{prev_id}"] = {
                "class_type": "SaveImage",
                "inputs": {"images": self._image_ref(img_src.node_id), "filename_prefix": "rhtv_pro"},
            }

    def build(self) -> dict[str, dict]:
        # 先发射所有未命中缓存的 Generate(其 vae_decode id 被下游确定性引用)+ Video(SVD 链),
        # 再发射 Preview。命中缓存的 Generate 不发射 KSampler 链(由 _image_ref 解析成 cached
        # LoadImage),与 estimate_graph_cost 的 ¥0 记账一致 —— cached 镜不重渲染、不重复花钱。
        # Upscale 是纯变换,按需在 _image_ref 里 lazy 发射(被消费才出现)。
        for nid in self.g.order:
            t = self.g.nodes[nid]["type"]
            if t == "Generate" and not self._is_cached(nid):
                self._emit_generate(nid)
            elif t == "Video":
                self._emit_video(nid)
        for nid in self.g.order:
            if self.g.nodes[nid]["type"] == "Preview":
                self._emit_preview(nid)
        return self.prompt


def _compile_runninghub(graph: dict, g: _Graph) -> dict:
    """RunningHub Advanced API payload(best-effort,真 workflowId 映射属 P3)。

    把每个节点的参数摊平成 nodeInfoList 字段覆盖。workflowId 取自 graph.workflowId。
    """
    node_info: list[dict] = []
    for nid in g.order:
        node = g.nodes[nid]
        params = _resolved_params(node)
        for field_name, field_value in params.items():
            node_info.append({"nodeId": nid, "fieldName": field_name, "fieldValue": field_value})
    return {"workflowId": str(graph.get("workflowId") or ""), "nodeInfoList": node_info}


def compile_graph(graph: dict, *, target: str = TARGET_SELFHOSTED) -> dict:
    """校验并编译 Pro 图 → 执行后端 payload。非法图抛 CompileError。"""
    g = validate_graph(graph)
    if target == TARGET_RUNNINGHUB:
        return _compile_runninghub(graph, g)
    return _ComfyEmitter(g).build()


# ── 成本估算 ─────────────────────────────────────────────────────────────────────


def estimate_graph_cost(graph: dict) -> dict[str, Any]:
    """估算整图成本(只数 billable 且未命中缓存的节点)。先 validate 保证图合法。

    返回 {"billable_node_count","cached_skipped","cost_cny"}。cost_cny 经
    cost_guard.predict_generation_cost('comfyui', n_images=...) 计算 —— 与 Run 时记账同源单价。
    """
    g = validate_graph(graph)
    # 延迟导入避免循环依赖(cost_guard 不依赖 comfyui)。
    from agent.cascade.cost_guard import predict_generation_cost

    billable = 0
    cached = 0
    cost_cny = 0.0
    for nid in g.order:
        node = g.nodes[nid]
        nt = get_node_type(node["type"])
        if not nt or not nt.billable:
            continue
        if node.get("cached") and node.get("cached_url"):
            cached += 1
            continue
        billable += 1
        # 按 cost_kind 计价(与 worker 记账同源)。video=按 duration 秒;其余(image)=按图。
        if nt.cost_kind == "video":
            params = _resolved_params(node)
            secs = float(params.get(nt.duration_param) or 0) if nt.duration_param else 0.0
            cost_cny += predict_generation_cost("video", video_seconds=secs)
        else:
            cost_cny += predict_generation_cost("comfyui", n_images=1)

    return {"billable_node_count": billable, "cached_skipped": cached, "cost_cny": round(cost_cny, 4)}
