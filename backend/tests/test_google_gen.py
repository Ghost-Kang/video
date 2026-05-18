"""Google Gemini 生图测试

使用 Gemini API (google.ai.dev)，仅支持 response_modalities 参数。
image_config 和 media_resolution 是 Vertex AI 专属参数。
"""

from __future__ import annotations

import io
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from PIL import Image as PILImage

# 加载 .env
_project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(_project_root / ".env")

MODEL = "gemini-3.1-flash-image-preview"


def _call(prompt: str, refs: list[PILImage.Image] | None = None):
    """封装 Google Gemini 生图调用，返回 (texts, images)。"""
    client = genai.Client()
    contents = [prompt] + (refs or [])

    response = client.models.generate_content(
        model=MODEL,
        contents=contents,
        config={"response_modalities": ["TEXT", "IMAGE"]},
    )

    texts = []
    images = []
    for part in response.parts:
        if part.text is not None:
            texts.append(part.text)
        elif img := part.as_image():
            pil_img = PILImage.open(io.BytesIO(img.image_bytes))
            images.append((img, pil_img))

    return texts, images


def _save(genai_img, path: str):
    genai_img.save(path)
    pil = PILImage.open(io.BytesIO(genai_img.image_bytes))
    print(f"[图片] 已保存 → {path}  ({pil.width}x{pil.height})")


def test_text_to_image():
    """纯文本生图"""
    texts, images = _call(
        "A little boy, sitting on a cozy windowsill, holding a book, bathed in warm afternoon sunlight, "
        "reading. The atmosphere is peaceful and nostalgic, soft lighting, shallow depth of field, "
        "photorealistic 4k quality."
    )

    for t in texts:
        print(f"[文本] {t[:200]}")
    for i, (img, _) in enumerate(images):
        _save(img, "/tmp/google_gen_test_text.png")


def test_image_to_image():
    """参考图生图"""
    ref = PILImage.open("/tmp/google_gen_test_text.png")

    texts, images = _call(
        "The same boy holding an orange tabby cat, sitting on the windowsill",
        refs=[ref],
    )

    for t in texts:
        print(f"[文本] {t[:200]}")
    for i, (img, _) in enumerate(images):
        _save(img, "/tmp/google_gen_test_ref.png")


def test_multiple_refs():
    """多张参考图生图"""
    ref1 = PILImage.open("/tmp/google_gen_test_text.png")
    ref2 = PILImage.open("/tmp/google_gen_test_ref.png")

    texts, images = _call(
        "The same boy holding the same orange tabby cat, reading a book together on the windowsill",
        refs=[ref1, ref2],
    )

    for t in texts:
        print(f"[文本] {t[:200]}")
    for i, (img, _) in enumerate(images):
        _save(img, "/tmp/google_gen_test_multi.png")


def test_aspect_ratio_guidance():
    """通过 prompt 引导不同宽高比"""
    test_cases = [
        ("A cute shiba inu portrait, square format, 1:1 aspect ratio", "正方形头像"),
        ("A cute shiba inu standing, vertical poster, 9:16 aspect ratio", "竖屏海报"),
        ("A cute shiba inu running, landscape wallpaper, 16:9 aspect ratio", "横屏壁纸"),
    ]

    for prompt, desc in test_cases:
        print(f"\n测试: {desc}")
        texts, images = _call(prompt)
        for t in texts:
            print(f"  [文本] {t[:100]}")
        for i, (img, pil) in enumerate(images):
            path = f"/tmp/google_gen_test_aspect_{i}.png"
            _save(img, path)


if __name__ == "__main__":
    print("=" * 50)
    print("测试 1: 纯文本生图")
    print("=" * 50)
    test_text_to_image()

    print("\n" + "=" * 50)
    print("测试 2: 参考图生图")
    print("=" * 50)
    test_image_to_image()

    print("\n" + "=" * 50)
    print("测试 3: 多参考图生图")
    print("=" * 50)
    test_multiple_refs()

    print("\n" + "=" * 50)
    print("测试 4: 宽高比引导")
    print("=" * 50)
    test_aspect_ratio_guidance()
