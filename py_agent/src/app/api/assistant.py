"""
智能社区助手路由

对外接口保持不变，内部改用 LangChain Tool Calling Agent。
支持：创建计划、发帖、搜索、查看活动、打卡。
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

from app.service.agent_service import get_agent_service
from app.common.llm_factory import set_request_token
from app.common.langchain_tools import _last_jump_data
from app.service.conversation_state import get_conversation_state, reset_conversation_state
from app.dao.redis_dao import (
    get_session,
    save_session,
    is_redis_available
)
from config import settings

router = APIRouter(prefix="/assistant")

# 简单响应缓存（避免重复调用LLM）
_response_cache = {}
CACHE_EXPIRY_SECONDS = 300  # 5分钟过期


# ─── 请求 / 响应模型 ───────────────────────────────────────────────

class AssistantRequest(BaseModel):
    user_message: str
    user_id: Optional[int] = None
    session_id: Optional[str] = None


class AssistantResponse(BaseModel):
    success: bool
    content: str
    action: Optional[dict] = None
    requires_action: bool = False


# ─── 核心接口 ───────────────────────────────────────────────────────

@router.post("/execute", response_model=AssistantResponse)
async def execute_assistant(request: AssistantRequest):
    """
    智能社区助手 — 主入口

    示例请求:
    {
        "user_message": "帮我创建一个学习计划，标题是每天学英语",
        "user_id": 1,
        "session_id": "default"
    }
    """
    try:
        # 构造带上下文的输入
        user_input = request.user_message
        if request.user_id:
            user_input = f"[用户ID: {request.user_id}] {user_input}"

        # 调用 Tool Calling Agent
        agent_service = get_agent_service()
        reply = agent_service.run(user_input)

        return AssistantResponse(
            success=True,
            content=reply,
            action={"type": "tool_calling", "status": "completed"},
            requires_action=False,
        )
    except Exception as e:
        return AssistantResponse(
            success=False,
            content=f"处理失败：{str(e)}",
            action={"type": "error"},
            requires_action=True,
        )


@router.post("")
async def assistant_simple(request: Request):
    """简化版助手接口（兼容旧接口格式）"""
    try:
        data = await request.json()
        query = data.get("query", "")
        session_id = data.get("session_id", "default")
        user_id = data.get("user_id", None)

        # 从请求 Header 获取 Authorization token
        authorization = request.headers.get("Authorization")
        token = None
        if authorization and authorization.startswith("Bearer "):
            token = authorization[7:]

        # 设置请求上下文的 token
        set_request_token(token)

        # 调试日志：检查 token 是否被正确接收
        print(f"[DEBUG] Authorization header: {authorization[:30] if authorization else 'None'}...")
        print(f"[DEBUG] Token set: {'Yes' if token else 'No'}")

        # 检查是否是简单问候（直接返回缓存，不调用LLM）
        simple_greetings = ["你好", "hi", "hello", "嗨", "在吗", "你是谁"]
        if query.strip().lower() in simple_greetings:
            cached_response = _response_cache.get("greeting")
            if cached_response:
                return {
                    "reply": cached_response,
                    "response": cached_response,
                    "session_id": session_id,
                    "search_results": [],
                    "success": True,
                    "content": cached_response,
                    "cached": True
                }

        # 从会话存储中获取历史记录
        chat_history = []
        if settings.use_redis_bool and is_redis_available():
            session_data = get_session(session_id)
            if session_data and "history" in session_data:
                chat_history = session_data["history"]

        # 调用 Tool Calling Agent（传递历史记录和会话ID）
        agent_service = get_agent_service()
        user_input = query
        if user_id:
            user_input = f"[用户ID: {user_id}] {user_input}"

        # 直接调用异步版本，避免事件循环冲突
        reply = await agent_service.run_async(user_input, chat_history, session_id=session_id)

        # 缓存简单问候的回复
        if query.strip().lower() in simple_greetings:
            _response_cache["greeting"] = reply

        # 保存历史记录（包含工具调用结果，以支持多轮对话）
        # 注意：必须包含完整的对话历史（用户输入 → 工具调用 → 工具返回 → AI回复）
        # 这样下一轮对话时，AI 才能看到之前的工具调用结果
        new_history = chat_history + [
            {"role": "user", "content": query},
            {"role": "assistant", "content": reply, "tool_calls": []}  # TODO: 保存实际的工具调用
        ]

        # 如果有工具调用历史（从 agent 返回的消息中提取），也保存它们
        # 注意：这里简化处理，实际应该从 agent_service 返回完整的消息列表
        if hasattr(reply, 'tool_calls') and reply.tool_calls:
            for tc in reply.tool_calls:
                new_history.append({
                    "role": "tool",
                    "content": tc.get('result', ''),
                    "tool_call_id": tc.get('id', ''),
                    "name": tc.get('name', '')
                })

        if settings.use_redis_bool and is_redis_available():
            session_data = session_data or {}
            MAX_HISTORY = 30  # 增加历史记录长度，以包含工具调用
            session_data["history"] = new_history[-MAX_HISTORY:]
            # 保存时传递 user_id 和 module，这样在历史记录列表中能正确显示
            save_session(
                session_id,
                session_data,
                86400,
                user_id=user_id,
                module="assistant"
            )

        # 检查是否有跳转数据
        jump_data = None
        try:
            from app.common.langchain_tools import _last_jump_data
            if _last_jump_data:
                jump_data = _last_jump_data
                # 读取后在 langchain_tools 中重置
                import app.common.langchain_tools as langchain_tools
                langchain_tools._last_jump_data = None
        except Exception as e:
            print(f"[DEBUG] Error checking jump data: {e}")

        # 返回旧接口兼容格式 + 跳转数据
        response_data = {
            "reply": reply,
            "response": reply,
            "session_id": session_id,
            "search_results": [],
            "success": True,
            "content": reply,
        }

        # 如果有跳转数据，添加到响应中
        if jump_data:
            response_data["need_jump"] = True
            response_data["jump_data"] = {
                "type": jump_data["type"],
                "id": jump_data["id"],
                "title": jump_data["title"],
                "display_id": jump_data["display_id"]
            }
        else:
            response_data["need_jump"] = False
            response_data["jump_data"] = None

        return response_data
    except Exception as e:
        import traceback
        print(f"[Error] {e}")
        print(f"[Error] Stack trace: {traceback.format_exc()}")
        return {
            "reply": f"抱歉，发生了错误，请稍后再试。",
            "response": f"抱歉，发生了错误，请稍后再试。",
            "success": False,
            "content": f"处理失败：{str(e)}",
        }


@router.get("/history/{session_id}")
async def get_history(session_id: str):
    """
    获取智能助手对话历史记录

    参数:
    - session_id: 会话ID

    返回:
    - history: 历史记录列表
    - session_id: 会话ID
    """
    try:
        session_data = get_session(session_id) or {}
        history = session_data.get("history", [])

        return {
            "session_id": session_id,
            "history": history,
            "message_count": len(history)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── 重置对话状态 ───────────────────────────────────────────────────

@router.post("/reset/{session_id}")
async def reset_state(session_id: str):
    """
    重置对话状态

    用于：
    1. 用户想开始新对话
    2. 对话陷入死循环需要重新开始
    3. 测试时清理状态

    参数:
    - session_id: 会话ID

    返回:
    - success: 是否成功
    - message: 提示信息
    """
    try:
        reset_conversation_state(session_id)
        return {
            "success": True,
            "message": f"会话 {session_id} 的状态已重置，可以开始新的对话"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"重置失败：{str(e)}"
        }


# ─── 获取对话状态 ───────────────────────────────────────────────────

@router.get("/state/{session_id}")
async def get_state(session_id: str):
    """
    获取当前对话状态（调试用）

    返回:
    - state: 当前状态
    - current_task: 当前任务
    - params: 已收集的参数
    - required_params: 还需要的参数
    - retry_count: 重试次数
    - last_error: 最后一次错误
    """
    try:
        conv_state = get_conversation_state(session_id)
        return {
            "success": True,
            "session_id": session_id,
            "state": conv_state.state.value,
            "current_task": conv_state.current_task,
            "current_tool": conv_state.current_tool,
            "params": conv_state.params,
            "required_params": conv_state.required_params,
            "retry_count": conv_state.retry_count,
            "last_error": conv_state.last_error,
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"获取失败：{str(e)}"
        }


# ─── 健康检查 ───────────────────────────────────────────────────────

@router.get("/health")
async def health_check():
    return {
        "success": True,
        "service": "PlanHub AI Assistant (Tool Calling)",
        "model": "qwen-max-latest (DashScope)",
        "tools": ["create_plan", "create_post", "search_plans", "get_user_activity", "check_in_plan"],
        "features": {
            "state_management": True,
            "parameter_validation": True,
            "error_recovery": True,
            "response_caching": True,
            "history_length_limit": 20,
        }
    }
