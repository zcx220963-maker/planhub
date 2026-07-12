"""
Plan Generator节点 - 计划信息收集器
完全依靠LLM + 对话历史，不做任何硬编码提取
"""

import re
from prompts.plan_generator import PLAN_GENERATOR_SYSTEM_PROMPT
from ..stream_writer import emit_token, is_streaming

MAX_COLLECT_ROUNDS = 10

CONFIRM_TRIGGERS = {"确认", "确定", "可以", "好的", "好", "ok", "嗯", "没问题", "是", "对", "没错", "行", "要", "开始", "__CLICK_CONFIRM__"}


def _is_confirm(user_input: str) -> bool:
    """判断用户是否确认（仅按钮点击触发，用户输入文字不触发）"""
    text = user_input.strip().lower()
    return text == "__click_confirm__"


def _build_plan_summary(plan_history: list, last_response: str = "") -> str:
    """提取用户确认时的需求摘要给plan_builder
    优先解析XML标签，fallback到前缀匹配，再fallback到拼接用户消息"""
    if last_response and len(last_response) > 10:
        match = re.search(r'<summary>(.*?)</summary>', last_response, re.DOTALL)
        if match:
            return match.group(1).strip()[:500]

        for prefix in ["好的，目前了解到：", "好的，目前了解到", "目前了解到：", "已收集的信息："]:
            if prefix in last_response:
                idx = last_response.index(prefix) + len(prefix)
                summary = last_response[idx:]
                for sep in ["请问", "还需要了解", "还有什么"]:
                    s_idx = summary.find(sep)
                    if s_idx > 0:
                        summary = summary[:s_idx]
                summary = summary.strip().rstrip("，。")
                if summary:
                    return summary[:500]
        return last_response[:500]
    parts = []
    for msg in plan_history:
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if content and len(content) > 2:
                parts.append(content)
    return "；".join(parts[-5:])[:500]


