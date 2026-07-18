"""
MCP Client Adapter — 供 LangGraph agent 调用 MCP Tools

用法：
    from src.app.mcp.mcp_client import MCPToolAdapter

    # 初始化（连接到 MCP server）
    adapter = MCPToolAdapter(server_url="http://127.0.0.1:8001/sse")
    await adapter.connect()

    # 列出所有可用工具
    tools = adapter.get_tools_schema()  # 返回 OpenAI function-calling 格式

    # 调用单个工具
    result = await adapter.call_tool("search_books", {"query": "Python", "limit": 3})

架构：
  Agent (LLM) → 看到 tools schema → 决定调用 tool → MCPToolAdapter.call_tool() → MCP Server → 返回结果
"""

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MCPToolAdapter:
    """
    MCP 工具适配器 — 桥接 LangGraph agent 和 MCP server

    支持两种连接模式：
    1. SSE 模式：连接远程 MCP server（独立进程运行）
    2. 直连模式：直接引用 MCP server 实例（同进程，当前默认）
    """

    def __init__(self, server_url: str = "http://127.0.0.1:8001/sse"):
        self.server_url = server_url
        self._client = None
        self._tools: Dict[str, dict] = {}  # name -> {description, parameters}
        self._connected = False

    async def connect(self):
        """连接到 MCP server（或使用直连模式）"""
        try:
            # 先尝试直连（同进程，更稳定）
            from src.app.mcp.mcp_server import mcp as mcp_server
            self._client = mcp_server._mcp_server if hasattr(mcp_server, '_mcp_server') else mcp_server
            self._tools = await self._fetch_tools_local(mcp_server)
            self._connected = True
            logger.info(f"[MCP] 直连模式：已加载 {len(self._tools)} 个工具")
        except Exception as e:
            logger.warning(f"[MCP] 直连失败，回退到 SSE 模式: {e}")
            await self._connect_sse()

    async def _fetch_tools_local(self, mcp_server) -> Dict[str, dict]:
        """从本地 FastMCP 实例获取工具列表"""
        tools = {}
        try:
            mcp_tools = await mcp_server.list_tools()
            for tool_obj in mcp_tools:
                name = getattr(tool_obj, 'name', '')
                tools[name] = {
                    "description": getattr(tool_obj, 'description', '') or '',
                    "parameters": getattr(tool_obj, 'parameters', {}) or {},
                }
        except Exception as e:
            logger.warning(f"[MCP] 本地工具获取失败: {e}")
        return tools

    async def _connect_sse(self):
        """通过 SSE 连接到远程 MCP server"""
        try:
            from mcp.client.streamable_http import streamablehttp_client
            from mcp import ClientSession

            # 使用 streamable HTTP 客户端
            async with streamablehttp_client(self.server_url) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tool_list = await session.list_tools()
                    for tool in tool_list.tools:
                        self._tools[tool.name] = {
                            "description": tool.description or "",
                            "parameters": getattr(tool, 'parameters', {}) or {},
                        }
            self._connected = True
            logger.info(f"[MCP] SSE 模式：已加载 {len(self._tools)} 个工具")
        except Exception as e:
            logger.error(f"[MCP] SSE 连接失败: {e}")
            self._connected = False

    def get_tools_schema(self) -> List[dict]:
        """
        返回 OpenAI function-calling 格式的 tools schema

        可直接传给 LLM 的 tools 参数
        """
        tools = []
        for name, info in self._tools.items():
            tools.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": info["description"],
                    "parameters": info["parameters"],
                }
            })
        return tools

    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """
        调用 MCP tool

        返回格式：
        {"success": true, "data": ...} 或 {"success": false, "error": "..."}
        """
        if not self._connected:
            return {"success": False, "error": "MCP 未连接"}

        if tool_name not in self._tools:
            return {"success": False, "error": f"未知工具: {tool_name}"}

        try:
            # 直连模式：通过 FastMCP 的 call_tool
            from src.app.mcp.mcp_server import mcp as mcp_server
            result = await mcp_server.call_tool(tool_name, arguments)
            # FastMCP 返回 ToolResult，content[0].text 是 JSON 字符串
            if hasattr(result, 'content') and result.content:
                text_content = result.content[0]
                text = getattr(text_content, 'text', str(text_content))
                try:
                    data = json.loads(text)
                except (json.JSONDecodeError, TypeError):
                    data = text
                return {"success": True, "data": data}

            # 回退：通过 client 调用
            return await self._call_tool_remote(tool_name, arguments)

        except Exception as e:
            logger.error(f"[MCP] 调用 {tool_name} 失败: {e}")
            return {"success": False, "error": str(e)}

    async def _call_tool_remote(self, tool_name: str, arguments: dict) -> dict:
        """通过远程 MCP session 调用工具"""
        try:
            from mcp.client.streamable_http import streamablehttp_client
            from mcp import ClientSession

            async with streamablehttp_client(self.server_url) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments)

                    # 解析结果
                    content = result.content
                    if content and len(content) > 0:
                        text_content = content[0]
                        if hasattr(text_content, 'text'):
                            try:
                                data = json.loads(text_content.text)
                                return {"success": True, "data": data}
                            except json.JSONDecodeError:
                                return {"success": True, "data": text_content.text}

                    return {"success": True, "data": str(result)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def tool_names(self) -> List[str]:
        return list(self._tools.keys())


# ─── 全局单例 ──────────────────────────────────────────────────────────

_mcp_adapter: Optional[MCPToolAdapter] = None


async def get_mcp_adapter() -> MCPToolAdapter:
    """获取全局 MCP adapter 单例"""
    global _mcp_adapter
    if _mcp_adapter is None:
        from config import settings
        url = settings.MCP_SERVER_URL
        _mcp_adapter = MCPToolAdapter(server_url=url)
        await _mcp_adapter.connect()
    return _mcp_adapter


async def call_mcp_tool(tool_name: str, arguments: dict) -> dict:
    """便捷函数：调用 MCP tool"""
    adapter = await get_mcp_adapter()
    return await adapter.call_tool(tool_name, arguments)
