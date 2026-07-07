"""
Plan Confirmation节点 - 询问用户是否创建计划到平台

流程：
1. 检查是否有生成的计划文本
2. 询问用户是否要创建到 PlanHub 平台
3. 用户回复"是" → 提取标题 → 创建到平台
4. 用户回复"否" → 直接返回文本计划
"""


async def plan_confirmation_node(state) -> dict:
    """Plan Confirmation节点：询问用户是否创建计划到平台"""

    # 记忆透传辅助
    short_term = state.get("short_term_memory", [])
    long_term = state.get("long_term_memory", [])
    def _wm(d: dict) -> dict:
        d.setdefault("short_term_memory", short_term)
        d.setdefault("long_term_memory", long_term)
        return d

    print(f"[DEBUG] plan_confirmation: entering node")
    
    # 获取缓存的计划文本
    plan_text = state.get("plan_text_cache", "")
    waiting_for_confirmation = state.get("waiting_for_plan_confirmation", False)
    user_input_raw = state.get("user_input", "")
    user_input = user_input_raw.lower()
    
    print(f"[DEBUG] plan_confirmation: plan_text length={len(plan_text)}, waiting_for_confirmation={waiting_for_confirmation}, user_input={user_input}")
    
    # 如果已经询问过，处理用户回复
    if waiting_for_confirmation:
        # 只有点击超链接发送的 __CLICK_CONFIRM__ 才算确认
        if user_input_raw.strip() == "__CLICK_CONFIRM__":
            print(f"[DEBUG] plan_confirmation: user confirmed, plan_text length={len(plan_text)}")
            return _wm({
                "user_confirmed_create": True,
                "plan_text_cache": plan_text,
                "plan_type": state.get("plan_type"),
                "plan_info": state.get("plan_info", {}),
                "execution_trace": [
                    {
                        "node": "plan_confirmation",
                        "user_response": "confirmed",
                        "source": "frontend_link",
                        "success": True
                    }
                ]
            })

        # 点击超链接发送的 __CLICK_NO__ 表示跳过，直接返回计划文本
        if user_input_raw.strip() == "__CLICK_NO__":
            print(f"[DEBUG] plan_confirmation: user skipped")
            return _wm({
                "final_response": plan_text,
                "agent_output": plan_text,
                "waiting_for_plan_confirmation": False,
                "execution_trace": [
                    {
                        "node": "plan_confirmation",
                        "user_response": "skipped",
                        "source": "frontend_link",
                        "success": True
                    }
                ]
            })

        # 用户输入不是点击确认，按普通对话处理，继续等待确认
        else:
            return _wm({
                "intent": "chat",
                "chat_override_input": state.get("user_input", ""),
                "selected_agent": "chat",
                "waiting_for_plan_confirmation": True,
                "plan_text_cache": plan_text,
                "execution_trace": [
                    {
                        "node": "plan_confirmation",
                        "action": "chat_fallback",
                        "reason": "用户输入不是点击确认，转为普通对话"
                    }
                ]
            })

    # 首次询问（还没有问过用户）
    else:
        # 检查是否有有效的计划文本
        if not plan_text or len(plan_text) < 50:
            # 没有有效计划，直接返回
            return _wm({
                "final_response": plan_text or "计划生成失败，请重试。",
                "execution_trace": [
                    {
                        "node": "plan_confirmation",
                        "no_plan_text": True
                    }
                ]
            })

        # 构建确认询问
        # 展示计划摘要，太长时截断
        display_plan = plan_text[:1000] if len(plan_text) > 1000 else plan_text
        if len(plan_text) > 1000:
            display_plan += "\n\n...(计划过长已截断，完整计划将保存到平台)"
        confirmation_question = f"""
 计划已生成！

{display_plan}

---

是否要将此计划创建到 PlanHub 平台？

创建到平台后，您可以：
-  在平台上查看和管理计划
-  进行每日打卡
-  追踪进度

请点击「确认」来创建，或点击「否」跳过。
"""

        return _wm({
            "agent_output": confirmation_question,
            "waiting_for_plan_confirmation": True,
            "plan_text_cache": plan_text,
            "plan_type": state.get("plan_type"),
            "plan_info": state.get("plan_info", {}),
            "execution_trace": [
                {
                    "node": "plan_confirmation",
                    "action": "asked_user",
                    "plan_text_length": len(plan_text),
                    "success": True
                }
            ]
        })