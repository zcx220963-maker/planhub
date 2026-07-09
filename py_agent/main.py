"""
PlanHub AI 服务 - 应用入口

安全架构：
1. Python AI 服务作为内部服务，只监听 127.0.0.1，不直接暴露给外部
2. 只接受来自 Java 后端的内部请求（通过 X-Internal-Api-Secret 鉴权）
3. 前端请求必须经过 Java 后端（JWT 鉴权），由 Java 转发到 Python

性能优化：
1. 记忆系统（短期/工作/长期记忆）
2. 上下文工程（智能历史过滤、上下文压缩）
3. 工具调用优化（缓存、重试）
4. 性能监控（请求耗时、Token 消耗）
5. 错误恢复和降级
"""

import sys
import os

# 将项目根目录和 src 目录添加到 Python 路径
# 这样 config.py 在根目录，app 在 src/ 目录
project_root = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(project_root, "src")
sys.path.insert(0, project_root)
sys.path.insert(0, src_path)

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from config import settings
from src.app.dao.redis_dao import init_redis, get_redis_client

# 导入路由
from src.app.api.chat import router as chat_router
from src.app.api.assistant import router as assistant_router
from src.app.api.rag import router as rag_router
from src.app.api.conversations import router as conversation_router
from src.app.api.orchestrator import router as orchestrator_router  # LangGraph 统一入口

# 导入性能监控中间件
from src.app.middleware.metrics_middleware import MetricsMiddleware
from src.app.service.metrics_service import MetricsService

# 创建 FastAPI 应用（类似 Spring Boot 的 @SpringBootApplication）
app = FastAPI(
    title="PlanHub AI 服务（内部）",
    description="PlanHub 的 AI 内部服务，仅接受 Java 后端的转发请求",
    version="1.1.0"
)

# 添加 CORS 中间件（只允许来自 Java 后端的请求，Java 通常在 8080 端口）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化性能监控服务
metrics_service = None
if settings.use_redis_bool:
    try:
        redis_client = get_redis_client()
        metrics_service = MetricsService(redis_client)
        print("[INFO] 性能监控服务初始化完成")
    except Exception as e:
        print(f"[WARN] 性能监控服务初始化失败: {e}")

# 添加性能监控中间件
if metrics_service:
    app.add_middleware(MetricsMiddleware, metrics_service=metrics_service)
    print("[INFO] 性能监控中间件已注册")


# ─── 内部鉴权中间件 ─────────────────────────────────────────────
# 每个请求必须携带正确的 X-Internal-Api-Secret Header
# 这是防止外部直接访问 Python 服务的关键防线
@app.middleware("http")
async def internal_auth_middleware(request: Request, call_next):
    """内部 API 鉴权中间件
    
    所有请求必须携带正确的 X-Internal-Api-Secret Header
    只有 Java 后端知道这个密钥，因此可以确保请求来自可信来源
    """
    # 放行健康检查和根路径（便于调试，但仍建议在生产中限制
    path = request.url.path
    if path in ["/", "/health"]:
        return await call_next(request)
    
    # 验证内部密钥
    provided_secret = request.headers.get(settings.AI_INTERNAL_SECRET_HEADER)
    
    if not provided_secret:
        return JSONResponse(
            status_code=401,
            content={"detail": "Missing internal API secret header"}
        )
    
    if provided_secret != settings.AI_INTERNAL_SECRET:
        return JSONResponse(
            status_code=403,
            content={"detail": "Invalid internal API secret"}
        )
    
    return await call_next(request)


# 注册路由（类似 @RequestMapping）
app.include_router(chat_router)
app.include_router(assistant_router)
app.include_router(rag_router)
app.include_router(conversation_router)
app.include_router(orchestrator_router)  # LangGraph 统一入口


# 应用启动时的初始化（类似 @PostConstruct 或 ApplicationRunner）
@app.on_event("startup")
async def startup_event():
    """应用启动时初始化"""
    if settings.use_redis_bool:
        init_redis()
        print("[INFO] Redis 初始化完成")

    # 从 original_docs 磁盘目录重建 RAG 文档索引（BM25 + 内存索引）
    try:
        from src.app.api.rag import init_document_indices, init_vector_store
        init_vector_store()
        init_document_indices()
        print("[INFO] RAG 索引初始化完成")
    except Exception as e:
        print(f"[WARN] RAG 初始化失败: {e}")

    # 初始化降级服务
    try:
        from src.app.service.fallback_service import FallbackService
        from src.app.dao.redis_dao import get_redis_client
        redis_client = get_redis_client()
        fallback_service = FallbackService(redis_client)
        fallback_service.load_state()  # 同步调用
        print("[INFO] 降级服务初始化完成")
    except Exception as e:
        print(f"[WARN] 降级服务初始化失败: {e}")

    print("[INFO] PlanHub AI 服务启动完成")


@app.get("/")
async def root():
    return {
        "message": "PlanHub AI 内部服务已启动",
        "version": "1.1.0",
        "security_note": "此服务仅接受 Java 后端的内部请求，外部直接访问将被拒绝",
        "endpoints": {
            "chat": "/chat",
            "assistant": "/assistant",
            "rag": "/rag",
            "conversations": "/conversations",
            "orchestrator": "/orchestrator (LangGraph统一入口)"
        }
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "planhub-ai-internal"}


# ─── 性能指标接口 ─────────────────────────────────────────────
@app.get("/metrics")
async def get_metrics(hours: int = 24):
    """获取性能指标统计

    Args:
        hours: 统计最近 N 小时，默认 24 小时

    Returns:
        性能指标
    """
    if not metrics_service:
        return {"error": "性能监控服务未初始化"}

    stats = await metrics_service.get_statistics(hours)
    return stats


@app.get("/metrics/requests")
async def get_recent_requests(limit: int = 10):
    """获取最近的请求列表

    Args:
        limit: 返回数量，默认 10

    Returns:
        请求列表
    """
    if not metrics_service:
        return {"requests": []}

    requests = await metrics_service.get_recent_requests(limit)
    return {"requests": requests}


@app.get("/metrics/slow")
async def get_slow_requests(threshold: float = 5.0, hours: int = 24):
    """获取慢请求列表

    Args:
        threshold: 耗时阈值（秒），默认 5 秒
        hours: 时间范围（小时），默认 24 小时

    Returns:
        慢请求列表
    """
    if not metrics_service:
        return {"slow_requests": []}

    slow_requests = await metrics_service.get_slow_requests(threshold, hours)
    return {"slow_requests": slow_requests}


@app.get("/metrics/errors")
async def get_error_requests(hours: int = 24):
    """获取错误请求列表

    Args:
        hours: 时间范围（小时），默认 24 小时

    Returns:
        错误请求列表
    """
    if not metrics_service:
        return {"error_requests": []}

    error_requests = await metrics_service.get_error_requests(hours)
    return {"error_requests": error_requests}


if __name__ == "__main__":
    import uvicorn
    print(f"[INFO] PlanHub AI 内部服务启动于 http://{settings.HOST}:{settings.PORT}")
    print(f"[INFO] 此服务只监听 127.0.0.1，不直接暴露给外部")
    print(f"[INFO] 所有请求必须携带 Header: {settings.AI_INTERNAL_SECRET_HEADER}: <内部密钥>")
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True  # 开发模式自动重载
    )
