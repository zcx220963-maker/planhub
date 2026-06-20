"""
错误恢复服务 - 智能错误处理和恢复

设计思路：
1. 错误分类：根据错误类型和原因进行分类
2. 恢复策略：针对不同错误类型采用不同的恢复策略
3. 重试机制：指数退避重试
4. 降级策略：主服务失败时切换到备用服务

错误类型：
- TIMEOUT: 超时错误
- RATE_LIMIT: 速率限制
- SERVICE_UNAVAILABLE: 服务不可用
- INVALID_RESPONSE: 无效响应
- TOOL_ERROR: 工具调用错误
- CONTEXT_TOO_LONG: 上下文过长
- UNKNOWN: 未知错误

恢复策略：
- 重试（Retry）：超时、速率限制
- 降级（Fallback）：服务不可用
- 重生成（Regenerate）：无效响应
- 跳过工具（Skip Tool）：工具调用错误
- 压缩上下文（Compress Context）：上下文过长
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Any, Callable, Dict, Optional, Tuple

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """错误类型枚举"""
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    SERVICE_UNAVAILABLE = "service_unavailable"
    INVALID_RESPONSE = "invalid_response"
    TOOL_ERROR = "tool_error"
    CONTEXT_TOO_LONG = "context_too_long"
    MODEL_ERROR = "model_error"
    UNKNOWN = "unknown"


class RecoveryStrategy(Enum):
    """恢复策略枚举"""
    RETRY = "retry"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    FALLBACK_TO_BACKUP_MODEL = "fallback_to_backup_model"
    FALLBACK_TO_BACKUP_SERVICE = "fallback_to_backup_service"
    REGENERATE = "regenerate"
    SKIP_TOOL = "skip_tool"
    COMPRESS_CONTEXT = "compress_context"
    GRACEFUL_FAILURE = "graceful_failure"


class ErrorRecoveryService:
    """错误恢复服务

    核心功能：
    - 错误分类
    - 恢复策略选择
    - 重试和降级
    """

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client

        # 重试配置
        self.max_retries = 3
        self.base_delay = 1  # 基础延迟（秒）
        self.max_delay = 30  # 最大延迟（秒）

        # 错误类型 -> 恢复策略映射
        self.recovery_strategies: Dict[ErrorType, RecoveryStrategy] = {
            ErrorType.TIMEOUT: RecoveryStrategy.RETRY_WITH_BACKOFF,
            ErrorType.RATE_LIMIT: RecoveryStrategy.RETRY_WITH_BACKOFF,
            ErrorType.SERVICE_UNAVAILABLE: RecoveryStrategy.FALLBACK_TO_BACKUP_SERVICE,
            ErrorType.INVALID_RESPONSE: RecoveryStrategy.REGENERATE,
            ErrorType.TOOL_ERROR: RecoveryStrategy.SKIP_TOOL,
            ErrorType.CONTEXT_TOO_LONG: RecoveryStrategy.COMPRESS_CONTEXT,
            ErrorType.MODEL_ERROR: RecoveryStrategy.FALLBACK_TO_BACKUP_MODEL,
            ErrorType.UNKNOWN: RecoveryStrategy.GRACEFUL_FAILURE,
        }

        # 错误处理器映射
        self.error_handlers: Dict[ErrorType, Callable] = {
            ErrorType.TIMEOUT: self._handle_timeout,
            ErrorType.RATE_LIMIT: self._handle_rate_limit,
            ErrorType.SERVICE_UNAVAILABLE: self._handle_service_unavailable,
            ErrorType.INVALID_RESPONSE: self._handle_invalid_response,
            ErrorType.TOOL_ERROR: self._handle_tool_error,
            ErrorType.CONTEXT_TOO_LONG: self._handle_context_too_long,
            ErrorType.MODEL_ERROR: self._handle_model_error,
            ErrorType.UNKNOWN: self._handle_unknown,
        }

    def classify_error(self, error: Exception) -> ErrorType:
        """对错误进行分类

        Args:
            error: 错误异常

        Returns:
            错误类型
        """
        error_msg = str(error).lower()
        error_type = type(error).__name__.lower()

        # 超时错误
        if "timeout" in error_msg or "timed out" in error_msg:
            return ErrorType.TIMEOUT

        # 速率限制
        if "rate limit" in error_msg or "429" in error_msg or "too many requests" in error_msg:
            return ErrorType.RATE_LIMIT

        # 服务不可用
        if "503" in error_msg or "unavailable" in error_msg or "connection refused" in error_msg:
            return ErrorType.SERVICE_UNAVAILABLE

        # 无效响应
        if any(kw in error_msg for kw in ["json", "parse", "decode", "invalid format", "malformed"]):
            return ErrorType.INVALID_RESPONSE

        # 上下文过长
        if any(kw in error_msg for kw in ["context length", "token limit", "too long", "max_tokens"]):
            return ErrorType.CONTEXT_TOO_LONG

        # 模型错误
        if any(kw in error_msg for kw in ["model", "llm", "chat completion", "openai"]):
            return ErrorType.MODEL_ERROR

        # 工具错误
        if "tool" in error_msg:
            return ErrorType.TOOL_ERROR

        return ErrorType.UNKNOWN

    async def handle_error(self, error: Exception, context: Dict[str, Any] = None) -> Tuple[RecoveryStrategy, Any]:
        """处理错误并返回恢复策略和结果

        Args:
            error: 错误异常
            context: 上下文信息

        Returns:
            (恢复策略, 结果) 元组
        """
        context = context or {}
        error_type = self.classify_error(error)
        strategy = self.recovery_strategies.get(error_type, RecoveryStrategy.GRACEFUL_FAILURE)

        logger.error(f"错误分类: {error_type.value}, 策略: {strategy.value}, 错误: {error}")

        # 获取错误处理器
        handler = self.error_handlers.get(error_type, self._handle_unknown)

        # 执行恢复策略
        result = await handler(error, context)

        return strategy, result

    async def _handle_timeout(self, error: Exception, context: Dict[str, Any]) -> Any:
        """处理超时错误

        策略：指数退避重试

        Args:
            error: 错误异常
            context: 上下文

        Returns:
            重试结果或错误信息
        """
        retry_count = context.get("retry_count", 0)

        if retry_count < self.max_retries:
            delay = min(self.base_delay * (2 ** retry_count), self.max_delay)
            logger.info(f"超时重试 {retry_count + 1}/{self.max_retries}, 延迟 {delay}s")
            await asyncio.sleep(delay)

            # 更新重试计数
            context["retry_count"] = retry_count + 1
            return {"action": "retry", "delay": delay}
        else:
            logger.warning(f"超时重试次数用尽 ({self.max_retries})")
            return {"action": "fail", "reason": "max_retries_exceeded"}

    async def _handle_rate_limit(self, error: Exception, context: Dict[str, Any]) -> Any:
        """处理速率限制错误

        策略：延迟重试

        Args:
            error: 错误异常
            context: 上下文

        Returns:
            重试结果或错误信息
        """
        retry_count = context.get("retry_count", 0)

        if retry_count < self.max_retries:
            # 速率限制通常需要更长的延迟
            delay = min(self.base_delay * (2 ** retry_count) * 2, self.max_delay)
            logger.info(f"速率限制重试 {retry_count + 1}/{self.max_retries}, 延迟 {delay}s")
            await asyncio.sleep(delay)

            context["retry_count"] = retry_count + 1
            return {"action": "retry", "delay": delay}
        else:
            logger.warning(f"速率限制重试次数用尽 ({self.max_retries})")
            return {"action": "fail", "reason": "rate_limit_exceeded"}

    async def _handle_service_unavailable(self, error: Exception, context: Dict[str, Any]) -> Any:
        """处理服务不可用错误

        策略：切换到备用服务

        Args:
            error: 错误异常
            context: 上下文

        Returns:
            切换结果
        """
        logger.warning(f"服务不可用，尝试切换到备用服务")
        return {"action": "fallback_to_backup_service"}

    async def _handle_invalid_response(self, error: Exception, context: Dict[str, Any]) -> Any:
        """处理无效响应错误

        策略：重新生成

        Args:
            error: 错误异常
            context: 上下文

        Returns:
            重新生成指令
        """
        logger.warning(f"无效响应，重新生成")
        return {"action": "regenerate"}

    async def _handle_tool_error(self, error: Exception, context: Dict[str, Any]) -> Any:
        """处理工具调用错误

        策略：跳过工具继续执行

        Args:
            error: 错误异常
            context: 上下文

        Returns:
            跳过指令
        """
        tool_name = context.get("tool_name", "unknown")
        logger.warning(f"工具调用失败 ({tool_name})，跳过工具")
        return {"action": "skip_tool", "tool_name": tool_name}

    async def _handle_context_too_long(self, error: Exception, context: Dict[str, Any]) -> Any:
        """处理上下文过长错误

        策略：压缩上下文

        Args:
            error: 错误异常
            context: 上下文

        Returns:
            压缩指令
        """
        logger.warning(f"上下文过长，需要压缩")
        return {"action": "compress_context"}

    async def _handle_model_error(self, error: Exception, context: Dict[str, Any]) -> Any:
        """处理模型错误

        策略：切换到备用模型

        Args:
            error: 错误异常
            context: 上下文

        Returns:
            切换模型指令
        """
        logger.warning(f"模型错误，切换到备用模型")
        return {"action": "fallback_to_backup_model"}

    async def _handle_unknown(self, error: Exception, context: Dict[str, Any]) -> Any:
        """处理未知错误

        策略：优雅失败

        Args:
            error: 错误异常
            context: 上下文

        Returns:
            失败信息
        """
        logger.error(f"未知错误: {error}")
        return {"action": "graceful_failure", "error": str(error)}

    def get_error_summary(self, error: Exception) -> Dict[str, Any]:
        """获取错误摘要

        Args:
            error: 错误异常

        Returns:
            错误摘要字典
        """
        error_type = self.classify_error(error)
        strategy = self.recovery_strategies.get(error_type, RecoveryStrategy.GRACEFUL_FAILURE)

        return {
            "error_type": error_type.value,
            "error_message": str(error),
            "recovery_strategy": strategy.value,
            "timestamp": time.time(),
        }


class RetryWithBackoff:
    """带指数退避的重试装饰器

    用法：
    @RetryWithBackoff(max_retries=3, base_delay=1)
    async def my_function():
        ...
    """

    def __init__(self, max_retries: int = 3, base_delay: float = 1,
                 max_delay: float = 30, exponential_base: float = 2):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base

    def __call__(self, func):
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(self.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if attempt < self.max_retries:
                        delay = min(self.base_delay * (self.exponential_base ** attempt), self.max_delay)
                        logger.warning(f"重试 {attempt + 1}/{self.max_retries}, 延迟 {delay}s: {e}")
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"重试次数用尽 ({self.max_retries}): {e}")

            raise last_exception

        return wrapper


def with_retry(max_retries: int = 3, base_delay: float = 1,
               max_delay: float = 30, retryable_exceptions: tuple = (Exception,)):
    """重试装饰器（函数式）

    用法：
    @with_retry(max_retries=3, retryable_exceptions=(TimeoutError, ConnectionError))
    async def my_function():
        ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e

                    if attempt < max_retries:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        logger.warning(f"重试 {attempt + 1}/{max_retries}, 延迟 {delay}s: {e}")
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"重试次数用尽 ({max_retries}): {e}")

            raise last_exception

        return wrapper
    return decorator
