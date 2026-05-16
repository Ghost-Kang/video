"""导演 agent 连通性验证"""

import pytest
from agent.main import create_director_agent


def test_director_agent():
    """验证 director agent 能正常创建和响应"""
    agent = create_director_agent()
    result = agent.invoke({
        "messages": [{"role": "user", "content": "你好，我想创作一支30秒的科幻短片"}]
    })

    # deepagents 的响应在 messages 中
    assert result["messages"]
    last_msg = result["messages"][-1]
    assert last_msg.content
    print(f"Director 响应: {last_msg.content[:200]}...")
