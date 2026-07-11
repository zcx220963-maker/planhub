"""
对话管理路由

提供对话列表、详情查询、删除等功能。
"""

import logging
import sys

from fastapi import APIRouter, HTTPException
from config import settings
from app.dao.redis_dao import (
    list_conversations,
    get_conversation_count,
    get_conversation_detail,
    clear_session
)

router = APIRouter(prefix="/conversations", tags=["对话管理"])
logger = logging.getLogger(__name__)


def _safe_log(msg: str):
    """安全日志输出，避免 Windows GBK 控制台编码错误（如 emoji 👋🌟）"""
    try:
        print(msg)
    except (UnicodeEncodeError, OSError):
        try:
            sys.stderr.write(msg.encode("ascii", errors="replace").decode("ascii") + "\n")
        except Exception:
            pass


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
        logger.debug("list_conversations called - user_id: %s, module: %s, limit: %s", user_id, module, limit)
        conversations = list_conversations(user_id, limit, offset, module)
        total = get_conversation_count(user_id, module)
        logger.debug("Found %d conversations, total: %d", len(conversations), total)

        return {
            "conversations": conversations,
            "total": total,
            "limit": limit,
            "offset": offset,
            "module": module
        }
    except Exception as e:
        logger.error("list_conversations failed: %s", e)
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
        logger.debug("get_conversation called - session_id: %s", session_id)
        conversation = get_conversation_detail(session_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="对话不存在")

        return conversation
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_conversation failed: %s", e)
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
        logger.debug("delete_conversation called - session_id: %s", session_id)
        clear_session(session_id)
        return {"message": "对话已删除", "session_id": session_id}
    except Exception as e:
        logger.error("delete_conversation failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
