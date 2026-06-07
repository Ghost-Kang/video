"""av_post 字幕换行(纯函数,可测;ffmpeg 路径靠 prod 真机验证)。"""

from __future__ import annotations

from agent.tools.av_post import _wrap_caption


def test_short_caption_single_line():
    assert _wrap_caption("南瓜泥") == "南瓜泥"


def test_long_cjk_wraps():
    out = _wrap_caption("新手妈妈别愁南瓜泥这样做营养又简单快收藏", per_line=8)
    lines = out.split("\n")
    assert len(lines) >= 2
    # 每行视觉宽度不超 per_line(CJK 计 1.0)
    for ln in lines:
        assert len(ln) <= 8


def test_truncate_to_max_lines_with_ellipsis():
    out = _wrap_caption("一二三四五六七八九十" * 5, per_line=5, max_lines=3)
    lines = out.split("\n")
    assert len(lines) == 3
    assert lines[-1].endswith("…")


def test_collapses_whitespace():
    assert _wrap_caption("  a   b  ") == "a b"


def test_empty():
    assert _wrap_caption("") == ""


def test_ascii_half_width():
    # ASCII 半宽:per_line=4 → 能放 ~8 个 ASCII
    out = _wrap_caption("abcdefgh", per_line=4)
    assert out == "abcdefgh"  # 8*0.5=4.0,不超
