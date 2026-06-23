"""
性能监控中间件 - 自动记录请求指标

功能：
1. 自动为每个请求生成唯一 ID
2. 记录请求开始和结束时间
3. 统计 Token 消耗
4. 记录错误信息
5. 提供请求追踪能力

用法：
app.add_middleware(MetricsMiddleware, metrics_service=metrics_service)
"""

import time
import uuid
import logging
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """性能监控中间件

    自动记录每个请求的：
    - 请求 ID
    - 处理时间
    - Token 消耗
    - 错误信息
    """

    def __init__(self, app, metrics_service):
        super().__init__(app)
        self.metrics = metrics_service

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 为每个请求生成唯一 ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # 记录请求信息
        endpoint = request.url.path
        method = request.method
        user_id = self._extract_user_id(request)

        # 开始记录
        metrics = self.metrics.start_request(
            request_id=request_id,
            user_id=user_id,
            endpoint=f"{method} {endpoint}"
        )

        # 记录请求开始时间
        start_time = time.time()

        try:
            # 处理请求
            response = await call_next(request)

            # 计算处理时间
            duration = time.time() - start_time

            # 尝试从响应中获取 Token 消耗
            token_count = self._extract_token_count(response)

            # 结束记录
            self.metrics.end_request(
                request_id=request_id,
                token_count=token_count
            )

            # 添加请求 ID 到响应头
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration:.3f}s"

            return response

        except Exception as e:
            # 记录错误
            duration = time.time() - start_time
            self.metrics.end_request(
                request_id=request_id,
                error=str(e),
                error_type=self._classify_error(e)
            )

            logger.error(f"请求失败: {request_id}, 错误: {e}, 耗时: {duration:.3f}s")
            raise

    def _extract_user_id(self, request: Request) -> str:
        """从请求中提取用户 ID

        Args:
            request: 请求对象

        Returns:
            用户 ID 或空字符串
        """
        # 尝试从请求头获取
        user_id = request.headers.get("X-User-ID")
        if user_id:
            return user_id

        # 尝试从 JWT token 获取
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            # TODO: 解析 JWT token 获取用户 ID
            pass

        return ""

    def _extract_token_count(self, response: Response) -> int:
        """从响应中提取 Token 消耗

        Args:
            response: 响应对象

        Returns:
            Token 数量
        """
        # 尝试从响应头获取
        token_header = response.headers.get("X-Token-Count")
        if token_header:
            try:
                return int(token_header)
            except ValueError:
                pass

        return 0

    def _classify_error(self, error: Exception) -> str:
        """对错误进行分类

        Args:
            error: 错误异常

        Returns:
            错误类型字符串
        """
        error_msg = str(error).lower()
        error_type = type(error).__name__.lower()

        if "timeout" in error_msg:
            return "timeout"
        elif "rate limit" in error_msg or "429" in error_msg:
            return "rate_limit"
        elif "503" in error_msg or "unavailable" in error_msg:
            return "service_unavailable"
        elif "json" in error_msg or "parse" in error_msg:
            return "invalid_response"
        elif "tool" in error_msg:
            return "tool_error"
        else:
            return "unknown"
