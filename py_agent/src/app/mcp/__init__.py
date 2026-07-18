"""
MCP (Model Context Protocol) 集成模块

提供两个入口：
1. mcp_server.py  — FastMCP 服务器，注册所有外部 API 为 MCP tools
2. mcp_client.py  — MCP 客户端适配器，供 LangGraph agent 调用 MCP tools

启动方式：
- 独立模式：python -m src.app.mcp.mcp_server  (HTTP/SSE on port 8001)
- 开发模式：在 main.py 中直接 mount MCP server
"""
