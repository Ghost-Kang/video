"""主题→脚本 LLM 模块单测(mock ainvoke,不打真模型)。"""

from __future__ import annotations

import asyncio

import pytest

from agent.comfyui.script_gen import (
    ScriptGenError,
    generate_script_from_theme,
    generate_shots_from_script,
)


class _Res:
    def __init__(self, content):
        self.content = content


def _fake_model(*contents):
    seq = list(contents)

    class M:
        async def ainvoke(self, msgs):
            return _Res(seq.pop(0))

    return M()


def _patch_model(monkeypatch, model):
    monkeypatch.setattr("agent.comfyui.script_gen.get_chat_model", lambda: model)
    monkeypatch.setattr("agent.comfyui.script_gen.current_model_name", lambda: "doubao-test")


def test_parses_clean_json(monkeypatch):
    _patch_model(monkeypatch, _fake_model('{"script_markdown":"# 脚本","shots":[{"visual":"开场","dialogue":"钩子"},{"visual":"正文"}]}'))
    out = asyncio.run(generate_script_from_theme("主题"))
    assert out["script_markdown"] == "# 脚本"
    assert [s["shot_index"] for s in out["shots"]] == [1, 2]
    assert out["shots"][0]["visual"] == "开场" and out["shots"][0]["dialogue"] == "钩子"
    assert out["model"] == "doubao-test"


def test_strips_code_fence(monkeypatch):
    _patch_model(monkeypatch, _fake_model('```json\n{"script_markdown":"x","shots":[{"visual":"a"}]}\n```'))
    out = asyncio.run(generate_script_from_theme("主题"))
    assert len(out["shots"]) == 1 and out["shots"][0]["visual"] == "a"


def test_retry_on_bad_json_then_ok(monkeypatch):
    _patch_model(monkeypatch, _fake_model("not json at all", '{"script_markdown":"y","shots":[{"visual":"b"}]}'))
    out = asyncio.run(generate_script_from_theme("主题"))
    assert out["shots"][0]["visual"] == "b"


def test_bad_output_raises(monkeypatch):
    _patch_model(monkeypatch, _fake_model("garbage", "still garbage"))
    with pytest.raises(ScriptGenError) as ei:
        asyncio.run(generate_script_from_theme("主题"))
    assert ei.value.code == "bad_output"


def test_shots_without_visual_dropped(monkeypatch):
    _patch_model(monkeypatch, _fake_model('{"script_markdown":"z","shots":[{"dialogue":"只有口播"},{"visual":"有画面"}]}'))
    out = asyncio.run(generate_script_from_theme("主题"))
    assert len(out["shots"]) == 1 and out["shots"][0]["visual"] == "有画面"


def test_empty_theme_raises():
    with pytest.raises(ScriptGenError) as ei:
        asyncio.run(generate_script_from_theme("   "))
    assert ei.value.code == "theme_required"


def test_shots_capped_at_12(monkeypatch):
    many = ",".join('{"visual":"v%d"}' % i for i in range(20))
    _patch_model(monkeypatch, _fake_model('{"script_markdown":"x","shots":[%s]}' % many))
    out = asyncio.run(generate_script_from_theme("主题"))
    assert len(out["shots"]) == 12


# ── 脚本卡重生(script → shots) ─────────────────────────────────────────────────


def test_shots_from_script_keeps_script(monkeypatch):
    _patch_model(monkeypatch, _fake_model('{"shots":[{"visual":"开场","dialogue":"d"},{"visual":"结尾"}]}'))
    out = asyncio.run(generate_shots_from_script("# 我的脚本正文"))
    assert out["script_markdown"] == "# 我的脚本正文"  # 保留用户编辑的脚本
    assert [s["shot_index"] for s in out["shots"]] == [1, 2]
    assert out["shots"][0]["visual"] == "开场"


def test_shots_from_script_empty_raises():
    with pytest.raises(ScriptGenError) as ei:
        asyncio.run(generate_shots_from_script("   "))
    assert ei.value.code == "script_required"


def test_shots_from_script_bad_output_raises(monkeypatch):
    _patch_model(monkeypatch, _fake_model("garbage", "still garbage"))
    with pytest.raises(ScriptGenError) as ei:
        asyncio.run(generate_shots_from_script("# 脚本"))
    assert ei.value.code == "bad_output"
