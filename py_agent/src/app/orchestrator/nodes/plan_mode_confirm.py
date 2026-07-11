"""
Plan Mode Confirmation节点 - 确认用户是否要开启计划模式

流程：
1. 识别到计划相关意图时，先询问用户确认
2. 用户回复"是"/"确认" → 开启计划流程（路由到 plan_generator）
3. 用户回复"否" → 用原始问题路由到 chat，直接回答用户的问题

关键：
- 首次进入此节点时，保存原始问题到 original_user_input
- 用户拒绝后，把 original_user_input 放回 user_input，路由到 chat 回答
"""

PLAN_TYPE_MAP = {
    "learning": "学习计划",
    "health": "健康计划",
    "travel": "旅行计划",
    "work": "工作计划",
    "finance": "财务计划",
    "plan_creation": "计划"
}


async def plan_mode_confirm_node(state) -> dict:
    """确认用户是否要开启计划模式"""
    user_input = state.get("user_input", "").strip()
    intent = state.get("intent", "learning")
    
    plan_type_name = PLAN_TYPE_MAP.get(intent, "计划")
    
    # 检查是否是首次进入此节点（通过检查 execution_trace）
    execution_trace = state.get("execution_trace", [])
    has_asked_before = any(
        trace.get("node") == "plan_mode_confirm" and trace.get("action") in ["ask", "re_ask"]
        for trace in execution_trace
    )
    
    # 获取原始用户问题（触发计划确认的那条消息）
    original_user_input = state.get("original_user_input", "")
    if not original_user_input and not has_asked_before:
        # 首次进入，保存原始问题
        original_user_input = user_input
    
    print(f"[DEBUG] plan_mode_confirm: has_asked_before={has_asked_before}, user_input={user_input}")
    print(f"[DEBUG] plan_mode_confirm: original_user_input={original_user_input}")
    
    # 如果之前已经询问过，检查用户的回复
    if has_asked_before and user_input:
        is_confirm = user_input.strip().lower() == "__click_confirm__"
        is_reject = user_input.strip().lower() == "__click_reject__"
        
        print(f"[DEBUG] plan_mode_confirm: is_confirm={is_confirm}, is_reject={is_reject}")
        
        if is_confirm:
            return {
                "final_response": f"好的，开始为您制定{plan_type_name}！",
                "agent_output": f"好的，开始为您制定{plan_type_name}！",
                "selected_agent": "plan_generator",
                "plan_type": intent,
                "waiting_for_plan_mode_confirm": False,
                "execution_trace": [
                    {
                        "node": "plan_mode_confirm",
                        "action": "confirmed",
                        "plan_type": intent,
                        "plan_type_name": plan_type_name
                    }
                ]
            }
        elif is_reject:
            # 用户拒绝，把原始问题保存到 chat_input，路由到 chat 直接回答
            # 注意：不修改 user_input，保持对话历史一致性
            print(f"[DEBUG] plan_mode_confirm: User rejected, routing to chat with original question")
            return {
                "intent": "chat",  # 更新意图为 chat
                "chat_override_input": original_user_input,  # chat 节点用这个来回答
                "selected_agent": "chat",
                "waiting_for_plan_mode_confirm": False,
                "original_user_input": "",  # 清空
                "execution_trace": [
                    {
                        "node": "plan_mode_confirm",
                        "action": "rejected",
                        "plan_type": intent,
                        "plan_type_name": plan_type_name,
                        "original_question": original_user_input,
                        "reason": "用户拒绝计划模式，用原始问题路由到 chat"
                    }
                ]
            }
        else:
            # 回复不明确，重新询问
            return {
                "agent_output": f"好的，请问您想制定{plan_type_name}吗？请点击下方按钮选择。",
                "waiting_for_plan_mode_confirm": True,
                "original_user_input": original_user_input,
                "execution_trace": [
                    {
                        "node": "plan_mode_confirm",
                        "action": "re_ask",
                        "plan_type": intent
                    }
                ]
            }

    return {
        "agent_output": f"好的，请问您想制定{plan_type_name}吗？请点击下方按钮选择。",
        "waiting_for_plan_mode_confirm": True,
        "original_user_input": original_user_input,
        "execution_trace": [
            {
                "node": "plan_mode_confirm",
                "action": "ask",
                "plan_type": intent,
                "plan_type_name": plan_type_name
            }
        ]
    }