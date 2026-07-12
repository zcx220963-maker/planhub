"""
Extract Plan Title节点 - 从计划文本中提取标题
使用 LLM 准确提炼，不再靠正则猜。
"""
from prompts.extract_plan_title import EXTRACT_TITLE_PROMPT, EXTRACT_TITLE_RETRY_PROMPT


async def extract_plan_title_node(state) -> dict:
    """Extract Plan Title节点：用 LLM 从计划文本中提取标题"""

    print(f"[DEBUG] extract_plan_title: entering node")

    plan_text = state.get("plan_text_cache", "")
    plan_type = state.get("plan_type", "learning")

    print(f"[DEBUG] extract_plan_title: plan_text length={len(plan_text)}, plan_type={plan_type}")

    type_names = {
        "learning": "学习计划",
        "health": "健康计划",
        "travel": "旅行计划",
        "work": "工作计划",
        "finance": "财务计划",
    }

    title = ""

    try:
        from app.common.llm_factory import get_llm
        from langchain_core.messages import HumanMessage

        prompt = EXTRACT_TITLE_PROMPT.format(plan_text=plan_text[:1500])

        llm = get_llm(temperature=0.3)
        result = llm.bind(max_tokens=30).invoke([HumanMessage(content=prompt)])
        raw = result.content if hasattr(result, 'content') else str(result)
        # 清理：取第一行，去除标点和空白
        raw = raw.strip().split("\n")[0]
        title = raw.strip().strip('"').strip("'").strip("：:").strip()

        if len(title) > 20:
            title = title[:20]

        print(f"[DEBUG] extract_plan_title: LLM提取标题='{title}'")

    except Exception as e:
        print(f"[WARN] extract_plan_title: LLM提取失败: {e}，使用回退方案")

    # 兜底：LLM 返回空或太短时，用 plan_summary 让 LLM 再试一次
    if not title or len(title) < 2:
        plan_summary = state.get("plan_summary", "")
        if plan_summary:
            retry_prompt = EXTRACT_TITLE_RETRY_PROMPT.format(plan_summary=plan_summary[:300])
            try:
                result = llm.invoke([HumanMessage(content=retry_prompt)])
                title = result.content.strip().split("\n")[0].strip().strip('"').strip("'").strip("：:").strip()
            except Exception:
                pass
        if not title or len(title) < 2:
            title = type_names.get(plan_type, "我的计划")

    return {
        "plan_title": title,
        "plan_text_cache": plan_text,
        "execution_trace": [
            {
                "node": "extract_plan_title",
                "plan_type": plan_type,
                "extracted_title": title,
                "title_length": len(title),
                "success": True,
            }
        ]
    }
