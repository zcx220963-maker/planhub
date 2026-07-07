"""
长期记忆服务（Long-Term Memory Service）

核心功能：
1. 存储：每轮对话结束后，用 LLM 从对话中提取值得记住的事实，存入 Chroma 向量库
2. 检索：每轮请求时，用用户原话语义检索 top-K 条相关记忆，注入 State

架构：
- 每个用户有独立的 Chroma collection: ltm_{user_id}
- 记忆以文本形式存储，附带 metadata（timestamp, session_id, category）
- 检索使用向量相似度（embedding）
"""

import json
import logging
import os
from datetime import datetime
from typing import List, Optional

from langchain_chroma import Chroma
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

# LLM 提取长期记忆的 Prompt
EXTRACT_MEMORY_PROMPT = """从以下对话中提取值得长期记住的用户事实（偏好、习惯、目标、重要事件）。
只提取明确的、有价值的信息，不要推测。如果没有值得记住的，返回空列表。

输出格式（JSON 数组）：
[{{"fact": "用户喜欢简洁的回答", "category": "preference"}}]

分类说明：
- preference: 用户偏好（如喜欢简洁/详细回答）
- habit: 用户习惯（如每天打卡、经常制定学习计划）
- goal: 用户目标（如正在准备考研、想减肥）
- event: 重要事件（如完成了某个计划、去了某地旅行）
- knowledge: 用户提到的专业知识/技能

对话：
用户: {user_input}
助手: {assistant_response}

只输出 JSON 数组，不要其他内容："""


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
    ) -> List[str]:
        """
        从对话中提取长期记忆并存储到 Chroma

        Args:
            user_id: 用户 ID
            session_id: 会话 ID
            user_input: 用户输入
            assistant_response: 助手回复

        Returns:
            提取到的记忆列表
        """
        if not user_id or user_id == "anonymous":
            return []

        try:
            from app.common.llm_factory import get_llm
            from langchain_core.messages import HumanMessage

            llm = get_llm(temperature=0.1)
            prompt = EXTRACT_MEMORY_PROMPT.format(
                user_input=user_input[:500],
                assistant_response=assistant_response[:500],
            )

            result = await llm.ainvoke([HumanMessage(content=prompt)])
            raw = result.content if hasattr(result, "content") else str(result)
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
                if not fact or len(fact) < 3:
                    continue

                doc_id = f"mem_{session_id}_{now}_{i}"
                documents.append(Document(
                    page_content=fact,
                    metadata={
                        "timestamp": now,
                        "session_id": session_id,
                        "category": category,
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

    def _parse_memories(self, raw: str) -> List[dict]:
        """解析 LLM 输出的 JSON 记忆列表"""
        try:
            # 尝试直接解析
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

        Args:
            user_id: 用户 ID
            query: 用户原始输入（用于语义检索）
            top_k: 返回记忆数量

        Returns:
            记忆文本列表
        """
        if not user_id or user_id == "anonymous" or not query:
            return []

        try:
            store = self._get_collection(user_id)
            results = store.similarity_search(query, k=top_k)

            memories = []
            for doc in results:
                content = doc.page_content.strip()
                if content:
                    # 可选：附带分类信息
                    category = doc.metadata.get("category", "")
                    if category:
                        memories.append(f"[{category}] {content}")
                    else:
                        memories.append(content)

            logger.debug(f"长期记忆检索: user_id={user_id}, query={query[:50]}, 命中 {len(memories)} 条")
            return memories

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
