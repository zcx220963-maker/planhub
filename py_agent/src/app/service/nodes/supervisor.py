"""
Supervisor节点 - 意图分类和路由
使用结构化输出确保稳定性

关键改进：
- 如果当前正在进行计划生成（有 plan_text_cache 或 execution_trace 中有 plan_generator），
  则直接路由回 plan_generator，继续收集信息
"""

from langchain_core.messages import SystemMessage, HumanMessage
from src.app.common.llm_factory import get_llm
from prompts.supervisor import build_supervisor_prompt
from ..schemas import IntentResult


async def supervisor_node(state) -> dict:
    """Supervisor节点：所有意图由 LLM 判断，发标签路由。

    supervisor 不做任何硬编码路由——用户是否选中文档、选中的是什么文档，
    都通过提示词告诉 LLM，由 LLM 决定发什么标签。
    """

    execution_trace = state.get("execution_trace", [])
    print(f"[DEBUG] supervisor: execution_trace length = {len(execution_trace)}")

    # ===== 计划流程进行中 → 继续回到计划节点 =====
    # 如果用户已取消/拒绝计划创建，不再从旧 execution_trace 推断，直接走 LLM 分类
    if state.get("plan_flow_cancelled"):
        print(f"[DEBUG] supervisor: plan_flow_cancelled=True, 跳过旧 trace 推断，走 LLM 分类")
    else:
        # 以下整个计划流程推断都只在"未取消"时执行
        has_plan_mode_confirm = any(t.get("node") == "plan_mode_confirm" for t in execution_trace)
        has_plan_generator = any(t.get("node") == "plan_generator" for t in execution_trace)
        is_in_plan_generation = False
        plan_type = None

        if has_plan_generator:
            is_in_plan_generation = True

        from ..state import get_conversation_state, ConversationStateEnum
        session_id = state.get("session_id", "default")
        conv_state = get_conversation_state(session_id)

        if conv_state.state in [ConversationStateEnum.WAITING_PARAM, ConversationStateEnum.WAITING_SELECT]:
            # 独立模式下不应有待处理的 Java 后端任务，若出现则降级到 chat
            task = conv_state.current_task or "unknown"
            print(f"[WARN] supervisor: 遗留的 WAITING 状态（{task}），降级到 chat")
            from ..state import reset_conversation_state
            reset_conversation_state(session_id)
            # 继续走下面的 LLM 分类流程（不 return）

        # 优先检查是否正在等待计划模式确认
        if state.get("waiting_for_plan_mode_confirm"):
            plan_type = state.get("plan_type")
            print(f"[DEBUG] supervisor: waiting_for_plan_mode_confirm=True, routing to plan_mode_confirm")
            return {
                "intent": "plan_creation",
                "selected_agent": "plan_mode_confirm",
                "confidence": 1.0,
                "execution_trace": [
                    {
                        "node": "supervisor",
                        "intent": "plan_creation",
                        "selected_agent": "plan_mode_confirm",
                        "confidence": 1.0,
                        "reason": "等待用户确认开启计划模式",
                        "plan_type": plan_type
                    }
                ]
            }

        # 优先检查是否正在等待计划确认
        if state.get("waiting_for_plan_confirmation"):
            is_in_plan_generation = True
            plan_type = state.get("plan_type")
            print(f"[DEBUG] supervisor: waiting_for_plan_confirmation=True, routing to plan_confirmation")
            return {
                "intent": "plan_creation",
                "selected_agent": "plan_confirmation",
                "confidence": 1.0,
                "execution_trace": [
                    {
                        "node": "supervisor",
                        "intent": "plan_creation",
                        "selected_agent": "plan_confirmation",
                        "confidence": 1.0,
                        "reason": "等待用户确认创建计划",
                        "plan_type": plan_type
                    }
                ]
            }

        for trace in reversed(execution_trace):
            if trace.get("node") == "plan_generator":
                print(f"[DEBUG] supervisor: found plan_generator trace, plan_generated={trace.get('plan_generated')}, collecting_info={trace.get('collecting_info')}")

                # 检查 plan_text_cache 是否已清空（计划已创建完成）
                plan_text_cache = state.get("plan_text_cache")
                if trace.get("plan_generated") and not plan_text_cache:
                    print(f"[DEBUG] supervisor: plan_generated=True but plan_text_cache is empty, plan already created, skipping plan_confirmation")
                    # 计划已经创建完成，不需要再路由回 plan_confirmation，继续走正常路由流程
                    break

                # 如果计划已生成且 plan_text_cache 还在，路由到 plan_confirmation
                if trace.get("plan_generated"):
                    is_in_plan_generation = True
                    plan_type = trace.get("plan_type")
                    return {
                        "intent": "plan_creation",
                        "selected_agent": "plan_confirmation",
                        "confidence": 1.0,
                        "execution_trace": [
                            {
                                "node": "supervisor",
                                "intent": "plan_creation",
                                "selected_agent": "plan_confirmation",
                                "confidence": 1.0,
                                "reason": "计划已生成，等待确认",
                                "plan_type": plan_type
                            }
                        ]
                    }
                # 如果计划还在收集信息或需要澄清，继续路由到 plan_generator
                if trace.get("collecting_info") or trace.get("need_clarification"):
                    is_in_plan_generation = True
                    plan_type = trace.get("plan_type")
                    break

        # 如果正在计划生成过程中，直接路由回 plan_generator
        if is_in_plan_generation:
            print(f"[DEBUG] supervisor: routing back to plan_generator, plan_type={plan_type}")
            return {
                "intent": "plan_creation",
                "selected_agent": "plan_generator",
                "confidence": 1.0,
                "execution_trace": [
                    {
                        "node": "supervisor",
                        "intent": "plan_creation",
                        "selected_agent": "plan_generator",
                        "confidence": 1.0,
                        "reason": "继续计划生成流程",
                        "plan_type": plan_type
                    }
                ]
            }

    # ── 规则预检：明显是计划意图的输入直接路由，不依赖 LLM ──
    # 防止 LLM 指令遵循不稳定导致明显意图被误分类
    user_input_lower = state.get("user_input", "").lower()
    plan_keywords = [
        "制定计划", "制定.*计划", "做.*计划", "做.*规划", "规划.*行程",
        "旅行计划", "旅游计划", "学习计划", "减肥计划", "健身计划",
        "帮我安排", "帮我规划", "帮我制定",
        "我想去.*玩", "我想去.*旅游", "去.*旅游", "去.*旅行",
        "到.*旅游", "到.*旅行", "游.*攻略",
    ]
    import re
    for pattern in plan_keywords:
        if re.search(pattern, user_input_lower):
            print(f"[DEBUG] supervisor: 规则预检命中 plan_creation, pattern={pattern}")
            return {
                "intent": "plan_creation",
                "selected_agent": "plan_generator",
                "confidence": 0.95,
                "execution_trace": [
                    {
                        "node": "supervisor",
                        "intent": "plan_creation",
                        "selected_agent": "plan_generator",
                        "confidence": 0.95,
                        "reason": f"规则预检命中: {pattern}",
                        "user_input": state["user_input"][:100],
                    }
                ]
            }

    # ── 所有意图判断都交给 LLM ──
    try:
        llm = get_llm().with_structured_output(IntentResult)

        # 告诉 LLM 用户是否选中文档，让它一起判断
        has_docs = bool(state.get("selected_doc_ids"))
        system_prompt = build_supervisor_prompt(
            user_input=state["user_input"],
            has_selected_docs=has_docs,
        )

        messages = [
            SystemMessage(content=system_prompt),
        ]

        result: IntentResult = await llm.ainvoke(messages)
        print(f"[DEBUG] supervisor: has_docs={has_docs} | LLM result = {result.intent} (conf={result.confidence})")

        # plan_creation → 直接进入计划生成（不再需要用户点击确认）
        if result.intent == "plan_creation" and result.confidence >= 0.5:
            return {
                "intent": "plan_creation",
                "selected_agent": "plan_generator",
                "confidence": result.confidence,
                "execution_trace": [
                    {
                        "node": "supervisor",
                        "intent": "plan_creation",
                        "selected_agent": "plan_generator",
                        "confidence": result.confidence,
                        "user_input": state["user_input"][:100],
                    }
                ]
            }

        # doc_query → 用户选了文档，走 RAG 检索
        if result.intent == "doc_query":
            return {
                "intent": "doc_query",
                "selected_agent": "rag",
                "confidence": result.confidence,
                "execution_trace": [
                    {
                        "node": "supervisor",
                        "intent": "doc_query",
                        "selected_agent": "rag",
                        "confidence": result.confidence,
                        "user_input": state["user_input"][:100],
                        "reason": "LLM 判断用户想查询文档知识",
                    }
                ]
            }

        # clarify → 标记需要澄清，路由到 chat
        if result.intent == "clarify":
            return {
                "intent": "clarify",
                "selected_agent": "chat",
                "confidence": result.confidence,
                "needs_clarification": True,
                "execution_trace": [
                    {
                        "node": "supervisor",
                        "intent": "clarify",
                        "selected_agent": "chat",
                        "confidence": result.confidence,
                        "user_input": state["user_input"][:100],
                    }
                ]
            }

        # chat → 直接路由
        return {
            "intent": "chat",
            "selected_agent": "chat",
            "confidence": result.confidence,
            "execution_trace": [
                {
                    "node": "supervisor",
                    "intent": "chat",
                    "selected_agent": "chat",
                    "confidence": result.confidence,
                    "user_input": state["user_input"][:100],
                }
            ]
        }

    except Exception as e:
        return {
            "intent": "chat",
            "selected_agent": "chat",
            "confidence": 0.0,
            "error": f"意图分类失败: {str(e)}",
            "execution_trace": [
                {
                    "node": "supervisor",
                    "intent": "chat",
                    "confidence": 0.0,
                    "error": str(e),
                    "fallback": True,
                }
            ],
        }
