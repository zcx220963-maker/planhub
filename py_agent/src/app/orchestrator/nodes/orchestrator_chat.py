"""
Chat节点 - 简单对话Agent
处理闲聊和简单问答

核心改进：
1. 支持 RAG fallback：如果 rag_fallback_to_chat=True，先提示"知识库未命中，正在思考..."
2. 检查 execution_trace 了解 fallback 原因，在回答中给出更友好的提示
"""

import logging
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from src.app.common.llm_factory import get_llm

logger = logging.getLogger(__name__)

CHAT_SYSTEM_PROMPT = """你是一个友好的聊天助手，名叫PlanHub助手。

你的职责：
1. 友好地回应用户的问候和闲聊
2. 介绍自己的能力（计划生成、知识查询、工具调用等）
3. 如果用户有具体需求，引导他们使用相应的功能
4. 回答用户的一般性问题（不需要特定工具或计划生成的问答）

请保持简洁、友好的语气，不要超过200字。
"""


async def chat_node(state) -> dict:
    """Chat节点：简单对话（支持 RAG fallback 和计划模式拒绝 fallback）"""
    try:
        # 检查是否是从 RAG fallback 过来的
        rag_fallback = state.get("rag_fallback_to_chat", False)
        
        # 检查是否有覆盖输入（如计划模式被拒后用原始问题回答）
        override_input = state.get("chat_override_input")
        actual_input = override_input if override_input else state.get("user_input", "")
        
        # 如果是 fallback，检查 fallback 原因
        fallback_reason = None
        if rag_fallback:
            execution_trace = state.get("execution_trace", [])
            for trace in reversed(execution_trace):
                if trace.get("node") == "rag":
                    fallback_reason = trace.get("reason", "知识库未找到相关内容")
                    break
        
        llm = get_llm()

        # 构建消息（根据是否 fallback 调整提示词）
        system_prompt = CHAT_SYSTEM_PROMPT
        if rag_fallback:
            system_prompt += "\n\n重要提示：用户之前尝试查询知识库，但知识库未找到相关内容。你现在需要直接回答用户的问题，并在回答开头简短说明'知识库未找到相关内容，以下是我的思考：'"
        elif override_input:
            system_prompt += "\n\n重要提示：用户之前拒绝了制定计划的提议，现在请直接回答用户的原始问题。开头可以简短说'好的'，然后直接给出答案。"

        # —— 组装发送给 LLM 的消息列表 ——
        # 结构：[SystemMessage(人设+长期记忆)] + [历史 HumanMessage/AIMessage 列表] + [当前 HumanMessage]
        # 短期记忆作为**独立消息列表**插入，保留角色边界，LLM 能清楚区分每轮对话的说话者。

        long_term = state.get("long_term_memory", [])

        # SystemMessage：只放人设 + 长期记忆（用户事实）
        if long_term:
            system_prompt += "\n\n【用户记忆】\n"
            for i, fact in enumerate(long_term, 1):
                system_prompt += f"{i}. {fact}\n"
            system_prompt += "\n请基于以上记忆信息回答用户问题，让对话更连贯自然。"

        messages: list[SystemMessage | HumanMessage | AIMessage] = [
            SystemMessage(content=system_prompt),
        ]

        # 短期记忆：按 LangChain 消息对象列表直接追加（保持角色分离）
        short_term = state.get("short_term_memory", [])
        if short_term:
            messages.extend(short_term)

        # 当前用户输入
        messages.append(HumanMessage(content=actual_input))

        # 调用LLM
        response = await llm.ainvoke(messages)
        result = response.content if hasattr(response, 'content') else str(response)

        # 如果是 RAG fallback，在回答前加上提示（如果 LLM 没有自动加上）
        if rag_fallback and "知识库未找到相关内容" not in result:
            result = f"知识库未找到相关内容，以下是我的思考：\n\n{result}"

        # 更新状态（透传 short_term_memory / long_term_memory，防止 LangGraph 后续节点覆盖为空）
        return {
            "intent": "chat",
            "agent_output": result,
            "rag_fallback_to_chat": False,
            "chat_override_input": None,
            "short_term_memory": state.get("short_term_memory", []),
            "long_term_memory": state.get("long_term_memory", []),
            "execution_trace": [
                {
                    "node": "chat",
                    "success": True,
                    "response_length": len(result),
                    "rag_fallback": rag_fallback,
                    "fallback_reason": fallback_reason,
                    "override_input": bool(override_input)
                }
            ]
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f"chat_node LLM调用异常: {error_msg}")
        
        # 如果用户有原始问题，返回错误信息而非通用问候语
        original_input = actual_input or state.get("user_input", "")
        if original_input:
            result = f"抱歉，我暂时无法回答您的问题（LLM调用异常: {error_msg}）"
        else:
            result = "你好！我是PlanHub助手，有什么可以帮你的吗？"
            
        return {
            "intent": "chat",
            "agent_output": result,
            "rag_fallback_to_chat": False,
            "chat_override_input": None,
            "error": error_msg,
            "execution_trace": [
                {
                    "node": "chat",
                    "error": error_msg,
                    "success": False,
                    "fallback": True
                }
            ]
        }
