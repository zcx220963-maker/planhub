"""
LangGraph图结构定义
负责创建和配置Agent编排图

图结构：
memory_load → supervisor → [plan_generator | assistant | rag | chat]
                                    ↓
                          plan_generator → plan_confirmation
                                    ↓                    ↓
                              用户确认              用户拒绝
                                    ↓                    ↓
                          extract_plan_title      memory_save
                                    ↓
                          create_plan_to_platform
                                    ↓
                          memory_save → END

特性：
1. 记忆加载：从Redis加载用户短期记忆和偏好
2. 智能路由：根据意图分类路由到对应Agent
3. 计划确认：生成计划后询问用户是否创建到平台
4. 记忆保存：将对话记录和状态保存到Redis
5. 能力开关：可动态控制各Agent能力
"""

from langgraph.graph import StateGraph, END
from .state import AgentState
from .nodes.supervisor import supervisor_node
from .nodes.plan_mode_confirm import plan_mode_confirm_node
from .nodes.plan_generator import plan_generator_node
from .nodes.plan_confirmation import plan_confirmation_node
from .nodes.extract_plan_title import extract_plan_title_node
from .nodes.create_plan_to_platform import create_plan_to_platform_node
from .nodes.assistant import assistant_node
from .nodes.rag import rag_node
from .nodes.chat import chat_node
from .memory_bridge import MemoryBridge


async def memory_load_node(state) -> dict:
    """记忆加载节点：从Redis加载用户记忆"""
    memory_bridge = MemoryBridge()
    session_id = state.get("session_id", "default")
    user_id = state.get("user_id")
    
    try:
        memory_data = await memory_bridge.load_memory(session_id, user_id)
        
        return {
            "short_term_memory": memory_data.get("short_term_memory", []),
            "user_preference": memory_data.get("user_preference"),
            "working_memory": memory_data.get("working_memory"),
            "execution_trace": [
                *state.get("execution_trace", []),
                {
                    "node": "memory_load",
                    "session_id": session_id,
                    "user_id": user_id,
                    "short_term_count": len(memory_data.get("short_term_memory", [])),
                    "success": True
                }
            ]
        }
    except Exception as e:
        return {
            "short_term_memory": [],
            "user_preference": None,
            "working_memory": None,
            "execution_trace": [
                *state.get("execution_trace", []),
                {
                    "node": "memory_load",
                    "error": str(e),
                    "success": False,
                    "fallback": True
                }
            ]
        }


async def memory_save_node(state) -> dict:
    """记忆保存节点：将对话记录和状态保存到Redis"""
    memory_bridge = MemoryBridge()
    session_id = state.get("session_id", "default")
    user_id = state.get("user_id") or "anonymous"
    
    # 构建聊天历史
    chat_history = []
    if state.get("user_input"):
        chat_history.append({"role": "user", "content": state["user_input"]})
    if state.get("agent_output"):
        chat_history.append({"role": "assistant", "content": state["agent_output"]})
    
    try:
        # 保存短期记忆
        await memory_bridge.save_memory(
            session_id=session_id,
            user_id=user_id,
            chat_history=chat_history,
            user_preference=state.get("user_preference"),
            working_memory=state.get("working_memory")
        )
        
        # 保存会话到 Redis（用于前端会话列表显示）
        # 尝试从 Redis 获取现有会话历史，追加新消息
        existing_conv = memory_bridge.get_conversation(session_id)
        if existing_conv and existing_conv.get("history"):
            # 追加新消息到现有历史
            full_history = existing_conv["history"] + chat_history
        else:
            full_history = chat_history
        
        # 保存会话（module 为 orchestrator）
        memory_bridge.save_conversation(
            session_id=session_id,
            user_id=user_id,
            module="orchestrator",
            history=full_history
        )
        
        return {
            "final_response": state.get("agent_output", "处理完成"),
            "execution_trace": [
                *state.get("execution_trace", []),
                {
                    "node": "memory_save",
                    "session_id": session_id,
                    "user_id": user_id,
                    "chat_history_count": len(chat_history),
                    "total_history_count": len(full_history),
                    "success": True
                }
            ]
        }
    except Exception as e:
        return {
            "final_response": state.get("agent_output", "处理完成"),
            "execution_trace": [
                *state.get("execution_trace", []),
                {
                    "node": "memory_save",
                    "error": str(e),
                    "success": False,
                    "fallback": True
                }
            ]
        }


