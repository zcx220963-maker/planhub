"""
Plan Generator节点 - 计划生成Agent
与 chat.py 的 /chat/plan 接口行为一致

流程：
1. 检测计划类型，显示欢迎信息 + 一次性所有必填问题
2. 用户回答后，提取信息并更新 collector
3. 如果信息收集完整，进入计划生成
4. 如果信息不完整，返回下一个问题
"""

import asyncio


async def plan_generator_node(state) -> dict:
    """Plan Generator节点：处理计划生成请求"""
    try:
        # 检查能力开关
        capabilities = state.get("capabilities", {})
        if isinstance(capabilities, dict):
            enable_plan_mode = capabilities.get("enable_plan_mode", True)
        else:
            enable_plan_mode = getattr(capabilities, "enable_plan_mode", True)

        if not enable_plan_mode:
            return {
                "agent_output": "抱歉，计划模式已被关闭。如需启用，请在能力开关中打开「📋 计划模式」。",
                "execution_trace": [
                    *state.get("execution_trace", []),
                    {
                        "node": "plan_generator",
                        "blocked": True,
                        "reason": "计划模式已关闭"
                    }
                ]
            }

        # 延迟导入，避免循环依赖
        from src.app.skills.plan_generator import (
            PlanInfoCollectorManager, 
            PlanInfoCollector, 
            detect_plan_type,
            extract_info_from_input,
            get_suggestions_for_plan
        )
        from src.app.dao.redis_dao import redis_client

        # 复用现有的PlanInfoCollector
        manager = PlanInfoCollectorManager(redis_client=redis_client)
        session_id = state.get("session_id", "default")
        user_input = state.get("user_input", "")

        # 获取现有的Collector或创建新的
        collector = manager.get_collector(session_id)
        print(f"[DEBUG] plan_generator: collector found = {collector is not None}, user_input = {user_input}")
        
        # 检测用户输入是否是首次触发（包含"制定xx计划"）
        is_first_trigger = False
        if collector is None:
            is_first_trigger = True
            print(f"[DEBUG] plan_generator: is_first_trigger = True (collector is None)")
        else:
            # 如果用户输入是新的计划类型触发词（且与当前 collector 类型不同），删除旧的 collector
            plan_type_check = detect_plan_type(user_input)
            print(f"[DEBUG] plan_generator: plan_type_check = {plan_type_check}, collector.plan_type = {collector.plan_type if collector else None}")
            if plan_type_check and plan_type_check != "unknown" and not plan_type_check.startswith("__AMBIGUOUS__"):
                # 只有当计划类型发生变化时才重建 collector
                if collector.plan_type != plan_type_check:
                    manager.delete_collector(session_id)
                    collector = None
                    is_first_trigger = True
                    print(f"[DEBUG] plan_generator: is_first_trigger = True (plan type changed: {collector.plan_type if collector else None} -> {plan_type_check})")
                else:
                    print(f"[DEBUG] plan_generator: plan_type unchanged ({plan_type_check}), keeping existing collector")
        
        if collector is None:
            # 新的计划请求 - 检测计划类型
            plan_type = detect_plan_type(user_input)
            print(f"[DEBUG] plan_generator: detected plan_type = {plan_type}")
            
            # 检查是否是模糊匹配（多意图冲突）
            if plan_type and plan_type.startswith("__AMBIGUOUS__"):
                return {
                    "agent_output": "您好！我可以帮您制定学习、健康、旅行、工作或财务计划。请问您想制定哪种类型的计划？",
                    "waiting_for_plan_confirmation": False,
                    "execution_trace": [
                        *state.get("execution_trace", []),
                        {
                            "node": "plan_generator",
                            "plan_type": None,
                            "need_clarification": True
                        }
                    ]
                }
            
            # 检查是否是 unknown（无法识别）
            if plan_type is None or plan_type == "unknown":
                return {
                    "agent_output": "好的，我们现在提供五种计划类型：\n\n1. 📚 学习计划 - 制定学习目标、课程安排\n2. 💪 健康计划 - 健身、饮食、作息安排\n3. ✈️ 旅行计划 - 行程规划、攻略推荐\n4. 💼 工作计划 - 项目任务、目标分解\n5. 💰 财务计划 - 理财储蓄、投资规划\n\n请问您想制定哪种类型的计划？请回复序号或名称，例如：'1' 或 '学习计划'。",
                    "waiting_for_plan_confirmation": False,
                    "execution_trace": [
                        *state.get("execution_trace", []),
                        {
                            "node": "plan_generator",
                            "plan_type": None,
                            "need_clarification": True
                        }
                    ]
                }
            
            # 创建新的收集器
            collector = PlanInfoCollector(plan_type)
            print(f"[DEBUG] plan_generator: Created new collector for plan_type: {plan_type}, required_fields: {collector.required_fields}")
            
            # 立即保存收集器到 Redis
            manager.save_collector(session_id, collector)
            
            # 一次性生成所有必填字段的问题
            all_questions = collector.get_all_questions_once()
            print(f"[DEBUG] plan_generator: all_questions = {all_questions}")
            
            # 获取建议信息
            suggestions = get_suggestions_for_plan(plan_type)
            print(f"[DEBUG] plan_generator: suggestions = {suggestions}")
            
            # 类型名称映射（中文）
            type_name_map = {
                "learning": "学习",
                "health": "健康",
                "travel": "旅行",
                "work": "工作",
                "finance": "财务",
            }
            plan_type_cn = type_name_map.get(plan_type, plan_type)
            
            # 构建回复：显示必填字段 + 委婉询问是否需要额外信息
            response = f"好的，{plan_type_cn}计划！\n\n"
            response += f"请告诉我以下必填信息（可以一次性回答）：\n\n{all_questions}\n\n"
            
            if suggestions:
                response += f"💡 {suggestions}\n"
            
            print(f"[DEBUG] plan_generator: final response = {response[:200]}")
            
            return {
                "agent_output": response,
                "plan_type": plan_type,
                "waiting_for_plan_confirmation": False,
                "execution_trace": [
                    *state.get("execution_trace", []),
                    {
                        "node": "plan_generator",
                        "plan_type": plan_type,
                        "progress": f"0/{len(collector.required_fields)}",
                        "collecting_info": True,
                        "first_time": True
                    }
                ]
            }
        
        # 继续收集信息
        print(f"[DEBUG] plan_generator: continuing collection, collector.plan_type={collector.plan_type}, current_field_index={collector.current_field_index}, required_fields={collector.required_fields}")
        
        # 1. 提取信息
        extracted = extract_info_from_input(user_input, collector.plan_type)
        print(f"[DEBUG] plan_generator: extract_info_from_input result = {extracted}")
        
        if extracted:
            for field, value in extracted.items():
                if field in collector.collected_info:
                    collector.collected_info[field] = value
                elif field in collector.required_fields:
                    collector.collected_info[field] = value
            print(f"[DEBUG] plan_generator: Extracted info: {extracted}, collected_info: {collector.collected_info}")
            
            # 更新 current_field_index（用于 is_complete 判断）
            collector.current_field_index = len([k for k in collector.required_fields if k in collector.collected_info])
            print(f"[DEBUG] plan_generator: updated current_field_index = {collector.current_field_index}")
            
            # 保存更新后的 collector 到 Redis
            manager.save_collector(session_id, collector)
        
        # 2. 检查是否完成
        print(f"[DEBUG] plan_generator: collector.is_complete() = {collector.is_complete()}, collected_info={collector.collected_info}")
        
        if collector.is_complete():
            # 生成计划
            from src.app.skills.plan_generator import generate_plan, _get_default_apis, call_apis_for_plan
            apis = _get_default_apis(collector.plan_type)
            api_results = call_apis_for_plan(collector.plan_type, collector.collected_info, apis)
            plan_text = generate_plan(
                collector.plan_type,
                collector.collected_info,
                api_results,
                collector.rag_context,
                collector.context_summary
            )
            
            # 清除收集器
            manager.delete_collector(session_id)
            
            return {
                "agent_output": plan_text,
                "plan_text_cache": plan_text,
                "plan_type": collector.plan_type,
                "waiting_for_plan_confirmation": False,
                "tools_called": [
                    *state.get("tools_called", []),
                    *[api.__name__ for api in apis]
                ],
                "execution_trace": [
                    *state.get("execution_trace", []),
                    {
                        "node": "plan_generator",
                        "plan_type": collector.plan_type,
                        "progress": "complete",
                        "plan_generated": True,
                        "success": True
                    }
                ]
            }
        else:
            # 返回下一个问题（信息收集未完成）
            next_question = collector.get_next_question()
            return {
                "agent_output": next_question or "请提供更多信息",
                "waiting_for_plan_confirmation": False,
                "execution_trace": [
                    *state.get("execution_trace", []),
                    {
                        "node": "plan_generator",
                        "plan_type": collector.plan_type,
                        "progress": f"{collector.current_field_index}/{len(collector.required_fields)}",
                        "collecting_info": True,
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
                *state.get("execution_trace", []),
                {
                    "node": "plan_generator",
                    "error": str(e),
                    "success": False
                }
            ]
        }