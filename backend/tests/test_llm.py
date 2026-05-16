"""LLM 连通性验证"""

import pytest
from langchain_google_genai import ChatGoogleGenerativeAI

from agent import config


def test_llm_connectivity():
    """验证 Gemini 能正常调用"""
    model = ChatGoogleGenerativeAI(model=config.LLM_MODEL)
    response = model.invoke("你好，请用一句话介绍你自己")
    assert response.content
    assert len(response.content) > 0
    print(f"LLM 响应: {response.content}")
