"""Pro 节点注册表(单一真相源)单测。"""

from __future__ import annotations

from agent.comfyui.node_registry import (
    NODE_TYPES,
    PROVIDER_ANY,
    PortType,
    get_node_type,
    is_billable,
    node_available_for_provider,
    registry_json,
)


def test_node_types_present():
    assert set(NODE_TYPES) == {
        "Model", "Prompt", "LoadImage", "Anchor", "Generate", "Upscale", "Video", "Preview",
    }


def test_billable_nodes_are_generate_and_video():
    assert is_billable("Generate") is True
    assert is_billable("Video") is True
    for k in ("Model", "Prompt", "LoadImage", "Anchor", "Upscale", "Preview"):
        assert is_billable(k) is False


def test_cost_kinds():
    assert NODE_TYPES["Generate"].cost_kind == "image"
    assert NODE_TYPES["Video"].cost_kind == "video"
    assert NODE_TYPES["Video"].duration_param == "duration"


def test_generate_ports():
    gen = get_node_type("Generate")
    assert gen is not None
    assert gen.input("model").required is True
    assert gen.input("positive").required is True
    assert gen.input("negative").required is False
    assert gen.input("image").required is False
    assert gen.output("image").type == PortType.IMAGE


def test_get_node_type_unknown_returns_none():
    assert get_node_type("Nope") is None


def test_all_mvp_nodes_available_to_any_provider():
    for k in NODE_TYPES:
        assert node_available_for_provider(k, "selfhosted") is True
        assert node_available_for_provider(k, "runninghub") is True
    assert node_available_for_provider("Nope", "selfhosted") is False


def test_registry_json_is_serializable_and_complete():
    import json

    j = registry_json()
    # round-trips through JSON (frontend consumes this)
    json.dumps(j)
    keys = {n["key"] for n in j["nodes"]}
    assert keys == set(NODE_TYPES)
    gen = next(n for n in j["nodes"] if n["key"] == "Generate")
    assert gen["billable"] is True
    assert {p["name"] for p in gen["inputs"]} == {"model", "positive", "negative", "image"}
    # params carry defaults + choices
    prompt = next(n for n in j["nodes"] if n["key"] == "Prompt")
    role = next(p for p in prompt["params"] if p["name"] == "role")
    assert role["choices"] == ["positive", "negative"]


def test_provider_any_constant():
    assert PROVIDER_ANY in get_node_type("Model").providers
