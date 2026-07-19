"""
数据库连接池 —— 全局共享 MySQL 连接池 + 查询工具

所有 MySQL 持久化模块（plan_store / document_store）统一使用此连接池，
避免多模块各自创建池子导致连接浪费。
"""

import aiomysql
from config import settings
from typing import Optional, Dict, Any, List

# ── MySQL 连接配置 ──────────────────────────────────────────
DB_HOST = settings.DB_HOST
DB_PORT = settings.DB_PORT
DB_USER = settings.DB_USER
DB_PASSWORD = settings.DB_PASSWORD
DB_NAME = settings.DB_NAME

# 全局连接池（单例）
_pool: aiomysql.Pool = None


async def get_pool() -> aiomysql.Pool:
    """获取（或创建）全局 MySQL 连接池"""
    global _pool
    if _pool is None:
        _pool = await aiomysql.create_pool(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            db=DB_NAME,
            charset="utf8mb4",
            autocommit=True,
            minsize=1,
            maxsize=10,
        )
    return _pool


async def close_pool():
    """关闭连接池（应用退出时调用）"""
    global _pool
    if _pool:
        _pool.close()
        await _pool.wait_closed()
        _pool = None


async def _query_one(sql: str, params: tuple = None) -> Optional[Dict]:
    """执行查询，返回单行 dict"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(sql, params)
            return await cur.fetchone()


async def _query_all(sql: str, params: tuple = None) -> List[Dict]:
    """执行查询，返回多行 list[dict]"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(sql, params)
            return await cur.fetchall()


async def _execute(sql: str, params: tuple = None) -> int:
    """执行 INSERT/UPDATE/DELETE，返回 lastrowid"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, params)
            return cur.lastrowid


async def _execute_rowcount(sql: str, params: tuple = None) -> int:
    """执行 UPDATE/DELETE，返回 affected rows"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            return await cur.execute(sql, params)
