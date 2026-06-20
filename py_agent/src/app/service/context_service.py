"""
上下文工程服务（简化版）

核心原则：
1. 最小化 Token 消耗
2. 只保留最近对话，不添加额外信息
3. 智能压缩，避免超长上下文

策略：
- 短对话（< 5 轮）：保留完整历史
- 中等对话（5-10 轮）：保留最近 5 轮
- 长对话（> 10 轮）：压缩为摘要 + 最近 3 轮
"""

import re
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ContextService:
    """简化版上下文工程服务"""

    def __init__(self):
        # Token 限制（中文约 1.5 token/字）
        self.max_context_chars = 16000  # 约 10000 token
        self.compression_threshold = 12000  # 约 8000 token 时触发压缩

        # 对话轮数限制
        self.min_history_turns = 3
        self.max_history_turns = 10

    def build_context(self, message: str,
                      history: List[Dict[str, Any]],
                      user_preference: str = "",
                      system_prompt: str = "") -> str:
        """构建优化的上下文（极简版）

        Args:
            message: 用户当前消息
            history: 对话历史
            user_preference: 用户偏好摘要（1-2 句话）
            system_prompt: 系统提示词

        Returns:
            优化后的上下文字符串
        """
        # 1. 组装基础上下文
        context = system_prompt + "\n\n"

        # 2. 添加用户偏好（如果有，只有 1-2 句话）
        if user_preference:
            context += f"用户偏好：{user_preference}\n\n"

        # 3. 智能选择历史对话
        relevant_history = self._select_relevant_history(history, message)

        # 4. 格式化历史
        if relevant_history:
            context += "对话历史：\n"
            for msg in relevant_history:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                if role == "user":
                    context += f"用户: {content}\n"
                elif role == "assistant":
                    context += f"助手: {content}\n"

        # 5. 添加当前消息
        context += f"\n用户: {message}"

        # 6. 检查是否需要压缩
        if len(context) > self.max_context_chars:
            context = self._compress_context(context, relevant_history, message, user_preference, system_prompt)

        return context

    def _select_relevant_history(self, history: List[Dict[str, Any]], current_message: str) -> List[Dict[str, Any]]:
        """智能选择相关历史对话（简化版）

        策略：
        - 如果历史很短（< 10 条），全部保留
        - 如果历史较长，只保留最近 5-10 轮

        Args:
            history: 完整历史
            current_message: 当前消息

        Returns:
            筛选后的历史
        """
        if not history:
            return []

        # 保留最近 N 条消息（10 条 = 5 轮）
        return history[-10:]

    def _compress_context(self, context: str, history: List[Dict[str, Any]],
                          message: str, user_preference: str,
                          system_prompt: str) -> str:
        """压缩上下文（极简版）

        策略：
        1. 保留系统提示
        2. 保留用户偏好
        3. 只保留最近 3 轮对话
        4. 添加摘要标记

        Args:
            context: 原始上下文
            history: 对话历史
            message: 当前消息
            user_preference: 用户偏好
            system_prompt: 系统提示词

        Returns:
            压缩后的上下文
        """
        # 只保留最近 3 轮（6 条消息）
        recent_history = history[-6:] if len(history) > 6 else history

        # 重新组装
        compressed = system_prompt + "\n\n"

        if user_preference:
            compressed += f"用户偏好：{user_preference}\n\n"

        if recent_history:
            compressed += "[对话历史摘要]\n"
            for msg in recent_history:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")[:100]  # 截断每条消息
                if role == "user":
                    compressed += f"用户: {content}\n"
                elif role == "assistant":
                    compressed += f"助手: {content}\n"

        compressed += f"\n用户: {message}"

        return compressed

    def estimate_token_count(self, text: str) -> int:
        """估算 Token 数量

        Args:
            text: 输入文本

        Returns:
            Token 数量
        """
        # 简单估算：中文 1.5 token/字，英文 1.3 token/词
        chinese_chars = len(re.findall(r'[一-鿿]', text))
        english_words = len(re.findall(r'[a-zA-Z]+', text))
        other_chars = len(text) - chinese_chars - sum(len(w) for w in re.findall(r'[a-zA-Z]+', text))

        return int(chinese_chars * 1.5 + english_words * 1.3 + other_chars)

    def should_compress(self, history: List[Dict[str, Any]], message: str) -> bool:
        """判断是否需要压缩

        Args:
            history: 对话历史
            message: 当前消息

        Returns:
            是否需要压缩
        """
        # 估算总长度
        total_chars = len(message)
        for msg in history:
            total_chars += len(msg.get("content", ""))

        return total_chars > self.compression_threshold
