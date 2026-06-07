"""Pro 图编译器单测(plan §8 头号风险:图编译正确性)。

锁:校验(8 类错误码)、self-host ComfyUI prompt 结构(文生图/图生图展开)、RunningHub payload、成本估算。
"""

from __future__ import annotations

import pytest

from agent.comfyui.compiler import (
    CompileError,
    compile_graph,
    estimate_graph_cost,
    validate_graph,
)


def _text2img_graph():
    return {
        "version": 1,
        "nodes": [
            {"id": "m", "type": "Model", "params": {"ckpt_name": "x.safetensors"}},
            {"id": "p", "type": "Prompt", "params": {"text": "一只猫", "role": "positive"}},
            {"id": "n", "type": "Prompt", "params": {"text": "模糊", "role": "negative"}},
            {"id": "g", "type": "Generate", "params": {"steps": 25, "seed": 7, "width": 768, "height": 512}},
            {"id": "v", "type": "Preview", "params": {}},
        ],
        "edges": [
            {"id": "e1", "source": "m", "sourceHandle": "model", "target": "g", "targetHandle": "model"},
            {"id": "e2", "source": "p", "sourceHandle": "text", "target": "g", "targetHandle": "positive"},
            {"id": "e3", "source": "n", "sourceHandle": "text", "target": "g", "targetHandle": "negative"},
            {"id": "e4", "source": "g", "sourceHandle": "image", "target": "v", "targetHandle": "image"},
        ],
    }


def _img2img_graph():
    g = _text2img_graph()
    g["nodes"].append({"id": "li", "type": "LoadImage", "params": {"image_url": "https://x/y.png"}})
    g["edges"].append({"id": "e5", "source": "li", "sourceHandle": "image", "target": "g", "targetHandle": "image"})
    return g


# ── validate: happy ─────────────────────────────────────────────────────────────


def test_validate_happy():
    g = validate_graph(_text2img_graph())
    assert set(g.nodes) == {"m", "p", "n", "g", "v"}
    assert g.incoming[("g", "model")].node_id == "m"


# ── validate: error codes ───────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "mutate,code",
    [
        (lambda g: g.update(nodes=[]), "empty_graph"),
        (lambda g: g["nodes"].append({"id": "g", "type": "Generate"}), "duplicate_node_id"),
        (lambda g: g["nodes"].append({"id": "z", "type": "Bogus"}), "unknown_node_type"),
    ],
)
def test_validate_node_errors(mutate, code):
    g = _text2img_graph()
    mutate(g)
    with pytest.raises(CompileError) as ei:
        validate_graph(g)
    assert ei.value.code == code


def test_validate_bad_edge_endpoint():
    g = _text2img_graph()
    g["edges"].append({"id": "x", "source": "ghost", "sourceHandle": "image", "target": "v", "targetHandle": "image"})
    with pytest.raises(CompileError) as ei:
        validate_graph(g)
    assert ei.value.code == "bad_edge"


def test_validate_port_type_mismatch():
    # Model.model (model) → Generate.positive (text) — incompatible, neither is ANY.
    # (Preview.image is ANY now to accept image|video, so use a typed pair instead.)
    g = _text2img_graph()
    g["edges"] = [e for e in g["edges"] if e["id"] != "e2"]  # free up Generate.positive
    g["edges"].append({"id": "x", "source": "m", "sourceHandle": "model", "target": "g", "targetHandle": "positive"})
    with pytest.raises(CompileError) as ei:
        validate_graph(g)
    assert ei.value.code == "port_type_mismatch"


def test_validate_multi_input():
    g = _text2img_graph()
    g["edges"].append({"id": "x", "source": "n", "sourceHandle": "text", "target": "g", "targetHandle": "positive"})
    with pytest.raises(CompileError) as ei:
        validate_graph(g)
    assert ei.value.code == "multi_input"


def test_validate_missing_required_input():
    g = _text2img_graph()
    g["edges"] = [e for e in g["edges"] if e["id"] != "e1"]  # drop model edge
    with pytest.raises(CompileError) as ei:
        validate_graph(g)
    assert ei.value.code == "missing_required_input"


