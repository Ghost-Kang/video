"""主题 → 脚本 + 分镜(Doubao 境内 LLM)。Pro 画布空白入口「输入主题」/自动种子用。

deterministic 结构、境内合规(走 llm_factory 的 doubao)。产出 {script_markdown, shots:[{shot_index,
visual, dialogue}]},分镜数按主题自适应(1-12 钳)。失败抛 ScriptGenError(带机器码,路由映射)。
"""

from __future__ import annotations

import json
import re

from agent.llm_factory import current_model_name, get_chat_model


class ScriptGenError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


_PROMPT = """你是资深短视频编导。根据用户给的【主题】,产出一支可拍摄的竖屏短视频「脚本 + 分镜」。
要求:
- 全程中文。
- 分镜数量按主题复杂度自适应(一般 3~8 个镜,最多 12)。
- 每个分镜给:visual(画面描述,要具体到场景/主体/动作/光线/景别,能直接拿去生成图)、dialogue(口播或字幕,可空)。
- script_markdown 是整篇脚本(含钩子开头、正文、结尾 CTA)。
只输出 JSON,不要任何额外文字、不要 markdown 代码块:
{{"script_markdown": "...", "shots": [{{"visual": "...", "dialogue": "..."}}]}}

【主题】:{theme}
"""

_RETRY = "\n\n上次不是合法 JSON。请严格只输出上面格式的纯 JSON(无代码块、无解释)。"

_MAX_SHOTS = 12


def _extract_json(text: str) -> dict | None:
    t = (text or "").strip()
    # 去掉 ```json ... ``` 包裹
    t = re.sub(r"^```(?:json)?\s*", "", t)
    t = re.sub(r"\s*```$", "", t)
    start, end = t.find("{"), t.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        out = json.loads(t[start : end + 1])
        return out if isinstance(out, dict) else None
    except (json.JSONDecodeError, TypeError):
        return None


def _content(res) -> str:
    return res.content if hasattr(res, "content") else str(res)


async def generate_script_from_theme(theme: str) -> dict:
    theme = (theme or "").strip()
    if not theme:
        raise ScriptGenError("theme_required", "缺少主题")
    if len(theme) > 500:
        theme = theme[:500]

    model = get_chat_model()
    prompt = _PROMPT.format(theme=theme)
    try:
        data = _extract_json(_content(await model.ainvoke([{"role": "user", "content": prompt}])))
        if data is None:
            data = _extract_json(_content(await model.ainvoke([{"role": "user", "content": prompt + _RETRY}])))
    except Exception as e:  # noqa: BLE001 — 网络/LLM 异常统一成 ScriptGenError
        raise ScriptGenError("llm_error", f"脚本生成调用失败: {e}") from e

    if not data or not isinstance(data.get("shots"), list):
        raise ScriptGenError("bad_output", "脚本生成失败,请换个主题或重试")

    shots: list[dict] = []
    for s in data["shots"][:_MAX_SHOTS]:
        if not isinstance(s, dict):
            continue
        visual = str(s.get("visual") or "").strip()
        if not visual:
            continue
        shots.append({"shot_index": len(shots) + 1, "visual": visual, "dialogue": str(s.get("dialogue") or "").strip()})

    if not shots:
        raise ScriptGenError("bad_output", "脚本没有可用分镜,请换个主题或重试")

    return {
        "script_markdown": str(data.get("script_markdown") or "").strip(),
        "shots": shots,
        "model": current_model_name(),
    }
