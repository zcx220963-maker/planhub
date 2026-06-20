"""
对话管理路由

提供对话列表、详情查询、删除等功能。
"""

from fastapi import APIRouter, HTTPException
from config import settings
from app.dao.redis_dao import (
    list_conversations,
    get_conversation_count,
    get_conversation_detail,
    clear_session
)

router = APIRouter(prefix="/conversations", tags=["对话管理"])


@router.get("")
async def list_conversations_api(
    user_id: str = None,
    limit: int = 20,
    offset: int = 0,
    module: str = None
):
    """
    获取对话列表

    参数:
    - user_id: 用户ID（可选）
    - limit: 返回数量限制（默认20）
    - offset: 分页偏移量（默认0）
    - module: 模块类型（可选） - chat/assistant/rag

    返回:
    - conversations: 对话列表
    - total: 总对话数
    """
    try:
        print(f"[DEBUG] list_conversations called - user_id: {user_id}, module: {module}, limit: {limit}")
        conversations = list_conversations(user_id, limit, offset, module)
        total = get_conversation_count(user_id, module)
        print(f"[DEBUG] Found {len(conversations)} conversations, total: {total}")

        return {
            "conversations": conversations,
            "total": total,
            "limit": limit,
            "offset": offset,
            "module": module
        }
    except Exception as e:
        print(f"[ERROR] list_conversations failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}")
async def get_conversation(session_id: str):
    """
    获取单个对话详情（完整历史记录）

    参数:
    - session_id: 会话ID

    返回:
    - 完整的对话信息，包含所有历史记录
    """
    try:
        print(f"[DEBUG] get_conversation called - session_id: {session_id}")
        conversation = get_conversation_detail(session_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="对话不存在")

        return conversation
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] get_conversation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{session_id}")
async def delete_conversation(session_id: str):
    """
    删除单个对话

    参数:
    - session_id: 会话ID

    返回:
    - 成功/失败信息
    """
    try:
        print(f"[DEBUG] delete_conversation called - session_id: {session_id}")
        clear_session(session_id)
        return {"message": "对话已删除", "session_id": session_id}
    except Exception as e:
        print(f"[ERROR] delete_conversation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
