"""
LangGraph状态定义
定义整个Agent编排系统的状态结构
"""

from typing import TypedDict, Optional, List, Dict, Any
from langchain_core.messages import BaseMessage
from .schemas import CapabilityFlags


class AgentState(TypedDict):
    """Agent编排系统的完整状态"""

    # ===== 输入 =====
    user_input: str
    session_id: str
    chat_history: List[BaseMessage]
    user_id: Optional[str]
    capabilities: Dict[str, bool]  # 能力开关，使用字典便于序列化

    # ===== 路由决策 =====
    intent: Optional[str]
    selected_agent: Optional[str]
    confidence: float
    blocked_by_capability: bool  # 是否被能力开关阻止

    # ===== Agent执行 =====
    agent_input: Optional[Dict[str, Any]]
    agent_output: Optional[str]
    execution_trace: List[Dict[str, Any]]
    tools_called: List[str]

    # ===== 记忆 =====
    short_term_memory: List[BaseMessage]
    user_preference: Optional[str]
    working_memory: Optional[Dict[str, Any]]

    # ===== 协调 =====
    handoff_reason: Optional[str]
    context_transfer: Optional[Dict[str, Any]]

    # ===== 计划确认流程 =====
    waiting_for_plan_mode_confirm: bool  # 是否等待用户确认开启计划模式
    waiting_for_plan_confirmation: bool  # 是否等待用户确认创建计划
    user_confirmed_create: bool          # 用户是否确认创建计划到平台
    plan_text_cache: Optional[str]       # 缓存生成的计划文本
    plan_title: Optional[str]            # 提取的计划标题
    plan_type: Optional[str]             # 计划类型（learning/health/travel/work/finance）

    # ===== 输出 =====
    final_response: Optional[str]
    error: Optional[str]
    metrics: Dict[str, Any]
