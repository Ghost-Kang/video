"""agent_runner.extract_text pure-function unit tests.

`extract_text` 把 LangChain message content(可能是 str 或 part-list)抽成纯文本。
run_agent 和 optimize_prompt 都依赖它正确处理 multi-modal content,但因为流处理
在 streaming 上下文里很难 mock,这里只测 pure helper。
"""

from __future__ import annotations

from agent.transport.agent_runner import extract_text


class TestExtractText:
    def test_plain_string(self):
        assert extract_text("hello") == "hello"

    def test_empty_string(self):
        assert extract_text("") == ""

    def test_text_part_list(self):
        # LangChain content 可能是 [{"type": "text", "text": "..."}] 形式
        content = [{"type": "text", "text": "first"}, {"type": "text", "text": "second"}]
        assert extract_text(content) == "first\nsecond"

    def test_mixed_part_list_skips_non_text(self):
        # 非 text part(如 image_url)应该被跳过
        content = [
            {"type": "text", "text": "hi"},
            {"type": "image_url", "image_url": "https://..."},
            {"type": "text", "text": "bye"},
        ]
        assert extract_text(content) == "hi\nbye"

    def test_empty_part_list(self):
        assert extract_text([]) == ""

    def test_text_part_missing_field(self):
        # {"type": "text"} 没有 text 字段 → 默认 ""
        content = [{"type": "text"}]
        assert extract_text(content) == ""

    def test_text_part_with_empty_string(self):
        content = [{"type": "text", "text": ""}, {"type": "text", "text": "x"}]
        assert extract_text(content) == "\nx"

    def test_unknown_type_fallback_to_str(self):
        # 既不是 str 也不是 list → fallback str()
        assert extract_text(42) == "42"
        assert extract_text(None) == "None"

    def test_dict_fallback(self):
        # 单个 dict(不是 list)→ fallback str()
        result = extract_text({"unexpected": "shape"})
        assert "unexpected" in result  # str() of dict 包含 key
