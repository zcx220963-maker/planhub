"""
内存桥接器
同步LangGraph状态与Redis内存系统
保留现有MemoryService，不修改老代码

注意：由于 redis_dao 使用同步 Redis，这里使用同步操作
"""

import json
from typing import Optional, Dict, Any
from datetime import datetime


class MemoryBridge:
    """LangGraph状态与Redis内存的桥接器"""

    def __init__(self):
        # 使用同步 Redis 客户端
        from src.app.dao.redis_dao import redis_client
        self.redis = redis_client
        self.short_term_ttl = 7200  # 2小时过期

    def _get(self, key: str) -> Optional[str]:
        """同步获取值"""
        try:
            return self.redis.get(key)
        except Exception:
            return None

    def _set(self, key: str, value: str, ex: int = None) -> bool:
        """同步设置值"""
        try:
            self.redis.set(key, value, ex=ex)
            return True
        except Exception:
            return False

    def _lpush(self, key: str, value: str) -> bool:
        """同步 LPUSH"""
        try:
            pipe = self.redis.pipeline()
            pipe.lpush(key, value)
            pipe.ltrim(key, 0, 19)  # 保留最近 10 轮
            pipe.expire(key, self.short_term_ttl)
            pipe.execute()
            return True
        except Exception:
            return False

    def _lrange(self, key: str, start: int, end: int) -> list:
        """同步 LRANGE"""
        try:
            return self.redis.lrange(key, start, end)
        except Exception:
            return []

    def save_conversation(self, session_id: str, user_id: str, module: str, history: list) -> bool:
        """
        保存会话到Redis（用于前端会话列表显示）

        Args:
            session_id: 会话ID
            user_id: 用户ID
            module: 模块名称（如 orchestrator, chat 等）
            history: 对话历史列表
        """
        try:
            key = f"session:{session_id}"
            now = datetime.now().isoformat()

            conversation = {
                "session_id": session_id,
                "user_id": user_id,
                "module": module,
                "history": history,
                "created_at": now,
                "updated_at": now
            }

            self.redis.set(key, json.dumps(conversation, ensure_ascii=False), ex=86400 * 7)  # 7天过期
            return True
        except Exception as e:
            print(f"[ERROR] save_conversation failed: {e}")
            return False

    def get_conversation(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话详情"""
        try:
            key = f"session:{session_id}"
            data = self.redis.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception:
            return None

    async def load_memory(self, session_id: str, user_id: Optional[str]) -> Dict[str, Any]:
        """
        从Redis加载记忆（异步接口，同步实现）

        Returns:
            {
                "short_term_memory": [...],
                "user_preference": "...",
                "working_memory": {...}
            }
        """
        try:
            # 获取短期记忆
            key = f"memory:short:{session_id}"
            messages = self._lrange(key, 0, -1)
            short_term = [json.loads(m) for m in messages] if messages else []

            # 获取用户偏好
            pref_key = f"memory:pref:{user_id or 'anonymous'}"
            user_pref = self._get(pref_key) or ""

            # 获取工作记忆
            work_key = f"memory:working:{session_id}"
            work_data = self._get(work_key)
            working = json.loads(work_data) if work_data else {}

            return {
                "short_term_memory": short_term,
                "user_preference": user_pref,
                "working_memory": working
            }
        except Exception as e:
            return {
                "short_term_memory": [],
                "user_preference": None,
                "working_memory": None
            }

    async def save_memory(
        self,
        session_id: str,
        user_id: Optional[str],
        chat_history: list,
        user_preference: Optional[str] = None,
        working_memory: Optional[Dict[str, Any]] = None
    ):
        """
        保存记忆到Redis（异步接口，同步实现）
        """
        try:
            # 保存短期记忆
            if chat_history:
                key = f"memory:short:{session_id}"
                # chat_history 可能是 list of dict，需要转换
                for item in chat_history:
                    if isinstance(item, dict):
                        self._lpush(key, json.dumps(item, ensure_ascii=False))

            # 保存用户偏好
            if user_preference and user_id:
                pref_key = f"memory:pref:{user_id}"
                self._set(pref_key, user_preference)

            # 保存工作记忆
            if working_memory:
                work_key = f"memory:working:{session_id}"
                self._set(work_key, json.dumps(working_memory, ensure_ascii=False), ex=3600)

        except Exception as e:
            pass
