"""
Memory Save 节点 - 保存短期和长期记忆

核心设计：
- 每轮对话结束前调用（在输出最终响应之前）
- 短期记忆：追加到 Redis（7天过期，保留最近 20 条）
- 长期记忆：用 LLM 提取值得记住的事实，存入 Chroma 向量库
- 计划创建完成或被打断时，清空计划流程相关的短期状态
"""

from typing import Dict, Any, List


async def memory_save_node(state) -> dict:
    """
    记忆保存节点：保存短期记忆和长期记忆

    调用时机：
    - 每轮对话的最后（在输出最终响应之前）

    保存内容：
    - 短期记忆：本轮的 user_input 和 final_response/agent_output
    - 长期记忆：用 LLM 从对话中提取值得记住的事实
    """
    try:
        session_id = state.get("session_id", "")
        user_id = state.get("user_id") or "anonymous"
        user_input = state.get("user_input", "")
        agent_output = state.get("agent_output") or state.get("final_response") or ""
        plan_text_cache = state.get("plan_text_cache")
        user_confirmed_create = state.get("user_confirmed_create", False)

        print(f"[DEBUG] memory_save: 开始保存记忆, session_id={session_id[:8]}...")

        # 1. 保存短期记忆到 Redis（7 天过期）
        short_term_saved = False
        try:
            from src.app.orchestrator.memory_bridge import MemoryBridge
            bridge = MemoryBridge()

            chat_history = []
            if user_input:
                chat_history.append({"role": "user", "content": user_input})
            if agent_output:
                chat_history.append({"role": "assistant", "content": agent_output})

            if chat_history:
                await bridge.save_memory(
                    session_id=session_id,
                    user_id=user_id,
                    chat_history=chat_history
                )
                short_term_saved = True
                print(f"[DEBUG] memory_save: 短期记忆已保存 {len(chat_history)} 条")
        except Exception as e:
            print(f"[WARN] memory_save: 短期记忆保存失败: {e}")

        # 2. 提取并保存长期记忆到 Chroma
        long_term_saved = 0
        try:
            from src.app.services.long_term_memory_service import get_long_term_memory_service
            ltm_service = get_long_term_memory_service()

            if user_input and agent_output and user_id != "anonymous":
                memories = await ltm_service.extract_and_store(
                    user_id=user_id,
                    session_id=session_id,
                    user_input=user_input,
                    assistant_response=agent_output
                )
                long_term_saved = len(memories)
                if long_term_saved > 0:
                    print(f"[DEBUG] memory_save: 长期记忆已提取 {long_term_saved} 条")
        except Exception as e:
            print(f"[WARN] memory_save: 长期记忆保存失败: {e}")

        # 3. 如果计划创建完成，清空所有计划流程状态（下次全新开始）
        plan_cleared = False
        if user_confirmed_create and plan_text_cache:
            plan_cleared = True
            print(f"[DEBUG] memory_save: 计划已创建完成，清空所有计划流程状态")

        result = {
            "execution_trace": [
                {
                    "node": "memory_save",
                    "short_term_saved": short_term_saved,
                    "long_term_saved_count": long_term_saved,
                    "plan_cleared": plan_cleared,
                    "success": True
                }
            ]
        }

        # 计划创建完成时，清空所有计划相关状态，确保下一轮对话不受影响
        if plan_cleared:
            result.update({
                # 计划确认相关
                "waiting_for_plan_mode_confirm": False,
                "waiting_for_plan_confirmation": False,
                "user_confirmed_create": False,
                # 计划内容相关
                "plan_text_cache": None,
                "plan_title": None,
                "plan_type": None,
                "plan_info": None,
                "plan_summary": "",
                "plan_generated": False,
                "needs_plan_building": False,
                # 计划对话历史
                "plan_conversation_history": [],
                # 工具执行相关
                "ranked_tools": [],
                "parameter_extraction_status": "",
                "tool_call_results": [],
                "tool_data_parts": [],
                "tool_success_count": 0,
                "tool_total_count": 0,
                "tool_fail_log": [],
                # 文档检索相关
                "doc_data_parts": [],
                "doc_retrieval_status": "",
                # 前端展示
                "plan_metadata": None,
                # 协调相关
                "original_user_input": None,
                "chat_override_input": None,
                "selected_agent": None,
                "intent": None,
                "agent_input": None,
                # assistant 操作类型
                "action_type": None,
                "action_params": {},
            })

        return result

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[ERROR] memory_save: {e}")
        return {
            "execution_trace": [
                {
                    "node": "memory_save",
                    "error": str(e),
                    "success": False
                }
            ]
        }
