"""
LangGraph状态定义
定义整个Agent编排系统的状态结构
"""
import operator
from datetime import datetime
from enum import Enum
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
    long_term_memory: List[str]  # 长期记忆（含用户画像 + 语义检索结果）
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
    plan_flow_cancelled: bool            # 用户取消/拒绝计划创建后标记，supervisor 据此跳过旧 execution_trace 推断
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
    preview_url: Optional[str]               # 后端生成的 HTML 预览页面 URL（plan_writer 输出）
    plan_id: Optional[int]                   # 持久化到计划库后的 ID（plan_writer 输出）

    # ===== 文档知识检索 =====
    doc_data_parts: List[str]              # doc_retriever 输出：知识库检索结果片段
    doc_retrieval_status: str              # 文档检索状态

    # ===== 输出 =====
    final_response: Optional[str]
    error: Optional[str]
    metrics: Dict[str, Any]


# ═══════════════════════════════════════════════════════════════════════════
# 对话状态管理器（从 service/conversation_state.py 迁移）
# ═══════════════════════════════════════════════════════════════════════════

class ConversationStateEnum(Enum):
    """对话状态枚举"""
    IDLE = "idle"                        # 空闲状态，等待用户输入
    WAITING_PARAM = "waiting_param"      # 等待用户提供必要参数
    WAITING_SELECT = "waiting_select"    # 等待用户从列表中选择一个
    EXECUTING = "executing"              # 正在执行工具调用
    COMPLETED = "completed"              # 任务已完成


class ConversationState:
    """对话状态管理器：追踪"AI当前在干什么"""

    def __init__(self):
        self.state: ConversationStateEnum = ConversationStateEnum.IDLE
        self.current_task: Optional[str] = None
        self.current_tool: Optional[str] = None
        self.params: Dict[str, Any] = {}
        self.required_params: List[str] = []
        self.optional_params: List[str] = []
        self.context: Dict[str, Any] = {}
        self.retry_count: int = 0
        self.max_retries: int = 2
        self.last_error: Optional[str] = None
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()

    def transition(self, new_state: ConversationStateEnum):
        self.state = new_state
        self.updated_at = datetime.now()

    def set_task(self, task_type: str, tool_name: str, required: List[str], optional: List[str] = None):
        self.current_task = task_type
        self.current_tool = tool_name
        self.required_params = required.copy()
        self.optional_params = optional or []
        self.params = {}
        self.retry_count = 0
        self.last_error = None
        self.transition(ConversationStateEnum.WAITING_PARAM)

    def add_param(self, key: str, value: Any):
        self.params[key] = value
        if key in self.required_params:
            self.required_params.remove(key)
        self.updated_at = datetime.now()

    def get_missing_params(self) -> List[str]:
        return self.required_params

    def is_ready_to_execute(self) -> bool:
        return len(self.required_params) == 0 and self.state == ConversationStateEnum.WAITING_PARAM

    def increment_retry(self) -> bool:
        self.retry_count += 1
        return self.retry_count <= self.max_retries

    def reset(self):
        self.state = ConversationStateEnum.IDLE
        self.current_task = None
        self.current_tool = None
        self.params = {}
        self.required_params = []
        self.optional_params = []
        self.context = {}
        self.retry_count = 0
        self.last_error = None
        self.updated_at = datetime.now()


# 全局状态存储（session_id -> ConversationState）
_state_store: Dict[str, ConversationState] = {}


def get_conversation_state(session_id: str) -> ConversationState:
    """获取或创建会话状态"""
    if session_id not in _state_store:
        _state_store[session_id] = ConversationState()
    return _state_store[session_id]


def reset_conversation_state(session_id: str):
    """重置会话状态"""
    if session_id in _state_store:
        _state_store[session_id].reset()