def test_validate_no_output():
    g = _text2img_graph()
    g["nodes"] = [n for n in g["nodes"] if n["id"] != "v"]
    g["edges"] = [e for e in g["edges"] if e["id"] != "e4"]
    with pytest.raises(CompileError) as ei:
        validate_graph(g)
    assert ei.value.code == "no_output"


def test_validate_cycle():
    # Two Generates feeding each other's image input -> cycle
    g = {
        "version": 1,
        "nodes": [
            {"id": "m", "type": "Model"},
            {"id": "p", "type": "Prompt", "params": {"text": "x"}},
            {"id": "a", "type": "Generate"},
            {"id": "b", "type": "Generate"},
            {"id": "v", "type": "Preview"},
        ],
        "edges": [
            {"id": "1", "source": "m", "sourceHandle": "model", "target": "a", "targetHandle": "model"},
            {"id": "2", "source": "p", "sourceHandle": "text", "target": "a", "targetHandle": "positive"},
            {"id": "3", "source": "m", "sourceHandle": "model", "target": "b", "targetHandle": "model"},
            {"id": "4", "source": "p", "sourceHandle": "text", "target": "b", "targetHandle": "positive"},
            {"id": "5", "source": "a", "sourceHandle": "image", "target": "b", "targetHandle": "image"},
            {"id": "6", "source": "b", "sourceHandle": "image", "target": "a", "targetHandle": "image"},
            {"id": "7", "source": "a", "sourceHandle": "image", "target": "v", "targetHandle": "image"},
        ],
    }
    with pytest.raises(CompileError) as ei:
        validate_graph(g)
    assert ei.value.code == "cycle"


# ── compile: self-host ComfyUI prompt ───────────────────────────────────────────


def test_compile_text2img_structure():
    prompt = compile_graph(_text2img_graph(), target="selfhosted")
    classes = sorted(v["class_type"] for v in prompt.values())
    assert classes == sorted(
        [
            "CheckpointLoaderSimple",
            "CLIPTextEncode",  # positive
            "CLIPTextEncode",  # negative
            "EmptyLatentImage",
            "KSampler",
            "VAEDecode",
            "SaveImage",
        ]
    )
    ks = next(v for v in prompt.values() if v["class_type"] == "KSampler")
    ckpt_id = next(k for k, v in prompt.items() if v["class_type"] == "CheckpointLoaderSimple")
    # model wired from checkpoint output 0
    assert ks["inputs"]["model"] == [ckpt_id, 0]
    # sampler params carried through
    assert ks["inputs"]["steps"] == 25
    assert ks["inputs"]["seed"] == 7
    # latent from EmptyLatentImage
    lat_id = next(k for k, v in prompt.items() if v["class_type"] == "EmptyLatentImage")
    assert ks["inputs"]["latent_image"] == [lat_id, 0]
    assert prompt[lat_id]["inputs"] == {"width": 768, "height": 512, "batch_size": 1}
    # SaveImage references VAEDecode
    save = next(v for v in prompt.values() if v["class_type"] == "SaveImage")
    vd_id = next(k for k, v in prompt.items() if v["class_type"] == "VAEDecode")
    assert save["inputs"]["images"] == [vd_id, 0]
    # VAEDecode vae from checkpoint output 2
    assert prompt[vd_id]["inputs"]["vae"] == [ckpt_id, 2]


def test_compile_negative_wired_distinctly():
    prompt = compile_graph(_text2img_graph(), target="selfhosted")
    ks = next(v for v in prompt.values() if v["class_type"] == "KSampler")
    pos_ref = ks["inputs"]["positive"]
    neg_ref = ks["inputs"]["negative"]
    assert pos_ref != neg_ref
    assert prompt[pos_ref[0]]["inputs"]["text"] == "一只猫"
    assert prompt[neg_ref[0]]["inputs"]["text"] == "模糊"


def test_compile_missing_negative_emits_empty():
    g = _text2img_graph()
    g["nodes"] = [n for n in g["nodes"] if n["id"] != "n"]
    g["edges"] = [e for e in g["edges"] if e["id"] != "e3"]
    prompt = compile_graph(g, target="selfhosted")
    ks = next(v for v in prompt.values() if v["class_type"] == "KSampler")
    neg_ref = ks["inputs"]["negative"]
    assert prompt[neg_ref[0]]["inputs"]["text"] == ""


