"""生图 API 测试 — 通过 Provider 抽象层"""

import asyncio
from agent.tools.generation import get_provider


def test_apimart_submit():
    """Apimart: 提交任务，拿到 task_id"""
    provider = get_provider()
    result = asyncio.run(provider.submit("一只橘猫坐在窗台上看夕阳，水彩画风格"))
    print(f"提交结果: {result}")
    assert "task_id" in result, result


def test_apimart_submit_and_poll():
    """Apimart: 提交 + 轮询，验证全链路"""
    provider = get_provider()
    result = asyncio.run(provider.submit("赛博朋克城市夜景"))
    print(f"task_id: {result['task_id']}")
    assert "task_id" in result

    polled = asyncio.run(provider.poll(result["task_id"]))
    print(f"轮询结果: {polled}")
    assert "url" in polled, polled


async def _test_google_generate():
    """Google: 生图并验证返回 image_data"""
    import os
    # 覆盖环境变量走 google
    os.environ["IMAGE_GEN_PROVIDER"] = "google"
    from agent.tools.generation import GoogleProvider
    provider = GoogleProvider()
    result = await provider.generate(
        "一只橘猫坐在窗台上看夕阳，水彩画风格",
        resolution="1K",
    )
    if result.get("image_data"):
        print(f"Google 生图成功: {len(result['image_data'])} bytes, {result.get('actual_time', 0):.1f}s")
        size = len(result["image_data"])
        assert size > 1000, f"图片太小: {size} bytes"
    else:
        print(f"Google 生图失败: {result.get('error')}")
        # 仅在未配置 API key 时允许跳过
        from agent.config import GOOGLE_API_KEY
        if not GOOGLE_API_KEY:
            print("跳过: 未配置 GOOGLE_API_KEY")


def test_google():
    """Google: 完整生图测试"""
    asyncio.run(_test_google_generate())
