"""
Token 计数工具 - 估算文本的 Token 数量

由于不同的 LLM 使用不同的 tokenizer，这里提供几种估算方法：

1. 粗略估算（默认）：
   - 中文：1 字 ≈ 1.5 token
   - 英文：1 词 ≈ 1.3 token
   - 代码：1 行 ≈ 2-3 token

2. TikToken 精确计数（需要安装 tiktoken）：
   - 支持 GPT-4、GPT-3.5 等模型
   - 更准确，但需要额外的依赖

3. 字符估算（最简单）：
   - 总字符数 / 4
   - 适合快速估算

用法：
from token_counter import count_tokens, estimate_tokens

# 粗略估算
tokens = count_tokens("Hello, 世界!")

# TikToken 精确计数
tokens = count_tokens("Hello, 世界!", method="tiktoken", model="gpt-4")

# 字符估算
tokens = count_tokens("Hello, 世界!", method="char")
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def count_tokens(text: str, method: str = "estimate",
                 model: str = "gpt-3.5-turbo") -> int:
    """计算文本的 Token 数量

    Args:
        text: 输入文本
        method: 估算方法，可选 "estimate"、"tiktoken"、"char"
        model: 模型名称（仅 tiktoken 方法需要）

    Returns:
        Token 数量
    """
    if not text:
        return 0

    if method == "tiktoken":
        return _count_with_tiktoken(text, model)
    elif method == "char":
        return _count_by_chars(text)
    else:
        return _count_by_estimate(text)


def estimate_tokens(text: str) -> int:
    """快速估算 Token 数量（使用默认估算方法）

    Args:
        text: 输入文本

    Returns:
        Token 数量
    """
    return _count_by_estimate(text)


def _count_by_estimate(text: str) -> int:
    """粗略估算 Token 数量

    规则：
    - 中文字符：1 字 ≈ 1.5 token
    - 英文单词：1 词 ≈ 1.3 token
    - 数字：1 字符 ≈ 1 token
    - 标点符号：1 字符 ≈ 0.5 token
    - 空格：1 字符 ≈ 0.25 token

    Args:
        text: 输入文本

    Returns:
        Token 数量
    """
    # 统计中文字符数
    chinese_chars = len(re.findall(r'[一-鿿]', text))

    # 统计英文单词数
    english_words = re.findall(r'[a-zA-Z]+', text)
    english_count = len(english_words)

    # 统计数字
    digits = len(re.findall(r'[0-9]+', text))

    # 统计标点符号
    punctuations = len(re.findall(r'[^\w\s一-鿿]', text))

    # 统计空格
    spaces = len(re.findall(r'\s', text))

    # 计算 Token
    tokens = (
        chinese_chars * 1.5 +
        english_count * 1.3 +
        digits * 1.0 +
        punctuations * 0.5 +
        spaces * 0.25
    )

    return int(tokens)


def _count_by_chars(text: str) -> int:
    """基于字符数的简单估算

    规则：总字符数 / 4

    Args:
        text: 输入文本

    Returns:
        Token 数量
    """
    return len(text) // 4


def _count_with_tiktoken(text: str, model: str = "gpt-3.5-turbo") -> int:
    """使用 TikToken 精确计数

    Args:
        text: 输入文本
        model: 模型名称

    Returns:
        Token 数量
    """
    try:
        import tiktoken
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except ImportError:
        logger.warning("tiktoken 未安装，使用估算方法")
        return _count_by_estimate(text)
    except KeyError:
        logger.warning(f"模型 {model} 不支持，使用估算方法")
        return _count_by_estimate(text)
    except Exception as e:
        logger.error(f"TikToken 计数失败: {e}")
        return _count_by_estimate(text)


def count_messages_tokens(messages: list, method: str = "estimate",
                          model: str = "gpt-3.5-turbo") -> int:
    """计算消息列表的 Token 数量

    Args:
        messages: 消息列表，每个消息是 {"role": "...", "content": "..."}
        method: 估算方法
        model: 模型名称

    Returns:
        Token 数量
    """
    total_tokens = 0

    for message in messages:
        content = message.get("content", "")
        role = message.get("role", "")

        # 计算内容 Token
        content_tokens = count_tokens(content, method, model)

        # 计算角色 Token（通常 1-2 token）
        role_tokens = len(role) // 4

        # 每条消息的开销（通常 3-4 token）
        overhead = 3

        total_tokens += content_tokens + role_tokens + overhead

    return total_tokens


def truncate_text_by_tokens(text: str, max_tokens: int,
                            method: str = "estimate") -> str:
    """按 Token 数量截断文本

    Args:
        text: 输入文本
        max_tokens: 最大 Token 数量
        method: 估算方法

    Returns:
        截断后的文本
    """
    current_tokens = count_tokens(text, method)

    if current_tokens <= max_tokens:
        return text

    # 计算需要保留的比例
    ratio = max_tokens / current_tokens
    target_chars = int(len(text) * ratio * 0.9)  # 留一些余量

    # 截断文本
    truncated = text[:target_chars]

    # 确保不在单词或中文字符中间截断
    # 找到最后一个空格或标点
    last_space = truncated.rfind(" ")
    last_newline = truncated.rfind("\n")

    if last_space > target_chars * 0.8:
        truncated = truncated[:last_space]
    elif last_newline > target_chars * 0.8:
        truncated = truncated[:last_newline]

    return truncated + "..."


def format_token_count(tokens: int) -> str:
    """格式化 Token 数量

    Args:
        tokens: Token 数量

    Returns:
        格式化字符串
    """
    if tokens >= 1000000:
        return f"{tokens / 1000000:.1f}M"
    elif tokens >= 1000:
        return f"{tokens / 1000:.1f}K"
    else:
        return str(tokens)


# 常见模型的上下文窗口
MODEL_CONTEXT_WINDOWS = {
    "gpt-4": 8192,
    "gpt-4-32k": 32768,
    "gpt-4-turbo": 128000,
    "gpt-3.5-turbo": 16385,
    "gpt-3.5-turbo-16k": 16385,
    "claude-2": 100000,
    "claude-3-opus": 200000,
    "claude-3-sonnet": 200000,
    "claude-3-haiku": 200000,
    "qwen-plus": 8000,
    "qwen-max": 32000,
    "deepseek-chat": 128000,
    "glm-4": 128000,
    "moonshot-v1": 128000,
    "ollama/llama2": 4096,
    "ollama/llama3": 8192,
    "ollama/mistral": 8192,
    "ollama/qwen": 32000,
}


def get_model_context_window(model: str) -> int:
    """获取模型的上下文窗口大小

    Args:
        model: 模型名称

    Returns:
        上下文窗口大小（Token 数量）
    """
    # 精确匹配
    if model in MODEL_CONTEXT_WINDOWS:
        return MODEL_CONTEXT_WINDOWS[model]

    # 模糊匹配
    for key, value in MODEL_CONTEXT_WINDOWS.items():
        if key in model.lower() or model.lower() in key:
            return value

    # 默认 8K
    return 8192
