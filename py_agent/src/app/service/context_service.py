"""
上下文服务（ContextService）
用于优化对话上下文，减少 Token 消耗
"""

from typing import List, Optional, Dict


class ContextService:
    """
    上下文服务类
    负责构建和优化对话上下文，减少 Token 消耗
    """
    
    def __init__(self):
        pass
    
    def build_context(
        self,
        message: str,
        history: Optional[List[Dict]] = None,
        user_preference: Optional[Dict] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        构建优化后的上下文
        
        Args:
            message: 当前用户消息
            history: 历史对话记录
            user_preference: 用户偏好设置
            system_prompt: 系统提示词
            
        Returns:
            优化后的上下文字符串
        """
        parts = []
        
        if system_prompt:
            parts.append(system_prompt)
        
        if user_preference and isinstance(user_preference, dict):
            pref_lines = []
            for key, value in user_preference.items():
                if value:
                    pref_lines.append(f"- {key}: {value}")
            if pref_lines:
                parts.append("\n【用户偏好】\n" + "\n".join(pref_lines))
        
        if history and isinstance(history, list):
            history_lines = []
            for item in history[-10:]:  # 只保留最近10条
                role = item.get("role", "")
                content = item.get("content", "")
                if role and content:
                    history_lines.append(f"{role}: {content}")
            if history_lines:
                parts.append("\n【对话历史】\n" + "\n".join(history_lines))
        
        return "\n".join(parts)