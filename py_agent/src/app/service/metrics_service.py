"""
性能评估服务 - 监控系统运行状态

设计思路：
1. 请求耗时监控：记录每个请求的处理时间
2. Token 消耗统计：追踪 LLM 调用的 Token 使用量
3. 错误率追踪：统计各类错误的发生频率
4. 实时指标：提供实时查询接口

数据结构：
- 每个请求一个指标记录
- 使用 Redis Sorted Set 按时间排序
- 自动清理 24 小时前的数据

指标类型：
- 请求总数
- 平均响应时间
- Token 消耗总量和平均值
- 错误率和错误分布
- 工具调用成功率
"""

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

import redis

import logging

logger = logging.getLogger(__name__)


@dataclass
class RequestMetrics:
    """请求指标"""
    request_id: str
    start_time: float
    end_time: float = 0
    duration: float = 0
    token_count: int = 0
    tool_calls: List[str] = field(default_factory=list)
    tool_success_count: int = 0
    tool_fail_count: int = 0
    error: Optional[str] = None
    error_type: Optional[str] = None
    model: str = ""
    endpoint: str = ""
    user_id: Optional[str] = None


class MetricsService:
    """性能评估服务

    核心功能：
    - 记录请求指标
    - 计算统计数据
    - 提供实时查询
    """

    def __init__(self, redis_client: redis.Redis, retention_hours: int = 24):
        self.redis = redis_client
        self.retention_hours = retention_hours
        self.retention_seconds = retention_hours * 3600

        # 活跃请求（内存中）
        self.active_requests: Dict[str, RequestMetrics] = {}

    def start_request(self, request_id: str = None, user_id: str = None,
                      endpoint: str = "", model: str = "") -> RequestMetrics:
        """开始记录请求

        Args:
            request_id: 请求 ID（可选，自动生成）
            user_id: 用户 ID
            endpoint: 请求端点
            model: 使用的模型

        Returns:
            RequestMetrics 对象
        """
        if request_id is None:
            request_id = str(uuid.uuid4())

        metrics = RequestMetrics(
            request_id=request_id,
            start_time=time.time(),
            user_id=user_id,
            endpoint=endpoint,
            model=model,
        )

        self.active_requests[request_id] = metrics
        logger.debug(f"开始记录请求: {request_id}")
        return metrics

    def end_request(self, request_id: str, token_count: int = 0,
                    error: str = None, error_type: str = None) -> Optional[RequestMetrics]:
        """结束记录请求

        Args:
            request_id: 请求 ID
            token_count: Token 消耗量
            error: 错误信息
            error_type: 错误类型

        Returns:
            RequestMetrics 对象，如果请求不存在返回 None
        """
        if request_id not in self.active_requests:
            logger.warning(f"请求不存在: {request_id}")
            return None

        metrics = self.active_requests.pop(request_id)
        metrics.end_time = time.time()
        metrics.duration = metrics.end_time - metrics.start_time
        metrics.token_count = token_count

        if error:
            metrics.error = error
            metrics.error_type = error_type or self._classify_error(error)

        # 同步保存到 Redis
        self._save_metrics(metrics)

        logger.debug(f"结束记录请求: {request_id}, duration={metrics.duration:.2f}s, tokens={token_count}")
        return metrics

    def record_tool_call(self, request_id: str, tool_name: str, success: bool = True):
        """记录工具调用

        Args:
            request_id: 请求 ID
            tool_name: 工具名称
            success: 是否成功
        """
        if request_id not in self.active_requests:
            return

        metrics = self.active_requests[request_id]
        metrics.tool_calls.append(tool_name)

        if success:
            metrics.tool_success_count += 1
        else:
            metrics.tool_fail_count += 1

    def _classify_error(self, error: str) -> str:
        """对错误进行分类

        Args:
            error: 错误信息

        Returns:
            错误类型
        """
        error_lower = str(error).lower()

        if "timeout" in error_lower:
            return "timeout"
        elif "rate limit" in error_lower or "429" in error_lower:
            return "rate_limit"
        elif "503" in error_lower or "unavailable" in error_lower:
            return "service_unavailable"
        elif "json" in error_lower or "parse" in error_lower:
            return "invalid_response"
        elif "tool" in error_lower:
            return "tool_error"
        else:
            return "unknown"

    def _save_metrics(self, metrics: RequestMetrics):
        """保存指标到 Redis（同步）

        Args:
            metrics: 请求指标
        """
        try:
            # 使用 Redis Sorted Set，按时间排序
            key = f"metrics:{int(metrics.start_time)}"
            data = {
                "request_id": metrics.request_id,
                "start_time": metrics.start_time,
                "duration": metrics.duration,
                "token_count": metrics.token_count,
                "tool_calls": len(metrics.tool_calls),
                "tool_success": metrics.tool_success_count,
                "tool_fail": metrics.tool_fail_count,
                "error": metrics.error,
                "error_type": metrics.error_type,
                "model": metrics.model,
                "endpoint": metrics.endpoint,
                "user_id": metrics.user_id,
            }

            pipe = self.redis.pipeline()
            pipe.zadd("metrics:timeline", {key: metrics.start_time})
            pipe.setex(key, self.retention_seconds, json.dumps(data))
            pipe.execute()

            logger.debug(f"保存指标: {metrics.request_id}")
        except Exception as e:
            logger.error(f"保存指标失败: {e}")

    def get_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """获取统计信息（同步）

        Args:
            hours: 统计最近 N 小时

        Returns:
            统计信息字典
        """
        try:
            min_time = time.time() - hours * 3600

            # 获取时间范围内的指标 key
            keys = self.redis.zrangebyscore("metrics:timeline", min_time, "+inf")

            if not keys:
                return self._empty_stats(hours)

            # 获取所有指标数据
            total_requests = len(keys)
            total_tokens = 0
            total_duration = 0
            error_count = 0
            error_types: Dict[str, int] = {}
            model_usage: Dict[str, int] = {}
            tool_call_count = 0
            tool_success_count = 0
            tool_fail_count = 0

            for key in keys:
                data = self.redis.get(key)
                if data:
                    metrics = json.loads(data)
                    total_tokens += metrics.get("token_count", 0)
                    total_duration += metrics.get("duration", 0)
                    tool_call_count += metrics.get("tool_calls", 0)
                    tool_success_count += metrics.get("tool_success", 0)
                    tool_fail_count += metrics.get("tool_fail", 0)

                    if metrics.get("error"):
                        error_count += 1
                        error_type = metrics.get("error_type", "unknown")
                        error_types[error_type] = error_types.get(error_type, 0) + 1

                    model = metrics.get("model", "unknown")
                    model_usage[model] = model_usage.get(model, 0) + 1

            return {
                "hours": hours,
                "total_requests": total_requests,
                "total_tokens": total_tokens,
                "total_tokens_formatted": self._format_tokens(total_tokens),
                "avg_duration": total_duration / total_requests if total_requests > 0 else 0,
                "avg_duration_formatted": f"{total_duration / total_requests:.2f}s" if total_requests > 0 else "0s",
                "avg_tokens_per_request": total_tokens / total_requests if total_requests > 0 else 0,
                "error_count": error_count,
                "error_rate": error_count / total_requests if total_requests > 0 else 0,
                "error_rate_percent": f"{(error_count / total_requests * 100):.1f}%" if total_requests > 0 else "0%",
                "error_types": error_types,
                "model_usage": model_usage,
                "total_tool_calls": tool_call_count,
                "tool_success_rate": tool_success_count / tool_call_count if tool_call_count > 0 else 1,
                "tool_success_rate_percent": f"{(tool_success_count / tool_call_count * 100):.1f}%" if tool_call_count > 0 else "100%",
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return self._empty_stats(hours)

    def _empty_stats(self, hours: int) -> Dict[str, Any]:
        """返回空统计信息

        Args:
            hours: 时间范围

        Returns:
            空统计信息字典
        """
        return {
            "hours": hours,
            "total_requests": 0,
            "total_tokens": 0,
            "total_tokens_formatted": "0",
            "avg_duration": 0,
            "avg_duration_formatted": "0s",
            "avg_tokens_per_request": 0,
            "error_count": 0,
            "error_rate": 0,
            "error_rate_percent": "0%",
            "error_types": {},
            "model_usage": {},
            "total_tool_calls": 0,
            "tool_success_rate": 1,
            "tool_success_rate_percent": "100%",
        }

    def _format_tokens(self, tokens: int) -> str:
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

    async def get_recent_requests(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近的请求

        Args:
            limit: 返回数量

        Returns:
            请求列表
        """
        try:
            # 获取最近的指标 key
            keys = await self.redis.zrevrange("metrics:timeline", 0, limit - 1)

            results = []
            for key in keys:
                data = await self.redis.get(key)
                if data:
                    results.append(json.loads(data))

            return results
        except Exception as e:
            logger.error(f"获取最近请求失败: {e}")
            return []

    async def get_slow_requests(self, threshold: float = 5.0, hours: int = 24) -> List[Dict[str, Any]]:
        """获取慢请求

        Args:
            threshold: 耗时阈值（秒）
            hours: 时间范围

        Returns:
            慢请求列表
        """
        try:
            min_time = time.time() - hours * 3600
            keys = await self.redis.zrangebyscore("metrics:timeline", min_time, "+inf")

            slow_requests = []
            for key in keys:
                data = await self.redis.get(key)
                if data:
                    metrics = json.loads(data)
                    if metrics.get("duration", 0) > threshold:
                        slow_requests.append(metrics)

            # 按耗时降序排序
            slow_requests.sort(key=lambda x: x.get("duration", 0), reverse=True)

            return slow_requests[:20]  # 最多返回 20 条
        except Exception as e:
            logger.error(f"获取慢请求失败: {e}")
            return []

    async def get_error_requests(self, hours: int = 24) -> List[Dict[str, Any]]:
        """获取错误请求

        Args:
            hours: 时间范围

        Returns:
            错误请求列表
        """
        try:
            min_time = time.time() - hours * 3600
            keys = await self.redis.zrangebyscore("metrics:timeline", min_time, "+inf")

            error_requests = []
            for key in keys:
                data = await self.redis.get(key)
                if data:
                    metrics = json.loads(data)
                    if metrics.get("error"):
                        error_requests.append(metrics)

            return error_requests
        except Exception as e:
            logger.error(f"获取错误请求失败: {e}")
            return []

    async def cleanup(self) -> int:
        """清理过期数据

        Returns:
            清理的数据数量
        """
        try:
            min_time = time.time() - self.retention_seconds

            # 获取过期的 key
            keys = await self.redis.zrangebyscore("metrics:timeline", "-inf", min_time)

            if not keys:
                return 0

            # 删除过期的 key
            pipe = self.redis.pipeline()
            for key in keys:
                pipe.delete(key)
            pipe.zremrangebyscore("metrics:timeline", "-inf", min_time)
            await pipe.execute()

            logger.info(f"清理过期数据: {len(keys)} 条")
            return len(keys)
        except Exception as e:
            logger.error(f"清理过期数据失败: {e}")
            return 0
