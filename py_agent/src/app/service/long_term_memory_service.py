"""
长期记忆服务（Long-Term Memory Service）

核心功能：
1. 存储：每轮对话结束后，用 LLM 从对话中提取值得记住的事实，存入 Chroma 向量库
2. 检索：每轮请求时，用用户原话语义检索 top-K 条相关记忆，注入 State
3. 画像：每累积 50 条记忆，自动提炼用户画像

架构：
- 每个用户有独立的 Chroma collection: ltm_{user_id}
- 记忆以文本形式存储，附带 metadata（timestamp, session_id, category, importance）
- 检索使用向量相似度（embedding）
- 画像存储在 Redis（key: memory:profile:{user_id}, TTL 7天）
"""

import json
import logging
import os
import re
from datetime import datetime
from typing import List, Optional

from langchain_chroma import Chroma
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

# LLM 提取长期记忆的 Prompt（增强版：importance + pattern + conversation_context）
EXTRACT_MEMORY_PROMPT = """从以下对话中提取值得长期记住的用户事实（偏好、习惯、目标、重要事件）。
只提取明确的、有价值的信息，不要推测。如果没有值得记住的，返回空列表。

输出格式（JSON 数组）：
[{{"fact": "用户喜欢简洁的回答", "category": "preference", "importance": "high"}}]

分类说明：
- preference: 用户偏好（如喜欢简洁/详细回答）
- habit: 用户习惯（如每天打卡、经常制定学习计划）
- goal: 用户目标（如正在准备考研、想减肥）
- event: 重要事件（如完成了某个计划、去了某地旅行）
- knowledge: 用户提到的专业知识/技能

重要性分级：
- high: 核心偏好、重要目标、关键事件
- medium: 一般习惯、普通偏好
- low: 轻微提及、可能临时起意

{context_section}

对话：
用户: {user_input}
助手: {assistant_response}

只输出 JSON 数组，不要其他内容："""


SYNTHESIZE_PROFILE_PROMPT = """根据以下用户记忆，提炼一段简洁的用户画像（200字以内），用于后续对话时注入System Prompt让AI更了解用户。
画像应包含：用户的核心目标、行为模式、偏好。

记忆列表：
{memories}

只输出画像文本，不要其他内容："""


