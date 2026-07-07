"""
Parameter Extractor 节点 - 工具选择 + 参数提取

流程：
1. 用 Tool RAG 从 plan_summary 中检索相关工具
2. LLM 对候选工具打分排序 + 从 plan_summary 中提取参数值
3. 输出 ranked_tools 给 tool_executor

设计思路：
- Tool RAG 召回候选工具（代码做，确定性强）
- LLM 只做打分排序 + 参数提取（难度降低）
- 拆分避免小模型同时"选工具"和"填参数"出错
"""


async def parameter_extractor_node(state) -> dict:
    """Parameter Extractor 节点：Tool RAG 检索工具 + LLM 打分/参数提取"""
    short_term = state.get("short_term_memory", [])
    long_term = state.get("long_term_memory", [])
    def _wm(d: dict) -> dict:
        d.setdefault("short_term_memory", short_term)
        d.setdefault("long_term_memory", long_term)
        return d

    try:
        from app.common.llm_factory import get_llm
        from langchain_core.messages import HumanMessage, SystemMessage
        from src.app.orchestrator.tool_rag import retrieve_relevant_tools

        plan_summary = state.get("plan_summary", "")
        user_id = state.get("user_id")

        print(f"[DEBUG] parameter_extractor: plan_summary={plan_summary[:200]}")

        if not plan_summary:
            return _wm({
                "ranked_tools": [],
                "parameter_extraction_status": "no_plan_summary",
                "execution_trace": [
                    {
                        "node": "parameter_extractor",
                        "status": "skipped",
                        "reason": "plan_summary 为空"
                    }
                ]
            })

        # 1. Tool RAG 检索候选工具（双路召回 + LLM Rerank）
        candidate_tools = await retrieve_relevant_tools(plan_summary, top_k=7)
        print(f"[DEBUG] parameter_extractor: 检索到 {len(candidate_tools)} 个候选工具")

        if not candidate_tools:
            return _wm({
                "ranked_tools": [],
                "parameter_extraction_status": "no_tools_found",
                "execution_trace": [
                    {
                        "node": "parameter_extractor",
                        "status": "no_tools",
                        "reason": "Tool RAG 未检索到相关工具"
                    }
                ]
            })

        # 2. LLM 打分排序 + 参数提取
        tools_desc = "\n".join([
            f"- {t['tool_name']}: 需要{t['required_slots']}, 可选{t['optional_slots']}"
            for t in candidate_tools
        ])

        prompt = f"""你是一个工具选择器。根据计划信息，从候选工具中选择需要调用的工具并提取参数。

【计划信息】
{plan_summary}

【候选工具】
{tools_desc}

请完成两件事：
a. 对每个工具打分 0-10（≥6 分才选，低于6分不选）
b. 从计划信息中按参数要求提取参数值（禁止编造、禁止推测）

输出格式（JSON）：
{{"rankings": [
  {{"tool": "tool_name", "score": 分数, "params": {{"slot名": "值"}}}}
]}}

注意：
- 只输出 JSON
- 没有明确信息的参数不要填
- 城市名、地点名可以从计划信息中提取
"""

        llm = get_llm(temperature=0.3)
        result = await llm.ainvoke([
            SystemMessage(content="你是一个工具选择器，只输出 JSON，不输出其他内容。"),
            HumanMessage(content=prompt)
        ])
        raw = result.content if hasattr(result, "content") else str(result)

        # 3. 解析 LLM 输出
        ranked_tools = _parse_rerank_output(raw, candidate_tools)
        print(f"[DEBUG] parameter_extractor: 选中 {len(ranked_tools)} 个工具")

        return _wm({
            "ranked_tools": ranked_tools,
            "parameter_extraction_status": "success" if ranked_tools else "empty",
            "execution_trace": [
                {
                    "node": "parameter_extractor",
                    "candidate_count": len(candidate_tools),
                    "selected_count": len(ranked_tools),
                    "selected_tools": [t["tool"] for t in ranked_tools],
                    "success": True
                }
            ]
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return _wm({
            "ranked_tools": [],
            "parameter_extraction_status": f"error: {str(e)}",
            "execution_trace": [
                {
                    "node": "parameter_extractor",
                    "error": str(e),
                    "success": False
                }
            ]
        })


def _parse_rerank_output(raw: str, candidate_tools: list) -> list:
    """解析 LLM 的打分排序输出"""
    import json

    try:
        # 提取 JSON
        text = raw.strip()
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return []

        data = json.loads(text[start:end + 1])
        rankings = data.get("rankings", [])

        # 过滤：只保留 ≥ 6 分且在候选列表中的工具
        candidate_names = {t["tool_name"]: t for t in candidate_tools}
        result = []

        for item in rankings:
            tool_name = item.get("tool", "")
            score = item.get("score", 0)
            params = item.get("params", {})

            if score < 6:
                continue
            if tool_name not in candidate_names:
                continue

            tool_info = candidate_names[tool_name]

            # 参数校验：过滤非法 key
            valid_slots = set(tool_info["required_slots"] + tool_info["optional_slots"])
            validated_params = {k: v for k, v in params.items() if k in valid_slots}

            result.append({
                "tool": tool_name,
                "score": score,
                "params": validated_params,
                "required_slots": tool_info["required_slots"],
                "optional_slots": tool_info["optional_slots"],
            })

        return result

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"[WARN] parameter_extractor: 解析 LLM 输出失败: {e}")
        return []
