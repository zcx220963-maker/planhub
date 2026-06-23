"""
工具调用缓存服务 - 提高工具调用效率

设计思路：
1. 结果缓存：相同查询复用，减少重复调用
2. 缓存过期：根据工具类型设置不同的 TTL
3. 缓存清理：支持按工具名或全部清除

缓存策略：
- 查询类工具：缓存 5 分钟（如搜索、知识库查询）
- 计算类工具：缓存 10 分钟（如数据分析）
- 用户相关：缓存 1 分钟（如用户信息）
- 实时数据：不缓存（如天气、新闻）

技术实现：
- 使用 Redis 作为缓存后端
- 缓存 key = tool_name + params_hash
- 支持 TTL 和手动清理
"""

import hashlib
import json
import logging
import time
from typing import Any, Dict, List, Optional

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class ToolCacheService:
    """工具调用缓存服务

    核心功能：
    - 缓存工具调用结果
    - 自动过期管理
    - 缓存统计
    """

    # 默认缓存 TTL（秒）
    DEFAULT_TTL = 300  # 5 分钟

    # 工具类型对应的 TTL
    TOOL_TTL_MAP = {
        # 查询类（5 分钟）
        "search": 300,
        "web_search": 300,
        "knowledge_base": 300,
        "rag_query": 300,

        # 计算类（10 分钟）
        "calculator": 600,
        "data_analysis": 600,
        "statistics": 600,

        # 用户相关（1 分钟）
        "user_info": 60,
        "user_profile": 60,
        "user_preferences": 60,

        # 配置类（30 分钟）
        "config": 1800,
        "settings": 1800,

        # 不缓存
        "weather": 0,
        "news": 0,
        "realtime": 0,
    }

    def __init__(self, redis_client: redis.Redis, default_ttl: int = None):
        self.redis = redis_client
        self.default_ttl = default_ttl or self.DEFAULT_TTL

        # 统计信息
        self.stats = {
            "hits": 0,
            "misses": 0,
            "total_requests": 0,
        }

    def _make_key(self, tool_name: str, params: Dict[str, Any]) -> str:
        """生成缓存 key

        Args:
            tool_name: 工具名称
            params: 工具参数

        Returns:
            缓存 key
        """
        # 序列化参数并计算哈希
        param_str = json.dumps(params, sort_keys=True, ensure_ascii=False)
        param_hash = hashlib.md5(param_str.encode()).hexdigest()

        return f"tool:cache:{tool_name}:{param_hash}"

    def _get_ttl(self, tool_name: str) -> int:
        """获取工具的缓存 TTL

        Args:
            tool_name: 工具名称

        Returns:
            TTL（秒），0 表示不缓存
        """
        # 精确匹配
        if tool_name in self.TOOL_TTL_MAP:
            return self.TOOL_TTL_MAP[tool_name]

        # 模糊匹配
        for key, ttl in self.TOOL_TTL_MAP.items():
            if key in tool_name.lower():
                return ttl

        # 默认 TTL
        return self.default_ttl

    async def get(self, tool_name: str, params: Dict[str, Any]) -> Optional[Any]:
        """获取缓存结果

        Args:
            tool_name: 工具名称
            params: 工具参数

        Returns:
            缓存结果，如果不存在返回 None
        """
        self.stats["total_requests"] += 1

        # 检查是否需要缓存
        ttl = self._get_ttl(tool_name)
        if ttl == 0:
            self.stats["misses"] += 1
            return None

        try:
            key = self._make_key(tool_name, params)
            data = await self.redis.get(key)

            if data:
                self.stats["hits"] += 1
                result = json.loads(data)
                logger.debug(f"缓存命中: {tool_name}")
                return result
            else:
                self.stats["misses"] += 1
                logger.debug(f"缓存未命中: {tool_name}")
                return None
        except Exception as e:
            logger.error(f"获取缓存失败: {e}")
            self.stats["misses"] += 1
            return None

    async def set(self, tool_name: str, params: Dict[str, Any],
                  result: Any, ttl: int = None) -> bool:
        """设置缓存

        Args:
            tool_name: 工具名称
            params: 工具参数
            result: 要缓存的结果
            ttl: 自定义 TTL（可选）

        Returns:
            是否成功
        """
        # 检查是否需要缓存
        if ttl is None:
            ttl = self._get_ttl(tool_name)

        if ttl == 0:
            return False

        try:
            key = self._make_key(tool_name, params)
            data = json.dumps(result, ensure_ascii=False, default=str)

            await self.redis.setex(key, ttl, data)
            logger.debug(f"设置缓存: {tool_name}, TTL={ttl}s")
            return True
        except Exception as e:
            logger.error(f"设置缓存失败: {e}")
            return False

    async def get_or_set(self, tool_name: str, params: Dict[str, Any],
                         fetch_func, ttl: int = None) -> Any:
        """获取缓存，如果不存在则调用函数获取并缓存

        Args:
            tool_name: 工具名称
            params: 工具参数
            fetch_func: 获取数据的异步函数
            ttl: 自定义 TTL（可选）

        Returns:
            结果
        """
        # 尝试获取缓存
        cached = await self.get(tool_name, params)
        if cached is not None:
            return cached

        # 调用函数获取结果
        result = await fetch_func()

        # 缓存结果
        await self.set(tool_name, params, result, ttl)

        return result

    async def clear(self, tool_name: str = None) -> int:
        """清除缓存

        Args:
            tool_name: 工具名称，如果为 None 则清除所有缓存

        Returns:
            清除的缓存数量
        """
        try:
            if tool_name:
                pattern = f"tool:cache:{tool_name}:*"
            else:
                pattern = "tool:cache:*"

            # 查找匹配的 key
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)

            if not keys:
                return 0

            # 删除所有匹配的 key
            await self.redis.delete(*keys)
            logger.info(f"清除缓存: {tool_name or 'all'}, count={len(keys)}")
            return len(keys)
        except Exception as e:
            logger.error(f"清除缓存失败: {e}")
            return 0

    async def clear_expired(self) -> int:
        """清除已过期的缓存（Redis 自动处理，此方法用于手动清理）

        Returns:
            清除的缓存数量
        """
        # Redis 会自动删除过期的 key，这里可以做一些额外的清理
        # 比如清理统计信息等
        return 0

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息

        Returns:
            统计信息字典
        """
        total = self.stats["total_requests"]
        hits = self.stats["hits"]
        misses = self.stats["misses"]

        return {
            "total_requests": total,
            "hits": hits,
            "misses": misses,
            "hit_rate": hits / total if total > 0 else 0,
            "hit_rate_percent": f"{(hits / total * 100):.1f}%" if total > 0 else "0%",
        }

    def reset_stats(self) -> None:
        """重置统计信息"""
        self.stats = {
            "hits": 0,
            "misses": 0,
            "total_requests": 0,
        }

    async def get_cache_size(self, tool_name: str = None) -> int:
        """获取缓存大小（key 数量）

        Args:
            tool_name: 工具名称，如果为 None 则统计所有缓存

        Returns:
            缓存 key 数量
        """
        try:
            if tool_name:
                pattern = f"tool:cache:{tool_name}:*"
            else:
                pattern = "tool:cache:*"

            count = 0
            async for _ in self.redis.scan_iter(match=pattern):
                count += 1

            return count
        except Exception as e:
            logger.error(f"获取缓存大小失败: {e}")
            return 0

    async def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存详细信息

        Returns:
            缓存信息字典
        """
        try:
            # 统计各工具的缓存数量
            tool_counts = {}
            total_size = 0

            async for key in self.redis.scan_iter(match="tool:cache:*"):
                # 解析工具名
                key_str = key.decode() if isinstance(key, bytes) else key
                parts = key_str.split(":")
                if len(parts) >= 3:
                    tool_name = parts[2]
                    tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1
                    total_size += 1

            return {
                "total_keys": total_size,
                "tool_counts": tool_counts,
                "stats": self.get_stats(),
            }
        except Exception as e:
            logger.error(f"获取缓存信息失败: {e}")
            return {"error": str(e)}


class CachedTool:
    """带缓存的工具包装器

    用法：
    cached_tool = CachedTool(original_tool, cache_service)
    result = await cached_tool.call(**params)
    """

    def __init__(self, tool: Any, cache_service: ToolCacheService):
        self.tool = tool
        self.cache = cache_service
        self.name = getattr(tool, 'name', 'unknown')

    async def call(self, **kwargs) -> Any:
        """调用工具（带缓存）"""
        # 尝试获取缓存
        cached = await self.cache.get(self.name, kwargs)
        if cached is not None:
            return cached

        # 调用原始工具
        if hasattr(self.tool, '_arun'):
            result = await self.tool._arun(**kwargs)
        elif hasattr(self.tool, 'run'):
            result = await self.tool.run(**kwargs)
        else:
            result = await self.tool(**kwargs)

        # 缓存结果
        await self.cache.set(self.name, kwargs, result)

        return result

    async def clear_cache(self) -> int:
        """清除此工具的缓存"""
        return await self.cache.clear(self.name)
