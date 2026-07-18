"""
Plan HTML Writer 节点 - 用户确认后生成杂志风 HTML 预览页面

设计思路：
- plan_writer 只输出文本计划（流式），用户先审阅
- 用户确认后，plan_html_writer 才将文本计划转换为杂志风 HTML
- HTML 内容必须与已确认的文本计划匹配（不能凭空添加内容）
- 图片使用 picsum.photos / unsplash 占位图服务
- 生成后保存为独立 .html 文件，返回 preview_url 给前端 iframe 渲染
"""

from prompts.plan_writer import PLAN_WRITER_SYSTEM_PROMPT


async def plan_html_writer_node(state) -> dict:
    """Plan HTML Writer 节点：将已确认的文本计划转换为杂志风 HTML 页面

    触发时机：用户确认创建计划后（route_after_plan_confirmation 路由）
    输入：plan_text_cache（已确认的文本计划）
    输出：preview_url（iframe 加载的 HTML 页面 URL）
    """

    try:
        from app.common.llm_factory import get_llm
        from langchain_core.messages import HumanMessage, SystemMessage
        from src.app.common.llm_factory import extract_text

        plan_text = state.get("plan_text_cache", "")
        plan_summary = state.get("plan_summary", "")
        tool_data_parts = state.get("tool_data_parts", [])
        doc_data_parts = state.get("doc_data_parts", [])

        print(f"[DEBUG] plan_html_writer: plan_text长度={len(plan_text)}, "
              f"tool_data={len(tool_data_parts)}条, doc_data={len(doc_data_parts)}条")

        if not plan_text or len(plan_text) < 50:
            print(f"[WARN] plan_html_writer: 计划文本为空或太短，跳过 HTML 生成")
            return {
                "preview_url": None,
                "plan_id": None,
                "execution_trace": [
                    {
                        "node": "plan_html_writer",
                        "status": "skipped",
                        "reason": "plan_text 为空或太短",
                        "success": False
                    }
                ]
            }

        # 构建系统提示词（专门用于 HTML 生成，强调与文本计划匹配）
        html_system_prompt = _build_html_system_prompt()

        # 构建用户提示词（注入文本计划 + 数据源）
        user_prompt = _build_html_user_prompt(plan_text, plan_summary, tool_data_parts, doc_data_parts)

        from ..stream_writer import emit_token, flush_buffer, emit_log, is_streaming, reset_streaming_complete, emit_streaming_complete, send_ws_message

        await emit_log("正在将计划转换为杂志风 HTML 页面...")

        # 重置流式状态（plan_writer 已经用过流式了）
        reset_streaming_complete()

        llm = get_llm(temperature=0.7)
        html_output = ""
        streaming = is_streaming()

        if streaming:
            async for chunk in llm.astream([
                SystemMessage(content=html_system_prompt),
                HumanMessage(content=user_prompt)
            ]):
                content = chunk.content if hasattr(chunk, 'content') else str(chunk)
                text = extract_text(content) if content is not None else ""
                if text:
                    html_output += text
                    # HTML 不输出到聊天窗口，只累积
            html_output = html_output.strip()
            await flush_buffer()
            await emit_streaming_complete()
        else:
            result = await llm.ainvoke([
                SystemMessage(content=html_system_prompt),
                HumanMessage(content=user_prompt)
            ])
            html_output = extract_text(result.content) if hasattr(result, "content") else str(result)
            html_output = html_output.strip()

        if not html_output or len(html_output) < 100:
            print(f"[WARN] plan_html_writer: HTML 输出为空，跳过")
            return {
                "preview_url": None,
                "plan_id": None,
                "execution_trace": [
                    {
                        "node": "plan_html_writer",
                        "status": "failed",
                        "reason": "HTML 输出为空",
                        "success": False
                    }
                ]
            }

        # 提取 HTML 代码块并保存
        preview_url = None
        plan_id = None
        filepath = None
        try:
            from ..plan_html_generator import generate_plan_html, get_preview_url
            session_id = state.get("session_id", "")

            # 先持久化到计划库获取 plan_id
            from ..plan_store import save_plan, update_plan
            _title = plan_summary.strip().split('\n')[0][:60] if plan_summary else "AI 生成计划"
            if len(_title) > 60:
                _title = _title[:57] + "..."
            _saved = await save_plan(
                title=_title,
                description=plan_summary[:500] if plan_summary else "",
                category="PERSONAL",
                plan_text=plan_text[:5000],
                html_path="",
                session_id=session_id,
                user_id=state.get("user_id"),
            )
            plan_id = _saved.get("id")

            # 生成 HTML 文件
            filepath = generate_plan_html(html_output, plan_summary, session_id, plan_id=plan_id)
            preview_url = get_preview_url(filepath)
            if preview_url:
                await emit_log(f"杂志风 HTML 页面已生成，正在加载预览...")
                print(f"[DEBUG] plan_html_writer: HTML 预览页面已生成: {preview_url}")

            # 更新计划的 html_path
            if plan_id and filepath:
                await update_plan(plan_id, html_path=filepath)
                print(f"[DEBUG] plan_html_writer: 计划已持久化到计划库, plan_id={plan_id}")

            # 通知前端打开预览面板（不经过聊天窗口）
            if preview_url:
                await send_ws_message({
                    "type": "html_preview_ready",
                    "preview_url": preview_url,
                    "plan_id": plan_id,
                })
        except Exception as e:
            print(f"[WARN] plan_html_writer: HTML 保存/持久化失败（非关键）: {e}")

        return {
            "preview_url": preview_url,
            "plan_id": plan_id,
            "html_generated": True,
            "execution_trace": [
                {
                    "node": "plan_html_writer",
                    "status": "success",
                    "html_length": len(html_output),
                    "preview_url": preview_url,
                    "plan_id": plan_id,
                    "success": True
                }
            ]
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "preview_url": None,
            "plan_id": None,
            "execution_trace": [
                {
                    "node": "plan_html_writer",
                    "error": str(e),
                    "success": False
                }
            ]
        }


