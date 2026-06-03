"""canvas 统筹 P2 ④ — 长会话上下文降本中间件(SummarizationMiddleware)的 flag 门控。
默认 OFF → build_middleware 返回 None(行为不变);ON → 挂一个 SummarizationMiddleware。"""

import agent.config as config
from agent.main import build_middleware, get_chat_model


def test_off_by_default_returns_none(monkeypatch):
    monkeypatch.setattr(config, "CANVAS_CONTEXT_MIDDLEWARE", False)
    assert build_middleware(model=get_chat_model()) is None


def test_on_returns_one_summarization_middleware(monkeypatch):
    from langchain.agents.middleware import SummarizationMiddleware

    monkeypatch.setattr(config, "CANVAS_CONTEXT_MIDDLEWARE", True)
    monkeypatch.setattr(config, "CONTEXT_SUMMARY_TRIGGER_TOKENS", 120000)
    monkeypatch.setattr(config, "CONTEXT_SUMMARY_KEEP_MESSAGES", 30)
    mw = build_middleware(model=get_chat_model())
    assert mw is not None and len(mw) == 1
    assert isinstance(mw[0], SummarizationMiddleware)
