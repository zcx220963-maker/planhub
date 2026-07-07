"""
LangGraph图结构定义
负责创建和配置Agent编排图

图结构（优化版：记忆按需加载）：
supervisor → [assistant | rag | chat | plan_mode_confirm]
                                   ↓
                            plan_mode_confirm → memory_load_for_generator
                                                     ↓
                                               plan_generator
                                                     ↓ (收集完成)
                                            parameter_extractor
                                                     ↓ ╱══════════╲
                                              tool_executor  doc_retriever
                                                     ↓ ╲══════════╱
                                            memory_load_for_writer
                                                     ↓
                                               plan_writer
                                                     ↓
                                             plan_confirmation
                                              ↓              ↓
                                       用户确认          用户拒绝
                                              ↓              ↓
                                     extract_plan_title  memory_save
                                              ↓
                                     create_plan_to_platform
                                              ↓
                                     memory_save → END

特性：
1. 记忆按需加载：只在 plan_generator 和 plan_writer 前加载记忆，节省资源
2. 智能路由：关键词匹配优先 + LLM兜底分类
3. 参数提取 → 工具执行 + 文档检索（并行）→ 计划编写 三阶段分离
4. 计划确认：生成计划后询问用户是否创建到平台
5. 记忆保存：短期Redis(7天) + 长期Chroma
6. 能力开关：可动态控制各Agent能力
7. RedisCheckpointer：30min 过期，跨轮次断点续传
"""

from langgraph.graph import StateGraph, END
from .state import AgentState
from .nodes.supervisor import supervisor_node
from .nodes.plan_mode_confirm import plan_mode_confirm_node
from .nodes.plan_collector import plan_generator_node
from .nodes.parameter_extractor import parameter_extractor_node
from .nodes.tool_executor import tool_executor_node
from .nodes.doc_retriever import doc_retriever_node
from .nodes.plan_writer import plan_writer_node
from .nodes.plan_confirmation import plan_confirmation_node
from .nodes.extract_plan_title import extract_plan_title_node
from .nodes.create_plan_to_platform import create_plan_to_platform_node
from .nodes.orchestrator_assistant import assistant_node
from .nodes.orchestrator_rag import rag_node
from .nodes.orchestrator_chat import chat_node
from .nodes.memory_load import memory_load_node
from .nodes.memory_save import memory_save_node
from .memory_bridge import MemoryBridge


async def memory_load_for_generator(state) -> dict:
    """为 plan_generator 加载记忆（多轮询问需要上下文）"""
    result = await memory_load_node(state)
    # 标记是为 plan_generator 加载的
    for trace in result.get("execution_trace", []):
        trace["for_node"] = "plan_generator"
    return result


async def memory_load_for_writer(state) -> dict:
    """为 plan_writer 加载记忆（生成计划需要短期上下文 + 长期偏好作为参考数据）"""
    result = await memory_load_node(state)
    for trace in result.get("execution_trace", []):
        trace["for_node"] = "plan_writer"
    # 单独检索长期记忆，作为结构化参考数据（同 tool_data_parts/doc_data_parts 一样）
    try:
        from src.app.services.long_term_memory_service import get_long_term_memory_service
        ltm_service = get_long_term_memory_service()
        user_id = state.get("user_id") or "anonymous"
        query = state.get("plan_summary", "") or state.get("user_input", "")
        if query and user_id != "anonymous":
            long_term_memory = await ltm_service.retrieve_memories(
                user_id=user_id, query=query, top_k=5
            )
            if long_term_memory:
                result["long_term_memory"] = long_term_memory
                print(f"[DEBUG] memory_load_for_writer: 长期记忆 {len(long_term_memory)} 条")
    except Exception as e:
        print(f"[WARN] memory_load_for_writer: 长期记忆加载失败: {e}")
    return result


