"""
PlanHub AI 服务 - 应用入口（LangGraph 架构）

安全架构：
1. Python AI 服务作为内部服务，只监听 127.0.0.1，不直接暴露给外部
2. 只接受来自 Java 后端的内部请求（通过 X-Internal-Api-Secret 鉴权）
3. 前端请求必须经过 Java 后端（JWT 鉴权），由 Java 转发到 Python

核心功能：
- LangGraph 多 Agent 编排
- RAG 知识库（向量 + BM25 双路召回 + LLM Rerank）
- 记忆系统（短期 Redis + 长期 Chroma）
- 工具调用（内部后端接口 + 外部 API）
"""

import sys
import os

project_root = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(project_root, "src")
sys.path.insert(0, project_root)
sys.path.insert(0, src_path)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from config import settings
from src.app.dao.redis_dao import init_redis

from src.app.api.rag_api import router as rag_router
from src.app.api.orchestrator import router as orchestrator_router


async def lifespan(app: FastAPI):
    """应用生命周期管理（替代 @app.on_event）"""
    print("[INFO] PlanHub AI 服务启动中...")
    
    if settings.use_redis_bool:
        init_redis()
        print("[INFO] Redis 初始化完成")

    try:
        from src.app.api.rag_api import init_document_indices, init_vector_store
        init_vector_store()
        init_document_indices()
        print("[INFO] RAG 索引初始化完成")
    except Exception as e:
        print(f"[WARN] RAG 初始化失败: {e}")

    print("[INFO] PlanHub AI 服务启动完成（LangGraph 架构）")
    yield
    
    print("[INFO] PlanHub AI 服务关闭中...")


app = FastAPI(
    title="PlanHub AI 服务（内部）",
    description="PlanHub 的 AI 内部服务，仅接受 Java 后端的转发请求",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def internal_auth_middleware(request: Request, call_next):
    """内部 API 鉴权中间件

    所有请求必须携带正确的 X-Internal-Api-Secret Header
    只有 Java 后端知道这个密钥，因此可以确保请求来自可信来源
    """
    path = request.url.path
    if path in ["/", "/health"]:
        return await call_next(request)

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


app.include_router(rag_router)
app.include_router(orchestrator_router)


@app.get("/")
async def root():
    return {
        "message": "PlanHub AI 内部服务已启动",
        "version": "2.0.0",
        "architecture": "LangGraph",
        "security_note": "此服务仅接受 Java 后端的内部请求，外部直接访问将被拒绝",
        "endpoints": {
            "rag": "/rag",
            "orchestrator": "/orchestrator (LangGraph统一入口)"
        }
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "planhub-ai-internal", "architecture": "LangGraph"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000)
