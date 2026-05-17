"""生图 API 测试"""

import asyncio
from agent.tools.generation import submit_image, poll_image


def test_submit_image():
    """提交任务，拿到 task_id"""
    result = submit_image("一只橘猫坐在窗台上看夕阳，水彩画风格")
    print(f"提交结果: {result}")
    assert "task_id" in result, result


def test_submit_and_poll():
    """提交 + 轮询，验证全链路"""
    result = submit_image("赛博朋克城市夜景")
    print(f"task_id: {result['task_id']}")
    assert "task_id" in result

    polled = asyncio.run(poll_image(result["task_id"]))
    print(f"轮询结果: {polled}")
    assert "url" in polled, polled
