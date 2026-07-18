"""
Parameter Extractor 节点 - 工具选择 + 参数提取

流程（MCP 版）：
1. 从 MCP server 获取所有可用工具 schema
2. LLM 根据 plan_summary 选择最相关的工具 + 提取参数值
3. 输出 ranked_tools 给 tool_executor

MCP 替代了旧的 Tool RAG：
- 不需要向量库检索，直接拿全部工具 schema
- LLM 看工具描述就能判断该用哪个
- 新增工具零成本（@mcp.tool 即注册即用）
"""
from prompts.parameter_extractor import TOOL_SELECTOR_SYSTEM_PROMPT, TOOL_SELECTOR_PROMPT_TEMPLATE
from src.app.common.llm_factory import extract_text


async def parameter_extractor_node(state) -> dict:
    """Parameter Extractor 节点：MCP 工具发现 + LLM 打分/参数提取"""
    short_term = state.get("short_term_memory", [])
    long_term = state.get("long_term_memory", [])
    def _wm(d: dict) -> dict:
        d.setdefault("short_term_memory", short_term)
        d.setdefault("long_term_memory", long_term)
        return d

    try:
        from app.common.llm_factory import get_llm
        from langchain_core.messages import HumanMessage, SystemMessage
        from src.app.mcp.mcp_client import get_mcp_adapter

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

        # 1. 从 MCP 获取所有可用工具（替代旧的 Tool RAG 检索）
        from ..stream_writer import emit_log
        await emit_log("正在分析需求，选择需要调用的工具...")

        mcp_adapter = await get_mcp_adapter()
        if not mcp_adapter.is_connected:
            print("[DEBUG] parameter_extractor: MCP 未连接，跳过工具选择")
            await emit_log("工具服务未连接，跳过工具调用")
            return _wm({
                "ranked_tools": [],
                "parameter_extraction_status": "mcp_not_connected",
                "execution_trace": [
                    {
                        "node": "parameter_extractor",
                        "status": "skipped",
                        "reason": "MCP 未连接"
                    }
                ]
            })

        # 把所有 MCP tools 转为候选格式
        mcp_tools = mcp_adapter.get_tools_schema()
        candidate_tools = []
        for t in mcp_tools:
            func = t["function"]
            # 从参数 schema 中提取 required 和 optional slots
            params = func.get("parameters", {})
            properties = params.get("properties", {})
            required = params.get("required", [])
            optional = [k for k in properties if k not in required]
            candidate_tools.append({
                "tool_name": func["name"],
                "description": func.get("description", ""),
                "required_slots": required,
                "optional_slots": optional,
            })

        print(f"[DEBUG] parameter_extractor: MCP 提供 {len(candidate_tools)} 个候选工具")
        await emit_log(f"从 {len(candidate_tools)} 个工具中选择最相关的...")

        # 2. LLM 打分排序 + 参数提取
        tools_desc = "\n".join([
            f"- {t['tool_name']}: {t['description']}（需要{t['required_slots']}, 可选{t['optional_slots']}）"
            for t in candidate_tools
        ])

        prompt = TOOL_SELECTOR_PROMPT_TEMPLATE.format(
            plan_summary=plan_summary,
            tools_desc=tools_desc,
        )

        llm = get_llm(temperature=0.3)
        result = await llm.ainvoke([
            SystemMessage(content=TOOL_SELECTOR_SYSTEM_PROMPT),
            HumanMessage(content=prompt)
        ])
        raw = extract_text(result.content) if hasattr(result, "content") else str(result)

        # 打印 LLM 原始输出，方便调试参数提取问题
        print(f"[DEBUG] parameter_extractor: LLM 原始输出:\n{raw}")

        # 打印 MCP 原始 schema，诊断 parameters 结构
        if mcp_tools:
            print(f"[DEBUG] parameter_extractor: MCP 原始 schema 示例 (前2个):")
            for t in mcp_tools[:2]:
                func = t["function"]
                print(f"  - {func['name']}: parameters={func.get('parameters', {})}")

        # 3. 解析 LLM 输出
        ranked_tools = _parse_rerank_output(raw, candidate_tools)
        print(f"[DEBUG] parameter_extractor: 选中 {len(ranked_tools)} 个工具")
        for t in ranked_tools:
            print(f"[DEBUG] parameter_extractor:   {t['tool']} -> params={t['params']}")
            missing = [s for s in t["required_slots"] if not t["params"].get(s)]
            if missing:
                print(f"[WARN] parameter_extractor: {t['tool']} 缺参数: {missing}")

        tool_names = [t["tool"] for t in ranked_tools]
        await emit_log(f"已选择 {len(ranked_tools)} 个工具：{', '.join(tool_names)}")

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
