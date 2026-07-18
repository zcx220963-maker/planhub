"""
Plan → Mermaid 转换器
将计划文本自动转换为 Mermaid 时间轴/流程图

策略：
1. 解析计划文本中的"第X天/阶段/步骤"结构
2. 生成 Mermaid timeline 或 graph 语法
3. 如果解析失败，生成简单的 graph 兜底
"""


def plan_text_to_mermaid(plan_text: str, plan_summary: str = "") -> str:
    """将计划文本转换为 Mermaid 语法

    优先尝试 timeline（时间轴），如果提取不到时间结构则用 graph（流程图）
    """
    if not plan_text:
        return ""

    # 尝试提取"第X天/阶段"结构 → timeline
    timeline = _try_extract_timeline(plan_text)
    if timeline:
        return timeline

    # 尝试提取步骤/阶段 → graph
    graph = _try_extract_graph(plan_text)
    if graph:
        return graph

    # 兜底：简单 graph
    return _build_fallback_graph(plan_text, plan_summary)


def _try_extract_timeline(plan_text: str) -> str | None:
    """尝试提取 Day1/Day2/第一天/第二天 结构，生成 Mermaid timeline"""
    import re

    lines = plan_text.split('\n')

    # 匹配 "第X天" 或 "Day X" 或 "第X天：标题" 格式
    day_pattern = re.compile(
        r'^(?:第[一二三四五六七八九十\d]+天|Day\s*\d+|阶段\s*\d+)\s*[：:.\-]?\s*(.*)$',
        re.MULTILINE
    )

    sections = []
    current_title = ""
    current_items = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        match = day_pattern.match(line)
        if match:
            # 保存上一个 section
            if current_title:
                sections.append((current_title, current_items))
            current_title = match.group(1) or line
            current_items = []
        elif current_title and (line.startswith('-') or line.startswith('•') or line.startswith('◦')):
            # 列表项 → 归入当前 section
            item = line.lstrip('- •◦').strip()
            if item:
                current_items.append(item[:60])  # 截断过长文本
        elif current_title and len(line) > 5:
            # 非列表但属于当前 section 的描述
            current_items.append(line[:60])

    # 保存最后一个 section
    if current_title:
        sections.append((current_title, current_items))

    if len(sections) < 2:
        return None

    # 生成 Mermaid timeline
    mermaid_lines = ["timeline", f"    title {sections[0][0] if sections else '计划时间轴'}"]

    for title, items in sections:
        section_title = title[:30] if title else "阶段"
        if items:
            # timeline 语法：title : item1 : item2
            items_text = " : ".join(items[:3])  # 每段最多 3 项
            mermaid_lines.append(f"    {section_title} : {items_text}")
        else:
            mermaid_lines.append(f"    {section_title}")

    return "\n".join(mermaid_lines)


def _try_extract_graph(plan_text: str) -> str | None:
    """尝试提取步骤/阶段结构，生成 Mermaid graph"""
    import re

    lines = plan_text.split('\n')

    # 匹配数字编号步骤：1. 2. 或 一、二、
    step_pattern = re.compile(
        r'^(?:\d+[.、．]|[一二三四五六七八九十]+[、.])\s*(.+)$'
    )

    steps = []
    for line in lines:
        line = line.strip()
        match = step_pattern.match(line)
        if match:
            step_text = match.group(1).strip()[:40]
            steps.append(step_text)

    if len(steps) < 2:
        return None

    # 生成 Mermaid graph（流程图）
    mermaid_lines = ["graph LR"]

    for i, step in enumerate(steps):
        node_id = f"S{i}"
        # 节点文本用引号包裹
        mermaid_lines.append(f'    {node_id}["{step}"]')
        if i > 0:
            prev_id = f"S{i-1}"
            mermaid_lines.append(f"    {prev_id} --> {node_id}")

    return "\n".join(mermaid_lines)


def _build_fallback_graph(plan_text: str, plan_summary: str = "") -> str:
    """兜底：生成简单的 graph"""
    # 取前几行非空内容作为节点
    lines = [l.strip() for l in plan_text.split('\n') if l.strip() and len(l.strip()) > 5]

    if not lines:
        return ""

    # 取前 5 行作为节点
    nodes = lines[:5]

    mermaid_lines = ["graph LR", '    Start["计划开始"]']

    for i, node in enumerate(nodes):
        node_id = f"N{i}"
        text = node[:30]
        mermaid_lines.append(f'    {node_id}["{text}"]')
        if i == 0:
            mermaid_lines.append(f"    Start --> {node_id}")
        else:
            mermaid_lines.append(f"    N{i-1} --> {node_id}")

    mermaid_lines.append(f'    {f"N{len(nodes)-1}" if nodes else "Start"} --> End["完成"]')

    return "\n".join(mermaid_lines)
