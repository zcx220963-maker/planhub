"""
Plan Writer 节点 - 最终计划文本生成

核心功能：
1. 合并所有数据源：tool_data_parts + doc_data_parts + plan_summary
2. 注入短期记忆（最近对话）和长期记忆（用户偏好）
3. LLM 生成最终计划文本
4. 构建 plan_metadata（数据来源标注，供前端展示）

prompt 约束：
- 严禁编造具体数据（温度、价格、时间等）
- API 数据为空时基于通用知识生成框架
- [参考] 标记的信息以建议口吻呈现
- 字数 500-2000
"""


async def plan_writer_node(state) -> dict:
    """Plan Writer 节点：综合所有数据生成最终计划，支持逐 token 流式
    
    记忆注入：
    - 短期记忆：最近 10 轮对话（从 Redis 加载）
    - 长期记忆：用户相关的事实/偏好（从 Chroma 语义检索）
    - 记忆由 memory_load_for_writer 节点预先加载到 State
    """

    try:
        from app.common.llm_factory import get_llm
        from langchain_core.messages import HumanMessage, SystemMessage

        plan_summary = state.get("plan_summary", "")
        tool_data_parts = state.get("tool_data_parts", [])
        doc_data_parts = state.get("doc_data_parts", [])

        short_term_memory = state.get("short_term_memory", [])
        long_term_memory = state.get("long_term_memory", [])
        print(f"[DEBUG] plan_writer: plan_summary长度={len(plan_summary)}, "
              f"tool_data={len(tool_data_parts)}条, doc_data={len(doc_data_parts)}条, "
              f"短期记忆={len(short_term_memory)}条, 长期记忆={len(long_term_memory)}条")

        if not plan_summary:
            return {
                "plan_text_cache": "",
                "plan_generated": False,
                "plan_metadata": {},
                "execution_trace": [
                    {
                        "node": "plan_writer",
                        "status": "failed",
                        "reason": "plan_summary 为空"
                    }
                ]
            }

        all_data_parts = list(tool_data_parts)
        if doc_data_parts:
            all_data_parts.append("【知识库参考】\n" + "\n\n".join(doc_data_parts))

        from datetime import datetime
        current_date = datetime.now().strftime("%Y-%m-%d")

        tool_data_text = "\n\n".join(all_data_parts) if all_data_parts else "暂无外部数据"

        system_prompt = """你是一个专业的计划生成助手。请根据用户的需求摘要和提供的数据，生成一份完整的执行计划。

规则：
1. 严禁编造具体数据（温度、价格、时间等），只能使用提供的数据
2. 如果 API 数据为空，基于通用知识生成框架性计划
3. 用 [参考] 标记的信息以建议口吻呈现
4. 计划要有可执行性，包含具体的步骤和时间安排
5. 必须完整覆盖计划要求的所有天数/阶段，不能中途截断，确保每天都有详细安排
6. 用中文输出，格式清晰，使用简单的分段和缩进，不要使用 markdown 格式（如 #、**、* 等符号）
7. 不要使用任何表情符号或特殊符号（如 🎒、📅、🚄、🌧️、🍜、🏯、🍽️、🚌、☔️、🍵、🏮、🌙、🎭、🌊、🌿、🌸、🌺、🌻、🌹、🍃、🍂、🍁、🌾、🍀、🌵、🌴、🌲、🌳、🌱、🌷、🌼、🌺、🍄、🐾、🦋、🐦、🐬、🐠、🦀、🐙、🦐、🐚、🐳、🐋、🦈、🐟、🐡、🦑、🐙、🦀、🦐、🦞、🦐、🦀、🦐、🦞、🦀、🦐、🦞、🦀、🦐、🦞）
8. 【用户长期记忆】仅供参考，只有与当前计划直接相关时才使用；如果不相关则完全忽略，不要强行加入计划中
9. 输出要完整，不要省略任何天数的内容"""

        user_prompt_parts = [f"【当前日期】{current_date}", f"【计划信息】\n{plan_summary}"]

        if long_term_memory:
            lt_text = "\n".join([f"{i+1}. {mem}" for i, mem in enumerate(long_term_memory)])
            user_prompt_parts.append(f"【用户长期记忆 - 偏好与习惯】\n{lt_text}\n（以上仅供参考，仅在与当前计划相关时使用，不相关则忽略）")

        if short_term_memory:
            st_lines = []
            for msg in short_term_memory[-8:]:
                role = "用户" if hasattr(msg, 'type') and msg.type == 'human' else "助手"
                content = msg.content if hasattr(msg, 'content') else str(msg)
                st_lines.append(f"{role}: {content[:150]}")
            st_text = "\n".join(st_lines)
            user_prompt_parts.append(f"【最近对话背景】\n{st_text}")

        user_prompt_parts.append(f"【API 数据】\n{tool_data_text}")
        user_prompt_parts.append("请根据以上信息，生成一份完整的执行计划：")

        user_prompt = "\n\n".join(user_prompt_parts)

        from ..stream_writer import emit_token, is_streaming

        llm = get_llm(temperature=0.7)

        plan_text = ""
        streaming = is_streaming()
        if streaming:
            async for chunk in llm.astream([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]):
                content = chunk.content if hasattr(chunk, 'content') else str(chunk)
                if content:
                    plan_text += content
                    emit_token(content)
            plan_text = plan_text.strip()
        else:
            result = await llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])
            plan_text = result.content if hasattr(result, "content") else str(result)
            plan_text = plan_text.strip()

        if not plan_text or len(plan_text) < 50:
            plan_text = _build_fallback_plan(plan_summary)
            if streaming:
                emit_token("\n\n" + plan_text)
            print(f"[DEBUG] plan_writer: LLM 输出为空，使用兜底计划")

        plan_metadata = {
            "generated_at": datetime.now().isoformat(),
            "data_sources": {
                "tool_count": len(tool_data_parts),
                "doc_count": len(doc_data_parts),
                "tools_used": _extract_tool_names(tool_data_parts),
            },
            "memory_used": {
                "short_term_count": len(short_term_memory),
                "long_term_count": len(long_term_memory),
            },
            "plan_summary": plan_summary[:200],
            "plan_length": len(plan_text),
        }

        print(f"[DEBUG] plan_writer: 计划生成完成，长度={len(plan_text)}")

        return {
            "plan_text_cache": plan_text,
            "plan_generated": True,
            "plan_metadata": plan_metadata,
            "execution_trace": [
                {
                    "node": "plan_writer",
                    "status": "success",
                    "plan_length": len(plan_text),
                    "data_sources_count": len(all_data_parts),
                    "short_term_used": len(short_term_memory) > 0,
                    "long_term_used": len(long_term_memory) > 0,
                    "success": True
                }
            ]
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "plan_text_cache": _build_fallback_plan(state.get("plan_summary", "")),
            "plan_generated": True,
            "plan_metadata": {"error": str(e), "fallback": True},
            "execution_trace": [
                {
                    "node": "plan_writer",
                    "error": str(e),
                    "success": False,
                    "fallback": True
                }
            ]
        }


def _build_fallback_plan(plan_summary: str) -> str:
    """兜底计划生成（当 LLM 输出为空时）"""
    if not plan_summary:
        return "暂无足够信息生成计划，请提供更多需求细节。"

    return f"""# 执行计划

## 目标
{plan_summary}

## 执行步骤
1. **准备阶段**：明确目标，收集必要资源
2. **执行阶段**：按照计划逐步推进
3. **复盘阶段**：定期回顾进度，调整计划

## 注意事项
- 根据实际情况灵活调整
- 建议设置阶段性里程碑
- 定期打卡记录进度

---
*此计划基于您提供的信息生成，建议根据实际情况调整细节。*"""


def _extract_tool_names(tool_data_parts: list) -> list:
    """从工具数据中提取工具名"""
    tools = []
    for part in tool_data_parts:
        if part.startswith("[") and "]" in part:
            name = part[1:part.index("]")]
            tools.append(name)
    return tools