class LongTermMemoryService:
    """长期记忆服务：基于 Chroma 向量库的语义记忆存储与检索"""

    def __init__(self, chroma_path: str = "./chroma_db"):
        self.chroma_path = chroma_path
        self._collections = {}  # {user_id: Chroma instance}
        os.makedirs(chroma_path, exist_ok=True)

    def _get_embeddings(self):
        """获取 embedding 模型"""
        from app.common.llm_factory import get_embeddings
        return get_embeddings()

    def _get_collection(self, user_id: str) -> Chroma:
        """获取或创建用户的长期记忆集合"""
        if user_id in self._collections:
            return self._collections[user_id]

        collection_name = f"ltm_{user_id}"
        try:
            store = Chroma(
                collection_name=collection_name,
                persist_directory=self.chroma_path,
                embedding_function=self._get_embeddings(),
            )
            self._collections[user_id] = store
            logger.info(f"长期记忆集合已创建: user_id={user_id}, collection={collection_name}")
            return store
        except Exception as e:
            logger.error(f"长期记忆集合创建失败: {e}")
            # 重试一次
            store = Chroma(
                collection_name=collection_name,
                persist_directory=self.chroma_path,
                embedding_function=self._get_embeddings(),
            )
            self._collections[user_id] = store
            return store

    async def extract_and_store(
        self,
        user_id: str,
        session_id: str,
        user_input: str,
        assistant_response: str,
        conversation_context: str = "",
    ) -> List[str]:
        """
        从对话中提取长期记忆并存储到 Chroma

        Args:
            user_id: 用户 ID
            session_id: 会话 ID
            user_input: 用户输入
            assistant_response: 助手回复
            conversation_context: 对话上下文（最近几轮），帮助 LLM 判断信息重要性

        Returns:
            提取到的记忆列表
        """
        if not user_id or user_id == "anonymous":
            return []

        try:
            from app.common.llm_factory import get_llm, extract_text
            from langchain_core.messages import HumanMessage

            llm = get_llm(temperature=0.1)

            context_section = ""
            if conversation_context:
                context_section = f"\n最近对话上下文：\n{conversation_context}\n"

            prompt = EXTRACT_MEMORY_PROMPT.format(
                user_input=user_input[:500],
                assistant_response=assistant_response[:500],
                context_section=context_section,
            )

            result = await llm.ainvoke([HumanMessage(content=prompt)])
            # 使用 extract_text 处理 thinking 模型返回的结构化内容
            raw = extract_text(result.content) if hasattr(result, "content") else str(result)
            raw = raw.strip()

            # 解析 JSON
            memories = self._parse_memories(raw)
            if not memories:
                return []

            # 存入 Chroma
            store = self._get_collection(user_id)
            documents = []
            ids = []
            now = datetime.now().isoformat()

            for i, mem in enumerate(memories):
                fact = mem.get("fact", "").strip()
                category = mem.get("category", "general").strip()
                importance = mem.get("importance", "medium").strip()
                if not fact or len(fact) < 3:
                    continue

                doc_id = f"mem_{session_id}_{now}_{i}"
                documents.append(Document(
                    page_content=fact,
                    metadata={
                        "timestamp": now,
                        "session_id": session_id,
                        "category": category,
                        "importance": importance,
                        "user_id": user_id,
                    },
                ))
                ids.append(doc_id)

            if documents:
                store.add_documents(documents=documents, ids=ids)
                logger.info(f"长期记忆已存储: user_id={user_id}, 共 {len(documents)} 条")

            return [d.page_content for d in documents]

        except Exception as e:
            logger.error(f"长期记忆提取失败: {e}")
            return []

    async def synthesize_profile(self, user_id: str) -> Optional[str]:
        """定期提炼用户画像，存入 Redis"""
        try:
            from app.common.llm_factory import get_llm, extract_text
            from langchain_core.messages import HumanMessage
            from app.dao.redis_dao import redis_client

            all_memories = self.get_all_memories(user_id)
            if len(all_memories) < 5:
                return None

            recent = all_memories[-50:]
            prompt = SYNTHESIZE_PROFILE_PROMPT.format(
                memories="\n".join(f"- {m}" for m in recent)
            )

            llm = get_llm(temperature=0.3)
            result = await llm.ainvoke([HumanMessage(content=prompt)])
            profile = extract_text(result.content).strip() if hasattr(result, "content") else str(result).strip()

            if profile:
                # 存入 Redis，TTL 7天
                redis_client.set(f"memory:profile:{user_id}", profile, ex=86400 * 7)
                logger.info(f"用户画像已更新: user_id={user_id}")
                return profile
            return None
        except Exception as e:
            logger.error(f"画像提炼失败: {e}")
            return None

    def _parse_memories(self, raw: str) -> List[dict]:
        """解析 LLM 输出的 JSON 记忆列表"""
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "memories" in data:
                return data["memories"]
        except json.JSONDecodeError:
            pass

        # 尝试从文本中提取 JSON 数组
        try:
            start = raw.find("[")
            end = raw.rfind("]")
            if start != -1 and end != -1 and end > start:
                data = json.loads(raw[start:end + 1])
                if isinstance(data, list):
                    return data
        except (json.JSONDecodeError, ValueError):
            pass

        # 尝试逐行解析
        memories = []
        for line in raw.strip().split("\n"):
            line = line.strip().strip(",").strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    item = json.loads(line)
                    if "fact" in item:
                        memories.append(item)
                except json.JSONDecodeError:
                    continue

        return memories

    async def retrieve_memories(
        self,
        user_id: str,
        query: str,
        top_k: int = 5,
    ) -> List[str]:
        """
        按用户原话语义检索 top-K 条长期记忆

        增强：先取 Redis 画像 → 注入为第一条 → 语义检索 → 去重 → 加标签
        """
        if not user_id or user_id == "anonymous" or not query:
            return []

        try:
            from app.dao.redis_dao import redis_client

            results = []

            # 1. 先取用户画像（Redis）
            profile = redis_client.get(f"memory:profile:{user_id}")
            if profile:
                results.append(f"[画像] {profile}")

            # 2. 语义检索
            store = self._get_collection(user_id)
            search_results = store.similarity_search(query, k=top_k)

            for doc in search_results:
                content = doc.page_content.strip()
                if not content:
                    continue
                # 去重
                if content in results:
                    continue
                # 加标签
                category = doc.metadata.get("category", "")
                importance = doc.metadata.get("importance", "")
                if category and importance:
                    results.append(f"[{category}|{importance}] {content}")
                elif category:
                    results.append(f"[{category}] {content}")
                else:
                    results.append(content)

            return results

        except Exception as e:
            logger.error(f"长期记忆检索失败: {e}")
            return []

    def get_all_memories(self, user_id: str) -> List[str]:
        """获取用户的所有长期记忆（用于调试）"""
        try:
            store = self._get_collection(user_id)
            result = store.get()
            if result and "documents" in result:
                return [doc for doc in result["documents"]]
            return []
        except Exception as e:
            logger.error(f"获取所有长期记忆失败: {e}")
            return []

    def clear_user_memories(self, user_id: str) -> bool:
        """清除用户的所有长期记忆"""
        try:
            store = self._get_collection(user_id)
            store.delete_collection()
            if user_id in self._collections:
                del self._collections[user_id]
            logger.info(f"长期记忆已清除: user_id={user_id}")
            return True
        except Exception as e:
            logger.error(f"清除长期记忆失败: {e}")
            return False


# 全局单例
_ltm_service: Optional[LongTermMemoryService] = None


def get_long_term_memory_service() -> LongTermMemoryService:
    """获取长期记忆服务单例"""
    global _ltm_service
    if _ltm_service is None:
        from config import settings
        _ltm_service = LongTermMemoryService(chroma_path=settings.CHROMA_DB_PATH)
    return _ltm_service
