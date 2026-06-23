"""
结构化输出模式定义
使用Pydantic确保LLM输出的稳定性和类型安全
"""

from pydantic import BaseModel, Field
from typing import Literal


class IntentResult(BaseModel):
    """意图分类结果 - Supervisor的结构化输出"""
    intent: Literal[
        "learning", "health", "travel", "work", "finance",
        "plan_creation", "rag", "assistant", "chat", "clarify"
    ] = Field(description="用户意图类别")
    confidence: float = Field(ge=0, le=1, description="置信度")


class CapabilityFlags(BaseModel):
    """能力开关标志 - 前端控制Agent能力边界"""
    enable_rag: bool = Field(default=True, description="是否启用知识库")
    enable_mcp_tools: bool = Field(default=True, description="是否启用MCP工具")
    enable_plan_mode: bool = Field(default=True, description="是否启用计划模式")

    class Config:
        # 允许从字典创建
        json_schema_extra = {
            "example": {
                "enable_rag": True,
                "enable_mcp_tools": True,
                "enable_plan_mode": True
            }
        }