async def _clear_checkpoint(session_id: str):
    """清除 LangGraph checkpoint，释放计划流程状态"""
    try:
        from app.api.orchestrator import _checkpointer, get_thread_id
        if _checkpointer and hasattr(_checkpointer, 'redis'):
            thread_id = get_thread_id(session_id)
            key = f"ckpt:{thread_id}"
            await _checkpointer.redis.delete(key)
            print(f"[DEBUG] memory_save: 已清除 checkpoint key={key}")
    except Exception as e:
        print(f"[WARN] memory_save: 清除 checkpoint 失败: {e}")


def route_after_rag(state) -> str:
    """
    RAG 完成后的路由

    路由逻辑：
    1. 如果 RAG 查询成功（rag_fallback_to_chat=False）→ memory_save
    2. 如果 RAG 查询失败（rag_fallback_to_chat=True）→ chat（fallback）
    """
    fallback = state.get("rag_fallback_to_chat", False)
    
    if fallback:
        print(f"[DEBUG] route_after_rag: RAG fallback to chat")
        return "chat"
    
    print(f"[DEBUG] route_after_rag: RAG success, routing to memory_save")
    return "memory_save"


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
    
    # 学习/健康/旅行/工作/财务计划/计划创建都走 plan_generator
    # 注意：先经过 memory_load_for_generator 加载记忆，再进入 plan_generator
    if selected in ["learning", "health", "travel", "work", "finance", "plan_creation", "plan_generator"]:
        if enable_plan_mode:
            return "memory_load_for_generator"
        else:
            return "assistant"

    # 其他意图正常路由
    if selected in ["assistant", "rag", "chat", "clarify"]:
        return selected

    # plan_builder 直接路由到 parameter_extractor
    if selected == "plan_builder":
        return "parameter_extractor"

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
        # 需要计划构建，路由到 parameter_extractor
        if last_pg_trace.get("needs_plan_building"):
            print(f"[DEBUG] route_after_plan_generator: needs_plan_building=True, routing to parameter_extractor")
            return "parameter_extractor"

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


def route_after_plan_writer(state) -> str:
    """
    plan_writer 完成后的路由

    路由逻辑：
    1. 计划生成成功（plan_generated=True）→ plan_confirmation
    2. 生成失败（plan_generated=False）→ memory_save（回退）
    """
    plan_generated = state.get("plan_generated", False)
    
    if plan_generated:
        print(f"[DEBUG] route_after_plan_writer: plan_generated=True, routing to plan_confirmation")
        return "plan_confirmation"
    
    print(f"[DEBUG] route_after_plan_writer: plan_generated=False, routing to memory_save")
    return "memory_save"


def route_after_plan_confirmation(state) -> str:
    """
    plan_confirmation 完成后的路由

    路由逻辑：
    1. 用户确认创建（user_confirmed_create=True）→ extract_plan_title
    2. 用户说普通对话（selected_agent="chat"）→ chat（同时保持等待确认状态）
    3. 继续等待确认（waiting_for_plan_confirmation=True）→ memory_save（等待下次对话）
    """
    user_confirmed = state.get("user_confirmed_create", False)
    selected = state.get("selected_agent")
    waiting = state.get("waiting_for_plan_confirmation", False)
    
    if user_confirmed:
        return "extract_plan_title"
    
    if selected == "chat":
        return "chat"
    
    if waiting:
        return "memory_save"
    
    return "memory_save"


def route_after_plan_mode_confirm(state) -> str:
    """
    plan_mode_confirm 完成后的路由

    路由逻辑：
    1. 用户确认开启计划（selected_agent="plan_collector"）→ memory_load_for_generator → plan_generator
    2. 用户拒绝/聊天（selected_agent="chat"）→ chat
    3. 等待用户回复（没有 selected_agent）→ memory_save
    """
    selected = state.get("selected_agent")
    
    if selected in ("plan_generator", "plan_collector"):
        return "memory_load_for_generator"
    
    if selected == "chat":
        return "chat"
    
    return "memory_save"