async def plan_generator_node(state) -> dict:
    """Plan Generator节点：LLM对话收集信息，用户说确认后路由到plan_builder，支持逐 token 流式"""
    try:
        from app.common.llm_factory import get_llm
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

        user_input = state.get("user_input", "")
        plan_text_cache = state.get("plan_text_cache", "")

        plan_history = state.get("plan_conversation_history", [])

        is_first_entry = len(plan_history) == 0
        assistant_rounds = len([m for m in plan_history if m.get("role") == "assistant"])
        print(f"[DEBUG] plan_generator: is_first_entry={is_first_entry}, history_len={len(plan_history)}, assistant_rounds={assistant_rounds}")

        last_ai_response = ""
        for msg in reversed(plan_history):
            if msg.get("role") == "assistant":
                last_ai_response = msg.get("content", "")
                break

        # ===== 判断是否确认：精确匹配白名单 =====
        if not is_first_entry and _is_confirm(user_input):
            print(f"[DEBUG] plan_generator: 用户说了确认，路由到plan_builder")
            plan_summary = _build_plan_summary(plan_history, last_ai_response)
            print(f"[DEBUG] plan_generator: 需求摘要={plan_summary[:200]}")

            return {
                "agent_output": "好的，正在为你生成计划，请稍候...",
                "plan_text_cache": "",
                "plan_type": "custom",
                "plan_info": {},
                "plan_summary": plan_summary,
                "plan_conversation_history": [],
                "needs_plan_building": True,
                "waiting_for_plan_confirmation": False,
                "execution_trace": [
                    {
                        "node": "plan_generator",
                        "plan_type": "custom",
                        "needs_plan_building": True,
                        "plan_summary": plan_summary,
                        "progress": "complete",
                        "success": True
                    }
                ]
            }

        # ===== 最大轮次兜底 =====
        if not is_first_entry and assistant_rounds >= MAX_COLLECT_ROUNDS:
            print(f"[DEBUG] plan_generator: 达到最大收集轮次{MAX_COLLECT_ROUNDS}，强制进入plan_builder")
            plan_summary = _build_plan_summary(plan_history, last_ai_response)
            return {
                "agent_output": f"好的，根据目前已收集的信息为你生成计划。如有遗漏可以补充。",
                "plan_text_cache": "",
                "plan_type": "custom",
                "plan_info": {},
                "plan_summary": plan_summary,
                "plan_conversation_history": [],
                "needs_plan_building": True,
                "waiting_for_plan_confirmation": False,
                "execution_trace": [
                    {
                        "node": "plan_generator",
                        "plan_type": "custom",
                        "needs_plan_building": True,
                        "plan_summary": plan_summary,
                        "progress": "complete",
                        "success": True,
                        "reason": "max_rounds_reached"
                    }
                ]
            }

        # ===== LLM对话收集信息 =====
        messages = [SystemMessage(content=PLAN_GENERATOR_SYSTEM_PROMPT)]

        for msg in plan_history:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))

        if is_first_entry:
            messages.append(HumanMessage(content=(
                f"这是第一轮对话，用户刚确认要制定计划。\n"
                f"用户原始需求：{state.get('original_user_input', '')}\n"
                f"用户确认：{user_input}\n\n"
                f"请直接问第一个问题，不要输出<summary>标签（因为还没有任何信息可总结）。"
            )))
        else:
            messages.append(HumanMessage(content=(
                f"{user_input}\n\n"
                f"请先回顾上面的对话历史，在<summary>中用你自己的话写一段真实总结，"
                f"不要写'目前了解到的信息总结'这个占位文本。"
            )))

        llm = get_llm(temperature=0.7)

        # 流式调用LLM，逐 token 推送
        raw_chunks = []
        streaming = is_streaming()
        if streaming:
            async for chunk in llm.astream(messages):
                content = chunk.content if hasattr(chunk, 'content') else str(chunk)
                if content:
                    raw_chunks.append(content)
                    emit_token(content)
            llm_raw_response = "".join(raw_chunks).strip()
        else:
            result = await llm.ainvoke(messages)
            llm_raw_response = result.content if hasattr(result, 'content') else str(result)
            llm_raw_response = llm_raw_response.strip()

        print(f"[DEBUG] plan_generator: raw_response = {llm_raw_response[:200]}")

        # 清洗XML标签，只保留用户可读内容
        def _clean_llm_response(text: str, is_first: bool) -> str:
            q_match = re.search(r'<question>(.*?)</question>', text, re.DOTALL)
            s_match = re.search(r'<summary>(.*?)</summary>', text, re.DOTALL)
            parts = []
            if s_match and not is_first:
                summary = s_match.group(1).strip()
                if summary and summary not in {"暂无", "无", "目前没有", "待收集", "目前了解到的信息总结"}:
                    parts.append(summary)
            if q_match:
                parts.append(q_match.group(1).strip())
            return "\n\n".join(parts) if parts else text

        clean_response = _clean_llm_response(llm_raw_response, is_first_entry)

        def _remove_guide_sentences(text: str) -> str:
            import re
            patterns = [
                r"[，,]?\s*要是你现在还没想好[^。！？.!?]*?生成计划看看[~～]?",
                r"[，,]?\s*要是你现在还没想好[^。！？.!?]*?生成个基础计划[~～]?",
                r"[，,]?\s*如果不想回答[^。！？.!?]*?点击[^。！？.!?]*?确认[^。！？.!?]*?生成计划[~～]?",
                r"[，,]?\s*如果不想回答[^。！？.!?]*?点击[^。！？.!?]*?确认[^。！？.!?]*?[。！？.!?]?",
                r"[，,]?\s*没有要补充[^。！？.!?]*?点击[^。！？.!?]*?确认[^。！？.!?]*?[。！？.!?]?",
                r"[，,]?\s*没有需要补充[^。！？.!?]*?点击[^。！？.!?]*?确认[^。！？.!?]*?[。！？.!?]?",
                r"[，,]?\s*没啥要补充[^。！？.!?]*?点击[^。！？.!?]*?确认[^。！？.!?]*?[。！？.!?]?",
                r"[，,]?\s*也可以直接点击「确认」[^。！？.!?]*?[。！？.!?]?",
                r"[，,]?\s*也可以直接点击确认[^。！？.!?]*?[。！？.!?]?",
                r"[，,]?\s*帮你生成个基础计划看看[~～]?",
                r"[，,]?\s*我先帮你生成[^。！？.!?]*?[。！？.!?]?",
                r"[，,]?\s*我将为您生成计划[^。！？.!?]*?[。！？.!?]?",
                r"[，,]?\s*我将为你生成计划[^。！？.!?]*?[。！？.!?]?",
                r"[，,]?\s*请说确认[。！？.!?]?",
                r"[，,]?\s*说确认[。！？.!?]?",
                r"[，,]?\s*没有的话请说确认[。！？.!?]?",
                r"[，,]?\s*点击下方确认[^。！？.!?]*?[。！？.!?]?",
                r"[，,]?\s*下方确认[。！？.!?]?",
                r"[，,]?\s*点击确认按钮[^。！？.!?]*?[。！？.!?]?",
                r"[，,]?\s*随时可以点击「确认」[^。！？.!?]*?[。！？.!?]?",
                r"[，,]?\s*随时可以点击确认[^。！？.!?]*?[。！？.!?]?",
            ]
            result = text
            for pattern in patterns:
                result = re.sub(pattern, "", result)
            # 兜底：修复 LLM 生成的"如果…就够了让个…看看"类缺主语句
            result = re.sub(
                r"(如果[^。，,]{1,30}就够了)\s*让([^。！？.!?~～]{1,20}看看)[~～]?",
                r"\1，我帮你生成\2。",
                result
            )
            result = re.sub(r"[，,]\s*([。！？.!?])", r"\1", result)
            result = re.sub(r"\n{3,}", "\n\n", result)
            return result.strip()

        clean_response = _remove_guide_sentences(clean_response)
        display_response = clean_response

        # 更新对话历史（使用纯净的LLM输出，不含引导语）
        new_history = list(plan_history)
        new_history.append({"role": "user", "content": user_input})
        new_history.append({"role": "assistant", "content": llm_raw_response})

        return {
            "agent_output": display_response,
            "plan_text_cache": plan_text_cache,
            "plan_type": "custom",
            "plan_info": {},
            "plan_conversation_history": new_history,
            "waiting_for_plan_confirmation": False,
            "execution_trace": [
                {
                    "node": "plan_generator",
                    "plan_type": "custom",
                    "current_status": "collecting",
                    "collecting_info": True,
                    "is_first_entry": is_first_entry,
                    "progress": "ongoing",
                    "success": True
                }
            ]
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "agent_output": f"抱歉，计划生成失败：{str(e)}",
            "error": str(e),
            "execution_trace": [
                {
                    "node": "plan_generator",
                    "error": str(e),
                    "success": False
                }
            ]
        }
