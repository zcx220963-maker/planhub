"""
Chat节点 - 简单对话Agent
处理闲聊和简单问答
"""

from langchain_core.messages import SystemMessage, HumanMessage
from src.app.common.llm_factory import get_llm

CHAT_SYSTEM_PROMPT = """你是一个友好的聊天助手，名叫PlanHub助手。

你的职责：
1. 友好地回应用户的问候和闲聊
2. 介绍自己的能力（计划生成、知识查询、工具调用等）
3. 如果用户有具体需求，引导他们使用相应的功能

请保持简洁、友好的语气，不要超过100字。
"""


async def chat_node(state) -> dict:
    """Chat节点：简单对话"""
    try:
        llm = get_llm()

        # 构建消息
        messages = [
            SystemMessage(content=CHAT_SYSTEM_PROMPT),
            HumanMessage(content=state.get("user_input", ""))
        ]

        # 调用LLM
        response = await llm.ainvoke(messages)
        result = response.content if hasattr(response, 'content') else str(response)

        # 更新状态
        return {
            "agent_output": result,
            "execution_trace": [
                *state.get("execution_trace", []),
                {
                    "node": "chat",
                    "success": True,
                    "response_length": len(result)
                }
            ]
        }

    except Exception as e:
        return {
            "agent_output": "你好！我是PlanHub助手，有什么可以帮你的吗？",
            "error": str(e),
            "execution_trace": [
                *state.get("execution_trace", []),
                {
                    "node": "chat",
                    "error": str(e),
                    "success": False,
                    "fallback": True
                }
            ]
        }