def route_by_intent(state) -> str:
    """
    根据意图和能力开关路由到对应Agent

    路由逻辑：
    1. 首先检查能力开关，如果被阻止则降级
    2. 然后根据selected_agent路由
    3. 默认路由到chat
    """
    selected = state.get("selected_agent", "chat")
    capabilities = state.get("capabilities", {})

    # 处理capabilities可能是dict或Pydantic模型的情况
    if isinstance(capabilities, dict):
        enable_rag = capabilities.get("enable_rag", True)
        enable_plan_mode = capabilities.get("enable_plan_mode", True)
    else:
        enable_rag = getattr(capabilities, "enable_rag", True)
        enable_plan_mode = getattr(capabilities, "enable_plan_mode", True)

    # 能力开关降级逻辑
    if selected == "rag" and not enable_rag:
        return "assistant"

    if selected == "plan_generator" and not enable_plan_mode:
        return "assistant"

    # 计划模式确认直接路由
    if selected == "plan_mode_confirm":
        return "plan_mode_confirm"
    
    # 计划确认直接路由到 plan_confirmation
    if selected == "plan_confirmation":
        return "plan_confirmation"
    
    # 学习/健康/旅行/工作/财务计划/计划创建都走plan_generator
    if selected in ["learning", "health", "travel", "work", "finance", "plan_creation", "plan_generator"]:
        if enable_plan_mode:
            return "plan_generator"
        else:
            return "assistant"

    # 其他意图正常路由
    if selected in ["assistant", "rag", "chat", "clarify"]:
        return selected

    # 默认降级到chat
    return "chat"


def route_after_plan_generator(state) -> str:
    """
    plan_generator 完成后的路由

    路由逻辑：
    1. 如果计划已生成（plan_generated=True）→ plan_confirmation（询问用户）
    2. 如果还在收集信息（collecting_info=True）→ memory_save（等待下次对话）
    3. 如果需要澄清（need_clarification=True）→ memory_save
    """
    execution_trace = state.get("execution_trace", [])
    
    print(f"[DEBUG] route_after_plan_generator: execution_trace length = {len(execution_trace)}")
    
    # 查找最后一个 plan_generator 的执行记录
    last_pg_trace = None
    for trace in reversed(execution_trace):
        if trace.get("node") == "plan_generator":
            last_pg_trace = trace
            print(f"[DEBUG] route_after_plan_generator: found plan_generator trace: {last_pg_trace}")
            break
    
    if last_pg_trace:
        # 计划已生成，询问用户是否创建到平台
        if last_pg_trace.get("plan_generated"):
            print(f"[DEBUG] route_after_plan_generator: plan_generated=True, routing to plan_confirmation")
            return "plan_confirmation"
        
        # 还在收集信息，保存记忆等待下次对话
        if last_pg_trace.get("collecting_info"):
            print(f"[DEBUG] route_after_plan_generator: collecting_info=True, routing to memory_save")
            return "memory_save"
        
        # 需要澄清，保存记忆
        if last_pg_trace.get("need_clarification"):
            print(f"[DEBUG] route_after_plan_generator: need_clarification=True, routing to memory_save")
            return "memory_save"
    
    # 默认保存记忆
    print(f"[DEBUG] route_after_plan_generator: default routing to memory_save")
    return "memory_save"


