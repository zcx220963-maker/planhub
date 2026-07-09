"""
LangGraph状态定义
定义整个Agent编排系统的状态结构
"""
import operator
from typing import TypedDict, Optional, List, Dict, Any, Union

try:
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated  # type: ignore

from langchain_core.messages import BaseMessage
from .schemas import CapabilityFlags


class AgentState(TypedDict):
    """Agent编排系统的完整状态"""

    # ===== 输入 =====
    user_input: str
    session_id: str
    chat_history: List[BaseMessage]
    user_id: Optional[str]
    capabilities: Dict[str, Any]  # 能力开关，使用字典便于序列化（包含 selected_doc_ids）
    selected_doc_ids: List[str]  # 用户选中的文档ID列表，用于知识库查询
    rag_fallback_to_chat: bool  # RAG查询失败后是否fallback到chat

    # ===== 路由决策 =====
    intent: Optional[str]
    selected_agent: Optional[str]
    confidence: float
    blocked_by_capability: bool  # 是否被能力开关阻止

    # ===== Agent执行 =====
    agent_input: Optional[Dict[str, Any]]
    agent_output: Optional[str]
    execution_trace: Annotated[List[Dict[str, Any]], operator.add]
    tools_called: List[str]

    # ===== Assistant操作类型 =====
    action_type: Optional[str]  # 操作类型：search/checkin/post/detail/activity/none
    action_params: Dict[str, Any]  # 已解析的操作参数（如 keyword、plan_id 等）

    # ===== 记忆 =====
    short_term_memory: List[BaseMessage]
    user_preference: Optional[str]
    working_memory: Optional[Dict[str, Any]]

    # ===== 协调 =====
    handoff_reason: Optional[str]
    context_transfer: Optional[Dict[str, Any]]
    original_user_input: Optional[str]  # 用户原始问题（计划模式确认被拒后用于 fallback 到 chat）
    chat_override_input: Optional[str]  # chat 节点覆盖输入（用于 fallback 场景）

    # ===== 计划确认流程 =====
    waiting_for_plan_mode_confirm: bool  # 是否等待用户确认开启计划模式
    waiting_for_plan_confirmation: bool  # 是否等待用户确认创建计划
    user_confirmed_create: bool          # 用户是否确认创建计划到平台
    plan_text_cache: Optional[str]       # 缓存生成的计划文本
    plan_title: Optional[str]            # 提取的计划标题
    plan_type: Optional[str]             # 计划类型（learning/health/travel/work/finance）
    plan_info: Optional[Dict[str, Any]]  # 计划信息（包含topic/goal/duration等）
    plan_conversation_history: List[Dict[str, Any]]  # 计划对话历史（用于多轮问答）
    needs_plan_building: bool            # 是否需要执行plan_builder（plan_generator确认后标记）
    plan_generated: bool                 # 计划是否已生成（plan_builder完成后标记）
    plan_summary: Optional[str]          # 需求摘要（plan_generator输出，plan_builder消费）

    # ===== 三阶段计划生成 =====
    ranked_tools: List[Dict[str, Any]]     # parameter_extractor 输出：选中的工具列表
    parameter_extraction_status: str       # 参数提取状态
    tool_call_results: List[Dict[str, Any]]  # tool_executor 输出：成功调用的工具结果
    tool_data_parts: List[str]             # tool_executor 输出：格式化后的工具数据文本
    tool_success_count: int                # tool_executor 输出：成功工具数
    tool_total_count: int                  # tool_executor 输出：总工具数
    tool_fail_log: List[Dict[str, Any]]   # tool_executor 输出：失败日志

    # ===== 前端展示数据 =====
    plan_metadata: Optional[Dict[str, Any]]  # 结构化元数据（工具调用、计划摘要等），供前端展示

    # ===== 文档知识检索 =====
    doc_data_parts: List[str]              # doc_retriever 输出：知识库检索结果片段
    doc_retrieval_status: str              # 文档检索状态

    # ===== 输出 =====
    final_response: Optional[str]
    error: Optional[str]
    metrics: Dict[str, Any]
