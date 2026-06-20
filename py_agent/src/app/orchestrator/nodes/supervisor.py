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

INTENT_CLASSIFICATION_PROMPT = """你是一个意图分类器，根据用户输入判断其意图类别。

意图类别：
1. learning - 学习计划相关（学习计划、课程、考试、学习）
2. health - 健康计划相关（健身、减肥、饮食、运动）
3. travel - 旅行计划相关（旅行、旅游、出行）
4. work - 工作计划相关（工作、项目、任务）
5. finance - 财务计划相关（理财、储蓄、投资）
6. plan_creation - 计划创建相关（制定计划、创建计划、生成计划、做计划）
7. rag - 知识库查询（知识库、文档、资料库、查询XXX的文档）
8. assistant - 通用助手（发帖、发帖到社区、搜索计划、打卡、今日打卡、查看活动、选择计划）
9. chat - 闲聊（问候、天气、日常对话、关于你、你是谁）
10. clarify - 意图不明确，需要进一步澄清

重要规则：
- "搜索"单独出现 → assistant
- "打卡/今日打卡/我要打卡" → assistant
- "知识库查询XXX/查询XXX的文档" → rag
- "制定/创建/生成计划" → plan_creation
- 问候类（你好/嗨/在吗）→ chat
- 只有单个词（"搜索"、"发帖"、"打卡"）→ assistant
- **单个数字（"1"、"2"、"3"等）或序号（"第一个"、"第二个"、"第1个"）→ assistant**
  - 这通常表示用户正在选择之前展示列表中的某一项
  - 例如：助手展示了计划列表，用户说"1"表示选择第1个计划
  - 例如：助手展示了搜索结果，用户说"2"表示选择第2个结果

请只返回意图类别名称和置信度。
"""


async def supervisor_node(state) -> dict:
    """Supervisor节点：意图分类和路由（使用结构化输出）"""
    
    # 检查是否正在进行计划生成
    # 如果已经在计划生成过程中，直接路由回 plan_generator
    is_in_plan_generation = False
    plan_type = None
    
    # 检查 execution_trace 中是否有 plan_generator 记录
    execution_trace = state.get("execution_trace", [])
    print(f"[DEBUG] supervisor: execution_trace length = {len(execution_trace)}")
    
    # 优先检查是否正在等待计划模式确认
    if state.get("waiting_for_plan_mode_confirm"):
        plan_type = state.get("plan_type")
        print(f"[DEBUG] supervisor: waiting_for_plan_mode_confirm=True, routing to plan_mode_confirm")
        return {
            "intent": plan_type or "learning",
            "selected_agent": "plan_mode_confirm",
            "confidence": 1.0,
            "execution_trace": [
                *state.get("execution_trace", []),
                {
                    "node": "supervisor",
                    "intent": plan_type or "learning",
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
            "intent": plan_type or "learning",
            "selected_agent": "plan_confirmation",
            "confidence": 1.0,
            "execution_trace": [
                *state.get("execution_trace", []),
                {
                    "node": "supervisor",
                    "intent": plan_type or "learning",
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
            # 如果计划已生成，路由到 plan_confirmation
            if trace.get("plan_generated"):
                is_in_plan_generation = True
                plan_type = trace.get("plan_type")
                return {
                    "intent": plan_type or "learning",
                    "selected_agent": "plan_confirmation",
                    "confidence": 1.0,
                    "execution_trace": [
                        *state.get("execution_trace", []),
                        {
                            "node": "supervisor",
                            "intent": plan_type or "learning",
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
            "intent": plan_type or "learning",
            "selected_agent": "plan_generator",
            "confidence": 1.0,
            "execution_trace": [
                *state.get("execution_trace", []),
                {
                    "node": "supervisor",
                    "intent": plan_type or "learning",
                    "selected_agent": "plan_generator",
                    "confidence": 1.0,
                    "reason": "继续计划生成流程",
                    "plan_type": plan_type
                }
            ]
        }
    
    try:
        # 使用结构化输出，自动验证格式
        llm = get_llm().with_structured_output(IntentResult)

        # 构建消息
        messages = [
            SystemMessage(content=INTENT_CLASSIFICATION_PROMPT),
            HumanMessage(content=state["user_input"])
        ]

        # 调用LLM进行意图分类
        result: IntentResult = await llm.ainvoke(messages)
        print(f"[DEBUG] supervisor: LLM result = {result}")

        # 如果识别到计划相关意图（learning, health, travel, work, finance, plan_creation），先询问确认
        plan_intents = ["learning", "health", "travel", "work", "finance", "plan_creation"]
        if result.intent in plan_intents and result.confidence >= 0.5:
            return {
                "intent": result.intent,
                "selected_agent": "plan_mode_confirm",
                "confidence": result.confidence,
                "execution_trace": [
                    *state.get("execution_trace", []),
                    {
                        "node": "supervisor",
                        "intent": result.intent,
                        "confidence": result.confidence,
                        "user_input": state["user_input"][:100],
                        "action": "ask_confirmation"
                    }
                ]
            }

        # 更新状态（直接访问属性，无需 json.loads）
        return {
            "intent": result.intent,
            "selected_agent": result.intent,
            "confidence": result.confidence,
            "execution_trace": [
                *state.get("execution_trace", []),
                {
                    "node": "supervisor",
                    "intent": result.intent,
                    "confidence": result.confidence,
                    "user_input": state["user_input"][:100]
                }
            ]
        }

    except Exception as e:
        # 降级到chat
        return {
            "intent": "chat",
            "selected_agent": "chat",
            "confidence": 0.0,
            "error": f"意图分类失败: {str(e)}",
            "execution_trace": [
                *state.get("execution_trace", []),
                {
                    "node": "supervisor",
                    "intent": "chat",
                    "confidence": 0.0,
                    "error": str(e),
                    "fallback": True
                }
            ]
        }
