"""
Chat节点 - 简单对话Agent
处理闲聊和简单问答

核心改进：
1. 支持 RAG fallback：如果 rag_fallback_to_chat=True，先提示"知识库未命中，正在思考..."
2. 检查 execution_trace 了解 fallback 原因，在回答中给出更友好的提示
"""

import logging
from langchain_core.messages import SystemMessage, HumanMessage
from src.app.common.llm_factory import get_llm, extract_text
from prompts.assistant import CHAT_SYSTEM_PROMPT
from ..stream_writer import emit_token, emit_streaming_complete, flush_buffer, is_streaming

logger = logging.getLogger(__name__)


async def chat_node(state) -> dict:
    """Chat节点：简单对话，支持逐 token 流式输出"""
    try:
        rag_fallback = state.get("rag_fallback_to_chat", False)
        override_input = state.get("chat_override_input")
        actual_input = override_input if override_input else state.get("user_input", "")

        fallback_reason = None
        if rag_fallback:
            execution_trace = state.get("execution_trace", [])
            for trace in reversed(execution_trace):
                if trace.get("node") == "rag":
                    fallback_reason = trace.get("reason", "知识库未找到相关内容")
                    break

        llm = get_llm()

        system_prompt = CHAT_SYSTEM_PROMPT
        needs_clarification = state.get("needs_clarification", False)
        if rag_fallback:
            system_prompt += "\n\n重要提示：用户之前尝试查询知识库，但知识库未找到相关内容。你现在需要直接回答用户的问题，并在回答开头简短说明'知识库未找到相关内容，以下是我的思考：'"
        elif override_input:
            system_prompt += "\n\n重要提示：用户之前拒绝了制定计划的提议，现在请直接回答用户的原始问题。开头可以简短说'好的'，然后直接给出答案。"
        elif needs_clarification:
            system_prompt += "\n\n重要提示：用户的意图不太明确，你需要友好地询问用户具体想做什么（比如想制定什么计划、想查询什么知识、还是只是想聊聊），引导用户给出更清晰的需求。回答要简短自然，不要列一堆选项。"

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=actual_input)
        ]

        # 流式调用LLM，逐 token 推送
        chunks = []
        streaming = is_streaming()
        if streaming:
            async for chunk in llm.astream(messages):
                content = getattr(chunk, 'content', None)
                text = extract_text(content) if content is not None else ""
                if text:
                    chunks.append(text)
                    await emit_token(text)
            await flush_buffer()
            result = "".join(chunks)
            # LLM 流式生成结束，立即通知前端（不等待后续 post-processing）
            await emit_streaming_complete()
        else:
            response = await llm.ainvoke(messages)
            result = extract_text(getattr(response, 'content', None))

        # 如果是 RAG fallback，在回答前加上提示
        if rag_fallback and "知识库未找到相关内容" not in result:
            prefix = "知识库未找到相关内容，以下是我的思考：\n\n"
            if streaming:
                await emit_token(prefix)
            result = prefix + result

        return {
            "intent": "chat",
            "agent_output": result,
            "rag_fallback_to_chat": False,
            "chat_override_input": None,
            "needs_clarification": False,
            "execution_trace": [
                {
                    "node": "chat",
                    "success": True,
                    "response_length": len(result),
                    "rag_fallback": rag_fallback,
                    "fallback_reason": fallback_reason,
                    "override_input": bool(override_input),
                    "was_clarification": needs_clarification
                }
            ]
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f"chat_node LLM调用异常: {error_msg}")

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