def test_compile_img2img_uses_vaeencode_not_emptylatent():
    prompt = compile_graph(_img2img_graph(), target="selfhosted")
    classes = [v["class_type"] for v in prompt.values()]
    assert "VAEEncode" in classes
    assert "EmptyLatentImage" not in classes
    ks = next(v for v in prompt.values() if v["class_type"] == "KSampler")
    venc_id = next(k for k, v in prompt.items() if v["class_type"] == "VAEEncode")
    assert ks["inputs"]["latent_image"] == [venc_id, 0]
    # VAEEncode pixels from LoadImage
    load_id = next(k for k, v in prompt.items() if v["class_type"] == "LoadImage")
    assert prompt[venc_id]["inputs"]["pixels"] == [load_id, 0]


def test_compile_shared_checkpoint_deduped():
    # two generates off one model -> single CheckpointLoaderSimple
    g = _text2img_graph()
    g["nodes"].append({"id": "g2", "type": "Generate"})
    g["nodes"].append({"id": "v2", "type": "Preview"})
    g["edges"] += [
        {"id": "f1", "source": "m", "sourceHandle": "model", "target": "g2", "targetHandle": "model"},
        {"id": "f2", "source": "p", "sourceHandle": "text", "target": "g2", "targetHandle": "positive"},
        {"id": "f3", "source": "g2", "sourceHandle": "image", "target": "v2", "targetHandle": "image"},
    ]
    prompt = compile_graph(g, target="selfhosted")
    ckpts = [v for v in prompt.values() if v["class_type"] == "CheckpointLoaderSimple"]
    assert len(ckpts) == 1


def test_compile_invalid_graph_raises():
    with pytest.raises(CompileError):
        compile_graph({"nodes": [], "edges": []}, target="selfhosted")


# ── compile: RunningHub payload ─────────────────────────────────────────────────


def test_compile_runninghub_shape():
    g = _text2img_graph()
    g["workflowId"] = "wf-123"
    payload = compile_graph(g, target="runninghub")
    assert payload["workflowId"] == "wf-123"
    assert isinstance(payload["nodeInfoList"], list)
    sample = payload["nodeInfoList"][0]
    assert set(sample) == {"nodeId", "fieldName", "fieldValue"}
    # every param of every node is represented
    assert any(e["nodeId"] == "g" and e["fieldName"] == "steps" for e in payload["nodeInfoList"])


# ── cost estimate ───────────────────────────────────────────────────────────────


def test_estimate_counts_billable_generate_nodes():
    est = estimate_graph_cost(_text2img_graph())
    assert est["billable_node_count"] == 1
    assert est["cached_skipped"] == 0
    assert est["cost_cny"] == pytest.approx(1.5)


def test_upscale_emits_imagescaleby():
    g = _text2img_graph()
    g["nodes"].append({"id": "up", "type": "Upscale", "params": {"scale_by": 2.0}})
    # rewire Preview to take the upscaled image: g -> up -> v
    g["edges"] = [e for e in g["edges"] if e["id"] != "e4"]
    g["edges"].append({"id": "u1", "source": "g", "sourceHandle": "image", "target": "up", "targetHandle": "image"})
    g["edges"].append({"id": "u2", "source": "up", "sourceHandle": "image", "target": "v", "targetHandle": "image"})
    prompt = compile_graph(g, target="selfhosted")
    scale = next((k for k, val in prompt.items() if val["class_type"] == "ImageScaleBy"), None)
    assert scale is not None
    vd = next(k for k, val in prompt.items() if val["class_type"] == "VAEDecode")
    assert prompt[scale]["inputs"]["image"] == [vd, 0]
    save = next(val for val in prompt.values() if val["class_type"] == "SaveImage")
    assert save["inputs"]["images"] == [scale, 0]


