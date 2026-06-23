"""
Extract Plan Title节点 - 从计划文本中提取标题

策略：
1. 从第一行提取标题（去除 markdown 标记）
2. 如果第一行不合适，根据计划类型生成默认标题
3. 标题最多50字符
"""

import re


async def extract_plan_title_node(state) -> dict:
    """Extract Plan Title节点：从计划文本中提取标题"""
    
    print(f"[DEBUG] extract_plan_title: entering node")
    
    plan_text = state.get("plan_text_cache", "")
    plan_type = state.get("plan_type", "learning")
    
    print(f"[DEBUG] extract_plan_title: plan_text length={len(plan_text)}, plan_type={plan_type}")
    
    # 1. 尝试从第一行提取标题
    lines = plan_text.split("\n")
    title = ""
    
    for line in lines:
        line = line.strip()
        # 跳过空行、markdown标题标记、分隔线
        if not line:
            continue
        if line.startswith("#"):
            # 去除 markdown 标题标记
            line = line.lstrip("#").strip()
        if line.startswith("---") or line.startswith("==="):
            continue
        if line.startswith("-") or line.startswith("*"):
            continue
        
        # 找到第一个有效行作为标题
        if len(line) > 5:
            title = line[:50]  # 最多50字符
            break
    
    # 2. 如果没有找到有效标题，根据计划类型生成默认标题
    if not title or title == "":
        type_names = {
            "learning": "学习计划",
            "health": "健康计划",
            "travel": "旅行计划",
            "work": "工作计划",
            "finance": "财务计划"
        }
        title = type_names.get(plan_type, "计划")
    
    # 3. 清理标题（去除特殊字符）
    title = re.sub(r'[【】\[\]《》]', '', title)
    title = title.strip()
    
    # 4. 确保标题不为空
    if not title:
        title = "计划"
    
    return {
        "plan_title": title,
        "plan_text_cache": plan_text,  # 保持缓存
        "execution_trace": [
            *state.get("execution_trace", []),
            {
                "node": "extract_plan_title",
                "plan_type": plan_type,
                "extracted_title": title,
                "title_length": len(title),
                "success": True
            }
        ]
    }