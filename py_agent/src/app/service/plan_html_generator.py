"""
Plan HTML Generator - 将 LLM 生成的 HTML 代码块提取并保存为独立文件

架构参考：yu-ai-code-mother 项目的 iframe 预览方案
- LLM 直接生成完整的自包含 HTML 文件（CSS 内联 + 在线占位图）
- 后端提取 ```html 代码块，保存到静态文件目录
- 前端通过 <iframe src="previewUrl"> 展示真实页面

与 yu-ai-code-mother 的区别：
- 本项目 LLM 输出的是旅行计划手册（杂志风）
- 图片使用 picsum.photos / unsplash 占位图服务
- 后端只负责提取和保存，不做模板拼接
"""

import os
import re
from datetime import datetime
from typing import Optional

# 静态文件输出目录
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "plan_previews")


def _ensure_output_dir():
    """确保输出目录存在"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def _sanitize_filename(text: str, max_len: int = 40) -> str:
    """从计划标题生成安全的文件名"""
    text = re.sub(r'[#*`\[\]]', '', text)
    text = re.sub(r'[^\w一-鿿\s-]', '', text)
    text = text.strip()[:max_len].strip()
    text = re.sub(r'\s+', '_', text)
    return text or "plan"


def extract_html_code(raw_content: str) -> Optional[str]:
    """从 LLM 输出中提取 ```html 代码块

    策略（参考 yu-ai-code-mother 的 HtmlCodeParser）：
    1. 优先匹配 ```html ... ``` 代码块
    2. 如果没有代码块标记，检查整个内容是否以 <!DOCTYPE 或 <html 开头
    3. 兜底：将整个内容作为 HTML 返回
    """
    # 策略 1: 提取 ```html 代码块
    pattern = re.compile(r'```html\s*\n([\s\S]*?)```', re.IGNORECASE)
    match = pattern.search(raw_content)
    if match:
        return match.group(1).strip()

    # 策略 2: 提取 ``` 代码块（不带 html 标记）
    pattern2 = re.compile(r'```\s*\n([\s\S]*?)```')
    match2 = pattern2.search(raw_content)
    if match2:
        content = match2.group(1).strip()
        if content.lower().startswith(('<!doctype', '<html', '<head', '<body')):
            return content

    # 策略 3: 整个内容就是 HTML
    stripped = raw_content.strip()
    if stripped.lower().startswith(('<!doctype', '<html', '<head', '<body')):
        return stripped

    return None


def generate_plan_html(plan_text: str, plan_summary: str = "", session_id: str = "", plan_id: int = None) -> Optional[str]:
    """提取 LLM 生成的 HTML 代码并保存为独立文件

    Args:
        plan_text: LLM 原始输出（包含 ```html 代码块）
        plan_summary: 计划摘要（用于兜底文件名）
        session_id: 会话 ID（用于文件名）
        plan_id: 计划库 ID（优先用于文件名）

    Returns:
        HTML 文件路径，如果提取失败返回 None
    """
    # 提取 HTML 代码
    html_code = extract_html_code(plan_text)
    if not html_code:
        print(f"[HTML Generator] 未找到 HTML 代码块，跳过")
        return None

    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # 尝试从 HTML 中提取 <title> 作为文件名
    title_match = re.search(r'<title>(.*?)</title>', html_code, re.IGNORECASE)
    if title_match:
        safe_title = _sanitize_html_filename(title_match.group(1))
    else:
        safe_title = _sanitize_html_filename(plan_summary[:40]) if plan_summary else "plan"

    if plan_id:
        filename = f"plan{plan_id}_{safe_title}_{timestamp}.html"
    elif session_id:
        filename = f"{session_id[:8]}_{safe_title}_{timestamp}.html"
    else:
        filename = f"{safe_title}_{timestamp}.html"

    _ensure_output_dir()
    filepath = os.path.join(OUTPUT_DIR, filename)

    # 保存 HTML 文件
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html_code)

    print(f"[HTML Generator] 保存计划页面: {filepath} ({len(html_code)} bytes)")
    return filepath


def _sanitize_html_filename(text: str, max_len: int = 40) -> str:
    """从 HTML 标题生成安全的文件名"""
    text = re.sub(r'<[^>]+>', '', text)  # 移除 HTML 标签
    text = re.sub(r'[^\w一-鿿\s-]', '', text)
    text = text.strip()[:max_len].strip()
    text = re.sub(r'\s+', '_', text)
    return text or "plan"


def get_preview_url(filepath: str) -> Optional[str]:
    """从文件路径生成预览 URL

    Args:
        filepath: HTML 文件的绝对路径

    Returns:
        相对 URL 路径，如 /orchestrator/plan-preview/xxx.html
    """
    if not filepath or not os.path.exists(filepath):
        return None
    filename = os.path.basename(filepath)
    return f"/orchestrator/plan-preview/{filename}"


def cleanup_old_previews(max_age_hours: int = 24):
    """清理过期的预览文件"""
    try:
        if not os.path.exists(OUTPUT_DIR):
            return
        now = datetime.now().timestamp()
        max_age = max_age_hours * 3600
        count = 0
        for f in os.listdir(OUTPUT_DIR):
            if f.endswith('.html'):
                filepath = os.path.join(OUTPUT_DIR, f)
                if now - os.path.getmtime(filepath) > max_age:
                    os.remove(filepath)
                    count += 1
        if count > 0:
            print(f"[HTML Generator] 清理了 {count} 个过期预览文件")
    except Exception as e:
        print(f"[HTML Generator] 清理失败: {e}")
