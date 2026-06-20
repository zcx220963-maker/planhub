"""
统一异常处理
"""

from fastapi import HTTPException, status


class AgentException(Exception):
    """Agent 基础异常"""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class ToolExecutionException(AgentException):
    """工具执行异常"""
    def __init__(self, message: str):
        super().__init__(message, status_code=500)


class LLMException(AgentException):
    """LLM 调用异常"""
    def __init__(self, message: str):
        super().__init__(message, status_code=503)


class VectorStoreException(AgentException):
    """向量存储异常"""
    def __init__(self, message: str):
        super().__init__(message, status_code=500)


def handle_agent_exception(e: AgentException) -> HTTPException:
    """将 Agent 异常转换为 HTTP 异常"""
    return HTTPException(
        status_code=e.status_code,
        detail=e.message
    )
