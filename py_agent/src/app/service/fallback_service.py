"""
降级服务 - 主服务失败时自动切换备用

设计思路：
1. 模型降级：主模型失败时切换到备用模型
2. 服务降级：主服务失败时切换到备用服务
3. 功能降级：关闭非核心功能，保证核心功能可用

降级级别：
- Level 0: 完全正常，使用主服务
- Level 1: 切换到备用模型
- Level 2: 切换到备用服务
- Level 3: 只保留核心功能（关闭工具调用）
- Level 4: 只返回缓存结果或默认响应

触发条件：
- 连续失败次数超过阈值
- 响应时间超过阈值
- 错误率超过阈值
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Any, Dict, List, Optional

import redis

logger = logging.getLogger(__name__)


class DegradationLevel(Enum):
    """降级级别枚举"""
    NORMAL = 0          # 正常状态
    BACKUP_MODEL = 1    # 备用模型
    BACKUP_SERVICE = 2  # 备用服务
    CORE_ONLY = 3       # 只保留核心功能
    CACHE_ONLY = 4      # 只返回缓存结果


class FallbackService:
    """降级服务

    核心功能：
    - 模型降级
    - 服务降级
    - 功能降级
    - 自动恢复检测
    """

    def __init__(self, redis_client):
        self.redis = redis_client

        # 降级配置
        self.failure_threshold = 3        # 连续失败次数阈值
        self.response_time_threshold = 10  # 响应时间阈值（秒）
        self.error_rate_threshold = 0.5    # 错误率阈值（50%）
        self.recovery_interval = 300      # 恢复检测间隔（秒）

        # 模型配置
        self.primary_model = None
        self.backup_model = None

        # 当前降级级别
        self.current_level = DegradationLevel.NORMAL

        # 失败记录
        self.failure_count = 0
        self.last_failure_time = 0
        self.last_success_time = time.time()

        # 统计
        self.stats = {
            "total_requests": 0,
            "primary_success": 0,
            "primary_failure": 0,
            "fallback_success": 0,
            "fallback_failure": 0,
        }

    def configure_models(self, primary_model: str, backup_model: str):
        """配置主模型和备用模型

        Args:
            primary_model: 主模型名称
            backup_model: 备用模型名称
        """
        self.primary_model = primary_model
        self.backup_model = backup_model
        logger.info(f"配置模型: primary={primary_model}, backup={backup_model}")

    async def call_with_fallback(self, messages: List[Dict[str, Any]],
                                 tools: Optional[List] = None,
                                 primary_func = None,
                                 backup_func = None,
                                 **kwargs) -> Dict[str, Any]:
        """带降级的模型调用

        Args:
            messages: 消息列表
            tools: 工具列表
            primary_func: 主模型调用函数
            backup_func: 备用模型调用函数
            **kwargs: 其他参数

        Returns:
            模型响应
        """
        self.stats["total_requests"] += 1

        # 检查当前降级级别
        if self.current_level == DegradationLevel.CACHE_ONLY:
            return await self._get_cached_response(messages)

        if self.current_level == DegradationLevel.CORE_ONLY:
            # 只保留核心功能，不调用工具
            tools = None

        # 尝试主模型
        if self.current_level in [DegradationLevel.NORMAL, DegradationLevel.CORE_ONLY]:
            try:
                if primary_func:
                    result = await asyncio.wait_for(
                        primary_func(messages, tools, **kwargs),
                        timeout=self.response_time_threshold
                    )
                    await self._record_success()
                    return result
            except asyncio.TimeoutError:
                logger.warning(f"主模型超时 ({self.response_time_threshold}s)")
                await self._record_failure("timeout")
            except Exception as e:
                logger.warning(f"主模型失败: {e}")
                await self._record_failure(str(e))

        # 切换到备用模型
        if self.backup_model and (self.current_level in [DegradationLevel.NORMAL, DegradationLevel.BACKUP_MODEL]):
            try:
                logger.info(f"切换到备用模型: {self.backup_model}")
                if backup_func:
                    result = await asyncio.wait_for(
                        backup_func(messages, tools, **kwargs),
                        timeout=self.response_time_threshold
                    )
                    self.stats["fallback_success"] += 1
                    return result
            except asyncio.TimeoutError:
                logger.warning(f"备用模型超时 ({self.response_time_threshold}s)")
                await self._record_failure("backup_timeout")
            except Exception as e:
                logger.warning(f"备用模型失败: {e}")
                await self._record_failure(str(e))

        # 所有模型都失败，返回默认响应
        return await self._get_default_response(messages)

    async def _record_success(self):
        """记录成功"""
        self.stats["primary_success"] += 1
        self.failure_count = 0
        self.last_success_time = time.time()

        # 如果当前是降级状态，考虑恢复
        if self.current_level != DegradationLevel.NORMAL:
            await self._try_recover()

    async def _record_failure(self, error: str):
        """记录失败

        Args:
            error: 错误信息
        """
        self.stats["primary_failure"] += 1
        self.failure_count += 1
        self.last_failure_time = time.time()

        # 检查是否需要降级
        if self.failure_count >= self.failure_threshold:
            await self._degrade()

    async def _degrade(self):
        """执行降级"""
        old_level = self.current_level

        if self.current_level == DegradationLevel.NORMAL:
            self.current_level = DegradationLevel.BACKUP_MODEL
        elif self.current_level == DegradationLevel.BACKUP_MODEL:
            self.current_level = DegradationLevel.BACKUP_SERVICE
        elif self.current_level == DegradationLevel.BACKUP_SERVICE:
            self.current_level = DegradationLevel.CORE_ONLY
        elif self.current_level == DegradationLevel.CORE_ONLY:
            self.current_level = DegradationLevel.CACHE_ONLY

        if old_level != self.current_level:
            logger.warning(f"降级: {old_level.name} -> {self.current_level.name}")

            # 保存降级状态到 Redis
            self._save_state()

    def _try_recover(self):
        """尝试恢复"""
        # 检查是否满足恢复条件
        time_since_last_failure = time.time() - self.last_failure_time

        if time_since_last_failure < self.recovery_interval:
            return

        old_level = self.current_level

        if self.current_level == DegradationLevel.CACHE_ONLY:
            self.current_level = DegradationLevel.CORE_ONLY
        elif self.current_level == DegradationLevel.CORE_ONLY:
            self.current_level = DegradationLevel.BACKUP_SERVICE
        elif self.current_level == DegradationLevel.BACKUP_SERVICE:
            self.current_level = DegradationLevel.BACKUP_MODEL
        elif self.current_level == DegradationLevel.BACKUP_MODEL:
            self.current_level = DegradationLevel.NORMAL

        if old_level != self.current_level:
            logger.info(f"恢复: {old_level.name} -> {self.current_level.name}")
            self._save_state()

    def _get_cached_response(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """获取缓存响应

        Args:
            messages: 消息列表

        Returns:
            缓存的响应或默认响应
        """
        # TODO: 实现缓存响应逻辑
        return self._get_default_response(messages)

    def _get_default_response(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """获取默认响应

        Args:
            messages: 消息列表

        Returns:
            默认响应
        """
        return {
            "content": "抱歉，当前服务暂时不可用，请稍后再试。",
            "model": "default",
            "error": True,
            "degradation_level": self.current_level.name,
        }

    def _save_state(self):
        """保存状态到 Redis（同步）"""
        try:
            state = {
                "current_level": self.current_level.value,
                "failure_count": self.failure_count,
                "last_failure_time": self.last_failure_time,
                "last_success_time": self.last_success_time,
                "stats": self.stats,
            }
            self.redis.setex(
                "fallback:state",
                3600,  # 1 小时过期
                json.dumps(state)
            )
        except Exception as e:
            logger.error(f"保存降级状态失败: {e}")

    def load_state(self):
        """从 Redis 加载状态（同步）"""
        try:
            data = self.redis.get("fallback:state")
            if data:
                state = json.loads(data)
                self.current_level = DegradationLevel(state.get("current_level", 0))
                self.failure_count = state.get("failure_count", 0)
                self.last_failure_time = state.get("last_failure_time", 0)
                self.last_success_time = state.get("last_success_time", time.time())
                self.stats = state.get("stats", self.stats)
                logger.info(f"加载降级状态: level={self.current_level.name}")
        except Exception as e:
            logger.error(f"加载降级状态失败: {e}")

    def get_status(self) -> Dict[str, Any]:
        """获取降级状态

        Returns:
            状态信息字典
        """
        return {
            "current_level": self.current_level.name,
            "failure_count": self.failure_count,
            "stats": self.stats,
            "primary_model": self.primary_model,
            "backup_model": self.backup_model,
        }

    def reset(self):
        """重置降级状态"""
        self.current_level = DegradationLevel.NORMAL
        self.failure_count = 0
        self.last_failure_time = 0
        self.last_success_time = time.time()
        logger.info("重置降级状态")


import json
