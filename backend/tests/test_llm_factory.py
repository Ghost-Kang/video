from __future__ import annotations

import pytest

from agent import config
from agent.llm_factory import current_model_name, get_chat_model


def test_factory_returns_doubao_when_provider_doubao(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "LLM_PROVIDER", "doubao")
    monkeypatch.setattr(config, "ARK_API_KEY", "fake")
    monkeypatch.setattr(config, "ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
    monkeypatch.setattr(config, "DOUBAO_MODEL", "doubao-seed-2-0-pro")

    model = get_chat_model()

    assert model.__class__.__name__ == "ChatOpenAI"
    assert str(model.openai_api_base).startswith("https://ark.cn-beijing.volces.com")
    assert current_model_name() == "doubao-seed-2-0-pro"


def test_factory_returns_gemini_when_provider_gemini(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "LLM_PROVIDER", "gemini")
    monkeypatch.setattr(config, "GOOGLE_API_KEY", "fake")
    monkeypatch.setattr(config, "LLM_MODEL", "gemini-3-flash-preview")

    model = get_chat_model()

    assert model.__class__.__name__ == "ChatGoogleGenerativeAI"
    assert current_model_name() == "gemini-3-flash-preview"


def test_factory_raises_when_api_key_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "LLM_PROVIDER", "doubao")
    monkeypatch.setattr(config, "ARK_API_KEY", "")

    with pytest.raises(RuntimeError, match="ARK_API_KEY missing"):
        get_chat_model()
