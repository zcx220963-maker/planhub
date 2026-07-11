"""
RAG节点 - 知识库查询Agent
包装现有的RAG服务

核心改进：
1. 只在用户选中的文档中查询（selected_doc_ids）
2. 如果知识库查不到相关内容，设置 rag_fallback_to_chat=True
3. 不再返回"知识库中暂无相关文档"，而是让 chat 节点处理
"""


async def rag_node(state) -> dict:
    """RAG节点：知识库查询（只在选中文档中查询，查不到则 fallback 到 chat）"""
    # 记忆透传辅助
    short_term = state.get("short_term_memory", [])
    long_term = state.get("long_term_memory", [])
    def _wm(d: dict) -> dict:
        d.setdefault("short_term_memory", short_term)
        d.setdefault("long_term_memory", long_term)
        return d

    try:
        # 检查能力开关
        capabilities = state.get("capabilities", {})
        if isinstance(capabilities, dict):
            enable_rag = capabilities.get("enable_rag", True)
        else:
            enable_rag = getattr(capabilities, "enable_rag", True)

        if not enable_rag:
            return _wm({
                "agent_output": "抱歉，知识库功能已被关闭。如需启用，请在能力开关中打开「知识库」。",
                "execution_trace": [
                    {
                        "node": "rag",
                        "blocked": True,
                        "reason": "知识库已关闭"
                    }
                ]
            })

        # 获取用户选中的文档ID
        selected_doc_ids = state.get("selected_doc_ids", [])
        
        # 重要：如果没有选中文档，直接 fallback 到 chat
        if not selected_doc_ids:
            print(f"[DEBUG] rag_node: No selected documents, fallback to chat")
            return _wm({
                "rag_fallback_to_chat": True,
                "execution_trace": [
                    {
                        "node": "rag",
                        "no_selected_docs": True,
                        "fallback_to_chat": True,
                        "reason": "用户未选中任何文档，知识库查询跳过"
                    }
                ]
            })

        # 使用 app.api.rag 中的 query_rag_internal 函数
        from src.app.api.rag import query_rag_internal

        # 执行查询（只在选中文档中）
        user_input = state.get("user_input", "")
        session_id = state.get("session_id")
        user_id = state.get("user_id", "1")

        result = await query_rag_internal(
            question=user_input,
            user_id=user_id,
            session_id=session_id,
            top_k=5,  # 增加返回文档数，确保相关内容不被遗漏
            use_rerank=False,
            use_compression=False,
            doc_ids=selected_doc_ids  # 限制在选中文档中查询
        )

        if result and result.get("answer"):
            # 检查回答是否是"未找到"类的空回答
            answer = result["answer"].strip()
            no_result_keywords = [
                "在知识库中未找到相关信息",
                "知识库中暂无文档",
                "未找到相关文档",
                "没有找到相关内容",
                "抱歉，没有找到",
            ]
            is_no_result = any(kw in answer for kw in no_result_keywords)
            
            if is_no_result:
                # 知识库查不到，设置 fallback 标记，让 chat 节点处理
                print(f"[DEBUG] rag_node: Answer is no-result type, fallback to chat")
                return _wm({
                    "rag_fallback_to_chat": True,
                    "execution_trace": [
                        {
                            "node": "rag",
                            "query": user_input[:100],
                            "selected_doc_ids": selected_doc_ids,
                            "results_count": len(result.get("sources", [])),
                            "fallback_to_chat": True,
                            "reason": "知识库回答为'未找到相关信息'，fallback 到 chat"
                        }
                    ]
                })

            return _wm({
                "intent": "rag",
                "agent_output": result["answer"],
                "tools_called": [
                    *state.get("tools_called", []),
                    "rag_query"
                ],
                "execution_trace": [
                    {
                        "node": "rag",
                        "query": user_input[:100],
                        "results_count": len(result.get("sources", [])),
                        "selected_doc_ids": selected_doc_ids,
                        "success": True
                    }
                ]
            })

        else:
            # 知识库查不到，设置 fallback 标记，让 chat 节点处理
            print(f"[DEBUG] rag_node: No results in selected docs, fallback to chat")
            return _wm({
                "rag_fallback_to_chat": True,
                "execution_trace": [
                    {
                        "node": "rag",
                        "query": user_input[:100],
                        "selected_doc_ids": selected_doc_ids,
                        "results_count": 0,
                        "fallback_to_chat": True,
                        "reason": "知识库未找到相关内容，fallback 到 chat"
                    }
                ]
            })

    except Exception as e:
        # 异常情况也 fallback 到 chat
        print(f"[DEBUG] rag_node: Exception {e}, fallback to chat")
        return _wm({
            "rag_fallback_to_chat": True,
            "error": str(e),
            "execution_trace": [
                {
                    "node": "rag",
                    "error": str(e),
                    "fallback_to_chat": True,
                    "reason": f"知识库查询异常: {str(e)}，fallback 到 chat"
                }
            ]
        })
