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
    
    print(f"[DEBUG] plan_confirmation: entering node")
    
    # 获取缓存的计划文本
    plan_text = state.get("plan_text_cache", "")
    waiting_for_confirmation = state.get("waiting_for_plan_confirmation", False)
    user_input = state.get("user_input", "").lower()
    
    print(f"[DEBUG] plan_confirmation: plan_text length={len(plan_text)}, waiting_for_confirmation={waiting_for_confirmation}, user_input={user_input}")
    
    # 如果已经询问过，处理用户回复
    if waiting_for_confirmation:
        # 用户确认创建
        if user_input in ["是", "确认", "yes", "ok", "好", "创建", "要", "可以", "没问题"]:
            print(f"[DEBUG] plan_confirmation: user confirmed, plan_text length={len(plan_text)}")
            return {
                "user_confirmed_create": True,
                "plan_text_cache": plan_text,  # 保持缓存
                "plan_type": state.get("plan_type"),  # 保持计划类型
                "execution_trace": [
                    *state.get("execution_trace", []),
                    {
                        "node": "plan_confirmation",
                        "user_response": "confirmed",
                        "success": True
                    }
                ]
            }
        
        # 用户拒绝创建
        elif user_input in ["否", "no", "不", "跳过", "取消", "不要", "不用"]:
            return {
                "final_response": plan_text,
                "agent_output": plan_text,
                "execution_trace": [
                    *state.get("execution_trace", []),
                    {
                        "node": "plan_confirmation",
                        "user_response": "rejected",
                        "success": True
                    }
                ]
            }
        
        # 用户回复不明确，检查是否是新的意图（比如问其他问题）
        else:
            # 检查用户输入是否是新的意图（长度较长或包含问号）
            # 如果用户输入明显不是确认/拒绝，清除等待确认状态
            if len(user_input) > 10 or "?" in user_input or "？" in user_input or "谁" in user_input or "什么" in user_input or "怎么" in user_input:
                # 用户可能在问其他问题，取消等待确认状态
                return {
                    "final_response": f"好的，已取消计划创建。您可以在之后随时重新创建。\n\n请问有什么其他需要帮助的吗？",
                    "agent_output": f"好的，已取消计划创建。请问有什么其他需要帮助的吗？",
                    "waiting_for_plan_confirmation": False,  # 清除等待确认状态
                    "plan_text_cache": None,  # 清除缓存
                    "execution_trace": [
                        *state.get("execution_trace", []),
                        {
                            "node": "plan_confirmation",
                            "user_response": "cancelled",
                            "reason": "user_asked_other_question",
                            "success": True
                        }
                    ]
                }

            # 否则继续询问
            confirmation_question = f"""
我已经为您生成了计划，是否要将此计划创建到 PlanHub 平台？

创建到平台后，您可以：
- 📋 在平台上查看和管理计划
- ✅ 进行每日打卡
- 📊 追踪进度

请回复「是」或「确认」来创建，或回复「否」跳过。
"""
            return {
                "agent_output": confirmation_question,
                "waiting_for_plan_confirmation": True,
                "execution_trace": [
                    *state.get("execution_trace", []),
                    {
                        "node": "plan_confirmation",
                        "user_response": "unclear",
                        "re_asked": True
                    }
                ]
            }
    
    # 首次询问（还没有问过用户）
    else:
        # 检查是否有有效的计划文本
        if not plan_text or len(plan_text) < 50:
            # 没有有效计划，直接返回
            return {
                "final_response": plan_text or "计划生成失败，请重试。",
                "execution_trace": [
                    *state.get("execution_trace", []),
                    {
                        "node": "plan_confirmation",
                        "no_plan_text": True
                    }
                ]
            }
        
        # 构建确认询问
        # 显示计划摘要（前200字符）
        plan_preview = plan_text[:200] if len(plan_text) > 200 else plan_text
        
        confirmation_question = f"""
✅ 计划已生成！

{plan_preview}...

---

是否要将此计划创建到 PlanHub 平台？

创建到平台后，您可以：
- 📋 在平台上查看和管理计划
- ✅ 进行每日打卡
- 📊 追踪进度

请回复「是」或「确认」来创建，或回复「否」跳过。
"""
        
        return {
            "agent_output": confirmation_question,
            "waiting_for_plan_confirmation": True,  # 设置等待确认标志
            "plan_text_cache": plan_text,           # 保持缓存
            "execution_trace": [
                *state.get("execution_trace", []),
                {
                    "node": "plan_confirmation",
                    "action": "asked_user",
                    "plan_preview_length": len(plan_preview),
                    "success": True
                }
            ]
        }