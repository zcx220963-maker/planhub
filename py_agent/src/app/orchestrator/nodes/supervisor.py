"""
Supervisor节点 - 意图分类和路由
使用结构化输出确保稳定性

关键改进：
- 如果当前正在进行计划生成（有 plan_text_cache 或 execution_trace 中有 plan_generator），
  则直接路由回 plan_generator，继续收集信息
"""

from langchain_core.messages import SystemMessage, HumanMessage
from src.app.common.llm_factory import get_llm
from ..schemas import IntentResult

INTENT_CLASSIFICATION_PROMPT = """你是一个意图分类器，根据用户输入判断其意图类别。请以 JSON 格式返回结果。

意图类别（简化版）：
1. plan_creation - 计划创建相关（任何涉及规划、安排、计划的意图）
2. assistant - 通用助手（搜索、发帖、打卡、查看活动）
3. chat - 闲聊（问候、天气、日常对话）
4. clarify - 意图不明确

【最高优先级规则 - 必须先判断】
- 如果输入以"搜索"/"搜"/"找"开头 → assistant
- 如果输入以"打卡"/"我要打卡"/"今日打卡"开头 → assistant
- 如果输入以"发帖"/"发布"开头 → assistant
- 如果输入是单个数字或序号 → assistant

【计划创建意图 - 宽松识别】
以下表达都应该识别为 plan_creation：
- "制定计划"、"创建计划"、"做个计划"、"帮我规划"
- "学习计划"、"健身计划"、"旅行计划"等（任何XX计划）
- "我想学习XX"、"我要健身"、"准备旅行"（隐含需要计划）
- "最近想规划一下"、"做个年度安排"（通用规划意图）

注意：
- 不要区分具体是学习/健康/旅行等类型，统一识别为 plan_creation
- 后续由 plan_generator 通过对话了解具体需求

请只返回意图类别名称和置信度的 JSON 对象。
"""


def _detect_action_type(user_input: str) -> tuple:
    """
    从用户输入中检测 assistant 类操作类型和初始参数

    返回: (action_type, action_params)
    action_type: search / checkin / post / detail / activity / none
    """
    import re
    text = user_input.strip()
    text_lower = text.lower()

    # 1. 搜索
    search_patterns = [
        r'^(搜索|搜|找|查找|查询)(一下|下)?(.+)$',
        r'^(.+?)(搜索|搜|找)$',
    ]
    for pattern in search_patterns:
        match = re.match(pattern, text_lower)
        if match:
            keyword = match.group(match.lastindex).strip()
            if keyword and keyword not in ["计划", "帖子", ""]:
                return ("search", {"keyword": keyword})
            return ("search", {})
    if text_lower in ["搜索", "搜", "找", "查询", "查一下"]:
        return ("search", {})

    # 2. 打卡
    checkin_keywords = ["我要打卡", "今日打卡", "打卡", "签到", "完成打卡"]
    for kw in checkin_keywords:
        if kw in text_lower:
            return ("checkin", {})

    # 3. 发帖
    post_keywords = ["发帖", "发帖子", "发布帖子", "发个帖", "发表"]
    for kw in post_keywords:
        if kw in text_lower:
            params = {}
            # 尝试提取内容和标题
            content_match = re.search(r'内容[：:]\s*(.+?)(?=标题|标签|$)', text)
            if content_match:
                params["content"] = content_match.group(1).strip()
            title_match = re.search(r'(标题|标签|hashtag)[：:]\s*(.+?)(?=内容|$)', text)
            if title_match:
                params["title"] = title_match.group(2).strip()
            return ("post", params)

    # 4. 纯数字或序号 → 详情/选择
    if text.isdigit():
        return ("detail", {"index": int(text)})
    num_patterns = [r'^第([一二三四五六七八九十\d]+)[个条项]$', r'^第(\d+)$']
    for pattern in num_patterns:
        match = re.match(pattern, text_lower)
        if match:
            num = match.group(1)
            if num in "一二三四五六七八九十":
                num_map = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
                num = num_map.get(num, 0)
            return ("detail", {"index": int(num)})

    # 5. 查看活动
    activity_keywords = ["查看活动", "我的活动", "活动记录", "查看我的"]
    for kw in activity_keywords:
        if kw in text_lower:
            return ("activity", {})

    return ("none", {})


