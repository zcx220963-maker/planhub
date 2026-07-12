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
    
    CONFIRM_KEYWORDS = ["是", "确认", "yes", "ok", "好", "创建", "要", "可以", "没问题", "对", "没错", "行", "开始"]
    REJECT_KEYWORDS = ["否", "no", "不", "跳过", "取消", "不要", "不用", "算了", "结束"]

    def _clean_plan_text(text: str) -> str:
        import re
        text = re.sub(r'^.*?计划已[生成修改]！\s*\n', '', text, flags=re.DOTALL)
        text = re.sub(r'\n\n__DATA_SOURCES__[\s\S]*?__END_DATA_SOURCES__', '', text)
        text = re.sub(r'\n\s*---\s*\n\s*是否要将此计划创建到 PlanHub 平台[\s\S]*$', '', text)
        text = re.sub(r'\n\s*---\s*\n\s*是否要将此计划创建到 planhub 平台[\s\S]*$', '', text)
        return text.strip()

    # 如果已经询问过，处理用户回复
    if waiting_for_confirmation:
        # 用户修改计划
        if user_input.startswith("__modify_plan__:"):
            modified_plan_raw = user_input[len("__modify_plan__:"):]
            modified_plan = _clean_plan_text(modified_plan_raw)
            print(f"[DEBUG] plan_confirmation: user modified plan, raw length={len(modified_plan_raw)}, clean length={len(modified_plan)}")
            display_plan = modified_plan
            confirmation_question = f" 计划已修改！\n\n{display_plan}\n\n---\n\n是否要将此计划创建到 PlanHub 平台？\n\n创建到平台后，您可以：\n-  在平台上查看和管理计划\n-  进行每日打卡\n-  追踪进度\n\n请点击下方按钮选择。"
            return {
                "agent_output": confirmation_question,
                "waiting_for_plan_confirmation": True,
                "plan_text_cache": modified_plan,
                "plan_type": state.get("plan_type"),
                "plan_info": state.get("plan_info", {}),
                "execution_trace": [
                    {
                        "node": "plan_confirmation",
                        "action": "plan_modified",
                        "plan_text_length": len(modified_plan),
                        "waiting_for_confirmation": True,
                        "success": True
                    }
                ]
            }

        # 用户确认创建（仅按钮点击）
        if user_input.strip() == "__click_confirm__":
            print(f"[DEBUG] plan_confirmation: user confirmed, plan_text length={len(plan_text)}")
            return {
                "user_confirmed_create": True,
                "plan_text_cache": plan_text,
                "plan_type": state.get("plan_type"),
                "plan_info": state.get("plan_info", {}),
                "execution_trace": [
                    {
                        "node": "plan_confirmation",
                        "user_response": "confirmed",
                        "success": True
                    }
                ]
            }
        
        # 用户拒绝创建（仅按钮点击）
        elif user_input.strip() == "__click_reject__":
            return {
                "final_response": "已取消计划创建，您可以重新发起新的计划需求。",
                "agent_output": "已取消计划创建，您可以重新发起新的计划需求。",
                "plan_text_cache": None,
                "waiting_for_plan_confirmation": False,
                "plan_generated": False,
                "execution_trace": [
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
-  在平台上查看和管理计划
-  进行每日打卡
-  追踪进度

请点击下方按钮选择。
"""
            return {
                "agent_output": confirmation_question,
                "waiting_for_plan_confirmation": True,
                "execution_trace": [
                    {
                        "node": "plan_confirmation",
                        "user_response": "unclear",
                        "re_asked": True,
                        "waiting_for_confirmation": True
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
                    {
                        "node": "plan_confirmation",
                        "no_plan_text": True
                    }
                ]
            }
        
        # 构建确认询问（完整展示计划 + 数据来源）
        display_plan = plan_text

        # 附加工具调用和文档检索信息（供前端展示，不保存到平台）
        tool_data_parts = state.get("tool_data_parts", [])
        doc_data_parts = state.get("doc_data_parts", [])
        tool_success_count = state.get("tool_success_count", 0)
        tool_total_count = state.get("tool_total_count", 0)
        tool_fail_log = state.get("tool_fail_log", [])

        data_source_section = ""
        if tool_data_parts or doc_data_parts:
            data_source_section = "\n\n__DATA_SOURCES__\n"
            if tool_data_parts:
                data_source_section += f"__TOOL_DATA__\n"
                for part in tool_data_parts:
                    data_source_section += part + "\n"
            if tool_fail_log:
                data_source_section += f"__TOOL_FAILS__\n"
                for fail in tool_fail_log:
                    data_source_section += f"{fail.get('tool', '')}: {fail.get('error', '')}\n"
            if doc_data_parts:
                data_source_section += f"__DOC_DATA__\n"
                for part in doc_data_parts:
                    data_source_section += part + "\n"
            data_source_section += "__END_DATA_SOURCES__"

        confirmation_question = f"""
 计划已生成！

{display_plan}
{data_source_section}

---

是否要将此计划创建到 PlanHub 平台？

创建到平台后，您可以：
-  在平台上查看和管理计划
-  进行每日打卡
-  追踪进度

请点击下方按钮选择。
"""
        
        return {
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
                    "waiting_for_confirmation": True,
                    "success": True
                }
            ]
        }