def create_agent_graph():
    """
    创建LangGraph多Agent编排图

    完整流程（记忆按需加载版）：
    1. supervisor - 意图分类和路由决策（关键词匹配优先 + LLM兜底）
    2. agent节点 - 根据路由执行对应Agent
       - plan_mode_confirm → memory_load_for_generator → plan_generator
       - plan_generator: 多轮收集 → parameter_extractor → [tool_executor | doc_retriever]
                         → memory_load_for_writer → plan_writer → plan_confirmation
       - assistant: 通用工具调用
       - rag: 知识库查询（双路召回 + Rerank）
       - chat: 闲聊
    3. memory_save - 保存短期记忆(Redis 7天) + 长期记忆(Chroma)
    4. END - 结束
    """
    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("plan_mode_confirm", plan_mode_confirm_node)
    workflow.add_node("memory_load_for_generator", memory_load_for_generator)
    workflow.add_node("plan_generator", plan_generator_node)
    workflow.add_node("parameter_extractor", parameter_extractor_node)
    workflow.add_node("tool_executor", tool_executor_node)
    workflow.add_node("doc_retriever", doc_retriever_node)
    workflow.add_node("memory_load_for_writer", memory_load_for_writer)
    workflow.add_node("plan_writer", plan_writer_node)
    workflow.add_node("plan_confirmation", plan_confirmation_node)
    workflow.add_node("extract_plan_title", extract_plan_title_node)
    workflow.add_node("create_plan_to_platform", create_plan_to_platform_node)
    workflow.add_node("assistant", assistant_node)
    workflow.add_node("rag", rag_node)
    workflow.add_node("chat", chat_node)
    workflow.add_node("memory_save", memory_save_node)

    # 设置入口点：直接从 supervisor 开始（记忆按需加载）
    workflow.set_entry_point("supervisor")

    # Supervisor条件路由到各Agent
    workflow.add_conditional_edges(
        "supervisor",
        route_by_intent,
        {
            "plan_mode_confirm": "plan_mode_confirm",
            "memory_load_for_generator": "memory_load_for_generator",
            "parameter_extractor": "parameter_extractor",
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
            "memory_load_for_generator": "memory_load_for_generator",
            "chat": "chat",
            "memory_save": "memory_save",
        }
    )

    # memory_load_for_generator → plan_generator
    workflow.add_edge("memory_load_for_generator", "plan_generator")

    # plan_generator → 条件路由（收集信息/确认后提取参数）
    workflow.add_conditional_edges(
        "plan_generator",
        route_after_plan_generator,
        {
            "parameter_extractor": "parameter_extractor",
            "plan_confirmation": "plan_confirmation",
            "memory_save": "memory_save",
        }
    )

    # 参数提取 → 工具执行 + 文档检索（并行）
    workflow.add_edge("parameter_extractor", "tool_executor")
    workflow.add_edge("parameter_extractor", "doc_retriever")
    # 两者都完成后 → memory_load_for_writer → plan_writer
    workflow.add_edge("tool_executor", "memory_load_for_writer")
    workflow.add_edge("doc_retriever", "memory_load_for_writer")
    workflow.add_edge("memory_load_for_writer", "plan_writer")

    # plan_writer → 条件路由（成功→确认，失败→保存）
    workflow.add_conditional_edges(
        "plan_writer",
        route_after_plan_writer,
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
            "chat": "chat",
            "memory_save": "memory_save",
        }
    )

    # extract_plan_title → create_plan_to_platform
    workflow.add_edge("extract_plan_title", "create_plan_to_platform")

    # create_plan_to_platform → memory_save
    workflow.add_edge("create_plan_to_platform", "memory_save")

    # 其他Agent执行完成后 → 保存记忆
    workflow.add_edge("assistant", "memory_save")
    
    # RAG → 条件路由（成功 → memory_save，失败 → chat fallback）
    workflow.add_conditional_edges(
        "rag",
        route_after_rag,
        {
            "memory_save": "memory_save",
            "chat": "chat",
        }
    )
    
    workflow.add_edge("chat", "memory_save")

    # 记忆保存完成 → END
    workflow.add_edge("memory_save", END)

    return workflow