def test_video_emits_svd_chain_and_webp_save():
    g = _text2img_graph()
    g["nodes"].append({"id": "vid", "type": "Video", "params": {"duration": 4, "fps": 8}})
    g["edges"] = [e for e in g["edges"] if e["id"] != "e4"]
    g["edges"].append({"id": "v1", "source": "g", "sourceHandle": "image", "target": "vid", "targetHandle": "image"})
    g["edges"].append({"id": "v2", "source": "vid", "sourceHandle": "video", "target": "v", "targetHandle": "image"})
    prompt = compile_graph(g, target="selfhosted")
    classes = [val["class_type"] for val in prompt.values()]
    assert "ImageOnlyCheckpointLoader" in classes
    assert "SVD_img2vid_Conditioning" in classes
    assert "SaveAnimatedWEBP" in classes  # video preview, not SaveImage
    assert "SaveImage" not in classes
    cond = next(val for val in prompt.values() if val["class_type"] == "SVD_img2vid_Conditioning")
    # i2v init_image wired from the generate's VAEDecode
    vd = next(k for k, val in prompt.items() if val["class_type"] == "VAEDecode" and k.startswith("vae_decode_"))
    assert cond["inputs"]["init_image"] == [vd, 0]
    assert cond["inputs"]["video_frames"] == 32  # 4s * 8fps


def test_estimate_video_priced_by_duration():
    g = _text2img_graph()
    g["nodes"].append({"id": "vid", "type": "Video", "params": {"duration": 5, "fps": 8}})
    g["edges"] = [e for e in g["edges"] if e["id"] != "e4"]
    g["edges"].append({"id": "v1", "source": "g", "sourceHandle": "image", "target": "vid", "targetHandle": "image"})
    g["edges"].append({"id": "v2", "source": "vid", "sourceHandle": "video", "target": "v", "targetHandle": "image"})
    est = estimate_graph_cost(g)
    # 1 Generate (¥1.5, image) + 1 Video 5s (5 * ¥0.30 = ¥1.5) = ¥3.0
    assert est["billable_node_count"] == 2
    assert est["cost_cny"] == pytest.approx(3.0)


def test_estimate_skips_cached_generate():
    g = _text2img_graph()
    g["nodes"] = [
        {**n, "cached": True, "cached_url": "https://x/cached.png"} if n["id"] == "g" else n
        for n in g["nodes"]
    ]
    est = estimate_graph_cost(g)
    assert est["billable_node_count"] == 0
    assert est["cached_skipped"] == 1
    assert est["cost_cny"] == pytest.approx(0.0)


# ── cached execution must match the ¥0 estimate (review fix) ─────────────────────


def test_cached_generate_emits_no_ksampler():
    """缓存命中的 Generate 不重渲染:编译产物不含 KSampler/VAEDecode,改为 LoadImage(cached_url),
    下游 Preview 引用它。否则 cached 镜照样烧 GPU/按次扣费,而成本却算 ¥0(成本闸不可见)。"""
    g = _text2img_graph()
    g["nodes"] = [
        {**n, "cached": True, "cached_url": "https://x/cached.png"} if n["id"] == "g" else n
        for n in g["nodes"]
    ]
    prompt = compile_graph(g, target="selfhosted")
    classes = [v["class_type"] for v in prompt.values()]
    assert "KSampler" not in classes
    assert "VAEDecode" not in classes
    # cached LoadImage carries the cached url
    cached = [v for v in prompt.values() if v["class_type"] == "LoadImage"]
    assert any(v["inputs"]["image"] == "https://x/cached.png" for v in cached)
    # Preview (SaveImage) references the cached loader, not a vae_decode
    save = next(v for v in prompt.values() if v["class_type"] == "SaveImage")
    ref_id = save["inputs"]["images"][0]
    assert prompt[ref_id]["class_type"] == "LoadImage"


def test_param_bounds_clamped():
    """registry 的 min/max 服务端强制:steps=99999→150,width=10→64(防客户端编出吃爆 GPU 的图)。"""
    g = _text2img_graph()
    for n in g["nodes"]:
        if n["id"] == "g":
            n["params"] = {"steps": 99999, "width": 10, "cfg": 999, "denoise": 5}
    prompt = compile_graph(g, target="selfhosted")
    ks = next(v for v in prompt.values() if v["class_type"] == "KSampler")
    assert ks["inputs"]["steps"] == 150  # clamped to max
    assert ks["inputs"]["cfg"] == 30.0   # clamped to max
    assert ks["inputs"]["denoise"] == 1.0  # clamped to max
    lat = next(v for v in prompt.values() if v["class_type"] == "EmptyLatentImage")
    assert lat["inputs"]["width"] == 64  # clamped to min