def route_after_plan_confirmation(state) -> str:
    """
    plan_confirmation 完成后的路由

    路由逻辑：
    1. 用户确认创建（user_confirmed_create=True）→ extract_plan_title
    2. 用户拒绝创建 → memory_save
    3. 继续等待确认（waiting_for_plan_confirmation=True）→ memory_save（等待下次对话）
    """
    user_confirmed = state.get("user_confirmed_create", False)
    waiting = state.get("waiting_for_plan_confirmation", False)
    
    if user_confirmed:
        return "extract_plan_title"
    
    if waiting:
        return "memory_save"
    
    return "memory_save"


def route_after_plan_mode_confirm(state) -> str:
    """
    plan_mode_confirm 完成后的路由

    路由逻辑：
    1. 用户确认开启计划（selected_agent="plan_generator"）→ plan_generator
    2. 用户拒绝（selected_agent="chat"）→ chat
    3. 等待用户回复（没有 selected_agent）→ memory_save
    """
    selected = state.get("selected_agent")
    
    if selected == "plan_generator":
        return "plan_generator"
    
    if selected == "chat":
        return "chat"
    
    return "memory_save"


def create_agent_graph():
    """
    创建LangGraph多Agent编排图

    完整流程：
    1. memory_load - 从Redis加载用户记忆
    2. supervisor - 意图分类和路由决策
    3. agent节点 - 根据路由执行对应Agent
       - plan_generator: 计划生成 → plan_confirmation → extract_plan_title → create_plan_to_platform
       - assistant: 通用工具调用
       - rag: 知识库查询
       - chat: 闲聊
    4. memory_save - 保存对话记录和状态到Redis
    5. END - 结束
    """
    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("memory_load", memory_load_node)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("plan_mode_confirm", plan_mode_confirm_node)
    workflow.add_node("plan_generator", plan_generator_node)
    workflow.add_node("plan_confirmation", plan_confirmation_node)
    workflow.add_node("extract_plan_title", extract_plan_title_node)
    workflow.add_node("create_plan_to_platform", create_plan_to_platform_node)
    workflow.add_node("assistant", assistant_node)
    workflow.add_node("rag", rag_node)
    workflow.add_node("chat", chat_node)
    workflow.add_node("memory_save", memory_save_node)

    # 设置入口点：先加载记忆
    workflow.set_entry_point("memory_load")

    # 记忆加载 → Supervisor路由
    workflow.add_edge("memory_load", "supervisor")

    # Supervisor条件路由到各Agent
    workflow.add_conditional_edges(
        "supervisor",
        route_by_intent,
        {
            "plan_mode_confirm": "plan_mode_confirm",
            "plan_generator": "plan_generator",
            "plan_confirmation": "plan_confirmation",
            "assistant": "assistant",
            "rag": "rag",
            "chat": "chat",
            "clarify": "chat",
        }
    )

    # plan_mode_confirm → 条件路由（用户确认开启计划或拒绝）
    workflow.add_conditional_edges(
        "plan_mode_confirm",
        route_after_plan_mode_confirm,
        {
            "plan_generator": "plan_generator",
            "chat": "chat",
            "memory_save": "memory_save",
        }
    )

    # plan_generator → 条件路由（询问确认或直接保存）
    workflow.add_conditional_edges(
        "plan_generator",
        route_after_plan_generator,
        {
            "plan_confirmation": "plan_confirmation",
            "memory_save": "memory_save",
        }
    )

    # plan_confirmation → 条件路由（用户确认或拒绝）
    workflow.add_conditional_edges(
        "plan_confirmation",
        route_after_plan_confirmation,
        {
            "extract_plan_title": "extract_plan_title",
            "memory_save": "memory_save",
        }
    )

    # extract_plan_title → create_plan_to_platform
    workflow.add_edge("extract_plan_title", "create_plan_to_platform")

    # create_plan_to_platform → memory_save
    workflow.add_edge("create_plan_to_platform", "memory_save")

    # 其他Agent执行完成后 → 保存记忆
    workflow.add_edge("assistant", "memory_save")
    workflow.add_edge("rag", "memory_save")
    workflow.add_edge("chat", "memory_save")

    # 记忆保存完成 → END
    workflow.add_edge("memory_save", END)

    return workflow