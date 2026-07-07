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
    
    # 记忆透传辅助
    short_term = state.get("short_term_memory", [])
    long_term = state.get("long_term_memory", [])
    def _wm(d: dict) -> dict:
        d.setdefault("short_term_memory", short_term)
        d.setdefault("long_term_memory", long_term)
        return d

    # 只有点击超链接发送的 __CLICK_CONFIRM__ 才算确认
    if user_input == "__CLICK_CONFIRM__":
        return _wm({
            "final_response": f"好的，开始为您制定{plan_type_name}！",
            "agent_output": f"好的，开始为您制定{plan_type_name}！",
            "selected_agent": "plan_collector",
            "plan_type": intent,
            "waiting_for_plan_mode_confirm": False,
            "execution_trace": [
                {
                    "node": "plan_mode_confirm",
                    "action": "confirmed",
                    "plan_type": intent,
                    "plan_type_name": plan_type_name,
                    "source": "frontend_link"
                }
            ]
        })

    # 如果之前已经询问过，检查用户是否点击了超链接确认
    if has_asked_before and user_input:
        # 只有 __CLICK_CONFIRM__ 才算确认，普通文字"确认"不算
        if user_input == "__CLICK_CONFIRM__":
            return _wm({
                "final_response": f"好的，开始为您制定{plan_type_name}！",
                "agent_output": f"好的，开始为您制定{plan_type_name}！",
                "selected_agent": "plan_collector",
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
            })
        else:
            # 用户说的是普通对话，不触发确认，把消息交给 chat 节点处理
            return _wm({
                "intent": "chat",
                "chat_override_input": user_input,
                "selected_agent": "chat",
                "waiting_for_plan_mode_confirm": True,
                "original_user_input": original_user_input,
                "execution_trace": [
                    {
                        "node": "plan_mode_confirm",
                        "action": "chat_fallback",
                        "plan_type": intent,
                        "reason": "用户输入不是点击确认，转为普通对话"
                    }
                ]
            })
    
    # 首次进入此节点，直接询问确认（不检查用户输入）
    return _wm({
        "agent_output": f"好的，请问您想制定{plan_type_name}吗？请点击「确认」开始制定。",
        "waiting_for_plan_mode_confirm": True,
        "original_user_input": original_user_input,  # 保存原始问题
        "execution_trace": [
            {
                "node": "plan_mode_confirm",
                "action": "ask",
                "plan_type": intent,
                "plan_type_name": plan_type_name
            }
        ]
    })