def _build_html_system_prompt() -> str:
    """构建 HTML 生成的系统提示词

    核心要求：
    1. HTML 内容必须严格基于提供的文本计划
    2. 不能凭空添加文本中没有的信息
    3. 图片使用占位图服务
    4. 杂志风设计，美观易读
    5. 内容要详细、丰富、有信息量
    """
    return """你是一位专业的计划设计师和 Web 前端开发专家。
你的任务是将用户已确认的文本计划，转换为一份精美、详细的杂志风 HTML 页面。

【核心原则：内容必须匹配文本计划】
- HTML 页面的所有内容必须严格基于提供的文本计划
- 不能凭空添加文本中没有的信息
- 文本计划的每一个要点都必须在 HTML 中有对应的详细展示
- 将文本计划中的内容**展开细化**：具体的数值、步骤、建议、注意事项等都必须完整体现
- 图片作为装饰性配图，使用占位图服务即可

【详细度要求】
- 文本计划中提到的每一个数据（BMI、体重、天数、次数等）都必须体现在 HTML 中
- 文本计划中提到的每一个建议/步骤都要**详细展开**，写出具体内容
- 如果文本计划有阶段划分，每个阶段都要有独立、完整的展示
- 不要省略或简化文本计划中的任何内容
- HTML 页面总内容应丰富饱满，能独立作为一份完整的计划文档阅读

【HTML 页面设计要求】
生成一个完整、独立的 HTML 文件，所有 CSS 必须内联在 <head> 的 <style> 标签中（不允许外部引用）。

设计规范：
1. Hero 封面区：
   - 大标题（从计划标题提取）+ 副标题
   - 元信息：生成日期、关键指标概览
   - 素净典雅的配色：顶部使用柔和浅色背景（如 #f8f7f4 米白 / #faf9f6 象牙白 / #f0f4f8 浅灰蓝），配深灰色文字（#2d2d2d / #333）
   - 可用极淡的装饰性元素（如细线分隔、小圆点），不要大面积浓艳色块
   - 整体风格：留白多、文字清晰、杂志感，不要花哨

2. 概览区：
   - 以卡片或列表形式展示计划的核心要点
   - 左侧彩色竖线 + 圆点装饰

3. 详细卡片区（按章节/阶段/天划分，每部分一个卡片）：
   - 左侧彩色徽章（不同部分用不同颜色主题循环）
   - 子标题用主题色标注
   - 列表项用圆点装饰
   - 段落文字灰色阅读友好
   - 每个卡片内展开详细的具体内容

4. 图片使用（必须与内容匹配）：
   - 每个主要部分插入 1 张与**该部分文字内容直接相关**的图片
   - 从段落中提取的关键词**必须翻译成英文**
   - 使用 picsum 的 seed 模式（同一个英文关键词始终返回同一张图）：
     URL 格式：https://picsum.photos/seed/{英文关键词}/800/400
     示例：https://picsum.photos/seed/nanjing/800/400
     多个关键词组合：https://picsum.photos/seed/nanjing-food/800/400
   - 关键词示例对照：鸡胸肉→chicken、南京→nanjing、西湖→west-lake、灵隐寺→temple、杭帮菜→hangzhou-food
   - 禁止所有段落使用同一张图（每个段落用不同关键词）
   - 图片需有圆角、阴影，且自适应宽度

5. 排版原则：
   - 大量留白，呼吸感
   - 圆角卡片（border-radius: 12-16px）
   - 微阴影（box-shadow）
   - 字体层级分明（标题 20-32px，正文 14-15px）
   - 颜色主题统一但有变化

6. 响应式设计：
   - 使用 Flexbox/Grid 布局
   - 内边距 padding: 20-32px
   - max-width: 760px 居中

7. 技术约束：
   - 只使用 HTML + 内联 CSS（不使用外部 CSS/JS 框架）
   - 不使用 JavaScript（纯静态展示）
   - 图片全部使用在线占位图服务

【输出格式】
- 最终输出必须是一个完整的 HTML 代码块
- 格式：```html
...完整 HTML 代码...
```
- 代码块前面可以用一句话总结计划亮点
- 禁止使用表情符号
"""


def _build_html_user_prompt(plan_text: str, plan_summary: str, tool_data_parts: list, doc_data_parts: list) -> str:
    """构建 HTML 生成的用户提示词"""
    from datetime import datetime
    parts = []

    parts.append("【任务】将以下已确认的文本计划转换为杂志风 HTML 页面。")
    parts.append("HTML 内容必须严格基于文本计划，不能添加计划中不存在的信息。\n")

    # 注入当前日期，避免 LLM 编造日期
    current_date = datetime.now().strftime("%Y年%m月%d日")
    parts.append(f"【当前日期】{current_date}（页面中的生成日期必须使用此日期，禁止编造）\n")

    if plan_summary:
        parts.append(f"【计划概要】\n{plan_summary}\n")

    parts.append(f"【完整文本计划】\n{plan_text}\n")

    if tool_data_parts:
        parts.append("【API 参考数据】（可用于丰富页面中的具体数据展示）")
        for part in tool_data_parts[:5]:  # 限制数量避免超长
            parts.append(part[:500])
        parts.append("")

    if doc_data_parts:
        parts.append("【知识库参考】（可用于补充背景信息）")
        for part in doc_data_parts[:3]:  # 限制数量
            parts.append(part[:500])
        parts.append("")

    parts.append("请根据以上文本计划，生成完整的杂志风 HTML 页面：")
    return "\n".join(parts)
