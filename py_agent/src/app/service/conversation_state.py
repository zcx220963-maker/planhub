"""
对话状态管理器

管理智能助手的对话状态，解决"AI忘记当前在干什么"的问题。

核心功能：
1. 状态追踪：idle（空闲）→ waiting_param（等待参数）→ executing（执行中）→ waiting_select（等待选择）
2. 参数暂存：多轮对话中暂存用户已提供的参数
3. 任务上下文：记住当前任务的目标和进度
4. 错误恢复：工具调用失败时的重试策略
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime


class ConversationStateEnum(Enum):
    """对话状态枚举"""
    IDLE = "idle"                        # 空闲状态，等待用户输入
    WAITING_PARAM = "waiting_param"      # 等待用户提供必要参数
    WAITING_SELECT = "waiting_select"    # 等待用户从列表中选择一个
    EXECUTING = "executing"              # 正在执行工具调用
    COMPLETED = "completed"              # 任务已完成


class ConversationState:
    """对话状态管理器"""

    def __init__(self):
        self.state: ConversationStateEnum = ConversationStateEnum.IDLE
        self.current_task: Optional[str] = None          # 当前任务类型（如 "create_plan"）
        self.current_tool: Optional[str] = None          # 当前要调用的工具名
        self.params: Dict[str, Any] = {}                 # 已收集的参数
        self.required_params: List[str] = []             # 还需要的参数列表
        self.optional_params: List[str] = []             # 可选参数列表
        self.context: Dict[str, Any] = {}                # 上下文信息（如搜索结果、未打卡列表）
        self.retry_count: int = 0                        # 当前工具调用重试次数
        self.max_retries: int = 2                        # 最大重试次数
        self.last_error: Optional[str] = None            # 最后一次错误信息
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()

    def transition(self, new_state: ConversationStateEnum):
        """状态转换"""
        old_state = self.state
        self.state = new_state
        self.updated_at = datetime.now()
        print(f"[State] {old_state.value} -> {new_state.value}")

    def set_task(self, task_type: str, tool_name: str, required: List[str], optional: List[str] = None):
        """设置当前任务"""
        self.current_task = task_type
        self.current_tool = tool_name
        self.required_params = required.copy()
        self.optional_params = optional or []
        self.params = {}
        self.retry_count = 0
        self.last_error = None
        self.transition(ConversationStateEnum.WAITING_PARAM)
        print(f"[State] 设置任务: {task_type}, 工具: {tool_name}, 需要参数: {required}")

    def add_param(self, key: str, value: Any):
        """添加一个参数"""
        self.params[key] = value
        if key in self.required_params:
            self.required_params.remove(key)
        self.updated_at = datetime.now()
        print(f"[State] 添加参数: {key}={value}, 还需: {self.required_params}")

    def add_params(self, params: Dict[str, Any]):
        """批量添加参数"""
        for key, value in params.items():
            self.add_param(key, value)

    def get_missing_params(self) -> List[str]:
        """获取还缺少的必填参数"""
        return self.required_params

    def is_ready_to_execute(self) -> bool:
        """是否已收集完所有必填参数，可以执行"""
        return len(self.required_params) == 0 and self.state == ConversationStateEnum.WAITING_PARAM

    def set_context(self, key: str, value: Any):
        """设置上下文信息"""
        self.context[key] = value
        self.updated_at = datetime.now()

    def get_context(self, key: str, default: Any = None) -> Any:
        """获取上下文信息"""
        return self.context.get(key, default)

    def clear_context(self):
        """清空上下文"""
        self.context = {}

    def increment_retry(self) -> bool:
        """增加重试次数，返回是否还可以重试"""
        self.retry_count += 1
        self.updated_at = datetime.now()
        can_retry = self.retry_count <= self.max_retries
        print(f"[State] 重试次数: {self.retry_count}/{self.max_retries}, 是否可重试: {can_retry}")
        return can_retry

    def set_error(self, error_msg: str):
        """设置错误信息"""
        self.last_error = error_msg
        self.updated_at = datetime.now()
        print(f"[State] 错误: {error_msg}")

    def reset(self):
        """重置状态"""
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
        print("[State] 状态已重置")

    def get_prompt_context(self) -> str:
        """
        生成给AI看的状态提示
        告诉AI当前处于什么状态，还需要什么信息
        """
        lines = []

        if self.state == ConversationStateEnum.WAITING_PARAM:
            lines.append(f"[状态] 正在执行任务: {self.current_task}")
            lines.append(f"[已提供参数] {', '.join(f'{k}={v}' for k, v in self.params.items())}")
            if self.required_params:
                lines.append(f"[缺少参数] {', '.join(self.required_params)}")
                lines.append(f"[提示] 请向用户询问缺少的参数，不要猜测")

        elif self.state == ConversationStateEnum.WAITING_SELECT:
            lines.append(f"[状态] 等待用户从列表中选择一个项目")
            if "options" in self.context:
                options = self.context["options"]
                lines.append(f"[选项列表] 共有 {len(options)} 个选项")
                lines.append("[提示] 等待用户回复序号，收到序号后调用相应工具")

        elif self.state == ConversationStateEnum.EXECUTING:
            lines.append(f"[状态] 正在执行工具调用: {self.current_tool}")
            lines.append(f"[参数] {self.params}")

        elif self.state == ConversationStateEnum.COMPLETED:
            lines.append(f"[状态] 任务已完成: {self.current_task}")
            lines.append("[提示] 询问用户是否还有其他需要")

        if self.last_error:
            lines.append(f"[上次错误] {self.last_error}")
            lines.append(f"[重试次数] {self.retry_count}/{self.max_retries}")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典（用于存储到Redis）"""
        return {
            "state": self.state.value,
            "current_task": self.current_task,
            "current_tool": self.current_tool,
            "params": self.params,
            "required_params": self.required_params,
            "optional_params": self.optional_params,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "last_error": self.last_error,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationState':
        """从字典恢复状态"""
        state = cls()
        state.state = ConversationStateEnum(data.get("state", "idle"))
        state.current_task = data.get("current_task")
        state.current_tool = data.get("current_tool")
        state.params = data.get("params", {})
        state.required_params = data.get("required_params", [])
        state.optional_params = data.get("optional_params", [])
        state.retry_count = data.get("retry_count", 0)
        state.max_retries = data.get("max_retries", 2)
        state.last_error = data.get("last_error")
        state.context = {}  # context不序列化（可能包含不可序列化的对象）
        return state


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


def save_conversation_state_to_redis(session_id: str):
    """保存状态到Redis（需要额外实现序列化）"""
    # TODO: 如果需要持久化到Redis，可以在这里实现
    pass
