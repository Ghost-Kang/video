"""Provider switch for text LLM calls."""

from __future__ import annotations

import os

from agent import config


def get_chat_model():
    """Return a LangChain chat model for the configured provider."""
    provider = config.LLM_PROVIDER.lower().strip()
    if provider == "doubao":
        from langchain_openai import ChatOpenAI

        if not config.ARK_API_KEY:
            raise RuntimeError("LLM_PROVIDER=doubao but ARK_API_KEY missing")
        return ChatOpenAI(
            model=config.DOUBAO_MODEL,
            base_url=config.ARK_BASE_URL,
            api_key=config.ARK_API_KEY,
        )
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        api_key = config.GOOGLE_API_KEY or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("LLM_PROVIDER=gemini but GOOGLE_API_KEY missing")
        return ChatGoogleGenerativeAI(model=config.LLM_MODEL, api_key=api_key)
    raise RuntimeError(f"unknown LLM_PROVIDER={provider!r}; expected doubao|gemini")


def current_model_name() -> str:
    provider = config.LLM_PROVIDER.lower().strip()
    if provider == "doubao":
        return config.DOUBAO_MODEL
    return config.LLM_MODEL