async def supervisor_node(state) -> dict:
    """Supervisor节点：意图分类和路由（使用结构化输出）
    
    核心改进：
    1. 如果正在计划流程中，优先路由到 plan_generator / 计划节点，不受文档选中干扰
    2. 如果用户选中了文档但不是计划意图，路由到 RAG 节点
    3. 如果没有选中文档，走正常的意图分类流程（chat/plan/assistant）
    4. 不再通过关键词猜测 RAG 意图，而是由用户行为（选中文档）触发
    """
    
    execution_trace = state.get("execution_trace", [])
    user_input = state.get("user_input", "").strip()
    print(f"[DEBUG] supervisor: execution_trace length = {len(execution_trace)}")

    # —— 记忆透传：LangGraph 中如果一个节点返回的 dict 没有某个字段，该字段会被重置为默认值。
    #     因此每个节点的返回值都必须带上 short_term_memory / long_term_memory，一路传到消费节点。
    short_term = state.get("short_term_memory", [])
    long_term = state.get("long_term_memory", [])

    def _with_memory(d: dict) -> dict:
        """合并 memory 字段到返回字典，避免后续节点丢失短期/长期记忆。"""
        d.setdefault("short_term_memory", short_term)
        d.setdefault("long_term_memory", long_term)
        return d

    # ===== 最高优先级：前端点击「确认」超链接发送的特殊指令 =====
    # 检查当前是否正在等待确认的流程中
    _has_plan_ask = any(
        t.get("node") == "plan_mode_confirm" and t.get("action") == "ask"
        for t in execution_trace
    )
    _has_plan_generator = any(
        t.get("node") == "plan_generator" and t.get("collecting_info")
        for t in execution_trace
    )
    _has_plan_confirmation_waiting = state.get("waiting_for_plan_confirmation", False)
    
    if user_input == "__CLICK_CONFIRM__":
        # 优先级：最新的阶段优先（plan_confirmation > plan_collector > plan_mode_confirm）
        if _has_plan_confirmation_waiting:
            print(f"[DEBUG] supervisor: 收到 __CLICK_CONFIRM__，路由到 plan_confirmation")
            return _with_memory({
                "intent": "plan_creation",
                "selected_agent": "plan_confirmation",
                "confidence": 1.0,
                "execution_trace": [
                    *execution_trace,
                    {
                        "node": "supervisor",
                        "intent": "plan_creation",
                        "selected_agent": "plan_confirmation",
                        "confidence": 1.0,
                        "user_input": "__CLICK_CONFIRM__",
                        "rule": "frontend_confirm_link"
                    }
                ]
            })
        elif _has_plan_generator:
            print(f"[DEBUG] supervisor: 收到 __CLICK_CONFIRM__，路由到 plan_generator（收集完成）")
            return _with_memory({
                "intent": "plan_creation",
                "selected_agent": "plan_generator",
                "confidence": 1.0,
                "execution_trace": [
                    *execution_trace,
                    {
                        "node": "supervisor",
                        "intent": "plan_creation",
                        "selected_agent": "plan_generator",
                        "confidence": 1.0,
                        "user_input": "__CLICK_CONFIRM__",
                        "rule": "frontend_confirm_link"
                    }
                ]
            })
        elif _has_plan_ask:
            print(f"[DEBUG] supervisor: 收到 __CLICK_CONFIRM__，路由到 plan_mode_confirm")
            return _with_memory({
                "intent": "plan_creation",
                "selected_agent": "plan_mode_confirm",
                "confidence": 1.0,
                "execution_trace": [
                    *execution_trace,
                    {
                        "node": "supervisor",
                        "intent": "plan_creation",
                        "selected_agent": "plan_mode_confirm",
                        "confidence": 1.0,
                        "user_input": "__CLICK_CONFIRM__",
                        "rule": "frontend_confirm_link"
                    }
                ]
            })

    # ===== 前端点击「否」超链接发送的特殊指令 =====
    if user_input == "__CLICK_NO__" and _has_plan_confirmation_waiting:
        print(f"[DEBUG] supervisor: 收到 __CLICK_NO__，路由到 plan_confirmation（跳过创建）")
        return _with_memory({
            "intent": "plan_creation",
            "selected_agent": "plan_confirmation",
            "confidence": 1.0,
            "execution_trace": [
                *execution_trace,
                {
                    "node": "supervisor",
                    "intent": "plan_creation",
                    "selected_agent": "plan_confirmation",
                    "confidence": 1.0,
                    "user_input": "__CLICK_NO__",
                    "rule": "frontend_reject_link"
                }
            ]
        })

    # ===== 优先检查：是否正在进行计划生成流程 =====
    # 判断标准：execution_trace 有计划节点 且 至少有一个等待标记为 True
    # 计划完成后所有 waiting_for_* 都会被清空，此时即使 trace 有历史记录也不算"在流程中"
    has_plan_mode_confirm = any(t.get("node") == "plan_mode_confirm" for t in execution_trace)
    has_plan_generator = any(t.get("node") == "plan_generator" for t in execution_trace)
    waiting_mode = state.get("waiting_for_plan_mode_confirm", False)
    waiting_confirmation = state.get("waiting_for_plan_confirmation", False)
    needs_building = state.get("needs_plan_building", False)
    plan_not_finished = waiting_mode or waiting_confirmation or needs_building
    is_in_plan_flow = (has_plan_mode_confirm or has_plan_generator) and plan_not_finished
    
    if is_in_plan_flow:
        print(f"[DEBUG] supervisor: 检测到计划进行中，跳过 RAG 路由（doc_retriever 会在 plan_writer 前注入文档知识）")
        # 继续执行下面的原逻辑（plan_generator 恢复/plan_mode_confirm 确认等）
        # 不走 selected_doc_ids 守卫
    else:
        # ===== 普通查询：检查是否选中了文档 =====
        selected_doc_ids = state.get("selected_doc_ids", [])
        enable_rag = True
        capabilities = state.get("capabilities", {})
        if isinstance(capabilities, dict):
            enable_rag = capabilities.get("enable_rag", True)
        else:
            enable_rag = getattr(capabilities, "enable_rag", True)
        
        if selected_doc_ids and enable_rag:
            # 检查用户的输入是不是计划意图（如"制定计划"），如果是则不应走 RAG
            user_input = state.get("user_input", "").strip()
            plan_keywords = ["计划", "制定", "规划", "安排"]
            is_plan_intent = any(kw in user_input for kw in plan_keywords) if user_input else False
            
            if is_plan_intent:
                print(f"[DEBUG] supervisor: User selected docs but intent is plan creation, skipping RAG route")
            else:
                print(f"[DEBUG] supervisor: User selected {len(selected_doc_ids)} docs, routing directly to RAG")
                return _with_memory({
                    "intent": "rag",
                    "selected_agent": "rag",
                    "confidence": 1.0,
                    "execution_trace": [
                        *execution_trace,
                        {
                            "node": "supervisor",
                            "intent": "rag",
                            "selected_agent": "rag",
                            "confidence": 1.0,
                            "reason": "用户选中了文档，触发知识库查询",
                            "selected_doc_ids": selected_doc_ids
                        }
                    ]
                })
    
    # ===== 原逻辑：检查是否正在进行计划生成 =====
    # 如果已经在计划生成过程中，直接路由回 plan_generator
    is_in_plan_generation = False
    plan_type = None
    
    # 复用上面已获取的 has_plan_generator
    if has_plan_generator:
        is_in_plan_generation = True
    from src.app.services.conversation_state import get_conversation_state, ConversationStateEnum
    session_id = state.get("session_id", "default")
    conv_state = get_conversation_state(session_id)
    
    if conv_state.state in [ConversationStateEnum.WAITING_PARAM, ConversationStateEnum.WAITING_SELECT]:
        print(f"[DEBUG] supervisor: 当前状态={conv_state.state.value}, 任务={conv_state.current_task}, 路由到 assistant")
        # 从对话状态中获取 action_type 和已收集的参数
        action_type = conv_state.current_task or "none"
        action_params = conv_state.params.copy()
        # 如果是 WAITING_SELECT 且用户输入是数字，解析 index
        user_input = state["user_input"]
        action_type_detected, params_detected = _detect_action_type(user_input)
        if action_type_detected == "detail":
            action_params.update(params_detected)
            # 如果当前任务是checkin，将action_type改为checkin（用户正在选择打卡序号）
            if action_type == "checkin":
                print(f"[DEBUG] supervisor: 当前任务是checkin，用户输入序号，action_type改为checkin")
        return _with_memory({
            "intent": "assistant",
            "selected_agent": "assistant",
            "confidence": 1.0,
            "action_type": action_type,
            "action_params": action_params,
            "execution_trace": [
                {
                    "node": "supervisor",
                    "intent": "assistant",
                    "selected_agent": "assistant",
                    "confidence": 1.0,
                    "reason": f"正在等待参数/选择（状态={conv_state.state.value}），继续执行任务",
                    "current_task": conv_state.current_task,
                    "action_type": action_type,
                    "action_params": action_params
                }
            ]
        })
    
    # 优先检查是否正在等待计划模式确认
    if state.get("waiting_for_plan_mode_confirm"):
        plan_type = state.get("plan_type")
        print(f"[DEBUG] supervisor: waiting_for_plan_mode_confirm=True, routing to plan_mode_confirm")
        return _with_memory({
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
        })
    
    # 优先检查是否正在等待计划确认
    if state.get("waiting_for_plan_confirmation"):
        is_in_plan_generation = True
        plan_type = state.get("plan_type")
        print(f"[DEBUG] supervisor: waiting_for_plan_confirmation=True, routing to plan_confirmation")
        return _with_memory({
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
        })
    
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
                return _with_memory({
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
                })
            # 如果计划还在收集信息或需要澄清，继续路由到 plan_generator
            # 但只有在计划未完成的情况下（needs_plan_building 或 plan_text_cache 还在）
            if (trace.get("collecting_info") or trace.get("need_clarification")) and plan_not_finished:
                is_in_plan_generation = True
                plan_type = trace.get("plan_type")
                break
    
    # 如果正在计划生成过程中，直接路由回 plan_generator
    if is_in_plan_generation:
        print(f"[DEBUG] supervisor: routing back to plan_generator, plan_type={plan_type}")
        return _with_memory({
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
        })
    
    # ===== 前置关键词检查（比 LLM 分类更快更准确）=====
    user_input = state["user_input"].strip().lower()

    # 搜索关键词：直接路由到 assistant（最高优先级，覆盖计划意图）
    # 仅匹配以搜索词开头的输入
    search_keywords = ["搜索", "搜", "找", "查找", "查询", "搜一下", "查一下", "搜搜", "找找"]
    is_search = user_input.startswith(tuple(search_keywords))
    if is_search:
        action_type, action_params = _detect_action_type(state["user_input"])
        print(f"[DEBUG] supervisor: 前置规则匹配「搜索」，路由到 assistant, action_type={action_type}")
        return _with_memory({
            "intent": "assistant",
            "selected_agent": "assistant",
            "confidence": 1.0,
            "action_type": action_type,
            "action_params": action_params,
            "execution_trace": [
                {
                    "node": "supervisor",
                    "intent": "assistant",
                    "confidence": 1.0,
                    "user_input": state["user_input"][:100],
                    "rule": "前置搜索关键词",
                    "action_type": action_type
                }
            ]
        })

    # 打卡关键词：直接路由到 assistant
    if user_input.startswith(("打卡", "我要打卡", "今日打卡", "签到")):
        print(f"[DEBUG] supervisor: 前置规则匹配「打卡」，路由到 assistant")
        return _with_memory({
            "intent": "assistant",
            "selected_agent": "assistant",
            "confidence": 1.0,
            "action_type": "checkin",
            "action_params": {},
            "execution_trace": [
                {
                    "node": "supervisor",
                    "intent": "assistant",
                    "confidence": 1.0,
                    "user_input": state["user_input"][:100],
                    "rule": "前置打卡关键词"
                }
            ]
        })
    
    # 发帖关键词：直接路由到 assistant
    if user_input.startswith(("发帖", "发帖子", "发布帖子", "发布", "发表")):
        action_type, action_params = _detect_action_type(state["user_input"])
        print(f"[DEBUG] supervisor: 前置规则匹配「发帖」，路由到 assistant")
        return _with_memory({
            "intent": "assistant",
            "selected_agent": "assistant",
            "confidence": 1.0,
            "action_type": "post",
            "action_params": action_params,
            "execution_trace": [
                {
                    "node": "supervisor",
                    "intent": "assistant",
                    "confidence": 1.0,
                    "user_input": state["user_input"][:100],
                    "rule": "前置发帖关键词"
                }
            ]
        })
    
    # 纯数字或序号：直接路由到 assistant（选择）
    if user_input.isdigit() or user_input.startswith(("第", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十")):
        action_type, action_params = _detect_action_type(state["user_input"])
        print(f"[DEBUG] supervisor: 前置规则匹配「数字/序号」，路由到 assistant, action_type={action_type}")
        return _with_memory({
            "intent": "assistant",
            "selected_agent": "assistant",
            "confidence": 1.0,
            "action_type": action_type,
            "action_params": action_params,
            "execution_trace": [
                {
                    "node": "supervisor",
                    "intent": "assistant",
                    "confidence": 1.0,
                    "user_input": state["user_input"][:100],
                    "rule": "前置数字/序号规则"
                }
            ]
        })
    
    # ===== 计划创建关键词：直接路由到 plan_mode_confirm =====
    # 任何表达规划意图的输入，都统一路由到计划生成流程
    plan_keywords = [
        "制定计划", "创建计划", "生成计划", "做计划", "做个计划",
        "计划", "规划", "安排", "学习计划", "健身计划", "旅行计划",
        "工作计划", "理财计划", "健康计划", "减肥计划", "年度计划",
        "我想学习", "我要学习", "我想健身", "我要健身",
        "我想减肥", "我要减肥", "我想旅行", "准备旅行",
        "去旅行", "旅游计划", "帮我规划", "我想规划",
        "提升自己", "自我提升", "年度安排", "最近想规划"
    ]
    
    # 检查是否包含计划关键词（搜索/打卡/发帖已在上方处理，不会走到这里）
    if any(kw in user_input for kw in plan_keywords):
            print(f"[DEBUG] supervisor: 前置规则匹配「计划创建」，统一路由到 plan_mode_confirm")
            return _with_memory({
                "intent": "plan_creation",
                "selected_agent": "plan_mode_confirm",
                "confidence": 1.0,
                "execution_trace": [
                    {
                        "node": "supervisor",
                        "intent": "plan_creation",
                        "confidence": 1.0,
                        "user_input": state["user_input"][:100],
                        "rule": "前置计划关键词"
                    }
                ]
            })
    
    try:
        # ===== LLM 预处理用户输入（提取核心语义用于检索匹配）=====
        user_input = state["user_input"].strip()
        processed_input = user_input  # 默认直接用原输入
        if len(user_input) > 20:
            try:
                preprocess_llm = get_llm(temperature=0.1)
                preprocess_prompt = (
                    f"提取以下用户输入的核心意图关键词（最多10字），只输出关键词不要解释：\n{user_input}"
                )
                preprocess_result = await preprocess_llm.ainvoke([HumanMessage(content=preprocess_prompt)])
                processed_text = preprocess_result.content.strip() if hasattr(preprocess_result, "content") else str(preprocess_result).strip()
                if processed_text and len(processed_text) <= 50:
                    processed_input = processed_text
                    print(f"[DEBUG] supervisor: 用户输入预处理 '{user_input[:30]}...' → '{processed_input}'")
            except Exception:
                pass  # 预处理失败不影响主流程

        # 使用结构化输出，自动验证格式
        llm = get_llm().with_structured_output(IntentResult)

        # 构建消息（用预处理后的输入辅助分类）
        messages = [
            SystemMessage(content=INTENT_CLASSIFICATION_PROMPT),
            HumanMessage(content=processed_input if processed_input != user_input else user_input)
        ]

        # 调用LLM进行意图分类
        result: IntentResult = await llm.ainvoke(messages)
        print(f"[DEBUG] supervisor: LLM result = {result}")

        # 如果识别到计划相关意图，先询问确认
        plan_intents = ["plan_creation"]
        if result.intent in plan_intents and result.confidence >= 0.5:
            return _with_memory({
                "intent": result.intent,
                "selected_agent": "plan_mode_confirm",
                "confidence": result.confidence,
                "processed_user_input": processed_input,
                "execution_trace": [
                    {
                        "node": "supervisor",
                        "intent": result.intent,
                        "confidence": result.confidence,
                        "user_input": state["user_input"][:100],
                        "action": "ask_confirmation"
                    }
                ]
            })

        # 如果是 assistant 意图，解析 action_type 和参数
        if result.intent == "assistant":
            action_type, action_params = _detect_action_type(state["user_input"])
            print(f"[DEBUG] supervisor: 识别为 assistant, action_type={action_type}, params={action_params}")
            return _with_memory({
                "intent": "assistant",
                "selected_agent": "assistant",
                "confidence": result.confidence,
                "action_type": action_type,
                "action_params": action_params,
                "processed_user_input": processed_input,
                "execution_trace": [
                    {
                        "node": "supervisor",
                        "intent": "assistant",
                        "confidence": result.confidence,
                        "user_input": state["user_input"][:100],
                        "action_type": action_type,
                        "action_params": action_params
                    }
                ]
            })

        # 更新状态（直接访问属性，无需 json.loads）
        return _with_memory({
            "intent": result.intent,
            "selected_agent": result.intent,
            "confidence": result.confidence,
            "processed_user_input": processed_input,
            "execution_trace": [
                {
                    "node": "supervisor",
                    "intent": result.intent,
                    "confidence": result.confidence,
                    "user_input": state["user_input"][:100]
                }
            ]
        })

    except Exception as e:
        # 降级到chat
        return _with_memory({
            "intent": "chat",
            "selected_agent": "chat",
            "confidence": 0.0,
            "processed_user_input": state.get("user_input", ""),
            "error": f"意图分类失败: {str(e)}",
            "execution_trace": [
                {
                    "node": "supervisor",
                    "intent": "chat",
                    "confidence": 0.0,
                    "error": str(e),
                    "fallback": True
                }
            ]
        })

async def _preprocess_user_input_supervisor(state) -> dict:
    """
    轻量级预处理节点：只做 LLM 预处理用户输入，不分类。
    用于在 supervisor 之外的场景（如独立调用）提取核心语义。
    """
    user_input = state.get("user_input", "").strip()
    if not user_input or len(user_input) <= 20:
        return {"processed_user_input": user_input}

    try:
        from langchain_core.messages import HumanMessage
        from src.app.common.llm_factory import get_llm
        llm = get_llm(temperature=0.1)
        prompt = f"提取以下用户输入的核心意图关键词（最多10字），只输出关键词不要解释：\n{user_input}"
        result = await llm.ainvoke([HumanMessage(content=prompt)])
        processed = result.content.strip() if hasattr(result, "content") else str(result).strip()
        if processed and len(processed) <= 50:
            return {"processed_user_input": processed}
    except Exception:
        pass
    return {"processed_user_input": user_input}
