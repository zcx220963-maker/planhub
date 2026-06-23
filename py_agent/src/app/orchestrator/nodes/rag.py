"""
RAG节点 - 知识库查询Agent
包装现有的RAG服务
"""


async def rag_node(state) -> dict:
    """RAG节点：知识库查询"""
    try:
        # 检查能力开关
        capabilities = state.get("capabilities", {})
        if isinstance(capabilities, dict):
            enable_rag = capabilities.get("enable_rag", True)
        else:
            enable_rag = getattr(capabilities, "enable_rag", True)

        if not enable_rag:
            return {
                "agent_output": "抱歉，知识库功能已被关闭。如需启用，请在能力开关中打开「知识库」。",
                "execution_trace": [
                    *state.get("execution_trace", []),
                    {
                        "node": "rag",
                        "blocked": True,
                        "reason": "知识库已关闭"
                    }
                ]
            }

        # 使用 app.api.rag 中的 query_rag_internal 函数
        from src.app.api.rag import query_rag_internal

        # 执行查询
        user_input = state.get("user_input", "")
        session_id = state.get("session_id")
        user_id = state.get("user_id", "1")

        result = await query_rag_internal(
            question=user_input,
            user_id=user_id,
            session_id=session_id,
            top_k=3,
            use_rerank=False,
            use_compression=False
        )

        if result and result.get("answer"):
            return {
                "agent_output": result["answer"],
                "tools_called": [
                    *state.get("tools_called", []),
                    "rag_query"
                ],
                "execution_trace": [
                    *state.get("execution_trace", []),
                    {
                        "node": "rag",
                        "query": user_input[:100],
                        "results_count": len(result.get("sources", [])),
                        "success": True
                    }
                ]
            }
        else:
            return {
                "agent_output": "知识库中暂无相关文档，请先上传文档后再进行查询。",
                "execution_trace": [
                    *state.get("execution_trace", []),
                    {
                        "node": "rag",
                        "query": user_input[:100],
                        "results_count": 0,
                        "success": True
                    }
                ]
            }

    except Exception as e:
        return {
            "agent_output": f"抱歉，知识库查询失败：{str(e)}",
            "error": str(e),
            "execution_trace": [
                *state.get("execution_trace", []),
                {
                    "node": "rag",
                    "error": str(e),
                    "success": False
                }
            ]
        }
