"""
记忆系统服务（简化版）

核心原则：
1. 上下文里只放最精华的信息，减少 Token 消耗
2. 详细记忆按需检索，不预加载到上下文
3. 摘要极简（1-2 句话），不是完整历史

三层记忆架构：
- 短期记忆：最近 5-10 轮对话（每次都传，消耗 Token）
- 用户偏好：1-2 句话摘要（每次都传，消耗少量 Token）
- 工作记忆：当前任务状态（按需使用，不预加载）
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class MemoryService:
    """简化版记忆系统服务"""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.short_term_ttl = 7200  # 对话历史 2 小时过期

    # ─── 短期记忆（对话历史）────────────────────────────────
    # 注意：这是唯一会每次都传给 LLM 的记忆

    async def save_short_term(self, session_id: str, message: Dict[str, Any]) -> None:
        """保存对话历史"""
        try:
            key = f"memory:short:{session_id}"
            message_json = json.dumps(message, ensure_ascii=False)

            pipe = self.redis.pipeline()
            pipe.lpush(key, message_json)
            pipe.ltrim(key, 0, 19)  # 只保留最近 10 轮（20 条消息）
            pipe.expire(key, self.short_term_ttl)
            await pipe.execute()
        except Exception as e:
            logger.error(f"保存对话历史失败: {e}")

    async def get_short_term(self, session_id: str) -> List[Dict[str, Any]]:
        """获取对话历史"""
        try:
            key = f"memory:short:{session_id}"
            messages = await self.redis.lrange(key, 0, -1)

            if not messages:
                return []

            result = [json.loads(m) for m in messages]
            result.reverse()
            return result
        except Exception as e:
            logger.error(f"获取对话历史失败: {e}")
            return []

    # ─── 用户偏好（摘要，极简）────────────────────────────────
    # 每次只传 1-2 句话摘要，减少 Token 消耗

    async def save_user_preference(self, user_id: str, preference_summary: str) -> None:
        """保存用户偏好摘要（只存 1-2 句话）

        Args:
            user_id: 用户 ID
            preference_summary: 极简摘要，如 "喜欢简洁回答，关注健康"
        """
        try:
            key = f"memory:pref:{user_id}"
            await self.redis.set(key, preference_summary)
        except Exception as e:
            logger.error(f"保存用户偏好失败: {e}")

    async def get_user_preference(self, user_id: str) -> str:
        """获取用户偏好摘要

        Returns:
            偏好摘要字符串，如 "喜欢简洁回答，关注健康"
        """
        try:
            key = f"memory:pref:{user_id}"
            data = await self.redis.get(key)
            return data.decode() if data else ""
        except Exception as e:
            logger.error(f"获取用户偏好失败: {e}")
            return ""

    async def update_user_preference(self, user_id: str, chat_history: List[Dict]) -> None:
        """从对话历史中提取用户偏好并保存（极简版）

        只提取关键偏好，生成 1-2 句话摘要

        Args:
            user_id: 用户 ID
            chat_history: 对话历史
        """
        if not chat_history:
            return

        # 简单提取：统计用户常提到的关键词
        preferences = []

        # 检查是否有明确偏好
        full_text = " ".join([msg.get("content", "") for msg in chat_history if msg.get("role") == "user"])

        # 简单关键词匹配
        if "简洁" in full_text or "简短" in full_text:
            preferences.append("喜欢简洁回答")
        if "详细" in full_text or "详细一点" in full_text:
            preferences.append("喜欢详细解释")
        if "健康" in full_text or "运动" in full_text:
            preferences.append("关注健康")
        if "打卡" in full_text:
            preferences.append("使用打卡功能")
        if "计划" in full_text:
            preferences.append("使用计划管理")

        if preferences:
            summary = "，".join(preferences[:3])  # 最多 3 条
            await self.save_user_preference(user_id, summary)

    # ─── 工作记忆（按需使用）─────────────────────────────────
    # 不预加载到上下文，只有需要时才查询

    async def save_working(self, session_id: str, task_info: Dict[str, Any]) -> None:
        """保存当前任务状态（临时）"""
        try:
            key = f"memory:working:{session_id}"
            await self.redis.setex(key, 3600, json.dumps(task_info, ensure_ascii=False))
        except Exception as e:
            logger.error(f"保存工作记忆失败: {e}")

    async def get_working(self, session_id: str) -> Dict[str, Any]:
        """获取当前任务状态（按需调用）"""
        try:
            key = f"memory:working:{session_id}"
            data = await self.redis.get(key)
            return json.loads(data) if data else {}
        except Exception as e:
            logger.error(f"获取工作记忆失败: {e}")
            return {}

    # ─── 构建上下文（核心方法）───────────────────────────────
    # 这是唯一会传给 LLM 的方法，必须控制 Token 消耗

    async def build_context_summary(self, session_id: str, user_id: str = None) -> str:
        """构建极简上下文摘要（传给 LLM）

        只包含：
        1. 用户偏好摘要（1-2 句话）
        2. 不包含完整对话历史！

        Args:
            session_id: 会话 ID
            user_id: 用户 ID

        Returns:
            极简摘要字符串
        """
        parts = []

        # 只添加用户偏好（1-2 句话）
        if user_id:
            preference = await self.get_user_preference(user_id)
            if preference:
                parts.append(f"用户偏好：{preference}")

        return "\n".join(parts)

    # ─── 清理方法 ───────────────────────────────────────────

    async def clear_session(self, session_id: str) -> None:
        """清理会话的所有记忆"""
        try:
            pipe = self.redis.pipeline()
            pipe.delete(f"memory:short:{session_id}")
            pipe.delete(f"memory:working:{session_id}")
            await pipe.execute()
        except Exception as e:
            logger.error(f"清理会话记忆失败: {e}")
