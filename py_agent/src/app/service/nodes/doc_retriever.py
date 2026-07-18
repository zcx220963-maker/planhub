"""
Doc Retriever 节点 - 用户文档知识检索

与 tool_executor 并行执行（都在 needs_plan_building=True 后触发）

核心设计：
- 用 plan_summary 在用户选中的文档中做 hybrid_search（向量 + BM25 双路召回）
- 双路召回后用 LLM Rerank 精排，提高检索精度
- 输出 doc_data_parts 给 plan_writer 使用

与 RAG 节点的区别：
- RAG 节点面向用户直接提问（需要 HyDE、压缩 → 交互友好）
- doc_retriever 面向计划生成（需要 Rerank → 精度优先）
"""


async def doc_retriever_node(state) -> dict:
    """Doc Retriever 节点：从用户选中的文档中检索相关知识
    
    检索流程：
    1. 双路召回：向量相似度 + BM25 关键词（各取 top-20）
    2. 融合去重，计算加权融合分数
    3. LLM Rerank 精排，返回 top-5
    """
    try:
        plan_summary = state.get("plan_summary", "")
        selected_doc_ids = state.get("selected_doc_ids", [])
        user_id = state.get("user_id", "default")

        print(f"[DEBUG] doc_retriever: plan_summary长度={len(plan_summary)}, "
              f"selected_doc_ids={selected_doc_ids}, user_id={user_id}")

        # 检查前置条件
        if not plan_summary:
            return {
                "doc_data_parts": [],
                "doc_retrieval_status": "no_plan_summary",
                "execution_trace": [
                    {
                        "node": "doc_retriever",
                        "status": "skipped",
                        "reason": "plan_summary 为空"
                    }
                ]
            }

        if not selected_doc_ids:
            return {
                "doc_data_parts": [],
                "doc_retrieval_status": "no_selected_docs",
                "execution_trace": [
                    {
                        "node": "doc_retriever",
                        "status": "skipped",
                        "reason": "用户未选中文档"
                    }
                ]
            }

        # 步骤 1: 双路召回（向量 + BM25）
        from src.app.api.rag import hybrid_search, llm_rerank
        from ..stream_writer import emit_log

        if selected_doc_ids:
            await emit_log(f"正在从 {len(selected_doc_ids)} 篇文档中检索相关知识...")

        docs, retrieval_info = hybrid_search(
            query=plan_summary,
            top_k=10,
            fetch_k=20,
            doc_ids=selected_doc_ids,
            user_id=user_id
        )

        print(f"[DEBUG] doc_retriever: 双路召回 {len(docs)} 个候选")
        if docs:
            await emit_log(f"检索到 {len(docs)} 篇相关文档")

        # 步骤 2: LLM Rerank 精排（如果候选数 > 5）
        rerank_info = {}
        if docs and len(docs) > 5:
            try:
                docs, rerank_info = llm_rerank(
                    question=plan_summary,
                    candidate_docs=docs,
                    top_k=5,
                    temperature=0.1
                )
                print(f"[DEBUG] doc_retriever: LLM Rerank 后剩余 {len(docs)} 个文档")
            except Exception as e:
                print(f"[WARN] doc_retriever: LLM Rerank 失败，使用融合分数: {e}")
                docs = docs[:5]
        elif docs:
            docs = docs[:5]

        if not docs:
            return {
                "doc_data_parts": [],
                "doc_retrieval_status": "no_results",
                "execution_trace": [
                    {
                        "node": "doc_retriever",
                        "status": "no_results",
                        "query": plan_summary[:100],
                        "selected_doc_ids": selected_doc_ids,
                        "retrieval_info": retrieval_info
                    }
                ]
            }

        # 格式化文档片段
        doc_data_parts = []
        for doc in docs:
            doc_name = doc.metadata.get("doc_name", "未知文档")
            chunk_idx = doc.metadata.get("chunk_index", 0)
            score = doc.metadata.get("rerank_score") or doc.metadata.get("final_score", 0)
            content = doc.page_content.strip()

            if content:
                formatted = f"[来源: {doc_name}#{chunk_idx+1}]（相关度: {score:.2f}）\n{content}"
                doc_data_parts.append(formatted)

        print(f"[DEBUG] doc_retriever: 最终检索到 {len(doc_data_parts)} 个文档片段")

        return {
            "doc_data_parts": doc_data_parts,
            "doc_retrieval_status": "success",
            "execution_trace": [
                {
                    "node": "doc_retriever",
                    "status": "success",
                    "query": plan_summary[:100],
                    "results_count": len(doc_data_parts),
                    "selected_doc_ids": selected_doc_ids,
                    "retrieval_info": retrieval_info,
                    "rerank_used": bool(rerank_info),
                    "success": True
                }
            ]
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "doc_data_parts": [],
            "doc_retrieval_status": f"error: {str(e)}",
            "execution_trace": [
                {
                    "node": "doc_retriever",
                    "error": str(e),
                    "success": False
                }
            ]
        }
