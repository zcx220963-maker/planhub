"""
Plan Mode Confirmation节点 - 确认用户是否要开启计划模式

流程：
1. 识别到计划相关意图时，先询问用户确认
2. 用户回复"是"/"确认" → 开启计划流程（路由到 plan_generator）
3. 用户回复"否" → 继续聊天（路由到 chat）

关键：首次进入此节点时，直接询问确认，不检查用户输入
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
    
    print(f"[DEBUG] plan_mode_confirm: has_asked_before={has_asked_before}, user_input={user_input}")
    
    # 如果之前已经询问过，检查用户的回复
    if has_asked_before and user_input:
        confirm_keywords = ["是", "确认", "好的", "可以", "开启", "开始", "想", "要"]
        reject_keywords = ["否", "不", "算了", "取消", "不用", "结束", "不要"]
        
        is_confirm = any(keyword in user_input for keyword in confirm_keywords)
        is_reject = any(keyword in user_input for keyword in reject_keywords)
        
        print(f"[DEBUG] plan_mode_confirm: is_confirm={is_confirm}, is_reject={is_reject}")
        
        if is_confirm:
            return {
                "final_response": f"好的，开始为您制定{plan_type_name}！",
                "agent_output": f"好的，开始为您制定{plan_type_name}！",
                "selected_agent": "plan_generator",
                "plan_type": intent,
                "waiting_for_plan_mode_confirm": False,
                "execution_trace": [
                    *state.get("execution_trace", []),
                    {
                        "node": "plan_mode_confirm",
                        "action": "confirmed",
                        "plan_type": intent,
                        "plan_type_name": plan_type_name
                    }
                ]
            }
        elif is_reject:
            return {
                "final_response": "好的，那我们继续聊天吧！请问有什么可以帮您的？",
                "agent_output": "好的，那我们继续聊天吧！请问有什么可以帮您的？",
                "selected_agent": "chat",
                "waiting_for_plan_mode_confirm": False,
                "execution_trace": [
                    *state.get("execution_trace", []),
                    {
                        "node": "plan_mode_confirm",
                        "action": "rejected",
                        "plan_type": intent,
                        "plan_type_name": plan_type_name
                    }
                ]
            }
        else:
            # 回复不明确，重新询问
            return {
                "agent_output": f"好的，请问您想制定{plan_type_name}吗？请回复「是」开始制定，或回复「否」继续聊天。",
                "waiting_for_plan_mode_confirm": True,
                "execution_trace": [
                    *state.get("execution_trace", []),
                    {
                        "node": "plan_mode_confirm",
                        "action": "re_ask",
                        "plan_type": intent
                    }
                ]
            }
    
    # 首次进入此节点，直接询问确认（不检查用户输入）
    return {
        "agent_output": f"好的，请问您想制定{plan_type_name}吗？请回复「是」开始制定，或回复「否」继续聊天。",
        "waiting_for_plan_mode_confirm": True,
        "execution_trace": [
            *state.get("execution_trace", []),
            {
                "node": "plan_mode_confirm",
                "action": "ask",
                "plan_type": intent,
                "plan_type_name": plan_type_name
            }
        ]
    }